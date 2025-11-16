"""
Core backtesting engine with Strategy Pattern implementation.

This module provides an abstract backtesting engine that can run any trading strategy.
It handles position management, order execution, stop loss/take profit logic, and
portfolio tracking.

SOLID Principles:
- Single Responsibility: Engine only manages trade execution and portfolio
- Open/Closed: Open for extension (new strategies), closed for modification
- Liskov Substitution: Any strategy implementing the interface can be used
- Dependency Inversion: Depends on strategy abstraction, not concrete implementation

Design Pattern:
- Strategy Pattern: Separates execution engine from strategy logic
- Template Method: Define skeleton of backtest in base class
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional
from pathlib import Path

from .models import Trade, PortfolioState


class TradingStrategy(ABC):
    """
    Abstract base class for trading strategies.

    Any strategy must implement the generate_signal method which analyzes
    market data and returns a trading signal with entry/exit levels.
    """

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        Generate trading signal based on market data.

        Args:
            df: DataFrame with OHLCV data and any required indicators

        Returns:
            Dictionary with:
                - action: 'BUY', 'SELL', or 'HOLD'
                - stop_loss: Stop loss price (if action != HOLD)
                - take_profit_1: First take profit price (if action != HOLD)
                - take_profit_2: Second take profit price (if action != HOLD)
                - confirmations: List of confirmation signals
        """
        pass


