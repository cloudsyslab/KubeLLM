#!/usr/bin/env python3
"""Run Cloudflare tools with environment or macOS Keychain credentials."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple


KEYCHAIN_SERVICE = "portable-agent-toolkit.cloudflare"
API_ROOT = "https://api.cloudflare.com/client/v4"


class CredentialError(Exception):
    """A safe-to-display credential error without underlying secret data."""


def resolve_token(profile: Optional[str] = None) -> Tuple[str, str]:
    """Explicit profiles select Keychain; implicit default permits environment."""
    if profile is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", profile):
        raise CredentialError("Profile must be 1–64 letters, digits, dots, underscores or hyphens.")
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "") if profile is None else ""
    source = "environment"
    if not token:
        if sys.platform != "darwin":
            raise CredentialError("Supply CLOUDFLARE_API_TOKEN through your secret manager; Keychain requires macOS.")
        try:
            result = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
                 "-a", profile or "default", "-w"],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise CredentialError("Keychain lookup failed or timed out; unlock/authorize the item manually.") from None
        if result.returncode:
            raise CredentialError("Keychain credential unavailable (status %d); check the profile and item access." % result.returncode)
        token = result.stdout.rstrip("\r\n")
        source = "macos-keychain"
    if not token or any(character.isspace() for character in token):
        raise CredentialError("Credential is empty or contains whitespace; replace it in the secret source.")
    return token, source


def child_environment(token: str, account_id: Optional[str], explicit_profile: bool) -> Dict[str, str]:
    environment = dict(os.environ)
    # Prevent legacy global-key authentication from overriding the selected token.
    for key in ("CLOUDFLARE_API_KEY", "CLOUDFLARE_EMAIL", "CF_API_KEY", "CF_EMAIL", "CF_API_TOKEN"):
        environment.pop(key, None)
    if explicit_profile:
        environment.pop("CLOUDFLARE_ACCOUNT_ID", None)
        environment.pop("CF_ACCOUNT_ID", None)
    environment["CLOUDFLARE_API_TOKEN"] = token
    if account_id:
        environment["CLOUDFLARE_ACCOUNT_ID"] = account_id
    return environment


def run_command(command: List[str], token: str, account_id: Optional[str], explicit_profile: bool = False) -> int:
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise CredentialError("Provide a command after run --.")
    try:
        child = subprocess.Popen(
            command, env=child_environment(token, account_id, explicit_profile),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError:
        raise CredentialError("Could not start command; check its executable and working directory.") from None

    def forward(stream, destination):
        for line in iter(stream.readline, b""):
            destination.buffer.write(line.replace(token.encode(), b"[REDACTED]"))
            destination.buffer.flush()
        stream.close()

    threads = [threading.Thread(target=forward, args=(child.stdout, sys.stdout)),
               threading.Thread(target=forward, args=(child.stderr, sys.stderr))]
    for thread in threads:
        thread.start()
    try:
        status = child.wait()
    except KeyboardInterrupt:
        child.terminate()
        child.wait()
        status = 130
    finally:
        for thread in threads:
            thread.join()
    return status if status >= 0 else 128 - status


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api_request(method: str, path: str, token: str, account_id: Optional[str], data_file: Optional[str] = None) -> int:
    if "{account_id}" in path:
        if not account_id:
            raise CredentialError("Supply --account-id or CLOUDFLARE_ACCOUNT_ID for {account_id} paths.")
        path = path.replace("{account_id}", account_id)
    if not path.startswith("/") or path.startswith("//") or "#" in path or any(ord(c) < 33 for c in path):
        raise CredentialError("API path must be a relative /path without fragments or whitespace.")
    body = None
    if data_file:
        if method not in {"POST", "PUT", "PATCH", "DELETE"}:
            raise CredentialError("A JSON body requires POST, PUT, PATCH or DELETE.")
        try:
            body = sys.stdin.buffer.read() if data_file == "-" else Path(data_file).read_bytes()
            json.loads(body)
        except (OSError, ValueError):
            raise CredentialError("Could not read valid JSON from --data-file.") from None
    request = urllib.request.Request(API_ROOT + path, data=body, method=method)
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Accept", "application/json")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            output = response.read()
    except urllib.error.HTTPError as error:
        output = error.read()
        sys.stderr.write("Cloudflare API returned HTTP %d.\n" % error.code)
        sys.stderr.buffer.write(output.replace(token.encode(), b"[REDACTED]") + b"\n")
        return 1
    except (urllib.error.URLError, OSError, ValueError):
        raise CredentialError("Cloudflare API request failed; check network access and the request path.") from None
    sys.stdout.buffer.write(output.replace(token.encode(), b"[REDACTED]") + b"\n")
    try:
        payload = json.loads(output)
        return 1 if isinstance(payload, dict) and payload.get("success") is False else 0
    except ValueError:
        return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Use only this macOS Keychain account; ignore inherited token/account credentials")
    parser.add_argument("--account-id", help="Explicit account for the child environment and API {account_id} paths")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("doctor", help="Check local credential availability without making a network request")
    run = commands.add_parser("run", help="Run a command with credentials in its environment")
    run.add_argument("command", nargs=argparse.REMAINDER)
    api = commands.add_parser("api", help="Call the Cloudflare REST API without credentials in argv")
    api.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    api.add_argument("path")
    api.add_argument("--data-file", help="JSON file, or - to read JSON from stdin")
    arguments = parser.parse_args(argv)
    try:
        if arguments.account_id and not re.fullmatch(r"[A-Za-z0-9_-]+", arguments.account_id):
            raise CredentialError("Account ID must contain only letters, digits, underscores or hyphens.")
        token, source = resolve_token(arguments.profile)
        account_id = arguments.account_id
        if arguments.profile is None and account_id is None:
            account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        if arguments.action == "doctor":
            print(json.dumps({"credential_available": True, "source": source, "profile": arguments.profile or "default",
                              "note": "Local presence only; verify identity/scopes with Wrangler or the API."}))
            return 0
        if arguments.action == "run":
            return run_command(arguments.command, token, account_id, arguments.profile is not None)
        return api_request(arguments.method, arguments.path, token, account_id, arguments.data_file)
    except CredentialError as error:
        if arguments.action == "doctor":
            print(json.dumps({"credential_available": False, "error": str(error)}))
        else:
            sys.stderr.write(str(error) + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
