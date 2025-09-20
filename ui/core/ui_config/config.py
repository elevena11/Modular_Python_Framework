"""
ui/core/ui_config/config.py
UI Configuration system for managing element visibility and ordering.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Set

# Configuration defaults (moved from constants.py)
DEFAULT_CONFIG_VERSION = "1.0.0"
DEFAULT_ELEMENT_ORDER = 100

logger = logging.getLogger("ui.core.ui_config.config")

class UIConfig:
    """UI Configuration manager for the standalone UI application."""
    
    def __init__(self, app_context):
        """Initialize the UI configuration manager."""
        self.app_context = app_context
        self.config_file = os.path.join(app_context.config.get("data_dir", "./data"), "ui_elements_config.json")
        # No protected elements - all elements are configurable
        self.config = self._load_config()
        logger.info("UI Config initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded UI configuration from {self.config_file}")
                return config
            except Exception as e:
                logger.error(f"Error loading UI configuration: {str(e)}")
                return self._create_default_config()
        else:
            logger.info("No UI configuration found, creating default")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create a default configuration."""
        config = {
            "ui_elements": {},
            "version": DEFAULT_CONFIG_VERSION,
            "last_updated": datetime.now().isoformat()
        }
        
        # Save the default configuration
        self._save_config(config)
        return config
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Update the last_updated timestamp
            config["last_updated"] = datetime.now().isoformat()
            
            # Write to file
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Saved UI configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving UI configuration: {str(e)}")
            return False
    
    def save(self) -> bool:
        """Save the current configuration."""
        return self._save_config(self.config)
    
    def is_element_visible(self, element_id: str) -> bool:
        """Check if an element should be visible."""
        # Check in configuration
        if element_id in self.config["ui_elements"]:
            return self.config["ui_elements"][element_id].get("visible", True)

        # Default to visible for unknown elements
        return True
    
    def get_element_order(self, element_id: str, default_priority: int = DEFAULT_ELEMENT_ORDER) -> int:
        """Get the display order for an element."""
        if element_id in self.config["ui_elements"]:
            return self.config["ui_elements"][element_id].get("order", default_priority)
        return default_priority
    
    def set_element_visibility(self, element_id: str, visible: bool) -> bool:
        """Set the visibility of an element."""
        
        # Create element config if doesn't exist
        if element_id not in self.config["ui_elements"]:
            self.config["ui_elements"][element_id] = {
                "visible": visible,
                "order": DEFAULT_ELEMENT_ORDER
            }
        else:
            # Update visibility
            self.config["ui_elements"][element_id]["visible"] = visible
        
        # Save the updated configuration
        return self.save()
    
    def set_element_order(self, element_id: str, order: int) -> bool:
        """Set the display order of an element."""
        # Create element config if doesn't exist
        if element_id not in self.config["ui_elements"]:
            self.config["ui_elements"][element_id] = {
                "visible": True,
                "order": order
            }
        else:
            # Update order
            self.config["ui_elements"][element_id]["order"] = order
        
        # Save the updated configuration
        return self.save()
    
    def get_all_element_settings(self) -> Dict[str, Dict[str, Any]]:
        """Get all element settings."""
        return self.config["ui_elements"]
    
    def update_with_registered_elements(self) -> bool:
        """Update configuration with all registered elements."""
        changed = False
        
        # Get all registered elements
        all_elements = self.app_context.get_all_elements()
        
        # Ensure each element has a config entry
        for element in all_elements:
            element_id = element.get("full_id")
            if element_id and element_id not in self.config["ui_elements"]:
                # Create default config for this element
                self.config["ui_elements"][element_id] = {
                    "visible": True,
                    "order": element.get("priority", DEFAULT_ELEMENT_ORDER)
                }
                changed = True
                logger.info(f"Added config for new element: {element_id}")
        
        # Save if changes were made
        if changed:
            self.save()
        
        return changed