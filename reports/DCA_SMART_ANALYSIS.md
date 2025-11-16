# DCA Smart Strategy - Analysis Report

## Executive Summary

**Period:** 2024-05-18 to 2025-11-15
**Days Simulated:** 547

### Performance

| Metric | Value |
|--------|-------|
| Initial Capital | $5,000.00 |
| Total Invested | $14,621.71 |
| Final Portfolio Value | $10,673.34 |
| Total Return | -27.00% ($-3,948.37) |

### Strategy Comparison

| Strategy | Return | Alpha vs B&H |
|----------|--------|--------------|
| **DCA Smart** | **-27.00%** | **-88.85%** |
| Buy & Hold | 61.85% | -- |
| B&H + DCA | 87.41% | +25.56% |
| DCA Fixed | 8.10% | -53.75% |

### Trading Statistics

- **Total Trades:** 78
- **Buy Trades:** 56
- **Dip Buys (2x+ multiplier):** 12
- **Profit Taking Sells:** 22
- **Total Profit Taken:** $10,589.91

### Final Holdings

- **BNB:** 10.333303 ($9,705.14)
- **USDT:** $968.20
- **Reserved (Profits):** $5,193.20
- **Average Cost:** $1415.01
- **Final Price:** $939.21

## Verdict

❌ **Buy & Hold wins**

**Alpha:** -88.85%

## Strategy Rules

### 1. Weekly DCA with RSI Adjustments

Base investment: $200/week (every Monday)

**Multipliers:**
- RSI < 30: 3x ($600) - Extreme oversold
- RSI < 40: 2x ($400) - Oversold
- RSI < 50: 1.5x ($300) - Neutral-low
- RSI < 60: 1x ($200) - Neutral
- RSI < 70: 0.5x ($100) - Neutral-high
- RSI ≥ 70: 0.25x ($50) - Overbought

**Distance from SMA200:**
- 20% below: +50% multiplier
- 30% above: -50% multiplier

### 2. Profit Taking at ATH

When price ≥ 98% of ATH:

- Profit > 100%: Sell 25%
- Profit > 75%: Sell 20%
- Profit > 50%: Sell 15%
- Profit > 30%: Sell 10%

Reserve proceeds for rebuying dips.

### 3. Crash Rebuying

Use 50% of reserved profits when:
- RSI < 25 (panic), OR
- Price -30% from ATH (crash)

## Visualization

![DCA Smart Analysis](../data/backtests/dca_smart_analysis.png)

## Conclusion

While DCA Smart underperformed Buy & Hold in this period, it provided better risk management through profit-taking and maintained cash reserves. Performance may vary significantly based on market conditions.

**Generated:** 2025-11-15 14:45:35
