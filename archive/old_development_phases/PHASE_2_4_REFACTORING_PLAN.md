# Phase 2.4: Multi-Asset Trading Daemon Refactoring Plan

## Executive Summary

**Target File**: `scripts/multi_asset_trading_daemon.py` (672 lines)
**Current Issues**:
- Mixed responsibilities (trading, monitoring, database, notifications)
- No dependency injection
- Hardcoded dependencies on concrete implementations
- Direct database access violating DDD principles
- No separation between domain logic and infrastructure

**Goal**: Create a modular, SOLID-compliant architecture with clear separation of concerns.

---

## Architectural Analysis

### Current Responsibilities (Violations)

The current `MultiAssetTradingDaemon` class handles:
1. **Trading Logic** - Signal checking, trade execution
2. **Database Operations** - Direct SQLite queries
3. **Portfolio Management** - Position tracking, balance queries
4. **Notification System** - Telegram integration
5. **Daemon Management** - Threading, lifecycle, scheduling
6. **Market Data** - Price fetching, indicator calculation

**Violations**:
- Single Responsibility Principle (SRP) - Does everything
- Open/Closed Principle (OCP) - Hard to extend without modification
- Dependency Inversion Principle (DIP) - Depends on concrete implementations

---

## Proposed Architecture

### Domain Layer (`src/daemon/`)

```
src/daemon/
├── __init__.py                    # Package exports
├── REQUIREMENTS.md                # Documentation
├── models.py                      # Domain models (Signal, Position, PortfolioStatus)
├── interfaces.py                  # Abstract interfaces (protocols)
├── daemon_manager.py              # Main orchestrator (< 350 lines)
├── signal_processor.py            # Signal detection and processing (< 300 lines)
├── trade_executor.py              # Trade execution logic (< 300 lines)
├── portfolio_service.py           # Portfolio management (< 300 lines)
├── monitoring_service.py          # Health monitoring and metrics (< 250 lines)
└── notification_handler.py        # Alert handling abstraction (< 200 lines)
```

### Design Patterns

1. **Strategy Pattern**: Different signal generation strategies
2. **Observer Pattern**: Event-driven notifications
3. **Dependency Injection**: Constructor-based DI for all services
4. **Repository Pattern**: Abstract database access
5. **Facade Pattern**: Simplified daemon interface

---

## Module Specifications

### 1. `models.py` - Domain Models

**Purpose**: Pure domain entities with no infrastructure dependencies.

**Classes**:
- `Signal` - Trading signal data
- `Position` - Asset position data
- `PortfolioStatus` - Portfolio snapshot
- `TradeResult` - Execution result
- `DaemonConfig` - Configuration model

**Lines**: ~150

---

### 2. `interfaces.py` - Abstract Protocols

**Purpose**: Define contracts for infrastructure dependencies.

**Protocols**:
- `ExchangeClient` - Market data and order execution
- `BalanceRepository` - Balance CRUD operations
- `OrderRepository` - Order CRUD operations
- `PositionRepository` - Position queries
- `NotificationService` - Alert sending
- `SignalStrategy` - Signal generation strategy

**Lines**: ~200

---

### 3. `daemon_manager.py` - Main Orchestrator

**Purpose**: Coordinate daemon lifecycle and workflow.

**Responsibilities**:
- Start/stop daemon
- Schedule periodic checks
- Coordinate services
- Handle daemon state (running, paused)

**Dependencies** (injected):
- `SignalProcessor`
- `TradeExecutor`
- `PortfolioService`
- `MonitoringService`
- `NotificationHandler`

**Key Methods**:
- `run()` - Main loop
- `stop()` - Graceful shutdown
- `pause()`/`resume()` - State control
- `_check_signals()` - Periodic signal check
- `_send_status_update()` - Status reporting

**Lines**: ~350

---

### 4. `signal_processor.py` - Signal Detection

**Purpose**: Detect trading signals from market data.

