#!/usr/bin/env python3
"""
tools/pytest_compliance.py
Pytest-based compliance testing for framework modules.

This provides a more developer-friendly testing approach than the JSON-based compliance.py.
Perfect for LLM-assisted iterative development.

Usage:
    python -m pytest tools/pytest_compliance.py::test_module_compliance[standard.veritas_knowledge_graph]
    python -m pytest tools/pytest_compliance.py -v
    python tools/pytest_compliance.py --module veritas_knowledge_graph
"""

import pytest
from _pytest.outcomes import Skipped
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import sys

# Framework root
FRAMEWORK_ROOT = Path(__file__).parent.parent

def discover_modules() -> List[Dict[str, Any]]:
    """Discover all modules in the framework."""
    modules = []
    
    for module_type in ['core', 'standard', 'extensions']:
        type_path = FRAMEWORK_ROOT / "modules" / module_type
        
        if not type_path.exists():
            continue
            
        for module_dir in type_path.iterdir():
            if module_dir.is_dir():
                manifest_path = module_dir / "manifest.json"
                
                if manifest_path.exists() and not (module_dir / ".disabled").exists():
                    try:
                        with open(manifest_path) as f:
                            manifest = json.load(f)
                        
                        modules.append({
                            'id': f"{module_type}.{manifest['id']}",
                            'name': manifest['id'],
                            'type': module_type,
                            'path': module_dir,
                            'manifest': manifest
                        })
                    except Exception:
                        continue
    
    return modules

class ComplianceChecker:
    """Enhanced compliance checker with test-friendly methods."""
    
    def __init__(self, module_info: Dict[str, Any]):
        self.module = module_info
        self.path = module_info['path']
        self.module_id = module_info['id']
    
    def check_file_exists(self, filename: str) -> bool:
        """Check if a required file exists."""
        return (self.path / filename).exists()
    
    def get_file_content(self, filename: str) -> str:
        """Get file content safely."""
        file_path = self.path / filename
        if not file_path.exists():
            return ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    def check_pattern_in_file(self, filename: str, pattern: str) -> bool:
        """Check if a pattern exists in a file."""
        content = self.get_file_content(filename)
        return bool(re.search(pattern, content, re.MULTILINE | re.DOTALL))
    
    def check_anti_pattern_in_file(self, filename: str, pattern: str) -> bool:
        """Check if an anti-pattern exists in a file (returns True if found - bad)."""
        content = self.get_file_content(filename)
        return bool(re.search(pattern, content, re.MULTILINE | re.DOTALL))
    
    def extract_function_body(self, filename: str, function_name: str) -> str:
        """Extract function body for detailed analysis."""
        content = self.get_file_content(filename)
        
        # Find the function definition
        func_pattern = rf"async\s+def\s+{function_name}\s*\([^)]*\):"
        match = re.search(func_pattern, content)
        
        if not match:
            return ""
        
        start_pos = match.end()
        lines = content[start_pos:].split('\n')
        
        # Find the function body by tracking indentation
        function_lines = []
        base_indent = None
        
        for line in lines:
            if not line.strip():  # Empty line
                function_lines.append(line)
                continue
                
            current_indent = len(line) - len(line.lstrip())
            
            if base_indent is None and line.strip():
                base_indent = current_indent
            
            if line.strip() and current_indent <= base_indent and function_lines:
                # We've reached the end of the function
                break
                
            function_lines.append(line)
        
        return '\n'.join(function_lines)

# Pytest fixtures
@pytest.fixture(params=discover_modules(), ids=lambda m: m['id'])
def module_info(request):
    """Parametrized fixture providing all discovered modules."""
    return request.param

@pytest.fixture
def compliance_checker(module_info):
    """Create compliance checker for module."""
    return ComplianceChecker(module_info)

