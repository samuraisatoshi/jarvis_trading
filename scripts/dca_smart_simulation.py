#!/usr/bin/env python3
"""
DCA SMART SIMULATION - Refactored Entry Point

Simulates a sophisticated DCA strategy using clean, modular architecture.

Key Features:
1. Adjusts weekly investments based on RSI (buys more in dips)
2. Takes profits at ATH (All-Time Highs)
3. Rebuys during crashes with reserved profits
4. Compares performance against simple strategies

Period: 2 years (Nov 2023 - Nov 2025)
Capital: $5,000 initial + $200/week
Asset: BNB/USDT

Architecture:
- Strategy Pattern for trading logic
- Dependency Injection throughout
- Separation of Concerns (Strategy, Simulator, Analyzer, Visualizer)
- SOLID principles applied

Module Structure:
- dca/strategy.py: Strategy implementation
- dca/simulator.py: Backtest execution
- dca/analyzer.py: Performance analysis
- dca/visualizer.py: Chart generation
"""

import sys
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import warnings

warnings.filterwarnings('ignore')

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import refactored modules
from scripts.dca import (
    DCASmartStrategy,
    DCASimulator,
    DCAAnalyzer,
    DCAVisualizer
)
from scripts.dca.simulator import DataProvider


def save_results(
    strategy: DCASmartStrategy,
    results: dict,
    output_dir: Path
) -> None:
    """
    Save results to various formats.

    Args:
        strategy: Strategy instance
        results: Results dictionary
        output_dir: Output directory
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save results JSON
    results_file = output_dir / 'dca_smart_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved: {results_file}")

    # Save trades CSV
    trades_file = output_dir / 'dca_smart_trades.csv'
    trades_df = pd.DataFrame([t.to_dict() for t in strategy.trades])
    trades_df.to_csv(trades_file, index=False)
    print(f"Trades saved: {trades_file}")


def generate_markdown_report(results: dict, output_path: Path) -> None:
    """
    Generate markdown analysis report.

    Args:
        results: Results dictionary
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(f"""# DCA Smart Strategy - Analysis Report

## Executive Summary

**Period:** {results['period']}
**Days Simulated:** {results['days']}

### Performance

| Metric | Value |
|--------|-------|
| Initial Capital | ${results['initial_capital']:,.2f} |
| Total Invested | ${results['total_invested']:,.2f} |
| Final Portfolio Value | ${results['final_portfolio']:,.2f} |
| Total Return | {results['total_return_pct']:.2f}% (${results['total_return_usd']:,.2f}) |

### Strategy Comparison

| Strategy | Return | Alpha vs B&H |
|----------|--------|--------------|
| **DCA Smart** | **{results['total_return_pct']:.2f}%** | **{results['total_return_pct'] - results['buy_hold_return_pct']:+.2f}%** |
| Buy & Hold | {results['buy_hold_return_pct']:.2f}% | -- |
| B&H + DCA | {results['buy_hold_dca_return_pct']:.2f}% | {results['buy_hold_dca_return_pct'] - results['buy_hold_return_pct']:+.2f}% |
| DCA Fixed | {results['dca_fixed_return_pct']:.2f}% | {results['dca_fixed_return_pct'] - results['buy_hold_return_pct']:+.2f}% |

### Trading Statistics

- **Total Trades:** {results['total_trades']}
- **Buy Trades:** {results['buy_trades']}
- **Dip Buys (2x+ multiplier):** {results['dip_buys']}
- **Profit Taking Sells:** {results['sell_trades']}
- **Total Profit Taken:** ${results['total_profit_taken']:,.2f}

### Final Holdings

- **BNB:** {results['bnb_balance']:.6f} (${results['bnb_value']:,.2f})
- **USDT:** ${results['usdt_balance']:,.2f}
- **Reserved (Profits):** ${results['usdt_reserved']:,.2f}
- **Average Cost:** ${results['avg_cost']:.2f}
- **Final Price:** ${results['final_price']:.2f}

## Verdict

{'✅ **DCA SMART WINS!**' if results['total_return_pct'] > results['buy_hold_return_pct'] else '❌ **Buy & Hold wins**'}

**Alpha:** {results['total_return_pct'] - results['buy_hold_return_pct']:+.2f}%

## Strategy Rules

### 1. Weekly DCA with RSI Adjustments

Base investment: $200/week (every Monday)

**Multipliers:**
- RSI < 30: 3x ($600) - Extreme oversold
- RSI < 40: 2x ($400) - Oversold
- RSI < 50: 1.5x ($300) - Neutral-low
- RSI < 60: 1x ($200) - Neutral
- RSI < 70: 0.5x ($100) - Neutral-high
- RSI ≥ 70: 0.25x ($50) - Overbought

**Distance from SMA200:**
- 20% below: +50% multiplier
- 30% above: -50% multiplier

### 2. Profit Taking at ATH

When price ≥ 98% of ATH:

- Profit > 100%: Sell 25%
- Profit > 75%: Sell 20%
- Profit > 50%: Sell 15%
- Profit > 30%: Sell 10%

Reserve proceeds for rebuying dips.

### 3. Crash Rebuying

Use 50% of reserved profits when:
- RSI < 25 (panic), OR
- Price -30% from ATH (crash)

## Visualization

![DCA Smart Analysis](../data/backtests/dca_smart_analysis.png)

## Conclusion

{'The DCA Smart strategy successfully outperformed simple Buy & Hold by intelligently timing purchases during dips (RSI-based) and taking profits at peaks (ATH-based). The strategy demonstrates that active management with clear rules can add value over passive strategies.' if results['total_return_pct'] > results['buy_hold_return_pct'] else 'While DCA Smart underperformed Buy & Hold in this period, it provided better risk management through profit-taking and maintained cash reserves. Performance may vary significantly based on market conditions.'}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")

    print(f"Report saved: {output_path}")


def main() -> int:
    """Main execution with clean architecture."""
    parser = argparse.ArgumentParser(description='DCA Smart Simulation (Refactored)')
    parser.add_argument('--symbol', default='BNB/USDT', help='Trading pair')
    parser.add_argument('--start-date', default='2023-11-01', help='Start date')
    parser.add_argument('--initial-capital', type=float, default=5000, help='Initial capital')
    parser.add_argument('--weekly-investment', type=float, default=200, help='Weekly investment')
    parser.add_argument('--download', action='store_true', help='Download fresh data')
    parser.add_argument('--data-file', help='Use existing CSV file')

    args = parser.parse_args()

    # Data handling
    if args.data_file:
        print(f"Loading data from {args.data_file}...")
        df = pd.read_csv(args.data_file, index_col=0, parse_dates=True)
    else:
        if args.download:
            df = DataProvider.download_historical_data(
                symbol=args.symbol,
                start_date=args.start_date
            )

            # Save
            data_dir = Path(__file__).parent.parent / 'data' / 'historical'
            data_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{args.symbol.replace('/', '_')}_1d_historical.csv"
            filepath = data_dir / filename
            df.to_csv(filepath)
            print(f"Data saved: {filepath}")
        else:
            print("Error: Must provide --data-file or use --download")
            return 1

    print(f"Data loaded: {len(df)} candles from {df.index[0].date()} to {df.index[-1].date()}")

    # Create strategy (Dependency Injection)
    strategy = DCASmartStrategy(
        initial_capital=args.initial_capital,
        weekly_investment=args.weekly_investment
    )

    # Create simulator and run backtest
    simulator = DCASimulator(strategy)
    results = simulator.backtest(df, verbose=True)

    # Create analyzer and print report
    analyzer = DCAAnalyzer(strategy, df)
    analyzer.print_detailed_report(results)

    # Create visualizer and generate charts
    output_dir = Path(__file__).parent.parent / 'data' / 'backtests'
    visualizer = DCAVisualizer(strategy, df, results)
    output_path = output_dir / 'dca_smart_analysis.png'
    visualizer.create_comprehensive_chart(output_path)

    # Save results
    save_results(strategy, results, output_dir)

    # Generate markdown report
    report_file = Path(__file__).parent.parent / 'reports' / 'DCA_SMART_ANALYSIS.md'
    generate_markdown_report(results, report_file)

    return 0


if __name__ == '__main__':
    sys.exit(main())
