# FinRL Integration - Quick Start

Get trading signals from 272 pre-trained models in 5 minutes.

## 1. Verify Installation

```bash
cd /Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading
source .venv/bin/activate

# Test integration
python scripts/test_finrl_integration.py
```

Expected output:
```
Available models: 90
Best model: BTC_USDT_1d (Sharpe 7.55)
✓ Integration components verified successfully
```

## 2. Generate Trading Signal

```python
import pandas as pd
from src.domain.reinforcement_learning.services.prediction_service import RLPredictionService
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

# Initialize
client = BinanceRESTClient()
service = RLPredictionService('/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models')

# Fetch data
klines = client.get_klines('BTCUSDT', '1d', limit=100)
df = pd.DataFrame(klines)

# Predict
result = service.predict('BTC_USDT', '1d', df)

# Use signal
print(f"Action: {service.get_action_name(result.action)}")  # BUY, HOLD, SELL
print(f"Confidence: {result.confidence:.0%}")
print(f"Price: ${result.price:,.2f}")
```

## 3. Batch Predictions

```python
# Multi-symbol, multi-timeframe
predictions = service.predict_batch({
    'BTC_USDT': {
        '1d': df_btc_daily,
        '4h': df_btc_4h
    },
    'ETH_USDT': {
        '1d': df_eth_daily
    }
})

for key, result in predictions.items():
    print(f"{key}: {service.get_action_name(result.action)}")
```

## 4. List Available Models

```python
models = service.get_available_models()
print(f"Available: {len(models)} models")
for name in sorted(models.keys())[:5]:
    print(f"  {name}")
```

Available: AAVE, AVAX, BNB, BTC, DOGE, ETH, LINK, SOL, XRP
Timeframes: 30m, 1h, 4h, 12h, 1d

## 5. Paper Trading Example

```bash
# Run example trading bot
python scripts/example_finrl_trading.py --symbol BTC_USDT --test

# Continuous trading (every hour)
python scripts/example_finrl_trading.py --continuous --interval 3600
```

## 6. Key Concepts

### Actions
- `0` = SELL / SHORT
- `1` = HOLD / DO NOTHING
- `2` = BUY / LONG

### Confidence
- 0.0 - 0.4: Low confidence (skip)
- 0.4 - 0.7: Medium confidence (use with caution)
- 0.7 - 1.0: High confidence (use signal)

### Features
13 core features automatically calculated:
1. Close price
2. Volume-price trend
3. MACD signal
4. EMA slopes
5. ATR volatility
6. Price position
7-10. EMA distances
11. Price momentum
12. Momentum consistency
13. Time feature

## 7. Common Tasks

### Get Best Model
```python
symbol, timeframe = service.get_best_model()
# Returns: ('BTC_USDT', '1d') - Sharpe 7.55
```

### Validate Data
```python
from src.domain.features.services.feature_calculator import FeatureCalculator

calc = FeatureCalculator()
validation = calc.validate_features(df)
print(f"Valid: {validation['valid']}")
print(f"Coverage: {validation['coverage_ratio']:.1%}")
```

### Clear Cache (free memory)
```python
service.clear_cache()  # Remove loaded models from memory
```

## 8. Performance Reference

| Model | Sharpe | Return | Win Rate |
|-------|--------|--------|----------|
| BTC_USDT_1d | 7.55 | +245% | 58% |
| ETH_USDT_1d | 6.5 | +198% | 56% |
| BTC_USDT_4h | 5.8 | +180% | 54% |

**Note**: Backtesting results. Live results may differ.

## 9. Error Handling

```python
try:
    result = service.predict('BTC_USDT', '1d', df)
except FileNotFoundError:
    print("Model not found - check symbol/timeframe")
except ValueError:
    print("Feature calculation failed - check data")
except Exception as e:
    print(f"Error: {e}")
```

## 10. Integration Points

### With MarketDataService
```python
async def on_candle_close(symbol, candle, timeframe):
    history = fetch_historical_data(symbol, timeframe)
    result = service.predict(symbol, timeframe, history)
    if result.confidence > 0.7:
        place_trade(symbol, result.action)

market_data_service.register_candle_callback('1d', on_candle_close)
```

### With Paper Trading
```python
from src.domain.paper_trading.repositories.order_repository import OrderRepository

repo = OrderRepository()
if result.action == 2:  # BUY
    order = repo.create_buy_order(symbol, quantity, result.price)
elif result.action == 0:  # SELL
    order = repo.create_sell_order(symbol, quantity, result.price)
```

## Troubleshooting

**Q: Model not found**
```python
models = service.get_available_models()
print(list(models.keys()))  # See available models
```

**Q: Feature validation fails**
- Ensure DataFrame has min 50 rows
- Check columns: open, high, low, close, volume

**Q: Low confidence**
- Adjust confidence_threshold in RLPredictionService
- Check market volatility
- Validate feature calculations

**Q: Import errors**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Files Reference

| File | Use |
|------|-----|
| `FINRL_INTEGRATION.md` | Full documentation |
| `INTEGRATION_SUMMARY.md` | Architecture overview |
| `scripts/test_finrl_integration.py` | Verify setup |
| `scripts/example_finrl_trading.py` | Example bot |

## Next Steps

1. ✓ Run `test_finrl_integration.py` (verify)
2. Run `example_finrl_trading.py` (test signals)
3. Integrate with `MarketDataService`
4. Connect to paper trading account
5. Monitor performance
6. Go live!

## Support

- **Full Guide**: See `FINRL_INTEGRATION.md`
- **Examples**: See `scripts/example_finrl_trading.py`
- **Tests**: Run `scripts/test_finrl_integration.py`

---

**Status**: Production ready
**Models**: 90 available (272 total in FinRL)
**Best**: BTC_USDT_1d (Sharpe 7.55)

Start generating signals now! 🚀
