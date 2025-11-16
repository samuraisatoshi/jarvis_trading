"""
Message Formatter Module
Handles all message formatting and template rendering for Telegram bot.
Follows Single Responsibility Principle: format only, no business logic.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime


class MessageFormatter:
    """Formats Telegram messages with consistent styling."""

    def format_welcome(self) -> str:
        """Format welcome message for /start command."""
        return (
            "🤖 *Bot de Trading - Menu Principal*\n\n"
            "Bem-vindo! Este bot suporta tanto comandos diretos "
            "quanto navegação por botões.\n\n"
            "📱 *Use os botões abaixo ou digite comandos*\n"
            "💡 Digite /help para ver todos os comandos\n\n"
            "_Sistema operando normalmente_"
        )

    def format_help(self) -> str:
        """Format help message."""
        return """
🤖 *Bot de Trading - Ajuda*

📝 *Comandos Principais:*
• `/start` - Menu principal com botões
• `/status` - Status completo do sistema
• `/portfolio` ou `/p` - Ver portfólio atual
• `/watchlist` ou `/w` - Lista de ativos monitorados
• `/signals` ou `/s` - Sinais de trading ativos
• `/performance` - Análise de performance

🔧 *Gerenciar Watchlist:*
• `/add SYMBOL` - Adicionar ativo (ex: /add ADAUSDT)
• `/remove SYMBOL` - Remover ativo
• `/update` - Atualizar dados da watchlist

💰 *Trading Manual:*
• `/buy SYMBOL AMOUNT` - Comprar com valor em USDT
• `/sell SYMBOL PERCENT` - Vender % da posição

📊 *Consultas:*
• `/history [N]` - Últimas N transações
• `/orders [N]` - Últimas N ordens
• `/balance` - Saldos da conta
• `/candles SYMBOL [TF]` - Gráfico candlestick

⚙️ *Configurações:*
• `/settings` - Ver configurações
• `/pause` - Pausar trading automático
• `/resume` - Retomar trading automático

