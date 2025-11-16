#!/usr/bin/env python3
"""
Fibonacci Golden Zone Strategy Backtest for 2025

Comprehensive backtesting comparing:
1. Fibonacci Golden Zone Strategy
2. Buy & Hold baseline
3. FinRL ML Model (optional comparison)

Generates detailed performance metrics and comparison charts.

Usage:
    # Backtest Fibonacci strategy
    python scripts/backtest_fibonacci_2025.py --symbol BNB_USDT --start 2025-01-01

    # Compare with ML model
    python scripts/backtest_fibonacci_2025.py --symbol BNB_USDT --compare-ml

    # Custom initial balance
    python scripts/backtest_fibonacci_2025.py --symbol BNB_USDT --balance 5000

Example Output:
    ================================================================================
    FIBONACCI GOLDEN ZONE BACKTEST RESULTS - BNB_USDT (2025-01-01 to 2025-11-15)
    ================================================================================

    Strategy Performance:
      Total Return: +35.20% ($13,520)
      Sharpe Ratio: 1.85
      Max Drawdown: -12.30% ($1,230)
      Win Rate: 62.50% (10/16 trades)
      Profit Factor: 2.45

    Buy & Hold Performance:
      Total Return: +28.50% ($11,350)

    Fibonacci vs Buy & Hold: +6.70% outperformance

    Report saved: data/backtests/fibonacci_2025_BNB_USDT_20251115.json
    Chart saved: data/backtests/fibonacci_2025_BNB_USDT_20251115.png
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from src/backtesting framework
from src.backtesting import (
    FibonacciBacktester,
    MetricsCalculator,
    BuyAndHoldBaseline,
    BacktestVisualizer,
    print_baseline_comparison
)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backtest Fibonacci Golden Zone strategy on 2025 data"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BNB_USDT",
        help="Trading pair (e.g., BNB_USDT)"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1d",
        help="Candle timeframe (e.g., 1d)"
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2025-01-01",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=10000,
        help="Initial balance in USDT"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: data/backtests/)"
    )

    args = parser.parse_args()

    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = project_root / 'data' / 'backtests'

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'fibonacci_2025_{args.symbol}_{timestamp}.json'
    chart_path = output_dir / f'fibonacci_2025_{args.symbol}_{timestamp}.png'
    trades_path = output_dir / f'fibonacci_2025_{args.symbol}_{timestamp}_trades.csv'

    print(f"\n{'='*80}")
    print(f"FIBONACCI GOLDEN ZONE BACKTEST - {args.symbol} {args.timeframe}")
    print(f"{'='*80}\n")

    try:
        # Initialize backtester (uses src/backtesting framework)
        backtester = FibonacciBacktester(initial_balance=args.balance)

        # Fetch historical data
        df = backtester.fetch_historical_data(args.symbol, args.timeframe, args.start)

        # Run backtest
        trades, portfolio_df = backtester.run(df)

        # Calculate metrics using MetricsCalculator
        metrics = MetricsCalculator.calculate(
            trades=trades,
            portfolio_df=portfolio_df,
            initial_balance=args.balance,
            symbol=args.symbol,
            timeframe=args.timeframe,
            strategy_name='Fibonacci Golden Zone'
        )

        # Calculate Buy & Hold baseline using framework
        baseline = BuyAndHoldBaseline()
        buy_hold = baseline.calculate(
            df=df,
            initial_balance=args.balance,
            start_idx=200  # Same warmup as strategy
        )

        # Print results
        print(f"\n{'='*80}")
        print(f"RESULTS - {metrics.start_date} to {metrics.end_date}")
        print(f"{'='*80}\n")

        # Print strategy metrics
        metrics.print_summary()

        # Print baseline comparison
        print_baseline_comparison(
            strategy_metrics=asdict(metrics),
            baseline_metrics=buy_hold
        )

        # Save results
        report = {
            'fibonacci_strategy': asdict(metrics),
            'buy_hold_baseline': buy_hold,
            'outperformance_pct': metrics.total_return_pct - buy_hold['total_return_pct'],
            'trades': [asdict(t) for t in trades]
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to: {report_path}")

        # Save trades to CSV
        if trades:
            import pandas as pd
            trades_df = pd.DataFrame([asdict(t) for t in trades])
            trades_df.to_csv(trades_path, index=False)
            print(f"Trades saved to: {trades_path}")

        # Create comparison chart using framework visualizer
        visualizer = BacktestVisualizer()
        visualizer.create_comparison_chart(
            portfolio_df=portfolio_df,
            price_df=df,
            baseline_metrics=buy_hold,
            strategy_name='Fibonacci Golden Zone',
            output_path=str(chart_path)
        )

        print(f"\n{'='*80}\n")
        print("Backtest complete!")

    except Exception as e:
        print(f"\nError during backtest: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
