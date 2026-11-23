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
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tarfile
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple
from urllib.parse import unquote, urlparse


SCHEMA_VERSION = 1
CONTROL_DIRECTORY = ".agent-toolkit"
STATE_PATH = f"{CONTROL_DIRECTORY}/state.json"
INVENTORY_PATH = f"{CONTROL_DIRECTORY}/inventory.json"
STAGING_DIRECTORY = f"{CONTROL_DIRECTORY}/staged"
REFRESH_DIRECTORY = f"{CONTROL_DIRECTORY}/refresh"
REFRESH_PLAN_PATH = f"{REFRESH_DIRECTORY}/plan.json"
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
    "browser-workflow",
    "reconcile-branches",
    "publish-github",
    "discovery",
    "grilling",
    "refresh-docs",
    "site-reference",
    "show-me",
    "website-design",
    "website-design-build",
    "unslop",
    "writing-session",
    "workspace-onboarding",
)
REQUIRED_ONBOARDING_SKILL = "workspace-onboarding"

# Claude Code reads CLAUDE.md and .claude/skills, not AGENTS.md beside a
# CLAUDE.md or .agents/skills.  The binding imports AGENTS.md and links the
# canonical skill tree so both runtimes share one set of files.
CLAUDE_INSTRUCTION = "CLAUDE.md"
CLAUDE_SKILLS_LINK = ".claude/skills"
CLAUDE_SKILLS_LINK_TARGET = "../.agents/skills"
CLAUDE_EXCLUSION_KIND = "claude-binding-exclusion"
CLAUDE_AGENTS_IMPORT_RE = re.compile(r"(?:^|\s)@(?:\./)?AGENTS\.md(?=\s|$)")

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
    lifecycle_decisions = lifecycle.get("decisions")
    excluded_skill_names = {
        decision.get("name")
        for decision in lifecycle_decisions
        if isinstance(decision, dict)
        and decision.get("kind") == "skill-exclusion"
        and decision.get("decision") == "exclude"
        and isinstance(decision.get("name"), str)
        and isinstance(decision.get("reason"), str)
        and decision.get("reason", "").strip()
    } if isinstance(lifecycle_decisions, list) else set()
    seen_skills: Set[str] = set()
    helper_count = 0
    seen_instructions: Set[str] = set()
    for item in managed:
        if not isinstance(item, dict):
            return False
        kind = item.get("kind")
        if kind == "helper":
            if item.get("target") != HELPER_PATH or not isinstance(item.get("source_sha256"), str):
                return False
            helper_count += 1
        elif kind == "instruction":
            # CLAUDE.md is optional so states written before the Claude
            # binding remain valid until refresh adopts it.
            target = item.get("target")
            if (
                target not in {"AGENTS.md", CLAUDE_INSTRUCTION}
                or target in seen_instructions
                or not isinstance(item.get("source_sha256"), str)
            ):
                return False
            seen_instructions.add(target)
        elif kind == "skill":
            name = item.get("name")
            target = item.get("target")
            status = item.get("status")
            if (
                isinstance(name, str)
                and name not in skill_names
                and status == "excluded"
                and name in excluded_skill_names
            ):
                if name in seen_skills or not isinstance(target, str) or not isinstance(item.get("source_sha256"), str):
                    return False
                try:
                    target_path = checked_relative_path(target, f"prior target for {name}")
                except ToolkitError:
                    return False
                if len(target_path.parts) < 3 or target_path.parts[:2] != (".agents", "skills"):
                    return False
                seen_skills.add(name)
                continue
            if item.get("source") == "workspace-local":
                if (
                    not isinstance(name, str)
                    or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name)
                    or name in seen_skills
                    or not isinstance(target, str)
                    or item.get("status") not in {"current", "tailored"}
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
                continue
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
    staged = state.get("staged", [])
    staged_skills = {
        Path(value).name
        for value in staged
        if isinstance(value, str)
        and len(Path(value).parts) == 4
        and Path(value).parts[:3] == (CONTROL_DIRECTORY, "staged", "skills")
    }
    # New upstream skills are additive. Keep older workspace states valid so
    # refresh can review them without forcing a fresh initialization.
    managed_upstream_skills = {
        item["name"]
        for item in managed
        if item.get("kind") == "skill" and item.get("source") != "workspace-local" and item.get("name") in skill_names
    }
    local_skills = {
        item["name"]
        for item in managed
        if item.get("kind") == "skill" and item.get("source") == "workspace-local"
    }
    return managed_upstream_skills == staged_skills and staged_skills.issubset(skill_names) and not (local_skills & staged_skills) and helper_count == 1 and "AGENTS.md" in seen_instructions


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


def manifest_requires(manifest: Dict[str, Any], names: Set[str]) -> Dict[str, List[str]]:
    """Return each skill's declared dependencies on other toolkit skills."""
    requires: Dict[str, List[str]] = {}
    configured = manifest.get("skills")
    for value in configured if isinstance(configured, list) else []:
        if not isinstance(value, dict) or not isinstance(value.get("name"), str) or "requires" not in value:
            continue
        name = value["name"]
        declared = value["requires"]
        if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared):
            raise ToolkitError(f"requires for skill {name} must be a list of skill names")
        unknown = sorted(set(declared) - names)
        if unknown:
            raise ToolkitError(f"skill {name} requires unknown toolkit skills: {', '.join(unknown)}")
        if name in declared:
            raise ToolkitError(f"skill {name} cannot require itself")
        if declared:
            requires[name] = sorted(set(declared))
    return requires


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
    manifest_requires(manifest, seen)
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


def claude_template_path(toolkit_root: Path, manifest: Dict[str, Any]) -> Optional[Path]:
    configured = manifest.get("claude_template")
    if configured is None:
        return None
    if not isinstance(configured, str) or not configured:
        raise ToolkitError("claude_template must be a relative path")
    relative = checked_relative_path(configured, "Claude template path")
    template = checked_source_path(toolkit_root, relative, "Claude template")
    if not template.is_file() or template.is_symlink():
        raise ToolkitError(f"missing Claude template: {relative.as_posix()}")
    return template


def imports_root_agents(text: str) -> bool:
    """Return whether Claude Code would expand an @AGENTS.md import in text."""
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced and CLAUDE_AGENTS_IMPORT_RE.search(re.sub(r"`[^`]*`", "", line)):
            return True
    return False


def claude_skills_link_is_current(root: Path) -> bool:
    link = root / CLAUDE_SKILLS_LINK
    if link.parent.is_symlink() or not link.is_symlink():
        return False
    value = os.readlink(link)
    if os.path.isabs(value):
        return False
    resolved = os.path.normpath(os.path.join(str(link.parent), value))
    return resolved == os.path.normpath(str(root / ".agents" / "skills"))


def materialize_claude_skills_link(root: Path, dry_run: bool) -> str:
    link = root / CLAUDE_SKILLS_LINK
    if claude_skills_link_is_current(root):
        return "unchanged"
    # A Claude-native skill folder, a link elsewhere, or a symlinked .claude
    # directory is reconciled during onboarding, never replaced here.
    if (
        link.exists()
        or link.is_symlink()
        or link.parent.is_symlink()
        or (link.parent.exists() and not link.parent.is_dir())
    ):
        return "staged"
    if not dry_run:
        ensure_safe_destination(root, link)
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(CLAUDE_SKILLS_LINK_TARGET, link, target_is_directory=True)
        except OSError:
            # Hosts without symlink support leave the link to onboarding.
            return "staged"
    return "installed"


def claude_exclusions(lifecycle: Dict[str, Any]) -> Set[str]:
    decisions = lifecycle.get("decisions")
    if not isinstance(decisions, list):
        return set()
    return {
        decision["name"]
        for decision in decisions
        if isinstance(decision, dict)
        and decision.get("kind") == CLAUDE_EXCLUSION_KIND
        and decision.get("decision") == "exclude"
        and decision.get("name") in {CLAUDE_INSTRUCTION, CLAUDE_SKILLS_LINK}
        and isinstance(decision.get("reason"), str)
        and decision.get("reason", "").strip()
    }


def skill_exclusions(lifecycle: Dict[str, Any]) -> Dict[str, str]:
    decisions = lifecycle.get("decisions")
    if not isinstance(decisions, list):
        return {}
    return {
        decision["name"]: decision["reason"]
        for decision in decisions
        if isinstance(decision, dict)
        and decision.get("kind") == "skill-exclusion"
        and decision.get("decision") == "exclude"
        and isinstance(decision.get("name"), str)
        and isinstance(decision.get("reason"), str)
        and decision["reason"].strip()
    }


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
    skill_requires = manifest_requires(manifest, {name for name, _, _ in skills})
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
    saved_source = existing_state.get("source") if isinstance(existing_state.get("source"), dict) else {}
    if prior_state_valid and previous_lifecycle.get("status") == "ready":
        candidate_source = source_provenance(toolkit_root, manifest)
        if (
            saved_source.get("commit") != candidate_source.get("commit")
            or saved_source.get("version") != candidate_source.get("version")
        ):
            raise ToolkitError("this ready workspace has a different adopted toolkit source; use refresh to review the upstream changes")
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
                **({"requires": skill_requires[name]} if name in skill_requires else {}),
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

    claude_template = claude_template_path(toolkit_root, manifest)
    claude_staged: List[str] = []
    if claude_template is not None:
        prior_claude_exclusions = (
            claude_exclusions(previous_lifecycle)
            if prior_state_valid and previous_lifecycle.get("status") == "ready"
            else set()
        )
        claude_excluded = CLAUDE_INSTRUCTION in prior_claude_exclusions and isinstance(previous_managed, list) and any(
            isinstance(item, dict)
            and item.get("kind") == "instruction"
            and item.get("target") == CLAUDE_INSTRUCTION
            and item.get("status") == "excluded"
            for item in previous_managed
        )
        claude_destination = root / CLAUDE_INSTRUCTION
        claude_candidate = f"{STAGING_DIRECTORY}/{CLAUDE_INSTRUCTION}"
        stage_candidate(claude_template, root / claude_candidate, root, dry_run)
        claude_staged.append(claude_candidate)
        if claude_excluded:
            status = "excluded"
        elif claude_destination.is_symlink():
            status = "staged"
        else:
            status = materialize_candidate(claude_template, claude_destination, root, dry_run)
        managed.append(
            {
                "kind": "instruction",
                "name": CLAUDE_INSTRUCTION,
                "source": claude_template.relative_to(toolkit_root).as_posix(),
                "target": CLAUDE_INSTRUCTION,
                "source_sha256": sha256_file(claude_template),
                "status": "current" if status in {"installed", "unchanged"} else status,
            }
        )
        actions.append({"kind": "instruction", "name": CLAUDE_INSTRUCTION, "target": CLAUDE_INSTRUCTION, "status": status})
        if status == "staged":
            conflicts.append({"kind": "instruction", "target": CLAUDE_INSTRUCTION, "candidate": claude_candidate})
        if claude_excluded or CLAUDE_SKILLS_LINK in prior_claude_exclusions:
            link_status = "excluded"
        else:
            link_status = materialize_claude_skills_link(root, dry_run)
        actions.append({"kind": "link", "name": CLAUDE_SKILLS_LINK, "target": CLAUDE_SKILLS_LINK, "status": link_status})
        if link_status == "staged":
            conflicts.append({"kind": "claude-skills-link", "target": CLAUDE_SKILLS_LINK, "expected": CLAUDE_SKILLS_LINK_TARGET})

    if prior_state_valid and isinstance(previous_managed, list):
        current_skill_names = {name for name, _, _ in skills}
        for item in previous_managed:
            if (
                isinstance(item, dict)
                and item.get("kind") == "skill"
                and item.get("source") == "workspace-local"
                and item.get("name") not in current_skill_names
            ):
                managed.append(dict(item))

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
            *claude_staged,
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


def refresh_source_entries(toolkit_root: Path) -> Tuple[Dict[Tuple[str, str], Dict[str, Any]], Dict[str, Any]]:
    template, skills, manifest = toolkit_configuration(toolkit_root)
    skill_requires = manifest_requires(manifest, {name for name, _, _ in skills})
    entries: Dict[Tuple[str, str], Dict[str, Any]] = {
        ("instruction", "AGENTS.md"): {
            "kind": "instruction",
            "name": "AGENTS.md",
            "source": template.relative_to(toolkit_root).as_posix(),
            "path": template,
            "hash": sha256_file(template),
            "directory": False,
            "upstream_target": "AGENTS.md",
        }
    }
    claude_template = claude_template_path(toolkit_root, manifest)
    if claude_template is not None:
        entries[("instruction", CLAUDE_INSTRUCTION)] = {
            "kind": "instruction",
            "name": CLAUDE_INSTRUCTION,
            "source": claude_template.relative_to(toolkit_root).as_posix(),
            "path": claude_template,
            "hash": sha256_file(claude_template),
            "directory": False,
            "upstream_target": CLAUDE_INSTRUCTION,
        }
    for name, source, target in skills:
        entries[("skill", name)] = {
            "kind": "skill",
            "name": name,
            "source": source.relative_to(toolkit_root).as_posix(),
            "path": source,
            "hash": sha256_tree(source)[0],
            "directory": True,
            "upstream_target": target.as_posix(),
            "requires": skill_requires.get(name, []),
        }
    helper = toolkit_root / "scripts" / "workspace_toolkit.py"
    if not helper.is_file() or helper.is_symlink():
        raise ToolkitError("toolkit source is missing scripts/workspace_toolkit.py")
    entries[("helper", "workspace-toolkit")] = {
        "kind": "helper",
        "name": "workspace-toolkit",
        "source": "scripts/workspace_toolkit.py",
        "path": helper,
        "hash": sha256_file(helper),
        "directory": False,
        "upstream_target": HELPER_PATH,
    }
    return entries, manifest


def export_toolkit_revision(repository: Path, commit: str, destination: Path) -> None:
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", commit):
        raise ToolkitError("recorded toolkit source commit is missing or invalid; refresh cannot reconstruct its baseline")
    resolved = run_git(repository, ["rev-parse", "--verify", f"{commit}^{{commit}}"], check=False)
    if not resolved:
        raise ToolkitError("recorded toolkit source commit is unavailable; refresh cannot guess the previous baseline")
    extract_toolkit_archive(repository, commit, ["AGENTS.md", "toolkit.json", "scripts/workspace_toolkit.py", "skills"], destination)
    # Revisions before the Claude binding declare no template; export it only
    # when that revision's manifest names one.
    claude_template = load_json(destination / "toolkit.json").get("claude_template")
    if isinstance(claude_template, str) and claude_template:
        relative = checked_relative_path(claude_template, "Claude template path")
        extract_toolkit_archive(repository, commit, [relative.as_posix()], destination)


