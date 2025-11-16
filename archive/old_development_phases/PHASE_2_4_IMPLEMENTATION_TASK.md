# Phase 2.4 Implementation Task - Multi-Asset Trading Daemon Refactoring

## Task Overview

**Assigned To**: script-developer agent
**Priority**: HIGH (FINAL Phase 2.4 target)
**Complexity**: MEDIUM-HIGH
**Estimated Time**: 6-7 hours

**Input File**: `/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/scripts/multi_asset_trading_daemon.py` (672 lines)

**Output**: Modular architecture in `src/daemon/` + repository implementations + new entry point

---

## Detailed Implementation Steps

### Step 1: Create Domain Models (`src/daemon/models.py`)

**Purpose**: Pure domain entities with no infrastructure dependencies.

**Implementation Requirements**:

```python
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

class SignalAction(Enum):
    """Trading signal action."""
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Signal:
    """Trading signal domain model."""
    symbol: str
    timeframe: str
    action: SignalAction
    price: float
    ma: float
    distance: float
    threshold: float
    reason: str
    timestamp: datetime

    def __str__(self) -> str:
        return f"{self.action.value} {self.symbol} @ ${self.price:.2f} ({self.timeframe})"

@dataclass
class Position:
    """Asset position domain model."""
    symbol: str
    currency: str
    quantity: float
    average_price: Optional[float] = None

    def get_value(self, current_price: float) -> float:
        """Calculate position value at current price."""
        return self.quantity * current_price

@dataclass
class PortfolioStatus:
    """Portfolio status snapshot."""
    total_value: float
    usdt_balance: float
    positions: List[Position]
    timestamp: datetime

    @property
    def num_positions(self) -> int:
        return len(self.positions)

    @property
    def invested_value(self) -> float:
        return self.total_value - self.usdt_balance

@dataclass
class TradeResult:
    """Trade execution result."""
    success: bool
    signal: Signal
    quantity: Optional[float] = None
    total_value: Optional[float] = None
    order_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class DaemonConfig:
    """Daemon configuration."""
    timeframes: List[str]
    check_interval: int  # seconds
    position_sizes: Dict[str, float]  # timeframe -> allocation %
    min_check_intervals: Optional[Dict[str, int]] = None  # timeframe -> min seconds
```

**Validation**:
- All classes use `@dataclass`
- Type hints everywhere
- No infrastructure dependencies
- Include docstrings
- Add helper methods where useful

**Lines**: ~150

---

### Step 2: Create Abstract Interfaces (`src/daemon/interfaces.py`)

**Purpose**: Define protocols for dependency injection.

**Implementation Requirements**:

```python
from typing import Protocol, Dict, List, Optional
from .models import Signal, Position, TradeResult

class ExchangeClient(Protocol):
    """Exchange API client protocol."""

    def get_24h_ticker(self, symbol: str) -> Dict:
        """Get 24h ticker for symbol."""
        ...

    def get_klines(self, symbol: str, interval: str, limit: int) -> List:
        """Get historical klines."""
        ...

class BalanceRepository(Protocol):
    """Balance repository protocol."""

    def get_balance(self, currency: str) -> float:
        """Get available balance for currency."""
        ...

    def get_all_balances(self) -> Dict[str, float]:
        """Get all balances."""
        ...

    def update_balance(self, currency: str, amount: float, operation: str) -> bool:
        """Update balance (add/subtract)."""
        ...

class OrderRepository(Protocol):
    """Order repository protocol."""

    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: str = "MARKET"
    ) -> str:
        """Create and save order. Returns order_id."""
        ...

class PositionRepository(Protocol):
    """Position repository protocol."""

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for symbol."""
        ...

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        ...

class NotificationService(Protocol):
    """Notification service protocol."""

    def send_message(self, message: str) -> bool:
        """Send generic message."""
        ...

    def notify_trade_executed(
        self,
        trade_type: str,
        symbol: str,
        quantity: float,
        price: float,
        timeframe: str,
        reason: Optional[str] = None
    ) -> bool:
        """Notify trade execution."""
        ...

    def notify_daemon_started(
        self,
        watchlist: List[str],
        capital: float
    ) -> bool:
        """Notify daemon started."""
        ...

    def notify_signals_found(self, signals: List[Signal]) -> bool:
        """Notify signals detected."""
        ...

class SignalStrategy(Protocol):
    """Signal generation strategy protocol."""

    def generate_signal(
        self,
        symbol: str,
        timeframe: str,
        exchange_client: ExchangeClient,
        position_repo: PositionRepository
    ) -> Optional[Signal]:
        """Generate trading signal."""
        ...
```

**Validation**:
- All interfaces use `Protocol`
- Methods have `...` body
- Complete type hints
- Docstrings for all methods

**Lines**: ~200

---

### Step 3: Create Portfolio Service (`src/daemon/portfolio_service.py`)

**Purpose**: Manage portfolio state and queries.

