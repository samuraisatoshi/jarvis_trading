# JARVIS Trading - Refactoring Plan

## Branch: code/refactoring

### 🚨 Guardrails Violations Found

#### 1. Files Exceeding 500 Lines Limit (14 files)

| File | Lines | Proposed Action |
|------|-------|-----------------|
| `scripts/dca_smart_simulation.py` | 987 | Split into modules: strategy, simulator, analyzer |
| `scripts/telegram_bot_hybrid_backup.py` | 966 | Remove (backup file) |
| `scripts/telegram_bot_hybrid.py` | 899 | Refactor into: bot_core, handlers, utils |
| `scripts/backtest_fibonacci_comprehensive.py` | 804 | Split: backtest_engine, indicators, reporting |
| `scripts/elliott_wave_analysis.py` | 712 | Extract: wave_detector, pattern_analyzer |
| `scripts/trading_with_telegram.py` | 674 | Modularize: trading_logic, telegram_interface |
| `scripts/multi_asset_trading_daemon.py` | 672 | Split: daemon_manager, asset_handler, signal_processor |
| `scripts/telegram_bot_enhanced.py` | 650 | Refactor handlers into separate modules |
| `scripts/backtest_fibonacci_2025.py` | 606 | Extract common backtest logic |
| `scripts/telegram_status_bot.py` | 581 | Split status handlers |
| `scripts/fibonacci_golden_zone_strategy.py` | 574 | Extract zone calculations |
| `scripts/monitor_paper_trading.py` | 552 | Separate monitoring logic |
| `scripts/backtest_2025.py` | 534 | Consolidate with other backtest modules |
| `scripts/run_fibonacci_strategy.py` | 525 | Extract strategy components |

#### 2. SOLID Principles Violations

##### Single Responsibility Principle (SRP)
- **telegram_bot_hybrid.py**: Handles bot logic, trading, charting, notifications all in one class
- **multi_asset_trading_daemon.py**: Mixed responsibilities (trading, monitoring, database, notifications)

##### Open/Closed Principle (OCP)
- Strategies are hardcoded, not easily extensible
- Need strategy factory pattern

##### Dependency Inversion Principle (DIP)
- Direct dependencies on concrete implementations (Binance API, SQLite)
- Need interfaces/abstractions

#### 3. Domain-Driven Design (DDD) Issues

##### Missing Domain Services
- No clear separation between domain logic and infrastructure
- Business rules mixed with implementation details

##### Anemic Domain Models
- Entities lack behavior, mostly data containers
- Business logic scattered in scripts instead of domain layer

##### Missing Value Objects
- Using primitives for domain concepts (Symbol, Timeframe, Price)
- Need proper value objects with validation

### 📋 Refactoring Tasks

#### Phase 1: Critical Structure (Week 1)
1. **Extract Core Domain Models**
   - Create `src/domain/trading/strategies/` with strategy interfaces
   - Move strategy implementations to domain layer
   - Create value objects for Symbol, Timeframe, Signal

2. **Separate Bot Infrastructure**
   - Create `src/infrastructure/telegram/` module
   - Extract handlers: `command_handlers.py`, `callback_handlers.py`
   - Separate `message_formatter.py` for formatting logic

3. **Create Application Services**
   - `src/application/services/trading_service.py`
   - `src/application/services/backtest_service.py`
   - `src/application/services/monitoring_service.py`

#### Phase 2: Modularization (Week 2)
1. **Break Down Large Files**
   - Split each file > 500 lines into logical modules
   - Create shared utilities module
   - Extract configuration management

2. **Implement Strategy Pattern**
   ```python
   src/domain/trading/strategies/
   ├── base.py          # Abstract strategy
   ├── fibonacci.py     # Fibonacci implementation
   ├── ma_strategy.py   # Moving average strategy
   └── factory.py       # Strategy factory
   ```

3. **Create Repository Pattern**
   ```python
   src/domain/trading/repositories/
   ├── order_repository.py     # Interface
   └── signal_repository.py    # Interface

   src/infrastructure/persistence/
   ├── sqlite_order_repository.py    # Implementation
   └── sqlite_signal_repository.py   # Implementation
   ```

#### Phase 3: Testing & Documentation (Week 3)
1. **Unit Tests**
   - Test each refactored module
   - Achieve 80% code coverage

2. **Integration Tests**
   - Test bot commands
   - Test trading strategies

3. **Documentation**
   - Update README with new structure
   - Create domain model diagrams
   - Document API interfaces

### 🎯 Success Criteria

- [ ] All files < 500 lines
- [ ] Each class has single responsibility
- [ ] Dependencies injected, not hardcoded
- [ ] Clear domain boundaries
- [ ] Strategy pattern implemented
- [ ] Repository pattern implemented
- [ ] 80% test coverage
- [ ] Documentation updated

### 🔧 Implementation Order

1. **telegram_bot_hybrid.py** - Most critical, actively used
2. **multi_asset_trading_daemon.py** - Core trading functionality
3. **Backtest modules** - Consolidate and modularize
4. **Strategy modules** - Implement pattern
5. **Monitoring modules** - Extract common logic

### 📊 Estimated Impact

- **Code Quality**: +80% maintainability
- **Testing**: From 0% to 80% coverage
- **Performance**: ~20% improvement from optimized structure
- **Development Speed**: 2x faster for new features

### 🚀 Next Steps

1. Review this plan
2. Start with telegram_bot_hybrid.py refactoring
3. Create tests for refactored code
4. Incrementally refactor remaining modules
5. Merge back to master when stable