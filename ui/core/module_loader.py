# ui/core/module_loader.py
import os
import sys
import importlib
import logging
from typing import Dict, List, Any

logger = logging.getLogger("ui.core.module_loader")

class UIModuleLoader:
    """Loads UI modules and their components."""
    
    def __init__(self, app_context):
        """Initialize with application context."""
        self.app_context = app_context
        self.modules = {}
        # Get the UI framework from the config
        self.ui_framework = app_context.config.get("default_ui", "streamlit")
        logger.info(f"UI Module Loader initialized with framework: {self.ui_framework}")
        
    def discover_modules(self):
        """Discover modules with UI components."""
        discovered_modules = []
        
        # Check in main application modules
        for module_type in ["core", "standard", "extensions"]:
            base_path = os.path.join("modules", module_type)
            
            if not os.path.exists(base_path):
                continue
                
            # Look for modules with ui/ui_[framework].py
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                
                if not os.path.isdir(item_path):
                    continue
                    
                # Skip if .disabled file exists
                if os.path.exists(os.path.join(item_path, ".disabled")):
                    logger.info(f"Skipping disabled module: {module_type}.{item}")
                    continue
                    
                # Check for ui/ui_[framework].py in each module
                ui_dir_path = os.path.join(item_path, "ui")
                ui_file_path = os.path.join(ui_dir_path, f"ui_{self.ui_framework}.py")
                
                if os.path.exists(ui_file_path):
                    module_id = f"{module_type}.{item}"
                    discovered_modules.append({
                        "id": module_id,
                        "path": item_path,
                        "ui_path": ui_file_path,
                        "import_path": f"modules.{module_type}.{item}.ui.ui_{self.ui_framework}"
                    })
                    logger.info(f"Discovered UI module: {module_id} for {self.ui_framework}")
                
                # Also check one level deeper for sub-modules with UI components
                elif os.path.isdir(item_path):
                    for subitem in os.listdir(item_path):
                        subitem_path = os.path.join(item_path, subitem)
                        if not os.path.isdir(subitem_path):
                            continue
                            
                        # Skip if .disabled file exists
                        if os.path.exists(os.path.join(subitem_path, ".disabled")):
                            logger.info(f"Skipping disabled module: {module_type}.{item}.{subitem}")
                            continue
                            
                        # Check for ui/ui_[framework].py in sub-module
                        sub_ui_dir_path = os.path.join(subitem_path, "ui")
                        sub_ui_file_path = os.path.join(sub_ui_dir_path, f"ui_{self.ui_framework}.py")
                        
                        if os.path.exists(sub_ui_file_path):
                            module_id = f"{module_type}.{item}.{subitem}"
                            discovered_modules.append({
                                "id": module_id,
                                "path": subitem_path,
                                "ui_path": sub_ui_file_path,
                                "import_path": f"modules.{module_type}.{item}.{subitem}.ui.ui_{self.ui_framework}"
                            })
                            logger.info(f"Discovered UI module: {module_id} for {self.ui_framework}")
        
        logger.info(f"Discovered {len(discovered_modules)} modules with UI components for {self.ui_framework}")
        return discovered_modules
    
    def load_modules(self):
        """Load discovered modules."""
        modules = self.discover_modules()
        
        for module in modules:
            module_id = module["id"]
            
            try:
                # Import the UI module using the correct import path
                ui_module = importlib.import_module(module["import_path"])
                
                # Store the module
                self.modules[module_id] = {
                    "id": module_id,
                    "module": ui_module,
                    "path": module["path"]
                }
                
                # Register UI components
                if hasattr(ui_module, "register_components"):
                    # Set current module ID for element registration
                    self.app_context.current_module_id = module_id
                    
                    # Call the registration function
                    ui_module.register_components(self.app_context)
                    
                    # Reset current module ID
                    self.app_context.current_module_id = None
                    
                    logger.info(f"Registered UI components for {module_id}")
                else:
                    logger.warning(f"Module {module_id} has no register_components function")
                
            except Exception as e:
                logger.error(f"Error loading UI module {module_id}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        return self.modules
