# JARVIS Paper Trading - Deployment Report
**Status**: OPERATIONAL
**Deployed**: 2025-11-14 16:44:59 UTC
**Next Execution**: 2025-11-15 00:00:00 UTC (~7h15min)

---

## 1. System Overview

### Trading Configuration
- **Model**: BNB_USDT_1d_ppo_model.zip (Winner +25% in 2025)
- **Timeframe**: 1 day (executes at 00:00 UTC daily)
- **Account ID**: 868e0dd8-37f5-43ea-a956-7cc05e6bad66
- **Initial Capital**: $5,000 USDT
- **Position Size**: 100% (as tested in backtest)
- **Mode**: Paper Trading (zero risk)

### Model Performance (Backtest 2025)
- **Period**: Jan 1 - Nov 14, 2025 (318 days)
- **Return**: +25.0%
- **Final Balance**: $6,249.22
- **Trades**: 1 (low frequency, low fees)
- **vs Buy & Hold**: -5% (83% capture rate - ACCEPTABLE)
- **Market Context**: BNB uptrend (+30% buy & hold)

---

## 2. Deployment Status

### Daemon Process
```
Status:     RUNNING
PID:        73438
Started:    2025-11-14 16:44:59 UTC
Uptime:     ~2 minutes
Log File:   logs/paper_trading_BNB_USDT_1d.log
PID File:   paper_trading.pid
```

### Health Check
```
Health Status:       HEALTHY
Risk Score:          20/100 (LOW)
Daemon Status:       RUNNING
Portfolio Value:     $5,000.00 (initial state)
Daily P&L:           $0.00 (no trades yet)
Drawdown:            0.00%
Active Positions:    0
Consecutive Losses:  0
```

---

## 3. Circuit Breakers (Active)

The system has 5 circuit breakers that will automatically PAUSE trading if triggered:

| Circuit Breaker      | Threshold  | Recovery Time | Status   |
|----------------------|------------|---------------|----------|
| **Drawdown**         | > 20%      | 1 hour        | ARMED    |
| **Daily Loss**       | > 10%      | 24 hours      | ARMED    |
| **Consecutive Losses**| ≥ 3 losses | 30 minutes    | ARMED    |
| **API Latency**      | > 5 seconds| 10 minutes    | ARMED    |
| **API Failures**     | ≥ 5/hour   | 30 minutes    | ARMED    |

**What happens when triggered?**
1. Trading is PAUSED immediately
2. Alert notification sent
3. System waits for recovery time
4. Manual review required for critical breakers

---

## 4. Monitoring & Alerts

### Automatic Health Checks
```bash
# Manual check
cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading
.venv/bin/python scripts/auto_health_check.py

# Cron job (every hour) - TO BE CONFIGURED
0 * * * * cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading && .venv/bin/python scripts/auto_health_check.py >> logs/cron.log 2>&1
```

### Manual Monitoring
```bash
# Check daemon status
.venv/bin/python scripts/monitor_paper_trading.py status

# Full health report
.venv/bin/python scripts/monitor_paper_trading.py health

# View recent logs
tail -f logs/paper_trading_BNB_USDT_1d.log

# Check account balance
.venv/bin/python scripts/check_account_status.py
```

### Control Commands
```bash
# Pause trading (emergency)
.venv/bin/python scripts/monitor_paper_trading.py pause

# Resume trading
.venv/bin/python scripts/monitor_paper_trading.py resume

# Stop daemon completely
.venv/bin/python scripts/monitor_paper_trading.py stop
kill -15 73438

# Restart daemon
.venv/bin/python scripts/run_paper_trading.py \
  --account-id=868e0dd8-37f5-43ea-a956-7cc05e6bad66 \
  --symbol=BNB_USDT \
  --timeframe=1d \
  --models-path=/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models \
  --db=data/jarvis_trading.db \
  --daemon &
```

---

## 5. Operation Schedule

