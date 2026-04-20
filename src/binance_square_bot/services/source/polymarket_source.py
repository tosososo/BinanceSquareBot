from typing import List, Optional
from pydantic import BaseModel
import httpx
from loguru import logger

from binance_square_bot.services.base import BaseSource


class PolymarketMarket(BaseModel):
    """Polymarket market model."""
    condition_id: str
    question: str
    yes_price: float
    no_price: float
    volume: float
    image: Optional[str] = None
    description: Optional[str] = None


class PolymarketSource(BaseSource):
    """Polymarket data source - fetches markets and generates research."""

    Model = PolymarketMarket

    class Config(BaseSource.Config):
        host: str = "https://clob.polymarket.com"
        min_volume_threshold: float = 1000.0
        min_win_rate: float = 0.6
        max_win_rate: float = 0.95
        daily_max_executions: int = 10

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def fetch(self) -> List[PolymarketMarket]:
        """Fetch all markets from Polymarket."""
        url = f"{self.Config.model_fields['host'].default}/markets"

        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            markets: List[PolymarketMarket] = []

            # Handle different response formats - could be list or dict with data key
            if isinstance(data, list):
                market_list = data
            elif isinstance(data, dict) and "data" in data:
                market_list = data["data"]
            else:
                market_list = []

            for item in market_list:
                try:
                    # Get outcome prices
                    outcomes = item.get("outcomes", [])
                    outcome_prices = item.get("outcomePrices", [])

                    yes_price = 0.0
                    no_price = 0.0

                    for i, outcome in enumerate(outcomes):
                        if outcome.lower() == "yes" and i < len(outcome_prices):
                            yes_price = float(outcome_prices[i])
                        elif outcome.lower() == "no" and i < len(outcome_prices):
                            no_price = float(outcome_prices[i])

                    market = PolymarketMarket(
                        condition_id=item.get("conditionId", ""),
                        question=item.get("question", ""),
                        yes_price=yes_price,
                        no_price=no_price,
                        volume=float(item.get("volume", 0)),
                        image=item.get("image"),
                        description=item.get("description"),
                    )
                    markets.append(market)
                except Exception as e:
                    logger.warning(f"Failed to parse market: {e}")
                    continue

            logger.info(f"Fetched {len(markets)} markets from Polymarket")
            return markets

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    def generate(self, markets: List[PolymarketMarket]) -> List[str]:
        """Generate research tweets from high-confidence markets."""
        # Filter for high volume and extreme probability
        candidate_markets = [
            m for m in markets
            if m.volume >= self.Config.model_fields['min_volume_threshold'].default
            and (
                m.yes_price >= self.Config.model_fields['min_win_rate'].default
                or m.no_price >= self.Config.model_fields['min_win_rate'].default
            )
            and (
                m.yes_price <= self.Config.model_fields['max_win_rate'].default
                or m.no_price <= self.Config.model_fields['max_win_rate'].default
            )
        ]

        # Sort by volume
        candidate_markets.sort(key=lambda m: m.volume, reverse=True)

        tweets = []
        for market in candidate_markets[:5]:  # Top 5 by volume
            direction = "YES" if market.yes_price > market.no_price else "NO"
            probability = max(market.yes_price, market.no_price)

            content = (
                f"📊 Polymarket Research Alert\n\n"
                f"{market.question}\n\n"
                f"🎯 Direction: {direction} ({probability:.1%})\n"
                f"💰 Volume: ${market.volume:,.0f}\n\n"
                f"#Polymarket #PredictionMarket"
            )

            if len(content) > 280:
                content = content[:277] + "..."

            tweets.append(content)

        logger.info(f"Generated {len(tweets)} research tweets from markets")
        return tweets