# Core Implementation Standards Tests
class TestCoreStandards:
    """Test core implementation standards."""
    
    def test_module_structure(self, compliance_checker):
        """Test basic module structure requirements."""
        checker = compliance_checker
        
        # Required files
        assert checker.check_file_exists("manifest.json"), "manifest.json missing"
        assert checker.check_file_exists("api.py"), "api.py missing - required for framework integration"
        assert checker.check_file_exists("services.py"), "services.py missing"
        
        # Check manifest format
        manifest = checker.module['manifest']
        required_fields = ["id", "name", "version", "description", "author", "dependencies", "entry_point"]
        
        for field in required_fields:
            assert field in manifest, f"manifest.json missing required field: {field}"
        
        assert manifest["entry_point"] == "api.py", "entry_point must be api.py for framework compliance"
    
    def test_two_phase_initialization_phase1(self, compliance_checker):
        """Test Phase 1 initialization compliance."""
        checker = compliance_checker
        
        # Phase 1 function must exist
        assert checker.check_pattern_in_file(
            "api.py", 
            r"async\s+def\s+initialize\s*\(\s*app_context\s*\):"
        ), "Missing Phase 1 initialize(app_context) function in api.py"
        
        # Extract Phase 1 function body
        phase1_body = checker.extract_function_body("api.py", "initialize")
        
        # Phase 1 must not contain database operations
        forbidden_patterns = [
            r"db_session",
            r"create_tables",
            r"session\.",
            r"engine\.",
            r"execute\s*\("
        ]
        
        for pattern in forbidden_patterns:
            assert not re.search(pattern, phase1_body), f"Phase 1 contains forbidden database operation: {pattern}"
    
    def test_two_phase_initialization_phase2(self, compliance_checker):
        """Test Phase 2 initialization compliance."""
        checker = compliance_checker
        
        # Check for setup hook registration in Phase 1
        assert checker.check_pattern_in_file(
            "api.py",
            r"app_context\.register_module_setup_hook\s*\("
        ), "Missing setup hook registration in Phase 1"
        
        # Phase 2 function must exist
        assert checker.check_pattern_in_file(
            "api.py",
            r"async\s+def\s+setup_module\s*\(\s*app_context\s*\):"
        ), "Missing Phase 2 setup_module(app_context) function in api.py"
    
    def test_service_registration(self, compliance_checker):
        """Test service registration pattern."""
        checker = compliance_checker
        
        # Must register service in Phase 1
        assert checker.check_pattern_in_file(
            "api.py",
            r"app_context\.register_service\s*\("
        ), "Missing service registration in api.py"
        
        # Must register shutdown handler
        assert checker.check_pattern_in_file(
            "api.py", 
            r"app_context\.register_shutdown_handler\s*\("
        ), "Missing shutdown handler registration in api.py"
    
    def test_module_dependency_management(self, compliance_checker):
        """Test module dependency declaration."""
        checker = compliance_checker
        manifest = checker.module['manifest']
        
        # Dependencies must be a list
        assert isinstance(manifest.get('dependencies', []), list), "dependencies must be a list in manifest.json"
        
        # If dependencies exist, they should be valid module IDs
        for dep in manifest.get('dependencies', []):
            assert isinstance(dep, str), f"Dependency '{dep}' must be a string"
            assert '.' in dep or dep in ['core', 'standard', 'extensions'], f"Invalid dependency format: {dep}"

class TestAPIStandards:
    """Test API implementation standards."""
    
    def test_api_schema_validation(self, compliance_checker):
        """Test API schema validation implementation."""
        checker = compliance_checker
        
        # Skip if no API functionality
        api_content = checker.get_file_content("api.py")
        if "from fastapi import" not in api_content and "APIRouter" not in api_content:
            pytest.skip("Module does not implement API functionality")
        
        # If API is implemented, schemas should exist
        assert checker.check_file_exists("api_schemas.py"), "api_schemas.py required for API modules"
        
        # Check for Pydantic imports in schemas
        assert checker.check_pattern_in_file(
            "api_schemas.py",
            r"from pydantic import.*BaseModel"
        ), "api_schemas.py must import Pydantic BaseModel"
        
        # Check for response model usage in API
        assert checker.check_pattern_in_file(
            "api.py",
            r"response_model\s*="
        ), "API endpoints should use response_model for validation"

