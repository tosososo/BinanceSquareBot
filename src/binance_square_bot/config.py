"""
@file config.py
@description 应用配置，使用pydantic-settings从环境变量加载
@design-doc docs/03-backend-design/domain-model.md
@task-id BE-02
@created-by fullstack-dev-workflow
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Config(BaseSettings):
    """应用配置，从环境变量加载"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 币安API密钥列表，逗号分隔
    binance_api_keys: List[str]

    # Fn新闻列表URL
    fn_news_url: str = "https://news.fn.org/news"

    # SQLite数据库文件路径
    sqlite_db_path: str = "data/processed_urls.db"

    # LLM配置
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str

    # 生成配置
    max_retries: int = 3
    min_chars: int = 101
    max_chars: int = 799
    max_hashtags: int = 2
    max_mentions: int = 2

    # 发布限制
    daily_max_posts: int = 100
    publish_interval_seconds: float = 1.0  # 单账号连续两篇推文发布间隔（秒）
    max_concurrent_accounts: int = 3  # 最大并发账号数

    # Polymarket API 配置
    polymarket_host: str = "https://clob.polymarket.com"
    polymarket_chain_id: int = 137  # Polygon
    min_volume_threshold: float = 1000.0  # 最小交易量阈值


config = Config()  # type: ignore[call-arg]
