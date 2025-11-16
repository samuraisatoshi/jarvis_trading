"""
Multi-Asset Trading Daemon Package.

This package provides a modular, SOLID-compliant architecture for
automated multi-asset trading across multiple timeframes.

Architecture:
- Domain models: Pure domain entities with no infrastructure dependencies
- Interfaces: Abstract protocols for dependency injection
- Services: Business logic coordinating domain operations
- Manager: Main orchestrator for daemon lifecycle

Main Components:
- DaemonManager: Main orchestrator
- SignalProcessor: Signal detection and filtering
- TradeExecutor: Trade execution with validation
- PortfolioService: Portfolio management
- MonitoringService: Health monitoring and metrics
- NotificationHandler: Centralized notifications

Design Patterns:
- Dependency Injection: All services injected via constructor
- Repository Pattern: Data access abstracted behind interfaces
- Strategy Pattern: Pluggable signal generation strategies
- Observer Pattern: Event-driven notifications
- Facade Pattern: Simplified daemon interface

Usage Example:
    ```python
    from src.daemon import (
        DaemonManager,
        DaemonConfig,
        SignalProcessor,
        TradeExecutor,
        PortfolioService,
        MonitoringService,
        NotificationHandler
    )

    # Create configuration
    config = DaemonConfig(
        timeframes=['1h', '4h', '1d'],
        check_interval=3600,
        position_sizes={'1h': 0.1, '4h': 0.2, '1d': 0.3}
    )

    # Instantiate services (with DI)
    signal_processor = SignalProcessor(...)
    trade_executor = TradeExecutor(...)
    portfolio_service = PortfolioService(...)
    monitoring_service = MonitoringService(...)
    notification_handler = NotificationHandler(...)

    # Create daemon
    daemon = DaemonManager(
        signal_processor=signal_processor,
        trade_executor=trade_executor,
        portfolio_service=portfolio_service,
        monitoring_service=monitoring_service,
        notification_handler=notification_handler,
        config=config
    )

    # Run daemon
    daemon.run()
    ```

For complete setup with infrastructure components, see entry point:
    scripts/multi_asset_trading_daemon.py
"""

from .models import (
    Signal,
    SignalAction,
    Position,
    PortfolioStatus,
    TradeResult,
    DaemonConfig
)

from .interfaces import (
    ExchangeClient,
    BalanceRepository,
    OrderRepository,
    PositionRepository,
    NotificationService,
    SignalStrategy,
    WatchlistManager
)

from .daemon_manager import DaemonManager
from .signal_processor import SignalProcessor
from .trade_executor import TradeExecutor
from .portfolio_service import PortfolioService
from .monitoring_service import MonitoringService
from .notification_handler import NotificationHandler

__all__ = [
    # Models
    'Signal',
    'SignalAction',
    'Position',
    'PortfolioStatus',
    'TradeResult',
    'DaemonConfig',
    # Interfaces
    'ExchangeClient',
    'BalanceRepository',
    'OrderRepository',
    'PositionRepository',
    'NotificationService',
    'SignalStrategy',
    'WatchlistManager',
    # Services
    'DaemonManager',
    'SignalProcessor',
    'TradeExecutor',
    'PortfolioService',
    'MonitoringService',
    'NotificationHandler',
]

__version__ = '1.0.0'
__author__ = 'Jarvis Trading'
__description__ = 'Multi-Asset Trading Daemon with SOLID Architecture'
