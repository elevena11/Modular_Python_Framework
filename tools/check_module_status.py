# tools/check_module_status.py

"""
Standalone module status checker utility.
Analyzes module structure and dependencies without requiring a running application.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("module_status_checker")

def scan_module_manifests() -> Dict[str, Dict[str, Any]]:
    """
    Scan all modules and read their manifest files.
    
    Returns:
        Dictionary mapping module IDs to their manifest data
    """
    modules = {}
    modules_path = "modules"
    
    # Scan core, standard, and extensions directories
    for module_type in ["core", "standard", "extensions"]:
        type_path = os.path.join(modules_path, module_type)
        
        if not os.path.exists(type_path):
            logger.warning(f"Module directory not found: {type_path}")
            continue
            
        # First check for modules directly in this directory
        for item in os.listdir(type_path):
            item_path = os.path.join(type_path, item)
            
            if os.path.isdir(item_path):
                manifest_path = os.path.join(item_path, "manifest.json")
                
                if os.path.exists(manifest_path):
                    # Skip if .disabled file exists
                    if os.path.exists(os.path.join(item_path, ".disabled")):
                        logger.info(f"Skipping disabled module: {item}")
                        continue
                    
                    try:
                        # Read the manifest
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)
                        
                        # Build the module ID
                        module_id = f"{module_type}.{manifest['id']}"
                        
                        # Store module info
                        modules[module_id] = {
                            "manifest": manifest,
                            "path": item_path,
                            "type": module_type,
                            "entry_point": manifest.get("entry_point", "api.py")
                        }
                        
                        logger.info(f"Found module: {module_id}")
                    except Exception as e:
                        logger.error(f"Error loading manifest for {item}: {str(e)}")
                
                # Also check for nested modules (one level deep)
                for subitem in os.listdir(item_path):
                    subitem_path = os.path.join(item_path, subitem)
                    
                    if os.path.isdir(subitem_path):
                        manifest_path = os.path.join(subitem_path, "manifest.json")
                        
                        if os.path.exists(manifest_path):
                            # Skip if .disabled file exists
                            if os.path.exists(os.path.join(subitem_path, ".disabled")):
                                logger.info(f"Skipping disabled module: {item}/{subitem}")
                                continue
                            
                            try:
                                # Read the manifest
                                with open(manifest_path, "r") as f:
                                    manifest = json.load(f)
                                
                                # Build the module ID
                                module_id = f"{module_type}.{item}.{manifest['id']}"
                                
                                # Store module info
                                modules[module_id] = {
                                    "manifest": manifest,
                                    "path": subitem_path,
                                    "type": module_type,
                                    "entry_point": manifest.get("entry_point", "api.py")
                                }
                                
                                logger.info(f"Found nested module: {module_id}")
                            except Exception as e:
                                logger.error(f"Error loading manifest for {item}/{subitem}: {str(e)}")
    
    return modules

def check_module_dependencies(modules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check dependencies between modules.
    
    Args:
        modules: Dictionary of modules and their manifests
        
    Returns:
        Dictionary with dependency analysis results
    """
    # Build dependency graph
    dependency_graph = {}
    missing_dependencies = {}
    cyclic_dependencies = []
    
    for module_id, module_data in modules.items():
        dependencies = module_data["manifest"].get("dependencies", [])
        dependency_graph[module_id] = dependencies
        
        # Check for missing dependencies
        missing = [dep for dep in dependencies if dep not in modules]
        if missing:
            missing_dependencies[module_id] = missing
    
    # Check for cyclic dependencies using a simple DFS
    def has_cycle(node, visited, path):
        visited.add(node)
        path.add(node)
        
        for neighbor in dependency_graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, path):
                    return True
            elif neighbor in path:
                cyclic_dependencies.append((node, neighbor))
                return True
        
        path.remove(node)
        return False
    
    visited = set()
    for node in dependency_graph:
        if node not in visited:
            has_cycle(node, visited, set())
    
    return {
        "dependency_graph": dependency_graph,
        "missing_dependencies": missing_dependencies,
        "cyclic_dependencies": cyclic_dependencies
    }

