# FinRL Integration Requirements

## System Requirements

### Python
- Python 3.11+ (tested with 3.11)
- Virtual environment activated

### External Dependencies
The following packages are required:

```
pandas>=2.0.0          - Data manipulation
numpy>=1.24.0          - Numerical computing
stable-baselines3>=2.0 - RL models (PPO)
scikit-learn>=1.3.0    - Utilities
python-binance>=1.0.0  - Binance API
```

### Installation

```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or pip
pip install -r requirements.txt

# Or individual packages
pip install pandas numpy stable-baselines3 scikit-learn python-binance
```

## File System Requirements

### Trained Models
**Location**: `/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/`

Required structure:
```
trained_models/
├── AAVE_USDT_30m_ppo_model.zip
├── AAVE_USDT_30m_vecnormalize.pkl
├── AAVE_USDT_1h_ppo_model.zip
├── AAVE_USDT_1h_vecnormalize.pkl
├── ... (90 total models)
├── BTC_USDT_1d_ppo_model.zip
├── BTC_USDT_1d_vecnormalize.pkl
└── ...
```

## Memory Requirements

### Minimum
- CPU: 1 core
- RAM: 512 MB (features only)
- Storage: 100 MB (models)

### Recommended
- CPU: 2+ cores
- RAM: 2 GB (models cached)
- Storage: 1 GB (logs, databases)

## Network Requirements

### For Live Trading
- Stable internet connection
- Low latency to Binance (< 200ms)
- Binance API access enabled

### API Rate Limits
- Default: 1200 requests/minute
- Current use: ~1 request per candle close
- Sufficient for 20+ symbols

## Validation Checklist

Before running integration:

- [ ] Python 3.11+ installed
- [ ] Virtual environment activated
- [ ] Required packages installed
- [ ] Models directory exists with files
- [ ] Test script passes: `python scripts/test_finrl_integration.py`

## Compatibility

### Operating Systems
- macOS 10.15+
- Linux Ubuntu 20.04+
- Windows 10/11 (WSL2 recommended)

### Python Versions
- 3.11 - Fully supported
- 3.10, 3.12 - Partial support (untested)

### Stable-Baselines3
- 2.0+ - Fully supported

## Performance Benchmarks

| Operation | Time |
|-----------|------|
| Load model | 100-200ms |
| Calculate 13 features | 5-10ms |
| Generate prediction | 50-100ms |
| Batch prediction (10) | 500-1000ms |

---

**Last Updated**: 2025-11-14
**Version**: 1.0
**Status**: Production Ready