### Daily Execution (1d timeframe)
- **Execution Time**: 00:00:00 UTC (daily)
- **Process**:
  1. Fetch latest 300 candles from Binance
  2. Calculate 13 core features (RSI, MACD, BB, etc)
  3. Get model prediction (BUY/SELL/HOLD)
  4. Execute trade if confidence > 30%
  5. Update account balance in SQLite
  6. Log all actions

### Next Execution
- **Scheduled**: 2025-11-15 00:00:00 UTC (~7h15min from now)
- **Expected Action**: Model will decide based on BNB price and features

---

## 6. Risk Management

### Built-in Safeguards
1. **Circuit Breakers**: Auto-pause on risk events
2. **Confidence Threshold**: Only trade if confidence > 30%
3. **Paper Trading Mode**: Zero real money at risk
4. **Transaction Fees**: 0.1% maker/taker (realistic simulation)
5. **Slippage**: 0.05-0.1% (realistic simulation)
6. **Max Position Size**: $5,000 (100% of capital, as tested)
7. **Leverage**: 1.0x (no leverage)

### Manual Intervention Triggers
- Drawdown > 15% → Review model performance
- 3+ consecutive losses → Pause and analyze
- Win rate < 40% after 10 trades → Re-evaluate strategy
- Any circuit breaker triggered 3+ times → Stop and retrain

---

## 7. Success Criteria (30-90 days)

| Metric              | Target      | Action if Failed                |
|---------------------|-------------|---------------------------------|
| Return              | > +15%      | Continue if > +10%              |
| Max Drawdown        | < 20%       | Review risk management          |
| Win Rate            | > 50%       | Analyze losing trades           |
| Sharpe Ratio        | > 1.0       | Acceptable if > 0.8             |
| Trade Frequency     | 5-20 trades | Investigate if < 3 or > 50      |
| Avg Trade Duration  | 5-30 days   | OK for daily timeframe          |

**Evaluation Date**: 2025-12-14 (30 days from deployment)

---

## 8. File Locations

### Code
- Main script: `scripts/run_paper_trading.py`
- Monitor: `scripts/monitor_paper_trading.py`
- Health check: `scripts/auto_health_check.py`
- Account status: `scripts/check_account_status.py`

### Data
- Database: `data/jarvis_trading.db`
- Logs: `logs/paper_trading_BNB_USDT_1d.log`
- Health reports: `logs/health_reports/health_*.json`
- PID file: `paper_trading.pid`

### Models
- Model: `/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/BNB_USDT_1d_ppo_model.zip`
- Normalizer: `/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/BNB_USDT_1d_vecnormalize.pkl`

### Configuration
- Trading config: `config/trading.yaml`
- Paper trading config: `config/paper_trading.yaml`
- Risk config: Embedded in `src/domain/monitoring/services.py`

---

## 9. Technical Details

### Feature Engineering (13 Core Features)
The model uses these features for prediction:
1. RSI (14 period)
2. MACD
3. MACD Signal
4. MACD Histogram
5. Bollinger Bands Upper
6. Bollinger Bands Middle
7. Bollinger Bands Lower
8. ATR (14 period)
9. Volume SMA (20 period)
10. Price Change %
11. Close/Open ratio
12. High/Low range
13. Volatility (rolling std)

### Model Architecture
- **Algorithm**: PPO (Proximal Policy Optimization)
- **Framework**: Stable-Baselines3
- **Reward Function**: Sharpe Ratio
- **Training Data**: 2020-2023 (BNB/USDT historical data)
- **Validation**: 2025 forward test (318 days)
- **Result**: +25% return (approved for deployment)

### Trading Logic
```python
# Pseudo-code
if model_action > 0.3 and no_position:
    BUY(100% of capital)
elif model_action < -0.3 and has_position:
    SELL(entire position)
else:
    HOLD(no action)
```

---

## 10. Troubleshooting

### Daemon Not Running
```bash
# Check if crashed
tail -50 logs/paper_trading_BNB_USDT_1d.log

# Check process
ps aux | grep run_paper_trading

# Restart
.venv/bin/python scripts/run_paper_trading.py --daemon &
```

