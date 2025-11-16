# 2025 Backtest Execution Guide

## Overview

This guide provides step-by-step instructions to execute the complete 2025 backtesting pipeline with FinRL pre-trained models.

**What You Have:**
- 3 production-ready Python scripts
- Comprehensive documentation
- Complete FinRL integration (90+ pre-trained models)
- Real Binance API support

**What You Can Do:**
1. Download complete 2025 market data (Jan 1 - Nov 14)
2. Backtest all FinRL models on historical data
3. Generate detailed performance reports
4. Identify best-performing combinations
5. Analyze learnings and optimization opportunities

## Quick Start (3 Steps)

### Step 1: Download 2025 Data

```bash
cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading
source .venv/bin/activate

# Download BTC daily data (fastest to test)
python scripts/download_2025_data.py --symbols BTC --timeframes 1d

# Download all symbols and timeframes (recommended)
python scripts/download_2025_data.py --symbols BTC,ETH,BNB,XRP,ADA,DOGE,AVAX --timeframes 1h,4h,1d

# Dry-run (shows what would be downloaded)
python scripts/download_2025_data.py --dry-run
```

**Expected Output:**
- `data/2025/BTC_USDT_1d_2025.csv` - 318 candles (27KB)
- `data/2025/ETH_USDT_1h_2025.csv` - ~2,856 candles per pair
- `data/2025/metadata.json` - Download metadata

### Step 2: Run Backtests

```bash
# Backtest specific combination (fastest)
python scripts/backtest_2025.py \
  --symbol BTC_USDT \
  --timeframe 1d \
  --initial-balance 5000

# Backtest all downloaded combinations
python scripts/backtest_2025.py \
  --all-models \
  --data-dir data/2025 \
  --models-dir ../finrl/trained_models \
  --output-dir data/backtests/2025

# With confidence threshold
python scripts/backtest_2025.py \
  --all-models \
  --min-confidence 0.5 \
  --output-dir data/backtests/2025
```

**Expected Output:**
- `data/backtests/2025/results.json` - Aggregated metrics
- `data/backtests/2025/BACKTEST_REPORT.txt` - Human-readable report
- `data/backtests/2025/analysis.json` - Performance insights
- `data/backtests/2025/trades_*.csv` - Individual trades

### Step 3: Analyze Results

```bash
# View human-readable report
cat data/backtests/2025/BACKTEST_REPORT.txt

# View raw results
python -c "import json; r=json.load(open('data/backtests/2025/results.json')); \
  top = sorted(r.items(), key=lambda x: x[1]['total_return_pct'], reverse=True); \
  print('\\n'.join([f\"{k}: Return {v['total_return_pct']:.1f}% | Sharpe {v['sharpe_ratio']:.2f} | Max DD {v['max_drawdown_pct']:.1f}%\" for k,v in top[:10]]))"

# View analysis insights
cat data/backtests/2025/analysis.json | python -m json.tool
```

## Complete Pipeline (One Command)

Run everything in sequence:

```bash
python scripts/run_2025_analysis.py
```

This executes:
1. **Download Phase** (~10 minutes): Fetches all 2025 data
2. **Backtest Phase** (~30 minutes): Tests all models
3. **Analysis Phase** (~1 minute): Generates insights

**Options:**
```bash
# Skip download if data already exists
python scripts/run_2025_analysis.py --skip-download

# Skip backtest (just analyze existing results)
python scripts/run_2025_analysis.py --skip-backtest

# Focus on specific symbols/timeframes
python scripts/run_2025_analysis.py --symbols BTC,ETH --timeframes 1d,4h
```

## File Locations

All scripts are in:
```
/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/scripts/
├── download_2025_data.py      (297 lines) - Download historical data
├── backtest_2025.py           (445 lines) - Backtest engine
└── run_2025_analysis.py       (345 lines) - Orchestration pipeline
```

Documentation:
```
/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/
├── BACKTEST_2025_README.md         - Complete reference
├── EXECUTION_GUIDE_2025_BACKTEST.md (this file)
├── FINRL_INTEGRATION.md            - FinRL integration details
└── FINRL_STATUS.md                 - Current system status
```

## Data & Results

**Input:**
```
data/2025/
├── BTC_USDT_1h_2025.csv
├── BTC_USDT_4h_2025.csv
├── BTC_USDT_1d_2025.csv
├── ETH_USDT_*.csv
└── ...metadata.json
```

