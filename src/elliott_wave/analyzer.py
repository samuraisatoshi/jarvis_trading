"""
Main Elliott Wave analyzer orchestrator.

This module coordinates all Elliott Wave components to perform complete analysis.
Simplified from original 200+ lines by delegating to specialized modules.

SOLID Principles:
- Single Responsibility: Orchestration only (no business logic)
- Dependency Inversion: Depends on abstractions
- Open/Closed: Extensible through component injection
"""

from typing import Optional
import pandas as pd
import logging
from datetime import datetime

from .models import WaveAnalysis, PivotPoint
from .wave_detector import PivotDetector, WaveDetectorInterface
from .pattern_analyzer import ElliottWaveCounter, PatternAnalyzerInterface
from .fibonacci_calculator import FibonacciCalculator
from .indicator_engine import IndicatorEngine
from .signal_generator import (ElliottWaveSignalGenerator,
                               SignalGeneratorInterface)

logger = logging.getLogger(__name__)


class ElliottWaveAnalyzer:
    """
    Main orchestrator for Elliott Wave analysis.

    Coordinates all components to perform comprehensive analysis.
    Significantly simplified from original by delegating to specialized modules.
    """

    def __init__(self,
                 wave_detector: Optional[WaveDetectorInterface] = None,
                 pattern_analyzer: Optional[PatternAnalyzerInterface] = None,
                 signal_generator: Optional[SignalGeneratorInterface] = None):
        """
        Initialize analyzer with pluggable components.

        Args:
            wave_detector: Wave detection strategy (default: PivotDetector)
            pattern_analyzer: Pattern analysis strategy (default: ElliottWaveCounter)
            signal_generator: Signal generation strategy (default: ElliottWaveSignalGenerator)
        """
        # Dependency Injection: Use provided or default implementations
        self.wave_detector = wave_detector or PivotDetector(window=5)
        self.pattern_analyzer = pattern_analyzer or ElliottWaveCounter()
        self.fib_calculator = FibonacciCalculator()
        self.indicator_engine = IndicatorEngine()
        self.signal_generator = signal_generator or ElliottWaveSignalGenerator()

        logger.info("ElliottWaveAnalyzer initialized with components")

    def analyze(self, df: pd.DataFrame, timeframe: str = '1d'
               ) -> WaveAnalysis:
        """
        Perform complete Elliott Wave analysis on DataFrame.

        This is the main public API - delegates to specialized components.

        Args:
            df: DataFrame with OHLCV data and datetime index
            timeframe: Timeframe identifier (e.g., '1d', '4h')

        Returns:
            WaveAnalysis with complete analysis results

        Raises:
            ValueError: If DataFrame is invalid or missing required columns
        """
        logger.info(f"Starting Elliott Wave analysis for {timeframe}")

        # Validate input
        self._validate_dataframe(df)

        current_price = df.iloc[-1]['close']

        # Step 1: Detect pivot points
        logger.debug("Detecting pivot points...")
        pivot_highs, pivot_lows = self.wave_detector.detect_pivots(df)
        logger.info(f"Detected {len(pivot_highs)} highs, {len(pivot_lows)} lows")

        # Step 2: Analyze wave pattern
        logger.debug("Analyzing wave pattern...")
        wave_pattern = self.pattern_analyzer.analyze(df, pivot_highs, pivot_lows)
        logger.info(f"Identified: {wave_pattern.wave_type.value} "
                   f"Wave {wave_pattern.current_wave.value} "
                   f"(confidence: {wave_pattern.confidence:.1f}%)")

        # Step 3: Calculate Fibonacci levels
        logger.debug("Calculating Fibonacci levels...")
        fib_levels = self._calculate_fibonacci(df, pivot_highs, pivot_lows,
                                               current_price)

        # Step 4: Calculate technical indicators
        logger.debug("Calculating technical indicators...")
        indicators = self.indicator_engine.calculate_all(df)
        logger.info(f"RSI: {indicators.rsi:.2f}, "
                   f"Momentum: {indicators.momentum.value}")

        # Step 5: Generate trading signal
        logger.debug("Generating trading signal...")
        signal = self.signal_generator.generate(wave_pattern, indicators,
                                                fib_levels, current_price)
        logger.info(f"Signal: {signal.action.value} "
                   f"(confidence: {signal.confidence:.1f}%)")

        # Step 6: Aggregate into WaveAnalysis
        analysis = WaveAnalysis(
            timeframe=timeframe,
            current_price=current_price,
            wave_pattern=wave_pattern,
            fibonacci_levels=fib_levels,
            indicators=indicators,
            signal=signal,
            pivot_highs=pivot_highs[-5:],  # Last 5 highs
            pivot_lows=pivot_lows[-5:],    # Last 5 lows
            timestamp=datetime.utcnow().isoformat()
        )

        logger.info(f"Analysis complete for {timeframe}")
        return analysis

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        Validate DataFrame has required structure.

        Args:
            df: DataFrame to validate

        Raises:
            ValueError: If DataFrame is invalid
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_columns if col not in df.columns]

        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")

        if len(df) < 50:
            raise ValueError(f"DataFrame too short ({len(df)} bars). "
                           f"Need at least 50 bars for analysis")

        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")

    def _calculate_fibonacci(self, df: pd.DataFrame,
                            pivot_highs: list[PivotPoint],
                            pivot_lows: list[PivotPoint],
                            current_price: float):
        """
        Calculate Fibonacci levels from recent pivots.

        Args:
            df: DataFrame with price data
            pivot_highs: Pivot high points
            pivot_lows: Pivot low points
            current_price: Current price

        Returns:
            FibonacciLevels
        """
        if len(pivot_highs) > 0 and len(pivot_lows) > 0:
            # Get recent swing high and low
            recent_high = max(p.price for p in pivot_highs[-3:])
            recent_low = min(p.price for p in pivot_lows[-3:])
            return self.fib_calculator.calculate_levels(recent_low, recent_high)
        else:
            # Fallback: Use price range
            logger.warning("Insufficient pivots, using price range for Fibonacci")
            return self.fib_calculator.calculate_levels(
                current_price * 0.9,
                current_price
            )

    def configure_wave_detector(self, detector: WaveDetectorInterface) -> None:
        """
        Replace wave detector strategy.

        Args:
            detector: New wave detector implementation
        """
        self.wave_detector = detector
        logger.info(f"Wave detector configured: {type(detector).__name__}")

    def configure_pattern_analyzer(self, analyzer: PatternAnalyzerInterface
                                  ) -> None:
        """
        Replace pattern analyzer strategy.

        Args:
            analyzer: New pattern analyzer implementation
        """
        self.pattern_analyzer = analyzer
        logger.info(f"Pattern analyzer configured: {type(analyzer).__name__}")

    def configure_signal_generator(self, generator: SignalGeneratorInterface
                                  ) -> None:
        """
        Replace signal generator strategy.

        Args:
            generator: New signal generator implementation
        """
        self.signal_generator = generator
        logger.info(f"Signal generator configured: {type(generator).__name__}")
