# -*- coding: utf-8 -*-
"""医院陪诊楼内导航 —— 零依赖后端（Python 标准库）"""
import json
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from hospital_graph import plan_route, graph_payload

BASE = os.path.dirname(os.path.abspath(__file__))

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/route":
            q = parse_qs(parsed.query)
            result = plan_route(
                q.get("from", ["entrance"])[0],
                q.get("to", ["registration"])[0],
                q.get("pref", ["shortest"])[0],
            )
            self._json(result, 200 if result.get("ok") else 400)
        elif parsed.path == "/api/graph":
            self._json(graph_payload())
        else:
            if parsed.path in ("/", ""):
                self.path = "/static/index.html"
            super().do_GET()

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    os.chdir(BASE)
    port = int(os.environ.get("PORT", 8000))
    print(f"🏥 医院陪诊导航服务已启动: http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
