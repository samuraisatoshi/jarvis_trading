"""Currency value object for account domain."""

from enum import Enum
from typing import Dict


class Currency(Enum):
    """
    Value Object representing cryptocurrency and fiat currencies.

    Supported currencies include major cryptocurrencies and USDT stablecoin.
    """

    USDT = "USDT"  # Tether
    BTC = "BTC"    # Bitcoin
    ETH = "ETH"    # Ethereum
    BNB = "BNB"    # Binance Coin
    XRP = "XRP"    # Ripple
    ADA = "ADA"    # Cardano
    SOL = "SOL"    # Solana
    DOGE = "DOGE"  # Dogecoin
    USDC = "USDC"  # USD Coin
    BUSD = "BUSD"  # Binance USD

    def __str__(self) -> str:
        """Return currency symbol."""
        return self.value

    def to_symbol(self) -> str:
        """Return currency symbol.

        Returns:
            Currency symbol string
        """
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "Currency":
        """Create Currency from string.

        Args:
            value: Currency symbol string (e.g., "BTC", "USDT")

        Returns:
            Currency enum value

        Raises:
            ValueError: If currency symbol is not supported
        """
        try:
            return cls[value.upper()]
        except KeyError:
            supported = ", ".join([c.value for c in cls])
            raise ValueError(
                f"Currency '{value}' not supported. Supported: {supported}"
            ) from None

    @classmethod
    def get_decimal_places(cls, currency: "Currency") -> int:
        """Get standard decimal places for currency.

        Args:
            currency: Currency value object

        Returns:
            Number of decimal places for display

        Raises:
            ValueError: If currency is unknown
        """
        decimal_map: Dict[Currency, int] = {
            cls.USDT: 2,
            cls.USDC: 2,
            cls.BUSD: 2,
            cls.BTC: 8,
            cls.ETH: 6,
            cls.BNB: 4,
            cls.XRP: 2,
            cls.ADA: 4,
            cls.SOL: 4,
            cls.DOGE: 8,
        }

        if currency not in decimal_map:
            raise ValueError(f"Decimal places unknown for currency {currency}")

        return decimal_map[currency]
