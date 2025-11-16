#!/usr/bin/env python3
"""
Test FinRL Integration with jarvis_trading

This script demonstrates:
1. Loading pre-trained FinRL models
2. Calculating 13 core features
3. Generating trading predictions
4. Comparing with real market data

Usage:
    python scripts/test_finrl_integration.py --symbol BTC_USDT --timeframe 1d

Requirements:
    - FinRL trained models at: ../finrl/trained_models/
    - Binance API access (for live data)
"""

import sys
import asyncio
import argparse
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.reinforcement_learning.services.model_loader import ModelLoader
from src.domain.reinforcement_learning.services.prediction_service import RLPredictionService
from src.domain.features.services.feature_calculator import FeatureCalculator
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_models_path() -> Path:
    """Resolve path to FinRL trained models."""
    # Try relative path from jarvis_trading
    relative = Path(__file__).parent.parent.parent / 'finrl' / 'trained_models'
    if relative.exists():
        return relative

    # Try absolute path
    absolute = Path('/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models')
    if absolute.exists():
        return absolute

    raise FileNotFoundError(
        "Cannot find FinRL trained_models directory.\n"
        "Expected at: ../finrl/trained_models/ or /Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models"
    )


def test_model_loader(models_path: Path):
    """Test ModelLoader functionality."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Model Loader")
    logger.info("="*80)

    loader = ModelLoader(str(models_path))

    # List available models
    available = loader.list_available_models()
    logger.info(f"Found {len(available)} models in {models_path}")
    logger.info(f"First 5 models: {list(available.keys())[:5]}")

    # Get best model
    best = loader.get_best_model_by_sharpe()
    if best:
        symbol, timeframe = best
        logger.info(f"Best known model: {symbol}_{timeframe} (Sharpe 7.55)")

        # Try loading best model
        try:
            model, vec_norm = loader.load_model(symbol, timeframe)
            logger.info(f"Successfully loaded: {symbol}_{timeframe}")
            logger.info(f"  Model type: {model.__class__.__name__}")
            logger.info(f"  VecNormalize type: {vec_norm.__class__.__name__}")
            return True
        except Exception as e:
            logger.error(f"Failed to load best model: {e}")
            return False
    else:
        logger.error("No best model found")
        return False


def test_feature_calculator():
    """Test FeatureCalculator functionality."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Feature Calculator")
    logger.info("="*80)

    calculator = FeatureCalculator()

    # Create sample data
    logger.info("Creating sample OHLCV data...")
    dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='1D')

    base_price = 40000
    df = pd.DataFrame({
        'open': base_price + pd.Series(range(100)) * 10,
        'high': base_price + pd.Series(range(100)) * 12,
        'low': base_price + pd.Series(range(100)) * 8,
        'close': base_price + pd.Series(range(100)) * 10 + pd.Series(range(100)) % 5,
        'volume': 1000000 + pd.Series(range(100)) * 1000,
    }, index=dates)

    logger.info(f"Sample data shape: {df.shape}")
    logger.info(f"Sample data:\n{df.head()}")

    # Calculate features
    logger.info("Calculating 13 core features...")
    df_features = calculator.calculate_features(df)

    logger.info(f"Result shape: {df_features.shape}")
    logger.info(f"Columns: {list(df_features.columns)}")

    # Validate features
    validation = calculator.validate_features(df_features)
    logger.info(f"Validation result:")
    logger.info(f"  Valid: {validation['valid']}")
    logger.info(f"  Coverage: {validation['coverage_ratio']:.1%}")
    logger.info(f"  Missing features: {validation['missing_features']}")

    # Show feature descriptions
    logger.info("\nFeature descriptions:")
    descriptions = calculator.get_feature_descriptions()
    for feature, desc in descriptions.items():
        logger.info(f"  {feature:30} - {desc}")

    logger.info(f"\nLast row features:")
    last_row = df_features.iloc[-1]
    for feature in FeatureCalculator.CORE_FEATURES:
        if feature in last_row.index:
            value = last_row[feature]
            logger.info(f"  {feature:30} = {value:10.4f}")

    return validation['valid']


