from __future__ import annotations

import json

from operator_ui import config, jobs
from operator_ui.events import ProgressLogTail, project_progress
from operator_ui import worker


def _isolated_jobs(monkeypatch, tmp_path):
    state = tmp_path / "operator-state"
    monkeypatch.setattr(config, "STATE", state)
    monkeypatch.setattr(config, "JOBS_DIR", state / "jobs")
    monkeypatch.setattr(jobs, "STATE", state)
    monkeypatch.setattr(jobs, "JOBS_DIR", state / "jobs")
    monkeypatch.setattr(jobs, "DB_PATH", state / "operator.sqlite3")
    monkeypatch.setenv("KUBELLM_LAB_CONFIG", str(tmp_path / "lane-selector.json"))


def test_job_events_have_stable_order_and_last_event_replay(monkeypatch, tmp_path):
    _isolated_jobs(monkeypatch, tmp_path)
    job = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
    first = jobs.add_event(job["id"], {
        "t": 1.25, "attempt": 0, "phase": "setup", "source": "runner",
        "level": "info", "text": "Attempt started.",
    })
    second = jobs.add_event(job["id"], {
        "t": 2.5, "attempt": 0, "phase": "debug", "source": "debug",
        "level": "command", "text": "$ kubectl get pods",
    })

    assert first and second
    assert first["id"] == 1 and second["id"] == 2
    assert jobs.events_after(job["id"], 0) == [first, second]
    assert jobs.events_after(job["id"], 1) == [second]
    assert not jobs.job_is_terminal(job["id"])

    safe = jobs.add_event(job["id"], {
        "t": 3, "attempt": 0, "phase": "debug", "source": "debug",
        "level": "output", "text": "Authorization: Bearer abcdefghijklmnop",
        "prompt": "private prompt",
    })
    assert safe == {
        "id": 3, "t": 3.0, "attempt": 0, "phase": "debug", "source": "debug",
        "level": "output", "text": "Authorization: Bearer <redacted>",
    }
    try:
        jobs.add_event(job["id"], {**safe, "phase": ["invalid"]})
    except ValueError:
        pass
    else:
        raise AssertionError("invalid event fields must be rejected")

    jobs.update_job(job["id"], status="completed", finished_at=jobs.now())
    assert jobs.job_is_terminal(job["id"])
    assert jobs.add_event("0" * 32, {
        "t": 0, "attempt": 0, "phase": "setup", "source": "runner",
        "level": "info", "text": "not stored",
    }) is None


def test_progress_projection_is_allowlisted_bounded_and_redacted():
    command = project_progress({
        "event": "tool_start",
        "phase": "debug",
        "pid": 1234,
        "cwd": "/private/path",
        "command": "kubectl get pods --token actual-token-value",
        "prompt": "private prompt that must never be serialized",
    }, attempt=2, elapsed_s=3.14159)
    output = project_progress({
        "event": "tool_end",
        "phase": "verification",
        "exit_code": 0,
        "stdout_preview": "OPENAI_API_KEY=sk-very-secret-token-value and status ok",
        "arbitrary": {"private": "value"},
    }, attempt=2, elapsed_s=4)

    assert command == {
        "t": 3.142,
        "attempt": 2,
        "phase": "debug",
        "source": "kubectl",
        "level": "command",
        "text": "$ kubectl get pods --token <redacted>",
    }
    assert output is not None
    assert output["phase"] == "verify" and output["source"] == "verifier"
    assert output["text"] == "Command completed · exit 0"
    assert "status ok" not in output["text"]
    assert "sk-very-secret-token-value" not in json.dumps([command, output])
    assert "private prompt" not in json.dumps([command, output])
    assert "private/path" not in json.dumps([command, output])
    assert project_progress({"event": "prompt_captured", "prompt": "never"}, attempt=0, elapsed_s=0) is None


def test_ground_truth_and_teardown_keep_distinct_status_signals():
    failed_truth = project_progress({
        "event": "ground_truth_checkpoint_end", "stage": "after_verification",
        "passed": False, "summary": "deployment check failed",
    }, attempt=0, elapsed_s=42)
    completed = project_progress({
        "event": "test_end", "status": "FAIL", "success": False,
        "verified": False, "teardown_status": "passed", "duration_s": 44,
    }, attempt=0, elapsed_s=45)

    assert failed_truth and failed_truth["phase"] == "truth" and failed_truth["level"] == "fail"
    assert completed and completed["phase"] == "teardown" and completed["level"] == "info"
    assert "Teardown completed" in completed["text"]
    assert "Ground Truth" not in completed["text"]


def test_progress_tail_waits_for_complete_lines_and_does_not_repeat(tmp_path):
    path = tmp_path / "progress.log"
    tail = ProgressLogTail(path)
    first = {"event": "phase_start", "phase": "debug"}
    second = {"event": "phase_end", "phase": "debug", "status": "ok"}
    path.write_bytes((json.dumps(first) + "\n{" + '"event":"phase_end"').encode())

    assert tail.read_new() == [first]
    assert tail.read_new() == []

    with path.open("ab") as stream:
        stream.write(b',"phase":"debug","status":"ok"}\n')
    assert tail.read_new() == [second]
    assert tail.read_new() == []


def test_progress_tail_discards_oversized_records_until_the_next_line(tmp_path):
    path = tmp_path / "progress.log"
    tail = ProgressLogTail(path)
    valid = {"event": "phase_start", "phase": "setup"}
    path.write_bytes(b"{" + b"x" * (256 * 1024) + b"\n" + (json.dumps(valid) + "\n").encode())

    assert tail.read_new() == [valid]


def test_worker_persists_progress_events_once(monkeypatch, tmp_path):
    _isolated_jobs(monkeypatch, tmp_path)
    job = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
    progress = tmp_path / "attempt" / "progress.log"
    progress.parent.mkdir()
    progress.write_text(
        json.dumps({"event": "phase_start", "phase": "debug"}) + "\n"
        + json.dumps({"event": "tool_start", "phase": "debug", "command": "kubectl get pods"}) + "\n",
        encoding="utf-8",
    )

    class Process:
        calls = 0

        def poll(self):
            self.calls += 1
            return None if self.calls == 1 else 0

    monkeypatch.setattr(worker.time, "sleep", lambda _seconds: None)
    result = worker._wait_for_runner(Process(), progress, job["id"], 0, worker.time.monotonic())
    records = jobs.events_after(job["id"])

    assert result == 0
    assert len(records) == 2
    assert [event["id"] for event in records] == [1, 2]
    assert [event["level"] for event in records] == ["info", "command"]
