import logging
from typing import List, Optional

# Handle import for testing - py_clob_client may not be installed in proxy environments
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.exceptions import PolyException
except ImportError:
    # Create dummy classes for when the module isn't installed
    # This allows tests to run with mocking
    class ClobClient:
        def __init__(self, host: str, chain_id: int) -> None:
            pass
        def get_simplified_markets(self, next_cursor: str = "") -> dict:
            return {}
        def get_market(self, condition_id: str) -> dict:
            return {}

    class PolyException(Exception):
        pass

from binance_square_bot.models.polymarket_market import PolymarketMarket, TokenInfo
from binance_square_bot.config import config

logger = logging.getLogger(__name__)


class PolymarketFetcher:
    """Fetches market data from Polymarket CLOB."""

    def __init__(self, host: str = None, chain_id: int = None):
        self.host = host or config.POLYMARKET_HOST
        self.chain_id = chain_id or config.POLYMARKET_CHAIN_ID
        self.client = ClobClient(self.host, self.chain_id)

    def fetch_all_simplified(self) -> List[PolymarketMarket]:
        """Fetch all simplified markets, handle pagination."""
        all_markets: List[PolymarketMarket] = []
        next_cursor = ""

        try:
            while True:
                response = self.client.get_simplified_markets(next_cursor=next_cursor)

                if not response or "data" not in response:
                    break

                data = response["data"]
                for item in data:
                    market = self._parse_simplified_item(item)
                    if market:
                        all_markets.append(market)

                next_cursor = response.get("next_cursor", "")
                if not next_cursor or next_cursor == "":
                    break

            logger.info(f"Fetched {len(all_markets)} markets from Polymarket")
            return all_markets

        except PolyException as e:
            logger.error(f"Polymarket API error: {e}")
            raise

    def fetch_market_detail(self, condition_id: str) -> Optional[PolymarketMarket]:
        """Fetch detailed information for a specific market."""
        try:
            detail = self.client.get_market(condition_id)
            if not detail:
                return None
            return self._parse_simplified_item(detail)
        except PolyException as e:
            logger.error(f"Failed to fetch market detail for {condition_id}: {e}")
            return None

    def _parse_simplified_item(self, item: dict) -> Optional[PolymarketMarket]:
        """Parse raw API response into PolymarketMarket."""
        try:
            condition_id = item.get("condition_id", "")
            question = item.get("question", "")

            if not condition_id or not question:
                return None

            tokens = []
            raw_tokens = item.get("tokens", [])
            for rt in raw_tokens:
                token = TokenInfo(
                    token_id=rt.get("token_id", ""),
                    outcome=rt.get("outcome", ""),
                    price=float(rt.get("price", 0.0)) if "price" in rt else None,
                )
                tokens.append(token)

            # Parse volume
            volume = 0.0
            if "volume" in item:
                try:
                    volume = float(item["volume"])
                except (ValueError, TypeError):
                    pass

            # Parse created_at
            created_at = item.get("created_at", 0)
            if isinstance(created_at, str):
                try:
                    created_at = int(created_at)
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
