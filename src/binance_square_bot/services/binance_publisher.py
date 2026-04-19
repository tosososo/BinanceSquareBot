"""
@file binance_publisher.py
@description Binance Publisher that publishes to all configured API keys
"""
import httpx
from typing import List, Tuple

from ..models.tweet import Tweet
from ..config import config


class BinancePublisher:
    """Publishes tweet to all configured Binance API keys."""

    API_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"

    def __init__(self) -> None:
        self.client = httpx.Client(timeout=30.0)

    def publish_tweet(self, tweet: Tweet) -> List[Tuple[bool, str]]:
        """Publish tweet to all configured API keys.

        Returns:
            List of (success, error_message) for each API key.
        """
        results: List[Tuple[bool, str]] = []

        for api_key in config.binance_api_keys:
            headers = {
                "X-Square-OpenAPI-Key": api_key,
                "Content-Type": "application/json",
                "clienttype": "binanceSkill",
            }

            body = {
                "bodyTextOnly": tweet.content,
            }

            try:
                response = self.client.post(
                    self.API_URL,
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()

                code = data.get("code")
                message = data.get("message", "")

                # 000000 or 0 means success
                if code == "000000" or code == 0:
                    results.append((True, ""))
                else:
                    results.append((False, message or f"API error code: {code}"))

            except httpx.HTTPError as e:
                results.append((False, f"HTTP error: {str(e)}"))
            except Exception as e:
                results.append((False, f"Unexpected error: {str(e)}"))

        return results
