"""
Trading signal generation from Elliott Wave analysis.

This module generates actionable trading signals with complete risk management
based on Elliott Wave patterns and technical indicators.

SOLID Principles:
- Single Responsibility: Focus only on signal generation
- Open/Closed: Extendable for different signal strategies
- Dependency Inversion: Depends on abstractions (models)
- Interface Segregation: Clean signal generation interface
"""

from typing import Dict, Optional
from .models import (TradingSignal, WavePattern, TechnicalIndicators,
                    FibonacciLevels, SignalAction, WaveType, WavePosition,
                    MomentumType)


class SignalGeneratorInterface:
    """Abstract interface for signal generators."""

    def generate(self, wave_pattern: WavePattern,
                indicators: TechnicalIndicators,
                fib_levels: FibonacciLevels,
                current_price: float) -> TradingSignal:
        """
        Generate trading signal.

        Args:
            wave_pattern: Identified wave pattern
            indicators: Technical indicators
            fib_levels: Fibonacci levels
            current_price: Current market price

        Returns:
            TradingSignal with action and risk management
        """
        raise NotImplementedError


class ElliottWaveSignalGenerator(SignalGeneratorInterface):
    """
    Main signal generator based on Elliott Wave principles.

    Combines wave position, indicators, and Fibonacci levels
    to generate high-probability trading signals.
    """

    def __init__(self, min_confidence: float = 50.0,
                 min_risk_reward: float = 1.5):
        """
        Initialize signal generator.

        Args:
            min_confidence: Minimum confidence for actionable signals
            min_risk_reward: Minimum risk/reward ratio
        """
        self.min_confidence = min_confidence
        self.min_risk_reward = min_risk_reward

    def generate(self, wave_pattern: WavePattern,
                indicators: TechnicalIndicators,
                fib_levels: FibonacciLevels,
                current_price: float) -> TradingSignal:
        """
        Generate trading signal from wave analysis.

        Logic:
        - Wave C (corrective): Look for buy opportunity
        - Wave 5 (impulsive): Look for sell opportunity
        - Wave 1/3 (impulsive): Look for buy continuation
        - Wave 2/4 (impulsive): Wait for correction to complete

        Args:
            wave_pattern: Wave pattern
            indicators: Technical indicators
            fib_levels: Fibonacci levels
            current_price: Current price

        Returns:
            TradingSignal
        """
        # Route to specialized signal logic
        if wave_pattern.wave_type == WaveType.CORRECTIVE:
            return self._generate_corrective_signal(
                wave_pattern, indicators, fib_levels, current_price
            )
        elif wave_pattern.wave_type == WaveType.IMPULSIVE:
            return self._generate_impulsive_signal(
                wave_pattern, indicators, fib_levels, current_price
            )
        else:
            return self._generate_hold_signal(current_price, fib_levels,
                                              "Wave structure unclear")

    def _generate_corrective_signal(self, wave_pattern: WavePattern,
                                   indicators: TechnicalIndicators,
                                   fib_levels: FibonacciLevels,
                                   current_price: float) -> TradingSignal:
        """
        Generate signal for corrective wave patterns.

        Wave C completion often presents buy opportunities.
        """
        if wave_pattern.current_wave == WavePosition.WAVE_C:
            # End of Wave C - potential reversal
            if self._confirm_wave_c_completion(indicators):
                return self._create_buy_signal(
                    entry_price=current_price,
                    stop_loss=wave_pattern.invalidation_level or (
                        current_price * 0.98
                    ),
                    fib_levels=fib_levels,
                    confidence=70 + (40 - indicators.rsi) / 2,
                    reasoning=f"Wave C correction ending, RSI oversold at "
                             f"{indicators.rsi:.1f}, momentum turning"
                )
            else:
                return self._generate_hold_signal(
                    current_price, fib_levels,
                    "Wait for clearer Wave C completion signal"
                )
        else:
            # Wave A or B - stay on sidelines
            return self._generate_hold_signal(
                current_price, fib_levels,
                f"Wave {wave_pattern.current_wave.value} in progress, "
                f"wait for correction to complete"
            )

    def _generate_impulsive_signal(self, wave_pattern: WavePattern,
                                  indicators: TechnicalIndicators,
                                  fib_levels: FibonacciLevels,
                                  current_price: float) -> TradingSignal:
        """
        Generate signal for impulsive wave patterns.

        Different actions for different wave positions.
        """
        wave = wave_pattern.current_wave

        if wave == WavePosition.WAVE_5:
            # Wave 5 - potential exhaustion
            return self._handle_wave_5(wave_pattern, indicators, fib_levels,
                                      current_price)
        elif wave in [WavePosition.WAVE_1, WavePosition.WAVE_3]:
            # Wave 1 or 3 - strong momentum
            return self._handle_wave_1_3(wave_pattern, indicators, fib_levels,
                                        current_price)
        elif wave in [WavePosition.WAVE_2, WavePosition.WAVE_4]:
            # Wave 2 or 4 - correction
            return self._handle_wave_2_4(wave_pattern, indicators, fib_levels,
                                        current_price)
        else:
            return self._generate_hold_signal(
                current_price, fib_levels,
                "Wave position unclear"
            )

    def _handle_wave_5(self, wave_pattern: WavePattern,
                      indicators: TechnicalIndicators,
                      fib_levels: FibonacciLevels,
                      current_price: float) -> TradingSignal:
        """Handle Wave 5 signals (potential exhaustion)."""
        # Check for exhaustion signals
        if (indicators.is_overbought(70) or
            indicators.volume_trend.value == 'decreasing'):
            # Wave 5 exhaustion - potential sell
            confidence = 65
            if indicators.is_overbought(70):
                confidence += (indicators.rsi - 70) / 2

            return self._create_sell_signal(
                entry_price=current_price,
                stop_loss=current_price * 1.03,
                fib_levels=fib_levels,
                confidence=confidence,
                reasoning=f"Wave 5 likely complete, RSI overbought at "
                         f"{indicators.rsi:.1f}, volume declining"
            )
        else:
            # Wave 5 still in progress
            return self._generate_hold_signal(
                current_price, fib_levels,
                "Wave 5 in progress, monitoring for exhaustion signals",
                confidence=55
            )

    def _handle_wave_1_3(self, wave_pattern: WavePattern,
                        indicators: TechnicalIndicators,
                        fib_levels: FibonacciLevels,
                        current_price: float) -> TradingSignal:
        """Handle Wave 1/3 signals (strong momentum)."""
        if indicators.momentum == MomentumType.BULLISH:
            # Strong impulsive move - buy
            return self._create_buy_signal(
                entry_price=current_price,
                stop_loss=fib_levels.level_618,
                fib_levels=fib_levels,
                confidence=75,
                reasoning=f"Strong Wave {wave_pattern.current_wave.value} "
                         f"in progress, momentum bullish"
            )
        else:
            # Wait for momentum confirmation
            return self._generate_hold_signal(
                current_price, fib_levels,
                "Wait for momentum confirmation",
                confidence=60
            )

    def _handle_wave_2_4(self, wave_pattern: WavePattern,
                        indicators: TechnicalIndicators,
                        fib_levels: FibonacciLevels,
                        current_price: float) -> TradingSignal:
        """Handle Wave 2/4 signals (corrections within impulse)."""
        # Corrections are pullbacks - look for entry on completion
        if self._is_correction_complete(indicators):
            return self._create_buy_signal(
                entry_price=current_price,
                stop_loss=fib_levels.level_786,
                fib_levels=fib_levels,
                confidence=65,
                reasoning=f"Wave {wave_pattern.current_wave.value} "
                         f"correction completing, prepare for next impulse"
            )
        else:
            return self._generate_hold_signal(
                current_price, fib_levels,
                f"Wave {wave_pattern.current_wave.value} correction "
                f"in progress",
                confidence=50
            )

    def _confirm_wave_c_completion(self, indicators: TechnicalIndicators
                                  ) -> bool:
        """
        Check if Wave C shows completion signals.

        Args:
            indicators: Technical indicators

        Returns:
            True if Wave C appears complete
        """
        return (indicators.is_oversold(40) and
                indicators.momentum != MomentumType.BEARISH)

    def _is_correction_complete(self, indicators: TechnicalIndicators) -> bool:
        """
        Check if correction (Wave 2/4) appears complete.

        Args:
            indicators: Technical indicators

        Returns:
            True if correction appears complete
        """
        return (indicators.momentum == MomentumType.BULLISH or
                indicators.has_bullish_macd())

    def _create_buy_signal(self, entry_price: float, stop_loss: float,
                          fib_levels: FibonacciLevels, confidence: float,
                          reasoning: str) -> TradingSignal:
        """Create BUY signal with risk management."""
        take_profit_1 = fib_levels.level_382
        take_profit_2 = fib_levels.level_618
        take_profit_3 = fib_levels.level_1618

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit_2 - entry_price)
        risk_reward = reward / risk if risk > 0 else 0

        return TradingSignal(
            action=SignalAction.BUY,
            confidence=min(100, confidence),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            take_profit_3=take_profit_3,
            risk_reward_ratio=risk_reward,
            reasoning=reasoning
        )

    def _create_sell_signal(self, entry_price: float, stop_loss: float,
                           fib_levels: FibonacciLevels, confidence: float,
                           reasoning: str) -> TradingSignal:
        """Create SELL signal with risk management."""
        take_profit_1 = fib_levels.level_382
        take_profit_2 = fib_levels.level_618
        take_profit_3 = fib_levels.level_786

        risk = abs(entry_price - stop_loss)
        reward = abs(entry_price - take_profit_2)
        risk_reward = reward / risk if risk > 0 else 0

        return TradingSignal(
            action=SignalAction.SELL,
            confidence=min(100, confidence),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            take_profit_3=take_profit_3,
            risk_reward_ratio=risk_reward,
            reasoning=reasoning
        )

    def _generate_hold_signal(self, current_price: float,
                             fib_levels: FibonacciLevels,
                             reasoning: str,
                             confidence: float = 40) -> TradingSignal:
        """Create HOLD signal."""
        return TradingSignal(
            action=SignalAction.HOLD,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=fib_levels.level_786,
            take_profit_1=current_price * 1.05,
            take_profit_2=current_price * 1.10,
            take_profit_3=current_price * 1.15,
            risk_reward_ratio=0,
            reasoning=reasoning
        )