**Output:**
```
data/backtests/2025/
├── results.json                    - All metrics JSON
├── analysis.json                   - Insights JSON
├── BACKTEST_REPORT.txt            - Text report
├── trades_BTC_USDT_1d.csv         - Trade records
├── trades_ETH_USDT_4h.csv
└── ...metrics_*.json
```

## Understanding the Output

### results.json Example
```json
{
  "BTC_USDT_1d": {
    "symbol": "BTC_USDT",
    "timeframe": "1d",
    "total_return_pct": 146.91,
    "sharpe_ratio": 4.52,
    "max_drawdown_pct": -18.5,
    "win_rate_pct": 58.3,
    "total_trades": 48,
    ...
  }
}
```

### BACKTEST_REPORT.txt Example
```
TOP 10 PERFORMERS BY RETURN
---
1. BTC_USDT_1d    Return: +146.9% | Sharpe: 4.52 | DD: -18.5% | Trades: 48
2. ETH_USDT_1d    Return: +98.5%  | Sharpe: 3.21 | DD: -22.1% | Trades: 52
...
```

### Metrics Interpretation

**Return Metrics:**
- Total Return %: Gain/loss as percentage of initial $5,000
  - +100% = Turned $5,000 into $10,000
  - +50% = Turned $5,000 into $7,500

**Risk Metrics:**
- Sharpe Ratio: Risk-adjusted return
  - > 1.0: Acceptable
  - > 2.0: Good
  - > 3.0: Excellent
  - > 5.0: Outstanding

- Max Drawdown: Worst peak-to-trough decline
  - -10%: Excellent
  - -20%: Good
  - -30%: Acceptable
  - -50%+: Poor

**Trade Metrics:**
- Win Rate: % of trades that were profitable
  - > 60%: Excellent
  - > 50%: Good
  - < 40%: Poor

- Profit Factor: Total profit / Total loss
  - > 2.0: Excellent
  - > 1.5: Good
  - < 1.0: Losing

## Troubleshooting

### Issue: "No data received"

**Cause:** API rate limit or connectivity issue

**Solution:**
```bash
# Try with smaller batch
python scripts/download_2025_data.py --symbols BTC --timeframes 1d

# Check Binance connectivity
curl https://api.binance.com/api/v3/time
```

### Issue: Models not found

**Cause:** FinRL models path incorrect

**Solution:**
```bash
# Verify models exist
ls /Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/ | head

# Should show: BTC_USDT_1d_ppo_model.zip, BTC_USDT_1d_vecnormalize.pkl, etc.
```

### Issue: Backtest takes too long

**Cause:** Testing too many combinations

**Solution:**
```bash
# Test one symbol first
python scripts/backtest_2025.py --symbol BTC_USDT --timeframe 1d

# Then expand
python scripts/backtest_2025.py --all-models
```

## Performance Expectations

**Timing:**
- Download (3 symbols × 3 TF): 5-10 seconds per symbol
- Backtest (1 combination): 30-60 seconds
- Full pipeline (21 combinations): 10-30 minutes

**Results (Based on 2024 Training):**
- Best models: +100% to +200% return
- Good models: +50% to +100%
- Average models: +10% to +50%
- Poor models: -50% to +10%

**Sharpe Ratios:**
- Best models: 3.0 to 5.0+
- Good models: 1.5 to 3.0
- Average: 0.5 to 1.5

## Next Steps After Backtesting

### 1. Analyze Results

```bash
# View top performers
python -c "
import json
r = json.load(open('data/backtests/2025/results.json'))
top = sorted(r.items(), key=lambda x: x[1]['total_return_pct'], reverse=True)
for i, (k, v) in enumerate(top[:5], 1):
    print(f'{i}. {k}: {v[\"total_return_pct\"]:.1f}% (Sharpe {v[\"sharpe_ratio\"]:.2f})')
"
```

### 2. Review Trades

```bash
# View individual trades for top performer
head -20 data/backtests/2025/trades_BTC_USDT_1d.csv
```

### 3. Compare Performance

```bash
# If you have 2024 backtests
diff <(cat 2024_results.json | python -m json.tool) \
     <(cat data/backtests/2025/results.json | python -m json.tool)
```

### 4. Identify Patterns

Ask yourself:
- Which timeframes performed best? (1h/4h/1d)
- Which symbols were most profitable?
- Did models generalize from 2024 to 2025?
- What confidence level works best?

### 5. Optimize for Live Trading