class TestDatabaseStandards:
    """Test database implementation standards."""
    
    def test_database_files_exist(self, compliance_checker):
        """Test that database files exist if database functionality is used."""
        checker = compliance_checker
        
        # Check if module uses database
        api_content = checker.get_file_content("api.py")
        services_content = checker.get_file_content("services.py")
        
        uses_database = any([
            "database" in checker.module['manifest'].get('dependencies', []),
            "sqlalchemy" in api_content.lower(),
            "sqlalchemy" in services_content.lower(),
            "db_models" in api_content or "db_models" in services_content
        ])
        
        if not uses_database:
            pytest.skip("Module does not use database functionality")
        
        # If database is used, these files should exist
        assert checker.check_file_exists("database.py"), "database.py required for database modules"
        assert checker.check_file_exists("db_models.py"), "db_models.py required for database modules"
    
    def test_async_database_operations(self, compliance_checker):
        """Test async database operations implementation."""
        checker = compliance_checker
        
        if not checker.check_file_exists("database.py"):
            pytest.skip("No database.py file")
        
        # Database operations should be async
        assert checker.check_pattern_in_file(
            "database.py",
            r"async\s+def\s+\w+"
        ), "Database operations should be async"
        
        # Should use AsyncSession
        assert checker.check_pattern_in_file(
            "database.py",
            r"AsyncSession"
        ), "Database operations should use AsyncSession"

class TestUIStandards:
    """Test UI implementation standards."""
    
    def test_streamlit_implementation(self, compliance_checker):
        """Test Streamlit UI implementation."""
        checker = compliance_checker
        
        streamlit_file = checker.path / "ui" / "ui_streamlit.py"
        if not streamlit_file.exists():
            pytest.skip("No Streamlit UI implementation")
        
        # Should have a render function that takes ui_context or app_context
        has_render_function = (
            checker.check_pattern_in_file(
                "ui/ui_streamlit.py",
                r"def\s+render_\w+\s*\(\s*(ui_context|app_context)\s*\)"
            ) or
            checker.check_pattern_in_file(
                "ui/ui_streamlit.py", 
                r"def\s+render_ui\s*\(\s*(ui_context|app_context)\s*\)"
            )
        )
        
        assert has_render_function, "Streamlit UI must have a render function that takes ui_context or app_context parameter"
    

# Utility functions for standalone usage
def test_specific_module(module_name: str):
    """Test a specific module by name."""
    modules = discover_modules()
    
    target_module = None
    for module in modules:
        if module['name'] == module_name or module['id'].endswith(f".{module_name}"):
            target_module = module
            break
    
    if not target_module:
        print(f"[ERROR] Module '{module_name}' not found")
        return False
    
    print(f"Testing module: {target_module['id']}")
    checker = ComplianceChecker(target_module)
    
    # Run core tests
    test_core = TestCoreStandards()
    test_api = TestAPIStandards() 
    test_db = TestDatabaseStandards()
    test_ui = TestUIStandards()
    
    tests_run = 0
    tests_passed = 0
    
    # Run all test methods
    for test_class in [test_core, test_api, test_db, test_ui]:
        for method_name in dir(test_class):
            if method_name.startswith('test_'):
                tests_run += 1
                try:
                    method = getattr(test_class, method_name)
                    method(checker)
                    print(f"[PASS] {method_name}")
                    tests_passed += 1
                except AssertionError as e:
                    print(f"[FAIL] {method_name}: {str(e)}")
                except Skipped as e:
                    print(f"[SKIP] {method_name}: {str(e)}")
                    tests_run -= 1  # Don't count skipped tests
                except Exception as e:
                    print(f"[ERROR] {method_name}: Error - {str(e)}")
    
    print(f"\nResults: {tests_passed}/{tests_run} tests passed")
    return tests_passed == tests_run

def main():
    """Main function for standalone usage."""
    parser = argparse.ArgumentParser(description="Test module compliance with pytest-style assertions")
    parser.add_argument("--module", "-m", help="Test specific module by name")
    
    args = parser.parse_args()
    
    if args.module:
        success = test_specific_module(args.module)
        sys.exit(0 if success else 1)
    else:
        print("Pytest Compliance Tester")
        print("Use: python -m pytest tools/pytest_compliance.py -v")
        print("Or:  python tools/pytest_compliance.py --module module_name")

if __name__ == "__main__":
    main()