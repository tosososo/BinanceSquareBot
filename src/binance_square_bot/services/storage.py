"""
@file storage.py
@description SQLite存储服务，用于存储已处理文章URL的MD5实现增量去重
@design-doc docs/01-architecture/system-architecture.md
@task-id BE-05
@created-by fullstack-dev-workflow
"""

import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import config


class StorageService:
    """SQLite存储服务，用于增量去重"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or config.sqlite_db_path
        # 确保目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self) -> None:
        """初始化数据库，创建表结构如果不存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_md5 TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            """)
            # 创建唯一索引加速去重查询
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_url_md5 ON processed_urls (url_md5)
            """)

            # 创建每日发布统计表，用于记录每个api_key每日发布数量
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_publish_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    publish_date DATE NOT NULL,
                    api_key_hash TEXT NOT NULL,
                    publish_count INTEGER DEFAULT 0,
                    UNIQUE(publish_date, api_key_hash)
                )
            """)

            # Create published_polymarket table if not exists
            cursor.execute("""
CREATE TABLE IF NOT EXISTS published_polymarket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id TEXT NOT NULL UNIQUE,
    question TEXT NOT NULL,
    published_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
            """)
            conn.commit()

    def _get_url_md5(self, url: str) -> str:
        """计算URL的MD5哈希"""
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    def is_url_processed(self, url: str) -> bool:
        """检查URL是否已经处理过"""
        url_md5 = self._get_url_md5(url)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM processed_urls WHERE url_md5 = ?",
                (url_md5,)
            )
            return cursor.fetchone() is not None

    def mark_url_processed(self, url: str, processed: bool = True) -> None:
        """标记URL为已处理"""
        url_md5 = self._get_url_md5(url)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 如果不存在则插入，存在则更新processed状态
            cursor.execute("""
                INSERT INTO processed_urls (url_md5, url, processed)
                VALUES (?, ?, ?)
                ON CONFLICT(url_md5)
                DO UPDATE SET processed = ?
            """, (url_md5, url, processed, processed))
            conn.commit()

    def clean_all(self) -> None:
        """清空所有已处理记录（用于cli clean命令）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM processed_urls")
            conn.commit()

    def count_processed(self) -> int:
        """统计已处理URL数量"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM processed_urls")
            result = cursor.fetchone()
            return result[0] if result else 0

    def _get_api_key_hash(self, api_key: str) -> str:
        """对API密钥哈希后存储，不保存明文"""
        return hashlib.md5(api_key.encode("utf-8")).hexdigest()

    def get_today_publish_count(self, api_key: str) -> int:
        """获取今日该API密钥已发布数量"""
        today = datetime.now().date().isoformat()
        api_key_hash = self._get_api_key_hash(api_key)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT publish_count FROM daily_publish_stats
                WHERE publish_date = ? AND api_key_hash = ?
            """, (today, api_key_hash))
            result = cursor.fetchone()
            return result[0] if result else 0

    def increment_today_publish_count(self, api_key: str) -> None:
        """今日该API密钥发布计数+1"""
        today = datetime.now().date().isoformat()
        api_key_hash = self._get_api_key_hash(api_key)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 如果不存在则插入计数=1，存在则更新+1
            cursor.execute("""
                INSERT INTO daily_publish_stats (publish_date, api_key_hash, publish_count)
                VALUES (?, ?, 1)
                ON CONFLICT(publish_date, api_key_hash)
                DO UPDATE SET publish_count = publish_count + 1
            """, (today, api_key_hash))
            conn.commit()

    def is_polymarket_published(self, condition_id: str) -> bool:
        """Check if a Polymarket has already been published."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM published_polymarket WHERE condition_id = ?",
                (condition_id,)
            )
            return cursor.fetchone() is not None

    def get_all_published_condition_ids(self) -> set:
        """Get all published Polymarket condition IDs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT condition_id FROM published_polymarket")
            return {row[0] for row in cursor.fetchall()}

    def add_published_polymarket(self, condition_id: str, question: str) -> None:
        """Mark a Polymarket as published."""
        import time
        now = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO published_polymarket
                (condition_id, question, published_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (condition_id, question, now, now)
            )
            conn.commit()
