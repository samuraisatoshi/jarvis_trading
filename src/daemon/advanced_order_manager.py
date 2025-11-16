"""
Advanced Order Manager for JARVIS Trading.

Implements sophisticated order controls:
- Cool down periods between orders
- Price gap requirements
- Asset exposure limits
- Cash reserve management
- Order history tracking

Uses configuration from trading_config.yaml.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger
from decimal import Decimal

from ruamel.yaml import YAML


class OrderCooldownManager:
    """Manages cool down periods and price gaps between orders."""

    def __init__(self, config: Dict, db_path: str = "data/order_history.db"):
        """
        Initialize cooldown manager.

        Args:
            config: Configuration dictionary
            db_path: Path to order history database
        """
        self.config = config
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize order history database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                timeframe TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'executed'
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp
            ON order_history(symbol, timestamp)
        """)

        conn.commit()
        conn.close()

    def can_place_order(
        self,
        symbol: str,
        current_price: float,
        timeframe: str,
        side: str = 'BUY'
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if order can be placed based on cooldown rules.

        Args:
            symbol: Trading symbol
            current_price: Current market price
            timeframe: Trading timeframe
            side: Order side (BUY/SELL)

        Returns:
            Tuple of (can_place, reason_if_not)
        """
        cooldown_config = self.config['order_cooldown']

        if not cooldown_config.get('enabled', True):
            return True, None

        # Check time-based cooldown
        cooldown_seconds = cooldown_config['cooldown_periods'].get(timeframe, 3600)
        last_order = self._get_last_order(symbol, side)

        if last_order:
            last_timestamp = datetime.fromisoformat(last_order['timestamp'])
            time_since_last = (datetime.now(timezone.utc) - last_timestamp).total_seconds()

            if time_since_last < cooldown_seconds:
                remaining = cooldown_seconds - time_since_last
                return False, f"Cooldown active: {remaining:.0f}s remaining"

        # Check price gap requirement
        min_gap_percent = cooldown_config.get('min_price_gap_percent', 2.0)

        if last_order and last_order['price'] > 0:
            price_change_percent = abs(
                (current_price - last_order['price']) / last_order['price'] * 100
            )

            if price_change_percent < min_gap_percent:
                return False, (
                    f"Price gap too small: {price_change_percent:.2f}% "
                    f"< {min_gap_percent}% required"
                )

        # Check daily order limit
        max_daily = cooldown_config.get('max_daily_orders_per_symbol', 5)
        daily_count = self._get_daily_order_count(symbol)

        if daily_count >= max_daily:
            return False, f"Daily limit reached: {daily_count}/{max_daily} orders"

        # Check stop loss cooldown
        if self._in_stop_loss_cooldown(symbol):
            return False, "In stop loss cooldown period (24h)"

        return True, None

    def record_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        timeframe: str,
        status: str = 'executed'
    ):
        """Record order in history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO order_history
            (symbol, side, price, quantity, timeframe, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, side, price, quantity, timeframe, status,
            datetime.now(timezone.utc).isoformat()
        ))

        conn.commit()
        conn.close()

        logger.info(
            f"Recorded {side} order: {symbol} @ ${price:.2f} "
            f"(qty: {quantity}, tf: {timeframe})"
        )

    def _get_last_order(self, symbol: str, side: str) -> Optional[Dict]:
        """Get last order for symbol and side."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT price, timestamp
            FROM order_history
            WHERE symbol = ? AND side = ? AND status = 'executed'
            ORDER BY timestamp DESC
            LIMIT 1
        """, (symbol, side))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'price': result[0],
                'timestamp': result[1]
            }
        return None

    def _get_daily_order_count(self, symbol: str) -> int:
        """Get count of orders today for symbol."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        cursor.execute("""
            SELECT COUNT(*)
            FROM order_history
            WHERE symbol = ? AND timestamp >= ? AND status = 'executed'
        """, (symbol, today.isoformat()))

        count = cursor.fetchone()[0]
        conn.close()

        return count

    def _in_stop_loss_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in stop loss cooldown."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cooldown_seconds = self.config['order_cooldown'].get('stop_loss_cooldown', 86400)
        cutoff_time = (
            datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
        ).isoformat()

        cursor.execute("""
            SELECT COUNT(*)
            FROM order_history
            WHERE symbol = ? AND status = 'stop_loss' AND timestamp >= ?
        """, (symbol, cutoff_time))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0


class PositionExposureManager:
    """Manages position exposure limits and cash reserves."""

    def __init__(self, config: Dict):
        """
        Initialize exposure manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config

    def can_open_position(
        self,
        symbol: str,
        position_size_usd: float,
        current_positions: List[Dict],
        total_portfolio_value: float,
        available_cash: float
    ) -> Tuple[bool, Optional[str], float]:
        """
        Check if new position can be opened based on exposure rules.

        Args:
            symbol: Trading symbol
            position_size_usd: Proposed position size in USD
            current_positions: List of current positions
            total_portfolio_value: Total portfolio value
            available_cash: Available cash balance

        Returns:
            Tuple of (can_open, reason_if_not, adjusted_size)
        """
        position_config = self.config['position_management']
        cash_config = self.config['cash_management']

        # Check max concurrent positions
        max_positions = position_config.get('max_concurrent_positions', 5)
        if len(current_positions) >= max_positions:
            return False, f"Max positions reached: {len(current_positions)}/{max_positions}", 0

        # Check minimum trade value
        min_trade = position_config.get('min_trade_value', 10.0)
        if position_size_usd < min_trade:
            return False, f"Position too small: ${position_size_usd:.2f} < ${min_trade}", 0

        # Check asset exposure limit
        max_exposure = position_config.get('max_asset_exposure', 0.25)
        current_exposure = self._calculate_asset_exposure(
            symbol, current_positions, total_portfolio_value
        )

        new_exposure = (current_exposure + position_size_usd) / total_portfolio_value

        if new_exposure > max_exposure:
            # Calculate maximum allowed size
            max_allowed = (max_exposure * total_portfolio_value) - (current_exposure * total_portfolio_value)
            if max_allowed < min_trade:
                return False, f"Asset exposure limit reached: {new_exposure:.1%} > {max_exposure:.1%}", 0

            # Adjust size to fit within limits
            position_size_usd = max_allowed
            logger.warning(
                f"Position size reduced to ${position_size_usd:.2f} "
                f"to maintain {max_exposure:.1%} exposure limit"
            )

        # Check cash reserve requirements
        min_reserve_percent = self._get_required_cash_reserve()
        required_cash_reserve = total_portfolio_value * min_reserve_percent

        cash_after_trade = available_cash - position_size_usd

        if cash_after_trade < required_cash_reserve:
            max_allowed = available_cash - required_cash_reserve
            if max_allowed < min_trade:
                return False, (
                    f"Insufficient cash: Need ${required_cash_reserve:.2f} reserve "
                    f"({min_reserve_percent:.1%}), have ${available_cash:.2f}"
                ), 0

            # Adjust size to maintain reserve
            position_size_usd = max_allowed
            logger.warning(
                f"Position size reduced to ${position_size_usd:.2f} "
                f"to maintain {min_reserve_percent:.1%} cash reserve"
            )

        return True, None, position_size_usd

    def _calculate_asset_exposure(
        self,
        symbol: str,
        positions: List[Dict],
        total_value: float
    ) -> float:
        """Calculate current exposure to specific asset."""
        exposure = 0.0
        for position in positions:
            if position.get('symbol') == symbol:
                position_value = position.get('quantity', 0) * position.get('current_price', 0)
                exposure += position_value

        return exposure

    def _get_required_cash_reserve(self) -> float:
        """
        Get required cash reserve percentage based on market conditions.

        Returns:
            Required cash reserve as decimal (0.20 = 20%)
        """
        cash_config = self.config['cash_management']
        base_reserve = cash_config.get('min_cash_reserve', 0.20)

        # Check progressive reserve based on drawdown
        progressive = cash_config.get('progressive_reserve', {})
        if progressive.get('enabled', False):
            # TODO: Calculate actual drawdown
            current_drawdown = 0  # Placeholder

            for threshold in progressive.get('drawdown_thresholds', []):
                if current_drawdown >= threshold['threshold']:
                    base_reserve += threshold['reserve_increase']

        return base_reserve

    def get_position_size_for_timeframe(
        self,
        timeframe: str,
        total_portfolio_value: float,
        has_existing_position: bool = False
    ) -> float:
        """
        Calculate position size for timeframe.

        Args:
            timeframe: Trading timeframe
            total_portfolio_value: Total portfolio value
            has_existing_position: Whether position already exists

        Returns:
            Position size in USD
        """
        position_sizes = self.config['position_management']['position_sizes']
        base_allocation = position_sizes.get(timeframe, 0.10)

        # Reduce by 50% if position already exists (DCA)
        if has_existing_position:
            dca_config = self.config['position_management'].get('dca', {})
            if dca_config.get('enabled', True):
                base_allocation *= 0.5
                logger.info(f"DCA mode: Reduced allocation to {base_allocation:.1%}")

        return total_portfolio_value * base_allocation