def check_module_entry_points(modules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check if module entry points exist.
    
    Args:
        modules: Dictionary of modules and their manifests
        
    Returns:
        Dictionary with entry point analysis results
    """
    missing_entry_points = {}
    invalid_entry_points = {}
    
    for module_id, module_data in modules.items():
        entry_point = module_data.get("entry_point", "api.py")
        path = module_data["path"]
        
        entry_point_path = os.path.join(path, entry_point)
        
        if not os.path.exists(entry_point_path):
            missing_entry_points[module_id] = entry_point
        else:
            # Check if entry point has initialize function
            try:
                with open(entry_point_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                if "def initialize(" not in content and "def initialize " not in content:
                    invalid_entry_points[module_id] = f"Missing initialize function in {entry_point}"
            except Exception as e:
                invalid_entry_points[module_id] = f"Error reading {entry_point}: {str(e)}"
    
    return {
        "missing_entry_points": missing_entry_points,
        "invalid_entry_points": invalid_entry_points
    }

def check_settings_files(modules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check which modules have dedicated settings files.
    
    Args:
        modules: Dictionary of modules and their manifests
        
    Returns:
        Dictionary with settings file analysis results
    """
    modules_with_settings = {}
    modules_without_settings = []
    
    for module_id, module_data in modules.items():
        path = module_data["path"]
        settings_path = os.path.join(path, "module_settings.py")
        
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Check for key components
                has_default_settings = "DEFAULT_SETTINGS" in content
                has_validation_schema = "VALIDATION_SCHEMA" in content
                has_ui_metadata = "UI_METADATA" in content
                has_register_function = "def register_settings" in content
                
                modules_with_settings[module_id] = {
                    "has_default_settings": has_default_settings,
                    "has_validation_schema": has_validation_schema,
                    "has_ui_metadata": has_ui_metadata,
                    "has_register_function": has_register_function,
                    "uses_new_pattern": has_default_settings and has_register_function
                }
            except Exception as e:
                modules_with_settings[module_id] = {
                    "error": f"Error reading settings file: {str(e)}"
                }
        else:
            modules_without_settings.append(module_id)
    
    return {
        "modules_with_settings": modules_with_settings,
        "modules_without_settings": modules_without_settings
    }

def check_module_status(module_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the status of modules.
    
    Args:
        module_id: ID of a specific module to check, or None for all modules
        
    Returns:
        Dictionary with module status information
    """
    # Scan all module manifests
    modules = scan_module_manifests()
    
    if not modules:
        return {
            "error": "No modules found",
            "details": "Check if you're running from the correct directory"
        }
    
    # If a specific module was requested
    if module_id:
        if module_id not in modules:
            return {
                "error": f"Module '{module_id}' not found",
                "available_modules": list(modules.keys())
            }
        
        # Get just the requested module
        module_data = modules[module_id]
        
        # Check dependencies
        dependencies = module_data["manifest"].get("dependencies", [])
        dependency_status = {}
        
        for dep in dependencies:
            dependency_status[dep] = {
                "available": dep in modules
            }
        
        # Check entry point
        entry_point = module_data.get("entry_point", "api.py")
        entry_point_path = os.path.join(module_data["path"], entry_point)
        entry_point_status = os.path.exists(entry_point_path)
        
        # Check settings file
        settings_path = os.path.join(module_data["path"], "module_settings.py")
        has_settings_file = os.path.exists(settings_path)
        
        return {
            "module_id": module_id,
            "name": module_data["manifest"].get("name", "Unknown"),
            "version": module_data["manifest"].get("version", "Unknown"),
            "description": module_data["manifest"].get("description", ""),
            "author": module_data["manifest"].get("author", "Unknown"),
            "type": module_data["type"],
            "path": module_data["path"],
            "entry_point": entry_point,
            "entry_point_status": "Found" if entry_point_status else "Missing",
            "dependencies": dependency_status,
            "has_settings_file": has_settings_file
        }
    
    # For all modules
    dependency_status = check_module_dependencies(modules)
    entry_point_status = check_module_entry_points(modules)
    settings_status = check_settings_files(modules)
    
    return {
        "total_modules": len(modules),
        "module_types": {
            "core": len([m for m in modules if m.startswith("core.")]),
            "standard": len([m for m in modules if m.startswith("standard.")]),
            "extensions": len([m for m in modules if m.startswith("extensions.")])
        },
        "dependency_status": dependency_status,
        "entry_point_status": entry_point_status,
        "settings_status": settings_status,
        "modules": {
            module_id: {
                "name": module_data["manifest"].get("name", "Unknown"),
                "version": module_data["manifest"].get("version", "Unknown"),
                "type": module_data["type"]
            }
            for module_id, module_data in modules.items()
        }
    }

def print_report(result: Dict[str, Any]):
    """
    Print a formatted report of the status check.
    
    Args:
        result: Result from check_module_status
    """
    if "error" in result:
        print(f"ERROR: {result['error']}")
        if "details" in result:
            print(f"Details: {result['details']}")
        if "available_modules" in result:
            print(f"Available modules: {', '.join(result['available_modules'])}")
        return
    
    if "total_modules" in result:
        # Full report for all modules
        print(f"== MODULE STATUS REPORT ==")
        print(f"Total modules: {result['total_modules']}")
        print(f"  - Core: {result['module_types']['core']}")
        print(f"  - Standard: {result['module_types']['standard']}")
        print(f"  - Extensions: {result['module_types']['extensions']}")
        print()
        
        # Dependency issues
        missing_deps = result["dependency_status"]["missing_dependencies"]
        cyclic_deps = result["dependency_status"]["cyclic_dependencies"]
        
        if missing_deps:
            print("MISSING DEPENDENCIES:")
            for module_id, missing in missing_deps.items():
                print(f"  {module_id} is missing: {', '.join(missing)}")
            print()
        
        if cyclic_deps:
            print("CYCLIC DEPENDENCIES:")
            for source, target in cyclic_deps:
                print(f"  {source} <-> {target}")
            print()
        
        # Entry point issues
        missing_entries = result["entry_point_status"]["missing_entry_points"]
        invalid_entries = result["entry_point_status"]["invalid_entry_points"]
        
        if missing_entries:
            print("MISSING ENTRY POINTS:")
            for module_id, entry_point in missing_entries.items():
                print(f"  {module_id}: {entry_point}")
            print()
        
        if invalid_entries:
            print("INVALID ENTRY POINTS:")
            for module_id, issue in invalid_entries.items():
                print(f"  {module_id}: {issue}")
            print()
        
        # Settings status
        with_settings = len(result["settings_status"]["modules_with_settings"])
        without_settings = len(result["settings_status"]["modules_without_settings"])
        
        print("SETTINGS STATUS:")
        print(f"  Modules with dedicated settings files: {with_settings}")
        print(f"  Modules without settings files: {without_settings}")
        
        if without_settings > 0:
            print("  Modules that need settings files:")
            for module_id in result["settings_status"]["modules_without_settings"]:
                print(f"    - {module_id}")
        print()
        
        # Print module summary
        print("MODULE SUMMARY:")
        for module_id, info in result["modules"].items():
            print(f"  {module_id} ({info['name']}) - {info['version']}")
    else:
        # Single module report
        print(f"== MODULE STATUS: {result['module_id']} ==")
        print(f"Name: {result['name']}")
        print(f"Version: {result['version']}")
        print(f"Description: {result['description']}")
        print(f"Author: {result['author']}")
        print(f"Type: {result['type']}")
        print(f"Path: {result['path']}")
        print(f"Entry Point: {result['entry_point']} ({result['entry_point_status']})")
        print(f"Has Settings File: {'Yes' if result['has_settings_file'] else 'No'}")
        print()
        
        print("Dependencies:")
        for dep, status in result["dependencies"].items():
            print(f"  {dep}: {'Available' if status['available'] else 'MISSING'}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        result = check_module_status(sys.argv[1])
    else:
        result = check_module_status()
    
    print_report(result)
