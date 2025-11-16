#!/usr/bin/env python3
"""
Gerenciador de Watchlist para Trading Multi-Ativo

Gerencia lista de ativos monitorados, baixa dados históricos
e calcula parâmetros ideais automaticamente.
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


class WatchlistManager:
    """Gerencia watchlist de ativos para trading."""

    def __init__(self):
        self.watchlist_file = 'data/watchlist.json'
        self.db_path = 'data/jarvis_trading.db'
        self.client = BinanceRESTClient(testnet=False)

        # Criar tabela de watchlist se não existir
        self._init_database()

        # Carregar watchlist
        self.load_watchlist()

    def _init_database(self):
        """Inicializa tabela de watchlist no banco."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_at TEXT NOT NULL,
                params_1h TEXT,
                params_4h TEXT,
                params_1d TEXT,
                last_updated TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)

        conn.commit()
        conn.close()

    def load_watchlist(self) -> List[str]:
        """Carrega watchlist do banco."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT symbol FROM watchlist WHERE is_active = 1
        """)

        self.symbols = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not self.symbols:
            # Watchlist padrão inicial
            self.symbols = ['BNBUSDT', 'BTCUSDT', 'ETHUSDT']
            for symbol in self.symbols:
                self.add_symbol(symbol, init_only=True)

        return self.symbols

    def add_symbol(self, symbol: str, init_only=False) -> Dict:
        """
        Adiciona símbolo à watchlist.

        Args:
            symbol: Símbolo (ex: BNBUSDT)
            init_only: Se True, apenas adiciona sem baixar dados

        Returns:
            Dict com status da operação
        """
        symbol = symbol.upper().replace('/', '').replace('_', '')

        if symbol in self.symbols:
            return {'status': 'error', 'message': f'{symbol} já está na watchlist'}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Adicionar ao banco
            cursor.execute("""
                INSERT INTO watchlist (symbol, added_at)
                VALUES (?, ?)
            """, (symbol, datetime.now(timezone.utc).isoformat()))

            conn.commit()
            self.symbols.append(symbol)

            if not init_only:
                # Baixar dados históricos
                print(f"📥 Baixando dados históricos de {symbol}...")
                self.download_historical_data(symbol)

                # Calcular parâmetros ideais
                print(f"📊 Calculando parâmetros ideais...")
                params = self.calculate_optimal_params(symbol)

                # Salvar parâmetros
                cursor.execute("""
                    UPDATE watchlist
                    SET params_1h = ?, params_4h = ?, params_1d = ?, last_updated = ?
                    WHERE symbol = ?
                """, (
                    json.dumps(params.get('1h', {})),
                    json.dumps(params.get('4h', {})),
                    json.dumps(params.get('1d', {})),
                    datetime.now(timezone.utc).isoformat(),
                    symbol
                ))
                conn.commit()

                return {
                    'status': 'success',
                    'message': f'{symbol} adicionado com sucesso',
                    'params': params
                }

            return {'status': 'success', 'message': f'{symbol} adicionado'}

        except Exception as e:
            conn.rollback()
            return {'status': 'error', 'message': str(e)}
        finally:
            conn.close()

    def remove_symbol(self, symbol: str) -> Dict:
        """
        Remove símbolo da watchlist.

        Mantém histórico de transações mas limpa dados de mercado.
        """
        symbol = symbol.upper().replace('/', '').replace('_', '')

        if symbol not in self.symbols:
            return {'status': 'error', 'message': f'{symbol} não está na watchlist'}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Marcar como inativo (não deletar para manter histórico)
            cursor.execute("""
                UPDATE watchlist SET is_active = 0 WHERE symbol = ?
            """, (symbol,))

            # Limpar dados de mercado (opcional)
            cursor.execute("""
                DELETE FROM market_data WHERE symbol = ?
            """, (symbol,))

            conn.commit()
            self.symbols.remove(symbol)

            return {'status': 'success', 'message': f'{symbol} removido da watchlist'}

        except Exception as e:
            conn.rollback()
            return {'status': 'error', 'message': str(e)}
        finally:
            conn.close()

    def list_symbols(self) -> List[Dict]:
        """Lista todos os símbolos com seus parâmetros."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT symbol, added_at, params_1h, params_4h, params_1d, last_updated
            FROM watchlist
            WHERE is_active = 1
            ORDER BY symbol
        """)

        results = []
        for row in cursor.fetchall():
            results.append({
                'symbol': row[0],
                'added_at': row[1],
                'params_1h': json.loads(row[2]) if row[2] else {},
                'params_4h': json.loads(row[3]) if row[3] else {},
                'params_1d': json.loads(row[4]) if row[4] else {},
                'last_updated': row[5]
            })

        conn.close()
        return results

    def download_historical_data(self, symbol: str):
        """Baixa dados históricos para todos os timeframes."""
        timeframes = {
            '1h': 1000,   # ~41 dias
            '4h': 1000,   # ~166 dias
            '1d': 1000    # ~3 anos
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for tf, limit in timeframes.items():
            print(f"  Baixando {limit} velas de {tf}...")

            try:
                klines = self.client.get_klines(
                    symbol=symbol,
                    interval=tf,
                    limit=limit
                )

                # Salvar no banco
                for kline in klines:
                    cursor.execute("""
                        INSERT OR REPLACE INTO market_data
                        (symbol, timeframe, timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol, tf,
                        kline['open_time'],
                        float(kline['open']),
                        float(kline['high']),
                        float(kline['low']),
                        float(kline['close']),
                        float(kline['volume'])
                    ))

                conn.commit()
                print(f"    ✅ {len(klines)} velas salvas")

            except Exception as e:
                print(f"    ❌ Erro: {e}")

        conn.close()

    def calculate_optimal_params(self, symbol: str) -> Dict:
        """
        Calcula parâmetros ideais para cada timeframe.

        Returns:
            Dict com parâmetros por timeframe
        """
        params = {}
        conn = sqlite3.connect(self.db_path)

        for tf in ['1h', '4h', '1d']:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, close
                FROM market_data
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp
            """, (symbol, tf))

            data = cursor.fetchall()
            if len(data) < 200:
                continue

            df = pd.DataFrame(data, columns=['timestamp', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Calcular MAs
            if tf == '1h':
                ma_period = 20
            elif tf == '4h':
                ma_period = 100
            else:  # 1d
                ma_period = 200

            df['ma'] = df['close'].rolling(window=ma_period).mean()
            df['dist'] = (df['close'] - df['ma']) / df['ma'] * 100

            # Identificar reversões
            df['is_bottom'] = (
                df['close'] == df['close'].rolling(window=12, center=True).min()
            )
            df['is_top'] = (
                df['close'] == df['close'].rolling(window=12, center=True).max()
            )

            # Distâncias nos pontos de reversão
            bottoms = df[df['is_bottom']]['dist'].values
            tops = df[df['is_top']]['dist'].values

            if len(bottoms) > 5 and len(tops) > 5:
                params[tf] = {
                    'ma_period': ma_period,
                    'buy_threshold': float(np.percentile(bottoms, 25)),
                    'sell_threshold': float(np.percentile(tops, 75)),
                    'bottoms_count': len(bottoms),
                    'tops_count': len(tops)
                }

        conn.close()
        return params

    def get_params(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Obtém parâmetros otimizados para um símbolo e timeframe."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT params_{timeframe}
            FROM watchlist
            WHERE symbol = ? AND is_active = 1
        """, (symbol,))

        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return json.loads(row[0])
        return None

    def update_all_params(self):
        """Atualiza parâmetros de todos os símbolos."""
        for symbol in self.symbols:
            print(f"\nAtualizando {symbol}...")
            self.download_historical_data(symbol)
            params = self.calculate_optimal_params(symbol)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE watchlist
                SET params_1h = ?, params_4h = ?, params_1d = ?, last_updated = ?
                WHERE symbol = ?
            """, (
                json.dumps(params.get('1h', {})),
                json.dumps(params.get('4h', {})),
                json.dumps(params.get('1d', {})),
                datetime.now(timezone.utc).isoformat(),
                symbol
            ))

            conn.commit()
            conn.close()


def main():
    """Interface CLI para gerenciar watchlist."""
    import argparse

    parser = argparse.ArgumentParser(description="Gerenciar watchlist de trading")
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')

    # Comando list
    subparsers.add_parser('list', help='Listar ativos na watchlist')

    # Comando add
    add_parser = subparsers.add_parser('add', help='Adicionar ativo')
    add_parser.add_argument('symbol', help='Símbolo (ex: BNBUSDT)')

    # Comando remove
    remove_parser = subparsers.add_parser('remove', help='Remover ativo')
    remove_parser.add_argument('symbol', help='Símbolo')

    # Comando update
    subparsers.add_parser('update', help='Atualizar parâmetros de todos os ativos')

    args = parser.parse_args()

    manager = WatchlistManager()

    if args.command == 'list':
        symbols = manager.list_symbols()
        print("\n📋 WATCHLIST ATUAL:")
        print("="*60)
        for item in symbols:
            print(f"\n{item['symbol']}:")
            print(f"  Adicionado: {item['added_at'][:10]}")
            if item['params_1h']:
                print(f"  1H: Compra {item['params_1h']['buy_threshold']:.1f}%, Venda {item['params_1h']['sell_threshold']:.1f}%")
            if item['params_4h']:
                print(f"  4H: Compra {item['params_4h']['buy_threshold']:.1f}%, Venda {item['params_4h']['sell_threshold']:.1f}%")
            if item['params_1d']:
                print(f"  1D: Compra {item['params_1d']['buy_threshold']:.1f}%, Venda {item['params_1d']['sell_threshold']:.1f}%")

    elif args.command == 'add':
        result = manager.add_symbol(args.symbol)
        print(result['message'])

    elif args.command == 'remove':
        result = manager.remove_symbol(args.symbol)
        print(result['message'])

    elif args.command == 'update':
        manager.update_all_params()
        print("✅ Parâmetros atualizados")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()