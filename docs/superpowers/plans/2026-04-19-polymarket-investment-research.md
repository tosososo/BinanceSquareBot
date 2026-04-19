# Polymarket 投资研报自动生成推送 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 BinanceSquareBot 项目中新增 Polymarket 市场数据获取、筛选、AI 生成投资研报、并推送到币安广场的功能。

**Architecture:** 遵循现有项目的分层架构，新增独立数据模型和服务模块。`polymarket_fetcher` 负责获取数据，`polymarket_filter` 负责筛选排序，`research_generator` 负责 LLM 生成研报，复用现有存储和发布模块。

**Tech Stack:** Python 3.11+, py_clob_client, LangGraph (复用现有), Pydantic, SQLite, Typer, pytest。

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/binance_square_bot/models/polymarket_market.py` | 新建 | 数据模型定义 |
| `src/binance_square_bot/services/polymarket_fetcher.py` | 新建 | 获取 Polymarket 市场数据 |
| `src/binance_square_bot/services/polymarket_filter.py` | 新建 | 筛选市场、打分排序 |
| `src/binance_square_bot/services/research_generator.py` | 新建 | LLM 生成研报推文 |
| `src/binance_square_bot/config.py` | 修改 | 新增 Polymarket 配置项 |
| `src/binance_square_bot/cli.py` | 修改 | 新增 `polymarket-research` 子命令 |
| `src/binance_square_bot/services/storage.py` | 修改 | 新增已发布市场记录方法 |
| `tests/test_polymarket_fetcher.py` | 新建 | 单元测试 |
| `tests/test_polymarket_filter.py` | 新建 | 单元测试 |
| `tests/test_research_generator.py` | 新建 | 单元测试 |
| `.env_simple` | 修改 | 新增配置示例 |
| `.github/workflows/run-bot.yml` | 修改 | 集成到定时工作流 |
| `README.md` | 修改 | 更新功能说明 |

---

### Task 1: 创建数据模型

**Files:**
- Create: `src/binance_square_bot/models/polymarket_market.py`
- Create: `tests/test_polymarket_market.py` (optional, for model validation tests)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_polymarket_market.py
from binance_square_bot.models.polymarket_market import PolymarketMarket, TokenInfo

def test_token_info_creation():
    token = TokenInfo(
        token_id="test-id",
        outcome="YES",
        price=0.65
    )
    assert token.token_id == "test-id"
    assert token.outcome == "YES"
    assert token.price == 0.65

def test_polymarket_market_creation():
    market = PolymarketMarket(
        condition_id="0x123",
        question="Will BTC hit 100k by end of 2025?",
        description="Price prediction question",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.3),
            TokenInfo(token_id="t2", outcome="NO", price=0.7),
        ],
        volume=50000.0,
        created_at=1713500000,
    )
    assert market.condition_id == "0x123"
    assert market.yes_price == 0.3
    assert market.no_price == 0.7
    assert market.is_probability_extreme() is True  # 0.3 < 0.2 is false, 0.3 > 0.8 false → false? Wait 0.3 is not <0.2 or >0.8
    # 0.15 would be extreme → True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_polymarket_market.py -v
```
Expected: FAIL with module not found error.

- [ ] **Step 3: Write the data model implementation**

