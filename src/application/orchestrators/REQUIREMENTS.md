# Application Orchestrators - Requirements & Architecture

**Package:** `src/application/orchestrators/`
**Layer:** Application (DDD Architecture)
**Created:** 2025-11-15
**Phase:** Phase C - Medium Refactoring

## Purpose

Orchestrators coordinate complex workflows that span multiple domains, services, and external systems. They are part of the **Application Layer** in Domain-Driven Design (DDD) architecture.

## Key Responsibilities

Orchestrators are responsible for:
- **Workflow Coordination**: Coordinate multiple domain services, repositories, and external systems
- **Error Handling**: Handle errors gracefully with retry logic
- **Transaction Management**: Define transaction boundaries across services
- **Logging & Monitoring**: Track workflow execution and results
- **State Management**: Maintain workflow state during execution

## What Orchestrators DO NOT Do

Orchestrators contain NO business logic. They should NOT:
- ❌ Implement business rules (belongs in domain layer)
- ❌ Directly access databases (use repositories)
- ❌ Make external API calls directly (use infrastructure services)
- ❌ Perform calculations (use domain services)
- ❌ Validate business data (use value objects/entities)

## Architecture

### Layer Hierarchy (DDD)

```
┌─────────────────────────────────────┐
│   Entry Points (scripts/)          │  ← CLI, config, logging
├─────────────────────────────────────┤
│   Application Layer                 │
│   - Orchestrators ✓ (workflow)     │  ← This package
│   - Use Cases (single operation)    │
│   - Application Services            │
├─────────────────────────────────────┤
│   Domain Layer                      │
│   - Entities, Value Objects         │
│   - Domain Services (logic)         │
│   - Repository Interfaces           │
├─────────────────────────────────────┤
│   Infrastructure Layer              │
│   - Database (SQLite)               │
│   - External APIs (Binance)         │
│   - Repository Implementations      │
└─────────────────────────────────────┘
```

### Orchestrator vs Service

| Aspect | Domain Service | Orchestrator |
|--------|---------------|--------------|
| **Location** | `src/domain/{domain}/services/` | `src/application/orchestrators/` |
| **Scope** | Single domain | Multi-domain |
| **Logic** | Business logic | Workflow coordination |
| **Dependencies** | Domain entities, value objects | Services, repositories, external systems |
| **Example** | `calculate_fibonacci_levels()` | `execute_trading_workflow()` |

## SOLID Principles Compliance

