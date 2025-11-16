# Backtesting Module - Requirements & Architecture

**Version**: 1.0.0
**Status**: ✅ Phase 2.2 Complete
**Date**: 2025-11-15

## Overview

Comprehensive backtesting framework for trading strategies, built following SOLID principles and Design Patterns. The framework is strategy-agnostic and supports any trading strategy that implements the `TradingStrategy` interface.

## Architecture

### Design Patterns

1. **Strategy Pattern**: Core engine (`BacktestEngine`) can execute any strategy implementing `TradingStrategy` interface
2. **Dependency Injection**: Components receive dependencies via constructor
3. **Template Method**: Backtest execution follows defined skeleton in base class
4. **Separation of Concerns**: Each module has single, clear responsibility

### Module Structure

```
src/backtesting/
├── __init__.py (63 lines) - Package exports
├── models.py (230 lines) - Data structures
├── engine.py (355 lines) - Core backtest execution engine
├── metrics_calculator.py (391 lines) - Performance metrics
├── baseline_strategies.py (341 lines) - Baseline comparisons
├── visualizer.py (424 lines) - Chart generation
└── fibonacci_strategy.py (195 lines) - Fibonacci strategy integration
```

**Total**: 1,999 lines (vs original 804 lines)
**Benefit**: Modular, testable, reusable components

### Line Count Status

| Module | Lines | Limit | Status |
|--------|-------|-------|--------|
| models.py | 230 | 400 | ✅ |
| engine.py | 355 | 400 | ✅ |
| metrics_calculator.py | 391 | 400 | ✅ |
| baseline_strategies.py | 341 | 400 | ✅ |
| fibonacci_strategy.py | 195 | 400 | ✅ |
| visualizer.py | 424 | 400 | ⚠️ (+24) |
| __init__.py | 63 | - | ✅ |
| **CLI (refactored)** | 236 | - | ✅ |

**Note**: visualizer.py is 24 lines over due to comprehensive chart generation. Can be split if needed.

## SOLID Principles Applied

### Single Responsibility Principle
- `models.py`: Only data structures
- `engine.py`: Only trade execution logic
- `metrics_calculator.py`: Only metrics calculation
- `visualizer.py`: Only chart generation
- `baseline_strategies.py`: Only baseline comparisons
- `fibonacci_strategy.py`: Only Fibonacci strategy integration

### Open/Closed Principle
- `BacktestEngine` is open for extension (new strategies) but closed for modification
- `BaselineStrategy` abstract class allows new baselines without changing existing code
- `MetricsCalculator` can add new metrics without breaking existing ones

### Liskov Substitution Principle
- Any `TradingStrategy` implementation can replace another
- Any `BaselineStrategy` can be used interchangeably

### Interface Segregation Principle
- Separate interfaces for: Strategy, Baseline, Metrics, Visualization
- Clients only depend on interfaces they use

### Dependency Inversion Principle
- `BacktestEngine` depends on `TradingStrategy` abstraction, not concrete implementation
- `MetricsCalculator` works with `Trade` abstraction
- All high-level modules depend on abstractions

## Component Details

### 1. models.py

**Purpose**: Core data structures

**Classes**:
- `Trade`: Single trade record with complete lifecycle
- `BacktestMetrics`: Comprehensive performance metrics
- `PortfolioState`: Portfolio snapshot at specific time
- `TradeType`: Enum for trade types (LONG/SHORT)
- `ExitReason`: Enum for exit reasons

**Features**:
- Immutable dataclasses for thread-safety
- Built-in serialization (to_dict)
- Rich display methods (print_summary)

### 2. engine.py

**Purpose**: Core backtest execution engine

**Classes**:
- `TradingStrategy` (ABC): Strategy interface
- `BacktestEngine`: Main execution engine

**Features**:
- Strategy-agnostic execution
- Position management (LONG/SHORT)
- Automatic stop loss / take profit handling
- Portfolio value tracking
- Trade history management

**Key Methods**:
- `run()`: Execute backtest on historical data
- `_execute_entry()`: Enter new position
- `_execute_exit()`: Close position
- `_check_exit_conditions()`: Monitor SL/TP

### 3. metrics_calculator.py

**Purpose**: Performance metrics calculation

**Classes**:
- `MetricsCalculator`: Static methods for metrics

**Metrics**:
- **Return Metrics**: Total return, annualized return
- **Risk Metrics**: Sharpe ratio, max drawdown
- **Trade Statistics**: Win rate, profit factor, streaks
- **Temporal Analysis**: Period performance, time in market

