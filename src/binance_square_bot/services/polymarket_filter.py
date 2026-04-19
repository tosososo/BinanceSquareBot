"""
@file polymarket_filter.py
@description Filters and scores Polymarket markets to find the most interesting one to feature
@created-by fullstack-dev-workflow
"""

import logging
from typing import List, Optional, Set

from binance_square_bot.models.polymarket_market import PolymarketMarket
from binance_square_bot.config import config

logger = logging.getLogger(__name__)


class PolymarketFilter:
    """Filters and scores Polymarket markets to find the most interesting one."""

    def __init__(
        self,
        min_volume: float = None,
        published_ids: Optional[Set[str]] = None,
    ):
        # Since MIN_VOLUME_THRESHOLD will be added in config later (Task 5),
        # provide a sensible default if it doesn't exist yet
        self.min_volume = min_volume if min_volume is not None else getattr(
            config, 'MIN_VOLUME_THRESHOLD', 1000.0
        )
        self.published_ids = published_ids or set()

    def filter_min_volume(self, markets: List[PolymarketMarket]) -> List[PolymarketMarket]:
        """Filter out markets with volume below minimum threshold."""
        return [m for m in markets if (m.volume or 0.0) >= self.min_volume]

    def exclude_published(self, markets: List[PolymarketMarket]) -> List[PolymarketMarket]:
        """Exclude already published markets."""
        return [m for m in markets if m.condition_id not in self.published_ids]

    def select_best_market(self, markets: List[PolymarketMarket]) -> Optional[PolymarketMarket]:
        """Select the best market to feature based on scoring.
        Returns None if no markets meet criteria.
        """
        # Filter step 1: min volume
        candidates = self.filter_min_volume(markets)
        # Filter step 2: exclude published
        candidates = self.exclude_published(candidates)

        if not candidates:
            logger.info("No candidate markets remaining after filtering")
            return None

        # Sort by score descending
        candidates.sort(key=lambda m: m.score(), reverse=True)

        best = candidates[0]
        logger.info(
            "Selected best market: question='%s' condition_id=%s score=%.2f volume=%.0f yes_price=%.1f%%",
            best.question, best.condition_id, best.score(), best.volume, best.yes_price * 100
        )
        return best
