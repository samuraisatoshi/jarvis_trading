# Trading Strategies Package - Requirements

## Overview

The `src/strategies/` package provides a Strategy Pattern implementation for trading algorithms, enabling flexible and extensible strategy selection for backtesting, live trading, and paper trading.

## Architecture

### Design Pattern: Strategy Pattern

The Strategy Pattern allows algorithms to be selected and swapped at runtime without modifying client code. All strategies implement a common interface (`TradingStrategy`), making them interchangeable.

**Benefits:**
- **Open/Closed Principle**: Open for extension (new strategies), closed for modification
- **Single Responsibility**: Each strategy focuses on one algorithm
- **Dependency Inversion**: Depend on abstraction, not concrete implementations
- **Liskov Substitution**: All strategies are substitutable via common interface

## Package Structure

```
src/strategies/
├── __init__.py                     # Package exports
├── base.py                         # Strategy interface (TradingStrategy, BaseIndicatorStrategy)
├── models.py                       # Data models (FibonacciLevels, TradeSignal, enums)
├── fibonacci_golden_zone.py       # Fibonacci strategy implementation
└── REQUIREMENTS.md                 # This file
```

## Core Components

### 1. base.py - Strategy Interface

**TradingStrategy (ABC)**
- Abstract base class for all strategies
- Core method: `generate_signal(df: pd.DataFrame) -> Dict`
- Helper: `validate_dataframe()` for input validation

**BaseIndicatorStrategy (extends TradingStrategy)**
- Extended base for indicator-based strategies
- Provides common indicators: RSI, EMA, SMA
- Strategies using technical indicators should inherit from this

### 2. models.py - Data Structures

**Enums:**
- `TrendType`: UPTREND, DOWNTREND, LATERAL, UNKNOWN
- `SignalType`: BUY, SELL, HOLD
- `ConfirmationSignal`: RSI divergences, volume, candlestick patterns, etc.

**Dataclasses:**
- `FibonacciLevels`: Fibonacci retracement/extension levels with helper methods
- `TradeSignal`: Complete trading signal with metadata (backward compatible)
- `SwingPoint`: Swing high/low point representation

### 3. fibonacci_golden_zone.py - Fibonacci Strategy

**FibonacciGoldenZoneStrategy**
- Targets Golden Zone (50%-61.8% Fibonacci retracement)
- EMA-based trend identification (20/50/200)
- Swing point detection
- Multiple confirmation signals (RSI, volume, candlesticks)
- Risk management (stop loss at 78.6%, targets at 161.8% and 261.8%)

## Signal Format

All strategies must return a dictionary with this structure:

```python
{
    # Required fields
    'action': str,              # 'BUY', 'SELL', or 'HOLD'
    'reason': str,              # Human-readable explanation
    'current_price': float,     # Current market price
    'trend': str,               # Market trend context

    # Required for BUY/SELL signals
    'entry': float,             # Entry price
    'stop_loss': float,         # Stop loss price
    'take_profit_1': float,     # First take profit target
    'take_profit_2': float,     # Second take profit target (optional)

    # Optional metadata
    'confirmations': list,      # List of confirmation signal names
    'confidence': float,        # Confidence score 0-1 (optional)
    'metadata': dict,           # Strategy-specific data (optional)
}
```

## Integration Points

### Backtesting Engine

```python
from src.backtesting.engine import BacktestEngine
from src.strategies import FibonacciGoldenZoneStrategy

strategy = FibonacciGoldenZoneStrategy()
engine = BacktestEngine(initial_balance=5000, strategy=strategy)
trades, portfolio = engine.run(historical_data)
```

### Live Trading

```python
from src.strategies import FibonacciGoldenZoneStrategy

strategy = FibonacciGoldenZoneStrategy()
signal = strategy.generate_signal(market_data)

if signal['action'] == 'BUY':
    execute_order(
        side='buy',
        price=signal['entry'],
        stop_loss=signal['stop_loss'],
        take_profit=signal['take_profit_1']
    )
```

### Paper Trading

Same interface as live trading, but orders go to paper account.

## Adding New Strategies

To add a new strategy:

1. **Create new strategy file**: `src/strategies/my_strategy.py`

