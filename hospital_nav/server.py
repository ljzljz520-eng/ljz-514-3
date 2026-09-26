# -*- coding: utf-8 -*-
"""零依赖后端：http.server 提供静态页 + 导航 JSON API。"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import planner
from graph import NODES, EDGES, ROOMS, CATEGORY_ORDER, CATEGORY_LABEL

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")

planner.refresh_queues(seed=42)

def node_payload(nid, n):
    item = {
        "id": nid, "label": n["label"], "x": n["x"], "y": n["y"],
        "category": n.get("category"),
        "categoryAlt": n.get("category_alt"),
        "queue": planner.current_queue(nid) if n.get("service") else None,
    }
    s = n.get("service")
    if s:
        item["serviceMin"] = s[1]
        item["accessible"] = s[2]
    return item

def api_state():
    return {
        "nodes": [node_payload(i, n) for i, n in NODES.items()],
        "edges": [{"a": e["a"], "b": e["b"], "dist": e["dist"],
                   "crowd": e["crowd"], "accessible": e["accessible"],
                   "type": e["type"]} for e in EDGES],
        "rooms": ROOMS,
        "categoryOrder": CATEGORY_ORDER,
        "categoryLabel": CATEGORY_LABEL,
    }

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/state":
            self._send(200, api_state())
            return
        if path in ("/", "/index.html"):
            path = "/index.html"
        safe = os.path.normpath(path.lstrip("/")).replace("..", "")
        fp = os.path.join(STATIC, safe)
        if os.path.isfile(fp):
            ctype = "text/html; charset=utf-8" if fp.endswith(".html") else \
                    "text/css; charset=utf-8" if fp.endswith(".css") else \
                    "application/javascript; charset=utf-8" if fp.endswith(".js") else \
                    "application/octet-stream"
            with open(fp, "rb") as f:
                self._send(200, f.read(), ctype)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid json"})
            return

        if path == "/api/refresh":
            snap = planner.refresh_queues(seed=payload.get("seed"))
            state = api_state()
            state["queues"] = snap
            self._send(200, state)
            return

        if path == "/api/plan":
            start = payload.get("start", "south_gate")
            cats = payload.get("categories", [])
            mode = payload.get("mode", "walk")
            if start not in NODES:
                self._send(400, {"error": f"未知起点: {start}"}); return
            if mode not in ("walk", "queue", "accessible"):
                self._send(400, {"error": f"未知偏好: {mode}"}); return
            bad = [c for c in cats if c not in CATEGORY_ORDER]
            if bad:
                self._send(400, {"error": f"未知目的地类别: {bad}"}); return
            result = planner.plan(start, cats, mode)
            if "error" in result:
                self._send(422, result)
            else:
                self._send(200, result)
            return

        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"医院陪诊导航已启动: http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