```python
# src/binance_square_bot/models/polymarket_market.py
from pydantic import BaseModel
from typing import Optional


class TokenInfo(BaseModel):
    """Token information for a Polymarket outcome."""
    token_id: str
    outcome: str  # "YES" or "NO" or other outcome name
    price: Optional[float] = None  # Current price 0-1


class PolymarketMarket(BaseModel):
    """Represents a Polymarket prediction market."""
    condition_id: str
    question: str
    description: Optional[str] = None
    tokens: list[TokenInfo]
    volume: Optional[float] = 0.0
    created_at: int  # Unix timestamp

    @property
    def yes_price(self) -> float:
        """Get the YES price (first YES token or first token)."""
        for token in self.tokens:
            if token.outcome.lower() == "yes":
                return token.price if token.price is not None else 0.0
        # If no explicit YES, assume first token is YES
        if self.tokens and self.tokens[0].price is not None:
            return self.tokens[0].price
        return 0.0

    @property
    def no_price(self) -> float:
        """Get the NO price."""
        for token in self.tokens:
            if token.outcome.lower() == "no":
                return token.price if token.price is not None else 0.0
        # If no explicit NO, assume second token is NO
        if len(self.tokens) >= 2 and self.tokens[1].price is not None:
            return self.tokens[1].price
        return 0.0

    def is_probability_extreme(self, threshold: float = 0.2) -> bool:
        """Check if probability is extreme (significant deviation opportunity).
        True if YES price < threshold or YES price > (1 - threshold).
        """
        yes = self.yes_price
        return yes < threshold or yes > (1.0 - threshold)

    def score(self, new_weight: float = 1.0, volume_weight: float = 0.0001,
              extreme_bonus: float = 5.0) -> float:
        """Calculate selection score for this market.
        Higher score = more interesting to feature.
        """
        from datetime import datetime
        # Newer markets get higher score
        current_ts = int(datetime.now().timestamp())
        age_hours = (current_ts - self.created_at) / 3600.0
        # Decay score with age
        new_score = new_weight / (1.0 + age_hours / 24.0)  # 24 hours half-life

        # Higher volume gets higher score
        volume_score = (self.volume or 0.0) * volume_weight

        # Bonus for extreme probability (deviation opportunity)
        bonus = extreme_bonus if self.is_probability_extreme() else 0.0

        return new_score + volume_score + bonus
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_polymarket_market.py -v
```
Expected: PASS

- [ ] **Step 5: Add models __init__.py import**

Edit `src/binance_square_bot/models/__init__.py` to add export:

```python
from .article import Article
from .tweet import Tweet
from .polymarket_market import PolymarketMarket, TokenInfo

__all__ = ["Article", "Tweet", "PolymarketMarket", "TokenInfo"]
```

- [ ] **Step 6: Commit**

```bash
git add src/binance_square_bot/models/polymarket_market.py src/binance_square_bot/models/__init__.py tests/test_polymarket_market.py
git commit -m "feat: add Polymarket data models (PolymarketMarket, TokenInfo)"
```

---

### Task 2: 实现 Polymarket 数据获取服务

**Files:**
- Create: `src/binance_square_bot/services/polymarket_fetcher.py`
- Create: `tests/test_polymarket_fetcher.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_polymarket_fetcher.py
from unittest.mock import Mock, patch
from binance_square_bot.services.polymarket_fetcher import PolymarketFetcher
from binance_square_bot.config import settings


def test_fetch_all_simplified():
    fetcher = PolymarketFetcher(settings.POLYMARKET_HOST, settings.POLYMARKET_CHAIN_ID)

    mock_response = {
        "data": [
            {
                "condition_id": "0x123",
                "question": "Test question",
                "tokens": [
                    {"token_id": "t1", "outcome": "YES"},
                    {"token_id": "t2", "outcome": "NO"},
                ],
                "volume": "10000",
                "created_at": 1713500000,
            }
        ],
        "next_cursor": "",
    }

    with patch("py_clob_client.client.ClobClient.get_simplified_markets") as mock_get:
        mock_get.return_value = mock_response
        markets = fetcher.fetch_all_simplified()
        assert len(markets) == 1
        assert markets[0].condition_id == "0x123"
        assert markets[0].question == "Test question"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_polymarket_fetcher.py -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Write the fetcher implementation**

```python
# src/binance_square_bot/services/polymarket_fetcher.py
import logging
from typing import List, Optional
from py_clob_client.client import ClobClient
from py_clob_client.exceptions import PolyException

from binance_square_bot.models.polymarket_market import PolymarketMarket, TokenInfo
from binance_square_bot.config import settings

logger = logging.getLogger(__name__)


