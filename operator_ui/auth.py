"""Single-operator password setup and signed session helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import STATE, secure_state_dir


AUTH_PATH = STATE / "auth.json"
SESSION_HOURS = 12
PASSWORD_ROUNDS = 360_000


def create_auth(password: str | None = None, *, replace: bool = False) -> str:
    """Create a private single-operator credential, returning its password once."""
    secure_state_dir()
    if AUTH_PATH.exists() and not replace:
        raise FileExistsError("Operator login is already configured; use the password-change command.")
    password = password or secrets.token_urlsafe(20)
    if len(password) < 14:
        raise ValueError("Choose a password with at least 14 characters.")
    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ROUNDS)
    data = {
        "version": 1,
        "password_salt": base64.b64encode(salt).decode("ascii"),
        "password_hash": base64.b64encode(digest).decode("ascii"),
        "session_key": _new_session_key(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_auth(data)
    return password


def _new_session_key() -> str:
    return base64.b64encode(secrets.token_bytes(48)).decode("ascii")


def _write_auth(data: dict) -> None:
    temporary = AUTH_PATH.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, AUTH_PATH)
    os.chmod(AUTH_PATH, 0o600)


def revoke_sessions() -> None:
    """Rotate the session key so every issued session, including copied tokens, stops verifying."""
    data = _auth_data()
    if not data:
        return
    data["session_key"] = _new_session_key()
    _write_auth(data)


def _auth_data() -> dict | None:
    try:
        st = AUTH_PATH.stat(follow_symlinks=False)
        import stat

        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
            return None
        value = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
        if value.get("version") != 1:
            return None
        return value
    except (OSError, ValueError, AttributeError):
        return None


def auth_configured() -> bool:
    return _auth_data() is not None


def verify_password(candidate: str) -> bool:
    data = _auth_data()
    if not data or len(candidate) > 1024:
        hashlib.pbkdf2_hmac("sha256", b"invalid", b"invalid-salt", PASSWORD_ROUNDS)
        return False
    try:
        salt = base64.b64decode(data["password_salt"], validate=True)
        expected = base64.b64decode(data["password_hash"], validate=True)
    except (KeyError, ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", candidate.encode("utf-8"), salt, PASSWORD_ROUNDS)
    return hmac.compare_digest(expected, actual)


def sign_session(session_id: str, expires: int) -> str | None:
    data = _auth_data()
    if not data:
        return None
    key = base64.b64decode(data["session_key"], validate=True)
    payload = f"{session_id}.{expires}".encode("ascii")
    digest = hmac.new(key, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + digest).decode("ascii").rstrip("=")


def make_session() -> tuple[str, int]:
    return secrets.token_urlsafe(24), int((datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).timestamp())


def verify_session(token: str) -> bool:
    if not token or len(token) > 512:
        return False
    try:
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        session_id, expires, mac = decoded.split(b".", maxsplit=2)
        expiry = int(expires)
        if expiry < int(datetime.now(timezone.utc).timestamp()) or expiry > int(
            (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS + 1)).timestamp()
        ):
            return False
        expected_token = sign_session(session_id.decode("ascii"), expiry)
        return bool(expected_token and hmac.compare_digest(expected_token, token))
    except (ValueError, UnicodeError, OSError):
        return False
