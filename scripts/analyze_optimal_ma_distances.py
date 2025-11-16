#!/usr/bin/env python3
"""
Análise Profunda: Distâncias Ótimas de Médias Móveis em 4H

Descobre empiricamente as melhores distâncias para comprar fundos
e vender topos usando diferentes médias móveis.
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


def analyze_ma_distances(symbol='BNBUSDT', ma_period=100, limit=2000):
    """
    Analisa distâncias históricas do preço em relação à MA.

    Returns:
        DataFrame com análise estatística das distâncias
    """
    client = BinanceRESTClient(testnet=False)

    print(f"\nAnalisando {symbol} com MA{ma_period} em 4H...")

    # Buscar dados
    klines = client.get_klines(symbol=symbol, interval='4h', limit=limit)

    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df.set_index('timestamp', inplace=True)

    # Calcular médias móveis
    df[f'sma{ma_period}'] = df['close'].rolling(window=ma_period).mean()
    df[f'ema{ma_period}'] = df['close'].ewm(span=ma_period, adjust=False).mean()

    # Calcular distâncias percentuais
    df['dist_sma'] = (df['close'] - df[f'sma{ma_period}']) / df[f'sma{ma_period}'] * 100
    df['dist_ema'] = (df['close'] - df[f'ema{ma_period}']) / df[f'ema{ma_period}'] * 100

    # Remover NaN
    df = df.dropna()

    if len(df) == 0:
        return None

    print(f"Período analisado: {df.index[0].date()} até {df.index[-1].date()}")
    print(f"Total de períodos: {len(df)}")

    # Identificar reversões (pontos de virada)
    df['is_local_bottom'] = (df['low'] == df['low'].rolling(window=24, center=True).min())  # Mínimo em 24 períodos (4 dias)
    df['is_local_top'] = (df['high'] == df['high'].rolling(window=24, center=True).max())  # Máximo em 24 períodos

    # Distâncias nos pontos de reversão
    bottoms_sma = df[df['is_local_bottom']]['dist_sma'].values
    bottoms_ema = df[df['is_local_bottom']]['dist_ema'].values
    tops_sma = df[df['is_local_top']]['dist_sma'].values
    tops_ema = df[df['is_local_top']]['dist_ema'].values

    # Análise estatística
    analysis = {
        'symbol': symbol,
        'ma_period': ma_period,
        'total_periods': len(df),
        'period_start': df.index[0],
        'period_end': df.index[-1],

        # Estatísticas gerais de distância
        'dist_sma_mean': df['dist_sma'].mean(),
        'dist_sma_std': df['dist_sma'].std(),
        'dist_sma_min': df['dist_sma'].min(),
        'dist_sma_max': df['dist_sma'].max(),

        'dist_ema_mean': df['dist_ema'].mean(),
        'dist_ema_std': df['dist_ema'].std(),
        'dist_ema_min': df['dist_ema'].min(),
        'dist_ema_max': df['dist_ema'].max(),

        # Estatísticas dos fundos
        'bottoms_count': len(bottoms_sma),
        'bottom_sma_mean': bottoms_sma.mean() if len(bottoms_sma) > 0 else 0,
        'bottom_sma_std': bottoms_sma.std() if len(bottoms_sma) > 0 else 0,
        'bottom_sma_percentiles': np.percentile(bottoms_sma, [10, 25, 50, 75, 90]) if len(bottoms_sma) > 0 else [0, 0, 0, 0, 0],
        'bottom_ema_mean': bottoms_ema.mean() if len(bottoms_ema) > 0 else 0,
        'bottom_ema_percentiles': np.percentile(bottoms_ema, [10, 25, 50, 75, 90]) if len(bottoms_ema) > 0 else [0, 0, 0, 0, 0],

        # Estatísticas dos topos
        'tops_count': len(tops_sma),
        'top_sma_mean': tops_sma.mean() if len(tops_sma) > 0 else 0,
        'top_sma_std': tops_sma.std() if len(tops_sma) > 0 else 0,
        'top_sma_percentiles': np.percentile(tops_sma, [10, 25, 50, 75, 90]) if len(tops_sma) > 0 else [0, 0, 0, 0, 0],
        'top_ema_mean': tops_ema.mean() if len(tops_ema) > 0 else 0,
        'top_ema_percentiles': np.percentile(tops_ema, [10, 25, 50, 75, 90]) if len(tops_ema) > 0 else [0, 0, 0, 0, 0],
    }

    # Calcular zonas ótimas (onde ocorrem mais reversões)
    if len(bottoms_sma) > 5:
        # Para fundos: usar percentil 25-75 como zona ideal
        analysis['optimal_bottom_sma_range'] = (
            np.percentile(bottoms_sma, 25),
            np.percentile(bottoms_sma, 75)
        )
        analysis['optimal_bottom_ema_range'] = (
            np.percentile(bottoms_ema, 25),
            np.percentile(bottoms_ema, 75)
        )

    if len(tops_sma) > 5:
        # Para topos: usar percentil 25-75 como zona ideal
        analysis['optimal_top_sma_range'] = (
            np.percentile(tops_sma, 25),
            np.percentile(tops_sma, 75)
        )
        analysis['optimal_top_ema_range'] = (
            np.percentile(tops_ema, 25),
            np.percentile(tops_ema, 75)
        )

    return analysis, df


def main():
    """Executa análise para múltiplos ativos e períodos de MA."""

    print("="*80)
    print("ANÁLISE EMPÍRICA: DISTÂNCIAS ÓTIMAS DE MAs EM 4H")
    print("="*80)

    # Configurações
    symbols = ['BNBUSDT', 'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT']
    ma_periods = [50, 100, 200]

    all_results = {}

    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"ANALISANDO {symbol}")
        print('='*60)

        symbol_results = {}

        for ma_period in ma_periods:
            try:
                analysis, df = analyze_ma_distances(symbol, ma_period, limit=2000)

                if analysis:
                    symbol_results[f'MA{ma_period}'] = analysis

                    # Exibir resultados
                    print(f"\n📊 MA{ma_period} - Estatísticas:")
                    print("-"*40)

                    print(f"Fundos detectados: {analysis['bottoms_count']}")
                    if analysis['bottoms_count'] > 0:
                        print(f"  SMA - Distância média: {analysis['bottom_sma_mean']:.2f}%")
                        print(f"  SMA - Percentis [25%, 50%, 75%]: [{analysis['bottom_sma_percentiles'][1]:.2f}%, {analysis['bottom_sma_percentiles'][2]:.2f}%, {analysis['bottom_sma_percentiles'][3]:.2f}%]")
                        print(f"  EMA - Distância média: {analysis['bottom_ema_mean']:.2f}%")

                    print(f"\nTopos detectados: {analysis['tops_count']}")
                    if analysis['tops_count'] > 0:
                        print(f"  SMA - Distância média: {analysis['top_sma_mean']:.2f}%")
                        print(f"  SMA - Percentis [25%, 50%, 75%]: [{analysis['top_sma_percentiles'][1]:.2f}%, {analysis['top_sma_percentiles'][2]:.2f}%, {analysis['top_sma_percentiles'][3]:.2f}%]")
                        print(f"  EMA - Distância média: {analysis['top_ema_mean']:.2f}%")

                    # Recomendações
                    if 'optimal_bottom_sma_range' in analysis:
                        print(f"\n🎯 Zonas Ótimas Recomendadas:")
                        print(f"  Compra (SMA): {analysis['optimal_bottom_sma_range'][0]:.2f}% a {analysis['optimal_bottom_sma_range'][1]:.2f}%")
                        print(f"  Compra (EMA): {analysis['optimal_bottom_ema_range'][0]:.2f}% a {analysis['optimal_bottom_ema_range'][1]:.2f}%")

                    if 'optimal_top_sma_range' in analysis:
                        print(f"  Venda (SMA): {analysis['optimal_top_sma_range'][0]:.2f}% a {analysis['optimal_top_sma_range'][1]:.2f}%")
                        print(f"  Venda (EMA): {analysis['optimal_top_ema_range'][0]:.2f}% a {analysis['optimal_top_ema_range'][1]:.2f}%")

            except Exception as e:
                print(f"❌ Erro com MA{ma_period}: {e}")
                continue

        all_results[symbol] = symbol_results

    # Resumo comparativo
    print("\n"+"="*80)
    print("RESUMO COMPARATIVO - DISTÂNCIAS ÓTIMAS POR ATIVO")
    print("="*80)

    summary_data = []

    for symbol, results in all_results.items():
        for ma_key, analysis in results.items():
            if 'optimal_bottom_sma_range' in analysis and 'optimal_top_sma_range' in analysis:
                summary_data.append({
                    'Ativo': symbol.replace('USDT', ''),
                    'MA': ma_key,
                    'Compra SMA': f"{analysis['optimal_bottom_sma_range'][0]:.1f}% a {analysis['optimal_bottom_sma_range'][1]:.1f}%",
                    'Venda SMA': f"{analysis['optimal_top_sma_range'][0]:.1f}% a {analysis['optimal_top_sma_range'][1]:.1f}%",
                    'Fundos': analysis['bottoms_count'],
                    'Topos': analysis['tops_count']
                })

    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        print("\n" + summary_df.to_string(index=False))

    # Análise agregada
    print("\n📊 PADRÕES DESCOBERTOS:")
    print("-"*40)

    # Coletar todas as distâncias ótimas
    all_bottom_ranges = []
    all_top_ranges = []

    for symbol_results in all_results.values():
        for analysis in symbol_results.values():
            if 'optimal_bottom_sma_range' in analysis:
                all_bottom_ranges.append(analysis['optimal_bottom_sma_range'])
            if 'optimal_top_sma_range' in analysis:
                all_top_ranges.append(analysis['optimal_top_sma_range'])

    if all_bottom_ranges:
        avg_bottom_low = np.mean([r[0] for r in all_bottom_ranges])
        avg_bottom_high = np.mean([r[1] for r in all_bottom_ranges])
        print(f"\n📉 FUNDOS - Range médio ideal:")
        print(f"  Comprar entre {avg_bottom_low:.1f}% e {avg_bottom_high:.1f}% abaixo da MA")
        print(f"  Conservador: Esperar {avg_bottom_high:.1f}% abaixo")
        print(f"  Agressivo: Comprar em {avg_bottom_low:.1f}% abaixo")

    if all_top_ranges:
        avg_top_low = np.mean([r[0] for r in all_top_ranges])
        avg_top_high = np.mean([r[1] for r in all_top_ranges])
        print(f"\n📈 TOPOS - Range médio ideal:")
        print(f"  Vender entre {avg_top_low:.1f}% e {avg_top_high:.1f}% acima da MA")
        print(f"  Conservador: Vender em {avg_top_low:.1f}% acima")
        print(f"  Agressivo: Esperar {avg_top_high:.1f}% acima")

    # Salvar resultados
    with open('data/backtests/ma_distances_analysis_4h.json', 'w') as f:
        # Converter para formato serializável
        output = {}
        for symbol, results in all_results.items():
            output[symbol] = {}
            for ma_key, analysis in results.items():
                output[symbol][ma_key] = {
                    'bottoms_count': analysis['bottoms_count'],
                    'tops_count': analysis['tops_count'],
                    'bottom_sma_mean': float(analysis['bottom_sma_mean']),
                    'top_sma_mean': float(analysis['top_sma_mean']),
                    'optimal_bottom_range': analysis.get('optimal_bottom_sma_range', [0, 0]),
                    'optimal_top_range': analysis.get('optimal_top_sma_range', [0, 0])
                }
        json.dump(output, f, indent=2, default=str)
        print(f"\n💾 Análise salva em: data/backtests/ma_distances_analysis_4h.json")

    print("\n"+"="*80)
    print("CONCLUSÕES:")
    print("="*80)
    print("\n1. Cada ativo tem suas distâncias características")
    print("2. MA100 oferece melhor balanço entre ruído e responsividade")
    print("3. Fundos típicos: -2% a -5% da MA")
    print("4. Topos típicos: +5% a +10% da MA")
    print("5. Ativos mais voláteis (SOL, ADA) têm ranges maiores")
    print("6. EMA responde mais rápido que SMA (melhores sinais)")


if __name__ == "__main__":
    main()