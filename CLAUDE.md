# Jarvis Trading - Development Guidelines

This document contains critical guidelines for development within the jarvis_trading project.

## Architecture Overview

**Jarvis Trading** follows strict **Domain-Driven Design (DDD)** and **SOLID principles**.

### Core Domains

```
jarvis_trading/src/domain/
├── market/               # Market data domain
│   ├── entities/
│   ├── services/
│   ├── repositories/
│   └── value_objects/
├── features/             # Feature engineering domain
├── trading/              # Trading logic domain
└── reinforcement_learning/  # RL domain
```

Each domain is **completely independent** and communicates via interfaces.

## Development Rules

### 1. File Organization (CRITICAL)

**Maximum file sizes**:
- Python: 400 lines (hard limit)
- Tests: 500 lines
- Scripts: 300 lines

**If file exceeds limit**: Break into multiple files in same package.

**Example - WRONG**:
```python
# market_service.py - 600 lines (TOO BIG)
class DataFetcher:
    ...
class DataValidator:
    ...
class DataCache:
    ...
```

**Example - CORRECT**:
```
market/services/
├── data_fetcher.py      # 150 lines
├── data_validator.py    # 120 lines
└── data_cache.py        # 100 lines
```

### 2. DDD Structure (MANDATORY)

Every domain must have:

```python
# domain/market/entities/candlestick.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Candlestick:
    """Entity: Represents a price candlestick"""
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float

    def is_bullish(self) -> bool:
        return self.close_price > self.open_price
```

```python
# domain/market/value_objects/timeframe.py
from enum import Enum

class Timeframe(Enum):
    """Value Object: Immutable timeframe"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    ONE_HOUR = "1h"

    def to_seconds(self) -> int:
        ...
```

```python
# domain/market/repositories/candlestick_repository.py
from abc import ABC, abstractmethod

class CandlestickRepository(ABC):
    """Repository: Abstracted data access"""

    @abstractmethod
    def save(self, candlestick: Candlestick) -> None:
        pass

    @abstractmethod
    def find_by_timestamp(self, timestamp: datetime) -> Candlestick:
        pass
```

```python
# domain/market/services/market_data_service.py
class MarketDataService:
    """Service: Domain logic"""

    def __init__(self, repository: CandlestickRepository):
        self.repository = repository

    def fetch_and_validate(self, pair: str, timeframe: str) -> List[Candlestick]:
        # Business logic here
        pass
```

### 3. SOLID Principles (CRITICAL)

#### S - Single Responsibility

```python
# WRONG: Multiple responsibilities
class MarketFetcher:
    def fetch_data(self):
        # Fetching
        pass

    def validate_data(self):
        # Validation
        pass

    def cache_data(self):
        # Caching
        pass
```

```python
# CORRECT: Single responsibility
class DataFetcher:
    def fetch_data(self):
        pass

class DataValidator:
    def validate(self, data):
        pass

class DataCache:
    def cache(self, data):
        pass
```

#### O - Open/Closed

```python
# WRONG: Closed for extension
class IndicatorCalculator:
    def calculate(self, indicator_type: str):
        if indicator_type == "RSI":
            return self.rsi()
        elif indicator_type == "MACD":
            return self.macd()
        # Adding new indicator requires modifying this class
```

```python
# CORRECT: Open for extension
from abc import ABC, abstractmethod

class Indicator(ABC):
    @abstractmethod
    def calculate(self, data: np.ndarray) -> np.ndarray:
        pass

class RSI(Indicator):
    def calculate(self, data):
        return self.rsi(data)

class MACD(Indicator):
    def calculate(self, data):
        return self.macd(data)

# Adding new indicator: Create new class inheriting Indicator
```

#### L - Liskov Substitution

```python
# WRONG: Subclass violates contract
class Repository(ABC):
    @abstractmethod
    def find(self, id: int):
        pass

class BrokenRepository(Repository):
    def find(self, id: int):
        raise NotImplementedError()  # Violates contract!
```

```python
# CORRECT: Subclass honors contract
class SQLiteRepository(Repository):
    def find(self, id: int):
        return self.db.query(id)  # Always fulfills contract
```

#### I - Interface Segregation

```python
# WRONG: Fat interface
class TradingService(ABC):
    @abstractmethod
    def fetch_data(self): pass
    @abstractmethod
    def engineer_features(self): pass
    @abstractmethod
    def generate_signals(self): pass
    @abstractmethod
    def execute_trade(self): pass
    @abstractmethod
    def log_metrics(self): pass
```

