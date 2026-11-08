#!/usr/bin/env python3
"""Install per-user systemd units for the selected KubeLLM lane."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CRON_MARKER = "# KUBELLM_LAB_SELECTED_SERVICES"


def checked(argv: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Could not run {Path(argv[0]).name}: {type(exc).__name__}") from exc


def quote_env(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("Environment values cannot contain newlines.")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def unit_text(description: str, repo: Path, python: Path, selector: Path, state: Path, *, rag: bool,
              service_path: str) -> str:
    if rag:
        start = f"{python} {repo / 'start_apiserver.py'} --lab-config {selector}"
    else:
        start = f"{python} -m uvicorn operator_ui.app:app --host 127.0.0.1 --port 8787 --workers 1 --no-access-log"
    return f"""[Unit]
Description={description}
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory={repo}
Environment=KUBELLM_LAB_CONFIG={quote_env(str(selector))}
Environment=KUBELLM_LAB_ACTIVE=1
Environment=KUBELLM_UI_STATE_DIR={quote_env(str(state))}
Environment=PYTHONUNBUFFERED=1
Environment=PATH={quote_env(service_path)}
UMask=0077
NoNewPrivileges=true
Restart=on-failure
RestartSec=10
ExecStartPre={python} {repo / 'scripts' / 'start_selected_lane_db.py'} --lab-config {selector}
ExecStart={start}

