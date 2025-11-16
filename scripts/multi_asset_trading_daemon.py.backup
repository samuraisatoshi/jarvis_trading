#!/usr/bin/env python3
"""
Daemon de Trading Multi-Ativo e Multi-Timeframe

Monitora múltiplos ativos em múltiplos timeframes (1h, 4h, 1d)
e executa trades baseado em parâmetros otimizados.
"""

import sys
import time
import json
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from queue import Queue

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.database import DatabaseManager
from src.infrastructure.notifications.telegram_helper import TradingTelegramNotifier
from scripts.watchlist_manager import WatchlistManager


class MultiAssetTradingDaemon:
    """Daemon que gerencia trading multi-ativo e multi-timeframe."""

    def __init__(self, account_id='868e0dd8-37f5-43ea-a956-7cc05e6bad66'):
        self.account_id = account_id
        self.db_path = 'data/jarvis_trading.db'
        self.client = BinanceRESTClient(testnet=False)
        self.watchlist = WatchlistManager()

        # Telegram notifier (opcional)
        try:
            self.telegram = TradingTelegramNotifier()
            logger.info("Telegram ativado - Notificações automáticas habilitadas")
        except Exception as e:
            self.telegram = None
            logger.warning(f"Telegram desativado: {e}")

        # Estado do daemon
        self.running = False
        self.paused = False
        self.last_check = {}
        self.positions = {}
        self.pending_orders = []

        # Configurações
        self.timeframes = ['1h', '4h', '1d']
        self.check_interval = 3600  # 1 hora em segundos
        self.position_sizes = {
            '1h': 0.1,   # 10% do capital para trades 1h
            '4h': 0.2,   # 20% do capital para trades 4h
            '1d': 0.3    # 30% do capital para trades 1d
        }

        # Fila de sinais
        self.signal_queue = Queue()

        logger.info(f"Daemon multi-ativo iniciado")
        logger.info(f"Account ID: {account_id}")
        logger.info(f"Ativos: {self.watchlist.symbols}")

    def get_account_balance(self) -> Dict[str, float]:
        """Obtém balanços da conta."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT currency, available_amount
            FROM balances
            WHERE account_id = ?
        """, (self.account_id,))

        balances = {}
        for currency, amount in cursor.fetchall():
            balances[currency] = amount

        conn.close()
        return balances

    def calculate_position_size(self, symbol: str, timeframe: str) -> float:
        """
        Calcula tamanho da posição baseado no timeframe.

        Returns:
            Quantidade em USD para investir
        """
        balances = self.get_account_balance()
        usdt_balance = balances.get('USDT', 0.0)

        # Percentual baseado no timeframe
        allocation = self.position_sizes.get(timeframe, 0.1)

        # Verificar posições existentes no símbolo
        existing_position = self.get_position(symbol)
        if existing_position:
            # Se já tem posição, usar menos capital
            allocation *= 0.5

        return usdt_balance * allocation

    def get_position(self, symbol: str) -> Optional[Dict]:
        """Obtém posição atual em um símbolo."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Buscar balanço do ativo
        base_currency = symbol.replace('USDT', '')
        cursor.execute("""
            SELECT available_amount
            FROM balances
            WHERE account_id = ? AND currency = ?
        """, (self.account_id, base_currency))

        row = cursor.fetchone()
        conn.close()

        if row and row[0] > 0:
            return {
                'symbol': symbol,
                'quantity': row[0],
                'currency': base_currency
            }

        return None

    def check_signal(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        Verifica sinal de trading para um símbolo e timeframe.

        Returns:
            Dict com sinal ou None
        """
        try:
            # Obter parâmetros otimizados
            params = self.watchlist.get_params(symbol, timeframe)
            if not params:
                return None

            # Buscar preço atual e MA
            ticker = self.client.get_24h_ticker(symbol)
            current_price = float(ticker['lastPrice'])

            # Buscar dados para calcular MA
            klines = self.client.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=params['ma_period'] + 10
            )

            df = pd.DataFrame(klines)
            df['close'] = df['close'].astype(float)

            # Calcular MA
            ma = df['close'].rolling(window=params['ma_period']).mean().iloc[-1]

            # Calcular distância
            distance = (current_price - ma) / ma * 100

            # Verificar sinais
            signal = None

            if distance <= params['buy_threshold']:
                signal = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'action': 'BUY',
                    'price': current_price,
                    'ma': ma,
                    'distance': distance,
                    'threshold': params['buy_threshold'],
                    'reason': f"Preço {distance:.1f}% abaixo da MA{params['ma_period']}"
                }

            elif distance >= params['sell_threshold']:
                # Verificar se temos posição
                position = self.get_position(symbol)
                if position:
                    signal = {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'action': 'SELL',
                        'price': current_price,
                        'ma': ma,
                        'distance': distance,
                        'threshold': params['sell_threshold'],
                        'reason': f"Preço {distance:.1f}% acima da MA{params['ma_period']}"
                    }

            return signal

        except Exception as e:
            logger.error(f"Erro ao verificar sinal {symbol} {timeframe}: {e}")
            return None

    def execute_trade(self, signal: Dict) -> bool:
        """
        Executa trade baseado no sinal.

        Returns:
            True se executado com sucesso
        """
        try:
            symbol = signal['symbol']
            action = signal['action']
            price = signal['price']

            if action == 'BUY':
                # Calcular quantidade
                position_size = self.calculate_position_size(symbol, signal['timeframe'])
                if position_size < 10:  # Mínimo $10
                    logger.warning(f"Posição muito pequena: ${position_size:.2f}")
                    return False

                quantity = position_size / price

                # Executar compra (paper trading)
                success = self.execute_buy(symbol, quantity, price, signal)

                if success and self.telegram:
                    self.telegram.send_message(
                        f"🟢 **COMPRA EXECUTADA**\n\n"
                        f"Ativo: {symbol}\n"
                        f"Timeframe: {signal['timeframe']}\n"
                        f"Quantidade: {quantity:.6f}\n"
                        f"Preço: ${price:.2f}\n"
                        f"Valor: ${position_size:.2f}\n"
                        f"Motivo: {signal['reason']}"
                    )

                return success

            elif action == 'SELL':
                # Obter posição
                position = self.get_position(symbol)
                if not position:
                    logger.warning(f"Sem posição em {symbol}")
                    return False

                quantity = position['quantity']

                # Executar venda
                success = self.execute_sell(symbol, quantity, price, signal)

                if success and self.telegram:
                    value = quantity * price
                    self.telegram.send_message(
                        f"🔴 **VENDA EXECUTADA**\n\n"
                        f"Ativo: {symbol}\n"
                        f"Timeframe: {signal['timeframe']}\n"
                        f"Quantidade: {quantity:.6f}\n"
                        f"Preço: ${price:.2f}\n"
                        f"Valor: ${value:.2f}\n"
                        f"Motivo: {signal['reason']}"
                    )

                return success

        except Exception as e:
            logger.error(f"Erro ao executar trade: {e}")
            return False

    def execute_buy(self, symbol: str, quantity: float, price: float, signal: Dict) -> bool:
        """Executa ordem de compra (paper trading)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Verificar saldo USDT
            cursor.execute("""
                SELECT available_amount FROM balances
                WHERE account_id = ? AND currency = 'USDT'
            """, (self.account_id,))

            usdt_balance = cursor.fetchone()[0]
            total_cost = quantity * price

            if usdt_balance < total_cost:
                logger.warning(f"Saldo insuficiente: ${usdt_balance:.2f} < ${total_cost:.2f}")
                return False

            # Atualizar balanços
            base_currency = symbol.replace('USDT', '')

            # Reduzir USDT
            cursor.execute("""
                UPDATE balances
                SET available_amount = available_amount - ?
                WHERE account_id = ? AND currency = 'USDT'
            """, (total_cost, self.account_id))

            # Adicionar ativo
            cursor.execute("""
                INSERT INTO balances (account_id, currency, available_amount, reserved_amount)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(account_id, currency)
                DO UPDATE SET available_amount = available_amount + ?
            """, (self.account_id, base_currency, quantity, quantity))

            # Registrar ordem
            order_id = f"BUY_{symbol}_{datetime.now(timezone.utc).timestamp()}"
            cursor.execute("""
                INSERT INTO orders (
                    id, account_id, symbol, side, order_type,
                    quantity, price, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, self.account_id, symbol, 'BUY', 'MARKET',
                quantity, price, 'FILLED',
                datetime.now(timezone.utc).isoformat()
            ))

            # Registrar transação
            cursor.execute("""
                INSERT INTO transactions (
                    id, account_id, transaction_type,
                    amount, currency, description, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"TX_{order_id}",
                self.account_id,
                'BUY',
                quantity,
                base_currency,
                f"Buy {symbol} @ ${price:.2f} ({signal['timeframe']})",
                datetime.now(timezone.utc).isoformat()
            ))

            conn.commit()
            logger.info(f"✅ Compra executada: {quantity:.6f} {symbol} @ ${price:.2f}")

            # Enviar notificação Telegram
            if self.telegram:
                try:
                    self.telegram.notify_trade_executed(
                        trade_type='BUY',
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        timeframe=signal['timeframe'],
                        reason=signal.get('reason')
                    )
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação: {e}")

            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Erro na compra: {e}")
            return False
        finally:
            conn.close()

    def execute_sell(self, symbol: str, quantity: float, price: float, signal: Dict) -> bool:
        """Executa ordem de venda (paper trading)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            base_currency = symbol.replace('USDT', '')

            # Verificar posição
            cursor.execute("""
                SELECT available_amount FROM balances
                WHERE account_id = ? AND currency = ?
            """, (self.account_id, base_currency))

            position = cursor.fetchone()
            if not position or position[0] < quantity:
                logger.warning(f"Posição insuficiente em {base_currency}")
                return False

            total_value = quantity * price

            # Reduzir ativo
            cursor.execute("""
                UPDATE balances
                SET available_amount = available_amount - ?
                WHERE account_id = ? AND currency = ?
            """, (quantity, self.account_id, base_currency))

            # Adicionar USDT
            cursor.execute("""
                UPDATE balances
                SET available_amount = available_amount + ?
                WHERE account_id = ? AND currency = 'USDT'
            """, (total_value, self.account_id))

            # Registrar ordem
            order_id = f"SELL_{symbol}_{datetime.now(timezone.utc).timestamp()}"
            cursor.execute("""
                INSERT INTO orders (
                    id, account_id, symbol, side, order_type,
                    quantity, price, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, self.account_id, symbol, 'SELL', 'MARKET',
                quantity, price, 'FILLED',
                datetime.now(timezone.utc).isoformat()
            ))

            conn.commit()
            logger.info(f"✅ Venda executada: {quantity:.6f} {symbol} @ ${price:.2f}")

            # Enviar notificação Telegram
            if self.telegram:
                try:
                    self.telegram.notify_trade_executed(
                        trade_type='SELL',
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        timeframe=signal['timeframe'],
                        reason=signal.get('reason')
                    )
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação: {e}")

            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Erro na venda: {e}")
            return False
        finally:
            conn.close()

    def check_all_signals(self):
        """Verifica sinais para todos os ativos e timeframes."""
        signals = []

        for symbol in self.watchlist.symbols:
            for timeframe in self.timeframes:
                # Verificar se já checamos recentemente
                last_key = f"{symbol}_{timeframe}"
                last_check = self.last_check.get(last_key, 0)
                now = time.time()

                # Intervalo mínimo entre checagens
                min_interval = {
                    '1h': 300,    # 5 minutos
                    '4h': 1200,   # 20 minutos
                    '1d': 3600    # 1 hora
                }.get(timeframe, 600)

                if now - last_check < min_interval:
                    continue

                # Verificar sinal
                signal = self.check_signal(symbol, timeframe)
                if signal:
                    signals.append(signal)
                    logger.info(f"📊 Sinal detectado: {signal['action']} {symbol} em {timeframe}")

                self.last_check[last_key] = now

        return signals

    def process_signals(self, signals: List[Dict]):
        """Processa lista de sinais e executa trades."""
        # Ordenar por timeframe (maior primeiro) e action (SELL primeiro)
        tf_priority = {'1d': 3, '4h': 2, '1h': 1}
        signals.sort(key=lambda x: (
            x['action'] == 'BUY',  # SELL primeiro
            -tf_priority.get(x['timeframe'], 0)  # Maior timeframe primeiro
        ))

        for signal in signals:
            try:
                # Verificar se não há conflito
                if self.has_conflicting_signal(signal, signals):
                    logger.warning(f"Sinal conflitante ignorado: {signal}")
                    continue

                # Executar trade
                if self.execute_trade(signal):
                    logger.info(f"✅ Trade executado: {signal}")
                else:
                    logger.warning(f"❌ Trade falhou: {signal}")

            except Exception as e:
                logger.error(f"Erro ao processar sinal: {e}")

    def has_conflicting_signal(self, signal: Dict, all_signals: List[Dict]) -> bool:
        """Verifica se há sinais conflitantes."""
        for other in all_signals:
            if other == signal:
                continue

            # Mesmo ativo, ação oposta
            if (other['symbol'] == signal['symbol'] and
                other['action'] != signal['action']):
                # Priorizar timeframe maior
                tf_priority = {'1d': 3, '4h': 2, '1h': 1}
                if tf_priority.get(other['timeframe'], 0) > tf_priority.get(signal['timeframe'], 0):
                    return True

        return False

    def get_portfolio_status(self) -> Dict:
        """Obtém status completo do portfólio."""
        balances = self.get_account_balance()
        total_value = balances.get('USDT', 0.0)

        # Adicionar valor das posições
        positions = []
        for symbol in self.watchlist.symbols:
            position = self.get_position(symbol)
            if position:
                ticker = self.client.get_24h_ticker(symbol)
                price = float(ticker['lastPrice'])
                value = position['quantity'] * price
                total_value += value

                positions.append({
                    'symbol': symbol,
                    'quantity': position['quantity'],
                    'price': price,
                    'value': value
                })

        return {
            'total_value': total_value,
            'usdt_balance': balances.get('USDT', 0.0),
            'positions': positions,
            'num_positions': len(positions)
        }

    def run(self):
        """Loop principal do daemon."""
        logger.info("🚀 Daemon multi-ativo iniciado")
        self.running = True

        # Notificar início
        if self.telegram:
            try:
                status = self.get_portfolio_status()
                self.telegram.notify_daemon_started(
                    watchlist=self.watchlist.symbols,
                    capital=status['total_value']
                )
            except Exception as e:
                logger.error(f"Erro ao enviar notificação de início: {e}")

        last_hour = datetime.now(timezone.utc).hour

        while self.running:
            try:
                if not self.paused:
                    current_hour = datetime.now(timezone.utc).hour

                    # Verificar a cada hora cheia
                    if current_hour != last_hour:
                        logger.info(f"🕐 Verificando sinais ({datetime.now(timezone.utc).strftime('%H:%M')} UTC)")

                        # Verificar todos os sinais
                        signals = self.check_all_signals()

                        if signals:
                            logger.info(f"📊 {len(signals)} sinais encontrados")

                            # Notificar sinais encontrados
                            if self.telegram:
                                try:
                                    self.telegram.notify_signals_found(signals)
                                except Exception as e:
                                    logger.error(f"Erro ao notificar sinais: {e}")

                            self.process_signals(signals)
                        else:
                            logger.info("Sem sinais no momento")

                        # Enviar status periódico (a cada 6 horas)
                        if current_hour % 6 == 0:
                            self.send_status_update()

                        last_hour = current_hour

                # Dormir 30 segundos
                time.sleep(30)

            except KeyboardInterrupt:
                logger.info("Interrupção recebida")
                break
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}")
                time.sleep(60)

        logger.info("Daemon finalizado")

    def send_status_update(self):
        """Envia atualização de status via Telegram."""
        if not self.telegram:
            return

        try:
            status = self.get_portfolio_status()

            message = f"📊 **STATUS DO PORTFÓLIO**\n\n"
            message += f"💰 Valor Total: ${status['total_value']:.2f}\n"
            message += f"💵 USDT Livre: ${status['usdt_balance']:.2f}\n\n"

            if status['positions']:
                message += "📈 **Posições Abertas:**\n"
                for pos in status['positions']:
                    message += f"• {pos['symbol']}: {pos['quantity']:.4f} @ ${pos['price']:.2f} = ${pos['value']:.2f}\n"
            else:
                message += "📉 Sem posições abertas\n"

            message += f"\n⏰ Última verificação: {datetime.now(timezone.utc).strftime('%H:%M')} UTC"

            self.telegram.send_message(message)

        except Exception as e:
            logger.error(f"Erro ao enviar status: {e}")

    def stop(self):
        """Para o daemon."""
        logger.info("Parando daemon...")
        self.running = False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Daemon de trading multi-ativo")
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="ID da conta"
    )

    args = parser.parse_args()

    # Configurar logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/multi_asset_trading.log",
        rotation="100 MB",
        retention="30 days",
        level="DEBUG"
    )

    # Criar e executar daemon
    daemon = MultiAssetTradingDaemon(args.account_id)

    try:
        daemon.run()
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    main()