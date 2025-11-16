"""
DCA Simulator - Backtest execution engine.

This module handles the backtesting simulation of DCA strategies.

SOLID Principles:
- Single Responsibility: Only simulation execution
- Open/Closed: Can simulate any strategy implementing the interface
- Dependency Inversion: Depends on strategy abstraction
"""

import pandas as pd
import ccxt
from typing import Dict
from .strategy import DCASmartStrategy


class DataProvider:
    """Abstract data provider for market data."""

    @staticmethod
    def download_historical_data(
        symbol: str = "BNB/USDT",
        timeframe: str = "1d",
        start_date: str = "2023-11-01"
    ) -> pd.DataFrame:
        """
        Download historical data from Binance.

        Args:
            symbol: Trading pair (e.g., "BNB/USDT")
            timeframe: Candle timeframe (e.g., "1d")
            start_date: Start date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
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


class DCASimulator:
    """
    Backtest simulator for DCA strategies.

    Executes strategy on historical data and tracks performance.
    """

    def __init__(self, strategy: DCASmartStrategy):
        """
        Initialize simulator.

        Args:
            strategy: DCA strategy to simulate (dependency injection)
        """
        self.strategy = strategy

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data with indicators.

        Args:
            df: Raw OHLCV data

        Returns:
            DataFrame with indicators calculated
        """
        print("Calculating indicators...")
        df['rsi'] = self.strategy.rsi_indicator.calculate(df['close'])
        df['sma_200'] = self.strategy.sma_indicator.calculate(df['close'])

        # Remove NaN rows (warm-up period)
        df = df.dropna().copy()
        print(f"Trading on {len(df)} days (after warm-up)\n")

        return df

    def backtest(self, df: pd.DataFrame, verbose: bool = True) -> Dict:
        """
        Execute backtest simulation.

        Args:
            df: DataFrame with OHLCV data (daily)
            verbose: Print progress logs

        Returns:
            Dict with results and metrics
        """
        if verbose:
            print(f"\n{'='*80}")
            print(f"DCA SMART SIMULATION - Intelligent Strategy")
            print(f"{'='*80}\n")
            print(f"Period: {df.index[0].date()} to {df.index[-1].date()}")
            print(f"Days: {len(df)}")
            print(f"Initial Capital: ${self.strategy.initial_capital:,.2f}")
            print(f"Weekly Investment: ${self.strategy.weekly_investment:.2f}")
            print(f"Purchase Day: Monday\n")

        # Prepare data
        df = self.prepare_data(df)

        # Initialize ATH
        self.strategy.ath_price = df['close'].iloc[0]

        # Weekly purchase tracking
        weeks_passed = 0
        last_purchase_week = None

        # Simulate day by day
        for timestamp, row in df.iterrows():
            price = row['close']
            rsi = row['rsi']
            sma_200 = row['sma_200']

            # Track portfolio value
            portfolio_value = self.strategy.get_portfolio_value(price)
            self.strategy.portfolio_values.append({
                'date': timestamp,
                'value': portfolio_value,
                'price': price
            })

            # Weekly DCA (every Monday)
            current_week = timestamp.isocalendar()[1]
            if timestamp.weekday() == self.strategy.purchase_day and current_week != last_purchase_week:
                last_purchase_week = current_week
                weeks_passed += 1

                # Calculate purchase amount with multiplier
                multiplier, reason = self.strategy.calculate_purchase_multiplier(
                    rsi, price, sma_200
                )
                amount = self.strategy.weekly_investment * multiplier

                trade = self.strategy.execute_buy(
                    date=str(timestamp.date()),
                    price=price,
                    amount_usd=amount,
                    rsi=rsi,
                    reason=f"Weekly DCA #{weeks_passed}: {reason}",
                    multiplier=multiplier
                )

                if trade and verbose:
                    print(f"[{timestamp.date()}] BUY: ${amount:.2f} @ ${price:.2f}")
                    print(f"  {reason}")
                    print(f"  BNB: {self.strategy.bnb_balance:.4f} | USDT: ${self.strategy.usdt_balance:.2f}")

            # Profit taking at ATH
            cost_basis = self.strategy.get_cost_basis()
            should_sell, sell_pct, sell_reason = self.strategy.should_take_profit(price, cost_basis)

            if should_sell:
                trade = self.strategy.execute_sell(
                    date=str(timestamp.date()),
                    price=price,
                    sell_pct=sell_pct,
                    rsi=rsi,
                    reason=f"ATH Profit Taking: {sell_reason}"
                )
                if verbose:
                    print(f"\n[{timestamp.date()}] SELL: {sell_pct*100:.0f}% @ ${price:.2f}")
                    print(f"  {sell_reason}")
                    print(f"  Amount: ${trade.amount_usd:.2f} | Reserved: ${self.strategy.usdt_reserved:.2f}\n")

            # Rebuy during crashes
            should_rebuy, rebuy_pct, rebuy_reason = self.strategy.should_rebuy_crash(rsi, price)

            if should_rebuy:
                rebuy_amount = self.strategy.usdt_reserved * rebuy_pct
                trade = self.strategy.execute_buy(
                    date=str(timestamp.date()),
                    price=price,
                    amount_usd=rebuy_amount,
                    rsi=rsi,
                    reason=f"Crash Rebuy: {rebuy_reason}"
                )
                if trade:
                    self.strategy.usdt_reserved -= rebuy_amount
                    if verbose:
                        print(f"\n[{timestamp.date()}] REBUY: ${rebuy_amount:.2f} @ ${price:.2f}")
                        print(f"  {rebuy_reason}")
                        print(f"  Reserved Left: ${self.strategy.usdt_reserved:.2f}\n")

        # Calculate final metrics
        final_price = df['close'].iloc[-1]
        from .analyzer import DCAAnalyzer
        analyzer = DCAAnalyzer(self.strategy, df)
        results = analyzer.calculate_metrics(final_price)

        return results

    def get_strategy(self) -> DCASmartStrategy:
        """
        Get strategy instance.

        Returns:
            Strategy being simulated
        """
        return self.strategy
