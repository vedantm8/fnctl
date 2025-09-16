import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Dict, Any

from .runtime import load_spec, invoke_function, write_log
from .utils import functions_dir


class FnctlHandler(BaseHTTPRequestHandler):
    server_version = "fnctl/0.1"

    def log_message(self, format: str, *args) -> None:
        # Suppress access logs when server.quiet is True
        if getattr(self.server, "quiet", False):  # type: ignore[attr-defined]
            return
        return super().log_message(format, *args)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return self.rfile.read(length)
        return b""

    def _send(self, status: int, headers: Dict[str, str], body: bytes):
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _handle(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2 or parts[0] != "fn":
            self._send(404, {"Content-Type": "text/plain"}, b"Not Found")
            return
        name = parts[1]
        fn_base = functions_dir() / name
        try:
            spec = load_spec(name)
        except Exception as e:
            self._send(404, {"Content-Type": "text/plain"}, f"Function not found: {e}".encode())
            return

        body_bytes = self._read_body()
        headers = {k: v for k, v in self.headers.items()}
        event: Dict[str, Any] = {
            "method": self.command,
            "path": parsed.path,
            "query": {k: v if len(v) > 1 else v[0] for k, v in parse_qs(parsed.query).items()},
            "headers": headers,
            "body": body_bytes.decode(errors="ignore"),
        }
        context = {"function": spec.name}

        try:
            status, out_headers, out_body = invoke_function(spec, fn_base, event, context)
        except Exception as e:
            status, out_headers, out_body = 500, {"Content-Type": "text/plain"}, f"Error: {e}".encode()

        if spec.logging:
            try:
                write_log(name, {
                    "request": event,
                    "response": {
                        "status": status,
                        "headers": out_headers,
                        "bodyPreview": out_body[:256].decode(errors="ignore"),
                    },
                })
            except Exception:
                pass

        self._send(status, out_headers, out_body)

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def do_DELETE(self):
        self._handle()


def serve(host: str = "127.0.0.1", port: int = 8080, quiet: bool = False):
    httpd = HTTPServer((host, port), FnctlHandler)
    # Attach a flag so the handler can decide whether to log access lines
    setattr(httpd, "quiet", bool(quiet))
    print(f"fnctl server listening on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
