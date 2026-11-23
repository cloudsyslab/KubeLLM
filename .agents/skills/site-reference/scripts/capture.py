#!/usr/bin/env python3
"""Capture a page as a WACZ (crawler or imported ArchiveWeb export) or make a labeled partial HTML snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit, urlunsplit
import zipfile
import zlib


DEFAULT_CRAWL_IMAGE = "webrecorder/browsertrix-crawler:1.15.4"
WARC_SUFFIXES = (".warc", ".warc.gz")
INDEX_SUFFIXES = (".cdx", ".cdxj", ".cdx.gz", ".cdxj.gz")
SCREENSHOT_KINDS = ("view", "fullPage", "fullPageFinal", "thumbnail")
SCREENSHOT_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_SCREENSHOT_BYTES = 50 * 1024 * 1024
MAX_INDEX_LINE = 1024 * 1024
MAX_UNCOMPRESSED = 5 * 1024**3
MAX_WARC_SCAN_BYTES = 1024**3
MAX_WARC_SCAN_SECONDS = 120
CONTAINER_OWNER_LABEL = "io.kubellm.site-reference.capture-id"


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


def find_app(name: str) -> list[str]:
    """Return installed macOS app bundle locations for a desktop tool."""
    volume = name.removesuffix(".app")
    return [str(path) for path in (Path("/Applications") / name, Path.home() / "Applications" / name,
                                   Path("/Volumes") / volume / name) if path.exists()]


INSTALL_SOURCES = {
    "archiveweb_app": ("brew install --cask archivewebpage", "https://archiveweb.page/"),
    "replayweb_app": ("brew install --cask replaywebpage", "https://replayweb.page/"),
    "single_file": ("npm install -g single-file-cli", "https://github.com/gildas-lormeau/single-file-cli"),
    "chrome": ("brew install --cask google-chrome", "https://www.google.com/chrome/"),
}
CRAWLER_HINTS = {
    "docker_missing": "Install Docker (Docker Desktop, Colima, or OrbStack) from https://docs.docker.com/get-started/get-docker/",
    "daemon_unavailable": "Start the Docker engine (for example `colima start` or open Docker Desktop), then rerun --doctor",
    "missing_image": "docker pull {image}  # official source: https://hub.docker.com/r/webrecorder/browsertrix-crawler",
}


def install_hint(tool: str) -> str:
    """Name the official install route without running it."""
    command, source = INSTALL_SOURCES[tool]
    manager = "npm" if tool == "single_file" else "brew"
    if find_tool(manager) and (manager == "npm" or sys.platform == "darwin"):
        return f"{command}  # official source: {source}"
    return f"Install from {source}"


def docker_status(docker: str | None, image: str) -> tuple[str, str]:
    """Ask the local Docker engine, read-only, whether the pinned crawler image is present."""
    if not docker:
        return "docker_missing", ""
    try:
        result = subprocess.run([docker, "image", "inspect", "--format", "{{json .RepoDigests}}", image],
                                capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        return "daemon_unavailable", "docker image inspect timed out"
    except OSError as error:
        return "docker_missing", str(error)
    if result.returncode == 0:
        try:
            digests = json.loads(result.stdout.strip() or "[]")
        except json.JSONDecodeError:
            digests = []
        return "ready", (digests[0] if isinstance(digests, list) and digests else "")
    message = (result.stderr or result.stdout).strip()
    if any(word in message.lower() for word in ("no such image", "no such object")):
        return "missing_image", message
    return "daemon_unavailable", message


def capture_routes(inventory: dict) -> tuple[dict, dict]:
    """Summarize which capture routes can run now and how to fill each gap."""
    wacz_missing = [tool for tool in ("archiveweb_app", "replayweb_app") if not inventory[tool]]
    partial_missing = [tool for tool in ("single_file", "chrome") if not inventory[tool]]
    crawler_status = inventory.get("crawler_status", "docker_missing")
    image = inventory.get("crawler_image", DEFAULT_CRAWL_IMAGE)
    routes = {
        "wacz_crawl": {
            "ready": crawler_status == "ready",
            "status": crawler_status,
            "note": ("Agent-run route. browsertrix-crawler in Docker loads the page, scrolls, plays media, and "
                     "writes a WACZ with screenshots, without a person driving a browser. Signed-in pages need "
                     "a login profile; states that need hand-driven clicks need ArchiveWeb.page."),
        },
        "wacz_original": {
            "ready": bool(inventory["archiveweb_app"]),
            "missing": wacz_missing,
            "replay": "ReplayWeb.page app" if inventory["replayweb_app"] else "replayweb.page web app in a browser",
            "note": "Hand-driven route. ArchiveWeb.page records the page as a person browses and clicks; export the WACZ and import it here.",
        },
        "singlefile_partial": {
            "ready": not partial_missing,
            "missing": partial_missing,
            "note": "Partial HTML snapshot. Use only when the user declines or cannot run the primary route.",
        },
    }
    install = {tool: install_hint(tool) for tool in dict.fromkeys(wacz_missing + partial_missing)}
    if crawler_status != "ready":
        install["browsertrix_crawler"] = CRAWLER_HINTS[crawler_status].format(image=image)
    return routes, install


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
    if shots.is_symlink():
        return False
    return shots.is_dir() and any(path.is_file() and not path.name.startswith("crawl-") and path.suffix.lower() in
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
    required = {"datapackage.json", "datapackage-digest.json", "pages/pages.jsonl"}
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
            warcs = sorted(name for name in names if name.startswith("archive/") and name.endswith(WARC_SUFFIXES))
            indexes = sorted(name for name in names if name.startswith("indexes/") and name.endswith(INDEX_SUFFIXES))
            if not required.issubset(names) or not warcs or not indexes:
                raise ValueError("WACZ is missing required package, page, index, or WARC files")
            if sum(member.file_size for member in members) > 5 * 1024**3:
                raise ValueError("WACZ uncompressed contents exceed the 5 GiB safety limit")
            corrupt = archive.testzip()
            if corrupt:
                raise ValueError(f"WACZ ZIP integrity check failed at {corrupt}")

            package_bytes = archive.read("datapackage.json")
            package = json.loads(package_bytes)
            if package.get("profile") not in (None, "data-package") or not isinstance(package.get("resources"), list):
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
            if not (required | set(warcs) | set(indexes)).issubset(
                    resource_paths | {"datapackage.json", "datapackage-digest.json"}):
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
            index_bytes = 0
            for index_name in indexes:
                with archive.open(index_name) as member:
                    stream = gzip.GzipFile(fileobj=member) if index_name.endswith(".gz") else member
                    while True:
                        raw_line = stream.readline(MAX_INDEX_LINE)
                        if not raw_line:
                            break
                        index_bytes += len(raw_line)
                        if index_bytes > MAX_UNCOMPRESSED:
                            raise ValueError("WACZ index expands beyond the 5 GiB safety limit")
                        try:
                            row = raw_line.decode("utf-8").split(" ", 2)
                            details = json.loads(row[2]) if len(row) == 3 else {}
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        index_entries += 1
                        mime = details.get("mime") if isinstance(details, dict) else None
                        if isinstance(mime, str):
                            mime_counts[mime] = mime_counts.get(mime, 0) + 1
    except (OSError, EOFError, zlib.error, ValueError, zipfile.BadZipFile, json.JSONDecodeError, KeyError,
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
        "warc_files": warcs,
        "index_files": indexes,
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
        crawl = metadata.get("crawl")
        if (screenshot_status == "screenshot_pending" and isinstance(crawl, dict) and crawl.get("screenshots")
                and crawl.get("archive_sha256") == archive_metadata.get("sha256")):
            screenshot_status = "crawler_still_captured"
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


def read_exact(stream, length: int, keep: bool = True, on_read=None) -> bytes:
    """Read or skip one WARC record body in bounded chunks."""
    chunks, remaining = [], length
    while remaining > 0:
        chunk = stream.read(min(remaining, 1024 * 1024))
        if not chunk:
            raise ValueError("WARC record ended early")
        if on_read is not None:
            on_read(len(chunk))
        if keep:
            chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def wacz_screenshots(path: Path, url: str) -> dict[str, tuple[str, bytes]]:
    """Return crawler screenshot records for the requested page from a WACZ, without writing anything."""
    try:
        wanted = canonical_url(url)
    except ValueError:
        return {}
    found: dict[str, tuple[str, bytes]] = {}
    scanned_bytes = 0
    started = time.monotonic()

    def charge(size: int) -> None:
        nonlocal scanned_bytes
        scanned_bytes += size
        if scanned_bytes > MAX_WARC_SCAN_BYTES:
            raise ValueError(f"WARC screenshot scan exceeded its {MAX_WARC_SCAN_BYTES}-byte expanded-data limit")
        if time.monotonic() - started > MAX_WARC_SCAN_SECONDS:
            raise ValueError(f"WARC screenshot scan exceeded its {MAX_WARC_SCAN_SECONDS}-second time limit")

    def read_line(stream) -> bytes:
        remaining = MAX_WARC_SCAN_BYTES - scanned_bytes
        line = stream.readline(min(MAX_INDEX_LINE, max(1, remaining + 1)))
        charge(len(line))
        return line

    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not (name.startswith("archive/") and name.endswith(WARC_SUFFIXES)):
                    continue
                with archive.open(name) as member:
                    stream = gzip.GzipFile(fileobj=member) if name.endswith(".gz") else member
                    while True:
                        line = read_line(stream)
                        if not line:
                            break
                        if not line.startswith(b"WARC/"):
                            continue
                        headers: dict[str, str] = {}
                        while True:
                            header = read_line(stream)
                            if header in (b"\r\n", b"\n", b""):
                                break
                            key, _, value = header.decode("utf-8", "replace").partition(":")
                            headers[key.strip().lower()] = value.strip()
                        try:
                            length = int(headers.get("content-length", "0") or 0)
                        except ValueError as error:
                            raise ValueError(f"malformed WARC Content-Length in {name}") from error
                        if length < 0:
                            raise ValueError(f"negative WARC Content-Length in {name}")
                        kind, _, page = headers.get("warc-target-uri", "").removeprefix("urn:").partition(":")
                        mime = headers.get("content-type", "").split(";")[0].strip().lower()
                        try:
                            same_page = canonical_url(page) == wanted
                        except ValueError:
                            same_page = False
                        keep = (headers.get("warc-type") == "resource" and kind in SCREENSHOT_KINDS and same_page
                                and mime in SCREENSHOT_TYPES and 0 < length <= MAX_SCREENSHOT_BYTES)
                        body = read_exact(stream, length, keep, on_read=charge)
                        if keep:
                            found[kind] = (mime, body)
    except (OSError, EOFError, zlib.error, zipfile.BadZipFile) as error:
        raise ValueError(f"could not read crawler screenshots: {error}") from error
    return found


def checked_crawl_shots_directory(clone: Path) -> Path:
    """Reject a screenshot path that can make crawler writes leave the clone."""
    shots = clone / "shots"
    if shots.is_symlink():
        raise ValueError("clone/shots must not be a symlink")
    try:
        clone_root = clone.resolve()
        shots_root = shots.resolve()
    except OSError as error:
        raise ValueError(f"could not resolve clone/shots: {error}") from error
    if not shots_root.is_relative_to(clone_root):
        raise ValueError("clone/shots resolves outside its clone")
    if shots.exists() and not shots.is_dir():
        raise ValueError("clone/shots exists but is not a directory")
    return shots


def install_crawl_shots(found: dict[str, tuple[str, bytes]], shots: Path) -> list[dict]:
    """Replace earlier crawler stills in clone/shots with this capture's stills."""
    shots = checked_crawl_shots_directory(shots.parent)
    if shots.is_dir():
        for old in shots.glob("crawl-*"):
            if old.is_file():
                old.unlink()
    saved = []
    if found:
        shots.mkdir(parents=True, exist_ok=True)
    for kind, (mime, body) in found.items():
        target = shots / f"crawl-{kind.lower()}{SCREENSHOT_TYPES[mime]}"
        with tempfile.NamedTemporaryFile(dir=shots, prefix=".crawl-", delete=False) as handle:
            handle.write(body)
            temporary = Path(handle.name)
        temporary.chmod(0o644)
        os.replace(temporary, target)
        entry = {"file": f"clone/shots/{target.name}", "kind": kind, "mime": mime,
                 "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        if body[:8] == b"\x89PNG\r\n\x1a\n" and len(body) >= 24:
            entry["width"], entry["height"] = struct.unpack(">II", body[16:24])
        saved.append(entry)
    return saved


def stop_container(docker: str, name: str, owner_token: str) -> bool:
    """Stop only a crawler container whose per-run ownership label still matches."""
    try:
        inspected = subprocess.run(
            [docker, "inspect", "--format", '{{ index .Config.Labels "io.kubellm.site-reference.capture-id" }}', name],
            capture_output=True, text=True, timeout=10,
        )
        if inspected.returncode != 0 or inspected.stdout.strip() != owner_token:
            return False
        killed = subprocess.run([docker, "kill", name], capture_output=True, timeout=20)
        return killed.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
    return False


def crawl_diagnostic(output: str, result: int, container_stopped: bool = False) -> str:
    lowered = output.lower()
    if result == 124:
        if container_stopped:
            return "The crawl timed out; its owned crawler container was stopped."
        return "The crawl timed out; container ownership could not be verified, so no container was stopped."
    if any(phrase in lowered for phrase in ("bind source path does not exist", "mounts denied",
                                            "is not shared from the host")):
        return ("Docker's VM cannot see the project folder. Share it with the VM (Colima, Docker Desktop, "
                "OrbStack) or use a project under your home folder; do not switch routes for this.")
    if "cannot connect to the docker daemon" in lowered or "is the docker daemon running" in lowered:
        return "The Docker engine is not running; start it (for example `colima start`) and retry."
    if any(word in lowered for word in ("err_name_not_resolved", "enotfound", "eai_again", "dns", "proxy", "certificate")):
        return "The crawler's browser could not reach the page through DNS, proxy, or TLS; check networking inside Docker."
    if "seed" in lowered and "fail" in lowered:
        return "The crawler could not load the requested page; check the URL, sign-in needs, or bot blocking."
    return "Inspect the bounded crawler log below."


def run_crawl(args: argparse.Namespace, site: Path, clone: Path, docker: str | None) -> int:
    """Capture one page with browsertrix-crawler in Docker, then import and validate its WACZ."""
    try:
        shots_directory = checked_crawl_shots_directory(clone)
    except ValueError as error:
        print(f"ERROR: unsafe crawler screenshot directory: {error}", file=sys.stderr)
        return 2
    image = args.crawl_image
    status, detail = docker_status(docker, image)
    if status != "ready":
        print(f"ERROR: crawler route not ready ({status}). {CRAWLER_HINTS[status].format(image=image)}", file=sys.stderr)
        if detail:
            print(detail[-1000:], file=sys.stderr)
        return 127
    profile_mount: list[str] = []
    profile_flag: list[str] = []
    if args.profile:
        profile = args.profile.expanduser().resolve()
        if not profile.is_file() or not profile.name.endswith(".tar.gz"):
            print("ERROR: --profile must be an existing .tar.gz login profile", file=sys.stderr)
            return 2
        if any(character in str(profile) for character in ',"'):
            print("ERROR: --profile path must not contain a comma or double quote", file=sys.stderr)
            return 2
        profile_mount = ["--mount", f"type=bind,source={profile},target=/profile/profile.tar.gz,readonly"]
        profile_flag = ["--profile", "/profile/profile.tar.gz"]
    if any(character in str(site) for character in ',"'):
        print("ERROR: the pack path must not contain a comma or double quote for a Docker bind mount", file=sys.stderr)
        return 2
    site.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".crawl-", dir=site))
    owner_token = secrets.token_hex(16)
    container = f"site-reference-crawl-{owner_token}"
    imported: dict | None = None
    try:
        command = [docker, "run", "--rm", "--pull", "never", "--name", container,
                   "--label", f"{CONTAINER_OWNER_LABEL}={owner_token}",
                   "--mount", f"type=bind,source={work},target=/crawls", *profile_mount,
                   image, "crawl", "--url", args.url, "--scopeType", "page", "--generateWACZ",
                   # The crawler's view screenshot forces a 1920x1080 window, so phone captures take full-page only.
                   "--collection", args.slug, "--screenshot", "fullPage" if args.mobile_device else "view,fullPage",
                   "--postLoadDelay", str(args.post_load_delay), "--behaviorTimeout", str(args.behavior_timeout),
                   "--failOnFailedSeed", *profile_flag]
        if args.mobile_device:
            command += ["--mobileDevice", args.mobile_device]
        result, output = run_capture(command, work, args.capture_timeout)
        if result != 0:
            stopped = stop_container(docker, container, owner_token)
            print(f"ERROR: crawl failed (exit {result}). {crawl_diagnostic(output, result, stopped)} "
                  "The previous pack is preserved.", file=sys.stderr)
            print(output, file=sys.stderr)
            return 1
        wacz = work / "collections" / args.slug / f"{args.slug}.wacz"
        if not wacz.is_file():
            print(f"ERROR: the crawler finished but no WACZ reached {work}. If Docker runs in a VM (Colima, "
                  "Docker Desktop, OrbStack), share this folder with it; projects under your home folder usually "
                  "are. The previous pack is preserved.", file=sys.stderr)
            return 1
        viewport = args.viewport or (f"crawler mobileDevice {args.mobile_device}" if args.mobile_device
                                     else "crawler default desktop window")
        validate_wacz(wacz, args.url)
        found = wacz_screenshots(wacz, args.url)
        imported = import_wacz(wacz, clone, site, args.url, args.slug, False, [], viewport, [], None)
        shots = install_crawl_shots(found, shots_directory)
        metadata_path = site / "meta.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["crawl"] = {
            "tool": "browsertrix-crawler", "image": image, "image_digest": detail or None, "scope": "page",
            "archive_sha256": imported.get("sha256"),
            "behaviors": "crawler defaults: autoplay, autofetch, autoscroll, siteSpecific",
            "post_load_delay_seconds": args.post_load_delay, "behavior_timeout_seconds": args.behavior_timeout,
            "mobile_device": args.mobile_device or None, "login_profile": "used" if args.profile else "none",
            "screenshots": shots,
        }
        if shots and metadata.get("screenshot_status") == "screenshot_pending":
            metadata["screenshot_status"] = "crawler_still_captured"
        elif not shots and metadata.get("screenshot_status") == "crawler_still_captured":
            metadata["screenshot_status"] = "screenshot_pending"
        measured = next((shot for kind in ("view", "fullPage") for shot in shots
                         if shot["kind"] == kind and "width" in shot), None)
        if measured and not args.viewport:
            metadata["capture_session"]["viewport"] = (f"{viewport}; {measured['kind']} screenshot "
                                                       f"{measured['width']}x{measured['height']} px")
        atomic_json(metadata_path, metadata)
        print(json.dumps({**imported, "crawl": metadata["crawl"],
                          "screenshot_status": metadata["screenshot_status"]}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        state = ("The new archive was imported, but its crawl record is incomplete; rerun the crawl."
                 if imported else "The previous pack is preserved.")
        print(f"ERROR: {error}. {state}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


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


def private_path_error(path: Path, label: str) -> str | None:
    """Require protected capture inputs and outputs to stay outside Git or under an ignored path."""
    candidate = path.expanduser().resolve()
    probe = candidate if candidate.is_dir() else candidate.parent
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    repository = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        check=False, capture_output=True, text=True,
    )
    if repository.returncode != 0:
        return None
    repository_root = Path(repository.stdout.strip()).resolve()
    try:
        relative = candidate.relative_to(repository_root)
    except ValueError:
        return None
    relative_name = relative.as_posix() or "."
    tracked = subprocess.run(
        ["git", "-C", str(repository_root), "ls-files", "--", f":(top,literal){relative_name}"],
        check=False, capture_output=True, text=True,
    )
    if tracked.returncode != 0:
        return f"could not check whether {label} is tracked in Git"
    if tracked.stdout.strip():
        return f"{label} is tracked in Git; move it outside the repository or remove it from the index"
    ignored = subprocess.run(
        ["git", "-C", str(repository_root), "check-ignore", "--quiet", "--no-index", "--", relative_name],
        check=False, capture_output=True,
    )
    if ignored.returncode == 0:
        return None
    return (f"{label} must be outside Git or under an ignored path; "
            "use an external path or --root .local/site-reference")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root (default: current directory)")
    parser.add_argument("--doctor", action="store_true",
                        help="Read-only tool inventory; no network, browser launch, or writes (asks the local Docker engine read-only)")
    parser.add_argument("--url", type=validate_url)
    parser.add_argument("--slug", help="Lowercase pack name, letters/digits and single hyphens")
    parser.add_argument("--import-wacz", type=Path, help="Validate and import a WACZ exported by ArchiveWeb.page")
    parser.add_argument("--allow-versioned-wacz", action="store_true",
                        help="Allow importing a non-sensitive WACZ into tracked repository paths after user approval")
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
    parser.add_argument("--crawl", action="store_true", help="Capture the page with browsertrix-crawler in Docker and import its WACZ")
    parser.add_argument("--crawl-image", default=DEFAULT_CRAWL_IMAGE, help="Pinned browsertrix-crawler image already pulled locally")
    parser.add_argument("--docker", help="Installed docker executable")
    parser.add_argument("--mobile-device", help="Crawler device emulation name, for example 'iPhone 15'")
    parser.add_argument("--profile", type=Path, help="Login profile .tar.gz made with create-login-profile; never commit it")
    parser.add_argument("--post-load-delay", type=int, default=2, help="Crawler wait after load, in seconds")
    parser.add_argument("--behavior-timeout", type=int, default=30, help="Crawler behavior time limit, in seconds")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error("--root must be an existing directory")
    if not 0 <= args.wait_delay <= 60000 or not 0 < args.capture_timeout <= 600:
        parser.error("wait delay must be 0..60000 ms and capture timeout >0..600 seconds")
    if not 0 <= args.post_load_delay <= 60 or not 0 <= args.behavior_timeout <= 300:
        parser.error("post-load delay must be 0..60 seconds and behavior timeout 0..300 seconds")
    if args.mobile_device and not re.fullmatch(r"[A-Za-z0-9 ._()+-]{1,60}", args.mobile_device):
        parser.error("--mobile-device must be a short device name")
    if args.slug and (len(args.slug) > 80 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slug)):
        parser.error("--slug must contain lowercase letters/digits and single hyphens, at most 80 characters")
    single_file = executable(args.single_file) if args.single_file else find_tool("single-file", "single-file-cli")
    chrome = executable(args.chrome) if args.chrome else find_chrome()
    inventory = {"root": str(root), "archiveweb_app": find_app("ArchiveWeb.page.app"),
                 "replayweb_app": find_app("ReplayWeb.page.app"), "single_file": single_file, "chrome": chrome,
                 "shot_scraper_optional": find_tool("shot-scraper"), "npx": find_tool("npx"),
                 "npx_note": "npx may require a network package download; no automatic download or install."}
    if args.doctor:
        docker = executable(args.docker) if args.docker else find_tool("docker")
        inventory["docker"] = docker
        inventory["crawler_image"] = args.crawl_image
        inventory["crawler_status"], _ = docker_status(docker, args.crawl_image)
        routes, install = capture_routes(inventory)
        inventory["routes"] = routes
        inventory["install"] = install
        inventory["policy"] = ("This helper installs nothing. Prefer wacz_crawl for pages an agent can load by URL and "
                               "wacz_original for states that need hand-driven clicks. When the evidence needs a missing "
                               "tool, offer the install command above and install it once the user agrees, then rerun "
                               "--doctor. Do not switch to a partial route only because a tool is not installed yet.")
        print(json.dumps(inventory, indent=2))
        return 0
    if args.crawl and args.profile:
        for private_path, label in ((root, "authenticated capture output"),
                                    (args.profile, "login profile")):
            error = private_path_error(private_path, label)
            if error:
                parser.error(error)
    if args.allow_versioned_wacz and not args.import_wacz:
        parser.error("--allow-versioned-wacz applies only when importing a WACZ")
    if args.import_wacz and not args.allow_versioned_wacz:
        error = private_path_error(root, "WACZ import output")
        if error:
            parser.error(error)
    if not args.url or not args.slug:
        parser.error("--url and --slug are required unless --doctor is used")
    if not args.url or not args.slug:
        parser.error("--url and --slug are required unless --doctor is used")
    if args.crawl and args.import_wacz:
        parser.error("choose either --crawl or --import-wacz")
    if args.crawl and (args.replay_validated or args.tested_state or args.action or args.consent_choice):
        parser.error("a crawl records no replay test or live actions; test replay, then re-import with --import-wacz")
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
    if args.crawl:
        return run_crawl(args, site, clone, executable(args.docker) if args.docker else find_tool("docker"))
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
