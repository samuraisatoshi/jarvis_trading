# Official Candle Close Times (UTC)

**Important**: All candle close times are in UTC (Coordinated Universal Time), also known as GMT+0.

## Candle Close Schedule

### 1-Minute Candles (1m)
- **Close Time**: Every minute at :00 seconds
- **Examples**:
  - 14:00:00 UTC
  - 14:01:00 UTC
  - 14:02:00 UTC
  - 23:59:00 UTC

### 5-Minute Candles (5m)
- **Close Time**: At :00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55 (every 5 minutes)
- **Examples**:
  - 14:00:00 UTC
  - 14:05:00 UTC
  - 14:10:00 UTC
  - 14:15:00 UTC
  - 23:55:00 UTC

### 15-Minute Candles (15m)
- **Close Time**: At :00, :15, :30, :45
- **Examples**:
  - 14:00:00 UTC
  - 14:15:00 UTC
  - 14:30:00 UTC
  - 14:45:00 UTC
  - 23:45:00 UTC

### 30-Minute Candles (30m)
- **Close Time**: At :00 and :30
- **Examples**:
  - 14:00:00 UTC
  - 14:30:00 UTC
  - 15:00:00 UTC
  - 23:30:00 UTC

### 1-Hour Candles (1h)
- **Close Time**: At minute :00 of each hour
- **Examples**:
  - 14:00:00 UTC
  - 15:00:00 UTC
  - 16:00:00 UTC
  - 23:00:00 UTC
  - 00:00:00 UTC (midnight)

### 4-Hour Candles (4h)
- **Close Time**: At 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
- **Examples**:
  - 00:00:00 UTC
  - 04:00:00 UTC
  - 08:00:00 UTC
  - 12:00:00 UTC
  - 16:00:00 UTC
  - 20:00:00 UTC

### Daily Candles (1d)
- **Close Time**: At 00:00:00 UTC (midnight)
- **Examples**:
  - 2024-11-14 00:00:00 UTC
  - 2024-11-15 00:00:00 UTC
  - 2024-11-16 00:00:00 UTC

### Weekly Candles (1w)
- **Close Time**: Monday at 00:00:00 UTC
- **Examples**:
  - 2024-11-11 00:00:00 UTC (Monday)
  - 2024-11-18 00:00:00 UTC (Monday)
  - 2024-11-25 00:00:00 UTC (Monday)

## Important Notes

### UTC Time Zone
- All times shown above are in **UTC** (GMT+0)
- Convert to your local timezone as needed
- Binance API uses UTC for all timestamps

### Microseconds
- Candles close at exactly :00 seconds (microseconds = 0)
- The job scheduler ensures execution happens at :00.000000 seconds

### Next Candle Calculation
The `CandleScheduler.get_next_candle_time()` function calculates the exact time of the next candle close:

```python
from src.domain.market_data.services.candle_scheduler import CandleScheduler
from datetime import datetime

scheduler = CandleScheduler()

# Get next close times
next_1h = scheduler.get_next_candle_time("1h")
next_4h = scheduler.get_next_candle_time("4h")
next_1d = scheduler.get_next_candle_time("1d")

print(f"1h closes at: {next_1h.isoformat()} UTC")
print(f"4h closes at: {next_4h.isoformat()} UTC")
print(f"1d closes at: {next_1d.isoformat()} UTC")
```

### Wait Time Calculation
Get seconds to wait until next candle close:

```python
wait_seconds = scheduler.get_wait_seconds("1h")
print(f"Next 1h candle closes in {wait_seconds:.1f} seconds")
```

## Job Execution Guarantee

The `CandleScheduler` ensures jobs execute **at official candle close times**, not arbitrary delays:

### What NOT to do (Wrong Approach)
```python
# ❌ WRONG: This executes 1 hour after START, not at candle close
async def bad_timing():
    while True:
        await asyncio.sleep(3600)  # 1 hour after start
        fetch_data()  # Might not be at official close time
```

### What TO do (Correct Approach)
```python
# ✅ CORRECT: This executes at official candle close
scheduler = CandleScheduler()
scheduler.start_job("1h", fetch_data_callback)  # Runs at :00 of each hour
```

**Key Difference**:
- Wrong approach: Sleeps arbitrary duration, then executes (timing drifts)
- Correct approach: Calculates exact next close time, waits precisely, executes

## Performance Benefits

### REST API vs WebSocket
- **REST API**: Minimal data transfer, only fetch when needed (efficient)
- **WebSocket**: Continuous stream of updates (unnecessary for timeframe-based trading)

### Exact Timing
- Jobs execute **exactly** when candles close
- No missed closes
- No premature execution
- Perfect synchronization with exchange

### Rate Limiting
- Binance allows 1200 weight/minute
- Each `klines` request costs 1 weight
- Fetching 8 symbols at 4 timeframes per close = 32 weight
- Can execute ~37 times per minute without issues

## Example: Fetching at Candle Close

```python
from src.application.services.market_data_service import MarketDataService
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.domain.market_data.services.candle_scheduler import CandleScheduler

# Setup
binance = BinanceRESTClient()
scheduler = CandleScheduler()
market_data = MarketDataService(binance, scheduler)

# Register callback
async def on_1h_close(symbol, candle, timeframe):
    print(f"{symbol} 1h candle closed: {candle['close']}")

market_data.register_candle_callback("1h", on_1h_close)

# Start jobs - will execute callbacks at exact 1h closes
await market_data.start_all_jobs()

# When next hour arrives (e.g., 15:00:00 UTC exactly):
# - CandleScheduler waits precisely
# - Executes on_1h_close() with latest completed candle
# - Fetches from REST API
# - Callback executes with exact close data
```

## Verification

To verify your local time and calculate correct UTC times:

```python
from datetime import datetime, timezone

# Get current UTC time
now_utc = datetime.now(timezone.utc)
print(f"Current UTC: {now_utc.isoformat()}")

# Get next 1h close
from src.domain.market_data.services.candle_scheduler import CandleScheduler
scheduler = CandleScheduler()
next_1h = scheduler.get_next_candle_time("1h")
print(f"Next 1h close: {next_1h.isoformat()} UTC")
```

## Troubleshooting

### Jobs not executing at right time?
- Check server time is accurate with `ntpdate` (macOS/Linux)
- Verify using `binance_client.get_server_time()` vs your system time
- Difference should be < 1 second

### Missing data points?
- Ensure callbacks complete before next close
- Check network connectivity to Binance API
- Monitor logs for fetch errors

### Timing off by seconds?
- System clock drift - synchronize with NTP
- High CPU load - may delay thread execution
- Check `CandleScheduler.get_job_status()` for actual next close time

## References

- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Kline/Candlestick Data](https://binance-docs.github.io/apidocs/#kline-candlestick-data)
- [Rate Limits](https://binance-docs.github.io/apidocs/#limits)
