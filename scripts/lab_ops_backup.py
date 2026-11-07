#!/usr/bin/env python3
"""Create and verify a client-encrypted KubeLLM lab snapshot on GitHub.

The snapshot is streamed from the lab through age into a local ciphertext-only
temporary file, uploaded as a private GitHub Release asset, then downloaded,
decrypted in a mode-0600 temporary directory, and checked before success.
"""

from __future__ import annotations

import argparse
import datetime as dt
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
REMOTE_IDLE_CHECK = r'''import pathlib, sqlite3, sys
selector = str(pathlib.Path(sys.argv[1]).expanduser().resolve()).encode()
db_path = pathlib.Path(sys.argv[2]) / "operator.sqlite3"
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
        environment = (proc / "environ").read_bytes().split(b"\0")
    except OSError:
        continue
    if b"debug_assistant_latest/runner.py" in command_line and any(item == b"KUBELLM_LAB_CONFIG=" + selector for item in environment):
        raise SystemExit(2)
'''
REMOTE_DATABASE_IDENTITY_CHECK = r'''import json, subprocess, sys
expected_id, expected_lane = sys.argv[1:3]
result = subprocess.run(["docker", "inspect", expected_id], stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=10, check=False)
if result.returncode:
    raise SystemExit(2)
try:
    item = json.loads(result.stdout)[0]
except (ValueError, IndexError, TypeError):
    raise SystemExit(2)
labels = (item.get("Config") or {}).get("Labels") or {}
if item.get("Id") != expected_id or labels.get("io.kubellm.lane") != expected_lane:
    raise SystemExit(2)
if (item.get("State") or {}).get("Running") is not True:
    raise SystemExit(2)
'''


