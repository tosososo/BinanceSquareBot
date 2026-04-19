import logging
from typing import Any

import httpx

from binance_square_bot.models.polymarket_market import PolymarketMarket, TokenInfo

from loguru import logger


class PolymarketFetcher:
    """Fetches market data from Polymarket Gamma API."""

    GAMMA_API_HOST = "https://gamma-api.polymarket.com"

    def __init__(self) -> None:
        self.client = httpx.Client(timeout=30.0)

    def fetch_all_simplified(self, max_pages: int = 10, limit: int = 100) -> list[PolymarketMarket]:
        """Fetch all available markets from Polymarket Gamma API.

        Uses the official Gamma API to fetch markets sorted by 24h volume descending,
        which gives us the most active/hottest markets first.

        Args:
            max_pages: Maximum number of pages to fetch (default: 10).
            limit: Number of markets per page (default: 100).

        Returns:
            List[PolymarketMarket]: List of successfully parsed market objects.
        """
        all_markets: list[PolymarketMarket] = []
        offset = 0

        try:
            for page in range(max_pages):
                params = {
                    "limit": limit,
                    "offset": offset,
                    "order": "volume24hr",
                    "ascending": False,
                    "closed": False,  # Only fetch active markets
                }

                url = f"{self.GAMMA_API_HOST}/markets"
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data or len(data) == 0:
                    break

                for item in data:
                    market = self._parse_simplified_item(item)
                    if market:
                        all_markets.append(market)

                offset += len(data)
                logger.info(f"Fetched {len(data)} markets from Polymarket page {page+1}/{max_pages}")

                if len(data) < limit:
                    # No more pages
                    break

            logger.info(f"Fetched {len(all_markets)} active markets from Polymarket Gamma API")
            return all_markets

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch markets from Polymarket API: {e}")
            raise

    def fetch_market_detail(self, condition_id: str) -> PolymarketMarket | None:
        """Fetch detailed information for a specific market by condition ID.

        Retrieves full details for a single market including token information.
        Returns None if the market cannot be found or parsing fails.

        Args:
            condition_id: The unique condition ID of the market (hex string).

        Returns:
            Optional[PolymarketMarket]: Parsed market object if successful,
                None if the API returns empty data, parsing fails, or API error occurs.
        """
        try:
            params = {
                "condition_ids": [condition_id]
            }
            url = f"{self.GAMMA_API_HOST}/markets"
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data or len(data) == 0:
                return None

            return self._parse_simplified_item(data[0])
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch market detail for condition_id={condition_id}: {e}")
            return None

    def _parse_simplified_item(self, item: dict[str, Any]) -> PolymarketMarket | None:
        """Parse raw API response into PolymarketMarket from Gamma API."""
        try:
            # Gamma API uses camelCase instead of snake_case
            condition_id = item.get("conditionId", "")
            question = item.get("question", "")

            if not condition_id or not question:
                return None

            # Parse outcome prices (YES/NO)
            # outcomePrices is a string-encoded JSON array
            tokens = []
            yes_price: float | None = None
            no_price: float | None = None

            outcome_prices_str = item.get("outcomePrices", "")
            if outcome_prices_str:
                try:
                    import json
                    prices = json.loads(outcome_prices_str)
                    if len(prices) >= 2:
                        # First outcome is usually YES, second is NO
                        yes_price = float(prices[0])
                        no_price = float(prices[1])
                        tokens.append(TokenInfo(token_id="", outcome="Yes", price=yes_price))
                        tokens.append(TokenInfo(token_id="", outcome="No", price=no_price))
                except (json.JSONDecodeError, ValueError):
                    pass

            # Parse volume - use 24h volume if available, fall back to total
            volume = 0.0
            volume24h = item.get("volume24hr")
            if volume24h is not None:
                try:
                    volume = float(volume24h)
                except (ValueError, TypeError):
                    pass
            else:
                volume_str = item.get("volume", "0")
                try:
                    volume = float(volume_str)
                except (ValueError, TypeError):
                    pass

            # Parse created_at - convert ISO date string to unix timestamp
            created_at = 0
            created_at_str = item.get("createdAt", "")
            if created_at_str:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    created_at = int(dt.timestamp())
                except ValueError:
                    created_at = 0

            return PolymarketMarket(
                condition_id=condition_id,
                question=question,
                description=item.get("description"),
                tokens=tokens,
                volume=volume,
                created_at=created_at,
            )

        except Exception as e:
            logger.warning(f"Failed to parse market item: {e}, item={item}")
            return None
