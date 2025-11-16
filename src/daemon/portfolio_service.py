"""
Portfolio management service.

Handles portfolio state queries, position tracking, and capital allocation.
"""

from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime, timezone

from .models import Position, PortfolioStatus
from .interfaces import (
    BalanceRepository,
    PositionRepository,
    ExchangeClient
)


class PortfolioService:
    """
    Portfolio management service.

    Coordinates portfolio queries across balances, positions, and market data.
    Calculates position sizing and capital allocation.
    """

    def __init__(
        self,
        balance_repo: BalanceRepository,
        position_repo: PositionRepository,
        exchange_client: ExchangeClient
    ):
        """
        Initialize portfolio service.

        Args:
            balance_repo: Balance repository for account balances
            position_repo: Position repository for asset holdings
            exchange_client: Exchange client for market prices
        """
        self.balance_repo = balance_repo
        self.position_repo = position_repo
        self.exchange_client = exchange_client

    def get_portfolio_status(
        self,
        watchlist: List[str]
    ) -> PortfolioStatus:
        """
        Get complete portfolio status snapshot.

        Aggregates balances, positions, and current values across
        all watched symbols.

        Args:
            watchlist: List of symbols to check for positions

        Returns:
            PortfolioStatus with current state
        """
        try:
            # Get all balances
            balances = self.balance_repo.get_all_balances()
            usdt_balance = balances.get('USDT', 0.0)
            total_value = usdt_balance

            # Get positions with current values
            positions = []
            for symbol in watchlist:
                position = self.position_repo.get_position(symbol)

                if position and position.quantity > 0:
                    try:
                        # Get current market price
                        ticker = self.exchange_client.get_24h_ticker(symbol)
                        current_price = float(ticker['lastPrice'])

                        # Add to total value
                        position_value = position.get_value(current_price)
                        total_value += position_value

                        positions.append(position)

                    except Exception as e:
                        logger.error(
                            f"Error getting price for {symbol}: {e}"
                        )

            return PortfolioStatus(
                total_value=total_value,
                usdt_balance=usdt_balance,
                positions=positions,
                timestamp=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Error getting portfolio status: {e}")
            # Return empty status on critical error
            return PortfolioStatus(
                total_value=0.0,
                usdt_balance=0.0,
                positions=[],
                timestamp=datetime.now(timezone.utc)
            )

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for specific symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Position if exists with quantity > 0, None otherwise
        """
        try:
            return self.position_repo.get_position(symbol)
        except Exception as e:
            logger.error(f"Error getting position for {symbol}: {e}")
            return None

    def get_all_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List of all positions with quantity > 0
        """
        try:
            return self.position_repo.get_all_positions()
        except Exception as e:
            logger.error(f"Error getting all positions: {e}")
            return []

    def get_available_capital(self) -> float:
        """
        Get available USDT balance.

        Returns:
            Available USDT balance for trading
        """
        try:
            return self.balance_repo.get_balance('USDT')
        except Exception as e:
            logger.error(f"Error getting available capital: {e}")
            return 0.0

    def calculate_position_size(
        self,
        symbol: str,
        timeframe: str,
        position_sizes: Dict[str, float]
    ) -> float:
        """
        Calculate position size based on timeframe and current holdings.

        Position sizing rules:
        1. Base allocation determined by timeframe
        2. Reduce allocation by 50% if position already exists
        3. Based on available USDT balance

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for the signal (1h, 4h, 1d)
            position_sizes: Dict mapping timeframe to allocation %

        Returns:
            Position size in USD
        """
        try:
            # Get available USDT
            usdt_balance = self.get_available_capital()

            # Get base allocation for timeframe
            allocation = position_sizes.get(timeframe, 0.1)

            # Check for existing position
            existing_position = self.get_position(symbol)
            if existing_position and existing_position.quantity > 0:
                # Reduce allocation if position already exists
                allocation *= 0.5
                logger.info(
                    f"Position exists for {symbol}, "
                    f"reducing allocation to {allocation:.1%}"
                )

            position_size = usdt_balance * allocation

            logger.debug(
                f"Position size for {symbol} ({timeframe}): "
                f"${position_size:.2f} ({allocation:.1%} of ${usdt_balance:.2f})"
            )

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0

    def get_total_allocated(self, watchlist: List[str]) -> float:
        """
        Get total value currently allocated to positions.

        Args:
            watchlist: List of symbols to check

        Returns:
            Total USD value in positions
        """
        portfolio = self.get_portfolio_status(watchlist)
        return portfolio.invested_value

    def get_allocation_percent(self, watchlist: List[str]) -> float:
        """
        Get percentage of capital allocated to positions.

        Args:
            watchlist: List of symbols to check

        Returns:
            Allocation percentage (0-100)
        """
        portfolio = self.get_portfolio_status(watchlist)
        return portfolio.allocation_percent

    def validate_sufficient_balance(
        self,
        amount: float,
        currency: str = 'USDT'
    ) -> bool:
        """
        Validate sufficient balance for operation.

        Args:
            amount: Required amount
            currency: Currency to check (default: USDT)

        Returns:
            True if balance >= amount, False otherwise
        """
        try:
            balance = self.balance_repo.get_balance(currency)
            return balance >= amount
        except Exception as e:
            logger.error(f"Error validating balance: {e}")
            return False
