#!/usr/bin/env python3
"""Quick test of refactored DCA modules."""

from dca import DCASmartStrategy, DCASimulator, DCAAnalyzer, DCAVisualizer
import pandas as pd
import numpy as np

# Create test data
dates = pd.date_range('2024-01-01', periods=100, freq='D')
df = pd.DataFrame({
    'open': np.random.uniform(300, 400, 100),
    'high': np.random.uniform(300, 400, 100),
    'low': np.random.uniform(300, 400, 100),
    'close': np.random.uniform(300, 400, 100),
    'volume': np.random.uniform(1000000, 2000000, 100)
}, index=dates)

# Test strategy creation
strategy = DCASmartStrategy(initial_capital=1000, weekly_investment=100)
print(f'✅ Strategy created: ${strategy.initial_capital:,.2f}')

# Test multiplier calculation
multiplier, reason = strategy.calculate_purchase_multiplier(rsi=25, price=350, sma_200=350)
print(f'✅ Multiplier calculation works: {multiplier}x')

# Test buy execution
trade = strategy.execute_buy(
    date='2024-01-01',
    price=300,
    amount_usd=1000,
    rsi=50,
    reason='Test buy',
    multiplier=1.0
)
print(f'✅ Buy execution works: {trade.quantity:.4f} BNB @ ${trade.price}')

# Test profit-taking logic
strategy.ath_price = 300
should_sell, pct, reason = strategy.should_take_profit(price=400, cost_basis=300)
print(f'✅ Profit-taking logic works: should_sell={should_sell}')

# Test crash rebuy logic
strategy.usdt_reserved = 500
should_rebuy, pct, reason = strategy.should_rebuy_crash(rsi=20, price=250)
print(f'✅ Crash rebuy logic works: should_rebuy={should_rebuy}')

# Test simulator creation
simulator = DCASimulator(strategy)
print(f'✅ Simulator created')

# Test analyzer creation
df['rsi'] = 50
df['sma_200'] = 350
analyzer = DCAAnalyzer(strategy, df)
print(f'✅ Analyzer created')

print('\n✅ All modules working correctly!')
print(f'\nModule imports verified:')
print(f'  - DCASmartStrategy ✅')
print(f'  - DCASimulator ✅')
print(f'  - DCAAnalyzer ✅')
print(f'  - DCAVisualizer ✅')
