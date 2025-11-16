## Elliott Wave Analysis Package - Requirements & Documentation

**Version:** 1.0.0
**Created:** 2025-11-15
**Module:** `src/elliott_wave/`
**Purpose:** Modular Elliott Wave analysis framework for cryptocurrency markets

---

## 📋 Overview

This package provides comprehensive Elliott Wave analysis through a modular, extensible architecture. Refactored from monolithic 712-line script into 9 focused modules following SOLID principles.

### Key Features

- **Multiple Wave Detection Algorithms**: Pivot, ZigZag, Adaptive (ATR-based)
- **Pattern Recognition**: Impulsive (1-5) and Corrective (ABC) wave structures
- **Fibonacci Integration**: Retracement and extension levels
- **Technical Indicators**: RSI, MACD, Volume, Momentum analysis
- **Risk Management**: Complete signal generation with stop-loss and take-profit levels
- **Multi-Timeframe**: Aggregate signals across timeframes (1D + 4H)
- **Extensible Design**: Strategy Pattern allows easy algorithm swapping

---

## 🏗️ Architecture

### Module Structure

```
src/elliott_wave/
├── __init__.py                  # Package exports (50 lines)
├── models.py                    # Data models (340 lines)
├── wave_detector.py             # Wave detection strategies (280 lines)
├── pattern_analyzer.py          # Pattern recognition (320 lines)
├── fibonacci_calculator.py      # Fibonacci calculations (230 lines)
├── indicator_engine.py          # Technical indicators (290 lines)
├── signal_generator.py          # Signal generation (380 lines)
├── analyzer.py                  # Main orchestrator (180 lines)
├── visualizer.py                # Report generation (280 lines)
└── REQUIREMENTS.md              # This file
```

**Total Lines:** ~2,350 (modular) vs 712 (monolithic)
**Average Module Size:** ~260 lines (all < 400 line limit)

---

## 🎯 SOLID Principles Applied

### Single Responsibility
Each module has ONE clear purpose:
- `models.py`: Data structures only
- `wave_detector.py`: Pivot/swing detection only
- `pattern_analyzer.py`: Wave counting only
- `fibonacci_calculator.py`: Fibonacci math only
- `indicator_engine.py`: Technical indicators only
- `signal_generator.py`: Signal logic only
- `analyzer.py`: Orchestration only
- `visualizer.py`: Output formatting only

### Open/Closed Principle
Abstract interfaces allow extension without modification:
- `WaveDetectorInterface`: Add new detection algorithms
- `PatternAnalyzerInterface`: Add new wave counting methods
- `SignalGeneratorInterface`: Add new signal strategies
- `IndicatorInterface`: Add new technical indicators

### Liskov Substitution
All implementations are interchangeable:
```python
# Can swap detectors without changing client code
analyzer = ElliottWaveAnalyzer(
    wave_detector=PivotDetector()  # or ZigZagDetector() or AdaptivePivotDetector()
)
```

### Interface Segregation
Small, focused interfaces:
- Each interface defines minimal required methods
- No client forced to depend on unused methods

### Dependency Inversion
High-level modules depend on abstractions:
- `ElliottWaveAnalyzer` depends on interfaces, not concrete implementations
- Components injected via constructor (Dependency Injection)

---

## 📦 Design Patterns

### Strategy Pattern
**Where:** Wave detectors, indicators, signal generators
**Why:** Allow runtime algorithm selection

```python
# Example: Swap wave detection strategy
from src.elliott_wave import ElliottWaveAnalyzer, ZigZagDetector

analyzer = ElliottWaveAnalyzer(
    wave_detector=ZigZagDetector(threshold_pct=3.0)
)
```

### Template Method Pattern
**Where:** `ElliottWaveCounter.analyze()`
**Why:** Define algorithm skeleton, customize specific steps

```python
# Base counter defines template
class ElliottWaveCounter:
    def analyze(self, ...):
        self._validate_pivots()
        self._merge_pivots()
        self._determine_trend()
        # ... specialized wave counting
```

### Dependency Injection
**Where:** `ElliottWaveAnalyzer.__init__()`
**Why:** Loose coupling, testability

```python
analyzer = ElliottWaveAnalyzer(
    wave_detector=custom_detector,
    pattern_analyzer=custom_analyzer,
    signal_generator=custom_generator
)
```

---

## 🔧 Component Details

### 1. models.py

**Purpose:** Immutable data structures for all domain concepts

**Key Classes:**
- `WavePattern`: Identified Elliott Wave structure
- `FibonacciLevels`: Retracement/extension levels
- `TechnicalIndicators`: RSI, MACD, volume, momentum
- `TradingSignal`: Complete signal with risk management
- `WaveAnalysis`: Aggregated analysis for one timeframe
- `PivotPoint`: Swing high/low marker