def extract_toolkit_archive(repository: Path, commit: str, paths: Sequence[str], destination: Path) -> None:
    archive = subprocess.run(
        ["git", "-C", str(repository), "archive", "--format=tar", commit, *paths],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if archive.returncode != 0:
        raise ToolkitError("could not export the recorded toolkit source revision")
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as bundle:
            for member in bundle.getmembers():
                relative = Path(member.name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ToolkitError("recorded toolkit archive contains an unsafe path")
                output = destination / relative
                if member.isdir():
                    output.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    source = bundle.extractfile(member)
                    if source is None:
                        raise ToolkitError("recorded toolkit archive contains an unreadable file")
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(source.read())
                    output.chmod(member.mode & 0o777)
                else:
                    raise ToolkitError("recorded toolkit archive contains a link or unsupported file")
    except (tarfile.TarError, OSError) as exc:
        raise ToolkitError(f"could not read the recorded toolkit archive: {type(exc).__name__}")


def hash_materialized_entry(root: Path, entry: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(entry, dict) or not isinstance(entry.get("target"), str):
        return None
    try:
        target = checked_relative_path(entry["target"], "workspace refresh target")
    except ToolkitError:
        return None
    path = root / target
    if entry.get("kind") == "skill":
        if not path.is_dir() or path.is_symlink():
            return None
        return sha256_tree(path)[0]
    if not path.is_file() or path.is_symlink():
        return None
    return sha256_file(path)


def copy_refresh_entry(source: Path, destination: Path, root: Path, directory: bool) -> None:
    ensure_safe_destination(root, destination)
    if destination.is_dir() and not destination.is_symlink():
        shutil.rmtree(destination)
    elif destination.exists() or destination.is_symlink():
        destination.unlink()
    if directory:
        copy_tree(source, destination, root)
    else:
        copy_file(source, destination, root)


def refresh_conflict_key(conflict: Dict[str, Any]) -> Tuple[str, str]:
    return str(conflict.get("component_kind", conflict.get("kind", ""))), str(conflict.get("name", ""))


def refresh_repository(
    target: Path,
    toolkit_root: Optional[Path],
    dry_run: bool,
    complete: bool,
) -> Dict[str, Any]:
    root = git_root(target)
    state_file = root / STATE_PATH
    state = load_json(state_file)
    lifecycle = state.get("lifecycle") if isinstance(state.get("lifecycle"), dict) else {}
    refresh_state = state.get("refresh") if isinstance(state.get("refresh"), dict) else {}

    if complete:
        if refresh_state.get("status") != "needs-agent-review":
            raise ToolkitError("workspace has no pending toolkit refresh to complete")
        plan = load_json(root / REFRESH_PLAN_PATH)
        entries = plan.get("entries")
        if not isinstance(entries, list):
            raise ToolkitError("workspace refresh plan has no valid entries")
        candidate_source = refresh_state.get("candidate_source")
        previous_source = refresh_state.get("previous_source")
        if not isinstance(candidate_source, dict) or not isinstance(previous_source, dict):
            raise ToolkitError("workspace refresh provenance is incomplete")
        conflicts = lifecycle.get("conflicts") if isinstance(lifecycle.get("conflicts"), list) else []
        decisions: Dict[Tuple[str, str], Dict[str, Any]] = {
            refresh_conflict_key(item): item
            for item in conflicts
            if isinstance(item, dict) and item.get("kind") == "refresh"
        }
        for item in entries:
            if not isinstance(item, dict):
                raise ToolkitError("workspace refresh plan contains an invalid entry")
            kind, name = item.get("kind"), item.get("name")
            if not isinstance(kind, str) or not isinstance(name, str):
                raise ToolkitError("workspace refresh plan entry is missing its identity")
            staged_path_value = item.get("candidate")
            upstream_hash = item.get("upstream_sha256")
            if isinstance(staged_path_value, str) and isinstance(upstream_hash, str):
                staged_path = root / checked_relative_path(staged_path_value, "refresh candidate")
                if kind == "skill":
                    actual_hash = sha256_tree(staged_path)[0] if staged_path.is_dir() and not staged_path.is_symlink() else None
                else:
                    actual_hash = sha256_file(staged_path) if staged_path.is_file() and not staged_path.is_symlink() else None
                if actual_hash != upstream_hash:
                    raise ToolkitError(f"staged upstream candidate changed; restage before completing: {staged_path_value}")
            baseline_path_value = item.get("baseline")
            baseline_hash = item.get("baseline_sha256")
            if isinstance(baseline_path_value, str) and isinstance(baseline_hash, str):
                baseline_path = root / checked_relative_path(baseline_path_value, "refresh baseline")
                if kind == "skill":
                    actual_baseline_hash = sha256_tree(baseline_path)[0] if baseline_path.is_dir() and not baseline_path.is_symlink() else None
                else:
                    actual_baseline_hash = sha256_file(baseline_path) if baseline_path.is_file() and not baseline_path.is_symlink() else None
                if actual_baseline_hash != baseline_hash:
                    raise ToolkitError(f"staged previous baseline changed; restage before completing: {baseline_path_value}")

            conflict = decisions.get((kind, name))
            required = bool(item.get("decision_required"))
            if required and (
                not isinstance(conflict, dict)
                or not isinstance(conflict.get("decision"), str)
                or not conflict.get("decision", "").strip()
                or not isinstance(conflict.get("reason"), str)
                or not conflict.get("reason", "").strip()
            ):
                raise ToolkitError(f"record a decision and reason for the upstream change to {item.get('target')}")
            if required:
                change = item.get("change")
                if kind == "instruction" and name == CLAUDE_INSTRUCTION and change in {"added", "added-collision"}:
                    allowed = {"adopt-upstream", "exclude", "recontextualize"}
                elif kind in {"instruction", "helper"}:
                    allowed = {"adopt-upstream", "keep-workspace", "recontextualize"}
                elif kind == "skill" and change == "removed":
                    allowed = {"remove-upstream", "keep-as-local", "recontextualize"}
                elif kind == "skill" and change in {"added", "added-collision"}:
                    allowed = {"adopt-upstream", "exclude", "recontextualize"}
                elif kind == "skill":
                    allowed = {"adopt-upstream", "exclude", "keep-workspace", "recontextualize"}
                else:
                    allowed = set()
                if conflict.get("decision") not in allowed:
                    raise ToolkitError(f"invalid refresh decision for {item.get('target')}: {conflict.get('decision')}")
            if conflict:
                item["decision"] = conflict.get("decision")
                item["reason"] = conflict.get("reason")
                if conflict.get("decision") in {"adopt-upstream", "keep-workspace"}:
                    selected_hash = upstream_hash if conflict.get("decision") == "adopt-upstream" else item.get("workspace_sha256")
                    actual_hash = hash_materialized_entry(root, {"kind": kind, "target": item.get("target")})
                    if actual_hash != selected_hash:
                        expected_action = "materialize the upstream candidate" if conflict.get("decision") == "adopt-upstream" else "restore the reviewed workspace version"
                        raise ToolkitError(f"{expected_action} for {item.get('target')} before completing the refresh")

        managed = state.get("managed") if isinstance(state.get("managed"), list) else []
        managed_by_key = {
            (str(item.get("kind")), str(item.get("name"))): dict(item)
            for item in managed
            if isinstance(item, dict)
        }
        refresh_keys = {
            (str(item.get("kind")), str(item.get("name")))
            for item in entries
            if isinstance(item, dict) and item.get("change") != "workspace-only"
        }
        updated_managed: List[Dict[str, Any]] = [
            item for key, item in managed_by_key.items() if key not in refresh_keys
        ]
        for item in entries:
            if (
                not isinstance(item, dict)
                or item.get("change") != "workspace-only"
                or not isinstance(item.get("upstream_sha256"), str)
            ):
                continue
            kind, name = str(item["kind"]), str(item["name"])
            previous = managed_by_key.get((kind, name))
            if previous is None:
                continue
            live_hash = hash_materialized_entry(root, {"kind": kind, "target": item.get("target")})
            if live_hash is None:
                raise ToolkitError(f"workspace-only managed entry is missing: {item.get('target')}")
            updated = {
                **previous,
                "source": item.get("upstream_source", previous.get("source")),
                # The helper's digest validates its installed file, while
                # other managed digests record the generic toolkit source.
                "source_sha256": live_hash if kind == "helper" else item["upstream_sha256"],
                "status": "current" if live_hash == item["upstream_sha256"] else "tailored",
            }
            if kind == "skill":
                requires = item.get("upstream_requires")
                if requires:
                    updated["requires"] = list(requires)
                else:
                    updated.pop("requires", None)
            for index, managed_item in enumerate(updated_managed):
                if (managed_item.get("kind"), managed_item.get("name")) == (kind, name):
                    updated_managed[index] = updated
                    break
        exclusion_decisions = lifecycle.get("decisions") if isinstance(lifecycle.get("decisions"), list) else []
        exclusion_decisions = list(exclusion_decisions)
        # Keep unchanged, locally tailored entries in the candidate manifest
        # and staging inventory while preserving their live content.
        retained_candidates = [
            item for item in entries
            if isinstance(item, dict) and item.get("change") == "workspace-only"
            and isinstance(item.get("upstream_sha256"), str)
        ]
        candidate_skill_names: Set[str] = {
            str(item["name"]) for item in retained_candidates if item.get("kind") == "skill"
        }
        staged_values: List[str] = [
            str(item["candidate"]) for item in retained_candidates if isinstance(item.get("candidate"), str)
        ]
        for item in entries:
            if not isinstance(item, dict) or item.get("change") == "workspace-only":
                continue
            kind, name = str(item["kind"]), str(item["name"])
            upstream_hash = item.get("upstream_sha256")
            previous = managed_by_key.get((kind, name), {})
            conflict = decisions.get((kind, name), {})
            decision = str(conflict.get("decision", item.get("decision", "adopt-upstream")))
            if kind == "skill" and isinstance(upstream_hash, str):
                candidate_skill_names.add(name)
                previous = {key: value for key, value in previous.items() if key != "requires"}
                if item.get("upstream_requires"):
                    previous["requires"] = list(item["upstream_requires"])
                staged_values.append(f"{STAGING_DIRECTORY}/skills/{name}")
                target_value = previous.get("target", item.get("upstream_target"))
                if item.get("excluded"):
                    updated = {**previous, "kind": "skill", "name": name, "source": item.get("upstream_source"), "target": target_value, "source_sha256": upstream_hash, "status": "excluded"}
                elif decision == "exclude":
                    updated = {**previous, "kind": "skill", "name": name, "source": item.get("upstream_source"), "target": target_value, "source_sha256": upstream_hash, "status": "excluded"}
                    if not any(isinstance(value, dict) and value.get("kind") == "skill-exclusion" and value.get("name") == name and value.get("decision") == "exclude" for value in exclusion_decisions):
                        exclusion_decisions.append({"kind": "skill-exclusion", "name": name, "decision": "exclude", "reason": conflict.get("reason") or "Excluded during toolkit refresh."})
                else:
                    target_path = root / checked_relative_path(str(target_value), "managed skill target")
                    live_hash = sha256_tree(target_path)[0] if target_path.is_dir() and not target_path.is_symlink() else None
                    if live_hash is None:
                        raise ToolkitError(f"adopted skill is missing from the workspace: {target_value}")
                    updated = {**previous, "kind": "skill", "name": name, "source": item.get("upstream_source"), "target": target_value, "source_sha256": upstream_hash, "status": "current" if live_hash == upstream_hash else "tailored"}
                updated_managed.append(updated)
            elif kind == "skill" and upstream_hash is None:
                exclusion_reason = skill_exclusions(lifecycle).get(name)
                if item.get("excluded") and exclusion_reason:
                    target_value = previous.get("target", item.get("target"))
                    source_hash = previous.get("source_sha256", item.get("baseline_sha256"))
                    if not isinstance(source_hash, str):
                        raise ToolkitError(f"excluded retired skill lacks source provenance: {name}")
                    updated_managed.append({
                        **previous,
                        "kind": "skill",
                        "name": name,
                        "source": item.get("baseline_source", previous.get("source", "workspace-local")),
                        "target": target_value,
                        "source_sha256": source_hash,
                        "status": "excluded",
                    })
                elif decision in {"keep-as-local", "recontextualize"}:
                    target_value = previous.get("target", item.get("target"))
                    target_path = root / checked_relative_path(str(target_value), "local skill target")
                    if not target_path.is_dir() or target_path.is_symlink():
                        raise ToolkitError(f"skill selected for local retention is missing: {target_value}")
                    updated_managed.append({**previous, "kind": "skill", "name": name, "source": "workspace-local", "target": target_value, "source_sha256": sha256_tree(target_path)[0], "status": "tailored"})
                elif decision != "remove-upstream":
                    raise ToolkitError(f"record keep-as-local or remove-upstream for removed skill {item.get('target')}")
                else:
                    target_value = previous.get("target", item.get("target"))
                    target_path = root / checked_relative_path(str(target_value), "retired managed skill")
                    ensure_safe_destination(root, target_path)
                    if target_path.is_dir() and not target_path.is_symlink():
                        shutil.rmtree(target_path)
                    elif target_path.exists() or target_path.is_symlink():
                        target_path.unlink()
            elif kind == "instruction" and isinstance(upstream_hash, str):
                staged_values.append(f"{STAGING_DIRECTORY}/{name}")
                if item.get("excluded") or decision == "exclude":
                    updated_managed.append({**previous, "kind": "instruction", "name": name, "source": item.get("upstream_source"), "target": name, "source_sha256": upstream_hash, "status": "excluded"})
                    if decision == "exclude" and name not in claude_exclusions({"decisions": exclusion_decisions}):
                        exclusion_decisions.append({"kind": CLAUDE_EXCLUSION_KIND, "name": name, "decision": "exclude", "reason": conflict.get("reason") or "Excluded during toolkit refresh."})
                else:
                    live_hash = hash_materialized_entry(root, {"kind": "instruction", "target": name})
                    updated_managed.append({**previous, "kind": "instruction", "name": name, "source": item.get("upstream_source"), "target": name, "source_sha256": upstream_hash, "status": "current" if live_hash == upstream_hash else "tailored"})
            elif kind == "helper" and isinstance(upstream_hash, str):
                staged_values.append(f"{STAGING_DIRECTORY}/bin/workspace_toolkit.py")
                live_helper = root / HELPER_PATH
                if not live_helper.is_file() or live_helper.is_symlink():
                    raise ToolkitError(f"workspace helper is missing: {HELPER_PATH}")
                updated_managed.append({**previous, "kind": "helper", "name": name, "source": item.get("upstream_source"), "target": HELPER_PATH, "source_sha256": sha256_file(live_helper), "status": "current" if sha256_file(live_helper) == upstream_hash else "tailored"})

        for item in entries:
            if (
                not isinstance(item, dict)
                or item.get("kind") != "skill"
                or item.get("change") != "workspace-only"
                or item.get("upstream_sha256") is not None
            ):
                continue
            name = str(item["name"])
            previous = managed_by_key.get(("skill", name))
            target_value = previous.get("target") if previous else item.get("target")
            target_path = root / checked_relative_path(str(target_value), "workspace-local skill target")
            live_hash = sha256_tree(target_path)[0] if target_path.is_dir() and not target_path.is_symlink() else None
            if live_hash is None:
                raise ToolkitError(f"workspace-local skill is missing: {target_value}")
            updated = {
                **(previous or {}),
                "kind": "skill",
                "name": name,
                "source": "workspace-local",
                "target": str(target_value),
                "source_sha256": live_hash,
                "status": "tailored",
            }
            replaced = False
            for index, managed_item in enumerate(updated_managed):
                if (managed_item.get("kind"), managed_item.get("name")) == ("skill", name):
                    updated_managed[index] = updated
                    replaced = True
                    break
            if not replaced:
                updated_managed.append(updated)

        candidate_manifest_entries = [item for item in entries if isinstance(item, dict) and item.get("kind") == "skill" and isinstance(item.get("upstream_sha256"), str)]
        if candidate_skill_names != {str(item.get("name")) for item in candidate_manifest_entries}:
            raise ToolkitError("candidate skill inventory does not match the refresh plan")
        candidate_inventory = inventory_repository(root)
        prospective = dict(state)
        prospective["source"] = candidate_source
        prospective["managed"] = updated_managed
        prospective["staged"] = sorted(set(staged_values))
        prospective["baseline_inventory"] = candidate_inventory
        next_lifecycle = dict(lifecycle)
        next_lifecycle["status"] = "ready"
        next_lifecycle["conflicts"] = [item for item in conflicts if not isinstance(item, dict) or item.get("kind") != "refresh"]
        automatic_skill_decisions = [
            {
                "kind": "toolkit-skill-sync",
                "name": item.get("name"),
                "decision": item.get("decision"),
                "from_commit": previous_source.get("commit"),
                "to_commit": candidate_source.get("commit"),
                "reason": item.get("reason"),
            }
            for item in entries
            if isinstance(item, dict)
            and item.get("kind") == "skill"
            and item.get("change") in {"added", "removed"}
            and not item.get("excluded")
        ]
        next_lifecycle["decisions"] = exclusion_decisions + automatic_skill_decisions + [
            {
                "kind": "toolkit-refresh",
                "from_commit": previous_source.get("commit"),
                "to_commit": candidate_source.get("commit"),
                "reason": "Adopted the reviewed toolkit refresh while preserving workspace decisions.",
            }
        ]
        prospective["lifecycle"] = next_lifecycle
        next_refresh = dict(refresh_state)
        next_refresh["status"] = "complete"
        prospective["refresh"] = next_refresh
        validation, valid = validate_repository(root, state_override=prospective, inventory_override=candidate_inventory)
        if not valid:
            reasons = ", ".join(f"{item['path']}:{item['reason']}" for item in validation["errors"][:5])
            raise ToolkitError(f"workspace refresh did not validate: {reasons}")
        write_json(root / INVENTORY_PATH, candidate_inventory)
        write_json(state_file, prospective)
        write_json(root / REFRESH_PLAN_PATH, plan)
        return {"schema_version": SCHEMA_VERSION, "status": "complete", "repository": repository_identity(root), "source": candidate_source, "validation": validation}

    if lifecycle.get("status") != "ready" and refresh_state.get("status") != "needs-agent-review":
        raise ToolkitError("workspace refresh requires a ready initialized workspace")
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    if not isinstance(source.get("commit"), str) or not re.fullmatch(r"[0-9a-fA-F]{40,64}", source["commit"]):
        raise ToolkitError("workspace has no recorded adopted toolkit commit; refresh cannot guess a baseline")
    if refresh_state.get("status") == "needs-agent-review":
        existing_candidate = refresh_state.get("candidate_source")
        if not isinstance(existing_candidate, dict):
            raise ToolkitError("pending toolkit refresh provenance is incomplete")
        if toolkit_root is None:
            locator = source.get("repository_locator")
            if not isinstance(locator, str) or not (is_portable_repository_locator(locator) or Path(locator).is_absolute()):
                raise ToolkitError("workspace source has no portable toolkit repository locator")
            with tempfile.TemporaryDirectory(prefix="portable-agent-toolkit-refresh-check-") as temporary:
                candidate_root = Path(temporary) / "candidate"
                clone = subprocess.run(["git", "clone", "--quiet", "--branch", "main", "--single-branch", "--", locator, str(candidate_root)], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if clone.returncode != 0:
                    raise ToolkitError("could not clone toolkit main for refresh")
                requested_candidate, _, _ = toolkit_candidate(candidate_root, source, root, verify_clean=True)
        else:
            requested_candidate, _, _ = toolkit_candidate(toolkit_root, source, root, verify_clean=True)
        if requested_candidate.get("commit") != existing_candidate.get("commit"):
            raise ToolkitError("a different toolkit revision is already pending; complete it before restaging")
        plan = load_json(root / REFRESH_PLAN_PATH)
        entries = plan.get("entries")
        if not isinstance(entries, list):
            raise ToolkitError("workspace refresh plan has no valid entries")
        for item in entries:
            if not isinstance(item, dict):
                raise ToolkitError("workspace refresh plan contains an invalid entry")
            for field, hash_field in (("candidate", "upstream_sha256"), ("baseline", "baseline_sha256")):
                relative_value, expected_hash = item.get(field), item.get(hash_field)
                if not isinstance(relative_value, str) or not isinstance(expected_hash, str):
                    continue
                staged = root / checked_relative_path(relative_value, f"refresh {field}")
                actual_hash = sha256_tree(staged)[0] if item.get("kind") == "skill" and staged.is_dir() and not staged.is_symlink() else (sha256_file(staged) if staged.is_file() and not staged.is_symlink() else None)
                if actual_hash != expected_hash:
                    raise ToolkitError(f"staged refresh {field} changed; restage before continuing: {relative_value}")
        return {"schema_version": SCHEMA_VERSION, "status": "needs-agent-review", "idempotent": True, "previous_source": refresh_state.get("previous_source"), "candidate_source": existing_candidate, "plan_path": REFRESH_PLAN_PATH, "entries": entries}

    with tempfile.TemporaryDirectory(prefix="portable-agent-toolkit-refresh-") as temporary:
        temporary_root = Path(temporary)
        if toolkit_root is None:
            locator = source.get("repository_locator")
            if not isinstance(locator, str) or not (is_portable_repository_locator(locator) or Path(locator).is_absolute()):
                raise ToolkitError("workspace source has no portable toolkit repository locator")
            candidate_root = temporary_root / "candidate"
            clone = subprocess.run(["git", "clone", "--quiet", "--branch", "main", "--single-branch", "--", locator, str(candidate_root)], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if clone.returncode != 0:
                raise ToolkitError("could not clone toolkit main for refresh")
        else:
            candidate_root = git_root(toolkit_root)
            if candidate_root == root:
                raise ToolkitError("workspace target cannot also be the toolkit source")
        candidate_source, manifest, candidate_entries = toolkit_candidate(candidate_root, source, root, verify_clean=True)
        if toolkit_root is None:
            # The clone directory is temporary, so preserve the recorded
            # toolkit identity and locator in candidate provenance.
            candidate_source["repository"] = source.get("repository")
            candidate_source["repository_locator"] = source.get("repository_locator")
        if candidate_source.get("repository") != source.get("repository"):
            raise ToolkitError("candidate toolkit identity does not match the adopted source")
        baseline_root = temporary_root / "baseline"
        export_toolkit_revision(candidate_root, str(source["commit"]), baseline_root)
        baseline_entries, _ = refresh_source_entries(baseline_root)

        managed_list = state.get("managed") if isinstance(state.get("managed"), list) else []
        managed_by_key = {
            (str(item.get("kind")), str(item.get("name"))): item
            for item in managed_list
            if isinstance(item, dict)
        }
        old_names = {name for (kind, name) in baseline_entries if kind == "skill"}
        new_names = {name for (kind, name) in candidate_entries if kind == "skill"}
        excluded = {
            key for key, item in managed_by_key.items()
            if key[0] in {"skill", "instruction"} and item.get("status") == "excluded"
        }
        excluded.update(("skill", name) for name in skill_exclusions(lifecycle))
        all_keys = set(baseline_entries) | set(candidate_entries)
        for skill in inventory_repository(root)["skills"]:
            if skill.get("snapshot_eligible") and skill["name"] not in old_names | new_names:
                all_keys.add(("skill", skill["name"]))

        plan_entries: List[Dict[str, Any]] = []
        conflicts = [item for item in lifecycle.get("conflicts", []) if not isinstance(item, dict) or item.get("kind") != "refresh"]
        for kind, name in sorted(all_keys):
            baseline_entry = baseline_entries.get((kind, name))
            upstream_entry = candidate_entries.get((kind, name))
            workspace_entry = managed_by_key.get((kind, name))
            if kind == "skill" and workspace_entry is None and (kind, name) not in baseline_entries and (kind, name) not in candidate_entries:
                workspace_entry = {"kind": "skill", "name": name, "target": f".agents/skills/{name}", "source": "workspace-local"}
            target_value = workspace_entry.get("target") if isinstance(workspace_entry, dict) else None
            if not isinstance(target_value, str):
                target_value = (upstream_entry or baseline_entry or {}).get("upstream_target")
            if not isinstance(target_value, str):
                continue
            workspace_hash = hash_materialized_entry(root, {"kind": kind, "target": target_value})
            baseline_hash = baseline_entry.get("hash") if baseline_entry else None
            upstream_hash = upstream_entry.get("hash") if upstream_entry else None
            # An instruction this workspace never adopted (for example CLAUDE.md
            # after a refresh through an older helper) is offered as an addition.
            never_adopted = kind == "instruction" and workspace_entry is None and upstream_entry is not None
            if baseline_entry is None or never_adopted:
                change = "workspace-only" if upstream_entry is None else ("added-collision" if workspace_hash is not None else "added")
            elif upstream_entry is None:
                change = "removed"
            elif baseline_hash == upstream_hash and workspace_hash == baseline_hash:
                change = "unchanged"
            elif baseline_hash == upstream_hash:
                change = "workspace-only"
            elif workspace_hash == baseline_hash:
                change = "upstream-only"
            else:
                change = "both-changed"
            already_excluded = (kind, name) in excluded
            if already_excluded and upstream_entry is not None:
                change = "excluded"
            automatic_skill_membership = kind == "skill" and change in {"added", "removed"}
            decision_required = (
                change in {"upstream-only", "both-changed", "added", "added-collision", "removed"}
                and not already_excluded
                and not automatic_skill_membership
            )
            decision = None
            reason = None
            if already_excluded and kind == "skill":
                reason = skill_exclusions(lifecycle).get(name, "Preserved the workspace's existing skill exclusion.")
                decision = "exclude" if upstream_entry is not None else "remove-upstream"
            elif automatic_skill_membership and change == "added":
                decision = "adopt-upstream"
                reason = "Added the skill because it is part of the adopted generic toolkit set."
            elif automatic_skill_membership and change == "removed":
                decision = "remove-upstream"
                reason = "Removed the skill because it is no longer part of the adopted generic toolkit set."
            candidate_path: Optional[str] = None
            baseline_path: Optional[str] = None
            if baseline_entry:
                baseline_relative = Path(REFRESH_DIRECTORY) / "baseline"
                if kind == "instruction":
                    baseline_relative /= name
                elif kind == "skill":
                    baseline_relative /= Path("skills") / name
                else:
                    baseline_relative /= Path("bin") / "workspace_toolkit.py"
                baseline_path = baseline_relative.as_posix()
            if upstream_entry:
                if kind == "instruction":
                    candidate_relative = Path(STAGING_DIRECTORY) / name
                elif kind == "skill":
                    candidate_relative = Path(STAGING_DIRECTORY) / "skills" / name
                else:
                    candidate_relative = Path(STAGING_DIRECTORY) / "bin" / "workspace_toolkit.py"
                candidate_path = candidate_relative.as_posix()
            plan_entry = {
                "kind": kind,
                "name": name,
                "target": target_value,
                "upstream_target": upstream_entry.get("upstream_target") if upstream_entry else None,
                "baseline_source": baseline_entry.get("source") if baseline_entry else None,
                "upstream_source": upstream_entry.get("source") if upstream_entry else None,
                "upstream_requires": upstream_entry.get("requires", []) if upstream_entry else [],
                "baseline": baseline_path,
                "candidate": candidate_path,
                "baseline_sha256": baseline_hash,
                "upstream_sha256": upstream_hash,
                "workspace_sha256": workspace_hash,
                "change": change,
                "excluded": already_excluded,
                "decision_required": decision_required,
                "decision": decision,
                "reason": reason,
            }
            plan_entries.append(plan_entry)
            if decision_required:
                conflicts.append({"kind": "refresh", "component_kind": kind, "name": name, "target": target_value, "change": change, "candidate": candidate_path or baseline_path})

        if dry_run:
            return {"schema_version": SCHEMA_VERSION, "dry_run": True, "previous_source": source, "candidate_source": candidate_source, "entries": plan_entries, "decisions_required": sum(1 for item in plan_entries if item["decision_required"])}

        baseline_destination = root / REFRESH_DIRECTORY / "baseline"
        if baseline_destination.exists():
            shutil.rmtree(baseline_destination)
        for key, entry in baseline_entries.items():
            kind, name = key
            if kind == "instruction":
                destination = baseline_destination / name
            elif kind == "skill":
                destination = baseline_destination / "skills" / name
            else:
                destination = baseline_destination / "bin" / "workspace_toolkit.py"
            copy_refresh_entry(entry["path"], destination, root, entry["directory"])
        for key, entry in candidate_entries.items():
            kind, name = key
            if kind == "instruction":
                destination = root / STAGING_DIRECTORY / name
            elif kind == "skill":
                destination = root / STAGING_DIRECTORY / "skills" / name
            else:
                destination = root / STAGING_DIRECTORY / "bin" / "workspace_toolkit.py"
            copy_refresh_entry(entry["path"], destination, root, entry["directory"])
        for name in old_names - new_names:
            stale_stage = root / STAGING_DIRECTORY / "skills" / name
            if stale_stage.exists() or stale_stage.is_symlink():
                ensure_safe_destination(root, stale_stage)
                shutil.rmtree(stale_stage) if stale_stage.is_dir() and not stale_stage.is_symlink() else stale_stage.unlink()
        plan = {
            "schema_version": SCHEMA_VERSION,
            "repository": repository_identity(root),
            "previous_source": source,
            "candidate_source": candidate_source,
            "entries": plan_entries,
        }
        next_lifecycle = dict(lifecycle)
        next_lifecycle["status"] = "needs-agent-review"
        next_lifecycle["conflicts"] = conflicts
        next_state = dict(state)
        next_state["lifecycle"] = next_lifecycle
        next_refresh = dict(refresh_state)
        next_refresh.update({"status": "needs-agent-review", "previous_source": source, "candidate_source": candidate_source})
        next_state["refresh"] = next_refresh
        write_json(root / REFRESH_PLAN_PATH, plan)
        write_json(state_file, next_state)
        return {"schema_version": SCHEMA_VERSION, "status": "needs-agent-review", "repository": repository_identity(root), "previous_source": source, "candidate_source": candidate_source, "plan_path": REFRESH_PLAN_PATH, "entries": plan_entries, "conflicts": [item for item in conflicts if isinstance(item, dict) and item.get("kind") == "refresh"], "next_step": f"Use ${REQUIRED_ONBOARDING_SKILL} to recontextualize upstream changes, record decisions, validate, and complete the refresh."}


def toolkit_candidate(toolkit_root: Path, previous_source: Dict[str, Any], target_root: Path, verify_clean: bool) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[Tuple[str, str], Dict[str, Any]]]:
    candidate_root = git_root(toolkit_root)
    if candidate_root == target_root:
        raise ToolkitError("workspace target cannot also be the toolkit source")
    branch = run_git(candidate_root, ["branch", "--show-current"], check=False)
    if branch != "main":
        raise ToolkitError("toolkit refresh candidate must be checked out on main")
    if verify_clean and run_git(candidate_root, ["status", "--porcelain"]):
        raise ToolkitError("toolkit refresh candidate has uncommitted changes; use a clean main revision")
    try:
        _, _, manifest = toolkit_configuration(candidate_root)
        candidate_source = source_provenance(candidate_root, manifest)
        entries, _ = refresh_source_entries(candidate_root)
    except ToolkitError:
        raise
    return candidate_source, manifest, entries


def validate_repository(target: Path, state_override: Optional[Dict[str, Any]] = None, inventory_override: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], bool]:
    root = git_root(target)
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    state_file = root / STATE_PATH
    try:
        state = state_override if state_override is not None else load_json(state_file)
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
    # Validate the suite declared when this workspace was staged. Adding a new
    # upstream core skill must not invalidate an older, ready installation.
    declared_skills = {
        Path(value).name
        for value in state.get("staged", [])
        if isinstance(value, str)
        and len(Path(value).parts) == 4
        and Path(value).parts[:3] == (CONTROL_DIRECTORY, "staged", "skills")
        and re.fullmatch(r"[a-z0-9][a-z0-9-]*", Path(value).name)
    } if isinstance(state.get("staged"), list) else set()
    required_skills: Dict[str, str] = {
        name: (Path(".agents/skills") / name).as_posix()
        for name in (declared_skills or set(FALLBACK_SKILLS))
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
    for item in managed:
        if not isinstance(item, dict) or item.get("kind") != "skill" or item.get("status") == "excluded":
            continue
        declared = item.get("requires")
        if not isinstance(declared, list):
            continue
        for required in sorted(value for value in declared if isinstance(value, str)):
            if required in excluded_skills or required not in seen_skill_records:
                warnings.append({"path": str(item.get("target")), "reason": f"required-skill-not-adopted:{item.get('name')}->{required}"})
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

    if inventory_override is not None:
        inventory = inventory_override
    else:
        try:
            inventory = inventory_repository(root)
        except ToolkitError as exc:
            inventory = {"collisions": []}
            errors.append({"path": ".", "reason": str(exc)})
    for collision in inventory.get("collisions", []):
        warnings.append({"path": ",".join(collision["paths"]), "reason": f"duplicate-skill-name:{collision['name']}"})

    # The Claude binding is checked only once a toolkit revision that ships it
    # has been staged or adopted; older ready states keep validating as before.
    claude_records = [
        item for item in managed
        if isinstance(item, dict) and item.get("kind") == "instruction" and item.get("target") == CLAUDE_INSTRUCTION
    ]
    recorded_claude_exclusions = claude_exclusions(lifecycle)
    if len(claude_records) > 1:
        errors.append({"path": STATE_PATH, "reason": "duplicate-managed-claude-instructions"})
    elif claude_records and claude_records[0].get("status") == "excluded":
        if CLAUDE_INSTRUCTION not in recorded_claude_exclusions:
            errors.append({"path": STATE_PATH, "reason": "missing-claude-binding-exclusion-decision"})
    elif claude_records:
        if claude_records[0].get("status") not in {"current", "staged", "tailored"}:
            errors.append({"path": STATE_PATH, "reason": "invalid-managed-claude-instructions-status"})
        claude_file = root / CLAUDE_INSTRUCTION
        if not claude_file.is_file() or claude_file.is_symlink():
            errors.append({"path": CLAUDE_INSTRUCTION, "reason": "missing-or-symlinked-claude-instructions"})
        elif not imports_root_agents(claude_file.read_text(encoding="utf-8", errors="replace")):
            errors.append({"path": CLAUDE_INSTRUCTION, "reason": "claude-instructions-do-not-import-agents"})
        if CLAUDE_SKILLS_LINK not in recorded_claude_exclusions and not claude_skills_link_is_current(root):
            errors.append({"path": CLAUDE_SKILLS_LINK, "reason": "missing-or-misdirected-claude-skills-link"})
        # Claude Code skips a nested AGENTS.md beneath a root CLAUDE.md, so
        # each one needs a sibling CLAUDE.md that imports it.
        for instruction in inventory.get("instructions", []):
            relative = Path(instruction["path"])
            if relative.name != "AGENTS.md" or len(relative.parts) == 1:
                continue
            sibling = root / relative.parent / CLAUDE_INSTRUCTION
            if not sibling.is_file():
                warnings.append({"path": relative.as_posix(), "reason": "nested-agents-without-claude-instructions"})
            elif not imports_root_agents(sibling.read_text(encoding="utf-8", errors="replace")):
                warnings.append({"path": (relative.parent / CLAUDE_INSTRUCTION).as_posix(), "reason": "nested-claude-instructions-do-not-import-agents"})

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


def workspace_checkout_preferences_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))).expanduser()
    return config_home / "portable-agent-toolkit" / "workspace-checkouts.json"


def load_workspace_checkout_preferences() -> Dict[str, str]:
    path = workspace_checkout_preferences_path()
    if not path.exists():
        return {}
    document = load_json(path)
    if document.get("schema_version") != 1 or not isinstance(document.get("checkouts"), dict):
        raise ToolkitError(f"invalid workspace checkout preferences: {path}")
    preferences: Dict[str, str] = {}
    for branch, checkout in document["checkouts"].items():
        if not isinstance(branch, str) or not branch.startswith("workspace/"):
            raise ToolkitError(f"invalid workspace branch in checkout preferences: {path}")
        if not isinstance(checkout, str) or not Path(checkout).is_absolute():
            raise ToolkitError(f"checkout preference must be an absolute path: {branch}")
        preferences[branch] = str(Path(checkout).expanduser().resolve())
    return preferences


def set_workspace_checkout_preference(checkout: Path) -> Dict[str, Any]:
    root = git_root(checkout)
    identity = repository_identity(root)
    branch = snapshot_branch(identity)
    preferences = load_workspace_checkout_preferences()
    preferences[branch] = str(root)
    write_json(workspace_checkout_preferences_path(), {"schema_version": 1, "checkouts": preferences})
    return {"workspace_branch": branch, "checkout": str(root), "path": str(workspace_checkout_preferences_path())}


def remove_workspace_checkout_preference(branch: str) -> Dict[str, Any]:
    if not branch.startswith("workspace/"):
        raise ToolkitError("checkout preference key must be a workspace/* branch")
    preferences = load_workspace_checkout_preferences()
    removed = preferences.pop(branch, None)
    if removed is not None:
        write_json(workspace_checkout_preferences_path(), {"schema_version": 1, "checkouts": preferences})
    return {"workspace_branch": branch, "removed": removed is not None, "checkout": removed}


def git_common_directory(root: Path) -> Path:
    value = Path(run_git(root, ["rev-parse", "--git-common-dir"]))
    return (root / value).resolve() if not value.is_absolute() else value.resolve()


def workspace_search_roots(
    values: Optional[Sequence[Path]], replace_defaults: bool = False, existing_only: bool = True,
) -> List[Path]:
    defaults = [] if replace_defaults else [Path.home(), Path.home() / ".codex" / "worktrees"]
    candidates = defaults + list(values or [])
    roots: List[Path] = []
    seen: Set[Path] = set()
    for value in candidates:
        root = value.expanduser().resolve()
        if (not existing_only or root.is_dir()) and root not in seen:
            roots.append(root)
            seen.add(root)
    return roots


def local_git_worktrees(search_roots: Sequence[Path], max_depth: int) -> List[Dict[str, Any]]:
    found: Dict[Path, Dict[str, Any]] = {}
    excluded = EXCLUDED_DIRECTORY_NAMES | {"Applications", "Library", "Movies", "Music", "Pictures", "Public"}
    for search_root in search_roots:
        for current, directory_names, _ in os.walk(search_root, topdown=True, followlinks=False):
            root = Path(current).resolve()
            relative = root.relative_to(search_root)
            depth = len(relative.parts)
            if (root / ".git").exists() and root not in found:
                try:
                    repository = git_root(root)
                    identity = repository_identity(repository)
                    common_directory = git_common_directory(repository)
                    found[root] = {
                        "path": root,
                        "common_directory": common_directory,
                        "identity": identity,
                        "default_branch": run_git(repository, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], check=False).removeprefix("origin/"),
                    }
                except ToolkitError:
                    pass
            if depth >= max_depth:
                directory_names[:] = []
                continue
            directory_names[:] = [
                name
                for name in sorted(directory_names)
                if name not in excluded and not name.startswith(".") and not (root / name).is_symlink()
            ]
    return list(found.values())