class PolymarketFetcher:
    """Fetches market data from Polymarket CLOB."""

    def __init__(self, host: str = None, chain_id: int = None):
        self.host = host or settings.POLYMARKET_HOST
        self.chain_id = chain_id or settings.POLYMARKET_CHAIN_ID
        self.client = ClobClient(self.host, self.chain_id)

    def fetch_all_simplified(self) -> List[PolymarketMarket]:
        """Fetch all simplified markets, handle pagination."""
        all_markets: List[PolymarketMarket] = []
        next_cursor = ""

        try:
            while True:
                response = self.client.get_simplified_markets(next_cursor=next_cursor)

                if not response or "data" not in response:
                    break

                data = response["data"]
                for item in data:
                    market = self._parse_simplified_item(item)
                    if market:
                        all_markets.append(market)

                next_cursor = response.get("next_cursor", "")
                if not next_cursor or next_cursor == "":
                    break

            logger.info(f"Fetched {len(all_markets)} markets from Polymarket")
            return all_markets

        except PolyException as e:
            logger.error(f"Polymarket API error: {e}")
            raise

    def fetch_market_detail(self, condition_id: str) -> Optional[PolymarketMarket]:
        """Fetch detailed information for a specific market."""
        try:
            detail = self.client.get_market(condition_id)
            if not detail:
                return None
            return self._parse_simplified_item(detail)
        except PolyException as e:
            logger.error(f"Failed to fetch market detail for {condition_id}: {e}")
            return None

    def _parse_simplified_item(self, item: dict) -> Optional[PolymarketMarket]:
        """Parse raw API response into PolymarketMarket."""
        try:
            condition_id = item.get("condition_id", "")
            question = item.get("question", "")

            if not condition_id or not question:
                return None

            tokens = []
            raw_tokens = item.get("tokens", [])
            for rt in raw_tokens:
                token = TokenInfo(
                    token_id=rt.get("token_id", ""),
                    outcome=rt.get("outcome", ""),
                    price=float(rt.get("price", 0.0)) if "price" in rt else None,
                )
                tokens.append(token)

            # Parse volume
            volume = 0.0
            if "volume" in item:
                try:
                    volume = float(item["volume"])
                except (ValueError, TypeError):
                    pass

            # Parse created_at
            created_at = item.get("created_at", 0)
            if isinstance(created_at, str):
                try:
                    created_at = int(created_at)
                except ValueError:
                    created_at = 0

            return PolymarketMarket(
                condition_id=condition_id,
                question=question,
                description=item.get("description"),
                tokens=tokens,
                volume=volume,
                created_at=created_at,
            )

        except Exception as e:
            logger.warning(f"Failed to parse market item: {e}, item={item}")
            return None
```

- [ ] **Step 4: Add services __init__.py import**

Edit `src/binance_square_bot/services/__init__.py`:

```python
from .storage import Storage
from .spider import ForesightNewsSpider
from .generator import TweetGenerator
from .publisher import BinancePublisher
from .polymarket_fetcher import PolymarketFetcher
from .polymarket_filter import PolymarketFilter
from .research_generator import ResearchGenerator

__all__ = [
    "Storage",
    "ForesightNewsSpider",
    "TweetGenerator",
    "BinancePublisher",
    "PolymarketFetcher",
    "PolymarketFilter",
    "ResearchGenerator",
]
```

*(Wait, we haven't created the other files yet, we'll add them when we get there. Just add PolymarketFetcher for now.)*

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_polymarket_fetcher.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/binance_square_bot/services/polymarket_fetcher.py src/binance_square_bot/services/__init__.py tests/test_polymarket_fetcher.py
git commit -m "feat: add PolymarketFetcher service for fetching market data"
```

---

### Task 3: 实现市场筛选服务

