"""
@file polymarket_market.py
@description Polymarket数据模型，表示Polymarket预测市场
@created-by fullstack-dev-workflow
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class TokenInfo(BaseModel):
    """Token information for a Polymarket outcome."""
    token_id: str
    outcome: str  # "YES" or "NO" or other outcome name
    price: Optional[float] = None  # Current price 0-1


class PolymarketMarket(BaseModel):
    """Represents a Polymarket prediction market."""
    condition_id: str
    question: str
    description: Optional[str] = None
    tokens: List[TokenInfo]
    volume: Optional[float] = 0.0
    created_at: int  # Unix timestamp

    @property
    def yes_price(self) -> float:
        """Get the YES price (first YES token or first token)."""
        for token in self.tokens:
            if token.outcome.lower() == "yes":
                return token.price if token.price is not None else 0.0
        # If no explicit YES, assume first token is YES
        if self.tokens and self.tokens[0].price is not None:
            return self.tokens[0].price
        return 0.0

    @property
    def no_price(self) -> float:
        """Get the NO price."""
        for token in self.tokens:
            if token.outcome.lower() == "no":
                return token.price if token.price is not None else 0.0
        # If no explicit NO, assume second token is NO
        if len(self.tokens) >= 2 and self.tokens[1].price is not None:
            return self.tokens[1].price
        return 0.0

    def is_probability_extreme(self, threshold: float = 0.2) -> bool:
        """Check if probability is extreme (significant deviation opportunity).
        True if YES price < threshold or YES price > (1 - threshold).
        """
        yes = self.yes_price
        return yes < threshold or yes > (1.0 - threshold)

    def score(self, new_weight: float = 1.0, volume_weight: float = 0.0001,
              extreme_bonus: float = 5.0) -> float:
        """Calculate selection score for this market.
        Higher score = more interesting to feature.
        """
        # Newer markets get higher score
        current_ts = int(datetime.now().timestamp())
        age_hours = (current_ts - self.created_at) / 3600.0
        # Decay score with age
        new_score = new_weight / (1.0 + age_hours / 24.0)  # 24 hours half-life

        # Higher volume gets higher score
        volume_score = (self.volume or 0.0) * volume_weight

        # Bonus for extreme probability (deviation opportunity)
        bonus = extreme_bonus if self.is_probability_extreme() else 0.0

        return new_score + volume_score + bonus
