# Telegram Integration Guide - Jarvis Trading

Complete guide for setting up and using Telegram notifications for your trading system.

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Setup Instructions](#setup-instructions)
5. [Usage](#usage)
6. [Commands Reference](#commands-reference)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)
9. [Security](#security)

---

## Overview

This Telegram integration provides real-time notifications and interactive control for your paper trading system. Get instant alerts for trades, market analysis, errors, and control your system via Telegram commands.

**Key Benefits:**
- 📱 Real-time notifications on your phone
- 🤖 Interactive bot commands
- 📊 Performance reports
- 🚨 Circuit breaker alerts
- ⚡ Zero configuration needed (after setup)

---

## Features

### Automatic Notifications

**System Events:**
- ✅ System startup/shutdown
- ✅ Circuit breaker activation
- ✅ Critical errors and warnings

**Market Analysis:**
- 📊 Market analysis every execution
- 📈 Technical indicator summaries
- 💹 Price movements

**Trading Signals:**
- 🎯 BUY/SELL/HOLD signals
- 📊 Confidence scores
- 💡 Reasoning and indicators

**Trade Executions:**
- ✅ Trade confirmations
- 💰 Balance updates
- 📈 Position changes

**Performance Reports:**
- 📊 Daily summaries
- 📈 Weekly reports
- 💹 Performance metrics

### Interactive Commands

Control your trading system via Telegram:

```
/status      - Current system status
/balance     - Account balance
/trades      - Recent trade history
/performance - Performance metrics
/health      - Full health check
/pause       - Pause trading
/resume      - Resume trading
/report      - Comprehensive report
/help        - Show available commands
```

---

## Architecture

### Components

```
src/infrastructure/notifications/
├── telegram_notifier.py       # Core notification service
├── message_templates.py        # Message formatting
└── __init__.py

scripts/
├── setup_telegram.py           # Interactive setup
├── trading_with_telegram.py    # Trading system with notifications
└── telegram_status_bot.py      # Interactive bot

config/
└── telegram_templates.yaml     # Message template configuration
```

### Flow Diagram

```
Trading System
    ↓
Trading Event (signal, execution, error)
    ↓
TradingMessageTemplates (format message)
    ↓
TelegramNotifier (rate limiting, retry logic)
    ↓
Telegram Bot API
    ↓
Your Phone 📱
```

---

## Setup Instructions

### Step 1: Create Telegram Bot

1. **Open Telegram** and search for `@BotFather`

2. **Send `/newbot`** to BotFather

3. **Name your bot:**
   ```
   Bot name: Jarvis Trading Bot
   Username: jarvis_trading_bot (must be unique)
   ```

4. **Copy the token** that BotFather gives you:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567
   ```

### Step 2: Get Your Chat ID

1. **Send a message** to your new bot (any message like "Hello")

2. **Open this URL** in your browser (replace YOUR_TOKEN):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```

3. **Find your chat ID** in the JSON response:
   ```json
   {
     "result": [{
       "message": {
         "chat": {
           "id": 123456789  ← This is your chat ID
         }
       }
     }]
   }
   ```

### Step 3: Run Setup Script

```bash
cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading

# Activate environment
source .venv/bin/activate

# Run interactive setup
python scripts/setup_telegram.py
```

The script will:
1. Ask for your bot token
2. Ask for your chat ID
3. Test the connection
4. Send a test message
5. Save configuration to `.env`

**Example:**

```bash
$ python scripts/setup_telegram.py

================================================================================
🤖 TELEGRAM BOT SETUP - TRADING NOTIFICATIONS
================================================================================

📋 STEP 1: Create a Telegram Bot
----------------------------------------
1. Open Telegram and search for @BotFather
2. Send /newbot to BotFather
3. Follow instructions to name your bot
4. BotFather will give you a TOKEN - copy it!

📋 STEP 2: Get Your Chat ID
----------------------------------------
1. Send a message to your new bot (any message)
2. Open this URL in browser (replace YOUR_TOKEN):
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
3. Find 'chat':{'id': YOUR_CHAT_ID} in the response
4. Copy the chat ID number

📋 STEP 3: Run This Script
----------------------------------------
   python scripts/setup_telegram.py

================================================================================
📝 CONFIGURATION
================================================================================

Enter your Bot Token (from BotFather): 123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567
Enter your Chat ID (numeric): 123456789

(Optional) Enter additional authorized chat IDs
If you want to allow multiple users, enter their chat IDs separated by commas
Leave blank to only allow the main chat ID
Additional chat IDs (optional):

================================================================================
📋 CONFIGURATION SUMMARY
================================================================================
Bot Token: 123456789:...1234567
Chat ID: 123456789
Authorized Chat IDs: 123456789
================================================================================

Save this configuration? (y/n): y

🔧 Testing Telegram bot...
✅ Test message sent successfully!
   Check your Telegram chat: 123456789

✅ Configuration saved to .env

================================================================================
✅ SETUP COMPLETE!
================================================================================

Your Telegram bot is now configured.

Next steps:
1. Run paper trading with Telegram notifications:
   python scripts/trading_with_telegram.py --daemon

2. Check bot status:
   python scripts/telegram_status_bot.py

3. Monitor trading:
   python scripts/monitor_paper_trading.py
================================================================================
```

### Step 4: Test Configuration

```bash
# Test existing configuration
python scripts/setup_telegram.py --test
```

---

## Usage

### Option 1: Paper Trading with Telegram (Recommended)

Run the enhanced paper trading system with full Telegram integration:

```bash
# One-time execution
python scripts/trading_with_telegram.py

# Daemon mode (scheduled execution)
python scripts/trading_with_telegram.py --daemon

# Dry run (no trades, but notifications)
python scripts/trading_with_telegram.py --dry-run

# Custom symbol
python scripts/trading_with_telegram.py --symbol BTC_USDT --daemon

# Disable Telegram (use original behavior)
python scripts/trading_with_telegram.py --no-telegram
```

**What you'll receive:**
- 🚀 Startup notification with initial balance
- 📊 Market analysis every execution
- 🎯 Trading signals (BUY/SELL/HOLD)
- ✅ Trade execution confirmations
- 🚨 Circuit breaker alerts
- ⚠️ Error notifications

### Option 2: Interactive Status Bot

Run the interactive bot for on-demand status checks:

```bash
# Start interactive bot (responds to commands)
python scripts/telegram_status_bot.py

# Send single command and exit
python scripts/telegram_status_bot.py --command /status
```

**Send commands via Telegram:**
```
You: /status
Bot: 📊 SYSTEM STATUS
     Daemon: 🟢 Running
     Trading: ✅ Active
     ...

You: /balance
Bot: 💰 ACCOUNT BALANCE
     Available Balances:
     • USDT: 5000.00
     • BNB: 5.39
     ...

You: /pause
Bot: ⏸️ TRADING PAUSED
     Trading has been paused manually.
     ...
```

---

## Commands Reference

### System Status

#### `/status`
Get current system status, daemon state, and balance summary.

**Response:**
```
📊 SYSTEM STATUS

Daemon: 🟢 Running
Trading: ✅ Active
Symbol: BNB_USDT
Price: $926.49

💰 Balance:
• USDT: $5,000.00
• BNB: 5.39
• Position: $4,994.76
• Total: $9,994.76

⏰ 2025-11-15 00:00:00 UTC
```

#### `/balance`
Detailed balance and portfolio value.

**Response:**
```
💰 ACCOUNT BALANCE

Available Balances:
• USDT: 5000.00
• BNB: 5.39

Current Position:
• Price: $926.49
• Value: $4,994.76

Total Portfolio Value:
💵 $9,994.76

⏰ 2025-11-15 00:00:00 UTC
```

#### `/trades`
Recent trade history (last 10 trades).

**Response:**
```
📝 RECENT TRADES (Last 10)

🟢 BUY
  Amount: 5.39 BNB
  Time: 2025-11-15 00:00
  Note: BUY 5.39 BNB @ $926.49

🔴 SELL
  Amount: 5.39 BNB
  Time: 2025-11-14 00:00
  Note: SELL 5.39 BNB @ $920.15

⏰ 2025-11-15 00:00:00 UTC
```

### Performance Metrics

#### `/performance`
Performance metrics for the last 7 days.

**Response:**
```
📊 PERFORMANCE METRICS
📅 Last 7 days

Trading Activity:
• Trades: 15
• Wins: 9 ✅
• Losses: 6 ❌
• Win Rate: 60.0%

Profit & Loss:
• Total P&L: $+245.67
• Total P&L%: +2.46%

Best Trade:
• $+89.23 (+0.89%)
• 2025-11-12

Worst Trade:
• $-45.12 (-0.45%)
• 2025-11-10

⏰ 2025-11-15 00:00:00 UTC
```

#### `/health`
Full system health check.

**Response:**
```
🏥 HEALTH CHECK

System Components:
• Binance API: ✅ Connected
• Database: ✅ OK
• Daemon: ✅ Running
• Log File: ✅ 2.45MB (modified 2025-11-15 00:00)

Trading Status:
• Mode: ✅ Active
• Symbol: BNB_USDT
• Account: 868e0dd8...

⏰ 2025-11-15 00:00:00 UTC
```

### Control Commands

#### `/pause`
Pause trading (manual circuit breaker).

**Response:**
```
⏸️ TRADING PAUSED

Trading has been paused manually.
No new trades will be executed.

Use /resume to resume trading.

⏰ 2025-11-15 00:00:00 UTC
```

#### `/resume`
Resume trading after pause.

**Response:**
```
✅ TRADING RESUMED

Trading has been resumed.
System will execute trades normally.

⏰ 2025-11-15 00:00:00 UTC
```

### Reports

#### `/report`
Comprehensive report combining all information.

**Response:**
```
📋 COMPREHENSIVE TRADING REPORT
========================================

[Includes /status, /balance, /performance, /health combined]
```

#### `/help`
Show all available commands.

---

## Configuration

### Environment Variables (.env)

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567
TELEGRAM_CHAT_ID=123456789
TELEGRAM_AUTHORIZED_CHAT_IDS=123456789,987654321
```

### Template Configuration (config/telegram_templates.yaml)

Customize message templates, thresholds, and notification preferences:

```yaml
# Notification Preferences
notifications:
  startup: true
  shutdown: true
  market_analysis: true
  trade_signals: true
  trade_executions: true
  circuit_breaker: true
  daily_reports: true
  weekly_reports: true
  errors: true
  warnings: true
  health_checks: false  # On-demand only

# Rate Limiting
rate_limiting:
  max_messages_per_minute: 30
  retry_attempts: 3
  retry_delay_seconds: 2

# Formatting
formatting:
  parse_mode: "HTML"  # HTML, Markdown, MarkdownV2
  disable_web_page_preview: true
  disable_notification: false
```

---

## Troubleshooting

### Common Issues

#### 1. "Telegram configuration not found in .env"

**Solution:**
```bash
python scripts/setup_telegram.py
```

#### 2. "Bot connection test failed"

**Possible causes:**
- Invalid bot token
- Bot was deleted by BotFather
- Network connectivity issues

**Solution:**
1. Verify token in `.env` matches BotFather token
2. Test manually:
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```

#### 3. "Unauthorized chat_id"

**Cause:** Chat ID not in authorized list.

**Solution:**
Edit `.env` and add chat ID to `TELEGRAM_AUTHORIZED_CHAT_IDS`:
```bash
TELEGRAM_AUTHORIZED_CHAT_IDS=123456789,987654321,555555555
```

#### 4. "Rate limit reached"

**Cause:** Sending more than 30 messages per minute.

**Solution:**
- System will auto-wait and retry
- Adjust `max_messages_per_minute` in `config/telegram_templates.yaml`

#### 5. Messages not received

**Checklist:**
- [ ] Did you start a conversation with your bot? (Send any message first)
- [ ] Is bot token correct in `.env`?
- [ ] Is chat ID correct in `.env`?
- [ ] Check logs for errors:
  ```bash
  tail -f logs/telegram_trading_BNB_USDT_1d.log
  ```

---

## Security

### Best Practices

1. **Never commit `.env` to version control**
   - Already in `.gitignore`
   - Contains sensitive bot token

2. **Use whitelist authorization**
   ```bash
   TELEGRAM_AUTHORIZED_CHAT_IDS=your_chat_id,trusted_friend_id
   ```

3. **Keep bot token secret**
   - Don't share publicly
   - Regenerate if compromised (via BotFather)

4. **Monitor unauthorized access**
   - Check logs for unauthorized chat IDs
   - Bot will reject unauthorized users automatically

5. **Rate limiting enabled**
   - Prevents API abuse
   - Max 30 messages/minute default

### Regenerate Bot Token (if compromised)

1. Open Telegram → @BotFather
2. Send `/token`
3. Select your bot
4. Get new token
5. Update `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=new_token_here
   ```
6. Restart trading system

---

## Example Notification Flow

### System Startup
```
🚀 SISTEMA INICIADO

📊 Par: BNB_USDT
⏰ Timeframe: 1d
💰 Saldo inicial: $10,000.00 USDT
🆔 Conta: 868e0dd8-37f5-43ea-a956-7cc05e6bad66

✅ Sistema operacional e monitorando mercado
⏰ 2025-11-15 00:00:00 UTC
```

### Trading Signal
```
🎯 SINAL DE TRADING - BNB_USDT

📊 Análise do Modelo:
• Ação: COMPRAR 💚
• Confiança: 65.0%
• Preço atual: $926.49

📈 Indicadores:
• RSI: 32.5
• MACD: cruzamento alta
• Volume: +15.3%

⏰ 2025-11-15 00:00:15 UTC
```

### Trade Executed
```
✅ TRADE EXECUTADO

🪙 Ativo: BNB_USDT
📝 Tipo: BUY
📊 Quantidade: 5.39 BNB
💵 Preço: $926.49
💰 Total: $5,000.00 USDT

📈 Novo Saldo:
• USDT: $5,000.00
• BNB: 5.39
• Valor total: $9,994.76

⏰ 2025-11-15 00:00:20 UTC
```

### Circuit Breaker
```
🚨 CIRCUIT BREAKER ATIVADO

⚠️ Razão: Drawdown máximo excedido
📉 Drawdown atual: 16.2%
🛑 Limite máximo: 15.0%

🔒 Trading pausado até revisão manual

⏰ 2025-11-15 12:30:00 UTC
```

---

## Advanced Usage

### Multiple Bots

Run multiple trading systems with separate bots:

```bash
# Bot 1: BNB_USDT
TELEGRAM_BOT_TOKEN_BNB=token1
TELEGRAM_CHAT_ID_BNB=chat1
python scripts/trading_with_telegram.py --symbol BNB_USDT

# Bot 2: BTC_USDT
TELEGRAM_BOT_TOKEN_BTC=token2
TELEGRAM_CHAT_ID_BTC=chat2
python scripts/trading_with_telegram.py --symbol BTC_USDT
```

### Custom Message Templates

Edit `src/infrastructure/notifications/message_templates.py` to customize:

```python
@classmethod
def trade_signal(cls, symbol, action, confidence, ...):
    # Customize message format here
    return custom_message
```

### Programmatic Usage

Use directly in your code:

```python
from src.infrastructure.notifications.telegram_notifier import TelegramNotifier
from src.infrastructure.notifications.message_templates import TradingMessageTemplates

# Initialize
notifier = TelegramNotifier(
    bot_token="your_token",
    chat_id="your_chat_id"
)

# Send custom message
message = "🎉 Custom notification"
notifier.send_message(message)

# Use templates
msg = TradingMessageTemplates.trade_executed(
    trade_type="BUY",
    symbol="BNB_USDT",
    quantity=5.39,
    price=926.49,
    ...
)
notifier.send_message(msg)
```

---

## Support

### Get Help

1. **Check logs:**
   ```bash
   tail -f logs/telegram_trading_BNB_USDT_1d.log
   ```

2. **Test connection:**
   ```bash
   python scripts/setup_telegram.py --test
   ```

3. **Verify configuration:**
   ```bash
   cat .env | grep TELEGRAM
   ```

4. **Test manual message:**
   ```bash
   python -c "
   from src.infrastructure.notifications.telegram_notifier import TelegramNotifier
   bot = TelegramNotifier('YOUR_TOKEN', 'YOUR_CHAT_ID', parse_mode='HTML')
   bot.send_message('<b>Test</b>')
   "
   ```

---

## Summary

You now have a fully functional Telegram integration for your trading system with:

✅ Real-time notifications for all trading events
✅ Interactive bot commands for monitoring and control
✅ Circuit breaker alerts
✅ Performance reports
✅ Secure whitelist authorization
✅ Rate limiting and retry logic
✅ Comprehensive error handling

**Next Steps:**
1. Complete setup: `python scripts/setup_telegram.py`
2. Start trading: `python scripts/trading_with_telegram.py --daemon`
3. Monitor via Telegram commands: `/status`, `/balance`, `/trades`

Happy Trading! 🚀
