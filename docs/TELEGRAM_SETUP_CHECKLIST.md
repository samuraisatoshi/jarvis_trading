# Telegram Integration - Setup Checklist

Complete this checklist to ensure successful Telegram integration setup.

---

## Pre-Setup Checklist

### Environment

- [ ] Python 3.11+ installed
- [ ] Virtual environment activated (`.venv`)
- [ ] Project directory: `/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading`
- [ ] Internet connection active
- [ ] Telegram app installed (mobile or desktop)

### Prerequisites

```bash
cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading
source .venv/bin/activate
```

---

## Installation Checklist

### 1. Dependencies

- [ ] Run: `pip install -r requirements.txt`
- [ ] Verify: `python -c "import requests; print('OK')"`

**Command:**
```bash
pip install -r requirements.txt
python -c "import requests; print('✅ requests installed')"
```

### 2. Files Verification

- [ ] Infrastructure files exist:
  - [ ] `src/infrastructure/notifications/__init__.py`
  - [ ] `src/infrastructure/notifications/telegram_notifier.py`
  - [ ] `src/infrastructure/notifications/message_templates.py`

- [ ] Scripts exist and are executable:
  - [ ] `scripts/setup_telegram.py`
  - [ ] `scripts/trading_with_telegram.py`
  - [ ] `scripts/telegram_status_bot.py`

- [ ] Configuration exists:
  - [ ] `config/telegram_templates.yaml`

- [ ] Documentation exists:
  - [ ] `TELEGRAM_README.md`
  - [ ] `TELEGRAM_QUICKSTART.md`
  - [ ] `TELEGRAM_INTEGRATION_GUIDE.md`
  - [ ] `TELEGRAM_INSTALLATION.md`
  - [ ] `TELEGRAM_INDEX.md`
  - [ ] `TELEGRAM_EXECUTIVE_SUMMARY.md`
  - [ ] `TELEGRAM_DELIVERABLES.md`

**Verification:**
```bash
ls -la src/infrastructure/notifications/
ls -la scripts/*telegram*.py
ls -la config/telegram_templates.yaml
ls -la TELEGRAM*.md
```

---

## Telegram Bot Setup Checklist

### 3. Create Bot

