"""
RL Prediction Service

Integrates FinRL models with feature calculation to generate trading signals.
Handles model loading, feature engineering, and action generation.

Flow:
1. Load pre-trained FinRL model
2. Calculate features from candle data
3. Normalize features with VecNormalize
4. Generate prediction (0=SELL, 1=HOLD, 2=BUY)
5. Convert to trading signal
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from src.domain.reinforcement_learning.services.model_loader import ModelLoader
from src.domain.features.services.feature_calculator import FeatureCalculator

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Result of a model prediction."""
    symbol: str
    timeframe: str
    action: int  # 0=SELL, 1=HOLD, 2=BUY
    confidence: float  # 0-1
    price: float
    timestamp: str
    features_used: int
    model_name: str


class RLPredictionService:
    """
    Generates trading predictions using pre-trained RL models.

    This service:
    1. Loads FinRL models (no retraining needed)
    2. Calculates required features
    3. Handles normalization
    4. Produces trading signals
    """

    # Action mappings
    ACTION_NAMES = {
        0: 'SELL',
        1: 'HOLD',
        2: 'BUY'
    }

    def __init__(
        self,
        models_path: str,
        use_core_features: bool = True
    ):
        """
        Initialize RL prediction service.

        Args:
            models_path: Path to FinRL trained_models directory
            use_core_features: If True, use 13 core features.
                              If False, use 50+ features (requires advanced engineer)
        """
        self.model_loader = ModelLoader(models_path)
        self.feature_calculator = FeatureCalculator()
        self.use_core_features = use_core_features

        # Cache for loaded models (symbol_timeframe -> (model, vec_norm))
        self.model_cache: Dict[str, Tuple] = {}

        logger.info(
            f"RLPredictionService initialized:\n"
            f"  Models path: {models_path}\n"
            f"  Feature mode: {'core (13)' if use_core_features else 'advanced (50+)'}\n"
            f"  Model cache: empty (will load on demand)"
        )

    def predict(
        self,
        symbol: str,
        timeframe: str,
        candles: pd.DataFrame
    ) -> PredictionResult:
        """
        Generate trading prediction for a symbol/timeframe.

        Args:
            symbol: Trading pair (e.g., 'BTC_USDT')
            timeframe: Candle timeframe (e.g., '1d')
            candles: DataFrame with OHLCV data (at least 50 rows for full features)

        Returns:
            PredictionResult with action (SELL/HOLD/BUY) and confidence

        Raises:
            FileNotFoundError: If model not found
            ValueError: If features cannot be calculated
        """
        try:
            logger.info(
                f"Predicting {symbol} {timeframe}: "
                f"{len(candles)} candles available"
            )

            # 1. Calculate features
            df_features = self.feature_calculator.calculate_features(candles)

            if df_features.empty:
                raise ValueError("Failed to calculate features")

            # Get last row (most recent candle)
            last_row = df_features.iloc[-1]

            # Extract feature vector - handle duplicate 'close' column issue
            # df_features has 'close' both in OHLCV and CORE_FEATURES
            # We need to extract unique columns only
            feature_cols = []
            seen = set()
            for feat in FeatureCalculator.CORE_FEATURES:
                if feat not in seen:
                    feature_cols.append(feat)
                    seen.add(feat)

            # Get unique feature values (this handles duplicate 'close')
            feature_values = []
            for feat in feature_cols:
                val = last_row[feat]
                # Handle any Series or array-like values
                if isinstance(val, (pd.Series, np.ndarray)):
                    val = float(val.iloc[0] if isinstance(val, pd.Series) else val.flatten()[0])
                else:
                    val = float(val)
                feature_values.append(val)

            feature_vector = np.array(feature_values, dtype=np.float32).reshape(1, -1)

            logger.debug(f"Feature vector shape: {feature_vector.shape} (expected (1, 13))")

            # 2. Load model (with caching)
            model_key = f"{symbol}_{timeframe}"
            if model_key not in self.model_cache:
                model, vec_norm = self.model_loader.load_model(symbol, timeframe)
                self.model_cache[model_key] = (model, vec_norm)
                logger.info(f"Cached model: {model_key}")
            else:
                model, vec_norm = self.model_cache[model_key]

            # 3. Generate prediction
            action = self.model_loader.predict_action(model, vec_norm, feature_vector)

            # 4. Calculate confidence (based on action consistency)
            confidence = self._calculate_confidence(action, df_features)

            # Create result
            result = PredictionResult(
                symbol=symbol,
                timeframe=timeframe,
                action=action,
                confidence=confidence,
                price=float(last_row['close'].iloc[0] if isinstance(last_row['close'], pd.Series) else last_row['close']),
                timestamp=str(df_features.index[-1] if hasattr(df_features.index, '__getitem__') else 'unknown'),
                features_used=len(feature_cols),
                model_name=f"{symbol}_{timeframe}_ppo"
            )

            logger.info(
                f"Prediction: {symbol} {timeframe} -> "
                f"{self.ACTION_NAMES[action]} "
                f"(confidence={confidence:.2%}, price=${result.price:,.2f})"
            )

            return result

        except Exception as e:
            logger.error(
                f"Prediction failed for {symbol} {timeframe}: {e}",
                exc_info=True
            )
            raise

    def predict_batch(
        self,
        predictions: Dict[str, Dict[str, pd.DataFrame]]
    ) -> Dict[str, PredictionResult]:
        """
        Generate multiple predictions efficiently.

        Args:
            predictions: Dict structure:
            {
                'symbol': {
                    'timeframe': DataFrame,
                    ...
                }
            }
            Example:
            {
                'BTC_USDT': {
                    '1d': df_candles,
                    '4h': df_candles
                },
                'ETH_USDT': {
                    '1d': df_candles
                }
            }

        Returns:
            Dict mapping 'symbol_timeframe' -> PredictionResult
        """
        results = {}

        for symbol, timeframe_data in predictions.items():
            for timeframe, candles in timeframe_data.items():
                try:
                    result = self.predict(symbol, timeframe, candles)
                    key = f"{symbol}_{timeframe}"
                    results[key] = result
                except Exception as e:
                    logger.error(f"Batch prediction failed for {symbol} {timeframe}: {e}")
                    continue

        logger.info(f"Batch prediction complete: {len(results)} successful")
        return results

    def _calculate_confidence(self, action: int, df: pd.DataFrame) -> float:
        """
        Calculate confidence in the prediction.

        Based on:
        - Trend strength (if action is directional)
        - Volatility (lower = higher confidence)
        - Recent price momentum

        Args:
            action: Predicted action (0/1/2)
            df: DataFrame with features

        Returns:
            Confidence score (0-1)
        """
        try:
            last_row = df.iloc[-1]

            # Base confidence from trend indicators
            if action == 2:  # BUY
                # Confidence if uptrend signals are present
                trend_score = 0.5
                if last_row.get('ema_200_slope_normalized', 0) > 0:
                    trend_score += 0.1
                if last_row.get('close_position_20', 0) > 0.5:
                    trend_score += 0.1
                if last_row.get('price_diff_1c', 0) > 0:
                    trend_score += 0.1

            elif action == 0:  # SELL
                # Confidence if downtrend signals are present
                trend_score = 0.5
                if last_row.get('ema_200_slope_normalized', 0) < 0:
                    trend_score += 0.1
                if last_row.get('close_position_20', 0) < 0.5:
                    trend_score += 0.1
                if last_row.get('price_diff_1c', 0) < 0:
                    trend_score += 0.1

            else:  # HOLD
                trend_score = 0.6  # Higher base for HOLD

            # Volatility adjustment
            volatility = df['price_diff_1c'].std() if 'price_diff_1c' in df.columns else 1.0
            volatility_penalty = min(volatility / 5.0, 0.2)  # Max 20% penalty

            confidence = min(trend_score - volatility_penalty, 1.0)
            return max(confidence, 0.3)  # Minimum 30% confidence

        except Exception as e:
            logger.warning(f"Error calculating confidence: {e}")
            return 0.5  # Default neutral confidence

    def get_available_models(self) -> dict:
        """
        Get list of all available pre-trained models.

        Returns:
            Dict mapping model_name -> model_info
        """
        return self.model_loader.list_available_models()

    def get_best_model(self) -> Optional[Tuple[str, str]]:
        """
        Get the best known pre-trained model (BTC_USDT_1d with Sharpe 7.55).

        Returns:
            Tuple of (symbol, timeframe) or None
        """
        return self.model_loader.get_best_model_by_sharpe()

    def clear_cache(self):
        """Clear loaded model cache to free memory."""
        count = len(self.model_cache)
        self.model_cache.clear()
        logger.info(f"Cleared model cache: {count} models")

    def get_action_name(self, action: int) -> str:
        """Get human-readable action name."""
        return self.ACTION_NAMES.get(action, 'UNKNOWN')
