"""
Elliott Wave Analysis Package

A modular, extensible framework for Elliott Wave analysis of cryptocurrency markets.
Implements SOLID principles and design patterns for maintainability and extensibility.

Main Components:
- ElliottWaveAnalyzer: Main orchestrator
- WaveDetectors: Pivot/swing detection (Strategy Pattern)
- PatternAnalyzers: Wave counting algorithms (Template Method)
- FibonacciCalculator: Retracement/extension calculations
- IndicatorEngine: Technical indicators for confirmation
- SignalGenerator: Trading signal generation with risk management
- ElliottWaveVisualizer: Report generation

Example Usage:
    >>> from src.elliott_wave import ElliottWaveAnalyzer
    >>> from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
    >>>
    >>> # Fetch data
    >>> client = BinanceRESTClient(testnet=False)
    >>> klines = client.get_klines('BTCUSDT', '1d', limit=200)
    >>> df = pd.DataFrame(klines)
    >>>
    >>> # Analyze
    >>> analyzer = ElliottWaveAnalyzer()
    >>> analysis = analyzer.analyze(df, timeframe='1d')
    >>>
    >>> # View results
    >>> print(f"Wave: {analysis.wave_pattern.current_wave.value}")
    >>> print(f"Signal: {analysis.signal.action.value}")

Version: 1.0.0
"""

__version__ = '1.0.0'

# Core models
from .models import (
    WavePattern,
    FibonacciLevels,
    TechnicalIndicators,
    TradingSignal,
    WaveAnalysis,
    PivotPoint,
    WaveType,
    WavePosition,
    SignalAction,
    MomentumType,
    VolumeTrend
)

# Wave detectors
from .wave_detector import (
    WaveDetectorInterface,
    PivotDetector,
    ZigZagDetector,
    AdaptivePivotDetector
)

# Pattern analyzers
from .pattern_analyzer import (
    PatternAnalyzerInterface,
    ElliottWaveCounter,
    ImpulsiveWaveAnalyzer,
    CorrectiveWaveAnalyzer
)

# Fibonacci calculator
from .fibonacci_calculator import FibonacciCalculator

# Indicator engine
from .indicator_engine import (
    IndicatorInterface,
    RSIIndicator,
    MACDIndicator,
    VolumeAnalyzer,
    MomentumAnalyzer,
    IndicatorEngine
)

# Signal generator
from .signal_generator import (
    SignalGeneratorInterface,
    ElliottWaveSignalGenerator,
    MultiTimeframeSignalAggregator
)

# Main analyzer
from .analyzer import ElliottWaveAnalyzer

# Visualizer
from .visualizer import (
    ElliottWaveVisualizer,
    SingleTimeframeVisualizer
)

# Public API
__all__ = [
    # Main entry point
    'ElliottWaveAnalyzer',

    # Models
    'WavePattern',
    'FibonacciLevels',
    'TechnicalIndicators',
    'TradingSignal',
    'WaveAnalysis',
    'PivotPoint',
    'WaveType',
    'WavePosition',
    'SignalAction',
    'MomentumType',
    'VolumeTrend',

    # Wave Detectors
    'WaveDetectorInterface',
    'PivotDetector',
    'ZigZagDetector',
    'AdaptivePivotDetector',

    # Pattern Analyzers
    'PatternAnalyzerInterface',
    'ElliottWaveCounter',
    'ImpulsiveWaveAnalyzer',
    'CorrectiveWaveAnalyzer',

    # Calculators
    'FibonacciCalculator',

    # Indicators
    'IndicatorInterface',
    'RSIIndicator',
    'MACDIndicator',
    'VolumeAnalyzer',
    'MomentumAnalyzer',
    'IndicatorEngine',

    # Signal Generation
    'SignalGeneratorInterface',
    'ElliottWaveSignalGenerator',
    'MultiTimeframeSignalAggregator',

    # Visualization
    'ElliottWaveVisualizer',
    'SingleTimeframeVisualizer',
]