def remote_workspace_snapshots(toolkit_root: Path, locator: str) -> List[Dict[str, Any]]:
    listed = subprocess.run(
        ["git", "-C", str(toolkit_root), "ls-remote", "--heads", "--", locator, "refs/heads/workspace/*"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if listed.returncode != 0:
        raise ToolkitError("could not list workspace snapshot branches from the toolkit remote")
    refs: List[str] = []
    for line in listed.stdout.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].startswith("refs/heads/workspace/"):
            refs.append(fields[1])
    if not refs:
        return []

    with tempfile.TemporaryDirectory(prefix="portable-agent-toolkit-workspaces-") as temporary:
        reader = Path(temporary) / "reader.git"
        subprocess.run(["git", "init", "--quiet", "--bare", str(reader)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(["git", "-C", str(reader), "remote", "add", "origin", locator], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        fetched = subprocess.run(
            ["git", "-C", str(reader), "fetch", "--quiet", "--no-tags", "--depth=1", "origin", "+refs/heads/workspace/*:refs/remotes/origin/workspace/*"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if fetched.returncode != 0:
            raise ToolkitError("could not read workspace snapshot branches from the toolkit remote")
        available = set(run_git(reader, ["for-each-ref", "--format=%(refname)", "refs/remotes/origin/workspace"]).splitlines())
        readable: List[Tuple[str, str]] = []
        for source_ref in sorted(refs):
            branch = source_ref.removeprefix("refs/heads/")
            local_ref = f"refs/remotes/origin/{branch}"
            if local_ref in available:
                readable.append((branch, local_ref))
        return read_workspace_snapshots(reader, readable)


def read_workspace_snapshots(repository: Path, refs: Sequence[Tuple[str, str]]) -> List[Dict[str, Any]]:
    """Parse snapshot manifests from (workspace branch, readable ref) pairs."""
    snapshots: List[Dict[str, Any]] = []
    for branch, ref in refs:
        result = subprocess.run(
            ["git", "-C", str(repository), "show", f"{ref}:{SNAPSHOT_MANIFEST_PATH}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            snapshots.append({"branch": branch, "status": "invalid", "reason": "missing snapshot manifest"})
            continue
        try:
            manifest = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            snapshots.append({"branch": branch, "status": "invalid", "reason": "invalid snapshot manifest"})
            continue
        identity = manifest.get("repository") if isinstance(manifest, dict) else None
        if (
            not isinstance(identity, dict)
            or any(not isinstance(identity.get(key), str) or not identity[key] for key in ("host", "owner", "name"))
            or manifest.get("branch") != branch
            or snapshot_branch(identity) != branch
        ):
            snapshots.append({"branch": branch, "status": "invalid", "reason": "snapshot identity does not match its branch"})
            continue
        snapshots.append({"branch": branch, "identity": {key: identity[key] for key in ("host", "owner", "name")}, "snapshot_repository": identity, "status": "discovered"})
    return snapshots


def local_workspace_snapshots(toolkit_root: Path) -> List[Dict[str, Any]]:
    """Read the workspace registry from the toolkit's cached origin refs."""
    refs = run_git(toolkit_root, ["for-each-ref", "--format=%(refname)", "refs/remotes/origin/workspace"]).splitlines()
    return read_workspace_snapshots(
        toolkit_root,
        [(ref.removeprefix("refs/remotes/origin/"), ref) for ref in sorted(refs) if ref],
    )


def match_workspace_targets(
    snapshots: Sequence[Dict[str, Any]],
    repositories: Sequence[Dict[str, Any]],
    excluded_common_directories: Set[Path],
    checkout_preferences: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    checkout_preferences = checkout_preferences or {}
    by_identity: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for repository in repositories:
        if repository["common_directory"] in excluded_common_directories:
            continue
        identity = repository["identity"]
        key = (str(identity["host"]), str(identity["owner"]), str(identity["name"]))
        by_identity.setdefault(key, []).append(repository)

    targets: List[Dict[str, Any]] = []
    for snapshot in snapshots:
        target = dict(snapshot)
        if snapshot.get("status") != "discovered":
            targets.append(target)
            continue
        identity = snapshot["identity"]
        key = (identity["host"], identity["owner"], identity["name"])
        candidates = by_identity.get(key, [])
        preferred_path = checkout_preferences.get(str(snapshot["branch"]))
        if preferred_path and not any(str(candidate["path"]) == preferred_path for candidate in candidates):
            try:
                preferred_root = git_root(Path(preferred_path))
                preferred_identity = repository_identity(preferred_root)
                preferred_key = tuple(str(preferred_identity.get(part, "")) for part in ("host", "owner", "name"))
                preferred_common_directory = git_common_directory(preferred_root)
                if preferred_key == key and preferred_common_directory not in excluded_common_directories:
                    candidates = [
                        *candidates,
                        {
                            "path": preferred_root,
                            "common_directory": preferred_common_directory,
                            "identity": preferred_identity,
                            "default_branch": run_git(
                                preferred_root,
                                ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
                                check=False,
                            ).removeprefix("origin/"),
                        },
                    ]
            except ToolkitError:
                pass
        groups: Dict[Path, List[Dict[str, Any]]] = {}
        for candidate in candidates:
            groups.setdefault(candidate["common_directory"], []).append(candidate)
        exact = [
            candidate for candidate in candidates
            if candidate["identity"].get("branch") == snapshot["snapshot_repository"].get("branch")
            and candidate["identity"].get("head") == snapshot["snapshot_repository"].get("head")
        ]
        selected = None
        if preferred_path:
            preferred = [candidate for candidate in candidates if str(candidate["path"]) == preferred_path]
            if len(preferred) == 1:
                selected = preferred[0]
            else:
                target.update({
                    "status": "missing",
                    "local_paths": sorted(str(item["path"]) for item in candidates),
                    "canonical_path": preferred_path,
                    "reason": "configured canonical checkout is unavailable or does not match the target repository",
                })
        elif not groups:
            target.update({"status": "missing", "local_paths": []})
        elif len(groups) > 1:
            if len(exact) == 1:
                selected = exact[0]
            else:
                target.update({"status": "ambiguous", "local_paths": sorted(str(item["path"]) for item in candidates)})
        else:
            group = next(iter(groups.values()))
            default = [item for item in group if item["identity"].get("branch") == item.get("default_branch")]
            selected = exact[0] if len(exact) == 1 else (default[0] if len(default) == 1 else sorted(group, key=lambda item: (len(item["path"].parts), str(item["path"])))[0])
        if selected is not None:
            target.update({
                "status": "ready",
                "local_path": str(selected["path"]),
                "default_branch": selected.get("default_branch"),
                "linked_worktrees": sorted(str(item["path"]) for item in groups[selected["common_directory"]]),
                "dirty": bool(run_git(selected["path"], ["status", "--porcelain"])),
            })
            secondary_paths = sorted(
                str(candidate["path"])
                for common_directory, group in groups.items()
                if common_directory != selected["common_directory"]
                for candidate in group
            )
            if secondary_paths:
                target["other_clone_paths"] = secondary_paths
        targets.append(target)
    return targets


def refresh_all_journal_path(source_commit: str) -> Path:
    state_home = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))).expanduser()
    return state_home / "portable-agent-toolkit" / "refresh-all" / f"{source_commit}.json"


def latest_incomplete_refresh_all_journal(toolkit_repository: Dict[str, Any], current_commit: str) -> Optional[Dict[str, Any]]:
    directory = refresh_all_journal_path(current_commit).parent
    candidates: List[Tuple[int, Dict[str, Any]]] = []
    if not directory.is_dir():
        return None
    for path in directory.glob("*.json"):
        if path.stem == current_commit:
            continue
        try:
            journal = load_json(path)
        except ToolkitError:
            continue
        source = journal.get("source") if isinstance(journal.get("source"), dict) else {}
        repository = source.get("repository") if isinstance(source.get("repository"), dict) else {}
        targets = journal.get("targets") if isinstance(journal.get("targets"), list) else []
        if any(repository.get(key) != toolkit_repository.get(key) for key in ("host", "owner", "name")):
            continue
        if any(isinstance(target, dict) and target.get("status") != "complete" for target in targets):
            candidates.append((path.stat().st_mtime_ns, journal))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def rollout_exposure_roots(root: Path) -> List[Path]:
    """Find parent harnesses whose instructions import files from this repo."""
    resolved_root = root.resolve()
    matches: List[Path] = []
    for parent in root.parents:
        candidates = [
            parent / "AGENTS.md",
            parent / "CLAUDE.md",
            parent / ".agents" / "skills",
            parent / CLAUDE_SKILLS_LINK,
        ]
        skill_root = parent / ".agents" / "skills"
        if skill_root.is_dir() and not skill_root.is_symlink():
            candidates.extend(path for path in skill_root.iterdir() if path.is_symlink())
        for candidate in candidates:
            if not candidate.is_symlink():
                continue
            try:
                linked = candidate.resolve(strict=False)
                if linked.is_relative_to(resolved_root):
                    matches.append(parent.resolve())
                    break
            except (OSError, RuntimeError):
                continue
    return sorted(set(matches))


def agent_configuration_path(relative: str) -> bool:
    path = Path(relative)
    if path.name in AGENT_INSTRUCTION_NAMES:
        return True
    if relative.startswith((".agents/skills/", f"{CLAUDE_SKILLS_LINK}/")) or relative == CLAUDE_SKILLS_LINK:
        return True
    return relative in {
        f"{CONTROL_DIRECTORY}/state.json",
        f"{CONTROL_DIRECTORY}/inventory.json",
        f"{CONTROL_DIRECTORY}/bin/workspace_toolkit.py",
    } or relative.startswith((f"{STAGING_DIRECTORY}/", f"{REFRESH_DIRECTORY}/")) or relative.startswith(f"{CONTROL_DIRECTORY}/staged/")


def git_configuration_tree(root: Path, revision: str) -> Dict[str, Tuple[str, str, str]]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-rz", "--full-tree", revision],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise ToolkitError(f"cannot read agent configuration at {revision}")
    files: Dict[str, Tuple[str, str, str]] = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, object_id = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8", errors="surrogateescape")
        if kind == "blob" and agent_configuration_path(path):
            files[path] = (mode, object_id, kind)
    return files


def worktree_configuration_entry(root: Path, relative: str) -> Optional[Tuple[str, str, str]]:
    path = root / relative
    if path.is_symlink():
        mode = "120000"
        content = os.fsencode(os.readlink(path))
    elif path.is_file():
        mode = "100755" if os.access(path, os.X_OK) else "100644"
        content = path.read_bytes()
    else:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "hash-object", "--stdin"],
        check=False,
        input=content,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise ToolkitError(f"cannot hash local agent configuration: {relative}")
    return mode, result.stdout.decode("ascii").strip(), "blob"


def sync_agent_configuration(source_path: Path, destination_path: Path, source_sha: str) -> Dict[str, Any]:
    """Three-way sync only agent configuration, preserving application work."""
    source_root = git_root(source_path)
    destination_root = git_root(destination_path)
    source_identity = repository_identity(source_root)
    destination_identity = repository_identity(destination_root)
    if any(source_identity.get(key) != destination_identity.get(key) for key in ("host", "owner", "name")):
        raise ToolkitError(f"source and destination repository identities differ: {destination_root}")
    if run_git(source_root, ["rev-parse", "HEAD"]) != source_sha:
        raise ToolkitError(f"agent configuration source is not at the approved commit {source_sha}: {source_root}")
    same_checkout = source_root == destination_root

    if not same_checkout:
        available = subprocess.run(
            ["git", "-C", str(destination_root), "cat-file", "-e", f"{source_sha}^{{commit}}"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if available.returncode != 0:
            fetched = subprocess.run(
                ["git", "-C", str(destination_root), "fetch", "--quiet", "--no-tags", str(source_root), source_sha],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if fetched.returncode != 0:
                raise ToolkitError(f"cannot read approved agent configuration commit in {destination_root}")

    destination_head = run_git(destination_root, ["rev-parse", "HEAD"])
    if same_checkout:
        base_sha = source_sha
    else:
        merge_base = subprocess.run(
            ["git", "-C", str(destination_root), "merge-base", destination_head, source_sha],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if merge_base.returncode != 0:
            raise ToolkitError(f"cannot find common history for agent configuration sync: {destination_root}")
        base_sha = merge_base.stdout.strip()

    status = subprocess.run(
        ["git", "-C", str(destination_root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if status.returncode != 0:
        raise ToolkitError(f"cannot inspect destination worktree: {destination_root}")
    dirty_configuration: List[str] = []
    staged_configuration: List[str] = []
    records = status.stdout.split(b"\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        path = record[3:].decode("utf-8", errors="surrogateescape")
        paths = [path]
        if record[:2].find(b"R") >= 0 or record[:2].find(b"C") >= 0:
            if index < len(records) and records[index]:
                paths.append(records[index].decode("utf-8", errors="surrogateescape"))
            index += 1
        for changed_path in paths:
            if agent_configuration_path(changed_path):
                dirty_configuration.append(changed_path)
                if record[:1] not in {b" ", b"?"}:
                    staged_configuration.append(changed_path)
    base_tree = git_configuration_tree(destination_root, base_sha)
    source_tree = git_configuration_tree(destination_root, source_sha)
    local_tree = git_configuration_tree(destination_root, destination_head)
    modified_configuration = [
        path for path in sorted(set(dirty_configuration))
        if worktree_configuration_entry(destination_root, path) != source_tree.get(path)
    ]
    if modified_configuration:
        raise ToolkitError(f"agent configuration has uncommitted edits in {destination_root}: {', '.join(modified_configuration[:8])}")
    modified_staged_configuration: List[str] = []
    for path in sorted(set(staged_configuration)):
        index_result = subprocess.run(
            ["git", "-C", str(destination_root), "ls-files", "--stage", "-z", "--", path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if index_result.returncode != 0:
            raise ToolkitError(f"cannot inspect staged agent configuration: {destination_root}")
        entries = [record for record in index_result.stdout.split(b"\0") if record]
        index_entry = None
        if entries:
            if len(entries) != 1:
                modified_staged_configuration.append(path)
                continue
            metadata, _ = entries[0].split(b"\t", 1)
            mode, object_id, stage = metadata.decode("ascii").split()
            if stage != "0":
                modified_staged_configuration.append(path)
                continue
            index_entry = (mode, object_id, "blob")
        if index_entry != source_tree.get(path):
            modified_staged_configuration.append(path)
    if modified_staged_configuration:
        raise ToolkitError(f"agent configuration has staged edits in {destination_root}: {', '.join(modified_staged_configuration[:8])}")
    if same_checkout:
        drifted = [
            path for path, entry in source_tree.items()
            if worktree_configuration_entry(destination_root, path) != entry
        ]
        if drifted:
            raise ToolkitError(f"approved source has local agent configuration edits: {', '.join(drifted[:8])}")
        return {"path": str(destination_root), "status": "passed", "source_sha": source_sha, "changed": []}
    updates: Dict[str, Optional[Tuple[str, str, str]]] = {}
    conflicts: List[str] = []
    for path in sorted(set(base_tree) | set(source_tree) | set(local_tree)):
        base_entry = base_tree.get(path)
        source_entry = source_tree.get(path)
        local_entry = local_tree.get(path)
        if source_entry == base_entry or local_entry == source_entry:
            continue
        if local_entry != base_entry:
            conflicts.append(path)
        else:
            updates[path] = source_entry
    if conflicts:
        raise ToolkitError(f"agent configuration changed on both branches in {destination_root}: {', '.join(conflicts[:8])}")

    local_path_conflicts: List[str] = []
    for relative, entry in updates.items():
        destination = destination_root / relative
        if destination.exists() and not (destination.is_file() or destination.is_dir() or destination.is_symlink()):
            local_path_conflicts.append(relative)
        if relative not in local_tree:
            existing = worktree_configuration_entry(destination_root, relative)
            if existing is not None and existing != entry:
                local_path_conflicts.append(relative)
        if destination.is_dir() and not destination.is_symlink():
            try:
                has_children = next(destination.iterdir(), None) is not None
            except OSError:
                has_children = True
            if has_children:
                local_path_conflicts.append(relative)
        if entry is None:
            continue
        cursor = destination_root
        for component in Path(relative).parts[:-1]:
            cursor = cursor / component
            if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
                parent_relative = cursor.relative_to(destination_root).as_posix()
                if updates.get(parent_relative, "not-an-update") is not None:
                    local_path_conflicts.append(relative)
                    break
    if local_path_conflicts:
        raise ToolkitError(f"untracked or structurally conflicting agent configuration in {destination_root}: {', '.join(sorted(set(local_path_conflicts))[:8])}")

    applied: List[str] = []
    for relative, entry in sorted(updates.items(), key=lambda item: (item[1] is not None, item[0])):
        destination = destination_root / relative
        cursor = destination_root
        for component in Path(relative).parts[:-1]:
            cursor = cursor / component
            if cursor.is_symlink():
                raise ToolkitError(f"refusing to write through symlinked configuration directory: {cursor}")
        if entry is None:
            if destination.is_symlink() or destination.is_file():
                destination.unlink()
            elif destination.is_dir():
                destination.rmdir()
            applied.append(relative)
            continue
        mode, object_id, _ = entry
        content = subprocess.run(
            ["git", "-C", str(destination_root), "cat-file", "blob", object_id],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if content.returncode != 0:
            raise ToolkitError(f"cannot read configuration file {relative} from approved commit")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_dir() and not destination.is_symlink():
            destination.rmdir()
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            if mode == "120000":
                os.symlink(os.fsdecode(content.stdout), temporary)
            else:
                temporary.write_bytes(content.stdout)
                if mode == "100755":
                    temporary.chmod(0o755)
            os.replace(temporary, destination)
        finally:
            if temporary.is_symlink() or temporary.exists():
                temporary.unlink()
        applied.append(relative)

    return {"path": str(destination_root), "status": "passed", "source_sha": source_sha, "base_sha": base_sha, "head": destination_head, "changed": applied}


def validated_workspace_adoption(root: Path, toolkit_source_commit: str) -> bool:
    """Accept a validated workspace-specific config that already adopted this toolkit source."""
    try:
        root = git_root(root)
        state = load_json(root / STATE_PATH)
        source = state.get("source") if isinstance(state.get("source"), dict) else {}
        if source.get("commit") != toolkit_source_commit:
            return False
        validation, valid = validate_repository(root)
        if not valid or validation.get("lifecycle_status") != "ready":
            return False
        saved_inventory = load_json(root / INVENTORY_PATH)
        current_inventory = inventory_repository(root)
        return all(
            saved_inventory.get(key) == current_inventory.get(key)
            for key in ("instructions", "skills", "warnings")
        )
    except (OSError, ToolkitError, json.JSONDecodeError):
        return False


def validate_harness_exposure(root: Path, harness_root: Path) -> List[str]:
    """Check a parent workspace exposes the target's canonical managed skills."""
    errors: List[str] = []
    root = root.resolve()
    harness_root = harness_root.resolve()
    try:
        state = load_json(root / STATE_PATH)
    except ToolkitError as exc:
        return [f"{harness_root}: cannot read source workspace state ({exc})"]
    skill_root = harness_root / ".agents" / "skills"
    managed = [
        item for item in state.get("managed", [])
        if isinstance(item, dict) and item.get("kind") == "skill" and item.get("status") != "excluded"
    ]
    if not skill_root.is_dir():
        return [f"{harness_root}: missing .agents/skills exposure"]
    for item in managed:
        name = item.get("name")
        target = item.get("target")
        if not isinstance(name, str) or not isinstance(target, str):
            errors.append(f"{harness_root}: malformed managed skill exposure")
            continue
        canonical = (root / target).resolve()
        exposed = skill_root / name
        if not (exposed / "SKILL.md").is_file() or exposed.resolve() != canonical:
            errors.append(f"{harness_root}: skill {name} is missing or points away from {canonical}")

    agents_record = next((
        item for item in state.get("managed", [])
        if isinstance(item, dict) and item.get("kind") == "instruction" and item.get("target") == "AGENTS.md"
    ), None)
    if isinstance(agents_record, dict) and agents_record.get("status") != "excluded":
        target = agents_record.get("target")
        agents_file = harness_root / str(target)
        if not isinstance(target, str):
            errors.append(f"{harness_root}: malformed Codex AGENTS.md policy record")
        else:
            try:
                if not agents_file.read_text(encoding="utf-8").strip():
                    errors.append(f"{harness_root}: empty Codex AGENTS.md policy")
            except (OSError, UnicodeError):
                errors.append(f"{harness_root}: missing or unreadable Codex AGENTS.md policy")

    claude_record = next((
        item for item in state.get("managed", [])
        if isinstance(item, dict) and item.get("kind") == "instruction" and item.get("target") == CLAUDE_INSTRUCTION
    ), None)
    claude_excluded = isinstance(claude_record, dict) and claude_record.get("status") == "excluded"
    if claude_record and not claude_excluded:
        link = harness_root / CLAUDE_SKILLS_LINK
        if not link.is_symlink() or link.resolve() != skill_root.resolve():
            errors.append(f"{harness_root}: .claude/skills does not resolve to the canonical .agents/skills tree")
        claude_file = harness_root / CLAUDE_INSTRUCTION
        if not claude_file.is_file() or not imports_root_agents(claude_file.read_text(encoding="utf-8", errors="replace")):
            errors.append(f"{harness_root}: CLAUDE.md does not load its root AGENTS.md policy")
    return errors


def check_local_rollout(
    target: Dict[str, Any],
    target_sha: str,
    toolkit_source_commit: Optional[str],
    harness_roots: Sequence[Path],
    sync_receipts: Optional[Sequence[Dict[str, Any]]] = None,
    no_harnesses: bool = False,
) -> Dict[str, Any]:
    """Verify all inventoried checkouts and linked harnesses after local sync."""
    expected_identity = target.get("identity") if isinstance(target.get("identity"), dict) else {}
    path_values: List[str] = []
    for key in ("local_path", "linked_worktrees", "other_clone_paths"):
        value = target.get(key)
        if isinstance(value, str):
            path_values.append(value)
        elif isinstance(value, list):
            path_values.extend(item for item in value if isinstance(item, str))
    checkout_paths = sorted({Path(value).expanduser().resolve() for value in path_values}, key=str)
    errors: List[str] = []
    receipts: List[Dict[str, Any]] = []
    detected_harness_roots: Dict[Path, Path] = {}

    if not checkout_paths:
        errors.append("the run did not record any local checkout paths")
    for checkout in checkout_paths:
        if not checkout.is_dir():
            errors.append(f"checkout is missing: {checkout}")
            continue
        try:
            root = git_root(checkout)
            identity = repository_identity(root)
            if not repository_identity_matches(expected_identity, identity):
                errors.append(f"repository identity changed: {checkout}")
                continue
            head = run_git(root, ["rev-parse", "HEAD"])
            default_branch = target.get("default_branch") or run_git(root, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], check=False).removeprefix("origin/")
            current_branch = run_git(root, ["branch", "--show-current"])
            if not default_branch:
                errors.append(f"cannot determine default branch for checkout: {checkout}")
            if current_branch and current_branch == default_branch:
                ancestry = subprocess.run(
                    ["git", "-C", str(root), "merge-base", "--is-ancestor", target_sha, head],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if ancestry.returncode != 0:
                    errors.append(f"default checkout does not contain rollout commit {target_sha}: {checkout}")
                    continue
            state = load_json(root / STATE_PATH)
            state_source = state.get("source") if isinstance(state.get("source"), dict) else {}
            if toolkit_source_commit and state_source.get("commit") != toolkit_source_commit:
                errors.append(f"checkout has not adopted toolkit source {toolkit_source_commit}: {checkout}")
                continue
            validation, valid = validate_repository(root)
            if not valid or validation.get("lifecycle_status") != "ready":
                reasons = [item.get("reason", "invalid workspace") for item in validation.get("errors", [])]
                errors.append(f"checkout validation failed at {checkout}: {', '.join(reasons[:5])}")
                continue
            for harness_root in rollout_exposure_roots(root):
                detected_harness_roots[harness_root] = root
            receipts.append({
                "path": str(checkout),
                "repository_root": str(root),
                "branch": current_branch or "detached",
                "head": head,
                "toolkit_source_commit": state_source.get("commit"),
                "validation": "passed",
                "worktree_status": "clean" if not run_git(root, ["status", "--porcelain", "--untracked-files=normal"]) else "contains local changes",
            })
        except (OSError, ToolkitError, json.JSONDecodeError) as exc:
            errors.append(f"cannot verify checkout {checkout}: {exc}")

    harness_receipts: List[Dict[str, str]] = []
    canonical_root = None
    if target.get("local_path"):
        try:
            canonical_root = git_root(Path(target["local_path"]))
        except ToolkitError:
            pass
    if canonical_root is not None:
        for harness_root in harness_roots:
            detected_harness_roots.setdefault(harness_root.resolve(), canonical_root)
    if no_harnesses and detected_harness_roots:
        errors.append("harness exposures were found; remove --no-harnesses and validate each harness")
    elif not detected_harness_roots and not no_harnesses:
        errors.append("no harness roots were found; pass --harness-root for each harness or declare --no-harnesses")
    for harness_root in sorted(detected_harness_roots, key=str):
        exposure_root = detected_harness_roots[harness_root]
        harness_errors = validate_harness_exposure(exposure_root, harness_root)
        errors.extend(harness_errors)
        agents_file = harness_root / "AGENTS.md"
        agents_policy = str(agents_file.resolve(strict=False)) if agents_file.is_file() else "unavailable"
        harness_receipts.append({
            "path": str(harness_root),
            "validation": "failed" if harness_errors else "passed",
            "agents_policy": agents_policy,
        })

    return {
        "status": "passed" if not errors and len(receipts) == len(checkout_paths) else "pending",
        "target_sha": target_sha,
        "toolkit_source_commit": toolkit_source_commit,
        "checked_out_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "checkouts": receipts,
        "agent_sync": list(sync_receipts or []),
        "harnesses": harness_receipts,
        "harness_inventory": "none" if no_harnesses and not detected_harness_roots else "discovered" if detected_harness_roots else "unresolved",
        "errors": errors,
    }


def repository_identity_matches(expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
    keys = ("host", "owner", "name")
    return all(isinstance(expected.get(key), str) and expected[key] and expected[key] == actual.get(key) for key in keys)


def rollout_checkout_is_selected(checkout_root: Path, source_root: Path, selected_checkouts: Set[Path]) -> bool:
    """Allow the verified source checkout or a path explicitly selected after inspection."""
    checkout = checkout_root.resolve()
    return checkout == source_root.resolve() or checkout in selected_checkouts


def fast_forward_default_checkout(checkout_root: Path, target_sha: str) -> subprocess.CompletedProcess:
    """Advance a checkout without replacing ignored local files."""
    return subprocess.run(
        ["git", "-C", str(checkout_root), "merge", "--ff-only", "--no-overwrite-ignore", "--quiet", target_sha],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def local_rollout_check(
    kind: str,
    identifier: str,
    workspace_branch: str,
    target_sha: Optional[str],
    source_path: Optional[Path],
    harness_roots: Sequence[Path],
    no_harnesses: bool = False,
    allow_checkouts: Sequence[Path] = (),
) -> Dict[str, Any]:
    if no_harnesses and harness_roots:
        raise ToolkitError("--no-harnesses cannot be combined with --harness-root")
    if kind == "refresh-all":
        if not re.fullmatch(r"[0-9a-fA-F]{40,64}", identifier):
            raise ToolkitError("refresh rollout identifier must be a full toolkit source commit")
        path = refresh_all_journal_path(identifier)
        journal = load_json(path)
        target = next((item for item in journal.get("targets", []) if item.get("branch") == workspace_branch), None)
        if target is None:
            raise ToolkitError("workspace branch is not part of this refresh run")
        expected_sha = target_sha or target.get("merge_commit")
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40,64}", expected_sha):
            raise ToolkitError("record the verified merged commit before checking local rollout")
        toolkit_source = identifier
    elif kind == "reconcile-all":
        path = reconciliation_journal_path(identifier)
        journal = load_json(path)
        target = next((item for item in journal.get("targets", []) if item.get("branch") == workspace_branch), None)
        if target is None:
            raise ToolkitError("workspace branch is not part of this reconciliation run")
        expected_sha = target_sha or target.get("target_sha")
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40,64}", expected_sha):
            raise ToolkitError("record the verified default-branch target SHA before checking local rollout")
        toolkit_source = None
    else:
        raise ToolkitError("local rollout run kind must be refresh-all or reconcile-all")

    source_root = git_root(source_path) if source_path else git_root(Path(target["local_path"]))
    expected_identity = target.get("identity") if isinstance(target.get("identity"), dict) else {}
    if not repository_identity_matches(expected_identity, repository_identity(source_root)):
        raise ToolkitError("local rollout source repository identity does not match the recorded target")
    if run_git(source_root, ["rev-parse", "HEAD"]) != expected_sha:
        raise ToolkitError(f"local rollout source must be checked out at verified target {expected_sha}")

    checkout_values: List[str] = []
    for key in ("local_path", "linked_worktrees", "other_clone_paths"):
        value = target.get(key)
        if isinstance(value, str):
            checkout_values.append(value)
        elif isinstance(value, list):
            checkout_values.extend(item for item in value if isinstance(item, str))
    sync_receipts: List[Dict[str, Any]] = []
    sync_errors: List[str] = []
    selected_checkouts = {path.expanduser().resolve() for path in allow_checkouts}
    observed_checkouts: Set[Path] = set()
    for value in sorted(set(checkout_values)):
        try:
            checkout_root = git_root(Path(value))
            observed_checkouts.add(checkout_root.resolve())
            if not repository_identity_matches(expected_identity, repository_identity(checkout_root)):
                sync_errors.append(f"repository identity changed: {checkout_root}")
                continue
            if not rollout_checkout_is_selected(checkout_root, source_root, selected_checkouts):
                sync_errors.append(f"checkout was not selected for update after inspection: {checkout_root}")
                continue
            current_branch = run_git(checkout_root, ["branch", "--show-current"])
            default_branch = target.get("default_branch") or run_git(checkout_root, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], check=False).removeprefix("origin/")
            if not default_branch:
                sync_errors.append(f"cannot determine default branch for checkout: {checkout_root}")
            elif current_branch and current_branch == default_branch:
                ancestry = subprocess.run(
                    ["git", "-C", str(checkout_root), "merge-base", "--is-ancestor", expected_sha, "HEAD"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if ancestry.returncode != 0:
                    existing_changes = run_git(checkout_root, ["status", "--porcelain", "--untracked-files=all"])
                    if existing_changes:
                        sync_errors.append(f"default checkout has local changes and was not advanced: {checkout_root}")
                    elif checkout_root != source_root:
                        available = subprocess.run(
                            ["git", "-C", str(checkout_root), "cat-file", "-e", f"{expected_sha}^{{commit}}"],
                            check=False,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        if available.returncode != 0:
                            fetched = subprocess.run(
                                ["git", "-C", str(checkout_root), "fetch", "--quiet", "--no-tags", str(source_root), expected_sha],
                                check=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                            )
                            if fetched.returncode != 0:
                                sync_errors.append(f"cannot fetch verified target commit into {checkout_root}")
                        if not any(checkout_root.as_posix() in detail for detail in sync_errors):
                            advanced = fast_forward_default_checkout(checkout_root, expected_sha)
                            if advanced.returncode != 0:
                                sync_errors.append(f"default checkout could not fast-forward to {expected_sha}: {checkout_root}")
            if toolkit_source and validated_workspace_adoption(checkout_root, toolkit_source):
                sync_receipts.append({
                    "path": str(checkout_root),
                    "status": "passed",
                    "source_sha": expected_sha,
                    "changed": [],
                    "mode": "validated-workspace-adoption",
                })
            else:
                sync_receipts.append(sync_agent_configuration(source_root, checkout_root, expected_sha))
        except (OSError, ToolkitError) as exc:
            sync_errors.append(str(exc))

    for unobserved in sorted(selected_checkouts - observed_checkouts, key=str):
        sync_errors.append(f"selected checkout was not in the recorded run inventory: {unobserved}")

    receipt = check_local_rollout(target, expected_sha, toolkit_source, harness_roots, sync_receipts, no_harnesses)
    if sync_errors:
        receipt["errors"] = [*sync_errors, *receipt.get("errors", [])]
        receipt["status"] = "pending"
    target["local_rollout"] = receipt
    target["target_sha"] = expected_sha
    if receipt["status"] == "pending":
        target["status"] = "local_sync_pending"
        target["error"] = "; ".join(receipt["errors"][:5])
    else:
        target.pop("error", None)
        target["status"] = "in_progress"
    if kind == "reconcile-all":
        journal["complete"] = all(item.get("status") == "complete" for item in journal.get("targets", []))
    write_json(path, journal)
    return {"run_id": identifier if kind == "reconcile-all" else None, "source_commit": identifier if kind == "refresh-all" else None, "workspace_branch": workspace_branch, "journal_path": str(path), "local_rollout": receipt}


def pinned_toolkit_checkout(toolkit_root: Path, source_commit: str, create: bool) -> Optional[Path]:
    current_commit = run_git(toolkit_root, ["rev-parse", "HEAD"])
    if source_commit == current_commit:
        return toolkit_root
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", source_commit):
        raise ToolkitError("pinned toolkit source is not a full Git commit id")
    present = subprocess.run(
        ["git", "-C", str(toolkit_root), "cat-file", "-e", f"{source_commit}^{{commit}}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if present.returncode != 0:
        if not create:
            return None
        fetched = subprocess.run(
            ["git", "-C", str(toolkit_root), "fetch", "--quiet", "origin", source_commit],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if fetched.returncode != 0:
            raise ToolkitError("the recorded toolkit commit is unavailable for resume")
    cache = refresh_all_journal_path(source_commit).parent / "sources" / source_commit
    if cache.exists():
        try:
            cached_root = git_root(cache)
        except ToolkitError:
            raise ToolkitError("the cached toolkit source checkout is invalid; preserve it for inspection")
        if (
            run_git(cached_root, ["rev-parse", "HEAD"]) != source_commit
            or run_git(cached_root, ["branch", "--show-current"]) != "main"
            or run_git(cached_root, ["status", "--porcelain"])
        ):
            raise ToolkitError("the cached toolkit source checkout changed; preserve it for inspection")
        return cached_root
    cache.parent.mkdir(parents=True, exist_ok=True)
    clone = subprocess.run(
        ["git", "clone", "--quiet", "--no-checkout", "--", str(toolkit_root), str(cache)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if clone.returncode != 0:
        raise ToolkitError("could not create a local checkout of the pinned toolkit source")
    checked_out = subprocess.run(
        ["git", "-C", str(cache), "checkout", "--quiet", "-B", "main", source_commit],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if checked_out.returncode != 0:
        raise ToolkitError("could not check out the pinned toolkit source")
    origin = run_git(toolkit_root, ["remote", "get-url", "origin"], check=False)
    if origin and is_portable_repository_locator(origin):
        updated_origin = subprocess.run(
            ["git", "-C", str(cache), "remote", "set-url", "origin", sanitize_repository_locator(origin)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if updated_origin.returncode != 0:
            raise ToolkitError("could not preserve the toolkit remote in its pinned source checkout")
    return cache.resolve()


def plan_all_refreshes(
    toolkit_root: Path,
    search_roots: Optional[Sequence[Path]],
    replace_search_roots: bool,
    max_depth: int,
    dry_run: bool,
    toolkit_repository: Optional[str],
) -> Dict[str, Any]:
    root = git_root(toolkit_root)
    if run_git(root, ["branch", "--show-current"]) != "main":
        raise ToolkitError("all-workspaces refresh must run from the toolkit main branch")
    if run_git(root, ["status", "--porcelain"]):
        raise ToolkitError("all-workspaces refresh requires a clean toolkit main checkout")
    _, _, current_manifest = toolkit_configuration(root)
    current_source = source_provenance(root, current_manifest)
    previous_run = latest_incomplete_refresh_all_journal(current_source.get("repository", {}), str(current_source["commit"]))
    source = previous_run.get("source") if previous_run and isinstance(previous_run.get("source"), dict) else current_source
    source_commit = str(source.get("commit") or "")
    candidate_root = pinned_toolkit_checkout(root, source_commit, create=not dry_run)
    if candidate_root is not None:
        _, _, manifest = toolkit_configuration(candidate_root)
        verified_source = source_provenance(candidate_root, manifest)
        if verified_source.get("commit") != source_commit or verified_source.get("repository") != current_source.get("repository"):
            raise ToolkitError("the pinned toolkit source identity does not match this checkout")
        source = verified_source
    journal_path = refresh_all_journal_path(source_commit)
    existing_journal = load_json(journal_path) if journal_path.is_file() else {}
    existing_source = existing_journal.get("source") if isinstance(existing_journal.get("source"), dict) else {}
    existing_locator = existing_journal.get("toolkit_repository") if existing_source.get("commit") == source_commit else None
    resumed_locator = previous_run.get("toolkit_repository") if previous_run else None
    pinned_locator = resumed_locator or existing_locator
    requested_locator = sanitize_repository_locator(toolkit_repository) if toolkit_repository else None
    if pinned_locator and requested_locator and requested_locator != pinned_locator:
        raise ToolkitError("cannot change the toolkit repository while resuming an all-workspaces refresh")
    locator = requested_locator or pinned_locator or source.get("repository_locator") or safe_repository_locator(root, current_manifest)
    locator = sanitize_repository_locator(str(locator)) if locator else None
    if not locator:
        raise ToolkitError("toolkit source has no portable origin for workspace snapshot discovery")
    snapshots = remote_workspace_snapshots(candidate_root or root, locator)
    roots = workspace_search_roots(search_roots, replace_search_roots)
    local_repositories = local_git_worktrees(roots, max_depth)
    source_common_directories = {git_common_directory(root)}
    if candidate_root is not None:
        source_common_directories.add(git_common_directory(candidate_root))
    targets = match_workspace_targets(
        snapshots, local_repositories, source_common_directories, load_workspace_checkout_preferences(),
    )

    previous_targets: Dict[str, Dict[str, Any]] = {}
    if existing_journal:
        existing_targets = existing_journal.get("targets") if isinstance(existing_journal.get("targets"), list) else []
        if existing_source.get("commit") == source.get("commit"):
            previous_targets = {
                str(item.get("branch")): item
                for item in existing_targets
                if isinstance(item, dict) and isinstance(item.get("branch"), str)
            }
    for target in targets:
        previous_target = previous_targets.get(str(target.get("branch")))
        if (
            not dry_run
            and previous_target
            and previous_target.get("status") in {"in_progress", "pr_open", "merged", "snapshot_pending", "local_sync_pending", "complete", "blocked"}
            and previous_target.get("identity") == target.get("identity")
        ):
            target.update({key: value for key, value in previous_target.items() if key not in {"branch", "identity", "snapshot_repository", "status", "local_path", "dirty", "linked_worktrees", "other_clone_paths"}})
            if previous_target.get("status") == "complete" and not (
                isinstance(previous_target.get("local_rollout"), dict)
                and previous_target["local_rollout"].get("status") == "passed"
                and previous_target["local_rollout"].get("target_sha") == previous_target.get("merge_commit")
            ):
                target["status"] = "local_sync_pending"
                target["resume_status"] = "complete"
                target["error"] = "previous completion predates local checkout and harness verification; resume at local rollout"
            elif target.get("status") == "ready" or previous_target.get("status") == "complete":
                target["status"] = previous_target["status"]
            else:
                target["resume_status"] = previous_target["status"]

    result = {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "targets": targets,
        "toolkit_repository": locator,
        "search_roots": [str(path) for path in roots],
        "journal_path": str(journal_path),
        "toolkit_checkout": str(candidate_root) if candidate_root is not None else None,
        "resuming": bool(previous_run or previous_targets),
        "dry_run": dry_run,
    }
    if not dry_run:
        write_json(journal_path, result)
    return result


def update_refresh_all_journal(
    source_commit: str,
    branch: str,
    status: str,
    receipts: Dict[str, Optional[str]],
    clear_error: bool,
) -> Dict[str, Any]:
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", source_commit):
        raise ToolkitError("source commit must be a full Git commit id")
    if status not in {"discovered", "in_progress", "pr_open", "merged", "snapshot_pending", "local_sync_pending", "complete", "blocked"}:
        raise ToolkitError("invalid all-workspaces refresh status")
    path = refresh_all_journal_path(source_commit)
    journal = load_json(path)
    target = next((item for item in journal.get("targets", []) if isinstance(item, dict) and item.get("branch") == branch), None)
    if target is None:
        raise ToolkitError("workspace branch is not part of this refresh run")
    if status == "complete":
        rollout = target.get("local_rollout") if isinstance(target.get("local_rollout"), dict) else {}
        if not target.get("snapshot_commit") or rollout.get("status") != "passed" or rollout.get("target_sha") != target.get("merge_commit"):
            raise ToolkitError("cannot complete a workspace before snapshot publication and verified local rollout")
        harness_roots = [Path(item["path"]) for item in rollout.get("harnesses", []) if isinstance(item, dict) and isinstance(item.get("path"), str)]
        current_rollout = check_local_rollout(
            target,
            str(target["merge_commit"]),
            source_commit,
            harness_roots,
            no_harnesses=rollout.get("harness_inventory") == "none",
        )
        if current_rollout.get("status") != "passed":
            target["local_rollout"] = current_rollout
            target["status"] = "local_sync_pending"
            target["error"] = "; ".join(current_rollout.get("errors", [])[:5])
            write_json(path, journal)
            raise ToolkitError("local rollout changed or no longer validates; preserve the workspace and resume local rollout")
        target["local_rollout"] = current_rollout
    target["status"] = status
    for key, value in receipts.items():
        if value:
            target[key] = value
    if clear_error:
        target.pop("error", None)
    write_json(path, journal)
    return {"source_commit": source_commit, "branch": branch, "status": status, "journal_path": str(path), "target": target}


def reconciliation_journal_path(run_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ToolkitError("reconciliation run id must be the 32-character id returned by reconcile-all")
    state_home = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))).expanduser()
    return state_home / "portable-agent-toolkit" / "reconcile-all" / f"{run_id}.json"


def archive_workspace_run(kind: str, identifier: str, reason: str) -> Dict[str, Any]:
    if not reason.strip():
        raise ToolkitError("archiving a workspace run requires a reason")
    if kind == "refresh-all":
        if not re.fullmatch(r"[0-9a-fA-F]{40,64}", identifier):
            raise ToolkitError("refresh-all archive identifier must be a full Git commit id")
        source = refresh_all_journal_path(identifier)
    elif kind == "reconcile-all":
        source = reconciliation_journal_path(identifier)
    else:
        raise ToolkitError("workspace run kind must be refresh-all or reconcile-all")

    archive_directory = source.parent / "archive"
    archive_directory.mkdir(parents=True, exist_ok=True)

    def journal_matches(path: Path) -> bool:
        if path.is_symlink():
            return False
        try:
            journal = load_json(path)
        except ToolkitError:
            return False
        if kind == "refresh-all":
            source_record = journal.get("source") if isinstance(journal.get("source"), dict) else {}
            return source_record.get("commit") == identifier
        return journal.get("run_id") == identifier

    def finish_archive(staging: Path) -> Dict[str, Any]:
        source_sha = sha256_file(staging)
        archived = archive_directory / source.name
        if archived.is_symlink() or (archived.exists() and sha256_file(archived) != source_sha):
            archived = archive_directory / f"{source.stem}.{source_sha}{source.suffix}"
        if archived.is_symlink():
            raise ToolkitError(f"archive destination is a symlink; journal remains staged: {archived}")
        if archived.exists():
            if sha256_file(archived) != source_sha:
                # Keep the staged bytes intact if even the full-content name
                # collides; preserving the journal is safer than replacing history.
                raise ToolkitError(f"an archive with different contents already exists: {archived}")
            staging.unlink()
        else:
            os.replace(staging, archived)
        if sha256_file(archived) != source_sha:
            raise ToolkitError(f"archived workspace run did not verify: {archived}")

        receipt_path = archive_directory / f"{archived.name}.archive.json"
        if receipt_path.exists():
            receipt = load_json(receipt_path)
            if (
                receipt.get("sha256") != source_sha
                or receipt.get("kind") != kind
                or receipt.get("identifier") != identifier
            ):
                raise ToolkitError(f"archive receipt does not match workspace run: {receipt_path}")
        else:
            receipt = {
                "schema_version": 1,
                "kind": kind,
                "identifier": identifier,
                "original_path": str(source),
                "archived_path": str(archived),
                "sha256": source_sha,
                "reason": reason.strip(),
                "archived_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            write_json(receipt_path, receipt)
        return receipt

    def find_prior_archive() -> Optional[Dict[str, Any]]:
        recovered: List[Dict[str, Any]] = []
        pending_paths = sorted(archive_directory.glob(f".{source.name}.*.pending"))
        for pending in pending_paths:
            if journal_matches(pending):
                recovered.append(finish_archive(pending))
        if recovered:
            return recovered[-1]

        receipts = sorted(archive_directory.glob("*.archive.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
        for candidate_receipt in receipts:
            try:
                prior = load_json(candidate_receipt)
                archived_path = Path(str(prior.get("archived_path") or ""))
                if (
                    prior.get("kind") == kind
                    and prior.get("identifier") == identifier
                    and not archived_path.is_symlink()
                    and archived_path.is_file()
                    and sha256_file(archived_path) == prior.get("sha256")
                ):
                    return prior
            except (ToolkitError, OSError):
                continue
        candidates = [archive_directory / source.name]
        candidates.extend(sorted(archive_directory.glob(f"{source.stem}.*{source.suffix}")))
        for archived_path in candidates:
            if not archived_path.is_file() or archived_path.name.endswith(".archive.json") or not journal_matches(archived_path):
                continue
            source_sha = sha256_file(archived_path)
            receipt_path = archive_directory / f"{archived_path.name}.archive.json"
            receipt = {
                "schema_version": 1,
                "kind": kind,
                "identifier": identifier,
                "original_path": str(source),
                "archived_path": str(archived_path),
                "sha256": source_sha,
                "reason": reason.strip(),
                "archived_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            write_json(receipt_path, receipt)
            return receipt
        return None

    if source.is_symlink():
        raise ToolkitError(f"refusing to archive a symlinked workspace run journal: {source}")
    if not source.is_file():
        prior = find_prior_archive()
        if prior is None:
            raise ToolkitError(f"workspace run journal not found: {source}")
        return {"archived": True, "already_archived": True, **prior}

    # Move the journal atomically before verifying or writing its receipt. A
    # concurrent atomic journal update can then recreate `source`; it cannot
    # be deleted by this archival operation after the move.
    staging = archive_directory / f".{source.name}.{uuid.uuid4().hex}.pending"
    try:
        os.replace(source, staging)
    except FileNotFoundError:
        prior = find_prior_archive()
        if prior is None:
            raise ToolkitError(f"workspace run journal not found: {source}")
        return {"archived": True, "already_archived": True, **prior}
    if staging.is_symlink():
        if not source.exists():
            os.replace(staging, source)
        raise ToolkitError(f"refusing to archive a symlinked workspace run journal: {source}")

    receipt = finish_archive(staging)
    return {
        "archived": True,
        "already_archived": False,
        "active_journal_preserved": source.is_file(),
        **receipt,
    }


def reconciliation_refs(root: Path, previous: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Observe cached refs only; the agent verifies ownership before fetching."""
    listing = run_git(root, ["for-each-ref", "--format=%(refname)\t%(objectname)\t%(symref)", "refs/heads", "refs/remotes"])
    refs: Dict[str, Any] = {}
    changed = False
    for line in listing.splitlines():
        ref, sha, *symbolic = line.split("\t")
        if symbolic and symbolic[0]:
            continue
        old = previous.get(ref, {})
        if old.get("observed_sha") == sha and old.get("present", True):
            entry = dict(old)
        else:
            entry = {"observed_sha": sha, "status": "unreviewed"}
            if old:
                entry["history"] = [*old.get("history", []), {key: value for key, value in old.items() if key != "history"}]
            changed = True
        entry["present"] = True
        refs[ref] = entry
    for ref, old in previous.items():
        if ref not in refs:
            refs[ref] = {**old, "present": False}
            if old.get("present", True) and old.get("status") != "cleaned":
                refs[ref]["status"] = "unreviewed"
                changed = True
    return refs, changed


def plan_all_reconciliations(
    toolkit_root: Path,
    search_roots: Optional[Sequence[Path]],
    replace_search_roots: bool,
    max_depth: int,
    dry_run: bool,
    toolkit_repository: Optional[str],
    run_id: Optional[str],
    new_run: bool,
) -> Dict[str, Any]:
    root = git_root(toolkit_root)
    if run_git(root, ["branch", "--show-current"]) != "main" or run_git(root, ["status", "--porcelain"]):
        raise ToolkitError("all-repositories reconciliation requires a clean toolkit main checkout")
    _, _, manifest = toolkit_configuration(root)
    locator = sanitize_repository_locator(toolkit_repository) if toolkit_repository else safe_repository_locator(root, manifest)
    if not locator:
        raise ToolkitError("toolkit source has no origin for workspace discovery")
    roots = workspace_search_roots(search_roots, replace_search_roots, existing_only=False)
    scope = {"toolkit_repository": locator, "search_roots": [str(path) for path in roots], "max_depth": max_depth}
    previous: Dict[str, Any] = {}
    if run_id:
        previous = load_json(reconciliation_journal_path(run_id))
        if previous.get("scope") != scope:
            raise ToolkitError("cannot change the registry or search scope while resuming reconciliation")
    elif not new_run:
        directory = reconciliation_journal_path("0" * 32).parent
        candidates = []
        if directory.is_dir():
            for path in directory.glob("*.json"):
                if not re.fullmatch(r"[0-9a-f]{32}", path.stem):
                    continue
                try:
                    journal = load_json(path)
                except ToolkitError:
                    continue
                if journal.get("run_id") != path.stem:
                    continue
                if journal.get("scope") == scope and not journal.get("complete"):
                    candidates.append((path.stat().st_mtime_ns, journal))
        if candidates:
            previous = max(candidates, key=lambda item: item[0])[1]
    run_id = str(previous["run_id"]) if previous else uuid.uuid4().hex
    journal_path = reconciliation_journal_path(run_id)
    snapshots = remote_workspace_snapshots(root, locator)
    targets = match_workspace_targets(
        snapshots,
        local_git_worktrees(roots, max_depth),
        {git_common_directory(root)},
        load_workspace_checkout_preferences(),
    )
    if previous:
        current_targets = {target["branch"]: target for target in targets}
        targets = []
        for old in previous["targets"]:
            current = current_targets.get(old["branch"])
            if current is None or current.get("identity") != old.get("identity"):
                current = {"branch": old["branch"], "identity": old.get("identity"), "status": "unregistered"}
            targets.append(current)

    old_targets = {target["branch"]: target for target in previous.get("targets", [])}
    for target in targets:
        old = old_targets.get(target["branch"], {})
        target["discovery_status"] = target["status"]
        target["branches"] = old.get("branches", {})
        for key in ("pr_url", "merge_commit", "target_sha", "reason", "error"):
            if key in old:
                target.setdefault(key, old[key])
        if target["status"] != "ready":
            if old:
                target["resume_status"] = old.get("status")
            continue
        try:
            branches, changed = reconciliation_refs(Path(target["local_path"]), target["branches"])
            target["branches"] = branches
            restored = old.get("discovery_status") != "ready"
            target["status"] = "ready" if changed or restored else old.get("status", "ready")
            if target["status"] == "complete":
                rollout = old.get("local_rollout") if isinstance(old.get("local_rollout"), dict) else {}
                if not target.get("target_sha") or rollout.get("status") != "passed" or rollout.get("target_sha") != target.get("target_sha"):
                    target["status"] = "local_sync_pending"
                    target["error"] = "previous completion has no verified local rollout; resume local rollout"
        except ToolkitError as error:
            target.update({"status": "blocked", "error": str(error)})
    result = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "scope": scope,
        "toolkit_commit": previous.get("toolkit_commit") or run_git(root, ["rev-parse", "HEAD"]),
        "targets": targets,
        "journal_path": str(journal_path),
        "resuming": bool(previous),
        "dry_run": dry_run,
        "complete": all(target["status"] == "complete" for target in targets),
    }
    if not dry_run:
        write_json(journal_path, result)
    return result


def update_reconciliation_journal(
    run_id: str,
    workspace_branch: str,
    status: str,
    ref: Optional[str],
    observed_sha: Optional[str],
    receipts: Dict[str, Optional[str]],
    clear_error: bool,
) -> Dict[str, Any]:
    path = reconciliation_journal_path(run_id)
    journal = load_json(path)
    target = next((item for item in journal["targets"] if item["branch"] == workspace_branch), None)
    if target is None:
        raise ToolkitError("workspace is not part of this reconciliation run")
    entry = target
    if ref:
        entry = target["branches"].get(ref)
        if entry is None or not observed_sha or entry.get("observed_sha") != observed_sha:
            raise ToolkitError("ref or observed SHA does not match the inventory; re-observe before recording progress")
        if status not in {"in_progress", "pr_open", "merged", "cleaned", "preserved", "blocked"}:
            raise ToolkitError("invalid branch reconciliation status")
        if status in {"preserved", "blocked"} and not (receipts.get("reason") or receipts.get("error")):
            raise ToolkitError("preserved or blocked branches require a reason or error")
    else:
        if observed_sha or status not in {"in_progress", "local_sync_pending", "complete", "blocked"}:
            raise ToolkitError("invalid workspace status or observed SHA without a ref")
        if status == "complete" and (
            target["discovery_status"] != "ready"
            or any(item["status"] not in {"cleaned", "preserved"} for item in target["branches"].values())
        ):
            raise ToolkitError("cannot complete a workspace with unavailable discovery or unaccounted branches")
        if status == "complete":
            rollout = target.get("local_rollout") if isinstance(target.get("local_rollout"), dict) else {}
            if not target.get("target_sha") or rollout.get("status") != "passed" or rollout.get("target_sha") != target.get("target_sha"):
                raise ToolkitError("cannot complete a workspace before verified local rollout")
            harness_roots = [Path(item["path"]) for item in rollout.get("harnesses", []) if isinstance(item, dict) and isinstance(item.get("path"), str)]
            current_rollout = check_local_rollout(
                target,
                str(target["target_sha"]),
                None,
                harness_roots,
                no_harnesses=rollout.get("harness_inventory") == "none",
            )
            if current_rollout.get("status") != "passed":
                target["local_rollout"] = current_rollout
                target["status"] = "blocked"
                target["error"] = "; ".join(current_rollout.get("errors", [])[:5])
                journal["complete"] = False
                write_json(path, journal)
                raise ToolkitError("local rollout changed or no longer validates; preserve the workspace and resume local rollout")
            target["local_rollout"] = current_rollout
    entry["status"] = status
    for key, value in receipts.items():
        if value:
            entry[key] = value
    if clear_error:
        entry.pop("error", None)
    if ref:
        target["status"] = "in_progress"
    journal["complete"] = all(item["status"] == "complete" for item in journal["targets"])
    write_json(path, journal)
    return {"run_id": run_id, "journal_path": str(path), "target": target}


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


UPSTREAM_DECISION_PREFIXES = ("adopt", "accept")
UPSTREAM_DECISIONS = {"exclude", "remove-upstream"}


def is_tailoring_decision(decision: str) -> bool:
    """Workspaces record tailoring in free-form words; only adoption and removal follow upstream."""
    return not decision.startswith(UPSTREAM_DECISION_PREFIXES) and decision not in UPSTREAM_DECISIONS


@contextlib.contextmanager
def read_only_git() -> Iterator[None]:
    """Stop `git status` from refreshing index files while status inspects checkouts."""
    previous = os.environ.get("GIT_OPTIONAL_LOCKS")
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("GIT_OPTIONAL_LOCKS", None)
        else:
            os.environ["GIT_OPTIONAL_LOCKS"] = previous


def latest_refresh_all_journal(toolkit_repository: Dict[str, Any]) -> Optional[Tuple[Path, Dict[str, Any]]]:
    """Return the most recently written refresh-all journal for this toolkit."""
    directory = refresh_all_journal_path("0" * 40).parent
    if not directory.is_dir():
        return None
    candidates: List[Tuple[int, Path, Dict[str, Any]]] = []
    for path in directory.glob("*.json"):
        if not re.fullmatch(r"[0-9a-fA-F]{40,64}", path.stem) or path.is_symlink():
            continue
        try:
            journal = load_json(path)
        except ToolkitError:
            continue
        source = journal.get("source") if isinstance(journal.get("source"), dict) else {}
        repository = source.get("repository") if isinstance(source.get("repository"), dict) else {}
        if not isinstance(journal.get("targets"), list):
            continue
        if any(repository.get(key) != toolkit_repository.get(key) for key in ("host", "owner", "name")):
            continue
        candidates.append((path.stat().st_mtime_ns, path, journal))
    if not candidates:
        return None
    _, path, journal = max(candidates, key=lambda item: item[0])
    return path, journal


def toolkit_hashes_at(toolkit_root: Path, commit: str, cache: Dict[str, Optional[Dict[Tuple[str, str], str]]]) -> Optional[Dict[Tuple[str, str], str]]:
    """Hash each managed toolkit component exactly as refresh does, at one commit."""
    if commit not in cache:
        try:
            with tempfile.TemporaryDirectory(prefix="portable-agent-toolkit-status-") as temporary:
                exported = Path(temporary) / "toolkit"
                export_toolkit_revision(toolkit_root, commit, exported)
                entries, _ = refresh_source_entries(exported)
                cache[commit] = {key: str(entry["hash"]) for key, entry in entries.items()}
        except (OSError, ToolkitError):
            cache[commit] = None
    return cache[commit]


def recorded_tailoring_decision(
    state: Dict[str, Any],
    plan: Dict[str, Any],
    kind: str,
    name: str,
    target: str,
) -> Optional[Dict[str, Any]]:
    """Find the latest decision recorded for one managed entry."""
    lifecycle = state.get("lifecycle") if isinstance(state.get("lifecycle"), dict) else {}
    records: List[Dict[str, Any]] = []
    for field in ("decisions", "conflicts"):
        values = lifecycle.get(field)
        if isinstance(values, list):
            records.extend(
                item for item in values
                if isinstance(item, dict) and (item.get("name") == name or item.get("target") == target)
            )
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    candidate = plan.get("candidate_source") if isinstance(plan.get("candidate_source"), dict) else {}
    # The refresh plan that produced the adopted commit holds its newest review decisions.
    if candidate.get("commit") and candidate.get("commit") == source.get("commit") and isinstance(plan.get("entries"), list):
        records.extend(
            item for item in plan["entries"]
            if isinstance(item, dict) and item.get("kind") == kind and item.get("name") == name
        )
    selected = None
    for record in records:
        if isinstance(record.get("decision"), str) and record["decision"].strip():
            selected = record
    if selected is None:
        return None
    decision = selected["decision"].strip()
    return {"decision": decision, "tailoring": is_tailoring_decision(decision)}


def workspace_local_changes(root: Path, state: Dict[str, Any], upstream: Dict[Tuple[str, str], str]) -> List[Dict[str, Any]]:
    """List managed files that differ from the toolkit at the adopted commit."""
    try:
        plan = load_json(root / REFRESH_PLAN_PATH) if (root / REFRESH_PLAN_PATH).is_file() else {}
    except ToolkitError:
        plan = {}
    changes: List[Dict[str, Any]] = []
    managed = state.get("managed") if isinstance(state.get("managed"), list) else []
    for item in managed:
        if not isinstance(item, dict) or item.get("status") == "excluded" or item.get("source") == "workspace-local":
            continue
        kind, name, target = item.get("kind"), item.get("name"), item.get("target")
        if not all(isinstance(value, str) for value in (kind, name, target)):
            continue
        upstream_hash = upstream.get((kind, name))
        if upstream_hash is None:
            continue
        try:
            live_hash = hash_materialized_entry(root, item)
        except ToolkitError:
            live_hash = None
        if live_hash == upstream_hash:
            continue
        decision = recorded_tailoring_decision(state, plan, kind, name, target)
        explained = bool(decision and decision["tailoring"])
        changes.append({
            "kind": kind,
            "name": name,
            "target": target,
            "live_sha256": live_hash,
            "upstream_sha256": upstream_hash,
            "decision": decision["decision"] if decision else None,
            "explained": explained,
        })
    return changes


def changed_file_count(root: Path) -> int:
    output = run_git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    return len([line for line in output.splitlines() if line.strip()])


def workspace_status(
    toolkit_target: Path,
    search_roots: Optional[Sequence[Path]],
    replace_search_roots: bool,
    max_depth: int,
    fetch: bool,
) -> Dict[str, Any]:
    """Report how far each registered workspace is from toolkit main. Read-only unless fetch is set."""
    root = git_root(toolkit_target)
    toolkit_configuration(root)
    toolkit_identity = repository_identity(root)
    toolkit_repository = {key: toolkit_identity[key] for key in ("host", "owner", "name")}
    if fetch:
        fetched = subprocess.run(
            [
                "git", "-C", str(root), "fetch", "--quiet", "--no-tags", "--prune", "origin",
                "+refs/heads/main:refs/remotes/origin/main",
                "+refs/heads/workspace/*:refs/remotes/origin/workspace/*",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if fetched.returncode != 0:
            raise ToolkitError("could not fetch toolkit main and workspace branches from origin")

    with read_only_git():
        main_ref = next(
            (ref for ref in ("refs/remotes/origin/main", "refs/heads/main") if run_git(root, ["rev-parse", "--verify", "--quiet", ref], check=False)),
            None,
        )
        if main_ref is None:
            raise ToolkitError("toolkit has no main or origin/main ref")
        main_commit = run_git(root, ["rev-parse", main_ref])
        snapshots = local_workspace_snapshots(root)
        roots = workspace_search_roots(search_roots, replace_search_roots)
        targets = match_workspace_targets(
            snapshots,
            local_git_worktrees(roots, max_depth),
            {git_common_directory(root)},
            load_workspace_checkout_preferences(),
        )
        latest = latest_refresh_all_journal(toolkit_repository)
        journal_path, journal = latest if latest else (None, {})
        journal_targets = {
            str(item["branch"]): item
            for item in journal.get("targets", [])
            if isinstance(item, dict) and isinstance(item.get("branch"), str)
        }
        registered = {str(item.get("branch")) for item in targets}
        for branch, item in sorted(journal_targets.items()):
            # A workspace the last batch run tracked stays visible even if its
            # registry ref is not cached locally, so blocked work is not hidden.
            if branch not in registered:
                targets.append({
                    "branch": branch,
                    "identity": item.get("identity"),
                    "status": "journal-only",
                    "canonical_path": item.get("local_path"),
                })

        hash_cache: Dict[str, Optional[Dict[Tuple[str, str], str]]] = {}
        workspaces: List[Dict[str, Any]] = []
        for target in sorted(targets, key=lambda item: str(item.get("branch"))):
            branch = str(target.get("branch"))
            identity = target.get("identity") if isinstance(target.get("identity"), dict) else {}
            journal_target = journal_targets.get(branch)
            path_value = target.get("local_path") or target.get("canonical_path") or (journal_target or {}).get("local_path")
            path = Path(str(path_value)) if path_value else None
            row: Dict[str, Any] = {
                "branch": branch,
                "repository": "/".join(str(identity.get(key)) for key in ("owner", "name")) if identity else branch.removeprefix("workspace/"),
                "registry": "journal-only" if target.get("status") == "journal-only" else ("invalid" if target.get("status") == "invalid" else "snapshot-branch"),
                "match": target.get("status"),
                "path": str(path) if path else None,
                "exists": bool(path and path.is_dir()),
                "adopted_commit": None,
                "adopted_version": None,
                "behind": None,
                "journal": None,
                "changed_files": None,
                "local_changes": [],
                "unexplained_changes": 0,
                "notes": [],
            }
            if target.get("status") == "invalid":
                row["notes"].append(str(target.get("reason", "invalid registry entry")))
            if target.get("status") == "ambiguous":
                row["notes"].append("ambiguous local checkouts: " + ", ".join(target.get("local_paths", [])) + "; choose one with checkout-path set")
            if target.get("status") == "missing" and target.get("reason"):
                row["notes"].append(str(target["reason"]))
            if journal_target:
                row["journal"] = {
                    "source_commit": (journal.get("source") or {}).get("commit") if isinstance(journal.get("source"), dict) else None,
                    "status": journal_target.get("status"),
                    "error": journal_target.get("error"),
                }
            checkout = None
            if row["exists"] and path is not None:
                try:
                    checkout = git_root(path)
                    if repository_identity_matches(identity, repository_identity(checkout)) or not identity:
                        row["changed_files"] = changed_file_count(checkout)
                    else:
                        row["notes"].append("checkout identity does not match the registered repository")
                        checkout = None
                except ToolkitError as exc:
                    row["notes"].append(f"cannot read checkout: {exc}")
                    checkout = None
            if checkout is not None:
                try:
                    state = load_json(checkout / STATE_PATH)
                except ToolkitError:
                    state = {}
                    row["notes"].append("no readable toolkit state; workspace is not onboarded here")
                source = state.get("source") if isinstance(state.get("source"), dict) else {}
                adopted = source.get("commit") if isinstance(source.get("commit"), str) else None
                row["adopted_commit"] = adopted
                row["adopted_version"] = source.get("version")
                refresh_state = state.get("refresh") if isinstance(state.get("refresh"), dict) else {}
                if refresh_state.get("status") == "needs-agent-review":
                    row["notes"].append("a staged toolkit refresh is awaiting review")
                if adopted and re.fullmatch(r"[0-9a-fA-F]{40,64}", adopted):
                    present = subprocess.run(
                        ["git", "-C", str(root), "cat-file", "-e", f"{adopted}^{{commit}}"],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if present.returncode == 0:
                        row["behind"] = int(run_git(root, ["rev-list", "--count", f"{adopted}..{main_commit}"]))
                        upstream = toolkit_hashes_at(root, adopted, hash_cache)
                        if upstream is None:
                            row["notes"].append("cannot reconstruct toolkit files at the adopted commit")
                        else:
                            row["local_changes"] = workspace_local_changes(checkout, state, upstream)
                            row["unexplained_changes"] = sum(1 for item in row["local_changes"] if not item["explained"])
                    else:
                        row["notes"].append("adopted commit is not in the local toolkit clone; rerun with --fetch")
            workspaces.append(row)

    return {
        "schema_version": SCHEMA_VERSION,
        "toolkit": {
            "path": str(root),
            "repository": toolkit_repository,
            "main_ref": main_ref,
            "main_commit": main_commit,
            "fetched": fetch,
        },
        "journal_path": str(journal_path) if journal_path else None,
        "search_roots": [str(path) for path in roots],
        "workspaces": workspaces,
    }


def run_label(journal: Dict[str, Any], adopted: Optional[str]) -> str:
    """The latest refresh-all state, marked when that run targeted a different commit.

    A workspace refreshed since that run (for example by a single-workspace refresh)
    would otherwise read as blocked even though it is current.
    """
    status = journal.get("status")
    if not status:
        return "-"
    source = journal.get("source_commit")
    if source and adopted and not adopted.startswith(source[:7]) and not source.startswith(adopted[:7]):
        return f"{status} @{source[:7]}"
    return str(status)


def format_workspace_status(report: Dict[str, Any]) -> str:
    headers = ("WORKSPACE", "ADOPTED", "BEHIND", "RUN", "DIRTY", "NOT UPSTREAMED", "PATH")
    rows: List[Tuple[str, ...]] = []
    details: List[str] = []
    for item in report["workspaces"]:
        journal = item.get("journal") or {}
        adopted = item.get("adopted_commit")
        path = item.get("path") or "-"
        if item.get("path") and not item.get("exists"):
            path += " (missing)"
        rows.append((
            item["repository"],
            adopted[:7] if adopted else "-",
            str(item["behind"]) if item.get("behind") is not None else "-",
            run_label(journal, adopted),
            str(item["changed_files"]) if item.get("changed_files") is not None else "-",
            str(item["unexplained_changes"]),
            path,
        ))
        if journal.get("status") not in (None, "complete") and journal.get("error"):
            details.append(f"{item['repository']}: {run_label(journal, adopted)}: {journal['error']}")
        for change in item.get("local_changes", []):
            if not change["explained"]:
                decision = f"recorded decision {change['decision']}" if change.get("decision") else "no tailoring decision"
                details.append(f"{item['repository']}: not upstreamed: {change['kind']} {change['target']} ({decision})")
        for note in item.get("notes", []):
            details.append(f"{item['repository']}: {note}")
    widths = [max(len(header), *(len(row[index]) for row in rows)) if rows else len(header) for index, header in enumerate(headers)]
    lines = ["  ".join(value.ljust(widths[index]) for index, value in enumerate(headers)).rstrip()]
    lines.extend("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)).rstrip() for row in rows)
    toolkit = report["toolkit"]
    lines.append("")
    lines.append(
        f"toolkit main {toolkit['main_commit'][:7]} ({toolkit['main_ref']}); registry read from local refs"
        + ("" if toolkit["fetched"] else "; pass --fetch to update")
    )
    lines.append(f"latest refresh-all journal: {report['journal_path'] or 'none'}")
    if details:
        lines.append("")
        lines.extend(details)
    return "\n".join(lines) + "\n"


def print_json(value: Dict[str, Any]) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portable agent toolkit workspace helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="inventory agent instructions and skills")
    inventory_parser.add_argument("target", nargs="?", default=".")

    init_parser = subparsers.add_parser("init", help="stage a repository-scoped toolkit onboarding")
    init_parser.add_argument("target", nargs="?", default=".")
    init_parser.add_argument("--toolkit-root", default=str(Path(__file__).resolve().parent.parent))
    init_parser.add_argument("--dry-run", action="store_true")

    checkout_parser = subparsers.add_parser(
        "checkout-path",
        help="view or change the machine-local canonical checkout for a workspace",
    )
    checkout_modes = checkout_parser.add_subparsers(dest="checkout_action", required=True)
    checkout_set = checkout_modes.add_parser("set", help="select a repository checkout as canonical")
    checkout_set.add_argument("path", type=Path)
    checkout_remove = checkout_modes.add_parser("remove", help="clear a canonical checkout preference")
    checkout_remove.add_argument("workspace_branch")
    checkout_modes.add_parser("list", help="show saved canonical checkout preferences")

    validate_parser = subparsers.add_parser("validate", help="validate initialized workspace topology")
    validate_parser.add_argument("target", nargs="?", default=".")

    refresh_parser = subparsers.add_parser("refresh", help="stage or complete a reviewed upstream toolkit refresh")
    refresh_parser.add_argument("target", nargs="?", default=".")
    refresh_parser.add_argument("--toolkit-root", help="use a specific clean toolkit clone instead of recorded main")
    refresh_mode = refresh_parser.add_mutually_exclusive_group()
    refresh_mode.add_argument("--dry-run", action="store_true")
    refresh_mode.add_argument("--complete", action="store_true")

    snapshot_parser = subparsers.add_parser("snapshot", help="snapshot workspace agent files to a workspace branch")
    snapshot_parser.add_argument("target", nargs="?", default=".")
    snapshot_parser.add_argument("--toolkit-repo")
    snapshot_parser.add_argument("--push", action="store_true")

    refresh_all_parser = subparsers.add_parser(
        "refresh-all",
        help="discover workspace snapshot branches and matching local repositories",
    )
    refresh_all_parser.add_argument("target", nargs="?", default=".")
    refresh_all_parser.add_argument("--search-root", action="append", type=Path, help="add a local repository discovery root; may be repeated")
    refresh_all_parser.add_argument("--replace-search-roots", action="store_true", help="search only roots supplied with --search-root")
    refresh_all_parser.add_argument("--toolkit-repo", help="select the toolkit repository for workspace discovery and snapshot publication")
    refresh_all_parser.add_argument("--max-depth", type=int, default=8, help="maximum directory depth under each search root")
    refresh_all_parser.add_argument("--dry-run", action="store_true", help="discover targets without writing the local run journal")

    status_parser = subparsers.add_parser(
        "status",
        help="show how far each registered workspace is behind toolkit main without changing anything",
    )
    status_parser.add_argument("target", nargs="?", default=".", help="toolkit checkout")
    status_parser.add_argument("--fetch", action="store_true", help="fetch toolkit main and workspace branches from origin first")
    status_parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    status_parser.add_argument("--search-root", action="append", type=Path, help="add a local repository discovery root; may be repeated")
    status_parser.add_argument("--replace-search-roots", action="store_true", help="search only roots supplied with --search-root")
    status_parser.add_argument("--max-depth", type=int, default=8, help="maximum directory depth under each search root")

    refresh_all_mark_parser = subparsers.add_parser(
        "refresh-all-mark",
        help="record progress and receipts for one workspace in an all-workspaces refresh",
    )
    refresh_all_mark_parser.add_argument("source_commit")
    refresh_all_mark_parser.add_argument("workspace_branch")
    refresh_all_mark_parser.add_argument("status", choices=("discovered", "in_progress", "pr_open", "merged", "snapshot_pending", "local_sync_pending", "complete", "blocked"))
    refresh_all_mark_parser.add_argument("--pr-branch")
    refresh_all_mark_parser.add_argument("--pr-url")
    refresh_all_mark_parser.add_argument("--merge-commit")
    refresh_all_mark_parser.add_argument("--snapshot-branch")
    refresh_all_mark_parser.add_argument("--snapshot-commit")
    refresh_all_mark_parser.add_argument("--error")
    refresh_all_mark_parser.add_argument("--clear-error", action="store_true")

    rollout_parser = subparsers.add_parser(
        "local-rollout-check",
        help="verify every discovered local checkout and linked harness after a merge",
    )
    rollout_parser.add_argument("kind", choices=("refresh-all", "reconcile-all"))
    rollout_parser.add_argument("identifier", help="toolkit source commit or reconciliation run id")
    rollout_parser.add_argument("workspace_branch")
    rollout_parser.add_argument("--target-sha", help="verified default-branch commit for reconciliation runs")
    rollout_parser.add_argument("--source-root", type=Path, help="checkout at the verified merged/default-branch commit")
    rollout_parser.add_argument("--allow-checkout", action="append", type=Path, default=[],
                                help="checkout explicitly inspected and selected for update; may be repeated")
    harness_inventory = rollout_parser.add_mutually_exclusive_group()
    harness_inventory.add_argument("--harness-root", action="append", type=Path, default=[], help="linked harness root to verify; may be repeated")
    harness_inventory.add_argument("--no-harnesses", action="store_true", help="confirm that no separate parent harness applies")

    reconcile_parser = subparsers.add_parser("reconcile-all", help="inventory registered repos and create or resume branch reconciliation receipts")
    reconcile_parser.add_argument("target", nargs="?", default=".")
    reconcile_parser.add_argument("--toolkit-repo")
    reconcile_parser.add_argument("--search-root", action="append", type=Path)
    reconcile_parser.add_argument("--replace-search-roots", action="store_true")
    reconcile_parser.add_argument("--max-depth", type=int, default=8)
    reconcile_parser.add_argument("--dry-run", action="store_true")
    reconcile_mode = reconcile_parser.add_mutually_exclusive_group()
    reconcile_mode.add_argument("--run-id", help="resume the named run with the same registry and search scope")
    reconcile_mode.add_argument("--new-run", action="store_true", help="start a fresh inventory instead of resuming an incomplete run")

    reconcile_mark = subparsers.add_parser("reconcile-all-mark", help="record workspace or branch progress in a reconciliation run")
    reconcile_mark.add_argument("run_id")
    reconcile_mark.add_argument("workspace_branch")
    reconcile_mark.add_argument("status", choices=("in_progress", "local_sync_pending", "pr_open", "merged", "cleaned", "preserved", "blocked", "complete"))
    reconcile_mark.add_argument("--ref", help="full inventory ref; omit to mark the workspace")
    reconcile_mark.add_argument("--observed-sha", help="required with --ref; must match the current journal observation")
    for receipt in ("pr-url", "merge-commit", "target-sha", "reason", "error"):
        reconcile_mark.add_argument(f"--{receipt}")
    reconcile_mark.add_argument("--clear-error", action="store_true")

    archive_run = subparsers.add_parser("archive-run", help="preserve a superseded batch journal outside automatic resume")
    archive_run.add_argument("kind", choices=("refresh-all", "reconcile-all"))
    archive_run.add_argument("identifier", help="source commit for refresh-all or run id for reconcile-all")
    archive_run.add_argument("--reason", required=True)

    sync_parser = subparsers.add_parser(
        "sync-agent-config",
        help="copy approved agent configuration into a checkout without merging application changes",
    )
    sync_parser.add_argument("source", type=Path, help="checkout at the approved source commit")
    sync_parser.add_argument("destination", type=Path, help="checkout whose agent setup should be synchronized")
    sync_parser.add_argument("--source-sha", help="approved source commit; defaults to source HEAD")

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
        if arguments.command == "archive-run":
            print_json(archive_workspace_run(arguments.kind, arguments.identifier, arguments.reason))
            return 0
        if arguments.command == "sync-agent-config":
            source = git_root(arguments.source)
            print_json(sync_agent_configuration(source, arguments.destination, arguments.source_sha or run_git(source, ["rev-parse", "HEAD"])))
            return 0
        if arguments.command == "checkout-path":
            if arguments.checkout_action == "set":
                print_json(set_workspace_checkout_preference(arguments.path))
            elif arguments.checkout_action == "remove":
                print_json(remove_workspace_checkout_preference(arguments.workspace_branch))
            else:
                print_json({
                    "path": str(workspace_checkout_preferences_path()),
                    "checkouts": load_workspace_checkout_preferences(),
                })
            return 0
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
        if arguments.command == "refresh":
            result = refresh_repository(
                Path(arguments.target),
                Path(arguments.toolkit_root) if arguments.toolkit_root else None,
                arguments.dry_run,
                arguments.complete,
            )
            print_json(result)
            return 0
        if arguments.command == "snapshot":
            print_json(snapshot_repository(Path(arguments.target), arguments.toolkit_repo, arguments.push))
            return 0
        if arguments.command == "refresh-all":
            if arguments.max_depth < 1 or arguments.max_depth > 32:
                raise ToolkitError("all-workspaces search depth must be between 1 and 32")
            print_json(plan_all_refreshes(Path(arguments.target), arguments.search_root, arguments.replace_search_roots, arguments.max_depth, arguments.dry_run, arguments.toolkit_repo))
            return 0
        if arguments.command == "status":
            if arguments.max_depth < 1 or arguments.max_depth > 32:
                raise ToolkitError("status search depth must be between 1 and 32")
            report = workspace_status(
                Path(arguments.target), arguments.search_root, arguments.replace_search_roots,
                arguments.max_depth, arguments.fetch,
            )
            if arguments.json:
                print_json(report)
            else:
                sys.stdout.write(format_workspace_status(report))
            return 0
        if arguments.command == "refresh-all-mark":
            receipts = {
                "pr_branch": arguments.pr_branch,
                "pr_url": arguments.pr_url,
                "merge_commit": arguments.merge_commit,
                "snapshot_branch": arguments.snapshot_branch,
                "snapshot_commit": arguments.snapshot_commit,
                "error": arguments.error,
            }
            result = update_refresh_all_journal(
                arguments.source_commit,
                arguments.workspace_branch,
                arguments.status,
                receipts,
                arguments.clear_error,
            )
            print_json(result)
            return 0
        if arguments.command == "local-rollout-check":
            result = local_rollout_check(
                arguments.kind,
                arguments.identifier,
                arguments.workspace_branch,
                arguments.target_sha,
                arguments.source_root,
                arguments.harness_root,
                arguments.no_harnesses,
                arguments.allow_checkout,
            )
            print_json(result)
            return 0 if result["local_rollout"]["status"] == "passed" else 1
        if arguments.command == "reconcile-all":
            if arguments.max_depth < 1 or arguments.max_depth > 32:
                raise ToolkitError("all-repositories search depth must be between 1 and 32")
            print_json(plan_all_reconciliations(
                Path(arguments.target), arguments.search_root, arguments.replace_search_roots,
                arguments.max_depth, arguments.dry_run, arguments.toolkit_repo, arguments.run_id, arguments.new_run,
            ))
            return 0
        if arguments.command == "reconcile-all-mark":
            receipts = {key: getattr(arguments, key) for key in ("pr_url", "merge_commit", "target_sha", "reason", "error")}
            print_json(update_reconciliation_journal(
                arguments.run_id, arguments.workspace_branch, arguments.status,
                arguments.ref, arguments.observed_sha, receipts, arguments.clear_error,
            ))
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
