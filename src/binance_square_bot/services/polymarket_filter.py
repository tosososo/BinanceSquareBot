"""
@file polymarket_filter.py
@description Filters and scores Polymarket markets to find the most interesting one to feature
@created-by fullstack-dev-workflow
"""

import logging

from binance_square_bot.config import config
from binance_square_bot.models.polymarket_market import PolymarketMarket

from loguru import logger


class PolymarketFilter:
    """Filters and scores Polymarket markets to find the most interesting one."""

    def __init__(
        self,
        min_volume: float | None = None,
        published_ids: set[str] | None = None,
    ):
        self.min_volume = min_volume if min_volume is not None else config.min_volume_threshold
        self.published_ids = published_ids or set()

    def filter_min_volume(self, markets: list[PolymarketMarket]) -> list[PolymarketMarket]:
        """Filter out markets with volume below minimum threshold."""
        return [m for m in markets if (m.volume or 0.0) >= self.min_volume]

    def exclude_published(self, markets: list[PolymarketMarket]) -> list[PolymarketMarket]:
        """Exclude already published markets."""
        return [m for m in markets if m.condition_id not in self.published_ids]

    def select_best_market(self, markets: list[PolymarketMarket]) -> PolymarketMarket | None:
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

        # Log top candidates for debugging
        logger.debug("Candidate markets after filtering and scoring:")
        for i, candidate in enumerate(candidates[:10], 1):
            logger.debug(
                "  %d: question='%s' condition_id=%s score=%.2f",
                i, candidate.question, candidate.condition_id, candidate.score()
            )

        best = candidates[0]
        logger.info(
            "Selected best market: question='%s' condition_id=%s score=%.2f volume=%.0f yes_price=%.1f%%",
            best.question, best.condition_id, best.score(), best.volume, best.yes_price * 100
        )
        return best
