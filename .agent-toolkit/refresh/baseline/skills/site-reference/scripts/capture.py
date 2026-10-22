#!/usr/bin/env python3
"""Import an original WACZ capture or make a clearly labeled partial HTML snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit, urlunsplit
import zipfile


def executable(value: str | Path | None) -> str | None:
    if not value:
        return None
    located = shutil.which(str(value))
    path = Path(located or value).expanduser()
    return str(path.resolve()) if path.is_file() and os.access(path, os.X_OK) else None


def find_tool(*names: str) -> str | None:
    for name in names:
        found = executable(name) or executable(Path.home() / ".local/bin" / name)
        if found:
            return found
    return None


def find_chrome() -> str | None:
    found = find_tool("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
    if found:
        return found
    for path in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/opt/google/chrome/chrome",
    ):
        found = executable(path)
        if found:
            return found
    return None


def stop_group(process: subprocess.Popen, sig: signal.Signals) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def interrupted(_sig: int, _frame: object) -> None:
    raise KeyboardInterrupt


def run_capture(command: list[str], cwd: Path, timeout: float) -> tuple[int, str]:
    # A temporary log avoids blocking on pipe buffers or unbounded in-memory logs.
    with tempfile.TemporaryFile() as log:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=log,
                                       start_new_session=True)
        except OSError as error:
            return 127, str(error)
        previous_term = signal.signal(signal.SIGTERM, interrupted)
        try:
            result = process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            stop_group(process, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                stop_group(process, signal.SIGKILL)
                process.wait()
            result = 124 if isinstance(error, subprocess.TimeoutExpired) else 130
        finally:
            # Also clean up browser descendants left behind after a successful CLI.
            stop_group(process, signal.SIGTERM)
            time.sleep(0.05)
            stop_group(process, signal.SIGKILL)
            signal.signal(signal.SIGTERM, previous_term)
        log.seek(0, os.SEEK_END)
        log.seek(max(0, log.tell() - 5000))
        return result, log.read().decode("utf-8", errors="replace")


def diagnostic(output: str, result: int) -> str:
    lowered = output.lower()
    if result == 124:
        return "Capture timed out; its process group was terminated. The previous capture is preserved."
    if result == 130:
        return "Capture interrupted; its process group was terminated. The previous capture is preserved."
    if any(word in lowered for word in ("eacces", "eperm", "operation not permitted", "sandbox")):
        return ("Browser capture appears blocked by execution/sandbox permissions. Retry only this "
                "authorized capture command through the established approval mechanism.")
    if any(word in lowered for word in ("enotfound", "eai_again", "name not resolved", "dns", "proxy", "certificate")):
        return ("Capture appears blocked by shell networking, DNS, proxy, or TLS. Browser access "
                "is separate; inspect that layer before retrying.")
    if "node" in lowered and any(word in lowered for word in ("not found", "no such file")):
        return "The CLI cannot find Node in this shell. Locate the installed runtime; do not reinstall automatically."
    return f"SingleFile failed (exit {result}); inspect the bounded tool log below. The previous capture is preserved."


def atomic_json(path: Path, value: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".meta-", suffix=".json",
                                     encoding="utf-8", delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2)
        handle.write("\n")
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def has_screenshot_evidence(clone: Path, metadata: dict) -> bool:
    if metadata.get("live_visuals") or metadata.get("screenshots"):
        return True
    shots = clone / "shots"
    return shots.is_dir() and any(path.is_file() and path.suffix.lower() in
                                  {".png", ".jpg", ".jpeg", ".webp"} for path in shots.iterdir())


def sha256_stream(stream) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def safe_zip_member(name: str) -> bool:
    path = Path(name)
    return (bool(name) and "\\" not in name and not path.is_absolute()
            and all(part not in ("", ".", "..") for part in path.parts))


def canonical_url(value: str) -> str:
    """Compare archived navigations while allowing a browser-added final slash."""
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port and not ((parsed.scheme == "https" and port == 443) or (parsed.scheme == "http" and port == 80)):
        host = f"{host}:{port}"
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host, path, parsed.query, ""))


def validate_wacz(path: Path, source_url: str) -> dict:
    """Check WACZ ZIP structure, package/resource digests, and its captured page URL."""
    required = {"datapackage.json", "datapackage-digest.json", "pages/pages.jsonl",
                "indexes/index.cdx", "archive/data.warc.gz"}
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if len(names) > 200_000 or len(names) != len(set(names)):
                raise ValueError("WACZ has too many or duplicate ZIP entries")
            if any(not safe_zip_member(name.rstrip("/")) for name in names if name.rstrip("/")):
                raise ValueError("WACZ contains an unsafe ZIP member path")
            if any((member.external_attr >> 16) & 0o170000 == 0o120000 for member in members):
                raise ValueError("WACZ contains a symbolic link")
            if not required.issubset(names):
                raise ValueError("WACZ is missing required package, page, index, or WARC files")
            if sum(member.file_size for member in members) > 5 * 1024**3:
                raise ValueError("WACZ uncompressed contents exceed the 5 GiB safety limit")
            corrupt = archive.testzip()
            if corrupt:
                raise ValueError(f"WACZ ZIP integrity check failed at {corrupt}")

            package_bytes = archive.read("datapackage.json")
            package = json.loads(package_bytes)
            if package.get("profile") != "data-package" or not isinstance(package.get("resources"), list):
                raise ValueError("WACZ datapackage is not a supported data-package profile")
            digest = json.loads(archive.read("datapackage-digest.json"))
            expected_package_hash = str(digest.get("hash", "")).removeprefix("sha256:")
            if (digest.get("path") != "datapackage.json" or len(expected_package_hash) != 64
                    or hashlib.sha256(package_bytes).hexdigest() != expected_package_hash):
                raise ValueError("WACZ datapackage digest does not match datapackage.json")

            resources = package["resources"]
            resource_paths = set()
            for resource in resources:
                member_name = resource.get("path")
                expected = str(resource.get("hash", "")).removeprefix("sha256:")
                if (not isinstance(member_name, str) or not safe_zip_member(member_name)
                        or member_name not in names or member_name in resource_paths
                        or len(expected) != 64):
                    raise ValueError("WACZ datapackage has an invalid or duplicate resource")
                resource_paths.add(member_name)
                with archive.open(member_name) as stream:
                    actual_hash, actual_size = sha256_stream(stream)
                if actual_hash != expected or actual_size != resource.get("bytes"):
                    raise ValueError(f"WACZ resource integrity check failed for {member_name}")
            if not required.issubset(resource_paths | {"datapackage.json", "datapackage-digest.json"}):
                raise ValueError("WACZ datapackage does not cover the required archive resources")

            page_urls = []
            with archive.open("pages/pages.jsonl") as stream:
                for raw_line in stream:
                    try:
                        record = json.loads(raw_line)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    url = record.get("url") if isinstance(record, dict) else None
                    if isinstance(url, str):
                        page_urls.append(url)
            if not page_urls or canonical_url(source_url) not in {canonical_url(url) for url in page_urls}:
                raise ValueError("requested source URL is not present in WACZ pages/pages.jsonl")

            index_entries = 0
            mime_counts: dict[str, int] = {}
            with archive.open("indexes/index.cdx") as stream:
                for raw_line in stream:
                    try:
                        row = raw_line.decode("utf-8").split(" ", 2)
                        details = json.loads(row[2]) if len(row) == 3 else {}
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    index_entries += 1
                    mime = details.get("mime")
                    if isinstance(mime, str):
                        mime_counts[mime] = mime_counts.get(mime, 0) + 1
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError, KeyError,
            TypeError, AttributeError) as error:
        raise ValueError(f"could not validate WACZ: {error}") from error

    with path.open("rb") as stream:
        file_hash, file_size = sha256_stream(stream)
    return {
        "file": path.name,
        "bytes": file_size,
        "sha256": file_hash,
        "profile": package.get("profile"),
        "wacz_version": package.get("wacz_version"),
        "title": package.get("title"),
        "software": package.get("software"),
        "archived_at": package.get("created"),
        "page_urls": page_urls,
        "index_entry_count": index_entries,
        "mime_counts": dict(sorted(mime_counts.items())),
        "integrity": "ZIP CRC, datapackage digest, and listed resource SHA-256/byte counts verified",
    }


def import_wacz(source: Path, clone: Path, site: Path, url: str, slug: str,
                replay_validated: bool, tested_states: list[str], viewport: str,
                actions: list[str], consent_choice: str | None) -> dict:
    clone.mkdir(parents=True, exist_ok=True)
    metadata_path = site / "meta.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"existing meta.json needs inspection: {error}") from error
    if not isinstance(metadata, dict):
        raise ValueError("existing meta.json must contain an object")
    screenshot_status = "live_still_captured" if has_screenshot_evidence(clone, metadata) else "screenshot_pending"
    with tempfile.NamedTemporaryFile(dir=clone, prefix=".original-", suffix=".wacz", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with source.open("rb") as incoming, temporary.open("wb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        archive_metadata = validate_wacz(temporary, url)
        destination = clone / "original.wacz"
        archive_metadata["file"] = str(destination.relative_to(site))
        previous_archive = metadata.get("original_archive")
        same_archive = (isinstance(previous_archive, dict)
                        and previous_archive.get("sha256") == archive_metadata.get("sha256"))
        metadata.update({
            "url": url,
            "slug": slug,
            "captured_at": archive_metadata.get("archived_at") or dt.datetime.now(dt.timezone.utc).isoformat(),
            "capture_tool": archive_metadata.get("software") or "WACZ importer",
            "original_archive": archive_metadata,
            "capture_session": {
                "viewport": viewport or "not recorded",
                "live_actions": actions,
                "consent_choice": consent_choice or "not recorded",
            },
            "snapshot_status": "archived_client_runtime",
            "replay_status": "interaction_replay_validated" if replay_validated else "replay_unverified",
            "tested_states": tested_states,
            "screenshot_status": screenshot_status,
            "visual_comparison_status": (metadata.get("visual_comparison_status", "not_compared")
                                          if same_archive else "not_compared"),
            "fidelity_status": "runtime_replay_validated" if replay_validated else "fidelity_unverified",
        })
        os.replace(temporary, destination)
        atomic_json(metadata_path, metadata)
        for name, initial in (
            ("preferences.md", "# Preferences\n\nNo user-stated preferences recorded yet.\n"),
            ("notes.md", "# Reference notes\n\nWACZ archive imported. Review original replay, responsive states, motion, and any missing resources before adapting.\n"),
        ):
            target = site / name
            if not target.exists():
                target.write_text(initial, encoding="utf-8")
        return {"archive": str(destination), "metadata": str(metadata_path), **metadata["original_archive"],
                "replay_status": metadata["replay_status"], "tested_states": tested_states}
    finally:
        temporary.unlink(missing_ok=True)


def validate_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                 and parsed.username is None and parsed.password is None)
        _ = parsed.port
    except ValueError:
        valid = False
    if not valid or any(ord(char) < 32 or char.isspace() for char in value):
        raise argparse.ArgumentTypeError("use an http(s) page URL without credentials or whitespace")
    return value


def check_existing_source(site: Path, url: str) -> None:
    """Never repurpose an existing reference pack for a different or unknown URL."""
    sources = []
    metadata = site / "meta.json"
    legacy = site / "meta.yaml"
    if metadata.exists():
        try:
            value = json.loads(metadata.read_text(encoding="utf-8")).get("url")
        except (OSError, ValueError, AttributeError) as error:
            raise ValueError(f"existing meta.json needs inspection: {error}") from error
        if not isinstance(value, str):
            raise ValueError("existing meta.json has no source URL; inspect it or choose a new slug")
        sources.append(value)
    if legacy.exists():
        # Read only the old skill's top-level scalar, avoiding a YAML dependency.
        match = re.search(r"^url:\s*(.*?)\s*$", legacy.read_text(encoding="utf-8"), re.MULTILINE)
        if not match:
            raise ValueError("legacy meta.yaml has no simple top-level URL; inspect it or choose a new slug")
        scalar = match.group(1)
        try:
            if scalar.startswith('"'):
                value = json.loads(scalar)
            elif scalar.startswith("'") and scalar.endswith("'"):
                value = scalar[1:-1].replace("''", "'")
            else:
                value = re.split(r"\s+#", scalar, maxsplit=1)[0].strip()
            validate_url(value)
        except (ValueError, TypeError, argparse.ArgumentTypeError) as error:
            raise ValueError("legacy URL syntax needs inspection; choose a new slug if this is another page") from error
        sources.append(value)
    if any(canonical_url(source) != canonical_url(url) for source in sources):
        raise ValueError("slug belongs to a different source URL; preserve that pack and choose a new slug")
    existing_archives = (site / "clone/index.html", site / "clone/original.wacz")
    if not sources and any(path.exists() for path in existing_archives):
        raise ValueError("existing archive has no source metadata; inspect it or choose a new slug")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root (default: current directory)")
    parser.add_argument("--doctor", action="store_true", help="Read-only tool inventory; no network, launch, or writes")
    parser.add_argument("--url", type=validate_url)
    parser.add_argument("--slug", help="Lowercase pack name, letters/digits and single hyphens")
    parser.add_argument("--import-wacz", type=Path, help="Validate and import a WACZ exported by ArchiveWeb.page")
    parser.add_argument("--replay-validated", action="store_true", help="Record only after testing the archive in ReplayWeb.page")
    parser.add_argument("--tested-state", action="append", default=[], help="An interaction/state actually tested in original replay; repeatable")
    parser.add_argument("--viewport", help="Observed capture viewport; distinguish screenshot pixels from CSS pixels")
    parser.add_argument("--action", action="append", default=[], help="An interaction actually performed during live capture; repeatable")
    parser.add_argument("--consent-choice", help="Non-sensitive cookie/privacy choice made during capture")
    parser.add_argument("--single-file", help="Installed SingleFile CLI executable")
    parser.add_argument("--chrome", help="Installed Chrome/Chromium executable")
    parser.add_argument("--wait-delay", type=int, default=3000, help="Page settling delay in milliseconds")
    parser.add_argument("--capture-timeout", type=float, default=180, help="Bounded CLI execution in seconds")
    parser.add_argument("--bypass-csp", action="store_true")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error("--root must be an existing directory")
    if not 0 <= args.wait_delay <= 60000 or not 0 < args.capture_timeout <= 600:
        parser.error("wait delay must be 0..60000 ms and capture timeout >0..600 seconds")
    if args.slug and (len(args.slug) > 80 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slug)):
        parser.error("--slug must contain lowercase letters/digits and single hyphens, at most 80 characters")
    single_file = executable(args.single_file) if args.single_file else find_tool("single-file", "single-file-cli")
    chrome = executable(args.chrome) if args.chrome else find_chrome()
    archiveweb_apps = [str(path) for path in (
        Path("/Applications/ArchiveWeb.page.app"), Path.home() / "Applications/ArchiveWeb.page.app",
        Path("/Volumes/ArchiveWeb.page/ArchiveWeb.page.app")) if path.exists()]
    inventory = {"root": str(root), "archiveweb_app": archiveweb_apps, "single_file": single_file, "chrome": chrome,
                 "shot_scraper_optional": find_tool("shot-scraper"), "npx": find_tool("npx"),
                 "npx_note": "npx may require a network package download; no automatic download or install."}
    if args.doctor:
        print(json.dumps(inventory, indent=2))
        return 0
    if not args.url or not args.slug:
        parser.error("--url and --slug are required unless --doctor is used")
    if not args.url or not args.slug:
        parser.error("--url and --slug are required unless --doctor is used")
    if args.replay_validated and not args.import_wacz:
        parser.error("--replay-validated applies only when importing a WACZ")
    site = root / "references/sites" / args.slug
    if not site.resolve().is_relative_to(root):
        parser.error("reference directory resolves outside --root")
    clone = site / "clone"
    if not clone.resolve().is_relative_to(root):
        parser.error("clone directory resolves outside --root")
    for name in ("meta.json", "meta.yaml", "preferences.md", "notes.md"):
        if not (site / name).resolve().is_relative_to(root):
            parser.error(f"{name} resolves outside --root")
    try:
        check_existing_source(site, args.url)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if args.import_wacz:
        try:
            result = import_wacz(args.import_wacz.expanduser().resolve(), clone, site, args.url,
                                 args.slug, args.replay_validated, args.tested_state,
                                 args.viewport or "", args.action, args.consent_choice)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2))
        return 0
    if args.tested_state or args.viewport or args.action or args.consent_choice:
        parser.error("capture metadata options apply only when importing a WACZ")
    if not single_file or not chrome:
        missing = [name for name, value in (("SingleFile CLI", single_file), ("Chrome/Chromium", chrome)) if not value]
        print("ERROR: missing installed " + ", ".join(missing) + ". Use --doctor or explicit executable paths.", file=sys.stderr)
        if not single_file and inventory["npx"]:
            print(inventory["npx_note"], file=sys.stderr)
        return 127
    clone.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=clone, prefix=".capture-", suffix=".html", delete=False) as handle:
        temporary = Path(handle.name)
    # SingleFile otherwise uniquifies an existing output filename, leaving this
    # pre-created temporary file empty while writing a differently named sibling.
    command = [single_file, args.url, str(temporary), "--filename-conflict-action", "overwrite",
               "--compress-content", "false", "--self-extracting-archive", "false",
               "--block-scripts", "false", "--block-videos", "false", "--block-audios", "false",
               "--block-fonts", "false", "--block-alternative-images", "false",
               "--remove-hidden-elements", "false", "--remove-unused-styles", "false",
               "--remove-unused-fonts", "false", "--remove-alternative-fonts", "false",
               "--remove-alternative-medias", "false", "--browser-executable-path", chrome,
               "--browser-wait-delay", str(args.wait_delay)]
    if args.bypass_csp:
        command.extend(["--browser-bypass-csp", "true"])
    try:
        result, log = run_capture(command, root, args.capture_timeout)
        if result:
            print("ERROR: " + diagnostic(log, result), file=sys.stderr)
            if log.strip():
                print(log.strip(), file=sys.stderr)
            return result
        content = temporary.read_bytes()
        if not content.strip() or b"<html" not in content[:65536].lower():
            print("ERROR: SingleFile produced empty or invalid HTML; previous capture preserved.", file=sys.stderr)
            return 1
        os.replace(temporary, clone / "index.html")
        metadata_path = site / "meta.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        metadata.update({"url": args.url, "slug": args.slug,
                         "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                         "capture_tool": single_file, "browser": chrome, "bypass_csp": args.bypass_csp,
                         "snapshot_status": "captured",
                         "screenshot_status": "live_still_captured" if has_screenshot_evidence(clone, metadata) else "screenshot_pending",
                         "visual_comparison_status": metadata.get("visual_comparison_status", "not_compared"),
                         "fidelity_status": "fidelity_unverified", "motion_and_embeds": "unverified",
                         "singlefile_preservation": "scripts, video/audio, fonts, hidden states, and unused styles retained where SingleFile permits"})
        atomic_json(site / "meta.json", metadata)
        for name, initial in (
            ("preferences.md", "# Preferences\n\nNo user-stated preferences recorded yet.\n"),
            ("notes.md", "# Reference notes\n\nCapture exists; visual fidelity, dynamic embeds, and motion require browser inspection.\n"),
        ):
            target = site / name
            if not target.exists():
                target.write_text(initial, encoding="utf-8")
        print(json.dumps({"capture": str(clone / "index.html"), "metadata": str(site / "meta.json"),
                          "snapshot_status": "captured", "screenshot_status": "screenshot_pending",
                          "fidelity_status": "fidelity_unverified"}, indent=2))
        return 0
    except OSError as error:
        print(f"ERROR: reference pack write failed: {error}", file=sys.stderr)
        return 1
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