```python
# CORRECT: Segregated interfaces
class DataProvider(ABC):
    @abstractmethod
    def fetch_data(self): pass

class FeatureEngineer(ABC):
    @abstractmethod
    def engineer_features(self): pass

class SignalGenerator(ABC):
    @abstractmethod
    def generate_signals(self): pass
```

#### D - Dependency Inversion

```python
# WRONG: Direct dependency on concrete class
class TrainingPipeline:
    def __init__(self):
        self.db = SQLiteDatabase()  # Tight coupling!

    def run(self):
        data = self.db.fetch()
```

```python
# CORRECT: Dependency injection
class TrainingPipeline:
    def __init__(self, repository: DataRepository):
        self.repository = repository  # Loose coupling

    def run(self):
        data = self.repository.fetch()
```

### 4. Naming Conventions

**Classes**:
- Entities: Noun (e.g., `Candlestick`, `TradingSignal`)
- Services: Noun + "Service" (e.g., `MarketDataService`)
- Repositories: Noun + "Repository" (e.g., `CandlestickRepository`)
- Value Objects: Noun (e.g., `Timeframe`, `Price`)

**Methods**:
- Queries: `get_*`, `find_*` (e.g., `get_candlesticks`, `find_by_timestamp`)
- Commands: `*` or `create_*`, `save_*` (e.g., `save`, `create_signal`)
- Booleans: `is_*`, `has_*` (e.g., `is_bullish`, `has_volume`)

**Constants**:
- ALL_CAPS (e.g., `DEFAULT_TIMEFRAME = "1h"`)

### 5. Type Hints (MANDATORY)

```python
# WRONG: No type hints
def fetch_data(pair, timeframe):
    ...

def calculate_rsi(data, periods):
    ...
```

```python
# CORRECT: Full type hints
from typing import List, Dict
import numpy as np

def fetch_data(pair: str, timeframe: str) -> List[Candlestick]:
    ...

def calculate_rsi(data: np.ndarray, periods: int = 14) -> np.ndarray:
    ...
```

### 6. Error Handling (CRITICAL)

**NEVER silently fail**. Always propagate errors with context.

```python
# WRONG: Silent failure
def fetch_from_binance(pair: str):
    try:
        return client.get_klines(pair)
    except:
        return None  # User doesn't know what happened!
```

```python
# CORRECT: Explicit error handling
class BinanceException(Exception):
    """Base exception for Binance operations"""
    pass

class FetchFailedException(BinanceException):
    """Raised when data fetch fails"""
    pass

def fetch_from_binance(pair: str) -> List[Candlestick]:
    try:
        return client.get_klines(pair)
    except ConnectionError as e:
        raise FetchFailedException(f"Failed to fetch {pair}: {e}") from e
    except ValueError as e:
        raise FetchFailedException(f"Invalid response format: {e}") from e
```

### 7. Testing (MANDATORY)

**Test structure**:
```
tests/
├── unit/
│   ├── domain/
│   │   ├── market/
│   │   │   ├── test_candlestick.py
│   │   │   └── test_market_data_service.py
│   │   └── features/
│   └── application/
├── integration/
│   ├── test_journey_1.py
│   ├── test_journey_2.py
│   └── test_journey_3.py
└── fixtures/
    └── market_data_fixtures.py
```

**Test naming**:
```python
def test_candlestick_is_bullish_when_close_greater_than_open():
    """Clear description of what is tested"""
    candlestick = Candlestick(open_price=100, close_price=101, ...)
    assert candlestick.is_bullish()
```

**Minimum coverage**: 80% of critical paths

### 8. Documentation (MANDATORY)

**Module docstrings**:
```python
"""
Market domain services.

This module provides services for fetching, validating, and caching
market data from external exchanges.

Example:
    >>> service = MarketDataService(repository)
    >>> candlesticks = service.fetch_candlesticks("BTCUSDT", "1h")
"""
```

**Class docstrings**:
```python
class Candlestick:
    """
    Entity representing a price candlestick (OHLCV).

    A candlestick represents price movement within a time period.

    Attributes:
        timestamp: When the candlestick closed
        open_price: Opening price
        close_price: Closing price
        volume: Trading volume
    """
```

**Method docstrings**:
```python
def is_bullish(self) -> bool:
    """
    Check if candlestick is bullish.

    Returns:
        True if close > open, False otherwise
    """
```

### 9. Configuration Management

