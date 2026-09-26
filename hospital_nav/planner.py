# -*- coding: utf-8 -*-
"""
路线规划：图搜索 + Dijkstra
三种偏好：
  walk      少走路：代价≈距离
  queue     少排队：代价≈步行时间 + 通道拥堵时间 + 排队时间 + 基础办理时间
  accessible 无障碍：屏蔽不可用通道/高柜窗口；其余尽量短
就诊顺序固定：挂号处 → 检验科 → 影像区 → 药房 → 出口，
每一类服务点内部用 Dijkstra 选最优窗口；阶段间用动态规划拼接。
"""
import heapq
import random

from graph import (NODES, EDGES, build_adj, CATEGORY_ORDER,
                   CATEGORY_LABEL, SERVICE_ACTION)

WALK_SPEED = 48.0          # 陪诊步行速度 米/分钟（约0.8m/s，含慢行/等电梯感）
INACCESS_PENALTY = 800.0   # 无障碍模式下每段不可用通道的代价（米）
INACCESS_SVC_PENALTY = 800.0
BASE_SERVICE_MIN = 2.0     # 非“少排队”模式下窗口办理的统一基础时间
ADJ = build_adj()

# 运行时排队快照（可随机刷新，模拟实时叫号）
_queue_snapshot = {}

def _service(node_id):
    return NODES[node_id].get("service")

def current_queue(node_id):
    if not _service(node_id):
        return 0.0
    return float(_queue_snapshot.get(node_id, _service(node_id)[0]))

def current_service_min(node_id):
    return float(_service(node_id)[1]) if _service(node_id) else 0.0

def refresh_queues(seed=None):
    """在基础排队时长上 ±40% 随机波动，模拟实时叫号。"""
    rng = random.Random(seed)
    snap = {}
    for nid, n in NODES.items():
        s = n.get("service")
        if s:
            base = s[0]
            snap[nid] = max(1, round(base * rng.uniform(0.6, 1.4)))
    _queue_snapshot.clear()
    _queue_snapshot.update(snap)
    return dict(snap)

def all_queues():
    if not _queue_snapshot:
        refresh_queues(seed=42)
    return dict(_queue_snapshot)

# ---------------- 代价 ----------------
def edge_cost(e, mode):
    if mode == "walk":
        return e["dist"]
    if mode == "queue":
        walk = e["dist"] / WALK_SPEED
        crowd = e["crowd"] * 0.6          # 每级拥堵 +0.6 分钟
        return walk + crowd
    if mode == "accessible":
        c = e["dist"]
        if not e["accessible"]:
            c += INACCESS_PENALTY
        return c
    raise ValueError(mode)

def entry_cost(v, mode):
    """进入服务窗口节点的附加代价（排队/办理/无障碍）。"""
    s = _service(v)
    if not s:
        return 0.0
    accessible = s[2]
    if mode == "queue":
        return current_queue(v) + BASE_SERVICE_MIN
    if mode == "accessible":
        return 0.0 if accessible else INACCESS_SVC_PENALTY
    # walk 模式：计入统一基础办理时间，不鼓励为近而绕远窗
    return BASE_SERVICE_MIN * WALK_SPEED * 0.0 + 0.0

def usable_node(v, mode):
    if mode == "accessible":
        s = _service(v)
        if s and not s[2]:
            return False
    return True

# ---------------- Dijkstra ----------------
def dijkstra(src, dst_set, mode):
    """从 src 出发到目标集合中任意节点的最短路径。
    返回 {dst: (cost, nodes[], edges[])}。
    """
    dist = {src: 0.0}
    prev = {}                 # node -> (from_node, edge)
    pq = [(0.0, src)]
    found = {}
    remain = set(dst_set)

    while pq and remain:
        d, u = heapq.heappop(pq)
        if d != dist.get(u):
            continue
        if u in remain:
            remain.remove(u)
            path_nodes, path_edges = _rebuild(prev, src, u)
            found[u] = (d, path_nodes, path_edges)
            # 不 break：可能还有其它目标节点更优
        for e in ADJ[u]:
            v = e["b"] if e["a"] == u else e["a"]
            if not usable_node(v, mode):
                continue
            nd = d + edge_cost(e, mode) + entry_cost(v, mode)
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = (u, e)
                heapq.heappush(pq, (nd, v))
    return found

def _rebuild(prev, src, dst):
    nodes, edges = [dst], []
    cur = dst
    while cur != src:
        u, e = prev[cur]
        edges.append(e)
        nodes.append(u)
        cur = u
    nodes.reverse()
    edges.reverse()
    return nodes, edges

# ---------------- 分阶段规划 ----------------
def _candidates(category):
    out = []
    for nid, n in NODES.items():
        cat = n.get("category")
        if cat == category or n.get("category_alt") == category:
            out.append(nid)
    return out

