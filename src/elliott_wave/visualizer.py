"""
Visualization and reporting for Elliott Wave analysis.

This module generates formatted reports for console and file output.
Follows patterns from src/backtesting/visualizer.py

SOLID Principles:
- Single Responsibility: Focus only on output formatting
- Open/Closed: Extendable for new output formats
- Dependency Inversion: Depends on model abstractions
"""

from typing import Dict, Optional
from datetime import datetime
from .models import WaveAnalysis


class ElliottWaveVisualizer:
    """
    Visualizer for Elliott Wave analysis results.

    Generates formatted reports for console and file output.
    """

    def __init__(self, symbol: str = 'BTCUSDT'):
        """
        Initialize visualizer.

        Args:
            symbol: Trading symbol for reports
        """
        self.symbol = symbol

    def generate_report(self, analysis_1d: WaveAnalysis,
                       analysis_4h: WaveAnalysis) -> str:
        """
        Generate comprehensive multi-timeframe report.

        Args:
            analysis_1d: 1D timeframe analysis
            analysis_4h: 4H timeframe analysis

        Returns:
            Formatted report string
        """
        lines = []

        # Header
        lines.extend(self._generate_header())

        # 1D Analysis
        lines.extend(self._generate_timeframe_section(analysis_1d, "MACRO"))

        # 4H Analysis
        lines.extend(self._generate_timeframe_section(analysis_4h, "MICRO"))

        # Multi-timeframe comparison
        lines.extend(self._generate_comparison_section(analysis_1d, analysis_4h))

        # Trading signals
        lines.extend(self._generate_signal_section(analysis_1d, analysis_4h))

        # Risk management
        lines.extend(self._generate_risk_section(analysis_4h))

        # Footer
        lines.extend(self._generate_footer())

        return '\n'.join(lines)

    def _generate_header(self) -> list[str]:
        """Generate report header."""
        return [
            "",
            "=" * 80,
            f"ELLIOTT WAVE ANALYSIS - {self.symbol}",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "=" * 80,
            ""
        ]

    def _generate_timeframe_section(self, analysis: WaveAnalysis,
                                   label: str) -> list[str]:
        """
        Generate section for single timeframe.

        Args:
            analysis: WaveAnalysis for the timeframe
            label: Label for section (MACRO/MICRO)

        Returns:
            List of formatted lines
        """
        lines = [
            "-" * 80,
            f"TIMEFRAME: {analysis.timeframe.upper()} ({label} STRUCTURE)",
            "-" * 80,
            ""
        ]

        # Current price
        lines.append(f"Current Price: ${analysis.current_price:,.2f}\n")

        # Wave analysis
        wp = analysis.wave_pattern
        lines.extend([
            "Wave Analysis:",
            f"  Wave Type: {wp.wave_type.value.upper()}",
            f"  Current Wave: {wp.current_wave.value}",
            f"  Confidence: {wp.confidence:.1f}%",
            f"  Wave Start: ${wp.start_price:,.2f}"
        ])

        if wp.projected_target:
            lines.append(f"  Projected Target: ${wp.projected_target:,.2f}")

        if wp.invalidation_level:
            lines.append(f"  Invalidation Level: ${wp.invalidation_level:,.2f}")

        lines.append("")

        # Fibonacci levels
        fib = analysis.fibonacci_levels
        lines.extend([
            "Fibonacci Levels:",
            f"  0.0%   (Low):    ${fib.level_0:,.2f}",
            f"  23.6%:           ${fib.level_236:,.2f}",
            f"  38.2%:           ${fib.level_382:,.2f}",
            f"  50.0%:           ${fib.level_500:,.2f}",
            f"  61.8% (Golden):  ${fib.level_618:,.2f}",
            f"  78.6%:           ${fib.level_786:,.2f}",
            f"  100% (High):     ${fib.level_100:,.2f}",
            f"  161.8%:          ${fib.level_1618:,.2f}",
            f"  261.8%:          ${fib.level_2618:,.2f}",
            ""
        ])

        # Technical indicators
        ind = analysis.indicators
        lines.extend([
            "Technical Indicators:",
            f"  RSI: {ind.rsi:.2f}",
            f"  MACD: {ind.macd:.2f}",
            f"  MACD Signal: {ind.macd_signal:.2f}",
            f"  MACD Histogram: {ind.macd_histogram:.2f}",
            f"  Volume Trend: {ind.volume_trend.value.upper()}",
            f"  Momentum: {ind.momentum.value.upper()}",
            ""
        ])

        return lines

    def _generate_comparison_section(self, analysis_1d: WaveAnalysis,
                                    analysis_4h: WaveAnalysis) -> list[str]:
        """
        Generate multi-timeframe comparison section.

        Args:
            analysis_1d: 1D analysis
            analysis_4h: 4H analysis

        Returns:
            List of formatted lines
        """
        lines = [
            "-" * 80,
            "MULTI-TIMEFRAME ANALYSIS",
            "-" * 80,
            ""
        ]

        # Wave type comparison
        if analysis_1d.wave_pattern.wave_type == analysis_4h.wave_pattern.wave_type:
            lines.append(
                f"  CONFIRMATION: Both timeframes show "
                f"{analysis_1d.wave_pattern.wave_type.value.upper()} structure"
            )
        else:
            lines.append(
                f"  DIVERGENCE: 1D shows "
                f"{analysis_1d.wave_pattern.wave_type.value.upper()}, "
                f"4H shows {analysis_4h.wave_pattern.wave_type.value.upper()}"
            )

        # Momentum comparison
        if analysis_1d.indicators.momentum == analysis_4h.indicators.momentum:
            lines.append(
                f"  MOMENTUM ALIGNED: "
                f"{analysis_1d.indicators.momentum.value.upper()} "
                f"on both timeframes"
            )
        else:
            lines.append(
                f"  MOMENTUM CONFLICT: 1D is "
                f"{analysis_1d.indicators.momentum.value.upper()}, "
                f"4H is {analysis_4h.indicators.momentum.value.upper()}"
            )

        lines.append("")
        return lines

    def _generate_signal_section(self, analysis_1d: WaveAnalysis,
                                 analysis_4h: WaveAnalysis) -> list[str]:
        """
        Generate trading signal section.

        Args:
            analysis_1d: 1D analysis
            analysis_4h: 4H analysis

        Returns:
            List of formatted lines
        """
        lines = [
            "=" * 80,
            "TRADING SIGNAL",
            "=" * 80,
            ""
        ]

        sig_1d = analysis_1d.signal
        sig_4h = analysis_4h.signal

        # Strategic (1D)
        lines.extend([
            f"Strategic Position (1D): {sig_1d.action.value}",
            f"  Confidence: {sig_1d.confidence:.1f}%",
            f"  Reasoning: {sig_1d.reasoning}",
            ""
        ])

        # Tactical (4H)
        lines.extend([
            f"Tactical Position (4H): {sig_4h.action.value}",
            f"  Confidence: {sig_4h.confidence:.1f}%",
            f"  Reasoning: {sig_4h.reasoning}",
            ""
        ])

        # Final recommendation
        lines.extend([
            "-" * 80,
            "RECOMMENDED ACTION",
            "-" * 80,
            ""
        ])

        if sig_1d.action == sig_4h.action:
            final_confidence = (sig_1d.confidence + sig_4h.confidence) / 2
            lines.extend([
                f"  ACTION: {sig_1d.action.value}",
                f"  CONFIDENCE: {final_confidence:.1f}%",
                f"  ALIGNMENT: Both timeframes agree",
                ""
            ])
        else:
            lines.extend([
                f"  ACTION: HOLD (timeframes conflict)",
                f"  WAIT FOR: Alignment between 1D and 4H signals",
                ""
            ])

        return lines

    def _generate_risk_section(self, analysis: WaveAnalysis) -> list[str]:
        """
        Generate risk management section.

        Args:
            analysis: Analysis to extract risk parameters from (typically 4H)

        Returns:
            List of formatted lines
        """
        lines = [
            "-" * 80,
            "RISK MANAGEMENT (Based on 4H for precise entry)",
            "-" * 80,
            ""
        ]

        sig = analysis.signal

        # Entry and stop
        lines.extend([
            f"  Entry Price: ${sig.entry_price:,.2f}",
            f"  Stop Loss: ${sig.stop_loss:,.2f} "
            f"({((sig.stop_loss/sig.entry_price - 1) * 100):.2f}%)",
            ""
        ])

        # Take profit levels
        lines.extend([
            "  Take Profit Levels:",
            f"    TP1: ${sig.take_profit_1:,.2f} "
            f"({((sig.take_profit_1/sig.entry_price - 1) * 100):.2f}%)",
            f"    TP2: ${sig.take_profit_2:,.2f} "
            f"({((sig.take_profit_2/sig.entry_price - 1) * 100):.2f}%)",
            f"    TP3: ${sig.take_profit_3:,.2f} "
            f"({((sig.take_profit_3/sig.entry_price - 1) * 100):.2f}%)",
            ""
        ])

        # Risk/Reward
        lines.append(f"  Risk/Reward Ratio: 1:{sig.risk_reward_ratio:.2f}")
        lines.append("")

        return lines

    def _generate_footer(self) -> list[str]:
        """Generate report footer."""
        return [
            "=" * 80,
            "DISCLAIMER: This analysis is for educational purposes only.",
            "Always do your own research and never risk more than you can afford to lose.",
            "=" * 80,
            ""
        ]

    def print_report(self, analysis_1d: WaveAnalysis,
                    analysis_4h: WaveAnalysis) -> None:
        """
        Print report to console.

        Args:
            analysis_1d: 1D timeframe analysis
            analysis_4h: 4H timeframe analysis
        """
        report = self.generate_report(analysis_1d, analysis_4h)
        print(report)

    def save_report(self, analysis_1d: WaveAnalysis,
                   analysis_4h: WaveAnalysis,
                   filepath: str) -> None:
        """
        Save report to file.

        Args:
            analysis_1d: 1D timeframe analysis
            analysis_4h: 4H timeframe analysis
            filepath: Output file path
        """
        report = self.generate_report(analysis_1d, analysis_4h)

        with open(filepath, 'w') as f:
            f.write(report)