**Enums:**
- `WaveType`: IMPULSIVE, CORRECTIVE, UNKNOWN
- `WavePosition`: WAVE_1, WAVE_2, ..., WAVE_A, WAVE_B, WAVE_C
- `SignalAction`: BUY, SELL, HOLD
- `MomentumType`: BULLISH, BEARISH, NEUTRAL
- `VolumeTrend`: INCREASING, DECREASING, NEUTRAL

**Design:** All dataclasses with `to_dict()` for serialization

---

### 2. wave_detector.py

**Purpose:** Detect significant price swings (pivots) from OHLCV data

**Interface:** `WaveDetectorInterface`
```python
def detect_pivots(df: pd.DataFrame) -> Tuple[List[PivotPoint], List[PivotPoint]]
```

**Implementations:**

#### PivotDetector (Standard)
- Swing high/low algorithm
- Configurable window (default: 5 bars)
- Minimum price change filter
- **Use for:** General wave detection

#### ZigZagDetector (Aggressive)
- Percentage-based threshold
- Fewer pivots, larger swings
- Configurable threshold (default: 3%)
- **Use for:** Longer-term analysis

#### AdaptivePivotDetector (Dynamic)
- ATR-based adaptive threshold
- Adjusts to volatility
- More lenient in volatile markets
- **Use for:** All market conditions

**Example:**
```python
from src.elliott_wave import PivotDetector, ZigZagDetector

# Standard pivot detection
detector1 = PivotDetector(window=5, min_price_change=0.5)
highs, lows = detector1.detect_pivots(df)

# Aggressive ZigZag
detector2 = ZigZagDetector(threshold_pct=5.0)
highs, lows = detector2.detect_pivots(df)
```

---

### 3. pattern_analyzer.py

**Purpose:** Identify Elliott Wave patterns from pivots

**Interface:** `PatternAnalyzerInterface`
```python
def analyze(df, pivot_highs, pivot_lows) -> WavePattern
```

**Implementations:**

#### ElliottWaveCounter (Main)
- Template Method pattern
- Determines trend direction
- Identifies wave type (impulsive/corrective)
- Counts wave position (1-5 or A-B-C)
- Calculates projections and invalidation levels

#### ImpulsiveWaveAnalyzer (Specialized)
- Focuses on 5-wave impulsive structures
- Additional impulsive wave validation
- Returns UNKNOWN if not impulsive

#### CorrectiveWaveAnalyzer (Specialized)
- Focuses on ABC corrective structures
- Additional corrective wave validation
- Returns UNKNOWN if not corrective

**Algorithm Flow:**
1. Validate minimum pivots
2. Merge and sort pivots chronologically
3. Determine overall trend (bullish/bearish)
4. Extract recent pivots (last 8)
5. Classify as impulsive or corrective
6. Count wave position
7. Calculate projection target
8. Calculate invalidation level

**Example:**
```python
from src.elliott_wave import ElliottWaveCounter

analyzer = ElliottWaveCounter(min_confidence=50)
pattern = analyzer.analyze(df, pivot_highs, pivot_lows)

print(f"Wave Type: {pattern.wave_type.value}")
print(f"Current Wave: {pattern.current_wave.value}")
print(f"Confidence: {pattern.confidence}%")
```

---

### 4. fibonacci_calculator.py

**Purpose:** Calculate Fibonacci retracement and extension levels

**Main Class:** `FibonacciCalculator`

**Methods:**
- `calculate_levels(start, end)`: All standard Fibonacci levels
- `calculate_retracement(start, end, ratio)`: Specific retracement
- `calculate_extension(start, end, ratio)`: Specific extension
- `find_nearest_level(price, fib_levels)`: Closest Fibonacci level
- `get_support_levels(price, fib_levels)`: Supports below price
- `get_resistance_levels(price, fib_levels)`: Resistances above price
- `calculate_wave_projection(wave1_start, wave1_end, wave2_end)`: Wave 3 target
- `validate_wave2_retracement(...)`: Validate Wave 2 rules

**Standard Ratios:**
- Retracements: 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
- Extensions: 161.8%, 261.8%, 361.8%, 423.6%
- Golden Ratio: 1.618 (phi)

