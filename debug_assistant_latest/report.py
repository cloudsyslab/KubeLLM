"""
Report generation module for KubeLLM test runner.

Provides functions to generate per-test summary.json files and
aggregate reports across test runs.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class AgentMetrics:
    """Metrics for a single agent execution."""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    duration_s: float = 0.0


AGENT_METRIC_FIELDS = tuple(AgentMetrics.__dataclass_fields__.keys())


def normalize_agent_metrics(agent_metrics: Any) -> AgentMetrics:
    """Coerce raw metrics payloads into the report's supported metric shape."""
    if isinstance(agent_metrics, AgentMetrics):
        return agent_metrics

    if isinstance(agent_metrics, dict):
        filtered = {
            field_name: agent_metrics[field_name]
            for field_name in AGENT_METRIC_FIELDS
            if field_name in agent_metrics
        }
        return AgentMetrics(**filtered)

    return AgentMetrics()


def normalize_metrics_map(metrics: Optional[Dict[str, Any]]) -> Dict[str, AgentMetrics]:
    """Normalize a metrics mapping so reporting code can treat all entries uniformly."""
    return {
        agent_name: normalize_agent_metrics(agent_metrics)
        for agent_name, agent_metrics in (metrics or {}).items()
    }


@dataclass
class TestSummary:
    """Summary of a single test execution."""
    test_name: str
    technique: str
    status: str  # PASS, FAIL, ERROR, TIMEOUT
    verified: Optional[bool]  # True/False if verification ran, None if no verification
    debug_self_report: Optional[bool] = None
    started_at: str = ""
    finished_at: str = ""
    duration_s: float = 0.0
    error_message: Optional[str] = None
    metrics: Dict[str, AgentMetrics] = field(default_factory=dict)
    config_overrides_applied: Dict[str, Any] = field(default_factory=dict)
    ground_truth_passed: Optional[bool] = None  # True/False if GT ran, None if no GT config

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "test_name": self.test_name,
            "technique": self.technique,
            "status": self.status,
            "verified": self.verified,
            "debug_self_report": self.debug_self_report,
            "ground_truth_passed": self.ground_truth_passed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": round(self.duration_s, 3),
            "error_message": self.error_message,
            "metrics": {},
            "config_overrides_applied": self.config_overrides_applied,
        }
        for agent_name, agent_metrics in normalize_metrics_map(self.metrics).items():
            result["metrics"][agent_name] = asdict(agent_metrics)
        return result


