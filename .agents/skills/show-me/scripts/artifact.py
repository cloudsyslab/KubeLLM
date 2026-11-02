#!/usr/bin/env python3
"""Make show-me artifacts fast.

  artifact.py new OUT.html --title T [--layout page|map|blog] [--kicker K]
                                                    single file with the house style and behaviors inlined
  artifact.py workbench status                      is the shared workbench installed and current?
  artifact.py workbench install                     copy the template and install packages (ask first)
  artifact.py workbench new SRC_DIR                 start an artifact's own source from the example
  artifact.py workbench build SRC_DIR OUT.html      build that source into one self-contained HTML file
  artifact.py workbench dev SRC_DIR [--port N]      live preview while editing SRC_DIR

The workbench lives at $SHOW_ME_WORKBENCH (default ~/.show-me/workbench). It only
holds the toolchain; every artifact keeps its source next to its built HTML.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets"
STAMP = ".show-me-stamp.json"
# Workbench paths the helper owns at runtime; never part of the template copy.
RUNTIME_PATHS = {"node_modules", ".stage", ".builds", STAMP}
SOURCE_IGNORE = shutil.ignore_patterns("node_modules", ".DS_Store", "dist")


class ArtifactError(Exception):
    pass


def emit(payload: Dict[str, object]) -> None:
    print(json.dumps(payload, indent=2))


def workbench_root() -> Path:
    configured = os.environ.get("SHOW_ME_WORKBENCH")
    return Path(configured).expanduser() if configured else Path.home() / ".show-me" / "workbench"


def template_files() -> List[Tuple[str, Path]]:
    """Every file the workbench should contain, as (relative path, source)."""
    template = ASSETS / "workbench"
    files = [
        (path.relative_to(template).as_posix(), path)
        for path in sorted(template.rglob("*"))
        if path.is_file() and path.name != ".DS_Store"
    ]
    files.append(("src/house-tokens.css", ASSETS / "house-tokens.css"))
    return files


def digest(files: List[Tuple[str, Path]]) -> str:
    hasher = hashlib.sha256()
    for relative, source in files:
        hasher.update(relative.encode())
        hasher.update(b"\0")
        hasher.update(source.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def expected_stamp() -> Dict[str, object]:
    files = template_files()
    return {
        "template_sha256": digest(files),
        "package_sha256": hashlib.sha256((ASSETS / "workbench" / "package.json").read_bytes()).hexdigest(),
        "files": [relative for relative, _ in files],
    }


def read_stamp(root: Path) -> Dict[str, object]:
    try:
        return json.loads((root / STAMP).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def package_manager() -> List[str]:
    if shutil.which("pnpm"):
        return ["pnpm"]
    if shutil.which("npm"):
        return ["npm"]
    raise ArtifactError("neither pnpm nor npm is on PATH; install Node.js first")


def status() -> Dict[str, object]:
    root = workbench_root()
    stamp = read_stamp(root)
    expected = expected_stamp()
    if not (root / "node_modules").is_dir() or stamp.get("package_sha256") != expected["package_sha256"]:
        needs = "install"
    elif stamp.get("template_sha256") != expected["template_sha256"]:
        needs = "sync"
    else:
        needs = "none"
    return {"workbench": str(root), "needs": needs}


def sync(root: Path, package_sha256: Optional[str] = None) -> None:
    """Copy the template over the workbench, dropping files a newer template retired."""
    root.mkdir(parents=True, exist_ok=True)
    previous = read_stamp(root)
    expected = expected_stamp()
    for relative in previous.get("files", []):
        if isinstance(relative, str) and relative not in expected["files"] and relative.split("/")[0] not in RUNTIME_PATHS:
            stale = root / relative
            if stale.is_file():
                stale.unlink()
    for relative, source in template_files():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    stamp = dict(expected)
    stamp["package_sha256"] = package_sha256 if package_sha256 is not None else previous.get("package_sha256")
    (root / STAMP).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")


def install() -> Dict[str, object]:
    root = workbench_root()
    sync(root)
    manager = package_manager()
    command = manager + (["install", "--config.confirm-modules-purge=false"] if manager == ["pnpm"] else ["install", "--no-audit", "--no-fund"])
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise ArtifactError(f"{' '.join(command)} failed:\n{tail(result)}")
    sync(root, package_sha256=str(expected_stamp()["package_sha256"]))
    return {"workbench": str(root), "installed": True, "package_manager": manager[0]}


def ensure_ready() -> Path:
    current = status()
    root = Path(str(current["workbench"]))
    if current["needs"] == "install":
        raise ArtifactError(
            "the workbench needs an install (new or changed packages). Ask the user first, then run: "
            "artifact.py workbench install"
        )
    if current["needs"] == "sync":
        sync(root)
    return root


def slug(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.resolve().name.lower()).strip("-") or "artifact"


def check_source(source: Path) -> None:
    if not source.is_dir():
        raise ArtifactError(f"artifact source directory not found: {source}")
    if not any((source / f"App{suffix}").is_file() for suffix in (".tsx", ".jsx", ".ts", ".js")):
        raise ArtifactError(f"{source} needs an App.tsx (or .jsx) whose default export is the artifact")


def stage(root: Path, source: Path) -> Path:
    staged = root / ".stage" / slug(source)
    if staged.exists():
        shutil.rmtree(staged)
    shutil.copytree(source, staged, ignore=SOURCE_IGNORE)
    return staged


def vite(manager: List[str], *args: str) -> List[str]:
    return manager + ["exec", "vite", *args] if manager == ["pnpm"] else ["npx", "--no-install", "vite", *args]


def tail(result: subprocess.CompletedProcess, lines: int = 40) -> str:
    return "\n".join(((result.stdout or "") + (result.stderr or "")).strip().splitlines()[-lines:])


def artifact_env(staged: Path, title: str, out_dir: Optional[Path] = None) -> Dict[str, str]:
    env = dict(os.environ, ARTIFACT_DIR=str(staged), VITE_ARTIFACT_TITLE=html.escape(title))
    if out_dir is not None:
        env["ARTIFACT_OUT_DIR"] = str(out_dir)
    return env


def build(source: Path, output: Path, title: Optional[str]) -> Dict[str, object]:
    check_source(source)
    root = ensure_ready()
    staged = stage(root, source)
    out_dir = root / ".builds" / staged.name
    command = vite(package_manager(), "build")
    result = subprocess.run(command, cwd=root, env=artifact_env(staged, title or staged.name, out_dir), capture_output=True, text=True)
    built = out_dir / "index.html"
    if result.returncode != 0 or not built.is_file():
        raise ArtifactError(f"build failed for {source}:\n{tail(result)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(built, output)
    extra = sorted(path.relative_to(out_dir).as_posix() for path in out_dir.rglob("*") if path.is_file() and path != built)
    return {"built": str(output), "bytes": output.stat().st_size, "not_inlined": extra}


def snapshot(source: Path) -> Dict[str, Tuple[float, int]]:
    return {
        path.relative_to(source).as_posix(): (path.stat().st_mtime, path.stat().st_size)
        for path in source.rglob("*")
        if path.is_file() and "node_modules" not in path.parts
    }


def dev(source: Path, port: int) -> int:
    check_source(source)
    root = ensure_ready()
    staged = stage(root, source)
    env = artifact_env(staged, staged.name)
    env["PORT"] = str(port)
    process = subprocess.Popen(vite(package_manager(), "--port", str(port), "--strictPort"), cwd=root, env=env)
    seen = snapshot(source)
    try:
        while process.poll() is None:
            time.sleep(0.4)
            current = snapshot(source)
            for relative, signature in current.items():
                if seen.get(relative) != signature:
                    destination = staged / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source / relative, destination)
            for relative in seen.keys() - current.keys():
                (staged / relative).unlink(missing_ok=True)
            seen = current
    except KeyboardInterrupt:
        process.terminate()
    return process.wait()


def new_workbench_artifact(source: Path, force: bool) -> Dict[str, object]:
    if source.exists() and any(source.iterdir()) and not force:
        raise ArtifactError(f"{source} is not empty; pass --force to overwrite its App.tsx")
    source.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSETS / "workbench" / "example" / "App.tsx", source / "App.tsx")
    return {"created": str(source / "App.tsx")}


LAYOUTS = ("page", "map", "blog")
DEFAULT_KICKERS = {"page": "Show me", "map": "Learning map", "blog": "Notes"}


def render_layout(layout: str, title: str, kicker: Optional[str] = None) -> str:
    if layout not in LAYOUTS:
        raise ArtifactError(f"unknown layout {layout!r}; choose one of {', '.join(LAYOUTS)}")
    page = (ASSETS / "layouts" / f"{layout}.html").read_text(encoding="utf-8")
    for name in ("house-tokens.css", "house-base.css"):
        page = page.replace(f"/* @inline {name} */", (ASSETS / name).read_text(encoding="utf-8").strip())
    page = page.replace("/* @inline house.js */", (ASSETS / "house.js").read_text(encoding="utf-8").strip())
    today = datetime.date.today()
    replacements = {
        "{{TITLE}}": html.escape(title),
        "{{KICKER}}": html.escape(kicker or DEFAULT_KICKERS[layout]),
        "{{DATE}}": f"{today:%b} {today.day}, {today.year}",
    }
    for placeholder, value in replacements.items():
        page = page.replace(placeholder, value)
    return page


def new_single_file(output: Path, title: str, kicker: Optional[str], force: bool, layout: str = "page") -> Dict[str, object]:
    if output.exists() and not force:
        raise ArtifactError(f"{output} exists; pass --force to replace it")
    page = render_layout(layout, title, kicker)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    return {"created": str(output), "layout": layout}


def parse(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("new", help="write a single-file artifact from a house layout")
    single.add_argument("output", type=Path)
    single.add_argument("--title", required=True)
    single.add_argument("--layout", choices=LAYOUTS, default="page")
    single.add_argument("--kicker")
    single.add_argument("--force", action="store_true")
    bench = commands.add_parser("workbench", help="the shared toolchain for games and experiences")
    actions = bench.add_subparsers(dest="action", required=True)
    actions.add_parser("status")
    actions.add_parser("install")
    start = actions.add_parser("new")
    start.add_argument("source", type=Path)
    start.add_argument("--force", action="store_true")
    make = actions.add_parser("build")
    make.add_argument("source", type=Path)
    make.add_argument("output", type=Path)
    make.add_argument("--title")
    preview = actions.add_parser("dev")
    preview.add_argument("source", type=Path)
    preview.add_argument("--port", type=int, default=5174)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse(argv)
    try:
        if args.command == "new":
            emit(new_single_file(args.output, args.title, args.kicker, args.force, args.layout))
        elif args.action == "status":
            emit(status())
        elif args.action == "install":
            emit(install())
        elif args.action == "new":
            emit(new_workbench_artifact(args.source, args.force))
        elif args.action == "build":
            emit(build(args.source, args.output, args.title))
        elif args.action == "dev":
            return dev(args.source, args.port)
    except ArtifactError as exc:
        print(f"artifact: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
