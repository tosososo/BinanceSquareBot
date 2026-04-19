"""
@file test_polymarket_filter.py
@description Tests for PolymarketFilter service
@created-by fullstack-dev-workflow
"""

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
