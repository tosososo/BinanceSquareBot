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
            TokenInfo(token_id="t1", outcome="YES", price=0.3),
            TokenInfo(token_id="t2", outcome="NO", price=0.7),
        ],
        volume=50000.0,
        created_at=1713500000,
    )
    assert market.condition_id == "0x123"
    assert market.yes_price == 0.3
    assert market.no_price == 0.7
    assert market.is_probability_extreme() is False  # 0.3 is not <0.2 or >0.8
    # 0.15 would be extreme → True


def test_is_probability_extreme_cases():
    """Test various cases for the is_probability_extreme method."""
    # YES price 0.15 is extreme (below 0.2 threshold)
    market = PolymarketMarket(
        condition_id="0x123",
        question="Test question",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.15),
            TokenInfo(token_id="t2", outcome="NO", price=0.85),
        ],
        created_at=1713500000,
    )
    assert market.is_probability_extreme() is True

    # YES price 0.85 is extreme (above 0.8 (1-0.2))
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

    # YES price 0.2 is NOT extreme (equal to threshold)
    market3 = PolymarketMarket(
        condition_id="0x125",
        question="Test question 3",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.2),
            TokenInfo(token_id="t2", outcome="NO", price=0.8),
        ],
        created_at=1713500000,
    )
    assert market3.is_probability_extreme() is False


def test_price_fallback_behavior():
    """Test fallback price selection when tokens don't have explicit YES/NO labels."""
    # No explicit YES/no labels - use first and second tokens
    market = PolymarketMarket(
        condition_id="0x123",
        question="Will X happen?",
        tokens=[
            TokenInfo(token_id="t1", outcome="Bull", price=0.4),
            TokenInfo(token_id="t2", outcome="Bear", price=0.6),
        ],
        created_at=1713500000,
    )
    assert market.yes_price == 0.4
    assert market.no_price == 0.6


def test_score_calculation():
    """Test score calculation with different age, volume and probability conditions."""
    # Recently created market with high volume should get high score
    from datetime import datetime
    current_ts = int(datetime.now().timestamp())

    market = PolymarketMarket(
        condition_id="0x123",
        question="Test scoring",
        tokens=[
            TokenInfo(token_id="t1", outcome="YES", price=0.15),  # Extreme
            TokenInfo(token_id="t2", outcome="NO", price=0.85),
        ],
        volume=100000.0,
        created_at=current_ts,  # Created just now
    )
    score = market.score()
    # new_score ~1.0 / (1 + 0) = 1.0, volume_score = 100000 * 0.0001 = 10, extreme_bonus=5 → total ~16
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