- [ ] Open Telegram app
- [ ] Search for `@BotFather`
- [ ] Send `/newbot` to BotFather
- [ ] Enter bot name (e.g., `Jarvis Trading Bot`)
- [ ] Enter bot username (e.g., `jarvis_trading_bot`)
- [ ] Copy bot token (format: `123456789:ABCdef...`)
- [ ] Save token temporarily (you'll need it in next step)

**Example token:**
```
123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567
```

### 4. Get Chat ID

- [ ] Send any message to your new bot (e.g., "Hello")
- [ ] Open browser
- [ ] Navigate to: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
  - Replace `<YOUR_TOKEN>` with your actual token
- [ ] Find `"chat":{"id":123456789}` in JSON response
- [ ] Copy the chat ID number
- [ ] Save chat ID temporarily

**Example URL:**
```
https://api.telegram.org/bot123456789:ABCdef.../getUpdates
```

**Example response:**
```json
{
  "ok": true,
  "result": [{
    "message": {
      "chat": {
        "id": 123456789  ← YOUR CHAT ID
      }
    }
  }]
}
```

---

## Configuration Checklist

### 5. Run Setup Script

- [ ] Run: `python scripts/setup_telegram.py`
- [ ] Enter bot token when prompted
- [ ] Enter chat ID when prompted
- [ ] Leave additional chat IDs blank (press Enter)
- [ ] Confirm configuration (type `y`)
- [ ] Wait for test message
- [ ] Receive test message in Telegram
- [ ] See "✅ Configuration saved" message

**Expected output:**
```
Enter your Bot Token (from BotFather): [paste token]
Enter your Chat ID (numeric): [paste chat ID]
Additional chat IDs (optional): [press Enter]

Save this configuration? (y/n): y

🔧 Testing Telegram bot...
✅ Test message sent successfully!
✅ Configuration saved to .env
```

### 6. Verify Configuration

- [ ] Check `.env` file exists
- [ ] Verify token in `.env`: `cat .env | grep TELEGRAM_BOT_TOKEN`
- [ ] Verify chat ID in `.env`: `cat .env | grep TELEGRAM_CHAT_ID`
- [ ] Verify authorized IDs in `.env`: `cat .env | grep TELEGRAM_AUTHORIZED_CHAT_IDS`

**Verification:**
```bash
cat .env | grep TELEGRAM

# Should show:
# TELEGRAM_BOT_TOKEN=123456789:ABCdef...
# TELEGRAM_CHAT_ID=123456789
# TELEGRAM_AUTHORIZED_CHAT_IDS=123456789
```

### 7. Test Connection

- [ ] Run: `python scripts/setup_telegram.py --test`
- [ ] See "Telegram bot connected" message
- [ ] See bot username and ID
- [ ] Receive test message in Telegram

**Expected output:**
```
Testing existing Telegram configuration...
🔧 Testing Telegram bot...
Telegram bot connected:
  Username: @your_bot
  Name: Your Bot Name
  ID: 123456789
✅ Test message sent successfully!
```

---

## First Execution Checklist

### 8. One-Time Test

- [ ] Run: `python scripts/trading_with_telegram.py`
- [ ] See system startup in logs
- [ ] Receive startup notification in Telegram
- [ ] See market analysis in logs
- [ ] Receive market analysis in Telegram
- [ ] See trading signal in logs
- [ ] Receive trading signal in Telegram
- [ ] Check logs for errors: `tail -f logs/telegram_trading_BNB_USDT_1d.log`

**Check Telegram for:**
```
🚀 SISTEMA INICIADO
📊 Par: BNB_USDT
...

📊 ANÁLISE DE MERCADO
🪙 Ativo: BNB_USDT
...

🎯 SINAL DE TRADING
📊 Análise: ...
```

### 9. Dry Run Test

- [ ] Run: `python scripts/trading_with_telegram.py --dry-run`
- [ ] Receive notifications in Telegram
- [ ] Verify no trades executed (check "DRY RUN" in logs)
- [ ] Confirm balance unchanged

**Verify in logs:**
```
DRY RUN: No trade executed
```

---

## Interactive Bot Checklist

### 10. Start Status Bot

- [ ] Run: `python scripts/telegram_status_bot.py`
- [ ] See "Starting Telegram status bot" in logs
- [ ] Leave terminal open (bot running)

### 11. Test Commands

Send each command in Telegram and verify response:

- [ ] Send `/status` → Receive system status
- [ ] Send `/balance` → Receive balance details
- [ ] Send `/trades` → Receive trade history
- [ ] Send `/performance` → Receive metrics
- [ ] Send `/health` → Receive health check
- [ ] Send `/help` → Receive command list

**Example:**
```
You: /status
Bot: 📊 SYSTEM STATUS
     Daemon: 🔴 Stopped
     Trading: ✅ Active
     ...
```

---

## Production Deployment Checklist

### 12. Daemon Mode

- [ ] Stop test executions (Ctrl+C)
- [ ] Run: `python scripts/trading_with_telegram.py --daemon`
- [ ] See "Starting daemon mode" in logs
- [ ] Receive startup notification
- [ ] Verify scheduled execution time (00:00 UTC)
- [ ] Keep terminal open OR run in background

**Background execution:**
```bash
nohup python scripts/trading_with_telegram.py --daemon > logs/daemon.log 2>&1 &
```

### 13. Process Management

- [ ] Check if daemon is running: `ps aux | grep trading_with_telegram`
- [ ] Check PID file exists: `ls -la paper_trading.pid`
- [ ] Monitor logs: `tail -f logs/telegram_trading_BNB_USDT_1d.log`

**Optional: Add to crontab for auto-restart**
```bash
@reboot cd /path/to/jarvis_trading && source .venv/bin/activate && python scripts/trading_with_telegram.py --daemon
```

---

## Validation Checklist

### 14. Full Integration Test

- [ ] Daemon running in background
- [ ] Interactive bot running (optional)
- [ ] Receive notifications:
  - [ ] Startup notification received
  - [ ] Market analysis received (on schedule)
  - [ ] Signal notifications received
  - [ ] Trade execution notifications (if executed)
- [ ] Commands working:
  - [ ] `/status` responds correctly
  - [ ] `/balance` shows current balance
  - [ ] `/trades` shows history

### 15. Error Handling Test

- [ ] Stop Binance API (disconnect network briefly)
- [ ] Receive error notification in Telegram
- [ ] Restore network
- [ ] Verify system recovers
- [ ] Check retry logic in logs

### 16. Circuit Breaker Test (Optional)

**⚠️ Warning: This will pause trading**

- [ ] Send `/pause` to bot
- [ ] Verify "TRADING PAUSED" notification
- [ ] Send `/resume` to bot
- [ ] Verify "TRADING RESUMED" notification

---

## Monitoring Checklist

### 17. Daily Monitoring

- [ ] Check Telegram for notifications
- [ ] Send `/status` to bot daily
- [ ] Review logs weekly: `tail -100 logs/telegram_trading_*.log`
- [ ] Monitor message statistics: `grep "messages_sent" logs/*.log`

### 18. Log Management

- [ ] Logs rotating correctly (check file sizes)
- [ ] Old logs archived (30-day retention)
- [ ] Disk space sufficient: `df -h`

**Check log sizes:**
```bash
ls -lh logs/telegram_trading_*.log
```

---

## Security Checklist

### 19. Security Verification

- [ ] `.env` file exists and contains token
- [ ] `.env` is in `.gitignore` (verify: `cat .gitignore | grep .env`)
- [ ] Token not committed to git (verify: `git log --all -p | grep TELEGRAM_BOT_TOKEN`)
- [ ] Only authorized chat IDs in whitelist
- [ ] Rate limiting enabled (check config)

**Verify .gitignore:**
```bash
cat .gitignore | grep "^.env$"
# Should show: .env
```

### 20. Access Control

- [ ] Only you can send commands to bot
- [ ] Test with another Telegram account (should be rejected)
- [ ] Check logs for unauthorized access attempts
- [ ] Review authorized chat IDs monthly

---

## Documentation Checklist

### 21. Read Documentation

- [ ] Read: `TELEGRAM_README.md` (overview)
- [ ] Read: `TELEGRAM_QUICKSTART.md` (quick reference)
- [ ] Bookmark: `TELEGRAM_INTEGRATION_GUIDE.md` (full guide)
- [ ] Understand troubleshooting section

### 22. Troubleshooting Knowledge

- [ ] Know how to test connection: `python scripts/setup_telegram.py --test`
- [ ] Know how to check logs: `tail -f logs/telegram_trading_*.log`
- [ ] Know how to restart daemon: Kill process and restart
- [ ] Know how to disable Telegram: Use `--no-telegram` flag

---

## Final Checklist

### 23. Production Ready

- [ ] All notifications working
- [ ] All commands responding
- [ ] Daemon running stable
- [ ] Logs clean (no errors)
- [ ] Documentation understood
- [ ] Monitoring routine established

### 24. Backup Configuration

- [ ] Backup `.env` file: `cp .env .env.backup`
- [ ] Store bot token securely (password manager)
- [ ] Document chat ID (in secure location)

**Backup command:**
```bash
cp .env .env.backup
# Store .env.backup in secure location (not in git)
```

---

## Completion Summary

### Check Your Status

**Count completed items:**
```
[ ] Setup: 24 items
[ ] All items checked: ✅
```

### Success Criteria

✅ **Minimum (working system):**
- Dependencies installed
- Bot created and configured
- At least one notification received
- Daemon running

✅ **Recommended (production ready):**
- All notifications working
- Interactive bot responding
- Logs clean
- Documentation read
- Backup created

✅ **Optimal (fully monitored):**
- All checklist items completed
- Daily monitoring routine
- Security verified
- Performance validated

---

## Next Steps After Completion

1. **Monitor first 24 hours:**
   - Check Telegram regularly
   - Review logs
   - Verify scheduled execution

2. **Establish routine:**
   - Daily: Check `/status`
   - Weekly: Review logs
   - Monthly: Review performance

3. **Optimize:**
   - Adjust notification preferences (if needed)
   - Add more authorized users (if team)
   - Customize message templates (if desired)

---

## Support

If any checklist item fails:

1. **Check documentation:**
   - `TELEGRAM_QUICKSTART.md` - Quick fixes
   - `TELEGRAM_INSTALLATION.md` - Setup issues
   - `TELEGRAM_INTEGRATION_GUIDE.md` - Comprehensive troubleshooting

2. **Test connection:**
   ```bash
   python scripts/setup_telegram.py --test
   ```

3. **Check logs:**
   ```bash
   tail -50 logs/telegram_trading_*.log | grep -i error
   ```

4. **Verify configuration:**
   ```bash
   cat .env | grep TELEGRAM
   ```

---

## Checklist Status

**Setup started:** _______________ (date)
**Setup completed:** _______________ (date)
**Time taken:** _______________ (should be ~5-10 minutes)
**Status:** [ ] Completed successfully

---

**Congratulations! 🎉**

If all items are checked, your Telegram integration is complete and production-ready!

**Happy Trading! 🚀📱**
