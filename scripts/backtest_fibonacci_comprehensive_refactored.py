#!/usr/bin/env python3
"""
Comprehensive Fibonacci Golden Zone Strategy Backtest (Refactored)

This is the refactored version using modular architecture from src/backtesting/.

Executes detailed backtesting comparing:
1. Fibonacci Golden Zone Strategy
2. Buy & Hold baseline

Features:
- 2-year historical analysis (Nov 2023 - Nov 2025)
- Quarterly performance breakdown
- Detailed trade analysis
- Visual comparisons
- Risk metrics (Sharpe, Max Drawdown, Win Rate, etc.)
- Market condition analysis

Usage:
    python scripts/backtest_fibonacci_comprehensive_refactored.py --symbol BNB_USDT --timeframe 4h --balance 5000

Architecture:
    Uses modular components from src/backtesting/:
    - FibonacciBacktester: Strategy + data fetching
    - MetricsCalculator: Performance metrics
    - BuyAndHoldBaseline: Baseline comparison
    - BacktestVisualizer: Chart generation
    - Models: Trade and BacktestMetrics dataclasses
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

from src.backtesting import (
    FibonacciBacktester,
    MetricsCalculator,
    BuyAndHoldBaseline,
    BacktestVisualizer,
    print_baseline_comparison
)


def print_executive_summary(metrics, buy_hold_dict, trades):
    """
    Print executive summary comparing strategy vs baseline.

    Args:
        metrics: BacktestMetrics object
        buy_hold_dict: Buy & Hold baseline metrics dict
        trades: List of Trade objects
    """
    print("\n" + "="*80)
    print(" EXECUTIVE SUMMARY")
    print("="*80)

    outperformance = metrics.total_return_pct - buy_hold_dict['total_return_pct']
    winner = "FIBONACCI WINS" if outperformance > 0 else "BUY & HOLD WINS"

    print(f"\n Winner: {winner}")
    print(f" Outperformance: {outperformance:+.2f}%")
    print(f"\n Period: {metrics.start_date} to {metrics.end_date}")
    print(f" Initial Capital: ${metrics.initial_balance:,.2f}")

    print(f"\n {'Metric':<30} {'Fibonacci':<20} {'Buy & Hold':<20}")
    print(" " + "-"*70)
    print(f" {'Final Balance':<30} ${metrics.final_balance:>18,.2f} ${buy_hold_dict['final_balance']:>18,.2f}")
    print(f" {'Total Return':<30} {metrics.total_return_pct:>17.2f}% {buy_hold_dict['total_return_pct']:>17.2f}%")
    print(f" {'Annualized Return':<30} {metrics.annualized_return_pct:>17.2f}% {buy_hold_dict['annualized_return_pct']:>17.2f}%")
    print(f" {'Max Drawdown':<30} {metrics.max_drawdown_pct:>17.2f}% {buy_hold_dict['max_drawdown_pct']:>17.2f}%")
    print(f" {'Sharpe Ratio':<30} {metrics.sharpe_ratio:>19.2f} {'N/A':>20}")
    print(f" {'Win Rate':<30} {metrics.win_rate_pct:>17.2f}% {'N/A':>20}")
    print(f" {'Profit Factor':<30} {metrics.profit_factor:>19.2f} {'N/A':>20}")
    print(f" {'Total Trades':<30} {metrics.total_trades:>19} {'1':>20}")

    print("\n" + "="*80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Fibonacci Golden Zone backtest (Refactored)"
    )
    parser.add_argument("--symbol", type=str, default="BNB_USDT", help="Trading pair")
    parser.add_argument("--timeframe", type=str, default="4h", help="Candle timeframe")
    parser.add_argument("--start", type=str, default="2023-11-01", help="Start date")
    parser.add_argument("--balance", type=float, default=5000, help="Initial balance")
    parser.add_argument("--output", type=str, default=None, help="Output directory")

    args = parser.parse_args()

    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = project_root / 'data' / 'backtests'

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'fibonacci_comprehensive_{args.symbol}_{timestamp}.json'
    chart_path = output_dir / f'fibonacci_comprehensive_{args.symbol}_{timestamp}.png'
    trades_path = output_dir / f'fibonacci_trades_{args.symbol}_{timestamp}.csv'
    periods_path = output_dir / f'fibonacci_periods_{args.symbol}_{timestamp}.csv'

    print("\n" + "="*80)
    print(f" FIBONACCI GOLDEN ZONE - COMPREHENSIVE BACKTEST (REFACTORED)")
    print("="*80)
    print(f"\n Symbol: {args.symbol}")
    print(f" Timeframe: {args.timeframe}")
    print(f" Start Date: {args.start}")
    print(f" Initial Balance: ${args.balance:,.2f}")
    print(f"\n Output Directory: {output_dir}")

    try:
        # 1. Initialize backtester
        backtester = FibonacciBacktester(initial_balance=args.balance)

        # 2. Fetch historical data
        df = backtester.fetch_historical_data(args.symbol, args.timeframe, args.start)

        # 3. Run backtest
        trades, portfolio_df = backtester.run(df)

        # 4. Calculate metrics
        print("\nCalculating metrics...")
        metrics = MetricsCalculator.calculate(
            trades=trades,
            portfolio_df=portfolio_df,
            initial_balance=args.balance,
            symbol=args.symbol,
            timeframe=args.timeframe,
            strategy_name='Fibonacci Golden Zone'
        )

        # 5. Calculate Buy & Hold baseline
        print("Calculating Buy & Hold baseline...")
        baseline = BuyAndHoldBaseline()
        buy_hold_dict = baseline.calculate(df, args.balance, start_idx=200)

        # 6. Period analysis
        print("Analyzing by period...")
        periods_df = MetricsCalculator.analyze_by_period(trades, portfolio_df, period='Q')

        # 7. Print results
        print_executive_summary(metrics, buy_hold_dict, trades)

        print("\n" + "="*80)
        print(" DETAILED METRICS - FIBONACCI STRATEGY")
        print("="*80)
        print(f"\n Trades: {metrics.total_trades} ({metrics.winning_trades}W / {metrics.losing_trades}L)")
        print(f" Win Rate: {metrics.win_rate_pct:.2f}%")
        print(f" Profit Factor: {metrics.profit_factor:.2f}")
        print(f" Average Win: {metrics.average_win_pct:+.2f}%")
        print(f" Average Loss: {metrics.average_loss_pct:.2f}%")
        print(f" Best Trade: {metrics.best_trade_pct:+.2f}%")
        print(f" Worst Trade: {metrics.worst_trade_pct:.2f}%")
        print(f" Longest Win Streak: {metrics.longest_win_streak}")
        print(f" Longest Loss Streak: {metrics.longest_loss_streak}")
        print(f" Avg Trade Duration: {metrics.avg_trade_duration_hours:.1f} hours")
        print(f" Time in Market: {metrics.time_in_market_pct:.1f}%")

        print("\n" + "="*80)
        print(" QUARTERLY PERFORMANCE")
        print("="*80)
        print(periods_df.to_string(index=False))

        # 8. Save results
        print("\n" + "="*80)
        print(" SAVING RESULTS")
        print("="*80)

        # Save comprehensive report
        report = {
            'fibonacci_strategy': asdict(metrics),
            'buy_hold_baseline': buy_hold_dict,
            'outperformance_pct': metrics.total_return_pct - buy_hold_dict['total_return_pct'],
            'quarterly_performance': periods_df.to_dict('records'),
            'trades': [trade.to_dict() for trade in trades],
            'parameters': {
                'symbol': args.symbol,
                'timeframe': args.timeframe,
                'start_date': args.start,
                'initial_balance': args.balance
            }
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f" Report: {report_path}")

        # Save trades CSV
        if trades:
            import pandas as pd
            trades_df = pd.DataFrame([trade.to_dict() for trade in trades])
            trades_df.to_csv(trades_path, index=False)
            print(f" Trades: {trades_path}")

        # Save periods CSV
        periods_df.to_csv(periods_path, index=False)
        print(f" Periods: {periods_path}")

        # 9. Generate visualization
        print("\nGenerating comprehensive chart...")
        visualizer = BacktestVisualizer()
        visualizer.create_comprehensive_chart(
            portfolio_df=portfolio_df,
            price_df=df,
            trades=trades,
            baseline_dict=buy_hold_dict,
            initial_balance=args.balance,
            output_path=str(chart_path),
            symbol=args.symbol,
            strategy_name='Fibonacci Golden Zone'
        )

        print("\n" + "="*80)
        print(" BACKTEST COMPLETE!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
