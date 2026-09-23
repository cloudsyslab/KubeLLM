#!/usr/bin/env python3
"""Repository-scoped bootstrap and snapshot tooling for portable-agent-toolkit.

The target repository is always authoritative.  ``init`` never overwrites a
different instruction file or skill; it stages the toolkit version for an
agent-guided review instead.  ``snapshot`` never writes to the target and only
pushes when explicitly requested.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple
from urllib.parse import unquote, urlparse


SCHEMA_VERSION = 1
CONTROL_DIRECTORY = ".agent-toolkit"
STATE_PATH = f"{CONTROL_DIRECTORY}/state.json"
INVENTORY_PATH = f"{CONTROL_DIRECTORY}/inventory.json"
STAGING_DIRECTORY = f"{CONTROL_DIRECTORY}/staged"
HELPER_PATH = f"{CONTROL_DIRECTORY}/bin/workspace_toolkit.py"
SNAPSHOT_MANIFEST_PATH = f"{CONTROL_DIRECTORY}/workspace-snapshot.json"

X_COMPONENT_NAME = "x-discovery"
X_COMPONENT_VERSION = "0.1.0"
X_COMPONENT_ROOT = "components/x-discovery"
X_STABLE_BINARIES = ("x-discovery", "x-discovery-mcp")
X_SECRET_KEYS = ("TWITTER_AUTH_TOKEN", "TWITTER_CT0")
X_PINNED_TWITTER_CLI = (
    "twitter-cli @ git+https://github.com/public-clis/twitter-cli.git@"
    "7c634e0d396b1e7af9f63315b414925fe4f29ae7"
)
X_REQUIRED_OVERLAY_PATHS = (
    Path("bin/x-discovery"),
    Path("bin/x-discovery-mcp"),
    Path("lib/x-discovery/pyproject.toml"),
    Path("lib/x-discovery/x_discovery/__init__.py"),
)

FALLBACK_SKILLS = (
    "build-from-plan",
    "discovery",
    "grilling",
    "show-me",
    "writing-session",
    "workspace-onboarding",
)
REQUIRED_ONBOARDING_SKILL = "workspace-onboarding"

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".agent-toolkit",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "caches",
    "dist",
    "node_modules",
    "runtime",
    "runtimes",
    "site-packages",
    "vendor",
    "vendors",
    "venv",
}

SNAPSHOT_RUNTIME_DIRECTORY_NAMES = {
    ".cache",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "cache",
    "caches",
    "exports",
    "logs",
    "node_modules",
    "raw",
    "runtime",
    "runtimes",
    "sessions",
    "venv",
}
SNAPSHOT_RUNTIME_FILE_NAMES = {
    ".DS_Store",
    ".bash_history",
    ".python_history",
    "cookies.json",
    "history.json",
    "session.json",
}
SNAPSHOT_RUNTIME_SUFFIXES = {".db", ".log", ".pyc", ".pyo", ".sqlite", ".sqlite3", ".swp", ".tmp"}

AGENT_INSTRUCTION_NAMES = {
    ".cursorrules",
    "AGENT.md",
    "AGENTS.md",
    "AGENTS.override.md",
    "CLAUDE.md",
    "CODEX.md",
    "GEMINI.md",
}

FRONTMATTER_NAME_RE = re.compile(r"(?m)^name\s*:\s*['\"]?([^'\"\r\n]+?)['\"]?\s*$")
PRIVATE_KEY_RE = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
JWT_RE = re.compile(rb"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?![A-Za-z0-9_-])")
KNOWN_TOKEN_RE = re.compile(
    rb"(?<![A-Za-z0-9])(?:"
    rb"AKIA[0-9A-Z]{16}"
    rb"|gh[opusr]_[A-Za-z0-9]{24,}"
    rb"|github_pat_[A-Za-z0-9_]{30,}"
    rb"|glpat-[A-Za-z0-9_-]{20,}"
    rb"|npm_[A-Za-z0-9]{30,}"
    rb"|pypi-[A-Za-z0-9_-]{30,}"
    rb"|AIza[0-9A-Za-z_-]{30,}"
    rb"|xox[baprs]-[A-Za-z0-9-]{20,}"
    rb"|sk-(?:proj-)?[A-Za-z0-9_-]{20,}"
    rb")(?![A-Za-z0-9])"
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?im)^\s*(?:export\s+)?['\"]?[A-Z][A-Z0-9_.-]*(?:TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE_KEY|API_KEY|ACCESS_KEY(?:_ID)?|CREDENTIALS)['\"]?\s*[:=]\s*['\"]?([^\s,'\"#}]+)"
)
AUTHORIZATION_RE = re.compile(r"(?im)^\s*authorization\s*[:=]\s*['\"]?(?:bearer|basic)\s+([^\s'\"]{12,})")


class ToolkitError(RuntimeError):
    """A safe, user-facing command error."""


def run_git(root: Path, args: Sequence[str], check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise ToolkitError(f"git {' '.join(args[:2])} failed{suffix}")
    return result.stdout.strip()


def git_root(path: Path) -> Path:
    candidate = path.resolve()
    if not candidate.exists():
        raise ToolkitError(f"target does not exist: {path}")
    if candidate.is_file():
        candidate = candidate.parent
    result = subprocess.run(
        ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise ToolkitError("target must be inside a Git worktree")
    return Path(result.stdout.strip()).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_tree_files(root: Path) -> Iterable[Path]:
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_directories: List[str] = []
        for name in sorted(directory_names):
            candidate = current_path / name
            if name in EXCLUDED_DIRECTORY_NAMES:
                continue
            if candidate.is_symlink():
                raise ToolkitError(f"symlinked directories are not portable: {candidate}")
            kept_directories.append(name)
        directory_names[:] = kept_directories
        for name in sorted(file_names):
            candidate = current_path / name
            if candidate.is_symlink():
                raise ToolkitError(f"symlinked files are not portable: {candidate}")
            if candidate.is_file():
                yield candidate


def sha256_tree(root: Path) -> Tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in iter_tree_files(root):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(path)))
        count += 1
    return digest.hexdigest(), count


def is_instruction_file(relative: Path) -> bool:
    name = relative.name
    parts = relative.parts
    if name in AGENT_INSTRUCTION_NAMES:
        return True
    if name.startswith("AGENTS.") and name.endswith(".md"):
        return True
    if relative.as_posix() == ".github/copilot-instructions.md":
        return True
    if len(parts) >= 3 and parts[0:2] == (".cursor", "rules") and relative.suffix.lower() in {".md", ".mdc"}:
        return True
    if len(parts) >= 3 and parts[0:2] == (".github", "instructions") and name.endswith(".instructions.md"):
        return True
    return False


def is_snapshot_skill_root(relative: Path) -> bool:
    return (
        len(relative.parts) == 3
        and relative.parts[:2] == (".agents", "skills")
        and bool(re.fullmatch(r"[a-z0-9][a-z0-9-]*", relative.parts[2]))
    )


def snapshot_runtime_reason(relative: Path) -> Optional[str]:
    if any(part.lower() in SNAPSHOT_RUNTIME_DIRECTORY_NAMES for part in relative.parts[:-1]):
        return "runtime-directory"
    if relative.name in SNAPSHOT_RUNTIME_FILE_NAMES:
        return "runtime-file"
    if relative.suffix.lower() in SNAPSHOT_RUNTIME_SUFFIXES:
        return "runtime-file-type"
    return None


def parse_skill_name(skill_file: Path) -> str:
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return skill_file.parent.name
    if not text.startswith("---"):
        return skill_file.parent.name
    closing = text.find("\n---", 3)
    frontmatter = text[3:closing] if closing >= 0 else text[:65536]
    match = FRONTMATTER_NAME_RE.search(frontmatter)
    return match.group(1).strip() if match else skill_file.parent.name


def remote_identity(remote: str, fallback_name: str) -> Tuple[str, str, str]:
    """Return a credential-free host/owner/repository identity."""
    remote = remote.strip()
    if not remote:
        return "local", "unowned", fallback_name

    host = "local"
    raw_path = remote
    scp_match = re.match(r"^(?:[^@/]+@)?([^:/]+):(.+)$", remote)
    if scp_match and "://" not in remote:
        host = scp_match.group(1)
        raw_path = scp_match.group(2)
    elif "://" in remote:
        parsed = urlparse(remote)
        host = parsed.hostname or "local"
        raw_path = unquote(parsed.path)
    elif remote.startswith(("/", "./", "../")):
        raw_path = remote

    components = [component for component in raw_path.strip("/").split("/") if component]
    repository = components[-1] if components else fallback_name
    if repository.endswith(".git"):
        repository = repository[:-4]
    owner = "--".join(components[:-1]) if len(components) >= 2 and host != "local" else "unowned"
    return host.lower(), owner, repository or fallback_name


def repository_identity(root: Path) -> Dict[str, Any]:
    remotes = run_git(root, ["remote"], check=False).splitlines()
    selected = "origin" if "origin" in remotes else (sorted(remotes)[0] if remotes else "")
    remote = run_git(root, ["remote", "get-url", selected], check=False) if selected else ""
    host, owner, name = remote_identity(remote, root.name)
    branch = run_git(root, ["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
    head = run_git(root, ["rev-parse", "--verify", "HEAD"], check=False)
    return {
        "host": host,
        "owner": owner,
        "name": name,
        "branch": branch or None,
        "head": head or None,
        "remote": selected or None,
    }


def inventory_repository(path: Path) -> Dict[str, Any]:
    root = git_root(path)
    instructions: List[Dict[str, Any]] = []
    skills: List[Dict[str, Any]] = []
    warnings: List[Dict[str, str]] = []

    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept: List[str] = []
        for name in sorted(directory_names):
            candidate = current_path / name
            relative = candidate.relative_to(root)
            if name in EXCLUDED_DIRECTORY_NAMES:
                continue
            if candidate.is_symlink():
                warnings.append({"path": relative.as_posix(), "reason": "symlinked-directory-skipped"})
                continue
            kept.append(name)
        directory_names[:] = kept

        for name in sorted(file_names):
            candidate = current_path / name
            relative = candidate.relative_to(root)
            if candidate.is_symlink():
                if name == "SKILL.md" or is_instruction_file(relative):
                    warnings.append({"path": relative.as_posix(), "reason": "symlinked-file-skipped"})
                continue
            if not candidate.is_file():
                continue
            if name == "SKILL.md":
                skill_root = candidate.parent
                relative_skill_root = skill_root.relative_to(root)
                snapshot_eligible = is_snapshot_skill_root(relative_skill_root)
                try:
                    if snapshot_eligible:
                        tree_hash, file_count = sha256_tree(skill_root)
                        hash_scope = "skill-tree"
                    else:
                        tree_hash, file_count = sha256_file(candidate), 1
                        hash_scope = "skill-file"
                except (OSError, ToolkitError):
                    warnings.append({"path": relative_skill_root.as_posix(), "reason": "unreadable-or-nonportable-skill"})
                    continue
                skills.append(
                    {
                        "name": parse_skill_name(candidate),
                        "path": relative_skill_root.as_posix(),
                        "skill_file": relative.as_posix(),
                        "sha256": tree_hash,
                        "file_count": file_count,
                        "hash_scope": hash_scope,
                        "snapshot_eligible": snapshot_eligible,
                    }
                )
            elif is_instruction_file(relative):
                try:
                    instructions.append(
                        {
                            "path": relative.as_posix(),
                            "sha256": sha256_file(candidate),
                            "size": candidate.stat().st_size,
                        }
                    )
                except OSError:
                    warnings.append({"path": relative.as_posix(), "reason": "unreadable-instruction-file"})

    instructions.sort(key=lambda item: item["path"])
    skills.sort(key=lambda item: (item["name"], item["path"]))
    grouped: Dict[str, List[str]] = {}
    for skill in skills:
        grouped.setdefault(skill["name"], []).append(skill["path"])
    collisions = [
        {"name": name, "paths": paths}
        for name, paths in sorted(grouped.items())
        if len(paths) > 1
    ]
    warnings.sort(key=lambda item: (item["path"], item["reason"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository_identity(root),
        "instructions": instructions,
        "skills": skills,
        "collisions": collisions,
        "warnings": warnings,
    }


def load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ToolkitError(f"missing JSON file: {path}")
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolkitError(f"invalid JSON file {path}: {exc}")
    if not isinstance(value, dict):
        raise ToolkitError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def configured_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()


def codex_local_ref(path: Path, codex_home: Optional[Path] = None) -> str:
    root = Path(os.path.abspath(str(codex_home or configured_codex_home())))
    resolved = Path(os.path.abspath(str(path)))
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        return "${CODEX_HOME}/%s" % resolved.name
    return "${CODEX_HOME}/%s" % relative.as_posix()


def x_secret_path(codex_home: Optional[Path] = None) -> Path:
    override = os.environ.get("X_DISCOVERY_SECRET_FILE")
    if override:
        return Path(override).expanduser()
    return (codex_home or configured_codex_home()) / "secrets" / "x-discovery.env"


def x_auth_state(codex_home: Optional[Path] = None) -> Dict[str, Any]:
    env_present = {key: bool(os.environ.get(key)) for key in X_SECRET_KEYS}
    secret_path = x_secret_path(codex_home)
    file_keys: Set[str] = set()
    if secret_path.is_file():
        try:
            for raw_line in secret_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if line.startswith("export "):
                    line = line[7:].strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() in X_SECRET_KEYS and value.strip().strip("'\""):
                        file_keys.add(key.strip())
        except OSError:
            return {
                "configured": False,
                "source": "unreadable_secret_file",
                "secret_file": codex_local_ref(secret_path, codex_home),
                "permissions_ok": False,
            }

    env_complete = all(env_present.values())
    file_complete = set(X_SECRET_KEYS).issubset(file_keys)
    if env_complete:
        source = "environment"
    elif file_complete:
        source = "secret_file"
    elif env_present["TWITTER_AUTH_TOKEN"] or env_present["TWITTER_CT0"] or file_keys:
        source = "incomplete"
    else:
        source = "missing"

    permissions_ok = True
    if secret_path.exists():
        try:
            permissions_ok = (secret_path.stat().st_mode & 0o077) == 0
        except OSError:
            permissions_ok = False
    return {
        "configured": env_complete or file_complete,
        "source": source,
        "secret_file": codex_local_ref(secret_path, codex_home),
        "permissions_ok": permissions_ok,
    }


def x_twitter_candidates() -> List[Path]:
    candidates: List[Path] = []
    override = os.environ.get("X_DISCOVERY_TWITTER_BIN")
    if override:
        candidates.append(Path(override).expanduser())
    resolved = shutil.which("twitter")
    if resolved:
        candidates.append(Path(resolved))
    candidates.extend(
        [
            Path.home() / ".local" / "bin" / "twitter",
            Path("/opt/homebrew/bin/twitter"),
            Path("/usr/local/bin/twitter"),
        ]
    )
    return candidates


def find_x_twitter_cli() -> Optional[Path]:
    for candidate in x_twitter_candidates():
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def is_x_overlay(root: Path) -> bool:
    return root.is_dir() and all((root / relative).is_file() for relative in X_REQUIRED_OVERLAY_PATHS)


def x_overlay_from_toolkit_root(toolkit_root: Path) -> Optional[Path]:
    candidate = toolkit_root.resolve() / "overlay"
    return candidate if is_x_overlay(candidate) else None


@contextlib.contextmanager
def x_source_from_state(target: Path) -> Iterator[Path]:
    root = git_root(target)
    state_path = root / STATE_PATH
    if not state_path.is_file():
        raise ToolkitError(
            "X companion source is not available here; run setup-x from a toolkit clone or an initialized workspace"
        )
    state = load_json(state_path)
    source = state.get("source")
    if not isinstance(source, dict):
        raise ToolkitError("workspace state has no portable-agent-toolkit provenance for X setup")
    locator = source.get("repository_locator")
    commit = source.get("commit")
    if not isinstance(locator, str) or not locator.strip() or not isinstance(commit, str) or not commit.strip():
        raise ToolkitError("workspace state lacks a fetchable toolkit repository and commit")
    locator = sanitize_repository_locator(locator)
    with tempfile.TemporaryDirectory(prefix="portable-agent-toolkit-x-") as temporary:
        checkout = Path(temporary) / "toolkit"
        clone = subprocess.run(
            ["git", "clone", "--quiet", "--no-checkout", locator, str(checkout)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if clone.returncode != 0:
            raise ToolkitError("could not fetch the recorded portable-agent-toolkit commit for X setup")
        checkout_result = subprocess.run(
            ["git", "-C", str(checkout), "checkout", "--quiet", "--detach", commit],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if checkout_result.returncode != 0:
            raise ToolkitError("recorded portable-agent-toolkit commit is unavailable for X setup")
        overlay = x_overlay_from_toolkit_root(checkout)
        if overlay is None:
            raise ToolkitError("recorded toolkit commit does not contain the X discovery companion")
        yield overlay


@contextlib.contextmanager
def x_source_context(target: Path, toolkit_root: Optional[Path] = None) -> Iterator[Path]:
    if toolkit_root is not None:
        overlay = x_overlay_from_toolkit_root(toolkit_root)
        if overlay is None:
            raise ToolkitError(f"toolkit root does not contain the X discovery companion: {toolkit_root}")
        yield overlay
        return

    local_root = Path(__file__).resolve().parents[1]
    overlay = x_overlay_from_toolkit_root(local_root)
    if overlay is not None:
        yield overlay
        return

    with x_source_from_state(target) as fetched_overlay:
        yield fetched_overlay


def x_component_id(overlay: Path) -> Tuple[str, str]:
    package = overlay / "lib" / "x-discovery" / "pyproject.toml"
    version = X_COMPONENT_VERSION
    match = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']', package.read_text(encoding="utf-8"))
    if match:
        version = match.group(1)
    digest, _ = sha256_tree(overlay)
    return f"{version}-{digest[:12]}", version


def replace_symlink(target: Path, destination: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not target.is_symlink():
        if target.is_dir():
            raise ToolkitError(f"refusing to replace directory with X launcher: {target}")
        target.unlink()
    elif target.is_symlink():
        target.unlink()
    temporary_directory = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=str(target.parent)))
    temporary_link = temporary_directory / target.name
    try:
        os.symlink(destination, temporary_link)
        os.replace(temporary_link, target)
    finally:
        shutil.rmtree(temporary_directory, ignore_errors=True)


def write_stable_launcher(target: Path, binary_name: str) -> None:
    """Write a stable CODEX_HOME-relative launcher for the current component."""
    target.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "#!/bin/sh\n"
        "set -eu\n"
        'CODEX_ROOT="${CODEX_HOME:-${HOME}/.codex}"\n'
        f'exec "$CODEX_ROOT/components/x-discovery/current/bin/{binary_name}" "$@"\n'
    )
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(0o755)
    os.replace(temporary, target)


def install_x_component(overlay: Path, codex_home: Path) -> Dict[str, Any]:
    component_id, package_version = x_component_id(overlay)
    component_root = codex_home / X_COMPONENT_ROOT
    versioned = component_root / component_id
    component_root.mkdir(parents=True, exist_ok=True)
    if not versioned.exists():
        staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=str(component_root)))
        try:
            shutil.copytree(overlay, staging, dirs_exist_ok=True)
            os.replace(staging, versioned)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
    elif not is_x_overlay(versioned):
        raise ToolkitError(f"existing X component is corrupt: {codex_local_ref(versioned, codex_home)}")

    current = component_root / "current"
    replace_symlink(current, versioned)
    bin_root = codex_home / "bin"
    bin_root.mkdir(parents=True, exist_ok=True)
    stable_paths: Dict[str, str] = {}
    for name in X_STABLE_BINARIES:
        stable = bin_root / name
        write_stable_launcher(stable, name)
        stable_paths[name] = codex_local_ref(stable, codex_home)
    return {
        "component_id": component_id,
        "version": package_version,
        "component": codex_local_ref(versioned, codex_home),
        "current": codex_local_ref(current, codex_home),
        "launchers": stable_paths,
    }


def install_pinned_twitter_cli() -> None:
    uv = shutil.which("uv")
    if not uv:
        raise ToolkitError("uv is required to install the pinned twitter CLI")
    result = subprocess.run(
        [uv, "tool", "install", "--force", X_PINNED_TWITTER_CLI],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise ToolkitError("uv could not install the pinned twitter CLI; check network access and retry")


def x_mcp_config_path(codex_home: Path) -> Path:
    return codex_home / "config.toml"


def x_mcp_section(config: str) -> Tuple[Optional[int], Optional[int], str]:
    lines = config.splitlines(keepends=True)
    start: Optional[int] = None
    end: Optional[int] = None
    for index, line in enumerate(lines):
        if line.strip() == "[mcp_servers.x_discovery]":
            start = index
            break
    if start is None:
        return None, None, ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if re.match(r"^\s*\[[^]]+\]\s*$", lines[index]):
            end = index
            break
    return start, end, "".join(lines[start:end])


def read_x_mcp_config(codex_home: Path) -> Dict[str, Any]:
    config_path = x_mcp_config_path(codex_home)
    if not config_path.is_file():
        return {"configured": False, "path": codex_local_ref(config_path, codex_home)}
    try:
        config = config_path.read_text(encoding="utf-8")
    except OSError:
        return {"configured": False, "path": codex_local_ref(config_path, codex_home), "error": "unreadable"}
    _, _, section = x_mcp_section(config)
    command_match = re.search(r'(?m)^\s*command\s*=\s*["\']([^"\']+)["\']', section)
    command = command_match.group(1) if command_match else None
    return {
        "configured": bool(section),
        "path": codex_local_ref(config_path, codex_home),
        "command": command,
    }


def configure_x_mcp(codex_home: Path, launcher: Path) -> Dict[str, Any]:
    config_path = x_mcp_config_path(codex_home)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    previous = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    start, end, _ = x_mcp_section(previous)
    section = (
        "[mcp_servers.x_discovery]\n"
        f"command = {json.dumps(str(launcher))}\n"
        "env_vars = [\"TWITTER_AUTH_TOKEN\", \"TWITTER_CT0\"]\n"
        "startup_timeout_sec = 60.0\n"
        "tool_timeout_sec = 90.0\n"
    )
    if start is None:
        updated = previous
        if updated and not updated.endswith("\n"):
            updated += "\n"
        if updated:
            updated += "\n"
        updated += section
    else:
        lines = previous.splitlines(keepends=True)
        updated = "".join(lines[:start]) + section + "".join(lines[end:])
    if updated != previous:
        mode = config_path.stat().st_mode & 0o777 if config_path.exists() else 0o600
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{config_path.name}.", dir=str(config_path.parent))
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(updated)
            os.chmod(temporary_name, mode)
            os.replace(temporary_name, config_path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
    configured = read_x_mcp_config(codex_home)
    return {
        "configured": bool(configured.get("configured")),
        "path": configured.get("path"),
        "command_matches": configured.get("command") == str(launcher),
    }


def x_doctor_payload(codex_home: Optional[Path] = None) -> Dict[str, Any]:
    home = codex_home or configured_codex_home()
    supported = sys.platform in {"darwin", "linux"}
    current = home / X_COMPONENT_ROOT / "current"
    stable_mcp = home / "bin" / "x-discovery-mcp"
    runtime_ok = current.is_dir() and is_x_overlay(current) and stable_mcp.is_file()
    twitter = find_x_twitter_cli()
    auth = x_auth_state(home)
    mcp = read_x_mcp_config(home)
    mcp_ok = bool(mcp.get("configured")) and mcp.get("command") == str(stable_mcp)
    if not supported:
        status = "unsupported_platform"
    elif not runtime_ok:
        status = "missing_runtime"
    elif twitter is None:
        status = "missing_cli"
    elif not mcp_ok:
        status = "missing_mcp"
    elif not auth["configured"]:
        status = "needs_auth"
    elif not auth["permissions_ok"]:
        status = "insecure_secret_permissions"
    else:
        status = "ready"
    next_steps: List[str] = []
    if status in {"missing_runtime", "missing_cli", "missing_mcp"}:
        next_steps.append("Run workspace_toolkit.py setup-x")
    if status in {"needs_auth", "insecure_secret_permissions"}:
        next_steps.append("Provide both X credentials in the protected x-discovery secret file or environment")
    if status == "ready":
        next_steps.append("Start a new Codex task, then run one bounded read-only X query")
    return {
        "ok": status == "ready",
        "status": status,
        "platform": sys.platform,
        "codex_home": "${CODEX_HOME}",
        "runtime": {"installed": runtime_ok, "current": codex_local_ref(current, home)},
        "twitter_cli": {"installed": twitter is not None},
        "mcp": {"configured": mcp_ok, "config": mcp.get("path"), "command_matches": mcp.get("command") == str(stable_mcp)},
        "auth": {
            "configured": auth["configured"],
            "source": auth["source"],
            "secret_file": auth["secret_file"],
            "permissions_ok": auth["permissions_ok"],
        },
        "next_steps": next_steps,
    }


def doctor_x() -> Dict[str, Any]:
    return x_doctor_payload()


def setup_x(target: Path, toolkit_root: Optional[Path], dry_run: bool) -> Dict[str, Any]:
    home = configured_codex_home()
    if sys.platform not in {"darwin", "linux"}:
        return x_doctor_payload(home)
    with x_source_context(target, toolkit_root) as overlay:
        component_id, package_version = x_component_id(overlay)
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "status": "planned",
                "component_id": component_id,
                "version": package_version,
                "twitter_cli": "uv tool install --force <pinned twitter-cli commit>",
                "codex_home": "${CODEX_HOME}",
            }
        install_pinned_twitter_cli()
        component = install_x_component(overlay, home)
        mcp = configure_x_mcp(home, home / "bin" / "x-discovery-mcp")
    result = x_doctor_payload(home)
    result["setup"] = {"component": component, "mcp": mcp}
    return result


def ensure_safe_destination(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise ToolkitError(f"destination escapes target repository: {path}")
    if ".." in relative.parts:
        raise ToolkitError(f"destination escapes target repository: {path}")
    cursor = root
    for component in relative.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ToolkitError(f"refusing symlinked destination ancestry: {cursor.relative_to(root)}")


def copy_file(source: Path, destination: Path, root: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise ToolkitError(f"source must be a regular file: {source}")
    ensure_safe_destination(root, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source: Path, destination: Path, root: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ToolkitError(f"source must be a regular directory: {source}")
    ensure_safe_destination(root, destination)
    if destination.exists():
        raise ToolkitError(f"copy destination already exists: {destination.relative_to(root)}")
    destination.mkdir(parents=True)
    for path in iter_tree_files(source):
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def files_equal(left: Path, right: Path) -> bool:
    return left.is_file() and right.is_file() and sha256_file(left) == sha256_file(right)


def trees_equal(left: Path, right: Path) -> bool:
    if not left.is_dir() or not right.is_dir() or left.is_symlink() or right.is_symlink():
        return False
    return sha256_tree(left)[0] == sha256_tree(right)[0]


def checked_relative_path(value: str, label: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
        raise ToolkitError(f"unsafe {label}: {value}")
    return relative


def prior_state_is_valid(
    state: Dict[str, Any],
    repository: Dict[str, Any],
    skill_names: Set[str],
    source_name: str,
) -> bool:
    if state.get("schema_version") != SCHEMA_VERSION:
        return False
    if state.get("inventory_path") != INVENTORY_PATH or state.get("helper_path") != HELPER_PATH:
        return False
    if not isinstance(state.get("baseline_inventory"), dict) or not isinstance(state.get("staged"), list):
        return False
    saved_repository = state.get("repository")
    if not isinstance(saved_repository, dict) or any(
        saved_repository.get(key) != repository.get(key) for key in ("host", "owner", "name")
    ):
        return False
    source = state.get("source")
    if not isinstance(source, dict) or source.get("name") != source_name:
        return False
    lifecycle = state.get("lifecycle")
    if not isinstance(lifecycle, dict) or lifecycle.get("status") not in {"needs-agent-review", "ready"}:
        return False
    managed = state.get("managed")
    if not isinstance(managed, list):
        return False
    seen_skills: Set[str] = set()
    helper_count = 0
    instruction_count = 0
    for item in managed:
        if not isinstance(item, dict):
            return False
        kind = item.get("kind")
        if kind == "helper":
            if item.get("target") != HELPER_PATH or not isinstance(item.get("source_sha256"), str):
                return False
            helper_count += 1
        elif kind == "instruction":
            if item.get("target") != "AGENTS.md" or not isinstance(item.get("source_sha256"), str):
                return False
            instruction_count += 1
        elif kind == "skill":
            name = item.get("name")
            target = item.get("target")
            if (
                not isinstance(name, str)
                or name in seen_skills
                or name not in skill_names
                or not isinstance(target, str)
                or item.get("status") not in {"current", "staged", "tailored", "excluded"}
                or not isinstance(item.get("source_sha256"), str)
            ):
                return False
            try:
                target_path = checked_relative_path(target, f"prior target for {name}")
            except ToolkitError:
                return False
            if len(target_path.parts) < 3 or target_path.parts[:2] != (".agents", "skills"):
                return False
            seen_skills.add(name)
    return seen_skills == skill_names and helper_count == 1 and instruction_count == 1


def checked_source_path(root: Path, relative: Path, label: str) -> Path:
    cursor = root
    for component in relative.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ToolkitError(f"symlinked {label} is not portable: {relative.as_posix()}")
    try:
        cursor.resolve().relative_to(root.resolve())
    except ValueError:
        raise ToolkitError(f"{label} escapes toolkit root: {relative.as_posix()}")
    return cursor


def toolkit_configuration(toolkit_root: Path) -> Tuple[Path, List[Tuple[str, Path, Path]], Dict[str, Any]]:
    manifest_path = toolkit_root / "toolkit.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
    template_relative = checked_relative_path(str(manifest.get("agents_template", "AGENTS.md")), "AGENTS template path")
    template = checked_source_path(toolkit_root, template_relative, "AGENTS template")
    if not template.is_file() or template.is_symlink():
        raise ToolkitError(f"missing AGENTS template: {template_relative.as_posix()}")

    skill_directory_relative = checked_relative_path(str(manifest.get("skills_directory", "skills")), "skills directory")
    skill_directory = toolkit_root / skill_directory_relative
    configured = manifest.get("skills")
    skill_entries: List[Tuple[str, Path, Path]] = []
    if isinstance(configured, list):
        for value in configured:
            if isinstance(value, str):
                skill_entries.append(
                    (value, skill_directory_relative / value, Path(".agents/skills") / value)
                )
            elif isinstance(value, dict) and isinstance(value.get("name"), str):
                name = value["name"]
                source = checked_relative_path(
                    str(value.get("source", skill_directory_relative / name)),
                    f"source path for skill {name}",
                )
                target = checked_relative_path(
                    str(value.get("target", Path(".agents/skills") / name)),
                    f"target path for skill {name}",
                )
                if target.parts[:2] != (".agents", "skills"):
                    raise ToolkitError(f"skill target must be under .agents/skills: {target}")
                skill_entries.append((name, source, target))
    elif skill_directory.is_dir():
        skill_entries = [
            (candidate.name, skill_directory_relative / candidate.name, Path(".agents/skills") / candidate.name)
            for candidate in sorted(skill_directory.iterdir(), key=lambda item: item.name)
            if candidate.is_dir() and (candidate / "SKILL.md").is_file()
        ]
    else:
        skill_entries = [
            (name, skill_directory_relative / name, Path(".agents/skills") / name)
            for name in FALLBACK_SKILLS
        ]

    if REQUIRED_ONBOARDING_SKILL not in {entry[0] for entry in skill_entries}:
        raise ToolkitError(f"toolkit must include the {REQUIRED_ONBOARDING_SKILL} skill")

    skills: List[Tuple[str, Path, Path]] = []
    seen: Set[str] = set()
    for name, source_relative, target_relative in skill_entries:
        if name in seen or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise ToolkitError(f"invalid or duplicate toolkit skill name: {name}")
        seen.add(name)
        source = checked_source_path(toolkit_root, source_relative, f"source for skill {name}")
        if source.is_symlink() or not (source / "SKILL.md").is_file() or (source / "SKILL.md").is_symlink():
            raise ToolkitError(f"missing toolkit skill: {name}")
        skills.append((name, source, target_relative))
    return template, skills, manifest


def safe_repository_locator(toolkit_root: Path, manifest: Dict[str, Any]) -> Optional[str]:
    remote = run_git(toolkit_root, ["remote", "get-url", "origin"], check=False)
    if remote and is_portable_repository_locator(remote):
        return sanitize_repository_locator(remote)
    configured = manifest.get("source_repository")
    if isinstance(configured, str) and configured:
        return sanitize_repository_locator(configured)
    return None


def is_portable_repository_locator(locator: str) -> bool:
    locator = locator.strip()
    if re.match(r"^[^@/]+@[^:/]+:.+$", locator):
        return True
    if "://" not in locator:
        return False
    parsed = urlparse(locator)
    return parsed.scheme.lower() in {"http", "https", "ssh", "git+ssh"} and bool(parsed.hostname)


def sanitize_repository_locator(locator: str) -> str:
    locator = locator.strip()
    if "://" in locator:
        parsed = urlparse(locator)
        scheme = parsed.scheme.lower()
        if parsed.password or parsed.query or parsed.fragment:
            raise ToolkitError("repository locator must not contain embedded credentials, query parameters, or fragments")
        if parsed.username and scheme not in {"ssh", "git+ssh"}:
            raise ToolkitError("repository locator must not contain HTTP user information")
        return locator
    if re.match(r"^[^@/]+@[^:/]+:.+$", locator):
        return locator
    return locator


def source_provenance(toolkit_root: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    identity: Dict[str, Any]
    try:
        identity = repository_identity(git_root(toolkit_root))
    except ToolkitError:
        identity = {"host": "local", "owner": "unowned", "name": toolkit_root.name, "branch": None, "head": None, "remote": None}
    return {
        "name": manifest.get("name", "portable-agent-toolkit"),
        "version": manifest.get("version"),
        "repository": {key: identity[key] for key in ("host", "owner", "name")},
        "branch": identity.get("branch"),
        "commit": identity.get("head"),
        "repository_locator": safe_repository_locator(toolkit_root, manifest),
    }


def materialize_candidate(
    source: Path,
    destination: Path,
    root: Path,
    dry_run: bool,
) -> str:
    ensure_safe_destination(root, destination)
    is_directory = source.is_dir()
    same = trees_equal(source, destination) if is_directory else files_equal(source, destination)
    if same:
        return "unchanged"
    if destination.exists() or destination.is_symlink():
        return "staged"
    if not dry_run:
        if is_directory:
            copy_tree(source, destination, root)
        else:
            copy_file(source, destination, root)
    return "installed"


def stage_candidate(source: Path, staged: Path, root: Path, dry_run: bool) -> None:
    ensure_safe_destination(root, staged)
    is_directory = source.is_dir()
    same = trees_equal(source, staged) if is_directory else files_equal(source, staged)
    if same or dry_run:
        return
    if staged.exists() or staged.is_symlink():
        if staged.is_dir() and not staged.is_symlink():
            shutil.rmtree(staged)
        else:
            staged.unlink()
    if is_directory:
        copy_tree(source, staged, root)
    else:
        copy_file(source, staged, root)


def init_repository(target: Path, toolkit_root: Path, dry_run: bool) -> Dict[str, Any]:
    root = git_root(target)
    toolkit_root = toolkit_root.resolve()
    try:
        toolkit_worktree = git_root(toolkit_root)
    except ToolkitError:
        toolkit_worktree = None
    if root == toolkit_root or root == toolkit_worktree:
        raise ToolkitError("refusing to initialize the toolkit source repository as a target")
    template, skills, manifest = toolkit_configuration(toolkit_root)
    initial_inventory = inventory_repository(root)
    managed: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    for collision in initial_inventory["collisions"]:
        conflicts.append(
            {
                "kind": "skill-name-collision",
                "name": collision["name"],
                "paths": collision["paths"],
            }
        )

    existing_state: Dict[str, Any] = {}
    state_file = root / STATE_PATH
    if state_file.is_file():
        try:
            existing_state = load_json(state_file)
        except ToolkitError:
            conflicts.append({"kind": "state", "target": STATE_PATH, "candidate": "regenerated-state"})
    previous_lifecycle = existing_state.get("lifecycle", {}) if isinstance(existing_state.get("lifecycle"), dict) else {}
    prior_state_valid = prior_state_is_valid(
        existing_state,
        initial_inventory["repository"],
        {name for name, _, _ in skills},
        str(manifest.get("name", "portable-agent-toolkit")),
    )
    previous_decisions = previous_lifecycle.get("decisions")
    decided_exclusions: Set[str] = set()
    if prior_state_valid and previous_lifecycle.get("status") == "ready" and isinstance(previous_decisions, list):
        decided_exclusions = {
            decision["name"]
            for decision in previous_decisions
            if isinstance(decision, dict)
            and decision.get("kind") == "skill-exclusion"
            and decision.get("decision") == "exclude"
            and isinstance(decision.get("name"), str)
            and isinstance(decision.get("reason"), str)
            and decision.get("reason", "").strip()
        }
    previous_managed = existing_state.get("managed")
    approved_exclusions: Set[str] = set()
    if isinstance(previous_managed, list):
        approved_exclusions = {
            item["name"]
            for item in previous_managed
            if isinstance(item, dict)
            and item.get("kind") == "skill"
            and item.get("status") == "excluded"
            and isinstance(item.get("name"), str)
            and item["name"] in decided_exclusions
        }

    agents_destination = root / "AGENTS.md"
    agents_staged = root / STAGING_DIRECTORY / "AGENTS.md"
    stage_candidate(template, agents_staged, root, dry_run)
    status = materialize_candidate(template, agents_destination, root, dry_run)
    managed.append(
        {
            "kind": "instruction",
            "name": "AGENTS.md",
            "source": template.relative_to(toolkit_root).as_posix(),
            "target": "AGENTS.md",
            "source_sha256": sha256_file(template),
            "status": "current" if status in {"installed", "unchanged"} else status,
        }
    )
    actions.append({"kind": "instruction", "name": "AGENTS.md", "target": "AGENTS.md", "status": status})
    if status == "staged":
        conflicts.append({"kind": "instruction", "target": "AGENTS.md", "candidate": f"{STAGING_DIRECTORY}/AGENTS.md"})

    for name, source, relative_destination in skills:
        destination = root / relative_destination
        staged = root / STAGING_DIRECTORY / "skills" / name
        stage_candidate(source, staged, root, dry_run)
        status = "excluded" if name in approved_exclusions else materialize_candidate(source, destination, root, dry_run)
        source_hash, _ = sha256_tree(source)
        managed.append(
            {
                "kind": "skill",
                "name": name,
                "source": source.relative_to(toolkit_root).as_posix(),
                "target": relative_destination.as_posix(),
                "source_sha256": source_hash,
                "status": "current" if status in {"installed", "unchanged"} else status,
            }
        )
        actions.append({"kind": "skill", "name": name, "target": relative_destination.as_posix(), "status": status})
        if status == "staged":
            conflicts.append(
                {
                    "kind": "skill",
                    "name": name,
                    "target": relative_destination.as_posix(),
                    "candidate": (Path(STAGING_DIRECTORY) / "skills" / name).as_posix(),
                }
            )

    bundled_helper = toolkit_root / "scripts" / "workspace_toolkit.py"
    helper_source = bundled_helper if bundled_helper.is_file() and not bundled_helper.is_symlink() else Path(__file__).resolve()
    helper_source_label = "scripts/workspace_toolkit.py" if helper_source == bundled_helper else "bootstrap-helper"
    helper_destination = root / HELPER_PATH
    helper_staged = root / STAGING_DIRECTORY / "bin" / "workspace_toolkit.py"
    helper_status = materialize_candidate(helper_source, helper_destination, root, dry_run)
    if helper_status == "staged":
        stage_candidate(helper_source, helper_staged, root, dry_run)
    actions.append({"kind": "helper", "target": HELPER_PATH, "status": helper_status})
    managed.append(
        {
            "kind": "helper",
            "name": "workspace-toolkit",
            "source": helper_source_label,
            "target": HELPER_PATH,
            "source_sha256": sha256_file(helper_source),
            "status": "current" if helper_status in {"installed", "unchanged"} else helper_status,
        }
    )
    if not dry_run and helper_status == "installed":
        helper_destination.chmod(helper_destination.stat().st_mode | 0o111)
    if helper_status == "staged":
        conflicts.append({"kind": "helper", "target": HELPER_PATH, "candidate": f"{STAGING_DIRECTORY}/bin/workspace_toolkit.py"})

    baseline = existing_state.get("baseline_inventory") if prior_state_valid else None
    if not isinstance(baseline, dict):
        baseline = initial_inventory
    lifecycle_status = previous_lifecycle.get("status")
    if not prior_state_valid or conflicts:
        lifecycle_status = "needs-agent-review"

    lifecycle_record = dict(previous_lifecycle) if prior_state_valid else {}
    lifecycle_record.update({"status": lifecycle_status, "conflicts": conflicts})
    state = dict(existing_state) if prior_state_valid else {}
    state.update({
        "schema_version": SCHEMA_VERSION,
        "repository": repository_identity(root),
        "source": source_provenance(toolkit_root, manifest),
        "baseline_inventory": baseline,
        "inventory_path": INVENTORY_PATH,
        "helper_path": HELPER_PATH,
        "managed": managed,
        "staged": [
            f"{STAGING_DIRECTORY}/AGENTS.md",
            *[(Path(STAGING_DIRECTORY) / "skills" / name).as_posix() for name, _, _ in skills],
            *([f"{STAGING_DIRECTORY}/bin/workspace_toolkit.py"] if helper_status == "staged" else []),
        ],
        "lifecycle": lifecycle_record,
    })

    if not dry_run:
        refreshed_inventory = inventory_repository(root)
        write_json(root / INVENTORY_PATH, refreshed_inventory)
        write_json(state_file, state)
    return {
        "schema_version": SCHEMA_VERSION,
        "dry_run": dry_run,
        "repository": initial_inventory["repository"],
        "actions": actions,
        "conflicts": conflicts,
        "state_path": STATE_PATH,
        "inventory_path": INVENTORY_PATH,
        "next_step": (
            f"Read {STAGING_DIRECTORY}/skills/{REQUIRED_ONBOARDING_SKILL}/SKILL.md and follow it for onboarding."
            if any(
                conflict.get("kind") == "skill" and conflict.get("name") == REQUIRED_ONBOARDING_SKILL
                for conflict in conflicts
            )
            else f"Use ${REQUIRED_ONBOARDING_SKILL} to review inventory and staged conflicts."
        ),
    }


def validate_repository(target: Path) -> Tuple[Dict[str, Any], bool]:
    root = git_root(target)
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    state_file = root / STATE_PATH
    try:
        state = load_json(state_file)
    except ToolkitError as exc:
        state = {}
        errors.append({"path": STATE_PATH, "reason": str(exc)})

    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append({"path": STATE_PATH, "reason": "unsupported-or-missing-schema-version"})
    if not (root / "AGENTS.md").is_file() or (root / "AGENTS.md").is_symlink():
        errors.append({"path": "AGENTS.md", "reason": "missing-or-symlinked-root-instructions"})
    inventory_file = root / INVENTORY_PATH
    if not inventory_file.is_file() or inventory_file.is_symlink():
        errors.append({"path": INVENTORY_PATH, "reason": "missing-inventory"})
    else:
        try:
            saved_inventory = load_json(inventory_file)
            if saved_inventory.get("schema_version") != SCHEMA_VERSION:
                errors.append({"path": INVENTORY_PATH, "reason": "unsupported-or-missing-schema-version"})
        except ToolkitError as exc:
            errors.append({"path": INVENTORY_PATH, "reason": str(exc)})
    helper = root / HELPER_PATH
    if not helper.is_file() or helper.is_symlink():
        errors.append({"path": HELPER_PATH, "reason": "missing-or-symlinked-helper"})

    lifecycle = state.get("lifecycle") if isinstance(state.get("lifecycle"), dict) else {}
    managed = state.get("managed", [])
    required_skills: Dict[str, str] = {
        name: (Path(".agents/skills") / name).as_posix() for name in FALLBACK_SKILLS
    }
    helper_records: List[Dict[str, Any]] = []
    seen_skill_records: Set[str] = set()
    excluded_skills: Set[str] = set()
    if not isinstance(managed, list):
        errors.append({"path": STATE_PATH, "reason": "managed-records-must-be-a-list"})
        managed = []
    for item in managed:
        if not isinstance(item, dict):
            errors.append({"path": STATE_PATH, "reason": "malformed-managed-record"})
            continue
        if item.get("kind") == "helper":
            helper_records.append(item)
            continue
        if item.get("kind") != "skill":
            continue
        name = item.get("name")
        target_path = item.get("target")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            errors.append({"path": STATE_PATH, "reason": "malformed-managed-skill-name"})
            continue
        if name in seen_skill_records:
            errors.append({"path": STATE_PATH, "reason": f"duplicate-managed-skill:{name}"})
            continue
        seen_skill_records.add(name)
        if not isinstance(target_path, str):
            errors.append({"path": STATE_PATH, "reason": f"missing-managed-target:{name}"})
            continue
        try:
            target_relative = checked_relative_path(target_path, f"managed target for {name}")
        except ToolkitError:
            errors.append({"path": STATE_PATH, "reason": f"unsafe-managed-target:{name}"})
            continue
        if len(target_relative.parts) < 3 or target_relative.parts[:2] != (".agents", "skills"):
            errors.append({"path": STATE_PATH, "reason": f"managed-target-outside-skills:{name}"})
            continue
        status = item.get("status")
        if status == "excluded":
            excluded_skills.add(name)
            required_skills.pop(name, None)
            excluded_target = root / target_relative
            if excluded_target.exists() or excluded_target.is_symlink():
                errors.append({"path": target_path, "reason": f"excluded-skill-still-present:{name}"})
            continue
        if status not in {"current", "staged", "tailored"}:
            errors.append({"path": STATE_PATH, "reason": f"invalid-managed-skill-status:{name}"})
            continue
        required_skills[name] = target_path

    decisions = lifecycle.get("decisions")
    exclusion_decisions: Set[str] = set()
    if isinstance(decisions, list):
        for decision in decisions:
            if (
                isinstance(decision, dict)
                and decision.get("kind") == "skill-exclusion"
                and decision.get("decision") == "exclude"
                and isinstance(decision.get("name"), str)
                and isinstance(decision.get("reason"), str)
                and decision.get("reason", "").strip()
            ):
                exclusion_decisions.add(decision["name"])
    for name in sorted(excluded_skills):
        if name not in exclusion_decisions:
            errors.append({"path": STATE_PATH, "reason": f"missing-skill-exclusion-decision:{name}"})
    for name, target_path in sorted(required_skills.items()):
        skill_file = root / target_path / "SKILL.md"
        symlinked_ancestry = False
        cursor = root
        for component in Path(target_path).parts:
            cursor = cursor / component
            if cursor.is_symlink():
                symlinked_ancestry = True
                break
        if not skill_file.is_file() or skill_file.is_symlink() or symlinked_ancestry:
            errors.append({"path": skill_file.relative_to(root).as_posix(), "reason": "missing-or-symlinked-skill"})
        elif parse_skill_name(skill_file) != name:
            errors.append({"path": skill_file.relative_to(root).as_posix(), "reason": "frontmatter-name-mismatch"})

    if len(helper_records) != 1:
        errors.append({"path": STATE_PATH, "reason": "expected-one-managed-helper-record"})
    else:
        helper_record = helper_records[0]
        expected_hash = helper_record.get("source_sha256")
        if helper_record.get("target") != HELPER_PATH or not isinstance(expected_hash, str):
            errors.append({"path": STATE_PATH, "reason": "malformed-managed-helper-record"})
        elif helper.is_file() and not helper.is_symlink() and sha256_file(helper) != expected_hash:
            errors.append({"path": HELPER_PATH, "reason": "helper-does-not-match-staged-version"})

    expected_repository = state.get("repository") if isinstance(state.get("repository"), dict) else {}
    current_repository = repository_identity(root)
    for key in ("host", "owner", "name"):
        if expected_repository.get(key) and expected_repository.get(key) != current_repository.get(key):
            errors.append({"path": STATE_PATH, "reason": f"repository-identity-{key}-mismatch"})

    try:
        inventory = inventory_repository(root)
    except ToolkitError as exc:
        inventory = {"collisions": []}
        errors.append({"path": ".", "reason": str(exc)})
    for collision in inventory.get("collisions", []):
        warnings.append({"path": ",".join(collision["paths"]), "reason": f"duplicate-skill-name:{collision['name']}"})

    if lifecycle.get("status") not in {"needs-agent-review", "ready"}:
        errors.append({"path": STATE_PATH, "reason": "invalid-or-missing-lifecycle-status"})
    if not isinstance(state.get("baseline_inventory"), dict):
        errors.append({"path": STATE_PATH, "reason": "missing-baseline-inventory"})
    staged_paths = state.get("staged")
    if not isinstance(staged_paths, list) or not staged_paths:
        errors.append({"path": STATE_PATH, "reason": "missing-staged-candidate-list"})
    else:
        for value in staged_paths:
            if not isinstance(value, str):
                errors.append({"path": STATE_PATH, "reason": "invalid-staged-candidate-path"})
                continue
            try:
                relative = checked_relative_path(value, "staged candidate path")
            except ToolkitError:
                errors.append({"path": STATE_PATH, "reason": "invalid-staged-candidate-path"})
                continue
            candidate = root / relative
            symlinked = candidate.is_symlink()
            cursor = root
            for component in relative.parts:
                cursor = cursor / component
                if cursor.is_symlink():
                    symlinked = True
                    break
            if not candidate.exists() or symlinked:
                errors.append({"path": value, "reason": "missing-staged-candidate"})
    result = {
        "schema_version": SCHEMA_VERSION,
        "valid": not errors,
        "repository": current_repository,
        "lifecycle_status": lifecycle.get("status"),
        "errors": errors,
        "warnings": warnings,
    }
    return result, not errors


def suspicious_filename(path: Path) -> Optional[str]:
    name = path.name.lower()
    if name == ".env" or (name.startswith(".env.") and not name.endswith((".example", ".sample", ".template"))):
        return "environment-file"
    if name in {
        ".netrc",
        ".npmrc",
        ".pypirc",
        "application_default_credentials.json",
        "credentials",
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "service-account.json",
    }:
        return "credential-file"
    if path.suffix.lower() in {".key", ".p12", ".pfx"}:
        return "private-key-file"
    return None


def secret_findings(paths: Iterable[Tuple[Path, str]]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    visited: Set[Path] = set()
    for path, display in paths:
        resolved = path.resolve()
        if resolved in visited:
            continue
        visited.add(resolved)
        reason = suspicious_filename(path)
        if reason:
            findings.append({"path": display, "reason": reason})
            continue
        try:
            payload = path.read_bytes()
        except OSError:
            findings.append({"path": display, "reason": "unreadable-file"})
            continue
        if PRIVATE_KEY_RE.search(payload):
            findings.append({"path": display, "reason": "private-key-material"})
            continue
        if JWT_RE.search(payload):
            findings.append({"path": display, "reason": "jwt-like-value"})
            continue
        if KNOWN_TOKEN_RE.search(payload):
            findings.append({"path": display, "reason": "credential-like-token"})
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            continue
        matches = list(SECRET_ASSIGNMENT_RE.finditer(text)) + list(AUTHORIZATION_RE.finditer(text))
        for match in matches:
            value = match.group(1).strip().strip("'\"")
            if (
                len(value) >= 8
                and value.lower() not in {
                    "<api-key>",
                    "<password>",
                    "<secret>",
                    "<token>",
                    "<value>",
                    "changeme",
                    "example",
                    "redacted",
                }
                and not value.startswith(("$", "${", "{{"))
            ):
                findings.append({"path": display, "reason": "credential-assignment"})
                break
    return findings


def safe_branch_component(value: str) -> str:
    component = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-").lower()
    component = re.sub(r"\.{2,}", ".", component)
    return component or "unknown"


def snapshot_branch(identity: Dict[str, Any]) -> str:
    return "workspace/{}/{}/{}".format(
        safe_branch_component(str(identity.get("host") or "local")),
        safe_branch_component(str(identity.get("owner") or "unowned")),
        safe_branch_component(str(identity.get("name") or "repository")),
    )


def resolve_snapshot_repository(root: Path, explicit: Optional[str]) -> str:
    if explicit:
        return sanitize_repository_locator(explicit)
    state = load_json(root / STATE_PATH)
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    locator = source.get("repository_locator")
    if not isinstance(locator, str) or not locator:
        raise ToolkitError("snapshot requires --toolkit-repo because provenance has no repository locator")
    return sanitize_repository_locator(locator)


def checkout_snapshot_branch(clone: Path, branch: str) -> bool:
    if branch in {"main", "master"} or not branch.startswith("workspace/"):
        raise ToolkitError("snapshot branch must be under workspace/")
    remote_ref = f"refs/remotes/origin/{branch}"
    probe = subprocess.run(
        ["git", "-C", str(clone), "show-ref", "--verify", "--quiet", remote_ref],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if probe.returncode == 0:
        run_git(clone, ["checkout", "--quiet", "-b", branch, f"origin/{branch}"])
        return True
    base = "origin/main"
    probe_main = subprocess.run(
        ["git", "-C", str(clone), "show-ref", "--verify", "--quiet", "refs/remotes/origin/main"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if probe_main.returncode != 0:
        base = "origin/master"
        probe_master = subprocess.run(
            ["git", "-C", str(clone), "show-ref", "--verify", "--quiet", "refs/remotes/origin/master"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if probe_master.returncode != 0:
            base = "HEAD"
    run_git(clone, ["checkout", "--quiet", "-b", branch, base])
    return False


def safe_relative_snapshot_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
        raise ToolkitError(f"unsafe snapshot manifest path: {value}")
    return relative


def snapshot_repository(target: Path, toolkit_repository: Optional[str], push: bool) -> Dict[str, Any]:
    root = git_root(target)
    inventory = inventory_repository(root)
    canonical_skill_warnings = [
        warning
        for warning in inventory["warnings"]
        if Path(warning["path"]).parts[:2] == (".agents", "skills")
    ]
    if canonical_skill_warnings:
        paths = ", ".join(warning["path"] for warning in canonical_skill_warnings[:5])
        raise ToolkitError(f"canonical skill inventory is not portable: {paths}")
    snapshot_skills = [item for item in inventory["skills"] if item.get("snapshot_eligible") is True]
    grouped_snapshot_skills: Dict[str, List[str]] = {}
    for skill in snapshot_skills:
        grouped_snapshot_skills.setdefault(skill["name"], []).append(skill["path"])
    snapshot_collisions = {
        name: paths for name, paths in grouped_snapshot_skills.items() if len(paths) > 1
    }
    if snapshot_collisions:
        names = ", ".join(sorted(snapshot_collisions))
        raise ToolkitError(f"resolve duplicate skill names before snapshot: {names}")
    if not any(item["path"] == "AGENTS.md" for item in inventory["instructions"]):
        raise ToolkitError("snapshot requires a root AGENTS.md")
    if not snapshot_skills:
        raise ToolkitError("snapshot requires at least one canonical .agents/skills entry")
    invalid_skill_names = [
        item["name"]
        for item in snapshot_skills
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", item["name"])
    ]
    if invalid_skill_names:
        raise ToolkitError("snapshot requires portable lowercase skill names")

    selected_files: List[Tuple[Path, str]] = []
    for instruction in inventory["instructions"]:
        source = root / instruction["path"]
        selected_files.append((source, instruction["path"]))
    for skill in snapshot_skills:
        skill_root = root / skill["path"]
        for source in iter_tree_files(skill_root):
            relative_source = source.relative_to(skill_root)
            display = (Path("skills") / skill["name"] / relative_source).as_posix()
            runtime_reason = snapshot_runtime_reason(relative_source)
            if runtime_reason:
                raise ToolkitError(f"runtime artifact blocked snapshot ({runtime_reason}): {display}")
            selected_files.append((source, display))
    findings = secret_findings(selected_files)
    if findings:
        paths = ", ".join(finding["path"] for finding in findings[:5])
        raise ToolkitError(f"secret scan blocked snapshot ({len(findings)} finding(s)): {paths}")

    identity = inventory["repository"]
    branch = snapshot_branch(identity)
    repository = resolve_snapshot_repository(root, toolkit_repository)
    with tempfile.TemporaryDirectory(prefix="portable-agent-toolkit-snapshot-") as temporary:
        clone = Path(temporary) / "toolkit"
        clone_result = subprocess.run(
            ["git", "clone", "--quiet", "--", repository, str(clone)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if clone_result.returncode != 0:
            detail = clone_result.stderr.strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            raise ToolkitError(f"could not clone toolkit repository{suffix}")
        existing_workspace_branch = checkout_snapshot_branch(clone, branch)

        previous_manifest_path = clone / SNAPSHOT_MANIFEST_PATH
        ensure_safe_destination(clone, previous_manifest_path)
        if existing_workspace_branch and not previous_manifest_path.is_file():
            raise ToolkitError("existing workspace branch has no identity manifest; refusing to overwrite it")
        if previous_manifest_path.is_file():
            previous_manifest = load_json(previous_manifest_path)
            previous_identity = previous_manifest.get("repository")
            identity_keys = ("host", "owner", "name")
            if not isinstance(previous_identity, dict) or any(
                previous_identity.get(key) != identity.get(key) for key in identity_keys
            ):
                raise ToolkitError("workspace branch identity does not match the target repository")
            for value in previous_manifest.get("instruction_paths", []):
                if not isinstance(value, str):
                    continue
                relative = safe_relative_snapshot_path(value)
                path = clone / relative
                ensure_safe_destination(clone, path)
                if path.is_file() or path.is_symlink():
                    path.unlink()

        skills_destination = clone / "skills"
        ensure_safe_destination(clone, skills_destination)
        if skills_destination.exists():
            if skills_destination.is_symlink() or not skills_destination.is_dir():
                raise ToolkitError("snapshot clone has an unsafe skills destination")
            shutil.rmtree(skills_destination)
        skills_destination.mkdir()

        for instruction in inventory["instructions"]:
            relative = safe_relative_snapshot_path(instruction["path"])
            copy_file(root / relative, clone / relative, clone)
        for skill in snapshot_skills:
            copy_tree(root / skill["path"], skills_destination / skill["name"], clone)

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "branch": branch,
            "repository": identity,
            "instruction_paths": [item["path"] for item in inventory["instructions"]],
            "skills": [
                {"name": item["name"], "source_path": item["path"], "sha256": item["sha256"]}
                for item in snapshot_skills
            ],
        }
        write_json(previous_manifest_path, manifest)

        exported_files: List[Tuple[Path, str]] = []
        for instruction in inventory["instructions"]:
            exported = clone / instruction["path"]
            exported_files.append((exported, instruction["path"]))
        for skill in snapshot_skills:
            exported_root = skills_destination / skill["name"]
            for exported in iter_tree_files(exported_root):
                exported_files.append((exported, exported.relative_to(clone).as_posix()))
        exported_files.append((previous_manifest_path, SNAPSHOT_MANIFEST_PATH))
        clone_findings = secret_findings(exported_files)
        if clone_findings:
            paths = ", ".join(finding["path"] for finding in clone_findings[:5])
            raise ToolkitError(f"secret scan blocked snapshot clone ({len(clone_findings)} finding(s)): {paths}")

        run_git(clone, ["add", "-A"])
        changed = bool(run_git(clone, ["status", "--porcelain"]))
        if changed:
            message = f"Snapshot {identity['host']}/{identity['owner']}/{identity['name']}"
            run_git(
                clone,
                [
                    "-c",
                    "user.name=Portable Agent Toolkit",
                    "-c",
                    "user.email=portable-agent-toolkit@localhost",
                    "commit",
                    "--quiet",
                    "-m",
                    message,
                ],
            )
        commit = run_git(clone, ["rev-parse", "HEAD"])
        if push:
            run_git(clone, ["push", "--quiet", "origin", f"HEAD:refs/heads/{branch}"])
        return {
            "schema_version": SCHEMA_VERSION,
            "repository": identity,
            "branch": branch,
            "commit": commit,
            "changed": changed,
            "pushed": push,
            "instruction_count": len(inventory["instructions"]),
            "skill_count": len(snapshot_skills),
        }


def print_json(value: Dict[str, Any]) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repository-scoped portable agent toolkit helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="inventory agent instructions and skills")
    inventory_parser.add_argument("target", nargs="?", default=".")

    init_parser = subparsers.add_parser("init", help="stage a repository-scoped toolkit onboarding")
    init_parser.add_argument("target", nargs="?", default=".")
    init_parser.add_argument("--toolkit-root", default=str(Path(__file__).resolve().parent.parent))
    init_parser.add_argument("--dry-run", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="validate initialized workspace topology")
    validate_parser.add_argument("target", nargs="?", default=".")

    snapshot_parser = subparsers.add_parser("snapshot", help="snapshot workspace agent files to a workspace branch")
    snapshot_parser.add_argument("target", nargs="?", default=".")
    snapshot_parser.add_argument("--toolkit-repo")
    snapshot_parser.add_argument("--push", action="store_true")

    doctor_x_parser = subparsers.add_parser(
        "doctor-x",
        help="report the local X discovery runtime, CLI, MCP, and authentication state",
    )
    doctor_x_parser.add_argument("--json", action="store_true", help="kept for command symmetry; output is always JSON")

    setup_x_parser = subparsers.add_parser(
        "setup-x",
        help="install or repair the optional read-only X discovery companion",
    )
    setup_x_parser.add_argument("target", nargs="?", default=".")
    setup_x_parser.add_argument("--toolkit-root", help="use a specific toolkit clone instead of recorded provenance")
    setup_x_parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "inventory":
            print_json(inventory_repository(Path(arguments.target)))
            return 0
        if arguments.command == "init":
            print_json(init_repository(Path(arguments.target), Path(arguments.toolkit_root), arguments.dry_run))
            return 0
        if arguments.command == "validate":
            result, valid = validate_repository(Path(arguments.target))
            print_json(result)
            return 0 if valid else 1
        if arguments.command == "snapshot":
            print_json(snapshot_repository(Path(arguments.target), arguments.toolkit_repo, arguments.push))
            return 0
        if arguments.command == "doctor-x":
            result = doctor_x()
            print_json(result)
            return 0 if result.get("ok") else 1
        if arguments.command == "setup-x":
            result = setup_x(
                Path(arguments.target),
                Path(arguments.toolkit_root) if arguments.toolkit_root else None,
                arguments.dry_run,
            )
            print_json(result)
            return 0 if result.get("ok") or result.get("dry_run") or result.get("status") == "needs_auth" else 1
    except ToolkitError as exc:
        print_json({"error": str(exc), "command": arguments.command})
        return 1
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
