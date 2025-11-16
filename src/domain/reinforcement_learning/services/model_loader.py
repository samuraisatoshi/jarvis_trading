"""
FinRL Model Loader Service

Loads pre-trained PPO models and VecNormalize instances from the FinRL project.
Supports multiple timeframes and assets using standard naming conventions.

Benefits:
- Reuses 272 already-trained models (no need to retrain)
- Best model: BTC_USDT_1d with Sharpe 7.55
- Handles normalization correctly for live predictions
"""

from typing import Tuple, Optional
import pickle
import logging
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecNormalize

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Loads pre-trained RL models from FinRL trained_models directory.

    Models are saved as:
    - {SYMBOL}_{TIMEFRAME}_ppo_model.zip (PPO model)
    - {SYMBOL}_{TIMEFRAME}_vecnormalize.pkl (Normalization state)

    Example:
        loader = ModelLoader('/path/to/trained_models')
        model, vec_norm = loader.load_model('BTC_USDT', '1d')
    """

    def __init__(self, models_path: str):
        """
        Initialize model loader.

        Args:
            models_path: Path to FinRL trained_models directory
                       (typically /path/to/finrl/trained_models/)
        """
        self.models_path = Path(models_path)

        if not self.models_path.exists():
            raise ValueError(f"Models path does not exist: {models_path}")

        logger.info(f"ModelLoader initialized with path: {self.models_path}")

    def load_model(self, symbol: str, timeframe: str) -> Tuple[PPO, VecNormalize]:
        """
        Load a pre-trained PPO model with its normalization state.

        Args:
            symbol: Trading pair (e.g., 'BTC_USDT', 'ETH_USDT')
            timeframe: Candle timeframe (e.g., '1d', '4h', '1h')

        Returns:
            Tuple of (PPO_model, VecNormalize_instance)

        Raises:
            FileNotFoundError: If model files don't exist
            Exception: If files are corrupted
        """
        model_name = f"{symbol}_{timeframe}"
        model_file = self.models_path / f"{model_name}_ppo_model.zip"
        vec_norm_file = self.models_path / f"{model_name}_vecnormalize.pkl"

        logger.info(f"Loading model: {model_name}")

        # Check if files exist
        if not model_file.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_file}\n"
                f"Available models at: {self.models_path}"
            )

        if not vec_norm_file.exists():
            raise FileNotFoundError(
                f"VecNormalize file not found: {vec_norm_file}\n"
                f"Available models at: {self.models_path}"
            )

        try:
            # Load PPO model
            logger.debug(f"Loading PPO model from: {model_file}")
            model = PPO.load(str(model_file), device='auto')

            # Load VecNormalize (handles feature normalization)
            logger.debug(f"Loading VecNormalize from: {vec_norm_file}")
            with open(vec_norm_file, 'rb') as f:
                vec_normalize = pickle.load(f)

            logger.info(
                f"Successfully loaded {model_name}: "
                f"model_type={model.__class__.__name__}, "
                f"vec_norm_type={vec_normalize.__class__.__name__}"
            )

            return model, vec_normalize

        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}", exc_info=True)
            raise

    def predict_action(
        self,
        model: PPO,
        vec_normalize: VecNormalize,
        observation: 'np.ndarray'
    ) -> int:
        """
        Generate trading action from observation.

        Args:
            model: Loaded PPO model
            vec_normalize: VecNormalize instance for feature normalization
            observation: Features array (will be normalized automatically)

        Returns:
            Action: 0 = SELL, 1 = HOLD, 2 = BUY

        Note:
            The model outputs actions in range [0, 1, 2]:
            - 0: SELL / SHORT
            - 1: HOLD / DO NOTHING
            - 2: BUY / LONG
        """
        try:
            # Normalize observation using VecNormalize
            # The vec_normalize.normalize_obs() handles feature scaling
            normalized_obs = vec_normalize.normalize_obs(observation)

            # Generate prediction (deterministic)
            action, _states = model.predict(
                normalized_obs,
                deterministic=True
            )

            # Convert to integer action
            action_int = int(action[0]) if hasattr(action, '__len__') else int(action)

            logger.debug(
                f"Prediction: action={action_int} (0=SELL, 1=HOLD, 2=BUY), "
                f"raw_action={action}"
            )

            return action_int

        except Exception as e:
            logger.error(f"Error generating prediction: {e}", exc_info=True)
            raise

    def list_available_models(self) -> dict:
        """
        List all available models in the models directory.

        Returns:
            Dict mapping {symbol_timeframe: model_info}
            Example:
            {
                'BTC_USDT_1d': {'model': path, 'vec_norm': path, 'exists': True},
                'ETH_USDT_4h': {'model': path, 'vec_norm': path, 'exists': True},
            }
        """
        available = {}

        # Find all PPO model files
        for model_file in sorted(self.models_path.glob('*_ppo_model.zip')):
            # Extract name without extension
            base_name = model_file.name.replace('_ppo_model.zip', '')

            # Check if corresponding vecnormalize exists
            vec_norm_file = self.models_path / f"{base_name}_vecnormalize.pkl"

            available[base_name] = {
                'model': str(model_file),
                'vec_norm': str(vec_norm_file),
                'exists': vec_norm_file.exists(),
                'size_mb': model_file.stat().st_size / 1024 / 1024
            }

        logger.info(f"Found {len(available)} models in {self.models_path}")
        return available

    def get_best_model_by_sharpe(self) -> Optional[Tuple[str, str]]:
        """
        Get the best model based on filename convention.
        BTC_USDT_1d is documented as best with Sharpe 7.55.

        Returns:
            Tuple of (symbol, timeframe) for best known model
            or None if not found
        """
        best_models = [
            ('BTC_USDT', '1d'),  # Sharpe 7.55 - documented best
            ('ETH_USDT', '1d'),  # Second best typically
            ('BNB_USDT', '1d'),  # Third best typically
        ]

        available = self.list_available_models()

        for symbol, timeframe in best_models:
            key = f"{symbol}_{timeframe}"
            if key in available and available[key]['exists']:
                logger.info(f"Best available model: {key}")
                return symbol, timeframe

        logger.warning("No known best models found. Use list_available_models() to see options.")
        return None

    def validate_model(self, symbol: str, timeframe: str) -> bool:
        """
        Validate that a model can be loaded successfully.

        Args:
            symbol: Trading pair
            timeframe: Timeframe

        Returns:
            True if model can be loaded, False otherwise
        """
        try:
            model, vec_norm = self.load_model(symbol, timeframe)
            logger.info(f"Model validation passed: {symbol}_{timeframe}")
            return True
        except Exception as e:
            logger.warning(f"Model validation failed: {e}")
            return False