**Implementation Requirements**:

```python
from typing import Dict, List, Optional
from loguru import logger

from .models import Position, PortfolioStatus
from .interfaces import (
    BalanceRepository,
    PositionRepository,
    ExchangeClient
)
from datetime import datetime, timezone

class PortfolioService:
    """Portfolio management service."""

    def __init__(
        self,
        balance_repo: BalanceRepository,
        position_repo: PositionRepository,
        exchange_client: ExchangeClient
    ):
        self.balance_repo = balance_repo
        self.position_repo = position_repo
        self.exchange_client = exchange_client

    def get_portfolio_status(self, watchlist: List[str]) -> PortfolioStatus:
        """Get complete portfolio status."""
        try:
            balances = self.balance_repo.get_all_balances()
            usdt_balance = balances.get('USDT', 0.0)
            total_value = usdt_balance

            positions = []
            for symbol in watchlist:
                position = self.position_repo.get_position(symbol)
                if position and position.quantity > 0:
                    # Get current price
                    ticker = self.exchange_client.get_24h_ticker(symbol)
                    current_price = float(ticker['lastPrice'])
                    total_value += position.get_value(current_price)
                    positions.append(position)

            return PortfolioStatus(
                total_value=total_value,
                usdt_balance=usdt_balance,
                positions=positions,
                timestamp=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Error getting portfolio status: {e}")
            # Return empty status on error
            return PortfolioStatus(
                total_value=0.0,
                usdt_balance=0.0,
                positions=[],
                timestamp=datetime.now(timezone.utc)
            )

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for specific symbol."""
        return self.position_repo.get_position(symbol)

    def get_available_capital(self) -> float:
        """Get available USDT balance."""
        return self.balance_repo.get_balance('USDT')

    def calculate_position_size(
        self,
        symbol: str,
        timeframe: str,
        position_sizes: Dict[str, float]
    ) -> float:
        """
        Calculate position size based on timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1h, 4h, 1d)
            position_sizes: Dict mapping timeframe to allocation %

        Returns:
            Position size in USD
        """
        usdt_balance = self.get_available_capital()
        allocation = position_sizes.get(timeframe, 0.1)

        # Check if position already exists
        existing_position = self.get_position(symbol)
        if existing_position and existing_position.quantity > 0:
            # Reduce allocation if position exists
            allocation *= 0.5

        return usdt_balance * allocation
```

**Key Points**:
- Constructor-based dependency injection
- Error handling with logger
- Clear separation from infrastructure
- Helper methods for common operations

**Lines**: ~300

---

### Step 4: Create Signal Processor (`src/daemon/signal_processor.py`)

**Purpose**: Detect and filter trading signals.

**Implementation Requirements**:

```python
import pandas as pd
from typing import List, Optional, Dict
from loguru import logger
import time

from .models import Signal, SignalAction
from .interfaces import ExchangeClient, PositionRepository
from datetime import datetime, timezone

class SignalProcessor:
    """Signal detection and processing service."""

    def __init__(
        self,
        exchange_client: ExchangeClient,
        position_repo: PositionRepository,
        watchlist_manager,  # WatchlistManager instance
        min_check_intervals: Optional[Dict[str, int]] = None
    ):
        self.exchange_client = exchange_client
        self.position_repo = position_repo
        self.watchlist = watchlist_manager
        self.min_check_intervals = min_check_intervals or {
            '1h': 300,
            '4h': 1200,
            '1d': 3600
        }
        self.last_check: Dict[str, float] = {}

    def check_signal(self, symbol: str, timeframe: str) -> Optional[Signal]:
        """Check for trading signal on specific symbol/timeframe."""
        try:
            # Get optimized parameters
            params = self.watchlist.get_params(symbol, timeframe)
            if not params:
                logger.debug(f"No params for {symbol} {timeframe}")
                return None

            # Get current price
            ticker = self.exchange_client.get_24h_ticker(symbol)
            current_price = float(ticker['lastPrice'])

            # Get historical data for MA calculation
            klines = self.exchange_client.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=params['ma_period'] + 10
            )

            # Calculate MA
            df = pd.DataFrame(klines)
            df['close'] = df['close'].astype(float)
            ma = df['close'].rolling(window=params['ma_period']).mean().iloc[-1]

            # Calculate distance from MA
            distance = (current_price - ma) / ma * 100

            # Check for buy signal
            if distance <= params['buy_threshold']:
                return Signal(
                    symbol=symbol,
                    timeframe=timeframe,
                    action=SignalAction.BUY,
                    price=current_price,
                    ma=ma,
                    distance=distance,
                    threshold=params['buy_threshold'],
                    reason=f"Price {distance:.1f}% below MA{params['ma_period']}",
                    timestamp=datetime.now(timezone.utc)
                )

            # Check for sell signal (only if we have position)
            elif distance >= params['sell_threshold']:
                position = self.position_repo.get_position(symbol)
                if position and position.quantity > 0:
                    return Signal(
                        symbol=symbol,
                        timeframe=timeframe,
                        action=SignalAction.SELL,
                        price=current_price,
                        ma=ma,
                        distance=distance,
                        threshold=params['sell_threshold'],
                        reason=f"Price {distance:.1f}% above MA{params['ma_period']}",
                        timestamp=datetime.now(timezone.utc)
                    )

            return None

        except Exception as e:
            logger.error(f"Error checking signal {symbol} {timeframe}: {e}")
            return None

    def check_all_signals(
        self,
        timeframes: List[str]
    ) -> List[Signal]:
        """Check signals for all watchlist symbols and timeframes."""
        signals = []
        now = time.time()

        for symbol in self.watchlist.symbols:
            for timeframe in timeframes:
                # Check rate limiting
                check_key = f"{symbol}_{timeframe}"
                last_check = self.last_check.get(check_key, 0)
                min_interval = self.min_check_intervals.get(timeframe, 600)

                if now - last_check < min_interval:
                    continue

                # Check signal
                signal = self.check_signal(symbol, timeframe)
                if signal:
                    signals.append(signal)
                    logger.info(f"Signal detected: {signal}")

                self.last_check[check_key] = now

        return signals

    def prioritize_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        Sort signals by priority.
        SELL signals first, then by timeframe (larger first).
        """
        tf_priority = {'1d': 3, '4h': 2, '1h': 1}
        return sorted(signals, key=lambda s: (
            s.action == SignalAction.BUY,  # SELL first
            -tf_priority.get(s.timeframe, 0)  # Larger timeframe first
        ))

    def has_conflicting_signal(
        self,
        signal: Signal,
        all_signals: List[Signal]
    ) -> bool:
        """Check if signal conflicts with higher priority signals."""
        tf_priority = {'1d': 3, '4h': 2, '1h': 1}

        for other in all_signals:
            if other == signal:
                continue

            # Same symbol, opposite action
            if (other.symbol == signal.symbol and
                other.action != signal.action):
                # Higher priority timeframe wins
                if (tf_priority.get(other.timeframe, 0) >
                    tf_priority.get(signal.timeframe, 0)):
                    return True

        return False
```

