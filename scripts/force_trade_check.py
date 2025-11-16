#!/usr/bin/env python3
"""
Force immediate signal check and trade execution.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.multi_asset_trading_daemon import MultiAssetTradingDaemon


def main():
    """Force immediate signal check."""
    account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'

    logger.info("🔥 Forçando verificação imediata de sinais...")

    # Create daemon instance
    daemon = MultiAssetTradingDaemon(account_id)

    # Check all signals
    signals = daemon.check_all_signals()

    if signals:
        logger.info(f"📡 {len(signals)} sinais ativos encontrados!")

        # Process signals
        trades_executed = daemon.process_signals(signals)

        if trades_executed:
            logger.success(f"✅ {len(trades_executed)} trades executados com sucesso!")

            # Show executed trades
            for trade in trades_executed:
                logger.info(
                    f"  • {trade['action']} {trade['quantity']:.6f} {trade['symbol']} "
                    f"@ ${trade['price']:.2f} ({trade['timeframe']})"
                )

            # Show portfolio status
            status = daemon.get_portfolio_status()
            logger.info(f"\n💼 Portfolio atualizado:")
            logger.info(f"  USDT: ${status['usdt_balance']:.2f}")
            for symbol, info in status['positions'].items():
                if info['quantity'] > 0:
                    logger.info(
                        f"  {symbol}: {info['quantity']:.6f} "
                        f"(${info['value']:.2f})"
                    )
            logger.info(f"  💰 Valor Total: ${status['total_value']:.2f}")
        else:
            logger.warning("❌ Nenhum trade executado (possível erro ou saldo insuficiente)")
    else:
        logger.info("📊 Nenhum sinal ativo no momento")

    # Check orders table
    import sqlite3
    conn = sqlite3.connect('data/jarvis_trading.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders WHERE account_id = ?", (account_id,))
    order_count = cursor.fetchone()[0]
    conn.close()

    logger.info(f"\n📋 Total de ordens no histórico: {order_count}")


if __name__ == "__main__":
    main()