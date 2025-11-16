"""
Signal detection and processing service.

Monitors market data, generates trading signals, and handles signal prioritization.
"""

import pandas as pd
import time
from typing import List, Optional, Dict
from loguru import logger
from datetime import datetime, timezone

from .models import Signal, SignalAction
from .interfaces import ExchangeClient, PositionRepository, WatchlistManager


class SignalProcessor:
    """
    Signal detection and processing service.

    Generates trading signals based on moving average strategy,
    filters conflicts, and prioritizes by timeframe.
    """

    def __init__(
        self,
        exchange_client: ExchangeClient,
        position_repo: PositionRepository,
        watchlist_manager: WatchlistManager,
        min_check_intervals: Optional[Dict[str, int]] = None
    ):
        """
        Initialize signal processor.

        Args:
            exchange_client: Exchange client for market data
            position_repo: Position repository for holdings
            watchlist_manager: Watchlist manager for symbols and params
            min_check_intervals: Min seconds between checks per timeframe
        """
        self.exchange_client = exchange_client
        self.position_repo = position_repo
        self.watchlist = watchlist_manager
        self.min_check_intervals = min_check_intervals or {
            '1h': 300,    # 5 minutes
            '4h': 1200,   # 20 minutes
            '1d': 3600    # 1 hour
        }
        self.last_check: Dict[str, float] = {}

    def check_signal(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[Signal]:
        """
        Check for trading signal on specific symbol/timeframe.

        Uses moving average distance strategy:
        - BUY when price is below MA by threshold %
        - SELL when price is above MA by threshold % (and position exists)

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe to analyze

        Returns:
            Signal if opportunity detected, None otherwise
        """
        try:
            # Get optimized parameters for this symbol/timeframe
            params = self.watchlist.get_params(symbol, timeframe)
            if not params:
                logger.debug(
                    f"No parameters configured for {symbol} {timeframe}"
                )
                return None

            # Get current price
            ticker = self.exchange_client.get_24h_ticker(symbol)
            current_price = float(ticker['lastPrice'])

            # Get historical data for MA calculation
            ma_period = params['ma_period']
            klines = self.exchange_client.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=ma_period + 10  # Extra buffer
            )

            if len(klines) < ma_period:
                logger.warning(
                    f"Insufficient data for {symbol} {timeframe}: "
                    f"{len(klines)} < {ma_period}"
                )
                return None

            # Calculate moving average
            df = pd.DataFrame(klines)
            df['close'] = df['close'].astype(float)
            ma = df['close'].rolling(window=ma_period).mean().iloc[-1]

            # Calculate distance from MA (%)
            distance = ((current_price - ma) / ma) * 100

            logger.debug(
                f"{symbol} {timeframe}: Price ${current_price:.2f}, "
                f"MA{ma_period} ${ma:.2f}, Distance {distance:.2f}%"
            )

            # Check for BUY signal
            if distance <= params['buy_threshold']:
                return Signal(
                    symbol=symbol,
                    timeframe=timeframe,
                    action=SignalAction.BUY,
                    price=current_price,
                    ma=ma,
                    distance=distance,
                    threshold=params['buy_threshold'],
                    reason=(
                        f"Price {distance:.1f}% below "
                        f"MA{ma_period} (threshold: {params['buy_threshold']:.1f}%)"
                    ),
                    timestamp=datetime.now(timezone.utc)
                )

            # Check for SELL signal (only if we have position)
            elif distance >= params['sell_threshold']:
                position = self.position_repo.get_position(symbol)

                if position and position.quantity > 0:
                    return Signal(
                        symbol=symbol,
                        timeframe=timeframe,
                        action=SignalAction.SELL,
                        price=current_price,
                        ma=ma,
                        distance=distance,
                        threshold=params['sell_threshold'],
                        reason=(
                            f"Price {distance:.1f}% above "
                            f"MA{ma_period} (threshold: {params['sell_threshold']:.1f}%)"
                        ),
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    logger.debug(
                        f"SELL signal for {symbol} but no position held"
                    )

            return None

        except Exception as e:
            logger.error(f"Error checking signal {symbol} {timeframe}: {e}")
            return None

    def check_all_signals(
        self,
        timeframes: List[str]
    ) -> List[Signal]:
        """
        Check signals for all watchlist symbols and timeframes.

        Implements rate limiting to avoid excessive API calls.
        Each symbol/timeframe combination has minimum check interval.

        Args:
            timeframes: List of timeframes to check

        Returns:
            List of detected signals
        """
        signals = []
        now = time.time()

        for symbol in self.watchlist.symbols:
            for timeframe in timeframes:
                # Check rate limiting
                check_key = f"{symbol}_{timeframe}"
                last_check = self.last_check.get(check_key, 0)
                min_interval = self.min_check_intervals.get(timeframe, 600)

                elapsed = now - last_check
                if elapsed < min_interval:
                    logger.debug(
                        f"Skipping {check_key}: "
                        f"checked {elapsed:.0f}s ago (min: {min_interval}s)"
                    )
                    continue

                # Check for signal
                signal = self.check_signal(symbol, timeframe)
                if signal:
                    signals.append(signal)
                    logger.info(f"Signal detected: {signal}")

                # Update last check time
                self.last_check[check_key] = now

        logger.info(f"Signal check complete: {len(signals)} signals found")
        return signals

    def prioritize_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        Sort signals by priority.

        Priority rules:
        1. SELL signals before BUY (exit positions first)
        2. Larger timeframes before smaller (1d > 4h > 1h)

        Args:
            signals: List of signals to prioritize

        Returns:
            Sorted list of signals
        """
        timeframe_priority = {'1d': 3, '4h': 2, '1h': 1}

        sorted_signals = sorted(signals, key=lambda s: (
            s.action == SignalAction.BUY,  # SELL=0 comes first, BUY=1 comes second
            -timeframe_priority.get(s.timeframe, 0)  # Larger TF first
        ))

        if sorted_signals != signals:
            logger.debug(
                f"Prioritized signals: "
                f"{[f'{s.action.value} {s.symbol} {s.timeframe}' for s in sorted_signals]}"
            )

        return sorted_signals

    def has_conflicting_signal(
        self,
        signal: Signal,
        all_signals: List[Signal]
    ) -> bool:
        """
        Check if signal conflicts with higher priority signals.

        A conflict occurs when:
        - Same symbol
        - Opposite action (BUY vs SELL)
        - Other signal has higher priority timeframe

        Args:
            signal: Signal to check
            all_signals: All signals in current batch

        Returns:
            True if conflicting signal found, False otherwise
        """
        timeframe_priority = {'1d': 3, '4h': 2, '1h': 1}
        signal_priority = timeframe_priority.get(signal.timeframe, 0)

        for other in all_signals:
            if other == signal:
                continue

            # Check for conflict
            if (other.symbol == signal.symbol and
                other.action != signal.action):

                other_priority = timeframe_priority.get(other.timeframe, 0)

                if other_priority > signal_priority:
                    logger.warning(
                        f"Signal conflict: {signal.action.value} {signal.symbol} "
                        f"({signal.timeframe}) overridden by {other.action.value} "
                        f"({other.timeframe})"
                    )
                    return True

        return False

    def get_check_statistics(self) -> Dict:
        """
        Get signal checking statistics.

        Returns:
            Dict with check counts and timing info
        """
        return {
            'symbols_monitored': len(self.watchlist.symbols),
            'last_checks': {
                key: {
                    'timestamp': datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                    'elapsed_seconds': time.time() - ts
                }
                for key, ts in self.last_check.items()
            },
            'min_check_intervals': self.min_check_intervals
        }