💡 *Dicas:*
• Todos os comandos mostram feedback visual
• Use botões ou comandos conforme preferir
• O bot verifica sinais a cada hora
• Notificações automáticas ativadas
"""

    def format_status(
        self,
        balances: List[Tuple[str, float]],
        last_order: Optional[Tuple] = None,
        orders_today: int = 0
    ) -> str:
        """Format status message with balances and order info."""
        status_msg = "✅ *Status do Sistema*\n\n"
        status_msg += "🟢 *Bot:* Online\n"
        status_msg += "🟢 *Trading:* Ativo\n"
        status_msg += "🟢 *Notificações:* Habilitadas\n\n"

        status_msg += "💼 *Saldos Principais:*\n"
        for currency, amount in balances[:5]:
            if currency == 'USDT':
                status_msg += f"• {currency}: ${amount:.2f}\n"
            else:
                status_msg += f"• {currency}: {amount:.6f}\n"

        status_msg += f"\n📊 *Ordens Hoje:* {orders_today}\n"

        if last_order:
            symbol, side, qty, price, created_at = last_order
            time_str = datetime.fromisoformat(created_at).strftime('%H:%M')
            status_msg += f"\n📈 *Última Ordem:* {side} {symbol}\n"
            status_msg += f"   {qty:.6f} @ ${price:.2f} ({time_str})\n"

        return status_msg

    def format_portfolio(
        self,
        balances: List[Tuple[str, float]],
        total_value: float,
        price_data: Dict[str, float]
    ) -> str:
        """Format portfolio message with holdings and distribution."""
        if not balances:
            return "📊 *Portfolio vazio*\n\nNenhuma posição encontrada."

        portfolio_text = "💼 *Seu Portfolio*\n\n"

        for currency, amount in balances:
            if currency == 'USDT':
                value = amount
                portfolio_text += f"💵 *USDT:* ${amount:.2f}\n"
            else:
                symbol = f"{currency}USDT"
                price = price_data.get(symbol, 0)
                value = amount * price if price else 0
                portfolio_text += (
                    f"🪙 *{currency}:* {amount:.6f}\n"
                    f"   └ ${price:.2f} = *${value:.2f}*\n"
                )

        portfolio_text += f"\n💰 *Valor Total:* ${total_value:.2f}"

        # Distribution percentages
        portfolio_text += "\n\n📊 *Distribuição:*\n"
        for currency, amount in balances[:5]:
            if currency == 'USDT':
                pct = (amount / total_value) * 100 if total_value else 0
                portfolio_text += f"• USDT: {pct:.1f}%\n"
            else:
                symbol = f"{currency}USDT"
                price = price_data.get(symbol, 0)
                value = amount * price if price else 0
                pct = (value / total_value) * 100 if total_value else 0
                portfolio_text += f"• {currency}: {pct:.1f}%\n"

        return portfolio_text

    def format_signals(self) -> str:
        """Format trading signals message."""
        return (
            "📈 *Sinais de Trading*\n\n"
            "🟢 *COMPRA Potencial:*\n"
            "• BTCUSDT (1h): -2.3% da MA50\n"
            "• ETHUSDT (4h): -3.1% da MA100\n\n"
            "🔴 *VENDA Potencial:*\n"
            "• Nenhum sinal ativo\n\n"
            "⏰ *Próxima verificação:* em 45 min\n"
            "_Use /candles SYMBOL para ver gráfico_"
        )

    def format_buy_confirmation(self, symbol: str, amount_usdt: float) -> str:
        """Format buy order confirmation message."""
        return (
            f"💰 *Confirmação de Compra*\n\n"
            f"Ativo: {symbol}\n"
            f"Valor: ${amount_usdt:.2f} USDT\n"
        )

    def format_buy_result(self, symbol: str, quantity: float, price: float, amount_usdt: float) -> str:
        """Format buy order result message."""
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        return (
            f"✅ *Compra Executada!*\n\n"
            f"📊 *Ativo:* {symbol}\n"
            f"💰 *Quantidade:* {quantity} BTC\n"
            f"💵 *Preço:* ${price:,.2f}\n"
            f"💎 *Valor Total:* ${amount_usdt:.2f} USDT\n"
            f"📅 *Data:* {timestamp}\n\n"
            f"_Ordem executada via Telegram_"
        )

    def format_sell_instruction(self) -> str:
        """Format sell instruction message."""
        return (
            "🔴 Venda processada (simulação)\n"
            "_Implemente lógica real aqui_"
        )

    def format_candles_processing(self, symbol: str, timeframe: str) -> str:
        """Format candles processing message."""
        return (
            f"📊 Gerando gráfico {symbol} ({timeframe})...\n"
            f"_Isso pode levar alguns segundos_"
        )

    def format_candles_caption(self, symbol: str, timeframe: str) -> str:
        """Format candles chart caption."""
        return (
            f"📊 *{symbol} - {timeframe.upper()}*\n\n"
            f"🟡 Médias Móveis (MA)\n"
            f"🟢 Linhas de Suporte\n"
            f"🔴 Linhas de Resistência\n"
            f"⬆️ Compras executadas\n"
            f"⬇️ Vendas executadas\n\n"
            f"_Últimas 100 velas_"
        )

    def format_watchlist(self, symbols: List[Tuple[str, Optional[float]]]) -> str:
        """Format watchlist message."""
        if not symbols:
            return (
                "📋 *Watchlist vazia*\n\n"
                "Use `/add SYMBOL` para adicionar ativos"
            )

        watchlist_text = "📋 *Sua Watchlist*\n\n"
        for i, (symbol, price) in enumerate(symbols, 1):
            if price is not None:
                watchlist_text += f"{i}. {symbol}: ${price:,.2f}\n"
            else:
                watchlist_text += f"{i}. {symbol}\n"

        watchlist_text += "\n_Use /add ou /remove para gerenciar_"
        return watchlist_text

    def format_history(self, transactions: List[Tuple]) -> str:
        """Format transaction history message."""
        if not transactions:
            return (
                "📜 *Sem transações*\n\n"
                "Nenhuma transação encontrada."
            )

        history_text = f"📜 *Últimas {len(transactions)} Transações*\n\n"

        for tx_type, amount, currency, desc, created_at in transactions:
            time_str = datetime.fromisoformat(created_at).strftime('%d/%m %H:%M')
            emoji = "🟢" if tx_type == "BUY" else "🔴"

            history_text += (
                f"{emoji} *{tx_type}* - {time_str}\n"
                f"   {amount:.6f} {currency}\n"
            )
            if desc:
                history_text += f"   _{desc}_\n"
            history_text += "\n"

        return history_text

    def format_performance(self) -> str:
        """Format performance analysis message."""
        return (
            "📈 *Análise de Performance*\n\n"
            "📅 *Período:* Últimos 30 dias\n\n"
            "💰 *Resultado Geral:*\n"
            "• P&L: +$234.56 (+2.3%)\n"
            "• Win Rate: 65%\n"
            "• Total Trades: 45\n\n"
            "📊 *Por Ativo:*\n"
            "• BTCUSDT: +$123.45 (+1.2%)\n"
            "• ETHUSDT: +$89.12 (+3.4%)\n"
            "• BNBUSDT: +$22.99 (+0.8%)\n\n"
            "🎯 *Melhor Trade:* +$45.67 (ETHUSDT)\n"
            "⚠️ *Pior Trade:* -$12.34 (SOLUSDT)\n\n"
            "_Use /history para ver detalhes_"
        )

    def format_settings(self) -> str:
        """Format settings message."""
        return (
            "⚙️ *Configurações do Sistema*\n\n"
            "🤖 *Trading Automático:* ✅ Ativo\n"
            "🔔 *Notificações:* ✅ Habilitadas\n"
            "⏰ *Verificação:* A cada hora\n"
            "💰 *Capital:* $1,000.00\n\n"
            "📊 *Estratégia:*\n"
            "• Tipo: MA Distance\n"
            "• Timeframes: 1h, 4h, 1d\n"
            "• Risk: Conservador\n\n"
            "🔧 *Comandos:*\n"
            "• `/pause` - Pausar trading\n"
            "• `/resume` - Retomar trading\n\n"
            "_Configurações avançadas em breve_"
        )

    def format_error_unknown_command(self, command: str, suggestions: List[str]) -> str:
        """Format unknown command error message."""
        error_msg = f"❌ *Comando desconhecido:* `{command}`\n\n"

        if suggestions:
            error_msg += "💡 *Você quis dizer:*\n"
            error_msg += "\n".join(suggestions[:3])  # Max 3 suggestions
            error_msg += "\n\n"

        error_msg += (
            "📝 *Comandos disponíveis:*\n"
            "Digite /help para ver todos os comandos\n"
            "ou /start para o menu principal"
        )
        return error_msg

    def format_error_invalid_command(self) -> str:
        """Format invalid command usage error."""
        return (
            "❌ *Uso incorreto*\n\n"
            "Formato: `/buy SYMBOL AMOUNT`\n"
            "Exemplo: `/buy BTCUSDT 100`\n\n"
            "AMOUNT = valor em USDT"
        )

    def format_error_invalid_amount(self) -> str:
        """Format invalid amount error."""
        return "❌ Valor inválido. Use números apenas."

    def format_error_invalid_sell_command(self) -> str:
        """Format invalid sell command error."""
        return (
            "❌ *Uso incorreto*\n\n"
            "Formato: `/sell SYMBOL PERCENT`\n"
            "Exemplo: `/sell BTCUSDT 50`\n\n"
            "PERCENT = % da posição (0-100)"
        )

    def format_error_add_command(self) -> str:
        """Format add command usage error."""
        return (
            "❌ *Uso:* `/add SYMBOL`\n"
            "Exemplo: `/add ADAUSDT`"
        )

    def format_error_remove_command(self) -> str:
        """Format remove command usage error."""
        return (
            "❌ *Uso:* `/remove SYMBOL`\n"
            "Exemplo: `/remove ADAUSDT`"
        )

    def format_error_candles_command(self) -> str:
        """Format candles command usage error."""
        return (
            "❌ *Uso incorreto*\n\n"
            "Formato: `/candles SYMBOL [TIMEFRAME]`\n"
            "Exemplos:\n"
            "• `/candles BTCUSDT` (default: 1h)\n"
            "• `/candles BTC 4h`\n"
            "• `/candles ETHUSDT 1d`\n\n"
            "Timeframes: 1h, 4h, 1d"
        )

    def format_error_invalid_timeframe(self, timeframe: str) -> str:
        """Format invalid timeframe error."""
        return (
            f"❌ Timeframe inválido: {timeframe}\n"
            f"Use: 1h, 4h ou 1d"
        )

    def format_error_generic(self, error_msg: str) -> str:
        """Format generic error message."""
        return f"❌ Erro: {error_msg}"

    def format_success_symbol_added(self, symbol: str, price: float) -> str:
        """Format symbol added success message."""
        return (
            f"✅ *{symbol} adicionado!*\n"
            f"Preço atual: ${price:,.2f}"
        )

    def format_success_symbol_removed(self, symbol: str) -> str:
        """Format symbol removed success message."""
        return f"✅ *{symbol} removido da watchlist*"

    def format_warning_symbol_not_in_watchlist(self, symbol: str) -> str:
        """Format symbol not in watchlist warning."""
        return f"⚠️ {symbol} não estava na watchlist"

    def format_processing(self, message: str) -> str:
        """Format processing/loading message."""
        return f"⏳ {message}"
