"""
Trade execution service.

Handles trade execution with validation, position sizing, and error handling.
"""

from typing import Optional
from loguru import logger

from .models import Signal, SignalAction, TradeResult
from .interfaces import (
    BalanceRepository,
    OrderRepository,
    PositionRepository,
    NotificationService
)


class TradeExecutor:
    """
    Trade execution service.

    Coordinates trade execution across balance updates, order creation,
    and notification sending with proper validation and error handling.
    """

    MIN_TRADE_VALUE = 10.0  # Minimum trade size in USD

    def __init__(
        self,
        balance_repo: BalanceRepository,
        order_repo: OrderRepository,
        position_repo: PositionRepository,
        notification_service: NotificationService
    ):
        """
        Initialize trade executor.

        Args:
            balance_repo: Balance repository for account balances
            order_repo: Order repository for order persistence
            position_repo: Position repository for holdings
            notification_service: Notification service for alerts
        """
        self.balance_repo = balance_repo
        self.order_repo = order_repo
        self.position_repo = position_repo
        self.notification_service = notification_service

    def execute_trade(
        self,
        signal: Signal,
        position_size_usd: float
    ) -> TradeResult:
        """
        Execute trade based on signal.

        Routes to BUY or SELL execution with proper validation.

        Args:
            signal: Trading signal to execute
            position_size_usd: Position size in USD (for BUY only)

        Returns:
            TradeResult with execution status and details
        """
        try:
            if signal.action == SignalAction.BUY:
                return self._execute_buy(signal, position_size_usd)

            elif signal.action == SignalAction.SELL:
                return self._execute_sell(signal)

            else:
                return TradeResult(
                    success=False,
                    signal=signal,
                    error=f"Unknown action: {signal.action}"
                )

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return TradeResult(
                success=False,
                signal=signal,
                error=str(e)
            )

    def _execute_buy(
        self,
        signal: Signal,
        position_size_usd: float
    ) -> TradeResult:
        """
        Execute BUY order.

        Process:
        1. Validate position size
        2. Check USDT balance
        3. Calculate quantity
        4. Update balances (atomic)
        5. Create order record
        6. Send notification

        Args:
            signal: BUY signal
            position_size_usd: Position size in USD

        Returns:
            TradeResult with execution details
        """
        # Validate position size
        if position_size_usd < self.MIN_TRADE_VALUE:
            return TradeResult(
                success=False,
                signal=signal,
                error=(
                    f"Position too small: ${position_size_usd:.2f} "
                    f"< ${self.MIN_TRADE_VALUE}"
                )
            )

        # Calculate quantity
        quantity = position_size_usd / signal.price
        base_currency = signal.symbol.replace('USDT', '')

        logger.info(
            f"Executing BUY: {quantity:.6f} {signal.symbol} @ "
            f"${signal.price:.2f} = ${position_size_usd:.2f}"
        )

        # Check USDT balance
        usdt_balance = self.balance_repo.get_balance('USDT')
        if usdt_balance < position_size_usd:
            return TradeResult(
                success=False,
                signal=signal,
                error=(
                    f"Insufficient USDT balance: ${usdt_balance:.2f} "
                    f"< ${position_size_usd:.2f}"
                )
            )

        try:
            # Update balances (atomic operation)
            # Subtract USDT
            success = self.balance_repo.update_balance(
                'USDT',
                position_size_usd,
                'subtract'
            )
            if not success:
                return TradeResult(
                    success=False,
                    signal=signal,
                    error="Failed to update USDT balance"
                )

            # Add base currency
            success = self.balance_repo.update_balance(
                base_currency,
                quantity,
                'add'
            )
            if not success:
                # Rollback USDT (best effort)
                self.balance_repo.update_balance(
                    'USDT',
                    position_size_usd,
                    'add'
                )
                return TradeResult(
                    success=False,
                    signal=signal,
                    error="Failed to update asset balance"
                )

            # Create order record
            order_id = self.order_repo.create_order(
                symbol=signal.symbol,
                side='BUY',
                quantity=quantity,
                price=signal.price,
                order_type='MARKET'
            )

            logger.info(
                f"✅ BUY executed: {quantity:.6f} {signal.symbol} @ "
                f"${signal.price:.2f} = ${position_size_usd:.2f} "
                f"(Order: {order_id})"
            )

            # REMOVED: Duplicate notification - moved to daemon_manager
            # Notification is now handled by daemon_manager.py to avoid duplication
            # The daemon_manager calls notification_handler.notify_trade_executed(result)
            # after trade execution, so we don't need to send it here anymore

            return TradeResult(
                success=True,
                signal=signal,
                quantity=quantity,
                total_value=position_size_usd,
                order_id=order_id
            )

        except Exception as e:
            logger.error(f"BUY execution failed: {e}")
            return TradeResult(
                success=False,
                signal=signal,
                error=str(e)
            )

    def _execute_sell(self, signal: Signal) -> TradeResult:
        """
        Execute SELL order.

        Process:
        1. Get current position
        2. Validate position exists
        3. Calculate proceeds
        4. Update balances (atomic)
        5. Create order record
        6. Send notification

        Args:
            signal: SELL signal

        Returns:
            TradeResult with execution details
        """
        base_currency = signal.symbol.replace('USDT', '')

        # Get current position
        position = self.position_repo.get_position(signal.symbol)
        if not position or position.quantity <= 0:
            return TradeResult(
                success=False,
                signal=signal,
                error=f"No position in {signal.symbol}"
            )

        quantity = position.quantity
        total_value = quantity * signal.price

        logger.info(
            f"Executing SELL: {quantity:.6f} {signal.symbol} @ "
            f"${signal.price:.2f} = ${total_value:.2f}"
        )

        try:
            # Update balances (atomic operation)
            # Subtract base currency
            success = self.balance_repo.update_balance(
                base_currency,
                quantity,
                'subtract'
            )
            if not success:
                return TradeResult(
                    success=False,
                    signal=signal,
                    error="Failed to update asset balance"
                )

            # Add USDT
            success = self.balance_repo.update_balance(
                'USDT',
                total_value,
                'add'
            )
            if not success:
                # Rollback asset (best effort)
                self.balance_repo.update_balance(
                    base_currency,
                    quantity,
                    'add'
                )
                return TradeResult(
                    success=False,
                    signal=signal,
                    error="Failed to update USDT balance"
                )

            # Create order record
            order_id = self.order_repo.create_order(
                symbol=signal.symbol,
                side='SELL',
                quantity=quantity,
                price=signal.price,
                order_type='MARKET'
            )

            logger.info(
                f"✅ SELL executed: {quantity:.6f} {signal.symbol} @ "
                f"${signal.price:.2f} = ${total_value:.2f} "
                f"(Order: {order_id})"
            )

            # REMOVED: Duplicate notification - moved to daemon_manager
            # Notification is now handled by daemon_manager.py to avoid duplication
            # The daemon_manager calls notification_handler.notify_trade_executed(result)
            # after trade execution, so we don't need to send it here anymore

            return TradeResult(
                success=True,
                signal=signal,
                quantity=quantity,
                total_value=total_value,
                order_id=order_id
            )

        except Exception as e:
            logger.error(f"SELL execution failed: {e}")
            return TradeResult(
                success=False,
                signal=signal,
                error=str(e)
            )

    def validate_trade(
        self,
        signal: Signal,
        position_size_usd: Optional[float] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate trade before execution.

        Args:
            signal: Trading signal to validate
            position_size_usd: Position size (required for BUY)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if signal.action == SignalAction.BUY:
                # Validate position size provided
                if position_size_usd is None:
                    return False, "Position size required for BUY"

                # Validate minimum size
                if position_size_usd < self.MIN_TRADE_VALUE:
                    return False, (
                        f"Position too small: ${position_size_usd:.2f} "
                        f"< ${self.MIN_TRADE_VALUE}"
                    )

                # Validate sufficient balance
                usdt_balance = self.balance_repo.get_balance('USDT')
                if usdt_balance < position_size_usd:
                    return False, (
                        f"Insufficient balance: ${usdt_balance:.2f} "
                        f"< ${position_size_usd:.2f}"
                    )

            elif signal.action == SignalAction.SELL:
                # Validate position exists
                position = self.position_repo.get_position(signal.symbol)
                if not position or position.quantity <= 0:
                    return False, f"No position in {signal.symbol}"

            return True, None

        except Exception as e:
            return False, f"Validation error: {e}"
