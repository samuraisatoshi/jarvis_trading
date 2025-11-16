#!/usr/bin/env python3
"""
ESTRATÉGIA 2: Momentum Breakout (Day Trade)

Baseada nos aprendizados dos backtests:
- Evitar counter-trend trading (3 SHORTs em bull market = desastre)
- Simplicidade vence
- Seguir momentum forte

REGRAS KISS:

SETUP de ALTA (9:00-10:00 UTC):
- High > Yesterday High (novo topo)
- Volume > Yesterday Volume * 1.5 (volume alto)
- RSI > 50 (momentum positivo)

SAÍDA (mesmo dia):
- Tempo >= 20:00 UTC (fim do dia) OU
- Profit >= 3% (take profit) OU
- Loss >= 1.5% (stop loss)

Timeframe: 15min para entries, 1H para contexto
Risk: Máximo 1.5% por trade
Target: 3% profit (2:1 risk/reward)
Sem SHORT: Apenas LONG em crypto bull market

Meta: Win rate > 55%, Sharpe > 1.5
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import time
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
    duration_hours: Optional[float] = None

    def close(self, exit_time: str, exit_price: float, reason: str):
        """Fecha o trade."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason
        self.pnl = (exit_price - self.entry_price) * self.quantity
        self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100

        # Duration
        entry_dt = pd.to_datetime(self.entry_time)
        exit_dt = pd.to_datetime(exit_time)
        self.duration_hours = (exit_dt - entry_dt).total_seconds() / 3600


