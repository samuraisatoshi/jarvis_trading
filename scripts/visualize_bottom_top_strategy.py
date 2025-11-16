#!/usr/bin/env python3
"""
Visualização da Estratégia Bottom/Top com EMAs
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


def create_visualization():
    """Cria gráfico mostrando os pontos de entrada e saída."""

    # Buscar dados
    client = BinanceRESTClient(testnet=False)
    klines = client.get_klines(symbol='BNBUSDT', interval='1d', limit=1000)

    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close'] = df['close'].astype(float)
    df.set_index('timestamp', inplace=True)

    # Calcular EMAs
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_250'] = df['close'].ewm(span=250, adjust=False).mean()

    # Calcular limites
    df['bottom_limit'] = df['ema_200'] * 0.95  # -5%
    df['top_limit'] = df['ema_250'] * 1.15     # +15%

    # Identificar sinais
    df['dist_ema_200'] = (df['close'] - df['ema_200']) / df['ema_200']
    df['dist_ema_250'] = (df['close'] - df['ema_250']) / df['ema_250']
    df['is_bottom'] = df['dist_ema_200'] <= -0.05
    df['is_top'] = df['dist_ema_250'] >= 0.15
    df['buy_signal'] = df['is_bottom'] & ~df['is_bottom'].shift(1, fill_value=False)
    df['sell_signal'] = df['is_top'] & ~df['is_top'].shift(1, fill_value=False)

    # Criar figura com 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), height_ratios=[3, 1])

    # Plot principal
    ax1.plot(df.index, df['close'], label='BNB Price', color='black', linewidth=2)
    ax1.plot(df.index, df['ema_200'], label='EMA 200', color='blue', linewidth=1.5, alpha=0.7)
    ax1.plot(df.index, df['ema_250'], label='EMA 250', color='purple', linewidth=1.5, alpha=0.7)
    ax1.plot(df.index, df['bottom_limit'], '--', label='Bottom (-5% EMA200)', color='green', alpha=0.5)
    ax1.plot(df.index, df['top_limit'], '--', label='Top (+15% EMA250)', color='red', alpha=0.5)

    # Marcar pontos de compra e venda
    buy_points = df[df['buy_signal']]
    sell_points = df[df['sell_signal']]

    ax1.scatter(buy_points.index, buy_points['close'],
                marker='^', s=150, color='green', zorder=5,
                label=f'Buy Signals ({len(buy_points)})')
    ax1.scatter(sell_points.index, sell_points['close'],
                marker='v', s=150, color='red', zorder=5,
                label=f'Sell Signals ({len(sell_points)})')

    # Adicionar anotações para os trades
    for idx, row in buy_points.iterrows():
        ax1.annotate(f'${row["close"]:.0f}',
                    xy=(idx, row['close']),
                    xytext=(5, -15), textcoords='offset points',
                    fontsize=8, color='green')

    for idx, row in sell_points.iterrows():
        ax1.annotate(f'${row["close"]:.0f}',
                    xy=(idx, row['close']),
                    xytext=(5, 10), textcoords='offset points',
                    fontsize=8, color='red')

    # Sombrear zonas
    ax1.fill_between(df.index, 0, df['bottom_limit'],
                     where=(df['close'] <= df['bottom_limit']),
                     color='green', alpha=0.1, label='Bottom Zone')
    ax1.fill_between(df.index, df['top_limit'], df['close'].max() * 1.1,
                     where=(df['close'] >= df['top_limit']),
                     color='red', alpha=0.1, label='Top Zone')

    ax1.set_ylabel('Price (USD)', fontsize=12)
    ax1.set_title('BNB Bottom/Top Strategy: Buy at -5% EMA200, Sell at +15% EMA250', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')

    # Subplot inferior: Distância das EMAs
    ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
    ax2.axhline(y=-0.05, color='green', linestyle='--', alpha=0.5, label='Buy Threshold (-5%)')
    ax2.axhline(y=0.15, color='red', linestyle='--', alpha=0.5, label='Sell Threshold (+15%)')

    ax2.plot(df.index, df['dist_ema_200'] * 100, label='Distance from EMA200', color='blue', alpha=0.7)
    ax2.plot(df.index, df['dist_ema_250'] * 100, label='Distance from EMA250', color='purple', alpha=0.7)

    ax2.fill_between(df.index, -5, df['dist_ema_200'] * 100,
                     where=(df['dist_ema_200'] <= -0.05),
                     color='green', alpha=0.2)
    ax2.fill_between(df.index, df['dist_ema_250'] * 100, 15,
                     where=(df['dist_ema_250'] >= 0.15),
                     color='red', alpha=0.2)

    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Distance from EMA (%)', fontsize=12)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # Adicionar estatísticas
    stats_text = (
        f"Period: {df.index[0].date()} to {df.index[-1].date()}\n"
        f"Buy Signals: {len(buy_points)} (avg ${buy_points['close'].mean():.2f})\n"
        f"Sell Signals: {len(sell_points)} (avg ${sell_points['close'].mean():.2f})\n"
        f"Current Price: ${df['close'].iloc[-1]:.2f}\n"
        f"Distance from EMA200: {df['dist_ema_200'].iloc[-1]*100:.2f}%\n"
        f"Distance from EMA250: {df['dist_ema_250'].iloc[-1]*100:.2f}%"
    )

    ax1.text(0.02, 0.98, stats_text,
            transform=ax1.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()

    # Salvar
    output_path = 'data/backtests/bottom_top_strategy_visualization.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"📊 Gráfico salvo em: {output_path}")

    plt.show()

    # Análise adicional
    print("\n📈 ANÁLISE DETALHADA DOS PONTOS")
    print("="*60)

    print("\n🟢 PONTOS DE COMPRA (Fundos):")
    for idx, row in buy_points.iterrows():
        print(f"  {idx.date()}: ${row['close']:.2f} (EMA200: ${row['ema_200']:.2f}, diff: {row['dist_ema_200']*100:.2f}%)")

    print("\n🔴 PONTOS DE VENDA (Topos):")
    for idx, row in sell_points.iterrows():
        print(f"  {idx.date()}: ${row['close']:.2f} (EMA250: ${row['ema_250']:.2f}, diff: {row['dist_ema_250']*100:.2f}%)")

    # Calcular tempo fora do mercado
    total_days = len(df)
    days_in_position = 0

    position_open = False
    entry_date = None

    for idx, row in df.iterrows():
        if row['buy_signal'] and not position_open:
            position_open = True
            entry_date = idx
        elif row['sell_signal'] and position_open:
            days_in_position += (idx - entry_date).days
            position_open = False
            entry_date = None

    if position_open and entry_date:
        days_in_position += (df.index[-1] - entry_date).days

    days_out = total_days - days_in_position
    pct_in = (days_in_position / total_days) * 100
    pct_out = (days_out / total_days) * 100

    print(f"\n⏱️ TEMPO NO MERCADO:")
    print(f"  Dentro de posição: {days_in_position} dias ({pct_in:.1f}%)")
    print(f"  Fora de posição: {days_out} dias ({pct_out:.1f}%)")

    print("\n💡 INSIGHT PRINCIPAL:")
    if pct_out > 50:
        print(f"  ⚠️ Estratégia fica {pct_out:.1f}% do tempo FORA do mercado!")
        print("  📉 Isso explica por que Buy & Hold geralmente vence")
        print("  💰 Estar fora = perder rallies importantes")
    else:
        print(f"  ✅ Estratégia fica {pct_in:.1f}% do tempo no mercado")


if __name__ == "__main__":
    create_visualization()