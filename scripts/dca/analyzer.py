"""
DCA Analyzer - Performance analysis module.

This module calculates strategy metrics and compares with baselines.

SOLID Principles:
- Single Responsibility: Only performance calculation
- Open/Closed: Can add new metrics without modifying existing
"""

import pandas as pd
from typing import Dict, List
from .strategy import DCASmartStrategy


class DCAAnalyzer:
    """
    Analyze DCA strategy performance.

    Calculates metrics and compares with baseline strategies.
    """

    def __init__(self, strategy: DCASmartStrategy, df: pd.DataFrame):
        """
        Initialize analyzer.

        Args:
            strategy: Strategy to analyze
            df: Historical data used in backtest
        """
        self.strategy = strategy
        self.df = df

    def calculate_metrics(self, final_price: float) -> Dict:
        """
        Calculate comprehensive strategy metrics.

        Args:
            final_price: Final asset price

        Returns:
            Dict with all metrics and comparisons
        """
        # Final portfolio
        final_bnb_value = self.strategy.bnb_balance * final_price
        final_portfolio = self.strategy.usdt_balance + final_bnb_value

        # DCA Smart metrics
        total_return_usd = final_portfolio - self.strategy.total_invested
        total_return_pct = (
            (total_return_usd / self.strategy.total_invested) * 100
            if self.strategy.total_invested > 0 else 0
        )

        # Cost basis
        avg_cost = self.strategy.get_cost_basis()

        # Baseline calculations
        bh_return = self._calculate_buy_hold_return(final_price)
        bh_dca_return = self._calculate_buy_hold_dca_return(final_price)
        dca_fixed_return = self._calculate_dca_fixed_return(final_price)

        # Trade statistics
        buy_trades = [t for t in self.strategy.trades if t.type == 'buy']
        sell_trades = [t for t in self.strategy.trades if t.type == 'sell']
        dip_buys = [t for t in buy_trades if t.multiplier >= 2.0]

        return {
            'strategy': 'DCA Smart',
            'period': f"{self.df.index[0].date()} to {self.df.index[-1].date()}",
            'days': len(self.df),

            # Portfolio
            'final_portfolio': final_portfolio,
            'bnb_balance': self.strategy.bnb_balance,
            'bnb_value': final_bnb_value,
            'usdt_balance': self.strategy.usdt_balance,
            'usdt_reserved': self.strategy.usdt_reserved,

            # Investment
            'initial_capital': self.strategy.initial_capital,
            'total_invested': self.strategy.total_invested,
            'avg_cost': avg_cost,
            'final_price': final_price,

            # Returns
            'total_return_usd': total_return_usd,
            'total_return_pct': total_return_pct,

            # Comparisons
            'buy_hold_return_pct': bh_return,
            'buy_hold_dca_return_pct': bh_dca_return,
            'dca_fixed_return_pct': dca_fixed_return,

            # Trades
            'total_trades': len(self.strategy.trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'dip_buys': len(dip_buys),
            'ath_sells': len(sell_trades),
            'total_profit_taken': self.strategy.total_profit_taken,

            # Top events
            'top_dip_buys': self._get_top_dip_buys(dip_buys),
            'top_ath_sells': self._get_top_sells(sell_trades)
        }

    def _calculate_buy_hold_return(self, final_price: float) -> float:
        """
        Calculate Buy & Hold return (invest everything at start).

        Args:
            final_price: Final price

        Returns:
            Return percentage
        """
        first_price = self.df['close'].iloc[0]
        bh_quantity = self.strategy.initial_capital / first_price
        bh_final = bh_quantity * final_price
        return ((bh_final - self.strategy.initial_capital) / self.strategy.initial_capital) * 100

    def _calculate_buy_hold_dca_return(self, final_price: float) -> float:
        """
        Calculate Buy & Hold + Weekly DCA return.

        Args:
            final_price: Final price

        Returns:
            Return percentage
        """
        first_price = self.df['close'].iloc[0]
        weeks = len([t for t in self.strategy.trades if t.type == 'buy'])
        bh_dca_invested = self.strategy.initial_capital + (weeks * self.strategy.weekly_investment)
        bh_dca_quantity = self.strategy.initial_capital / first_price

        for i, (timestamp, row) in enumerate(self.df.iterrows()):
            if i > 0 and timestamp.weekday() == self.strategy.purchase_day:
                week_num = timestamp.isocalendar()[1]
                if i == 0 or self.df.index[i-1].isocalendar()[1] != week_num:
                    bh_dca_quantity += self.strategy.weekly_investment / row['close']

        bh_dca_final = bh_dca_quantity * final_price
        return ((bh_dca_final - bh_dca_invested) / bh_dca_invested) * 100

    def _calculate_dca_fixed_return(self, final_price: float) -> float:
        """
        Calculate DCA Fixed return (no adjustments).

        Args:
            final_price: Final price

        Returns:
            Return percentage
        """
        dca_fixed_invested = self.strategy.initial_capital
        dca_fixed_quantity = 0

        for i, (timestamp, row) in enumerate(self.df.iterrows()):
            if timestamp.weekday() == self.strategy.purchase_day:
                week_num = timestamp.isocalendar()[1]
                if i == 0 or self.df.index[i-1].isocalendar()[1] != week_num:
                    if dca_fixed_invested >= self.strategy.weekly_investment:
                        dca_fixed_quantity += self.strategy.weekly_investment / row['close']
                        dca_fixed_invested += self.strategy.weekly_investment

        dca_fixed_final = dca_fixed_quantity * final_price
        return ((dca_fixed_final - dca_fixed_invested) / dca_fixed_invested) * 100

    def _get_top_dip_buys(self, dip_buys: List, top_n: int = 5) -> List[Dict]:
        """
        Get top dip buying opportunities.

        Args:
            dip_buys: List of dip buy trades
            top_n: Number of top buys to return

        Returns:
            List of trade dicts
        """
        return [
            {
                'date': t.date,
                'price': t.price,
                'amount': t.amount_usd,
                'rsi': t.rsi,
                'multiplier': t.multiplier,
                'reason': t.reason
            }
            for t in sorted(dip_buys, key=lambda x: x.multiplier, reverse=True)[:top_n]
        ]

    def _get_top_sells(self, sell_trades: List, top_n: int = 5) -> List[Dict]:
        """
        Get top profit-taking sells.

        Args:
            sell_trades: List of sell trades
            top_n: Number of top sells to return

        Returns:
            List of trade dicts
        """
        return [
            {
                'date': t.date,
                'price': t.price,
                'amount': t.amount_usd,
                'quantity': t.quantity,
                'reason': t.reason
            }
            for t in sell_trades[:top_n]
        ]

    def print_detailed_report(self, results: Dict) -> None:
        """
        Print detailed analysis report.

        Args:
            results: Results dict from calculate_metrics()
        """
        print(f"\n{'='*80}")
        print(f"DCA SMART STRATEGY - DETAILED REPORT")
        print(f"{'='*80}\n")

        print(f"SIMULATION PERIOD")
        print(f"  Period: {results['period']}")
        print(f"  Days: {results['days']}\n")

        print(f"FINAL PORTFOLIO")
        print(f"  Total Value:        ${results['final_portfolio']:,.2f}")
        print(f"  BNB Holdings:       {results['bnb_balance']:.6f} BNB")
        print(f"  BNB Value:          ${results['bnb_value']:,.2f}")
        print(f"  USDT Balance:       ${results['usdt_balance']:,.2f}")
        print(f"  Reserved (Profits): ${results['usdt_reserved']:,.2f}\n")

        print(f"INVESTMENT")
        print(f"  Initial Capital:    ${results['initial_capital']:,.2f}")
        print(f"  Total Invested:     ${results['total_invested']:,.2f}")
        print(f"  Average Cost:       ${results['avg_cost']:.2f}")
        print(f"  Final Price:        ${results['final_price']:.2f}")
        print(f"  Price Change:       {((results['final_price']/results['avg_cost'])-1)*100:+.2f}%\n")

        print(f"PERFORMANCE COMPARISON")
        print(f"  {'Strategy':<20} {'Return':<15} {'Alpha vs B&H':<15}")
        print(f"  {'-'*50}")
        alpha_bh = results['total_return_pct'] - results['buy_hold_return_pct']
        print(f"  {'DCA Smart':<20} {results['total_return_pct']:>12.2f}%   {alpha_bh:>12.2f}%")
        print(f"  {'Buy & Hold':<20} {results['buy_hold_return_pct']:>12.2f}%   {'--':>12}")
        alpha_bh_dca = results['buy_hold_dca_return_pct'] - results['buy_hold_return_pct']
        print(f"  {'B&H + DCA':<20} {results['buy_hold_dca_return_pct']:>12.2f}%   {alpha_bh_dca:>12.2f}%")
        alpha_fixed = results['dca_fixed_return_pct'] - results['buy_hold_return_pct']
        print(f"  {'DCA Fixed':<20} {results['dca_fixed_return_pct']:>12.2f}%   {alpha_fixed:>12.2f}%\n")

        print(f"TRADING ACTIVITY")
        print(f"  Total Trades:       {results['total_trades']}")
        print(f"  Buy Trades:         {results['buy_trades']}")
        print(f"  Dip Buys (2x+):     {results['dip_buys']}")
        print(f"  Profit Sells:       {results['sell_trades']}")
        print(f"  Total Profit Taken: ${results['total_profit_taken']:,.2f}\n")

        # Top dip buys
        if results['top_dip_buys']:
            print(f"TOP DIP BUYS (Highest Multipliers)")
            print(f"  {'Date':<12} {'Price':<12} {'Amount':<12} {'RSI':<8} {'Multiplier':<12}")
            print(f"  {'-'*70}")
            for buy in results['top_dip_buys'][:5]:
                print(f"  {buy['date']:<12} ${buy['price']:<11.2f} ${buy['amount']:<11.2f} "
                      f"{buy['rsi']:<7.1f} {buy['multiplier']:.1f}x")
            print()

        # ATH sells
        if results['top_ath_sells']:
            print(f"PROFIT TAKING EVENTS (ATH)")
            print(f"  {'Date':<12} {'Price':<12} {'Amount':<12} {'Quantity':<12}")
            print(f"  {'-'*70}")
            for sell in results['top_ath_sells']:
                print(f"  {sell['date']:<12} ${sell['price']:<11.2f} ${sell['amount']:<11.2f} "
                      f"{sell['quantity']:.4f} BNB")
            print()

        # Verdict
        print(f"VERDICT")
        if results['total_return_pct'] > results['buy_hold_return_pct']:
            print(f"  ✅ DCA SMART WINS!")
            print(f"  Outperformed Buy & Hold by {alpha_bh:+.2f}%")
        else:
            print(f"  ❌ Buy & Hold wins")
            print(f"  DCA Smart underperformed by {alpha_bh:+.2f}%")

        print(f"\n{'='*80}\n")