class MomentumDayTradeStrategy:
    """
    Estratégia de Day Trade baseada em Momentum Breakout.

    Objetivo: Capturar movimentos intraday fortes com risco controlado.
    """

    def __init__(self, initial_balance: float = 5000.0, risk_per_trade: float = 0.015):
        """
        Inicializa estratégia.

        Args:
            initial_balance: Capital inicial
            risk_per_trade: Risco por trade (default 1.5%)
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.position: Optional[Trade] = None
        self.trades: List[Trade] = []

        # Parâmetros
        self.entry_window = (time(9, 0), time(10, 0))  # 9:00-10:00 UTC
        self.exit_time = time(20, 0)  # 20:00 UTC
        self.take_profit = 0.03  # 3%
        self.stop_loss = 0.015  # 1.5%

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores necessários.

        Args:
            df: DataFrame com OHLCV (15min timeframe)

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

        # Yesterday high/volume (usando shift de 96 períodos = 24h em 15min)
        df['yesterday_high'] = df['high'].shift(96).rolling(window=96).max()
        df['yesterday_volume'] = df['volume'].shift(96).rolling(window=96).sum()

        return df

    def check_entry_signal(self, row: pd.Series, current_time: pd.Timestamp) -> bool:
        """
        Verifica sinal de ENTRADA.

        Args:
            row: Linha atual do DataFrame
            current_time: Timestamp atual

        Returns:
            True se deve entrar
        """
        # Apenas na janela de entrada (9:00-10:00 UTC)
        current_hour_min = current_time.time()
        if not (self.entry_window[0] <= current_hour_min <= self.entry_window[1]):
            return False

        # Precisa de indicadores válidos
        if pd.isna(row['yesterday_high']) or pd.isna(row['yesterday_volume']):
            return False

        # Regras de entrada:
        new_high = row['high'] > row['yesterday_high']
        volume_spike = row['volume'] > row['yesterday_volume'] * 0.015  # Ajustado para 15min
        momentum = row['rsi'] > 50

        return new_high and volume_spike and momentum

    def check_exit_signal(
        self,
        row: pd.Series,
        current_time: pd.Timestamp,
        entry_price: float
    ) -> Tuple[bool, str]:
        """
        Verifica sinal de SAÍDA.

        Args:
            row: Linha atual do DataFrame
            current_time: Timestamp atual
            entry_price: Preço de entrada

        Returns:
            Tuple (deve_sair, razão)
        """
        price = row['close']

        # 1. Fim do dia (20:00 UTC)
        if current_time.time() >= self.exit_time:
            return True, "End of day"

        # 2. Take Profit (3%)
        if price >= entry_price * (1 + self.take_profit):
            return True, "Take profit (3%)"

        # 3. Stop Loss (1.5%)
        if price <= entry_price * (1 - self.stop_loss):
            return True, "Stop loss (1.5%)"

        return False, ""

    def backtest(self, df: pd.DataFrame, symbol: str = "BNB_USDT") -> Dict:
        """
        Executa backtest da estratégia.

        Args:
            df: DataFrame com OHLCV (15min timeframe)
            symbol: Símbolo do ativo

        Returns:
            Dict com métricas de performance
        """
        print(f"\n{'='*80}")
        print(f"BACKTESTING: Momentum Day Trade - {symbol}")
        print(f"{'='*80}\n")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Period: {df.index[0]} to {df.index[-1]}")
        print(f"Candles: {len(df)} (15min timeframe)\n")
        print(f"Risk per trade: {self.risk_per_trade:.1%}")
        print(f"Entry window: {self.entry_window[0]} - {self.entry_window[1]} UTC")
        print(f"Exit time: {self.exit_time} UTC")
        print(f"Take Profit: {self.take_profit:.1%}")
        print(f"Stop Loss: {self.stop_loss:.1%}\n")

        # Calcula indicadores
        df = self.calculate_indicators(df)

        # Remove primeiras 24h (warm-up)
        df = df.iloc[96:].copy()

        print(f"Trading on {len(df)} candles (after warm-up)\n")

        # Simula trading
        for timestamp, row in df.iterrows():
            price = row['close']

            # Sem posição - procura ENTRADA
            if self.position is None:
                if self.check_entry_signal(row, timestamp):
                    # Calcula position size (risco de 1.5%)
                    risk_amount = self.balance * self.risk_per_trade
                    quantity = risk_amount / (price * self.stop_loss)

                    # Garante que não usa mais que o capital disponível
                    max_quantity = self.balance / price
                    quantity = min(quantity, max_quantity)

                    cost = quantity * price
                    self.position = Trade(
                        entry_time=str(timestamp),
                        entry_price=price,
                        quantity=quantity
                    )
                    self.balance -= cost
                    print(f"[{timestamp}] BUY: {quantity:.6f} @ ${price:.2f}")
                    print(f"  Cost: ${cost:.2f} | Remaining: ${self.balance:.2f}")
                    print(f"  RSI: {row['rsi']:.1f} | High: ${row['high']:.2f} vs Yesterday: ${row['yesterday_high']:.2f}")

            # Com posição - procura SAÍDA
            else:
                should_exit, reason = self.check_exit_signal(row, timestamp, self.position.entry_price)
                if should_exit:
                    # Fecha posição
                    self.position.close(str(timestamp), price, reason)
                    proceeds = self.position.quantity * price
                    self.balance += proceeds
                    print(f"[{timestamp}] SELL: {reason}")
                    print(f"  PnL: ${self.position.pnl:+,.2f} ({self.position.pnl_pct:+.2f}%)")
                    print(f"  Duration: {self.position.duration_hours:.1f}h")
                    print(f"  Balance: ${self.balance:,.2f}\n")
                    self.trades.append(self.position)
                    self.position = None

        # Fecha posição aberta no final
        if self.position is not None:
            last_price = df.iloc[-1]['close']
            last_time = df.index[-1]
            self.position.close(str(last_time), last_price, "End of period")
            proceeds = self.position.quantity * last_price
            self.balance += proceeds
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

        # Avg trade duration
        durations = [t.duration_hours for t in self.trades if t.duration_hours]
        avg_duration = np.mean(durations) if durations else 0

        return {
            'symbol': symbol,
            'strategy': 'Momentum Day Trade',
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_return_usd': total_return_usd,
            'total_return_pct': total_return_pct,
            'buy_hold_return_pct': bh_return_pct,
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
            'avg_duration_hours': avg_duration,
        }

    def _print_results(self, metrics: Dict):
        """Imprime resultados do backtest."""
        print(f"\n{'='*80}")
        print(f"RESULTS: {metrics['strategy']} - {metrics['symbol']}")
        print(f"{'='*80}\n")

        print(f"PERFORMANCE:")
        print(f"  Total Return:       {metrics['total_return_pct']:+.2f}% (${metrics['total_return_usd']:+,.2f})")
        print(f"  Buy & Hold Return:  {metrics['buy_hold_return_pct']:+.2f}%")
        print(f"  Final Balance:      ${metrics['final_balance']:,.2f}\n")

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
        print(f"  Worst Trade:        {metrics['worst_trade_pct']:+.2f}%")
        print(f"  Avg Duration:       {metrics['avg_duration_hours']:.1f}h\n")

        # Veredicto
        print(f"VERDICT:")
        if metrics['win_rate_pct'] >= 55 and metrics['sharpe_ratio'] >= 1.5:
            print(f"  ✅ APPROVED - Win Rate {metrics['win_rate_pct']:.1f}% > 55% AND Sharpe {metrics['sharpe_ratio']:.2f} > 1.5")
        elif metrics['win_rate_pct'] >= 55 or metrics['sharpe_ratio'] >= 1.5:
            print(f"  ⚠️  MARGINAL - Win Rate {metrics['win_rate_pct']:.1f}% OR Sharpe {metrics['sharpe_ratio']:.2f} meets threshold")
        else:
            print(f"  ❌ REJECTED - Win Rate {metrics['win_rate_pct']:.1f}% < 55% AND Sharpe {metrics['sharpe_ratio']:.2f} < 1.5")

        print(f"\n{'='*80}\n")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest Momentum Day Trade Strategy')
    parser.add_argument('--data', type=str, required=True, help='CSV file with OHLCV data (15min)')
    parser.add_argument('--symbol', type=str, default='BNB_USDT', help='Trading symbol')
    parser.add_argument('--initial-balance', type=float, default=5000.0, help='Initial capital')
    parser.add_argument('--risk-per-trade', type=float, default=0.015, help='Risk per trade (default 1.5%)')
    parser.add_argument('--output', type=str, help='Output JSON file for results')

    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.data}...")
    df = pd.read_csv(args.data, index_col=0, parse_dates=True)
    print(f"Loaded {len(df)} candles (15min timeframe)\n")

    # Run backtest
    strategy = MomentumDayTradeStrategy(
        initial_balance=args.initial_balance,
        risk_per_trade=args.risk_per_trade
    )
    metrics = strategy.backtest(df, symbol=args.symbol)

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"Results saved to {args.output}")

    # Aprovado se Win Rate > 55% E Sharpe > 1.5
    approved = metrics['win_rate_pct'] >= 55 and metrics['sharpe_ratio'] >= 1.5
    return 0 if approved else 1


if __name__ == '__main__':
    sys.exit(main())
