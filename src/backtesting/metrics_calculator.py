"""
Performance metrics calculator for backtest results.

This module calculates comprehensive performance metrics following industry standards.
Metrics include risk-adjusted returns, drawdowns, trade statistics, and temporal analysis.

SOLID Principles:
- Single Responsibility: Only calculates metrics
- Open/Closed: Extensible with new metric calculations
- Dependency Inversion: Works with any data following Trade/Portfolio structure
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from .models import Trade, BacktestMetrics


class MetricsCalculator:
    """
    Calculator for backtest performance metrics.

    This class provides static methods to calculate various performance metrics
    from backtest results. All methods are stateless and can be called independently.

    Metrics Categories:
    - Return Metrics: Total return, annualized return
    - Risk Metrics: Sharpe ratio, max drawdown
    - Trade Statistics: Win rate, profit factor, streaks
    - Temporal Analysis: Period performance, time in market
    """

    @staticmethod
    def calculate(
        trades: List[Trade],
        portfolio_df: pd.DataFrame,
        initial_balance: float,
        symbol: str,
        timeframe: str,
        strategy_name: str = "Trading Strategy"
    ) -> BacktestMetrics:
        """
        Calculate comprehensive performance metrics.

        Args:
            trades: List of completed trades
            portfolio_df: DataFrame with portfolio value history
            initial_balance: Starting capital
            symbol: Trading pair symbol
            timeframe: Candle timeframe
            strategy_name: Name of strategy

        Returns:
            BacktestMetrics with all calculated metrics

        Raises:
            ValueError: If portfolio_df is empty
        """
        if portfolio_df.empty:
            raise ValueError("Portfolio dataframe is empty")

        # Basic metrics
        final_balance = portfolio_df['portfolio_value'].iloc[-1]
        total_return_usd = final_balance - initial_balance
        total_return_pct = (total_return_usd / initial_balance) * 100

        # Annualized return
        days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
        years = days / 365.25
        annualized_return_pct = (
            ((final_balance / initial_balance) ** (1 / years) - 1) * 100
            if years > 0 else 0
        )

        # Trade statistics
        trade_stats = MetricsCalculator._calculate_trade_statistics(trades)

        # Risk metrics
        sharpe = MetricsCalculator._calculate_sharpe_ratio(
            portfolio_df,
            timeframe
        )
        max_dd_pct, max_dd_usd = MetricsCalculator._calculate_max_drawdown(
            portfolio_df
        )

        # Time in market
        time_in_market = (
            portfolio_df['in_position'].sum() / len(portfolio_df) * 100
        )

        return BacktestMetrics(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=str(portfolio_df.index[0].date()),
            end_date=str(portfolio_df.index[-1].date()),
            initial_balance=initial_balance,
            final_balance=final_balance,
            total_return_pct=total_return_pct,
            total_return_usd=total_return_usd,
            annualized_return_pct=annualized_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd_pct,
            max_drawdown_usd=max_dd_usd,
            win_rate_pct=trade_stats['win_rate'],
            total_trades=trade_stats['total_trades'],
            winning_trades=trade_stats['winning_trades'],
            losing_trades=trade_stats['losing_trades'],
            average_win_pct=trade_stats['avg_win'],
            average_loss_pct=trade_stats['avg_loss'],
            profit_factor=trade_stats['profit_factor'],
            best_trade_pct=trade_stats['best_trade'],
            worst_trade_pct=trade_stats['worst_trade'],
            avg_trade_duration_hours=trade_stats['avg_duration'],
            longest_win_streak=trade_stats['longest_win_streak'],
            longest_loss_streak=trade_stats['longest_loss_streak'],
            time_in_market_pct=time_in_market
        )

    @staticmethod
    def _calculate_trade_statistics(trades: List[Trade]) -> Dict:
        """
        Calculate trade-level statistics.

        Args:
            trades: List of completed trades

        Returns:
            Dictionary with trade statistics
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_duration': 0,
                'longest_win_streak': 0,
                'longest_loss_streak': 0
            }

        # Separate winners and losers
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl <= 0]

        # Win rate
        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0

        # Average win/loss
        avg_win = (
            np.mean([t.pnl_pct for t in winning_trades])
            if winning_trades else 0
        )
        avg_loss = (
            np.mean([t.pnl_pct for t in losing_trades])
            if losing_trades else 0
        )

        # Profit factor
        total_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
        profit_factor = (
            (total_profit / total_loss)
            if total_loss > 0 else float('inf')
        )

        # Best/worst trades
        best_trade = max([t.pnl_pct for t in trades]) if trades else 0
        worst_trade = min([t.pnl_pct for t in trades]) if trades else 0

        # Average duration
        avg_duration = (
            np.mean([t.duration_hours for t in trades if t.duration_hours])
            if trades else 0
        )

        # Win/Loss streaks
        streaks = MetricsCalculator._calculate_streaks(trades)

        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_duration': avg_duration,
            'longest_win_streak': streaks['longest_win'],
            'longest_loss_streak': streaks['longest_loss']
        }

    @staticmethod
    def _calculate_streaks(trades: List[Trade]) -> Dict:
        """
        Calculate winning and losing streaks.

        Args:
            trades: List of completed trades

        Returns:
            Dictionary with longest win and loss streaks
        """
        if not trades:
            return {'longest_win': 0, 'longest_loss': 0}

        win_streaks = []
        loss_streaks = []
        current_streak = 0
        current_type = None

        for trade in trades:
            is_win = trade.pnl and trade.pnl > 0

            if is_win:
                if current_type == 'win':
                    current_streak += 1
                else:
                    if current_type is not None:
                        loss_streaks.append(current_streak)
                    current_streak = 1
                    current_type = 'win'
            else:
                if current_type == 'loss':
                    current_streak += 1
                else:
                    if current_type is not None:
                        win_streaks.append(current_streak)
                    current_streak = 1
                    current_type = 'loss'

        # Add final streak
        if current_type == 'win':
            win_streaks.append(current_streak)
        elif current_type == 'loss':
            loss_streaks.append(current_streak)

        return {
            'longest_win': max(win_streaks) if win_streaks else 0,
            'longest_loss': max(loss_streaks) if loss_streaks else 0
        }

    @staticmethod
    def _calculate_sharpe_ratio(
        portfolio_df: pd.DataFrame,
        timeframe: str
    ) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted return).

        Args:
            portfolio_df: DataFrame with portfolio value history
            timeframe: Candle timeframe

        Returns:
            Sharpe ratio value
        """
        returns = portfolio_df['portfolio_value'].pct_change().dropna()

        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        # Determine periods per year based on timeframe
        periods_map = {
            '1m': 525600,  # 60 * 24 * 365
            '5m': 105120,  # 12 * 24 * 365
            '15m': 35040,  # 4 * 24 * 365
            '1h': 8760,    # 24 * 365
            '4h': 2190,    # 6 * 365
            '1d': 365,
            '1w': 52
        }
        periods_per_year = periods_map.get(timeframe, 2190)  # Default to 4h

        # Sharpe ratio = (mean return / std return) * sqrt(periods per year)
        sharpe = (returns.mean() / returns.std()) * np.sqrt(periods_per_year)

        return sharpe

    @staticmethod
    def _calculate_max_drawdown(
        portfolio_df: pd.DataFrame
    ) -> tuple[float, float]:
        """
        Calculate maximum drawdown.

        Args:
            portfolio_df: DataFrame with portfolio value history

        Returns:
            Tuple of (max_drawdown_pct, max_drawdown_usd)
        """
        portfolio_values = portfolio_df['portfolio_value']
        peak = portfolio_values.expanding(min_periods=1).max()
        drawdown = (portfolio_values - peak) / peak * 100

        max_drawdown_pct = drawdown.min()
        max_drawdown_usd = peak.max() - portfolio_values.min()

        return max_drawdown_pct, max_drawdown_usd

    @staticmethod
    def analyze_by_period(
        trades: List[Trade],
        portfolio_df: pd.DataFrame,
        period: str = 'Q'
    ) -> pd.DataFrame:
        """
        Analyze performance by time period.

        Args:
            trades: List of completed trades
            portfolio_df: DataFrame with portfolio value history
            period: Period frequency ('Q' for quarter, 'M' for month, etc.)

        Returns:
            DataFrame with period-level performance metrics
        """
        periods = []

        # Group by period
        portfolio_df_copy = portfolio_df.copy()
        portfolio_df_copy['period'] = portfolio_df_copy.index.to_period(period)

        for period_key, group in portfolio_df_copy.groupby('period'):
            period_start = group.index[0]
            period_end = group.index[-1]
            start_value = group['portfolio_value'].iloc[0]
            end_value = group['portfolio_value'].iloc[-1]

            # Trades in this period
            period_trades = [
                t for t in trades
                if period_start <= pd.to_datetime(t.entry_time) <= period_end
            ]

            period_return = (
                ((end_value - start_value) / start_value * 100)
                if start_value > 0 else 0
            )

            periods.append({
                'period': str(period_key),
                'start_date': period_start.strftime('%Y-%m-%d'),
                'end_date': period_end.strftime('%Y-%m-%d'),
                'start_value': start_value,
                'end_value': end_value,
                'return_pct': period_return,
                'num_trades': len(period_trades),
                'winning_trades': len([t for t in period_trades if t.pnl and t.pnl > 0])
            })

        return pd.DataFrame(periods)

    @staticmethod
    def compare_strategies(
        metrics_list: List[BacktestMetrics]
    ) -> pd.DataFrame:
        """
        Compare multiple strategy results.

        Args:
            metrics_list: List of BacktestMetrics from different strategies

        Returns:
            DataFrame with comparison metrics
        """
        comparison = []

        for metrics in metrics_list:
            comparison.append({
                'Strategy': metrics.strategy_name,
                'Total Return (%)': metrics.total_return_pct,
                'Annualized Return (%)': metrics.annualized_return_pct,
                'Max Drawdown (%)': metrics.max_drawdown_pct,
                'Sharpe Ratio': metrics.sharpe_ratio,
                'Win Rate (%)': metrics.win_rate_pct,
                'Profit Factor': metrics.profit_factor,
                'Total Trades': metrics.total_trades
            })

        df = pd.DataFrame(comparison)
        return df.set_index('Strategy')
