# 🏥 智慧陪诊 · 楼内导航

医院陪诊楼内导航页：患者选择目的地（挂号处 / 检验科 / 影像区 / 药房 / 出口），
系统按 **少走路、少排队、无障碍优先** 三种偏好，用图结构 + Dijkstra 算法计算路线，
前端展示路线步骤、SVG 地图高亮与预计时间。

## 运行

零第三方依赖（Python ≥ 3.8 标准库）：

```bash
python3 server.py        # 默认 8000 端口
PORT=9000 python3 server.py
```

浏览器打开 http://localhost:8000

## 测试

```bash
python3 test_route.py
```

## 架构

```
server.py          HTTP 服务（stdlib http.server），静态页 + JSON API
hospital_graph.py  图数据（14 节点 / 19 边）、Dijkstra、三种权重策略、步骤生成
static/index.html  前端单页：目的地卡片、偏好选择、SVG 地图、步骤时间线、时间汇总
test_route.py      核心逻辑测试
```

## API

| 接口 | 说明 |
|---|---|
| `GET /api/graph` | 节点、边、排队时间、可选起点/终点/偏好 |
| `GET /api/route?from=entrance&to=lab&pref=fastest` | 规划路线，返回步骤、路径节点、距离与时间 |

`pref` 取值：`shortest`（少走路，边权=距离）、`fastest`（少排队，边权=通行时间，
含拥挤系数与候梯 45s）、`accessible`（无障碍优先，仅走无障碍边后求最短，轮椅速度计时）。

## 时间模型

- 步行 1.25 m/s，轮椅 1.0 m/s，楼梯 0.6 m/s，扶梯 0.9 m/s
- 电梯：候梯 45s + 乘梯 12s
- 排队：挂号 12min / 检验 8min / 影像 20min / 药房 6min（计入全程预计）