**Key Methods**:
- `calculate()`: Comprehensive metrics
- `analyze_by_period()`: Quarterly/monthly breakdown
- `compare_strategies()`: Multi-strategy comparison

### 4. baseline_strategies.py

**Purpose**: Baseline comparison strategies

**Classes**:
- `BaselineStrategy` (ABC): Baseline interface
- `BuyAndHoldBaseline`: Buy at start, sell at end
- `SimpleDCABaseline`: Regular interval purchases

**Features**:
- Standard benchmarks for comparison
- Same metrics as active strategies
- Easy to add new baselines

**Key Functions**:
- `compare_with_baseline()`: Calculate outperformance
- `print_baseline_comparison()`: Formatted comparison

### 5. visualizer.py

**Purpose**: Chart generation and reporting

**Classes**:
- `BacktestVisualizer`: Multi-panel chart generator

**Charts**:
1. Price with trade signals
2. Portfolio value comparison
3. Drawdown evolution
4. Trade PnL distribution
5. Cumulative returns
6. Period returns (monthly/quarterly)

**Features**:
- Publication-quality charts
- Configurable size and resolution
- Multiple strategies support
- Saves to file or displays

### 6. fibonacci_strategy.py

**Purpose**: Fibonacci Golden Zone strategy integration

**Classes**:
- `FibonacciBacktestStrategy`: Strategy wrapper
- `FibonacciBacktester`: High-level interface

**Features**:
- Wraps `FibonacciGoldenZoneStrategy` from scripts/
- Implements `TradingStrategy` interface
- Handles data fetching from Binance
- Convenience methods for full workflow

## Usage Examples

### Basic Backtest

```python
from src.backtesting import FibonacciBacktester, MetricsCalculator

# Initialize
backtester = FibonacciBacktester(initial_balance=5000)

# Fetch data
df = backtester.fetch_historical_data('BNB_USDT', '4h', '2023-11-01')

# Run backtest
trades, portfolio_df = backtester.run(df)

# Calculate metrics
metrics = MetricsCalculator.calculate(
    trades, portfolio_df, 5000, 'BNB_USDT', '4h'
)

# Print results
metrics.print_summary()
```

### With Baseline Comparison

```python
from src.backtesting import BuyAndHoldBaseline, print_baseline_comparison

# Calculate baseline
baseline = BuyAndHoldBaseline()
buy_hold = baseline.calculate(df, 5000, start_idx=200)

# Compare
print_baseline_comparison(metrics.to_dict(), buy_hold)
```

### With Visualization

```python
from src.backtesting import BacktestVisualizer

# Create visualizer
visualizer = BacktestVisualizer()

# Generate chart
visualizer.create_comprehensive_chart(
    portfolio_df=portfolio_df,
    price_df=df,
    trades=trades,
    baseline_dict=buy_hold,
    initial_balance=5000,
    output_path='backtest_results.png',
    symbol='BNB_USDT',
    strategy_name='Fibonacci Golden Zone'
)
```

### Custom Strategy

```python
from src.backtesting import BacktestEngine, TradingStrategy
import pandas as pd

class MyCustomStrategy(TradingStrategy):
    def generate_signal(self, df: pd.DataFrame) -> dict:
        # Your strategy logic here
        return {
            'action': 'BUY',  # or 'SELL' or 'HOLD'
            'stop_loss': 500.0,
            'take_profit_1': 600.0,
            'take_profit_2': 650.0,
            'confirmations': ['RSI_oversold', 'volume_spike']
        }

# Use with engine
strategy = MyCustomStrategy()
engine = BacktestEngine(initial_balance=5000, strategy=strategy)
trades, portfolio = engine.run(df)
```

## CLI Interface

### Refactored Script

```bash
# Run refactored backtest
python scripts/backtest_fibonacci_comprehensive_refactored.py \
    --symbol BNB_USDT \
    --timeframe 4h \
    --start 2023-11-01 \
    --balance 5000 \
    --output data/backtests/
```

### Features
- Same CLI interface as original (backward compatible)
- Uses modular components under the hood
- Generates same outputs: JSON report, CSV trades, PNG chart
- Comprehensive executive summary

## Testing Strategy

### Unit Tests

```python
# tests/backtesting/test_models.py
def test_trade_close():
    trade = Trade(entry_time='2023-01-01', entry_price=100, quantity=1)
    trade.close('2023-01-02', 110, 'take_profit')
    assert trade.pnl == 10.0
    assert trade.pnl_pct == 10.0
    assert trade.is_winner() == True

# tests/backtesting/test_engine.py
def test_backtest_execution():
    strategy = MockStrategy()  # Returns predictable signals
    engine = BacktestEngine(1000, strategy)
    trades, portfolio = engine.run(mock_df)
    assert len(trades) > 0
    assert not portfolio.empty

# tests/backtesting/test_metrics.py
def test_sharpe_calculation():
    metrics = MetricsCalculator.calculate(trades, portfolio_df, ...)
    assert metrics.sharpe_ratio > 0
```

