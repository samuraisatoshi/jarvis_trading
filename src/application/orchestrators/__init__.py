"""
Application orchestrators package.

Orchestrators coordinate complex workflows that span multiple domains,
services, and external systems. They contain NO business logic - only
workflow coordination, error handling, and retry logic.

Key Differences:
- Services: Single-domain business logic (domain layer)
- Orchestrators: Multi-domain workflow coordination (application layer)

Available Orchestrators:
- BaseOrchestrator: Abstract base class for all orchestrators
- FibonacciTradingOrchestrator: Fibonacci Golden Zone trading workflow
- PaperTradingOrchestrator: Generic paper trading for any strategy

Usage Example (Fibonacci):
    >>> from src.application.orchestrators import FibonacciTradingOrchestrator
    >>> orchestrator = FibonacciTradingOrchestrator(
    ...     account_id="uuid",
    ...     symbol="BNB_USDT",
    ...     timeframe="1d",
    ...     db_path="data/db.sqlite",
    ...     dry_run=False
    ... )
    >>> result = orchestrator.execute()
    >>> print(result['status'])  # 'success' or 'failure'

Usage Example (Generic):
    >>> from src.application.orchestrators import PaperTradingOrchestrator
    >>> from src.strategies import FibonacciGoldenZoneStrategy
    >>> orchestrator = PaperTradingOrchestrator(
    ...     account_id="uuid",
    ...     strategy=FibonacciGoldenZoneStrategy(),
    ...     symbol="BTC_USDT",
    ...     timeframe="4h",
    ...     db_path="data/db.sqlite"
    ... )
    >>> result = orchestrator.execute()

SOLID Principles:
- Single Responsibility: Each orchestrator coordinates one specific workflow
- Open/Closed: Extend with new orchestrators, don't modify existing ones
- Liskov Substitution: All orchestrators implement BaseOrchestrator interface
- Interface Segregation: Minimal interface (execute + error handling)
- Dependency Inversion: Depend on abstractions (strategies, services, repos)
"""

from src.application.orchestrators.base import (
    BaseOrchestrator,
    OrchestrationError
)
from src.application.orchestrators.fibonacci_trading_orchestrator import (
    FibonacciTradingOrchestrator
)
from src.application.orchestrators.paper_trading_orchestrator import (
    PaperTradingOrchestrator
)

__all__ = [
    # Base
    'BaseOrchestrator',
    'OrchestrationError',

    # Concrete orchestrators
    'FibonacciTradingOrchestrator',
    'PaperTradingOrchestrator',
]
