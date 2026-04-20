from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime
import hashlib
from .base import Base

class DailyPublishStatsModel(Base):
    __tablename__ = "daily_publish_stats"

    target_name = Column(String, primary_key=True, index=True)
    api_key_hash = Column(String, primary_key=True, index=True)  # Hash API key for privacy
    api_key_mask = Column(String)                                  # Masked for display (e.g., "xxxx...abcd")
    date = Column(String, primary_key=True, index=True)           # YYYY-MM-DD
    count = Column(Integer, default=0)
    last_published_at = Column(DateTime)

    @classmethod
    def today(cls) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @classmethod
    def hash_key(cls, api_key: str) -> str:
        """Hash API key for indexing - returns first 16 hex chars of SHA256."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]

    @classmethod
    def mask_key(cls, api_key: str) -> str:
        """Mask API key for display - shows first 8 and last 4 chars.

        Kept for backward compatibility. Use mask_api_key from binance_target instead.
        """
        from binance_square_bot.services.target.binance_target import mask_api_key
        return mask_api_key(api_key)
