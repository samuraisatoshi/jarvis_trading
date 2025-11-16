#!/usr/bin/env python3
"""
ESTRATÉGIA DEFINITIVA: KISS Supreme (Keep It Simple Stupid)

APRENDIZADO BRUTAL dos backtests:
- Buy & Hold venceu TODAS estratégias: +59.72%
- Trend Following: +22.36% (failed - too many trades)
- Momentum Day Trade: -23.14% (disaster)
- Fibonacci Golden Zone: -4.6% (complete failure)

CONCLUSÃO: Em crypto bull markets, simplicidade EXTREMA vence.

REGRAS ULTRA-SIMPLES:

COMPRAR:
- Apenas 1 entrada no início
- Ou: RSI < 25 (oversold extremo, raramente acontece)

VENDER:
- Apenas se RSI > 85 (overbought extremo)
- OU: EMA20 cruza abaixo EMA200 (bear market confirmado)

Timeframe: 1D (sem ruído intraday)
Position: 100% all-in (como Buy & Hold)
Objetivo: Superar Buy & Hold com MÍNIMA interferência

Meta: Alpha > 5% vs Buy & Hold (reduzido de 10% - mais realista)
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


class KISSSupremeStrategy:
    """
    KISS Supreme: A estratégia mais simples possível.

    Quase um Buy & Hold, mas com proteção mínima contra crashes.
    """

    def __init__(self, initial_balance: float = 5000.0):
        """Inicializa estratégia."""
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position: Optional[Trade] = None
        self.trades: List[Trade] = []

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula apenas indicadores ESSENCIAIS.

        Args:
            df: DataFrame com OHLCV

        Returns:
            DataFrame com indicadores
        """
        df = df.copy()

        # EMAs (apenas 20 e 200 para detectar bear market)
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # RSI (para oversold extremo)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        return df

    def check_entry_signal(self, row: pd.Series, is_first_candle: bool) -> bool:
        """
        Verifica sinal de COMPRA (raramente acontece).

        Args:
            row: Linha atual
            is_first_candle: Se é primeira candle tradeable

        Returns:
            True se deve comprar
        """
        # Precisa de indicadores
        if pd.isna(row['ema_200']):
            return False

        # COMPRAR:
        # 1. Primeira candle (igual a Buy & Hold)
        if is_first_candle:
            return True

        # 2. Oversold EXTREMO (RSI < 25) - raramente acontece
        if row['rsi'] < 25:
            return True

        return False

    def check_exit_signal(self, row: pd.Series) -> Tuple[bool, str]:
        """
        Verifica sinal de VENDA (raramente acontece).

        Returns:
            Tuple (deve_vender, razão)
        """
        # VENDER apenas se:

        # 1. Overbought EXTREMO (RSI > 85) - realizar lucros parciais
        if row['rsi'] > 85:
            return True, "RSI extreme overbought (>85)"

        # 2. Bear market confirmado (EMA20 cruza abaixo EMA200)
        if row['ema_20'] < row['ema_200']:
            return True, "Bear market confirmed (EMA20 < EMA200)"

        return False, ""

    def backtest(self, df: pd.DataFrame, symbol: str = "BNB_USDT") -> Dict:
        """
        Executa backtest da estratégia.

        Args:
            df: DataFrame com OHLCV (1D timeframe)
            symbol: Símbolo do ativo

        Returns:
            Dict com métricas de performance
        """
        print(f"\n{'='*80}")
        print(f"BACKTESTING: KISS Supreme Strategy - {symbol}")
        print(f"{'='*80}\n")
        print(f"Philosophy: Almost Buy & Hold, minimal interference")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Period: {df.index[0]} to {df.index[-1]}")
        print(f"Candles: {len(df)} (1D timeframe)\n")

        # Calcula indicadores
        df = self.calculate_indicators(df)

        # Remove primeiras 200 linhas (warm-up para EMA200)
        df = df.iloc[200:].copy()

        print(f"Trading on {len(df)} candles (after warm-up)\n")
        print("RULES:")
        print("  BUY:  First candle OR RSI < 25 (extreme oversold)")
        print("  SELL: RSI > 85 (extreme overbought) OR EMA20 < EMA200 (bear market)")
        print("  Position: 100% all-in\n")

        # Simula trading
        is_first_candle = True

        for timestamp, row in df.iterrows():
            price = row['close']

            # Sem posição - procura ENTRADA
            if self.position is None:
                if self.check_entry_signal(row, is_first_candle):
                    # Compra tudo (100%)
                    quantity = self.balance / price
                    self.position = Trade(
                        entry_time=str(timestamp),
                        entry_price=price,
                        quantity=quantity
                    )
                    self.balance = 0  # All-in
                    reason = "First entry (like Buy & Hold)" if is_first_candle else f"Extreme oversold (RSI {row['rsi']:.1f})"
                    print(f"[{timestamp.date()}] BUY: {quantity:.6f} @ ${price:.2f}")
                    print(f"  Reason: {reason}")
                    print(f"  RSI: {row['rsi']:.1f} | EMA20: ${row['ema_20']:.2f} | EMA200: ${row['ema_200']:.2f}\n")

                is_first_candle = False

            # Com posição - procura SAÍDA
            else:
                should_exit, reason = self.check_exit_signal(row)
                if should_exit:
                    # Fecha posição
                    self.position.close(str(timestamp), price, reason)
                    self.balance = self.position.quantity * price
                    print(f"[{timestamp.date()}] SELL: {reason}")
                    print(f"  PnL: ${self.position.pnl:+,.2f} ({self.position.pnl_pct:+.2f}%)")
                    print(f"  Balance: ${self.balance:,.2f}")
                    print(f"  RSI: {row['rsi']:.1f} | EMA20: ${row['ema_20']:.2f} | EMA200: ${row['ema_200']:.2f}\n")
                    self.trades.append(self.position)
                    self.position = None

        # Fecha posição aberta no final
        if self.position is not None:
            last_price = df.iloc[-1]['close']
            last_time = df.index[-1]
            self.position.close(str(last_time), last_price, "End of period")
            self.balance = self.position.quantity * last_price
            print(f"[{last_time.date()}] AUTO-CLOSE at end")
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

        # Alpha
        alpha = total_return_pct - bh_return_pct

        # Trade stats
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl <= 0]
        win_rate = (len(winning_trades) / len(self.trades) * 100) if self.trades else 0

        # Sharpe Ratio
        if len(self.trades) > 1:
            returns = [t.pnl_pct for t in self.trades if t.pnl_pct]
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe = 0

        # Max Drawdown
        equity_curve = [self.initial_balance]
        current_equity = self.initial_balance
        for trade in self.trades:
            current_equity += trade.pnl if trade.pnl else 0
            equity_curve.append(current_equity)

        if len(equity_curve) > 1:
            equity_series = pd.Series(equity_curve)
            running_max = equity_series.expanding().max()
            drawdown = (equity_series - running_max) / running_max * 100
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0

        return {
            'symbol': symbol,
            'strategy': 'KISS Supreme',
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

        if metrics['total_trades'] > 0:
            print(f"  Avg Win:            {metrics['avg_win_pct']:+.2f}%")
            print(f"  Avg Loss:           {metrics['avg_loss_pct']:+.2f}%")
            print(f"  Best Trade:         {metrics['best_trade_pct']:+.2f}%")
            print(f"  Worst Trade:        {metrics['worst_trade_pct']:+.2f}%\n")

        # Veredicto
        print(f"VERDICT:")
        if metrics['alpha'] >= 5:
            print(f"  ✅ APPROVED - Alpha {metrics['alpha']:+.2f}% >= 5% threshold")
            print(f"  🎯 SUCCESS: Simplicity beats complexity!")
        elif metrics['alpha'] >= 0:
            print(f"  ⚠️  MARGINAL - Alpha {metrics['alpha']:+.2f}% positive but < 5%")
            print(f"  💡 LEARNING: Buy & Hold remains king in bull markets")
        else:
            print(f"  ❌ REJECTED - Alpha {metrics['alpha']:+.2f}% negative")
            print(f"  🚫 Even ultra-simple strategy can't beat pure Buy & Hold")

        print(f"\n{'='*80}\n")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest KISS Supreme Strategy')
    parser.add_argument('--data', type=str, required=True, help='CSV file with OHLCV data (1D)')
    parser.add_argument('--symbol', type=str, default='BNB_USDT', help='Trading symbol')
    parser.add_argument('--initial-balance', type=float, default=5000.0, help='Initial capital')
    parser.add_argument('--output', type=str, help='Output JSON file for results')

    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.data}...")
    df = pd.read_csv(args.data, index_col=0, parse_dates=True)
    print(f"Loaded {len(df)} candles\n")

    # Run backtest
    strategy = KISSSupremeStrategy(initial_balance=args.initial_balance)
    metrics = strategy.backtest(df, symbol=args.symbol)

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"Results saved to {args.output}")

    return 0 if metrics['alpha'] >= 5 else 1


if __name__ == '__main__':
    sys.exit(main())
