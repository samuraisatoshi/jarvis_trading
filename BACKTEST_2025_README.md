# 2025 Backtesting & Analysis Framework

Complete framework for backtesting FinRL pre-trained models on 2025 historical data.

## Overview

This framework enables comprehensive analysis of how FinRL's 90+ pre-trained models would have performed on 2025 market data (January 1 - November 14, 2025).

**Key Features:**
- Downloads real 2025 market data from Binance
- Tests all available FinRL models (symbols & timeframes)
- Generates detailed performance metrics
- Identifies best-performing combinations
- Analyzes learnings and optimization opportunities

## Quick Start

### 1. Run Complete Pipeline

```bash
cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading
source .venv/bin/activate

# Full pipeline (download + backtest + analyze)
python scripts/run_2025_analysis.py

# Or specify symbols/timeframes
python scripts/run_2025_analysis.py --symbols BTC,ETH --timeframes 1d,4h

# Skip download if data already exists
python scripts/run_2025_analysis.py --skip-download
```

### 2. Individual Commands

#### Download Only
```bash
python scripts/download_2025_data.py --symbols BTC,ETH,BNB --timeframes 1h,4h,1d
```

#### Backtest Specific Combination
```bash
python scripts/backtest_2025.py --symbol BTC_USDT --timeframe 1d --initial-balance 5000
```

#### Backtest All Models
```bash
python scripts/backtest_2025.py --all-models --data-dir data/2025
```

## File Structure

### Input Data
```
data/2025/
├── BTC_USDT_1h_2025.csv        # Downloaded OHLCV data
├── BTC_USDT_4h_2025.csv
├── BTC_USDT_1d_2025.csv
├── ETH_USDT_1h_2025.csv
└── ...metadata.json
```

### Output Results
```
data/backtests/2025/
├── results.json                  # Aggregated backtest results
├── analysis.json                 # Performance analysis
├── BACKTEST_REPORT.txt          # Human-readable report
├── trades_BTC_USDT_1d.csv       # Individual trades
├── trades_ETH_USDT_4h.csv
└── metrics_BTC_USDT_1d.json     # Detailed metrics
```

## Scripts

### 1. download_2025_data.py

Downloads complete 2025 market data from Binance.

**Usage:**
```bash
python scripts/download_2025_data.py \
  --symbols BTC,ETH,BNB \
  --timeframes 1h,4h,1d \
  --output data/2025
```

**Options:**
- `--symbols`: CSV list of symbols (default: BTC,ETH,BNB)
- `--timeframes`: CSV list of timeframes (default: 1h,4h,1d)
- `--output`: Output directory (default: data/2025)
- `--dry-run`: Show what would be downloaded

**Output:**
- CSV files with OHLCV data
- metadata.json with download info

**Duration:** ~5-10 minutes for 3 symbols × 3 timeframes

### 2. backtest_2025.py

Runs comprehensive backtests with FinRL models.

**Usage (Single Combination):**
```bash
python scripts/backtest_2025.py \
  --symbol BTC_USDT \
  --timeframe 1d \
  --initial-balance 5000
```

**Usage (All Models):**
```bash
python scripts/backtest_2025.py \
  --all-models \
  --data-dir data/2025 \
  --models-dir ../finrl/trained_models \
  --output-dir data/backtests/2025
```

**Options:**
- `--symbol`: Single symbol (format: BTC_USDT)
- `--timeframe`: Single timeframe
- `--all-models`: Test all symbol/timeframe combinations
- `--data-dir`: Directory with downloaded data
- `--models-dir`: Directory with trained FinRL models
- `--output-dir`: Directory for results
- `--initial-balance`: Starting capital (default: 5000)
- `--min-confidence`: Confidence threshold (default: 0.0)

**Output:**
- results.json - Aggregated metrics
- trades_*.csv - Individual trades
- metrics_*.json - Detailed per-combination metrics
- BACKTEST_REPORT.txt - Summary report

**Duration:** ~10-30 minutes for all models (depends on data volume)

### 3. run_2025_analysis.py

Orchestrates complete pipeline.

**Usage:**
```bash
python scripts/run_2025_analysis.py
python scripts/run_2025_analysis.py --skip-download  # Use existing data
python scripts/run_2025_analysis.py --symbols BTC,ETH --timeframes 1d
```

