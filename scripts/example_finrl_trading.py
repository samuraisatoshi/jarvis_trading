#!/usr/bin/env python3
"""
Example: FinRL Model Integration with Paper Trading

Demonstrates how to:
1. Generate FinRL signals
2. Place trades via paper trading account
3. Monitor positions and performance

This is a reference implementation. Customize for your needs.

Usage:
    python scripts/example_finrl_trading.py --symbol BTC_USDT --timeframe 1d --test
"""

import sys
import asyncio
import argparse
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.reinforcement_learning.services.prediction_service import RLPredictionService
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.domain.account.repositories.account_repository import AccountRepository
from src.infrastructure.persistence.sqlite_account_repository import SQLiteAccountRepository

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinRLTradingBot:
    """Simple trading bot using FinRL signals."""

    def __init__(
        self,
        models_path: str,
        symbol: str = 'BTC_USDT',
        timeframe: str = '1d',
        confidence_threshold: float = 0.7,
        test_mode: bool = True
    ):
        """
        Initialize trading bot.

        Args:
            models_path: Path to FinRL trained models
            symbol: Trading pair (e.g., BTC_USDT)
            timeframe: Candle timeframe (e.g., 1d)
            confidence_threshold: Minimum confidence for trades
            test_mode: If True, only log signals (no actual trades)
        """
        self.models_path = models_path
        self.symbol = symbol
        self.timeframe = timeframe
        self.confidence_threshold = confidence_threshold
        self.test_mode = test_mode

        # Initialize services
        self.prediction_service = RLPredictionService(models_path)
        self.binance_client = BinanceRESTClient()

        # Account repository for tracking trades
        db_path = 'workspace/trading/db/trading.db'
        self.account_repo = SQLiteAccountRepository(db_path)

        logger.info(
            f"FinRLTradingBot initialized:\n"
            f"  Symbol: {symbol}\n"
            f"  Timeframe: {timeframe}\n"
            f"  Confidence threshold: {confidence_threshold:.0%}\n"
            f"  Test mode: {test_mode}\n"
            f"  Models: {models_path}"
        )

    async def generate_signal(self) -> dict:
        """
        Generate trading signal from FinRL model.

        Returns:
            Dict with signal details:
            {
                'symbol': str,
                'action': str,  # 'BUY', 'HOLD', 'SELL'
                'confidence': float,
                'price': float,
                'valid': bool
            }
        """
        try:
            logger.info(f"Generating signal for {self.symbol} {self.timeframe}...")

            # Fetch historical data
            symbol_binance = self.symbol.replace('_USDT', 'USDT')
            klines = self.binance_client.get_klines(
                symbol_binance,
                self.timeframe,
                limit=100
            )

            if not klines:
                logger.error("Failed to fetch klines")
                return {'valid': False, 'error': 'Failed to fetch klines'}

            # Convert to DataFrame
            df = pd.DataFrame(klines)

            # Generate prediction
            result = self.prediction_service.predict(self.symbol, self.timeframe, df)

            # Prepare signal
            signal = {
                'symbol': self.symbol,
                'action': self.prediction_service.get_action_name(result.action),
                'confidence': result.confidence,
                'price': result.price,
                'timestamp': datetime.utcnow().isoformat(),
                'model': result.model_name,
                'valid': True
            }

            logger.info(
                f"Signal generated: {signal['action']} "
                f"(confidence={signal['confidence']:.1%}, "
                f"price=${signal['price']:,.2f})"
            )

            return signal

        except Exception as e:
            logger.error(f"Signal generation failed: {e}", exc_info=True)
            return {'valid': False, 'error': str(e)}

    async def execute_signal(self, signal: dict) -> dict:
        """
        Execute trade based on signal.

        Args:
            signal: Signal from generate_signal()

        Returns:
            Execution result
        """
        if not signal.get('valid'):
            logger.warning(f"Invalid signal: {signal.get('error')}")
            return {'executed': False, 'reason': 'invalid_signal'}

        # Check confidence threshold
        if signal['confidence'] < self.confidence_threshold:
            logger.info(
                f"Signal confidence {signal['confidence']:.1%} below threshold "
                f"{self.confidence_threshold:.1%} - skipping"
            )
            return {'executed': False, 'reason': 'low_confidence'}

        # Skip HOLD actions
        if signal['action'] == 'HOLD':
            logger.info("HOLD signal - no action")
            return {'executed': False, 'reason': 'hold_action'}

        # Log or execute
        if self.test_mode:
            logger.info(f"[TEST MODE] Would execute: {signal['action']} {self.symbol}")
            return {
                'executed': True,
                'test_mode': True,
                'action': signal['action'],
                'symbol': self.symbol,
                'price': signal['price']
            }
        else:
            logger.warning("REAL TRADING MODE - trades will be executed (DISABLED IN EXAMPLE)")
            # In real implementation, call Binance API:
            # if signal['action'] == 'BUY':
            #     await self.place_buy_order(...)
            # elif signal['action'] == 'SELL':
            #     await self.place_sell_order(...)
            return {'executed': False, 'reason': 'real_trading_disabled'}

    async def run_once(self) -> dict:
        """Run signal generation and execution once."""
        logger.info("="*80)
        logger.info("TRADING BOT CYCLE START")
        logger.info("="*80)

        # Generate signal
        signal = await self.generate_signal()

        # Execute if valid
        if signal['valid']:
            execution = await self.execute_signal(signal)
            return {
                'signal': signal,
                'execution': execution,
                'success': execution['executed']
            }
        else:
            return {
                'signal': signal,
                'success': False
            }

    async def run_continuous(self, interval_seconds: int = 3600):
        """
        Run trading bot continuously.

        Args:
            interval_seconds: Seconds between signal generations
        """
        logger.info(f"Starting continuous trading bot (interval={interval_seconds}s)")

        cycle = 0
        while True:
            try:
                cycle += 1
                logger.info(f"\n--- Cycle {cycle} ---")

                result = await self.run_once()

                if result['success']:
                    logger.info("Trade executed successfully")
                else:
                    reason = result.get('signal', {}).get('error') or \
                             result.get('execution', {}).get('reason') or 'unknown'
                    logger.info(f"No trade this cycle: {reason}")

                # Wait for next cycle
                logger.info(f"Waiting {interval_seconds}s until next signal...")
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Error in continuous loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before retry


