#!/usr/bin/env python3
"""
Detailed Analysis of RL Model Actions
Investigate why models are not trading actively
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from pathlib import Path
import sys
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).parent.parent))

from src.domain.features.services.feature_calculator import FeatureCalculator
from stable_baselines3 import PPO


def analyze_model_actions(symbol, timeframe, data_path):
    """Analyze what actions the model is predicting"""

    print(f"\n{'='*80}")
    print(f"ANALYZING {symbol} {timeframe.upper()} MODEL ACTIONS")
    print(f"{'='*80}")

    # Load data
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    print(f"\nPeriod: {df.index[0]} to {df.index[-1]}")
    print(f"Total Candles: {len(df)}")

    # Calculate features
    feature_calc = FeatureCalculator()
    print(f"\nCalculating features...")
    df_features = feature_calc.calculate_features(df)

    # Load model
    model_path = f'/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/{symbol}_{timeframe}_ppo_model.zip'
    vec_path = f'/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/{symbol}_{timeframe}_vecnormalize.pkl'

    print(f"Loading model...")
    model = PPO.load(model_path)

    with open(vec_path, 'rb') as f:
        vec_normalize = pickle.load(f)

    # Collect all actions
    actions = []
    prices = df['close'].values

    print(f"Running model predictions on {len(df_features) - 200} candles...")

    for i in range(200, len(df_features)):
        # Prepare observation
        feature_values = []
        for feat in feature_calc.CORE_FEATURES:
            val = df_features.iloc[i][feat]
            try:
                val = float(np.asarray(val).flatten()[0])
            except:
                val = 0.0
            feature_values.append(val)

        obs = np.array(feature_values, dtype=np.float32).reshape(1, -1)

        # Normalize
        try:
            obs_normalized = vec_normalize.normalize_obs(obs)
        except:
            obs_normalized = obs

        # Predict
        try:
            action, _states = model.predict(obs_normalized, deterministic=True)
            action_val = float(np.asarray(action).flatten()[0])
            actions.append({
                'timestamp': df_features.index[i],
                'action': action_val,
                'price': prices[i]
            })
        except:
            continue

    actions_df = pd.DataFrame(actions)

    # Statistics
    print(f"\n{'='*80}")
    print(f"ACTION DISTRIBUTION ANALYSIS")
    print(f"{'='*80}")

    print(f"\nBasic Statistics:")
    print(f"  Mean Action:     {actions_df['action'].mean():.4f}")
    print(f"  Median Action:   {actions_df['action'].median():.4f}")
    print(f"  Std Dev:         {actions_df['action'].std():.4f}")
    print(f"  Min Action:      {actions_df['action'].min():.4f}")
    print(f"  Max Action:      {actions_df['action'].max():.4f}")

    # Count signals at different thresholds
    print(f"\nSignals at Different Thresholds:")
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    for thresh in thresholds:
        buy_signals = (actions_df['action'] > thresh).sum()
        sell_signals = (actions_df['action'] < -thresh).sum()
        hold_signals = len(actions_df) - buy_signals - sell_signals

        print(f"  Threshold ±{thresh:.1f}:")
        print(f"    BUY (>{thresh:.1f}):    {buy_signals:4d} ({buy_signals/len(actions_df)*100:5.1f}%)")
        print(f"    SELL (<-{thresh:.1f}):   {sell_signals:4d} ({sell_signals/len(actions_df)*100:5.1f}%)")
        print(f"    HOLD:          {hold_signals:4d} ({hold_signals/len(actions_df)*100:5.1f}%)")

    # Percentiles
    print(f"\nAction Percentiles:")
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    for p in percentiles:
        val = np.percentile(actions_df['action'], p)
        print(f"  {p:2d}th percentile: {val:+.4f}")

    # Identify strong signals
    print(f"\nStrong BUY Signals (action > 0.5):")
    strong_buys = actions_df[actions_df['action'] > 0.5].head(10)
    for _, row in strong_buys.iterrows():
        print(f"  {row['timestamp']} | Action: {row['action']:+.4f} | Price: ${row['price']:.2f}")

    print(f"\nStrong SELL Signals (action < -0.5):")
    strong_sells = actions_df[actions_df['action'] < -0.5].head(10)
    if len(strong_sells) > 0:
        for _, row in strong_sells.iterrows():
            print(f"  {row['timestamp']} | Action: {row['action']:+.4f} | Price: ${row['price']:.2f}")
    else:
        print(f"  NO STRONG SELL SIGNALS FOUND")

    # Recommended threshold
    print(f"\n{'='*80}")
    print(f"THRESHOLD RECOMMENDATION")
    print(f"{'='*80}")

    # Find threshold that gives reasonable number of trades (5-20% of candles)
    best_thresh = None
    best_trade_pct = 0

    for thresh in np.arange(0.05, 1.0, 0.05):
        buy_signals = (actions_df['action'] > thresh).sum()
        sell_signals = (actions_df['action'] < -thresh).sum()
        total_signals = buy_signals + sell_signals
        signal_pct = total_signals / len(actions_df) * 100

        if 5 <= signal_pct <= 20 and best_thresh is None:
            best_thresh = thresh
            best_trade_pct = signal_pct

    if best_thresh:
        buy_signals = (actions_df['action'] > best_thresh).sum()
        sell_signals = (actions_df['action'] < -best_thresh).sum()
        print(f"\nRecommended Threshold: ±{best_thresh:.2f}")
        print(f"  Expected BUY signals:  {buy_signals} ({buy_signals/len(actions_df)*100:.1f}%)")
        print(f"  Expected SELL signals: {sell_signals} ({sell_signals/len(actions_df)*100:.1f}%)")
        print(f"  Total trade signals:   {buy_signals + sell_signals} ({best_trade_pct:.1f}%)")
    else:
        print(f"\nWARNING: Model produces very few trading signals!")
        print(f"  The model appears to be in 'hold' mode most of the time.")
        print(f"  This could mean:")
        print(f"    1. Model learned to avoid trading during unfavorable conditions")
        print(f"    2. Model was trained with conservative reward function")
        print(f"    3. Feature normalization issues")

    print(f"\n{'='*80}\n")

    return actions_df, best_thresh


def backtest_with_threshold(symbol, timeframe, data_path, threshold):
    """Run backtest with custom threshold"""

    print(f"\n{'='*80}")
    print(f"BACKTESTING WITH THRESHOLD: ±{threshold:.2f}")
    print(f"{'='*80}")

    # Load data
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Calculate features
    feature_calc = FeatureCalculator()
    df_features = feature_calc.calculate_features(df)
    prices = df['close'].values

    # Load model
    model_path = f'/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/{symbol}_{timeframe}_ppo_model.zip'
    vec_path = f'/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/{symbol}_{timeframe}_vecnormalize.pkl'

    model = PPO.load(model_path)
    with open(vec_path, 'rb') as f:
        vec_normalize = pickle.load(f)

    # Backtest
    balance = 5000
    position = 0
    trades = []

    for i in range(200, len(df_features)):
        # Prepare observation
        feature_values = []
        for feat in feature_calc.CORE_FEATURES:
            val = df_features.iloc[i][feat]
            try:
                val = float(np.asarray(val).flatten()[0])
            except:
                val = 0.0
            feature_values.append(val)

        obs = np.array(feature_values, dtype=np.float32).reshape(1, -1)

        try:
            obs_normalized = vec_normalize.normalize_obs(obs)
        except:
            obs_normalized = obs

        try:
            action, _states = model.predict(obs_normalized, deterministic=True)
            action_val = float(np.asarray(action).flatten()[0])
        except:
            continue

        current_price = prices[i]
        current_time = df_features.index[i]

        # Trading logic with custom threshold
        if action_val > threshold and position == 0:  # BUY
            position = balance / current_price
            balance = 0
            trades.append({
                'date': str(current_time),
                'action': 'BUY',
                'price': current_price,
                'confidence': action_val
            })

        elif action_val < -threshold and position > 0:  # SELL
            balance = position * current_price
            position = 0
            trades.append({
                'date': str(current_time),
                'action': 'SELL',
                'price': current_price,
                'confidence': action_val
            })

    # Close position
    if position > 0:
        balance = position * prices[-1]

    total_return = (balance - 5000) / 5000 * 100
    num_trades = len([t for t in trades if t['action'] == 'BUY'])

    print(f"\nResults:")
    print(f"  Final Balance:  ${balance:,.2f}")
    print(f"  Total Return:   {total_return:+.2f}%")
    print(f"  Number of Trades: {num_trades}")

    # Show trades
    if len(trades) > 0:
        print(f"\nTrade History:")
        for trade in trades[:20]:  # Show first 20
            print(f"  {trade['date'][:16]} | {trade['action']:4s} | ${trade['price']:>7.2f} | Conf: {trade['confidence']:+.2f}")
        if len(trades) > 20:
            print(f"  ... ({len(trades) - 20} more trades)")

    print(f"\n{'='*80}\n")

    return {
        'threshold': threshold,
        'final_balance': balance,
        'total_return': total_return,
        'num_trades': num_trades,
        'trades': trades
    }


def main():
    symbol = 'BNB_USDT'

    print(f"\n{'='*80}")
    print(f"DETAILED RL MODEL ACTION ANALYSIS")
    print(f"{'='*80}\n")

    # Analyze 4h model
    print(f"\n--- ANALYZING 4H MODEL ---")
    actions_4h, best_thresh_4h = analyze_model_actions(
        symbol, '4h',
        '/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/data/2025/BNB_USDT_4h_2025.csv'
    )

    # Analyze 1d model
    print(f"\n--- ANALYZING 1D MODEL ---")
    actions_1d, best_thresh_1d = analyze_model_actions(
        symbol, '1d',
        '/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/data/2025/BNB_USDT_1d_2025.csv'
    )

    # Test with recommended thresholds
    if best_thresh_4h:
        print(f"\n--- TESTING 4H MODEL WITH OPTIMIZED THRESHOLD ---")
        result_4h = backtest_with_threshold(
            symbol, '4h',
            '/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/data/2025/BNB_USDT_4h_2025.csv',
            best_thresh_4h
        )

    if best_thresh_1d:
        print(f"\n--- TESTING 1D MODEL WITH OPTIMIZED THRESHOLD ---")
        result_1d = backtest_with_threshold(
            symbol, '1d',
            '/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/data/2025/BNB_USDT_1d_2025.csv',
            best_thresh_1d
        )


if __name__ == "__main__":
    main()