**Key Points**:
- Rate limiting per symbol/timeframe
- MA-based signal generation
- Conflict detection
- Priority sorting

**Lines**: ~300

---

### Step 5: Create Trade Executor (`src/daemon/trade_executor.py`)

**Purpose**: Execute trades with proper validation.

**Implementation Requirements**:

```python
from typing import Optional, Dict
from loguru import logger
from datetime import datetime, timezone

from .models import Signal, SignalAction, TradeResult
from .interfaces import (
    BalanceRepository,
    OrderRepository,
    PositionRepository,
    NotificationService
)

class TradeExecutor:
    """Trade execution service."""

    MIN_TRADE_VALUE = 10.0  # Minimum $10 per trade

    def __init__(
        self,
        balance_repo: BalanceRepository,
        order_repo: OrderRepository,
        position_repo: PositionRepository,
        notification_service: NotificationService
    ):
        self.balance_repo = balance_repo
        self.order_repo = order_repo
        self.position_repo = position_repo
        self.notification_service = notification_service

    def execute_trade(
        self,
        signal: Signal,
        position_size_usd: float
    ) -> TradeResult:
        """
        Execute trade based on signal.

        Args:
            signal: Trading signal
            position_size_usd: Position size in USD

        Returns:
            TradeResult with execution status
        """
        try:
            if signal.action == SignalAction.BUY:
                return self._execute_buy(signal, position_size_usd)
            elif signal.action == SignalAction.SELL:
                return self._execute_sell(signal)
            else:
                return TradeResult(
                    success=False,
                    signal=signal,
                    error=f"Unknown action: {signal.action}"
                )

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return TradeResult(
                success=False,
                signal=signal,
                error=str(e)
            )

    def _execute_buy(
        self,
        signal: Signal,
        position_size_usd: float
    ) -> TradeResult:
        """Execute buy order."""
        # Validate position size
        if position_size_usd < self.MIN_TRADE_VALUE:
            return TradeResult(
                success=False,
                signal=signal,
                error=f"Position too small: ${position_size_usd:.2f} < ${self.MIN_TRADE_VALUE}"
            )

        # Calculate quantity
        quantity = position_size_usd / signal.price

        # Check balance
        usdt_balance = self.balance_repo.get_balance('USDT')
        if usdt_balance < position_size_usd:
            return TradeResult(
                success=False,
                signal=signal,
                error=f"Insufficient balance: ${usdt_balance:.2f} < ${position_size_usd:.2f}"
            )

        # Execute trade (paper trading)
        try:
            # Update USDT balance (subtract)
            self.balance_repo.update_balance('USDT', -position_size_usd, 'subtract')

            # Update asset balance (add)
            base_currency = signal.symbol.replace('USDT', '')
            self.balance_repo.update_balance(base_currency, quantity, 'add')

            # Create order record
            order_id = self.order_repo.create_order(
                symbol=signal.symbol,
                side='BUY',
                quantity=quantity,
                price=signal.price
            )

            logger.info(
                f"Buy executed: {quantity:.6f} {signal.symbol} "
                f"@ ${signal.price:.2f} = ${position_size_usd:.2f}"
            )

            # Notify
            self.notification_service.notify_trade_executed(
                trade_type='BUY',
                symbol=signal.symbol,
                quantity=quantity,
                price=signal.price,
                timeframe=signal.timeframe,
                reason=signal.reason
            )

            return TradeResult(
                success=True,
                signal=signal,
                quantity=quantity,
                total_value=position_size_usd,
                order_id=order_id
            )

        except Exception as e:
            logger.error(f"Buy execution failed: {e}")
            return TradeResult(
                success=False,
                signal=signal,
                error=str(e)
            )

    def _execute_sell(self, signal: Signal) -> TradeResult:
        """Execute sell order."""
        # Get position
        position = self.position_repo.get_position(signal.symbol)
        if not position or position.quantity <= 0:
            return TradeResult(
                success=False,
                signal=signal,
                error=f"No position in {signal.symbol}"
            )

        quantity = position.quantity
        total_value = quantity * signal.price

        # Execute trade
        try:
            # Update asset balance (subtract)
            base_currency = signal.symbol.replace('USDT', '')
            self.balance_repo.update_balance(base_currency, -quantity, 'subtract')

            # Update USDT balance (add)
            self.balance_repo.update_balance('USDT', total_value, 'add')

            # Create order record
            order_id = self.order_repo.create_order(
                symbol=signal.symbol,
                side='SELL',
                quantity=quantity,
                price=signal.price
            )

            logger.info(
                f"Sell executed: {quantity:.6f} {signal.symbol} "
                f"@ ${signal.price:.2f} = ${total_value:.2f}"
            )

            # Notify
            self.notification_service.notify_trade_executed(
                trade_type='SELL',
                symbol=signal.symbol,
                quantity=quantity,
                price=signal.price,
                timeframe=signal.timeframe,
                reason=signal.reason
            )

            return TradeResult(
                success=True,
                signal=signal,
                quantity=quantity,
                total_value=total_value,
                order_id=order_id
            )

        except Exception as e:
            logger.error(f"Sell execution failed: {e}")
            return TradeResult(
                success=False,
                signal=signal,
                error=str(e)
            )
```