def save_test_summary(summary: TestSummary, output_dir: Path) -> Path:
    """
    Save a test summary to summary.json in the test output directory.

    Args:
        summary: TestSummary object
        output_dir: Directory to save summary.json (usually .local/test_runs/<ts>/<test_name>/)

    Returns:
        Path to saved summary.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"

    with open(summary_path, "w") as f:
        json.dump(summary.to_dict(), f, indent=2)

    return summary_path


def load_test_summary(summary_path: Path) -> TestSummary:
    """
    Load a test summary from a summary.json file.

    Args:
        summary_path: Path to summary.json

    Returns:
        TestSummary object
    """
    with open(summary_path) as f:
        data = json.load(f)

    metrics = normalize_metrics_map(data.get("metrics", {}))

    return TestSummary(
        test_name=data["test_name"],
        technique=data["technique"],
        status=data["status"],
        verified=data["verified"],
        debug_self_report=data.get("debug_self_report"),
        started_at=data.get("started_at", ""),
        finished_at=data.get("finished_at", ""),
        duration_s=data.get("duration_s", 0.0),
        error_message=data.get("error_message"),
        metrics=metrics,
        config_overrides_applied=data.get("config_overrides_applied", {}),
        ground_truth_passed=data.get("ground_truth_passed"),
    )


@dataclass
class AggregateReport:
    """Aggregate report across a test run."""
    run_id: str
    generated_at: str
    run_config: Dict[str, Any]
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    verified: int = 0
    tests_with_verification: int = 0  # Tests that had verification agent run
    ground_truth_passed: int = 0  # Tests where ground truth checks passed
    tests_with_ground_truth: int = 0  # Tests that had ground truth configured
    pass_rate: float = 0.0
    verified_rate: float = 0.0  # verified / tests_with_verification
    ground_truth_rate: float = 0.0  # ground_truth_passed / tests_with_ground_truth
    total_duration_s: float = 0.0
    wall_clock_s: float = 0.0
    total_cost: float = 0.0
    total_debug_cost: float = 0.0
    total_verification_cost: float = 0.0
    total_tokens: int = 0
    tests: List[Dict] = field(default_factory=list)
    failed_tests: List[str] = field(default_factory=list)
    error_tests: List[str] = field(default_factory=list)
    ground_truth_failed_tests: List[str] = field(default_factory=list)


def generate_aggregate_report(
    summaries: List[TestSummary],
    run_config: Dict[str, Any],
    run_id: str,
    wall_clock_s: float = 0.0,
) -> AggregateReport:
    """
    Generate an aggregate report from individual test summaries.

    Args:
        summaries: List of TestSummary objects
        run_config: Configuration used for the run (CLI args, overrides)
        run_id: Unique identifier for the run (usually timestamp)
        wall_clock_s: Total wall-clock time for the run

    Returns:
        AggregateReport object
    """
    total = len(summaries)
    passed = sum(1 for s in summaries if s.status == "PASS")
    failed = sum(1 for s in summaries if s.status == "FAIL")
    errors = sum(1 for s in summaries if s.status in ("ERROR", "TIMEOUT"))
    # Only count verified=True; verified=None means no verification was run
    verified_count = sum(1 for s in summaries if s.verified is True)
    # Count tests that actually had verification (verified is not None)
    tests_with_verification = sum(1 for s in summaries if s.verified is not None)
    # Ground truth stats
    gt_passed_count = sum(1 for s in summaries if s.ground_truth_passed is True)
    tests_with_gt = sum(1 for s in summaries if s.ground_truth_passed is not None)
    gt_failed_tests = [s.test_name for s in summaries if s.ground_truth_passed is False]

    total_duration = sum(s.duration_s for s in summaries)

    total_cost = 0.0
    debug_cost = 0.0
    verification_cost = 0.0
    total_tokens = 0

    for s in summaries:
        for agent_name, m in normalize_metrics_map(s.metrics).items():
            total_cost += m.cost
            total_tokens += m.total_tokens
            if "debug" in agent_name:
                debug_cost += m.cost
            elif "verification" in agent_name:
                verification_cost += m.cost

    tests = [
        {
            "name": s.test_name,
            "status": s.status,
            "verified": s.verified,
            "ground_truth_passed": s.ground_truth_passed,
            "duration_s": round(s.duration_s, 2),
            "error": s.error_message,
        }
        for s in sorted(summaries, key=lambda x: x.test_name)
    ]

    failed_tests = [s.test_name for s in summaries if s.status == "FAIL"]
    error_tests = [s.test_name for s in summaries if s.status in ("ERROR", "TIMEOUT")]

    return AggregateReport(
        run_id=run_id,
        generated_at=datetime.now().isoformat(),
        run_config=run_config,
        total_tests=total,
        passed=passed,
        failed=failed,
        errors=errors,
        verified=verified_count,
        tests_with_verification=tests_with_verification,
        ground_truth_passed=gt_passed_count,
        tests_with_ground_truth=tests_with_gt,
        pass_rate=round(passed / total * 100, 1) if total > 0 else 0.0,
        verified_rate=round(verified_count / tests_with_verification * 100, 1) if tests_with_verification > 0 else 0.0,
        ground_truth_rate=round(gt_passed_count / tests_with_gt * 100, 1) if tests_with_gt > 0 else 0.0,
        total_duration_s=round(total_duration, 2),
        wall_clock_s=round(wall_clock_s, 2),
        total_cost=round(total_cost, 4),
        total_debug_cost=round(debug_cost, 4),
        total_verification_cost=round(verification_cost, 4),
        total_tokens=total_tokens,
        tests=tests,
        failed_tests=failed_tests,
        error_tests=error_tests,
        ground_truth_failed_tests=gt_failed_tests,
    )


def save_aggregate_report(report: AggregateReport, output_dir: Path) -> Path:
    """
    Save aggregate report to aggregate.json.

    Args:
        report: AggregateReport object
        output_dir: Run output directory

    Returns:
        Path to saved aggregate.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate_path = output_dir / "aggregate.json"

    with open(aggregate_path, "w") as f:
        json.dump(asdict(report), f, indent=2)

    return aggregate_path


