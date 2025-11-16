#!/usr/bin/env python3
"""
Comprehensive backtesting engine for 2025 data with FinRL models.

This script backtests all available FinRL models on 2025 data and generates
detailed performance reports including:
- Individual trade analysis
- Drawdown analysis
- Confidence scoring
- Performance metrics

Usage:
    python scripts/backtest_2025.py --symbol BTC_USDT --timeframe 1d --initial-balance 5000
    python scripts/backtest_2025.py --all-models --parallel 4
    python scripts/backtest_2025.py --data-dir data/2025 --models-dir ../finrl/trained_models

Results:
    - data/backtests/2025/results.json - Aggregated results
    - data/backtests/2025/trades_{symbol}_{timeframe}.csv - Individual trades
    - data/backtests/2025/metrics_{symbol}_{timeframe}.json - Detailed metrics
"""

import sys
import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.reinforcement_learning.services.model_loader import ModelLoader
from src.domain.reinforcement_learning.services.prediction_service import RLPredictionService
from src.domain.features.services.feature_calculator import FeatureCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Single trade record."""
    entry_time: str
    entry_price: float
    exit_time: Optional[str]
    exit_price: Optional[float]
    quantity: float
    entry_confidence: float
    side: str  # 'LONG' or 'SHORT'
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    duration_hours: Optional[float] = None

    def close(self, exit_time: str, exit_price: float, exit_confidence: float):
        """Close the trade."""
        self.exit_time = exit_time
        self.exit_price = exit_price

        if self.side == 'LONG':
            self.pnl = (exit_price - self.entry_price) * self.quantity
            self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:
            self.pnl = (self.entry_price - exit_price) * self.quantity
            self.pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100

        # Duration
        entry_dt = pd.to_datetime(self.entry_time)
        exit_dt = pd.to_datetime(exit_time)
        self.duration_hours = (exit_dt - entry_dt).total_seconds() / 3600


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""
    symbol: str
    timeframe: str
    initial_balance: float
    final_balance: float
    total_return_pct: float
    total_return_usd: float
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
    avg_candles_per_trade: float


class BacktestEngine2025:
    """Backtest FinRL models on 2025 data."""

    def __init__(self, initial_balance: float = 5000.0):
        """
        Initialize backtest engine.

        Args:
            initial_balance: Starting capital in USDT
        """
        self.initial_balance = initial_balance
        self.feature_calc = FeatureCalculator()

    def backtest_symbol_timeframe(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        model_loader: ModelLoader,
        min_confidence: float = 0.0
    ) -> Tuple[BacktestMetrics, List[Trade]]:
        """
        Run backtest for single symbol/timeframe.

        Args:
            df: OHLCV DataFrame
            symbol: Trading pair (format: BTC_USDT)
            timeframe: Timeframe string
            model_loader: Loaded models
            min_confidence: Minimum confidence threshold

        Returns:
            Tuple of (metrics, trades list)
        """
        logger.info(f"\nBacktesting {symbol} {timeframe}...")

        try:
            # Load model
            model_symbol = symbol.replace('_', '').replace('USDT', '').upper()
            rl_service = RLPredictionService(model_loader)

            # Calculate features
            logger.debug("  Calculating features...")
            df_features = self.feature_calc.calculate_features(df.copy())

            # Validate we have enough data
            if len(df_features) < 100:
                logger.warning(f"  Not enough data: {len(df_features)} candles (need 100+)")
                return None, []

            # Initialize backtest state
            balance = self.initial_balance
            position = None  # None or Trade object
            trades = []
            equity_curve = [balance]
            timestamps = []

            # Process candles
            logger.debug(f"  Processing {len(df_features)} candles...")

            for i in range(100, len(df_features)):
                current_time = df_features.index[i]
                current_price = df_features.iloc[i]['close']
                current_row = df_features.iloc[i:i+1]

                # Get prediction from model
                try:
                    prediction = rl_service.predict(symbol, timeframe, df_features.iloc[max(0, i-100):i+1])

                    if prediction is None or prediction.confidence < min_confidence:
                        continue

                    action = prediction.action  # 0=SELL, 1=HOLD, 2=BUY
                    confidence = prediction.confidence

                except Exception as e:
                    logger.debug(f"  Prediction error at {current_time}: {e}")
                    continue

                # Handle trading logic
                if action == 2 and position is None:  # BUY signal
                    # Calculate position size (1% of balance per trade)
                    position_size = balance * 0.01 * confidence
                    if position_size > 0:
                        quantity = position_size / current_price
                        position = Trade(
                            entry_time=str(current_time),
                            entry_price=current_price,
                            exit_time=None,
                            exit_price=None,
                            quantity=quantity,
                            entry_confidence=confidence,
                            side='LONG'
                        )
                        balance -= position_size
                        logger.debug(f"  BUY {symbol}: {quantity:.4f} @ {current_price:.2f} (conf: {confidence:.0%})")

                elif action == 0 and position is not None:  # SELL signal
                    # Close position
                    proceeds = position.quantity * current_price
                    position.close(str(current_time), current_price, confidence)
                    balance += proceeds + position.pnl
                    trades.append(position)
                    logger.debug(f"  SELL {symbol}: PnL {position.pnl:.2f} ({position.pnl_pct:.1f}%)")
                    position = None

                # Update equity curve
                equity = balance
                if position is not None:
                    equity += position.quantity * current_price
                equity_curve.append(equity)
                timestamps.append(current_time)

            # Close any open position at end
            if position is not None:
                last_price = df_features.iloc[-1]['close']
                position.close(str(df_features.index[-1]), last_price, 0.5)
                balance += position.quantity * last_price + position.pnl
                trades.append(position)
                equity_curve[-1] = balance

            # Calculate metrics
            metrics = self._calculate_metrics(
                symbol=symbol,
                timeframe=timeframe,
                initial_balance=self.initial_balance,
                final_balance=balance,
                trades=trades,
                equity_curve=equity_curve,
                timestamps=timestamps,
                df=df_features
            )

            logger.info(
                f"  Complete: {len(trades)} trades, "
                f"Return: {metrics.total_return_pct:.1f}%, "
                f"Sharpe: {metrics.sharpe_ratio:.2f}, "
                f"Max DD: {metrics.max_drawdown_pct:.1f}%"
            )

            return metrics, trades

        except Exception as e:
            logger.error(f"  Error backtesting {symbol} {timeframe}: {e}")
            logger.debug(traceback.format_exc())
            return None, []

    def _calculate_metrics(
        self,
        symbol: str,
        timeframe: str,
        initial_balance: float,
        final_balance: float,
        trades: List[Trade],
        equity_curve: List[float],
        timestamps: List,
        df: pd.DataFrame
    ) -> BacktestMetrics:
        """Calculate performance metrics."""

        # Returns
        total_return_usd = final_balance - initial_balance
        total_return_pct = (total_return_usd / initial_balance) * 100

        # Sharpe Ratio
        equity_series = pd.Series(equity_curve)
        returns = equity_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

        # Drawdown
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        max_drawdown_pct = drawdown.min()
        max_drawdown_usd = initial_balance * (max_drawdown_pct / 100)

        # Win rate
        winning = [t for t in trades if t.pnl and t.pnl > 0]
        losing = [t for t in trades if t.pnl and t.pnl <= 0]
        win_rate = (len(winning) / len(trades) * 100) if trades else 0

        # Average P&L
        avg_win = np.mean([t.pnl_pct for t in winning]) if winning else 0
        avg_loss = np.mean([t.pnl_pct for t in losing]) if losing else 0

        # Profit factor
        total_profit = sum(t.pnl for t in winning if t.pnl) if winning else 0
        total_loss = abs(sum(t.pnl for t in losing if t.pnl)) if losing else 1
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        # Best/worst trades
        all_pnl_pcts = [t.pnl_pct for t in trades if t.pnl_pct is not None]
        best_trade = max(all_pnl_pcts) if all_pnl_pcts else 0
        worst_trade = min(all_pnl_pcts) if all_pnl_pcts else 0

        # Avg candles per trade
        avg_candles = len(df) / len(trades) if trades else 0

        return BacktestMetrics(
            symbol=symbol,
            timeframe=timeframe,
            initial_balance=initial_balance,
            final_balance=final_balance,
            total_return_pct=total_return_pct,
            total_return_usd=total_return_usd,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_drawdown_pct,
            max_drawdown_usd=max_drawdown_usd,
            win_rate_pct=win_rate,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            average_win_pct=avg_win,
            average_loss_pct=avg_loss,
            profit_factor=profit_factor,
            best_trade_pct=best_trade,
            worst_trade_pct=worst_trade,
            avg_candles_per_trade=avg_candles
        )

    def load_data(self, symbol: str, timeframe: str, data_dir: str = 'data/2025') -> Optional[pd.DataFrame]:
        """Load preprocessed CSV data."""
        safe_symbol = symbol.replace('_', '_').upper()
        filepath = Path(data_dir) / f"{safe_symbol}_{timeframe}_2025.csv"

        if not filepath.exists():
            logger.warning(f"Data file not found: {filepath}")
            return None

        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            logger.info(f"Loaded {len(df)} candles from {filepath.name}")
            return df
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return None

    def save_results(
        self,
        results_dir: str,
        all_metrics: Dict[str, BacktestMetrics],
        all_trades: Dict[str, List[Trade]]
    ):
        """Save backtest results to files."""
        output_dir = Path(results_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save aggregated metrics
        metrics_data = {
            key: asdict(metrics)
            for key, metrics in all_metrics.items()
            if metrics is not None
        }

        results_file = output_dir / 'results.json'
        with open(results_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        logger.info(f"Saved results to {results_file}")

        # Save individual trades
        for key, trades in all_trades.items():
            if not trades:
                continue

            trades_df = pd.DataFrame([asdict(t) for t in trades])
            trades_file = output_dir / f"trades_{key}.csv"
            trades_df.to_csv(trades_file, index=False)
            logger.info(f"Saved {len(trades)} trades to {trades_file.name}")

        # Save summary report
        summary_file = output_dir / 'BACKTEST_REPORT.txt'
        self._write_summary_report(summary_file, all_metrics)

    def _write_summary_report(self, filepath: Path, all_metrics: Dict[str, BacktestMetrics]):
        """Write human-readable summary report."""
        with open(filepath, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("2025 BACKTEST REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Report generated: {datetime.now().isoformat()}\n")
            f.write(f"Period: 2025-01-01 to 2025-11-14\n")
            f.write(f"Initial balance: $5,000 USDT\n\n")

            # Group by metric
            sorted_metrics = sorted(
                [m for m in all_metrics.values() if m],
                key=lambda x: x.total_return_pct,
                reverse=True
            )

            f.write("TOP 10 PERFORMERS BY RETURN\n")
            f.write("-" * 80 + "\n")
            for i, m in enumerate(sorted_metrics[:10], 1):
                f.write(
                    f"{i:2d}. {m.symbol:12s} {m.timeframe:5s} "
                    f"Return: {m.total_return_pct:+7.1f}% "
                    f"Sharpe: {m.sharpe_ratio:6.2f} "
                    f"DD: {m.max_drawdown_pct:+6.1f}% "
                    f"Trades: {m.total_trades:3d}\n"
                )

            f.write("\n")
            f.write("DETAILED RESULTS\n")
            f.write("-" * 80 + "\n\n")

            for m in sorted_metrics:
                f.write(f"Symbol: {m.symbol} | Timeframe: {m.timeframe}\n")
                f.write(f"  Return: {m.total_return_pct:+.1f}% (${m.total_return_usd:+.2f})\n")
                f.write(f"  Balance: ${m.final_balance:,.2f}\n")
                f.write(f"  Sharpe Ratio: {m.sharpe_ratio:.2f}\n")
                f.write(f"  Max Drawdown: {m.max_drawdown_pct:.1f}% (${m.max_drawdown_usd:.2f})\n")
                f.write(f"  Trades: {m.total_trades} (Win: {m.winning_trades}, Loss: {m.losing_trades})\n")
                f.write(f"  Win Rate: {m.win_rate_pct:.1f}%\n")
                f.write(f"  Avg Win/Loss: +{m.average_win_pct:.1f}% / {m.average_loss_pct:.1f}%\n")
                f.write(f"  Profit Factor: {m.profit_factor:.2f}\n")
                f.write(f"  Best/Worst Trade: {m.best_trade_pct:+.1f}% / {m.worst_trade_pct:+.1f}%\n")
                f.write("\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest FinRL models on 2025 data')
    parser.add_argument('--symbol', type=str, help='Single symbol to backtest (format: BTC_USDT)')
    parser.add_argument('--timeframe', type=str, help='Single timeframe to backtest')
    parser.add_argument('--data-dir', type=str, default='data/2025', help='Data directory')
    parser.add_argument('--models-dir', type=str, default='../finrl/trained_models', help='Models directory')
    parser.add_argument('--output-dir', type=str, default='data/backtests/2025', help='Output directory')
    parser.add_argument('--initial-balance', type=float, default=5000.0, help='Initial balance')
    parser.add_argument('--min-confidence', type=float, default=0.0, help='Minimum confidence threshold')
    parser.add_argument('--all-models', action='store_true', help='Test all available model combinations')

    args = parser.parse_args()

    # Create engine
    engine = BacktestEngine2025(initial_balance=args.initial_balance)

    # Resolve models directory
    models_path = Path(args.models_dir).resolve()
    if not models_path.exists():
        models_path = Path('/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models')

    if not models_path.exists():
        logger.error(f"Models directory not found: {models_path}")
        return 1

    # Load models
    logger.info(f"Loading models from {models_path}...")
    model_loader = ModelLoader(str(models_path))

    all_metrics = {}
    all_trades = {}

    if args.symbol and args.timeframe:
        # Single symbol/timeframe
        df = engine.load_data(args.symbol, args.timeframe, args.data_dir)
        if df is None:
            return 1

        metrics, trades = engine.backtest_symbol_timeframe(
            df, args.symbol, args.timeframe, model_loader,
            min_confidence=args.min_confidence
        )

        if metrics:
            key = f"{args.symbol}_{args.timeframe}"
            all_metrics[key] = metrics
            all_trades[key] = trades

    else:
        # All available combinations from data files
        data_dir = Path(args.data_dir)
        if not data_dir.exists():
            logger.error(f"Data directory not found: {data_dir}")
            return 1

        csv_files = list(data_dir.glob('*_*_2025.csv'))
        logger.info(f"Found {len(csv_files)} data files")

        for filepath in csv_files:
            # Parse filename: BTC_USDT_1h_2025.csv
            parts = filepath.stem.replace('_2025', '').split('_')
            if len(parts) < 2:
                continue

            timeframe = parts[-1]
            symbol = '_'.join(parts[:-1])

            df = engine.load_data(symbol, timeframe, args.data_dir)
            if df is None:
                continue

            metrics, trades = engine.backtest_symbol_timeframe(
                df, symbol, timeframe, model_loader,
                min_confidence=args.min_confidence
            )

            if metrics:
                key = f"{symbol}_{timeframe}"
                all_metrics[key] = metrics
                all_trades[key] = trades

    # Save results
    engine.save_results(args.output_dir, all_metrics, all_trades)

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Tested combinations: {len(all_metrics)}")
    logger.info(f"Total trades: {sum(len(t) for t in all_trades.values())}")

    successful = [m for m in all_metrics.values() if m and m.total_return_pct > 0]
    logger.info(f"Profitable combinations: {len(successful)}/{len(all_metrics)}")

    if successful:
        best = max(successful, key=lambda x: x.total_return_pct)
        logger.info(f"\nBest performer: {best.symbol} {best.timeframe}")
        logger.info(f"  Return: {best.total_return_pct:.1f}%")
        logger.info(f"  Sharpe: {best.sharpe_ratio:.2f}")
        logger.info(f"  Max DD: {best.max_drawdown_pct:.1f}%")

    logger.info(f"\nResults saved to {args.output_dir}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