**Key Points**:
- Validation before execution
- Transactional updates
- Error handling
- Notification integration

**Lines**: ~300

---

### Step 6: Create Notification Handler (`src/daemon/notification_handler.py`)

**Purpose**: Centralize notification logic.

**Implementation Requirements**:

```python
from typing import List
from loguru import logger
from datetime import datetime, timezone

from .models import Signal, PortfolioStatus, TradeResult
from .interfaces import NotificationService

class NotificationHandler:
    """Notification handling service."""

    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service

    def notify_daemon_started(
        self,
        watchlist: List[str],
        capital: float
    ) -> bool:
        """Notify daemon started."""
        try:
            return self.notification_service.notify_daemon_started(
                watchlist=watchlist,
                capital=capital
            )
        except Exception as e:
            logger.error(f"Failed to notify daemon start: {e}")
            return False

    def notify_signals_found(self, signals: List[Signal]) -> bool:
        """Notify signals detected."""
        if not signals:
            return True

        try:
            return self.notification_service.notify_signals_found(signals)
        except Exception as e:
            logger.error(f"Failed to notify signals: {e}")
            return False

    def notify_trade_executed(self, result: TradeResult) -> bool:
        """Notify trade execution."""
        if not result.success:
            return True

        try:
            return self.notification_service.notify_trade_executed(
                trade_type=result.signal.action.value,
                symbol=result.signal.symbol,
                quantity=result.quantity or 0.0,
                price=result.signal.price,
                timeframe=result.signal.timeframe,
                reason=result.signal.reason
            )
        except Exception as e:
            logger.error(f"Failed to notify trade execution: {e}")
            return False

    def send_status_update(self, portfolio: PortfolioStatus) -> bool:
        """Send portfolio status update."""
        try:
            message = self._format_status_message(portfolio)
            return self.notification_service.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
            return False

    def _format_status_message(self, portfolio: PortfolioStatus) -> str:
        """Format portfolio status message."""
        message = "📊 **PORTFOLIO STATUS**\n\n"
        message += f"💰 Total Value: ${portfolio.total_value:.2f}\n"
        message += f"💵 USDT Available: ${portfolio.usdt_balance:.2f}\n\n"

        if portfolio.positions:
            message += "📈 **Open Positions:**\n"
            for pos in portfolio.positions:
                message += f"• {pos.symbol}: {pos.quantity:.4f}\n"
        else:
            message += "📉 No open positions\n"

        message += f"\n⏰ {portfolio.timestamp.strftime('%H:%M')} UTC"

        return message
```

