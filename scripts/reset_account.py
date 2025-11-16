#!/usr/bin/env python3
"""
Reset da conta de Paper Trading para $5000 USD

Limpa todas as posições e reinicia com capital inicial.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import uuid

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def reset_account(account_id='868e0dd8-37f5-43ea-a956-7cc05e6bad66', initial_capital=5000.0):
    """
    Reseta a conta para o capital inicial.

    Args:
        account_id: ID da conta
        initial_capital: Capital inicial em USD
    """
    db_path = 'data/jarvis_trading.db'

    print("="*60)
    print("RESET DE CONTA - PAPER TRADING")
    print("="*60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Limpar balances atuais
        cursor.execute("DELETE FROM balances WHERE account_id = ?", (account_id,))
        print(f"✅ Balanços anteriores removidos")

        # 2. Inserir novo balance em USDT
        cursor.execute("""
            INSERT INTO balances (account_id, currency, available_amount, reserved_amount)
            VALUES (?, ?, ?, ?)
        """, (account_id, 'USDT', initial_capital, 0.0))
        print(f"✅ Novo balanço: ${initial_capital:.2f} USDT")

        # 3. Registrar transação de reset
        transaction_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO transactions (
                id, account_id, transaction_type,
                amount, currency, description, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id, account_id, 'DEPOSIT',
            initial_capital, 'USDT',
            f'Account reset to ${initial_capital}',
            timestamp
        ))
        print(f"✅ Transação de reset registrada")

        # 4. Limpar ordens abertas
        cursor.execute("""
            UPDATE orders
            SET status = 'CANCELLED'
            WHERE account_id = ? AND status IN ('PENDING', 'OPEN')
        """, (account_id,))
        print(f"✅ Ordens abertas canceladas")

        # 5. Resetar métricas de performance
        cursor.execute("""
            DELETE FROM performance_metrics
            WHERE account_id = ?
        """, (account_id,))
        print(f"✅ Métricas de performance resetadas")

        conn.commit()

        print(f"\n📊 CONTA RESETADA COM SUCESSO")
        print(f"   ID: {account_id}")
        print(f"   Capital: ${initial_capital:.2f} USDT")
        print(f"   Data: {timestamp}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro no reset: {e}")
        raise
    finally:
        conn.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Reset paper trading account")
    parser.add_argument(
        "--capital",
        type=float,
        default=5000.0,
        help="Initial capital in USD (default: 5000)"
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Account ID"
    )

    args = parser.parse_args()

    # Confirmar reset
    print(f"⚠️  ATENÇÃO: Isso irá resetar a conta para ${args.capital:.2f}")
    print(f"   Todas as posições serão fechadas!")
    response = input("\nContinuar? (y/N): ")

    if response.lower() == 'y':
        reset_account(args.account_id, args.capital)
    else:
        print("❌ Reset cancelado")


if __name__ == "__main__":
    main()