[Install]
WantedBy=default.target
"""


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    if path.exists() or path.is_symlink():
        if path.is_file() and not path.is_symlink() and path.read_text(encoding="utf-8") == text:
            if stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise RuntimeError(f"Existing service file is not owner-only: {path.name}")
            return
        raise RuntimeError(f"Refusing to overwrite an existing different service file: {path.name}")
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent, text=True)
    tmp = Path(name)
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        tmp.unlink(missing_ok=True)


def read_crontab() -> str:
    if not shutil.which("crontab"):
        raise RuntimeError("crontab is unavailable and user lingering is disabled.")
    result = checked(["crontab", "-l"])
    if result.returncode == 0:
        return result.stdout
    if result.returncode == 1 and not result.stdout.strip():
        return ""
    raise RuntimeError("Could not inspect the existing user crontab; it was left unchanged.")


def write_crontab(text: str) -> None:
    if not text.strip():
        result = checked(["crontab", "-r"])
        if result.returncode and "no crontab" not in (result.stderr or "").lower():
            raise RuntimeError("Could not remove the empty KubeLLM user crontab.")
        return
    result = subprocess.run(["crontab", "-"], input=text, capture_output=True,
                            text=True, timeout=30, check=False)
    if result.returncode:
        raise RuntimeError("Could not update only the KubeLLM user startup entry in crontab.")


def cron_entry(repo: Path, selector: Path, state: Path, python: Path, service_path: str,
               supervisor_script: Path | None = None) -> str:
    script = supervisor_script or repo / "scripts" / "supervise_lab_user_services.py"
    command = " ".join(shlex.quote(str(value)) for value in (
        python, script, "--repo", repo, "--lab-config", selector, "--state-dir", state, "--python", python,
        "--service-path", service_path,
    ))
    return f"@reboot sleep 30; PATH={shlex.quote(service_path)} {command} {CRON_MARKER}"


def update_crontab(text: str, *, entry: str | None) -> str:
    lines = [line for line in text.splitlines() if not line.rstrip().endswith(CRON_MARKER)]
    if entry:
        lines.append(entry)
    result = "\n".join(lines)
    return result + ("\n" if result else "")


def install(args: argparse.Namespace) -> dict:
    repo = args.repo.expanduser().resolve()
    selector = args.lab_config.expanduser().resolve()
    state = (args.state_dir or repo / ".local" / "operator_ui").expanduser().resolve()
    python = args.python.expanduser().resolve() if args.python else repo / ".venv" / "bin" / "python"
    supervisor_script = (args.supervisor_script or repo / "scripts" / "supervise_lab_user_services.py").expanduser().resolve()
    sys.path.insert(0, str(repo))
    from debug_assistant_latest.lab_context import load_lane_config

    lane = load_lane_config(selector)
    if (not (repo / "debug_assistant_latest" / "runner.py").is_file() or not python.is_file()
            or not supervisor_script.is_file()):
        raise RuntimeError("The selected checkout or its virtual environment is unavailable.")
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Docker CLI is unavailable; no service files were written.")
    service_path_items = [str(python.parent), str(Path(docker).resolve().parent)]
    for executable in ("minikube", "kubectl"):
        path = shutil.which(executable)
        if path:
            service_path_items.append(str(Path(path).resolve().parent))
    service_path = os.pathsep.join(dict.fromkeys([
        *service_path_items, "/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin",
    ]))
    inspected = checked(["docker", "inspect", lane["pgvector_container"], "--format", "{{json .}}"])
    if inspected.returncode:
        raise RuntimeError("The selected lane database container is unavailable.")
    container = json.loads(inspected.stdout)
    labels = (container.get("Config") or {}).get("Labels") or {}
    if labels.get("io.kubellm.lane") != lane["lane_id"]:
        raise RuntimeError("Database container owner label does not match the selected lane.")
    container_id = str(container.get("Id", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", container_id):
        raise RuntimeError("Database container identity is unavailable.")
    restart_policy = ((container.get("HostConfig") or {}).get("RestartPolicy") or {}).get("Name")

    user_config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    unit_dir = user_config / "systemd" / "user"
    desired = {
        unit_dir / "kubellm-ui.service": unit_text("KubeLLM operator UI", repo, python, selector, state, rag=False,
                                                   service_path=service_path),
        unit_dir / "kubellm-rag.service": unit_text("KubeLLM lane RAG API", repo, python, selector, state, rag=True,
                                                    service_path=service_path),
    }
    for path, contents in desired.items():
        if path.exists() and (not path.is_file() or path.is_symlink() or path.read_text(encoding="utf-8") != contents):
            raise RuntimeError(f"Refusing to overwrite existing different configuration: {path.name}")
    if not shutil.which("systemctl"):
        raise RuntimeError("systemctl is unavailable; no service files were written.")
    unit_names = ["kubellm-ui.service", "kubellm-rag.service"]
    was_enabled: dict[str, bool] = {}
    for name in unit_names:
        current = checked(["systemctl", "--user", "is-enabled", name])
        was_enabled[name] = current.returncode == 0 and current.stdout.strip() in {
            "enabled", "enabled-runtime", "linked", "linked-runtime", "alias",
        }

    linger = checked(["loginctl", "show-user", str(os.getuid()), "-p", "Linger", "--value"]) if shutil.which("loginctl") else None
    linger_enabled = bool(linger and linger.returncode == 0 and linger.stdout.strip().lower() == "yes")
    linger_enabled_by_installer = False
    if not linger_enabled and shutil.which("loginctl"):
        # A missing username selects the invoking user's own linger setting.
        enabled = checked(["loginctl", "enable-linger"])
        linger = checked(["loginctl", "show-user", str(os.getuid()), "-p", "Linger", "--value"])
        linger_enabled = bool(linger and linger.returncode == 0 and linger.stdout.strip().lower() == "yes")
        linger_enabled_by_installer = linger_enabled and enabled.returncode == 0
        if enabled.returncode == 0 and not linger_enabled:
            reverted = checked(["loginctl", "disable-linger"])
            if reverted.returncode:
                raise RuntimeError("Could not verify or roll back the user lingering change.")
    original_crontab = read_crontab() if shutil.which("crontab") else None
    if not linger_enabled and original_crontab is None:
        raise RuntimeError("User lingering is disabled and crontab is unavailable for the supervised fallback.")
    desired_crontab = None
    if not linger_enabled:
        desired_crontab = update_crontab(
            original_crontab or "",
            entry=cron_entry(repo, selector, state, python, service_path, supervisor_script),
        )
    elif original_crontab is not None:
        desired_crontab = update_crontab(original_crontab, entry=None)

    created: list[Path] = []
    database_policy_changed = False
    crontab_changed = False
    try:
        for path, contents in desired.items():
            existed = path.exists()
            write_private(path, contents)
            if not existed:
                created.append(path)
        reload_result = checked(["systemctl", "--user", "daemon-reload"])
        if linger_enabled:
            service_result = checked(["systemctl", "--user", "enable", "kubellm-ui.service", "kubellm-rag.service"])
        else:
            service_result = subprocess.CompletedProcess([], 0, "", "")
            for name in unit_names:
                if was_enabled[name]:
                    disabled = checked(["systemctl", "--user", "disable", name])
                    if disabled.returncode:
                        service_result = disabled
                        break
        if reload_result.returncode or service_result.returncode:
            raise RuntimeError("systemd user manager could not configure the service units; files were rolled back.")
        if restart_policy != "unless-stopped":
            updated = checked(["docker", "update", "--restart", "unless-stopped", container_id])
            if updated.returncode:
                raise RuntimeError("Could not enable automatic restart for the selected lane database.")
            database_policy_changed = True
        if desired_crontab is not None and desired_crontab != original_crontab:
            write_crontab(desired_crontab)
            crontab_changed = True
    except Exception:
        for name in unit_names:
            current = checked(["systemctl", "--user", "is-enabled", name])
            currently_enabled = current.returncode == 0 and current.stdout.strip() in {
                "enabled", "enabled-runtime", "linked", "linked-runtime", "alias",
            }
            if currently_enabled and not was_enabled[name]:
                checked(["systemctl", "--user", "disable", name])
            elif was_enabled[name] and not currently_enabled:
                checked(["systemctl", "--user", "enable", name])
        if database_policy_changed:
            checked(["docker", "update", "--restart", restart_policy or "no", container_id])
        if crontab_changed and original_crontab is not None:
            write_crontab(original_crontab)
        if linger_enabled_by_installer and shutil.which("loginctl"):
            checked(["loginctl", "disable-linger"])
        for path in created:
            path.unlink(missing_ok=True)
        checked(["systemctl", "--user", "daemon-reload"])
        raise

    return {
        "lane_id": lane["lane_id"],
        "units": ["kubellm-ui.service", "kubellm-rag.service"],
        "enabled": linger_enabled,
        "started": False,
        "database_restart_policy": "unless-stopped",
        "linger_enabled": linger_enabled,
        "startup_mode": "systemd-user" if linger_enabled else "supervised-user-crontab",
        "cron_fallback_installed": not linger_enabled,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install automatic UI/RAG startup and selected-lane DB restart.")
    parser.add_argument("--lab-config", type=Path, required=True, help="Explicit owner-only lane selector.")
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--supervisor-script", type=Path,
                        help="Optional persistent path for the cron fallback supervisor.")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args), sort_keys=True))
        return 0
    except Exception as exc:
        print(f"lab-ops-services: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
