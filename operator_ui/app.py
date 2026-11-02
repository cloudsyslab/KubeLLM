"""HTTP interface for the private KubeLLM operator UI."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import auth, jobs
from .config import JOB_ID_RE, JOBS_DIR, REPO, private_lab_config, private_lab_fingerprint, secure_state_dir, validate_campaign
from .results import all_runs, find_run, history_summary, inspect_detail, public_run


STATIC = Path(__file__).parent / "static"
COOKIE_NAME = "kubellm_operator"
OPERATOR_INSTANCE_ID = secrets.token_hex(16)
_LOGIN_FAILURES: dict[str, list[float]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    private_lab_config()  # refuse to start without an explicitly selected lane
    secure_state_dir()
    jobs.initialize()
    jobs.reconcile_jobs()
    yield


app = FastAPI(title="KubeLLM Operator", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _authenticated(request: Request) -> bool:
    return auth.verify_session(request.cookies.get(COOKIE_NAME, ""))


def _same_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    host = request.headers.get("host")
    if not origin or not host:
        return False
    return origin.rstrip("/") == f"{request.url.scheme}://{host}".rstrip("/")


def _require_auth(request: Request) -> None:
    if not _authenticated(request):
        raise HTTPException(status_code=401, detail="Sign in to continue.")


def _readiness_fresh() -> bool:
    if (
        jobs.app_value("readiness_status") != "READY"
        or jobs.app_value("readiness_lane_fingerprint") != private_lab_fingerprint()
        or jobs.app_value("readiness_server_id") != OPERATOR_INSTANCE_ID
    ):
        return False
    checked_at = jobs.app_value("readiness_at")
    if not checked_at:
        return False
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(checked_at)).total_seconds()
        return 0 <= age <= 20 * 60
    except (TypeError, ValueError):
        return False


def _new_worker(kind: str, config: dict, total: int = 0) -> dict:
    try:
        job = jobs.create_job(kind, config, total)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    worker_log = jobs.JOBS_DIR / job["id"] / "worker.log"
    fd = os.open(worker_log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    env = os.environ.copy()
    env["KUBELLM_LAB_CONFIG"] = str(private_lab_config())
    env["KUBELLM_OPERATOR_INSTANCE_ID"] = OPERATOR_INSTANCE_ID
    try:
        with os.fdopen(fd, "ab", buffering=0) as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "operator_ui.worker", job["id"]],
                cwd=REPO,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
        jobs.update_job(job["id"], worker_pid=process.pid)
    except OSError as exc:
        jobs.update_job(
            job["id"],
            status="failed",
            finished_at=jobs.now(),
            current_label="The background worker could not start.",
        )
        raise HTTPException(status_code=503, detail="Could not start the background worker.") from exc
    return jobs.get_job(job["id"])


@app.middleware("http")
async def operator_security(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not _same_origin(request):
        response = JSONResponse({"detail": "Request origin could not be verified."}, status_code=403)
    elif request.url.path.startswith("/api/") and request.url.path not in {"/api/login", "/api/session"} and not _authenticated(request):
        response = JSONResponse({"detail": "Sign in to continue."}, status_code=401)
    else:
        response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/session")
def session(request: Request):
    return {
        "authenticated": _authenticated(request),
        "configured": auth.auth_configured(),
        "username": "Operator" if _authenticated(request) else None,
    }


@app.post("/api/login")
async def login(request: Request):
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = [stamp for stamp in _LOGIN_FAILURES.get(client, []) if now - stamp < 900]
    _LOGIN_FAILURES[client] = attempts
    if len(attempts) >= 8:
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")
    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Enter your operator password.") from exc
    password = body.get("password") if isinstance(body, dict) else None
    if not auth.auth_configured():
        raise HTTPException(status_code=503, detail="Initialize the private operator login on the server first.")
    if not isinstance(password, str) or not auth.verify_password(password):
        attempts.append(now)
        _LOGIN_FAILURES[client] = attempts[-8:]
        raise HTTPException(status_code=401, detail="The password did not match.")
    _LOGIN_FAILURES.pop(client, None)
    session_id, expires = auth.make_session()
    token = auth.sign_session(session_id, expires)
    response = JSONResponse({"authenticated": True})
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=auth.SESSION_HOURS * 3600,
        path="/",
    )
    return response


@app.post("/api/logout")
def logout():
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict")
    return response


@app.get("/api/overview")
def overview(request: Request):
    _require_auth(request)
    runs = all_runs()
    recent = [public_run(item) for item in runs[:8]]
    readiness_at = jobs.app_value("readiness_at")
    readiness_status = jobs.app_value("readiness_status")
    readiness_matches = (
        jobs.app_value("readiness_lane_fingerprint") == private_lab_fingerprint()
        and jobs.app_value("readiness_server_id") == OPERATOR_INSTANCE_ID
    )
    readiness_fresh = _readiness_fresh()
    return {
        "headline": history_summary(runs),
        "sources": {
            "canonical": sum(item["source"] == "canonical" for item in runs),
            "exploratory": sum(item["source"] == "exploratory" for item in runs),
            "local": sum(item["source"] == "local" for item in runs),
        },
        "readiness": {
            "status": readiness_status if readiness_fresh or readiness_matches and readiness_status == "BLOCKED" else None,
            "checked_at": readiness_at,
        },
        "latest_runs": recent,
        "jobs": jobs.list_jobs(6),
    }


@app.get("/api/cases")
def cases(request: Request):
    _require_auth(request)
    sys.path.insert(0, str(REPO / "debug_assistant_latest"))
    try:
        from test_discovery import list_test_cases

        available = list_test_cases()
    except (OSError, ImportError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="The canonical runner case catalog is unavailable.") from exc
    return {"cases": [{"id": case, "label": case.replace("_", " ")} for case in available]}


@app.post("/api/readiness")
def readiness(request: Request):
    _require_auth(request)
    return _new_worker("readiness", {})


@app.post("/api/prepare")
def prepare(request: Request):
    _require_auth(request)
    return _new_worker("prepare", {})


@app.post("/api/campaign")
async def campaign(request: Request):
    _require_auth(request)
    try:
        payload = await request.json()
        sys.path.insert(0, str(REPO / "debug_assistant_latest"))
        from test_discovery import list_test_cases

        normalized = validate_campaign(payload, set(list_test_cases()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (OSError, ImportError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="The canonical runner case catalog is unavailable.") from exc
    if not _readiness_fresh():
        raise HTTPException(status_code=409, detail="Run fresh preflight and resolve blockers before launching a campaign.")
    return _new_worker("campaign", normalized, normalized["planned_count"])


@app.get("/api/jobs")
def get_jobs(request: Request):
    _require_auth(request)
    jobs.reconcile_jobs()
    return {"jobs": jobs.list_jobs()}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    _require_auth(request)
    if not JOB_ID_RE.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="Operator task not found.")
    record = jobs.get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Operator task not found.")
    jobs.reconcile_jobs()
    return jobs.get_job(job_id)


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str, request: Request):
    _require_auth(request)
    if not JOB_ID_RE.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="Operator task not found.")
    current = jobs.get_job(job_id)
    if not current:
        raise HTTPException(status_code=404, detail="Operator task not found.")
    if current["kind"] != "campaign":
        raise HTTPException(status_code=409, detail="Only campaigns can be stopped; environment checks and publication finish their current step.")
    job = jobs.request_stop(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Operator task not found.")
    return job


@app.get("/api/jobs/{job_id}/report")
def report(job_id: str, request: Request):
    _require_auth(request)
    if not JOB_ID_RE.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="Report not found.")
    job = jobs.worker_config(job_id)
    if not job or job["kind"] != "campaign":
        raise HTTPException(status_code=404, detail="Report not found.")
    root = Path(job["run_root"]).resolve()
    expected_root = (JOBS_DIR / job_id).resolve()
    try:
        root.relative_to(expected_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Report not found.") from exc
    path = root / "benchmark_summary.md"
    if not path.is_file() or path.is_symlink():
        raise HTTPException(status_code=404, detail="The campaign report is not ready yet.")
    return FileResponse(path, media_type="text/markdown", filename="benchmark_summary.md")


@app.get("/api/history")
def history(request: Request, source: str = "all", q: str = "", refresh: bool = False):
    _require_auth(request)
    if source not in {"all", "canonical", "exploratory", "local"}:
        raise HTTPException(status_code=422, detail="Choose a supported history source.")
    records = all_runs(force_refresh=refresh)
    if source != "all":
        records = [item for item in records if item["source"] == source]
    query = q.strip().casefold()[:100]
    if query:
        records = [
            item for item in records
            if query in item["run_id"].casefold()
            or query in item["source"].casefold()
            or any(query in case.casefold() for case in item["cases"])
            or any(query in model.casefold() for models in item["models"].values() for model in models)
            or (item["technique"] and query in item["technique"].casefold())
        ]
    return {
        "summary": history_summary(records),
        "runs": [public_run(item) for item in records[:500]],
        "total_matches": len(records),
        "truncated": len(records) > 500,
    }


@app.get("/api/history/{run_ref}")
def history_detail(run_ref: str, request: Request):
    _require_auth(request)
    if not re.fullmatch(r"[0-9a-f]{32}", run_ref):
        raise HTTPException(status_code=404, detail="Run not found.")
    result = inspect_detail(run_ref)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found.")
    return result


@app.post("/api/compare")
async def compare(request: Request):
    _require_auth(request)
    try:
        payload = await request.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Select runs to compare.") from exc
    refs = payload.get("refs") if isinstance(payload, dict) else None
    if not isinstance(refs, list) or not 2 <= len(refs) <= 8 or any(
        not isinstance(ref, str) or not re.fullmatch(r"[0-9a-f]{32}", ref) for ref in refs
    ) or len(set(refs)) != len(refs):
        raise HTTPException(status_code=422, detail="Select between two and eight distinct runs.")
    records = [find_run(ref) for ref in refs]
    if any(record is None for record in records):
        raise HTTPException(status_code=404, detail="One of the selected runs is no longer available.")
    selected = [record for record in records if record is not None]
    case_sets = [set(record["cases"]) for record in selected]
    common = set.intersection(*case_sets) if case_sets else set()
    conditions = [
        {
            "run": public_run(record),
            "cases_in_common": len(common),
            "cases_only_in_this_run": len(case_sets[index] - common),
        }
        for index, record in enumerate(selected)
    ]
    return {
        "runs": conditions,
        "common_cases": sorted(common),
        "aligned_case_sets": all(case_set == case_sets[0] for case_set in case_sets[1:]),
        "caution": "Descriptive comparison. Check case, repetition, provider, API model, and Verification model alignment before attributing a difference.",
    }


@app.post("/api/publish/preview/{job_id}")
def publish_preview(job_id: str, request: Request):
    _require_auth(request)
    if not JOB_ID_RE.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="Campaign not found.")
    try:
        from .publishing import create_publish_preview

        return create_publish_preview(job_id)
    except FileNotFoundError as exc:
        detail = str(exc) if str(exc) == "Campaign not found." else "Campaign results are no longer available."
        raise HTTPException(status_code=409, detail=detail) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/publish")
async def publish(request: Request):
    _require_auth(request)
    try:
        payload = await request.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Review a completed campaign before publishing.") from exc
    job_id, token = (payload.get("job_id"), payload.get("preview_token")) if isinstance(payload, dict) else (None, None)
    if not isinstance(job_id, str) or not JOB_ID_RE.fullmatch(job_id) or not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
        raise HTTPException(status_code=422, detail="The publication preview has expired. Review the files again.")
    try:
        from .publishing import validate_publish_token

        if not validate_publish_token(job_id, token):
            raise HTTPException(status_code=409, detail="The publication preview expired or its source files changed. Review the files again.")
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="The publication preview is no longer available. Review the files again.") from exc
    return _new_worker("publish", {"campaign_job_id": job_id, "preview_token": token}, 0)