**Example:**
```python
from src.elliott_wave import FibonacciCalculator

calc = FibonacciCalculator()

# Calculate levels from swing low to swing high
fib = calc.calculate_levels(start_price=30000, end_price=40000)

print(f"38.2% retracement: ${fib.level_382:,.2f}")
print(f"61.8% retracement: ${fib.level_618:,.2f}")
print(f"161.8% extension: ${fib.level_1618:,.2f}")

# Project Wave 3 target
targets = calc.calculate_wave_projection(
    wave1_start=30000,
    wave1_end=40000,
    wave2_end=36000
)
print(f"Wave 3 target: ${targets['standard']:,.2f}")
```

---

### 5. indicator_engine.py

**Purpose:** Calculate technical indicators for wave confirmation

**Interface:** `IndicatorInterface`
```python
def calculate(df: pd.DataFrame) -> float
```

**Implementations:**

#### RSIIndicator
- Relative Strength Index (0-100)
- Configurable period (default: 14)
- Identifies overbought/oversold conditions

#### MACDIndicator
- Moving Average Convergence Divergence
- Returns MACD, signal line, histogram
- Configurable periods (12, 26, 9)

#### VolumeAnalyzer
- Compares recent vs baseline volume
- Classifies trend: INCREASING, DECREASING, NEUTRAL
- Detects climactic volume

#### MomentumAnalyzer
- Combines RSI and MACD
- Overall momentum: BULLISH, BEARISH, NEUTRAL

**Main Class:** `IndicatorEngine`
- Coordinates all indicators
- Returns `TechnicalIndicators` model

**Example:**
```python
from src.elliott_wave import IndicatorEngine

engine = IndicatorEngine()
indicators = engine.calculate_all(df)

print(f"RSI: {indicators.rsi:.2f}")
print(f"MACD Histogram: {indicators.macd_histogram:.2f}")
print(f"Momentum: {indicators.momentum.value}")
print(f"Volume Trend: {indicators.volume_trend.value}")
```

---

### 6. signal_generator.py

**Purpose:** Generate trading signals with risk management

**Interface:** `SignalGeneratorInterface`
```python
def generate(wave_pattern, indicators, fib_levels, current_price) -> TradingSignal
```

**Main Class:** `ElliottWaveSignalGenerator`

**Signal Logic:**

**Corrective Waves (ABC):**
- **Wave C completion**: BUY signal (oversold RSI, momentum turning)
- **Wave A/B**: HOLD (wait for completion)

**Impulsive Waves (1-5):**
- **Wave 5 exhaustion**: SELL signal (overbought RSI, declining volume)
- **Wave 1/3 momentum**: BUY signal (strong momentum, bullish indicators)
- **Wave 2/4 correction**: HOLD (wait for correction completion)

**Risk Management:**
- Stop loss: Based on invalidation level or Fibonacci
- Take Profit 1: 38.2% Fibonacci
- Take Profit 2: 61.8% Fibonacci
- Take Profit 3: 161.8% extension
- Risk/Reward: Calculated automatically

**Multi-Timeframe Class:** `MultiTimeframeSignalAggregator`
- Combines 1D (strategic) + 4H (tactical)
- Weighted aggregation
- Conflict resolution (HOLD if disagree)

**Example:**
```python
from src.elliott_wave import ElliottWaveSignalGenerator

generator = ElliottWaveSignalGenerator(
    min_confidence=60,
    min_risk_reward=1.5
)

signal = generator.generate(wave_pattern, indicators, fib_levels, current_price)

print(f"Action: {signal.action.value}")
print(f"Confidence: {signal.confidence}%")
print(f"Entry: ${signal.entry_price:,.2f}")
print(f"Stop Loss: ${signal.stop_loss:,.2f}")
print(f"Take Profit: ${signal.take_profit_2:,.2f}")
print(f"R/R: 1:{signal.risk_reward_ratio:.2f}")
```

---

### 7. analyzer.py

**Purpose:** Main orchestrator coordinating all components

**Main Class:** `ElliottWaveAnalyzer`

**Constructor:** Accepts optional component injection
```python
def __init__(
    wave_detector: Optional[WaveDetectorInterface] = None,
    pattern_analyzer: Optional[PatternAnalyzerInterface] = None,
    signal_generator: Optional[SignalGeneratorInterface] = None
)
```

**Main Method:** `analyze(df, timeframe) -> WaveAnalysis`

**Analysis Flow:**
1. Validate DataFrame (OHLCV, min 50 bars, DatetimeIndex)
2. Detect pivots (via wave_detector)
3. Analyze wave pattern (via pattern_analyzer)
4. Calculate Fibonacci levels (via fib_calculator)
5. Calculate indicators (via indicator_engine)
6. Generate signal (via signal_generator)
7. Aggregate into WaveAnalysis

**Configuration Methods:**
- `configure_wave_detector(detector)`
- `configure_pattern_analyzer(analyzer)`
- `configure_signal_generator(generator)`

