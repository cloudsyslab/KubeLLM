"""Create or reset the one private KubeLLM operator login."""

from __future__ import annotations

import argparse
import getpass
import secrets

from .auth import AUTH_PATH, create_auth


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="replace the current password and invalidate existing sessions")
    args = parser.parse_args()
    if args.reset:
        first = getpass.getpass("New operator password (at least 14 characters): ")
        second = getpass.getpass("Repeat new operator password: ")
        if first != second:
            parser.error("passwords did not match")
        password = first
    else:
        password = secrets.token_urlsafe(24)
    try:
        create_auth(password, replace=args.reset)
    except (FileExistsError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Operator login initialized. Password: {password}")
    print(f"Private auth settings: {AUTH_PATH.relative_to(AUTH_PATH.parents[2])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
