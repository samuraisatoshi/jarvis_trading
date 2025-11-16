# Telegram Integration - Quick Start

Complete Telegram integration in 5 minutes! 🚀

## What You Get

📱 **Real-time notifications:**
- 🚀 System startup/shutdown
- 📊 Market analysis
- 🎯 Trading signals (BUY/SELL/HOLD)
- ✅ Trade execution confirmations
- 🚨 Circuit breaker alerts
- ⚠️ Error notifications

🤖 **Interactive commands:**
```
/status      - System status
/balance     - Account balance
/trades      - Trade history
/performance - Performance metrics
/pause       - Pause trading
/resume      - Resume trading
/report      - Full report
```

---

## Setup (5 minutes)

### 1. Create Telegram Bot

1. Open Telegram → Search `@BotFather`
2. Send `/newbot`
3. Name it: `Jarvis Trading Bot`
4. Copy the **token** (like `123456789:ABCdef...`)

### 2. Get Chat ID

1. Send any message to your new bot
2. Open: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` → Copy the **number**

### 3. Configure

```bash
cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading
source .venv/bin/activate

# Run interactive setup
python scripts/setup_telegram.py
```

Enter:
- Bot token: `123456789:ABCdef...`
- Chat ID: `123456789`

Done! ✅ You'll receive a test message.

---

## Usage

### Start Trading with Telegram

```bash
# Daemon mode (scheduled daily at 00:00 UTC)
python scripts/trading_with_telegram.py --daemon

# One-time execution
python scripts/trading_with_telegram.py

# Dry run (no trades, only notifications)
python scripts/trading_with_telegram.py --dry-run
```

### Interactive Bot

```bash
# Start bot (responds to commands)
python scripts/telegram_status_bot.py
```

Send commands in Telegram:
```
/status    → Get current status
/balance   → Check balance
/trades    → Recent trades
/pause     → Stop trading
```

---

## Example Notifications

### Startup
```
🚀 SISTEMA INICIADO

📊 Par: BNB_USDT
⏰ Timeframe: 1d
💰 Saldo inicial: $10,000.00 USDT

✅ Sistema operacional
⏰ 2025-11-15 00:00:00 UTC
```

### Trading Signal
```
🎯 SINAL DE TRADING - BNB_USDT

📊 Análise do Modelo:
• Ação: COMPRAR 💚
• Confiança: 65%
• Preço: $926.49

📈 Indicadores:
• RSI: 32 (sobrevendido)
• MACD: Cruzamento alta
• Volume: +15%
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
```

### Circuit Breaker
```
🚨 CIRCUIT BREAKER ATIVADO

⚠️ Razão: Drawdown máximo excedido
📉 Drawdown atual: 16%
🛑 Limite: 15%

🔒 Trading pausado
```

---

## Troubleshooting

### Not receiving messages?

1. **Did you send a message to your bot first?** (Required to start conversation)

2. **Test connection:**
   ```bash
   python scripts/setup_telegram.py --test
   ```

3. **Check configuration:**
   ```bash
   cat .env | grep TELEGRAM
   ```

4. **Check logs:**
   ```bash
   tail -f logs/telegram_trading_BNB_USDT_1d.log
   ```

### Common errors

**"Telegram configuration not found"**
```bash
python scripts/setup_telegram.py
```

**"Unauthorized chat_id"**

Edit `.env`:
```bash
TELEGRAM_AUTHORIZED_CHAT_IDS=123456789,your_other_id
```

**"Rate limit reached"**

Wait 60 seconds. System auto-retries.

---

## Files Created

```
jarvis_trading/
├── src/infrastructure/notifications/
│   ├── telegram_notifier.py        # Core service
│   ├── message_templates.py        # Message formatting
│   └── __init__.py
│
├── scripts/
│   ├── setup_telegram.py           # Setup wizard
│   ├── trading_with_telegram.py    # Trading + notifications
│   └── telegram_status_bot.py      # Interactive bot
│
├── config/
│   └── telegram_templates.yaml     # Configuration
│
├── .env (your credentials)
└── TELEGRAM_INTEGRATION_GUIDE.md   # Full documentation
```

---

## Security

✅ **Never commit `.env`** (contains bot token)
✅ **Whitelist authorized users** (in `.env`)
✅ **Rate limiting enabled** (max 30 msgs/min)
✅ **Regenerate token if compromised** (via @BotFather)

---

## Next Steps

1. ✅ Complete setup: `python scripts/setup_telegram.py`
2. ✅ Start trading: `python scripts/trading_with_telegram.py --daemon`
3. ✅ Test commands: Send `/status` to your bot
4. ✅ Read full docs: `TELEGRAM_INTEGRATION_GUIDE.md`

---

## Commands Reference Card

```
📊 MONITORING
/status        Current system status
/balance       Account balance
/trades        Recent trades (last 10)
/performance   Performance metrics (7 days)
/health        System health check
/report        Comprehensive report

🎮 CONTROL
/pause         Pause trading
/resume        Resume trading

❓ HELP
/help          Show all commands
```

---

## Support

Need help? Check:

1. **Full guide:** `TELEGRAM_INTEGRATION_GUIDE.md`
2. **Test setup:** `python scripts/setup_telegram.py --test`
3. **Logs:** `tail -f logs/telegram_trading_*.log`

Happy Trading! 🚀📱