**Configuration via YAML**:
```yaml
# config/trading.yaml
trading:
  pair: BTCUSDT
  interval: 1h
  lookback: 500

features:
  indicators:
    - rsi
    - macd
    - bollinger_bands
```

**Load configuration**:
```python
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    trading_pair: str = "BTCUSDT"
    trading_interval: str = "1h"

    class Config:
        env_file = ".env"
```

### 10. Logging (MANDATORY)

```python
from loguru import logger

def fetch_market_data(pair: str) -> List[Candlestick]:
    logger.info(f"Fetching market data for {pair}")
    try:
        data = _internal_fetch(pair)
        logger.debug(f"Fetched {len(data)} candlesticks")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch {pair}: {e}", exc_info=True)
        raise
```

## Code Review Checklist

Before submitting code:

- [ ] Follows SOLID principles (reviewed each principle)
- [ ] DDD structure correct (entities, services, repositories)
- [ ] Type hints complete (all parameters and returns)
- [ ] Error handling explicit (no silent failures)
- [ ] Tests added (minimum 80% coverage)
- [ ] Documentation added (module, class, method)
- [ ] File size < 400 lines (split if larger)
- [ ] Naming conventions followed (classes, methods, constants)
- [ ] No hardcoded values (use config or constants)
- [ ] No mock failures (only real error handling)

## Common Anti-Patterns to Avoid

### 1. God Classes

```python
# WRONG: One class doing everything
class TradingSystem:
    def fetch_data(self): pass
    def engineer_features(self): pass
    def generate_signals(self): pass
    def execute_trade(self): pass
    def log_metrics(self): pass
```

**Fix**: Break into separate domain services.

### 2. Circular Dependencies

```python
# WRONG: A depends on B, B depends on A
# market/repository.py
from features.service import FeatureService

# features/service.py
from market.repository import MarketRepository
```

**Fix**: Use dependency injection; create mediator if needed.

### 3. Hardcoded Values

```python
# WRONG: Magic numbers
def calculate_rsi(data):
    return rsi(data, 14)  # Where does 14 come from?
```

**Fix**: Use constants or configuration
```python
RSI_PERIOD = 14

def calculate_rsi(data, period: int = RSI_PERIOD):
    return rsi(data, period)
```

### 4. Silent Failures

```python
# WRONG: Exception swallowed
try:
    return fetch_data()
except:
    return default_value()  # User doesn't know what failed!
```

**Fix**: Explicit error handling with logging.

## Performance Considerations

### Data Pipeline
- Cache market data (24h expiry)
- Use vectorized NumPy operations
- Batch Binance API calls

### Feature Engineering
- Incremental feature computation
- Drop low-correlation features
- Parallelize where possible

### RL Training
- Use GPU acceleration (PyTorch)
- Vectorized environment (Gym)
- Efficient replay buffer

## Security Guidelines

- **Never commit .env files**
- **Validate all external input** (API responses, user input)
- **Use HTTPS for external APIs**
- **Rotate API keys regularly**
- **Log security events** (failed auth, suspicious activity)

## Deployment Checklist

Before deploying:

- [ ] All tests passing (pytest)
- [ ] Code coverage > 80%
- [ ] Linting clean (flake8)
- [ ] Type checking passes (mypy)
- [ ] Documentation updated
- [ ] .env configured correctly
- [ ] No hardcoded secrets
- [ ] Performance tested
- [ ] Error logging configured

## Quick Reference Commands

```bash
# Development
make dev-install    # Install with dev tools
make format        # Format code
make lint          # Check quality
make test          # Run tests

# Running journeys
make run-journey1  # Data pipeline
make run-journey2  # Feature engineering
make run-journey3  # MTF combination
make run-journey4  # RL training

# Cleanup
make clean         # Remove build artifacts
```

## Getting Help

1. **Architecture questions**: Check `docs/ARCHITECTURE.md`
2. **API questions**: Check `docs/API.md`
3. **Journey implementation**: Check `docs/JOURNEYS.md`
4. **MLOps setup**: Check `docs/MLOps.md`

## References

- Domain-Driven Design: https://martinfowler.com/bliki/DomainDrivenDesign.html
- SOLID Principles: https://en.wikipedia.org/wiki/SOLID
- Clean Code: https://www.oreilly.com/library/view/clean-code-a/9780136083238/
- Python Type Hints: https://docs.python.org/3/library/typing.html

---

**Remember**: Good architecture is not about perfection, it's about making the codebase easy to understand and modify.
