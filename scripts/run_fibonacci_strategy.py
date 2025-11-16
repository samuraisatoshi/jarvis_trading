#!/usr/bin/env python3
"""
Fibonacci Golden Zone Paper Trading System (Entry Point)

This is a thin wrapper script that uses the FibonacciTradingOrchestrator
from src/application/orchestrators for the actual trading workflow.

All business logic and workflow coordination has been extracted to:
- src/application/orchestrators/fibonacci_trading_orchestrator.py
- src/strategies/fibonacci_golden_zone.py
- src/domain/account/ (account management)

This script only handles:
- CLI argument parsing
- Logging configuration
- Scheduler setup (daemon mode)
- Entry point execution

Usage:
    # One-time execution
    python scripts/run_fibonacci_strategy.py

    # Scheduled execution (daemon mode)
    python scripts/run_fibonacci_strategy.py --daemon

    # Dry run (no trades)
    python scripts/run_fibonacci_strategy.py --dry-run

Example:
    $ python scripts/run_fibonacci_strategy.py --dry-run
    FIBONACCI TRADING WORKFLOW
    ================================================================================
    Fetching 300 candles for BNBUSDT 1d
    Fetched 300 candles. Latest: 2025-11-14 23:59:59
    Signal: BUY
    Reason: Golden Zone em UPTREND com 3 confirmações bullish
    Entry: $618.50
    DRY RUN: Would execute BUY signal
"""

import sys
import asyncio
from pathlib import Path
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.application.orchestrators import FibonacciTradingOrchestrator
from src.domain.market_data.services.candle_scheduler import CandleScheduler


async def run_trading_cycle(orchestrator: FibonacciTradingOrchestrator, **kwargs):
    """
    Execute single trading cycle using orchestrator.

    Args:
        orchestrator: FibonacciTradingOrchestrator instance
        **kwargs: Additional parameters (unused, for scheduler compatibility)
    """
    result = orchestrator.execute()

    if result['status'] == 'failure':
        logger.error(f"Trading cycle failed: {result.get('error')}")
    else:
        logger.info(f"Trading cycle completed. Trade executed: {result['trade_executed']}")


async def run_daemon(
    orchestrator: FibonacciTradingOrchestrator,
    timeframe: str
):
    """
    Run paper trading in daemon mode (scheduled execution).

    Args:
        orchestrator: FibonacciTradingOrchestrator instance
        timeframe: Candle timeframe for scheduling (e.g., '1d', '4h')
    """
    scheduler = CandleScheduler()

    logger.info(f"Starting daemon mode for {orchestrator.symbol} {timeframe}")
    logger.info("Trades will execute at candle close using Fibonacci Golden Zone strategy")

    # Schedule job
    scheduler.start_job(
        timeframe=timeframe,
        callback=run_trading_cycle,
        callback_args=(orchestrator,),
        callback_kwargs={},
    )

    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("Stopping daemon...")
        scheduler.stop_all_jobs()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fibonacci Golden Zone paper trading system"
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Paper trading account ID",
    )
    parser.add_argument(
        "--symbol", type=str, default="BNB_USDT", help="Trading pair (e.g., BNB_USDT)"
    )
    parser.add_argument(
        "--timeframe", type=str, default="1d", help="Candle timeframe (e.g., 1d)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(project_root / "data" / "jarvis_trading.db"),
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode (scheduled execution)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run (no trades executed)"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        project_root / "logs" / f"fibonacci_strategy_{args.symbol}_{args.timeframe}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )

    # Create orchestrator (now contains all workflow logic)
    orchestrator = FibonacciTradingOrchestrator(
        account_id=args.account_id,
        symbol=args.symbol,
        timeframe=args.timeframe,
        db_path=args.db,
        dry_run=args.dry_run,
    )

    # Run
    if args.daemon:
        asyncio.run(run_daemon(orchestrator, args.timeframe))
    else:
        # One-time execution
        asyncio.run(run_trading_cycle(orchestrator))


if __name__ == "__main__":
    main()
