import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("archive_run", ROOT / "scripts/archive_exploratory_run.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
spec = importlib.util.spec_from_file_location("analyze", ROOT / "data_analysis/analyze.py")
analyze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze)


def fixture(tmp_path):
    source = tmp_path / "raw"
    case = source / "wrong_port"
    case.mkdir(parents=True)
    values = {
        "run_config.json": {"run_id": "2026-09-28T11-48-23", "technique": "stepByStep",
                            "test_names": ["wrong_port"], "rag_api_url": "PRIVATE"},
        "provenance.json": {"git_commit": "a" * 40, "git_dirty": True, "environment": "PRIVATE"},
        "wrong_port/summary.json": {"status": "TIMEOUT", "ground_truth_passed": False,
                                    "verified": None, "error_message": "PRIVATE",
                                    "metrics": {"api": {"cost": 0.12, "secret": "PRIVATE"}}},
        "wrong_port/config_effective.json": {"api-agent": {"model": "gpt-5-mini", "key": "PRIVATE"}},
        "wrong_port/knowledge_execution.json": {
            "execution": {"status": "completed", "completed_action_count": 1,
                          "actions": [{"status": "completed", "command": "PRIVATE", "stdout": "PRIVATE"}]}},
    }
    for path, value in values.items():
        (source / path).write_text(json.dumps(value))
    (case / "verification_report.txt").write_text("PRIVATE")
    return source


def test_export_preserves_outcomes_without_secrets_or_default_discovery(tmp_path):
    source = fixture(tmp_path)
    destination = tmp_path / "exports" / "run"
    archive.archive_run(source, destination, {"gpt-5-mini"})
    serialized = "".join(p.read_text() for p in destination.rglob("*.json"))
    assert "PRIVATE" not in serialized
    summary = json.loads((destination / "wrong_port/summary.json").read_text())
    assert summary["status"] == "TIMEOUT"  # Historical labels are not repaired.
    assert summary["ground_truth_passed"] is False
    assert "verified" not in summary  # Unknown is never converted into success/failure.
    assert summary["metrics"]["api"]["cost"] == 0.12
    assert json.loads((destination / "provenance.archived.json").read_text())["git_dirty"] is True
    assert list(analyze.iter_run_dirs(destination.parent)) == []
    with pytest.raises(FileExistsError):
        archive.archive_run(source, destination, {"gpt-5-mini"})


def test_unreviewed_model_and_symlink_fail_before_writing(tmp_path):
    source = fixture(tmp_path)
    destination = tmp_path / "export"
    with pytest.raises(ValueError, match="Unreviewed model"):
        archive.archive_run(source, destination, set())
    assert not destination.exists()
    (source / "wrong_port/summary.json").unlink()
    (source / "wrong_port/summary.json").symlink_to(source / "run_config.json")
    with pytest.raises(ValueError, match="linked"):
        archive.archive_run(source, destination, {"gpt-5-mini"})
    assert not destination.exists()


def test_all_exploratory_evidence_stays_excluded():
    assert list(analyze.iter_run_dirs(ROOT / "data/exploratory")) == []