**Key Points**:
- Single responsibility: notification routing
- Error handling
- Message formatting

**Lines**: ~200

---

### Step 7: Create Monitoring Service (`src/daemon/monitoring_service.py`)

**Purpose**: Track daemon health and metrics.

**Implementation Requirements**:

```python
from typing import List
from loguru import logger
from datetime import datetime, timezone

from .models import Signal, TradeResult, PortfolioStatus
from .portfolio_service import PortfolioService
from .notification_handler import NotificationHandler

class MonitoringService:
    """Daemon health monitoring service."""

    def __init__(
        self,
        portfolio_service: PortfolioService,
        notification_handler: NotificationHandler
    ):
        self.portfolio_service = portfolio_service
        self.notification_handler = notification_handler
        self.signal_checks = 0
        self.trades_executed = 0
        self.trades_failed = 0
        self.start_time = datetime.now(timezone.utc)

    def record_signal_check(self, signals: List[Signal]) -> None:
        """Record signal check."""
        self.signal_checks += 1
        if signals:
            logger.info(f"Signal check #{self.signal_checks}: {len(signals)} signals found")
        else:
            logger.debug(f"Signal check #{self.signal_checks}: No signals")

    def record_trade_execution(self, result: TradeResult) -> None:
        """Record trade execution result."""
        if result.success:
            self.trades_executed += 1
            logger.info(f"Trade executed: {result.signal}")
        else:
            self.trades_failed += 1
            logger.warning(f"Trade failed: {result.error}")

    def get_health_status(self) -> dict:
        """Get daemon health status."""
        uptime = datetime.now(timezone.utc) - self.start_time
        uptime_hours = uptime.total_seconds() / 3600

        return {
            'uptime_hours': uptime_hours,
            'signal_checks': self.signal_checks,
            'trades_executed': self.trades_executed,
            'trades_failed': self.trades_failed,
            'success_rate': (
                self.trades_executed / (self.trades_executed + self.trades_failed)
                if (self.trades_executed + self.trades_failed) > 0
                else 1.0
            )
        }

    def send_periodic_report(self, watchlist: List[str]) -> None:
        """Send periodic status report."""
        try:
            portfolio = self.portfolio_service.get_portfolio_status(watchlist)
            self.notification_handler.send_status_update(portfolio)

            health = self.get_health_status()
            logger.info(
                f"Health: {health['uptime_hours']:.1f}h uptime, "
                f"{health['trades_executed']} trades, "
                f"{health['success_rate']:.1%} success rate"
            )
        except Exception as e:
            logger.error(f"Failed to send periodic report: {e}")
```

**Key Points**:
- Simple metrics tracking
- Health reporting
- Integration with portfolio service

**Lines**: ~250

---

### Step 8: Create Daemon Manager (`src/daemon/daemon_manager.py`)

**Purpose**: Main orchestrator coordinating all services.

**Implementation Requirements**:

```python
import time
from typing import List
from loguru import logger
from datetime import datetime, timezone

from .models import DaemonConfig
from .signal_processor import SignalProcessor
from .trade_executor import TradeExecutor
from .portfolio_service import PortfolioService
from .monitoring_service import MonitoringService
from .notification_handler import NotificationHandler

class DaemonManager:
    """Multi-asset trading daemon orchestrator."""

    def __init__(
        self,
        signal_processor: SignalProcessor,
        trade_executor: TradeExecutor,
        portfolio_service: PortfolioService,
        monitoring_service: MonitoringService,
        notification_handler: NotificationHandler,
        config: DaemonConfig
    ):
        self.signal_processor = signal_processor
        self.trade_executor = trade_executor
        self.portfolio_service = portfolio_service
        self.monitoring_service = monitoring_service
        self.notification_handler = notification_handler
        self.config = config

        # Daemon state
        self.running = False
        self.paused = False

    def run(self) -> None:
        """Main daemon loop."""
        logger.info("🚀 Multi-asset trading daemon started")
        self.running = True

        # Send startup notification
        watchlist = self.signal_processor.watchlist.symbols
        try:
            portfolio = self.portfolio_service.get_portfolio_status(watchlist)
            self.notification_handler.notify_daemon_started(
                watchlist=watchlist,
                capital=portfolio.total_value
            )
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")

        last_hour = datetime.now(timezone.utc).hour

        while self.running:
            try:
                if not self.paused:
                    current_hour = datetime.now(timezone.utc).hour

                    # Check signals every hour
                    if current_hour != last_hour:
                        logger.info(
                            f"🕐 Checking signals at "
                            f"{datetime.now(timezone.utc).strftime('%H:%M')} UTC"
                        )

                        self._check_and_process_signals()

                        # Send periodic status (every 6 hours)
                        if current_hour % 6 == 0:
                            self.monitoring_service.send_periodic_report(watchlist)

                        last_hour = current_hour

                # Sleep 30 seconds
                time.sleep(30)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)

        logger.info("Daemon stopped")

    def _check_and_process_signals(self) -> None:
        """Check for signals and process them."""
        # Check all signals
        signals = self.signal_processor.check_all_signals(
            self.config.timeframes
        )

        # Record check
        self.monitoring_service.record_signal_check(signals)

        if not signals:
            logger.info("No signals detected")
            return

        logger.info(f"📊 {len(signals)} signals found")

        # Notify signals found
        self.notification_handler.notify_signals_found(signals)

        # Prioritize signals
        signals = self.signal_processor.prioritize_signals(signals)

        # Process each signal
        for signal in signals:
            # Check for conflicts
            if self.signal_processor.has_conflicting_signal(signal, signals):
                logger.warning(f"Conflicting signal ignored: {signal}")
                continue

            # Calculate position size
            position_size = self.portfolio_service.calculate_position_size(
                symbol=signal.symbol,
                timeframe=signal.timeframe,
                position_sizes=self.config.position_sizes
            )

            # Execute trade
            result = self.trade_executor.execute_trade(signal, position_size)

            # Record result
            self.monitoring_service.record_trade_execution(result)

            # Notify result
            if result.success:
                self.notification_handler.notify_trade_executed(result)
            else:
                logger.warning(f"Trade failed: {result.error}")

    def stop(self) -> None:
        """Stop daemon gracefully."""
        logger.info("Stopping daemon...")
        self.running = False

    def pause(self) -> None:
        """Pause signal checking."""
        logger.info("Daemon paused")
        self.paused = True

    def resume(self) -> None:
        """Resume signal checking."""
        logger.info("Daemon resumed")
        self.paused = False
```

