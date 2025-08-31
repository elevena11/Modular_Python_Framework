# ui/core/config.py
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ui.core.config")

class UIConfig:
    """Configuration for the UI application."""
    
    def __init__(self, config_file=None):
        """Initialize with optional configuration file path."""
        self.config_file = config_file or os.path.join("data", "ui_config.json")
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        default_config = {
            "app_title": "Modular AI Framework",
            "ui_port": 8050,
            "api_base_url": "http://localhost:8000",
            "database_url": os.environ.get("DATABASE_URL", "sqlite:///./data/database/framework.db"),
            "debug": True,
            "default_ui": "streamlit"  # Default UI framework
        }
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Try to load existing config
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                logger.info(f"Loaded UI configuration from {self.config_file}")
                # Update defaults with loaded values
                default_config.update(loaded_config)
            except Exception as e:
                logger.warning(f"Error loading UI config, using defaults: {str(e)}")
        else:
            # Create default config file
            self._save_config(default_config)
            
        return default_config
    
    def _save_config(self, config=None):
        """Save configuration to file."""
        config_to_save = config or self.config
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            logger.info(f"Saved UI configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving UI configuration: {str(e)}")
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set a configuration value and save to file."""
        self.config[key] = value
        self._save_config()
        return True