**Example:**
```python
from src.elliott_wave import ElliottWaveAnalyzer, ZigZagDetector

# Default configuration
analyzer = ElliottWaveAnalyzer()

# Custom configuration
analyzer = ElliottWaveAnalyzer(
    wave_detector=ZigZagDetector(threshold_pct=4.0)
)

# Analyze
analysis = analyzer.analyze(df, timeframe='1d')
```

---

### 8. visualizer.py

**Purpose:** Generate formatted reports for console and file

**Main Class:** `ElliottWaveVisualizer`

**Methods:**
- `generate_report(analysis_1d, analysis_4h)`: Multi-timeframe report
- `print_report(analysis_1d, analysis_4h)`: Print to console
- `save_report(analysis_1d, analysis_4h, filepath)`: Save to file

**Report Sections:**
1. Header (symbol, timestamp)
2. 1D Analysis (macro structure)
   - Wave pattern
   - Fibonacci levels
   - Technical indicators
3. 4H Analysis (micro structure)
4. Multi-timeframe comparison
   - Wave type alignment
   - Momentum alignment
5. Trading signals
   - Strategic (1D)
   - Tactical (4H)
   - Final recommendation
6. Risk management
   - Entry, stop loss, take profits
   - Risk/reward ratio
7. Disclaimer

**Single Timeframe Class:** `SingleTimeframeVisualizer`
- For single timeframe reports

**Example:**
```python
from src.elliott_wave import ElliottWaveVisualizer

visualizer = ElliottWaveVisualizer(symbol='BTCUSDT')

# Print to console
visualizer.print_report(analysis_1d, analysis_4h)

# Save to file
visualizer.save_report(analysis_1d, analysis_4h, 'reports/elliott_wave.txt')
```

---

## 🚀 Usage Examples

### Basic Usage

```python
import pandas as pd
from src.elliott_wave import ElliottWaveAnalyzer, ElliottWaveVisualizer
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

# Fetch data
client = BinanceRESTClient(testnet=False)
klines = client.get_klines('BTCUSDT', '1d', limit=200)
df = pd.DataFrame(klines)
df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
df.set_index('timestamp', inplace=True)

# Analyze
analyzer = ElliottWaveAnalyzer()
analysis = analyzer.analyze(df, timeframe='1d')

# View results
print(f"Wave: {analysis.wave_pattern.current_wave.value}")
print(f"Type: {analysis.wave_pattern.wave_type.value}")
print(f"Signal: {analysis.signal.action.value}")
print(f"Confidence: {analysis.signal.confidence}%")
```

### Custom Wave Detection

```python
from src.elliott_wave import ElliottWaveAnalyzer, ZigZagDetector

# Use aggressive ZigZag detector
analyzer = ElliottWaveAnalyzer(
    wave_detector=ZigZagDetector(threshold_pct=5.0)
)

analysis = analyzer.analyze(df, timeframe='1d')
```

### Multi-Timeframe Analysis

```python
from src.elliott_wave import (
    ElliottWaveAnalyzer,
    ElliottWaveVisualizer,
    MultiTimeframeSignalAggregator
)

# Analyze both timeframes
analyzer = ElliottWaveAnalyzer()
analysis_1d = analyzer.analyze(df_1d, timeframe='1d')
analysis_4h = analyzer.analyze(df_4h, timeframe='4h')

# Aggregate signals
aggregator = MultiTimeframeSignalAggregator()
composite = aggregator.aggregate(analysis_1d.signal, analysis_4h.signal)

print(f"Final Action: {composite['final_action'].value}")
print(f"Aligned: {composite['aligned']}")

# Generate report
visualizer = ElliottWaveVisualizer(symbol='BTCUSDT')
visualizer.print_report(analysis_1d, analysis_4h)
```

### Custom Indicator Configuration

```python
from src.elliott_wave import ElliottWaveAnalyzer

analyzer = ElliottWaveAnalyzer()

# Configure RSI with 21-period instead of default 14
analyzer.indicator_engine.configure_rsi(period=21)

# Configure MACD with custom periods
analyzer.indicator_engine.configure_macd(fast=10, slow=20, signal=5)

analysis = analyzer.analyze(df, timeframe='1d')
```

---

## 🧪 Testing

### Unit Tests

Each module should have corresponding tests:

```python
# tests/test_wave_detector.py
from src.elliott_wave import PivotDetector

def test_pivot_detection():
    detector = PivotDetector(window=5)
    highs, lows = detector.detect_pivots(df)
    assert len(highs) > 0
    assert len(lows) > 0
```