REMOTE_SNAPSHOT = r'''import datetime, hashlib, json, os, pathlib, sqlite3, stat, subprocess, sys, threading, zipfile

selector = pathlib.Path(sys.argv[1])
state = pathlib.Path(sys.argv[2])
repo = pathlib.Path(sys.argv[3])
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
if not state.is_dir() or not repo.is_dir():
    raise SystemExit("requested state or checkout directory is missing")

manifest = {"schema_version": 1, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "host": __import__("socket").gethostname(), "lane_id": lane["lane_id"],
            "contents": [], "excluded": ["secrets outside the selected lane", "Docker image layers", "Minikube node disk"]}
def ensure_idle():
    db_path = state / "operator.sqlite3"
    if not db_path.is_file():
        return
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
                environment = (proc / "environ").read_bytes().split(b"\0")
            except OSError:
                continue
            selected = any(value == b"KUBELLM_LAB_CONFIG=" + expected for value in environment)
            runner = b"debug_assistant_latest/runner.py" in command_line
            if selected and runner:
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

# Preserve operational state/history, including raw attempt evidence, while
# excluding rebuildable source worktrees and dependency/build caches.
add_tree("operator-state", state, skip_worktrees=True)
local_root = repo / ".local"
if local_root.is_dir() and not local_root.is_symlink():
    for entry in sorted(local_root.iterdir()):
        if entry.resolve() == state.resolve():
            continue
        if entry.is_dir() and not entry.is_symlink():
            add_tree("local-evidence/" + entry.name, entry)
        elif entry.is_file() and not entry.is_symlink():
            with entry.open("rb") as source:
                add_stream("local-evidence/" + entry.name, source, stat.S_IMODE(entry.stat().st_mode))
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
        return subprocess.run(argv, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackupError(f"Could not complete {Path(argv[0]).name}: {type(exc).__name__}") from exc


def remote_command(args: argparse.Namespace) -> list[str]:
    import base64
    import shlex

    code = "import base64;exec(base64.b64decode(" + repr(base64.b64encode(REMOTE_SNAPSHOT.encode()).decode()) + "))"
    remote = "python3 -c " + shlex.quote(code) + " " + " ".join(
        shlex.quote(value) for value in (args.selector, args.state_dir, args.repo_dir)
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


def remote_docker(args: argparse.Namespace, container_id: str, script: str, *, stdin=None, timeout: int = 900) -> int:
    if len(container_id) != 64 or any(char not in "0123456789abcdef" for char in container_id):
        raise BackupError("Snapshot manifest has an invalid selected database container identity.")
    remote = "docker exec -i " + shlex.quote(container_id) + " sh -ec " + shlex.quote(script)
    process = subprocess.Popen([
        "ssh", "-T", "-i", str(args.ssh_key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
        args.host, remote,
    ], stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if stdin is not None:
        try:
            assert process.stdin is not None
            while True:
                block = stdin.read(1024 * 1024)
                if not block:
                    break
                process.stdin.write(block)
        except BrokenPipeError:
            pass
        finally:
            if process.stdin:
                process.stdin.close()
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        raise BackupError("Isolated PostgreSQL restore verification timed out.") from exc


def remote_check_idle(args: argparse.Namespace) -> None:
    import base64

    code = "import base64;exec(base64.b64decode(" + repr(base64.b64encode(REMOTE_IDLE_CHECK.encode()).decode()) + "))"
    remote = "python3 -c " + shlex.quote(code) + " " + shlex.quote(args.selector) + " " + shlex.quote(args.state_dir)
    result = run([
        "ssh", "-T", "-i", str(args.ssh_key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10", args.host, remote,
    ], timeout=20)
    if result.returncode:
        raise BackupError("Could not verify the selected lane is idle for isolated restore verification.")


def remote_check_restore_capacity(args: argparse.Namespace, container_id: str) -> None:
    if len(container_id) != 64 or any(char not in "0123456789abcdef" for char in container_id):
        raise BackupError("Snapshot manifest has an invalid selected database container identity.")
    capacity_check = (
        'set -- $(df -P -B1 "$PGDATA" | tail -n 1); free=$4; '
        'size=$(psql --username="${POSTGRES_USER:-postgres}" --dbname="${POSTGRES_DB:-postgres}" '
        '-Atc "select pg_database_size(current_database())"); '
        'test "$free" -ge "$((size * 2 + 2147483648))"'
    )
    remote = "docker exec " + shlex.quote(container_id) + " sh -ec " + shlex.quote(capacity_check)
    result = run([
        "ssh", "-T", "-i", str(args.ssh_key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10", args.host, remote,
    ], timeout=30)
    if result.returncode:
        raise BackupError("Selected database lacks verified headroom for an isolated restore test; no database was changed.")


def archive_member_sha256(archive, path: str) -> str:
    import hashlib

    digest = hashlib.sha256()
    with archive.open(path) as member:
        while True:
            block = member.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def verify_isolated_restore(args: argparse.Namespace, archive, manifest: dict) -> None:
    import io
    import sqlite3

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

    database_dump = "database/selected-lane.pgcustom"
    if database_dump not in archive.namelist():
        raise BackupError("Snapshot does not contain the selected database export.")
    remote_check_idle(args)
    container = manifest.get("database_container_id", "")
    lane_id = manifest.get("lane_id", "")
    if len(container) != 64 or any(char not in "0123456789abcdef" for char in container):
        raise BackupError("Snapshot manifest is missing the selected database container identity.")
    import base64
    code = "import base64;exec(base64.b64decode(" + repr(base64.b64encode(REMOTE_DATABASE_IDENTITY_CHECK.encode()).decode()) + "))"
    remote = "python3 -c " + shlex.quote(code) + " " + shlex.quote(container) + " " + shlex.quote(lane_id)
    identity = run([
        "ssh", "-T", "-i", str(args.ssh_key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10", args.host, remote,
    ], timeout=20)
    if identity.returncode:
        raise BackupError("The selected database container identity changed; restore verification stopped.")
    remote_check_restore_capacity(args, container)
    database = "kubellm_backup_verify_" + secrets.token_hex(4)
    create = f'createdb --maintenance-db=postgres --username="${{POSTGRES_USER:-postgres}}" {database}'
    if remote_docker(args, container, create, timeout=60):
        raise BackupError("Could not create an isolated database for restore verification.")
    restore_ok = False
    drop_ok = False
    try:
        restore = f'pg_restore --exit-on-error --no-owner --no-acl --username="${{POSTGRES_USER:-postgres}}" --dbname={database}'
        with archive.open(database_dump) as member:
            restore_ok = remote_docker(args, container, restore, stdin=member, timeout=1800) == 0
    finally:
        cleanup = f'dropdb --if-exists --maintenance-db=postgres --username="${{POSTGRES_USER:-postgres}}" {database}'
        drop_ok = remote_docker(args, container, cleanup, timeout=120) == 0
    if not restore_ok:
        raise BackupError("Selected database dump could not be restored into an isolated database.")
    if not drop_ok:
        raise BackupError(f"Restore verification passed, but temporary database {database} could not be removed.")


def create(args: argparse.Namespace) -> None:
    for executable in ("ssh", "age", "gh"):
        if not shutil.which(executable):
            raise BackupError(f"Required local tool is unavailable: {executable}")
    public_key = Path(str(args.ssh_key) + ".pub")
    if not args.ssh_key.is_file() or not public_key.is_file():
        raise BackupError("The configured SSH identity or matching public key is unavailable.")
    assert_private_repo(args.repository)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = "lab-backup-" + stamp
    with tempfile.TemporaryDirectory(prefix="kubellm-lab-backup-") as tmp_name:
        tmp = Path(tmp_name)
        os.chmod(tmp, 0o700)
        encrypted = tmp / (tag + ".zip.age")
        with encrypted.open("xb") as ciphertext:
            os.chmod(encrypted, stat.S_IRUSR | stat.S_IWUSR)
            ssh = subprocess.Popen(remote_command(args), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)
            age = subprocess.Popen(["age", "-R", str(public_key), "-o", str(encrypted)], stdin=ssh.stdout,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            assert ssh.stdout is not None
            ssh.stdout.close()
            try:
                age_error = age.communicate(timeout=1800)[1]
                ssh.wait(timeout=30)
            except subprocess.TimeoutExpired as exc:
                ssh.kill(); age.kill()
                raise BackupError("The snapshot stream timed out; no release was uploaded.") from exc
        if ssh.returncode or age.returncode:
            encrypted.unlink(missing_ok=True)
            # Remote errors are deliberately represented only by a generic status.
            raise BackupError("Snapshot streaming or age encryption failed; no release was uploaded.")
        if encrypted.stat().st_size > MAX_ASSET_BYTES:
            raise BackupError("Encrypted snapshot exceeds GitHub's per-asset limit; no release was uploaded.")

        notes = (
            "Client-encrypted KubeLLM lab recovery snapshot. The asset was encrypted to the configured "
            "OpenSSH Ed25519 recipient before upload. Keep the matching private identity offline. "
            "The encrypted manifest contains checksums and recovery contents."
        )
        created = run(["gh", "release", "create", tag, str(encrypted), "--repo", args.repository,
                       "--title", "Encrypted lab snapshot " + stamp, "--notes", notes], timeout=1800)
        if created.returncode:
            raise BackupError("GitHub did not accept the encrypted snapshot release asset.")

        downloaded = tmp / (tag + ".download.age")
        download = run(["gh", "release", "download", tag, "--repo", args.repository,
                        "--pattern", tag + ".zip.age", "--dir", str(tmp)], timeout=1800)
        if download.returncode:
            raise BackupError("Release was created, but its asset could not be downloaded for verification.")
        downloaded = tmp / (tag + ".zip.age")
        plain = tmp / (tag + ".zip")
        with plain.open("xb"):
            os.chmod(plain, stat.S_IRUSR | stat.S_IWUSR)
            decrypted = run(["age", "-d", "-i", str(args.ssh_key), "-o", str(plain), str(downloaded)], timeout=1800)
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
                verify_isolated_restore(args, archive, manifest)
        except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
            raise BackupError("Downloaded snapshot could not be verified.") from exc
        print(json.dumps({"repository": args.repository, "release_tag": tag,
                          "asset_bytes": encrypted.stat().st_size,
                          "archive_entries": len(names), "decryption": "passed",
                          "integrity": "passed", "isolated_restore": "passed",
                          "local_plaintext_removed_on_exit": True}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up selected lab state to an encrypted private GitHub Release.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-key", type=Path, default=DEFAULT_SSH_KEY)
    parser.add_argument("--selector", default=DEFAULT_SELECTOR)
    parser.add_argument("--state-dir", default=DEFAULT_STATE)
    parser.add_argument("--repo-dir", default=DEFAULT_REPO)
    parser.add_argument("--repository", default=DEFAULT_GITHUB_REPO)
    args = parser.parse_args()
    try:
        create(args)
        return 0
    except BackupError as exc:
        print(f"lab-ops-backup: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
