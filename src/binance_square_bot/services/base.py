from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import Type, Optional, Any

class BaseSource(ABC):
    """Base class for all data sources.

    Each Source implements: config definition + data model + data fetch + content generation.
    """

    # Subclasses should define their own Pydantic model
    Model: Optional[Type[BaseModel]] = None

    class Config(BaseModel):
        """Base configuration for all sources."""
        enabled: bool = True
        daily_max_executions: int = 1

    @abstractmethod
    def fetch(self) -> Any:
        """Fetch data from source. Returns Model instance(s)."""
        pass

    @abstractmethod
    def generate(self, data: Any) -> Any:
        """Generate content from fetched data."""
        pass


class BaseTarget(ABC):
    """Base class for all publish targets."""

    class Config(BaseModel):
        """Base configuration for all targets."""
        enabled: bool = True
        daily_max_posts_per_key: int = 100
        api_keys: list[str] = []

    @abstractmethod
    def publish(self, content: Any, api_key: str) -> tuple[bool, str]:
        """Publish content using a specific API key.

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        pass

    def filter(self, content: Any) -> Any:
        """Content filter hook. Override to filter before publishing."""
        return content
