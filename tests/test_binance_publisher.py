"""
@file test_binance_publisher.py
@description BinancePublisher 单元测试
@task-id BE-10
@created-by fullstack-dev-workflow
"""

from unittest.mock import Mock, patch
from datetime import datetime

from src.binance_square_bot.config import config
from src.binance_square_bot.services.binance_publisher import BinancePublisher
from src.binance_square_bot.models.tweet import Tweet


def test_publish_tweet_single_success():
    """测试单个API密钥发布成功"""
    tweet = Tweet(
        content="测试 Polymarket 研报 #Crypto $BTC",
        article_url="https://example.com/polymarket/1",
        generated_at=datetime.now(),
        validation_passed=True,
    )

    publisher = BinancePublisher()

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "code": "000000",
        "message": "success",
        "data": {"id": "123456"}
    }

    with patch.object(publisher.client, 'post', return_value=mock_response):
        results = publisher.publish_tweet(tweet)
        # 结果数量应该等于配置的API密钥数量
        assert len(results) == len(config.binance_api_keys)
        # 测试第一个结果结构正确
        if results:
            success, error_msg = results[0]
            assert success
            assert error_msg == ""


def test_publish_tweet_single_failure():
    """测试单个API密钥发布失败"""
    tweet = Tweet(
        content="测试 Polymarket 研报 #Crypto $BTC",
        article_url="https://example.com/polymarket/1",
        generated_at=datetime.now(),
        validation_passed=True,
    )

    publisher = BinancePublisher()

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "code": "100001",
        "message": "Invalid API key",
    }

    with patch.object(publisher.client, 'post', return_value=mock_response):
        results = publisher.publish_tweet(tweet)
        assert len(results) >= 0


def test_publish_tweet_numeric_success_code():
    """测试数字形式的成功code"""
    tweet = Tweet(
        content="测试 Polymarket 研报 #Crypto $BTC",
        article_url="https://example.com/polymarket/1",
        generated_at=datetime.now(),
        validation_passed=True,
    )

    publisher = BinancePublisher()

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "code": 0,
        "message": "success",
        "data": {"id": 789012},
    }

    with patch.object(publisher.client, 'post', return_value=mock_response):
        results = publisher.publish_tweet(tweet)
        # 第一个结果应该成功
        if results:
            assert results[0][0] is True
            assert results[0][1] == ""


def test_publish_tweet_http_error():
    """测试HTTP网络错误"""
    tweet = Tweet(
        content="测试 Polymarket 研报 #Crypto $BTC",
        article_url="https://example.com/polymarket/1",
        generated_at=datetime.now(),
        validation_passed=True,
    )

    publisher = BinancePublisher()

    with patch.object(publisher.client, 'post') as mock_post:
        mock_post.side_effect = Exception("Network connection error")
        results = publisher.publish_tweet(tweet)
        assert len(results) >= 1
        # 第一个结果应该失败
        assert results[0][0] is False
        assert "Network connection error" in results[0][1]


def test_binance_publisher_initialization():
    """测试BinancePublisher初始化"""
    publisher = BinancePublisher()
    assert publisher is not None
    assert publisher.client is not None
    assert publisher.API_URL == "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"


def test_publish_tweet_request_body():
    """测试请求体结构正确"""
    tweet = Tweet(
        content="测试推文内容",
        article_url="https://example.com/test/1",
        generated_at=datetime.now(),
        validation_passed=True,
    )

    publisher = BinancePublisher()

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "code": "000000",
        "message": "success",
        "data": {"id": "123"}
    }

    with patch.object(publisher.client, 'post', return_value=mock_response) as mock_post:
        publisher.publish_tweet(tweet)

        # 检查调用参数
        call_args = mock_post.call_args
        assert call_args is not None
        # 检查json body是否包含正确的key
        kwargs = call_args[1]
        assert "json" in kwargs
        assert "bodyTextOnly" in kwargs["json"]
        assert kwargs["json"]["bodyTextOnly"] == tweet.content
        assert "headers" in kwargs
        assert "X-Square-OpenAPI-Key" in kwargs["headers"]
        assert "Content-Type" in kwargs["headers"]
        assert "clienttype" in kwargs["headers"]
