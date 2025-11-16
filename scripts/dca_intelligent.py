#!/usr/bin/env python3
"""
ESTRATÉGIA 3: DCA Inteligente (Dollar Cost Averaging)

Baseada nos aprendizados dos backtests:
- Buy & Hold simples venceu (+59.72%)
- Timing de mercado é difícil
- Acumulação constante funciona em crypto bull markets

REGRAS KISS:

COMPRA REGULAR:
- Frequência: Semanal (toda segunda-feira 00:00 UTC)
- Valor base: $100 USDT fixo

AJUSTE INTELIGENTE baseado em RSI:
- Se RSI < 30 (sobrevendido): Dobra valor (2x = $200)
- Se RSI > 70 (sobrecomprado): Metade do valor (0.5x = $50)
- Se RSI entre 30-70: Valor normal ($100)

REBALANCEAMENTO MENSAL:
- Se BNB > 70% do portfolio: Realiza 25% dos lucros
- Se BNB < 30% do portfolio: Compra mais 10%

Timeframe: 1D para análise
Objetivo: Acumular BNB de forma inteligente
Sem venda emocional: Apenas rebalanceamento estratégico

Meta: Superar Buy & Hold puro através de timing inteligente
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Purchase:
    """Registro de compra DCA."""
    date: str
    price: float
    amount_usd: float
    quantity: float
    rsi: float
    reason: str
    total_invested: float
    total_bnb: float


@dataclass
class Rebalance:
    """Registro de rebalanceamento."""
    date: str
    action: str  # 'take_profit' ou 'buy_more'
    price: float
    amount_usd: float
    quantity: float
    reason: str
    portfolio_bnb_pct: float


class DCAIntelligentStrategy:
    """
    Estratégia de DCA (Dollar Cost Averaging) Inteligente.

    Objetivo: Acumular BNB de forma consistente com ajustes
    baseados em condições de mercado (RSI).
    """

    def __init__(
        self,
        initial_balance: float = 5000.0,
        weekly_amount: float = 100.0,
        purchase_day: int = 0  # 0 = Monday
    ):
        """
        Inicializa estratégia.

        Args:
            initial_balance: Capital inicial em USDT
            weekly_amount: Valor semanal base em USDT
            purchase_day: Dia da semana para compra (0=Monday, 6=Sunday)
        """
        self.initial_balance = initial_balance
        self.balance_usdt = initial_balance
        self.balance_bnb = 0.0
        self.weekly_amount = weekly_amount
        self.purchase_day = purchase_day

        self.purchases: List[Purchase] = []
        self.rebalances: List[Rebalance] = []

        # Tracking
        self.total_invested = 0.0
        self.last_rebalance_month = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores necessários.

        Args:
            df: DataFrame com OHLCV (1D timeframe)

        Returns:
            DataFrame com indicadores
        """
        df = df.copy()

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        return df

    def calculate_purchase_amount(self, rsi: float) -> float:
        """
        Calcula valor de compra ajustado pelo RSI.

        Args:
            rsi: Valor do RSI

        Returns:
            Valor em USDT para comprar
        """
        base_amount = self.weekly_amount

        # Ajuste inteligente
        if rsi < 30:
            # Sobrevendido: Dobra o valor
            return base_amount * 2.0
        elif rsi > 70:
            # Sobrecomprado: Metade do valor
            return base_amount * 0.5
        else:
            # Normal
            return base_amount

    def should_rebalance(self, current_month: int) -> bool:
        """
        Verifica se deve fazer rebalanceamento mensal.

        Args:
            current_month: Mês atual

        Returns:
            True se deve rebalancear
        """
        if self.last_rebalance_month is None:
            self.last_rebalance_month = current_month
            return False

        if current_month != self.last_rebalance_month:
            self.last_rebalance_month = current_month
            return True

        return False

    def rebalance_portfolio(self, price: float, date: str) -> Optional[Rebalance]:
        """
        Rebalanceia portfolio se necessário.

        Args:
            price: Preço atual do BNB
            date: Data atual

        Returns:
            Rebalance object se rebalanceou, None caso contrário
        """
        # Calcula % de BNB no portfolio
        bnb_value = self.balance_bnb * price
        total_value = self.balance_usdt + bnb_value

        if total_value == 0:
            return None

        bnb_pct = (bnb_value / total_value) * 100

        # BNB > 70%: Realiza 25% dos lucros
        if bnb_pct > 70 and self.balance_bnb > 0:
            sell_quantity = self.balance_bnb * 0.25
            proceeds = sell_quantity * price
            self.balance_bnb -= sell_quantity
            self.balance_usdt += proceeds

            return Rebalance(
                date=date,
                action='take_profit',
                price=price,
                amount_usd=proceeds,
                quantity=sell_quantity,
                reason=f'BNB at {bnb_pct:.1f}% > 70% threshold',
                portfolio_bnb_pct=bnb_pct
            )

        # BNB < 30%: Compra mais 10%
        elif bnb_pct < 30 and self.balance_usdt > 0:
            buy_amount = min(total_value * 0.10, self.balance_usdt)
            buy_quantity = buy_amount / price
            self.balance_usdt -= buy_amount
            self.balance_bnb += buy_quantity

            return Rebalance(
                date=date,
                action='buy_more',
                price=price,
                amount_usd=buy_amount,
                quantity=buy_quantity,
                reason=f'BNB at {bnb_pct:.1f}% < 30% threshold',
                portfolio_bnb_pct=bnb_pct
            )

        return None

    def backtest(self, df: pd.DataFrame, symbol: str = "BNB_USDT") -> Dict:
        """
        Executa backtest da estratégia DCA.

        Args:
            df: DataFrame com OHLCV (1D timeframe)
            symbol: Símbolo do ativo

        Returns:
            Dict com métricas de performance
        """
        print(f"\n{'='*80}")
        print(f"BACKTESTING: DCA Intelligent - {symbol}")
        print(f"{'='*80}\n")
        print(f"Initial Balance: ${self.initial_balance:,.2f} USDT")
        print(f"Period: {df.index[0]} to {df.index[-1]}")
        print(f"Candles: {len(df)} (1D timeframe)\n")
        print(f"Weekly Amount: ${self.weekly_amount:.2f}")
        print(f"Purchase Day: {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][self.purchase_day]}")
        print(f"Rebalancing: Monthly\n")

        # Calcula indicadores
        df = self.calculate_indicators(df)

        # Remove primeiras 14 linhas (warm-up para RSI)
        df = df.iloc[14:].copy()

        print(f"Trading on {len(df)} candles (after warm-up)\n")

        # Simula DCA
        for timestamp, row in df.iterrows():
            price = row['close']
            rsi = row['rsi']
            current_month = timestamp.month

            # Compra semanal (toda segunda-feira)
            if timestamp.weekday() == self.purchase_day:
                # Calcula valor ajustado pelo RSI
                purchase_amount = self.calculate_purchase_amount(rsi)

                # Garante que há USDT suficiente
                if self.balance_usdt >= purchase_amount:
                    quantity = purchase_amount / price
                    self.balance_usdt -= purchase_amount
                    self.balance_bnb += quantity
                    self.total_invested += purchase_amount

                    purchase = Purchase(
                        date=str(timestamp.date()),
                        price=price,
                        amount_usd=purchase_amount,
                        quantity=quantity,
                        rsi=rsi,
                        reason=self._get_purchase_reason(rsi),
                        total_invested=self.total_invested,
                        total_bnb=self.balance_bnb
                    )
                    self.purchases.append(purchase)

                    print(f"[{timestamp.date()}] PURCHASE: ${purchase_amount:.2f} @ ${price:.2f}")
                    print(f"  Quantity: {quantity:.6f} BNB | RSI: {rsi:.1f} | Reason: {purchase.reason}")
                    print(f"  Total Invested: ${self.total_invested:.2f} | Total BNB: {self.balance_bnb:.6f}")
                    print(f"  Balance: ${self.balance_usdt:.2f} USDT\n")

            # Rebalanceamento mensal (primeiro dia do mês)
            if self.should_rebalance(current_month):
                rebalance = self.rebalance_portfolio(price, str(timestamp.date()))
                if rebalance:
                    self.rebalances.append(rebalance)
                    print(f"[{timestamp.date()}] REBALANCE: {rebalance.action.upper()}")
                    print(f"  Price: ${price:.2f} | Amount: ${rebalance.amount_usd:.2f}")
                    print(f"  Reason: {rebalance.reason}")
                    print(f"  New Balance: ${self.balance_usdt:.2f} USDT | {self.balance_bnb:.6f} BNB\n")

        # Calcula valor final
        final_price = df.iloc[-1]['close']
        final_bnb_value = self.balance_bnb * final_price
        final_total_value = self.balance_usdt + final_bnb_value

        # Calcula métricas
        metrics = self._calculate_metrics(df, symbol, final_total_value, final_price)

        # Imprime resultados
        self._print_results(metrics, final_price)

        return metrics

    def _get_purchase_reason(self, rsi: float) -> str:
        """Retorna razão da compra baseado no RSI."""
        if rsi < 30:
            return "Oversold (2x amount)"
        elif rsi > 70:
            return "Overbought (0.5x amount)"
        else:
            return "Normal market"

    def _calculate_metrics(
        self,
        df: pd.DataFrame,
        symbol: str,
        final_value: float,
        final_price: float
    ) -> Dict:
        """Calcula métricas de performance."""

        # Returns
        total_return_usd = final_value - self.initial_balance
        total_return_pct = (total_return_usd / self.initial_balance) * 100

        # Buy & Hold baseline (comprar tudo no início)
        first_price = df.iloc[0]['close']
        bh_quantity = self.initial_balance / first_price
        bh_final_value = bh_quantity * final_price
        bh_return_pct = ((bh_final_value - self.initial_balance) / self.initial_balance) * 100

        # DCA Puro baseline (comprar valor fixo semanal sem ajustes)
        total_weeks = len(self.purchases)
        dca_pure_invested = total_weeks * self.weekly_amount
        dca_pure_quantity = sum([
            self.weekly_amount / df.iloc[df.index.get_loc(p.date, method='nearest')]['close']
            for p in self.purchases
        ])
        dca_pure_value = dca_pure_quantity * final_price + (self.initial_balance - dca_pure_invested)
        dca_pure_return_pct = ((dca_pure_value - self.initial_balance) / self.initial_balance) * 100

        # Alpha
        alpha_vs_bh = total_return_pct - bh_return_pct
        alpha_vs_dca = total_return_pct - dca_pure_return_pct

        # Average purchase price
        avg_purchase_price = (
            self.total_invested / self.balance_bnb
            if self.balance_bnb > 0 else 0
        )

        # ROI
        bnb_value = self.balance_bnb * final_price
        roi = ((bnb_value - self.total_invested) / self.total_invested * 100) if self.total_invested > 0 else 0

        return {
            'symbol': symbol,
            'strategy': 'DCA Intelligent',
            'initial_balance': self.initial_balance,
            'final_value': final_value,
            'final_balance_usdt': self.balance_usdt,
            'final_balance_bnb': self.balance_bnb,
            'final_bnb_value': bnb_value,
            'total_invested': self.total_invested,
            'total_return_usd': total_return_usd,
            'total_return_pct': total_return_pct,
            'buy_hold_return_pct': bh_return_pct,
            'dca_pure_return_pct': dca_pure_return_pct,
            'alpha_vs_buy_hold': alpha_vs_bh,
            'alpha_vs_dca_pure': alpha_vs_dca,
            'total_purchases': len(self.purchases),
            'total_rebalances': len(self.rebalances),
            'avg_purchase_price': avg_purchase_price,
            'roi_pct': roi,
        }

    def _print_results(self, metrics: Dict, final_price: float):
        """Imprime resultados do backtest."""
        print(f"\n{'='*80}")
        print(f"RESULTS: {metrics['strategy']} - {metrics['symbol']}")
        print(f"{'='*80}\n")

        print(f"FINAL PORTFOLIO:")
        print(f"  USDT Balance:       ${metrics['final_balance_usdt']:,.2f}")
        print(f"  BNB Balance:        {metrics['final_balance_bnb']:.6f} BNB")
        print(f"  BNB Value:          ${metrics['final_bnb_value']:,.2f} @ ${final_price:.2f}")
        print(f"  Total Value:        ${metrics['final_value']:,.2f}\n")

        print(f"PERFORMANCE:")
        print(f"  Strategy Return:    {metrics['total_return_pct']:+.2f}% (${metrics['total_return_usd']:+,.2f})")
        print(f"  Buy & Hold Return:  {metrics['buy_hold_return_pct']:+.2f}%")
        print(f"  DCA Pure Return:    {metrics['dca_pure_return_pct']:+.2f}%")
        print(f"  Alpha (vs B&H):     {metrics['alpha_vs_buy_hold']:+.2f}%")
        print(f"  Alpha (vs DCA):     {metrics['alpha_vs_dca_pure']:+.2f}%\n")

        print(f"INVESTMENT:")
        print(f"  Total Invested:     ${metrics['total_invested']:,.2f}")
        print(f"  Total Purchases:    {metrics['total_purchases']}")
        print(f"  Avg Purchase Price: ${metrics['avg_purchase_price']:.2f}")
        print(f"  Final Price:        ${final_price:.2f}")
        print(f"  ROI on BNB:         {metrics['roi_pct']:+.2f}%\n")

        print(f"REBALANCING:")
        print(f"  Total Rebalances:   {metrics['total_rebalances']}")
        if self.rebalances:
            take_profits = [r for r in self.rebalances if r.action == 'take_profit']
            buy_more = [r for r in self.rebalances if r.action == 'buy_more']
            print(f"  Take Profits:       {len(take_profits)}")
            print(f"  Buy More:           {len(buy_more)}\n")

        # Veredicto
        print(f"VERDICT:")
        if metrics['alpha_vs_buy_hold'] >= 10:
            print(f"  ✅ APPROVED - Alpha vs B&H {metrics['alpha_vs_buy_hold']:+.2f}% > 10% threshold")
        elif metrics['alpha_vs_buy_hold'] >= 0:
            print(f"  ⚠️  MARGINAL - Alpha vs B&H {metrics['alpha_vs_buy_hold']:+.2f}% positive but < 10%")
        else:
            print(f"  ❌ REJECTED - Alpha vs B&H {metrics['alpha_vs_buy_hold']:+.2f}% negative")

        if metrics['alpha_vs_dca_pure'] > 0:
            print(f"  ✅ Better than DCA Pure by {metrics['alpha_vs_dca_pure']:+.2f}%")
        else:
            print(f"  ⚠️  Worse than DCA Pure by {metrics['alpha_vs_dca_pure']:+.2f}%")

        print(f"\n{'='*80}\n")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest DCA Intelligent Strategy')
    parser.add_argument('--data', type=str, required=True, help='CSV file with OHLCV data (1D)')
    parser.add_argument('--symbol', type=str, default='BNB_USDT', help='Trading symbol')
    parser.add_argument('--initial-balance', type=float, default=5000.0, help='Initial capital')
    parser.add_argument('--weekly-amount', type=float, default=100.0, help='Weekly purchase amount')
    parser.add_argument('--output', type=str, help='Output JSON file for results')

    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.data}...")
    df = pd.read_csv(args.data, index_col=0, parse_dates=True)
    print(f"Loaded {len(df)} candles (1D timeframe)\n")

    # Run backtest
    strategy = DCAIntelligentStrategy(
        initial_balance=args.initial_balance,
        weekly_amount=args.weekly_amount
    )
    metrics = strategy.backtest(df, symbol=args.symbol)

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"Results saved to {args.output}")

    # Aprovado se Alpha vs B&H >= 10%
    approved = metrics['alpha_vs_buy_hold'] >= 10
    return 0 if approved else 1


if __name__ == '__main__':
    sys.exit(main())
