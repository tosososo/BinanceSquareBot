import pytest
from unittest.mock import Mock, patch
import httpx
from binance_square_bot.services.polymarket_fetcher import PolymarketFetcher


def test_fetch_all_simplified():
    fetcher = PolymarketFetcher()

    mock_response = [
        {
            "conditionId": "0x123",
            "question": "Test question",
            "outcomePrices": "[0.6, 0.4]",
            "volume24hr": 10000,
            "createdAt": "2024-04-18T00:00:00Z",
        }
    ]

    with patch("binance_square_bot.services.polymarket_fetcher.httpx.Client.get") as mock_get:
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        markets = fetcher.fetch_all_simplified(max_pages=1, limit=100)
        assert len(markets) == 1
        assert markets[0].condition_id == "0x123"
        assert markets[0].question == "Test question"
        assert abs(markets[0].yes_price - 0.6) < 0.001
        assert abs(markets[0].no_price - 0.4) < 0.001


def test_fetch_all_simplified_api_error():
    fetcher = PolymarketFetcher()
    with patch("binance_square_bot.services.polymarket_fetcher.httpx.Client.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("API Error")
        with pytest.raises(httpx.HTTPError):
            fetcher.fetch_all_simplified()


def test_parse_simplified_item_invalid_data():
    fetcher = PolymarketFetcher()
    invalid_item = {"invalid_key": "value"}
    result = fetcher._parse_simplified_item(invalid_item)
    assert result is None


def test_parse_simplified_item_missing_condition_id():
    fetcher = PolymarketFetcher()
    item = {"question": "Test question"}
    result = fetcher._parse_simplified_item(item)
    assert result is None


def test_parse_simplified_item_missing_question():
    fetcher = PolymarketFetcher()
    item = {"conditionId": "0x123"}
    result = fetcher._parse_simplified_item(item)
    assert result is None


def test_fetch_market_detail_success():
    fetcher = PolymarketFetcher()
    mock_response = [
        {
            "conditionId": "0x123",
            "question": "Test",
            "outcomePrices": "[0.7, 0.3]",
        }
    ]
    with patch("binance_square_bot.services.polymarket_fetcher.httpx.Client.get") as mock_get:
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = fetcher.fetch_market_detail("0x123")
        assert result is not None
        assert result.condition_id == "0x123"
        assert result.question == "Test"
        assert len(result.tokens) == 2


def test_fetch_market_detail_empty_response():
    fetcher = PolymarketFetcher()
    with patch("binance_square_bot.services.polymarket_fetcher.httpx.Client.get") as mock_get:
        mock_resp = Mock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = fetcher.fetch_market_detail("0x123")
        assert result is None


def test_fetch_market_detail_api_error():
    fetcher = PolymarketFetcher()
    with patch("binance_square_bot.services.polymarket_fetcher.httpx.Client.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("API Error")
        result = fetcher.fetch_market_detail("0x123")
        assert result is None


def test_fetch_all_simplified_pagination():
    fetcher = PolymarketFetcher()

    mock_response1 = [
        {
            "conditionId": "0x1",
            "question": "First question",
            "outcomePrices": "[0.5, 0.5]",
        }
    ]
    mock_response2 = [
        {
            "conditionId": "0x2",
            "question": "Second question",
            "outcomePrices": "[0.3, 0.7]",
        }
    ]

    with patch("binance_square_bot.services.polymarket_fetcher.httpx.Client.get") as mock_get:
        mock_get.side_effect = [
            (lambda: Mock(
                json=lambda: mock_response1,
                raise_for_status=lambda: None
            ))(),
            (lambda: Mock(
                json=lambda: mock_response2,
                raise_for_status=lambda: None
            ))(),
        ]
        markets = fetcher.fetch_all_simplified(max_pages=2, limit=1)
        assert len(markets) == 2
        assert markets[0].condition_id == "0x1"
        assert markets[1].condition_id == "0x2"