**Key Points**:
- Coordinates all services
- Main control loop
- Error handling
- Lifecycle management

**Lines**: ~350

---

### Step 9: Create Package Exports (`src/daemon/__init__.py`)

**Implementation Requirements**:

```python
"""
Multi-Asset Trading Daemon Package.

This package provides a modular, SOLID-compliant architecture for
automated multi-asset trading across multiple timeframes.

Main Components:
- DaemonManager: Main orchestrator
- SignalProcessor: Signal detection and filtering
- TradeExecutor: Trade execution with validation
- PortfolioService: Portfolio management
- MonitoringService: Health monitoring and metrics
- NotificationHandler: Centralized notifications

Usage:
    from src.daemon import (
        DaemonManager,
        DaemonConfig,
        create_daemon_with_dependencies
    )

    daemon = create_daemon_with_dependencies(account_id='...')
    daemon.run()
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
    SignalStrategy
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
    # Services
    'DaemonManager',
    'SignalProcessor',
    'TradeExecutor',
    'PortfolioService',
    'MonitoringService',
    'NotificationHandler',
]
```

---

### Step 10: Create Repository Implementations

**File**: `src/infrastructure/repositories/balance_repository_impl.py`

```python
from typing import Dict
from loguru import logger
import sqlite3

from src.daemon.interfaces import BalanceRepository

class BalanceRepositoryImpl(BalanceRepository):
    """SQLite implementation of BalanceRepository."""

    def __init__(self, db_path: str, account_id: str):
        self.db_path = db_path
        self.account_id = account_id

    def get_balance(self, currency: str) -> float:
        """Get available balance for currency."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT available_amount
                FROM balances
                WHERE account_id = ? AND currency = ?
            """, (self.account_id, currency))

            row = cursor.fetchone()
            return row[0] if row else 0.0

        finally:
            conn.close()

    def get_all_balances(self) -> Dict[str, float]:
        """Get all balances."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ?
            """, (self.account_id,))

            return {currency: amount for currency, amount in cursor.fetchall()}

        finally:
            conn.close()

    def update_balance(self, currency: str, amount: float, operation: str) -> bool:
        """Update balance (add/subtract)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if operation == 'add':
                # Add to balance (create if not exists)
                cursor.execute("""
                    INSERT INTO balances (account_id, currency, available_amount, reserved_amount)
                    VALUES (?, ?, ?, 0)
                    ON CONFLICT(account_id, currency)
                    DO UPDATE SET available_amount = available_amount + ?
                """, (self.account_id, currency, amount, amount))

            elif operation == 'subtract':
                # Subtract from balance
                cursor.execute("""
                    UPDATE balances
                    SET available_amount = available_amount - ?
                    WHERE account_id = ? AND currency = ?
                """, (amount, self.account_id, currency))

            else:
                logger.error(f"Unknown operation: {operation}")
                return False

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update balance: {e}")
            return False

        finally:
            conn.close()
```

**File**: `src/infrastructure/repositories/order_repository_impl.py`

