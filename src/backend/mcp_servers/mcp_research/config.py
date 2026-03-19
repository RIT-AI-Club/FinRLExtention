"""Configuration for the Perplexity MCP research server.

Loads settings from the central config/config.yml file.
"""

import sys
from pathlib import Path

import yaml

# Resolve project root: this file is at src/backend/mcp_servers/mcp_research/config.py
# so project root is 4 levels up
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yml"

def _load_config() -> dict:
    """Load and return the perplexity section from config.yml."""
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        return config.get("perplexity", {})
    except FileNotFoundError:
        sys.stderr.write(f"Config file not found: {CONFIG_PATH}\n")
        sys.stderr.flush()
        return {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"Error parsing config: {e}\n")
        sys.stderr.flush()
        return {}

_config = _load_config()

PERPLEXITY_API_KEY: str = _config.get("api_key", "")
PERPLEXITY_MODEL: str = _config.get("model", "sonar")
PERPLEXITY_TEMPERATURE: float = _config.get("temperature", 0.7)
PERPLEXITY_MAX_TOKENS: int = _config.get("max_tokens", 4096)