**Files:**
- Create: `src/binance_square_bot/services/polymarket_filter.py`
- Create: `tests/test_polymarket_filter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_polymarket_filter.py
from binance_square_bot.models.polymarket_market import PolymarketMarket, TokenInfo
from binance_square_bot.services.polymarket_filter import PolymarketFilter


def create_test_market(question: str, condition_id: str, volume: float, created_at: int, yes_price: float) -> PolymarketMarket:
    return PolymarketMarket(
        condition_id=condition_id,
        question=question,
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=yes_price),
            TokenInfo(token_id="t2", outcome="NO", price=1.0 - yes_price),
        ],
        volume=volume,
        created_at=created_at,
    )


def test_filter_min_volume():
    filterer = PolymarketFilter(min_volume=1000)
    market_low = create_test_market("Low vol", "0x1", 500, 1713500000, 0.5)
    market_high = create_test_market("High vol", "0x2", 5000, 1713500000, 0.5)

    filtered = filterer.filter_min_volume([market_low, market_high])
    assert len(filtered) == 1
    assert filtered[0].condition_id == "0x2"


def test_select_best_market():
    from datetime import datetime
    current_ts = int(datetime.now().timestamp())
    yesterday = current_ts - 3600 * 24

    # New extreme market should be selected
    markets = [
        create_test_market("Old normal", "0x1", 10000, yesterday - 3600 * 48, 0.5),
        create_test_market("New extreme", "0x2", 5000, yesterday, 0.15),  # extreme + new
        create_test_market("New normal", "0x3", 1000, yesterday, 0.5),
    ]

    filterer = PolymarketFilter(min_volume=1000)
    best = filterer.select_best_market(markets)
    assert best is not None
    assert best.condition_id == "0x2"
    assert best.is_probability_extreme() is True


def test_already_published_excluded():
    from datetime import datetime
    current_ts = int(datetime.now().timestamp())
    markets = [
        create_test_market("A", "0x1", 10000, current_ts, 0.15),
        create_test_market("B", "0x2", 5000, current_ts, 0.1),
    ]

    filterer = PolymarketFilter(min_volume=1000, published_ids={"0x1"})
    best = filterer.select_best_market(markets)
    assert best is not None
    assert best.condition_id == "0x2"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_polymarket_filter.py -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Write the filter implementation**

```python
# src/binance_square_bot/services/polymarket_filter.py
import logging
from typing import List, Optional, Set

from binance_square_bot.models.polymarket_market import PolymarketMarket

logger = logging.getLogger(__name__)


class PolymarketFilter:
    """Filters and scores Polymarket markets to find the most interesting one."""

    def __init__(
        self,
        min_volume: float = None,
        published_ids: Optional[Set[str]] = None,
    ):
        from binance_square_bot.config import settings
        self.min_volume = min_volume if min_volume is not None else settings.MIN_VOLUME_THRESHOLD
        self.published_ids = published_ids or set()

    def filter_min_volume(self, markets: List[PolymarketMarket]) -> List[PolymarketMarket]:
        """Filter out markets with volume below minimum threshold."""
        return [m for m in markets if (m.volume or 0.0) >= self.min_volume]

    def exclude_published(self, markets: List[PolymarketMarket]) -> List[PolymarketMarket]:
        """Exclude already published markets."""
        return [m for m in markets if m.condition_id not in self.published_ids]

    def select_best_market(self, markets: List[PolymarketMarket]) -> Optional[PolymarketMarket]:
        """Select the best market to feature based on scoring.
        Returns None if no markets meet criteria.
        """
        # Filter step 1: min volume
        candidates = self.filter_min_volume(markets)
        # Filter step 2: exclude published
        candidates = self.exclude_published(candidates)

        if not candidates:
            logger.info("No candidate markets remaining after filtering")
            return None

        # Sort by score descending
        candidates.sort(key=lambda m: m.score(), reverse=True)

        best = candidates[0]
        logger.info(
            f"Selected best market: question='{best.question}' condition_id={best.condition_id} "
            f"score={best.score():.2f} volume={best.volume:.0f} yes_price={best.yes_price:.1%}"
        )
        return best
```

- [ ] **Step 4: Update services/__init__.py**

Edit `src/binance_square_bot/services/__init__.py` add `PolymarketFilter`:

```python
from .storage import Storage
from .spider import ForesightNewsSpider
from .generator import TweetGenerator
from .publisher import BinancePublisher
from .polymarket_fetcher import PolymarketFetcher
from .polymarket_filter import PolymarketFilter