def plan(start, categories, mode):
    """categories 按就诊顺序排列；返回完整路线与统计。"""
    # layers[layer][node] = (cost, prev_node_in_prev_layer, nodes_segment, edges_segment)
    layers = [{start: (0.0, None, [start], [])}]
    for cat in categories:
        new_dp = {}
        cands = _candidates(cat)
        if cat == "exit" and start in cands and len(cands) > 1:
            cands = [c for c in cands if c != start]
        for frm, (base, _, _, _) in layers[-1].items():
            res = dijkstra(frm, cands, mode)
            for cand, (c, nodes, edges) in res.items():
                total = base + c
                if total < new_dp.get(cand, (float("inf"),))[0]:
                    new_dp[cand] = (total, frm, nodes, edges)
        if not new_dp:
            return {"error": f"没有可达的{CATEGORY_LABEL.get(cat, cat)}"}
        dp = new_dp
        layers.append(new_dp)

    # 选终点
    end = min(layers[-1], key=lambda k: layers[-1][k][0])
    # 按层回溯拼接
    node_path, edge_path, stops = [], [], []
    cur = end
    seg_rev = []
    for layer in range(len(layers) - 1, 0, -1):
        total, frm, nodes, edges = layers[layer][cur]
        seg_rev.append((cur, nodes, edges))
        cur = frm
    seg_rev.reverse()

    for stop_node, nodes, edges in seg_rev:
        if node_path and nodes and nodes[0] == node_path[-1]:
            node_path.extend(nodes[1:])
        else:
            node_path.extend(nodes)
        edge_path.extend(edges)
        if stop_node != start:
            stops.append(stop_node)

    stats = _stats(edge_path, stops, start, end, mode)
    steps = build_steps(edge_path, node_path, stops, mode)
    return {
        "mode": mode,
        "start": start,
        "end": end,
        "stops": stops,
        "nodePath": node_path,
        "edgePath": [[e["a"], e["b"]] for e in edge_path],
        "steps": steps,
        "stats": stats,
    }

# ---------------- 统计 ----------------
def _stats(edge_path, stops, start, end, mode):
    walk = sum(e["dist"] for e in edge_path)
    crowd = sum(e["crowd"] * 0.6 for e in edge_path)
    svc_stops = [s for s in stops if _service(s)]
    # 时间口径对三种模式统一（实时排队 + 实际办理 + 拥堵），模式差异体现在所选路径上
    queue_min = sum(current_queue(s) for s in svc_stops)
    service_min = sum(current_service_min(s) for s in svc_stops)
    walk_min = walk / WALK_SPEED
    total = walk_min + crowd + queue_min + service_min
    inaccess = sum(1 for e in edge_path if not e["accessible"])
    inaccess += sum(1 for s in svc_stops if not _service(s)[2])
    return {
        "distance_m": round(walk, 1),
        "walk_min": round(walk_min, 1),
        "queue_min": round(queue_min, 1),
        "service_min": round(service_min, 1),
        "crowd_min": round(crowd, 1),
        "total_min": round(total, 1),
        "inaccessible_segments": inaccess,
    }

# ---------------- 步骤文本 ----------------
def _bearing(p, q):
    import math
    ang = math.degrees(math.atan2(q["y"] - p["y"], q["x"] - p["x"]))
    return (ang + 360) % 360

def _turn_text(b1, b2):
    diff = (b2 - b1 + 540) % 360 - 180      # -180..180
    if abs(diff) <= 30:
        return "直行"
    if diff > 0:
        return "左转" if diff <= 100 else "掉头"
    return "右转" if diff >= -100 else "掉头"

def _place_phrase(node_id):
    label = NODES[node_id]["label"]
    return label

def build_steps(edge_path, node_path, stops, mode):
    """把逐边路径压缩成“转弯/到达”步骤。"""
    stop_set = set(stops)
    steps = []
    stop_idx = 0
    i = 0
    n = len(node_path)

    # 出发提示
    steps.append({
        "kind": "start",
        "text": f"从{_place_phrase(node_path[0])}出发，开始院内陪诊路线。",
    })

    while i < n - 1:
        j = i
        seg_edges = []
        bearing0 = _bearing(NODES[node_path[i]], NODES[node_path[i + 1]])
        bearing = bearing0
        while j < n - 1:
            nxt_b = _bearing(NODES[node_path[j]], NODES[node_path[j + 1]])
            at_stop = node_path[j + 1] in stop_set
            turn = _turn_text(bearing0, nxt_b)
            if j > i and turn != "直行":
                break
            seg_edges.append(edge_path[j])
            bearing = nxt_b
            j += 1
            if at_stop:
                break

        a_node, b_node = node_path[i], node_path[j]
        dist = sum(e["dist"] for e in seg_edges)
        # 特殊通道提示
        kinds = {e["type"] for e in seg_edges}
        via = ""
        if "stairs" in kinds:
            via = "（途经台阶）"
        elif "ramp" in kinds:
            via = "（经无障碍坡道）"

        if b_node in stop_set:
            stop_idx += 1
            steps.extend(_arrival_steps(b_node, stop_idx, len(stops)))
        else:
            steps.append({
                "kind": "walk",
                "text": f"沿通道前行约{round(dist)}米{via}，到达{_place_phrase(b_node)}。",
            })
        i = j

    steps.append({
        "kind": "end",
        "text": f"到达终点{_place_phrase(node_path[-1])}，本次陪诊路线结束。",
    })
    return steps

def _arrival_steps(node_id, idx, total_stops):
    n = NODES[node_id]
    cat = n.get("category") or n.get("category_alt")
    s = _service(node_id)
    out = []
    if s:
        q = current_queue(node_id)
        act = SERVICE_ACTION.get(cat, "办理")
        out.append({
            "kind": "arrive",
            "text": f"第{idx}站 · {n['label']}：在此{act}，"
                    f"预计排队约{round(q)}分钟、办理约{round(current_service_min(node_id))}分钟。",
        })
        if not s[2]:
            out.append({
                "kind": "warn",
                "text": "注意：该窗口为高柜台，轮椅患者不便，请改选无障碍窗口。",
            })
    else:
        out.append({
            "kind": "arrive",
            "text": f"第{idx}站 · {n['label']}，前往下一目的地。",
        })
    return out
