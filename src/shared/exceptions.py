"""Shared exception classes for Jarvis Trading."""


class JarvisTradingException(Exception):
    """Base exception for all Jarvis Trading errors."""

    pass


class MarketException(JarvisTradingException):
    """Base exception for market domain errors."""

    pass


class DataFetchException(MarketException):
    """Raised when market data fetch fails."""

    pass


class DataValidationException(MarketException):
    """Raised when market data validation fails."""

    pass


class CacheException(MarketException):
    """Raised when cache operation fails."""

    pass


class FeatureEngineeringException(JarvisTradingException):
    """Base exception for feature engineering errors."""

    pass


class IndicatorCalculationException(FeatureEngineeringException):
    """Raised when indicator calculation fails."""

    pass


class FeatureSelectionException(FeatureEngineeringException):
    """Raised when feature selection fails."""

    pass


class TradingException(JarvisTradingException):
    """Base exception for trading domain errors."""

    pass


class SignalGenerationException(TradingException):
    """Raised when signal generation fails."""

    pass


class PositionManagementException(TradingException):
    """Raised when position management fails."""

    pass


class RLException(JarvisTradingException):
    """Base exception for RL domain errors."""

    pass


class AgentTrainingException(RLException):
    """Raised when agent training fails."""

    pass


class EnvironmentException(RLException):
    """Raised when environment creation/management fails."""

    pass


class BacktestException(RLException):
    """Raised when backtesting fails."""

    pass


class ConfigurationException(JarvisTradingException):
    """Raised when configuration is invalid."""

    pass


class InfrastructureException(JarvisTradingException):
    """Base exception for infrastructure errors."""

    pass


class ExchangeException(InfrastructureException):
    """Raised when exchange connection fails."""

    pass


class PersistenceException(InfrastructureException):
    """Raised when persistence operation fails."""

    pass


class MLOpsException(InfrastructureException):
    """Raised when MLOps service fails."""

    pass
