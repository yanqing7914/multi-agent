"""HTTP server built on stdlib http.server."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import DEFAULT_HOST, DEFAULT_PORT
from .routes import health_payload, index_payload, version_payload


class DemoHandler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index"}:
            self._json(index_payload())
            return
        if self.path == "/health":
            self._json(health_payload())
            return
        if self.path == "/version":
            self._json(version_payload())
            return
        self._json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = HTTPServer((host, port), DemoHandler)
    server.serve_forever()
