# -*- coding: utf-8 -*-
"""路线规划核心逻辑测试"""
from hospital_graph import plan_route, graph_payload

# 1. 少走路：入口 -> 检验科
r = plan_route("entrance", "lab", "shortest")
assert r["ok"], r
print("少走路 入口→检验科:", " → ".join(r["path_nodes"]), f"| {r['walk_distance_m']}m {r['total_time_min']}min")

# 2. 少排队：入口 -> 检验科（应避开候梯，走扶梯）
r2 = plan_route("entrance", "lab", "fastest")
assert r2["ok"], r2
print("少排队 入口→检验科:", " → ".join(r2["path_nodes"]), f"| {r2['walk_distance_m']}m {r2['total_time_min']}min")
assert r2["queue_time_min"] == 8

# 3. 无障碍：不得经过楼梯/扶梯
r3 = plan_route("entrance", "imaging", "accessible")
assert r3["ok"], r3
print("无障碍 入口→影像区:", " → ".join(r3["path_nodes"]), f"| {r3['walk_distance_m']}m {r3['total_time_min']}min")
for bad in ("stairs1", "stairs2", "escalator1", "escalator2"):
    assert bad not in r3["path_nodes"], "无障碍路线不应经过楼梯/扶梯"
assert r3["wheelchair"] is True

# 4. 三种偏好都应能到达全部 5 个目的地
for pref in ("shortest", "fastest", "accessible"):
    for to in ("registration", "lab", "imaging", "pharmacy", "exit"):
        rr = plan_route("entrance", to, pref)
        assert rr["ok"], (pref, to, rr)
        assert rr["steps"][-1]["kind"] == "arrive"

# 5. 起点=终点 报错
r5 = plan_route("lab", "lab", "shortest")
assert not r5["ok"] and r5["error"]

# 6. 非法节点 / 非法偏好降级
assert not plan_route("xxx", "lab", "shortest")["ok"]
assert plan_route("entrance", "lab", "bogus")["pref"] == "shortest"

# 7. 药房 -> 出口 直达 22 米
r7 = plan_route("pharmacy", "exit", "shortest")
assert r7["ok"] and r7["walk_distance_m"] == 22

# 8. 图数据接口
g = graph_payload()
assert len(g["nodes"]) == 14 and len(g["edges"]) == 19 and len(g["destinations"]) == 5

print("\n✅ 全部测试通过")
