#!/usr/bin/env python3
"""Create and verify a client-encrypted KubeLLM lab snapshot on GitHub.

The snapshot is streamed from the lab through age into a local ciphertext-only
temporary file, uploaded as a private GitHub Release asset, then downloaded,
decrypted in a mode-0600 temporary directory, and checked before success.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_HOST = "minh@10.242.128.44"
DEFAULT_SSH_KEY = Path.home() / ".ssh" / "codex_kubellm_operator_ui"
DEFAULT_SELECTOR = "/home/minh/.config/kubellm/lanes/minh.json"
DEFAULT_STATE = "/home/minh/KubeLLM/.local/operator_ui"
DEFAULT_REPO = "/home/minh/KubeLLM"
DEFAULT_GITHUB_REPO = "minh-mhl-le/kubellm-lab-backups"
MAX_ASSET_BYTES = 2 * 1024**3 - 1
ASSET_PART_BYTES = 1800 * 1024**2
SNAPSHOT_TIMEOUT_SECONDS = 6 * 60 * 60
RELEASE_TIMEOUT_SECONDS = 4 * 60 * 60
DEFAULT_LOCAL_COPY_DIR = Path.home() / ".codex" / "lab-backups" / "snapshots"
DEFAULT_MINIKUBE_LOOPBACK_PORTS = frozenset({"22/tcp", "2376/tcp", "32443/tcp", "5000/tcp", "8443/tcp"})


def has_reviewed_dynamic_loopback_ports(bindings: object) -> bool:
    if not isinstance(bindings, dict) or set(bindings) != DEFAULT_MINIKUBE_LOOPBACK_PORTS:
        return False
    for values in bindings.values():
        if (not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict)
                or values[0].get("HostIp") != "127.0.0.1" or values[0].get("HostPort") != ""):
            return False
    return True


REMOTE_IDLE_CHECK = r'''import pathlib, sqlite3, sys
selector = str(pathlib.Path(sys.argv[1]).expanduser().resolve()).encode()
db_path = pathlib.Path(sys.argv[2]) / "operator.sqlite3"
include_default_profile = len(sys.argv) > 3 and sys.argv[3] == "1"
if db_path.is_file():
    db = sqlite3.connect("file:" + str(db_path) + "?mode=ro", uri=True, timeout=5)
    try:
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone()
        if exists and db.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running','stop_requested') LIMIT 1").fetchone():
            raise SystemExit(2)
    finally:
        db.close()
for proc in pathlib.Path("/proc").iterdir():
    if not proc.name.isdecimal():
        continue
    try:
        command_line = (proc / "cmdline").read_bytes()
    except OSError:
        continue
    arguments = [item.decode("utf-8", "replace") for item in command_line.split(b"\0") if item]
    runner = any(item.endswith("debug_assistant_latest/runner.py") or item == "debug_assistant_latest.runner"
                 for item in arguments)
    if not runner:
        continue
    if include_default_profile:
        raise SystemExit(2)
    try:
        environment = (proc / "environ").read_bytes().split(b"\0")
    except OSError:
        environment = []
    selected = any(item == b"KUBELLM_LAB_CONFIG=" + selector for item in environment)
    cwd = pathlib.Path("/")
    try:
        cwd = (proc / "cwd").resolve()
    except OSError:
        pass
    values = []
    for index, item in enumerate(arguments):
        if item == "--lab-config" and index + 1 < len(arguments):
            values.append(arguments[index + 1])
        elif item.startswith("--lab-config="):
            values.append(item.partition("=")[2])
    for value in values:
        candidate = pathlib.Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = cwd / candidate
        try:
            selected = selected or str(candidate.resolve()).encode() == selector
        except OSError:
            continue
    if selected or (not environment and not values):
        raise SystemExit(2)
'''
REMOTE_SNAPSHOT = r'''import datetime, hashlib, io, json, os, pathlib, sqlite3, stat, subprocess, sys, threading, zipfile

SNAPSHOT_TIMEOUT_SECONDS = 6 * 60 * 60
selector = pathlib.Path(sys.argv[1])
state = pathlib.Path(sys.argv[2])
repo = pathlib.Path(sys.argv[3])
expected_legacy_id = sys.argv[4] if len(sys.argv) > 4 else ""
if selector.is_symlink() or not selector.is_file() or stat.S_IMODE(selector.stat().st_mode) & 0o077:
    raise SystemExit("private lane selector is missing or not owner-only")
lane = json.loads(selector.read_text(encoding="utf-8"))
if not isinstance(lane, dict) or not lane.get("lane_id") or not lane.get("pgvector_container"):
    raise SystemExit("private lane selector is invalid")
files = [("lane/selector.json", selector)]
for key, member in (("service_env_file", "lane/service.env"), ("kubeconfig_path", "lane/kubeconfig")):
    path = pathlib.Path(lane[key]).expanduser()
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise SystemExit("private lane file is missing or not owner-only")
    files.append((member, path))
legacy_preflight = None
legacy_profile_files = []
legacy_kubeconfig = None
if expected_legacy_id:
    if len(expected_legacy_id) != 64 or any(ch not in "0123456789abcdef" for ch in expected_legacy_id):
        raise SystemExit("approved default profile requires a full immutable container ID")
    result = subprocess.run(["docker", "inspect", expected_legacy_id], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15, check=False)
    if result.returncode:
        raise SystemExit("approved default profile container is unavailable")
    try:
        item = json.loads(result.stdout)[0]
    except (ValueError, IndexError, TypeError):
        raise SystemExit("approved default profile identity could not be verified")
    labels = (item.get("Config") or {}).get("Labels") or {}
    mounts = item.get("Mounts") or []
    if (item.get("Id") != expected_legacy_id or str(item.get("Name", "")).lstrip("/") != "minikube"
            or labels.get("name.minikube.sigs.k8s.io") != "minikube"
            or not any(mount.get("Name") == "minikube" and mount.get("Destination") == "/var" for mount in mounts)
            or (item.get("State") or {}).get("Running") is not True):
        raise SystemExit("approved default profile identity, volume, or running state changed")
    profile = pathlib.Path.home() / ".minikube" / "profiles" / "minikube"
    if profile.is_symlink() or not profile.is_dir():
        raise SystemExit("approved default profile files are unavailable")
    for current, dirs, names in os.walk(profile, topdown=True, followlinks=False):
        base = pathlib.Path(current)
        if any((base / name).is_symlink() for name in dirs + names):
            raise SystemExit("approved default profile contains a symbolic link")
        dirs[:] = sorted(dirs)
        for name in sorted(names):
            path = base / name
            if path.is_file():
                legacy_profile_files.append(("legacy/minikube/profile/" + path.relative_to(profile).as_posix(), path))
    kubeconfig = pathlib.Path.home() / ".kube" / "config"
    view = subprocess.run(["kubectl", "--kubeconfig", str(kubeconfig), "config", "view", "--context", "minikube",
                           "--raw", "--minify", "-o", "json"], stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=False)
    if view.returncode:
        raise SystemExit("the default profile's isolated kubeconfig context could not be captured")
    legacy_kubeconfig = view.stdout
    volume = subprocess.run(["docker", "volume", "inspect", "minikube"], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15, check=False)
    if volume.returncode:
        raise SystemExit("approved default profile volume could not be inspected")
    try:
        volume_data = json.loads(volume.stdout)[0]
    except (ValueError, IndexError, TypeError):
        raise SystemExit("approved default profile volume metadata is invalid")
    if volume_data.get("Name") != "minikube":
        raise SystemExit("approved default profile volume identity changed")
    volume_users = subprocess.run(["docker", "ps", "-a", "--filter", "volume=minikube", "--no-trunc", "--format", "{{.ID}}"],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, timeout=15, check=False)
    if volume_users.returncode:
        raise SystemExit("approved default profile volume references could not be checked")
    users = {value.strip().removeprefix("sha256:") for value in volume_users.stdout.splitlines() if value.strip()}
    if users != {expected_legacy_id}:
        raise SystemExit("the approved default profile volume is attached to an unexpected container")
    network_name = str((item.get("HostConfig") or {}).get("NetworkMode", ""))
    if not network_name or network_name == "default":
        network_name = "minikube"
    network = subprocess.run(["docker", "network", "inspect", network_name], stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15, check=False)
    if network.returncode:
        raise SystemExit("approved default profile network could not be inspected")
    try:
        network_data = json.loads(network.stdout)[0]
    except (ValueError, IndexError, TypeError):
        raise SystemExit("approved default profile network metadata is invalid")
    network_users = {str(value).removeprefix("sha256:") for value in (network_data.get("Containers") or {})}
    if network_users != {expected_legacy_id}:
        raise SystemExit("the approved default profile network has unexpected container attachments")
    networks = (item.get("NetworkSettings") or {}).get("Networks") or {}
    if (len(networks) != 1 or network_name not in networks
            or str((item.get("HostConfig") or {}).get("NetworkMode") or "") != network_name):
        raise SystemExit("approved default profile network settings cannot be isolated for a restore drill")
    mounts = item.get("Mounts") or []
    volume_mount = any(mount.get("Name") == "minikube" and mount.get("Destination") == "/var"
                       and mount.get("Type") == "volume" for mount in mounts)
    modules_mount = any(mount.get("Type") == "bind" and mount.get("Source") == "/lib/modules"
                        and mount.get("Destination") == "/lib/modules" and mount.get("RW") is False
                        for mount in mounts)
    if len(mounts) != 2 or not volume_mount or not modules_mount:
        raise SystemExit("approved default profile mounts changed or include unreviewed paths")
    if modules_mount.get("Propagation") not in (None, "", "rprivate", "rshared", "rslave"):
        raise SystemExit("approved default profile bind propagation cannot be restored safely")
    host_config = item.get("HostConfig") or {}
    expected_ports = {"22/tcp", "2376/tcp", "32443/tcp", "5000/tcp", "8443/tcp"}
    port_bindings = host_config.get("PortBindings") or {}
    if set(port_bindings) != expected_ports:
        raise SystemExit("approved default profile port publications changed from the reviewed loopback mappings")
    for values in port_bindings.values():
        if (not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict)
                or values[0].get("HostIp") != "127.0.0.1" or values[0].get("HostPort") != ""):
            raise SystemExit("approved default profile port publications are not isolated dynamic loopback mappings")
    unsupported = [key for key in ("Devices", "DeviceRequests") if host_config.get(key)]
    unsupported.extend(key for key in ("PidMode", "IpcMode", "UTSMode", "UsernsMode")
                       if host_config.get(key) not in (None, "", "private"))
    if host_config.get("Runtime") not in (None, "", "runc"):
        unsupported.append("Runtime")
    if unsupported:
        raise SystemExit("approved default profile has unsupported Docker host settings: " + ", ".join(unsupported))
    legacy_preflight = {"container_id": expected_legacy_id, "volume": volume_data, "network": network_data}
if not state.is_dir() or not repo.is_dir():
    raise SystemExit("requested state or checkout directory is missing")

manifest = {"schema_version": 1, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "host": __import__("socket").gethostname(), "lane_id": lane["lane_id"],
            "contents": [], "excluded": ["secrets outside the selected lane"]}
if legacy_preflight:
    manifest["legacy_minikube"] = legacy_preflight
    manifest["excluded"] = ["secrets outside the selected lane and approved default profile"]
def ensure_idle():
    db_path = state / "operator.sqlite3"
    if db_path.is_file():
        db = sqlite3.connect("file:" + str(db_path) + "?mode=ro", uri=True, timeout=5)
        try:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone()
            if exists:
                active = db.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running','stop_requested') LIMIT 1").fetchone()
                if active:
                    raise SystemExit("an operator job is active; wait for it to finish before snapshotting")
        finally:
            db.close()
    expected = str(selector.resolve()).encode()
    proc_root = pathlib.Path("/proc")
    if proc_root.is_dir():
        for proc in proc_root.iterdir():
            if not proc.name.isdecimal():
                continue
            try:
                command_line = (proc / "cmdline").read_bytes()
            except OSError:
                continue
            arguments = [value.decode("utf-8", "replace") for value in command_line.split(b"\0") if value]
            runner = any(value.endswith("debug_assistant_latest/runner.py") or value == "debug_assistant_latest.runner"
                         for value in arguments)
            if not runner:
                continue
            if expected_legacy_id:
                raise SystemExit("a benchmark runner is active; wait before snapshotting the shared default profile")
            try:
                environment = (proc / "environ").read_bytes().split(b"\0")
            except OSError:
                environment = []
            selected = any(value == b"KUBELLM_LAB_CONFIG=" + expected for value in environment)
            cwd = pathlib.Path("/")
            try:
                cwd = (proc / "cwd").resolve()
            except OSError:
                pass
            values = []
            for index, value in enumerate(arguments):
                if value == "--lab-config" and index + 1 < len(arguments):
                    values.append(arguments[index + 1])
                elif value.startswith("--lab-config="):
                    values.append(value.partition("=")[2])
            for value in values:
                candidate = pathlib.Path(value).expanduser()
                if not candidate.is_absolute():
                    candidate = cwd / candidate
                try:
                    selected = selected or str(candidate.resolve()).encode() == expected
                except OSError:
                    continue
            if selected or (not environment and not values):
                raise SystemExit("a selected-lane runner process is active; wait before snapshotting")
ensure_idle()
try:
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=5, check=False)
    if head.returncode == 0:
        manifest["canonical_commit"] = head.stdout.strip()
except Exception:
    pass

out = zipfile.ZipFile(sys.stdout.buffer, mode="w", compression=zipfile.ZIP_STORED, allowZip64=True)
digests = []
def add_stream(name, source, mode=384):
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_STORED
    digest, size = hashlib.sha256(), 0
    with out.open(info, "w", force_zip64=True) as target:
        while True:
            block = source.read(1024 * 1024)
            if not block:
                break
            target.write(block)
            digest.update(block)
            size += len(block)
    digests.append({"path": name, "size_bytes": size, "mode": mode, "sha256": digest.hexdigest()})

for member, path in files:
    with path.open("rb") as source:
        add_stream(member, source, stat.S_IMODE(path.stat().st_mode))
for member, path in legacy_profile_files:
    with path.open("rb") as source:
        add_stream(member, source, stat.S_IMODE(path.stat().st_mode))
if legacy_kubeconfig is not None:
    add_stream("legacy/minikube/kubeconfig.json", io.BytesIO(legacy_kubeconfig), 0o600)

# SQLite backup API includes committed WAL content without copying a live DB file.
db = state / "operator.sqlite3"
if db.is_file():
    source = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True, timeout=10)
    memory = sqlite3.connect(":memory:")
    source.backup(memory)
    data = ("\n".join(memory.iterdump()) + "\n").encode("utf-8")
    source.close(); memory.close()
    import io
    add_stream("operator/operator.sqlite.sql", io.BytesIO(data))

# Dump the selected lane database directly into the encrypted stream. The
# selected container must prove its lane label and be running first.
inspection = subprocess.run(["docker", "inspect", lane["pgvector_container"]], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=False)
if inspection.returncode != 0:
    raise SystemExit("selected lane database container is unavailable")
container = json.loads(inspection.stdout)[0]
labels = (container.get("Config") or {}).get("Labels") or {}
if labels.get("io.kubellm.lane") != lane["lane_id"] or not (container.get("State") or {}).get("Running"):
    raise SystemExit("selected lane database ownership or health could not be verified")
manifest["database_container"] = lane["pgvector_container"]
manifest["database_container_id"] = container["Id"]
manifest["database_image_id"] = container.get("Image")
manifest["database_image_ref"] = (container.get("Config") or {}).get("Image")
database_env = {}
for entry in (container.get("Config") or {}).get("Env") or []:
    key, separator, value = entry.partition("=")
    if separator and key in {"POSTGRES_DB", "POSTGRES_USER"}:
        database_env[key] = value
manifest["database_name"] = database_env.get("POSTGRES_DB", "postgres")
manifest["database_user"] = database_env.get("POSTGRES_USER", "postgres")
dump = subprocess.Popen(["docker", "exec", container["Id"], "sh", "-ec",
                         'pg_dump --format=custom --no-owner --no-acl --username="${POSTGRES_USER:-postgres}" --dbname="${POSTGRES_DB:-postgres}"'],
                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
errors = bytearray()
def drain_errors():
    while True:
        block = dump.stderr.read(1024)
        if not block:
            return
        if len(errors) < 4096:
            errors.extend(block[:4096-len(errors)])
thread = threading.Thread(target=drain_errors, daemon=True)
thread.start()
add_stream("database/selected-lane.pgcustom", dump.stdout)
if dump.wait(timeout=900) != 0:
    raise SystemExit("selected lane database export failed")
thread.join(timeout=2)
image_save = subprocess.Popen(["docker", "image", "save", container["Image"]], stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
add_stream("database/selected-lane-image.tar", image_save.stdout)
if image_save.wait(timeout=SNAPSHOT_TIMEOUT_SECONDS) != 0:
    raise SystemExit("selected lane database image could not be archived")

if legacy_preflight:
    legacy_id = legacy_preflight["container_id"]
    stopped = subprocess.run(["docker", "stop", "--time", "120", legacy_id], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=150, check=False)
    if stopped.returncode:
        raise SystemExit("approved default profile could not be stopped for a cold snapshot")
    stopped_inspect = subprocess.run(["docker", "inspect", legacy_id], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                                     timeout=15, check=False)
    if stopped_inspect.returncode:
        raise SystemExit("approved default profile could not be inspected after stopping")
    legacy_container = json.loads(stopped_inspect.stdout)[0]
    if legacy_container.get("Id") != legacy_id or (legacy_container.get("State") or {}).get("Running") is not False:
        raise SystemExit("approved default profile is not cold; no retirement action is allowed")
    def add_json(name, value):
        raw = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        add_stream(name, io.BytesIO(raw), 0o600)
    add_json("legacy/minikube/volume-inspect.json", legacy_preflight["volume"])
    add_json("legacy/minikube/network-inspect.json", legacy_preflight["network"])
    temporary_image = "kubellm-legacy-snapshot:" + __import__("secrets").token_hex(6)
    committed = subprocess.run(["docker", "commit", legacy_id, temporary_image], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300, check=False)
    if committed.returncode:
        raise SystemExit("cold snapshot of the approved default container writable layer failed")
    try:
        image_id = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", temporary_image],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, timeout=30, check=False)
        if image_id.returncode or not image_id.stdout.strip():
            raise SystemExit("cold snapshot image identity could not be verified")
        manifest["legacy_minikube"]["container_image_id"] = image_id.stdout.strip()
        add_json("legacy/minikube/container-inspect.json", legacy_container)
        volume_copy = subprocess.Popen(["docker", "cp", legacy_id + ":/var", "-"], stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        add_stream("legacy/minikube/var-volume.tar", volume_copy.stdout)
        if volume_copy.wait(timeout=SNAPSHOT_TIMEOUT_SECONDS) != 0:
            raise SystemExit("approved default profile volume could not be copied from its stopped container")
        image_save = subprocess.Popen(["docker", "image", "save", temporary_image], stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        add_stream("legacy/minikube/container-image.tar", image_save.stdout)
        if image_save.wait(timeout=SNAPSHOT_TIMEOUT_SECONDS) != 0:
            raise SystemExit("approved default profile container image could not be streamed")
    finally:
        removed = subprocess.run(["docker", "image", "rm", temporary_image], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=False)
        if removed.returncode:
            raise SystemExit("cold snapshot helper image could not be removed")

def add_tree(label, root, *, skip_worktrees=False):
    root = pathlib.Path(root)
    if not root.exists():
        return
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("evidence path is not a regular directory")
    for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
        base = pathlib.Path(current)
        dirs[:] = sorted(name for name in dirs if name not in {"__pycache__", ".pytest_cache", "node_modules", ".venv", "dist", "cache", "caches"}
                        and not (skip_worktrees and name == "worktrees")
                        and not (base / name).is_symlink())
        for name in sorted(names):
            path = base / name
            if path.is_symlink() or not path.is_file():
                continue
            if path.name in {"operator.sqlite3", "operator.sqlite3-wal", "operator.sqlite3-shm"}:
                continue
            relative = path.relative_to(root).as_posix()
            archive_name = label + "/" + relative
            with path.open("rb") as source:
                add_stream(archive_name, source, stat.S_IMODE(path.stat().st_mode))

# Preserve only the selected operator state, including its history and logs.
# Other ignored files can belong to a different lane and are deliberately left out.
add_tree("operator-state", state, skip_worktrees=True)
ensure_idle()

manifest["contents"] = digests
raw = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
add_stream("manifest.json", __import__("io").BytesIO(raw))
out.close()
sys.stdout.buffer.flush()
'''


class BackupError(RuntimeError):
    pass


def run(argv: list[str], *, timeout: int = 60, stdin=None, stdout=None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL if stdin is None else stdin,
                              stdout=subprocess.PIPE if stdout is None else stdout,
                              stderr=subprocess.PIPE, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackupError(f"Could not complete {Path(argv[0]).name}: {type(exc).__name__}") from exc


def remote_command(args: argparse.Namespace) -> list[str]:
    import base64
    import shlex

    code = "import base64;exec(base64.b64decode(" + repr(base64.b64encode(REMOTE_SNAPSHOT.encode()).decode()) + "))"
    remote = "python3 -c " + shlex.quote(code) + " " + " ".join(
        shlex.quote(value) for value in (args.selector, args.state_dir, args.repo_dir,
                                         args.expected_default_minikube_container_id or "")
    )
    return [
        "ssh", "-T", "-i", str(args.ssh_key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
        args.host, remote,
    ]


def assert_private_repo(repository: str) -> None:
    result = run(["gh", "api", f"repos/{repository}", "--jq", ".visibility + \" \" + .owner.login"], timeout=20)
    if result.returncode:
        raise BackupError("The backup repository could not be verified with GitHub.")
    identity = result.stdout.decode("utf-8", "replace").strip().split()
    if identity != ["private", "minh-mhl-le"]:
        raise BackupError("The configured backup destination is not the expected private personal repository.")


def remote_ensure_legacy_started(args: argparse.Namespace) -> None:
    container_id = args.expected_default_minikube_container_id
    if not container_id:
        return
    if len(container_id) != 64 or any(char not in "0123456789abcdef" for char in container_id):
        raise BackupError("Refusing rollback because the approved default container ID is invalid.")
    remote_script = (
        "state=$(docker inspect --format '{{.State.Running}}' " + shlex.quote(container_id) + ") || exit 2; "
        "if [ \"$state\" != true ]; then docker start " + shlex.quote(container_id) + " >/dev/null || exit 3; fi; "
        "test \"$(docker inspect --format '{{.State.Running}}' " + shlex.quote(container_id) + ")\" = true"
    )
    result = run([
        "ssh", "-T", "-i", str(args.ssh_key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10", args.host, "sh -ec " + shlex.quote(remote_script),
    ], timeout=180)
    if result.returncode:
        raise BackupError("Restore verification failed and the approved original cluster could not be restarted.")


def remote_check_idle(args: argparse.Namespace) -> None:
    import base64

    code = "import base64;exec(base64.b64decode(" + repr(base64.b64encode(REMOTE_IDLE_CHECK.encode()).decode()) + "))"
    include_default = "1" if args.include_approved_default_minikube else "0"
    remote = ("python3 -c " + shlex.quote(code) + " " + shlex.quote(args.selector) + " "
              + shlex.quote(args.state_dir) + " " + include_default)
    result = run([
        "ssh", "-T", "-i", str(args.ssh_key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10", args.host, remote,
    ], timeout=20)
    if result.returncode:
        if args.include_approved_default_minikube:
            raise BackupError("Could not verify the lab is idle before snapshotting the shared default profile.")
        raise BackupError("Could not verify the selected lane is idle before snapshotting.")


def archive_member_sha256(archive, path: str) -> str:
    digest = hashlib.sha256()
    with archive.open(path) as member:
        while True:
            block = member.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def split_encrypted_asset(path: Path, output_dir: Path, tag: str) -> list[Path]:
    size = path.stat().st_size
    if size <= 0:
        raise BackupError("Encrypted snapshot is empty; no release was uploaded.")
    count = (size + ASSET_PART_BYTES - 1) // ASSET_PART_BYTES
    parts: list[Path] = []
    with path.open("rb") as source:
        for index in range(count):
            part = output_dir / f"{tag}-part-{index + 1:03d}-of-{count:03d}.age"
            expected_size = min(ASSET_PART_BYTES, size - index * ASSET_PART_BYTES)
            written = 0
            with part.open("xb") as target:
                os.chmod(part, stat.S_IRUSR | stat.S_IWUSR)
                remaining = expected_size
                while remaining:
                    block = source.read(min(1024 * 1024, remaining))
                    if not block:
                        break
                    target.write(block)
                    written += len(block)
                    remaining -= len(block)
                target.flush()
                os.fsync(target.fileno())
            if written != expected_size:
                raise BackupError("Encrypted snapshot changed while it was being split.")
            if part.stat().st_size > MAX_ASSET_BYTES:
                raise BackupError("A split encrypted asset exceeds GitHub's per-asset limit.")
            parts.append(part)
    return parts


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            block = source.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def concatenate_assets(parts: list[Path], output: Path) -> str:
    digest = hashlib.sha256()
    with output.open("xb") as target:
        os.chmod(output, stat.S_IRUSR | stat.S_IWUSR)
        for part in parts:
            with part.open("rb") as source:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    target.write(block)
                    digest.update(block)
        target.flush()
        os.fsync(target.fileno())
    return digest.hexdigest()


def retain_encrypted_copy(source: Path, directory: Path, tag: str) -> Path:
    if directory.is_symlink():
        raise BackupError("Local encrypted-copy directory cannot be a symbolic link.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    destination = directory / f"{tag}.zip.age"
    if destination.exists() or destination.is_symlink():
        raise BackupError("Local encrypted-copy destination already exists; refusing to overwrite it.")
    try:
        with source.open("rb") as reader, destination.open("xb") as writer:
            os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR)
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def local_docker(args: argparse.Namespace, *argv: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return run(["docker", "--host", args.restore_docker_host, *argv], timeout=timeout)


def require_isolated_restore_engine(args: argparse.Namespace) -> None:
    result = local_docker(args, "info", "--format", "{{.OSType}} {{.Architecture}}", timeout=20)
    if result.returncode or result.stdout.decode("utf-8", "replace").strip() not in {"linux x86_64", "linux amd64"}:
        raise BackupError("The isolated x86_64 Linux restore Docker engine is unavailable; no snapshot was started.")


def _copy_zip_member(archive, member_name: str, destination: Path) -> None:
    with archive.open(member_name) as source, destination.open("xb") as target:
        os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR)
        shutil.copyfileobj(source, target, length=1024 * 1024)
        target.flush()
        os.fsync(target.fileno())


def verify_postgres_restore(args: argparse.Namespace, archive, manifest: dict) -> None:
    import time

    image_member = "database/selected-lane-image.tar"
    dump_member = "database/selected-lane.pgcustom"
    image_id = str(manifest.get("database_image_id", ""))
    user = str(manifest.get("database_user", "postgres"))
    if image_member not in archive.namelist() or dump_member not in archive.namelist() or not image_id.startswith("sha256:"):
        raise BackupError("Snapshot is missing the selected database image or dump needed for restore.")

    with tempfile.TemporaryDirectory(prefix="kubellm-pg-restore-") as temp_name:
        temp = Path(temp_name)
        os.chmod(temp, 0o700)
        image_tar = temp / "database-image.tar"
        _copy_zip_member(archive, image_member, image_tar)
        exists = local_docker(args, "image", "inspect", image_id)
        loaded = exists.returncode != 0
        image_loaded = False
        if loaded:
            result = local_docker(args, "image", "load", "--input", str(image_tar), timeout=RELEASE_TIMEOUT_SECONDS)
            if result.returncode:
                raise BackupError("Selected database image could not be restored into the isolated engine.")
            image_loaded = True
            if local_docker(args, "image", "inspect", image_id).returncode:
                removed = local_docker(args, "image", "rm", image_id, timeout=120)
                if removed.returncode:
                    raise BackupError("Selected database image failed verification and could not be removed.")
                raise BackupError("Selected database image could not be restored into the isolated engine.")

        container = "kubellm-pg-restore-" + secrets.token_hex(4)
        database = "kubellm_restore_" + secrets.token_hex(4)
        started = local_docker(args, "run", "--detach", "--name", container,
                               "--env", "POSTGRES_HOST_AUTH_METHOD=trust", "--env", "POSTGRES_USER=" + user,
                               "--env", "POSTGRES_DB=postgres", image_id, timeout=120)
        if started.returncode:
            if image_loaded and local_docker(args, "image", "rm", image_id, timeout=120).returncode:
                raise BackupError("Isolated PostgreSQL restore could not start and its temporary image remains.")
            raise BackupError("Isolated PostgreSQL restore container could not start.")
        restore_ok = False
        cleanup_ok = False
        try:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                ready = local_docker(args, "exec", container, "pg_isready", "-q", "-U", user, timeout=15)
                if ready.returncode == 0:
                    break
                time.sleep(3)
            else:
                raise BackupError("Isolated PostgreSQL image did not become ready.")
            created = local_docker(args, "exec", container, "createdb", "-U", user, database, timeout=60)
            if created.returncode:
                raise BackupError("Could not create a database for the isolated restore check.")
            restore = subprocess.Popen(["docker", "--host", args.restore_docker_host, "exec", "-i", container,
                                        "pg_restore", "--exit-on-error", "--no-owner", "--no-acl", "-U", user,
                                        "--dbname", database], stdin=subprocess.PIPE,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                with archive.open(dump_member) as source:
                    assert restore.stdin is not None
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        restore.stdin.write(block)
                    restore.stdin.close()
                restore_ok = restore.wait(timeout=RELEASE_TIMEOUT_SECONDS) == 0
            except (BrokenPipeError, subprocess.TimeoutExpired):
                restore.kill()
                restore.wait(timeout=10)
            if not restore_ok:
                raise BackupError("Selected PostgreSQL backup did not restore in the isolated engine.")
            query = local_docker(args, "exec", container, "psql", "-U", user, "-d", database, "-Atc",
                                 "SELECT count(*) FROM pg_catalog.pg_class", timeout=30)
            table_count = query.stdout.decode("utf-8", "replace").strip() if query.stdout else ""
            if query.returncode or not table_count.isdigit() or int(table_count) < 1:
                raise BackupError("Restored PostgreSQL database did not pass its catalog check.")
        finally:
            removed = local_docker(args, "rm", "--force", container, timeout=60)
            cleanup_ok = removed.returncode == 0
            image_cleanup_ok = True
            if image_loaded:
                image_cleanup_ok = local_docker(args, "image", "rm", image_id, timeout=120).returncode == 0
        if not restore_ok:
            raise BackupError("Selected PostgreSQL backup failed isolated restore verification.")
        if not cleanup_ok:
            raise BackupError("Isolated PostgreSQL restore container could not be removed.")
        if not image_cleanup_ok:
            raise BackupError("Isolated PostgreSQL restore image could not be removed.")


def verify_default_minikube_restore(args: argparse.Namespace, archive, manifest: dict) -> None:
    import ipaddress
    import tarfile
    import time

    legacy = manifest.get("legacy_minikube") or {}
    container_inspect_name = "legacy/minikube/container-inspect.json"
    volume_inspect_name = "legacy/minikube/volume-inspect.json"
    network_inspect_name = "legacy/minikube/network-inspect.json"
    volume_tar_name = "legacy/minikube/var-volume.tar"
    image_tar_name = "legacy/minikube/container-image.tar"
    required = (container_inspect_name, volume_inspect_name, network_inspect_name, volume_tar_name,
                image_tar_name, "legacy/minikube/kubeconfig.json")
    if any(name not in archive.namelist() for name in required):
        raise BackupError("Approved default profile snapshot is incomplete; original cluster must remain intact.")

    container_data = json.loads(archive.read(container_inspect_name))
    volume_data = json.loads(archive.read(volume_inspect_name))
    network_data = json.loads(archive.read(network_inspect_name))
    container_config = container_data.get("Config") or {}
    host_config = container_data.get("HostConfig") or {}
    original_id = str(legacy.get("container_id", ""))
    snapshot_image_id = str(legacy.get("container_image_id", ""))
    saved_mounts = container_data.get("Mounts") or []
    original_volume = next((mount for mount in saved_mounts
                            if mount.get("Name") == volume_data.get("Name") == "minikube"
                            and mount.get("Destination") == "/var" and mount.get("Type") == "volume"), None)
    modules_mount = next((mount for mount in saved_mounts if mount.get("Type") == "bind"
                          and mount.get("Source") == "/lib/modules" and mount.get("Destination") == "/lib/modules"
                          and mount.get("RW") is False), None)
    if (len(original_id) != 64 or not snapshot_image_id.startswith("sha256:") or not original_volume
            or not modules_mount or len(saved_mounts) != 2
            or str(container_data.get("Name", "")).lstrip("/") != "minikube"
            or (container_data.get("State") or {}).get("Running") is not False):
        raise BackupError("Default profile archive identity is invalid; original cluster must remain intact.")

    saved_networks = (container_data.get("NetworkSettings") or {}).get("Networks") or {}
    network_name = str(network_data.get("Name") or "")
    if (len(saved_networks) != 1 or network_name not in saved_networks
            or str(host_config.get("NetworkMode") or "") != network_name):
        raise BackupError("Default profile network attachments cannot be recreated exactly; original cluster must remain intact.")
    if modules_mount.get("Propagation") not in (None, "", "rprivate", "rshared", "rslave"):
        raise BackupError("Default profile bind propagation cannot be recreated; original cluster must remain intact.")
    unsupported = []
    for key in ("Devices", "DeviceRequests"):
        if host_config.get(key):
            unsupported.append(key)
    for key in ("PidMode", "IpcMode", "UTSMode", "UsernsMode"):
        if host_config.get(key) not in (None, "", "private"):
            unsupported.append(key)
    if host_config.get("Runtime") not in (None, "", "runc"):
        unsupported.append("Runtime")
    if unsupported:
        raise BackupError("Default profile uses unsupported Docker host settings (" + ", ".join(unsupported)
                          + "); original cluster must remain intact.")
    port_bindings = host_config.get("PortBindings") or {}
    if not has_reviewed_dynamic_loopback_ports(port_bindings):
        raise BackupError("Default profile port publications differ from the reviewed isolated mappings; original cluster must remain intact.")

    with archive.open(volume_tar_name) as member:
        try:
            with tarfile.open(fileobj=member, mode="r|*") as volume_tar:
                first = next(volume_tar, None)
                if first is None:
                    raise BackupError("Default profile volume archive is empty.")
                cleaned = [part for part in first.name.split("/") if part not in {"", "."}]
                strip_components = 1 if first.name in {".", "./"} or cleaned[:1] == ["var"] else 0
        except (tarfile.TarError, OSError) as exc:
            raise BackupError("Default profile volume archive could not be read.") from exc

    tag = secrets.token_hex(4)
    clone_container = "minikube"
    clone_volume = "kubellm-restore-minikube-" + tag
    clone_network = "kubellm-restore-minikube-" + tag
    image_loaded = False
    volume_created = False
    network_created = False
    container_created = False
    with tempfile.TemporaryDirectory(prefix="kubellm-minikube-restore-") as temp_name:
        temp = Path(temp_name)
        os.chmod(temp, 0o700)
        image_tar = temp / "container-image.tar"
        _copy_zip_member(archive, image_tar_name, image_tar)
        before = local_docker(args, "image", "inspect", snapshot_image_id)
        if before.returncode:
            loaded = local_docker(args, "image", "load", "--input", str(image_tar), timeout=RELEASE_TIMEOUT_SECONDS)
            if loaded.returncode:
                raise BackupError("Old default Minikube image could not be restored into the isolated engine.")
            image_loaded = True
            if local_docker(args, "image", "inspect", snapshot_image_id).returncode:
                removed = local_docker(args, "image", "rm", snapshot_image_id, timeout=120)
                if removed.returncode:
                    raise BackupError("Minikube image loading failed and its partial restore image could not be removed.")
                image_loaded = False
                raise BackupError("Old default Minikube image could not be restored into the isolated engine.")
        try:
            created = local_docker(args, "volume", "create", clone_volume)
            if created.returncode:
                raise BackupError("Could not create the isolated Minikube restore volume.")
            volume_created = True

            network_command = ["network", "create", "--driver", str(network_data.get("Driver") or "bridge")]
            ipam = network_data.get("IPAM") or {}
            for entry in ipam.get("Config") or []:
                if entry.get("Subnet"):
                    network_command.extend(["--subnet", str(entry["Subnet"])])
                if entry.get("Gateway"):
                    network_command.extend(["--gateway", str(entry["Gateway"])])
                if entry.get("IPRange"):
                    network_command.extend(["--ip-range", str(entry["IPRange"])])
            for key, value in (network_data.get("Options") or {}).items():
                if not str(key).startswith("--"):
                    network_command.extend(["--opt", f"{key}={value or ''}"])
            for key, value in (network_data.get("Labels") or {}).items():
                network_command.extend(["--label", f"{key}={value}"])
            if network_data.get("Internal"):
                network_command.append("--internal")
            if network_data.get("Attachable"):
                network_command.append("--attachable")
            network_command.append(clone_network)
            created = local_docker(args, *network_command)
            if created.returncode:
                raise BackupError("Could not recreate the default profile's isolated Docker network.")
            network_created = True

            source_ip = str(saved_networks[network_name].get("IPAddress") or "")
            if not source_ip:
                raise BackupError("Default Minikube node IP is missing from its archive.")
            subnets = [entry.get("Subnet") for entry in ipam.get("Config") or [] if entry.get("Subnet")]
            if not subnets or not any(ipaddress.ip_address(source_ip) in ipaddress.ip_network(subnet)
                                      for subnet in subnets):
                raise BackupError("Default Minikube node IP is outside the saved network's subnets.")
            restore_command = ["docker", "--host", args.restore_docker_host, "run", "--rm", "-i",
                               "--volume", clone_volume + ":/restore", "--entrypoint", "sh", snapshot_image_id,
                               "-ec", "tar -xpf - -C /restore --strip-components=" + str(strip_components)]
            restore = subprocess.Popen(restore_command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
            with archive.open(volume_tar_name) as source:
                try:
                    assert restore.stdin is not None
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        restore.stdin.write(block)
                    restore.stdin.close()
                except BrokenPipeError:
                    restore.kill()
            if restore.wait(timeout=RELEASE_TIMEOUT_SECONDS) != 0:
                raise BackupError("Default Minikube node volume did not restore into the isolated engine.")

            module_mount_spec = "type=bind,source=/lib/modules,target=/lib/modules,readonly"
            propagation = modules_mount.get("Propagation")
            if propagation and propagation != "rprivate":
                module_mount_spec += ",bind-propagation=" + str(propagation)
            create_command = ["container", "create", "--name", clone_container, "--hostname",
                              str(container_config.get("Hostname") or "minikube"), "--network", clone_network,
                              "--ip", source_ip, "--volume", clone_volume + ":/var",
                              "--mount", module_mount_spec, "--restart", "no"]
            if host_config.get("Privileged"):
                create_command.append("--privileged")
            if host_config.get("CgroupnsMode"):
                create_command.extend(["--cgroupns", str(host_config["CgroupnsMode"])])
            if host_config.get("ShmSize"):
                create_command.extend(["--shm-size", str(host_config["ShmSize"])])
            if host_config.get("ReadonlyRootfs"):
                create_command.append("--read-only")
            if host_config.get("Init"):
                create_command.append("--init")
            for value in host_config.get("CapAdd") or []:
                create_command.extend(["--cap-add", str(value)])
            for value in host_config.get("CapDrop") or []:
                create_command.extend(["--cap-drop", str(value)])
            for key, value in (host_config.get("Sysctls") or {}).items():
                create_command.extend(["--sysctl", f"{key}={value}"])
            for value in host_config.get("ExtraHosts") or []:
                create_command.extend(["--add-host", str(value)])
            for value in host_config.get("Dns") or []:
                create_command.extend(["--dns", str(value)])
            for value in host_config.get("DnsOptions") or []:
                create_command.extend(["--dns-option", str(value)])
            for value in host_config.get("DnsSearch") or []:
                create_command.extend(["--dns-search", str(value)])
            for path, options in (host_config.get("Tmpfs") or {}).items():
                create_command.extend(["--tmpfs", f"{path}:{options}" if options else str(path)])
            for option in host_config.get("SecurityOpt") or []:
                create_command.extend(["--security-opt", str(option)])
            for key, value in (container_config.get("Labels") or {}).items():
                create_command.extend(["--label", f"{key}={value}"])
            create_command.append(snapshot_image_id)
            created = local_docker(args, *create_command, timeout=120)
            if created.returncode:
                raise BackupError("Could not recreate the old Minikube node in the isolated engine.")
            container_created = True
            started = local_docker(args, "start", clone_container, timeout=120)
            if started.returncode:
                raise BackupError("Restored Minikube node did not start in the isolated engine.")

            deadline = time.monotonic() + 300
            api_ready = False
            api_probe = (
                "curl --fail --silent --show-error --insecure --max-time 5 https://127.0.0.1:8443/readyz "
                "|| curl --fail --silent --show-error --insecure --max-time 5 https://" + source_ip + ":8443/readyz"
            )
            while time.monotonic() < deadline:
                probe = local_docker(args, "exec", clone_container, "sh", "-ec", api_probe,
                                     timeout=15)
                if probe.returncode == 0 and b"ok" in (probe.stdout or b"").lower():
                    api_ready = True
                    break
                time.sleep(5)
            if not api_ready:
                raise BackupError("Restored default Minikube volume did not bring up a healthy Kubernetes API; original cluster must remain intact.")
        finally:
            cleanup_failures = []
            if container_created:
                if local_docker(args, "rm", "--force", clone_container, timeout=120).returncode:
                    cleanup_failures.append("container")
            if volume_created:
                if local_docker(args, "volume", "rm", clone_volume, timeout=120).returncode:
                    cleanup_failures.append("volume")
            if network_created:
                if local_docker(args, "network", "rm", clone_network, timeout=120).returncode:
                    cleanup_failures.append("network")
            if image_loaded:
                if local_docker(args, "image", "rm", snapshot_image_id, timeout=120).returncode:
                    cleanup_failures.append("image")
            if cleanup_failures:
                raise BackupError("Isolated default Minikube restore artifacts could not be fully removed: "
                                  + ", ".join(cleanup_failures) + ".")


def verify_isolated_restore(args: argparse.Namespace, archive, manifest: dict) -> dict[str, str]:
    import sqlite3

    checks = {"sqlite": "not-present"}
    sqlite_dump = "operator/operator.sqlite.sql"
    if sqlite_dump in archive.namelist():
        with archive.open(sqlite_dump) as member:
            sql = member.read().decode("utf-8")
        memory = sqlite3.connect(":memory:")
        try:
            memory.executescript(sql)
            result = memory.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise BackupError("Isolated SQLite restore failed its integrity check.")
        finally:
            memory.close()
        checks["sqlite"] = "passed"

    verify_postgres_restore(args, archive, manifest)
    checks["postgresql"] = "passed"
    if manifest.get("legacy_minikube"):
        verify_default_minikube_restore(args, archive, manifest)
        checks["default_minikube_api_restore"] = "passed"
        checks["default_minikube_host_ports"] = "omitted-from-isolated-clone"
        checks["default_minikube_memory_limits"] = "omitted-from-isolated-clone"
    return checks


def create(args: argparse.Namespace) -> None:
    for executable in ("ssh", "age", "gh", "docker"):
        if not shutil.which(executable):
            raise BackupError(f"Required local tool is unavailable: {executable}")
    public_key = Path(str(args.ssh_key) + ".pub")
    if not args.ssh_key.is_file() or not public_key.is_file():
        raise BackupError("The configured SSH identity or matching public key is unavailable.")
    if args.include_approved_default_minikube != bool(args.expected_default_minikube_container_id):
        raise BackupError("Including the old default profile requires both explicit opt-in and its full container ID.")
    require_isolated_restore_engine(args)
    remote_check_idle(args)
    assert_private_repo(args.repository)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = "lab-backup-" + stamp
    snapshot_requested = False
    try:
        with tempfile.TemporaryDirectory(prefix="kubellm-lab-backup-") as tmp_name:
            tmp = Path(tmp_name)
            os.chmod(tmp, 0o700)
            encrypted = tmp / (tag + ".zip.age")
            with encrypted.open("xb") as ciphertext:
                os.chmod(encrypted, stat.S_IRUSR | stat.S_IWUSR)
                snapshot_requested = True
                ssh = subprocess.Popen(remote_command(args), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL)
                age = subprocess.Popen(["age", "-R", str(public_key), "-o", str(encrypted)], stdin=ssh.stdout,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                assert ssh.stdout is not None
                ssh.stdout.close()
                try:
                    age.wait(timeout=SNAPSHOT_TIMEOUT_SECONDS)
                    ssh.wait(timeout=30)
                except subprocess.TimeoutExpired as exc:
                    ssh.kill(); age.kill()
                    raise BackupError("The snapshot stream timed out; no release was uploaded.") from exc
            if ssh.returncode or age.returncode:
                raise BackupError("Snapshot streaming or age encryption failed; no release was uploaded.")
            parts = split_encrypted_asset(encrypted, tmp, tag)

            notes = (
                "Client-encrypted KubeLLM lab recovery snapshot. The asset was encrypted to the configured "
                "OpenSSH Ed25519 recipient before upload. Keep the matching private identity offline. "
                "The encrypted manifest contains checksums and recovery contents."
            )
            created = run(["gh", "release", "create", tag, *(str(part) for part in parts), "--repo", args.repository,
                           "--title", "Encrypted lab snapshot " + stamp, "--notes", notes, "--draft"],
                          timeout=RELEASE_TIMEOUT_SECONDS)
            if created.returncode:
                raise BackupError("GitHub did not accept the encrypted snapshot release assets.")

            download_dir = tmp / "downloaded"
            download_dir.mkdir(mode=0o700)
            downloaded_parts = []
            for part in parts:
                download = run(["gh", "release", "download", tag, "--repo", args.repository,
                                "--pattern", part.name, "--dir", str(download_dir)], timeout=RELEASE_TIMEOUT_SECONDS)
                if download.returncode:
                    raise BackupError("Release was created, but an asset could not be downloaded for verification.")
                downloaded_parts.append(download_dir / part.name)
            downloaded = tmp / (tag + ".download.zip.age")
            downloaded_digest = concatenate_assets(downloaded_parts, downloaded)
            if downloaded_digest != file_sha256(encrypted):
                raise BackupError("Downloaded release parts differ from the uploaded encrypted snapshot.")
            plain = tmp / (tag + ".zip")
            with plain.open("xb"):
                os.chmod(plain, stat.S_IRUSR | stat.S_IWUSR)
                decrypted = run(["age", "-d", "-i", str(args.ssh_key), "-o", str(plain), str(downloaded)], timeout=RELEASE_TIMEOUT_SECONDS)
            if decrypted.returncode:
                raise BackupError("Release asset failed decryption verification; the temporary plaintext was removed.")
            import zipfile
            try:
                with zipfile.ZipFile(plain, "r") as archive:
                    bad_member = archive.testzip()
                    names = set(archive.namelist())
                    if bad_member or "manifest.json" not in names or "lane/selector.json" not in names:
                        raise BackupError("Downloaded snapshot failed archive integrity checks.")
                    manifest = json.loads(archive.read("manifest.json"))
                    for item in manifest.get("contents", []):
                        digest = archive_member_sha256(archive, item["path"])
                        if digest != item["sha256"]:
                            raise BackupError("Snapshot manifest checksum verification failed.")
                    restore_checks = verify_isolated_restore(args, archive, manifest)
            except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
                raise BackupError("Downloaded snapshot could not be verified.") from exc
            local_copy = retain_encrypted_copy(encrypted, args.local_copy_dir.expanduser(), tag)
            if file_sha256(local_copy) != file_sha256(encrypted):
                local_copy.unlink(missing_ok=True)
                raise BackupError("The retained local encrypted copy failed its hash check.")
            published = run(["gh", "release", "edit", tag, "--repo", args.repository, "--draft=false"],
                            timeout=120)
            if published.returncode:
                raise BackupError("Snapshot verification passed, but the private GitHub release could not be published.")
            print(json.dumps({"repository": args.repository, "release_tag": tag,
                              "encrypted_bytes": encrypted.stat().st_size, "asset_parts": len(parts),
                              "archive_entries": len(names), "decryption": "passed",
                              "integrity": "passed", "restore_checks": restore_checks,
                              "local_encrypted_copy": str(local_copy),
                              "local_plaintext_removed_on_exit": True}, sort_keys=True))
    except Exception:
        if snapshot_requested and args.include_approved_default_minikube:
            remote_ensure_legacy_started(args)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up selected lab state to an encrypted private GitHub Release.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-key", type=Path, default=DEFAULT_SSH_KEY)
    parser.add_argument("--selector", default=DEFAULT_SELECTOR)
    parser.add_argument("--state-dir", default=DEFAULT_STATE)
    parser.add_argument("--repo-dir", default=DEFAULT_REPO)
    parser.add_argument("--repository", default=DEFAULT_GITHUB_REPO)
    parser.add_argument("--local-copy-dir", type=Path, default=DEFAULT_LOCAL_COPY_DIR,
                        help="Owner-only directory for a durable encrypted Mac copy.")
    parser.add_argument("--restore-docker-host", default="unix://" + str(Path.home() / ".colima" / "kubellm-restore" / "docker.sock"),
                        help="Docker socket for the isolated x86_64 Linux restore VM.")
    parser.add_argument("--include-approved-default-minikube", action="store_true",
                        help="Cold-snapshot only the explicitly approved old default Minikube profile.")
    parser.add_argument("--expected-default-minikube-container-id",
                        help="Full immutable container ID previously reviewed for the old default profile.")
    args = parser.parse_args()
    try:
        create(args)
        return 0
    except BackupError as exc:
        print(f"lab-ops-backup: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
