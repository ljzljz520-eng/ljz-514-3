# -*- coding: utf-8 -*-
"""医院楼内导航：图结构 + Dijkstra 路线规划"""
import heapq

# ---------------- 图数据 ----------------
# 节点: id -> 名称 / 楼层 / 地图坐标 / 类型
NODES = {
    "entrance":     {"name": "入口大厅", "floor": "1F", "x": 90,  "y": 400, "type": "transit"},
    "lobby":      {"name": "门诊大厅", "floor": "1F", "x": 220, "y": 310, "type": "transit"},
    "registration": {"name": "挂号处",   "floor": "1F", "x": 100, "y": 150, "type": "service"},
    "pharmacy":     {"name": "药房",     "floor": "1F", "x": 340, "y": 150, "type": "service"},
    "exit":         {"name": "出口",     "floor": "1F", "x": 395, "y": 400, "type": "service"},
    "elevator1":    {"name": "电梯厅",   "floor": "1F", "x": 350, "y": 300, "type": "lift"},
    "stairs1":      {"name": "楼梯",     "floor": "1F", "x": 110, "y": 290, "type": "lift"},
    "escalator1":   {"name": "扶梯",     "floor": "1F", "x": 235, "y": 425, "type": "lift"},
    "elevator2":    {"name": "电梯厅",   "floor": "2F", "x": 830, "y": 300, "type": "lift"},
    "stairs2":      {"name": "楼梯",     "floor": "2F", "x": 590, "y": 290, "type": "lift"},
    "escalator2":   {"name": "扶梯",     "floor": "2F", "x": 705, "y": 425, "type": "lift"},
    "corridor2":    {"name": "二层走廊", "floor": "2F", "x": 705, "y": 210, "type": "transit"},
    "lab":          {"name": "检验科",   "floor": "2F", "x": 570, "y": 110, "type": "service"},
    "imaging":      {"name": "影像区",   "floor": "2F", "x": 835, "y": 110, "type": "service"},
}

# 边: (a, b, 距离m, 类型, 是否无障碍, 拥挤系数)
EDGES = [
    ("entrance", "lobby",        18, "walk",      True, 1.0),
    ("entrance", "escalator1",   16, "walk",      True, 1.0),
    ("entrance", "exit",         32, "walk",      True, 1.0),
    ("lobby", "registration",    26, "walk",      True, 1.4),  # 挂号高峰拥挤
    ("lobby", "pharmacy",        24, "walk",      True, 1.1),
    ("lobby", "elevator1",       14, "walk",      True, 1.0),
    ("lobby", "stairs1",         12, "walk",      True, 1.0),
    ("registration", "pharmacy", 30, "walk",      True, 1.0),
    ("pharmacy", "elevator1",    12, "walk",      True, 1.0),
    ("pharmacy", "exit",         22, "walk",      True, 1.0),
    ("elevator1", "elevator2",    6, "elevator",  True, 1.0),  # 无障碍垂直交通
    ("stairs1", "stairs2",       24, "stairs",   False, 1.0),
    ("escalator1", "escalator2", 20, "escalator",False, 1.0),
    ("elevator2", "corridor2",   12, "walk",      True, 1.0),
    ("stairs2", "corridor2",     14, "walk",      True, 1.0),
    ("escalator2", "corridor2",  16, "walk",      True, 1.0),
    ("corridor2", "lab",         18, "walk",      True, 1.0),
    ("corridor2", "imaging",     16, "walk",      True, 1.3),  # 影像候诊人群
    ("lab", "imaging",           28, "walk",      True, 1.0),
]

# 各服务点预计排队时间（分钟）
QUEUE_MIN = {"registration": 12, "lab": 8, "imaging": 20, "pharmacy": 6, "exit": 0}

PREFS = {"shortest": "少走路", "fastest": "少排队", "accessible": "无障碍优先"}

# 目的地 / 可选起点
DESTINATIONS = ["registration", "lab", "imaging", "pharmacy", "exit"]
STARTS = ["entrance", "registration", "lab", "imaging", "pharmacy"]

# ---------------- 图构建 ----------------
def _build():
    g = {nid: [] for nid in NODES}
    for a, b, dist, kind, accessible, congestion in EDGES:
        g[a].append({"from": a, "to": b, "distance": dist, "kind": kind,
                     "accessible": accessible, "congestion": congestion})
        g[b].append({"from": b, "to": a, "distance": dist, "kind": kind,
                     "accessible": accessible, "congestion": congestion})
    return g

GRAPH = _build()

# ---------------- 时间模型 ----------------
SPEED = {"walk": 1.25, "stairs": 0.6, "escalator": 0.9}  # m/s
WHEELCHAIR_SPEED = 1.0
ELEVATOR_WAIT_SEC = 45   # 候梯
ELEVATOR_RIDE_SEC = 12   # 乘梯

