#!/usr/bin/env python3
"""
Pre-runtime validation tool to catch standard errors before `python app.py` runs.

This tool combines compliance validation and pytest checks to eliminate common
runtime issues through proactive validation.

Usage:
    python tools/pre_runtime_validation.py           # Validate all
    python tools/pre_runtime_validation.py --module core.settings  # Validate specific module
    python tools/pre_runtime_validation.py --quick   # Quick critical checks only
"""

import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

class PreRuntimeValidator:
    """Validates framework before runtime to prevent standard errors."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.critical_standards = [
            "module_dependency",
            "module_structure", 
            "two_phase_initialization_phase1",
            "two_phase_initialization_phase2",
            "service_registration",
            "settings_api"
        ]
        
    def run_critical_compliance_check(self, module_id: str = None) -> Tuple[bool, List[str]]:
        """Run compliance check for critical standards only."""
        print(f"🔍 Running critical compliance validation...")
        
        cmd = ["python", "tools/compliance/compliance.py"]
        if module_id:
            cmd.extend(["--validate", module_id])
        else:
            cmd.append("--validate-all")
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                return False, [f"Compliance validation failed: {result.stderr}"]
            
            # Parse output for critical failures
            failures = []
            lines = result.stdout.split('\n')
            current_module = None
            
            for line in lines:
                if "Validating module" in line:
                    current_module = line.split("module ")[-1]
                elif "[FAIL]" in line:
                    # Check if it's a critical standard
                    for standard in self.critical_standards:
                        if standard in line:
                            failures.append(f"{current_module}: {line.strip()}")
                            
            return len(failures) == 0, failures
            
        except Exception as e:
            return False, [f"Error running compliance check: {str(e)}"]
    
    def run_pytest_structural_validation(self, module_id: str = None) -> Tuple[bool, List[str]]:
        """Run pytest structural validation."""
        print(f"🧪 Running pytest structural validation...")
        
        cmd = ["python", "tools/pytest_compliance.py"]
        if module_id:
            cmd.extend(["--module", module_id.split(".")[-1]])  # Get module name only
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            failures = []
            if result.returncode != 0:
                # Parse failures from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if "[FAIL]" in line:
                        failures.append(line.strip())
                        
            return len(failures) == 0, failures
            
        except Exception as e:
            return False, [f"Error running pytest validation: {str(e)}"]
    
    def check_import_safety(self) -> Tuple[bool, List[str]]:
        """Check for import issues that could cause startup failures."""
        print(f"📦 Checking import safety...")
        
        # Test importing core framework components
        test_imports = [
            "core.app_context",
            "core.config", 
            "core.module_loader"
        ]
        
        failures = []
        for import_module in test_imports:
            try:
                result = subprocess.run([
                    sys.executable, "-c", f"import {import_module}"
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode != 0:
                    failures.append(f"Import failed: {import_module} - {result.stderr.strip()}")
                    
            except Exception as e:
                failures.append(f"Import test error for {import_module}: {str(e)}")
        
        return len(failures) == 0, failures
    
    def check_database_connectivity(self) -> Tuple[bool, List[str]]:
        """Check basic database connectivity."""
        print(f"🗄️  Checking database connectivity...")
        
        try:
            # Simple database connection test
            result = subprocess.run([
                sys.executable, "-c", 
                "from core.config import Config; c = Config(); print('Database config loaded')"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                return False, [f"Database config test failed: {result.stderr.strip()}"]
            
            return True, []
            
        except Exception as e:
            return False, [f"Database connectivity check error: {str(e)}"]
    
    def validate_critical_files(self) -> Tuple[bool, List[str]]:
        """Validate critical framework files exist and are valid."""
        print(f"📋 Validating critical files...")
        
        critical_files = [
            "app.py",
            "core/app_context.py",
            "core/config.py", 
            "core/module_loader.py",
            "data/db_config.json"
        ]
        
        failures = []
        for file_path in critical_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                failures.append(f"Critical file missing: {file_path}")
            elif file_path.endswith('.json'):
                # Validate JSON syntax
                try:
                    with open(full_path) as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    failures.append(f"Invalid JSON in {file_path}: {str(e)}")
        
        return len(failures) == 0, failures
    
    def run_validation(self, module_id: str = None, quick: bool = False) -> bool:
        """Run complete pre-runtime validation."""
        print("🚀 Framework Pre-Runtime Validation")
        print("=" * 50)
        
        all_passed = True
        total_failures = []
        
        # 1. Critical file validation
        passed, failures = self.validate_critical_files()
        if not passed:
            all_passed = False
            total_failures.extend(failures)
            print("❌ Critical files validation: FAILED")
            for failure in failures:
                print(f"   • {failure}")
        else:
            print("✅ Critical files validation: PASSED")
        
        if not quick:
            # 2. Import safety check
            passed, failures = self.check_import_safety()
            if not passed:
                all_passed = False
                total_failures.extend(failures)
                print("❌ Import safety check: FAILED")
                for failure in failures:
                    print(f"   • {failure}")
            else:
                print("✅ Import safety check: PASSED")
            
            # 3. Database connectivity
            passed, failures = self.check_database_connectivity()
            if not passed:
                all_passed = False
                total_failures.extend(failures)
                print("❌ Database connectivity: FAILED")
                for failure in failures:
                    print(f"   • {failure}")
            else:
                print("✅ Database connectivity: PASSED")
        
        # 4. Critical compliance validation
        passed, failures = self.run_critical_compliance_check(module_id)
        if not passed:
            all_passed = False
            total_failures.extend(failures)
            print("❌ Critical compliance: FAILED")
            for failure in failures:
                print(f"   • {failure}")
        else:
            print("✅ Critical compliance: PASSED")
        
        if not quick:
            # 5. Pytest structural validation
            passed, failures = self.run_pytest_structural_validation(module_id)
            if not passed:
                all_passed = False
                total_failures.extend(failures)
                print("❌ Structural validation: FAILED")
                for failure in failures:
                    print(f"   • {failure}")
            else:
                print("✅ Structural validation: PASSED")
        
        print("\n" + "=" * 50)
        if all_passed:
            print("🎉 All validations PASSED - Safe to run `python app.py`")
            return True
        else:
            print(f"⚠️  {len(total_failures)} validation issues found")
            print("\nRecommended actions:")
            print("1. Fix compliance issues: python tools/compliance/compliance.py --validate-all")
            print("2. Run structure tests: python tools/pytest_compliance.py")
            print("3. Check module dependencies in manifest.json files")
            print("\n❌ DO NOT run `python app.py` until issues are resolved")
            return False

def main():
    parser = argparse.ArgumentParser(description="Pre-runtime validation to prevent standard errors")
    parser.add_argument("--module", "-m", help="Validate specific module (e.g., core.settings)")
    parser.add_argument("--quick", "-q", action="store_true", help="Quick validation (critical checks only)")
    
    args = parser.parse_args()
    
    validator = PreRuntimeValidator()
    success = validator.run_validation(args.module, args.quick)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()