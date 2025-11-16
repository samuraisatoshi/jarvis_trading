#!/usr/bin/env python3
"""
Master Script: Testa TODAS as 3 Estratégias Vencedoras

Executa backtests completos de:
1. Trend Following (Swing Trade) - Timeframe 4H
2. Momentum Day Trade - Timeframe 15min
3. DCA Intelligent - Timeframe 1D

Compara todas contra Buy & Hold baseline e gera relatório executivo.

Critérios de Aprovação:
- Trend Following: Alpha > 10% vs Buy & Hold
- Momentum Day Trade: Win Rate > 55% AND Sharpe > 1.5
- DCA Intelligent: Alpha > 10% vs Buy & Hold

Usage:
    python scripts/test_all_strategies.py --symbol BNB_USDT
    python scripts/test_all_strategies.py --symbol BNB_USDT --data-dir data/2025
"""

import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import strategies
from trend_following_strategy import TrendFollowingStrategy
from momentum_day_trade import MomentumDayTradeStrategy
from dca_intelligent import DCAIntelligentStrategy


class StrategyComparison:
    """Compara múltiplas estratégias."""

    def __init__(self, symbol: str = "BNB_USDT", data_dir: str = "data/2025"):
        """Inicializa comparador."""
        self.symbol = symbol
        self.data_dir = Path(data_dir)
        self.initial_balance = 5000.0

        # Resultados
        self.results: Dict[str, Dict] = {}

    def load_data(self, timeframe: str) -> pd.DataFrame:
        """
        Carrega dados para timeframe específico.

        Args:
            timeframe: '4h', '1h', '15min', '1d'

        Returns:
            DataFrame com OHLCV
        """
        # Mapeia timeframe para arquivo
        timeframe_map = {
            '4h': '4h',
            '1h': '1h',
            '15min': '15min',
            '1d': '1d'
        }

        tf = timeframe_map.get(timeframe, timeframe)
        filepath = self.data_dir / f"{self.symbol}_{tf}_2025.csv"

        if not filepath.exists():
            print(f"⚠️  Data file not found: {filepath}")
            print(f"    Looking for alternative...")

            # Tenta variações
            alternatives = [
                self.data_dir / f"{self.symbol.replace('_', '')}_{tf}_2025.csv",
                self.data_dir / f"{self.symbol}_{tf}.csv",
            ]

            for alt in alternatives:
                if alt.exists():
                    filepath = alt
                    print(f"    Found: {filepath}")
                    break
            else:
                raise FileNotFoundError(f"Could not find data file for {self.symbol} {timeframe}")

        print(f"Loading {filepath.name}...")
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        print(f"  Loaded {len(df)} candles\n")
        return df

    def test_trend_following(self) -> Dict:
        """Testa estratégia Trend Following."""
        print("\n" + "="*80)
        print("TESTING STRATEGY 1: Trend Following (Swing Trade)")
        print("="*80 + "\n")

        try:
            df = self.load_data('4h')
            strategy = TrendFollowingStrategy(initial_balance=self.initial_balance)
            metrics = strategy.backtest(df, symbol=self.symbol)
            self.results['trend_following'] = metrics
            return metrics
        except Exception as e:
            print(f"❌ Error testing Trend Following: {e}\n")
            return {}

    def test_momentum_day_trade(self) -> Dict:
        """Testa estratégia Momentum Day Trade."""
        print("\n" + "="*80)
        print("TESTING STRATEGY 2: Momentum Day Trade")
        print("="*80 + "\n")

        # Tenta 15min, fallback para 1h
        for timeframe in ['15min', '1h']:
            try:
                df = self.load_data(timeframe)
                strategy = MomentumDayTradeStrategy(initial_balance=self.initial_balance)
                metrics = strategy.backtest(df, symbol=self.symbol)
                self.results['momentum_day_trade'] = metrics
                return metrics
            except FileNotFoundError:
                if timeframe == '1h':
                    print(f"❌ Error: No 15min or 1h data available\n")
                    return {}
                continue
            except Exception as e:
                print(f"❌ Error testing Momentum Day Trade: {e}\n")
                return {}

    def test_dca_intelligent(self) -> Dict:
        """Testa estratégia DCA Intelligent."""
        print("\n" + "="*80)
        print("TESTING STRATEGY 3: DCA Intelligent")
        print("="*80 + "\n")

        try:
            df = self.load_data('1d')
            strategy = DCAIntelligentStrategy(
                initial_balance=self.initial_balance,
                weekly_amount=100.0
            )
            metrics = strategy.backtest(df, symbol=self.symbol)
            self.results['dca_intelligent'] = metrics
            return metrics
        except Exception as e:
            print(f"❌ Error testing DCA Intelligent: {e}\n")
            return {}

    def generate_report(self) -> str:
        """Gera relatório executivo comparativo."""
        report = []
        report.append("\n" + "="*80)
        report.append("EXECUTIVE REPORT: WINNING STRATEGIES")
        report.append("="*80 + "\n")
        report.append(f"Symbol: {self.symbol}")
        report.append(f"Initial Balance: ${self.initial_balance:,.2f}")
        report.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Buy & Hold baseline
        if 'trend_following' in self.results and self.results['trend_following']:
            bh_return = self.results['trend_following'].get('buy_hold_return_pct', 0)
            bh_balance = self.initial_balance * (1 + bh_return / 100)
            report.append(f"Buy & Hold Baseline: {bh_return:+.2f}% (${bh_balance:,.2f})\n")

        report.append("-"*80)
        report.append("STRATEGY COMPARISON")
        report.append("-"*80 + "\n")

        # Tabela comparativa
        strategies = [
            ('trend_following', 'Trend Following', 'alpha'),
            ('momentum_day_trade', 'Momentum Day Trade', 'win_rate_pct'),
            ('dca_intelligent', 'DCA Intelligent', 'alpha_vs_buy_hold')
        ]

        approved = []
        marginal = []
        rejected = []

        for key, name, metric_key in strategies:
            if key not in self.results or not self.results[key]:
                report.append(f"{name}:")
                report.append(f"  ❌ FAILED - Could not test\n")
                rejected.append(name)
                continue

            metrics = self.results[key]
            report.append(f"{name}:")
            report.append(f"  Return:          {metrics.get('total_return_pct', 0):+.2f}%")
            report.append(f"  Final Balance:   ${metrics.get('final_balance', metrics.get('final_value', 0)):,.2f}")

            # Critérios específicos
            if key == 'trend_following':
                alpha = metrics.get('alpha', 0)
                sharpe = metrics.get('sharpe_ratio', 0)
                report.append(f"  Alpha (vs B&H):  {alpha:+.2f}%")
                report.append(f"  Sharpe Ratio:    {sharpe:.2f}")

                if alpha >= 10:
                    report.append(f"  ✅ APPROVED - Alpha {alpha:+.2f}% > 10%")
                    approved.append(name)
                elif alpha >= 0:
                    report.append(f"  ⚠️  MARGINAL - Alpha {alpha:+.2f}% positive but < 10%")
                    marginal.append(name)
                else:
                    report.append(f"  ❌ REJECTED - Alpha {alpha:+.2f}% negative")
                    rejected.append(name)

            elif key == 'momentum_day_trade':
                win_rate = metrics.get('win_rate_pct', 0)
                sharpe = metrics.get('sharpe_ratio', 0)
                trades = metrics.get('total_trades', 0)
                report.append(f"  Win Rate:        {win_rate:.1f}%")
                report.append(f"  Sharpe Ratio:    {sharpe:.2f}")
                report.append(f"  Total Trades:    {trades}")

                if win_rate >= 55 and sharpe >= 1.5:
                    report.append(f"  ✅ APPROVED - Win Rate {win_rate:.1f}% > 55% AND Sharpe {sharpe:.2f} > 1.5")
                    approved.append(name)
                elif win_rate >= 55 or sharpe >= 1.5:
                    report.append(f"  ⚠️  MARGINAL - Win Rate OR Sharpe meets threshold")
                    marginal.append(name)
                else:
                    report.append(f"  ❌ REJECTED - Win Rate {win_rate:.1f}% < 55% AND Sharpe {sharpe:.2f} < 1.5")
                    rejected.append(name)

            elif key == 'dca_intelligent':
                alpha_bh = metrics.get('alpha_vs_buy_hold', 0)
                alpha_dca = metrics.get('alpha_vs_dca_pure', 0)
                report.append(f"  Alpha (vs B&H):  {alpha_bh:+.2f}%")
                report.append(f"  Alpha (vs DCA):  {alpha_dca:+.2f}%")
                report.append(f"  Total Invested:  ${metrics.get('total_invested', 0):,.2f}")

                if alpha_bh >= 10:
                    report.append(f"  ✅ APPROVED - Alpha vs B&H {alpha_bh:+.2f}% > 10%")
                    approved.append(name)
                elif alpha_bh >= 0:
                    report.append(f"  ⚠️  MARGINAL - Alpha vs B&H {alpha_bh:+.2f}% positive but < 10%")
                    marginal.append(name)
                else:
                    report.append(f"  ❌ REJECTED - Alpha vs B&H {alpha_bh:+.2f}% negative")
                    rejected.append(name)

            report.append("")

        # Resumo final
        report.append("-"*80)
        report.append("FINAL VERDICT")
        report.append("-"*80 + "\n")
        report.append(f"✅ APPROVED:  {len(approved)} strategies - {', '.join(approved) if approved else 'None'}")
        report.append(f"⚠️  MARGINAL: {len(marginal)} strategies - {', '.join(marginal) if marginal else 'None'}")
        report.append(f"❌ REJECTED:  {len(rejected)} strategies - {', '.join(rejected) if rejected else 'None'}\n")

        if approved:
            report.append("RECOMMENDATION:")
            report.append(f"  Deploy approved strategies: {', '.join(approved)}")
            report.append(f"  Expected performance: Better than Buy & Hold baseline")
        elif marginal:
            report.append("RECOMMENDATION:")
            report.append(f"  Consider marginal strategies with caution: {', '.join(marginal)}")
            report.append(f"  Monitor closely for performance degradation")
        else:
            report.append("RECOMMENDATION:")
            report.append(f"  ⚠️  NO STRATEGIES APPROVED - Stick with Buy & Hold")
            report.append(f"  All tested strategies failed to beat baseline")

        report.append("\n" + "="*80 + "\n")

        return "\n".join(report)

    def save_results(self, output_dir: str = "data/backtests/winning_strategies"):
        """Salva resultados em arquivos."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save JSON results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = output_path / f"winning_strategies_{self.symbol}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to {json_file}")

        # Save report
        report = self.generate_report()
        report_file = output_path / f"winning_strategies_report_{self.symbol}_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"Report saved to {report_file}")

        return report


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Test All Winning Strategies')
    parser.add_argument('--symbol', type=str, default='BNB_USDT', help='Trading symbol')
    parser.add_argument('--data-dir', type=str, default='data/2025', help='Data directory')
    parser.add_argument('--output-dir', type=str, default='data/backtests/winning_strategies', help='Output directory')

    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"WINNING STRATEGIES BACKTEST - {args.symbol}")
    print(f"{'='*80}\n")
    print(f"Based on learnings from previous backtests:")
    print(f"  ✅ Buy & Hold beat all complex strategies")
    print(f"  ✅ Simplicity wins")
    print(f"  ✅ Follow trends, don't fight them")
    print(f"  ❌ Fibonacci Golden Zone: -4.6% (REJECTED)")
    print(f"  ❌ ML models with bugs: Only buy, never sell")
    print(f"\nTesting 3 SIMPLE winning strategies...\n")

    # Run tests
    comparison = StrategyComparison(symbol=args.symbol, data_dir=args.data_dir)

    comparison.test_trend_following()
    comparison.test_momentum_day_trade()
    comparison.test_dca_intelligent()

    # Generate and print report
    report = comparison.save_results(output_dir=args.output_dir)
    print(report)

    # Exit code: 0 if at least one strategy approved
    approved_count = sum([
        1 for key, metrics in comparison.results.items()
        if metrics and (
            (key == 'trend_following' and metrics.get('alpha', 0) >= 10) or
            (key == 'momentum_day_trade' and metrics.get('win_rate_pct', 0) >= 55 and metrics.get('sharpe_ratio', 0) >= 1.5) or
            (key == 'dca_intelligent' and metrics.get('alpha_vs_buy_hold', 0) >= 10)
        )
    ])

    return 0 if approved_count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