Based on 2025 results:
1. Confidence threshold tuning
2. Multi-timeframe ensemble
3. Symbol selection
4. Risk management adjustments
5. Position sizing optimization

## Advanced Usage

### Test Different Confidence Thresholds

```bash
for confidence in 0.0 0.3 0.5 0.7 0.9; do
  echo "Testing confidence: $confidence"
  python scripts/backtest_2025.py \
    --all-models \
    --min-confidence $confidence \
    --output-dir "data/backtests/2025_conf_$confidence"
done
```

### Test Different Initial Balances

```bash
for balance in 1000 5000 10000 50000; do
  python scripts/backtest_2025.py \
    --symbol BTC_USDT \
    --timeframe 1d \
    --initial-balance $balance
done
```

### Export Results to CSV

```bash
python -c "
import json
import pandas as pd
r = json.load(open('data/backtests/2025/results.json'))
df = pd.DataFrame(r).T
df.to_csv('data/backtests/2025/results.csv')
print('Exported to results.csv')
print(df[['symbol','timeframe','total_return_pct','sharpe_ratio','win_rate_pct']])
"
```

## Script Architecture

```
run_2025_analysis.py (Orchestrator)
  │
  ├── Stage 1: download_2025_data.py
  │     └── BinanceRESTClient (Binance API)
  │
  ├── Stage 2: backtest_2025.py
  │     ├── ModelLoader (Load FinRL models)
  │     ├── FeatureCalculator (Calculate 13 features)
  │     └── RLPredictionService (Generate signals)
  │
  └── Stage 3: Analysis Engine
        ├── results.json (Aggregated metrics)
        ├── analysis.json (Insights)
        └── BACKTEST_REPORT.txt (Human summary)
```

## Key Scripts Summary

### 1. download_2025_data.py
- **Purpose:** Download historical OHLCV data from Binance
- **Input:** Symbols, timeframes, date range
- **Output:** CSV files with market data
- **Time:** <1 second per symbol

### 2. backtest_2025.py
- **Purpose:** Backtest FinRL models on historical data
- **Input:** OHLCV data, trained models
- **Output:** Performance metrics, trade records
- **Time:** 30-60 seconds per combination

### 3. run_2025_analysis.py
- **Purpose:** Orchestrate complete pipeline
- **Input:** User preferences (symbols, timeframes)
- **Output:** Analysis report and metrics
- **Time:** 10-30 minutes for full pipeline

## Success Criteria

You know it's working when:
- [ ] Data downloads without errors
- [ ] Backtests show both profitable and unprofitable combinations
- [ ] Sharpe ratios are in expected range (0.5-5.0+)
- [ ] Win rates are between 40-70%
- [ ] Reports generate correctly
- [ ] Analysis shows clear patterns

## Common Patterns to Look For

**Good Sign:** Sharpe > 2.0
- Model is risk-adjusted profitable

**Red Flag:** Sharpe < 0.5
- Model may be overfitted or ineffective

**Good Sign:** Win rate > 55%
- More winning trades than losing

**Red Flag:** Max drawdown > 50%
- Too risky, needs position sizing adjustment

**Good Sign:** Profit factor > 1.5
- Each losing trade is offset by bigger wins

## Report Locations

After running the pipeline:

1. **Human-readable summary:**
   ```
   cat data/backtests/2025/BACKTEST_REPORT.txt
   ```

2. **Machine-readable results:**
   ```
   cat data/backtests/2025/results.json | python -m json.tool
   ```

3. **Analysis insights:**
   ```
   cat data/backtests/2025/analysis.json | python -m json.tool
   ```

4. **Individual trades:**
   ```
   head -20 data/backtests/2025/trades_BTC_USDT_1d.csv
   ```

## Contact & Support

For questions or issues:
1. Review BACKTEST_2025_README.md for detailed reference
2. Check FINRL_INTEGRATION.md for model details
3. Review test output for specific error messages

## Summary

You now have:

✓ **3 production scripts** (1,087 lines total)
✓ **Complete documentation** (2,000+ lines)
✓ **Real Binance integration** (live data download)
✓ **90+ pre-trained models** (ready to backtest)
✓ **Comprehensive metrics** (13+ performance indicators)

Ready to:
1. Download 2025 data
2. Backtest all FinRL models
3. Generate performance reports
4. Identify optimization opportunities
5. Prepare for live trading

---

**Status:** Production Ready
**Last Updated:** November 14, 2025
**Next Step:** Run `python scripts/run_2025_analysis.py`
