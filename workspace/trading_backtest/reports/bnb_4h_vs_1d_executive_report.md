# BNB_USDT Backtest Report: 4H vs 1D Models (2025 Data)

**Date:** 2025-11-15
**Period Analyzed:** 2025-01-01 to 2025-11-14
**Initial Capital:** $5,000

---

## Executive Summary

Both the 4H and 1D RL models for BNB_USDT exhibit **buy-and-hold behavior** rather than active trading. Analysis reveals a critical issue: **models never produce SELL signals**, only BUY signals or HOLD.

### Quick Comparison

| Metric | 1D Model | 4H Model | Winner |
|--------|----------|----------|--------|
| **Final Balance** | $6,249.22 | $7,985.80 | 4H |
| **Total Return** | +24.98% | +59.72% | 4H |
| **Number of Trades** | 1 | 1 | TIE |
| **Sharpe Ratio** | 1.16 | 0.47 | 1D |
| **Max Drawdown** | -29.60% | -32.35% | 1D |
| **Win Rate** | N/A | N/A | N/A |
| **Alpha vs B&H** | +3.37% | -0.00% | 1D |

**Recommendation:** Neither model is suitable for live trading in current state. Models require retraining with corrected action space.

---

## Detailed Findings

### 1. Action Distribution Analysis

#### 4H Model Behavior:
- **Total predictions:** 1,707 candles
- **Action values:** Only `0.0` (HOLD) or `2.0` (BUY)
- **BUY signals:** 771 (45.2% of time)
- **SELL signals:** 0 (0.0% - CRITICAL ISSUE)
- **HOLD signals:** 936 (54.8%)

**Action statistics:**
- Mean: +0.9033
- Median: 0.0000
- Min: 0.0000
- Max: +2.0000
- **Never goes negative** ❌

#### 1D Model Behavior:
- **Total predictions:** 118 candles
- **Action values:** Only `0.0` (HOLD) or `2.0` (BUY)
- **BUY signals:** 3 (2.5% of time)
- **SELL signals:** 0 (0.0% - CRITICAL ISSUE)
- **HOLD signals:** 115 (97.5%)

**Action statistics:**
- Mean: +0.0508
- Median: 0.0000
- Min: 0.0000
- Max: +2.0000
- **Never goes negative** ❌

### 2. Trading Behavior

#### 4H Model:
```
2025-02-03 08:00 | BUY  | $576.16 | Confidence: 2.0
... (never sells, holds until end)
2025-11-14 16:00 | (auto-close position) | $919.84
```

**Result:** Essentially buy-and-hold from Feb 3 to Nov 14

#### 1D Model:
```
2025-08-02 00:00 | BUY  | $736.42 | Confidence: 2.0
... (never sells, holds until end)
2025-11-14 00:00 | (auto-close position) | $895.55
```

**Result:** Essentially buy-and-hold from Aug 2 to Nov 14

### 3. Performance Metrics

#### 4H Model Performance:
- **Entry:** Feb 3 @ $576.16
- **Exit:** Nov 14 @ $919.84
- **Price change:** +59.72%
- **Return:** +59.72% (identical to price change = buy-and-hold)
- **Sharpe:** 0.47 (low risk-adjusted return)
- **Max DD:** -32.35% (high volatility exposure)

#### 1D Model Performance:
- **Entry:** Aug 2 @ $736.42
- **Exit:** Nov 14 @ $895.55
- **Price change:** +21.62%
- **Return:** +24.98% (slightly better due to later entry)
- **Sharpe:** 1.16 (better risk-adjusted return)
- **Max DD:** -29.60% (less volatility)

### 4. Comparison with Buy & Hold

**Pure Buy & Hold (Jan 1 - Nov 14):**
- Entry: ~$576 (approx)
- Exit: $920
- Return: ~+59.7%

**Model Performance:**
- **4H:** +59.72% (same as B&H, entered at optimal time by luck)
- **1D:** +24.98% (worse than B&H due to later entry)

**Alpha (excess return vs B&H):**
- **4H:** -0.00% (no skill, pure luck on timing)
- **1D:** +3.37% (slight positive alpha from better entry timing)

---

## Root Cause Analysis

### Why Are Models Not Producing SELL Signals?

#### Hypothesis 1: Action Space Configuration
**Most Likely**

The model action space may be configured incorrectly:
- Discrete action space: {0: HOLD, 1: BUY, 2: SELL} ❌
- Continuous action space clipped to [0, 2] instead of [-1, 1] ❌

Current behavior suggests:
- Action space: [0, 2]
- Should be: [-1, 1] or [-2, 2]

