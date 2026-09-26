#!/usr/bin/env python3
"""Deterministic loopback-only GitHub-like fixture for the comparison."""

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPOSITORIES = (
    "PVRLabs/statlite",
    "PVRLabs/aibadger",
    "scriptella/scriptella-etl",
)


class FixtureHandler(BaseHTTPRequestHandler):
    responses = {}
    request_log = None

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            self._send(200, b"ok\n", "text/plain; charset=utf-8")
            return
        prefix = "/repos/"
        if path.startswith(prefix):
            repo = path[len(prefix) :].rstrip("/").replace("/", "/", 1)
            body = self.responses.get(repo)
            if body is not None:
                self._send(200, body, "application/json")
                return
        self._send(404, b'{"message":"not found"}\n', "application/json")

    def log_message(self, format, *args):  # noqa: A002 - BaseHTTPRequestHandler API
        if self.request_log:
            self.request_log.info("%s %s %s", self.command, self.path, args[1])

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def load_responses(directory):
    responses = {}
    for repo in REPOSITORIES:
        filename = repo.replace("/", "__") + ".json"
        path = directory / filename
        data = json.loads(path.read_text())
        responses[repo] = (json.dumps(data, separators=(",", ":")) + "\n").encode()
    return responses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--responses", type=Path, default=Path(__file__).with_name("responses"))
    parser.add_argument("--log", type=Path, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format="%(asctime)s %(message)s",
    )
    FixtureHandler.responses = load_responses(args.responses)
    FixtureHandler.request_log = logging.getLogger("fixture.requests")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), FixtureHandler)
    logging.info("fixture_ready address=127.0.0.1:%d repositories=%d", args.port, len(REPOSITORIES))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
