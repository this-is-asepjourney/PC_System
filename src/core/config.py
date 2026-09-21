import yaml
import os
from typing import Any, Dict

class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self, config_path: str = "config.yaml"):
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            print(f"Warning: Configuration file not found at {config_path}")

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split('.')
        current = self._config
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

config = ConfigManager()