**Options:**
- `--skip-download`: Skip data download stage
- `--skip-backtest`: Skip backtesting stage
- `--symbols`: Specific symbols to analyze
- `--timeframes`: Specific timeframes to analyze

**Process:**
1. **Download Phase** (~5-10 min): Fetch 2025 data from Binance
2. **Backtest Phase** (~10-30 min): Run models on historical data
3. **Analysis Phase** (~1 min): Generate insights and reports

## Output Analysis

### results.json Structure

```json
{
  "BTC_USDT_1d": {
    "symbol": "BTC_USDT",
    "timeframe": "1d",
    "initial_balance": 5000,
    "final_balance": 12345.67,
    "total_return_pct": 146.91,
    "total_return_usd": 7345.67,
    "sharpe_ratio": 4.52,
    "max_drawdown_pct": -18.5,
    "max_drawdown_usd": -925.00,
    "win_rate_pct": 58.3,
    "total_trades": 48,
    "winning_trades": 28,
    "losing_trades": 20,
    "average_win_pct": 3.2,
    "average_loss_pct": -1.8,
    "profit_factor": 2.14,
    "best_trade_pct": 12.5,
    "worst_trade_pct": -5.8,
    "avg_candles_per_trade": 150
  }
  // ... more combinations
}
```

### Analysis Structure

```json
{
  "generated_at": "2025-11-14T...",
  "total_combinations": 21,
  "symbols": {
    "BTC_USDT": {
      "combinations": 3,
      "avg_return": 125.3,
      "best_return": 146.9,
      "worst_return": 98.7
    }
  },
  "timeframe_ranking": [
    {
      "timeframe": "1d",
      "avg_return": 112.5,
      "best_return": 146.9,
      "combinations": 7
    }
  ],
  "top_performers": [
    {
      "combination": "BTC_USDT_1d",
      "return": 146.91,
      "sharpe": 4.52,
      "max_dd": -18.5,
      "win_rate": 58.3
    }
  ],
  "insights": [...]
}
```

### BACKTEST_REPORT.txt

Human-readable summary including:
- Top 10 performers by return
- Detailed results for each combination
- Risk metrics (drawdown, Sharpe ratio)
- Trade statistics (win rate, P&L)

## Understanding the Metrics

### Return Metrics
- **Total Return %**: Percentage gain/loss on initial balance
- **Total Return USD**: Absolute gain/loss in dollars
- **Final Balance**: Starting capital + P&L

### Risk Metrics
- **Sharpe Ratio**: Risk-adjusted return (higher = better). Typical range: 0-10
  - < 1.0: Poor
  - 1.0-2.0: Acceptable
  - 2.0-3.0: Good
  - > 3.0: Excellent

- **Max Drawdown %**: Worst peak-to-trough decline
  - < 10%: Excellent
  - 10-20%: Good
  - 20-30%: Acceptable
  - > 30%: Poor

### Trade Metrics
- **Win Rate %**: Percentage of trades that were profitable
- **Average Win/Loss**: Mean profit/loss per winning/losing trade
- **Profit Factor**: Total profit / Total loss (> 1.5 is good)
- **Best/Worst Trade**: Individual trade extremes

## Example Workflow

### Scenario: Test if 2024 models still work in 2025

```bash
# 1. Download all 2025 data
python scripts/download_2025_data.py --symbols BTC,ETH,BNB --timeframes 1h,4h,1d

# 2. Backtest all models
python scripts/backtest_2025.py --all-models

# 3. View results
cat data/backtests/2025/BACKTEST_REPORT.txt

# 4. Check best performers
python -c "import json; r=json.load(open('data/backtests/2025/results.json')); \
  top = sorted(r.items(), key=lambda x: x[1]['total_return_pct'], reverse=True); \
  print('\n'.join([f\"{k}: {v['total_return_pct']:.1f}%\" for k,v in top[:10]]))"
```

## Troubleshooting

### Issue: "Binance API rate limit"

Solution: Download data in smaller batches
```bash
# Download one symbol at a time
python scripts/download_2025_data.py --symbols BTC
python scripts/download_2025_data.py --symbols ETH
```

### Issue: "Models directory not found"

Ensure FinRL models are available:
```bash
ls /Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/
# Should show: *_ppo_model.zip and *_vecnormalize.pkl files
```

