#!/usr/bin/env python3
"""
Análise de Estratégia: Comprar Fundos e Vender Topos

Definições:
- FUNDO: Preço 5% abaixo da EMA 200
- TOPO: Preço 15% acima da EMA 250

Objetivo: Calcular o retorno potencial desta estratégia
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


class BottomTopAnalyzer:
    """Analisa estratégia de compra em fundos e venda em topos."""

    def __init__(self, bottom_threshold=-0.05, top_threshold=0.15):
        """
        Inicializa analisador.

        Args:
            bottom_threshold: % abaixo da EMA 200 para considerar fundo (-0.05 = -5%)
            top_threshold: % acima da EMA 250 para considerar topo (0.15 = +15%)
        """
        self.bottom_threshold = bottom_threshold
        self.top_threshold = top_threshold
        self.client = BinanceRESTClient(testnet=False)

    def fetch_data(self, symbol='BNBUSDT', interval='1d', limit=1000):
        """Busca dados históricos."""
        print(f"Buscando {limit} velas de {symbol} {interval}...")

        klines = self.client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

        df = pd.DataFrame(klines)
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df.set_index('timestamp', inplace=True)

        return df

    def calculate_signals(self, df):
        """
        Calcula sinais de compra (fundo) e venda (topo).

        Returns:
            DataFrame com sinais e métricas
        """
        # Calcular EMAs
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['ema_250'] = df['close'].ewm(span=250, adjust=False).mean()

        # Calcular distância percentual das EMAs
        df['dist_ema_200'] = (df['close'] - df['ema_200']) / df['ema_200']
        df['dist_ema_250'] = (df['close'] - df['ema_250']) / df['ema_250']

        # Identificar fundos e topos
        df['is_bottom'] = df['dist_ema_200'] <= self.bottom_threshold
        df['is_top'] = df['dist_ema_250'] >= self.top_threshold

        # Marcar pontos exatos de entrada e saída
        df['buy_signal'] = df['is_bottom'] & ~df['is_bottom'].shift(1, fill_value=False)
        df['sell_signal'] = df['is_top'] & ~df['is_top'].shift(1, fill_value=False)

        return df

    def simulate_trades(self, df, initial_capital=10000):
        """
        Simula trades baseados nos sinais.

        Args:
            df: DataFrame com sinais
            initial_capital: Capital inicial em USD

        Returns:
            Dict com resultados da simulação
        """
        trades = []
        position = None
        capital = initial_capital
        shares = 0

        for idx, row in df.iterrows():
            # Compra no fundo
            if row['buy_signal'] and position is None:
                shares = capital / row['close']
                position = {
                    'entry_date': idx,
                    'entry_price': row['close'],
                    'entry_ema200': row['ema_200'],
                    'shares': shares,
                    'capital_invested': capital
                }
                capital = 0

            # Venda no topo
            elif row['sell_signal'] and position is not None:
                exit_value = shares * row['close']
                profit = exit_value - position['capital_invested']
                profit_pct = (profit / position['capital_invested']) * 100

                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': idx,
                    'entry_price': position['entry_price'],
                    'exit_price': row['close'],
                    'exit_ema250': row['ema_250'],
                    'shares': position['shares'],
                    'invested': position['capital_invested'],
                    'exit_value': exit_value,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'days_held': (idx - position['entry_date']).days
                })

                capital = exit_value
                shares = 0
                position = None

        # Se ainda tem posição aberta
        if position is not None:
            current_value = shares * df.iloc[-1]['close']
            unrealized_profit = current_value - position['capital_invested']
            unrealized_pct = (unrealized_profit / position['capital_invested']) * 100
        else:
            current_value = capital
            unrealized_profit = 0
            unrealized_pct = 0

        # Calcular métricas
        if trades:
            total_profit = sum(t['profit'] for t in trades)
            avg_profit_per_trade = np.mean([t['profit_pct'] for t in trades])
            win_rate = len([t for t in trades if t['profit'] > 0]) / len(trades) * 100
            best_trade = max(trades, key=lambda x: x['profit_pct'])
            worst_trade = min(trades, key=lambda x: x['profit_pct'])
            avg_days_held = np.mean([t['days_held'] for t in trades])
        else:
            total_profit = 0
            avg_profit_per_trade = 0
            win_rate = 0
            best_trade = None
            worst_trade = None
            avg_days_held = 0

        # Buy & Hold comparison
        buy_hold_shares = initial_capital / df.iloc[0]['close']
        buy_hold_value = buy_hold_shares * df.iloc[-1]['close']
        buy_hold_profit = buy_hold_value - initial_capital
        buy_hold_pct = (buy_hold_profit / initial_capital) * 100

        return {
            'trades': trades,
            'num_trades': len(trades),
            'initial_capital': initial_capital,
            'final_value': current_value,
            'total_profit': total_profit + unrealized_profit,
            'total_return_pct': ((current_value - initial_capital) / initial_capital) * 100,
            'avg_profit_per_trade': avg_profit_per_trade,
            'win_rate': win_rate,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_days_held': avg_days_held,
            'position_open': position is not None,
            'unrealized_profit': unrealized_profit,
            'unrealized_pct': unrealized_pct,
            'buy_hold_value': buy_hold_value,
            'buy_hold_profit': buy_hold_profit,
            'buy_hold_return_pct': buy_hold_pct,
            'alpha': ((current_value - initial_capital) / initial_capital) * 100 - buy_hold_pct
        }

    def analyze_symbol(self, symbol='BNBUSDT', timeframe='1d', limit=1000):
        """
        Análise completa para um símbolo.

        Returns:
            Dict com todos os resultados
        """
        # Buscar dados
        df = self.fetch_data(symbol, timeframe, limit)
        print(f"Dados de {df.index[0].date()} até {df.index[-1].date()}")

        # Calcular sinais
        df = self.calculate_signals(df)

        # Contar ocorrências
        num_bottoms = df['buy_signal'].sum()
        num_tops = df['sell_signal'].sum()

        print(f"\nSinais detectados:")
        print(f"  Fundos (compra): {num_bottoms}")
        print(f"  Topos (venda): {num_tops}")

        # Simular trades
        results = self.simulate_trades(df)

        # Adicionar informações do período
        results['period_start'] = df.index[0]
        results['period_end'] = df.index[-1]
        results['days_analyzed'] = (df.index[-1] - df.index[0]).days
        results['symbol'] = symbol
        results['bottom_threshold'] = self.bottom_threshold
        results['top_threshold'] = self.top_threshold

        # Estatísticas dos pontos de entrada/saída
        bottom_prices = df[df['buy_signal']]['close'].tolist()
        top_prices = df[df['sell_signal']]['close'].tolist()

        if bottom_prices:
            results['avg_bottom_price'] = np.mean(bottom_prices)
            results['min_bottom_price'] = min(bottom_prices)
            results['max_bottom_price'] = max(bottom_prices)

        if top_prices:
            results['avg_top_price'] = np.mean(top_prices)
            results['min_top_price'] = min(top_prices)
            results['max_top_price'] = max(top_prices)

        return results, df


def main():
    """Executa análise para múltiplos símbolos."""

    print("=" * 80)
    print("ANÁLISE: COMPRAR FUNDOS (-5% EMA200) E VENDER TOPOS (+15% EMA250)")
    print("=" * 80)

    analyzer = BottomTopAnalyzer(
        bottom_threshold=-0.05,  # -5% abaixo da EMA 200
        top_threshold=0.15        # +15% acima da EMA 250
    )

    # Analisar múltiplos timeframes e períodos
    configs = [
        ('BNBUSDT', '1d', 1000),  # ~3 anos diário
        ('BNBUSDT', '4h', 1000),  # ~6 meses 4h
        ('BTCUSDT', '1d', 1000),  # Bitcoin comparação
        ('ETHUSDT', '1d', 1000),  # Ethereum comparação
    ]

    all_results = {}

    for symbol, timeframe, limit in configs:
        print(f"\n{'='*60}")
        print(f"Analisando {symbol} {timeframe}")
        print('='*60)

        try:
            results, df = analyzer.analyze_symbol(symbol, timeframe, limit)
            all_results[f"{symbol}_{timeframe}"] = results

            # Exibir resultados
            print(f"\n📊 RESULTADOS - {symbol} {timeframe}")
            print(f"Período: {results['period_start'].date()} até {results['period_end'].date()}")
            print(f"Dias analisados: {results['days_analyzed']}")

            print(f"\n📈 PERFORMANCE:")
            print(f"Capital inicial: ${results['initial_capital']:,.2f}")
            print(f"Valor final: ${results['final_value']:,.2f}")
            print(f"Lucro total: ${results['total_profit']:,.2f}")
            print(f"Retorno: {results['total_return_pct']:.2f}%")

            print(f"\n🎯 TRADES:")
            print(f"Total de trades: {results['num_trades']}")
            if results['num_trades'] > 0:
                print(f"Taxa de acerto: {results['win_rate']:.1f}%")
                print(f"Lucro médio por trade: {results['avg_profit_per_trade']:.2f}%")
                print(f"Dias médios por trade: {results['avg_days_held']:.1f}")

                if results['best_trade']:
                    print(f"\nMelhor trade:")
                    print(f"  Entrada: ${results['best_trade']['entry_price']:.2f} ({results['best_trade']['entry_date'].date()})")
                    print(f"  Saída: ${results['best_trade']['exit_price']:.2f} ({results['best_trade']['exit_date'].date()})")
                    print(f"  Lucro: {results['best_trade']['profit_pct']:.2f}%")

                if results['worst_trade']:
                    print(f"\nPior trade:")
                    print(f"  Entrada: ${results['worst_trade']['entry_price']:.2f} ({results['worst_trade']['entry_date'].date()})")
                    print(f"  Saída: ${results['worst_trade']['exit_price']:.2f} ({results['worst_trade']['exit_date'].date()})")
                    print(f"  Lucro: {results['worst_trade']['profit_pct']:.2f}%")

            print(f"\n🆚 COMPARAÇÃO COM BUY & HOLD:")
            print(f"Buy & Hold: {results['buy_hold_return_pct']:.2f}%")
            print(f"Bottom/Top Strategy: {results['total_return_pct']:.2f}%")
            print(f"Alpha: {results['alpha']:.2f}%")

            if results['alpha'] > 0:
                print("✅ ESTRATÉGIA VENCEU BUY & HOLD!")
            else:
                print("❌ Buy & Hold foi superior")

            # Salvar trades detalhados
            if results['trades']:
                trades_df = pd.DataFrame(results['trades'])
                output_file = f"data/backtests/bottom_top_trades_{symbol}_{timeframe}.csv"
                trades_df.to_csv(output_file, index=False)
                print(f"\n💾 Trades salvos em: {output_file}")

        except Exception as e:
            print(f"❌ Erro ao analisar {symbol}: {e}")
            continue

    # Resumo final
    print("\n" + "="*80)
    print("RESUMO FINAL - TODOS OS ATIVOS")
    print("="*80)

    for key, result in all_results.items():
        print(f"\n{key}:")
        print(f"  Retorno Bottom/Top: {result['total_return_pct']:.2f}%")
        print(f"  Retorno Buy & Hold: {result['buy_hold_return_pct']:.2f}%")
        print(f"  Alpha: {result['alpha']:+.2f}%")
        print(f"  Trades: {result['num_trades']}")
        print(f"  Win Rate: {result['win_rate']:.1f}%")

    # Salvar resultados completos
    with open('data/backtests/bottom_top_analysis.json', 'w') as f:
        # Converter dates para string
        for key in all_results:
            for trade in all_results[key]['trades']:
                trade['entry_date'] = trade['entry_date'].isoformat()
                trade['exit_date'] = trade['exit_date'].isoformat()
            all_results[key]['period_start'] = all_results[key]['period_start'].isoformat()
            all_results[key]['period_end'] = all_results[key]['period_end'].isoformat()
            if all_results[key]['best_trade']:
                all_results[key]['best_trade']['entry_date'] = all_results[key]['best_trade']['entry_date']
                all_results[key]['best_trade']['exit_date'] = all_results[key]['best_trade']['exit_date']
            if all_results[key]['worst_trade']:
                all_results[key]['worst_trade']['entry_date'] = all_results[key]['worst_trade']['entry_date']
                all_results[key]['worst_trade']['exit_date'] = all_results[key]['worst_trade']['exit_date']

        json.dump(all_results, f, indent=2, default=str)
        print(f"\n📊 Análise completa salva em: data/backtests/bottom_top_analysis.json")


if __name__ == "__main__":
    main()