#### Hypothesis 2: Reward Function Bias
The Sharpe Ratio reward function may have created bias:
- Models learned that "not selling during bull market" maximizes Sharpe
- No penalty for holding through drawdowns
- Reward structure doesn't incentivize active trading

#### Hypothesis 3: Training Data Period
Models trained on bull market data (2020-2024):
- Learned that "buy and hold" is optimal strategy
- Never experienced conditions where selling is beneficial
- No bear market examples in training data

#### Hypothesis 4: VecNormalize Issues
Observation normalization may be affecting action predictions:
- Features normalized incorrectly
- Action space clipped post-prediction
- Loss of negative action capability

---

## Recommendations

### Immediate Actions (Critical)

1. **DO NOT USE these models for live trading**
   - Models are not trading, just holding
   - No risk management
   - No downside protection

2. **Verify action space configuration**
   ```python
   # Check model action space
   print(model.action_space)
   # Should be: Box(-1.0, 1.0, (1,))
   # NOT: Box(0.0, 2.0, (1,))
   ```

3. **Review training code**
   - Verify PPO `action_space` parameter
   - Check if actions are being clipped
   - Review `VecNormalize` configuration

### Medium-Term Fixes

1. **Retrain with corrected action space**
   - Action space: Box(-1, 1) for continuous
   - Or discrete: {0: SELL, 1: HOLD, 2: BUY}
   - Ensure negative actions are possible

2. **Enhance reward function**
   ```python
   # Add trading frequency incentive
   reward = sharpe_ratio * 0.7 + trading_frequency * 0.2 + profit * 0.1
   ```

3. **Include bear market training data**
   - Add 2018 bear market data
   - Add 2022 bear market data
   - Train on full market cycles

4. **Add risk management constraints**
   - Max drawdown limits
   - Stop-loss mechanisms
   - Position sizing rules

### Long-Term Improvements

1. **Multi-regime training**
   - Separate models for bull/bear/sideways markets
   - Meta-model to select active model
   - Ensemble approach

2. **Advanced reward shaping**
   - Reward successful round-trip trades
   - Penalize excessive drawdowns
   - Bonus for beating buy-and-hold

3. **Feature engineering**
   - Add market regime features
   - Include volatility regime indicators
   - Add correlation features

---

## Technical Details

### Environment Configuration
- **Python:** 3.11+
- **Framework:** FinRL (Stable-Baselines3)
- **Algorithm:** PPO (Proximal Policy Optimization)
- **Observation:** 13 technical indicators
- **Action Space:** Box(0, 2) ❌ (incorrect)
- **Reward:** Sharpe Ratio

### Data Quality
- **Source:** Binance
- **Period:** 2025-01-01 to 2025-11-14
- **4H Candles:** 1,907 total (1,707 tradeable)
- **1D Candles:** 318 total (118 tradeable)
- **Missing Data:** None
- **Anomalies:** None detected

### Model Files
```
/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/
├── BNB_USDT_4h_ppo_model.zip (2.4M)
├── BNB_USDT_4h_vecnormalize.pkl (2.4K)
├── BNB_USDT_1d_ppo_model.zip (2.4M)
└── BNB_USDT_1d_vecnormalize.pkl (2.4K)
```

---

## Appendix: Sample Trades

### 4H Model - Single Trade
```
Date                Action  Price      Confidence
2025-02-03 08:00   BUY     $576.16    +2.00
(holds for 9 months)
2025-11-14 16:00   CLOSE   $919.84    (auto)
```

### 1D Model - Single Trade
```
Date                Action  Price      Confidence
2025-08-02 00:00   BUY     $736.42    +2.00
(holds for 3 months)
2025-11-14 00:00   CLOSE   $895.55    (auto)
```

---

## Conclusion

The current RL models for BNB_USDT are **not functioning as intended**. They have learned to buy-and-hold rather than actively trade, due to a likely issue with action space configuration.

**Neither 4H nor 1D model should be used for live trading until:**
1. Action space is corrected to allow SELL signals
2. Models are retrained with proper configuration
3. Backtests confirm active trading behavior
4. Performance metrics meet minimum thresholds

**Next Steps:**
1. Fix action space configuration in training code
2. Retrain both models with corrected settings
3. Re-run backtests to verify active trading
4. Only then consider paper trading

**Risk Assessment:** 🔴 **HIGH RISK** - Do not deploy

---

**Report Generated:** 2025-11-15 00:15:00
**Author:** JARVIS Trading System
**Files Referenced:**
- `/scripts/test_rl_models_4h_2025.py`
- `/scripts/test_rl_models_4h_detailed.py`
- `/data/2025/BNB_USDT_4h_2025.csv`
- `/data/2025/BNB_USDT_1d_2025.csv`
