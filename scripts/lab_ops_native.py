#!/usr/bin/env python3
"""Control the lab-native backup worker; bulk snapshot bytes never cross SSH."""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


HOST = "minh@10.242.128.44"
SSH_KEY = Path.home() / ".ssh/codex_kubellm_operator_ui"
REMOTE_REPO = "/home/minh/KubeLLM"
REMOTE_SELECTOR = "/home/minh/.config/kubellm/lanes/minh.json"
REMOTE_STATE = "/home/minh/KubeLLM/.local/operator_ui"
REMOTE_JOB_ROOT = "/dev/shm"
GITHUB_TOKEN_PATH = "/home/minh/.config/kubellm/lab-ops/github.token"
RECOVERY_IDENTITY = Path.home() / ".codex/lab-backups/recovery.agekey"
DEFAULT_MINIKUBE_ID = "sha256:b99726f2d7533eed1aaa0089828b87c9a4f5c307dc159eed4a58ac84579ac4b4"

REQUIRED_SCRIPTS = ("lab_ops_native_remote.py", "lab_ops_github.py", "lab_ops_backup.py")


class ControlError(RuntimeError):
    pass


def ssh_base():
    if not SSH_KEY.is_file():
        raise ControlError("The configured SSH identity is unavailable.")
    return ["ssh", "-T", "-i", str(SSH_KEY), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3"]


def run(argv, *, timeout=120, stdin=None):
    try:
        return subprocess.run(argv, input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ControlError(f"Could not complete {Path(argv[0]).name} ({type(exc).__name__}).") from None


def remote(host: str, command: str, *, stdin=None, timeout=120):
    result = run(ssh_base() + [host, command], stdin=stdin, timeout=timeout)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise ControlError(detail or "The lab control command failed.")
    return result.stdout


def ensure_recovery_identity() -> tuple[Path, str]:
    if RECOVERY_IDENTITY.is_symlink():
        raise ControlError("The recovery identity path must not be a symbolic link.")
    if not RECOVERY_IDENTITY.exists():
        RECOVERY_IDENTITY.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(RECOVERY_IDENTITY.parent, 0o700)
        generated = run(["age-keygen", "-o", str(RECOVERY_IDENTITY)], timeout=30)
        if generated.returncode:
            raise ControlError("A dedicated age recovery key could not be created.")
        os.chmod(RECOVERY_IDENTITY, 0o600)
    if (not RECOVERY_IDENTITY.is_file() or RECOVERY_IDENTITY.stat().st_mode & 0o077):
        raise ControlError("The dedicated age recovery identity must be a mode-0600 regular file.")
    public = run(["age-keygen", "-y", str(RECOVERY_IDENTITY)], timeout=20)
    if public.returncode:
        raise ControlError("The dedicated age recovery identity could not be validated.")
    recipient = public.stdout.decode("ascii", "strict").strip().splitlines()[-1]
    if not re.fullmatch(r"age1[0-9a-z]{58}", recipient):
        raise ControlError("The dedicated age recovery identity produced an invalid recipient.")
    return RECOVERY_IDENTITY, recipient


def configure_token(args):
    token = getpass.getpass(
        "Fine-grained GitHub token (private kubellm-lab-backups repo, Contents read/write): "
    ).strip()
    if not token.startswith("github_pat_") or any(ch.isspace() for ch in token) or len(token) > 4096:
        raise ControlError("Use a GitHub fine-grained token; the token was not sent or stored.")
    code = (
        "import os,pathlib,sys; p=pathlib.Path(" + repr(GITHUB_TOKEN_PATH) + "); "
        "p.parent.mkdir(mode=0o700,parents=True,exist_ok=True); os.chmod(p.parent,0o700); "
        "assert not p.exists() and not p.is_symlink(), 'token file already exists'; "
        "fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); "
        "f=os.fdopen(fd,'w',encoding='ascii'); f.write(sys.stdin.read(4097).strip()+'\\n'); f.close(); "
        "print('token_configured=true mode=0600')"
    )
    result = remote(args.host, "python3 -c " + shlex.quote(code), stdin=(token + "\n").encode("ascii"))
    print(result.decode("utf-8", "replace").strip())
    print("The token stayed out of chat, process arguments, and shell history.")


def scp_scripts(host: str, job_id: str, repo: Path, *, create_dir: bool = True):
    directory = f"{REMOTE_JOB_ROOT}/kubellm-{job_id}"
    if create_dir:
        remote(host, "umask 077; mkdir -m 700 " + shlex.quote(directory))
    result = run(["scp", "-i", str(SSH_KEY), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                  *[str(repo / "scripts" / name) for name in REQUIRED_SCRIPTS],
                  f"{host}:{directory}/"], timeout=120)
    if result.returncode:
        raise ControlError(result.stderr.decode("utf-8", "replace").strip() or
                           "The small lab control scripts could not be copied to RAM.")
    remote(host, "chmod 600 " + shlex.quote(directory) + "/*.py")


def common_args(job_id: str, release_tag: str, recipient: str, minikube_id: str) -> list[str]:
    return ["--job-id", job_id, "--release-tag", release_tag, "--selector", REMOTE_SELECTOR,
            "--state-dir", REMOTE_STATE, "--repo-dir", REMOTE_REPO,
            "--minikube-id", minikube_id, "--age-recipient", recipient]


def create_job_id() -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    import secrets
    return "job-" + stamp + "-" + secrets.token_hex(4)


def prepare(args):
    identity_path, recipient = ensure_recovery_identity()
    job_id = create_job_id()
    release_tag = args.release_tag or "lab-backup-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"lab-backup-[0-9]{8}T[0-9]{6}Z", release_tag):
        raise ControlError("Use a lab-backup tag with a UTC timestamp.")
    scp_scripts(args.host, job_id, Path(args.repo_dir))
    remote_command = "python3 " + shlex.quote(f"{REMOTE_JOB_ROOT}/kubellm-{job_id}/lab_ops_native_remote.py") + " prepare"
    remote_command += " " + " ".join(shlex.quote(value) for value in
                                     common_args(job_id, release_tag, recipient, args.minikube_id))
    output = remote(args.host, remote_command, timeout=120)
    print(output.decode("utf-8", "replace").strip())
    print(f"Recovery key: {identity_path}")
    print("Check status until phase=awaiting-recovery-key, then run resume with this job ID.")


def status(args):
    if not re.fullmatch(r"job-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}", args.job_id):
        raise ControlError("The job ID is invalid.")
    path = f"/home/minh/KubeLLM/.local/lab-ops/jobs/{args.job_id}.json"
    code = (
        "import json,pathlib; p=pathlib.Path(" + repr(path) + "); "
        "print(p.read_text() if p.is_file() else json.dumps({"
        "'job_id':" + repr(args.job_id) + ",'phase':'starting',"
        "'detail':'Worker started; initial bootstrap checks have not written status yet.'}))"
    )
    result = remote(args.host, "python3 -c " + shlex.quote(code))
    try:
        value = json.loads(result)
    except (ValueError, TypeError):
        raise ControlError("The lab returned invalid job status.") from None
    print(json.dumps(value, indent=2, sort_keys=True))


def resume(args):
    if not re.fullmatch(r"job-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}", args.job_id):
        raise ControlError("The job ID is invalid.")
    path = f"/home/minh/KubeLLM/.local/lab-ops/jobs/{args.job_id}.json"
    result = remote(args.host, "cat " + shlex.quote(path))
    try:
        record = json.loads(result)
    except (ValueError, TypeError):
        raise ControlError("The lab returned invalid job status.") from None
    if record.get("phase") != "awaiting-recovery-key":
        raise ControlError("The job is not waiting for its recovery identity; inspect status first.")
    identity_path, recipient = ensure_recovery_identity()
    scp_scripts(args.host, args.job_id, Path(args.repo_dir), create_dir=False)
    work = Path(f"/dev/shm/kubellm-{args.job_id}")
    config_remote = work / "data/job.json"
    config_data = remote(args.host, "cat " + shlex.quote(str(config_remote)))
    try:
        saved = json.loads(config_data)
    except (ValueError, TypeError):
        raise ControlError("The prepared restore job metadata is invalid.") from None
    identity = identity_path.read_text(encoding="ascii")
    if saved.get("age_recipient") != recipient:
        raise ControlError("The local recovery identity does not match this prepared job.")
    command = "python3 " + shlex.quote(str(work / "lab_ops_native_remote.py")) + " resume"
    command += " " + " ".join(shlex.quote(value) for value in common_args(
        args.job_id, saved["release_tag"], recipient, saved["minikube_id"]))
    output = remote(args.host, command, stdin=identity.encode("ascii"), timeout=120)
    print(output.decode("utf-8", "replace").strip())
    print("The recovery identity was sent only after the prepared VM was shut down.")


def main():
    parser = argparse.ArgumentParser(description="Run a lab-native encrypted backup and QEMU restore drill.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--repo-dir", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("configure-token")
    start = sub.add_parser("prepare")
    start.add_argument("--release-tag", help="Resume this exact existing draft tag if one is available.")
    start.add_argument("--minikube-id", default=DEFAULT_MINIKUBE_ID)
    check = sub.add_parser("status")
    check.add_argument("--job-id", required=True)
    finish = sub.add_parser("resume")
    finish.add_argument("--job-id", required=True)
    args = parser.parse_args()
    try:
        if args.action == "configure-token":
            configure_token(args)
        elif args.action == "prepare":
            prepare(args)
        elif args.action == "status":
            status(args)
        else:
            resume(args)
        return 0
    except (ControlError, UnicodeError) as exc:
        print("lab-ops-native: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
