from src.eval.scenarios import EVALUATION_SCENARIOS, EvaluationScenario

__all__ = [
    "EVALUATION_SCENARIOS",
    "EvaluationScenario",
    "ThreeWayBenchmarkHarness",
    "BenchmarkResult",
]


def __getattr__(name):
    # Keep lightweight scenario imports independent of optional report exports
    # such as pandas, which is only needed when the legacy DataFrame harness runs.
    if name in {"ThreeWayBenchmarkHarness", "BenchmarkResult"}:
        from src.eval.benchmark_harness import BenchmarkResult, ThreeWayBenchmarkHarness

        return {
            "ThreeWayBenchmarkHarness": ThreeWayBenchmarkHarness,
            "BenchmarkResult": BenchmarkResult,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
