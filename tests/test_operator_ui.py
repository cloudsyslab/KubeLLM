from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from operator_ui import app, auth, config, jobs, publishing
from operator_ui import results, worker
from operator_ui.config import private_lab_fingerprint, validate_campaign
from operator_ui.results import history_summary
from operator_ui.safe import safe_readiness


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _isolated_paths(monkeypatch, root: Path) -> None:
    state = root / "operator-state"
    job_store = state / "jobs"
    monkeypatch.setattr(config, "STATE", state)
    monkeypatch.setattr(config, "JOBS_DIR", job_store)
    monkeypatch.setattr(jobs, "STATE", state)
    monkeypatch.setattr(jobs, "JOBS_DIR", job_store)
    monkeypatch.setattr(jobs, "DB_PATH", state / "operator.sqlite3")
    monkeypatch.setattr(auth, "AUTH_PATH", state / "auth.json")
    web_dist = root / "web" / "dist"
    web_dist.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(app, "WEB_DIST", web_dist)
    monkeypatch.setenv("KUBELLM_LAB_CONFIG", str(root / "private-lane-selector.json"))


def test_lane_must_be_selected_explicitly(monkeypatch):
    monkeypatch.delenv("KUBELLM_LAB_CONFIG", raising=False)
    try:
        config.private_lab_config()
    except RuntimeError as exc:
        assert "KUBELLM_LAB_CONFIG" in str(exc)
    else:
        raise AssertionError("an unset lane selector must not fall back to a default")


