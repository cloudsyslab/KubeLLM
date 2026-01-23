#!/usr/bin/env python3
import argparse
import pathlib
import zipfile
from datetime import datetime

DEFAULT_INCLUDE = [
    "README.md",
    "CLAUDE.md",
    "requirements.txt",
    "assistant.py",
    "api_server.py",
    "streamlit_assistant.py",
    "start_apiserver.sh",
    ".gitignore",
    "config_template.json",
    "debug_assistant_latest/main.py",
    "debug_assistant_latest/agents.py",
    "debug_assistant_latest/kube_test.py",
    "debug_assistant_latest/teardownenv.py",
    "debug_assistant_latest/troubleshooting/**/*.yaml",
    "debug_assistant_latest/troubleshooting/**/readme.txt",
    "debug_assistant_latest/troubleshooting/**/config_step.json",
    "orchestrator/*.sh",
]

def expand_globs(root: pathlib.Path, patterns):
    files = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file():
                files.add(path)
    return sorted(files)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=".local/context_packs", help="Output directory")
    parser.add_argument("--include", action="append", default=[], help="Additional glob patterns")
    args = parser.parse_args()

    root = pathlib.Path(".").resolve()
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    patterns = DEFAULT_INCLUDE + args.include
    files = expand_globs(root, patterns)
    if not files:
        raise SystemExit("No files matched; check patterns")

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"context_pack_{stamp}.zip"

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            rel = f.relative_to(root)
            zf.write(f, rel.as_posix())

    print(str(out_path))

if __name__ == "__main__":
    main()
