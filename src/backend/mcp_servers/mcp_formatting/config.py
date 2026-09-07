"""Configuration loader for the formatting server."""

import os
import yaml
from pathlib import Path
import logging
from typing import Optional

# This file lives at src/backend/mcp_servers/mcp_formatting/config.py, so the
# project root is five levels up. Resolved from __file__ rather than the cwd
# because MCP launches this server as a subprocess whose working directory is
# not guaranteed. Same anchor the research server uses.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yml"

# Configure a basic logger for the application
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ClaudeAppConfig:
    """
    Handles loading and providing access to application configuration using a singleton pattern.
    It reads settings from a YAML file and allows overrides from environment variables.
    """

    _instance: Optional['ClaudeAppConfig'] = None

    def __new__(cls) -> 'ClaudeAppConfig':
        if cls._instance is None:
            cls._instance = super(ClaudeAppConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """
        Loads configuration from 'config.yml', handling potential errors
        and setting sensible defaults.
        """
        self._logger = logging.getLogger(__name__)
        config_path = CONFIG_PATH

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
        claude_config = self._config.get("claude", {}) if self._config else {}
        
        # The environment wins over config.yml so deployments can inject a key
        # without writing a secret to disk.
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or claude_config.get("api_key")

        # No temperature here on purpose: the models this project targets reject
        # the sampling parameters, and anthropic 1.x dropped them from the
        # request signatures. A `temperature:` key in config.yml is ignored.
        self.default_model: str = os.getenv("ANTHROPIC_MODEL") or claude_config.get("model", "claude-sonnet-5")
        self.max_output_tokens: int = int(claude_config.get("max_output_tokens", 8192))

        # Warn if API key is missing or is still the placeholder
        if not self.anthropic_api_key or self.anthropic_api_key == "YOUR_API_KEY_HERE":
            self._logger.warning("Anthropic API Key is not configured. Please set ANTHROPIC_API_KEY environment variable or update config.yml.")

        # Safely access debug flag
        self.debug: bool = self._config.get("debug", False) if self._config else False
        self._logger.info(f"Application config loaded. Debug mode is {'ON' if self.debug else 'OFF'}.")

# Create a single, globally accessible instance of the configuration
claudeConfig = ClaudeAppConfig()
    