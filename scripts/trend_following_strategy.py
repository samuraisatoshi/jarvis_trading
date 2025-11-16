#!/usr/bin/env python3
"""
ESTRATÉGIA 1: Trend Following Simples (Swing Trade)

Baseada nos aprendizados dos backtests:
- Buy & Hold superou TODAS estratégias complexas (+59.72%)
- Fibonacci Golden Zone fracassou (-4.6%, 0% win rate)
- Simplicidade vence complexidade

REGRAS KISS (Keep It Simple Stupid):

COMPRAR quando:
- EMA20 > EMA50 > EMA200 (uptrend confirmado)
- RSI > 40 (não sobrevendido)
- Volume > Volume_MA20 (volume confirmando)

VENDER quando:
- EMA20 < EMA50 (trend enfraquecendo) OU
- RSI > 80 (sobrecomprado) OU
- Price < EMA50 (quebrou suporte)

STOP LOSS:
- max(EMA50, entrada * 0.95) - 5% ou EMA50

Timeframe: 4H para swing trade
Position sizing: 100% (all-in como Buy&Hold)
Sem SHORT: Apenas LONG em crypto bull market

Meta: Superar Buy & Hold baseline em 10%+
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Trade:
    """Registro de trade."""
    entry_time: str
    entry_price: float
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    quantity: float = 0.0
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None

    def close(self, exit_time: str, exit_price: float, reason: str):
        """Fecha o trade."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason
        self.pnl = (exit_price - self.entry_price) * self.quantity
        self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100


