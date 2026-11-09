#!/usr/bin/env python3
"""Lab-native encrypted backup, isolated restore, and narrowly scoped cleanup."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

try:
    from .lab_ops_github import (
        GitHubReleaseError, chunk_manifest, chunks_from_release, download_assets,
        ensure_private_repository, find_release_by_tag, get_or_create_draft, publish_draft,
        read_scoped_token, release_by_id, upload_missing_chunks, validate_existing_assets,
    )
except ImportError:
    from lab_ops_github import (
        GitHubReleaseError, chunk_manifest, chunks_from_release, download_assets,
        ensure_private_repository, find_release_by_tag, get_or_create_draft, publish_draft,
        read_scoped_token, release_by_id, upload_missing_chunks, validate_existing_assets,
    )


IMAGE_ID = "sha256:8a960fe6f37ce18c936f81f5f1e6306d916fb7828f45a846b6d46a222b0b081b"
IMAGE_DIGEST = "ghcr.io/openclaw/openclaw@sha256:d65cc3d5fd0c8b1f752c2f70377843230112250c10e99c3b61769234c217c5db"
AGE_VERSION = "1.3.2"
AGE_SHA256 = "cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10"
UBUNTU_RELEASE = "20261106"
UBUNTU_IMAGE_SHA256 = "f77bc6d59cb8deaa9657095736b5f5003f7705b47055f01823459715c967de6a"
UBUNTU_SIGNING_KEY = "D2EB44626FDDC30B513D5BB71A5D6C4C7DB87C81"
UBUNTU_URL = f"https://cloud-images.ubuntu.com/releases/jammy/release-{UBUNTU_RELEASE}"
OWNER = "minh-mhl-le"
REPOSITORY = "kubellm-lab-backups"
TOKEN_PATH = Path.home() / ".config/kubellm/lab-ops/github.token"
STATUS_DIR = Path.home() / "KubeLLM/.local/lab-ops/jobs"
MAX_STAGING = 28 * 1024**3
GUEST_MEMORY_MIB = 32 * 1024
GUEST_DISK_GIB = 48
TRACKED_CONTAINER = None
LAST_CONTAINER_MEMORY_CHECK = 0.0


def job_root(job_id: str) -> Path:
    return Path("/dev/shm") / ("kubellm-" + job_id)


class JobError(RuntimeError):
    pass


def run(argv, *, timeout=60, stdin=None, stdout=None, env=None):
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL if stdin is None else stdin,
                              stdout=subprocess.PIPE if stdout is None else stdout,
                              stderr=subprocess.DEVNULL, timeout=timeout, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise JobError(f"{Path(argv[0]).name} did not complete ({type(exc).__name__}).") from None


def write_json(path: Path, value: dict):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        os.chmod(temporary, 0o600)
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def status(status_path: Path, job_id: str, phase: str, detail: str, **fields):
    write_json(status_path, {"job_id": job_id, "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                             "phase": phase, "detail": detail[:500], **fields})


def safe_failure_detail(exc: Exception, last_phase: object) -> str:
    if isinstance(exc, (JobError, GitHubReleaseError)):
        return str(exc)
    phase = last_phase if isinstance(last_phase, str) and re.fullmatch(r"[a-z-]{1,40}", last_phase) else "unknown"
    return f"Unexpected {type(exc).__name__} during {phase}; sensitive RAM staging was removed."


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_capacity(work: Path, *, check_container_memory=True, force_container_memory=False):
    global LAST_CONTAINER_MEMORY_CHECK
    usage = run(["du", "-s", "-B1", str(work)], timeout=30)
    if usage.returncode:
        raise JobError("Could not verify RAM-backed staging usage.")
    try:
        size = int(usage.stdout.split()[0])
    except (ValueError, IndexError):
        raise JobError("Could not parse RAM-backed staging usage.") from None
    if size > MAX_STAGING:
        raise JobError("RAM-backed staging exceeded the 28 GiB limit; the job stopped safely.")
    available = next((int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines()
                      if line.startswith("MemAvailable:")), 0)
    if available < 8 * 1024**3:
        raise JobError("Lab memory headroom fell below 8 GiB; the job stopped safely.")
    if (check_container_memory and TRACKED_CONTAINER
            and (force_container_memory or time.monotonic() - LAST_CONTAINER_MEMORY_CHECK >= 30)):
        LAST_CONTAINER_MEMORY_CHECK = time.monotonic()
        stats = run(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", TRACKED_CONTAINER],
                    timeout=20)
        if stats.returncode == 0:
            match = re.match(r"([0-9.]+)\s*([KMGT]?i?B)", stats.stdout.decode("ascii", "ignore").strip())
            if match:
                amount, unit = float(match.group(1)), match.group(2)
                scale = {"B": 1, "kB": 1000, "MB": 1000**2, "GB": 1000**3, "TB": 1000**4,
                         "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}
                if amount * scale[unit] > 2 * 1024**3:
                    raise JobError("The existing Minikube profile exceeded its 2 GiB active-memory guard.")
    return size


def check_tools():
    needed = ("curl", "zstd", "tar", "qemu-system-x86_64", "qemu-img", "genisoimage", "gpg", "gpgv",
              "ssh", "ssh-keygen", "docker", "kubectl", "python3")
    absent = [item for item in needed if not shutil.which(item)]
    if absent:
        raise JobError("Lab is missing required user-level tools: " + ", ".join(absent) + ".")
    if not os.access("/dev/shm", os.W_OK) or shutil.disk_usage("/dev/shm").free < 40 * 1024**3:
        raise JobError("At least 40 GiB of free writable /dev/shm storage is required.")
    available = next((int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines()
                      if line.startswith("MemAvailable:")), 0)
    if available < 64 * 1024**3:
        raise JobError("At least 64 GiB of host memory must be available before starting.")


def check_args(args):
    if not re.fullmatch(r"job-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}", args.job_id):
        raise JobError("The lab backup job identifier is invalid.")
    if not re.fullmatch(r"lab-backup-[0-9]{8}T[0-9]{6}Z", args.release_tag):
        raise JobError("The backup release tag is invalid.")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.minikube_id):
        raise JobError("The reviewed Minikube ID must be the full immutable Docker ID.")
    if not re.fullmatch(r"age1[0-9a-z]{58}", args.age_recipient):
        raise JobError("The dedicated recovery age recipient is invalid.")
    selector = Path(args.selector).expanduser()
    state, repo = Path(args.state_dir).expanduser(), Path(args.repo_dir).expanduser()
    if selector.is_symlink() or not selector.is_file() or stat.S_IMODE(selector.stat().st_mode) & 0o077:
        raise JobError("The selected private lane selector is missing or not owner-only.")
    if not state.is_dir() or not repo.is_dir():
        raise JobError("The selected lane state or canonical checkout is missing.")
    if not Path("/dev/shm").is_dir() or not os.access("/dev/shm", os.W_OK):
        raise JobError("The lab has no writable RAM-backed /dev/shm filesystem.")


def check_minikube(args):
    expected = args.minikube_id.removeprefix("sha256:")
    inspected = run(["docker", "inspect", expected], timeout=20)
    if inspected.returncode:
        raise JobError("The reviewed default Minikube container is unavailable.")
    try:
        item = json.loads(inspected.stdout)[0]
    except (ValueError, IndexError, TypeError):
        raise JobError("The reviewed default Minikube container identity is invalid.") from None
    labels = (item.get("Config") or {}).get("Labels") or {}
    host = item.get("HostConfig") or {}
    mounts = item.get("Mounts") or []
    nets = (item.get("NetworkSettings") or {}).get("Networks") or {}
    if (item.get("Id") != expected or str(item.get("Name", "")).lstrip("/") != "minikube"
            or labels.get("name.minikube.sigs.k8s.io") != "minikube"
            or (item.get("State") or {}).get("Running") is not True
            or host.get("Memory") != 32 * 1024**3 or len(nets) != 1
            or not any(m.get("Name") == "minikube" and m.get("Destination") == "/var" and m.get("Type") == "volume"
                       for m in mounts)):
        raise JobError("The reviewed Minikube identity, volume, network, running state, or 32 GiB limit changed.")
    users = run(["docker", "ps", "-a", "--filter", "volume=minikube", "--no-trunc", "--format", "{{.ID}}"])
    if users.returncode or {x.strip() for x in users.stdout.decode().splitlines() if x.strip()} != {expected}:
        raise JobError("The reviewed Minikube volume has an unexpected container reference.")
    network_name = str(host.get("NetworkMode") or "minikube")
    network_out = run(["docker", "network", "inspect", network_name], timeout=20)
    if network_out.returncode:
        raise JobError("The reviewed Minikube network is unavailable.")
    network = json.loads(network_out.stdout)[0]
    attached = {str(x).removeprefix("sha256:") for x in (network.get("Containers") or {})}
    if attached != {expected}:
        raise JobError("The reviewed Minikube network has an unexpected container attachment.")


def check_openclaw():
    inspected = run(["docker", "image", "inspect", IMAGE_ID], timeout=20)
    if inspected.returncode:
        raise JobError("The previously reviewed OpenClaw image is no longer present.")
    item = json.loads(inspected.stdout)[0]
    if item.get("Id") != IMAGE_ID or IMAGE_DIGEST not in (item.get("RepoDigests") or []):
        raise JobError("The reviewed OpenClaw image ID or immutable registry digest changed.")
    refs = run(["docker", "ps", "-a", "--filter", "ancestor=" + IMAGE_ID, "--no-trunc", "--format", "{{.ID}}"])
    if refs.returncode or refs.stdout.strip():
        raise JobError("A container now references the reviewed OpenClaw image; cleanup is blocked.")


def verify_pulled_digest(value: str) -> str:
    try:
        repo_digests = json.loads(value)
    except (TypeError, ValueError):
        raise JobError("The fresh restore VM returned invalid OpenClaw digest metadata.") from None
    if not isinstance(repo_digests, list) or IMAGE_DIGEST not in repo_digests:
        raise JobError("The fresh restore VM did not retain the exact pinned OpenClaw registry digest.")
    return IMAGE_DIGEST


def download(url: str, path: Path, expected: str | None, work: Path):
    if path.exists() or path.is_symlink():
        raise JobError("A pinned bootstrap artifact already exists in this RAM-backed job.")
    result = run(["curl", "--fail", "--location", "--silent", "--show-error", "--retry", "2",
                  "--connect-timeout", "10", "--max-time", "900", "--output", str(path), url], timeout=930)
    if result.returncode or not path.is_file() or (expected and sha256_file(path) != expected):
        path.unlink(missing_ok=True)
        raise JobError("A pinned bootstrap artifact failed its download or SHA-256 check.")
    assert_capacity(work)


def create_seed(work: Path, public_key: str, instance: str):
    seed = work / ("seed-" + instance)
    seed.mkdir(mode=0o700)
    user_data = ("#cloud-config\nusers:\n  - default\n  - name: ubuntu\n"
                 "    groups: [adm, sudo]\n    sudo: ALL=(ALL) NOPASSWD:ALL\n"
                 "    shell: /bin/bash\n    lock_passwd: true\n    ssh_authorized_keys:\n"
                 "      - " + json.dumps(public_key) + "\npackage_update: true\npackages:\n  - docker.io\n"
                 "runcmd:\n  - [usermod, -aG, docker, ubuntu]\n  - [systemctl, enable, --now, docker]\n")
    (seed / "user-data").write_text(user_data, encoding="utf-8")
    (seed / "meta-data").write_text("instance-id: " + instance + "\nlocal-hostname: kubellm-restore\n", encoding="ascii")
    os.chmod(seed / "user-data", 0o600)
    os.chmod(seed / "meta-data", 0o600)
    iso = work / (instance + ".iso")
    made = run(["genisoimage", "-quiet", "-output", str(iso), "-volid", "cidata", "-joliet", "-rock",
                "-graft-points", "user-data=" + str(seed / "user-data"), "meta-data=" + str(seed / "meta-data")], timeout=30)
    if made.returncode:
        raise JobError("The local NoCloud restore seed could not be created.")
    os.chmod(iso, 0o600)
    return iso


def find_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RestoreVM:
    def __init__(self, work: Path):
        self.work = work
        self.disk = work / "restore.qcow2"
        self.guest_key = work / "guest-ed25519"
        self.port = None
        self.docker_env = os.environ.copy()

    def argv(self, seed: Path | None, restricted: bool):
        self.port = find_port()
        net = f"user,id=net0,{'restrict=on,' if restricted else ''}hostfwd=tcp:127.0.0.1:{self.port}-:22"
        argv = ["qemu-system-x86_64", "-name", "kubellm-lab-restore", "-accel", "tcg,thread=multi",
                "-cpu", "max", "-smp", "4", "-m", str(GUEST_MEMORY_MIB), "-drive",
                f"file={self.disk},if=virtio,format=qcow2"]
        if seed:
            argv += ["-drive", f"file={seed},media=cdrom,readonly=on"]
        return argv + ["-netdev", net, "-device", "virtio-net-pci,netdev=net0", "-display", "none",
                       "-monitor", "none", "-serial", "file:" + str(self.work / "qemu-serial.log"),
                       "-daemonize", "-pidfile", str(self.work / "qemu.pid")]

    def ssh(self, command: str, timeout=60, check=True):
        argv = ["ssh", "-F", "/dev/null", "-p", str(self.port), "-i", str(self.guest_key),
                "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=5",
                "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=2", "ubuntu@127.0.0.1", command]
        result = run(argv, timeout=timeout)
        if check and result.returncode:
            raise JobError("A bounded restore-VM SSH command failed.")
        return result

    def start(self, seed: Path | None, restricted: bool):
        started = run(self.argv(seed, restricted), timeout=60)
        if started.returncode:
            raise JobError("The software-emulated restore VM could not start.")
        deadline = time.monotonic() + 60 * 60
        while time.monotonic() < deadline:
            try:
                reachable = self.ssh("true", timeout=20, check=False).returncode == 0
            except JobError as exc:
                if "TimeoutExpired" not in str(exc):
                    raise
                reachable = False
            if reachable:
                break
            pid = self.pid()
            if not pid or not Path(f"/proc/{pid}").exists():
                raise JobError("The restore VM exited during boot.")
            assert_capacity(self.work)
            time.sleep(5)
        else:
            raise JobError("The restore VM did not become reachable over its loopback SSH forward.")
        wrapper_dir = self.work / "bin"
        wrapper_dir.mkdir(mode=0o700, exist_ok=True)
        config = self.work / "ssh-config"
        config.write_text(
            "Host 127.0.0.1\n  User ubuntu\n  Port " + str(self.port) +
            "\n  IdentityFile " + str(self.guest_key) +
            "\n  IdentitiesOnly yes\n  StrictHostKeyChecking no\n  UserKnownHostsFile /dev/null\n  LogLevel ERROR\n",
            encoding="ascii")
        os.chmod(config, 0o600)
        wrapper = wrapper_dir / "ssh"
        wrapper.write_text("#!/bin/sh\nexec /usr/bin/ssh -F " + shlex.quote(str(config)) + " \"$@\"\n",
                           encoding="ascii")
        os.chmod(wrapper, 0o700)
        self.docker_env["PATH"] = str(wrapper_dir) + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin")
        self.wait_for_docker()

    def wait_for_docker(self):
        deadline = time.monotonic() + 10 * 60
        while time.monotonic() < deadline:
            try:
                result = self.docker(["info", "--format", "{{.OSType}} {{.Architecture}}"], timeout=20, check=False)
            except JobError as exc:
                if "TimeoutExpired" not in str(exc):
                    raise
                result = None
            if result is not None and result.returncode == 0 and result.stdout.decode().strip() == "linux x86_64":
                return
            pid = self.pid()
            if not pid or not Path(f"/proc/{pid}").exists():
                raise JobError("The restore VM exited before Docker became ready.")
            assert_capacity(self.work)
            time.sleep(4)
        raise JobError("Docker did not become ready inside the isolated restore VM.")

    def docker(self, argv, timeout=60, check=True):
        target = f"ssh://ubuntu@127.0.0.1:{self.port}"
        result = run(["docker", "--host", target, *argv], timeout=timeout, env=self.docker_env)
        if check and result.returncode:
            raise JobError("An isolated restore-VM Docker operation failed.")
        return result

    def shutdown(self):
        pid = self.pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            end = time.monotonic() + 30
            while time.monotonic() < end and Path(f"/proc/{pid}").exists():
                time.sleep(0.2)
            if Path(f"/proc/{pid}").exists():
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        (self.work / "qemu.pid").unlink(missing_ok=True)

    def pid(self):
        try:
            return int((self.work / "qemu.pid").read_text().strip())
        except (OSError, ValueError):
            return None


def verify_guest_egress_blocked(vm: RestoreVM):
    if vm.ssh("python3 -c 'import sys; print(sys.version_info.major)'", timeout=15, check=False).returncode:
        raise JobError("The restricted restore VM does not have its expected Python runtime.")
    for address, port in (("1.1.1.1", 443), ("10.0.2.2", 22)):
        code = "import socket; socket.create_connection((" + repr(address) + "," + str(port) + "),3).close()"
        probe = vm.ssh("python3 -c " + shlex.quote(code), timeout=10, check=False)
        if probe.returncode == 0:
            raise JobError("QEMU restricted networking allowed guest egress or host access; the recovery key was not staged.")


def prepare_vm(args, work: Path, status_path: Path):
    key = work / "guest-ed25519"
    generated = run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "kubellm-restore-" + args.job_id,
                     "-f", str(key)], timeout=20)
    if generated.returncode:
        raise JobError("The temporary restore-VM SSH identity could not be generated.")
    os.chmod(key, 0o600)
    image = work / "ubuntu-22.04-cloud.img"
    sums, signature = work / "SHA256SUMS", work / "SHA256SUMS.gpg"
    download(UBUNTU_URL + "/ubuntu-22.04-server-cloudimg-amd64.img", image, UBUNTU_IMAGE_SHA256, work)
    for url, dest in ((UBUNTU_URL + "/SHA256SUMS", sums), (UBUNTU_URL + "/SHA256SUMS.gpg", signature)):
        download(url, dest, None, work)
    keyring = Path("/usr/share/keyrings/ubuntu-cloudimage-keyring.gpg")
    if keyring.is_symlink() or not keyring.is_file():
        raise JobError("Canonical's installed Ubuntu cloud-image keyring is unavailable.")
    keys = run(["gpg", "--batch", "--no-default-keyring", "--keyring", str(keyring), "--with-colons",
                "--fingerprint"], timeout=30)
    fprs = {line.split(":")[9].upper() for line in keys.stdout.decode(errors="replace").splitlines()
            if line.startswith("fpr:") and len(line.split(":")) > 9}
    if keys.returncode or UBUNTU_SIGNING_KEY not in fprs:
        raise JobError("Canonical's cloud-image signing key did not match the pinned fingerprint.")
    signed = run(["gpgv", "--keyring", str(keyring), str(signature), str(sums)], timeout=30)
    if signed.returncode:
        raise JobError("Canonical's dated Ubuntu checksum signature is invalid.")
    signed_lines = [line.split() for line in sums.read_text(encoding="ascii").splitlines()]
    if not any(len(fields) >= 2 and fields[0] == UBUNTU_IMAGE_SHA256
               and fields[-1].lstrip("*") == "ubuntu-22.04-server-cloudimg-amd64.img" for fields in signed_lines):
        raise JobError("The signed Ubuntu checksum manifest differs from the pinned cloud image.")
    disk = work / "restore.qcow2"
    made = run(["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", str(image), str(disk),
                f"{GUEST_DISK_GIB}G"], timeout=60)
    if made.returncode:
        raise JobError("The RAM-backed restore VM disk could not be created.")
    os.chmod(disk, 0o600)
    public_key = key.with_suffix(".pub").read_text(encoding="ascii").strip()
    seed = create_seed(work, public_key, "kubellm-bootstrap-" + args.job_id)
    vm = RestoreVM(work)
    try:
        status(status_path, args.job_id, "vm-bootstrap", "Installing Docker and checking the approved digest before secrets.")
        vm.start(seed, restricted=False)
        pulled = vm.docker(["pull", IMAGE_DIGEST], timeout=30 * 60, check=False)
        if pulled.returncode:
            raise JobError("The approved OpenClaw image digest could not be pulled in a fresh restore VM.")
        # Docker image stores differ on .Id semantics; the immutable pull and retained digest ref are the proof.
        inspected = vm.docker(["image", "inspect", "--format", "{{json .RepoDigests}}", IMAGE_DIGEST])
        verified_digest = verify_pulled_digest(inspected.stdout.decode(errors="replace"))
        (work / "openclaw-verified-digest.txt").write_text(verified_digest + "\n", encoding="ascii")
        # The clean pull proved registry reachability; release those temporary guest-disk blocks
        # so the later restore fits the RAM-backed staging cap.
        vm.docker(["image", "rm", IMAGE_DIGEST], timeout=120)
        if vm.docker(["image", "inspect", IMAGE_DIGEST], timeout=30, check=False).returncode == 0:
            raise JobError("The verified temporary OpenClaw image could not be cleared from the restore VM.")
        vm.ssh("sudo -n poweroff", timeout=60, check=False)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and (vm.pid() and Path(f"/proc/{vm.pid()}").exists()):
            time.sleep(0.5)
        vm.shutdown()
        config = vars(args).copy()
        write_json(work / "job.json", config)
        status(status_path, args.job_id, "awaiting-recovery-key",
               "VM bootstrap and immutable image pull passed; guest is shut down. Resume locks egress before key transfer.",
               release_tag=args.release_tag, openclaw_verified_digest=verified_digest)
    except Exception:
        vm.shutdown()
        raise


def add_job_parser(parser):
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--selector", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--repo-dir", required=True)
    parser.add_argument("--minikube-id", required=True)
    parser.add_argument("--age-recipient", required=True)


def prepare_job(args):
    global TRACKED_CONTAINER
    check_args(args)
    check_tools()
    check_minikube(args)
    TRACKED_CONTAINER = args.minikube_id.removeprefix("sha256:")
    check_openclaw()
    STATUS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    for record_path in STATUS_DIR.glob("job-*.json"):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("phase") in {"awaiting-recovery-key", "vm-bootstrap", "snapshot", "isolated-restore"}:
            prepared = job_root(str(record.get("job_id", ""))) / "data"
            if prepared.is_dir():
                raise JobError("Another prepared backup job must be resumed or cleaned up first.")
    work = job_root(args.job_id) / "data"
    if work.exists() or work.is_symlink():
        raise JobError("A RAM-backed directory already uses this job ID.")
    work.mkdir(mode=0o700)
    lock_path = STATUS_DIR / "active.lock"
    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        os.chmod(lock_path, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            shutil.rmtree(work, ignore_errors=True)
            raise JobError("Another lab backup or restore job is active.") from None
        try:
            prepare_vm(args, work, STATUS_DIR / (args.job_id + ".json"))
        except Exception:
            shutil.rmtree(work, ignore_errors=True)
            raise


def verify_archive(path: Path, lane_id: str):
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise JobError("The backup archive failed CRC validation.")
            names = archive.namelist()
            if (len(names) != len(set(names)) or names.count("manifest.json") != 1
                    or "lane/selector.json" not in names):
                raise JobError("The backup archive is missing its manifest or selected lane selector.")
            manifest = json.loads(archive.read("manifest.json"))
            if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
                    or manifest.get("lane_id") != lane_id or not manifest.get("legacy_minikube")):
                raise JobError("The backup manifest does not match the selected lane and approved profile.")
            declared = manifest.get("contents")
            if not isinstance(declared, list):
                raise JobError("The backup manifest has no checksum inventory.")
            seen = set()
            for item in declared:
                if (not isinstance(item, dict) or not isinstance(item.get("path"), str)
                        or item["path"] in seen or item["path"] not in names
                        or item["path"] == "manifest.json" or ".." in Path(item["path"]).parts
                        or Path(item["path"]).is_absolute()
                        or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", "")))):
                    raise JobError("The backup manifest checksum inventory is invalid.")
                seen.add(item["path"])
                digest = hashlib.sha256()
                with archive.open(item["path"]) as member:
                    for block in iter(lambda: member.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != item["sha256"]:
                    raise JobError("A backup member failed its manifest checksum.")
            if seen != set(names) - {"manifest.json"}:
                raise JobError("The backup archive contains members outside its checksum inventory.")
            return manifest, len(names)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, EOFError):
        raise JobError("The decrypted lab backup archive is invalid.") from None


def decompress_snapshot(compressed_path: Path, archive_path: Path, work: Path,
                        status_path: Path, job_id: str, release_tag: str) -> int:
    """Decompress zstd to RAM while enforcing staging and host-memory limits."""
    if (compressed_path.is_symlink() or not compressed_path.is_file()
            or archive_path.exists() or archive_path.is_symlink()):
        raise JobError("The decrypted compressed snapshot paths are invalid or already exist.")
    initial_usage = assert_capacity(work, check_container_memory=False)
    remaining_capacity = MAX_STAGING - initial_usage
    if remaining_capacity <= 0:
        raise JobError("No RAM-backed staging capacity remains for snapshot decompression.")
    process = subprocess.Popen(["zstd", "-d", "-c", str(compressed_path)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    written = 0
    next_capacity_check = 64 * 1024**2
    next_status = 1024**3
    try:
        with archive_path.open("xb") as output:
            os.chmod(archive_path, 0o600)
            assert process.stdout is not None
            while True:
                block = process.stdout.read(1024 * 1024)
                if not block:
                    break
                if written + len(block) > remaining_capacity:
                    raise JobError("The decompressed snapshot would exceed the 28 GiB RAM staging limit.")
                output.write(block)
                written += len(block)
                if written >= next_capacity_check:
                    assert_capacity(work, check_container_memory=False)
                    next_capacity_check = written + 64 * 1024**2
                if written >= next_status:
                    status(status_path, job_id, "snapshot-decompress",
                           "Decompressing the downloaded snapshot within the RAM staging limit.",
                           release_tag=release_tag, decompressed_bytes=written)
                    next_status = written + 1024**3
            output.flush()
            os.fsync(output.fileno())
        if process.wait(timeout=60) != 0:
            raise JobError("The age-decrypted snapshot is not a valid zstd stream.")
        assert_capacity(work, check_container_memory=False)
    except BaseException:
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pass
        archive_path.unlink(missing_ok=True)
        raise
    return written


def start_snapshot(args, work: Path, status_path: Path):
    status(status_path, args.job_id, "snapshot-source", "Preparing the selected-lane archive stream.",
           release_tag=args.release_tag)
    # The cold snapshot deliberately stops the exact Minikube container. Check its
    # memory limit once before that operation, then avoid competing docker-stats
    # requests while the daemon is stopping and archiving the container.
    assert_capacity(work, force_container_memory=True)
    source = Path(__file__).with_name("lab_ops_backup.py").read_text(encoding="utf-8")
    marker = "REMOTE_SNAPSHOT = r'''"
    start = source.index(marker) + len(marker)
    end = source.index("'''", start)
    snapshot_source = source[start:end].encode()
    code = "import base64;exec(base64.b64decode(" + repr(base64.b64encode(snapshot_source).decode()) + "))"
    archive = work / "snapshot.zip.zst.age"
    age = work / "age" / "age"
    status(status_path, args.job_id, "snapshot-python-start", "Starting the selected-lane snapshot stream.",
           release_tag=args.release_tag)
    snapshot = subprocess.Popen([sys.executable, "-c", code, args.selector, args.state_dir, args.repo_dir,
                                 args.minikube_id.removeprefix("sha256:")],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                start_new_session=True)
    status(status_path, args.job_id, "snapshot-zstd-start", "Starting RAM-stream compression.",
           release_tag=args.release_tag)
    compressed = subprocess.Popen(["zstd", "-T2", "-3", "-c"], stdin=snapshot.stdout, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, start_new_session=True)
    snapshot.stdout.close()
    status(status_path, args.job_id, "snapshot-age-start", "Starting age encryption for the snapshot stream.",
           release_tag=args.release_tag)
    encrypted = subprocess.Popen([str(age), "-R", str(work / "recipient.txt"), "-o", str(archive)],
                                 stdin=compressed.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
    compressed.stdout.close()
    status(status_path, args.job_id, "snapshot", "Streaming and compressing the cold profile snapshot into age ciphertext.",
           release_tag=args.release_tag)
    try:
        deadline = time.monotonic() + 6 * 60 * 60
        last_report = 0.0
        while time.monotonic() < deadline:
            if all(proc.poll() is not None for proc in (snapshot, compressed, encrypted)):
                break
            assert_capacity(work, check_container_memory=False)
            if time.monotonic() - last_report >= 30:
                last_report = time.monotonic()
                status(status_path, args.job_id, "snapshot",
                       "Streaming and compressing the cold profile snapshot directly into age ciphertext.",
                       encrypted_bytes=archive.stat().st_size if archive.exists() else 0,
                       staging_bytes=int(run(["du", "-s", "-B1", str(work)]).stdout.split()[0]))
            time.sleep(3)
        else:
            raise JobError("The selected-lane snapshot exceeded its six-hour safety limit.")
    except BaseException:
        for proc in (snapshot, compressed, encrypted):
            if proc.poll() is None:
                proc.kill()
        for proc in (snapshot, compressed, encrypted):
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
        raise
    if any(proc.returncode != 0 for proc in (snapshot, compressed, encrypted)):
        raise JobError("Snapshot, compression, or age encryption failed.")
    if not archive.is_file() or archive.stat().st_size == 0:
        raise JobError("The encrypted lab snapshot is empty.")
    os.chmod(archive, 0o600)
    assert_capacity(work, check_container_memory=False)
    return archive


def install_age(work: Path):
    archive = work / "age-v1.3.2-linux-amd64.tar.gz"
    download("https://github.com/FiloSottile/age/releases/download/v1.3.2/age-v1.3.2-linux-amd64.tar.gz",
             archive, AGE_SHA256, work)
    unpacked = run(["tar", "-xzf", str(archive), "-C", str(work), "age/age"], timeout=60)
    if unpacked.returncode or not (work / "age/age").is_file():
        raise JobError("The pinned age binary could not be installed in RAM.")
    binary = work / "age/age"
    os.chmod(binary, 0o700)
    archive.unlink(missing_ok=True)
    return binary


def upload_roundtrip(tag: str, encrypted: Path, work: Path, token: str, progress=None):
    chunks = chunk_manifest(encrypted, tag)
    release = get_or_create_draft(OWNER, REPOSITORY, tag, token, title="Encrypted lab recovery " + tag,
                                  notes=("Age-encrypted KubeLLM lab recovery snapshot. Immutable asset digests and "
                                         "a complete isolated restore are required before release publication."))
    validate_existing_assets(release, chunks)
    upload_missing_chunks(OWNER, REPOSITORY, release, chunks, encrypted, token, progress=progress)
    release = release_by_id(OWNER, REPOSITORY, release["id"], token)
    validate_existing_assets(release, chunks)
    encrypted.unlink()
    downloaded = work / "downloaded-snapshot.age"
    download_assets(OWNER, REPOSITORY, release, chunks, downloaded, token, progress=progress)
    return release, downloaded, len(chunks)


def retire_exact_resources(args, work: Path, manifest: dict, archive_path: Path, qemu_image_digest: str,
                            status_path: Path, release_url: str):
    expected = args.minikube_id.removeprefix("sha256:")
    current = run(["docker", "inspect", expected], timeout=20)
    if current.returncode:
        raise JobError("The reviewed Minikube container disappeared before retirement.")
    item = json.loads(current.stdout)[0]
    host = item.get("HostConfig") or {}
    mounts = item.get("Mounts") or []
    nets = (item.get("NetworkSettings") or {}).get("Networks") or {}
    legacy = manifest.get("legacy_minikube") or {}
    if (item.get("Id") != expected or str(item.get("Name", "")).lstrip("/") != "minikube"
            or (item.get("State") or {}).get("Running") is not True
            or legacy.get("container_id") != expected or len(nets) != 1
            or not any(m.get("Name") == "minikube" and m.get("Destination") == "/var"
                       and m.get("Type") == "volume" for m in mounts)):
        raise JobError("The reviewed Minikube identity changed after backup; retirement was blocked.")
    network_name = str(host.get("NetworkMode") or "minikube")
    network_result = run(["docker", "network", "inspect", network_name], timeout=20)
    if network_result.returncode:
        raise JobError("The reviewed Minikube network is unavailable at retirement.")
    network = json.loads(network_result.stdout)[0]
    network_id = network.get("Id")
    if {str(x).removeprefix("sha256:") for x in (network.get("Containers") or {})} != {expected} or not network_id:
        raise JobError("The reviewed Minikube network has an unexpected attachment.")
    volume_users = run(["docker", "ps", "-a", "--filter", "volume=minikube", "--no-trunc", "--format", "{{.ID}}"])
    network_users = run(["docker", "ps", "-a", "--filter", "network=" + network_name, "--no-trunc", "--format", "{{.ID}}"])
    if (volume_users.returncode or network_users.returncode
            or {x.strip() for x in volume_users.stdout.decode().splitlines() if x.strip()} != {expected}
            or {x.strip() for x in network_users.stdout.decode().splitlines() if x.strip()} != {expected}):
        raise JobError("The reviewed Minikube network or volume acquired an unexpected container reference.")

    profile = Path.home() / ".minikube/profiles/minikube"
    saved_profile = {x["path"]: x["sha256"] for x in manifest.get("contents", [])
                     if x.get("path", "").startswith("legacy/minikube/profile/")}
    if saved_profile:
        live_profile = {}
        for base, dirs, names in os.walk(profile, topdown=True, followlinks=False):
            root = Path(base)
            if any((root / n).is_symlink() for n in dirs + names):
                raise JobError("The Minikube profile changed or gained a symlink after backup; retirement was blocked.")
            dirs[:] = sorted(dirs)
            for name in sorted(names):
                path = root / name
                if path.is_file():
                    live_profile["legacy/minikube/profile/" + path.relative_to(profile).as_posix()] = sha256_file(path)
        if live_profile != saved_profile:
            raise JobError("The Minikube profile changed after backup; retirement was blocked.")
    elif profile.exists():
        raise JobError("The Minikube profile was not included in backup; retirement was blocked.")
    with zipfile.ZipFile(archive_path) as archive:
        saved_context = json.loads(archive.read("legacy/minikube/kubeconfig.json"))
    kubeconfig = Path.home() / ".kube/config"
    live_context = run(["kubectl", "--kubeconfig", str(kubeconfig), "config", "view", "--context", "minikube",
                        "--raw", "--minify", "-o", "json"], timeout=20)
    if live_context.returncode or json.loads(live_context.stdout) != saved_context:
        raise JobError("The Minikube kubeconfig context changed after backup; retirement was blocked.")
    check_openclaw()
    if qemu_image_digest != IMAGE_DIGEST:
        raise JobError("The isolated VM did not verify the exact OpenClaw digest; image cleanup was blocked.")

    status(status_path, args.job_id, "retiring-reviewed-profile",
           "Encrypted release and isolated restore passed; retiring only the exact reviewed default Minikube profile.",
           release_url=release_url)
    stopped = run(["docker", "stop", "--time", "120", expected], timeout=150)
    if stopped.returncode:
        raise JobError("The reviewed Minikube container could not be stopped for retirement.")
    removed = run(["docker", "rm", expected], timeout=120)
    if removed.returncode:
        run(["docker", "start", expected], timeout=120)
        raise JobError("The reviewed Minikube container could not be removed; it was restarted.")
    if run(["docker", "volume", "rm", "minikube"], timeout=120).returncode:
        raise JobError("The container is retired, but the exact Minikube data volume remains for manual recovery.")
    if run(["docker", "network", "rm", network_id], timeout=120).returncode:
        raise JobError("The container and data volume are retired, but the Minikube network remains for review.")
    if saved_profile:
        shutil.rmtree(profile)
    delete = run(["kubectl", "--kubeconfig", str(kubeconfig), "config", "delete-context", "minikube"], timeout=30)
    if delete.returncode:
        raise JobError("Docker profile resources are retired; the stale Minikube context remains for review.")
    # A clean disposable VM pulled this immutable digest from GHCR before it was sealed.
    remove = run(["docker", "image", "rm", "--no-prune", IMAGE_ID], timeout=120)
    if remove.returncode or run(["docker", "image", "inspect", IMAGE_ID], timeout=20).returncode == 0:
        raise JobError("The exact reviewed unused OpenClaw image could not be removed.")
    root = shutil.disk_usage("/")
    free_gib = round(root.free / 1024**3, 2)
    phase = "cleanup-complete" if root.free >= 20 * 1024**3 else "cleanup-complete-preflight-failing"
    status(status_path, args.job_id, phase,
           "Only the reviewed Minikube profile and pull-verified OpenClaw image were retired.",
           root_free_gib=free_gib, docker_data_root="/var/lib/docker", release_url=release_url)


def resume_job(args, identity: str):
    global TRACKED_CONTAINER
    check_args(args)
    work = job_root(args.job_id) / "data"
    status_path = STATUS_DIR / (args.job_id + ".json")
    config_path = work / "job.json"
    if work.is_symlink() or not work.is_dir() or config_path.is_symlink() or not config_path.is_file():
        raise JobError("The prepared RAM-backed restore VM is unavailable.")
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    if (saved.get("job_id") != args.job_id or saved.get("release_tag") != args.release_tag
            or saved.get("minikube_id") != args.minikube_id
            or saved.get("age_recipient") != args.age_recipient):
        raise JobError("Resume arguments do not match the prepared VM.")
    record = json.loads(status_path.read_text(encoding="utf-8"))
    if record.get("phase") != "awaiting-recovery-key":
        raise JobError("The job is not waiting for its recovery identity.")
    if not any(re.fullmatch(r"AGE-SECRET-KEY-1[0-9A-Z]{58}", line) for line in identity.splitlines()):
        raise JobError("The dedicated age recovery identity is invalid.")
    check_tools()
    check_minikube(args)
    TRACKED_CONTAINER = args.minikube_id.removeprefix("sha256:")
    check_openclaw()
    lock_path = STATUS_DIR / "active.lock"
    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        os.chmod(lock_path, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise JobError("Another lab backup or restore job is active.") from None
        vm = RestoreVM(work)
        retired = False
        expected = args.minikube_id.removeprefix("sha256:")
        try:
            # The private identity is still only in this host process. Lock guest egress first.
            status(
                status_path, args.job_id, "restricted-restore-boot",
                "Booting the isolated restore VM with egress restricted.", release_tag=args.release_tag)
            vm.start(work / ("kubellm-bootstrap-" + args.job_id + ".iso"), restricted=True)
            status(
                status_path, args.job_id, "restricted-restore-ready",
                "The isolated restore VM and Docker are ready.", release_tag=args.release_tag)
            status(
                status_path, args.job_id, "egress-check",
                "Verifying guest egress is blocked before staging the recovery identity.",
                release_tag=args.release_tag)
            verify_guest_egress_blocked(vm)
            status(
                status_path, args.job_id, "egress-blocked",
                "Guest egress is blocked before recovery data is staged.", release_tag=args.release_tag)
            verified_vm_digest = (work / "openclaw-verified-digest.txt").read_text(encoding="ascii").strip()
            if verified_vm_digest != IMAGE_DIGEST:
                raise JobError("The prepared VM's pull-verified image identity changed.")
            if vm.docker(["image", "inspect", IMAGE_DIGEST], timeout=30, check=False).returncode == 0:
                vm.docker(["image", "rm", IMAGE_DIGEST], timeout=120)
                if vm.docker(["image", "inspect", IMAGE_DIGEST], timeout=30, check=False).returncode == 0:
                    raise JobError("The temporary verified image could not be cleared before restore data.")
            age = install_age(work)
            status(
                status_path, args.job_id, "backup-auth-check",
                "Checking the private backup repository credentials.", release_tag=args.release_tag)
            token = read_scoped_token(TOKEN_PATH, expected_uid=os.getuid())
            ensure_private_repository(OWNER, REPOSITORY, token)
            (work / "recipient.txt").write_text(args.age_recipient + "\n", encoding="ascii")
            os.chmod(work / "recipient.txt", 0o600)
            identity_path = work / "recovery.agekey"
            identity_path.write_text(identity.rstrip() + "\n", encoding="ascii")
            os.chmod(identity_path, 0o600)
            def transfer_progress(value):
                status(status_path, args.job_id, "release-transfer",
                       value.get("status", "Transferring encrypted assets."),
                       asset_index=value.get("asset_index"), asset_count=value.get("asset_count"),
                       asset_name=value.get("asset"))

            release = find_release_by_tag(OWNER, REPOSITORY, args.release_tag, token)
            if release is not None and release.get("assets"):
                chunks = chunks_from_release(release, args.release_tag)
                status(status_path, args.job_id, "release-resume",
                       "Reusing the complete private draft; verifying every encrypted part before restore.",
                       release_tag=args.release_tag, asset_parts=len(chunks))
                downloaded = work / "downloaded-snapshot.age"
                download_assets(OWNER, REPOSITORY, release, chunks, downloaded, token,
                                progress=transfer_progress)
                count = len(chunks)
            else:
                status(status_path, args.job_id, "snapshot",
                       "Guest egress is blocked; taking the selected-lane snapshot.",
                       release_tag=args.release_tag)
                encrypted = start_snapshot(args, work, status_path)
                running = run(["docker", "inspect", "-f", "{{.State.Running}}", expected], timeout=15)
                if running.returncode or running.stdout.decode().strip() != "true":
                    start = run(["docker", "start", expected], timeout=120)
                    if start.returncode:
                        raise JobError("The reviewed Minikube profile could not be restarted after snapshot.")
                status(status_path, args.job_id, "snapshot-created",
                       "The encrypted snapshot is complete and the reviewed Minikube profile is running.",
                       encrypted_bytes=encrypted.stat().st_size)
                release, downloaded, count = upload_roundtrip(args.release_tag, encrypted, work, token,
                                                              progress=transfer_progress)

            compressed = work / "snapshot.zip.zst"
            plain = work / "snapshot.zip"
            decrypted = run([str(age), "-d", "-i", str(identity_path), "-o", str(compressed), str(downloaded)],
                            timeout=8 * 60 * 60)
            if decrypted.returncode:
                raise JobError("The downloaded GitHub assets failed age decryption.")
            downloaded.unlink(missing_ok=True)
            os.chmod(compressed, 0o600)
            decompress_snapshot(compressed, plain, work, status_path, args.job_id, args.release_tag)
            compressed.unlink(missing_ok=True)
            assert_capacity(work, check_container_memory=False)
            lane = json.loads(Path(args.selector).read_text(encoding="utf-8")).get("lane_id")
            manifest, entries = verify_archive(plain, lane)
            status(status_path, args.job_id, "asset-and-integrity-verified",
                   "Release asset SHA-256 digests, archive CRC, and member checksums passed.",
                   asset_parts=count, archive_entries=entries)

            # Restore helpers use tempfile; direct all their scratch to this RAM-only job.
            restore_tmp = work / "restore-tmp"
            restore_tmp.mkdir(mode=0o700)
            os.environ["TMPDIR"] = str(restore_tmp)
            tempfile.tempdir = None
            from types import SimpleNamespace
            try:
                from . import lab_ops_backup
            except ImportError:
                import lab_ops_backup
            restore_args = SimpleNamespace(restore_docker_host=f"ssh://ubuntu@127.0.0.1:{vm.port}")
            status(status_path, args.job_id, "isolated-restore",
                   "Restoring PostgreSQL, SQLite, and the old profile in the egress-restricted QEMU VM.",
                   guest_memory_mib=GUEST_MEMORY_MIB)
            previous_path = os.environ.get("PATH", "")
            os.environ["PATH"] = vm.docker_env["PATH"]
            try:
                with zipfile.ZipFile(plain) as archive:
                    checks = lab_ops_backup.verify_isolated_restore(restore_args, archive, manifest)
            finally:
                os.environ["PATH"] = previous_path
            vm.shutdown()
            status(status_path, args.job_id, "restore-passed",
                   "The full isolated restore passed; publishing the encrypted release before exact cleanup.",
                   restore_checks=checks)
            published = publish_draft(OWNER, REPOSITORY, release, token)
            if published.get("draft") is not False:
                raise JobError("The verified private backup release could not be published.")
            status(status_path, args.job_id, "backup-published",
                   "The private release is published after a successful isolated restore.",
                   release_tag=args.release_tag, release_url=published.get("html_url", ""), restore_checks=checks)
            retire_exact_resources(args, work, manifest, plain, verified_vm_digest, status_path,
                                   str(published.get("html_url", "")))
            retired = True
            shutil.rmtree(job_root(args.job_id), ignore_errors=True)
        except Exception as exc:
            vm.shutdown()
            # Only restart if the exact old container still exists; a completed retirement must stay retired.
            exists = run(["docker", "inspect", expected], timeout=15)
            if not retired and exists.returncode == 0:
                try:
                    value = json.loads(exists.stdout)[0]
                    if str(value.get("Name", "")).lstrip("/") == "minikube" and not value.get("State", {}).get("Running"):
                        run(["docker", "start", expected], timeout=120)
                except (ValueError, IndexError, TypeError):
                    pass
            prior = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
            detail = safe_failure_detail(exc, prior.get("phase"))
            phase = "retirement-incomplete" if str(prior.get("phase", "")).startswith("retiring") else "failed"
            status(status_path, args.job_id, phase, detail, release_tag=args.release_tag,
                   release_url=prior.get("release_url", ""), failure_phase=prior.get("phase", "unknown"))
            shutil.rmtree(job_root(args.job_id), ignore_errors=True)
            raise JobError(detail) from None


def configure_token():
    token = sys.stdin.read(4097).strip()
    if len(token) > 4096 or not token.startswith("github_pat_") or any(c.isspace() for c in token):
        raise JobError("Only a fine-grained GitHub token may be installed; no token was saved.")
    TOKEN_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(TOKEN_PATH.parent, 0o700)
    if TOKEN_PATH.exists() or TOKEN_PATH.is_symlink():
        raise JobError("A token file already exists; refusing to overwrite it.")
    fd = os.open(TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as output:
            output.write(token + "\n")
    except Exception:
        TOKEN_PATH.unlink(missing_ok=True)
        raise
    print(json.dumps({"token_configured": True, "path": str(TOKEN_PATH), "mode": "0600"}))


def detach(action, args):
    identity = sys.stdin.read(4097) if action == "resume-worker" else ""
    if len(identity) > 4096:
        raise JobError("The recovery identity exceeded the expected size.")
    script = str(Path(__file__).resolve())
    child_args = [sys.executable, script, action]
    for key, value in vars(args).items():
        if key == "action":
            continue
        if value is not None:
            child_args.extend(["--" + key.replace("_", "-"), str(value)])
    child = subprocess.Popen(child_args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True, close_fds=True, cwd=Path(__file__).parent)
    assert child.stdin is not None
    child.stdin.write(identity.encode("ascii"))
    child.stdin.close()
    print(json.dumps({"job_id": args.job_id, "started": True, "phase": action,
                      "status_file": str(STATUS_DIR / (args.job_id + ".json"))}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description="Lab-native encrypted snapshot and isolated restore.")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("configure-token")
    for action in ("prepare", "prepare-worker", "resume", "resume-worker"):
        item = sub.add_parser(action)
        add_job_parser(item)
    args = parser.parse_args()
    try:
        if args.action == "configure-token":
            configure_token()
        elif args.action in {"prepare", "resume"}:
            detach(args.action + "-worker", args)
        elif args.action == "prepare-worker":
            prepare_job(args)
        else:
            resume_job(args, sys.stdin.read(4097))
        return 0
    except (JobError, GitHubReleaseError) as exc:
        if (args.action in {"prepare-worker", "resume-worker"}
                and re.fullmatch(r"job-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}", getattr(args, "job_id", ""))):
            path = STATUS_DIR / (args.job_id + ".json")
            try:
                prior = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            except (OSError, ValueError):
                prior = {}
            if prior.get("phase") not in {"failed", "retirement-incomplete", "cleanup-complete",
                                          "cleanup-complete-preflight-failing"}:
                status(path, args.job_id, "failed", str(exc),
                       release_tag=getattr(args, "release_tag", ""))
            if args.action == "resume-worker":
                shutil.rmtree(job_root(args.job_id), ignore_errors=True)
            elif args.action == "prepare-worker":
                shutil.rmtree(job_root(args.job_id), ignore_errors=True)
        print("lab-ops-native: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
