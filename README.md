# Jarvis Trading - Multi-Journey RL Trading System

A sophisticated reinforcement learning trading system inspired by FinRL architecture, implementing 4 integrated journeys for cryptocurrency trading with adaptive multi-timeframe analysis.

## Overview

**Jarvis Trading** is a production-ready trading system built with domain-driven design (DDD) and SOLID principles. It orchestrates multiple specialized journeys to create an intelligent trading agent that adapts to market conditions.

### Key Features

- **4 Integrated Journeys**:
  1. **Data Pipeline** - Real-time market data capture with caching
  2. **Feature Engineering** - Auto-selecting technical indicators
  3. **MTF Combination** - Adaptive multi-timeframe analysis
  4. **RL Training** - Ensemble reinforcement learning with MLOps

- **Architecture**:
  - Domain-Driven Design (DDD)
  - SOLID principles
  - Microservice-ready
  - Full test coverage
  - MLOps integration (MLFlow, WandB)

- **Technology Stack**:
  - Python 3.11+
  - PyTorch + Stable-Baselines3
  - Binance API
  - FastAPI (optional deployment)
  - MLFlow + WandB monitoring

## Project Structure

```
jarvis_trading/
├── src/
│   ├── domain/                     # DDD domains
│   │   ├── market/                 # Market data domain
│   │   ├── features/               # Feature engineering domain
│   │   ├── trading/                # Trading logic domain
│   │   └── reinforcement_learning/ # RL domain
│   ├── application/                # Use cases & orchestration
│   ├── infrastructure/             # External services (Binance, MLFlow, etc)
│   └── shared/                     # Common utilities & types
├── scripts/
│   ├── journey_1_data_pipeline.py
│   ├── journey_2_feature_engineering.py
│   ├── journey_3_mtf_combination.py
│   └── journey_4_rl_training.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── config/
│   ├── trading.yaml
│   ├── rl.yaml
│   └── feature_engineering.yaml
├── data/
│   ├── cache/                      # Market data cache
│   ├── raw/                        # Raw market data
│   └── processed/                  # Processed datasets
├── models/
│   ├── trained/                    # Trained RL agents
│   └── checkpoints/                # Training checkpoints
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── JOURNEYS.md
│   └── MLOps.md
└── .claude/
    ├── agents/                     # Custom agents
    └── skills/                     # Custom skills
```

## Quick Start

### 1. Setup Environment

```bash
cd jarvis_trading
make venv          # Create virtual environment
make dev-install   # Install dependencies with dev tools
cp .env.example .env
```

### 2. Configure Binance API

Edit `.env` and add your Binance credentials:

```env
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_API_TESTNET=true  # Start with testnet
```

### 3. Run Individual Journeys

```bash
# Journey 1: Fetch and cache market data
make run-journey1

# Journey 2: Engineer features from raw data
make run-journey2

# Journey 3: Combine multi-timeframe signals
make run-journey3

# Journey 4: Train RL agent
make run-journey4
```

### 4. Run Tests

```bash
make test          # Run all tests with coverage
make lint          # Check code quality
make format        # Auto-format code
```

## Journeys Explained

### Journey 1: Data Pipeline

**Purpose**: Real-time market data capture with intelligent caching

**Components**:
- Multi-timeframe data fetching (1m, 5m, 15m, 1h, 4h, 1d)
- SQLite-based cache for offline analysis
- Data validation and quality checks
- Automatic cache expiry management

**Input**: Trading pair (e.g., BTCUSDT)
**Output**: Processed OHLCV data in cache

**Script**: `scripts/journey_1_data_pipeline.py`

### Journey 2: Feature Engineering

**Purpose**: Auto-select and engineer relevant technical indicators

**Components**:
- 30+ technical indicators (RSI, MACD, Bollinger Bands, etc)
- Correlation analysis for feature selection
- Auto-scaling and normalization
- Feature importance ranking

**Input**: Raw market data
**Output**: Feature matrix for ML training

**Script**: `scripts/journey_2_feature_engineering.py`

### Journey 3: MTF Combination

**Purpose**: Adaptive multi-timeframe analysis

**Components**:
- Timeframe hierarchies (1m → 1h → 1d)
- Signal combination strategies
- Adaptive weights based on market regime
- Trend confirmation logic

**Input**: Features from Journey 2
**Output**: Combined trading signals

**Script**: `scripts/journey_3_mtf_combination.py`

### Journey 4: RL Training

**Purpose**: Ensemble reinforcement learning with production MLOps

**Components**:
- PPO + SAC algorithms (Stable-Baselines3)
- Ensemble voting strategy
- MLFlow experiment tracking
- Optuna hyperparameter optimization
- Portfolio backtesting

**Input**: Combined signals from Journey 3
**Output**: Trained RL agent + performance metrics

**Script**: `scripts/journey_4_rl_training.py`

## Architecture Principles

### Domain-Driven Design (DDD)

The system is organized around business domains:

- **Market Domain**: Data fetching, caching, validation
- **Features Domain**: Technical analysis, feature engineering
- **Trading Domain**: Signal generation, decision making
- **RL Domain**: Agent training, optimization, backtesting

Each domain has:
- `entities/` - Core business objects
- `services/` - Domain logic
- `repositories/` - Data access
- `value_objects/` - Immutable value types

