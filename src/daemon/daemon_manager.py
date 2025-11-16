"""
Multi-asset trading daemon manager.

Main orchestrator coordinating all daemon services and lifecycle.
"""

import time
from typing import List
from loguru import logger
from datetime import datetime, timezone

from .models import DaemonConfig
from .signal_processor import SignalProcessor
from .trade_executor import TradeExecutor
from .portfolio_service import PortfolioService
from .monitoring_service import MonitoringService
from .notification_handler import NotificationHandler


class DaemonManager:
    """
    Multi-asset trading daemon orchestrator.

    Coordinates daemon lifecycle, signal checking, trade execution,
    and periodic reporting across all services.
    """

    def __init__(
        self,
        signal_processor: SignalProcessor,
        trade_executor: TradeExecutor,
        portfolio_service: PortfolioService,
        monitoring_service: MonitoringService,
        notification_handler: NotificationHandler,
        config: DaemonConfig
    ):
        """
        Initialize daemon manager.

        Args:
            signal_processor: Signal detection service
            trade_executor: Trade execution service
            portfolio_service: Portfolio management service
            monitoring_service: Health monitoring service
            notification_handler: Notification routing service
            config: Daemon configuration
        """
        self.signal_processor = signal_processor
        self.trade_executor = trade_executor
        self.portfolio_service = portfolio_service
        self.monitoring_service = monitoring_service
        self.notification_handler = notification_handler
        self.config = config

        # Validate configuration
        self.config.validate()

        # Daemon state
        self.running = False
        self.paused = False

    def run(self) -> None:
        """
        Main daemon loop.

        Coordinates:
        1. Periodic signal checking
        2. Trade execution
        3. Status reporting
        4. Health monitoring

        Runs until stopped via stop() or KeyboardInterrupt.
        """
        logger.info("🚀 Multi-asset trading daemon started")
        logger.info(f"Config: {self.config.timeframes}, "
                   f"Check interval: {self.config.check_interval}s")

        self.running = True

        # Send startup notification
        self._send_startup_notification()

        # Track last check time
        last_hour = datetime.now(timezone.utc).hour
        last_status_hour = datetime.now(timezone.utc).hour

        while self.running:
            try:
                if not self.paused:
                    current_hour = datetime.now(timezone.utc).hour

                    # Check signals every hour (on the hour)
                    if current_hour != last_hour:
                        logger.info(
                            f"🕐 Hourly check at "
                            f"{datetime.now(timezone.utc).strftime('%H:%M')} UTC"
                        )

                        self._check_and_process_signals()

                        last_hour = current_hour

                    # Send periodic status report
                    if current_hour % self.config.status_report_interval == 0:
                        if current_hour != last_status_hour:
                            self._send_periodic_status()
                            last_status_hour = current_hour

                # Sleep between iterations
                time.sleep(30)  # Check every 30 seconds

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.monitoring_service.record_error(
                    'main_loop',
                    str(e)
                )
                # Sleep longer on error to avoid tight error loop
                time.sleep(60)

        logger.info("Daemon stopped gracefully")

    def _check_and_process_signals(self) -> None:
        """
        Check for signals and process them.

        Workflow:
        1. Check all symbols/timeframes for signals
        2. Record check metrics
        3. Prioritize signals (SELL first, larger TF first)
        4. Filter conflicting signals
        5. Execute trades with position sizing
        6. Record execution metrics
        """
        try:
            # Check all signals
            signals = self.signal_processor.check_all_signals(
                self.config.timeframes
            )

            # Record check
            self.monitoring_service.record_signal_check(signals)

            if not signals:
                logger.info("No signals detected")
                return

            logger.info(f"📊 {len(signals)} signals found")

            # Notify signals found
            self.notification_handler.notify_signals_found(signals)

            # Prioritize signals (SELL first, larger TF first)
            signals = self.signal_processor.prioritize_signals(signals)

            # Process each signal
            for signal in signals:
                try:
                    # Check for conflicts
                    if self.signal_processor.has_conflicting_signal(
                        signal,
                        signals
                    ):
                        logger.warning(
                            f"Conflicting signal ignored: {signal}"
                        )
                        continue

                    # Calculate position size
                    position_size = self.portfolio_service.calculate_position_size(
                        symbol=signal.symbol,
                        timeframe=signal.timeframe,
                        position_sizes=self.config.position_sizes
                    )

                    # Validate minimum size
                    if position_size < self.config.min_trade_value:
                        logger.warning(
                            f"Position size too small: ${position_size:.2f}, "
                            f"skipping {signal}"
                        )
                        continue

                    # Execute trade
                    result = self.trade_executor.execute_trade(
                        signal,
                        position_size
                    )

                    # Record result
                    self.monitoring_service.record_trade_execution(result)

                    # Notify if successful
                    if result.success:
                        self.notification_handler.notify_trade_executed(result)
                    else:
                        logger.warning(f"Trade failed: {result.error}")

                except Exception as e:
                    logger.error(f"Error processing signal {signal}: {e}")
                    self.monitoring_service.record_error(
                        'signal_processing',
                        str(e),
                        str(signal)
                    )

        except Exception as e:
            logger.error(f"Error in signal check: {e}")
            self.monitoring_service.record_error(
                'signal_check',
                str(e)
            )

    def _send_startup_notification(self) -> None:
        """Send daemon startup notification."""
        try:
            watchlist = self.signal_processor.watchlist.symbols
            portfolio = self.portfolio_service.get_portfolio_status(watchlist)

            self.notification_handler.notify_daemon_started(
                watchlist=watchlist,
                capital=portfolio.total_value
            )

            logger.info(
                f"Monitoring {len(watchlist)} symbols: {watchlist}"
            )
            logger.info(f"Initial capital: ${portfolio.total_value:.2f}")

        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")

    def _send_periodic_status(self) -> None:
        """Send periodic status report."""
        try:
            watchlist = self.signal_processor.watchlist.symbols
            self.monitoring_service.send_periodic_report(
                watchlist=watchlist,
                include_health=True
            )

            # Check health and send alerts if needed
            self.monitoring_service.send_health_alert_if_needed()

        except Exception as e:
            logger.error(f"Failed to send periodic status: {e}")
            self.monitoring_service.record_error(
                'periodic_status',
                str(e)
            )

    def stop(self) -> None:
        """
        Stop daemon gracefully.

        Signals main loop to exit and waits for current iteration to complete.
        """
        logger.info("Stopping daemon...")
        self.running = False

    def pause(self) -> None:
        """
        Pause signal checking.

        Daemon continues running but skips signal checks and trade execution.
        """
        logger.info("Daemon paused - signal checking disabled")
        self.paused = True

    def resume(self) -> None:
        """
        Resume signal checking after pause.
        """
        logger.info("Daemon resumed - signal checking enabled")
        self.paused = False

    def get_status(self) -> dict:
        """
        Get current daemon status.

        Returns:
            Dict with daemon state and metrics
        """
        health = self.monitoring_service.get_health_status()
        watchlist = self.signal_processor.watchlist.symbols

        try:
            portfolio = self.portfolio_service.get_portfolio_status(watchlist)
            portfolio_dict = portfolio.to_dict()
        except Exception as e:
            logger.error(f"Error getting portfolio status: {e}")
            portfolio_dict = {}

        return {
            'running': self.running,
            'paused': self.paused,
            'watchlist': watchlist,
            'timeframes': self.config.timeframes,
            'health': health,
            'portfolio': portfolio_dict
        }

    def force_signal_check(self) -> None:
        """
        Force immediate signal check (bypass timing).

        Useful for testing or manual intervention.
        """
        logger.info("Forcing signal check...")
        self._check_and_process_signals()
