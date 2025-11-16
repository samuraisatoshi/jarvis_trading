"""
Fibonacci retracement and extension calculator for Elliott Wave analysis.

This module provides calculations for Fibonacci levels used in Elliott Wave
analysis for identifying potential support/resistance and price targets.

SOLID Principles:
- Single Responsibility: Focus only on Fibonacci calculations
- Open/Closed: Extensible for custom Fibonacci sequences
- Interface Segregation: Clean, focused API
"""

from typing import Optional, Dict, List
from .models import FibonacciLevels


class FibonacciCalculator:
    """
    Calculator for Fibonacci retracement and extension levels.

    Supports standard Fibonacci ratios and custom sequences.
    """

    # Standard Fibonacci ratios
    STANDARD_RATIOS = {
        'retracement': [0.0, 0.236, 0.382, 0.500, 0.618, 0.786, 1.0],
        'extension': [1.618, 2.618, 3.618, 4.236]
    }

    # Golden ratio (phi)
    GOLDEN_RATIO = 1.618

    def __init__(self):
        """Initialize Fibonacci calculator with standard ratios."""
        self.retracement_ratios = self.STANDARD_RATIOS['retracement'].copy()
        self.extension_ratios = self.STANDARD_RATIOS['extension'].copy()

    def calculate_levels(self, start_price: float,
                        end_price: float) -> FibonacciLevels:
        """
        Calculate Fibonacci levels from start to end price.

        For retracements: Calculates levels from end back toward start
        For extensions: Projects levels beyond the move

        Args:
            start_price: Starting price of the move
            end_price: Ending price of the move

        Returns:
            FibonacciLevels with all standard levels

        Example:
            Uptrend from 30000 to 40000:
            - Retracements pull back from 40000 toward 30000
            - Extensions project beyond 40000
        """
        if start_price <= 0 or end_price <= 0:
            raise ValueError("Prices must be positive")

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

    def calculate_retracement(self, start_price: float, end_price: float,
                             ratio: float) -> float:
        """
        Calculate specific retracement level.

        Args:
            start_price: Starting price
            end_price: Ending price
            ratio: Fibonacci ratio (e.g., 0.618)

        Returns:
            Price level at the retracement ratio
        """
        diff = end_price - start_price
        return end_price - diff * ratio

    def calculate_extension(self, start_price: float, end_price: float,
                           ratio: float) -> float:
        """
        Calculate specific extension level.

        Args:
            start_price: Starting price
            end_price: Ending price
            ratio: Fibonacci ratio (e.g., 1.618)

        Returns:
            Price level at the extension ratio
        """
        diff = end_price - start_price
        return start_price + diff * ratio

    def find_nearest_level(self, current_price: float,
                          fib_levels: FibonacciLevels) -> Dict[str, float]:
        """
        Find nearest Fibonacci level to current price.

        Args:
            current_price: Current market price
            fib_levels: Calculated Fibonacci levels

        Returns:
            Dict with 'level', 'price', 'distance_pct'
        """
        levels = {
            '0%': fib_levels.level_0,
            '23.6%': fib_levels.level_236,
            '38.2%': fib_levels.level_382,
            '50%': fib_levels.level_500,
            '61.8%': fib_levels.level_618,
            '78.6%': fib_levels.level_786,
            '100%': fib_levels.level_100,
            '161.8%': fib_levels.level_1618,
            '261.8%': fib_levels.level_2618
        }

        nearest = None
        min_distance = float('inf')

        for name, price in levels.items():
            distance = abs(current_price - price)
            if distance < min_distance:
                min_distance = distance
                nearest = {
                    'level': name,
                    'price': price,
                    'distance_pct': (distance / current_price) * 100
                }

        return nearest

    def get_support_levels(self, current_price: float,
                          fib_levels: FibonacciLevels) -> List[Dict]:
        """
        Get Fibonacci levels acting as support (below current price).

        Args:
            current_price: Current market price
            fib_levels: Calculated Fibonacci levels

        Returns:
            List of support levels sorted by proximity
        """
        levels = [
            {'level': '0%', 'price': fib_levels.level_0},
            {'level': '23.6%', 'price': fib_levels.level_236},
            {'level': '38.2%', 'price': fib_levels.level_382},
            {'level': '50%', 'price': fib_levels.level_500},
            {'level': '61.8%', 'price': fib_levels.level_618},
            {'level': '78.6%', 'price': fib_levels.level_786},
            {'level': '100%', 'price': fib_levels.level_100}
        ]

        supports = [lvl for lvl in levels if lvl['price'] < current_price]
        supports.sort(key=lambda x: current_price - x['price'])

        return supports

    def get_resistance_levels(self, current_price: float,
                             fib_levels: FibonacciLevels) -> List[Dict]:
        """
        Get Fibonacci levels acting as resistance (above current price).

        Args:
            current_price: Current market price
            fib_levels: Calculated Fibonacci levels

        Returns:
            List of resistance levels sorted by proximity
        """
        levels = [
            {'level': '23.6%', 'price': fib_levels.level_236},
            {'level': '38.2%', 'price': fib_levels.level_382},
            {'level': '50%', 'price': fib_levels.level_500},
            {'level': '61.8%', 'price': fib_levels.level_618},
            {'level': '78.6%', 'price': fib_levels.level_786},
            {'level': '100%', 'price': fib_levels.level_100},
            {'level': '161.8%', 'price': fib_levels.level_1618},
            {'level': '261.8%', 'price': fib_levels.level_2618}
        ]

        resistances = [lvl for lvl in levels if lvl['price'] > current_price]
        resistances.sort(key=lambda x: x['price'] - current_price)

        return resistances

    def calculate_wave_projection(self, wave1_start: float, wave1_end: float,
                                  wave2_end: float) -> Dict[str, float]:
        """
        Project Wave 3 target based on Wave 1 and Wave 2.

        Elliott Wave rules:
        - Wave 3 is typically 1.618x or 2.618x Wave 1
        - Wave 3 starts from Wave 2 end

        Args:
            wave1_start: Wave 1 starting price
            wave1_end: Wave 1 ending price
            wave2_end: Wave 2 ending price (retracement)

        Returns:
            Dict with 'conservative', 'standard', 'aggressive' targets
        """
        wave1_size = abs(wave1_end - wave1_start)
        direction = 1 if wave1_end > wave1_start else -1

        return {
            'conservative': wave2_end + direction * wave1_size * 1.0,
            'standard': wave2_end + direction * wave1_size * 1.618,
            'aggressive': wave2_end + direction * wave1_size * 2.618
        }

    def validate_wave2_retracement(self, wave1_start: float, wave1_end: float,
                                   wave2_end: float) -> Dict[str, bool]:
        """
        Validate if Wave 2 follows Elliott Wave rules.

        Wave 2 rules:
        - Must retrace 38.2% to 78.6% of Wave 1
        - Cannot retrace more than 100% (below Wave 1 start)

        Args:
            wave1_start: Wave 1 starting price
            wave1_end: Wave 1 ending price
            wave2_end: Wave 2 ending price

        Returns:
            Dict with validation results
        """
        wave1_size = abs(wave1_end - wave1_start)
        retracement = abs(wave1_end - wave2_end)
        retracement_pct = (retracement / wave1_size) * 100

        # Check if retraced past Wave 1 start
        invalidated = False
        if wave1_end > wave1_start:  # Uptrend
            invalidated = wave2_end < wave1_start
        else:  # Downtrend
            invalidated = wave2_end > wave1_start

        return {
            'valid': not invalidated and 38.2 <= retracement_pct <= 78.6,
            'retracement_pct': retracement_pct,
            'within_typical_range': 38.2 <= retracement_pct <= 78.6,
            'invalidated': invalidated
        }

    def add_custom_ratio(self, ratio: float, ratio_type: str = 'retracement'
                        ) -> None:
        """
        Add custom Fibonacci ratio.

        Args:
            ratio: Custom ratio to add (e.g., 0.5 for 50%)
            ratio_type: 'retracement' or 'extension'
        """
        if ratio_type == 'retracement':
            if ratio not in self.retracement_ratios:
                self.retracement_ratios.append(ratio)
                self.retracement_ratios.sort()
        elif ratio_type == 'extension':
            if ratio not in self.extension_ratios:
                self.extension_ratios.append(ratio)
                self.extension_ratios.sort()
        else:
            raise ValueError("ratio_type must be 'retracement' or 'extension'")