### SOLID Principles

- **S**ingle Responsibility: Each class has one reason to change
- **O**pen/Closed: Open for extension, closed for modification
- **L**iskov Substitution: Interfaces follow contracts
- **I**nterface Segregation: Specific interfaces, not monolithic
- **D**ependency Inversion: Depend on abstractions

### Key Patterns

- **Repository Pattern**: Abstracted data access
- **Factory Pattern**: Complex object creation
- **Strategy Pattern**: Pluggable algorithms (indicators, RL agents)
- **Observer Pattern**: Event-driven architecture
- **Decorator Pattern**: Feature engineering pipelines

## Configuration

### Trading Configuration (`config/trading.yaml`)

```yaml
trading:
  pair: BTCUSDT
  interval: "1h"
  lookback_periods: 500

data_pipeline:
  timeframes: ["1m", "5m", "15m", "1h", "4h", "1d"]
  cache_enabled: true
  cache_expiry_hours: 24
```

### RL Configuration (`config/rl.yaml`)

```yaml
environment:
  initial_balance: 10000
  transaction_cost: 0.001

training:
  algorithm: "PPO"
  total_timesteps: 100000
  learning_rate: 0.0003
  batch_size: 64

ensemble:
  algorithms: ["PPO", "SAC"]
  voting_strategy: "majority"
```

### Feature Engineering (`config/feature_engineering.yaml`)

```yaml
indicators:
  - rsi:
      periods: [14, 21]
  - macd:
      fast: 12
      slow: 26
  - bollinger_bands:
      period: 20
      std_dev: 2
```

## MLOps Integration

### MLFlow Experiment Tracking

```python
from src.infrastructure.mlops import MLFlowTracker

tracker = MLFlowTracker(tracking_uri="http://localhost:5000")
tracker.log_metric("episode_return", 150.5)
tracker.log_artifact("models/agent.zip")
```

### WandB Monitoring

```python
from src.infrastructure.monitoring import WandBMonitor

monitor = WandBMonitor(project="jarvis-trading")
monitor.log_training_episode(episode=1, return_value=150.5)
```

### Hyperparameter Optimization (Optuna)

```python
from src.application.optimization import OptunaOptimizer

optimizer = OptunaOptimizer(n_trials=100)
best_params = optimizer.optimize(objective_function)
```

## Testing

### Unit Tests

```bash
# Test individual domains
pytest tests/unit/domain/ -v

# Test specific service
pytest tests/unit/domain/market/test_data_fetcher.py -v
```

### Integration Tests

```bash
# Test journey execution
pytest tests/integration/test_journey_1.py -v
```

### Coverage

```bash
make test  # Generates HTML coverage report in htmlcov/
```

## Development Workflow

### Creating New Features

1. **Design Domain Model**: Define entities and value objects
2. **Implement Repository**: Data access abstraction
3. **Create Service**: Business logic
4. **Add Tests**: Unit + integration
5. **Document**: API and usage examples

### Code Quality

```bash
make lint      # Check syntax and types
make format    # Auto-format with black/isort
make clean     # Remove build artifacts
```

## Performance Optimization

### Data Pipeline Caching

- First run: Full data fetch (slow)
- Subsequent runs: Cached data (< 100ms)
- Cache invalidation: Configurable expiry

### Feature Engineering

- Vectorized NumPy operations
- Incremental feature computation
- Feature importance filtering

### RL Training

- Vectorized environment (Gym)
- Parallel episode collection
- GPU acceleration (PyTorch)

## Deployment

### Local Development

```bash
make dev-install
make run-journey1  # Run individual journey
```

### Docker (Future)

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "scripts/journey_4_rl_training.py"]
```

### MLFlow Server

```bash
mlflow server --host 127.0.0.1 --port 5000
```

## Monitoring & Alerts

- **Performance Metrics**: Win rate, Sharpe ratio, max drawdown
- **RL Metrics**: Episode return, exploration rate, loss
- **System Health**: Data freshness, cache hit rate, API latency

## Troubleshooting

### Binance API Errors

```python
# Check API keys
from src.infrastructure.exchange import BinanceConnector
connector = BinanceConnector()
connector.validate_credentials()  # Raises exception if invalid
```

### Cache Issues

```python
# Clear cache and rebuild
from src.domain.market.cache import DataCache
cache = DataCache()
cache.clear()
cache.rebuild()
```

### RL Training Convergence

- Check feature engineering quality
- Verify trading environment configuration
- Increase training episodes
- Adjust learning rate

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Follow code style (`make format`)
4. Add tests (`pytest tests/`)
5. Submit PR with description

## License

MIT License - See LICENSE file

## References

- [FinRL Paper](https://arxiv.org/abs/2011.09607)
- [Stable-Baselines3 Docs](https://stable-baselines3.readthedocs.io/)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Binance API Docs](https://binance-docs.github.io/apidocs/)

## Support

For issues, questions, or suggestions:
1. Check existing [Issues](https://github.com/your-repo/issues)
2. Review [JOURNEYS.md](docs/JOURNEYS.md)
3. Check [Architecture.md](docs/ARCHITECTURE.md)

---

**Last Updated**: 2025-11-14
**Version**: 1.0.0
**Status**: Alpha (Active Development)
