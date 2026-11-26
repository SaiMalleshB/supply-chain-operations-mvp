"""Run the project's deterministic topology comparison and export raw evidence.

This runner measures local execution traces and modeled token accounting. It does
not call an LLM, and its completion metric must not be read as business-task
correctness because expected scenario constraints are not programmatically checked.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from src.db.models import (
    DBExecutionUnit,
    DBEvidenceUnit,
    DBInventoryItem,
    DBLogisticsRoute,
    DBRunTrace,
    DBSupplierProfile,
)
from src.db.session import SessionLocal
from src.eval.scenarios import EVALUATION_SCENARIOS
from src.orchestration.topologies import TopologyRunner


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGIES = {
    "A - Single monolithic": TopologyRunner.run_single_monolithic_agent,
    "B - Sequential pipeline": TopologyRunner.run_sequential_pipeline,
    "C - Parallel supervisor": TopologyRunner.run_parallel_supervisor,
}
PACKAGES = (
    "langgraph",
    "SQLAlchemy",
    "pydantic",
    "pydantic-settings",
    "streamlit",
    "pytest",
    "pandas",
    "mcp",
)


def percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def trace_signature(trace: Any) -> str:
    def remove_run_ids(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: remove_run_ids(item)
                for key, item in value.items()
                if key not in {"run_id", "unit_id", "evidence_id", "evidence_ids", "timestamp", "execution_time_ms"}
            }
        if isinstance(value, list):
            return [remove_run_ids(item) for item in value]
        return value

    units = [
        {
            "agent": unit.agent_id,
            "type": unit.unit_type.value,
            "action": unit.action_name,
            "status": unit.status,
            "output": remove_run_ids(unit.output_payload),
        }
        for unit in trace.execution_units
    ]
    units.sort(key=lambda item: (item["agent"], item["action"], item["status"]))
    normalized = {
        "run_status": trace.status,
        "tokens": trace.total_token_accounting.total_tokens,
        "cost_estimate": trace.total_token_accounting.estimated_cost_usd,
        "units": units,
    }
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def persisted_counts(run_id: str) -> tuple[int, int, bool]:
    db = SessionLocal()
    try:
        run = db.query(DBRunTrace).filter(DBRunTrace.run_id == run_id).first()
        execution_count = db.query(DBExecutionUnit).filter(DBExecutionUnit.run_id == run_id).count()
        evidence_count = db.query(DBEvidenceUnit).filter(DBEvidenceUnit.run_id == run_id).count()
        persisted = (
            run is not None
            and execution_count == len(run.execution_units)
            and evidence_count == len(run.evidence_units)
        )
        return execution_count, evidence_count, persisted
    finally:
        db.close()


def package_versions() -> dict[str, str]:
    found: dict[str, str] = {}
    for package in PACKAGES:
        try:
            found[package] = version(package)
        except PackageNotFoundError:
            found[package] = "not installed in the active environment"
    return found


def summarize(rows: list[dict[str, Any]], repeats: int) -> dict[str, Any]:
    by_topology: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_topology[row["topology"]].append(row)
        by_cell[(row["topology"], row["scenario_id"])].append(row)

    aggregates = []
    for topology, group in by_topology.items():
        latencies = [float(row["latency_ms"]) for row in group]
        signatures_consistent = sum(
            len({row["outcome_signature"] for row in cells}) == 1
            for (cell_topology, _), cells in by_cell.items()
            if cell_topology == topology
        )
        aggregates.append(
            {
                "topology": topology,
                "runs": len(group),
                "completed_runs": sum(row["run_completed"] for row in group),
                "completion_rate_pct": round(100 * sum(row["run_completed"] for row in group) / len(group), 1),
                "median_latency_ms": round(statistics.median(latencies), 2),
                "p95_latency_ms": round(percentile95(latencies), 2),
                "mean_modeled_tokens": round(statistics.mean(row["modeled_tokens"] for row in group), 1),
                "mean_modeled_cost_usd": round(statistics.mean(row["modeled_cost_usd"] for row in group), 8),
                "mean_execution_units": round(statistics.mean(row["execution_units"] for row in group), 2),
                "mean_evidence_units": round(statistics.mean(row["evidence_units"] for row in group), 2),
                "mean_serialized_trace_bytes": round(statistics.mean(row["serialized_trace_bytes"] for row in group), 1),
                "evidence_link_integrity_pct": round(statistics.mean(row["evidence_link_integrity_pct"] for row in group), 1),
                "persisted_trace_count": sum(row["persisted_trace"] for row in group),
                "repeat_consistent_scenarios": signatures_consistent,
                "scenario_count": len(EVALUATION_SCENARIOS),
                "repeats_per_scenario": repeats,
            }
        )

    scenario_aggregates = []
    for (topology, scenario_id), group in by_cell.items():
        latencies = [float(row["latency_ms"]) for row in group]
        scenario_aggregates.append(
            {
                "topology": topology,
                "scenario_id": scenario_id,
                "runs": len(group),
                "completed_runs": sum(row["run_completed"] for row in group),
                "median_latency_ms": round(statistics.median(latencies), 2),
                "mean_modeled_tokens": round(statistics.mean(row["modeled_tokens"] for row in group), 1),
                "mean_modeled_cost_usd": round(statistics.mean(row["modeled_cost_usd"] for row in group), 8),
                "mean_execution_units": round(statistics.mean(row["execution_units"] for row in group), 2),
                "mean_evidence_units": round(statistics.mean(row["evidence_units"] for row in group), 2),
                "mean_serialized_trace_bytes": round(statistics.mean(row["serialized_trace_bytes"] for row in group), 1),
                "repeated_outcomes_identical": len({row["outcome_signature"] for row in group}) == 1,
            }
        )

    return {
        "method_note": (
            "Local deterministic code paths; run completion is not business-task success. "
            "Token counts are code-generated estimates, and cost is calculated from the "
            "configured illustrative rates; no provider API or live billing was used."
        ),
        "aggregate_by_topology": aggregates,
        "aggregate_by_scenario": scenario_aggregates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5, help="repeats per scenario and topology (default: 5)")
    parser.add_argument("--out-dir", default="results", help="output directory relative to project root")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    out_dir = (ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    for scenario in EVALUATION_SCENARIOS:
        for repeat in range(1, args.repeats + 1):
            for topology, run in TOPOLOGIES.items():
                started = __import__("time").perf_counter()
                trace = run(scenario.description, scenario.target_skus)
                latency_ms = (__import__("time").perf_counter() - started) * 1000
                all_evidence_ids = {evidence.evidence_id for evidence in trace.evidence_units}
                evidence_refs = [ref for unit in trace.execution_units for ref in unit.evidence_ids]
                valid_refs = sum(ref in all_evidence_ids for ref in evidence_refs)
                exec_count, evidence_count, persisted = persisted_counts(trace.run_id)
                rows.append(
                    {
                        "scenario_id": scenario.scenario_id,
                        "topology": topology,
                        "repeat": repeat,
                        "run_id": trace.run_id,
                        "run_status": trace.status,
                        "run_completed": trace.status == "COMPLETED",
                        "latency_ms": round(latency_ms, 3),
                        "modeled_tokens": trace.total_token_accounting.total_tokens,
                        "modeled_cost_usd": trace.total_token_accounting.estimated_cost_usd,
                        "execution_units": len(trace.execution_units),
                        "evidence_units": len(trace.evidence_units),
                        "retry_count": trace.retry_count,
                        "degraded_agents": len(trace.degraded_agents),
                        "tool_output_units": sum(unit.unit_type.value == "TOOL_OUTPUT" for unit in trace.execution_units),
                        "successful_tool_output_units": sum(unit.unit_type.value == "TOOL_OUTPUT" and unit.status == "SUCCESS" for unit in trace.execution_units),
                        "evidence_references": len(evidence_refs),
                        "valid_evidence_references": valid_refs,
                        "evidence_link_integrity_pct": round(100 * valid_refs / len(evidence_refs), 1) if evidence_refs else 100.0,
                        "persisted_execution_units": exec_count,
                        "persisted_evidence_units": evidence_count,
                        "persisted_trace": persisted,
                        "serialized_trace_bytes": len(trace.model_dump_json().encode("utf-8")),
                        "outcome_signature": trace_signature(trace),
                    }
                )

    csv_path = out_dir / "raw_runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, args.repeats)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    counts_db = SessionLocal()
    try:
        dataset_counts = {
            "inventory_items": counts_db.query(DBInventoryItem).count(),
            "supplier_profiles": counts_db.query(DBSupplierProfile).count(),
            "logistics_routes": counts_db.query(DBLogisticsRoute).count(),
            "evaluation_scenarios": len(EVALUATION_SCENARIOS),
            "random_seed": None,
            "data_generation": "fixed records in src/db/session.py; no random generator",
        }
    finally:
        counts_db.close()

    metadata = {
        "run_date_local": datetime.now().astimezone().date().isoformat(),
        "run_date_utc": datetime.now(timezone.utc).date().isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": package_versions(),
        "repeats_per_scenario_topology": args.repeats,
        "total_runs": len(rows),
        "dataset": dataset_counts,
        "llm": "not used; all agents and token usage are deterministic/synthetic",
        "model_api_settings": "No temperature, max-token, or provider endpoint is used by the execution path.",
        "token_and_cost_note": summary["method_note"],
        "outputs": ["results/raw_runs.csv", "results/summary.json", "results/metadata.json"],
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "summary": summary["aggregate_by_topology"], "metadata": metadata}, indent=2))


if __name__ == "__main__":
    main()