def save_run_config(run_config: Dict[str, Any], output_dir: Path) -> Path:
    """
    Save run configuration for audit trail.

    Args:
        run_config: Dictionary of CLI arguments and settings
        output_dir: Run output directory

    Returns:
        Path to saved run_config.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "run_config.json"

    with open(config_path, "w") as f:
        json.dump(run_config, f, indent=2)

    return config_path


def print_console_summary(report: AggregateReport, output_dir: Path) -> None:
    """
    Print a human-readable summary to the console.

    Args:
        report: AggregateReport object
        output_dir: Run output directory
    """
    print("\n" + "=" * 80)
    print(f"TEST RUN COMPLETE: {report.run_id}")
    print("=" * 80)
    print()
    print(f"Tests: {report.total_tests} total | {report.passed} passed | {report.failed} failed | {report.errors} error")
    if report.tests_with_verification > 0:
        print(f"Verified (LLM): {report.verified}/{report.tests_with_verification} ({report.verified_rate}%)")
    else:
        print(f"Verified (LLM): N/A (no verification agent ran)")
    if report.tests_with_ground_truth > 0:
        print(f"Ground Truth: {report.ground_truth_passed}/{report.tests_with_ground_truth} ({report.ground_truth_rate}%)")
    print(f"Duration: {report.total_duration_s}s (wall: {report.wall_clock_s}s)")

    if report.total_cost > 0:
        print(f"Cost: ${report.total_cost:.4f} (debug: ${report.total_debug_cost:.4f}, verification: ${report.total_verification_cost:.4f})")

    if report.failed_tests:
        print()
        print("FAILED:")
        for name in report.failed_tests:
            print(f"  - {name}")

    if report.error_tests:
        print()
        print("ERRORS:")
        for name in report.error_tests:
            print(f"  - {name}")

    if report.ground_truth_failed_tests:
        print()
        print("GROUND TRUTH FAILED:")
        for name in report.ground_truth_failed_tests:
            print(f"  - {name}")

    print()
    print(f"Logs: {output_dir}/")
    print(f"Report: {output_dir}/aggregate.json")
    print()


def collect_summaries_from_run(run_dir: Path) -> List[TestSummary]:
    """
    Collect all test summaries from a run directory.

    Args:
        run_dir: Path to run directory (e.g., .local/test_runs/2026-01-24T15-30-00/)

    Returns:
        List of TestSummary objects
    """
    summaries = []
    for test_dir in run_dir.iterdir():
        if test_dir.is_dir():
            summary_path = test_dir / "summary.json"
            if summary_path.exists():
                summaries.append(load_test_summary(summary_path))
    return summaries


if __name__ == "__main__":
    # Quick test of the module
    summary = TestSummary(
        test_name="wrong_port",
        technique="allStepsAtOnce",
        status="PASS",
        verified=True,
        debug_self_report=True,
        started_at="2026-01-24T15:30:00.000Z",
        finished_at="2026-01-24T15:32:45.123Z",
        duration_s=165.123,
        metrics={
            "debug_agent": AgentMetrics(
                model="gpt-5-nano",
                input_tokens=12500,
                output_tokens=3200,
                total_tokens=15700,
                cost=0.0134,
                duration_s=45.2,
            )
        },
    )

    print("Test Summary:")
    print(json.dumps(summary.to_dict(), indent=2))