def test_operator_requires_login_for_api_and_checks_write_origin(monkeypatch, tmp_path):
    _isolated_paths(monkeypatch, tmp_path)
    password = "an operator password with enough length"
    auth.create_auth(password)
    (app.WEB_DIST / "index.html").write_text("<!doctype html><main>operator shell</main>", encoding="utf-8")
    monkeypatch.setattr(app, "all_runs", lambda: [])

    with TestClient(app.app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "operator shell" in page.text
        assert client.get("/models/gpt-6-luna").text == page.text
        assert client.get("/api/session").json() == {
            "authenticated": False, "configured": True, "username": None,
        }
        assert client.get("/api/overview").status_code == 401
        policy = page.headers["content-security-policy"]
        assert "script-src 'self'" in policy
        assert "style-src 'self' 'unsafe-inline'" in policy
        assert client.post("/api/unknown").status_code == 403
        origin = {"origin": "http://testserver"}
        assert client.post("/api/login", json={"password": "wrong password"}, headers=origin).status_code == 401
        login = client.post("/api/login", json={"password": password}, headers=origin)
        assert login.status_code == 200
        assert "httponly" in login.headers["set-cookie"].lower()
        assert "samesite=strict" in login.headers["set-cookie"].lower()
        assert client.get("/api/overview").status_code == 200
        assert client.post("/api/unknown", headers=origin).status_code == 405
        assert client.post("/api/logout", headers=origin).status_code == 200
        assert client.get("/api/overview").status_code == 401
        assert "set-cookie" not in page.headers


def test_job_event_stream_replays_after_last_event_id(monkeypatch, tmp_path):
    _isolated_paths(monkeypatch, tmp_path)
    password = "another operator password"
    auth.create_auth(password)
    job = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
    jobs.add_event(job["id"], {
        "t": 1.0, "attempt": 0, "phase": "setup", "source": "runner",
        "level": "info", "text": "Attempt started.",
    })
    jobs.update_job(job["id"], status="completed", finished_at=jobs.now())

    with TestClient(app.app) as client:
        assert client.post(
            "/api/login", json={"password": password}, headers={"origin": "http://testserver"},
        ).status_code == 200
        response = client.get(f"/api/jobs/{job['id']}/events")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "id: 1\ndata:" in response.text
        replay = client.get(f"/api/jobs/{job['id']}/events", headers={"last-event-id": "1"})
        assert replay.status_code == 200
        assert replay.text == ""


def test_terminal_job_event_stream_replays_all_pages(monkeypatch, tmp_path):
    _isolated_paths(monkeypatch, tmp_path)
    password = "long enough operator password"
    auth.create_auth(password)
    job = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
    for index in range(510):
        jobs.add_event(job["id"], {
            "t": float(index), "attempt": 0, "phase": "debug", "source": "runner",
            "level": "info", "text": f"Event {index}.",
        })
    jobs.update_job(job["id"], status="completed", finished_at=jobs.now())

    with TestClient(app.app) as client:
        assert client.post(
            "/api/login", json={"password": password}, headers={"origin": "http://testserver"},
        ).status_code == 200
        response = client.get(f"/api/jobs/{job['id']}/events")

    ids = [int(line.removeprefix("id: ")) for line in response.text.splitlines() if line.startswith("id: ")]
    assert ids == list(range(1, 511))


def test_campaign_inputs_are_bounded_and_history_keeps_per_run_rates():
    valid = validate_campaign(
        {
            "cases": ["wrong_port"],
            "techniques": ["allStepsAtOnce"],
            "debug_models": ["model-a", "model-b"],
            "repetitions": 2,
        },
        {"wrong_port"},
    )
    assert valid["planned_count"] == 4
    assert valid["techniques"] == ["allStepsAtOnce"]

    for payload in (
        {"cases": ["unknown"], "techniques": ["singleAgent"], "repetitions": 1},
        {"cases": ["wrong_port"], "techniques": ["private-mode"], "repetitions": 1},
        {"cases": ["wrong_port"], "techniques": ["singleAgent"], "repetitions": 501},
    ):
        try:
            validate_campaign(payload, {"wrong_port"})
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid campaign input was accepted.")

    summary = history_summary([
        {"ground_truth_known": 10, "ground_truth_passed": 9, "total_cost": 100.0, "duration_s": 20, "status": "recorded"},
        {"ground_truth_known": 10, "ground_truth_passed": 1, "total_cost": 0.5, "duration_s": 10, "status": "recorded"},
    ])
    assert summary["ground_truth_known"] == 20
    assert summary["ground_truth_passed"] == 10
    assert "ground_truth_rate" not in summary
    assert "recorded_cost" not in summary
    assert summary["cost_run_count"] == 2


def test_readiness_projection_drops_endpoint_and_private_details():
    projected = safe_readiness({
        "status": "BLOCKED",
        "generated_at": "2026-10-30T00:00:00+00:00",
        "checks": [{
            "name": "db_connectivity", "status": "fail", "blocking": True,
            "message": "postgres://private-user:private-pass@127.0.0.1/private-db",
        }],
        "effective": {"database_url": "postgres://private-user:private-pass@127.0.0.1/private-db"},
    })
    serialized = json.dumps(projected)
    assert projected["checks"][0]["label"] == "Database connection"
    assert projected["checks"][0]["detail"] == "<endpoint>"
    assert "private-pass" not in serialized
    assert "127.0.0.1" not in serialized


def test_readiness_projection_includes_redacted_check_and_repair_messages():
    projected = safe_readiness({
        "status": "BLOCKED",
        "checks": [{
            "name": "rag_api", "status": "fail", "blocking": True,
            "message": "Could not connect to http://10.2.3.4:8000/healthz?token=private-token",
        }],
        "repairs": [{
            "name": "rag_api", "status": "fail",
            "message": "API_KEY=private-key could not be rotated",
        }],
    })
    serialized = json.dumps(projected)
    assert projected["checks"][0]["detail"].startswith("Could not connect to <endpoint>")
    assert projected["repairs"][0]["message"] == "API_KEY=<redacted> could not be rotated"
    assert "10.2.3.4" not in serialized
    assert "private-token" not in serialized
    assert "private-key" not in serialized


def test_readiness_fingerprint_tracks_only_the_private_lane_file_version(monkeypatch, tmp_path):
    selector = tmp_path / "private-lane.json"
    selector.write_text('{"database_url":"postgres://private-pass@localhost/db"}\n', encoding="utf-8")
    monkeypatch.setenv("KUBELLM_LAB_CONFIG", str(selector))
    before = private_lab_fingerprint()
    selector.write_text('{"database_url":"postgres://rotated-private-pass@localhost/db"}\n', encoding="utf-8")
    after = private_lab_fingerprint()

    assert before != after
    assert "private-pass" not in before and "rotated-private-pass" not in after


def test_worker_loss_marks_campaign_interrupted_without_dropping_attempts(monkeypatch, tmp_path):
    _isolated_paths(monkeypatch, tmp_path)
    jobs.initialize()
    job = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
    jobs.update_job(job["id"], status="running", worker_pid=999_999)
    jobs.add_attempt(job["id"], {
        "sequence": 1, "case": "wrong_port", "status": "PASS", "ground_truth_passed": True,
    })

    jobs.reconcile_jobs()

    result = jobs.get_job(job["id"])
    assert result["status"] == "interrupted"
    assert result["attempts"][0]["ground_truth_passed"] is True

    check = jobs.create_job("readiness", {})
    assert jobs.request_stop(check["id"]) is None
    assert jobs.get_job(check["id"])["status"] == "queued"


def test_lane_lock_holds_while_starting_or_while_an_orphaned_runner_lives(monkeypatch, tmp_path):
    _isolated_paths(monkeypatch, tmp_path)
    jobs.initialize()

    # Just created: the app has not recorded the worker's PID yet.
    starting = jobs.create_job("readiness", {})
    jobs.reconcile_jobs()
    assert jobs.get_job(starting["id"])["status"] == "queued"
    jobs.update_job(starting["id"], status="completed", finished_at=jobs.now())

    # The worker is gone, but a process in its group (the runner) still runs.
    orphan = subprocess.Popen(["sleep", "30"], start_new_session=True)
    try:
        job = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
        jobs.update_job(job["id"], status="running", worker_pid=orphan.pid)
        jobs.reconcile_jobs()
        assert jobs.get_job(job["id"])["status"] == "running"
        try:
            jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
        except RuntimeError:
            pass
        else:
            raise AssertionError("a second campaign must not start while the runner lives")
    finally:
        orphan.kill()
        orphan.wait()
    jobs.reconcile_jobs()
    assert jobs.get_job(job["id"])["status"] == "interrupted"

    # A worker that died but was never reaped (a zombie) does not hold the lane.
    dead = subprocess.Popen(["true"], start_new_session=True)
    os.waitid(os.P_PID, dead.pid, os.WEXITED | os.WNOWAIT)  # exited, not yet reaped
    lost = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
    jobs.update_job(lost["id"], status="running", worker_pid=dead.pid)
    jobs.reconcile_jobs()
    assert jobs.get_job(lost["id"])["status"] == "interrupted"
    dead.wait()


def test_serial_campaign_stop_waits_for_active_runner_then_preserves_unknown_outcome(monkeypatch, tmp_path):
    _isolated_paths(monkeypatch, tmp_path)
    jobs.initialize()
    job = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=3)
    monkeypatch.setattr(worker, "_readiness_fresh", lambda: True)
    monkeypatch.setattr(worker, "private_lab_config", lambda: tmp_path / "private-lane-selector.json")
    monkeypatch.setattr(worker, "_start_health_sampler", lambda *_args: None)
    monkeypatch.setattr(worker, "_stop_health_sampler", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(worker, "_report_attempt", lambda *args: None)
    monkeypatch.setattr(worker, "safe_campaign_attempts", lambda paths: [])
    observed_commands = []

    class FinishedRunner:
        returncode = 0

        def __init__(self, command, **kwargs):
            observed_commands.append(command)

        def wait(self):
            jobs.request_stop(job["id"])
            return self.returncode

    monkeypatch.setattr(worker.subprocess, "Popen", FinishedRunner)
    config_value = {
        "cases": ["wrong_port"], "debug_models": ["debug-test-model"],
        "techniques": ["allStepsAtOnce"], "repetitions": 3,
        "api_model": None, "verification_model": None,
    }

    worker._run_campaign(job["id"], config_value, jobs.JOBS_DIR / job["id"])

    result = jobs.get_job(job["id"])
    assert result["status"] == "stopped"
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["outcome"] == "unavailable"
    assert result["attempts"][0]["ground_truth_passed"] is None
    assert len(observed_commands) == 1
    assert observed_commands[0][observed_commands[0].index("--lab-config") + 1] == str(tmp_path / "private-lane-selector.json")
    assert "--no-teardown" not in observed_commands[0]
    manifest = json.loads((jobs.JOBS_DIR / job["id"] / "campaign.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "stopped"
    assert manifest["attempts_completed"] == 1


def test_public_jobs_expose_campaign_selectors_but_never_publish_tokens(monkeypatch, tmp_path):
    _isolated_paths(monkeypatch, tmp_path)
    campaign = jobs.create_job("campaign", {
        "cases": ["wrong_port"], "techniques": ["allStepsAtOnce"],
        "debug_models": ["model-a"], "repetitions": 2,
        "api_model": "api-model", "verification_model": None,
    }, total=2)
    assert campaign["campaign"] == {
        "cases": ["wrong_port"], "techniques": ["allStepsAtOnce"],
        "debug_models": ["model-a"], "repetitions": 2,
        "api_model": "api-model", "verification_model": None,
    }

    # The operator needs the token to run publication, but a public job
    # response must never serialize the private worker input.
    jobs.update_job(campaign["id"], status="completed", finished_at=jobs.now())
    private_token = "a" * 32
    publication = jobs.create_job("publish", {"campaign_job_id": campaign["id"], "preview_token": private_token})
    public = jobs.get_job(publication["id"])
    assert "campaign" not in public
    assert private_token not in json.dumps(public)


def test_campaign_health_history_is_bound_to_active_campaign_and_lane(monkeypatch, tmp_path):
    _isolated_paths(monkeypatch, tmp_path)
    campaign = jobs.create_job("campaign", {"cases": ["wrong_port"]}, total=1)
    sample = {"sampled_at": jobs.now(), "telemetry": {"cpu": {"total_pct": 12.5}}, "topology": {"status": "partial"}}
    assert jobs.record_campaign_health(campaign["id"], "lane-a", sample)
    history = jobs.campaign_health_history(campaign["id"], "lane-a")
    assert history["reason"] is None
    assert history["samples"] == [sample]
    assert jobs.campaign_health_history(campaign["id"], "lane-b")["reason"] == "lane_changed"

    jobs.update_job(campaign["id"], status="completed", finished_at=jobs.now())
    assert not jobs.record_campaign_health(campaign["id"], "lane-a", sample)


def test_history_lists_campaign_attempts_under_the_ref_the_worker_records(monkeypatch, tmp_path):
    jobs_root = tmp_path / "jobs"
    attempt = jobs_root / ("c" * 32) / "attempts" / "0001-wrong_port-allStepsAtOnce-default"
    (attempt / "wrong_port").mkdir(parents=True)
    (attempt / "run_config.json").write_text(json.dumps({
        "run_id": "2026-10-30T10-30-00", "test_names": ["wrong_port"], "technique": "allStepsAtOnce",
    }), encoding="utf-8")
    (attempt / "wrong_port" / "summary.json").write_text(json.dumps({
        "test_name": "wrong_port", "technique": "allStepsAtOnce", "status": "PASS",
        "ground_truth_passed": True, "ground_truth_configured": True,
    }), encoding="utf-8")
    # A publish preview copy in the same job folder is not a run.
    preview = jobs_root / ("c" * 32) / "publish-preview" / "attempt-0001"
    preview.mkdir(parents=True)
    (preview / "run_config.archived.json").write_text(json.dumps({"run_id": "2026-10-30T10-30-00"}), encoding="utf-8")
    monkeypatch.setattr(results, "RUNS_DIR", jobs_root)

    local = [run for run in results._all_runs() if run["source"] == "local"]
    recorded = results.safe_campaign_attempts([attempt])
    assert len(local) == 1 and len(recorded) == 1
    assert local[0]["ref"] == recorded[0]["ref"]


def test_publication_targets_a_new_results_branch_from_remote_default(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
    _git(repo, "config", "user.name", "Fixture Operator")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "Fixture baseline")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "--set-upstream", "origin", "main")
    writer = tmp_path / "remote-writer"
    subprocess.run(["git", "clone", str(remote), str(writer)], check=True, capture_output=True)
    _git(writer, "config", "user.name", "Remote Writer")
    _git(writer, "config", "user.email", "writer@example.invalid")
    (writer / "remote-only.txt").write_text("advanced remote base\n", encoding="utf-8")
    _git(writer, "add", "remote-only.txt")
    _git(writer, "commit", "-m", "Advance remote default branch")
    _git(writer, "push", "origin", "main")
    monkeypatch.setattr(publishing, "REPO", repo)
    monkeypatch.setattr(publishing, "_remote_repository", lambda _remote: publishing.CANONICAL_REPOSITORY)

    target = publishing._publication_target("a" * 32, "f" * 32)
    assert target["remote"] == "origin"
    assert target["repository"] == "github.com/cloudsyslab/KubeLLM"
    assert target["base_branch"] == "main"
    assert target["base_sha"] == _git(writer, "rev-parse", "HEAD")
    assert target["base_sha"] != _git(repo, "rev-parse", "HEAD")
    _git(repo, "cat-file", "-e", f"{target['base_sha']}^{{commit}}")
    assert target["branch"] == "codex/operator-results/aaaaaaaa-ffffffffffffffff"


def test_publication_remote_must_be_the_canonical_repository(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "remote", "add", "origin", "https://user:private-token@github.com/cloudsyslab/KubeLLM.git")
    monkeypatch.setattr(publishing, "REPO", repo)

    assert publishing._remote_repository("origin") == "github.com/cloudsyslab/KubeLLM"
    assert "private-token" not in publishing._remote_repository("origin")
    _git(repo, "remote", "add", "other", "https://github.com/someone-else/KubeLLM.git")
    try:
        publishing._remote_repository("other")
    except RuntimeError as exc:
        assert "someone-else" not in str(exc)
    else:
        raise AssertionError("results publication must reject non-canonical remotes")


def test_publish_preview_exports_allowlisted_files_and_pushes_only_reviewed_paths(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "data" / "exploratory").mkdir(parents=True)
    (repo / "scripts").mkdir()
    shutil.copy2(Path(__file__).parents[1] / "scripts" / "archive_exploratory_run.py", repo / "scripts" / "archive_exploratory_run.py")
    explorer_readme = (
        "# Exploratory run archive\n\nExisting packs remain separate.\n\n"
        "| Archive | Retained evidence | Limitation |\n|---|---|---|\n"
        "| [`prior/`](prior/) | old evidence | incomplete |\n\n"
        "New sanitized packs use `scripts/archive_exploratory_run.py` and keep raw evidence private.\n"
    )
    data_readme = "# Benchmark data catalog\n\nCanonical runs stay separate.\n"
    (repo / "data" / "exploratory" / "README.md").write_text(explorer_readme, encoding="utf-8")
    (repo / "data" / "README.md").write_text(data_readme, encoding="utf-8")
    (repo / "unrelated.txt").write_text("base\n", encoding="utf-8")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
    _git(repo, "config", "user.name", "Fixture Operator")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "add", "data", "unrelated.txt")
    _git(repo, "commit", "-m", "Fixture baseline")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "--set-upstream", "origin", "main")
    remote_main = _git(repo, "rev-parse", "origin/main")
    state = tmp_path / "private-state"
    campaign_id = "a" * 32
    publish_id = "b" * 32
    campaign_dir = state / "jobs" / campaign_id
    source = campaign_dir / "attempts" / "0001-wrong_port-allStepsAtOnce-default"
    (source / "wrong_port").mkdir(parents=True)
    (source / "run_config.json").write_text(json.dumps({
        "run_id": "2026-10-30T10-30-00", "test_names": ["wrong_port"],
        "technique": "allStepsAtOnce", "rag_api_url": "http://private-endpoint.invalid",
    }), encoding="utf-8")
    (source / "provenance.json").write_text(json.dumps({
        "run_id": "2026-10-30T10-30-00", "private_endpoint": "private-endpoint-marker",
        "git_dirty": False,
    }), encoding="utf-8")
    (source / "aggregate.json").write_text(json.dumps({
        "total_tests": 1, "passed": 1, "total_cost": 0.25, "total_tokens": 100,
        "private_text": "private-aggregate-marker",
    }), encoding="utf-8")
    (source / "wrong_port" / "summary.json").write_text(json.dumps({
        "test_name": "wrong_port", "technique": "allStepsAtOnce", "status": "PASS",
        "ground_truth_passed": True, "ground_truth_configured": True,
        "verified": True, "duration_s": 12,
        "metrics": {"api": {"cost": 0.25, "total_tokens": 100, "model": "private-model"}},
        "error_message": "private-summary-marker",
    }), encoding="utf-8")
    (source / "wrong_port" / "config_effective.json").write_text(json.dumps({
        "api-agent": {"model": "api-test-model"},
        "debug-agent": {"model": "debug-test-model"},
        "verification-agent": {"model": "verify-test-model"},
    }), encoding="utf-8")
    (source / "wrong_port" / "prompt.txt").write_text("private-prompt-marker", encoding="utf-8")

    public_campaign = {
        "id": campaign_id, "kind": "campaign", "status": "completed", "total": 1,
        "attempts": [{
            "sequence": 1, "case": "wrong_port", "technique": "allStepsAtOnce",
            "status": "PASS", "outcome": "recorded", "ground_truth_passed": True,
        }],
        "created_at": "2026-10-30T10:00:00+00:00", "started_at": "2026-10-30T10:00:00+00:00",
    }
    internal_campaign = {
        "id": campaign_id, "kind": "campaign", "status": "completed",
        "run_root": str(campaign_dir), "config": {},
    }
    publish_worker = {"id": publish_id, "kind": "publish"}
    monkeypatch.setattr(publishing, "REPO", repo)
    monkeypatch.setattr(publishing, "JOBS_DIR", state / "jobs")
    monkeypatch.setattr(worker, "JOBS_DIR", state / "jobs")
    monkeypatch.setattr(publishing, "_remote_repository", lambda _remote: publishing.CANONICAL_REPOSITORY)
    monkeypatch.setattr(publishing.jobs, "get_job", lambda job_id: public_campaign if job_id == campaign_id else None)
    monkeypatch.setattr(publishing.jobs, "worker_config", lambda job_id: internal_campaign if job_id == campaign_id else publish_worker if job_id == publish_id else None)
    updates = []
    monkeypatch.setattr(publishing.jobs, "update_job", lambda job_id, **fields: updates.append((job_id, fields)))

    worker._report_attempt(source, campaign_id, 1)
    local_report = source / "benchmark_summary.md"
    assert local_report.is_file()
    assert "private-prompt-marker" not in local_report.read_text(encoding="utf-8")

    preview = publishing.create_publish_preview(campaign_id)
    assert preview["campaign_status"] == "COMPLETED"
    assert preview["models"] == ["api-test-model", "debug-test-model", "verify-test-model"]
    assert any(item["path"].endswith("run_config.archived.json") for item in preview["files"])
    assert all(item["path"].startswith("data/") for item in preview["files"])
    assert preview["target"]["base_branch"] == "main"
    assert preview["target"]["branch"].startswith("codex/operator-results/aaaaaaaa-")
    reviewed_readme = next(item["path"] for item in preview["files"] if item["path"].endswith("/README.md") and "operator-campaign-" in item["path"])
    assert publishing.read_preview_file(campaign_id, reviewed_readme).startswith("# operator-campaign-")
    try:
        publishing.read_preview_file(campaign_id, "data/../../private.txt")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("preview file reads must be limited to reviewed manifest paths")
    assert publishing.validate_publish_token(campaign_id, preview["preview_token"])

    (repo / "unrelated.txt").write_text("staged private change\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")
    publishing.publish_campaign(publish_id, campaign_id, preview["preview_token"])

    target_branch = preview["target"]["branch"]
    commit = _git(repo, "--git-dir", str(remote), "rev-parse", f"refs/heads/{target_branch}")
    latest_paths = set(_git(repo, "--git-dir", str(remote), "diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
    reviewed_paths = {item["path"] for item in preview["files"]}
    assert latest_paths == reviewed_paths
    assert _git(repo, "rev-parse", "HEAD") == remote_main
    assert _git(repo, "--git-dir", str(remote), "rev-parse", "main") == remote_main
    assert _git(repo, "show", "HEAD:unrelated.txt") == "base"
    assert _git(repo, "diff", "--cached", "--", "unrelated.txt")
    pack_path = next(item["path"] for item in preview["files"] if item["path"].startswith("data/exploratory/operator-campaign-")).split("/", 3)[:3]
    pack_name = pack_path[2]
    published_pack = tmp_path / "published-pack"
    for path in latest_paths:
        prefix = f"data/exploratory/{pack_name}/"
        if path.startswith(prefix):
            destination = published_pack / Path(path).relative_to(prefix)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(_git(repo, "--git-dir", str(remote), "show", f"{commit}:{path}"), encoding="utf-8")
    serialized_pack = "\n".join(path.read_text(encoding="utf-8") for path in published_pack.rglob("*") if path.is_file())
    for private in ("private-prompt-marker", "private-summary-marker", "private-aggregate-marker", "private-endpoint-marker", "private-model"):
        assert private not in serialized_pack
    archived_run = published_pack / "allStepsAtOnce" / "attempt-0001-wrong_port"
    record = results._project_run(
        archived_run, archived_run / "run_config.archived.json", "exploratory", "fixture-pack/attempt-0001",
    )
    assert record is not None
    assert record["case_rows"][0]["case"] == "wrong_port"
    assert record["case_rows"][0]["ground_truth_passed"] is True
    assert record["case_rows"][0]["ground_truth_configured"] is True
    assert record["ground_truth_rate"] == 1.0
    assert updates[-1][1]["status"] == "completed"
    assert updates[-1][1]["result_json"]["branch"] == target_branch

