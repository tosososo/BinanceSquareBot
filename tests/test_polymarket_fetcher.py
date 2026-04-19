from unittest.mock import Mock, patch
from binance_square_bot.services.polymarket_fetcher import PolymarketFetcher
from binance_square_bot.config import config


def test_fetch_all_simplified():
    fetcher = PolymarketFetcher(config.POLYMARKET_HOST, config.POLYMARKET_CHAIN_ID)

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

    with patch("binance_square_bot.services.polymarket_fetcher.ClobClient.get_simplified_markets") as mock_get:
        mock_get.return_value = mock_response
        markets = fetcher.fetch_all_simplified()
        assert len(markets) == 1
        assert markets[0].condition_id == "0x123"
        assert markets[0].question == "Test question"