### No Trades Executed
- **Expected**: Model has low trading frequency (1 trade in 318 days in backtest)
- **Action**: This is NORMAL for conservative RL strategy
- **Review**: If 0 trades after 60 days, investigate model predictions

### Circuit Breaker Triggered
```bash
# Check health report
.venv/bin/python scripts/monitor_paper_trading.py health

# Review triggered breaker
grep "Circuit breaker triggered" logs/paper_trading_BNB_USDT_1d.log

# Resume if resolved
.venv/bin/python scripts/monitor_paper_trading.py resume
```

### API Connection Issues
- **Check**: Binance API status (https://www.binance.com/en/my/settings/api-management)
- **Verify**: .env file has correct API keys
- **Test**: 
  ```bash
  .venv/bin/python -c "from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient; client = BinanceRESTClient(); print(client.fetch_ohlcv('BNBUSDT', '1d', limit=1))"
  ```

---

## 11. Next Steps

### Immediate (Week 1)
- [x] Deploy daemon (DONE)
- [x] Configure monitoring (DONE)
- [ ] Set up cron job for health checks
- [ ] Monitor first execution (2025-11-15 00:00 UTC)
- [ ] Verify first trade (if any)

### Short-term (Weeks 2-4)
- [ ] Daily monitoring of model predictions
- [ ] Track win rate and drawdown
- [ ] Compare with live BNB price movement
- [ ] Document model decision rationale

### Medium-term (1-3 months)
- [ ] 30-day performance review (2025-12-14)
- [ ] 90-day comprehensive evaluation
- [ ] Decide: Continue, adjust, or retrain model
- [ ] Consider testing other timeframes (4h, 12h)

### Long-term (3+ months)
- [ ] If successful (>+15%): Extend evaluation period
- [ ] If underperforming: Retrain with updated data
- [ ] Explore BTC/ETH models (after retraining)
- [ ] Consider live trading (ONLY if paper trading very successful)

---

## 12. Emergency Contacts & Resources

### Manual Override
**User** (jfoc) has full control to:
- Pause trading anytime
- Stop daemon immediately
- Review all decisions
- Modify parameters
- Retrain model

### Key Commands (Emergency)
```bash
# STOP EVERYTHING NOW
kill -15 73438
.venv/bin/python scripts/monitor_paper_trading.py stop

# CHECK STATUS
.venv/bin/python scripts/monitor_paper_trading.py health
sqlite3 data/jarvis_trading.db "SELECT * FROM balances WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66';"

# BACKUP DATA
cp data/jarvis_trading.db data/backups/jarvis_trading_$(date +%Y%m%d_%H%M%S).db
```

---

## 13. Autonomous Operation Notes

**JARVIS has autonomy to**:
- Monitor health automatically
- Pause trading if circuit breakers trigger
- Resume after recovery periods
- Log all actions
- Generate health reports

**JARVIS will alert user if**:
- Any circuit breaker triggered
- Drawdown > 15%
- Win rate < 40% (after 10 trades)
- 3+ consecutive losses
- Any critical system error

**User approval required for**:
- Live trading deployment
- Parameter changes
- Model retraining
- Capital increase
- Multi-asset deployment

---

## 14. Success Indicators (What to Watch)

### Green Flags (Continue)
- Steady positive returns
- Low drawdown (< 10%)
- Win rate > 50%
- Model predictions align with price movement
- No circuit breakers triggered frequently

### Yellow Flags (Review)
- Return 0-10% (below target but positive)
- Drawdown 10-15%
- Win rate 40-50%
- 1-2 circuit breaker triggers (investigate cause)

### Red Flags (Stop & Retrain)
- Negative returns after 30 days
- Drawdown > 20%
- Win rate < 40%
- 3+ circuit breaker triggers
- Model predictions consistently wrong

---

**Report Generated**: 2025-11-14 16:47:00 UTC
**Report By**: JARVIS (Autonomous Trading System)
**Version**: 1.0.0
**Status**: OPERATIONAL ✅
