import pytest
from unittest.mock import Mock, patch
from binance_square_bot.services.polymarket_fetcher import PolymarketFetcher, PolyException
from binance_square_bot.config import config


def test_fetch_all_simplified():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)

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


def test_fetch_all_simplified_api_error():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)
    with patch("binance_square_bot.services.polymarket_fetcher.ClobClient.get_simplified_markets") as mock_get:
        mock_get.side_effect = PolyException("API Error")
        with pytest.raises(PolyException):
            fetcher.fetch_all_simplified()


def test_parse_simplified_item_invalid_data():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)
    invalid_item = {"invalid_key": "value"}
    result = fetcher._parse_simplified_item(invalid_item)
    assert result is None


def test_parse_simplified_item_missing_condition_id():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)
    item = {"question": "Test question"}
    result = fetcher._parse_simplified_item(item)
    assert result is None


def test_parse_simplified_item_missing_question():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)
    item = {"condition_id": "0x123"}
    result = fetcher._parse_simplified_item(item)
    assert result is None


def test_fetch_market_detail_success():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)
    mock_detail = {
        "condition_id": "0x123",
        "question": "Test",
        "tokens": [{"token_id": "t1", "outcome": "YES"}],
    }
    with patch("binance_square_bot.services.polymarket_fetcher.ClobClient.get_market") as mock_get:
        mock_get.return_value = mock_detail
        result = fetcher.fetch_market_detail("0x123")
        assert result is not None
        assert result.condition_id == "0x123"
        assert result.question == "Test"
        assert len(result.tokens) == 1


def test_fetch_market_detail_empty_response():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)
    with patch("binance_square_bot.services.polymarket_fetcher.ClobClient.get_market") as mock_get:
        mock_get.return_value = None
        result = fetcher.fetch_market_detail("0x123")
        assert result is None


def test_fetch_market_detail_api_error():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)
    with patch("binance_square_bot.services.polymarket_fetcher.ClobClient.get_market") as mock_get:
        mock_get.side_effect = PolyException("API Error")
        result = fetcher.fetch_market_detail("0x123")
        assert result is None


def test_fetch_all_simplified_pagination():
    fetcher = PolymarketFetcher(config.polymarket_host, config.polymarket_chain_id)

    mock_response1 = {
        "data": [
            {
                "condition_id": "0x1",
                "question": "First question",
                "tokens": [{"token_id": "t1", "outcome": "YES"}],
            }
        ],
        "next_cursor": "cursor_2",
    }

    mock_response2 = {
        "data": [
            {
                "condition_id": "0x2",
                "question": "Second question",
                "tokens": [{"token_id": "t2", "outcome": "NO"}],
            }
        ],
        "next_cursor": "",
    }

    with patch("binance_square_bot.services.polymarket_fetcher.ClobClient.get_simplified_markets") as mock_get:
        mock_get.side_effect = [mock_response1, mock_response2]
        markets = fetcher.fetch_all_simplified()
        assert len(markets) == 2
        assert markets[0].condition_id == "0x1"
        assert markets[1].condition_id == "0x2"
