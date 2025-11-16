"""
DCA (Dollar Cost Averaging) Trading Module.

This module provides intelligent DCA strategy implementation with:
- RSI-based purchase adjustments
- ATH profit-taking
- Crash rebuying with reserves
"""

from .strategy import DCASmartStrategy, Trade
from .simulator import DCASimulator
from .analyzer import DCAAnalyzer
from .visualizer import DCAVisualizer

__all__ = [
    'DCASmartStrategy',
    'Trade',
    'DCASimulator',
    'DCAAnalyzer',
    'DCAVisualizer',
]