class BacktestEngine:
    """
    Core backtesting engine for trading strategies.

    This engine simulates trading on historical data following a provided strategy.
    It manages:
    - Position entry/exit
    - Stop loss and take profit execution
    - Portfolio value tracking
    - Trade history recording

    The engine is strategy-agnostic and can backtest any strategy that implements
    the TradingStrategy interface.

    Attributes:
        initial_balance: Starting capital in USD
        strategy: Trading strategy instance
        cash: Current cash balance
        current_trade: Currently open trade (None if no position)
        trades: List of completed trades
        portfolio_history: List of portfolio states over time
    """

    def __init__(self, initial_balance: float, strategy: TradingStrategy):
        """
        Initialize backtest engine.

        Args:
            initial_balance: Starting capital in USD
            strategy: Strategy instance implementing TradingStrategy interface
        """
        self.initial_balance = initial_balance
        self.strategy = strategy

        # Portfolio state
        self.cash = initial_balance
        self.current_trade: Optional[Trade] = None

        # History tracking
        self.trades: List[Trade] = []
        self.portfolio_history: List[PortfolioState] = []

        print(f"\nBacktest Engine initialized:")
        print(f"  Initial Balance: ${initial_balance:,.2f}")
        print(f"  Strategy: {strategy.__class__.__name__}")

    def run(
        self,
        df: pd.DataFrame,
        warmup_periods: int = 200
    ) -> Tuple[List[Trade], pd.DataFrame]:
        """
        Execute backtest on historical data.

        Args:
            df: DataFrame with OHLCV data (indexed by timestamp)
            warmup_periods: Number of candles needed for indicator warmup

        Returns:
            Tuple of (trades_list, portfolio_dataframe)

        Raises:
            ValueError: If insufficient data for backtest
        """
        print("\n" + "="*80)
        print("RUNNING BACKTEST")
        print("="*80)

        if len(df) < warmup_periods:
            raise ValueError(
                f"Insufficient data. Need at least {warmup_periods} candles, "
                f"got {len(df)}"
            )

        # Reset state
        self.cash = self.initial_balance
        self.current_trade = None
        self.trades = []
        self.portfolio_history = []

        # Iterate through candles starting after warmup
        for i in range(warmup_periods, len(df)):
            df_slice = df.iloc[:i+1]
            current_candle = df_slice.iloc[-1]
            current_time = df_slice.index[-1]
            current_price = current_candle['close']

            # Calculate position value
            position_value = self._calculate_position_value(current_price)
            portfolio_value = self.cash + position_value

            # Process current position
            if self.current_trade:
                # Check for exit conditions (stop loss / take profit)
                exit_signal = self._check_exit_conditions(
                    current_price,
                    current_time
                )

                if exit_signal:
                    exit_price, exit_reason = exit_signal
                    self._execute_exit(
                        current_time,
                        exit_price,
                        exit_reason
                    )
                    position_value = 0.0
                    portfolio_value = self.cash

            # Record portfolio state
            self._record_portfolio_state(
                current_time,
                current_price,
                position_value,
                portfolio_value
            )

            # Look for entry signal if not in position
            if not self.current_trade:
                signal = self.strategy.generate_signal(df_slice)

                if signal['action'] in ['BUY', 'SELL']:
                    self._execute_entry(
                        current_time,
                        current_price,
                        signal
                    )

        # Close any remaining open trade
        if self.current_trade:
            final_time = df.index[-1]
            final_price = df.iloc[-1]['close']
            self._execute_exit(final_time, final_price, 'end_of_period')

        # Convert portfolio history to DataFrame
        portfolio_df = pd.DataFrame([state.to_dict() for state in self.portfolio_history])
        portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
        portfolio_df.set_index('timestamp', inplace=True)

        print(f"\nBacktest complete: {len(self.trades)} trades executed")

        return self.trades, portfolio_df

    def _calculate_position_value(self, current_price: float) -> float:
        """
        Calculate current position value.

        Args:
            current_price: Current asset price

        Returns:
            Position value in USD
        """
        if not self.current_trade:
            return 0.0

        if self.current_trade.side == 'LONG':
            return self.current_trade.quantity * current_price
        else:  # SHORT
            # For short: initial value + unrealized PnL
            initial_value = self.current_trade.quantity * self.current_trade.entry_price
            unrealized_pnl = (self.current_trade.entry_price - current_price) * self.current_trade.quantity
            return initial_value + unrealized_pnl

    def _check_exit_conditions(
        self,
        current_price: float,
        current_time: pd.Timestamp
    ) -> Optional[Tuple[float, str]]:
        """
        Check if any exit conditions are met.

        Args:
            current_price: Current asset price
            current_time: Current timestamp

        Returns:
            Tuple of (exit_price, exit_reason) if should exit, else None
        """
        if not self.current_trade:
            return None

        # Check stop loss
        if self.current_trade.stop_loss:
            if self.current_trade.side == 'LONG' and current_price <= self.current_trade.stop_loss:
                return (self.current_trade.stop_loss, 'stop_loss')
            elif self.current_trade.side == 'SHORT' and current_price >= self.current_trade.stop_loss:
                return (self.current_trade.stop_loss, 'stop_loss')

        # Check take profit 1
        if self.current_trade.take_profit_1:
            if self.current_trade.side == 'LONG' and current_price >= self.current_trade.take_profit_1:
                return (self.current_trade.take_profit_1, 'take_profit')
            elif self.current_trade.side == 'SHORT' and current_price <= self.current_trade.take_profit_1:
                return (self.current_trade.take_profit_1, 'take_profit')

        return None

    def _execute_entry(
        self,
        entry_time: pd.Timestamp,
        entry_price: float,
        signal: Dict
    ) -> None:
        """
        Execute trade entry.

        Args:
            entry_time: Entry timestamp
            entry_price: Entry price
            signal: Signal dictionary from strategy
        """
        quantity = self.cash / entry_price
        self.current_trade = Trade(
            entry_time=str(entry_time),
            entry_price=entry_price,
            quantity=quantity,
            side=signal['action'].replace('BUY', 'LONG').replace('SELL', 'SHORT'),
            stop_loss=signal.get('stop_loss'),
            take_profit_1=signal.get('take_profit_1'),
            take_profit_2=signal.get('take_profit_2'),
            confirmations=signal.get('confirmations', [])
        )

        action_label = "BUY" if signal['action'] == 'BUY' else "SELL"
        print(
            f"[{entry_time.strftime('%Y-%m-%d %H:%M')}] "
            f"{action_label} @ ${entry_price:,.2f} | "
            f"Qty: {quantity:.4f} | "
            f"SL: ${self.current_trade.stop_loss:,.2f} | "
            f"TP: ${self.current_trade.take_profit_1:,.2f}"
        )

        self.cash = 0  # All capital deployed

    def _execute_exit(
        self,
        exit_time: pd.Timestamp,
        exit_price: float,
        exit_reason: str
    ) -> None:
        """
        Execute trade exit.

        Args:
            exit_time: Exit timestamp
            exit_price: Exit price
            exit_reason: Reason for exit
        """
        if not self.current_trade:
            return

        self.current_trade.close(str(exit_time), exit_price, exit_reason)
        self.cash = self.initial_balance + self.current_trade.pnl
        self.trades.append(self.current_trade)

        reason_label = exit_reason.replace('_', ' ').title()
        print(
            f"[{exit_time.strftime('%Y-%m-%d %H:%M')}] "
            f"{reason_label} @ ${exit_price:,.2f} | "
            f"PnL: ${self.current_trade.pnl:+,.2f} "
            f"({self.current_trade.pnl_pct:+.2f}%)"
        )

        self.current_trade = None

    def _record_portfolio_state(
        self,
        timestamp: pd.Timestamp,
        price: float,
        position_value: float,
        portfolio_value: float
    ) -> None:
        """
        Record current portfolio state.

        Args:
            timestamp: Current timestamp
            price: Current asset price
            position_value: Current position value
            portfolio_value: Total portfolio value
        """
        state = PortfolioState(
            timestamp=str(timestamp),
            price=price,
            cash=self.cash,
            position_value=position_value,
            portfolio_value=portfolio_value,
            in_position=self.current_trade is not None
        )
        self.portfolio_history.append(state)

    def get_final_balance(self) -> float:
        """Get final portfolio balance."""
        if self.portfolio_history:
            return self.portfolio_history[-1].portfolio_value
        return self.initial_balance

    def get_trade_count(self) -> int:
        """Get total number of completed trades."""
        return len(self.trades)
