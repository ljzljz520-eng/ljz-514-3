# 医院陪诊 · 楼内导航

为陪诊场景设计的院内楼层导航：患者勾选 **挂号处 / 检验科 / 影像区 / 药房 / 出口**，
系统按 **少走路、少排队、无障碍** 三种偏好自动计算就诊顺序路线，
前端用 SVG 展示楼层地图、高亮路径与编号站点，并输出分步指引和预计时间。

## 运行（零依赖，仅需 Python 3）

```bash
cd hospital_nav
python3 server.py
# 打开 http://localhost:8000
```

## 目录结构

```
hospital_nav/
├── server.py        # 标准库 http.server：静态托管 + JSON API
├── graph.py         # 院内无向图：28 个节点 / 36 条边 + 房间区块
├── planner.py       # 图搜索：Dijkstra + 分阶段动态规划 + 步骤生成
└── static/
    ├── index.html   # 三栏页面：控制面板 / 地图 / 路线步骤
    ├── style.css
    └── app.js       # SVG 地图渲染、路径高亮、接口调用
```

## 建模说明

- **节点**：大厅、连廊、服务窗口（挂号 3、检验 3、影像 3、药房 2）、南门/北门。
  服务窗口带 `排队时长 / 办理时长 / 是否无障碍` 属性。
- **边**：通道，属性为 `距离 / 拥挤度(0-3) / 是否无障碍 / 类型(corridor|stairs|ramp)`。
  南门同时有近的「台阶」（轮椅不可用）和绕远的「无障碍坡道」。
- **就诊顺序**：挂号 → 检验 → 影像 → 药房 → 出口，类别内部用 Dijkstra 选最优窗口，
  阶段间用动态规划拼接全局最优。

### 三种偏好的代价函数（`planner.edge_cost` / `entry_cost`）

| 模式 | 通道代价 | 服务窗口代价 | 无障碍处理 |
|---|---|---|---|
| 少走路 walk | 距离(米) | — | 不限制 |
| 少排队 queue | 步行时间 + 拥挤度×0.6 分 | 实时排队 + 基础办理 | 不限制 |
| 无障碍 accessible | 距离 | 不可用窗口 +800 重罚 | 屏蔽台阶/高柜，必要时绕坡道 |

预计总时间三种模式口径统一：`步行 + 通道拥堵 + 排队 + 检查办理`，
方便横向对比；偏好只影响**选哪条路 / 哪个窗口**。

## API

- `GET /api/state` 节点、边、房间、类别、当前排队
- `POST /api/plan` `{start, categories[], mode}` → 站点、节点路径、边路径、分步指引、统计
- `POST /api/refresh` `{seed?}` 模拟实时叫号，排队时长在基础值 ±40% 波动

## 示例

```bash
curl -s -X POST http://localhost:8000/api/plan \
  -d '{"start":"south_gate",
       "categories":["registration","laboratory","imaging","pharmacy","exit"],
       "mode":"accessible"}'
```
