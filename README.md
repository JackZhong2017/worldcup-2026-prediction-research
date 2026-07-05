# World Cup 2026 Prediction Research

[![GitHub stars](https://img.shields.io/github/stars/JackZhong2017/worldcup-2026-prediction-research?style=flat-square)](https://github.com/JackZhong2017/worldcup-2026-prediction-research/stargazers)
[![License](https://img.shields.io/github/license/JackZhong2017/worldcup-2026-prediction-research?style=flat-square)](./LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square)](https://nextjs.org/)
[![NestJS](https://img.shields.io/badge/NestJS-11-E0234E?style=flat-square)](https://nestjs.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square)](https://www.postgresql.org/)

> 🇬🇧 **English: [README.en.md](README.en.md)** | 🇪🇸 **Español: [README.es.md](README.es.md)**

一个基于**对数意见池融合 + 时间序列外样本验证**的足球预测市场校准研究平台。聚焦 2026 世界杯，将每场比赛视为一次观测，对比 Polymarket 市场隐含概率与 StatsBomb xG 统计模型，科学评估融合模型是否具备预测能力。

**不做投注建议，不做策略优化，不做仓位建议。** 这是一个纯粹的研究工具——宁愿诚实地报告模型被拒绝，也不做不科学的预测。

---

## 30 秒开始

```bash
git clone https://github.com/JackZhong2017/worldcup-2026-prediction-research.git
cd worldcup-2026-prediction-research
cp .env.example .env
# 编辑 .env，填入你的 football-data.org API Token
docker compose up -d postgres redis
pnpm install
pnpm db:generate
pnpm dev
```

API 启动后验证：

```bash
curl 'http://localhost:3001/api/v1/providers/polymarket/events?limit=5'
```

---

## 它能回答什么问题

不是"谁会赢"，而是在回答更根本的问题：**预测市场真的有效吗？统计模型能提供增量信息吗？**

**市场质量研究**
- Polymarket 比分市场的隐含概率有多准确？
- 市场是否系统性地高估或低估某些结果？
- "other score" 尾部概率是否被合理定价？

**统计模型验证**
- 基于 xG 的独立泊松模型能否击败市场？
- 对数意见池融合是否优于单一信息源？
- 按时间序列严格外样本评估，避免前视偏差

**可复现研究**
- 每个实验都记录数据集快照、代码版本、参数、随机种子
- 88 场 2026 世界杯赛事的历史 CLOB 重建数据
- 所有中间产物（快照、报告、评估）全部可审计

---

## 工作原理

```
Provider 适配器 → 标准化领域对象 → PostgreSQL 不可变存储 → API 确定指标 → Python 统计实验 → 报告消费
                                                    ↑                           ↑
                                              Polymarket 快照              StatsBomb xG 数据
```

### 三个核心模块

| 模块 | 技术栈 | 职责 |
|---|---|---|
| **API** (`apps/api`) | NestJS 11 | 数据采集、标准化、预测融合、指标计算 |
| **Dashboard** (`apps/web`) | Next.js 15 | 研究仪表盘：比赛探索、校准曲线、市场质量 |
| **Worker** (`apps/worker`) | Python 3.11 | 统计计算：回测、参数优化、融合实验、CLOB 重建 |

### 模型验证门控

API 有两个输出状态。默认输出 `RESEARCH_OUTPUT_NOT_VALIDATED`。只有通过以下全部 5 项阈值，才会输出 `MODEL_PREDICTION`：

- 至少 200 场已完成比赛的外样本
- 多分类 Brier Score ≤ 0.85（bootstrap 95% 上界）
- 确切比分对数损失 ≤ 3.20（bootstrap 95% 上界）
- 期望校准误差 ≤ 0.05
- 融合模型对数损失比纯市场至少降低 0.01（配对 bootstrap）

> 所有阈值基于 bootstrap 的 **95% 置信区间上界**，不是点估计。训练/验证/测试窗口严格按时间切分，永不重叠。

### 融合方法论

1. **市场分布**：保存 Polymarket 所有确切比分价格，将 "other score" 尾部按独立统计模型比例展开到完整 0–10 得分网格
2. **统计分布**：从开球前的滚动 xG（进攻、防守、联赛均值、主场优势）构建独立泊松率
3. **对数意见池融合**：加权几何平均合并两个分布，权重在外样本评估前冻结
4. **校准**：使用 Top-Label ECE——每场只取最可能的确切比分，不将 121 个单元格展平

---

## 仓库结构

```
├── apps/
│   ├── api/         # NestJS 后端 API（端口 3001）
│   ├── web/         # Next.js 研究仪表盘
│   └── worker/      # Python 统计 Worker（11 个 CLI 入口）
├── packages/
│   ├── domain/      # 跨平台领域类型定义
│   └── database/    # Prisma ORM Schema 与迁移
├── data/
│   ├── processed/   # StatsBomb 国际赛事 xG 数据（262 场）
│   ├── snapshots/   # Polymarket 市场快照
│   ├── reports/     # 融合比分报告与统计基线
│   ├── backfill/    # 88 场 WC 2026 CLOB 历史重建
│   ├── manifests/   # 活跃样本清单
│   └── evaluations/ # 已结算观测
├── docs/            # 架构、路线图、模型验证文档
├── docker-compose.yml
└── pnpm-workspace.yaml
```

---

## 安装与运行

### 前置条件

- Node.js 22+、pnpm 10+
- Python 3.11+
- Docker（PostgreSQL 16 + Redis 7）

### 完整安装

```bash
# 1. 克隆仓库
git clone https://github.com/JackZhong2017/worldcup-2026-prediction-research.git
cd worldcup-2026-prediction-research

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 FOOTBALL_DATA_API_TOKEN（在 football-data.org 免费注册获取）

# 3. 启动服务
docker compose up -d postgres redis

# 4. 安装依赖
pnpm install
pnpm db:generate

# 5. 启动开发环境
pnpm dev
```

### Python Worker 安装

```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

---

## 使用示例

### 探索市场数据

```bash
# 列出 Polymarket 体育赛事
curl 'http://localhost:3001/api/v1/providers/polymarket/events?limit=5'

# 查询足球赛程（需要 Token）
curl 'http://localhost:3001/api/v1/providers/football-data/matches?dateFrom=2026-07-04&dateTo=2026-07-05'

# 获取单个市场的订单簿
curl 'http://localhost:3001/api/v1/providers/polymarket/orderbook/TOKEN_ID'
```

### 跨平台赛事匹配

跨平台身份（football-data match ↔ Polymarket event）**必须人工确认**后才能入库：

```bash
curl -X POST 'http://localhost:3001/api/v1/imports/preview' \
  -H 'content-type: application/json' \
  -d '{"footballDataMatchId": 537376, "polymarketEventId": "650891"}'
```

### 运行统计实验

```bash
cd apps/worker
source .venv/bin/activate

sprp-collect-statsbomb       # 采集 262 场国际赛事 xG 数据
sprp-backtest                # 时间序列 80/20 统计基线回测
sprp-optimize                # 60/20/20 参数网格搜索
sprp-collect-polymarket 650891  # 获取单场 Polymarket 比分快照
sprp-fuse-current            # 市场/统计/融合完整比分网格
sprp-settle 537376           # 赛后评估（幂等操作）
sprp-batch                   # 批量发现、配对、快照、融合
sprp-settle-batch            # 批量结算已完成赛事
sprp-backfill                # 历史 CLOB 价格重建（88 场 WC 2026）
sprp-recent-experiment       # 因果 tournament-form 融合实验
```

### 运行预测分析

```bash
curl -X POST 'http://localhost:3001/api/v1/analysis/predict' \
  -H 'content-type: application/json' \
  -d '{
    "matchId": "537376",
    "homeAttack": 1.2, "homeDefense": 0.8,
    "awayAttack": 0.9, "awayDefense": 1.1,
    "homeAdvantage": 0.3,
    "marketDistribution": [...]
  }'
```

---

## 当前实验结果

| 指标 | 纯市场 | 独立统计模型 |
|---|---|---|
| **对数损失** | 2.443 ✅ | 2.665 ❌ |
| **可用赛事** | 88 场 WC 2026 | 262 场国际赛事 |
| **验证结论** | 基线 | 未通过——选定 0% 统计权重 |

> **目前无任何模型被准入。** 统计模型未能展示对市场的增量价值，仍处于被拒绝的研究候选状态。需要等待后续预定队列反转该结果，且外样本总数达到 200 场。

详见 [docs/model-validation.md](docs/model-validation.md)。

---

## 架构原则

1. **仅追加、不可变**：市场快照不可修改，结果修正可审计
2. **跨平台身份隔离**：赛事匹配强制人工审核
3. **指标溯源**：每个指标记录输入快照、实现版本、参数、时间戳
4. **时间序列切分**：杜绝前视偏差，训练/验证/测试永不重叠
5. **Bootstrap 推断**：校准误差和损失用 bootstrap 置信区间而非点估计
6. **一次测试**：最终外样本窗口只评估一次，防止多重比较

详见 [docs/architecture.md](docs/architecture.md)。

---

## 路线图

- **M0 基础** ✅ — Monorepo、本地服务、领域契约、数据库 Schema、指标原语
- **M1 单样本链路** ✅ — 采集、快照、融合、结算、报告
- **M2 历史评估** ✅ — 批量流水线、CLOB 重建、参数优化
- **M3 研究工作台** 🚧 — 自定义分组、回归/贝叶斯实验、图表导出、模式审查

明确不做：多供应商覆盖（先做好一个）、实时交易、投注建议。

详见 [docs/roadmap.md](docs/roadmap.md)。

---

## 重要说明

- 本项目**不做预测建议**，所有输出在通过模型验证门控前均标记为 `RESEARCH_OUTPUT_NOT_VALIDATED`
- StatsBomb 开源数据在发布或分享研究时需注明归属
- football-data.org API 免费层有速率限制（每分钟 10 次），批量操作已内建延迟
- 所有实验数据均为研究用途，不构成投资或交易建议
- 统计模型目前**未被准入**，任何融合权重在通过外样本验证前不得部署

---

## License

MIT © 2026 JackZhong2017 — 可自由使用、修改、商用，需保留版权声明。
