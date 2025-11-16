"""
FinRL Feature Calculator

Calculates the 13 core features used by FinRL trained models.
These are the minimum features required for model predictions.

Core Features:
1. close - Current close price
2. vpt - Volume Price Trend
3. macd_signal - MACD signal line
4. ema_200_slope_normalized - Normalized slope of 200-period EMA
5. atr_percentage - ATR as percentage of price
6. close_position_20 - Price position in 20-period channel
7. ema_8_distance - Distance from 8-period EMA
8. ema_21_distance - Distance from 21-period EMA
9. ema_50_distance - Distance from 50-period EMA
10. ema_200_distance - Distance from 200-period EMA
11. price_diff_1c - 1-period price change
12. momentum_consistency_5c - Consistency of momentum over 5 candles
13. days_since_epoch - Time feature

See: FinRL liveTradeApp/backend/app/core/feature_alignment/feature_config.py
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FeatureCalculator:
    """
    Calculates FinRL core features from OHLCV data.

    This is the minimal feature set. For advanced predictions,
    use AlignedFeatureEngineer from FinRL for 50+ features.
    """

    # The 13 core features
    CORE_FEATURES = [
        'close',
        'vpt',
        'macd_signal',
        'ema_200_slope_normalized',
        'atr_percentage',
        'close_position_20',
        'ema_8_distance',
        'ema_21_distance',
        'ema_50_distance',
        'ema_200_distance',
        'price_diff_1c',
        'momentum_consistency_5c',
        'days_since_epoch'
    ]

    def __init__(self):
        """Initialize feature calculator."""
        self.required_columns = ['open', 'high', 'low', 'close', 'volume']
        logger.info(f"FeatureCalculator initialized - calculating {len(self.CORE_FEATURES)} core features")

    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all 13 core features.

        Args:
            df: DataFrame with OHLCV data
               Required columns: open, high, low, close, volume
               Can have datetime index or timestamp column

        Returns:
            DataFrame with original OHLCV + 13 calculated features
            Includes: open, high, low, close, volume, + 13 features

        Example:
            >>> df = pd.read_csv('btcusdt_daily.csv')
            >>> calculator = FeatureCalculator()
            >>> df_features = calculator.calculate_features(df)
            >>> print(df_features.columns)
            Index(['open', 'high', 'low', 'close', 'volume', 'vpt', 'macd_signal', ...])
        """
        try:
            df = df.copy()

            # Validate required columns
            missing = [col for col in self.required_columns if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

            if len(df) < 50:
                logger.warning(f"Limited data ({len(df)} rows) - some features will have NaN")

            # 1. Calculate EMAs (needed for distances and slope)
            ema_8 = df['close'].ewm(span=8, adjust=False).mean()
            ema_21 = df['close'].ewm(span=21, adjust=False).mean()
            ema_50 = df['close'].ewm(span=50, adjust=False).mean()
            ema_200 = df['close'].ewm(span=200, adjust=False).mean()

            # 2. EMA distances (normalized)
            df['ema_8_distance'] = (df['close'] - ema_8) / df['close']
            df['ema_21_distance'] = (df['close'] - ema_21) / df['close']
            df['ema_50_distance'] = (df['close'] - ema_50) / df['close']
            df['ema_200_distance'] = (df['close'] - ema_200) / df['close']

            # 3. EMA 200 Slope Normalized
            ema_200_slope = ema_200.diff()
            df['ema_200_slope_normalized'] = ema_200_slope / ema_200.shift(1)

            # 4. ATR Percentage
            atr = self._calculate_atr(df, period=14)
            df['atr_percentage'] = (atr / df['close']) * 100

            # 5. Volume Price Trend (VPT)
            df['vpt'] = self._calculate_vpt(df, smooth_period=14)

            # 6. MACD Signal (using FinRL parameters: fast=3, slow=10, signal=16)
            df['macd_signal'] = self._calculate_macd_signal(df)

            # 7. Close Position in 20-period channel (0-1)
            high_20 = df['high'].rolling(window=20).max()
            low_20 = df['low'].rolling(window=20).min()
            df['close_position_20'] = (df['close'] - low_20) / (high_20 - low_20 + 1e-8)
            df['close_position_20'] = df['close_position_20'].clip(0, 1)

            # 8. Price Diff 1c (1-period return as percentage)
            df['price_diff_1c'] = df['close'].pct_change() * 100

            # 9. Momentum Consistency (5-candle lookback)
            # Percentage of positive closes in last 5 candles
            returns = df['close'].pct_change() > 0
            df['momentum_consistency_5c'] = returns.rolling(window=5).mean() * 100

            # 10. Days Since Epoch (time feature)
            df['days_since_epoch'] = self._calculate_days_since_epoch(df)

            # Handle NaN values from rolling calculations
            df = df.ffill().fillna(0)

            # Replace infinite values
            df = df.replace([np.inf, -np.inf], 0)

            # Select OHLCV + core features
            output_cols = ['open', 'high', 'low', 'close', 'volume'] + self.CORE_FEATURES
            result = df[output_cols].copy()

            logger.info(f"Calculated features for {len(result)} rows. Shape: {result.shape}")
            return result

        except Exception as e:
            logger.error(f"Error calculating features: {e}", exc_info=True)
            raise

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).

        Args:
            df: DataFrame with high, low, close
            period: ATR period (typically 14)

        Returns:
            Series with ATR values
        """
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()

        return atr

    def _calculate_vpt(self, df: pd.DataFrame, smooth_period: int = 14) -> pd.Series:
        """
        Calculate Volume Price Trend (VPT).

        VPT = cumulative sum of (volume * percentage price change)
        Then smoothed with EMA.

        Args:
            df: DataFrame with close and volume
            smooth_period: EMA period for smoothing

        Returns:
            Series with VPT values
        """
        price_change = df['close'].pct_change()
        vpt_raw = (df['volume'] * price_change).fillna(0)
        vpt = vpt_raw.ewm(span=smooth_period, adjust=False).mean()

        return vpt

    def _calculate_macd_signal(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate MACD Signal Line.

        Uses FinRL parameters:
        - Fast EMA: 3 periods (not standard 12)
        - Slow EMA: 10 periods (not standard 26)
        - Signal: 16 periods (not standard 9)

        Args:
            df: DataFrame with close prices

        Returns:
            Series with MACD signal values
        """
        # FinRL uses non-standard parameters
        ema_fast = df['close'].ewm(span=3, adjust=False).mean()
        ema_slow = df['close'].ewm(span=10, adjust=False).mean()

        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=16, adjust=False).mean()

        return macd_signal

    def _calculate_days_since_epoch(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate days since Unix epoch (Jan 1, 1970).

        Args:
            df: DataFrame with datetime index or 'timestamp' column

        Returns:
            Series with days since epoch
        """
        # Get datetime from index or timestamp column
        if isinstance(df.index, pd.DatetimeIndex):
            timestamps = df.index
        elif 'timestamp' in df.columns:
            timestamps = pd.to_datetime(df['timestamp'])
        else:
            logger.warning("No timestamp found - using row number as proxy")
            return pd.Series(range(len(df)), index=df.index)

        # Convert to days since epoch
        epoch = pd.Timestamp('1970-01-01')
        days_since_epoch = (timestamps - epoch).days

        return pd.Series(days_since_epoch, index=df.index)

    def validate_features(self, df: pd.DataFrame) -> dict:
        """
        Validate that all core features are present and valid.

        Args:
            df: DataFrame to validate

        Returns:
            Dict with validation results:
            {
                'valid': bool,
                'missing_features': list,
                'nan_count': dict,
                'infinite_count': dict,
                'coverage_ratio': float (0-1)
            }
        """
        validation = {
            'valid': True,
            'missing_features': [],
            'nan_count': {},
            'infinite_count': {},
            'coverage_ratio': 1.0
        }

        # Check for missing features
        for feature in self.CORE_FEATURES:
            if feature not in df.columns:
                validation['missing_features'].append(feature)
                validation['valid'] = False
            else:
                # Count NaNs and infinites
                nan_count = int(df[feature].isna().sum())
                inf_count = int(np.isinf(df[feature]).sum())

                if nan_count > 0 or inf_count > 0:
                    validation['nan_count'][feature] = nan_count
                    validation['infinite_count'][feature] = inf_count

        # Calculate coverage ratio
        valid_features = [f for f in self.CORE_FEATURES if f in df.columns]
        validation['coverage_ratio'] = len(valid_features) / len(self.CORE_FEATURES)

        if validation['coverage_ratio'] < 1.0:
            validation['valid'] = False

        return validation

    def get_feature_descriptions(self) -> dict:
        """
        Get human-readable descriptions of each feature.

        Returns:
            Dict mapping feature_name -> description
        """
        return {
            'close': 'Closing price',
            'vpt': 'Volume Price Trend - weighted volume indicator',
            'macd_signal': 'MACD signal line (FinRL params: 3/10/16)',
            'ema_200_slope_normalized': 'Normalized slope of 200-period EMA',
            'atr_percentage': 'Average True Range as % of price',
            'close_position_20': 'Price position in 20-period channel (0-1)',
            'ema_8_distance': 'Normalized distance from 8-period EMA',
            'ema_21_distance': 'Normalized distance from 21-period EMA',
            'ema_50_distance': 'Normalized distance from 50-period EMA',
            'ema_200_distance': 'Normalized distance from 200-period EMA',
            'price_diff_1c': '1-period price change (%)',
            'momentum_consistency_5c': '% of positive closes in 5-candle window',
            'days_since_epoch': 'Days since 1970-01-01 (time feature)',
        }
