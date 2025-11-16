-- Jarvis Trading SQLite Schema
-- Persistence layer for accounts, balances, transactions, orders, and performance metrics

-- Accounts table: Core account records
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leverage REAL DEFAULT 1.0,
    is_active BOOLEAN DEFAULT 1,
    closed_at TIMESTAMP,
    max_leverage REAL DEFAULT 3.0,
    metadata JSON
);

-- Balances table: Multi-currency account balances
CREATE TABLE IF NOT EXISTS balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    available_amount REAL NOT NULL DEFAULT 0.0,
    reserved_amount REAL NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(account_id, currency)
);

-- Transactions table: Complete audit trail
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    reference_id TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Orders table: Paper trading orders
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    status TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL,
    executed_price REAL,
    fee_amount REAL,
    fee_currency TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Performance metrics table: Daily performance tracking
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    date DATE NOT NULL,
    total_value_usd REAL,
    pnl_daily REAL,
    pnl_total REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    max_drawdown REAL,
    win_rate REAL,
    profit_factor REAL,
    trades_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(account_id, date)
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_transactions_account_created
    ON transactions(account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_type
    ON transactions(account_id, transaction_type);

CREATE INDEX IF NOT EXISTS idx_orders_account_status
    ON orders(account_id, status);

CREATE INDEX IF NOT EXISTS idx_orders_created
    ON orders(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_balances_account
    ON balances(account_id);

CREATE INDEX IF NOT EXISTS idx_performance_account_date
    ON performance_metrics(account_id, date DESC);

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;