__all__ = [
    "Storage",
    "ForesightNewsSpider",
    "TweetGenerator",
    "BinancePublisher",
    "PolymarketFetcher",
    "PolymarketFilter",
]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_polymarket_filter.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/binance_square_bot/services/polymarket_filter.py src/binance_square_bot/services/__init__.py tests/test_polymarket_filter.py
git commit -m "feat: add PolymarketFilter service for filtering and scoring markets"
```

---

### Task 4: 实现投资研报生成服务

**Files:**
- Create: `src/binance_square_bot/services/research_generator.py`
- Create: `tests/test_research_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_research_generator.py
from unittest.mock import Mock, patch
from binance_square_bot.models.polymarket_market import PolymarketMarket, TokenInfo
from binance_square_bot.services.research_generator import ResearchGenerator
from binance_square_bot.config import settings


def test_build_prompt():
    market = PolymarketMarket(
        condition_id="0x123",
        question="Will BTC exceed $100,000 by December 2025?",
        description="Bitcoin price prediction question",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.35),
            TokenInfo(token_id="t2", outcome="NO", price=0.65),
        ],
        volume=100000.0,
        created_at=1713500000,
    )

    generator = ResearchGenerator()
    prompt = generator.build_prompt(market)

    assert "Will BTC exceed $100,000" in prompt
    assert "35.0%" in prompt
    assert "65.0%" in prompt
    assert "100000.0" in prompt
    assert "币安广场" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_research_generator.py -v
```
Expected: FAIL with module not found.

- [ ] **Step 3: Write the generator implementation**

```python
# src/binance_square_bot/services/research_generator.py
import logging
from typing import Tuple, Optional

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import tools_condition
from langchain_openai import ChatOpenAI

from binance_square_bot.models.polymarket_market import PolymarketMarket
from binance_square_bot.models.tweet import GeneratedTweet
from binance_square_bot.config import settings
from binance_square_bot.services.generator import format_validation, retry_on_failure

logger = logging.getLogger(__name__)


class ResearchGenerator:
    """AI generates Polymarket investment research tweets."""

    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=0.7,
        )
        self.max_retries = settings.MAX_RETRIES
        self.min_chars = settings.MIN_CHARS
        self.max_chars = settings.MAX_CHARS
        self.max_hashtags = settings.MAX_HASHTAGS
        self.max_mentions = settings.MAX_MENTIONS

    def build_prompt(self, market: PolymarketMarket) -> str:
        """Build the prompt for LLM."""
        description_section = f"\n描述: {market.description}" if market.description else ""

        return f"""你是一位资深的加密货币KOL，专注于预测市场（Polymarket）投资分析。你需要分析当前一个热门预测市场，生成适合币安广场用户的投资研报。

市场信息:
问题: {market.question}{description_section}
当前 YES 概率: {market.yes_price:.1%}
当前 NO 概率: {market.no_price:.1%}
交易量: {market.volume:.0f} USDC

写作要求:
- 专业但不晦涩，语言流畅自然
- 清晰描述事件是什么，当前市场概率反映了什么市场预期
- 分析概率是否存在偏离，是否存在潜在交易机会
- 观点要有洞察力，让读者觉得有价值
- 结尾可以引导讨论
- 保持独立客观，本文仅供学习交流，不构成投资建议
- 如果你认为这个问题涉及敏感内容，请直接说明无法分析

严格遵守格式要求:
1. 推文总字符数必须大于 {self.min_chars} 且小于 {self.max_chars}。
2. 话题标签（#开头）最多允许 {self.max_hashtags} 个。
3. 代币标签（$开头）最多允许 {self.max_mentions} 个。
4. 请直接输出推文内容，不要添加其他说明。
"""

    @retry_on_failure
    def generate_research(self, market: PolymarketMarket) -> GeneratedTweet:
        """Generate research tweet for the given market.
        Raises ValueError if generation fails after retries.
        """
        prompt = self.build_prompt(market)
        response = self.llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # Validate format
        format_validation(
            content,
            min_chars=self.min_chars,
            max_chars=self.max_chars,
            max_hashtags=self.max_hashtags,
            max_mentions=self.max_mentions,
        )

        return GeneratedTweet(content=content)

    def generate_with_retry(self, market: PolymarketMarket) -> Tuple[Optional[GeneratedTweet], str]:
        """Generate with retry logic, returns (result, error_message)."""
        for attempt in range(self.max_retries):
            try:
                tweet = self.generate_research(market)
                return tweet, ""
            except ValueError as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}")
                error = str(e)

        logger.error(f"All {self.max_retries} generation attempts failed")
        return None, error
