# -*- coding: utf-8 -*-
"""
院内楼层地图：无向图
- node: 大厅 / 连廊 / 服务窗口 / 出入口
- edge: 可双向通行的通道，属性含 距离(m)、拥挤度、是否无障碍、类型
坐标单位：米（仅本层平面，北翼=检验/影像，南翼=挂号/药房/南门）
"""
import math

# ---------------- 节点 ----------------
# category: entrance / exit / registration / laboratory / imaging / pharmacy / None
# service: 仅服务窗口有 -> (排队分钟, 办理分钟, 是否无障碍)
NODES = {
    # 主走廊（东西向）
    "lobby_west":      {"label": "西侧连廊",   "x": -40, "y":   0},
    "entrance_hall":   {"label": "门诊大厅",   "x":   0, "y":   0},
    "lobby_east":      {"label": "东侧连廊",   "x":  40, "y":   0},
    # 北翼分支
    "lab_link":        {"label": "检验连廊",   "x":   0, "y":  12},
    "img_link":        {"label": "影像连廊",   "x":  40, "y":  12},
    "exit_link":       {"label": "北口连廊",   "x": -40, "y":  12},
    # 南翼分支
    "reg_link":        {"label": "挂号连廊",   "x":   0, "y": -12},
    "phar_link":       {"label": "药房连廊",   "x": -40, "y": -12},
    # 检验科
    "lab_hall":        {"label": "检验科候诊厅", "x":   0, "y":  24},
    "lab_wait":        {"label": "体液检验窗",  "x":  -9, "y":  36,
                        "category": "laboratory", "service": (18, 8, True)},
    "lab_lab":         {"label": "常规抽血窗",  "x":   0, "y":  36,
                        "category": "laboratory", "service": (10, 10, True)},
    "lab_quick":       {"label": "快速检验窗",  "x":   9, "y":  36,
                        "category": "laboratory", "service": (6, 5, True)},
    # 影像科
    "img_hall":        {"label": "影像科候诊厅", "x":  40, "y":  24},
    "img_xray":        {"label": "X光室",      "x":  28, "y":  36,
                        "category": "imaging", "service": (9, 10, True)},
    "img_ct":          {"label": "CT室",       "x":  40, "y":  36,
                        "category": "imaging", "service": (15, 12, True)},
    "img_mri":         {"label": "MRI室",      "x":  52, "y":  36,
                        "category": "imaging", "service": (22, 15, True)},
    # 挂号处
    "reg_hall":        {"label": "挂号大厅",   "x":   0, "y": -24},
    "reg_1":           {"label": "1号挂号窗",  "x": -11, "y": -40,
                        "category": "registration", "service": (4, 6, True)},
    "reg_2":           {"label": "2号挂号窗",  "x":   0, "y": -40,
                        "category": "registration", "service": (7, 6, True)},
    "reg_3":           {"label": "3号挂号窗(高柜)", "x": 11, "y": -40,
                        "category": "registration", "service": (12, 5, False)},
    # 药房
    "phar_hall":       {"label": "药房大厅",   "x": -40, "y": -24},
    "phar_pickup":     {"label": "取药窗",     "x": -51, "y": -35,
                        "category": "pharmacy", "service": (5, 4, True)},
    "phar_pay":        {"label": "缴费窗",     "x": -29, "y": -35,
                        "category": "pharmacy", "service": (9, 3, True)},
    # 南门：台阶(无障碍不可用) vs 坡道(无障碍)
    "foyer":           {"label": "南门门厅",   "x":   0, "y": -32},
    "south_stairs":    {"label": "南门台阶",   "x":   0, "y": -37},
    "ramp":            {"label": "无障碍坡道", "x": -13, "y": -35},
    "south_gate":      {"label": "南门",       "x":   0, "y": -44,
                        "category": "entrance"},
    # 北门（出口，平路）
    "north_gate":      {"label": "北门",       "x": -40, "y":  22,
                        "category": "exit"},
}
# 南门、北门都可作为出口
NODES["south_gate"]["category_alt"] = "exit"

# ---------------- 边（无向） ----------------
# (a, b, 距离m|None按坐标, 拥挤度0-3, 是否无障碍, 类型 corridor/stairs/ramp)
def _d(a, b):
    return round(math.hypot(NODES[a]["x"] - NODES[b]["x"],
                            NODES[a]["y"] - NODES[b]["y"]), 1)

