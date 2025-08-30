# tools/test_module_dependencies.py

"""
Module dependency testing tool.
Scans all modules for service dependencies and ensures they match registered service names.
"""

import os
import re
import json
import logging
from typing import Dict, List, Set, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dependency_test")

def scan_module_manifests() -> Dict[str, List[str]]:
    """
    Scan all module manifests to get their dependencies.
    
    Returns:
        Dictionary mapping module IDs to their dependencies
    """
    dependencies = {}
    modules_path = "modules"
    
    # Scan core, standard, and extensions directories
    for module_type in ["core", "standard", "extensions"]:
        type_path = os.path.join(modules_path, module_type)
        
        if not os.path.exists(type_path):
            continue
            
        # Scan for module directories
        for item in os.listdir(type_path):
            item_path = os.path.join(type_path, item)
            
            if os.path.isdir(item_path):
                manifest_path = os.path.join(item_path, "manifest.json")
                
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)
                            
                        module_id = f"{module_type}.{manifest['id']}"
                        dependencies[module_id] = manifest.get("dependencies", [])
                        
                    except Exception as e:
                        logger.error(f"Error reading manifest for {item}: {e}")
    
    return dependencies

def scan_module_service_registrations() -> Dict[str, Set[str]]:
    """
    Scan module code to find service registrations.
    
    Returns:
        Dictionary mapping module IDs to set of registered service names
    """
    registered_services = {}
    modules_path = "modules"
    
    for module_type in ["core", "standard", "extensions"]:
        type_path = os.path.join(modules_path, module_type)
        
        if not os.path.exists(type_path):
            continue
            
        for item in os.listdir(type_path):
            item_path = os.path.join(type_path, item)
            
            if os.path.isdir(item_path):
                # Check if it's a module (has manifest.json)
                manifest_path = os.path.join(item_path, "manifest.json")
                
                if os.path.exists(manifest_path):
                    # Read the manifest to get the module ID
                    try:
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)
                            
                        module_id = f"{module_type}.{manifest['id']}"
                        
                        # Initialize services set
                        registered_services[module_id] = set()
                        
                        # Scan all .py files in the module
                        _scan_module_files(item_path, module_id, registered_services)
                        
                    except Exception as e:
                        logger.error(f"Error scanning services for {item}: {e}")
    
    return registered_services

def _scan_module_files(module_path: str, module_id: str, registered_services: Dict[str, Set[str]]):
    """
    Scan all Python files in a module for service registrations.
    
    Args:
        module_path: Path to the module directory
        module_id: ID of the module
        registered_services: Dictionary to update with found service registrations
    """
    service_registration_pattern = r'app_context\.register_service\s*\(\s*["\']([^"\']+)["\']'
    
    for root, _, files in os.walk(module_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # Find all service registrations
                    matches = re.findall(service_registration_pattern, content)
                    
                    for service_name in matches:
                        registered_services[module_id].add(service_name)
                        
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")

def scan_module_service_dependencies() -> Dict[str, Set[str]]:
    """
    Scan module code to find service dependencies (get_service calls).
    
    Returns:
        Dictionary mapping module IDs to set of referenced service names
    """
    service_dependencies = {}
    modules_path = "modules"
    
    for module_type in ["core", "standard", "extensions"]:
        type_path = os.path.join(modules_path, module_type)
        
        if not os.path.exists(type_path):
            continue
            
        for item in os.listdir(type_path):
            item_path = os.path.join(type_path, item)
            
            if os.path.isdir(item_path):
                # Check if it's a module (has manifest.json)
                manifest_path = os.path.join(item_path, "manifest.json")
                
                if os.path.exists(manifest_path):
                    # Read the manifest to get the module ID
                    try:
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)
                            
                        module_id = f"{module_type}.{manifest['id']}"
                        
                        # Initialize dependencies set
                        service_dependencies[module_id] = set()
                        
                        # Scan all .py files in the module
                        _scan_module_files_for_dependencies(item_path, module_id, service_dependencies)
                        
                    except Exception as e:
                        logger.error(f"Error scanning dependencies for {item}: {e}")
    
    return service_dependencies

def _scan_module_files_for_dependencies(module_path: str, module_id: str, service_dependencies: Dict[str, Set[str]]):
    """
    Scan all Python files in a module for service dependencies.
    
    Args:
        module_path: Path to the module directory
        module_id: ID of the module
        service_dependencies: Dictionary to update with found service dependencies
    """
    service_dependency_pattern = r'get_service\s*\(\s*["\']([^"\']+)["\']'
    
    for root, _, files in os.walk(module_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # Find all service dependencies
                    matches = re.findall(service_dependency_pattern, content)
                    
                    for service_name in matches:
                        service_dependencies[module_id].add(service_name)
                        
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")

def analyze_dependencies(
    module_dependencies: Dict[str, List[str]],
    registered_services: Dict[str, Set[str]],
    service_dependencies: Dict[str, Set[str]]
) -> List[Tuple[str, str, str]]:
    """
    Analyze dependencies for inconsistencies.
    
    Args:
        module_dependencies: Module manifest dependencies
        registered_services: Registered service names by module
        service_dependencies: Service dependencies by module
        
    Returns:
        List of (module_id, service_name, issue) tuples
    """
    issues = []
    
    # Create a mapping from module ID to service names
    module_to_services = {}
    for module_id, services in registered_services.items():
        for service_name in services:
            module_to_services[service_name] = module_id
    
    # Check each module's service dependencies
    for module_id, dependencies in service_dependencies.items():
        for service_name in dependencies:
            # See if we can find which module provides this service
            provider_module = module_to_services.get(service_name)
            
            if provider_module is None:
                # The service name doesn't match any registered service
                issues.append((module_id, service_name, "Service not registered by any module"))
            else:
                # Check if the module dependency is declared
                if provider_module not in module_dependencies.get(module_id, []):
                    issues.append((module_id, service_name, f"Missing dependency on {provider_module}"))
    
    # Check for mismatches between module ID and service name
    for module_id, services in registered_services.items():
        if module_id not in services:
            # The module doesn't register a service with its own name
            issues.append((module_id, module_id, "Module doesn't register service with its ID name"))
    
    return issues

def print_report(issues: List[Tuple[str, str, str]]):
    """
    Print a report of dependency issues.
    
    Args:
        issues: List of (module_id, service_name, issue) tuples
    """
    if not issues:
        print("No dependency issues found!")
        return
    
    print(f"Found {len(issues)} dependency issues:")
    print()
    
    for module_id, service_name, issue in issues:
        print(f"Module: {module_id}")
        print(f"Service: {service_name}")
        print(f"Issue: {issue}")
        print()

if __name__ == "__main__":
    # Scan module manifests
    module_dependencies = scan_module_manifests()
    print(f"Scanned {len(module_dependencies)} module manifests")
    
    # Scan for service registrations
    registered_services = scan_module_service_registrations()
    print(f"Found {sum(len(services) for services in registered_services.values())} service registrations")
    
    # Scan for service dependencies
    service_dependencies = scan_module_service_dependencies()
    print(f"Found {sum(len(deps) for deps in service_dependencies.values())} service dependencies")
    
    # Analyze dependencies
    issues = analyze_dependencies(module_dependencies, registered_services, service_dependencies)
    
    # Print report
    print_report(issues)
