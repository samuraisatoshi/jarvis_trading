"""Configuration management for Jarvis Trading.

Loads configuration from environment variables and .env file.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class BinanceConfig(BaseSettings):
    """Binance API configuration."""

    api_key: str = ""
    api_secret: str = ""
    testnet: bool = True

    class Config:
        env_prefix = "BINANCE_"


class TradingConfig(BaseSettings):
    """Trading configuration."""

    pair: str = "BTCUSDT"
    interval: str = "1h"
    lookback_periods: int = 500

    class Config:
        env_prefix = "TRADING_"


class DataPipelineConfig(BaseSettings):
    """Data pipeline configuration."""

    timeframes: list[str] = ["1m", "5m", "15m", "1h", "4h", "1d"]
    cache_enabled: bool = True
    cache_dir: Path = Path("./data/cache")
    cache_expiry_hours: int = 24

    class Config:
        env_prefix = "DATA_PIPELINE_"


class RLConfig(BaseSettings):
    """Reinforcement learning configuration."""

    initial_balance: float = 10000.0
    transaction_cost: float = 0.001
    training_episodes: int = 100
    timesteps_per_episode: int = 1000
    gamma: float = 0.99
    learning_rate: float = 0.0003
    batch_size: int = 64

    class Config:
        env_prefix = "RL_"


class MLFlowConfig(BaseSettings):
    """MLFlow configuration."""

    tracking_uri: str = "http://localhost:5000"
    experiment_name: str = "jarvis-trading"
    run_name: Optional[str] = None

    class Config:
        env_prefix = "MLFLOW_"


class WandBConfig(BaseSettings):
    """Weights & Biases configuration."""

    api_key: str = ""
    project: str = "jarvis-trading"
    entity: Optional[str] = None
    enabled: bool = True

    class Config:
        env_prefix = "WANDB_"


class Settings(BaseSettings):
    """Main application settings."""

    # Environment
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite:///./data/jarvis_trading.db"

    # Sub-configurations
    binance: BinanceConfig = BinanceConfig()
    trading: TradingConfig = TradingConfig()
    data_pipeline: DataPipelineConfig = DataPipelineConfig()
    rl: RLConfig = RLConfig()
    mlflow: MLFlowConfig = MLFlowConfig()
    wandb: WandBConfig = WandBConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def validate_required_settings(self) -> None:
        """Validate required settings are configured."""
        if self.environment == "production":
            if not self.binance.api_key or not self.binance.api_secret:
                raise ValueError("API keys required for production")


# Global settings instance
settings = Settings()
