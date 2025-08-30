"""
tools/compliance/core/scanner.py
Updated: March 17, 2025
Enhanced standards discovery with improved error handling and logging
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("compliance.scanner")

class StandardsScanner:
    """Scanner for discovering framework standards."""
    
    def __init__(self, modules_dir: str = "modules"):
        """
        Initialize the standards scanner.
        
        Args:
            modules_dir: Directory containing modules
        """
        self.modules_dir = modules_dir
        self.standards = {}
    
    def discover_standards(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover all standards in the framework.
        
        Returns:
            Dictionary of standards with ID as key
        """
        logger.info("Discovering framework standards")
        
        # Start with empty standards dict
        self.standards = {}
        
        # Check if modules directory exists
        if not os.path.exists(self.modules_dir):
            logger.error(f"Modules directory not found: {self.modules_dir}")
            return {}
        
        total_scanned_directories = 0
        found_standards_directories = 0
        
        # Look for standards in all module types (core, standard, extensions)
        for module_type in ["core", "standard", "extensions"]:
            module_type_path = os.path.join(self.modules_dir, module_type)
            
            if not os.path.exists(module_type_path):
                logger.debug(f"Module type directory not found: {module_type_path}")
                continue
            
            logger.info(f"Scanning {module_type} modules for standards")
            
            # Scan module directories for standards
            scanned, found = self._scan_directory_for_standards(module_type_path, f"{module_type}")
            total_scanned_directories += scanned
            found_standards_directories += found
        
        logger.info(f"Discovered {len(self.standards)} standards in {found_standards_directories} standards directories (scanned {total_scanned_directories} directories total)")
        
        # Add sections to standards if not already specified
        for standard_id, standard in self.standards.items():
            if "section" not in standard:
                standard["section"] = self._determine_section(standard_id)
        
        return self.standards
    
    def _scan_directory_for_standards(self, directory: str, prefix: str = "") -> tuple:
        """
        Scan a directory for standards.
        
        Args:
            directory: Directory to scan
            prefix: Prefix for module ID
            
        Returns:
            Tuple of (total_scanned_directories, found_standards_directories)
        """
        total_scanned = 0
        found_standards = 0
        
        # Check each item in the directory
        try:
            items = os.listdir(directory)
            total_scanned += 1
        except Exception as e:
            logger.error(f"Error reading directory {directory}: {str(e)}")
            return total_scanned, found_standards
        
        for item in items:
            item_path = os.path.join(directory, item)
            
            # Skip if not a directory
            if not os.path.isdir(item_path):
                continue
            
            # Check for standards directory
            standards_dir = os.path.join(item_path, "standards")
            if os.path.exists(standards_dir) and os.path.isdir(standards_dir):
                logger.info(f"Found standards directory in {item_path}")
                found_standards += 1
                
                # Load standards from this directory
                loaded_count = self._load_standards_from_directory(standards_dir, f"{prefix}.{item}")
                logger.info(f"  Loaded {loaded_count} standards from {standards_dir}")
            
            # Check for nested modules (one level deep)
            if prefix.count(".") == 0:  # Only one level of nesting
                try:
                    nested_items = os.listdir(item_path)
                    for nested_item in nested_items:
                        nested_path = os.path.join(item_path, nested_item)
                        
                        if not os.path.isdir(nested_path):
                            continue
                        
                        total_scanned += 1
                        
                        # Check for standards directory in nested module
                        nested_standards_dir = os.path.join(nested_path, "standards")
                        if os.path.exists(nested_standards_dir) and os.path.isdir(nested_standards_dir):
                            logger.info(f"Found standards directory in nested module {nested_path}")
                            found_standards += 1
                            
                            # Load standards from this directory
                            nested_module_id = f"{prefix}.{item}.{nested_item}"
                            loaded_count = self._load_standards_from_directory(nested_standards_dir, nested_module_id)
                            logger.info(f"  Loaded {loaded_count} standards from {nested_standards_dir}")
                except Exception as e:
                    logger.error(f"Error scanning nested directory {item_path}: {str(e)}")
        
        return total_scanned, found_standards
    
    def _load_standards_from_directory(self, standards_dir: str, module_id: str) -> int:
        """
        Load standards from a directory.
        
        Args:
            standards_dir: Directory containing standard JSON files
            module_id: ID of the module containing the standards
            
        Returns:
            Number of standards loaded
        """
        loaded_count = 0
        
        # Check each file in the standards directory
        try:
            files = os.listdir(standards_dir)
        except Exception as e:
            logger.error(f"Error reading standards directory {standards_dir}: {str(e)}")
            return 0
        
        for filename in files:
            if not filename.endswith(".json"):
                continue
            
            standard_path = os.path.join(standards_dir, filename)
            
            try:
                with open(standard_path, "r") as f:
                    standard = json.load(f)
                
                # Check if standard has required fields
                if not all(key in standard for key in ["id", "name"]):
                    logger.warning(f"Standard {standard_path} missing required fields: " + 
                                 ", ".join(k for k in ["id", "name"] if k not in standard))
                    continue
                
                # Create standard entry
                standard_id = standard["id"]
                standard["owner_module"] = module_id
                standard["file_path"] = standard_path
                
                # Make sure validation exists
                if "validation" not in standard:
                    standard["validation"] = {}
                    
                # Validate file_targets format and upgrade if needed
                if "validation" in standard:
                    validation = standard["validation"]
                    
                    # Convert old file_targets format to new format if needed
                    if "file_targets" in validation and isinstance(validation["file_targets"], list):
                        # Convert list format to dict format with a generic key
                        old_targets = validation["file_targets"]
                        validation["file_targets"] = {"general": old_targets}
                        logger.warning(f"Upgraded file_targets format for standard {standard_id}")
                
                # Add to standards dict
                self.standards[standard_id] = standard
                logger.debug(f"Loaded standard: {standard_id} (from {module_id})")
                loaded_count += 1
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in standard {standard_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error loading standard {standard_path}: {str(e)}")
        
        return loaded_count
    
    def _determine_section(self, standard_id: str) -> str:
        """
        Determine which section a standard belongs to based on its ID.
        
        Args:
            standard_id: ID of the standard
            
        Returns:
            Section name
        """
        standard_id = standard_id.lower()
        
        if any(keyword in standard_id for keyword in ["ui", "gradio", "streamlit", "component"]):
            return "UI Standards"
        elif any(keyword in standard_id for keyword in ["api", "endpoint", "validation", "schema"]):
            return "API Standards"
        elif any(keyword in standard_id for keyword in ["db", "database", "transaction", "migration"]):
            return "Database Standards"
        elif any(keyword in standard_id for keyword in ["test", "doc", "documentation"]):
            return "Testing & Documentation"
        else:
            return "Core Implementation Standards"
    
    def discover_module_files(self, module_path: str, comprehensive: bool = False) -> List[str]:
        """
        Discover Python files in a module for validation.
        
        Args:
            module_path: Path to the module directory
            comprehensive: If True, scan all Python files recursively
            
        Returns:
            List of Python file paths to validate
        """
        files = []
        module_dir = Path(module_path)
        
        if not module_dir.exists():
            logger.warning(f"Module directory does not exist: {module_path}")
            return files
        
        if comprehensive:
            # Recursive scan of all relevant files (Python and Markdown)
            for pattern in ["*.py", "*.md"]:
                for file_path in module_dir.rglob(pattern):
                    # Skip __pycache__ and other generated directories
                    if "__pycache__" not in str(file_path) and ".pyc" not in str(file_path):
                        files.append(str(file_path))
            logger.info(f"Comprehensive scan found {len(files)} files (.py, .md) in {module_path}")
        else:
            # Standard scan - only core files
            core_files = ["api.py", "services.py", "database.py", "module_settings.py", "__init__.py"]
            for core_file in core_files:
                file_path = module_dir / core_file
                if file_path.exists():
                    files.append(str(file_path))
            logger.info(f"Standard scan found {len(files)} core files in {module_path}")
        
        return sorted(files)


class ModuleScanner:
    """Scanner for discovering modules in the framework."""
    
    def __init__(self, modules_dir: str = "modules"):
        """
        Initialize the module scanner.
        
        Args:
            modules_dir: Directory containing modules
        """
        self.modules_dir = modules_dir
    
    def discover_modules(self) -> List[Dict[str, Any]]:
        """
        Discover all modules in the framework.
        
        Returns:
            List of module information dictionaries
        """
        logger.info("Discovering framework modules")
        
        # Start with empty modules list
        modules = []
        
        # Check if modules directory exists
        if not os.path.exists(self.modules_dir):
            logger.error(f"Modules directory not found: {self.modules_dir}")
            return []
        
        # Look for modules in all module types (core, standard, extensions)
        for module_type in ["core", "standard", "extensions"]:
            module_type_path = os.path.join(self.modules_dir, module_type)
            
            if not os.path.exists(module_type_path):
                logger.debug(f"Module type directory not found: {module_type_path}")
                continue
            
            # Scan module directories
            self._scan_directory_for_modules(module_type_path, module_type, "", modules)
        
        logger.info(f"Discovered {len(modules)} modules")
        return modules
    
    def _scan_directory_for_modules(self, directory: str, module_type: str, 
                                   group_prefix: str, modules: List[Dict[str, Any]],
                                   allow_nested: bool = True):
        """
        Scan a directory for modules.
        
        Args:
            directory: Directory to scan
            module_type: Type of module (core, standard, extensions)
            group_prefix: Prefix for module ID (for nested modules)
            modules: List to add discovered modules to
            allow_nested: Whether to allow looking for modules in subdirectories
        """
        # Check each item in the directory
        try:
            items = os.listdir(directory)
        except Exception as e:
            logger.error(f"Error reading directory {directory}: {str(e)}")
            return
            
        for item in items:
            item_path = os.path.join(directory, item)
            
            # Skip if not a directory
            if not os.path.isdir(item_path):
                continue
            
            # Skip if .disabled file exists
            if os.path.exists(os.path.join(item_path, ".disabled")):
                logger.debug(f"Skipping disabled module: {item}")
                continue
            
            # v3.0.0 ONLY: Check for decorator-based module (api.py with MODULE_* constants)
            api_path = os.path.join(item_path, "api.py")
            
            if os.path.exists(api_path):
                module_info = self._discover_v3_module(item_path, item, module_type, group_prefix)
                if module_info:
                    modules.append(module_info)
                    logger.debug(f"Discovered v3.0.0 module: {module_info['id']}")
                else:
                    logger.warning(f"Module {item} has api.py but doesn't follow v3.0.0 patterns (missing MODULE_* constants or decorators)")
                    # If no module found but we allow nesting and no group prefix yet (to limit nesting depth)
                    if allow_nested and not group_prefix:
                        # Look for modules one level deeper using the directory name as group prefix
                        self._scan_directory_for_modules(item_path, module_type, item, modules, allow_nested=False)
            else:
                logger.debug(f"Skipping directory {item}: no api.py file (v3.0.0 modules require api.py)")
                # If no api.py but we allow nesting and no group prefix yet (to limit nesting depth)
                if allow_nested and not group_prefix:
                    # Look for modules one level deeper using the directory name as group prefix
                    self._scan_directory_for_modules(item_path, module_type, item, modules, allow_nested=False)
    
    def find_module(self, module_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a specific module by ID.
        
        Args:
            module_id: ID of the module to find
            
        Returns:
            Module information dictionary or None if not found
        """
        modules = self.discover_modules()
        
        for module in modules:
            if module["id"] == module_id:
                return module
        
        return None
    
    def _discover_v3_module(self, module_path: str, module_dir_name: str, 
                           module_type: str, group_prefix: str) -> Optional[Dict[str, Any]]:
        """
        Discover v3.0.0 decorator-based module by parsing MODULE_* constants from api.py.
        
        Args:
            module_path: Path to the module directory
            module_dir_name: Name of the module directory
            module_type: Type of module (core, standard, extensions)
            group_prefix: Prefix for nested modules
            
        Returns:
            Module information dictionary or None if not a v3.0.0 module
        """
        import re
        
        api_path = os.path.join(module_path, "api.py")
        if not os.path.exists(api_path):
            return None
        
        try:
            with open(api_path, "r") as f:
                content = f.read()
            
            # Look for MODULE_* constants that indicate v3.0.0 architecture
            module_id_match = re.search(r'MODULE_ID\s*=\s*["\']([^"\']+)["\']', content)
            module_version_match = re.search(r'MODULE_VERSION\s*=\s*["\']([^"\']+)["\']', content)
            module_description_match = re.search(r'MODULE_DESCRIPTION\s*=\s*["\']([^"\']+)["\']', content)
            
            # Check for decorator patterns that indicate v3.0.0
            has_register_service = "@register_service" in content
            has_data_integrity = "@enforce_data_integrity" in content or "DataIntegrityModule" in content
            
            # Must have at least MODULE_ID and some v3.0.0 indicators
            if not (module_id_match and (has_register_service or has_data_integrity)):
                return None
            
            # Extract metadata
            module_id = module_id_match.group(1)
            version = module_version_match.group(1) if module_version_match else "1.0.0"
            description = module_description_match.group(1) if module_description_match else f"v3.0.0 module: {module_dir_name}"
            
            # Create v3.0.0 module metadata
            module_metadata = {
                "id": module_id.split(".")[-1],  # Just the module name part
                "version": version,
                "description": description
            }
            
            # Return v3.0.0 module info
            return {
                "path": module_path,
                "type": module_type,
                "manifest": module_metadata,  # For compatibility with existing code
                "id": module_id,
                "version": version,
                "architecture": "v3.0.0"
            }
            
        except Exception as e:
            logger.debug(f"Error parsing v3.0.0 module {module_path}: {str(e)}")
            return None
