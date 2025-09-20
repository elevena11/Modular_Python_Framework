"""
ui/services/api_client.py
Client for communicating with the main application API.
"""

import logging
import requests
from typing import Dict, List, Any, Optional

logger = logging.getLogger("ui.services.api_client")

class APIClient:
    """Client for communicating with the main application API."""
    
    def __init__(self, base_url="http://localhost:8000"):
        """Initialize with the base URL of the API."""
        self.base_url = base_url
        self.session = requests.Session()
        self._config_cache = None  # Cache for config
        logger.info(f"API client initialized with base URL: {base_url}")
    
    @property
    def config(self):
        """Backward compatibility property for modules expecting config."""
        if not self._config_cache:
            self._config_cache = self.get_frontend_config()
        return self._config_cache
    
    def check_connection(self):
        """Check if the API is available."""
        try:
            # Use the root endpoint which returns basic health info
            response = self.session.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "running":
                    return True
            logger.warning(f"API health check failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to API: {str(e)}")
            return False
    
    def get_frontend_config(self):
        """Get configuration settings from the backend."""
        try:
            # Use the root endpoint and settings info to build config
            root_response = self.session.get(f"{self.base_url}/")
            if root_response.status_code == 200:
                root_data = root_response.json()
                
                # Build a basic config from available endpoints
                config = {
                    "api_base_url": self.base_url,
                    "version": root_data.get("version", "0.1.0"),
                    "name": root_data.get("name", "Reality Anchor Hub"),
                    "features": {
                        "settings_ui": True,
                        "database_viewer": True
                    }
                }
                return config
            logger.warning(f"Failed to get frontend config: {root_response.status_code}")
            return {"api_base_url": self.base_url}
        except Exception as e:
            logger.error(f"Error getting frontend config: {str(e)}")
            return {"api_base_url": self.base_url}
    
    def get_modules(self):
        """Get a list of all active modules from the framework runtime API."""
        try:
            # Use the active modules endpoint to get actual running module information
            response = self.session.get(f"{self.base_url}/api/v1/core/framework/active-modules")
            if response.status_code == 200:
                data = response.json()
                modules_data = data.get("modules", {})

                # Convert active modules to module list format (already in proper format)
                modules = []
                for module_id, module_info in modules_data.items():
                    # Use the active module information directly since it's more comprehensive
                    modules.append({
                        "id": module_info.get("id", module_id),
                        "name": module_info.get("name", module_id.replace('.', ' ').title()),
                        "status": module_info.get("status", "active"),
                        "version": module_info.get("version", "1.0.0"),
                        "description": module_info.get("description", f"Active {module_id} module"),
                        "services": module_info.get("services", []),
                        "phase1_complete": module_info.get("phase1_complete", False),
                        "phase2_complete": module_info.get("phase2_complete", False),
                        "initialization_time": module_info.get("initialization_time")
                    })

                logger.info(f"Retrieved {len(modules)} active modules from framework runtime")
                return modules
            logger.warning(f"Failed to get active modules: {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error getting active modules: {str(e)}")
            return []
    
    def submit_instruction(self, instruction):
        """
        Submit an instruction to the AI Agent.
        
        Args:
            instruction: The instruction text
            
        Returns:
            Response from the AI Agent
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/llm/instruction",
                json={"instruction": instruction}
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.warning(f"Error submitting instruction: {response.status_code}")
            return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error submitting instruction: {str(e)}")
            return {"error": str(e)}