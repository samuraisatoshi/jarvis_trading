"""
Elliott Wave pattern analysis and wave counting.

This module implements wave counting algorithms to identify current position
within Elliott Wave structures (impulsive 1-5 or corrective A-B-C).

SOLID Principles:
- Single Responsibility: Focus only on pattern recognition
- Open/Closed: Extendable through PatternAnalyzerInterface
- Liskov Substitution: Analyzers are interchangeable
- Template Method: Common analysis flow with specialized steps

Design Pattern: Template Method + Strategy Pattern
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import pandas as pd
from .models import (WavePattern, PivotPoint, WaveType, WavePosition,
                    FibonacciLevels)


class PatternAnalyzerInterface(ABC):
    """Abstract interface for wave pattern analyzers."""

    @abstractmethod
    def analyze(self, df: pd.DataFrame, pivot_highs: List[PivotPoint],
                pivot_lows: List[PivotPoint]) -> WavePattern:
        """
        Analyze wave pattern from pivot points.

        Args:
            df: DataFrame with OHLCV data
            pivot_highs: List of pivot highs
            pivot_lows: List of pivot lows

        Returns:
            Identified WavePattern
        """
        pass


class ElliottWaveCounter(PatternAnalyzerInterface):
    """
    Main Elliott Wave counting algorithm.

    Template Method pattern: Defines skeleton of wave counting algorithm.
    Subclasses specialize specific wave types (impulsive/corrective).
    """

    def __init__(self, min_confidence: float = 40.0):
        """
        Initialize wave counter.

        Args:
            min_confidence: Minimum confidence for valid patterns
        """
        self.min_confidence = min_confidence

    def analyze(self, df: pd.DataFrame, pivot_highs: List[PivotPoint],
                pivot_lows: List[PivotPoint]) -> WavePattern:
        """
        Main template method for wave analysis.

        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Pivot highs
            pivot_lows: Pivot lows

        Returns:
            Identified WavePattern
        """
        current_price = df.iloc[-1]['close']

        # Step 1: Validate inputs
        if not self._validate_pivots(pivot_highs, pivot_lows):
            return self._create_unknown_pattern(current_price)

        # Step 2: Merge and sort pivots
        all_pivots = self._merge_pivots(pivot_highs, pivot_lows)

        # Step 3: Determine trend
        trend = self._determine_trend(all_pivots, current_price)

        # Step 4: Extract recent pivot sequence
        recent_pivots = self._get_recent_pivots(all_pivots)

        # Step 5: Identify wave type (impulsive or corrective)
        wave_type = self._identify_wave_type(recent_pivots, trend)

        # Step 6: Count waves and determine position
        if wave_type == WaveType.IMPULSIVE:
            wave_position, confidence = self._count_impulsive_waves(
                recent_pivots, trend
            )
        elif wave_type == WaveType.CORRECTIVE:
            wave_position, confidence = self._count_corrective_waves(
                recent_pivots, trend
            )
        else:
            return self._create_unknown_pattern(current_price)

        # Step 7: Calculate projection and invalidation
        projected_target = self._calculate_projection(
            recent_pivots, wave_type, wave_position, trend
        )
        invalidation_level = self._calculate_invalidation(
            recent_pivots, wave_type, wave_position
        )

        return WavePattern(
            wave_type=wave_type,
            current_wave=wave_position,
            confidence=confidence,
            start_price=recent_pivots[0]['price'],
            current_price=current_price,
            projected_target=projected_target,
            invalidation_level=invalidation_level
        )

    def _validate_pivots(self, pivot_highs: List[PivotPoint],
                        pivot_lows: List[PivotPoint]) -> bool:
        """Validate that we have enough pivots for analysis."""
        return len(pivot_highs) >= 2 and len(pivot_lows) >= 2

    def _merge_pivots(self, pivot_highs: List[PivotPoint],
                     pivot_lows: List[PivotPoint]) -> List[Dict]:
        """Merge and sort pivots chronologically."""
        all_pivots = []

        for p in pivot_highs:
            all_pivots.append({
                'price': p.price,
                'type': 'high',
                'timestamp': p.timestamp,
                'index': p.index
            })

        for p in pivot_lows:
            all_pivots.append({
                'price': p.price,
                'type': 'low',
                'timestamp': p.timestamp,
                'index': p.index
            })

        all_pivots.sort(key=lambda x: x['index'])
        return all_pivots

    def _determine_trend(self, pivots: List[Dict], current_price: float
                        ) -> str:
        """
        Determine overall trend direction.

        Args:
            pivots: Sorted pivot list
            current_price: Current market price

        Returns:
            'bullish' or 'bearish'
        """
        if len(pivots) < 2:
            return 'bullish'

        # Compare first and last significant pivots
        first_price = pivots[0]['price']
        last_price = pivots[-1]['price']

        # Also consider current price
        if current_price > first_price:
            return 'bullish'
        else:
            return 'bearish'

    def _get_recent_pivots(self, pivots: List[Dict],
                          lookback: int = 8) -> List[Dict]:
        """Extract most recent pivots for analysis."""
        return pivots[-lookback:] if len(pivots) > lookback else pivots

    def _identify_wave_type(self, pivots: List[Dict], trend: str) -> WaveType:
        """
        Identify if structure is impulsive or corrective.

        Impulsive: 5-wave structure in trend direction
        Corrective: 3-wave structure against trend

        Args:
            pivots: Recent pivot list
            trend: Current trend direction

        Returns:
            WaveType enum
        """
        if len(pivots) < 3:
            return WaveType.UNKNOWN

        # Count moves in trend direction
        trend_moves = 0
        counter_moves = 0

        for i in range(1, len(pivots)):
            prev_price = pivots[i-1]['price']
            curr_price = pivots[i]['price']

            if trend == 'bullish':
                if curr_price > prev_price:
                    trend_moves += 1
                else:
                    counter_moves += 1
            else:  # bearish
                if curr_price < prev_price:
                    trend_moves += 1
                else:
                    counter_moves += 1

        # Impulsive: more moves in trend direction
        # Corrective: more moves against trend
        if trend_moves > counter_moves:
            return WaveType.IMPULSIVE
        else:
            return WaveType.CORRECTIVE

    def _count_impulsive_waves(self, pivots: List[Dict], trend: str
                               ) -> tuple[WavePosition, float]:
        """
        Count position in 5-wave impulsive structure.

        Args:
            pivots: Recent pivot list
            trend: Trend direction

        Returns:
            Tuple of (WavePosition, confidence)
        """
        # Count alternating moves
        moves = []
        for i in range(1, len(pivots)):
            moves.append(pivots[i]['price'] - pivots[i-1]['price'])

        # In bullish trend: positive moves are impulse waves
        # In bearish trend: negative moves are impulse waves
        impulse_count = 0
        for move in moves:
            if (trend == 'bullish' and move > 0) or \
               (trend == 'bearish' and move < 0):
                impulse_count += 1

        # Map count to wave position
        wave_mapping = {
            1: WavePosition.WAVE_1,
            2: WavePosition.WAVE_3,
            3: WavePosition.WAVE_5
        }

        wave = wave_mapping.get(impulse_count, WavePosition.WAVE_3)

        # Calculate confidence based on structure clarity
        confidence = min(100, 40 + len(pivots) * 5 + impulse_count * 10)

        return wave, confidence

    def _count_corrective_waves(self, pivots: List[Dict], trend: str
                                ) -> tuple[WavePosition, float]:
        """
        Count position in ABC corrective structure.

        Args:
            pivots: Recent pivot list
            trend: Trend direction

        Returns:
            Tuple of (WavePosition, confidence)
        """
        # Corrective waves move against trend
        counter_moves = 0
        for i in range(1, len(pivots)):
            move = pivots[i]['price'] - pivots[i-1]['price']
            if (trend == 'bullish' and move < 0) or \
               (trend == 'bearish' and move > 0):
                counter_moves += 1

        # Simple ABC counting
        if counter_moves >= 3:
            wave = WavePosition.WAVE_C
            confidence = 60
        elif counter_moves >= 2:
            wave = WavePosition.WAVE_B
            confidence = 50
        else:
            wave = WavePosition.WAVE_A
            confidence = 40

        return wave, confidence

    def _calculate_projection(self, pivots: List[Dict], wave_type: WaveType,
                             wave_position: WavePosition, trend: str
                             ) -> Optional[float]:
        """
        Calculate projected price target.

        Uses Fibonacci extensions and wave relationships.

        Args:
            pivots: Pivot list
            wave_type: Impulsive or corrective
            wave_position: Current wave position
            trend: Trend direction

        Returns:
            Projected target price or None
        """
        if len(pivots) < 2:
            return None

        # Get recent swing
        recent_high = max(p['price'] for p in pivots[-3:])
        recent_low = min(p['price'] for p in pivots[-3:])

        # Simple projection using Fibonacci 1.618
        if wave_type == WaveType.IMPULSIVE:
            if trend == 'bullish':
                return recent_low + (recent_high - recent_low) * 1.618
            else:
                return recent_high - (recent_high - recent_low) * 1.618
        else:  # Corrective
            if trend == 'bullish':
                # Correction down, project next high
                return recent_high + (recent_high - recent_low) * 0.618
            else:
                # Correction up, project next low
                return recent_low - (recent_high - recent_low) * 0.618

    def _calculate_invalidation(self, pivots: List[Dict],
                               wave_type: WaveType,
                               wave_position: WavePosition) -> float:
        """
        Calculate pattern invalidation level.

        Args:
            pivots: Pivot list
            wave_type: Wave type
            wave_position: Wave position

        Returns:
            Invalidation price level
        """
        # Use recent swing low/high as invalidation
        if len(pivots) >= 3:
            recent_prices = [p['price'] for p in pivots[-3:]]
            return min(recent_prices)
        else:
            return pivots[0]['price'] * 0.95

    def _create_unknown_pattern(self, current_price: float) -> WavePattern:
        """Create unknown/insufficient data pattern."""
        return WavePattern(
            wave_type=WaveType.UNKNOWN,
            current_wave=WavePosition.UNKNOWN,
            confidence=0,
            start_price=current_price,
            current_price=current_price,
            projected_target=None,
            invalidation_level=current_price * 0.95
        )


class ImpulsiveWaveAnalyzer(PatternAnalyzerInterface):
    """
    Specialized analyzer for impulsive wave structures.

    Focuses on identifying and validating 5-wave structures.
    """

    def __init__(self):
        """Initialize impulsive wave analyzer."""
        self.base_counter = ElliottWaveCounter()

    def analyze(self, df: pd.DataFrame, pivot_highs: List[PivotPoint],
                pivot_lows: List[PivotPoint]) -> WavePattern:
        """
        Analyze for impulsive wave pattern.

        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Pivot highs
            pivot_lows: Pivot lows

        Returns:
            WavePattern (IMPULSIVE or UNKNOWN)
        """
        pattern = self.base_counter.analyze(df, pivot_highs, pivot_lows)

        # Only return if impulsive, otherwise mark unknown
        if pattern.wave_type == WaveType.IMPULSIVE:
            # Additional impulsive wave validation could go here
            return pattern
        else:
            return self.base_counter._create_unknown_pattern(
                df.iloc[-1]['close']
            )


class CorrectiveWaveAnalyzer(PatternAnalyzerInterface):
    """
    Specialized analyzer for corrective wave structures.

    Focuses on identifying and validating ABC corrections.
    """

    def __init__(self):
        """Initialize corrective wave analyzer."""
        self.base_counter = ElliottWaveCounter()

    def analyze(self, df: pd.DataFrame, pivot_highs: List[PivotPoint],
                pivot_lows: List[PivotPoint]) -> WavePattern:
        """
        Analyze for corrective wave pattern.

        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Pivot highs
            pivot_lows: Pivot lows

        Returns:
            WavePattern (CORRECTIVE or UNKNOWN)
        """
        pattern = self.base_counter.analyze(df, pivot_highs, pivot_lows)

        # Only return if corrective
        if pattern.wave_type == WaveType.CORRECTIVE:
            return pattern
        else:
            return self.base_counter._create_unknown_pattern(
                df.iloc[-1]['close']
            )
