#!/usr/bin/env python3
"""Serve an explicit directory on loopback, print the healthy URL, and stay running."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import signal
import sys
import threading
from urllib.error import URLError
from urllib.request import urlopen


class NarrowHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_head(self):
        root = Path(self.directory).resolve()
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            for name in ("index.html", "index.htm"):
                candidate = path / name
                if candidate.is_file():
                    path = candidate
                    break
        if not path.resolve().is_relative_to(root):
            self.send_error(403, "Path escapes preview directory")
            return None
        return super().send_head()


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def handle_error(self, _request: object, _client_address: object) -> None:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path, help="Explicit directory to serve")
    parser.add_argument("--port", type=int, default=0, help="Loopback port (0 selects a free port)")
    args = parser.parse_args()
    directory = args.directory.expanduser().resolve()
    if not directory.is_dir():
        parser.error("--directory must be an existing directory")
    if not 0 <= args.port <= 65535:
        parser.error("--port must be 0..65535")
    try:
        server = QuietServer(("127.0.0.1", args.port), partial(NarrowHandler, directory=str(directory)))
    except OSError as error:
        print("ERROR: loopback preview bind failed: " + str(error) + ". Retry this exact command "
              "through established approval for the explicit directory and 127.0.0.1 bind; "
              "do not change global permissions.", file=sys.stderr)
        return 1
    stopped = threading.Event()
    previous = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.signal(sig, lambda _sig, _frame: stopped.set())
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        with urlopen(url, timeout=5) as response:
            status = response.status
            response.read(1024)
        if status != 200:
            raise URLError(f"HTTP {status}")
        print(json.dumps({"url": url, "directory": str(directory), "health": "HTTP 200",
                          "lifetime": "running until SIGINT or SIGTERM"}), flush=True)
        while not stopped.wait(0.25):
            pass
        return 0
    except (OSError, URLError) as error:
        print(f"ERROR: loopback preview health failed: {error}", file=sys.stderr)
        return 1
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())
