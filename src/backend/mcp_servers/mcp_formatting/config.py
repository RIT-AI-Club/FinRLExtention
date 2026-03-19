"""Configuration loader for the formatting server."""

import yaml
from pathlib import Path
import logging
from typing import Optional

# Configure a basic logger for the application
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AppConfig:
    """
    Handles loading and providing access to application configuration using a singleton pattern.
    It reads settings from a YAML file and allows overrides from environment variables.
    """
    _instance: Optional['AppConfig'] = None

    def __new__(cls) -> 'AppConfig':
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """
        Loads configuration from 'config.yml', handling potential errors
        and setting sensible defaults.
        """
        self._logger = logging.getLogger(__name__)
        config_path = Path(__file__).parent / "config.yml"
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            self._logger.error(f"CRITICAL: Configuration file not found at {config_path}. Please ensure it exists.")
            self._config = {}
        except yaml.YAMLError as e:
            self._logger.error(f"CRITICAL: Error parsing YAML file at {config_path}: {e}")
            self._config = {}

        # Safely access nested configuration
        gemini_config = self._config.get("gemini", {}) if self._config else {}
        
        self.google_api_key = gemini_config.get("api_key")
        
        # Set other Gemini parameters with defaults
        self.temperature: float = float(gemini_config.get("temperature", 0.7))
        self.default_model: str = gemini_config.get("model", "gemini-1.5-pro-latest")
        self.max_output_tokens: int = int(gemini_config.get("max_output_tokens", 8192))

        # Warn if API key is missing or is still the placeholder
        if not self.google_api_key or self.google_api_key == "YOUR_API_KEY_HERE":
            self._logger.warning("Google API Key is not configured. Please set GOOGLE_API_KEY environment variable or update config.yml.")

        # Safely access debug flag
        self.debug: bool = self._config.get("debug", False) if self._config else False
        self._logger.info(f"Application config loaded. Debug mode is {'ON' if self.debug else 'OFF'}.")

# Create a single, globally accessible instance of the configuration
config = AppConfig()