class TrendFollowingStrategy:
    """
    Estratégia de Trend Following Simples.

    Objetivo: Superar Buy & Hold através de timing inteligente
    sem complexidade desnecessária.
    """

    def __init__(self, initial_balance: float = 5000.0):
        """Inicializa estratégia."""
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position: Optional[Trade] = None
        self.trades: List[Trade] = []

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores necessários (simples e eficientes).

        Args:
            df: DataFrame com OHLCV

        Returns:
            DataFrame com indicadores adicionados
        """
        df = df.copy()

        # EMAs
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume MA
        df['volume_ma_20'] = df['volume'].rolling(window=20).mean()

        return df

    def check_entry_signal(self, row: pd.Series) -> bool:
        """
        Verifica sinal de COMPRA (regras KISS).

        Returns:
            True se deve comprar
        """
        # Precisa de todos os indicadores
        if pd.isna(row['ema_200']):
            return False

        # COMPRAR quando:
        uptrend = (row['ema_20'] > row['ema_50'] > row['ema_200'])
        rsi_ok = row['rsi'] > 40  # Não sobrevendido
        volume_ok = row['volume'] > row['volume_ma_20']  # Volume confirmando

        return uptrend and rsi_ok and volume_ok

    def check_exit_signal(self, row: pd.Series, entry_price: float) -> Tuple[bool, str]:
        """
        Verifica sinal de VENDA (regras KISS).

        Returns:
            Tuple (deve_vender, razão)
        """
        # VENDER quando:

        # 1. Trend enfraquecendo
        if row['ema_20'] < row['ema_50']:
            return True, "EMA crossover down"

        # 2. Sobrecomprado
        if row['rsi'] > 80:
            return True, "RSI overbought"

        # 3. Quebrou suporte (EMA50)
        if row['close'] < row['ema_50']:
            return True, "Broke EMA50 support"

        # 4. Stop loss (5%)
        if row['close'] < entry_price * 0.95:
            return True, "Stop loss hit"

        return False, ""

    def backtest(self, df: pd.DataFrame, symbol: str = "BNB_USDT") -> Dict:
        """
        Executa backtest da estratégia.

        Args:
            df: DataFrame com OHLCV
            symbol: Símbolo do ativo

        Returns:
            Dict com métricas de performance
        """
        print(f"\n{'='*80}")
        print(f"BACKTESTING: Trend Following Strategy - {symbol}")
        print(f"{'='*80}\n")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Period: {df.index[0]} to {df.index[-1]}")
        print(f"Candles: {len(df)}\n")

        # Calcula indicadores
        df = self.calculate_indicators(df)

        # Remove primeiras 200 linhas (warm-up para EMA200)
        df = df.iloc[200:].copy()

        print(f"Trading on {len(df)} candles (after warm-up)\n")

        # Simula trading
        for i, (timestamp, row) in enumerate(df.iterrows()):
            price = row['close']

            # Sem posição - procura ENTRADA
            if self.position is None:
                if self.check_entry_signal(row):
                    # Calcula quantidade (100% do capital)
                    quantity = self.balance / price
                    self.position = Trade(
                        entry_time=str(timestamp),
                        entry_price=price,
                        quantity=quantity
                    )
                    self.balance = 0  # All-in
                    print(f"[{timestamp}] BUY: {quantity:.6f} @ ${price:.2f} | RSI={row['rsi']:.1f}")

            # Com posição - procura SAÍDA
            else:
                should_exit, reason = self.check_exit_signal(row, self.position.entry_price)
                if should_exit:
                    # Fecha posição
                    self.position.close(str(timestamp), price, reason)
                    self.balance = self.position.quantity * price
                    print(f"[{timestamp}] SELL: {reason}")
                    print(f"  PnL: ${self.position.pnl:+,.2f} ({self.position.pnl_pct:+.2f}%)")
                    print(f"  Balance: ${self.balance:,.2f}\n")
                    self.trades.append(self.position)
                    self.position = None

        # Fecha posição aberta no final
        if self.position is not None:
            last_price = df.iloc[-1]['close']
            last_time = df.index[-1]
            self.position.close(str(last_time), last_price, "End of period")
            self.balance = self.position.quantity * last_price
            print(f"[{last_time}] AUTO-CLOSE at end")
            print(f"  PnL: ${self.position.pnl:+,.2f} ({self.position.pnl_pct:+.2f}%)\n")
            self.trades.append(self.position)
            self.position = None

        # Calcula métricas
        metrics = self._calculate_metrics(df, symbol)

        # Imprime resultados
        self._print_results(metrics)

        return metrics

    def _calculate_metrics(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Calcula métricas de performance."""

        # Returns
        total_return_usd = self.balance - self.initial_balance
        total_return_pct = (total_return_usd / self.initial_balance) * 100

        # Buy & Hold baseline
        first_price = df.iloc[0]['close']
        last_price = df.iloc[-1]['close']
        bh_return_pct = ((last_price - first_price) / first_price) * 100
        bh_balance = self.initial_balance * (1 + bh_return_pct / 100)

        # Alpha (excess return vs Buy & Hold)
        alpha = total_return_pct - bh_return_pct

        # Trade stats
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl <= 0]
        win_rate = (len(winning_trades) / len(self.trades) * 100) if self.trades else 0

        # Sharpe Ratio (simplified)
        if len(self.trades) > 1:
            returns = [t.pnl_pct for t in self.trades if t.pnl_pct]
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe = 0

        # Max Drawdown (simplified)
        equity_curve = [self.initial_balance]
        current_equity = self.initial_balance
        for trade in self.trades:
            current_equity += trade.pnl if trade.pnl else 0
            equity_curve.append(current_equity)

        equity_series = pd.Series(equity_curve)
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        return {
            'symbol': symbol,
            'strategy': 'Trend Following',
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_return_usd': total_return_usd,
            'total_return_pct': total_return_pct,
            'buy_hold_return_pct': bh_return_pct,
            'buy_hold_balance': bh_balance,
            'alpha': alpha,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,
            'avg_win_pct': np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0,
            'avg_loss_pct': np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown,
            'best_trade_pct': max([t.pnl_pct for t in self.trades if t.pnl_pct], default=0),
            'worst_trade_pct': min([t.pnl_pct for t in self.trades if t.pnl_pct], default=0),
        }

    def _print_results(self, metrics: Dict):
        """Imprime resultados do backtest."""
        print(f"\n{'='*80}")
        print(f"RESULTS: {metrics['strategy']} - {metrics['symbol']}")
        print(f"{'='*80}\n")

        print(f"PERFORMANCE:")
        print(f"  Strategy Return:    {metrics['total_return_pct']:+.2f}% (${metrics['total_return_usd']:+,.2f})")
        print(f"  Buy & Hold Return:  {metrics['buy_hold_return_pct']:+.2f}%")
        print(f"  Alpha (vs B&H):     {metrics['alpha']:+.2f}%")
        print(f"  Final Balance:      ${metrics['final_balance']:,.2f}")
        print(f"  B&H Balance:        ${metrics['buy_hold_balance']:,.2f}\n")

        print(f"METRICS:")
        print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown:       {metrics['max_drawdown_pct']:.2f}%\n")

        print(f"TRADES:")
        print(f"  Total Trades:       {metrics['total_trades']}")
        print(f"  Winning:            {metrics['winning_trades']}")
        print(f"  Losing:             {metrics['losing_trades']}")
        print(f"  Win Rate:           {metrics['win_rate_pct']:.1f}%")
        print(f"  Avg Win:            {metrics['avg_win_pct']:+.2f}%")
        print(f"  Avg Loss:           {metrics['avg_loss_pct']:+.2f}%")
        print(f"  Best Trade:         {metrics['best_trade_pct']:+.2f}%")
        print(f"  Worst Trade:        {metrics['worst_trade_pct']:+.2f}%\n")

        # Veredicto
        print(f"VERDICT:")
        if metrics['alpha'] >= 10:
            print(f"  ✅ APPROVED - Alpha {metrics['alpha']:+.2f}% > 10% threshold")
        elif metrics['alpha'] >= 0:
            print(f"  ⚠️  MARGINAL - Alpha {metrics['alpha']:+.2f}% positive but < 10%")
        else:
            print(f"  ❌ REJECTED - Alpha {metrics['alpha']:+.2f}% negative (worse than B&H)")

        print(f"\n{'='*80}\n")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest Trend Following Strategy')
    parser.add_argument('--data', type=str, required=True, help='CSV file with OHLCV data')
    parser.add_argument('--symbol', type=str, default='BNB_USDT', help='Trading symbol')
    parser.add_argument('--initial-balance', type=float, default=5000.0, help='Initial capital')
    parser.add_argument('--output', type=str, help='Output JSON file for results')

    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.data}...")
    df = pd.read_csv(args.data, index_col=0, parse_dates=True)
    print(f"Loaded {len(df)} candles\n")

    # Run backtest
    strategy = TrendFollowingStrategy(initial_balance=args.initial_balance)
    metrics = strategy.backtest(df, symbol=args.symbol)

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"Results saved to {args.output}")

    return 0 if metrics['alpha'] >= 10 else 1


if __name__ == '__main__':
    sys.exit(main())
