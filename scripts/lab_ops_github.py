#!/usr/bin/env python3
"""Small, streaming GitHub Releases client for lab-owned backup jobs.

Only ciphertext assets use the upload/download data path. Tokens and metadata
remain in process memory; callers must never log request headers or signed URLs.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import time
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"
MAX_ASSET_BYTES = 2 * 1024**3 - 1
ASSET_CHUNK_BYTES = 128 * 1024**2
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_ATTEMPTS = 4


class GitHubReleaseError(RuntimeError):
    """A safe-to-display error without credentials, response bodies, or URLs."""


def read_scoped_token(path: Path, *, expected_uid: int | None = None) -> str:
    """Read a single-repository token from an owner-only regular file."""
    if path.is_symlink() or not path.is_file():
        raise GitHubReleaseError("The private backup repository token file is missing or unsafe.")
    info = path.stat()
    if info.st_mode & 0o077 or (expected_uid is not None and info.st_uid != expected_uid):
        raise GitHubReleaseError("The private backup repository token file must be owner-only.")
    token = path.read_text(encoding="ascii").strip()
    if (not token.startswith("github_pat_") or len(token) > 512
            or any(ch.isspace() for ch in token)):
        raise GitHubReleaseError("The private backup repository token file is invalid.")
    return token


def _api_request(method: str, endpoint: str, token: str, *, payload: dict | None = None,
                 accept: str = "application/vnd.github+json") -> tuple[int, dict, bytes]:
    if not endpoint.startswith("/") or endpoint.startswith("//") or "\r" in endpoint or "\n" in endpoint:
        raise GitHubReleaseError("The release API path is invalid.")
    data = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    request = Request(API_BASE + endpoint, data=data, method=method, headers={
        "Accept": accept,
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "KubeLLM-lab-backup/1",
        **({"Content-Type": "application/json"} if data is not None else {}),
    })
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise GitHubReleaseError("GitHub returned an oversized API response.")
            headers = dict(response.headers.items())
            status = response.status
    except HTTPError as exc:
        exc.close()
        raise GitHubReleaseError(f"GitHub API returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise GitHubReleaseError(f"GitHub API request failed ({type(exc).__name__}).") from None
    try:
        parsed = json.loads(body) if body else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise GitHubReleaseError("GitHub returned malformed API metadata.") from None
    if not isinstance(parsed, dict):
        raise GitHubReleaseError("GitHub returned an unexpected API response.")
    return status, headers, (json.dumps(parsed, separators=(",", ":")).encode())


def api_json(method: str, endpoint: str, token: str, *, payload: dict | None = None) -> tuple[int, dict]:
    status, _headers, body = _api_request(method, endpoint, token, payload=payload)
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        raise GitHubReleaseError("GitHub returned malformed API metadata.") from None
    if not isinstance(parsed, dict):
        raise GitHubReleaseError("GitHub returned an unexpected API response.")
    return status, parsed


def ensure_private_repository(owner: str, repo: str, token: str) -> None:
    _, metadata = api_json("GET", f"/repos/{quote(owner)}/{quote(repo)}", token)
    if metadata.get("full_name", "").casefold() != f"{owner}/{repo}".casefold():
        raise GitHubReleaseError("The configured backup repository identity changed.")
    if metadata.get("visibility") != "private" or metadata.get("owner", {}).get("login", "").casefold() != owner.casefold():
        raise GitHubReleaseError("The configured backup repository must be private and user-owned.")


def release_endpoint(owner: str, repo: str, tag: str) -> str:
    if not re.fullmatch(r"lab-backup-[0-9]{8}T[0-9]{6}Z", tag):
        raise GitHubReleaseError("The backup release tag is invalid.")
    return f"/repos/{quote(owner)}/{quote(repo)}/releases/tags/{quote(tag)}"


def get_or_create_draft(owner: str, repo: str, tag: str, token: str, *, title: str,
                        notes: str, target_commitish: str = "") -> dict:
    endpoint = release_endpoint(owner, repo, tag)
    try:
        _, release = api_json("GET", endpoint, token)
    except GitHubReleaseError as exc:
        if "HTTP 404" not in str(exc):
            raise
        status, release = api_json("POST", f"/repos/{quote(owner)}/{quote(repo)}/releases", token,
                                   payload={"tag_name": tag, "target_commitish": target_commitish,
                                            "name": title, "body": notes, "draft": True})
        if status != 201:
            raise GitHubReleaseError(f"GitHub did not create the private draft (HTTP {status}).")
    if (release.get("tag_name") != tag or release.get("draft") is not True
            or release.get("prerelease") is True or not isinstance(release.get("id"), int)):
        raise GitHubReleaseError("The named backup release is not the expected private draft.")
    if not isinstance(release.get("upload_url"), str):
        raise GitHubReleaseError("The draft release has no asset upload endpoint.")
    return release


def _validate_upload_url(upload_url: str) -> tuple[str, str]:
    parsed = urlsplit(upload_url)
    if (parsed.scheme != "https" or parsed.hostname != "uploads.github.com"
            or not parsed.path.startswith("/repos/") or parsed.username or parsed.password):
        raise GitHubReleaseError("GitHub returned an unexpected asset upload endpoint.")
    return parsed.hostname, parsed.path


def _asset_upload_path(upload_url: str, name: str) -> tuple[str, str]:
    host, base = _validate_upload_url(upload_url)
    clean = base.removesuffix("{")
    return host, clean + "?" + urlencode({"name": name})


def _digest_file(path: Path, *, offset: int = 0, length: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = path.stat().st_size - offset if length is None else length
    with path.open("rb") as source:
        source.seek(offset)
        while remaining:
            block = source.read(min(1024 * 1024, remaining))
            if not block:
                raise GitHubReleaseError("The encrypted snapshot changed while preparing an asset.")
            digest.update(block)
            remaining -= len(block)
    return digest.hexdigest()


def chunk_manifest(path: Path, tag: str, *, chunk_bytes: int = ASSET_CHUNK_BYTES) -> list[dict]:
    if path.is_symlink() or not path.is_file() or chunk_bytes < 1 or chunk_bytes >= MAX_ASSET_BYTES:
        raise GitHubReleaseError("The encrypted snapshot or asset size is invalid.")
    size = path.stat().st_size
    if size <= 0:
        raise GitHubReleaseError("The encrypted snapshot is empty.")
    count = (size + chunk_bytes - 1) // chunk_bytes
    result = []
    offset = 0
    for index in range(count):
        length = min(chunk_bytes, size - offset)
        result.append({
            "name": f"{tag}-part-{index + 1:03d}-of-{count:03d}.age",
            "offset": offset,
            "size": length,
            "digest": _digest_file(path, offset=offset, length=length),
        })
        offset += length
    return result


def asset_map(release: dict) -> dict[str, dict]:
    assets = release.get("assets")
    if not isinstance(assets, list) or not all(isinstance(item, dict) for item in assets):
        raise GitHubReleaseError("GitHub returned an incomplete asset inventory.")
    result = {}
    for item in assets:
        name = item.get("name")
        if not isinstance(name, str) or name in result:
            raise GitHubReleaseError("The draft release contains duplicate or invalid asset names.")
        result[name] = item
    return result


def validate_existing_assets(release: dict, chunks: list[dict], *, allow_manifest: bool = False) -> dict[str, dict]:
    existing = asset_map(release)
    expected_names = {item["name"] for item in chunks}
    if allow_manifest:
        expected_names.add("lab-backup-manifest.json")
    if set(existing) - expected_names:
        raise GitHubReleaseError("The draft contains unexpected assets; refusing to delete or overwrite them.")
    for chunk in chunks:
        item = existing.get(chunk["name"])
        if item is not None and (item.get("size") != chunk["size"]
                                 or item.get("digest") != "sha256:" + chunk["digest"]):
            raise GitHubReleaseError("An existing draft asset differs from this encrypted snapshot.")
    return existing


def chunks_from_release(release: dict, tag: str) -> list[dict]:
    """Build the ordered stream from a release inventory, rejecting gaps or extras."""
    if release.get("tag_name") != tag or release.get("draft") is not True:
        raise GitHubReleaseError("The named backup is not the expected private draft release.")
    prefix = re.escape(tag) + r"-part-([0-9]{3})-of-([0-9]{3})\.age"
    assets = asset_map(release)
    if not assets:
        raise GitHubReleaseError("The private release does not contain backup chunks.")
    parsed = []
    expected_total = None
    for name, asset in assets.items():
        match = re.fullmatch(prefix, name)
        if not match:
            raise GitHubReleaseError("The private release contains an unexpected backup asset.")
        index, total = map(int, match.groups())
        if expected_total is None:
            expected_total = total
        if total != expected_total or index < 1 or index > total:
            raise GitHubReleaseError("The private release chunk numbering is inconsistent.")
        digest = asset.get("digest")
        if (not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
                or not isinstance(asset.get("size"), int) or asset["size"] <= 0
                or asset["size"] > MAX_ASSET_BYTES):
            raise GitHubReleaseError("The private release has an invalid encrypted asset digest or size.")
        parsed.append((index, {"name": name, "offset": 0, "size": asset["size"],
                               "digest": digest.removeprefix("sha256:")}))
    if expected_total != len(parsed) or {index for index, _ in parsed} != set(range(1, expected_total + 1)):
        raise GitHubReleaseError("The private release has missing encrypted snapshot chunks.")
    parsed.sort(key=lambda item: item[0])
    return [item for _, item in parsed]


def _post_asset_stream(upload_url: str, name: str, source_path: Path, *, offset: int,
                       length: int, expected_digest: str, token: str) -> dict:
    host, path = _asset_upload_path(upload_url, name)
    last_error = "transfer failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        connection = http.client.HTTPSConnection(host, timeout=120)
        try:
            connection.putrequest("POST", path)
            connection.putheader("Authorization", "Bearer " + token)
            connection.putheader("Accept", "application/vnd.github+json")
            connection.putheader("X-GitHub-Api-Version", API_VERSION)
            connection.putheader("User-Agent", "KubeLLM-lab-backup/1")
            connection.putheader("Content-Type", "application/octet-stream")
            connection.putheader("Content-Length", str(length))
            connection.endheaders()
            digest = hashlib.sha256()
            sent = 0
            with source_path.open("rb") as source:
                source.seek(offset)
                while sent < length:
                    block = source.read(min(1024 * 1024, length - sent))
                    if not block:
                        raise GitHubReleaseError("The encrypted snapshot changed during upload.")
                    connection.send(block)
                    digest.update(block)
                    sent += len(block)
            if digest.hexdigest() != expected_digest:
                raise GitHubReleaseError("The encrypted snapshot changed during upload.")
            response = connection.getresponse()
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise GitHubReleaseError("GitHub returned an oversized asset response.")
            if response.status != 201:
                raise GitHubReleaseError(f"GitHub rejected encrypted asset upload (HTTP {response.status}).")
            try:
                result = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise GitHubReleaseError("GitHub returned malformed asset metadata.") from None
            if (not isinstance(result, dict) or result.get("name") != name or result.get("size") != length
                    or result.get("digest") != "sha256:" + expected_digest):
                raise GitHubReleaseError("GitHub's uploaded asset digest did not match the encrypted chunk.")
            return result
        except GitHubReleaseError:
            raise
        except (OSError, http.client.HTTPException, TimeoutError) as exc:
            last_error = type(exc).__name__
            if attempt < MAX_ATTEMPTS:
                time.sleep(min(2**attempt, 15))
        finally:
            connection.close()
    raise GitHubReleaseError(f"Encrypted asset transfer stopped after {MAX_ATTEMPTS} attempts ({last_error}).")


def upload_missing_chunks(owner: str, repo: str, release: dict, chunks: list[dict], encrypted_path: Path, token: str,
                         *, progress=None) -> list[dict]:
    existing = validate_existing_assets(release, chunks)
    uploaded = []
    for index, chunk in enumerate(chunks, start=1):
        if chunk["name"] in existing:
            if progress:
                progress({"asset_index": index, "asset_count": len(chunks), "asset": chunk["name"],
                          "status": "verified-existing"})
            uploaded.append(existing[chunk["name"]])
            continue
        if progress:
            progress({"asset_index": index, "asset_count": len(chunks), "asset": chunk["name"],
                      "status": "uploading"})
        try:
            asset = _post_asset_stream(release["upload_url"], chunk["name"], encrypted_path,
                                       offset=chunk["offset"], length=chunk["size"],
                                       expected_digest=chunk["digest"], token=token)
        except GitHubReleaseError as exc:
            # A lost success response can make a retry hit GitHub's duplicate-name 422.
            # Accept it only after the exact draft asset digest and size match this chunk.
            if "HTTP 422" not in str(exc):
                raise
            _, refreshed = api_json("GET", release_endpoint(owner, repo, release["tag_name"]), token)
            validate_existing_assets(refreshed, chunks)
            asset = asset_map(refreshed).get(chunk["name"])
            if asset is None:
                raise
        uploaded.append(asset)
    if set(asset_map({"assets": uploaded})) != {chunk["name"] for chunk in chunks}:
        raise GitHubReleaseError("The uploaded asset set does not match the encrypted snapshot.")
    return uploaded


def download_assets(owner: str, repo: str, release: dict, chunks: list[dict], destination: Path,
                    token: str, *, progress=None) -> Path:
    """Reassemble only assets whose GitHub SHA-256 matches this snapshot."""
    existing = validate_existing_assets(release, chunks)
    if set(existing) != {item["name"] for item in chunks}:
        raise GitHubReleaseError("The private release is missing encrypted snapshot assets.")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        raise GitHubReleaseError("The encrypted restore destination already exists.")
    digest = hashlib.sha256()
    try:
        with destination.open("xb") as output:
            os.chmod(destination, 0o600)
            for index, chunk in enumerate(chunks, start=1):
                asset = existing[chunk["name"]]
                if progress:
                    progress({"asset_index": index, "asset_count": len(chunks), "asset": chunk["name"],
                              "status": "downloading"})
                _download_asset(owner, repo, asset, chunk, output, token, digest)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    if destination.stat().st_size != sum(item["size"] for item in chunks):
        destination.unlink(missing_ok=True)
        raise GitHubReleaseError("The assembled encrypted restore does not match the asset inventory.")
    return destination


def stream_assets_to(owner: str, repo: str, release: dict, chunks: list[dict], target: BinaryIO,
                     token: str, *, progress=None) -> None:
    """Stream ciphertext chunks to a caller-owned pipe without staging them locally."""
    existing = validate_existing_assets(release, chunks)
    if set(existing) != {item["name"] for item in chunks}:
        raise GitHubReleaseError("The private release is missing encrypted snapshot assets.")
    for index, chunk in enumerate(chunks, start=1):
        if progress:
            progress({"asset_index": index, "asset_count": len(chunks), "asset": chunk["name"],
                      "status": "downloading"})
        _download_asset(owner, repo, existing[chunk["name"]], chunk, target, token, None)


def _download_asset(owner: str, repo: str, asset: dict, chunk: dict, output: BinaryIO, token: str,
                    complete_digest) -> None:
    asset_id = asset.get("id")
    if not isinstance(asset_id, int) or asset.get("digest") != "sha256:" + chunk["digest"]:
        raise GitHubReleaseError("A private release asset has no matching immutable digest.")
    endpoint = f"{API_BASE}/repos/{quote(owner)}/{quote(repo)}/releases/assets/{asset_id}"
    request = Request(endpoint, headers={
        "Accept": "application/octet-stream",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "KubeLLM-lab-backup/1",
    })
    try:
        response = urlopen(request, timeout=120)
    except HTTPError as exc:
        exc.close()
        raise GitHubReleaseError(f"GitHub could not download an encrypted asset (HTTP {exc.code}).") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise GitHubReleaseError(f"GitHub encrypted asset download failed ({type(exc).__name__}).") from None
    with response:
        final = urlsplit(response.geturl())
        if (final.scheme != "https" or not final.hostname
                or not (final.hostname == "api.github.com"
                        or final.hostname == "release-assets.githubusercontent.com"
                        or final.hostname.endswith(".release-assets.githubusercontent.com"))):
            raise GitHubReleaseError("GitHub returned an unexpected encrypted asset download endpoint.")
        if response.status in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location", "")
            parsed = urlsplit(location)
            if (parsed.scheme != "https" or not parsed.hostname
                    or not (parsed.hostname == "release-assets.githubusercontent.com"
                            or parsed.hostname.endswith(".release-assets.githubusercontent.com"))):
                raise GitHubReleaseError("GitHub returned an unexpected encrypted asset download endpoint.")
            try:
                with urlopen(Request(location, headers={"User-Agent": "KubeLLM-lab-backup/1"}), timeout=120) as raw:
                    _copy_verified(raw, output, chunk, complete_digest)
            except HTTPError as exc:
                exc.close()
                raise GitHubReleaseError(f"GitHub asset download failed (HTTP {exc.code}).") from None
            except (URLError, TimeoutError, OSError) as exc:
                raise GitHubReleaseError(f"GitHub asset download failed ({type(exc).__name__}).") from None
            return
        _copy_verified(response, output, chunk, complete_digest)


def _copy_verified(source: BinaryIO, target: BinaryIO, chunk: dict, overall_digest) -> None:
    local_digest = hashlib.sha256()
    remaining = chunk["size"]
    while remaining:
        block = source.read(min(1024 * 1024, remaining))
        if not block:
            raise GitHubReleaseError("GitHub returned a truncated encrypted asset.")
        target.write(block)
        local_digest.update(block)
        if overall_digest is not None:
            overall_digest.update(block)
        remaining -= len(block)
    if source.read(1) or local_digest.hexdigest() != chunk["digest"]:
        raise GitHubReleaseError("Downloaded encrypted asset does not match its immutable digest.")


def publish_draft(owner: str, repo: str, release: dict, token: str) -> dict:
    identifier = release.get("id")
    if not isinstance(identifier, int) or release.get("draft") is not True:
        raise GitHubReleaseError("Refusing to publish a release that is not the verified draft.")
    status, updated = api_json("PATCH", f"/repos/{quote(owner)}/{quote(repo)}/releases/{identifier}", token,
                               payload={"draft": False})
    if status != 200 or updated.get("draft") is not False or updated.get("tag_name") != release.get("tag_name"):
        raise GitHubReleaseError("GitHub did not confirm the private release publication.")
    return updated