class SingleTimeframeVisualizer:
    """Visualizer for single timeframe analysis."""

    def __init__(self, symbol: str = 'BTCUSDT'):
        """
        Initialize visualizer.

        Args:
            symbol: Trading symbol
        """
        self.symbol = symbol

    def generate_report(self, analysis: WaveAnalysis) -> str:
        """
        Generate report for single timeframe.

        Args:
            analysis: WaveAnalysis

        Returns:
            Formatted report string
        """
        visualizer = ElliottWaveVisualizer(self.symbol)

        lines = []
        lines.extend(visualizer._generate_header())
        lines.extend(visualizer._generate_timeframe_section(analysis, "ANALYSIS"))

        sig = analysis.signal
        lines.extend([
            "-" * 80,
            "TRADING SIGNAL",
            "-" * 80,
            "",
            f"Action: {sig.action.value}",
            f"Confidence: {sig.confidence:.1f}%",
            f"Reasoning: {sig.reasoning}",
            "",
            f"Entry: ${sig.entry_price:,.2f}",
            f"Stop Loss: ${sig.stop_loss:,.2f}",
            f"Take Profit: ${sig.take_profit_2:,.2f}",
            f"Risk/Reward: 1:{sig.risk_reward_ratio:.2f}",
            ""
        ])

        lines.extend(visualizer._generate_footer())

        return '\n'.join(lines)
