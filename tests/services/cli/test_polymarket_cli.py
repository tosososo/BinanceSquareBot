from binance_square_bot.services.cli.polymarket_cli import PolymarketCliService

def test_polymarket_cli_service_init():
    """Test PolymarketCliService can be initialized."""
    service = PolymarketCliService(dry_run=True)
    assert service.dry_run is True
