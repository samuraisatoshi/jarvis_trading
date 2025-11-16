#!/usr/bin/env python3
"""
DCA SMART SIMULATION - Intelligent Dollar Cost Averaging Strategy

Simulates a sophisticated DCA strategy that:
1. Adjusts weekly investments based on RSI (buys more in dips)
2. Takes profits at ATH (All-Time Highs)
3. Rebuys during crashes with reserved profits
4. Compares performance against simple strategies

Period: 2 years (Nov 2023 - Nov 2025)
Capital: $5,000 initial + $200/week
Asset: BNB/USDT
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import json
import warnings

warnings.filterwarnings('ignore')

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

# Styling
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (16, 10)


@dataclass
class Trade:
    """Trade record."""
    date: str
    type: str  # 'buy', 'sell', 'rebalance'
    price: float
    quantity: float
    amount_usd: float
    rsi: float
    reason: str
    portfolio_value: float
    bnb_balance: float
    usdt_balance: float
    multiplier: float = 1.0


class DCASmartStrategy:
    """
    Intelligent DCA Strategy with:
    - RSI-based purchase adjustments
    - ATH profit-taking
    - Crash rebuying with reserves
    """

    def __init__(
        self,
        initial_capital: float = 5000.0,
        weekly_investment: float = 200.0,
        purchase_day: int = 0  # Monday
    ):
        """Initialize strategy."""
        self.initial_capital = initial_capital
        self.weekly_investment = weekly_investment
        self.purchase_day = purchase_day

        # Portfolio
        self.usdt_balance = initial_capital
        self.bnb_balance = 0.0
        self.usdt_reserved = 0.0  # Profits reserved for rebuying
        self.total_invested = 0.0
        self.total_profit_taken = 0.0

        # Tracking
        self.trades: List[Trade] = []
        self.ath_price = 0.0
        self.portfolio_values = []

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_sma(self, prices: pd.Series, period: int = 200) -> pd.Series:
        """Calculate Simple Moving Average."""
        return prices.rolling(window=period).mean()

    def calculate_purchase_multiplier(
        self,
        rsi: float,
        price: float,
        sma_200: float
    ) -> Tuple[float, str]:
        """
        Calculate purchase amount multiplier based on market conditions.

        Args:
            rsi: Current RSI value
            price: Current price
            sma_200: 200-day SMA

        Returns:
            Tuple of (multiplier, reason)
        """
        multiplier = 1.0
        reasons = []

        # RSI-based adjustment
        if rsi < 30:
            multiplier = 3.0
            reasons.append("RSI<30 (Extreme Oversold: 3x)")
        elif rsi < 40:
            multiplier = 2.0
            reasons.append("RSI<40 (Oversold: 2x)")
        elif rsi < 50:
            multiplier = 1.5
            reasons.append("RSI<50 (Neutral-Low: 1.5x)")
        elif rsi < 60:
            multiplier = 1.0
            reasons.append("RSI<60 (Neutral: 1x)")
        elif rsi < 70:
            multiplier = 0.5
            reasons.append("RSI<70 (Neutral-High: 0.5x)")
        else:
            multiplier = 0.25
            reasons.append("RSI≥70 (Overbought: 0.25x)")

        # Distance from SMA200 adjustment
        if not np.isnan(sma_200):
            distance = (price - sma_200) / sma_200

            if distance < -0.20:  # 20% below SMA
                multiplier *= 1.5
                reasons.append("Price -20% below SMA200 (+50%)")
            elif distance > 0.30:  # 30% above SMA
                multiplier *= 0.5
                reasons.append("Price +30% above SMA200 (-50%)")

        reason = " | ".join(reasons)
        return multiplier, reason

    def should_take_profit(
        self,
        price: float,
        cost_basis: float
    ) -> Tuple[bool, float, str]:
        """
        Determine if should take profits at ATH.

        Args:
            price: Current price
            cost_basis: Average cost per BNB

        Returns:
            Tuple of (should_sell, sell_percentage, reason)
        """
        # Update ATH
        if price > self.ath_price:
            self.ath_price = price

        # Near ATH (within 2%)
        if price >= self.ath_price * 0.98:
            # Calculate profit
            portfolio_value = self.bnb_balance * price + self.usdt_balance
            profit_pct = (portfolio_value - self.total_invested) / self.total_invested

            if profit_pct > 1.0:  # >100% profit
                return True, 0.25, f"Profit {profit_pct*100:.1f}% > 100% (Sell 25%)"
            elif profit_pct > 0.75:  # >75% profit
                return True, 0.20, f"Profit {profit_pct*100:.1f}% > 75% (Sell 20%)"
            elif profit_pct > 0.50:  # >50% profit
                return True, 0.15, f"Profit {profit_pct*100:.1f}% > 50% (Sell 15%)"
            elif profit_pct > 0.30:  # >30% profit
                return True, 0.10, f"Profit {profit_pct*100:.1f}% > 30% (Sell 10%)"

        return False, 0.0, ""

    def should_rebuy_crash(self, rsi: float, price: float) -> Tuple[bool, float, str]:
        """
        Determine if should rebuy during crash with reserved funds.

        Args:
            rsi: Current RSI
            price: Current price

        Returns:
            Tuple of (should_rebuy, amount_percentage, reason)
        """
        if self.usdt_reserved <= 0:
            return False, 0.0, ""

        # Calculate drop from ATH
        drop_from_ath = (self.ath_price - price) / self.ath_price

        # Panic conditions
        if rsi < 25:
            return True, 0.5, f"RSI<25 panic (Use 50% reserve)"
        elif drop_from_ath > 0.30:
            return True, 0.5, f"Price -30% from ATH (Use 50% reserve)"

        return False, 0.0, ""

    def execute_buy(
        self,
        date: str,
        price: float,
        amount_usd: float,
        rsi: float,
        reason: str,
        multiplier: float = 1.0
    ):
        """Execute buy order."""
        if self.usdt_balance >= amount_usd:
            quantity = amount_usd / price
            self.usdt_balance -= amount_usd
            self.bnb_balance += quantity
            self.total_invested += amount_usd

            portfolio_value = self.bnb_balance * price + self.usdt_balance

            trade = Trade(
                date=date,
                type='buy',
                price=price,
                quantity=quantity,
                amount_usd=amount_usd,
                rsi=rsi,
                reason=reason,
                portfolio_value=portfolio_value,
                bnb_balance=self.bnb_balance,
                usdt_balance=self.usdt_balance,
                multiplier=multiplier
            )
            self.trades.append(trade)
            return trade
        return None

    def execute_sell(
        self,
        date: str,
        price: float,
        sell_pct: float,
        rsi: float,
        reason: str
    ):
        """Execute sell order (profit taking)."""
        quantity = self.bnb_balance * sell_pct
        amount_usd = quantity * price

        self.bnb_balance -= quantity
        self.usdt_balance += amount_usd
        self.usdt_reserved += amount_usd  # Reserve for rebuying
        self.total_profit_taken += amount_usd

        portfolio_value = self.bnb_balance * price + self.usdt_balance

        trade = Trade(
            date=date,
            type='sell',
            price=price,
            quantity=quantity,
            amount_usd=amount_usd,
            rsi=rsi,
            reason=reason,
            portfolio_value=portfolio_value,
            bnb_balance=self.bnb_balance,
            usdt_balance=self.usdt_balance
        )
        self.trades.append(trade)
        return trade

    def backtest(self, df: pd.DataFrame) -> Dict:
        """
        Execute backtest.

        Args:
            df: DataFrame with OHLCV data (daily)

        Returns:
            Dict with results and metrics
        """
        print(f"\n{'='*80}")
        print(f"DCA SMART SIMULATION - Intelligent Strategy")
        print(f"{'='*80}\n")
        print(f"Period: {df.index[0].date()} to {df.index[-1].date()}")
        print(f"Days: {len(df)}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Weekly Investment: ${self.weekly_investment:.2f}")
        print(f"Purchase Day: Monday\n")

        # Calculate indicators
        print("Calculating indicators...")
        df['rsi'] = self.calculate_rsi(df['close'])
        df['sma_200'] = self.calculate_sma(df['close'], 200)

        # Remove NaN rows (warm-up period)
        df = df.dropna().copy()
        print(f"Trading on {len(df)} days (after warm-up)\n")

        # Initialize ATH
        self.ath_price = df['close'].iloc[0]

        # Weekly purchase counter
        weeks_passed = 0
        last_purchase_week = None

        # Simulate day by day
        for timestamp, row in df.iterrows():
            price = row['close']
            rsi = row['rsi']
            sma_200 = row['sma_200']

            # Track portfolio value
            portfolio_value = self.bnb_balance * price + self.usdt_balance
            self.portfolio_values.append({
                'date': timestamp,
                'value': portfolio_value,
                'price': price
            })

            # Weekly DCA (every Monday)
            current_week = timestamp.isocalendar()[1]
            if timestamp.weekday() == self.purchase_day and current_week != last_purchase_week:
                last_purchase_week = current_week
                weeks_passed += 1

                # Calculate purchase amount with multiplier
                multiplier, reason = self.calculate_purchase_multiplier(
                    rsi, price, sma_200
                )
                amount = self.weekly_investment * multiplier

                trade = self.execute_buy(
                    date=str(timestamp.date()),
                    price=price,
                    amount_usd=amount,
                    rsi=rsi,
                    reason=f"Weekly DCA #{weeks_passed}: {reason}",
                    multiplier=multiplier
                )

                if trade:
                    print(f"[{timestamp.date()}] BUY: ${amount:.2f} @ ${price:.2f}")
                    print(f"  {reason}")
                    print(f"  BNB: {self.bnb_balance:.4f} | USDT: ${self.usdt_balance:.2f}")

            # Profit taking at ATH
            cost_basis = (self.total_invested / self.bnb_balance) if self.bnb_balance > 0 else 0
            should_sell, sell_pct, sell_reason = self.should_take_profit(price, cost_basis)

            if should_sell:
                trade = self.execute_sell(
                    date=str(timestamp.date()),
                    price=price,
                    sell_pct=sell_pct,
                    rsi=rsi,
                    reason=f"ATH Profit Taking: {sell_reason}"
                )
                print(f"\n[{timestamp.date()}] SELL: {sell_pct*100:.0f}% @ ${price:.2f}")
                print(f"  {sell_reason}")
                print(f"  Amount: ${trade.amount_usd:.2f} | Reserved: ${self.usdt_reserved:.2f}\n")

            # Rebuy during crashes
            should_rebuy, rebuy_pct, rebuy_reason = self.should_rebuy_crash(rsi, price)

            if should_rebuy:
                rebuy_amount = self.usdt_reserved * rebuy_pct
                trade = self.execute_buy(
                    date=str(timestamp.date()),
                    price=price,
                    amount_usd=rebuy_amount,
                    rsi=rsi,
                    reason=f"Crash Rebuy: {rebuy_reason}"
                )
                if trade:
                    self.usdt_reserved -= rebuy_amount
                    print(f"\n[{timestamp.date()}] REBUY: ${rebuy_amount:.2f} @ ${price:.2f}")
                    print(f"  {rebuy_reason}")
                    print(f"  Reserved Left: ${self.usdt_reserved:.2f}\n")

        # Calculate final metrics
        final_price = df['close'].iloc[-1]
        results = self.calculate_metrics(df, final_price)

        return results

    def calculate_metrics(self, df: pd.DataFrame, final_price: float) -> Dict:
        """Calculate strategy metrics and compare with baselines."""

        # Final portfolio
        final_bnb_value = self.bnb_balance * final_price
        final_portfolio = self.usdt_balance + final_bnb_value

        # DCA Smart metrics
        total_return_usd = final_portfolio - self.total_invested
        total_return_pct = (total_return_usd / self.total_invested) * 100 if self.total_invested > 0 else 0

        # Cost basis
        avg_cost = self.total_invested / self.bnb_balance if self.bnb_balance > 0 else 0

        # Baseline 1: Buy & Hold (invest everything at start)
        first_price = df['close'].iloc[0]
        bh_quantity = self.initial_capital / first_price
        bh_final = bh_quantity * final_price
        bh_return_pct = ((bh_final - self.initial_capital) / self.initial_capital) * 100

        # Baseline 2: Buy & Hold + Weekly DCA
        weeks = len([t for t in self.trades if t.type == 'buy'])
        bh_dca_invested = self.initial_capital + (weeks * self.weekly_investment)
        bh_dca_quantity = self.initial_capital / first_price

        for i, (timestamp, row) in enumerate(df.iterrows()):
            if i > 0 and timestamp.weekday() == self.purchase_day:
                week_num = timestamp.isocalendar()[1]
                if i == 0 or df.index[i-1].isocalendar()[1] != week_num:
                    bh_dca_quantity += self.weekly_investment / row['close']

        bh_dca_final = bh_dca_quantity * final_price
        bh_dca_return_pct = ((bh_dca_final - bh_dca_invested) / bh_dca_invested) * 100

        # Baseline 3: DCA Fixed (no adjustments)
        dca_fixed_invested = self.initial_capital
        dca_fixed_quantity = 0

        for i, (timestamp, row) in enumerate(df.iterrows()):
            if timestamp.weekday() == self.purchase_day:
                week_num = timestamp.isocalendar()[1]
                if i == 0 or df.index[i-1].isocalendar()[1] != week_num:
                    if dca_fixed_invested >= self.weekly_investment:
                        dca_fixed_quantity += self.weekly_investment / row['close']
                        dca_fixed_invested += self.weekly_investment

        dca_fixed_final = dca_fixed_quantity * final_price
        dca_fixed_return_pct = ((dca_fixed_final - dca_fixed_invested) / dca_fixed_invested) * 100

        # Trade statistics
        buy_trades = [t for t in self.trades if t.type == 'buy']
        sell_trades = [t for t in self.trades if t.type == 'sell']

        dip_buys = [t for t in buy_trades if t.multiplier >= 2.0]
        ath_sells = [t for t in sell_trades]

        return {
            'strategy': 'DCA Smart',
            'period': f"{df.index[0].date()} to {df.index[-1].date()}",
            'days': len(df),

            # Portfolio
            'final_portfolio': final_portfolio,
            'bnb_balance': self.bnb_balance,
            'bnb_value': final_bnb_value,
            'usdt_balance': self.usdt_balance,
            'usdt_reserved': self.usdt_reserved,

            # Investment
            'initial_capital': self.initial_capital,
            'total_invested': self.total_invested,
            'avg_cost': avg_cost,
            'final_price': final_price,

            # Returns
            'total_return_usd': total_return_usd,
            'total_return_pct': total_return_pct,

            # Comparisons
            'buy_hold_return_pct': bh_return_pct,
            'buy_hold_dca_return_pct': bh_dca_return_pct,
            'dca_fixed_return_pct': dca_fixed_return_pct,

            # Trades
            'total_trades': len(self.trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'dip_buys': len(dip_buys),
            'ath_sells': len(ath_sells),
            'total_profit_taken': self.total_profit_taken,

            # Top events
            'top_dip_buys': [
                {
                    'date': t.date,
                    'price': t.price,
                    'amount': t.amount_usd,
                    'rsi': t.rsi,
                    'multiplier': t.multiplier,
                    'reason': t.reason
                }
                for t in sorted(dip_buys, key=lambda x: x.multiplier, reverse=True)[:5]
            ],
            'top_ath_sells': [
                {
                    'date': t.date,
                    'price': t.price,
                    'amount': t.amount_usd,
                    'quantity': t.quantity,
                    'reason': t.reason
                }
                for t in ath_sells[:5]
            ]
        }


def download_historical_data(
    symbol: str = "BNB/USDT",
    timeframe: str = "1d",
    start_date: str = "2023-11-01"
) -> pd.DataFrame:
    """
    Download historical data from Binance.

    Args:
        symbol: Trading pair
        timeframe: Candle timeframe
        start_date: Start date (YYYY-MM-DD)

    Returns:
        DataFrame with OHLCV data
    """
    import ccxt

    print(f"\nDownloading {symbol} {timeframe} data from {start_date}...")

    exchange = ccxt.binance()
    since = exchange.parse8601(f"{start_date}T00:00:00Z")

    all_candles = []
    while True:
        candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not candles:
            break

        all_candles.extend(candles)
        since = candles[-1][0] + 1

        # Check if we've reached current time
        if candles[-1][0] >= exchange.milliseconds():
            break

    df = pd.DataFrame(
        all_candles,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    print(f"Downloaded {len(df)} candles")
    return df


def create_visualizations(
    df: pd.DataFrame,
    strategy: DCASmartStrategy,
    results: Dict,
    output_dir: Path
):
    """Create comprehensive visualization charts."""

    fig = plt.figure(figsize=(20, 14))

    # 1. Portfolio Value Comparison
    ax1 = plt.subplot(3, 2, 1)

    portfolio_df = pd.DataFrame(strategy.portfolio_values)
    portfolio_df.set_index('date', inplace=True)

    # Calculate baselines
    first_price = df['close'].iloc[0]
    bh_value = (results['initial_capital'] / first_price) * df['close']

    ax1.plot(portfolio_df.index, portfolio_df['value'],
             label='DCA Smart', linewidth=2, color='green')
    ax1.plot(df.index, bh_value,
             label='Buy & Hold', linewidth=2, color='blue', alpha=0.7)
    ax1.axhline(results['initial_capital'], color='gray',
                linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.set_title('Portfolio Value Over Time', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Portfolio Value (USD)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. BNB Price + Trades
    ax2 = plt.subplot(3, 2, 2)
    ax2.plot(df.index, df['close'], label='BNB Price', color='orange', linewidth=1.5)

    # Mark trades
    buy_trades = [t for t in strategy.trades if t.type == 'buy']
    sell_trades = [t for t in strategy.trades if t.type == 'sell']

    if buy_trades:
        buy_dates = [pd.to_datetime(t.date) for t in buy_trades]
        buy_prices = [t.price for t in buy_trades]
        ax2.scatter(buy_dates, buy_prices, color='green', marker='^',
                   s=100, alpha=0.6, label='Buys', zorder=5)

    if sell_trades:
        sell_dates = [pd.to_datetime(t.date) for t in sell_trades]
        sell_prices = [t.price for t in sell_trades]
        ax2.scatter(sell_dates, sell_prices, color='red', marker='v',
                   s=150, alpha=0.8, label='Sells (Profit Taking)', zorder=5)

    ax2.set_title('BNB Price + Trade Markers', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Price (USD)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. RSI + Buy Intensity
    ax3 = plt.subplot(3, 2, 3)
    ax3.plot(df.index, df['rsi'], label='RSI', color='purple', linewidth=1)
    ax3.axhline(70, color='red', linestyle='--', alpha=0.5, label='Overbought')
    ax3.axhline(30, color='green', linestyle='--', alpha=0.5, label='Oversold')
    ax3.fill_between(df.index, 0, 30, alpha=0.1, color='green')
    ax3.fill_between(df.index, 70, 100, alpha=0.1, color='red')

    # Mark dip buys
    dip_buys = [t for t in buy_trades if t.multiplier >= 2.0]
    if dip_buys:
        dip_dates = [pd.to_datetime(t.date) for t in dip_buys]
        dip_rsi = [t.rsi for t in dip_buys]
        ax3.scatter(dip_dates, dip_rsi, color='darkgreen', marker='o',
                   s=200, alpha=0.8, label='Dip Buys (2x+)', zorder=5)

    ax3.set_title('RSI + Dip Buying Opportunities', fontsize=14, fontweight='bold')
    ax3.set_ylabel('RSI')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Strategy Comparison
    ax4 = plt.subplot(3, 2, 4)
    strategies = ['DCA Smart', 'Buy & Hold', 'B&H + DCA', 'DCA Fixed']
    returns = [
        results['total_return_pct'],
        results['buy_hold_return_pct'],
        results['buy_hold_dca_return_pct'],
        results['dca_fixed_return_pct']
    ]
    colors = ['green', 'blue', 'cyan', 'orange']

    bars = ax4.barh(strategies, returns, color=colors, alpha=0.7)
    ax4.set_xlabel('Return (%)')
    ax4.set_title('Strategy Performance Comparison', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for i, (bar, ret) in enumerate(zip(bars, returns)):
        ax4.text(ret + 5, i, f"{ret:.1f}%", va='center', fontweight='bold')

    # 5. Cost Basis Evolution
    ax5 = plt.subplot(3, 2, 5)

    cost_basis_history = []
    running_invested = 0
    running_bnb = 0

    for trade in buy_trades:
        running_invested += trade.amount_usd
        running_bnb += trade.quantity
        cost_basis_history.append({
            'date': pd.to_datetime(trade.date),
            'cost_basis': running_invested / running_bnb if running_bnb > 0 else 0,
            'price': trade.price
        })

    if cost_basis_history:
        cb_df = pd.DataFrame(cost_basis_history)
        ax5.plot(cb_df['date'], cb_df['cost_basis'],
                label='Average Cost Basis', color='green', linewidth=2)
        ax5.plot(cb_df['date'], cb_df['price'],
                label='Market Price', color='orange', linewidth=1, alpha=0.7)
        ax5.fill_between(cb_df['date'], cb_df['cost_basis'], cb_df['price'],
                         where=(cb_df['price'] >= cb_df['cost_basis']),
                         alpha=0.2, color='green', label='Profit Zone')
        ax5.set_title('Cost Basis vs Market Price', fontsize=14, fontweight='bold')
        ax5.set_ylabel('Price (USD)')
        ax5.legend()
        ax5.grid(True, alpha=0.3)

    # 6. Investment Summary
    ax6 = plt.subplot(3, 2, 6)
    ax6.axis('off')

    summary_text = f"""
    DCA SMART STRATEGY - SUMMARY
    {'='*50}

    PORTFOLIO
    Final Value:        ${results['final_portfolio']:,.2f}
    BNB Holdings:       {results['bnb_balance']:.4f} BNB
    USDT Balance:       ${results['usdt_balance']:,.2f}
    Reserved (Profits): ${results['usdt_reserved']:,.2f}

    PERFORMANCE
    Total Return:       {results['total_return_pct']:.2f}% (${results['total_return_usd']:,.2f})
    Buy & Hold:         {results['buy_hold_return_pct']:.2f}%
    B&H + DCA:          {results['buy_hold_dca_return_pct']:.2f}%
    DCA Fixed:          {results['dca_fixed_return_pct']:.2f}%

    INVESTMENT
    Total Invested:     ${results['total_invested']:,.2f}
    Average Cost:       ${results['avg_cost']:.2f}
    Final Price:        ${results['final_price']:.2f}

    TRADING ACTIVITY
    Total Trades:       {results['total_trades']}
    Buys:              {results['buy_trades']}
    Dip Buys (2x+):    {results['dip_buys']}
    Profit Sells:      {results['sell_trades']}
    Profit Taken:      ${results['total_profit_taken']:,.2f}

    VERDICT
    {'✅ SUPERIOR' if results['total_return_pct'] > results['buy_hold_return_pct'] else '❌ INFERIOR'} to Buy & Hold
    Alpha: {results['total_return_pct'] - results['buy_hold_return_pct']:+.2f}%
    """

    ax6.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
             verticalalignment='center')

    plt.tight_layout()

    # Save
    output_path = output_dir / 'dca_smart_analysis.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nVisualization saved: {output_path}")

    plt.close()


def print_detailed_report(results: Dict):
    """Print detailed analysis report."""

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


def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(description='DCA Smart Simulation')
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
            df = download_historical_data(
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

    # Run simulation
    strategy = DCASmartStrategy(
        initial_capital=args.initial_capital,
        weekly_investment=args.weekly_investment
    )

    results = strategy.backtest(df)

    # Print report
    print_detailed_report(results)

    # Create visualizations
    output_dir = Path(__file__).parent.parent / 'data' / 'backtests'
    output_dir.mkdir(parents=True, exist_ok=True)

    create_visualizations(df, strategy, results, output_dir)

    # Save results JSON
    results_file = output_dir / 'dca_smart_results.json'

    # Convert to JSON-serializable format
    results_json = {k: v for k, v in results.items()}

    with open(results_file, 'w') as f:
        json.dump(results_json, f, indent=2)
    print(f"Results saved: {results_file}")

    # Save trades CSV
    trades_file = output_dir / 'dca_smart_trades.csv'
    trades_df = pd.DataFrame([asdict(t) for t in strategy.trades])
    trades_df.to_csv(trades_file, index=False)
    print(f"Trades saved: {trades_file}")

    # Generate markdown report
    report_file = Path(__file__).parent.parent / 'reports' / 'DCA_SMART_ANALYSIS.md'
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, 'w') as f:
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

    print(f"Report saved: {report_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