RAW_EDGES = [
    # 主走廊
    ("lobby_west", "entrance_hall", None, 2, True, "corridor"),
    ("entrance_hall", "lobby_east", None, 3, True, "corridor"),
    # 北翼
    ("entrance_hall", "lab_link", None, 2, True, "corridor"),
    ("lab_link", "lab_hall", None, 2, True, "corridor"),
    ("lobby_east", "img_link", None, 3, True, "corridor"),
    ("img_link", "img_hall", None, 2, True, "corridor"),
    ("lobby_west", "exit_link", None, 1, True, "corridor"),
    ("exit_link", "north_gate", None, 0, True, "corridor"),
    ("lab_link", "img_link", None, 2, True, "corridor"),
    # 检验科大厅 -> 窗口，窗口间短连
    ("lab_hall", "lab_wait", None, 1, True, "corridor"),
    ("lab_hall", "lab_lab", None, 1, True, "corridor"),
    ("lab_hall", "lab_quick", None, 1, True, "corridor"),
    ("lab_wait", "lab_lab", None, 1, True, "corridor"),
    ("lab_lab", "lab_quick", None, 1, True, "corridor"),
    # 影像科大厅 -> 机房
    ("img_hall", "img_xray", None, 1, True, "corridor"),
    ("img_hall", "img_ct", None, 1, True, "corridor"),
    ("img_hall", "img_mri", None, 1, True, "corridor"),
    ("img_xray", "img_ct", None, 1, True, "corridor"),
    ("img_ct", "img_mri", None, 1, True, "corridor"),
    # 南翼
    ("entrance_hall", "reg_link", None, 3, True, "corridor"),
    ("reg_link", "reg_hall", None, 3, True, "corridor"),
    ("reg_hall", "foyer", None, 1, True, "corridor"),
    ("lobby_west", "phar_link", None, 1, True, "corridor"),
    ("phar_link", "phar_hall", None, 1, True, "corridor"),
    # 挂号大厅 -> 窗口
    ("reg_hall", "reg_1", None, 2, True, "corridor"),
    ("reg_hall", "reg_2", None, 2, True, "corridor"),
    ("reg_hall", "reg_3", None, 2, True, "corridor"),
    ("reg_1", "reg_2", None, 2, True, "corridor"),
    ("reg_2", "reg_3", None, 2, True, "corridor"),
    # 药房大厅 -> 窗口
    ("phar_hall", "phar_pickup", None, 1, True, "corridor"),
    ("phar_hall", "phar_pay", None, 1, True, "corridor"),
    ("phar_pickup", "phar_pay", None, 1, True, "corridor"),
    # 南门：台阶（近，但轮椅不可用）
    ("foyer", "south_stairs", None, 0, False, "stairs"),
    ("south_stairs", "south_gate", None, 0, False, "stairs"),
    # 南门：无障碍坡道（绕远，但轮椅可用）
    ("foyer", "ramp", 13, 0, True, "ramp"),
    ("ramp", "south_gate", 14, 0, True, "ramp"),
]

EDGES = []
for a, b, dist, crowd, accessible, kind in RAW_EDGES:
    EDGES.append({
        "a": a, "b": b,
        "dist": dist if dist is not None else _d(a, b),
        "crowd": crowd, "accessible": accessible, "type": kind,
    })

# ---------------- 绘制用房间区块 ----------------
ROOMS = [
    {"name": "检验科",   "x": -17, "y": 30, "w": 34, "h": 11},
    {"name": "影像科",   "x":  21, "y": 30, "w": 38, "h": 11},
    {"name": "挂号处",   "x": -20, "y": -46, "w": 40, "h": 12},
    {"name": "药房",     "x": -59, "y": -41, "w": 36, "h": 12},
]

CATEGORY_ORDER = ["registration", "laboratory", "imaging", "pharmacy", "exit"]
CATEGORY_LABEL = {
    "registration": "挂号处",
    "laboratory": "检验科",
    "imaging": "影像区",
    "pharmacy": "药房",
    "exit": "出口",
}
SERVICE_ACTION = {
    "registration": "挂号登记",
    "laboratory": "采样/检验",
    "imaging": "影像检查",
    "pharmacy": "药房办理",
}

def build_adj():
    """构建邻接表（无向图）。"""
    adj = {n: [] for n in NODES}
    for e in EDGES:
        adj[e["a"]].append(e)
        adj[e["b"]].append(e)
    return adj

if __name__ == "__main__":
    print(f"nodes={len(NODES)} edges={len(EDGES)}")