```python
from datetime import datetime, timezone
import sqlite3
from loguru import logger

from src.daemon.interfaces import OrderRepository

class OrderRepositoryImpl(OrderRepository):
    """SQLite implementation of OrderRepository."""

    def __init__(self, db_path: str, account_id: str):
        self.db_path = db_path
        self.account_id = account_id

    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: str = "MARKET"
    ) -> str:
        """Create and save order. Returns order_id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            order_id = f"{side}_{symbol}_{datetime.now(timezone.utc).timestamp()}"

            cursor.execute("""
                INSERT INTO orders (
                    id, account_id, symbol, side, order_type,
                    quantity, price, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                self.account_id,
                symbol,
                side,
                order_type,
                quantity,
                price,
                'FILLED',
                datetime.now(timezone.utc).isoformat()
            ))

            # Also create transaction record
            cursor.execute("""
                INSERT INTO transactions (
                    id, account_id, transaction_type,
                    amount, currency, description, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"TX_{order_id}",
                self.account_id,
                side,
                quantity,
                symbol.replace('USDT', ''),
                f"{side} {symbol} @ ${price:.2f}",
                datetime.now(timezone.utc).isoformat()
            ))

            conn.commit()
            return order_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create order: {e}")
            raise

        finally:
            conn.close()
```

**File**: `src/infrastructure/repositories/position_repository_impl.py`

```python
from typing import Optional, List
import sqlite3
from loguru import logger

from src.daemon.interfaces import PositionRepository
from src.daemon.models import Position

class PositionRepositoryImpl(PositionRepository):
    """SQLite implementation of PositionRepository."""

    def __init__(self, db_path: str, account_id: str):
        self.db_path = db_path
        self.account_id = account_id

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for symbol."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            base_currency = symbol.replace('USDT', '')

            cursor.execute("""
                SELECT available_amount
                FROM balances
                WHERE account_id = ? AND currency = ?
            """, (self.account_id, base_currency))

            row = cursor.fetchone()

            if row and row[0] > 0:
                return Position(
                    symbol=symbol,
                    currency=base_currency,
                    quantity=row[0]
                )

            return None

        finally:
            conn.close()

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ? AND currency != 'USDT' AND available_amount > 0
            """, (self.account_id,))

            positions = []
            for currency, quantity in cursor.fetchall():
                positions.append(Position(
                    symbol=f"{currency}USDT",
                    currency=currency,
                    quantity=quantity
                ))

            return positions

        finally:
            conn.close()
```

**File**: `src/infrastructure/repositories/__init__.py`

```python
"""Repository implementations for daemon package."""

from .balance_repository_impl import BalanceRepositoryImpl
from .order_repository_impl import OrderRepositoryImpl
from .position_repository_impl import PositionRepositoryImpl

__all__ = [
    'BalanceRepositoryImpl',
    'OrderRepositoryImpl',
    'PositionRepositoryImpl',
]
```

---

### Step 11: Create New Entry Point (`scripts/multi_asset_trading_daemon.py`)

**Implementation Requirements**:

```python
#!/usr/bin/env python3
"""
Multi-Asset Trading Daemon - Entry Point

Orchestrates automated trading across multiple assets and timeframes
using a modular, SOLID-compliant architecture.
"""

import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from src.daemon import (
    DaemonManager,
    DaemonConfig,
    SignalProcessor,
    TradeExecutor,
    PortfolioService,
    MonitoringService,
    NotificationHandler
)
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.repositories import (
    BalanceRepositoryImpl,
    OrderRepositoryImpl,
    PositionRepositoryImpl
)
from src.infrastructure.notifications.telegram_helper import TradingTelegramNotifier
from scripts.watchlist_manager import WatchlistManager


class NullNotificationService:
    """Null object pattern for disabled notifications."""

    def send_message(self, message: str) -> bool:
        return True

    def notify_trade_executed(self, **kwargs) -> bool:
        return True

    def notify_daemon_started(self, **kwargs) -> bool:
        return True

    def notify_signals_found(self, signals) -> bool:
        return True


def create_daemon(account_id: str, db_path: str = 'data/jarvis_trading.db') -> DaemonManager:
    """
    Factory function to create daemon with all dependencies wired.

    Args:
        account_id: Trading account ID
        db_path: Path to SQLite database

    Returns:
        Configured DaemonManager instance
    """
    # Instantiate infrastructure
    exchange_client = BinanceRESTClient(testnet=False)
    watchlist = WatchlistManager()

    # Instantiate repositories
    balance_repo = BalanceRepositoryImpl(db_path, account_id)
    order_repo = OrderRepositoryImpl(db_path, account_id)
    position_repo = PositionRepositoryImpl(db_path, account_id)

    # Instantiate notification service
    try:
        telegram = TradingTelegramNotifier()
        notification_service = telegram
        logger.info("Telegram notifications enabled")
    except Exception as e:
        logger.warning(f"Telegram disabled: {e}")
        notification_service = NullNotificationService()

    # Instantiate domain services
    portfolio_service = PortfolioService(
        balance_repo=balance_repo,
        position_repo=position_repo,
        exchange_client=exchange_client
    )

    signal_processor = SignalProcessor(
        exchange_client=exchange_client,
        position_repo=position_repo,
        watchlist_manager=watchlist
    )

    trade_executor = TradeExecutor(
        balance_repo=balance_repo,
        order_repo=order_repo,
        position_repo=position_repo,
        notification_service=notification_service
    )

    notification_handler = NotificationHandler(
        notification_service=notification_service
    )

    monitoring_service = MonitoringService(
        portfolio_service=portfolio_service,
        notification_handler=notification_handler
    )

    # Create daemon configuration
    config = DaemonConfig(
        timeframes=['1h', '4h', '1d'],
        check_interval=3600,
        position_sizes={'1h': 0.1, '4h': 0.2, '1d': 0.3}
    )

    # Instantiate daemon manager
    daemon = DaemonManager(
        signal_processor=signal_processor,
        trade_executor=trade_executor,
        portfolio_service=portfolio_service,
        monitoring_service=monitoring_service,
        notification_handler=notification_handler,
        config=config
    )

    logger.info(f"Daemon created for account: {account_id}")
    logger.info(f"Watching {len(watchlist.symbols)} symbols: {watchlist.symbols}")

    return daemon


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-asset trading daemon with automated signal detection"
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Trading account ID"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/jarvis_trading.db",
        help="Path to SQLite database"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/multi_asset_trading.log",
        rotation="100 MB",
        retention="30 days",
        level="DEBUG"
    )

    # Create and run daemon
    daemon = create_daemon(args.account_id, args.db_path)

    try:
        daemon.run()
    except KeyboardInterrupt:
        daemon.stop()
    except Exception as e:
        logger.error(f"Daemon crashed: {e}")
        daemon.stop()
        raise


if __name__ == "__main__":
    main()
```

