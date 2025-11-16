"""
DCA Smart Strategy - Core strategy logic.

This module implements the intelligent DCA strategy with:
- RSI-based purchase multipliers
- ATH profit-taking
- Crash rebuying logic

SOLID Principles:
- Single Responsibility: Only strategy decisions
- Open/Closed: Extendable through inheritance
- Dependency Inversion: Uses abstract indicators
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict
from abc import ABC, abstractmethod


@dataclass
class Trade:
    """Trade record with immutable data."""
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

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class TechnicalIndicator(ABC):
    """Abstract base for technical indicators."""

    @abstractmethod
    def calculate(self, prices: pd.Series) -> pd.Series:
        """Calculate indicator values."""
        pass


class RSIIndicator(TechnicalIndicator):
    """RSI (Relative Strength Index) indicator."""

    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, prices: pd.Series) -> pd.Series:
        """
        Calculate RSI indicator.

        Args:
            prices: Price series

        Returns:
            RSI values (0-100)
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


class SMAIndicator(TechnicalIndicator):
    """Simple Moving Average indicator."""

    def __init__(self, period: int = 200):
        self.period = period

    def calculate(self, prices: pd.Series) -> pd.Series:
        """
        Calculate SMA.

        Args:
            prices: Price series

        Returns:
            SMA values
        """
        return prices.rolling(window=self.period).mean()


class DCASmartStrategy:
    """
    Intelligent DCA Strategy with adaptive position sizing.

    Features:
    - RSI-based purchase adjustments (buy more in dips)
    - ATH profit-taking (sell at highs)
    - Crash rebuying (use reserved profits)

    Strategy Pattern: Can be extended with new strategies
    """

    def __init__(
        self,
        initial_capital: float = 5000.0,
        weekly_investment: float = 200.0,
        purchase_day: int = 0,  # Monday
        rsi_indicator: TechnicalIndicator = None,
        sma_indicator: TechnicalIndicator = None
    ):
        """
        Initialize strategy.

        Args:
            initial_capital: Starting capital in USDT
            weekly_investment: Weekly DCA amount in USDT
            purchase_day: Day of week for purchases (0=Monday)
            rsi_indicator: RSI calculator (injected)
            sma_indicator: SMA calculator (injected)
        """
        self.initial_capital = initial_capital
        self.weekly_investment = weekly_investment
        self.purchase_day = purchase_day

        # Dependency injection for indicators
        self.rsi_indicator = rsi_indicator or RSIIndicator(period=14)
        self.sma_indicator = sma_indicator or SMAIndicator(period=200)

        # Portfolio state
        self.usdt_balance = initial_capital
        self.bnb_balance = 0.0
        self.usdt_reserved = 0.0  # Profits reserved for rebuying
        self.total_invested = 0.0
        self.total_profit_taken = 0.0

        # Tracking
        self.trades: List[Trade] = []
        self.ath_price = 0.0
        self.portfolio_values = []

    def calculate_purchase_multiplier(
        self,
        rsi: float,
        price: float,
        sma_200: float
    ) -> Tuple[float, str]:
        """
        Calculate purchase amount multiplier based on market conditions.

        RSI-based multipliers:
        - RSI < 30: 3x (extreme oversold)
        - RSI < 40: 2x (oversold)
        - RSI < 50: 1.5x (neutral-low)
        - RSI < 60: 1x (neutral)
        - RSI < 70: 0.5x (neutral-high)
        - RSI >= 70: 0.25x (overbought)

        Distance from SMA200:
        - 20% below: +50% multiplier
        - 30% above: -50% multiplier

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

        Profit-taking rules (when near ATH ≥98%):
        - Profit > 100%: Sell 25%
        - Profit > 75%: Sell 20%
        - Profit > 50%: Sell 15%
        - Profit > 30%: Sell 10%

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

        Rebuy triggers (use 50% of reserves):
        - RSI < 25 (panic)
        - Price -30% from ATH (crash)

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
    ) -> Trade:
        """
        Execute buy order.

        Args:
            date: Trade date
            price: Purchase price
            amount_usd: Amount in USDT
            rsi: Current RSI
            reason: Trade reason
            multiplier: Purchase multiplier

        Returns:
            Trade object or None if insufficient funds
        """
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
    ) -> Trade:
        """
        Execute sell order (profit taking).

        Args:
            date: Trade date
            price: Sell price
            sell_pct: Percentage to sell (0.0-1.0)
            rsi: Current RSI
            reason: Trade reason

        Returns:
            Trade object
        """
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

    def get_portfolio_value(self, current_price: float) -> float:
        """
        Calculate current portfolio value.

        Args:
            current_price: Current asset price

        Returns:
            Total portfolio value in USDT
        """
        return self.bnb_balance * current_price + self.usdt_balance

    def get_cost_basis(self) -> float:
        """
        Calculate average cost basis.

        Returns:
            Average cost per BNB or 0 if no holdings
        """
        if self.bnb_balance > 0:
            return self.total_invested / self.bnb_balance
        return 0.0

    def get_profit_pct(self, current_price: float) -> float:
        """
        Calculate current profit percentage.

        Args:
            current_price: Current asset price

        Returns:
            Profit percentage
        """
        if self.total_invested > 0:
            portfolio_value = self.get_portfolio_value(current_price)
            return ((portfolio_value - self.total_invested) / self.total_invested) * 100
        return 0.0