### ✓ Single Responsibility Principle (SRP)
- Each orchestrator coordinates ONE specific workflow
- No business logic (that's in domain services)
- No data access (that's in repositories)

### ✓ Open/Closed Principle (OCP)
- Extend functionality by creating new orchestrators
- Don't modify existing orchestrators
- Base class provides common functionality

### ✓ Liskov Substitution Principle (LSP)
- All orchestrators implement `BaseOrchestrator` interface
- Can be used interchangeably where `BaseOrchestrator` is expected
- Consistent return format (result dict)

### ✓ Interface Segregation Principle (ISP)
- Minimal interface: `execute()` + error handling
- Orchestrators only implement what they need
- No forced dependencies on unused methods

### ✓ Dependency Inversion Principle (DIP)
- Depend on abstractions (TradingStrategy, AccountRepository)
- Not on concrete implementations
- Constructor injection for all dependencies

## Package Structure

```
src/application/orchestrators/
├── __init__.py                              # Package exports
├── base.py                                  # BaseOrchestrator (abstract)
├── fibonacci_trading_orchestrator.py        # Fibonacci workflow
├── paper_trading_orchestrator.py            # Generic paper trading
└── REQUIREMENTS.md                          # This file
```

## Components

### 1. BaseOrchestrator (base.py)

**Abstract base class** for all orchestrators.

**Interface:**
```python
class BaseOrchestrator(ABC):
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the orchestrated workflow."""
        pass
```

**Provides:**
- Error handling with retry logic
- Execution logging (start/end)
- Standard result format

**Return format:**
```python
{
    'status': 'success' | 'failure',
    'data': <workflow results>,
    'error': <error message if failed>,
    'metadata': <execution metadata>
}
```

### 2. FibonacciTradingOrchestrator

**Specific orchestrator** for Fibonacci Golden Zone trading workflow.

**Workflow:**
1. Fetch market data from Binance
2. Generate signal using Fibonacci strategy
3. Get current account position
4. Execute trade if BUY/SELL signal
5. Return results

**Dependencies:**
- `FibonacciGoldenZoneStrategy` (strategy)
- `BinanceRESTClient` (market data)
- `SQLiteAccountRepository` (persistence)
- `DatabaseManager` (database)

**Usage:**
```python
from src.application.orchestrators import FibonacciTradingOrchestrator

orchestrator = FibonacciTradingOrchestrator(
    account_id="uuid",
    symbol="BNB_USDT",
    timeframe="1d",
    db_path="data/db.sqlite",
    dry_run=False
)

result = orchestrator.execute()

if result['status'] == 'success':
    print(f"Trade executed: {result['trade_executed']}")
    print(f"Signal: {result['signal']['action']}")
```

### 3. PaperTradingOrchestrator

**Generic orchestrator** for paper trading with ANY strategy.

**Benefits:**
- Strategy-agnostic (accepts any `TradingStrategy`)
- Reusable across different strategies
- Follows Strategy Pattern (OCP principle)

**Dependencies:**
- `TradingStrategy` (any implementation)
- `BinanceRESTClient` (market data)
- `SQLiteAccountRepository` (persistence)
- `DatabaseManager` (database)

**Usage:**
```python
from src.application.orchestrators import PaperTradingOrchestrator
from src.strategies import FibonacciGoldenZoneStrategy

strategy = FibonacciGoldenZoneStrategy()
orchestrator = PaperTradingOrchestrator(
    account_id="uuid",
    strategy=strategy,  # Any strategy!
    symbol="BTC_USDT",
    timeframe="4h",
    db_path="data/db.sqlite"
)

result = orchestrator.execute()
```

## Integration with Entry Points

Entry point scripts (in `scripts/`) are thin wrappers that:
1. Parse CLI arguments
2. Configure logging
3. Create orchestrator instance
4. Execute workflow
5. Handle results

**Example:** `scripts/run_fibonacci_strategy.py`

**Before refactoring:** 525 lines (monolithic)
**After refactoring:** 171 lines (thin wrapper)
**Reduction:** 354 lines (67%)

**Responsibilities:**
```python
# Entry point (scripts/run_fibonacci_strategy.py)
def main():
    args = parse_arguments()        # CLI args
    configure_logging()             # Logging setup
    orchestrator = create_orchestrator(args)  # Create
    result = orchestrator.execute() # Execute
    handle_result(result)           # Handle result
```

## Error Handling

Orchestrators handle errors at the workflow level:

```python
try:
    # Execute workflow steps
    data = fetch_data()
    signal = generate_signal(data)
    execute_trade(signal)
    return {'status': 'success', ...}

except Exception as e:
    return self._handle_error(
        error=e,
        context={'step': 'fetch_data', ...}
    )
```

**Error handling features:**
- Retry logic (configurable max retries)
- Context preservation (for debugging)
- Graceful degradation
- Detailed error logging

## Testing Strategy

### Unit Tests
Test individual orchestrators in isolation:
- Mock all dependencies (strategy, repository, client)
- Test workflow coordination logic
- Test error handling
- Test retry logic

### Integration Tests
Test orchestrators with real dependencies:
- Use test database
- Use mock Binance API (testnet)
- Test complete workflow end-to-end
- Verify database persistence

### Example Test
```python
def test_fibonacci_trading_orchestrator_buy_signal():
    # Mock dependencies
    mock_strategy = Mock(spec=FibonacciGoldenZoneStrategy)
    mock_strategy.generate_signal.return_value = {
        'action': 'BUY',
        'entry': 100.0,
        'stop_loss': 95.0,
        'take_profit_1': 110.0,
        'take_profit_2': 120.0
    }

    # Create orchestrator with mocks
    orchestrator = FibonacciTradingOrchestrator(...)
    orchestrator.strategy = mock_strategy

    # Execute
    result = orchestrator.execute()

    # Assert
    assert result['status'] == 'success'
    assert result['trade_executed'] == True
    assert result['signal']['action'] == 'BUY'
```

## Metrics

### Line Count Analysis

| Component | Lines | Purpose |
|-----------|-------|---------|
| `base.py` | 181 | Base class + error handling |
| `fibonacci_trading_orchestrator.py` | 533 | Fibonacci workflow |
| `paper_trading_orchestrator.py` | 354 | Generic paper trading |
| `__init__.py` | 65 | Package exports |
| **Total** | **1,133** | Orchestrators package |

### Refactoring Impact

**run_fibonacci_strategy.py:**
- Before: 525 lines (monolithic class + main)
- After: 171 lines (thin wrapper)
- Reduction: 354 lines (67%)
- Business logic: Moved to orchestrator

**Benefits:**
- Clear separation of concerns
- Reusable workflow logic
- Testable in isolation
- Easier to maintain

## Dependencies

### Internal (Framework)
- `src/strategies/` - Trading strategies
- `src/domain/account/` - Account management
- `src/domain/market_data/` - Market data services
- `src/infrastructure/database/` - Database management
- `src/infrastructure/exchange/` - Exchange clients
- `src/infrastructure/persistence/` - Repositories

### External (PyPI)
- `pandas` - Data manipulation
- `loguru` - Logging
- `asyncio` - Async support (for daemon mode)

## Future Orchestrators

Potential orchestrators to create:

1. **BacktestingOrchestrator**: Coordinate backtesting workflow
   - Load historical data
   - Run strategy against data
   - Calculate metrics
   - Generate report

2. **LiveTradingOrchestrator**: Coordinate live trading
   - Real-time data streaming
   - Risk management
   - Order execution
   - Position monitoring

3. **PortfolioRebalancingOrchestrator**: Rebalance portfolio
   - Analyze current allocation
   - Calculate target allocation
   - Generate rebalancing trades
   - Execute rebalancing

4. **MarketAnalysisOrchestrator**: Analyze market conditions
   - Fetch multi-timeframe data
   - Run multiple indicators
   - Aggregate analysis results
   - Generate market report

## Best Practices

### 1. Keep Orchestrators Thin
- Delegate to services and repositories
- No business logic in orchestrators
- Only coordination and error handling

### 2. Use Dependency Injection
```python
def __init__(self, strategy: TradingStrategy, repository: AccountRepository):
    self.strategy = strategy      # Injected
    self.repository = repository  # Injected
```

### 3. Standard Result Format
```python
return {
    'status': 'success' | 'failure',
    'data': {...},
    'error': None | "error message",
    'timestamp': datetime.utcnow().isoformat()
}
```

### 4. Comprehensive Logging
```python
self._log_execution_start(workflow_name, params)
# ... workflow steps ...
self._log_execution_end(workflow_name, result, duration)
```

### 5. Graceful Error Handling
```python
try:
    # Workflow
    pass
except Exception as e:
    return self._handle_error(error=e, context={...})
```

## References

- **DDD Architecture**: Eric Evans - Domain-Driven Design
- **SOLID Principles**: Robert C. Martin - Clean Architecture
- **Strategy Pattern**: Gang of Four - Design Patterns
- **Orchestration Pattern**: Martin Fowler - Enterprise Integration Patterns

## See Also

- `src/strategies/REQUIREMENTS.md` - Strategy Pattern implementation
- `src/domain/account/REQUIREMENTS.md` - Account domain
- `PHASE_B_COMPLETION.md` - Strategies package refactoring
- `COMPLETION_ROADMAP.md` - Full refactoring roadmap

---

**Last Updated:** 2025-11-15
**Version:** 1.0
**Status:** Complete ✓
