#!/usr/bin/env python3
"""
Elliott Wave Analysis for BTC/USDT

Performs comprehensive Elliott Wave analysis across multiple timeframes (4H, 1D)
to identify:
- Current wave position (1-5 impulsive, ABC corrective)
- Key support/resistance levels
- Fibonacci retracements
- Entry/exit signals
- Risk management levels

This script is EXPLICIT in error handling - NO silent failures or mock data.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from dataclasses import dataclass
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class WavePattern:
    """Elliott Wave pattern identification"""
    wave_type: str  # 'impulsive' or 'corrective'
    current_wave: str  # '1', '2', '3', '4', '5', 'A', 'B', 'C'
    confidence: float  # 0-100%
    start_price: float
    current_price: float
    projected_target: Optional[float]
    invalidation_level: float


@dataclass
class FibonacciLevels:
    """Fibonacci retracement/extension levels"""
    level_0: float  # 0%
    level_236: float  # 23.6%
    level_382: float  # 38.2%
    level_500: float  # 50%
    level_618: float  # 61.8%
    level_786: float  # 78.6%
    level_100: float  # 100%
    level_1618: float  # 161.8%
    level_2618: float  # 261.8%


@dataclass
class TechnicalIndicators:
    """Technical indicators for wave confirmation"""
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    volume_trend: str  # 'increasing', 'decreasing', 'neutral'
    momentum: str  # 'bullish', 'bearish', 'neutral'


@dataclass
class TradingSignal:
    """Trading signal with risk management"""
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-100%
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward_ratio: float
    reasoning: str


class ElliottWaveAnalyzer:
    """
    Elliott Wave analyzer for cryptocurrency markets.

    Implements:
    - Pivot point detection (high/low swings)
    - Wave counting algorithms
    - Fibonacci retracement/extension calculations
    - Technical indicator confirmation
    - Multi-timeframe analysis
    """

    def __init__(self, client: BinanceRESTClient):
        """
        Initialize Elliott Wave analyzer.

        Args:
            client: Binance REST client for data fetching
        """
        self.client = client

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """
        Fetch candlestick data from Binance.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            timeframe: Candle timeframe (4h, 1d)
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data

        Raises:
            RuntimeError: If data fetch fails
        """
        logger.info(f"Fetching {limit} candles for {symbol} {timeframe}")

        try:
            klines = self.client.get_klines(symbol, timeframe, limit=limit)

            if not klines:
                raise RuntimeError(f"No data returned from Binance for {symbol} {timeframe}")

            df = pd.DataFrame(klines)
            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
            df.set_index('timestamp', inplace=True)

            logger.info(f"Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch candles: {e}", exc_info=True)
            raise RuntimeError(f"Data fetch failed: {e}") from e

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_histogram = macd - macd_signal
        return macd, macd_signal, macd_histogram

    def detect_pivots(self, df: pd.DataFrame, window: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """
        Detect pivot highs and lows (swing points).

        Args:
            df: DataFrame with OHLCV data
            window: Number of bars on each side to confirm pivot

        Returns:
            Tuple of (pivot_highs, pivot_lows)
        """
        highs = []
        lows = []

        for i in range(window, len(df) - window):
            # Pivot high: current high is higher than window bars on both sides
            if all(df.iloc[i]['high'] >= df.iloc[i-j]['high'] for j in range(1, window+1)) and \
               all(df.iloc[i]['high'] >= df.iloc[i+j]['high'] for j in range(1, window+1)):
                highs.append({
                    'index': i,
                    'timestamp': df.index[i],
                    'price': df.iloc[i]['high']
                })

            # Pivot low: current low is lower than window bars on both sides
            if all(df.iloc[i]['low'] <= df.iloc[i-j]['low'] for j in range(1, window+1)) and \
               all(df.iloc[i]['low'] <= df.iloc[i+j]['low'] for j in range(1, window+1)):
                lows.append({
                    'index': i,
                    'timestamp': df.index[i],
                    'price': df.iloc[i]['low']
                })

        logger.info(f"Detected {len(highs)} pivot highs and {len(lows)} pivot lows")
        return highs, lows

    def calculate_fibonacci_levels(self, start_price: float, end_price: float) -> FibonacciLevels:
        """
        Calculate Fibonacci retracement and extension levels.

        Args:
            start_price: Starting price (wave start)
            end_price: Ending price (wave end)

        Returns:
            FibonacciLevels object with all levels
        """
        diff = end_price - start_price

        return FibonacciLevels(
            level_0=start_price,
            level_236=end_price - diff * 0.236,
            level_382=end_price - diff * 0.382,
            level_500=end_price - diff * 0.500,
            level_618=end_price - diff * 0.618,
            level_786=end_price - diff * 0.786,
            level_100=end_price,
            level_1618=start_price + diff * 1.618,
            level_2618=start_price + diff * 2.618
        )

    def identify_wave_pattern(self, df: pd.DataFrame, pivots_high: List[Dict], pivots_low: List[Dict]) -> WavePattern:
        """
        Identify Elliott Wave pattern from pivot points.

        This is a simplified algorithm. Full Elliott Wave analysis is complex
        and requires extensive pattern recognition.

        Args:
            df: DataFrame with OHLCV data
            pivots_high: List of pivot highs
            pivots_low: List of pivot lows

        Returns:
            WavePattern object
        """
        current_price = df.iloc[-1]['close']

        # Combine and sort pivots by timestamp
        all_pivots = []
        for p in pivots_high:
            all_pivots.append({'price': p['price'], 'type': 'high', 'timestamp': p['timestamp']})
        for p in pivots_low:
            all_pivots.append({'price': p['price'], 'type': 'low', 'timestamp': p['timestamp']})

        all_pivots.sort(key=lambda x: x['timestamp'])

        if len(all_pivots) < 5:
            logger.warning("Not enough pivot points for wave analysis")
            return WavePattern(
                wave_type='unknown',
                current_wave='?',
                confidence=0,
                start_price=current_price,
                current_price=current_price,
                projected_target=None,
                invalidation_level=current_price * 0.95
            )

        # Get last 5 significant pivots for wave counting
        recent_pivots = all_pivots[-8:]  # Look at last 8 pivots

        # Determine trend direction
        first_pivot_price = recent_pivots[0]['price']
        last_pivot_price = recent_pivots[-1]['price']
        trend = 'bullish' if last_pivot_price > first_pivot_price else 'bearish'

        # Simple wave counting logic
        # In real implementation, this would be much more sophisticated

        if trend == 'bullish':
            # Count upward moves as waves
            wave_count = sum(1 for i in range(1, len(recent_pivots))
                           if recent_pivots[i]['price'] > recent_pivots[i-1]['price'])

            # Determine likely wave position
            if wave_count >= 3:
                current_wave = '5'  # Likely in wave 5
                wave_type = 'impulsive'
            elif wave_count >= 2:
                current_wave = '3'  # Likely in wave 3
                wave_type = 'impulsive'
            else:
                current_wave = '1'  # Starting wave 1
                wave_type = 'impulsive'
        else:
            # Bearish trend - might be correction
            current_wave = 'C'
            wave_type = 'corrective'

        # Calculate confidence based on pivot clarity
        confidence = min(100, len(all_pivots) * 10)  # Simple confidence metric

        # Project target using Fibonacci
        if len(recent_pivots) >= 2:
            fib = self.calculate_fibonacci_levels(recent_pivots[0]['price'], recent_pivots[-1]['price'])
            projected_target = fib.level_1618 if trend == 'bullish' else fib.level_618
        else:
            projected_target = None

        # Set invalidation level
        invalidation_level = min(p['price'] for p in recent_pivots[-3:])

        return WavePattern(
            wave_type=wave_type,
            current_wave=current_wave,
            confidence=confidence,
            start_price=recent_pivots[0]['price'],
            current_price=current_price,
            projected_target=projected_target,
            invalidation_level=invalidation_level
        )

    def calculate_technical_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """Calculate technical indicators for wave confirmation"""
        rsi = self.calculate_rsi(df['close']).iloc[-1]
        macd, macd_signal, macd_histogram = self.calculate_macd(df['close'])

        # Volume trend
        recent_volume = df['volume'].iloc[-10:].mean()
        older_volume = df['volume'].iloc[-30:-10].mean()
        volume_trend = 'increasing' if recent_volume > older_volume * 1.1 else \
                      'decreasing' if recent_volume < older_volume * 0.9 else 'neutral'

        # Momentum
        if rsi > 60 and macd_histogram.iloc[-1] > 0:
            momentum = 'bullish'
        elif rsi < 40 and macd_histogram.iloc[-1] < 0:
            momentum = 'bearish'
        else:
            momentum = 'neutral'

        return TechnicalIndicators(
            rsi=rsi,
            macd=macd.iloc[-1],
            macd_signal=macd_signal.iloc[-1],
            macd_histogram=macd_histogram.iloc[-1],
            volume_trend=volume_trend,
            momentum=momentum
        )

    def generate_trading_signal(
        self,
        wave_pattern: WavePattern,
        indicators: TechnicalIndicators,
        fib_levels: FibonacciLevels,
        current_price: float
    ) -> TradingSignal:
        """
        Generate trading signal based on Elliott Wave and indicators.

        Args:
            wave_pattern: Identified wave pattern
            indicators: Technical indicators
            fib_levels: Fibonacci levels
            current_price: Current market price

        Returns:
            TradingSignal with action and risk management
        """
        # Decision logic based on wave position and indicators

        if wave_pattern.wave_type == 'corrective' and wave_pattern.current_wave == 'C':
            # End of correction - potential BUY
            if indicators.rsi < 40 and indicators.momentum != 'bearish':
                action = 'BUY'
                confidence = 70 + (40 - indicators.rsi) / 2  # Higher confidence if more oversold
                entry_price = current_price
                stop_loss = wave_pattern.invalidation_level * 0.98
                take_profit_1 = fib_levels.level_382
                take_profit_2 = fib_levels.level_618
                take_profit_3 = fib_levels.level_1618
                reasoning = f"Wave C correction ending, RSI oversold at {indicators.rsi:.1f}, momentum turning"
            else:
                action = 'HOLD'
                confidence = 50
                entry_price = current_price
                stop_loss = wave_pattern.invalidation_level
                take_profit_1 = fib_levels.level_382
                take_profit_2 = fib_levels.level_618
                take_profit_3 = fib_levels.level_1618
                reasoning = "Wait for clearer correction completion signal"

        elif wave_pattern.wave_type == 'impulsive' and wave_pattern.current_wave == '5':
            # End of wave 5 - potential SELL
            if indicators.rsi > 70 or indicators.volume_trend == 'decreasing':
                action = 'SELL'
                confidence = 65 + (indicators.rsi - 70) / 2 if indicators.rsi > 70 else 60
                entry_price = current_price
                stop_loss = current_price * 1.03
                take_profit_1 = fib_levels.level_382
                take_profit_2 = fib_levels.level_618
                take_profit_3 = fib_levels.level_786
                reasoning = f"Wave 5 likely complete, RSI overbought at {indicators.rsi:.1f}, volume declining"
            else:
                action = 'HOLD'
                confidence = 55
                entry_price = current_price
                stop_loss = fib_levels.level_786
                take_profit_1 = wave_pattern.projected_target or current_price * 1.05
                take_profit_2 = wave_pattern.projected_target or current_price * 1.10
                take_profit_3 = wave_pattern.projected_target or current_price * 1.15
                reasoning = "Wave 5 in progress, monitoring for exhaustion signals"

        elif wave_pattern.wave_type == 'impulsive' and wave_pattern.current_wave in ['1', '3']:
            # Strong impulsive wave - BUY
            if indicators.momentum == 'bullish':
                action = 'BUY'
                confidence = 75
                entry_price = current_price
                stop_loss = fib_levels.level_618
                take_profit_1 = fib_levels.level_1618
                take_profit_2 = fib_levels.level_2618
                take_profit_3 = wave_pattern.projected_target or current_price * 1.20
                reasoning = f"Strong Wave {wave_pattern.current_wave} in progress, momentum bullish"
            else:
                action = 'HOLD'
                confidence = 60
                entry_price = current_price
                stop_loss = fib_levels.level_500
                take_profit_1 = fib_levels.level_1618
                take_profit_2 = fib_levels.level_2618
                take_profit_3 = wave_pattern.projected_target or current_price * 1.20
                reasoning = "Wait for momentum confirmation"

        else:
            # Unclear pattern - HOLD
            action = 'HOLD'
            confidence = 40
            entry_price = current_price
            stop_loss = wave_pattern.invalidation_level
            take_profit_1 = current_price * 1.05
            take_profit_2 = current_price * 1.10
            take_profit_3 = current_price * 1.15
            reasoning = "Wave structure unclear, need more confirmation"

        # Calculate risk/reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit_2 - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0

        return TradingSignal(
            action=action,
            confidence=min(100, confidence),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            take_profit_3=take_profit_3,
            risk_reward_ratio=risk_reward_ratio,
            reasoning=reasoning
        )

    def analyze_timeframe(self, symbol: str, timeframe: str) -> Dict:
        """
        Perform complete Elliott Wave analysis for a timeframe.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe

        Returns:
            Dictionary with complete analysis
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"ANALYZING {symbol} {timeframe}")
        logger.info(f"{'='*60}")

        # Fetch data
        df = self.fetch_candles(symbol, timeframe, limit=200)
        current_price = df.iloc[-1]['close']

        # Detect pivots
        pivots_high, pivots_low = self.detect_pivots(df, window=5)

        # Identify wave pattern
        wave_pattern = self.identify_wave_pattern(df, pivots_high, pivots_low)

        # Calculate Fibonacci levels
        if len(pivots_high) > 0 and len(pivots_low) > 0:
            recent_low = min(p['price'] for p in pivots_low[-3:])
            recent_high = max(p['price'] for p in pivots_high[-3:])
            fib_levels = self.calculate_fibonacci_levels(recent_low, recent_high)
        else:
            fib_levels = self.calculate_fibonacci_levels(current_price * 0.9, current_price)

        # Calculate indicators
        indicators = self.calculate_technical_indicators(df)

        # Generate signal
        signal = self.generate_trading_signal(wave_pattern, indicators, fib_levels, current_price)

        return {
            'timeframe': timeframe,
            'current_price': current_price,
            'wave_pattern': wave_pattern,
            'fibonacci_levels': fib_levels,
            'indicators': indicators,
            'signal': signal,
            'pivots_high': pivots_high[-5:],  # Last 5 highs
            'pivots_low': pivots_low[-5:],   # Last 5 lows
        }


