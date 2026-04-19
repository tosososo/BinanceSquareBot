# Polymarket 投资研报自动生成推送功能 - 设计文档

## 概述

在现有 BinanceSquareBot 项目中新增功能：通过 `py_clob_client` 从 Polymarket 获取最新市场数据，筛选出热门新市场或概率偏离机会，使用 LLM 生成投资研报推文，并自动发布到币安广场。该功能与现有新闻爬虫每小时同步运行。

## 需求背景

- 用户需要跟踪 Polymarket 最新预测市场
- 自动发现热门新事件和概率偏离交易机会
- 生成专业研报并自动发布到币安广场
- 复用现有项目的基础设施（配置管理、发布、定时任务）

## 功能需求

### 输入

- Polymarket CLOB API 端点（默认为 `https://clob.polymarket.com`）
- Chain ID（Polymarket 在 Polygon，默认 137）

### 处理流程

1. **获取市场数据** - 调用 `get_simplified_markets()` 获取所有简化市场数据
2. **筛选** - 筛选出符合条件的市场：
   - **热门新市场**: 创建时间较近 + 交易量高
   - **概率偏离**: 当前概率明显偏离直觉/共识，存在交易机会
3 **排序打分** - 根据交易量和偏离程度打分，选出第一名
4. **获取详细数据** - 获取选中市场的当前概率、价格等详细信息
5. **LLM 生成研报** - 根据市场信息生成符合币安广场格式的研报推文
6. **去重检查** - 检查该市场是否已经发布过，避免重复
7. **发布** - 使用现有发布服务发布到币安广场
8. **存储记录** - 记录已发布市场，用于去重

### 输出

- 符合币安广场格式的投资研报推文
- 自动发布到配置的币安广场账号

### 筛选规则

| 筛选条件 | 说明 |
|---------|------|
| 新市场 | 优先选择最近创建的市场 |
| 高交易量 | 只考虑流动性足够的市场 |
| 概率偏离 | 概率 (YES 价格) < 0.2 或 > 0.8，寻找偏离机会 |

每次只选 **1 个** 最值得分析的市场生成研报。

## 非需求

- 不支持交易下单，只做分析分享
- 不保存完整历史市场数据，只保存已发布记录去重
- 不支持用户自定义筛选条件通过配置（如需可后续扩展）

## 架构设计

### 新增文件

```
src/binance_square_bot/
├── models/
│   └── polymarket_market.py       # Polymarket 市场数据模型
└── services/
    ├── polymarket_fetcher.py      # 市场数据获取服务
    ├── polymarket_filter.py       # 市场筛选服务
    └── research_generator.py      # 研报推文生成服务

tests/
├── test_polymarket_fetcher.py    # 获取服务单元测试
├── test_polymarket_filter.py     # 筛选服务单元测试
└── test_research_generator.py    # 生成服务单元测试
```

### 修改文件

- `src/binance_square_bot/cli.py` - 新增 `polymarket-research` 子命令
- `src/binance_square_bot/config.py` - 新增 Polymarket 配置项
- `.github/workflows/run-bot.yml` - 现有 workflow 新增 Polymarket 研报生成步骤

### 模块职责

| 模块 | 职责 |
|------|------|
| `polymarket_fetcher` | 调用 py_clob_client 获取市场列表、获取单个市场详情 |
| `polymarket_filter` | 根据规则筛选市场，打分排序，选出最佳市场 |
| `research_generator` | 构建 prompt，调用 LLM 生成研报推文，格式校验 |
| `polymarket_market` | 数据模型，定义市场结构 |

### 数据流

```
CLI 命令
  ↓
PolymarketFetcher.fetch_all_simplified()
  ↓
PolymarketFilter.select_best_market(markets)
  ↓
  有符合条件的市场？ → 否 → 退出，输出无
  ↓ 是
检查存储是否已发布 → 已发布 → 选下一个，重复
  ↓ 未发布
ResearchGenerator.generate_research(market)
  ↓
Publisher.publish()
  ↓
Storage.mark_as_published()
  ↓
完成
```

## 数据模型设计

### `PolymarketMarket`

