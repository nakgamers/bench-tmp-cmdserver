#!/usr/bin/env python3
"""Tiny authenticated remote-exec HTTP server (stdlib only).
POST /exec  headers: X-Token: <token>   body: {"cmd": "...", "timeout": 120}
  -> {"rc": int, "out": "...", "err": "..."}
GET  /ping -> "pong" (no auth needed, liveness only)
"""
import http.server
import json
import subprocess

TOKEN = "B3nch-S3cr3t-9f2k7q"
PORT = 10200
MAXOUT = 30000


class H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, data, ctype="application/json"):
        body = data if isinstance(data, bytes) else data.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ping":
            self._send(200, "pong", "text/plain")
        else:
            self._send(404, "nope", "text/plain")

    def do_POST(self):
        if self.path != "/exec" or self.headers.get("X-Token") != TOKEN:
            self._send(403, "forbidden", "text/plain")
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        cmd = body.get("cmd", "")
        timeout = min(int(body.get("timeout", 120)), 1500)
        try:
            p = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            out = {"rc": p.returncode,
                   "out": p.stdout[-MAXOUT:], "err": p.stderr[-MAXOUT:]}
        except subprocess.TimeoutExpired as e:
            so = (e.stdout or b"")
            so = so.decode(errors="replace") if isinstance(so, bytes) else so
            out = {"rc": -1, "out": so[-MAXOUT:], "err": "TIMEOUT"}
        except Exception as e:
            out = {"rc": -2, "out": "", "err": repr(e)}
        self._send(200, json.dumps(out))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