### Issue: "Not enough data" warning

Some symbol/timeframe combinations may have incomplete data. Check:
```bash
ls -lh data/2025/
# Look for very small files (< 1MB)
```

## Performance Expectations

Based on 2024 FinRL model training:

**Expected Returns (2025 Backtest):**
- Best models (BTC_USDT_1d): +100% to +200%
- Good models: +50% to +100%
- Average models: +10% to +50%
- Poor models: -10% to +10%

**Expected Sharpe Ratios:**
- Best models: 3.0 to 5.0+
- Good models: 1.5 to 3.0
- Average models: 0.5 to 1.5
- Poor models: < 0.5

**Expected Max Drawdown:**
- Best models: -15% to -25%
- Good models: -20% to -35%
- Average models: -30% to -50%

**Typical Execution Time:**
- Download (3 symbols × 3 TF): 5-10 minutes
- Backtest (21 combinations): 10-30 minutes
- Analysis: <1 minute

## Advanced Usage

### Filter by Minimum Confidence

Only trade signals with confidence > 0.7:
```bash
python scripts/backtest_2025.py --all-models --min-confidence 0.7
```

### Custom Initial Balance

Test with different capital amounts:
```bash
python scripts/backtest_2025.py --symbol BTC_USDT --timeframe 1d --initial-balance 10000
```

### Analyze Specific Symbols

Focus on specific coins:
```bash
python scripts/run_2025_analysis.py --symbols BTC,ETH --timeframes 1d,4h
```

## Learning from Results

### Questions to Answer

1. **Which timeframes performed best?**
   - Check `analysis.json` → `timeframe_ranking`
   - Should align with model training data

2. **Did 2024 models generalize to 2025?**
   - Overall profitability metrics
   - Sharpe ratio stability
   - Drawdown severity

3. **Which symbols are most predictable?**
   - Check `symbols` section in analysis
   - Compare Sharpe ratios and win rates

4. **What's the distribution of outcomes?**
   - How many combinations profitable? (profitable %)
   - Range of returns (best to worst)
   - Consistency within symbols

### Optimization Opportunities

After analyzing 2025 results, consider:

1. **Confidence Threshold Optimization**
   - Re-run with `--min-confidence 0.5, 0.6, 0.7, etc.`
   - Find threshold with best risk/reward

2. **Timeframe Ensemble**
   - Combine signals from multiple timeframes
   - Weight based on 2025 performance

3. **Symbol Selection**
   - Focus on top performers
   - Reduce drawdown by avoiding poor performers

4. **Risk Management**
   - Adjust position sizing based on volatility
   - Implement stop-losses at 2× max drawdown

## Output Files Reference

| File | Format | Purpose |
|------|--------|---------|
| results.json | JSON | Complete metrics for all combinations |
| analysis.json | JSON | Aggregated analysis and insights |
| BACKTEST_REPORT.txt | Text | Human-readable summary |
| trades_*.csv | CSV | Individual trade records |
| metadata.json | JSON | Download metadata |

## Architecture

```
┌─────────────────────────────────────────────┐
│ run_2025_analysis.py (Orchestrator)        │
└─────────────────────────────────────────────┘
          │
          ├──► download_2025_data.py ──► data/2025/
          │         │
          │         ▼
          │    BinanceRESTClient (Binance API)
          │
          ├──► backtest_2025.py ──► data/backtests/2025/
          │         │
          │         ├──► ModelLoader (Load FinRL models)
          │         ├──► FeatureCalculator (13 features)
          │         └──► RLPredictionService (Generate signals)
          │
          └──► Analysis Engine ──► insights & rankings
```

## Dependencies

- pandas: Data manipulation
- numpy: Numerical operations
- stable-baselines3: FinRL model training framework
- binance-connector: Binance API client

## Next Steps

After running 2025 backtest:

1. **Review results** in BACKTEST_REPORT.txt
2. **Identify patterns** in top performers
3. **Compare with 2024 backtests** if available
4. **Consider optimizations** for live trading
5. **Monitor 2025 actual performance** vs predicted

## Contact & Support

For issues or questions:
1. Check FINRL_INTEGRATION.md for model integration details
2. Review test output for error details
3. Ensure FinRL models are accessible and valid

---

**Last Updated**: November 14, 2025
**Status**: Production Ready
**Version**: 1.0