class MultiTimeframeSignalAggregator:
    """
    Aggregate signals from multiple timeframes.

    Combines signals from different timeframes (e.g., 1D + 4H)
    to generate higher-confidence composite signals.
    """

    def __init__(self, primary_weight: float = 0.6,
                 secondary_weight: float = 0.4):
        """
        Initialize aggregator.

        Args:
            primary_weight: Weight for primary timeframe (e.g., 1D)
            secondary_weight: Weight for secondary timeframe (e.g., 4H)
        """
        self.primary_weight = primary_weight
        self.secondary_weight = secondary_weight

    def aggregate(self, primary_signal: TradingSignal,
                 secondary_signal: TradingSignal) -> Dict:
        """
        Aggregate two signals into composite recommendation.

        Args:
            primary_signal: Signal from primary timeframe
            secondary_signal: Signal from secondary timeframe

        Returns:
            Dict with aggregated signal information
        """
        # Check for alignment
        aligned = primary_signal.action == secondary_signal.action

        if aligned:
            # Both agree - high confidence
            final_action = primary_signal.action
            final_confidence = (
                primary_signal.confidence * self.primary_weight +
                secondary_signal.confidence * self.secondary_weight
            )
            reasoning = f"Both timeframes agree: {final_action.value}"
        else:
            # Conflict - HOLD and wait
            final_action = SignalAction.HOLD
            final_confidence = 40
            reasoning = (f"Timeframes conflict: Primary={primary_signal.action.value}, "
                        f"Secondary={secondary_signal.action.value}")

        return {
            'final_action': final_action,
            'final_confidence': final_confidence,
            'aligned': aligned,
            'reasoning': reasoning,
            'primary_signal': primary_signal,
            'secondary_signal': secondary_signal
        }