### Integration Tests

```python
# tests/test_analyzer.py
from src.elliott_wave import ElliottWaveAnalyzer

def test_full_analysis():
    analyzer = ElliottWaveAnalyzer()
    analysis = analyzer.analyze(df, timeframe='1d')

    assert analysis.wave_pattern is not None
    assert analysis.signal.action in ['BUY', 'SELL', 'HOLD']
    assert 0 <= analysis.signal.confidence <= 100
```

---

## 📊 Performance

### Module Sizes
- All modules < 400 lines (requirement met)
- Average: ~260 lines per module
- Largest: signal_generator.py (380 lines)
- Smallest: __init__.py (50 lines)

### Complexity
- Cyclomatic complexity: Low (simple methods)
- Testability: High (dependency injection)
- Maintainability: High (SOLID principles)

---

## 🔄 Migration from Original Script

### Original Script (`scripts/elliott_wave_analysis.py`)
- Monolithic: 712 lines
- Hard to test
- Hard to extend
- Mixed responsibilities

### New Architecture (`src/elliott_wave/`)
- Modular: 9 files, ~2,350 total lines
- Easy to test (dependency injection)
- Easy to extend (interfaces)
- Clear responsibilities

### Backward Compatibility
Original script updated to import from new package:

```python
# scripts/elliott_wave_analysis_new.py
from src.elliott_wave import ElliottWaveAnalyzer, ElliottWaveVisualizer

analyzer = ElliottWaveAnalyzer()
analysis_1d = analyzer.analyze(df_1d, timeframe='1d')
analysis_4h = analyzer.analyze(df_4h, timeframe='4h')

visualizer = ElliottWaveVisualizer(symbol='BTCUSDT')
visualizer.print_report(analysis_1d, analysis_4h)
```

---

## 🛠️ Extension Points

### Add New Wave Detector

```python
from src.elliott_wave import WaveDetectorInterface

class MyCustomDetector(WaveDetectorInterface):
    def detect_pivots(self, df):
        # Custom pivot detection logic
        return pivot_highs, pivot_lows
```

### Add New Pattern Analyzer

```python
from src.elliott_wave import PatternAnalyzerInterface

class MyCustomAnalyzer(PatternAnalyzerInterface):
    def analyze(self, df, pivot_highs, pivot_lows):
        # Custom wave counting logic
        return wave_pattern
```

### Add New Indicator

```python
from src.elliott_wave import IndicatorInterface

class MyCustomIndicator(IndicatorInterface):
    def calculate(self, df):
        # Custom indicator logic
        return indicator_value
```

---

## 📚 References

### Elliott Wave Theory
- Original work by Ralph Nelson Elliott
- Impulsive waves: 5-wave structures (1-2-3-4-5)
- Corrective waves: 3-wave structures (A-B-C)
- Fibonacci relationships between waves

### Design Patterns
- Strategy Pattern (Gang of Four)
- Template Method Pattern (Gang of Four)
- Dependency Injection (Martin Fowler)

### SOLID Principles
- Robert C. Martin (Uncle Bob)
- Clean Architecture
- Agile Software Development

---

## ✅ Success Criteria

- [x] All modules < 400 lines
- [x] SOLID principles applied
- [x] Abstract interfaces for extensibility
- [x] Backward compatibility maintained
- [x] Comprehensive documentation
- [x] Design patterns implemented (Strategy, Template Method)
- [x] Type hints throughout
- [x] Detailed docstrings
- [x] Explicit error handling

---

## 🔜 Future Enhancements

1. **Additional Wave Detectors**
   - Fractal-based detection
   - Machine learning-based pivot detection

2. **Advanced Pattern Recognition**
   - Triangle patterns
   - Diagonal triangles
   - Complex corrections

3. **More Indicators**
   - Stochastic RSI
   - Bollinger Bands
   - Volume Profile

4. **Backtesting Integration**
   - Integration with backtesting engine
   - Strategy performance metrics

5. **Visualization**
   - Chart plotting with matplotlib
   - Interactive charts with plotly

6. **Real-time Analysis**
   - WebSocket integration
   - Live wave tracking

---

## 👥 Contributing

When extending this package:

1. Follow SOLID principles
2. Keep modules < 400 lines
3. Use type hints
4. Write comprehensive docstrings
5. Add unit tests
6. Update this REQUIREMENTS.md

---

## 📝 Version History

**1.0.0** (2025-11-15)
- Initial modular refactoring from monolithic script
- 9 core modules
- SOLID principles throughout
- Strategy Pattern for extensibility
- Template Method for wave counting
- Comprehensive documentation

---

**End of Requirements Document**
