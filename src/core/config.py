import yaml
import os
import sys
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
        resolved_path = config_path
        if not os.path.isabs(resolved_path) and not os.path.exists(resolved_path):
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(os.path.abspath(sys.executable))
                candidate = os.path.join(base_dir, resolved_path)
                if not os.path.exists(candidate) and hasattr(sys, '_MEIPASS'):
                    candidate = os.path.join(sys._MEIPASS, resolved_path)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                candidate = os.path.join(base_dir, resolved_path)
            if os.path.exists(candidate):
                resolved_path = candidate

        if os.path.exists(resolved_path):
            with open(resolved_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            print(f"Warning: Configuration file not found at {resolved_path}")

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
