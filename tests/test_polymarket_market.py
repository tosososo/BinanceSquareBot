from binance_square_bot.models.polymarket_market import PolymarketMarket, TokenInfo


def test_token_info_creation():
    """Test that TokenInfo model creates correctly with all fields."""
    token = TokenInfo(
        token_id="test-id",
        outcome="YES",
        price=0.65
    )
    assert token.token_id == "test-id"
    assert token.outcome == "YES"
    assert token.price == 0.65


def test_polymarket_market_creation():
    """Test that PolymarketMarket creates correctly and basic properties work."""
    market = PolymarketMarket(
        condition_id="0x123",
        question="Will BTC hit 100k by end of 2025?",
        description="Price prediction question",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.75),
            TokenInfo(token_id="t2", outcome="NO", price=0.25),
        ],
        volume=50000.0,
        created_at=1713500000,
    )
    assert market.condition_id == "0x123"
    assert market.yes_price == 0.75
    assert market.no_price == 0.25
    assert market.is_probability_extreme() is True  # 0.75 is between 0.6 and 0.9


def test_is_probability_extreme_cases():
    """Test various cases for the is_probability_extreme method."""
    # YES price 0.75 - interesting (between 0.6 and 0.9)
    market = PolymarketMarket(
        condition_id="0x123",
        question="Test question",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.75),
            TokenInfo(token_id="t2", outcome="NO", price=0.25),
        ],
        created_at=1713500000,
    )
    assert market.is_probability_extreme() is True

    # YES price 0.85 - interesting (between 0.6 and 0.9)
    market2 = PolymarketMarket(
        condition_id="0x124",
        question="Test question 2",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.85),
            TokenInfo(token_id="t2", outcome="NO", price=0.15),
        ],
        created_at=1713500000,
    )
    assert market2.is_probability_extreme() is True

    # YES price 0.60 - not interesting (lower bound exclusive)
    market3 = PolymarketMarket(
        condition_id="0x125",
        question="Test question 3",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.60),
            TokenInfo(token_id="t2", outcome="NO", price=0.40),
        ],
        created_at=1713500000,
    )
    assert market3.is_probability_extreme() is False

    # YES price 0.90 - not interesting (upper bound exclusive)
    market4 = PolymarketMarket(
        condition_id="0x126",
        question="Test question 4",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.90),
            TokenInfo(token_id="t2", outcome="NO", price=0.10),
        ],
        created_at=1713500000,
    )
    assert market4.is_probability_extreme() is False

    # YES price 0.50 - not interesting (below lower bound)
    market5 = PolymarketMarket(
        condition_id="0x127",
        question="Test question 5",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.50),
            TokenInfo(token_id="t2", outcome="NO", price=0.50),
        ],
        created_at=1713500000,
    )
    assert market5.is_probability_extreme() is False

    # YES price 0.95 - not interesting (above upper bound)
    market6 = PolymarketMarket(
        condition_id="0x128",
        question="Test question 6",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.95),
            TokenInfo(token_id="t2", outcome="NO", price=0.05),
        ],
        created_at=1713500000,
    )
    assert market6.is_probability_extreme() is False


def test_price_fallback_behavior():
    """Test fallback price selection when tokens don't have explicit YES/NO labels."""
    # No explicit YES/no labels - use first and second tokens
    market = PolymarketMarket(
        condition_id="0x123",
        question="Will X happen?",
        tokens=[
            TokenInfo(token_id="t1", outcome="Bull", price=0.75),
            TokenInfo(token_id="t2", outcome="Bear", price=0.25),
        ],
        created_at=1713500000,
    )
    assert market.yes_price == 0.75
    assert market.no_price == 0.25


def test_score_calculation():
    """Test score calculation with different age, volume and probability conditions."""
    # Recently created market with high volume should get high score
    from datetime import datetime
    current_ts = int(datetime.now().timestamp())

    market = PolymarketMarket(
        condition_id="0x123",
        question="Test scoring",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.75),  # Interesting gets bonus
            TokenInfo(token_id="t2", outcome="NO", price=0.25),
        ],
        volume=100000.0,
        created_at=current_ts,  # Created just now
    )
    score = market.score()
    # new_score ~1.0 / (1 + 0) = 1.0, volume_score = 100000 * 0.0001 = 10, bonus=5 → total ~16
    assert score > 15  # Should be around 16

    # Old market with low volume should get low score
    market2 = PolymarketMarket(
        condition_id="0x124",
        question="Old question",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.5),
            TokenInfo(token_id="t2", outcome="NO", price=0.5),
        ],
        volume=100.0,
        created_at=current_ts - (7 * 24 * 3600),  # 1 week ago
    )
    score2 = market2.score()
    assert score2 < 1  # Should be significantly lower
