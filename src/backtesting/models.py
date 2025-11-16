"""
Data models for backtesting framework.

This module defines core data structures used throughout the backtesting system.
All models are immutable dataclasses for thread-safety and predictability.

SOLID Principles:
- Single Responsibility: Each class represents ONE concept
- Open/Closed: Extensible through inheritance
- Liskov Substitution: Subtypes can replace base types
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict
from enum import Enum


class TradeType(Enum):
    """Trade direction types."""
    LONG = 'LONG'
    SHORT = 'SHORT'


class ExitReason(Enum):
    """Reasons for trade exit."""
    STOP_LOSS = 'stop_loss'
    TAKE_PROFIT = 'take_profit'
    MANUAL = 'manual'
    END_OF_PERIOD = 'end_of_period'
    SIGNAL = 'signal'


@dataclass
class Trade:
    """
    Single trade record with complete trade lifecycle information.

    Attributes:
        entry_time: ISO format timestamp of trade entry
        entry_price: Price at which trade was entered
        quantity: Amount of asset traded
        side: Trade direction (LONG or SHORT)
        exit_time: ISO format timestamp of trade exit (None if open)
        exit_price: Price at which trade was exited (None if open)
        stop_loss: Stop loss price level
        take_profit_1: First take profit price level
        take_profit_2: Second take profit price level
        confirmations: List of confirmation signals that triggered entry
        pnl: Profit/Loss in USD (None if open)
        pnl_pct: Profit/Loss percentage (None if open)
        duration_hours: Trade duration in hours (None if open)
        exit_reason: Reason for trade exit (None if open)
    """
    entry_time: str
    entry_price: float
    quantity: float
    side: str = 'LONG'
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    confirmations: Optional[List[str]] = field(default_factory=list)
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    duration_hours: Optional[float] = None
    exit_reason: Optional[str] = None

    def close(self, exit_time: str, exit_price: float, reason: str = 'manual') -> None:
        """
        Close the trade and calculate PnL.

        Args:
            exit_time: ISO format timestamp of exit
            exit_price: Price at which to exit
            reason: Reason for exit (stop_loss, take_profit, etc.)

        Note:
            This method mutates the Trade object. For pure functional approach,
            consider creating a new Trade instance instead.
        """
        import pandas as pd

        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason

        # Calculate PnL based on side
        if self.side == 'LONG':
            self.pnl = (exit_price - self.entry_price) * self.quantity
            self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            self.pnl = (self.entry_price - exit_price) * self.quantity
            self.pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100

        # Calculate duration
        entry_dt = pd.to_datetime(self.entry_time)
        exit_dt = pd.to_datetime(exit_time)
        self.duration_hours = (exit_dt - entry_dt).total_seconds() / 3600

    def is_open(self) -> bool:
        """Check if trade is still open."""
        return self.exit_time is None

    def is_winner(self) -> bool:
        """Check if trade was profitable."""
        return self.pnl is not None and self.pnl > 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class BacktestMetrics:
    """
    Comprehensive backtest performance metrics.

    This dataclass contains all key performance indicators for a backtest run.
    Metrics follow industry standards (Sharpe Ratio, Max Drawdown, etc.).

    Attributes:
        strategy_name: Name of the strategy tested
        symbol: Trading pair symbol (e.g., 'BNB_USDT')
        timeframe: Candle timeframe (e.g., '4h', '1d')
        start_date: Backtest start date (ISO format)
        end_date: Backtest end date (ISO format)
        initial_balance: Starting capital in USD
        final_balance: Ending capital in USD
        total_return_pct: Total return percentage
        total_return_usd: Total return in USD
        annualized_return_pct: Annualized return percentage
        sharpe_ratio: Risk-adjusted return metric
        max_drawdown_pct: Maximum drawdown percentage
        max_drawdown_usd: Maximum drawdown in USD
        win_rate_pct: Percentage of winning trades
        total_trades: Total number of trades executed
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        average_win_pct: Average winning trade percentage
        average_loss_pct: Average losing trade percentage
        profit_factor: Ratio of total profit to total loss
        best_trade_pct: Best single trade percentage
        worst_trade_pct: Worst single trade percentage
        avg_trade_duration_hours: Average trade duration in hours
        longest_win_streak: Longest consecutive winning streak
        longest_loss_streak: Longest consecutive losing streak
        time_in_market_pct: Percentage of time with open position
    """
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_return_pct: float
    total_return_usd: float
    annualized_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    max_drawdown_usd: float
    win_rate_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_win_pct: float
    average_loss_pct: float
    profit_factor: float
    best_trade_pct: float
    worst_trade_pct: float
    avg_trade_duration_hours: float
    longest_win_streak: int
    longest_loss_streak: int
    time_in_market_pct: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def print_summary(self) -> None:
        """Print formatted summary of metrics."""
        print(f"\n{'='*80}")
        print(f" {self.strategy_name.upper()} - PERFORMANCE SUMMARY")
        print(f"{'='*80}")
        print(f"\n Symbol: {self.symbol} | Timeframe: {self.timeframe}")
        print(f" Period: {self.start_date} to {self.end_date}")
        print(f"\n {'='*78}")
        print(f" {'Return Metrics':<39} {'Risk Metrics':<39}")
        print(f" {'='*78}")
        print(f" Initial Balance: ${self.initial_balance:>16,.2f}   Sharpe Ratio: {self.sharpe_ratio:>18.2f}")
        print(f" Final Balance:   ${self.final_balance:>16,.2f}   Max Drawdown: {self.max_drawdown_pct:>17.2f}%")
        print(f" Total Return:    {self.total_return_pct:>17.2f}%   Win Rate:     {self.win_rate_pct:>17.2f}%")
        print(f" Annualized:      {self.annualized_return_pct:>17.2f}%   Profit Factor:{self.profit_factor:>17.2f}")
        print(f"\n {'='*78}")
        print(f" {'Trade Statistics':<78}")
        print(f" {'='*78}")
        print(f" Total Trades: {self.total_trades:>5} ({self.winning_trades}W / {self.losing_trades}L)")
        print(f" Average Win:  {self.average_win_pct:>5.2f}% | Average Loss: {self.average_loss_pct:>5.2f}%")
        print(f" Best Trade:   {self.best_trade_pct:>5.2f}% | Worst Trade:  {self.worst_trade_pct:>5.2f}%")
        print(f" Avg Duration: {self.avg_trade_duration_hours:>5.1f}h | Time in Market: {self.time_in_market_pct:>5.1f}%")
        print(f" Win Streak:   {self.longest_win_streak:>5} | Loss Streak:  {self.longest_loss_streak:>5}")
        print(f"{'='*80}\n")


@dataclass
class PortfolioState:
    """
    Snapshot of portfolio state at a specific time.

    Used for tracking portfolio value evolution during backtest.

    Attributes:
        timestamp: ISO format timestamp
        price: Current asset price
        cash: Cash balance in USD
        position_value: Value of open positions in USD
        portfolio_value: Total portfolio value (cash + positions)
        in_position: Whether currently holding a position
    """
    timestamp: str
    price: float
    cash: float
    position_value: float
    portfolio_value: float
    in_position: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