```python
class PolymarketMarket:
    condition_id: str          # 市场条件 ID
    question: str              # 问题标题
    description: Optional[str] # 描述
    tokens: list[TokenInfo]   # 两个 outcome token (YES/NO)
    yes_price: float           # YES 当前价格 (0-1)，即概率
    no_price: float            # NO 当前价格
    volume: Optional[float]   # 交易量
    created_at: int            # 创建时间戳
```

## 配置设计

在 `config.py` 新增配置项：

```python
# Polymarket 设置
POLYMARKET_HOST: str = "https://clob.polymarket.com"
POLYMARKET_CHAIN_ID: int = 137
ENABLE_POLYMARKET: bool = True  # 是否启用该功能
MIN_VOLUME_THRESHOLD: float = 1000  # 最小交易量阈值
MAX_RETRIES: int = 3  # 生成失败重试次数
```

在 `.env` 中新增可选配置：

```
# Polymarket 配置（可选）
# ENABLE_POLYMARKET=true
# POLYMARKET_HOST=https://clob.polymarket.com
# POLYMARKET_CHAIN_ID=137
# MIN_VOLUME_THRESHOLD=1000
```

## LLM Prompt 设计

基于现有的新闻推文 prompt 调整：

```
你是一位资深的加密货币KOL，专注于预测市场（Polymarket）投资分析。你需要分析当前一个热门预测市场，生成适合币安广场用户的投资研报。

市场信息：
问题: {question}
当前 YES 概率: {yes_price:.1%}
当前 NO 概率: {no_price:.1%}
交易量: {volume}

写作要求：
- 专业但不晦涩，语言流畅自然
- 清晰描述事件是什么，当前市场概率反映了什么预期
- 分析概率是否存在偏离，是否存在交易机会
- 观点要有洞察力，让读者觉得有价值
- 结尾可以引导讨论
- 保持独立客观，不构成投资建议

严格遵守格式要求：
1. 推文总字符数必须大于 100 且小于 800。
2. 话题标签（#开头）最多允许 2 个。
3. 代币标签（$开头）最多允许 2 个。
4. 请直接输出推文内容，不要添加其他说明。
```

## 去重存储

复用现有的 `storage.py` SQLite 机制，新增表：

```sql
CREATE TABLE IF NOT EXISTS published_polymarket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id TEXT NOT NULL UNIQUE,
    question TEXT NOT NULL,
    published_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
```

## 错误处理

- API 获取失败 → 抛出异常，日志记录，本次运行跳过
- 筛选后没有符合条件的市场 → 正常退出，不报错
- LLM 生成格式失败 → 最多重试 3 次（和现有逻辑一致）
- 发布失败 → 重试 3 次，记录日志

## 命令行接口

新增子命令：

```bash
# 生成并发布研报
binance-square-bot polymarket-research run

# 试运行（只获取筛选，不发布）
binance-square-bot polymarket-research run --dry-run

# 查看当前筛选出的最佳市场，不生成不发布
binance-square-bot polymarket-research scan
```

## GitHub Actions 集成

在现有的 `run-bot.yml` 中新增步骤，在新闻发布之后运行 Polymarket 研报生成。

## 技术栈确认

| 技术 | 使用 | 理由 |
|------|------|------|
| Python | 是 | 项目现有技术栈 |
| py_clob_client | 是 | Polymarket 官方 Python 客户端 |
| LangGraph | 复用现有 generator | 遵循现有 AI 工作流 |
| SQLite | 复用现有存储 | 去重存储 |
| Typer | 复用现有 CLI | 新增子命令 |

所有技术都符合 AGENTS.md 锁定的技术栈，无新增技术栈变更。

## 测试计划

- 为每个新增模块编写单元测试
- 接口使用 mock 避免真实调用依赖
- 格式校验逻辑测试
- 筛选逻辑测试

## 风险与考虑

- Polymarket API 限流 → 通过重试机制应对
- 返回市场数量大 → 使用简化接口 `get_simplified_markets` 数据量小
- LLM 生成偏离内容 → prompt 约束 + 格式校验控制

## 变更影响

- 现有新闻功能不受影响
- 数据库新增表，不影响现有表
- GitHub Actions 新增步骤，原有步骤保留

---

**设计完成**，等待用户评审。