def print_analysis_report(analysis_1d: Dict, analysis_4h: Dict):
    """Print comprehensive analysis report"""

    print("\n" + "="*80)
    print("ELLIOTT WAVE ANALYSIS - BTC/USDT")
    print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("="*80)

    # 1D Analysis
    print("\n" + "-"*80)
    print("TIMEFRAME: 1D (MACRO STRUCTURE)")
    print("-"*80)

    wp_1d = analysis_1d['wave_pattern']
    ind_1d = analysis_1d['indicators']
    sig_1d = analysis_1d['signal']
    fib_1d = analysis_1d['fibonacci_levels']

    print(f"\nCurrent Price: ${analysis_1d['current_price']:,.2f}")
    print(f"\nWave Analysis:")
    print(f"  Wave Type: {wp_1d.wave_type.upper()}")
    print(f"  Current Wave: {wp_1d.current_wave}")
    print(f"  Confidence: {wp_1d.confidence:.1f}%")
    print(f"  Wave Start: ${wp_1d.start_price:,.2f}")
    if wp_1d.projected_target:
        print(f"  Projected Target: ${wp_1d.projected_target:,.2f}")
    print(f"  Invalidation Level: ${wp_1d.invalidation_level:,.2f}")

    print(f"\nFibonacci Levels:")
    print(f"  0.0%   (Low):    ${fib_1d.level_0:,.2f}")
    print(f"  23.6%:           ${fib_1d.level_236:,.2f}")
    print(f"  38.2%:           ${fib_1d.level_382:,.2f}")
    print(f"  50.0%:           ${fib_1d.level_500:,.2f}")
    print(f"  61.8% (Golden):  ${fib_1d.level_618:,.2f}")
    print(f"  78.6%:           ${fib_1d.level_786:,.2f}")
    print(f"  100% (High):     ${fib_1d.level_100:,.2f}")
    print(f"  161.8%:          ${fib_1d.level_1618:,.2f}")
    print(f"  261.8%:          ${fib_1d.level_2618:,.2f}")

    print(f"\nTechnical Indicators:")
    print(f"  RSI: {ind_1d.rsi:.2f}")
    print(f"  MACD: {ind_1d.macd:.2f}")
    print(f"  MACD Signal: {ind_1d.macd_signal:.2f}")
    print(f"  MACD Histogram: {ind_1d.macd_histogram:.2f}")
    print(f"  Volume Trend: {ind_1d.volume_trend.upper()}")
    print(f"  Momentum: {ind_1d.momentum.upper()}")

    # 4H Analysis
    print("\n" + "-"*80)
    print("TIMEFRAME: 4H (MICRO STRUCTURE)")
    print("-"*80)

    wp_4h = analysis_4h['wave_pattern']
    ind_4h = analysis_4h['indicators']
    sig_4h = analysis_4h['signal']
    fib_4h = analysis_4h['fibonacci_levels']

    print(f"\nCurrent Price: ${analysis_4h['current_price']:,.2f}")
    print(f"\nWave Analysis:")
    print(f"  Wave Type: {wp_4h.wave_type.upper()}")
    print(f"  Current Wave: {wp_4h.current_wave}")
    print(f"  Confidence: {wp_4h.confidence:.1f}%")
    print(f"  Sub-wave Context: Within {wp_1d.wave_type} Wave {wp_1d.current_wave} (1D)")

    print(f"\nFibonacci Levels (4H):")
    print(f"  38.2%:           ${fib_4h.level_382:,.2f}")
    print(f"  50.0%:           ${fib_4h.level_500:,.2f}")
    print(f"  61.8% (Golden):  ${fib_4h.level_618:,.2f}")

    print(f"\nTechnical Indicators:")
    print(f"  RSI: {ind_4h.rsi:.2f}")
    print(f"  MACD Histogram: {ind_4h.macd_histogram:.2f}")
    print(f"  Volume Trend: {ind_4h.volume_trend.upper()}")
    print(f"  Momentum: {ind_4h.momentum.upper()}")

    # Convergence/Divergence
    print("\n" + "-"*80)
    print("MULTI-TIMEFRAME ANALYSIS")
    print("-"*80)

    if wp_1d.wave_type == wp_4h.wave_type:
        print(f"\n  CONFIRMATION: Both timeframes show {wp_1d.wave_type.upper()} structure")
    else:
        print(f"\n  DIVERGENCE: 1D shows {wp_1d.wave_type.upper()}, 4H shows {wp_4h.wave_type.upper()}")

    if ind_1d.momentum == ind_4h.momentum:
        print(f"  MOMENTUM ALIGNED: {ind_1d.momentum.upper()} on both timeframes")
    else:
        print(f"  MOMENTUM CONFLICT: 1D is {ind_1d.momentum.upper()}, 4H is {ind_4h.momentum.upper()}")

    # Trading Signal
    print("\n" + "="*80)
    print("TRADING SIGNAL")
    print("="*80)

    # Use 1D for strategic direction, 4H for tactical entry
    print(f"\nStrategic Position (1D): {sig_1d.action}")
    print(f"  Confidence: {sig_1d.confidence:.1f}%")
    print(f"  Reasoning: {sig_1d.reasoning}")

    print(f"\nTactical Position (4H): {sig_4h.action}")
    print(f"  Confidence: {sig_4h.confidence:.1f}%")
    print(f"  Reasoning: {sig_4h.reasoning}")

    # Final recommendation
    print("\n" + "-"*80)
    print("RECOMMENDED ACTION")
    print("-"*80)

    if sig_1d.action == sig_4h.action:
        final_action = sig_1d.action
        final_confidence = (sig_1d.confidence + sig_4h.confidence) / 2
        print(f"\n  ACTION: {final_action}")
        print(f"  CONFIDENCE: {final_confidence:.1f}%")
        print(f"  ALIGNMENT: Both timeframes agree")
    else:
        print(f"\n  ACTION: HOLD (timeframes conflict)")
        print(f"  WAIT FOR: Alignment between 1D and 4H signals")

    # Risk Management
    print("\n" + "-"*80)
    print("RISK MANAGEMENT (Based on 4H for precise entry)")
    print("-"*80)

    print(f"\n  Entry Price: ${sig_4h.entry_price:,.2f}")
    print(f"  Stop Loss: ${sig_4h.stop_loss:,.2f} ({((sig_4h.stop_loss/sig_4h.entry_price - 1) * 100):.2f}%)")
    print(f"\n  Take Profit Levels:")
    print(f"    TP1: ${sig_4h.take_profit_1:,.2f} ({((sig_4h.take_profit_1/sig_4h.entry_price - 1) * 100):.2f}%)")
    print(f"    TP2: ${sig_4h.take_profit_2:,.2f} ({((sig_4h.take_profit_2/sig_4h.entry_price - 1) * 100):.2f}%)")
    print(f"    TP3: ${sig_4h.take_profit_3:,.2f} ({((sig_4h.take_profit_3/sig_4h.entry_price - 1) * 100):.2f}%)")
    print(f"\n  Risk/Reward Ratio: 1:{sig_4h.risk_reward_ratio:.2f}")

    print("\n" + "="*80)
    print("DISCLAIMER: This analysis is for educational purposes only.")
    print("Always do your own research and never risk more than you can afford to lose.")
    print("="*80 + "\n")


