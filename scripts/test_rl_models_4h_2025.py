#!/usr/bin/env python3
"""
Backtest BNB_USDT 4h Model with 2025 Data
Compare 4h vs 1d performance with detailed metrics
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent))

from src.domain.features.services.feature_calculator import FeatureCalculator
from stable_baselines3 import PPO


class AdvancedRLBacktest:
    def __init__(self, initial_balance=5000):
        self.initial_balance = initial_balance
        self.feature_calc = FeatureCalculator()

    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate=0.0) -> float:
        """Calculate annualized Sharpe ratio"""
        if len(returns) < 2 or returns.std() == 0:
            return 0.0
        excess_returns = returns - risk_free_rate
        return np.sqrt(252) * (excess_returns.mean() / excess_returns.std())

    def calculate_max_drawdown(self, equity_curve: list) -> float:
        """Calculate maximum drawdown percentage"""
        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def calculate_win_rate(self, trades: list) -> float:
        """Calculate win rate from completed trades"""
        if not trades:
            return 0.0

        winning_trades = 0
        total_trades = 0

        # Pair BUY/SELL trades
        buy_price = None
        for trade in trades:
            if trade['action'] == 'BUY':
                buy_price = trade['price']
            elif trade['action'] == 'SELL' and buy_price:
                if trade['price'] > buy_price:
                    winning_trades += 1
                total_trades += 1
                buy_price = None

        return (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    def backtest_model(self, symbol, timeframe, data_path):
        """Run comprehensive backtest with detailed metrics"""

        # Load data
        df = pd.read_csv(data_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        print(f"\n{'='*80}")
        print(f"BACKTESTING {symbol} {timeframe.upper()} MODEL WITH 2025 DATA")
        print(f"{'='*80}")
        print(f"Period: {df.index[0]} to {df.index[-1]}")
        print(f"Total Candles: {len(df)}")

        # Calculate features
        print(f"\nCalculating 13 core features...")
        df_features = self.feature_calc.calculate_features(df)

        # Get price data
        prices = df['close'].values
        initial_price = prices[200]  # First tradeable price
        final_price = prices[-1]
        buy_hold_return = (final_price - initial_price) / initial_price * 100

        # Load model
        try:
            model_path = f'/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/{symbol}_{timeframe}_ppo_model.zip'
            vec_path = f'/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models/{symbol}_{timeframe}_vecnormalize.pkl'

            print(f"Loading PPO model from {Path(model_path).name}...")
            model = PPO.load(model_path)

            with open(vec_path, 'rb') as f:
                vec_normalize = pickle.load(f)

        except Exception as e:
            print(f"\nERROR: Model not found - {e}")
            return None

        # Simulate trading
        balance = self.initial_balance
        position = 0
        trades = []
        equity_curve = [self.initial_balance]
        daily_returns = []

        print(f"\nRunning backtest with ${self.initial_balance:,.2f} initial capital...")

        # Start from candle 200 (need history for features)
        for i in range(200, len(df_features)):
            # Prepare observation (13 core features only)
            feature_values = []
            for feat in self.feature_calc.CORE_FEATURES:
                val = df_features.iloc[i][feat]
                try:
                    val = float(np.asarray(val).flatten()[0])
                except:
                    val = 0.0
                feature_values.append(val)

            obs = np.array(feature_values, dtype=np.float32).reshape(1, -1)

            # Normalize observation
            try:
                obs_normalized = vec_normalize.normalize_obs(obs)
            except:
                obs_normalized = obs

            # Model prediction
            try:
                action, _states = model.predict(obs_normalized, deterministic=True)
            except:
                continue

            # Convert action to trading signal
            action_val = float(np.asarray(action).flatten()[0])
            current_price = prices[i]
            current_time = df_features.index[i]

            # Calculate current equity
            if position > 0:
                current_equity = position * current_price
            else:
                current_equity = balance
            equity_curve.append(current_equity)

            # Calculate daily returns
            if len(equity_curve) > 1:
                daily_return = (equity_curve[-1] - equity_curve[-2]) / equity_curve[-2]
                daily_returns.append(daily_return)

            # Trading logic
            if action_val > 0.3 and position == 0:  # BUY
                position = balance / current_price
                balance = 0
                trades.append({
                    'date': str(current_time),
                    'action': 'BUY',
                    'price': current_price,
                    'confidence': action_val,
                    'equity': current_equity
                })

            elif action_val < -0.3 and position > 0:  # SELL
                balance = position * current_price
                profit = balance - trades[-1]['equity'] if trades else 0
                profit_pct = (profit / trades[-1]['equity'] * 100) if trades else 0
                position = 0
                trades.append({
                    'date': str(current_time),
                    'action': 'SELL',
                    'price': current_price,
                    'confidence': action_val,
                    'equity': balance,
                    'profit': profit,
                    'profit_pct': profit_pct
                })

        # Close any open position
        if position > 0:
            balance = position * prices[-1]
            equity_curve.append(balance)

        # Calculate final metrics
        total_return = (balance - self.initial_balance) / self.initial_balance * 100
        num_trades = len([t for t in trades if t['action'] == 'BUY'])
        win_rate = self.calculate_win_rate(trades)
        sharpe = self.calculate_sharpe_ratio(pd.Series(daily_returns))
        max_dd = self.calculate_max_drawdown(equity_curve)

        # Print results
        print(f"\n{'='*80}")
        print(f"BACKTEST RESULTS - {symbol} {timeframe.upper()}")
        print(f"{'='*80}")
        print(f"\nCAPITAL:")
        print(f"  Initial Balance:    ${self.initial_balance:,.2f}")
        print(f"  Final Balance:      ${balance:,.2f}")
        print(f"  Total Return:       {total_return:+.2f}%")
        print(f"  Buy & Hold Return:  {buy_hold_return:+.2f}%")
        print(f"  Alpha (vs B&H):     {total_return - buy_hold_return:+.2f}%")

        print(f"\nTRADING METRICS:")
        print(f"  Total Trades:       {num_trades}")
        print(f"  Win Rate:           {win_rate:.1f}%")
        print(f"  Sharpe Ratio:       {sharpe:.2f}")
        print(f"  Max Drawdown:       {max_dd:.2f}%")

        # Show recent trades
        print(f"\nRECENT TRADES (Last 10):")
        for trade in trades[-10:]:
            if trade['action'] == 'BUY':
                print(f"  {trade['date'][:16]} | BUY  | ${trade['price']:>7.2f} | Conf: {trade['confidence']:+.2f}")
            else:
                profit_str = f"{trade.get('profit_pct', 0):+.1f}%" if 'profit_pct' in trade else ""
                print(f"  {trade['date'][:16]} | SELL | ${trade['price']:>7.2f} | Conf: {trade['confidence']:+.2f} | P/L: {profit_str}")

        print(f"\n{'='*80}")

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'initial_balance': self.initial_balance,
            'final_balance': balance,
            'total_return': total_return,
            'buy_hold_return': buy_hold_return,
            'alpha': total_return - buy_hold_return,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'trades': trades,
            'equity_curve': equity_curve
        }


def compare_timeframes(result_4h, result_1d):
    """Print comparison table between 4h and 1d timeframes"""

    print(f"\n{'='*80}")
    print(f"TIMEFRAME COMPARISON: 1D vs 4H")
    print(f"{'='*80}")
    print(f"\n{'Metric':<20} | {'1D':>12} | {'4H':>12} | {'Difference':>12}")
    print(f"{'-'*20}-+-{'-'*12}-+-{'-'*12}-+-{'-'*12}")

    metrics = [
        ('Total Return', 'total_return', '%'),
        ('Number of Trades', 'num_trades', ''),
        ('Win Rate', 'win_rate', '%'),
        ('Sharpe Ratio', 'sharpe_ratio', ''),
        ('Max Drawdown', 'max_drawdown', '%'),
        ('Alpha vs B&H', 'alpha', '%')
    ]

    for name, key, unit in metrics:
        val_1d = result_1d.get(key, 0)
        val_4h = result_4h.get(key, 0)
        diff = val_4h - val_1d

        if unit == '%':
            print(f"{name:<20} | {val_1d:>11.2f}{unit} | {val_4h:>11.2f}{unit} | {diff:>+11.2f}{unit}")
        elif key == 'num_trades':
            print(f"{name:<20} | {val_1d:>12.0f} | {val_4h:>12.0f} | {diff:>+12.0f}")
        else:
            print(f"{name:<20} | {val_1d:>12.2f} | {val_4h:>12.2f} | {diff:>+12.2f}")

    print(f"\n{'='*80}")
    print(f"RECOMMENDATION:")

    # Scoring system
    score_1d = 0
    score_4h = 0

    if result_1d['total_return'] > result_4h['total_return']:
        score_1d += 1
        print(f"  Return:  1D wins ({result_1d['total_return']:.2f}% vs {result_4h['total_return']:.2f}%)")
    else:
        score_4h += 1
        print(f"  Return:  4H wins ({result_4h['total_return']:.2f}% vs {result_1d['total_return']:.2f}%)")

    if result_1d['sharpe_ratio'] > result_4h['sharpe_ratio']:
        score_1d += 1
        print(f"  Sharpe:  1D wins ({result_1d['sharpe_ratio']:.2f} vs {result_4h['sharpe_ratio']:.2f})")
    else:
        score_4h += 1
        print(f"  Sharpe:  4H wins ({result_4h['sharpe_ratio']:.2f} vs {result_1d['sharpe_ratio']:.2f})")

    if result_1d['max_drawdown'] < result_4h['max_drawdown']:
        score_1d += 1
        print(f"  Drawdown: 1D wins ({result_1d['max_drawdown']:.2f}% vs {result_4h['max_drawdown']:.2f}%)")
    else:
        score_4h += 1
        print(f"  Drawdown: 4H wins ({result_4h['max_drawdown']:.2f}% vs {result_1d['max_drawdown']:.2f}%)")

    print(f"\n  FINAL SCORE: 1D={score_1d} | 4H={score_4h}")

    if score_1d > score_4h:
        print(f"\n  WINNER: 1D timeframe is more consistent for live trading")
    elif score_4h > score_1d:
        print(f"\n  WINNER: 4H timeframe captures more opportunities")
    else:
        print(f"\n  RESULT: Both timeframes perform similarly - use based on preferences:")
        print(f"    - 1D: Less monitoring, more stable")
        print(f"    - 4H: More trades, more active management")

    print(f"{'='*80}\n")


def main():
    print(f"\n{'='*80}")
    print(f"BNB_USDT BACKTEST: 4H MODEL WITH 2025 DATA")
    print(f"{'='*80}")

    tester = AdvancedRLBacktest(initial_balance=5000)

    # Backtest 4h model
    result_4h = tester.backtest_model(
        symbol='BNB_USDT',
        timeframe='4h',
        data_path='/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/data/2025/BNB_USDT_4h_2025.csv'
    )

    if not result_4h:
        print("\nERROR: Failed to run 4h backtest")
        return 1

    # For comparison, we need 1d results
    # User mentioned +25% return on 1d, let's use that or run actual test
    print(f"\nFor comparison with 1D model, testing 1D as well...")

    result_1d = tester.backtest_model(
        symbol='BNB_USDT',
        timeframe='1d',
        data_path='/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/data/2025/BNB_USDT_1d_2025.csv'
    )

    if result_1d:
        compare_timeframes(result_4h, result_1d)

    # Save results
    output_dir = Path('/Users/jfoc/Documents/DevLabs/python/crypto/jarvis_trading/workspace/trading_backtest/reports')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / f"bnb_4h_vs_1d_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(results_file, 'w') as f:
        json.dump({
            '4h': {k: v for k, v in result_4h.items() if k not in ['trades', 'equity_curve']},
            '1d': {k: v for k, v in result_1d.items() if k not in ['trades', 'equity_curve']} if result_1d else None,
            'comparison_date': datetime.now().isoformat()
        }, f, indent=2)

    print(f"Results saved to: {results_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
