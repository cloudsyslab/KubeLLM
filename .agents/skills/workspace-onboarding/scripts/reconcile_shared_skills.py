#!/usr/bin/env python3
"""Check or create per-skill links from ~/.agents/skills to this checkout."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
CANONICAL_ROOT = REPO_ROOT / ".agents" / "skills"
SHARED_ROOT = Path.home() / ".agents" / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def canonical_skills() -> tuple[dict[str, Path], list[str]]:
    errors: list[str] = []
    if CANONICAL_ROOT.is_symlink() or not CANONICAL_ROOT.is_dir():
        return {}, [f"canonical skill root is missing or symlinked: {CANONICAL_ROOT}"]

    skills: dict[str, Path] = {}
    for folder in sorted(CANONICAL_ROOT.iterdir()):
        if folder.is_symlink() or not folder.is_dir():
            continue
        skill_file = folder / "SKILL.md"
        if not skill_file.is_file() or skill_file.is_symlink():
            continue
        match = re.search(r"^name:\s*(['\"]?)([a-z0-9-]+)\1\s*$", skill_file.read_text(), re.M)
        if not NAME_RE.fullmatch(folder.name) or not match:
            errors.append(f"invalid skill name or frontmatter: {folder}")
            continue
        declared = match.group(2)
        if declared != folder.name:
            errors.append(f"folder/frontmatter mismatch: {folder.name} declares {declared}")
            continue
        skills[folder.name] = folder

    if not skills:
        errors.append(f"no canonical skills found under {CANONICAL_ROOT}")
    return skills, errors


def shared_root_error() -> str | None:
    if SHARED_ROOT.is_symlink():
        return f"shared skill root must remain a real directory: {SHARED_ROOT}"
    if SHARED_ROOT.exists() and not SHARED_ROOT.is_dir():
        return f"shared skill path is not a directory: {SHARED_ROOT}"
    return None


def inspect(skills: dict[str, Path]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    missing: list[str] = []
    root_problem = shared_root_error()
    if root_problem:
        return [root_problem], missing
    if not SHARED_ROOT.exists():
        return errors, sorted(skills)

    entries = {p.name for p in SHARED_ROOT.iterdir() if not p.name.startswith(".")}
    for name, target in sorted(skills.items()):
        link = SHARED_ROOT / name
        if name not in entries:
            missing.append(name)
        elif not link.is_symlink():
            errors.append(f"existing non-link needs manual archive/reconciliation: {link}")
        else:
            try:
                if link.resolve(strict=True) != target.resolve(strict=True):
                    errors.append(f"link points somewhere else: {link} -> {os.readlink(link)}")
            except FileNotFoundError:
                errors.append(f"broken link needs manual review: {link} -> {os.readlink(link)}")

    for name in sorted(entries - set(skills)):
        errors.append(f"shared entry has no canonical skill: {SHARED_ROOT / name}")
    return errors, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="check links without changing anything (default)")
    mode.add_argument("--sync", action="store_true", help="create missing links; never replace existing files or folders")
    args = parser.parse_args()

    skills, errors = canonical_skills()
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    errors, missing = inspect(skills)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    if args.sync:
        SHARED_ROOT.mkdir(parents=True, exist_ok=True)
        for name in missing:
            target = skills[name]
            link = SHARED_ROOT / name
            relative_target = os.path.relpath(target, SHARED_ROOT)
            try:
                link.symlink_to(relative_target, target_is_directory=True)
            except FileExistsError:
                print(f"error: destination appeared during sync: {link}", file=sys.stderr)
                return 1
            print(f"linked {name} -> {relative_target}")
    elif missing:
        for name in missing:
            print(f"missing {name}")
        return 1

    action = "checked" if not args.sync else "synchronized"
    print(f"{action} {len(skills)} canonical skills; {len(missing) if args.sync else 0} links created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
