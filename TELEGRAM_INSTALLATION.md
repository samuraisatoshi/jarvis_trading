# Telegram Integration - Installation

Complete installation guide for the Telegram integration.

## Prerequisites

- Python 3.11+
- Active virtual environment
- Binance API access (for trading)
- Telegram account

---

## Installation Steps

### 1. Activate Virtual Environment

```bash
cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading
source .venv/bin/activate
```

### 2. Install Dependencies

The Telegram integration requires the `requests` library, which is already added to `requirements.txt`.

```bash
# Install/update all dependencies
pip install -r requirements.txt

# Or install just the new dependency
pip install requests>=2.31.0
```

**Verify installation:**
```bash
python -c "import requests; print(f'requests {requests.__version__} installed')"
```

### 3. Verify File Structure

Check that all files were created:

```bash
# Core infrastructure
ls -la src/infrastructure/notifications/
# Should show:
# - __init__.py
# - telegram_notifier.py
# - message_templates.py

# Scripts
ls -la scripts/ | grep telegram
# Should show:
# - setup_telegram.py (executable)
# - trading_with_telegram.py (executable)
# - telegram_status_bot.py (executable)

# Configuration
ls -la config/telegram_templates.yaml

# Documentation
ls -la TELEGRAM*.md
# Should show:
# - TELEGRAM_INTEGRATION_GUIDE.md
# - TELEGRAM_QUICKSTART.md
# - TELEGRAM_INDEX.md
# - TELEGRAM_INSTALLATION.md (this file)
```

### 4. Verify Script Permissions

```bash
# Make scripts executable (should already be done)
chmod +x scripts/setup_telegram.py
chmod +x scripts/trading_with_telegram.py
chmod +x scripts/telegram_status_bot.py

# Verify
ls -la scripts/*telegram*.py
# Should show -rwxr-xr-x (executable)
```

### 5. Create Telegram Bot

Follow the quick setup in `TELEGRAM_QUICKSTART.md`:

1. Open Telegram → @BotFather
2. Send `/newbot`
3. Copy bot token
4. Send message to bot
5. Get chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`

### 6. Run Setup Script

```bash
python scripts/setup_telegram.py
```

**Interactive prompts:**
```
Enter your Bot Token (from BotFather): [paste token]
Enter your Chat ID (numeric): [paste chat ID]
Additional chat IDs (optional): [press Enter]
Save this configuration? (y/n): y
```

**Expected output:**
```
🔧 Testing Telegram bot...
✅ Test message sent successfully!
   Check your Telegram chat: 123456789

✅ Configuration saved to .env
```

### 7. Verify Configuration

```bash
# Check .env file
cat .env | grep TELEGRAM

# Should show:
# TELEGRAM_BOT_TOKEN=your_token
# TELEGRAM_CHAT_ID=your_chat_id
# TELEGRAM_AUTHORIZED_CHAT_IDS=your_chat_id
```

### 8. Test Connection

```bash
python scripts/setup_telegram.py --test
```

**Expected output:**
```
Testing existing Telegram configuration...
🔧 Testing Telegram bot...
Telegram bot connected:
  Username: @your_bot
  Name: Your Bot Name
  ID: 123456789
✅ Test message sent successfully!
   Check your Telegram chat: 123456789
```

---

## Validation

### Quick Test

Run one-time trading cycle with notifications:

```bash
python scripts/trading_with_telegram.py
```

**You should receive:**
1. Market analysis notification
2. Trading signal notification
3. Trade execution notification (if conditions met)

**Check logs:**
```bash
tail -f logs/telegram_trading_BNB_USDT_1d.log
```

### Interactive Bot Test

```bash
# Start bot
python scripts/telegram_status_bot.py

# In Telegram, send:
/status
```

**You should receive:**
```
📊 SYSTEM STATUS

Daemon: 🔴 Stopped (or 🟢 Running)
Trading: ✅ Active
Symbol: BNB_USDT
...
```

---

## Troubleshooting Installation

### Issue: `requests` module not found

**Error:**
```
ModuleNotFoundError: No module named 'requests'
```

**Solution:**
```bash
pip install requests>=2.31.0
```

### Issue: Permission denied on scripts

**Error:**
```
-bash: ./scripts/setup_telegram.py: Permission denied
```

**Solution:**
```bash
chmod +x scripts/setup_telegram.py
chmod +x scripts/trading_with_telegram.py
chmod +x scripts/telegram_status_bot.py
```

### Issue: Import errors

**Error:**
```
ImportError: cannot import name 'TelegramNotifier'
```

**Diagnosis:**
```bash
# Check file exists
ls -la src/infrastructure/notifications/telegram_notifier.py

# Check __init__.py exists
ls -la src/infrastructure/notifications/__init__.py

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

**Solution:**
```bash
# Ensure project root in path
export PYTHONPATH=/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading:$PYTHONPATH
```

### Issue: .env not found

**Error:**
```
Telegram configuration not found in .env
```

**Solution:**
```bash
# Check if .env exists
ls -la .env

# If not, run setup
python scripts/setup_telegram.py
```

---

## Development Installation

For development/testing:

### Install in Editable Mode

```bash
pip install -e .
```

### Run Tests