---

### Step 12: Create REQUIREMENTS.md Documentation

**File**: `src/daemon/REQUIREMENTS.md`

**Content**: Comprehensive documentation covering:
- Architecture overview
- Module responsibilities
- Dependency injection setup
- Usage examples
- Testing approach
- Extension points
- SOLID principles applied

(See full template in refactoring plan document)

---

## Implementation Checklist

- [ ] Create `src/daemon/` directory
- [ ] Implement `models.py` (~150 lines)
- [ ] Implement `interfaces.py` (~200 lines)
- [ ] Implement `portfolio_service.py` (~300 lines)
- [ ] Implement `signal_processor.py` (~300 lines)
- [ ] Implement `trade_executor.py` (~300 lines)
- [ ] Implement `notification_handler.py` (~200 lines)
- [ ] Implement `monitoring_service.py` (~250 lines)
- [ ] Implement `daemon_manager.py` (~350 lines)
- [ ] Implement `__init__.py` (exports)
- [ ] Create `src/infrastructure/repositories/` directory
- [ ] Implement `balance_repository_impl.py` (~150 lines)
- [ ] Implement `order_repository_impl.py` (~150 lines)
- [ ] Implement `position_repository_impl.py` (~150 lines)
- [ ] Implement repositories `__init__.py`
- [ ] Backup old daemon script
- [ ] Implement new entry point (~250 lines)
- [ ] Create `REQUIREMENTS.md` documentation
- [ ] Test CLI compatibility
- [ ] Validate all modules < 400 lines

---

## Validation Requirements

### Code Quality
- All files must use type hints
- All public methods must have docstrings
- Follow PEP 8 style guide
- Use dataclasses for models
- Use Protocol for interfaces

### Architecture
- Dependency injection throughout
- No circular dependencies
- Repository pattern for data access
- Observer pattern for notifications
- Clear separation of concerns

### Testing
- All services must be unit testable
- Mock dependencies in tests
- Integration test for full daemon workflow

### Backward Compatibility
- Same CLI interface (`--account-id`, `--db-path`)
- Same database schema (no migrations)
- Same watchlist configuration
- Same Telegram integration

---

## Success Criteria

- ✅ All modules < 400 lines
- ✅ SOLID principles applied
- ✅ Dependency injection implemented
- ✅ Repository pattern for database
- ✅ Type hints everywhere
- ✅ Comprehensive documentation
- ✅ Backward compatible CLI
- ✅ No database schema changes
- ✅ Clean separation of concerns
- ✅ Testable architecture

---

## Deliverables

1. `src/daemon/` package (9 files)
2. `src/infrastructure/repositories/` package (4 files)
3. New `scripts/multi_asset_trading_daemon.py` entry point
4. Backup of old daemon: `scripts/multi_asset_trading_daemon.py.backup`
5. `src/daemon/REQUIREMENTS.md` documentation

**Total**: 14 new files, 1 backup, ~2,750 lines of well-organized code

---

**Status**: READY FOR IMPLEMENTATION
**Assigned To**: script-developer agent
**Start Immediately**: YES