**Responsibilities**:
- Fetch market data via `ExchangeClient`
- Calculate indicators (MA, distance from MA)
- Generate buy/sell signals
- Filter conflicting signals
- Prioritize signals by timeframe

**Dependencies** (injected):
- `ExchangeClient`
- `PositionRepository`
- `WatchlistManager`

**Key Methods**:
- `check_signal(symbol, timeframe)` - Single signal check
- `check_all_signals()` - Batch signal check
- `prioritize_signals(signals)` - Sort by priority
- `has_conflicting_signal(signal, all_signals)` - Conflict detection

**Lines**: ~300

---

### 5. `trade_executor.py` - Trade Execution

**Purpose**: Execute trades based on signals.

**Responsibilities**:
- Calculate position sizing
- Validate trade feasibility
- Execute buy/sell orders via repositories
- Handle trade failures
- Ensure transactional consistency

**Dependencies** (injected):
- `BalanceRepository`
- `OrderRepository`
- `PositionRepository`
- `NotificationService`

**Key Methods**:
- `execute_trade(signal)` - Main execution
- `execute_buy(symbol, quantity, price, signal)` - Buy logic
- `execute_sell(symbol, quantity, price, signal)` - Sell logic
- `calculate_position_size(symbol, timeframe)` - Position sizing
- `validate_trade(signal)` - Pre-trade validation

**Lines**: ~300

---

### 6. `portfolio_service.py` - Portfolio Management

**Purpose**: Track and report portfolio status.

**Responsibilities**:
- Get current balances
- Get open positions
- Calculate portfolio value
- Track position history

**Dependencies** (injected):
- `BalanceRepository`
- `PositionRepository`
- `ExchangeClient`

**Key Methods**:
- `get_portfolio_status()` - Full portfolio snapshot
- `get_position(symbol)` - Single position query
- `get_total_value()` - Calculate total portfolio value
- `get_available_capital()` - Available USDT

**Lines**: ~300

---

### 7. `monitoring_service.py` - Health Monitoring

**Purpose**: Monitor daemon health and performance.

**Responsibilities**:
- Track uptime
- Log signal checks
- Track trade success rate
- Monitor API health
- Detect anomalies

**Dependencies** (injected):
- `PortfolioService`
- `NotificationService`

**Key Methods**:
- `record_signal_check(results)` - Log signal check
- `record_trade_execution(result)` - Log trade
- `get_health_status()` - Health check
- `send_periodic_report()` - Status report

**Lines**: ~250

---

### 8. `notification_handler.py` - Notification Abstraction

**Purpose**: Handle all notification events.

**Responsibilities**:
- Send daemon lifecycle events (started, stopped)
- Send signal notifications
- Send trade execution alerts
- Send periodic status updates

**Dependencies** (injected):
- `NotificationService` (protocol)

**Key Methods**:
- `notify_daemon_started()`
- `notify_signals_found(signals)`
- `notify_trade_executed(result)`
- `notify_status_update(portfolio)`

**Lines**: ~200

---

## Infrastructure Layer

### Existing Components (Reuse)

- `src/infrastructure/database/` - Database access (already exists)
- `src/infrastructure/exchange/binance_rest_client.py` - Exchange API
- `src/infrastructure/notifications/telegram_helper.py` - Telegram

### New Repository Implementations

Create thin wrappers in `src/infrastructure/repositories/`:

```
src/infrastructure/repositories/
├── __init__.py
├── balance_repository_impl.py      # BalanceRepository implementation
├── order_repository_impl.py        # OrderRepository implementation
└── position_repository_impl.py     # PositionRepository implementation
```

Each repository:
- Implements corresponding protocol from `interfaces.py`
- Uses `DatabaseManager` for queries
- Handles database transactions
- Returns domain models (not raw tuples)

**Lines per repository**: ~150

---

## Entry Point

### `scripts/multi_asset_trading_daemon.py` (NEW)

**Purpose**: CLI entry point with dependency injection setup.