```bash
# Test imports
python -c "from src.infrastructure.notifications import TelegramNotifier; print('✅ Import OK')"

# Test message templates
python -c "from src.infrastructure.notifications.message_templates import TradingMessageTemplates; print('✅ Templates OK')"

# Test configuration
python -c "import yaml; config = yaml.safe_load(open('config/telegram_templates.yaml')); print('✅ Config OK')"
```

### Lint Code

```bash
# Flake8
flake8 src/infrastructure/notifications/

# Black (format)
black src/infrastructure/notifications/

# MyPy (type checking)
mypy src/infrastructure/notifications/
```

---

## Uninstallation

If you need to remove the Telegram integration:

### 1. Stop Running Services

```bash
# Stop daemon if running
pkill -f trading_with_telegram.py

# Stop interactive bot if running
pkill -f telegram_status_bot.py
```

### 2. Remove Configuration

```bash
# Remove from .env
sed -i '' '/TELEGRAM_/d' .env
```

### 3. Remove Files (Optional)

```bash
# Remove infrastructure
rm -rf src/infrastructure/notifications/

# Remove scripts
rm scripts/setup_telegram.py
rm scripts/trading_with_telegram.py
rm scripts/telegram_status_bot.py

# Remove config
rm config/telegram_templates.yaml

# Remove documentation
rm TELEGRAM*.md
```

### 4. Remove Dependency (Optional)

If not used elsewhere:

```bash
pip uninstall requests
```

### 5. Delete Telegram Bot (Optional)

1. Open Telegram → @BotFather
2. Send `/deletebot`
3. Select your bot
4. Confirm deletion

---

## Upgrade

To upgrade to a newer version:

### 1. Backup Configuration

```bash
cp .env .env.backup
```

### 2. Update Code

```bash
# Pull latest changes (if using git)
git pull origin main

# Or manually replace files
```

### 3. Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### 4. Test Configuration

```bash
python scripts/setup_telegram.py --test
```

### 5. Restart Services

```bash
# Stop old services
pkill -f trading_with_telegram.py

# Start new version
python scripts/trading_with_telegram.py --daemon
```

---

## Docker Installation (Optional)

If using Docker:

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run
CMD ["python", "scripts/trading_with_telegram.py", "--daemon"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  jarvis_trading:
    build: .
    container_name: jarvis_trading_telegram
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Build and Run

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Post-Installation

After successful installation:

1. ✅ **Read documentation:**
   - Quick start: `TELEGRAM_QUICKSTART.md`
   - Full guide: `TELEGRAM_INTEGRATION_GUIDE.md`

2. ✅ **Start trading with notifications:**
   ```bash
   python scripts/trading_with_telegram.py --daemon
   ```

3. ✅ **Test interactive commands:**
   ```bash
   # In Telegram, send:
   /status
   /help
   ```

4. ✅ **Monitor logs:**
   ```bash
   tail -f logs/telegram_trading_BNB_USDT_1d.log
   ```

5. ✅ **Schedule daily execution:**
   ```bash
   # Add to crontab (optional, daemon mode handles this)
   0 0 * * * cd /path/to/jarvis_trading && source .venv/bin/activate && python scripts/trading_with_telegram.py
   ```

---

## System Requirements

**Minimum:**
- CPU: 1 core
- RAM: 512 MB
- Disk: 100 MB
- Network: Stable internet connection

**Recommended:**
- CPU: 2+ cores
- RAM: 2 GB
- Disk: 1 GB (for logs)
- Network: Low latency (< 100ms to Telegram API)

**Tested on:**
- macOS 14.5 (Darwin 24.5.0)
- Python 3.11.14
- Ubuntu 22.04 LTS
- Python 3.11+

---

## Dependencies

**Core:**
- `requests>=2.31.0` - HTTP client for Telegram API

**Existing (unchanged):**
- `python-dotenv>=1.0.0` - Environment configuration
- `pandas>=2.1.0` - Data processing
- `loguru>=0.7.0` - Logging

**Total added size:**
- Code: ~50 KB
- Dependencies: ~500 KB (requests)
- Documentation: ~100 KB

---

## Support

### Installation Issues

1. **Check logs:**
   ```bash
   tail -f logs/telegram_trading_*.log
   ```

2. **Verify imports:**
   ```bash
   python -c "from src.infrastructure.notifications import TelegramNotifier"
   ```

3. **Test connection:**
   ```bash
   python scripts/setup_telegram.py --test
   ```

4. **Check configuration:**
   ```bash
   cat .env | grep TELEGRAM
   ```

### Get Help

- **Quick start:** `TELEGRAM_QUICKSTART.md`
- **Full guide:** `TELEGRAM_INTEGRATION_GUIDE.md`
- **Index:** `TELEGRAM_INDEX.md`

---

## Summary

Installation checklist:

- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Files verified (src/, scripts/, config/)
- [ ] Scripts executable (`chmod +x`)
- [ ] Telegram bot created (via @BotFather)
- [ ] Configuration saved (`.env` file)
- [ ] Connection tested (`python scripts/setup_telegram.py --test`)
- [ ] First execution successful

**Total installation time:** ~5-10 minutes

Ready to trade with Telegram notifications! 🚀📱
