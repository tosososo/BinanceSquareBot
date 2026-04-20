from binance_square_bot.services.source.polymarket_source import PolymarketSource, PolymarketMarket

def test_market_model():
    """Test PolymarketMarket model validation."""
    market = PolymarketMarket(
        condition_id="0x123",
        question="Will BTC reach 100k?",
        yes_price=0.75,
        no_price=0.25,
        volume=100000.0
    )
    assert market.condition_id == "0x123"
    assert market.yes_price == 0.75

def test_polymarket_source_config():
    """Test PolymarketSource has correct config fields."""
    assert "host" in PolymarketSource.Config.model_fields
    assert "min_volume_threshold" in PolymarketSource.Config.model_fields
    assert "min_win_rate" in PolymarketSource.Config.model_fields
    assert "max_win_rate" in PolymarketSource.Config.model_fields
