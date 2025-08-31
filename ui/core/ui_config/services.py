"""
ui/core/ui_config/services.py
Services for UI configuration management.
"""

import logging
from typing import Dict, List, Any, Optional

from .config import UIConfig
from .registry import ElementRegistry

logger = logging.getLogger("ui.core.ui_config.services")

class UIConfigService:
    """Service for managing UI configuration."""
    
    def __init__(self, app_context):
        """Initialize the UI configuration service."""
        self.app_context = app_context
        self.registry = ElementRegistry()
        self.config = UIConfig(app_context)
    
    def register_element(self, element_data: Dict[str, Any]) -> Optional[str]:
        """Register a UI element from the current module."""
        module_id = self.app_context.current_module_id
        if not module_id:
            logger.error("Cannot register element: No current module ID")
            return None
        
        return self.registry.register_element(module_id, element_data)
    
    def get_visible_elements(self, element_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all visible elements, optionally filtered by type."""
        elements = self.registry.get_elements_by_type(element_type) if element_type else self.registry.get_all_elements()
        
        # Filter visible elements and add order information
        visible_elements = []
        for element in elements:
            element_id = element.get("full_id")
            if self.config.is_element_visible(element_id):
                # Add order information
                element = element.copy()  # Create a copy to avoid modifying the original
                element["order"] = self.config.get_element_order(
                    element_id, 
                    element.get("priority", 100)
                )
                visible_elements.append(element)
        
        # Sort by order
        visible_elements.sort(key=lambda e: e.get("order", 100))
        
        return visible_elements