"""
tools/compliance/core/template.py
Updated: March 17, 2025
Simplified template manager for binary compliance model
"""

import os
import re
import logging
import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("compliance.template")

class TemplateManager:
    """Manager for compliance file templates."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            templates_dir: Directory containing templates (defaults to 'templates' in tool directory)
        """
        if templates_dir is None:
            # Use 'templates' directory in the same directory as this module
            self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        else:
            self.templates_dir = templates_dir
        
        self.template_file = os.path.join(self.templates_dir, "compliance.md")
        
        # Create templates directory if it doesn't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Create default template if it doesn't exist
        if not os.path.exists(self.template_file):
            self._create_default_template()
    
    def _create_default_template(self):
        """Create the default compliance template file."""
        template_content = """# Module Compliance Status

## Module: [module_id]
## Version: [version_from_manifest]

## Core Implementation Standards
- Settings API v2: No
- Error Handling v1: No
- Two-Phase Initialization: No
- Service Registration: No
- Async Programming: No
- Trace Logging: No
- ASCII-only Console Output: No
- Module Dependency Management: No

## UI Standards
- Multi-UI Architecture: No
- Gradio 5.20+ Compatible: No
- Streamlit Support: No
- UI Framework Detection: No
- Component Implementation Pattern: No
- UI Event Synchronization: No

## API Standards
- OpenAPI Documentation: No
- Standard Error Responses: No
- Validation Schema: No
- API Versioning: No

## Database Standards
- Two-Phase DB Operations: No
- SQLiteJSON for Complex Types: No
- Proper Transaction Handling: No
- Migration Support: No

## Testing & Documentation
- Unit Tests: No
- Integration Tests: No
- Developer Guide: No
- User Documentation: No

## Exceptions
# Add explanations for intentional non-compliance here

## Last Compliance Review: YYYY-MM-DD
## Reviewed By: [developer_name]
"""
        try:
            with open(self.template_file, 'w') as f:
                f.write(template_content)
            logger.info(f"Created default compliance template: {self.template_file}")
        except Exception as e:
            logger.error(f"Failed to create default template: {str(e)}")
    
    def get_template(self) -> str:
        """
        Get the compliance template content.
        
        Returns:
            Template content as string
        """
        try:
            with open(self.template_file, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read template: {str(e)}")
            return ""
    
    def create_compliance_file(self, module: Dict[str, Any]) -> bool:
        """
        Create a compliance file for a module from template.
        
        Args:
            module: Module information dictionary
            
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template()
        if not template:
            return False
        
        module_id = module["id"]
        version = module.get("version", module.get("manifest", {}).get("version", "1.0.0"))
        
        # Replace placeholders
        content = template
        content = content.replace("[module_id]", module_id)
        content = content.replace("[version_from_manifest]", version)
        
        # Add current date
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        content = content.replace("YYYY-MM-DD", today)
        
        # Write to file
        compliance_path = os.path.join(module["path"], "compliance.md")
        
        # Don't overwrite existing files
        if os.path.exists(compliance_path):
            logger.info(f"Skipping module {module_id}: compliance file already exists")
            return False
            
        try:
            with open(compliance_path, 'w') as f:
                f.write(content)
            logger.info(f"Created compliance file for {module_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create compliance file for {module_id}: {str(e)}")
            return False
