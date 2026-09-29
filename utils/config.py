"""
Config Manager
Handles API key storage, loading, and validation.
"""

import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".newslens"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load config from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: dict):
    """Save config to file."""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_api_key() -> str | None:
    """
    Get Anthropic API key from:
    1. Environment variable ANTHROPIC_API_KEY
    2. Config file
    """
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    config = load_config()
    return config.get("anthropic_api_key")


def save_api_key(key: str):
    """Save API key to config file."""
    config = load_config()
    config["anthropic_api_key"] = key
    save_config(config)


def get_output_dir() -> str:
    """Get the output directory for exports."""
    config = load_config()
    return config.get("output_dir", str(Path.home() / "newslens_output"))