async def main():
    parser = argparse.ArgumentParser(
        description='FinRL Trading Bot Example'
    )
    parser.add_argument(
        '--symbol',
        default='BTC_USDT',
        help='Trading symbol'
    )
    parser.add_argument(
        '--timeframe',
        default='1d',
        help='Candle timeframe'
    )
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.7,
        help='Confidence threshold (0-1)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode (no real trades)'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=3600,
        help='Interval between cycles (seconds)'
    )

    args = parser.parse_args()

    # Find models path
    models_path = Path('/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models')
    if not models_path.exists():
        logger.error(f"Models path not found: {models_path}")
        sys.exit(1)

    # Initialize bot
    bot = FinRLTradingBot(
        str(models_path),
        symbol=args.symbol,
        timeframe=args.timeframe,
        confidence_threshold=args.confidence,
        test_mode=args.test or True  # Always test mode for example
    )

    # Run bot
    if args.continuous:
        await bot.run_continuous(interval_seconds=args.interval)
    else:
        result = await bot.run_once()

        logger.info("\n" + "="*80)
        logger.info("RESULT")
        logger.info("="*80)
        logger.info(f"Signal: {result['signal'].get('action', 'N/A')}")
        logger.info(f"Confidence: {result['signal'].get('confidence', 'N/A'):.1%}")
        logger.info(f"Price: ${result['signal'].get('price', 'N/A'):,.2f}")
        logger.info(f"Executed: {result['success']}")


if __name__ == '__main__':
    asyncio.run(main())