2. **Inherit from appropriate base**:
   ```python
   from src.strategies.base import BaseIndicatorStrategy

   class MyStrategy(BaseIndicatorStrategy):
       def __init__(self):
           # Initialize parameters
           pass

       def generate_signal(self, df: pd.DataFrame) -> Dict:
           # Implement strategy logic
           return {
               'action': 'BUY',
               'reason': 'Strategy conditions met',
               'entry': 100.0,
               'stop_loss': 95.0,
               'take_profit_1': 110.0,
               # ... other fields
           }
   ```

3. **Add to package exports**: `src/strategies/__init__.py`
   ```python
   from src.strategies.my_strategy import MyStrategy

   __all__ = [
       # ... existing exports
       'MyStrategy',
   ]
   ```

4. **Document in REQUIREMENTS.md**: Add description of new strategy

5. **Create tests**: `tests/test_my_strategy.py`

## SOLID Principles Compliance

### Single Responsibility Principle (SRP)
- `base.py`: Only defines strategy interface
- `models.py`: Only defines data structures
- `fibonacci_golden_zone.py`: Only implements Fibonacci strategy
- Each method has one clear purpose

### Open/Closed Principle (OCP)
- Base class open for extension (inherit and implement)
- Closed for modification (don't change base class)
- New strategies added without modifying existing code

### Liskov Substitution Principle (LSP)
- All strategies are substitutable via `TradingStrategy` interface
- Same `generate_signal()` contract
- Consistent return format

### Interface Segregation Principle (ISP)
- Minimal interface: Only `generate_signal()` required
- Optional helpers available but not mandatory
- Strategies only implement what they need

### Dependency Inversion Principle (DIP)
- Backtesting engine depends on `TradingStrategy` abstraction
- Live trading depends on `TradingStrategy` abstraction
- Concrete strategies are implementation details

## Testing

### Unit Tests

```python
import pandas as pd
from src.strategies import FibonacciGoldenZoneStrategy

def test_fibonacci_strategy():
    strategy = FibonacciGoldenZoneStrategy()

    # Create test data
    df = pd.DataFrame({
        'open': [100, 102, 101],
        'high': [103, 104, 102],
        'low': [99, 101, 100],
        'close': [102, 101, 101.5],
        'volume': [1000, 1200, 1100]
    })

    # Generate signal
    signal = strategy.generate_signal(df)

    # Validate signal format
    assert 'action' in signal
    assert signal['action'] in ['BUY', 'SELL', 'HOLD']
    assert 'reason' in signal
    assert 'current_price' in signal
```

### Integration Tests

Test with backtesting engine using historical data.

## Performance Considerations

### Memory
- Strategies should not store large datasets
- Process DataFrames in streaming fashion when possible
- Clean up temporary calculations

### Speed
- Indicator calculations should use vectorized operations (pandas/numpy)
- Avoid loops where possible
- Cache expensive calculations if reused

## Dependencies

- `pandas`: DataFrame operations
- `numpy`: Numerical calculations
- `loguru`: Logging
- `src.backtesting.engine`: Backtesting integration

## Version History

- **v1.0.0** (2025-11-15): Initial implementation
  - Strategy Pattern architecture
  - Fibonacci Golden Zone strategy
  - Base classes and data models
  - Clean package structure

## Future Enhancements

1. **Additional Strategies**:
   - Mean Reversion Strategy
   - Momentum Strategy
   - Multi-timeframe Strategy

2. **Strategy Composition**:
   - Combine multiple strategies
   - Weighted ensemble voting
   - Strategy chains

3. **Optimization**:
   - Parameter optimization interface
   - Grid search support
   - Genetic algorithm optimization

4. **Machine Learning Integration**:
   - ML-based strategies
   - Feature engineering helpers
   - Model persistence

## Refactoring Notes

### Original Implementation
- Location: `scripts/fibonacci_golden_zone_strategy.py`
- Size: 574 lines
- Issues: Monolithic, not reusable, in scripts/ directory

### Refactored Implementation
- Location: `src/strategies/` package
- Size: ~1050 lines across 4 modules
- Benefits:
  - Strategy Pattern implementation
  - Reusable across backtesting/live/paper trading
  - SOLID principles compliance
  - Clean imports (no sys.path hacks)
  - Proper package structure
  - Backward compatible

### Migration Path
- Scripts wrapper: `scripts/fibonacci_golden_zone_strategy.py` (85 lines)
- Maintains backward compatibility
- Imports from refactored location
- Existing scripts work without changes

## Contact

For questions or enhancements, see project documentation or create an issue.
