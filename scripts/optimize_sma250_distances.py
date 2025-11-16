#!/usr/bin/env python3
"""
Otimização de Distâncias Ideais da SMA250 para Fundos e Topos

Testa múltiplas combinações de percentuais para encontrar a configuração
ótima por ativo no timeframe de 4 horas.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
from itertools import product
from typing import Dict, List, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


class SMA250Optimizer:
    """Otimizador de parâmetros para estratégia baseada em SMA250."""

    def __init__(self):
        self.client = BinanceRESTClient(testnet=False)
        self.results_cache = {}

    def fetch_data(self, symbol='BNBUSDT', interval='4h', limit=2000):
        """Busca dados históricos de 4h."""
        print(f"Buscando {limit} velas 4h de {symbol}...")

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

        # Calcular SMA250
        df['sma250'] = df['close'].rolling(window=250).mean()

        # Calcular distância percentual da SMA250
        df['dist_sma250'] = (df['close'] - df['sma250']) / df['sma250'] * 100

        return df

    def simulate_strategy(self, df, bottom_pct=-3, top_pct=10, initial_capital=10000):
        """
        Simula estratégia com parâmetros específicos.

        Args:
            df: DataFrame com dados e SMA250
            bottom_pct: % abaixo da SMA250 para comprar
            top_pct: % acima da SMA250 para vender
            initial_capital: Capital inicial

        Returns:
            Dict com métricas de performance
        """
        # Identificar sinais
        df['is_bottom'] = df['dist_sma250'] <= bottom_pct
        df['is_top'] = df['dist_sma250'] >= top_pct

        # Marcar pontos de entrada e saída
        df['buy_signal'] = df['is_bottom'] & ~df['is_bottom'].shift(1, fill_value=False)
        df['sell_signal'] = df['is_top'] & ~df['is_top'].shift(1, fill_value=False)

        # Simular trades
        trades = []
        position = None
        capital = initial_capital
        shares = 0
        max_drawdown = 0
        peak_capital = initial_capital

        for idx, row in df.iterrows():
            # Skip if SMA250 not yet calculated
            if pd.isna(row['sma250']):
                continue

            # Compra
            if row['buy_signal'] and position is None:
                shares = capital / row['close']
                position = {
                    'entry_date': idx,
                    'entry_price': row['close'],
                    'entry_sma250': row['sma250'],
                    'shares': shares,
                    'capital_invested': capital
                }
                capital = 0

            # Venda
            elif row['sell_signal'] and position is not None:
                exit_value = shares * row['close']
                profit = exit_value - position['capital_invested']
                profit_pct = (profit / position['capital_invested']) * 100

                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': idx,
                    'entry_price': position['entry_price'],
                    'exit_price': row['close'],
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'days_held': (idx - position['entry_date']).total_seconds() / (3600 * 24)
                })

                capital = exit_value
                shares = 0
                position = None

                # Track max drawdown
                peak_capital = max(peak_capital, capital)
                drawdown = (peak_capital - capital) / peak_capital * 100
                max_drawdown = max(max_drawdown, drawdown)

        # Valor final
        if position is not None:
            final_value = shares * df.iloc[-1]['close']
        else:
            final_value = capital

        # Calcular métricas
        total_return = (final_value - initial_capital) / initial_capital * 100

        if trades:
            win_rate = len([t for t in trades if t['profit'] > 0]) / len(trades) * 100
            avg_profit = np.mean([t['profit_pct'] for t in trades])
            avg_days = np.mean([t['days_held'] for t in trades])
            profit_factor = sum([t['profit'] for t in trades if t['profit'] > 0]) / abs(sum([t['profit'] for t in trades if t['profit'] < 0])) if any(t['profit'] < 0 for t in trades) else float('inf')
        else:
            win_rate = 0
            avg_profit = 0
            avg_days = 0
            profit_factor = 0

        # Buy & Hold comparison
        buy_hold_return = (df.iloc[-1]['close'] - df.iloc[250]['close']) / df.iloc[250]['close'] * 100 if len(df) > 250 else 0

        # Tempo no mercado
        total_periods = len(df[250:])  # After SMA250 available
        periods_in_position = sum(1 for _, row in df[250:].iterrows()
                                 if position is not None or any(t['entry_date'] <= row.name <= t['exit_date'] for t in trades))
        time_in_market = (periods_in_position / total_periods * 100) if total_periods > 0 else 0

        return {
            'bottom_pct': bottom_pct,
            'top_pct': top_pct,
            'total_return': total_return,
            'num_trades': len(trades),
            'win_rate': win_rate,
            'avg_profit_per_trade': avg_profit,
            'avg_days_held': avg_days,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'buy_hold_return': buy_hold_return,
            'alpha': total_return - buy_hold_return,
            'time_in_market_pct': time_in_market,
            'sharpe_ratio': (total_return / max_drawdown) if max_drawdown > 0 else total_return / 10
        }

    def optimize_parameters(self, symbol='BNBUSDT', limit=2000):
        """
        Testa múltiplas combinações de parâmetros para encontrar o ideal.

        Returns:
            DataFrame com todos os resultados ordenados por performance
        """
        # Buscar dados
        df = self.fetch_data(symbol, '4h', limit)

        print(f"\nTestando combinações para {symbol}...")
        print(f"Período: {df.index[0].date()} até {df.index[-1].date()}")
        print(f"Total de períodos: {len(df)}")

        # Definir ranges de parâmetros para testar
        bottom_range = np.arange(-10, -0.5, 0.5)  # -10% até -0.5%
        top_range = np.arange(2, 20, 1)           # 2% até 20%

        results = []
        total_combinations = len(bottom_range) * len(top_range)
        tested = 0

        # Testar todas as combinações
        for bottom, top in product(bottom_range, top_range):
            tested += 1
            if tested % 100 == 0:
                print(f"  Testadas {tested}/{total_combinations} combinações...")

            try:
                result = self.simulate_strategy(df, bottom, top)
                result['symbol'] = symbol
                results.append(result)
            except Exception as e:
                continue

        # Converter para DataFrame e ordenar
        results_df = pd.DataFrame(results)

        # Filtrar resultados válidos (pelo menos 3 trades)
        results_df = results_df[results_df['num_trades'] >= 3]

        # Criar score composto
        results_df['score'] = (
            results_df['total_return'] * 0.4 +           # 40% peso no retorno
            results_df['win_rate'] * 0.2 +               # 20% peso na win rate
            results_df['alpha'] * 0.2 +                  # 20% peso no alpha
            (100 - results_df['max_drawdown']) * 0.1 +   # 10% peso no drawdown
            results_df['sharpe_ratio'] * 0.1             # 10% peso no Sharpe
        )

        # Ordenar por score
        results_df = results_df.sort_values('score', ascending=False)

        return results_df

    def find_optimal_by_criteria(self, results_df):
        """
        Encontra configurações ótimas por diferentes critérios.

        Returns:
            Dict com melhores configurações por critério
        """
        optimal = {}

        # Maior retorno absoluto
        optimal['max_return'] = results_df.iloc[0] if len(results_df) > 0 else None

        # Maior alpha (vs Buy & Hold)
        optimal['max_alpha'] = results_df.nlargest(1, 'alpha').iloc[0] if len(results_df) > 0 else None

        # Melhor win rate (mínimo 5 trades)
        filtered = results_df[results_df['num_trades'] >= 5]
        optimal['best_win_rate'] = filtered.nlargest(1, 'win_rate').iloc[0] if len(filtered) > 0 else None

        # Melhor Sharpe ratio
        optimal['best_sharpe'] = results_df.nlargest(1, 'sharpe_ratio').iloc[0] if len(results_df) > 0 else None

        # Mais trades (liquidez)
        optimal['most_liquid'] = results_df.nlargest(1, 'num_trades').iloc[0] if len(results_df) > 0 else None

        # Balanceado (score composto)
        optimal['balanced'] = results_df.iloc[0] if len(results_df) > 0 else None

        return optimal


def main():
    """Executa otimização para múltiplos ativos."""

    print("=" * 80)
    print("OTIMIZAÇÃO DE DISTÂNCIAS SMA250 - TIMEFRAME 4H")
    print("=" * 80)

    optimizer = SMA250Optimizer()

    # Ativos para analisar
    symbols = ['BNBUSDT', 'BTCUSDT', 'ETHUSDT']

    all_results = {}
    optimal_configs = {}

    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"ANALISANDO {symbol}")
        print('='*60)

        try:
            # Otimizar parâmetros
            results_df = optimizer.optimize_parameters(symbol, limit=2000)

            if len(results_df) == 0:
                print(f"❌ Sem resultados válidos para {symbol}")
                continue

            # Salvar todos os resultados
            all_results[symbol] = results_df

            # Encontrar configurações ótimas
            optimal = optimizer.find_optimal_by_criteria(results_df)
            optimal_configs[symbol] = optimal

            # Exibir top 5 configurações
            print(f"\n🏆 TOP 5 CONFIGURAÇÕES - {symbol}:")
            print("-" * 60)

            for i, row in results_df.head(5).iterrows():
                print(f"\n#{results_df.index.get_loc(i) + 1}: Fundo {row['bottom_pct']:.1f}% | Topo {row['top_pct']:.1f}%")
                print(f"  Retorno: {row['total_return']:.2f}%")
                print(f"  Alpha vs B&H: {row['alpha']:+.2f}%")
                print(f"  Trades: {row['num_trades']:.0f}")
                print(f"  Win Rate: {row['win_rate']:.1f}%")
                print(f"  Max Drawdown: {row['max_drawdown']:.2f}%")
                print(f"  Sharpe: {row['sharpe_ratio']:.2f}")

            # Exibir configuração ótima balanceada
            if optimal['balanced'] is not None:
                best = optimal['balanced']
                print(f"\n✅ CONFIGURAÇÃO ÓTIMA BALANCEADA:")
                print(f"  Comprar: {best['bottom_pct']:.1f}% abaixo da SMA250")
                print(f"  Vender: {best['top_pct']:.1f}% acima da SMA250")
                print(f"  Performance esperada: {best['total_return']:.2f}%")
                print(f"  Vs Buy & Hold: {best['alpha']:+.2f}%")

            # Salvar resultados detalhados
            output_file = f"data/backtests/sma250_optimization_{symbol}_4h.csv"
            results_df.to_csv(output_file, index=False)
            print(f"\n💾 Resultados salvos em: {output_file}")

        except Exception as e:
            print(f"❌ Erro ao analisar {symbol}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Resumo final comparativo
    print("\n" + "="*80)
    print("RESUMO COMPARATIVO - CONFIGURAÇÕES ÓTIMAS POR ATIVO")
    print("="*80)

    summary = []
    for symbol in symbols:
        if symbol in optimal_configs and optimal_configs[symbol]['balanced'] is not None:
            best = optimal_configs[symbol]['balanced']
            summary.append({
                'Ativo': symbol.replace('USDT', ''),
                'Fundo (%)': f"{best['bottom_pct']:.1f}",
                'Topo (%)': f"{best['top_pct']:.1f}",
                'Retorno (%)': f"{best['total_return']:.1f}",
                'Alpha (%)': f"{best['alpha']:+.1f}",
                'Trades': int(best['num_trades']),
                'Win Rate (%)': f"{best['win_rate']:.1f}",
                'Sharpe': f"{best['sharpe_ratio']:.2f}"
            })

    if summary:
        summary_df = pd.DataFrame(summary)
        print("\n" + summary_df.to_string(index=False))

        # Análise de padrões
        print("\n📊 ANÁLISE DE PADRÕES:")
        print("-" * 40)

        # Médias por ativo
        for symbol in symbols:
            if symbol in all_results:
                df = all_results[symbol]
                top10 = df.head(10)

                print(f"\n{symbol.replace('USDT', '')}:")
                print(f"  Fundo médio ideal: {top10['bottom_pct'].mean():.1f}%")
                print(f"  Topo médio ideal: {top10['top_pct'].mean():.1f}%")
                print(f"  Range típico: [{top10['bottom_pct'].min():.1f}% a {top10['bottom_pct'].max():.1f}%] → [{top10['top_pct'].min():.1f}% a {top10['top_pct'].max():.1f}%]")

    # Salvar resumo geral
    with open('data/backtests/sma250_optimal_configs_4h.json', 'w') as f:
        # Converter para formato serializável
        output = {}
        for symbol, configs in optimal_configs.items():
            output[symbol] = {}
            for criteria, config in configs.items():
                if config is not None:
                    output[symbol][criteria] = {
                        'bottom_pct': float(config['bottom_pct']),
                        'top_pct': float(config['top_pct']),
                        'total_return': float(config['total_return']),
                        'alpha': float(config['alpha']),
                        'num_trades': int(config['num_trades']),
                        'win_rate': float(config['win_rate']),
                        'sharpe_ratio': float(config['sharpe_ratio'])
                    }

        json.dump(output, f, indent=2)
        print(f"\n📊 Configurações ótimas salvas em: data/backtests/sma250_optimal_configs_4h.json")

    print("\n" + "="*80)
    print("CONCLUSÕES:")
    print("="*80)
    print("\n1. Cada ativo tem sua configuração ótima específica")
    print("2. Timeframe 4h permite mais trades que diário")
    print("3. Parâmetros mais agressivos (menores) = mais trades")
    print("4. Balance entre retorno, win rate e drawdown é crucial")
    print("5. SMA250 em 4h = 250 * 4 = 1000 horas ≈ 41 dias de referência")


if __name__ == "__main__":
    main()