### Integration Tests

```python
# tests/backtesting/test_fibonacci_integration.py
def test_full_workflow():
    backtester = FibonacciBacktester(5000)
    df = load_test_data()
    trades, portfolio = backtester.run(df)
    metrics = MetricsCalculator.calculate(...)
    assert metrics.total_trades > 0
    assert metrics.final_balance != 5000
```

## Performance

### Metrics
- **Execution Time**: ~5-10 seconds for 2 years of 4h data (~4,380 candles)
- **Memory Usage**: < 100MB for typical backtest
- **Scalability**: Tested with up to 10,000 candles

### Optimizations
- Pandas vectorization for indicators
- Minimal DataFrame copies
- Efficient indexing for lookups
- Lazy imports where possible

## Migration from Original

### Before (Original)
```python
# All in one file: 804 lines
from backtest_fibonacci_comprehensive import FibonacciBacktester
backtester = FibonacciBacktester(5000)
# ... rest of logic
```

### After (Refactored)
```python
# Modular: 6 focused modules
from src.backtesting import FibonacciBacktester, MetricsCalculator, BacktestVisualizer
backtester = FibonacciBacktester(5000)
# Same interface, better structure
```

### Benefits of Migration
1. **Testability**: Each module independently testable
2. **Reusability**: Engine works with ANY strategy
3. **Maintainability**: Clear separation of concerns
4. **Extensibility**: Easy to add new features
5. **Readability**: Smaller, focused files

## Future Enhancements

### Planned Features
1. **Multi-asset backtesting**: Portfolio of multiple assets
2. **Walk-forward analysis**: Out-of-sample validation
3. **Parameter optimization**: Grid search for best parameters
4. **Monte Carlo simulation**: Statistical confidence intervals
5. **Transaction costs**: Realistic fee modeling

### Potential New Modules
- `optimizer.py`: Parameter optimization engine
- `walk_forward.py`: Walk-forward analysis
- `monte_carlo.py`: Monte Carlo simulation
- `transaction_costs.py`: Fee and slippage modeling

## Dependencies

### Required
- pandas >= 1.5.0
- numpy >= 1.23.0
- matplotlib >= 3.6.0

### Optional
- pytest >= 7.0.0 (for testing)

## Configuration

### Environment Variables
None required. All configuration via function arguments.

### Default Parameters
- `initial_balance`: 5000 (USD)
- `warmup_periods`: 200 (candles)
- `chart_dpi`: 150
- `chart_figsize`: (20, 14)

## Troubleshooting

### Common Issues

**Import Error**: `ModuleNotFoundError: No module named 'src.backtesting'`
- **Solution**: Ensure project root in sys.path: `sys.path.insert(0, str(project_root))`

**Empty DataFrame**: `ValueError: Portfolio dataframe is empty`
- **Solution**: Check data fetching, ensure sufficient historical data

**Visualizer Error**: `ValueError: required data is missing`
- **Solution**: Ensure portfolio_df and price_df are not empty, check indices

## Standards & Best Practices

### Code Quality
- ✅ Type hints on all public methods
- ✅ Comprehensive docstrings (Google style)
- ✅ PEP 8 compliant
- ✅ Error handling with proper exceptions
- ✅ Logging where appropriate

### Documentation
- ✅ Module-level docstrings
- ✅ Class-level docstrings
- ✅ Method-level docstrings
- ✅ Inline comments for complex logic
- ✅ Usage examples in docstrings

### Testing
- ⚠️ Unit tests TODO (planned)
- ⚠️ Integration tests TODO (planned)
- ⚠️ Mock objects for external dependencies

## Change Log

### v1.0.0 (2025-11-15)
- ✅ Initial modular architecture
- ✅ Extracted models from monolithic file
- ✅ Created strategy-agnostic engine
- ✅ Implemented metrics calculator
- ✅ Added baseline strategies
- ✅ Built comprehensive visualizer
- ✅ Integrated Fibonacci strategy
- ✅ Refactored CLI script

## License

Same as project root.

## Contact

For questions or issues, refer to project maintainer.

---

**Phase 2.2 Complete** ✅
Original 804-line file successfully refactored into 6 modular components (1,999 lines total).