def main():
    """Main execution function"""
    try:
        # Initialize Binance client (production)
        logger.info("Initializing Binance REST client...")
        client = BinanceRESTClient(testnet=False)

        # Test connection
        server_time = client.get_server_time()
        if not server_time:
            raise RuntimeError("Failed to connect to Binance API. Check your internet connection.")

        logger.info(f"Connected to Binance. Server time: {datetime.fromtimestamp(server_time/1000)}")

        # Initialize analyzer
        analyzer = ElliottWaveAnalyzer(client)

        # Analyze both timeframes
        analysis_1d = analyzer.analyze_timeframe('BTCUSDT', '1d')
        analysis_4h = analyzer.analyze_timeframe('BTCUSDT', '4h')

        # Print comprehensive report
        print_analysis_report(analysis_1d, analysis_4h)

        # Save report to file
        reports_dir = Path(__file__).parent.parent / 'reports'
        reports_dir.mkdir(exist_ok=True)

        report_file = reports_dir / f'elliott_wave_btcusdt_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

        # Redirect stdout to file
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = report_buffer = StringIO()

        print_analysis_report(analysis_1d, analysis_4h)

        report_content = report_buffer.getvalue()
        sys.stdout = old_stdout

        with open(report_file, 'w') as f:
            f.write(report_content)

        logger.info(f"Report saved to: {report_file}")

    except RuntimeError as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\n ERROR: {e}")
        print("\n If connection failed, check:")
        print("  1. Internet connectivity")
        print("  2. Binance API is accessible from your location")
        print("  3. No firewall blocking the connection")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n CRITICAL ERROR: {e}")
        print("\n This is a bug. Please report with the full error trace above.")
        sys.exit(1)

    finally:
        if 'client' in locals():
            client.close()


if __name__ == '__main__':
    main()