def test_prediction_service(models_path: Path):
    """Test RLPredictionService functionality."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Prediction Service")
    logger.info("="*80)

    # Initialize service
    service = RLPredictionService(str(models_path))

    # Create sample data
    logger.info("Creating sample OHLCV data...")
    dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='1D')

    base_price = 40000
    df_candles = pd.DataFrame({
        'open': base_price + pd.Series(range(100)) * 10,
        'high': base_price + pd.Series(range(100)) * 12,
        'low': base_price + pd.Series(range(100)) * 8,
        'close': base_price + pd.Series(range(100)) * 10 + pd.Series(range(100)) % 5,
        'volume': 1000000 + pd.Series(range(100)) * 1000,
    }, index=dates)

    # Try best model first
    best = service.get_best_model()
    if best:
        symbol, timeframe = best
        logger.info(f"Testing with best model: {symbol}_{timeframe}")

        try:
            result = service.predict(symbol, timeframe, df_candles)
            logger.info(f"Prediction result:")
            logger.info(f"  Symbol: {result.symbol}")
            logger.info(f"  Timeframe: {result.timeframe}")
            logger.info(f"  Action: {service.get_action_name(result.action)}")
            logger.info(f"  Confidence: {result.confidence:.1%}")
            logger.info(f"  Price: ${result.price:,.2f}")
            logger.info(f"  Features used: {result.features_used}")
            logger.info(f"  Model: {result.model_name}")
            return True

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return False
    else:
        logger.error("No best model available")
        return False


def test_batch_prediction(models_path: Path):
    """Test batch prediction functionality."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Batch Prediction")
    logger.info("="*80)

    service = RLPredictionService(str(models_path))

    # Create sample data for multiple symbols/timeframes
    logger.info("Creating sample data for multiple symbols...")
    dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='1D')

    batch_data = {}
    for symbol_base in ['BTC_USDT', 'ETH_USDT']:
        batch_data[symbol_base] = {}
        for timeframe in ['1d', '4h']:
            base_price = 40000 if symbol_base == 'BTC_USDT' else 2000
            df = pd.DataFrame({
                'open': base_price + pd.Series(range(100)) * 10,
                'high': base_price + pd.Series(range(100)) * 12,
                'low': base_price + pd.Series(range(100)) * 8,
                'close': base_price + pd.Series(range(100)) * 10,
                'volume': 1000000 + pd.Series(range(100)) * 1000,
            }, index=dates)
            batch_data[symbol_base][timeframe] = df

    logger.info(f"Batch data: {len(batch_data)} symbols, {sum(len(v) for v in batch_data.values())} timeframes")

    # Run batch prediction
    try:
        results = service.predict_batch(batch_data)
        logger.info(f"Batch predictions: {len(results)} successful")

        for key, result in sorted(results.items()):
            logger.info(
                f"  {key:20} -> {service.get_action_name(result.action):5} "
                f"(conf={result.confidence:.1%}, price=${result.price:,.2f})"
            )

        return len(results) > 0

    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        return False


def test_live_data(symbol: str = 'BTCUSDT', timeframe: str = '1d'):
    """Test with live Binance data."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Live Binance Data")
    logger.info("="*80)

    try:
        client = BinanceRESTClient()
        logger.info(f"Fetching live data for {symbol}...")

        # Fetch klines
        klines = client.get_klines(symbol, timeframe, limit=100)
        if not klines:
            logger.error("Failed to fetch klines")
            return False

        logger.info(f"Fetched {len(klines)} candles")

        # Convert to DataFrame
        df = pd.DataFrame(klines)
        logger.info(f"Data shape: {df.shape}")
        logger.info(f"Latest candle: Close=${df['close'].iloc[-1]:,.2f}, Volume={df['volume'].iloc[-1]:,.0f}")

        # Calculate features
        calculator = FeatureCalculator()
        df_features = calculator.calculate_features(df)

        logger.info(f"Calculated features: {df_features.shape}")
        logger.info(f"Last row features:")
        last_row = df_features.iloc[-1]
        for feature in FeatureCalculator.CORE_FEATURES[:5]:  # Show first 5
            if feature in last_row.index:
                logger.info(f"  {feature:30} = {last_row[feature]:10.4f}")

        return True

    except Exception as e:
        logger.error(f"Live data test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    parser = argparse.ArgumentParser(
        description='Test FinRL integration with jarvis_trading'
    )
    parser.add_argument(
        '--symbol',
        default='BTC_USDT',
        help='Trading symbol (e.g., BTC_USDT, ETH_USDT)'
    )
    parser.add_argument(
        '--timeframe',
        default='1d',
        help='Candle timeframe (e.g., 1d, 4h, 1h)'
    )
    parser.add_argument(
        '--skip-live',
        action='store_true',
        help='Skip live Binance data test'
    )
    args = parser.parse_args()

    logger.info("\n" + "="*80)
    logger.info("FINRL INTEGRATION TEST SUITE")
    logger.info("="*80)
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Timeframe: {args.timeframe}")
    logger.info(f"Skip live: {args.skip_live}")

    try:
        models_path = setup_models_path()
        logger.info(f"Models path: {models_path}")
    except FileNotFoundError as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

    # Run tests
    results = {}
    results['model_loader'] = test_model_loader(models_path)
    results['feature_calculator'] = test_feature_calculator()
    results['prediction_service'] = test_prediction_service(models_path)
    results['batch_prediction'] = test_batch_prediction(models_path)

    if not args.skip_live:
        # Convert symbol format (BTCUSDT instead of BTC_USDT)
        symbol_binance = args.symbol.replace('_', '')
        results['live_data'] = test_live_data(symbol_binance, args.timeframe)

    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info(f"  {test_name:25} - {status}")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    logger.info(f"\nTotal: {passed_count}/{total_count} tests passed")

    sys.exit(0 if passed_count == total_count else 1)


if __name__ == '__main__':
    main()
