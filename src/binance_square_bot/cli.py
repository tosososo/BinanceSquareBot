"""
@file cli.py
@description CLI命令行入口，使用Typer构建
@design-doc docs/08-cli-design/command-spec.md
@task-id BE-10
@created-by fullstack-dev-workflow
"""

from typing import Optional, Tuple
import time
import typer
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from datetime import datetime

from . import __version__
from .config import config
from .services.spider import FnSpiderService
from .services.storage import StorageService
from .services.generator import TweetGenerator
from .services.publisher import PublisherService, PublishResult
from binance_square_bot.services import (
    Storage,
    ForesightNewsSpider,
    TweetGenerator,
    BinancePublisher,
    PolymarketFetcher,
    PolymarketFilter,
    ResearchGenerator,
)


app = typer.Typer(
    name="binance-square-bot",
    help="BinanceSquareBot - 自动爬取Fn新闻生成币安广场推文",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"BinanceSquareBot v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="显示版本号",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """BinanceSquareBot - 自动爬取Fn新闻生成币安广场推文"""
    pass


@app.command("run")
def run(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="试运行模式：只爬取和生成，不实际发布",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="限制处理文章数量（用于测试）",
    ),
) -> None:
    """执行一次完整的爬取-生成-发布流程"""

    console.print("[bold blue]🚀 启动 BinanceSquareBot[/bold blue]")

    # 初始化服务
    storage = StorageService()
    spider = FnSpiderService()
    generator = TweetGenerator()
    publisher = PublisherService()

    # 爬取新闻
    console.print("[blue]📥 正在爬取Fn新闻列表...[/blue]")
    try:
        articles = spider.fetch_news_list()
    except Exception as e:
        console.print(f"[red]❌ 爬取失败: {str(e)}[/red]")
        raise typer.Exit(code=1)

    console.print(f"✓ 爬取完成，共 {len(articles)} 篇文章")

    # 过滤去重
    new_articles = []
    for article in articles:
        if not storage.is_url_processed(article.url):
            new_articles.append(article)

    console.print(f"✓ 去重完成，{len(new_articles)} 篇新文章待处理")

    if len(new_articles) == 0:
        console.print("[green]✨ 没有新文章，退出[/green]")
        raise typer.Exit()

    # 限制处理数量
    if limit is not None and len(new_articles) > limit:
        console.print(f"⚠️  限制处理数量: {limit}")
        new_articles = new_articles[:limit]

    # 统计（线程安全保护）
    total_attempted = 0
    generated_ok = 0
    published_ok = 0
    published_failed = 0

    # 遍历API密钥
    api_keys = config.binance_api_keys
    if not api_keys:
        console.print("[red]❌ 未配置BINANCE_API_KEYS[/red]")
        raise typer.Exit(code=1)

    # 定义每个API密钥的处理worker
    from threading import Lock
    stats_lock = Lock()

    def process_api_key(api_key_idx: int, api_key: str) -> Tuple[int, int, int, int]:
        """处理单个API密钥，返回(local_attempted, local_generated, local_published, local_failed)"""
        local_attempted = 0
        local_generated = 0
        local_published = 0
        local_failed = 0

        # 从数据库读取今日已发布计数
        current_count = storage.get_today_publish_count(api_key)
        with stats_lock:
            console.print(f"\n🔑 [blue]使用API密钥 #{api_key_idx + 1}[/blue] 今日已发布: {current_count}/{config.daily_max_posts}")

        for article in new_articles:
            # 检查每日发布限制
            if current_count >= config.daily_max_posts:
                with stats_lock:
                    console.print(f"⚠️  [yellow]已达到每日发布上限 {config.daily_max_posts} 篇，跳过剩余文章[/yellow]")
                break

            with stats_lock:
                local_attempted += 1
                console.print(f"\n🔄 [blue][API#{api_key_idx + 1}] 处理文章: {article.title}[/blue]")

            # 生成推文
            tweet = generator.generate_tweet(article)

            if not tweet.validation_passed:
                errors = ", ".join(tweet.validation_errors)
                with stats_lock:
                    console.print(f"⚠️  [yellow]格式校验失败: {errors}[/yellow]")
                continue

            with stats_lock:
                local_generated += 1

            with stats_lock:
                console.print(f"✓ 推文生成成功 ({len(tweet.content)} 字符)")

            if dry_run:
                with stats_lock:
                    console.print(f"⚠️  [yellow]试运行模式，跳过发布[/yellow]")
                storage.mark_url_processed(article.url, processed=False)
                continue

            # 发布
            result = publisher.publish_tweet(api_key, tweet)

            if result.success:
                with stats_lock:
                    local_published += 1
                current_count += 1
                # 数据库计数+1
                storage.increment_today_publish_count(api_key)
                with stats_lock:
                    console.print(f"✅ [green]发布成功: {result.tweet_url} ({current_count}/{config.daily_max_posts})[/green]")
                storage.mark_url_processed(article.url, processed=True)

                # 单账号发布频率限制：下一篇之前等待间隔
                if current_count < config.daily_max_posts and len(new_articles) > 1:
                    time.sleep(config.publish_interval_seconds)
            else:
                with stats_lock:
                    local_failed += 1
                with stats_lock:
                    console.print(f"❌ [red]发布失败: {result.error_message}[/red]")

        return (local_attempted, local_generated, local_published, local_failed)

    # 使用线程池并发处理多个API密钥
    max_workers = min(config.max_concurrent_accounts, len(api_keys))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, api_key in enumerate(api_keys):
            future = executor.submit(process_api_key, idx, api_key)
            futures.append(future)

        # 收集结果
        for future in futures:
            la, lg, lp, lf = future.result()
            with stats_lock:
                total_attempted += la
                generated_ok += lg
                published_ok += lp
                published_failed += lf

    # 输出统计
    console.print("\n[bold green]✨ 执行完成[/bold green]")

    table = Table(title="执行统计")
    table.add_column("指标", style="cyan")
    table.add_column("数量", style="magenta")
    table.add_row("爬取总文章", str(len(articles)))
    table.add_row("去重新文章", str(len(new_articles)))
    table.add_row("生成成功", str(generated_ok))
    table.add_row("发布成功", str(published_ok))
    table.add_row("发布失败", str(published_failed))
    console.print(table)


@app.command("clean")
def clean(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="跳过确认，直接清空",
    ),
) -> None:
    """清空已处理URL数据库，重置去重记录"""

    if not yes:
        confirm = typer.confirm(
            "⚠️  确认要清空已处理URL数据库吗？此操作不可恢复。"
        )
        if not confirm:
            raise typer.Exit()

    storage = StorageService()
    storage.clean_all()
    console.print("[green]✅ 已清空所有已处理记录[/green]")


@app.command()
def polymarket_research(
    dry_run: bool = typer.Option(False, "--dry-run", help="Only generate, don't publish"),
    limit: int = typer.Option(None, "--limit", help="Limit number of markets to scan"),
) -> None:
    """Generate and publish Polymarket investment research tweet."""
    from binance_square_bot.config import config
    if not config.enable_polymarket:
        typer.echo("Polymarket feature is disabled in config")
        raise typer.Exit(1)

    storage = Storage()
    fetcher = PolymarketFetcher()
    published_ids = storage.get_all_published_condition_ids()
    filterer = PolymarketFilter(published_ids=published_ids)
    generator = ResearchGenerator()
    publisher = BinancePublisher()

    typer.echo("Fetching Polymarket markets...")
    markets = fetcher.fetch_all_simplified()
    typer.echo(f"Fetched {len(markets)} markets")

    best_market = filterer.select_best_market(markets)
    if best_market is None:
        typer.echo("No eligible markets found")
        raise typer.Exit(0)

    typer.echo(f"Selected market: {best_market.question}")
    typer.echo(f"YES probability: {best_market.yes_price:.1%}, NO: {best_market.no_price:.1%}")
    typer.echo(f"Volume: {best_market.volume:.0f} USDC")

    typer.echo("\nGenerating research...")
    tweet, error = generator.generate_with_retry(best_market)
    if tweet is None:
        typer.echo(f"Generation failed after {config.max_retries} retries: {error}")
        raise typer.Exit(1)

    typer.echo("\nGenerated tweet:")
    typer.echo("-" * 60)
    typer.echo(tweet.content)
    typer.echo("-" * 60)
    typer.echo(f"\nLength: {len(tweet.content)} chars")

    if dry_run:
        typer.echo("\nDry-run mode, not publishing")
        raise typer.Exit(0)

    typer.echo("\nPublishing to all Binance accounts...")
    results = publisher.publish_tweet(tweet)

    success_count = sum(1 for success, _ in results if success)
    total_count = len(results)
    typer.echo(f"Published: {success_count}/{total_count} successful")

    if success_count > 0:
        storage.add_published_polymarket(best_market.condition_id, best_market.question)
        typer.echo(f"Market marked as published in storage: {best_market.condition_id}")
    else:
        typer.echo("No successful publishes, not marking as published")
        for _, msg in results:
            typer.echo(f"  Error: {msg}")
        raise typer.Exit(1)

    typer.echo("Done!")


@app.command()
def polymarket_scan(
    top_n: int = typer.Option(5, "--top-n", help="Show top N candidates"),
) -> None:
    """Scan Polymarket markets and show top candidates (don't generate or publish)."""
    from binance_square_bot.config import config
    if not config.enable_polymarket:
        typer.echo("Polymarket feature is disabled in config")
        raise typer.Exit(1)

    storage = Storage()
    fetcher = PolymarketFetcher()
    published_ids = storage.get_all_published_condition_ids()
    filterer = PolymarketFilter(published_ids=published_ids)

    typer.echo("Fetching Polymarket markets...")
    markets = fetcher.fetch_all_simplified()
    candidates = filterer.filter_min_volume(markets)
    candidates = filterer.exclude_published(candidates)
    candidates.sort(key=lambda m: m.score(), reverse=True)

    typer.echo(f"\nTop {min(top_n, len(candidates))} candidates:\n")
    for i, market in enumerate(candidates[:top_n], 1):
        typer.echo(f"{i}. {market.question}")
        typer.echo(f"   condition_id: {market.condition_id}")
        typer.echo(f"   YES: {market.yes_price:.1%}, NO: {market.no_price:.1%}")
        typer.echo(f"   Volume: {market.volume:.0f}, Score: {market.score():.2f}")
        typer.echo(f"   Extreme: {'Yes' if market.is_probability_extreme() else 'No'}")
        typer.echo("")

    typer.echo(f"Total candidates: {len(candidates)} / {len(markets)}")


if __name__ == "__main__":
    app()