class TradingConfigLoader:
    """Loads and manages trading configuration."""

    def __init__(self, config_path: str = "config/trading_config.yaml"):
        """Initialize config loader."""
        self.config_path = Path(config_path)
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self._config = None
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self._config = self.yaml.load(f)

        logger.info(f"Loaded trading config from {self.config_path}")

    def reload(self):
        """Reload configuration from file."""
        self._load_config()

    @property
    def config(self) -> Dict:
        """Get configuration dictionary."""
        return self._config

    def get(self, key_path: str, default=None):
        """Get configuration value by dot notation path."""
        keys = key_path.split('.')
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default


class AdvancedOrderManager:
    """
    Main order management class integrating all controls.

    Coordinates cooldown, exposure, and cash management.
    """

    def __init__(self, config_path: str = "config/trading_config.yaml"):
        """Initialize advanced order manager."""
        self.config_loader = TradingConfigLoader(config_path)
        self.config = self.config_loader.config

        self.cooldown_manager = OrderCooldownManager(self.config)
        self.exposure_manager = PositionExposureManager(self.config)

        logger.info("Advanced Order Manager initialized with enhanced controls")

    def validate_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        timeframe: str,
        current_positions: List[Dict],
        portfolio_value: float,
        available_cash: float
    ) -> Tuple[bool, Optional[str], float]:
        """
        Validate order against all rules and constraints.

        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            price: Order price
            quantity: Order quantity
            timeframe: Trading timeframe
            current_positions: Current open positions
            portfolio_value: Total portfolio value
            available_cash: Available cash

        Returns:
            Tuple of (is_valid, error_message, adjusted_quantity)
        """
        position_size_usd = price * quantity

        # Check cooldown rules
        can_place, cooldown_reason = self.cooldown_manager.can_place_order(
            symbol, price, timeframe, side
        )

        if not can_place:
            return False, cooldown_reason, 0

        # Check exposure and cash rules (only for BUY orders)
        if side == 'BUY':
            can_open, exposure_reason, adjusted_size = self.exposure_manager.can_open_position(
                symbol,
                position_size_usd,
                current_positions,
                portfolio_value,
                available_cash
            )

            if not can_open:
                return False, exposure_reason, 0

            # Calculate adjusted quantity if size was reduced
            if adjusted_size < position_size_usd:
                adjusted_quantity = adjusted_size / price
                return True, f"Size adjusted for risk limits", adjusted_quantity

        return True, None, quantity

    def record_executed_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        timeframe: str,
        status: str = 'executed'
    ):
        """Record executed order in history."""
        self.cooldown_manager.record_order(
            symbol, side, price, quantity, timeframe, status
        )

    def get_recommended_position_size(
        self,
        symbol: str,
        timeframe: str,
        portfolio_value: float,
        current_positions: List[Dict]
    ) -> float:
        """Get recommended position size based on configuration."""
        has_position = any(p.get('symbol') == symbol for p in current_positions)

        return self.exposure_manager.get_position_size_for_timeframe(
            timeframe,
            portfolio_value,
            has_position
        )

    def get_status_summary(self) -> Dict:
        """Get summary of current manager status."""
        return {
            "cooldown_enabled": self.config['order_cooldown']['enabled'],
            "min_price_gap": self.config['order_cooldown']['min_price_gap_percent'],
            "max_positions": self.config['position_management']['max_concurrent_positions'],
            "min_cash_reserve": self.config['cash_management']['min_cash_reserve'],
            "max_asset_exposure": self.config['position_management']['max_asset_exposure']
        }