**Responsibilities**:
- Parse CLI arguments
- Configure logging
- Instantiate all services
- Wire dependencies
- Start daemon

**Structure**:
```python
def create_daemon(account_id: str) -> DaemonManager:
    """Factory function with DI setup."""
    # Instantiate infrastructure
    exchange_client = BinanceRESTClient(testnet=False)
    db_manager = DatabaseManager()

    # Instantiate repositories
    balance_repo = BalanceRepositoryImpl(db_manager, account_id)
    order_repo = OrderRepositoryImpl(db_manager, account_id)
    position_repo = PositionRepositoryImpl(db_manager, account_id)

    # Instantiate notification service
    try:
        telegram = TradingTelegramNotifier()
        notification_service = telegram
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
        watchlist=WatchlistManager()
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

    # Instantiate daemon manager
    daemon = DaemonManager(
        signal_processor=signal_processor,
        trade_executor=trade_executor,
        portfolio_service=portfolio_service,
        monitoring_service=monitoring_service,
        notification_handler=notification_handler,
        config=DaemonConfig(
            timeframes=['1h', '4h', '1d'],
            check_interval=3600,
            position_sizes={'1h': 0.1, '4h': 0.2, '1d': 0.3}
        )
    )

    return daemon
```

**Lines**: ~250

---

## Implementation Steps

### Step 1: Create Domain Layer (Priority 1)

1. Create `src/daemon/` directory
2. Implement `models.py` - Pure domain models
3. Implement `interfaces.py` - Abstract protocols
4. Implement `portfolio_service.py` - Portfolio logic
5. Implement `signal_processor.py` - Signal generation
6. Implement `trade_executor.py` - Trade execution
7. Implement `notification_handler.py` - Notification abstraction
8. Implement `monitoring_service.py` - Health monitoring
9. Implement `daemon_manager.py` - Main orchestrator
10. Create `__init__.py` with exports
11. Create `REQUIREMENTS.md` documentation

### Step 2: Create Repository Layer (Priority 2)

1. Create `src/infrastructure/repositories/` directory
2. Implement `balance_repository_impl.py`
3. Implement `order_repository_impl.py`
4. Implement `position_repository_impl.py`
5. Create `__init__.py`

### Step 3: Create New Entry Point (Priority 3)

1. Create new `scripts/multi_asset_trading_daemon.py` with DI setup
2. Implement `create_daemon()` factory
3. Implement `main()` CLI handler
4. Test backward compatibility

### Step 4: Backup and Replace (Priority 4)

1. Backup old daemon: `scripts/multi_asset_trading_daemon.py.backup`
2. Replace with new implementation
3. Test CLI interface (same arguments)
4. Verify functionality

---

## Testing Strategy

### Unit Tests

Create `tests/daemon/`:
- `test_signal_processor.py` - Signal generation logic
- `test_trade_executor.py` - Trade execution logic
- `test_portfolio_service.py` - Portfolio calculations
- `test_notification_handler.py` - Notification routing

### Integration Tests

- `test_daemon_integration.py` - Full daemon workflow with mocks
- `test_repository_integration.py` - Repository layer with test DB

### Manual Testing

1. Run daemon with `--account-id` argument
2. Verify signals are detected
3. Verify trades are executed
4. Verify notifications are sent
5. Verify graceful shutdown

---

## Backward Compatibility

### CLI Interface (Must Preserve)

```bash
# Old
python scripts/multi_asset_trading_daemon.py --account-id=<uuid>

# New (SAME)
python scripts/multi_asset_trading_daemon.py --account-id=<uuid>
```

### Database Schema (No Changes)

- Uses existing `balances` table
- Uses existing `orders` table
- Uses existing `transactions` table
- No schema migrations needed

### Configuration (Same Files)

- Uses existing watchlist configuration
- Uses existing Telegram configuration
- No new config files

---

## Benefits of Refactoring

### SOLID Compliance