def edge_time_sec(e, wheelchair=False):
    if e["kind"] == "elevator":
        return ELEVATOR_WAIT_SEC + ELEVATOR_RIDE_SEC
    speed = WHEELCHAIR_SPEED if wheelchair else SPEED[e["kind"]]
    return e["distance"] / speed * e["congestion"]

# ---------------- Dijkstra ----------------
def dijkstra(start, goal, weight, allowed):
    """按 weight(e) 求最短路，allowed(e) 过滤不可用边（如无障碍模式过滤楼梯）。"""
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    done = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        if u == goal:
            break
        for e in GRAPH[u]:
            if not allowed(e):
                continue
            nd = d + weight(e)
            v = e["to"]
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = (u, e)
                heapq.heappush(pq, (nd, v))
    if goal not in dist:
        return None
    path, node = [], goal
    while node != start:
        u, e = prev[node]
        path.append(e)
        node = u
    path.reverse()
    return dist[goal], path

# ---------------- 路线规划 ----------------
def plan_route(start, to, pref):
    if start not in NODES or to not in NODES:
        return {"ok": False, "error": "未知的起点或终点"}
    if pref not in PREFS:
        pref = "shortest"
    if start == to:
        return {"ok": False, "error": "您已在目的地附近，无需导航"}

    wheelchair = pref == "accessible"
    if pref == "shortest":            # 少走路：最小化步行距离
        weight, allowed = (lambda e: e["distance"]), (lambda e: True)
    elif pref == "fastest":           # 少排队：最小化通行时间（含拥挤与候梯）
        weight, allowed = (lambda e: edge_time_sec(e)), (lambda e: True)
    else:                             # 无障碍优先：仅走无障碍通道，再求最短
        weight, allowed = (lambda e: e["distance"]), (lambda e: e["accessible"])

    result = dijkstra(start, to, weight, allowed)
    if not result:
        return {"ok": False, "error": "未找到可达路线，请咨询现场工作人员"}
    _, path = result

    walk_dist = sum(e["distance"] for e in path if e["kind"] == "walk")
    walk_sec = sum(edge_time_sec(e, wheelchair) for e in path)
    queue_min = QUEUE_MIN.get(to, 0)
    return {
        "ok": True,
        "pref": pref,
        "pref_label": PREFS[pref],
        "from": {"id": start, "name": NODES[start]["name"]},
        "to": {"id": to, "name": NODES[to]["name"], "floor": NODES[to]["floor"]},
        "steps": _build_steps(path, to, wheelchair),
        "path_nodes": [path[0]["from"]] + [e["to"] for e in path],
        "walk_distance_m": round(walk_dist),
        "walk_time_min": round(walk_sec / 60, 1),
        "queue_time_min": queue_min,
        "total_time_min": round(walk_sec / 60 + queue_min, 1),
        "wheelchair": wheelchair,
    }

def _build_steps(path, dest, wheelchair):
    steps = []
    for e in path:
        a, b = NODES[e["from"]], NODES[e["to"]]
        kind = e["kind"]
        if kind == "walk":
            icon = "🦽" if wheelchair else "🚶"
            text = f"步行 {e['distance']} 米，前往{b['name']}"
            detail = f"{a['floor']} · 约 {round(edge_time_sec(e, wheelchair) / 60, 1)} 分钟"
        elif kind == "elevator":
            icon, text = "🛗", f"乘无障碍电梯，从 {a['floor']} 到 {b['floor']}"
            detail = "候梯+乘梯约 1 分钟"
        elif kind == "stairs":
            icon, text = "🪜", f"走楼梯，从 {a['floor']} 到 {b['floor']}"
            detail = "注意台阶，扶好扶手"
        else:
            icon, text = "↗️", f"乘扶梯，从 {a['floor']} 到 {b['floor']}"
            detail = "请站稳扶好"
        steps.append({"icon": icon, "text": text, "detail": detail,
                      "kind": kind, "floor": b["floor"]})
    arrive = f"到达 {NODES[dest]['name']}"
    q = QUEUE_MIN.get(dest, 0)
    steps.append({"icon": "📍", "text": arrive, "kind": "arrive",
                  "floor": NODES[dest]["floor"],
                  "detail": f"预计排队 {q} 分钟" if q else "已到达"})
    return steps

def graph_payload():
    return {
        "nodes": [{"id": k, **v} for k, v in NODES.items()],
        "edges": [{"a": a, "b": b, "distance": d, "kind": k2, "accessible": acc}
                  for a, b, d, k2, acc, _ in EDGES],
        "queue": QUEUE_MIN,
        "destinations": DESTINATIONS,
        "starts": STARTS,
        "prefs": [{"id": k, "label": v} for k, v in PREFS.items()],
    }
