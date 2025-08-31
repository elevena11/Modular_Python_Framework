"""
ui/core/ui_config/registry.py
Element registry for UI components.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("ui.core.ui_config.registry")

class ElementRegistry:
    """Registry for UI elements."""
    
    def __init__(self):
        """Initialize an empty registry."""
        self.elements = {}  # Module ID -> List of elements
        self.elements_by_id = {}  # Full element ID -> Element data
    
    def register_element(self, module_id: str, element_data: Dict[str, Any]) -> Optional[str]:
        """
        Register a UI element.
        
        Args:
            module_id: ID of the module registering the element
            element_data: Element metadata including id, type, display_name, etc.
            
        Returns:
            Full element ID or None if registration failed
        """
        element_id = element_data.get("id")
        if not element_id:
            logger.error("Element registration failed: missing id")
            return None
            
        full_id = f"{module_id}.{element_id}"
        
        # Store in registry
        if module_id not in self.elements:
            self.elements[module_id] = []
        
        # Add full_id and module_id to element data
        element_data["full_id"] = full_id
        element_data["module_id"] = module_id
        
        self.elements[module_id].append(element_data)
        self.elements_by_id[full_id] = element_data
        
        logger.info(f"Registered UI element: {full_id}")
        return full_id
    
    def get_element(self, full_id: str) -> Optional[Dict[str, Any]]:
        """Get an element by its full ID."""
        return self.elements_by_id.get(full_id)
    
    def get_elements_by_type(self, element_type: str) -> List[Dict[str, Any]]:
        """Get all elements of a specific type."""
        return [e for e in self.elements_by_id.values() if e.get("type") == element_type]
    
    def get_all_elements(self) -> List[Dict[str, Any]]:
        """Get all registered elements."""
        return list(self.elements_by_id.values())
    
    def get_module_elements(self, module_id: str) -> List[Dict[str, Any]]:
        """Get all elements for a specific module."""
        return self.elements.get(module_id, [])
    
    def clear(self):
        """Clear the registry."""
        self.elements = {}
        self.elements_by_id = {}