1. **Single Responsibility**: Each module has one clear purpose
2. **Open/Closed**: Easy to add new signal strategies, notification channels
3. **Liskov Substitution**: All protocols are substitutable
4. **Interface Segregation**: Minimal, focused interfaces
5. **Dependency Inversion**: Depends on abstractions, not concretions

### Testability

- All services can be unit tested with mocks
- No database needed for unit tests
- Repository pattern isolates persistence

### Maintainability

- Clear module boundaries
- Easy to locate bugs
- Easy to add features
- Self-documenting structure

### Extensibility

- Add new signal strategies (implement `SignalStrategy` protocol)
- Add new notification channels (implement `NotificationService` protocol)
- Add new exchanges (implement `ExchangeClient` protocol)
- Add new repositories (implement repository protocols)

---

## File Size Comparison

| Module | Lines | Limit | Status |
|--------|-------|-------|--------|
| Old daemon | 672 | 400 | ❌ EXCEEDED |
| **New Architecture** | | | |
| models.py | ~150 | 400 | ✅ OK |
| interfaces.py | ~200 | 400 | ✅ OK |
| daemon_manager.py | ~350 | 400 | ✅ OK |
| signal_processor.py | ~300 | 400 | ✅ OK |
| trade_executor.py | ~300 | 400 | ✅ OK |
| portfolio_service.py | ~300 | 400 | ✅ OK |
| monitoring_service.py | ~250 | 400 | ✅ OK |
| notification_handler.py | ~200 | 400 | ✅ OK |
| balance_repository_impl.py | ~150 | 400 | ✅ OK |
| order_repository_impl.py | ~150 | 400 | ✅ OK |
| position_repository_impl.py | ~150 | 400 | ✅ OK |
| Entry point | ~250 | 400 | ✅ OK |

**Total**: ~2,750 lines (well-organized, testable, maintainable)

---

## Dependencies

### External (Already in Project)

- `loguru` - Logging
- `pandas` - Data analysis
- `numpy` - Numerical operations
- `sqlite3` - Database

### Internal (Already Exist)

- `src/infrastructure/exchange/binance_rest_client.py`
- `src/infrastructure/database/database_manager.py`
- `src/infrastructure/notifications/telegram_helper.py`
- `scripts/watchlist_manager.py`

### New Internal (To Create)

- `src/daemon/` - New domain package
- `src/infrastructure/repositories/` - New repository implementations

---

## Risk Assessment

### Low Risk

- Clear separation of concerns
- Existing infrastructure reused
- Backward compatible CLI
- No database schema changes

### Medium Risk

- More files to manage (11 new files vs 1)
- Requires understanding of DI pattern

### Mitigation

- Comprehensive documentation (`REQUIREMENTS.md`)
- Clear naming conventions
- Type hints everywhere
- Integration tests

---

## Success Criteria

- ✅ All modules < 400 lines
- ✅ SOLID principles applied
- ✅ Dependency injection throughout
- ✅ Repository pattern for database access
- ✅ Backward compatible CLI
- ✅ No database schema changes
- ✅ Unit tests for all services
- ✅ Integration test for daemon
- ✅ Comprehensive documentation

---

## Timeline Estimate

**Phase 1: Domain Layer** - 2-3 hours
**Phase 2: Repository Layer** - 1 hour
**Phase 3: Entry Point** - 1 hour
**Phase 4: Testing & Documentation** - 2 hours

**Total**: ~6-7 hours of development time

---

## Next Steps

1. Review and approve this plan
2. Create `src/daemon/` directory
3. Implement domain models (`models.py`)
4. Implement interfaces (`interfaces.py`)
5. Implement services one by one
6. Create repository implementations
7. Create new entry point
8. Test and validate
9. Backup old file
10. Replace with new implementation

---

**Status**: READY FOR IMPLEMENTATION
**Assigned To**: script-developer agent
**Complexity**: MEDIUM-HIGH
**Estimated Completion**: Phase 2.4 FINAL