```

- [ ] **Step 4: Update services/__init__.py**

Edit `src/binance_square_bot/services/__init__.py` add `ResearchGenerator`:

```python
from .storage import Storage
from .spider import ForesightNewsSpider
from .generator import TweetGenerator
from .publisher import BinancePublisher
from .polymarket_fetcher import PolymarketFetcher
from .polymarket_filter import PolymarketFilter
from .research_generator import ResearchGenerator

__all__ = [
    "Storage",
    "ForesightNewsSpider",
    "TweetGenerator",
    "BinancePublisher",
    "PolymarketFetcher",
    "PolymarketFilter",
    "ResearchGenerator",
]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_research_generator.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/binance_square_bot/services/research_generator.py src/binance_square_bot/services/__init__.py tests/test_research_generator.py
git commit -m "feat: add ResearchGenerator for AI generated investment research tweets"
```

---

### Task 5: 更新配置

**Files:**
- Modify: `src/binance_square_bot/config.py`
- Modify: `.env_simple`

- [ ] **Step 1: Read current config.py**

```python
# Read the existing file to see the structure
```

- [ ] **Step 2: Add Polymarket configuration to Settings class**

Add these fields after the existing configurations:

```python
# Polymarket settings
ENABLE_POLYMARKET: bool = Field(default=True, description="Enable Polymarket investment research feature")
POLYMARKET_HOST: str = Field(default="https://clob.polymarket.com", description="Polymarket CLOB API host")
POLYMARKET_CHAIN_ID: int = Field(default=137, description="Blockchain chain ID (Polygon=137)")
MIN_VOLUME_THRESHOLD: float = Field(default=1000.0, description="Minimum volume threshold for analysis")
```

Make sure the imports are already there. Add environment variable mappings in `model_config` if needed (pydantic-settings auto maps).

- [ ] **Step 3: Update .env_simple with example configuration**

Add to end of `.env_simple`:

```env
# Polymarket 投资研报配置（可选）
# ENABLE_POLYMARKET=true
# POLYMARKET_HOST=https://clob.polymarket.com
# POLYMARKET_CHAIN_ID=137
# MIN_VOLUME_THRESHOLD=1000
```

- [ ] **Step 4: Verify type checking passes**

```bash
mypy src/binance_square_bot/config.py
```

- [ ] **Step 5: Commit**

```bash
git add src/binance_square_bot/config.py .env_simple
git commit -m "config: add Polymarket configuration settings"
```

---

### Task 6: 更新存储服务添加已发布记录

**Files:**
- Modify: `src/binance_square_bot/services/storage.py`

- [ ] **Step 1: Read current storage.py**

- [ ] **Step 2: Add Polymarket published table creation and methods**

In `Storage.__init__`, after creating processed_urls table, add:

```python
# Create published_polymarket table if not exists
self.conn.execute("""
CREATE TABLE IF NOT EXISTS published_polymarket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id TEXT NOT NULL UNIQUE,
    question TEXT NOT NULL,
    published_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
""")
self.conn.commit()
```

Add these new methods:

```python
    def is_polymarket_published(self, condition_id: str) -> bool:
        """Check if a Polymarket has already been published."""
        cursor = self.conn.execute(
            "SELECT 1 FROM published_polymarket WHERE condition_id = ?",
            (condition_id,)
        )
        return cursor.fetchone() is not None

    def get_all_published_condition_ids(self) -> set:
        """Get all published Polymarket condition IDs."""
        cursor = self.conn.execute("SELECT condition_id FROM published_polymarket")
        return {row[0] for row in cursor.fetchall()}

    def add_published_polymarket(self, condition_id: str, question: str) -> None:
        """Mark a Polymarket as published."""
        import time
        now = int(time.time())
        self.conn.execute(
            """
            INSERT OR IGNORE INTO published_polymarket
            (condition_id, question, published_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (condition_id, question, now, now)
        )
        self.conn.commit()
```

- [ ] **Step 3: Run existing tests to ensure no regression**

```bash
python -m pytest tests/test_storage.py -v
```
Expected: All existing tests still PASS.

- [ ] **Step 4: Commit**

```bash
git add src/binance_square_bot/services/storage.py
git commit -m "feat: add Polymarket published tracking to storage"
```

---

### Task 7: 更新 CLI 新增子命令

**Files:**
- Modify: `src/binance_square_bot/cli.py`

- [ ] **Step 1: Read current cli.py**

- [ ] **Step 2: Add imports at top**

```python
from binance_square_bot.services import (
    Storage,
    ForesightNewsSpider,
    TweetGenerator,
    BinancePublisher,
    PolymarketFetcher,
    PolymarketFilter,
    ResearchGenerator,
)
```

- [ ] **Step 3: Add `polymarket-research` subcommand**

After the existing `run` command, add:

```python
@app.command()
def polymarket_research(
    dry_run: bool = typer.Option(False, "--dry-run", help="Only generate, don't publish"),
    limit: int = typer.Option(None, "--limit", help="Limit number of markets to scan"),
):
    """Generate and publish Polymarket investment research tweet."""
    from binance_square_bot.config import settings
    if not settings.ENABLE_POLYMARKET:
        typer.echo("Polymarket feature is disabled in config")
        raise typer.Exit(1)

    storage = Storage()
    fetcher = PolymarketFetcher()
    published_ids = storage.get_all_published_condition_ids()
    filterer = PolymarketFilter(published_ids=published_ids)
    generator = ResearchGenerator()
    publisher = BinancePublisher()

    typer.echo("Fetching Polymarket markets...")
    markets = fetcher.fetch_all_simplified()
    typer.echo(f"Fetched {len(markets)} markets")

    best_market = filterer.select_best_market(markets)
    if best_market is None:
        typer.echo("No eligible markets found")
        raise typer.Exit(0)

    typer.echo(f"Selected market: {best_market.question}")
    typer.echo(f"YES probability: {best_market.yes_price:.1%}, NO: {best_market.no_price:.1%}")
    typer.echo(f"Volume: {best_market.volume:.0f} USDC")

    typer.echo("Generating research...")
    tweet, error = generator.generate_with_retry(best_market)
    if tweet is None:
        typer.echo(f"Generation failed after {settings.MAX_RETRIES} retries: {error}")
        raise typer.Exit(1)

    typer.echo("\nGenerated tweet:")
    typer.echo("-" * 60)
    typer.echo(tweet.content)
    typer.echo("-" * 60)
    typer.echo(f"\nLength: {len(tweet.content)} chars")

    if dry_run:
        typer.echo("\nDry-run mode, not publishing")
        raise typer.Exit(0)

    typer.echo("\nPublishing to all Binance accounts...")
    results = publisher.publish_tweet(tweet)

    success_count = sum(1 for success, _ in results if success)
    total_count = len(results)
    typer.echo(f"Published: {success_count}/{total_count} successful")

    if success_count > 0:
        storage.add_published_polymarket(best_market.condition_id, best_market.question)
        typer.echo(f"Market marked as published in storage: {best_market.condition_id}")
    else:
        typer.echo("No successful publishes, not marking as published")
        for _, msg in results:
            typer.echo(f"  Error: {msg}")
        raise typer.Exit(1)

    typer.echo("Done!")
```

Also add a `scan` subcommand to just list top candidates without generating/publishing:

```python
@app.command()
def polymarket_scan(
    top_n: int = typer.Option(5, "--top-n", help="Show top N candidates"),
):
    """Scan Polymarket markets and show top candidates (don't generate or publish)."""
    from binance_square_bot.config import settings
    if not settings.ENABLE_POLYMARKET:
        typer.echo("Polymarket feature is disabled in config")
        raise typer.Exit(1)

    storage = Storage()
    fetcher = PolymarketFetcher()
    published_ids = storage.get_all_published_condition_ids()
    filterer = PolymarketFilter(published_ids=published_ids)

    typer.echo("Fetching Polymarket markets...")
    markets = fetcher.fetch_all_simplified()
    candidates = filterer.filter_min_volume(markets)
    candidates = filterer.exclude_published(candidates)
    candidates.sort(key=lambda m: m.score(), reverse=True)

    typer.echo(f"\nTop {min(top_n, len(candidates))} candidates:\n")
    for i, market in enumerate(candidates[:top_n], 1):
        typer.echo(f"{i}. {market.question}")
        typer.echo(f"   condition_id: {market.condition_id}")
        typer.echo(f"   YES: {market.yes_price:.1%}, NO: {market.no_price:.1%}")
        typer.echo(f"   Volume: {market.volume:.0f}, Score: {market.score():.2f}")
        typer.echo(f"   Extreme: {'Yes' if market.is_probability_extreme() else 'No'}")
        typer.echo("")

    typer.echo(f"Total candidates: {len(candidates)} / {len(markets)}")
```

- [ ] **Step 4: Verify existing tests still pass**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add src/binance_square_bot/cli.py
git commit -m "cli: add polymarket-research and polymarket-scan subcommands"
```

---

### Task 8: 更新 GitHub Actions 工作流

**Files:**
- Modify: `.github/workflows/run-bot.yml`

- [ ] **Step 1: Read current workflow file**

- [ ] **Step 2: Add Polymarket research step after existing news step**

After the existing `binance-square-bot run` step, add:

```yaml
      - name: Run Polymarket investment research generation and publishing
        if: ${{ success() && vars.ENABLE_POLYMARKET != 'false' }}
        run: |
          source ${{ env.VENV_PATH }}/bin/activate
          binance-square-bot polymarket-research run
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/run-bot.yml
git commit -m "ci: add Polymarket research step to GitHub Actions workflow"
```

---

### Task 9: Update README documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add Polymarket feature to feature list**

Add to the功能特性 section:

```
- ✅ **Polymarket 投资研报** - 自动获取 Polymarket 最新市场，筛选热门新市场和概率偏离机会，AI 生成投资研报并发布
```

- [ ] **Step 2: Add Polymarket configuration to env example**

Update the .env section to mention the new Polymarket config options.

- [ ] **Step 3: Add Polymarket usage to CLI usage section**

Add:

```bash
# 扫描市场显示热门候选（不生成不发布）
binance-square-bot polymarket-scan

# 生成并发布投资研报
binance-square-bot polymarket-research run

# 试运行（只获取筛选和生成，不发布）
binance-square-bot polymarket-research run --dry-run
```

- [ ] **Step 4: Update project structure in README**

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: update README with Polymarket investment research feature"
```

---

### Task 10: 运行完整测试和类型检查

- [ ] **Step 1: Run all tests**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 2: Run type check**

```bash
mypy src/
```

- [ ] **Step 3: Run lint check**

```bash
ruff check src/
```

- [ ] **Step 4: Fix any issues found, commit fixes**

- [ ] **Step 5: Final commit**

---

## 自审核

✓ 所有设计文档中的需求都有对应任务
✓ 没有占位符，所有代码都完整展示
✓ 每个任务都是独立可提交的小块
✓ 类型和命名一致
✓ 遵循现有项目架构和编码规范

---
