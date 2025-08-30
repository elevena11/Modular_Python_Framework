#!/usr/bin/env python3
"""
tools/dev_watch.py
Real-time development feedback tool for module compliance.

Watches module files for changes and provides immediate compliance feedback.
Perfect for LLM-assisted iterative development.

Usage:
    python tools/dev_watch.py --module veritas_knowledge_graph
    python tools/dev_watch.py --module veritas_knowledge_graph --test
"""

import time
import sys
import argparse
from pathlib import Path
from typing import Dict, Set, Optional
import subprocess
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# Import our compliance checker
from pytest_compliance import discover_modules, ComplianceChecker, TestCoreStandards, TestAPIStandards

class ModuleWatcher(FileSystemEventHandler):
    """Watch module files for changes and trigger compliance checks."""
    
    def __init__(self, module_info: Dict, run_tests: bool = False):
        self.module = module_info
        self.module_path = module_info['path']
        self.run_tests = run_tests
        self.last_check = 0
        self.debounce_seconds = 2  # Wait 2 seconds between checks
        
        print(f"🔄 Watching {self.module['id']} at {self.module_path}")
        print(f"📁 Files: api.py, services.py, manifest.json, *.py")
        print("=" * 60)
        
        # Initial check
        self.check_compliance()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        # Only watch Python files and manifest
        file_path = Path(event.src_path)
        if not (file_path.suffix == '.py' or file_path.name == 'manifest.json'):
            return
        
        # Debounce rapid file changes
        current_time = time.time()
        if current_time - self.last_check < self.debounce_seconds:
            return
        
        self.last_check = current_time
        
        print(f"\n🔄 File changed: {file_path.name} - Re-validating...")
        self.check_compliance()
    
    def check_compliance(self):
        """Run compliance checks and display results."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n⏰ [{timestamp}] Checking compliance for {self.module['id']}")
        
        checker = ComplianceChecker(self.module)
        
        # Quick compliance checks
        results = {}
        
        # Core standards
        results.update(self._check_core_standards(checker))
        
        # API standards (if applicable)
        if self._has_api_functionality(checker):
            results.update(self._check_api_standards(checker))
        
        # Display results
        self._display_results(results)
        
        # Run tests if requested
        if self.run_tests:
            self._run_tests()
    
    def _check_core_standards(self, checker: ComplianceChecker) -> Dict[str, Dict]:
        """Check core implementation standards."""
        results = {}
        
        # Module Structure
        try:
            assert checker.check_file_exists("manifest.json")
            assert checker.check_file_exists("api.py")
            assert checker.check_file_exists("services.py")
            results["Module Structure"] = {"status": "✅", "message": "All required files present"}
        except AssertionError:
            missing = []
            if not checker.check_file_exists("manifest.json"): missing.append("manifest.json")
            if not checker.check_file_exists("api.py"): missing.append("api.py")
            if not checker.check_file_exists("services.py"): missing.append("services.py")
            results["Module Structure"] = {"status": "❌", "message": f"Missing: {', '.join(missing)}"}
        
        # Two-Phase Initialization Phase 1
        try:
            assert checker.check_pattern_in_file("api.py", r"async\s+def\s+initialize\s*\(\s*app_context\s*\):")
            
            # Check for forbidden database operations in Phase 1
            phase1_body = checker.extract_function_body("api.py", "initialize")
            forbidden = ["db_session", "create_tables", "execute\\("]
            found_forbidden = [p for p in forbidden if p in phase1_body]
            
            if found_forbidden:
                results["Two-Phase Init Phase 1"] = {"status": "❌", "message": f"DB operations in Phase 1: {found_forbidden}"}
            else:
                results["Two-Phase Init Phase 1"] = {"status": "✅", "message": "Valid Phase 1 implementation"}
        except AssertionError:
            results["Two-Phase Init Phase 1"] = {"status": "❌", "message": "Missing initialize(app_context) function"}
        
        # Two-Phase Initialization Phase 2
        try:
            assert checker.check_pattern_in_file("api.py", r"app_context\.register_module_setup_hook")
            assert checker.check_pattern_in_file("api.py", r"async\s+def\s+setup_module\s*\(\s*app_context\s*\):")
            results["Two-Phase Init Phase 2"] = {"status": "✅", "message": "Valid Phase 2 implementation"}
        except AssertionError:
            missing = []
            if not checker.check_pattern_in_file("api.py", r"app_context\.register_module_setup_hook"):
                missing.append("setup hook registration")
            if not checker.check_pattern_in_file("api.py", r"async\s+def\s+setup_module"):
                missing.append("setup_module function")
            results["Two-Phase Init Phase 2"] = {"status": "❌", "message": f"Missing: {', '.join(missing)}"}
        
        # Service Registration
        try:
            assert checker.check_pattern_in_file("api.py", r"app_context\.register_service")
            assert checker.check_pattern_in_file("api.py", r"app_context\.register_shutdown_handler")
            results["Service Registration"] = {"status": "✅", "message": "Service and shutdown handlers registered"}
        except AssertionError:
            missing = []
            if not checker.check_pattern_in_file("api.py", r"app_context\.register_service"):
                missing.append("service registration")
            if not checker.check_pattern_in_file("api.py", r"app_context\.register_shutdown_handler"):
                missing.append("shutdown handler")
            results["Service Registration"] = {"status": "❌", "message": f"Missing: {', '.join(missing)}"}
        
        return results
    
    def _check_api_standards(self, checker: ComplianceChecker) -> Dict[str, Dict]:
        """Check API implementation standards."""
        results = {}
        
        # API Schema Validation
        if checker.check_file_exists("api_schemas.py"):
            if checker.check_pattern_in_file("api_schemas.py", r"from pydantic import.*BaseModel"):
                if checker.check_pattern_in_file("api.py", r"response_model\s*="):
                    results["API Schema Validation"] = {"status": "✅", "message": "Pydantic schemas with response models"}
                else:
                    results["API Schema Validation"] = {"status": "⚠️", "message": "Schemas exist but no response_model usage"}
            else:
                results["API Schema Validation"] = {"status": "❌", "message": "api_schemas.py missing Pydantic imports"}
        else:
            results["API Schema Validation"] = {"status": "❌", "message": "Missing api_schemas.py"}
        
        return results
    
    def _has_api_functionality(self, checker: ComplianceChecker) -> bool:
        """Check if module implements API functionality."""
        api_content = checker.get_file_content("api.py")
        return "from fastapi import" in api_content or "APIRouter" in api_content
    
    def _display_results(self, results: Dict[str, Dict]):
        """Display compliance results in a nice format."""
        print("\n📊 Compliance Status:")
        print("-" * 40)
        
        total_checks = len(results)
        passed_checks = sum(1 for r in results.values() if r["status"] == "✅")
        
        for standard, result in results.items():
            status = result["status"]
            message = result["message"]
            print(f"{status} {standard}: {message}")
        
        print("-" * 40)
        print(f"📈 Score: {passed_checks}/{total_checks} ({passed_checks/total_checks*100:.0f}%)")
        
        if passed_checks == total_checks:
            print("🎉 All compliance checks passed!")
        elif passed_checks > total_checks * 0.7:
            print("👍 Good progress, few issues remaining")
        else:
            print("🔧 Needs work - focus on failed checks")
    
    def _run_tests(self):
        """Run pytest tests for the module."""
        print(f"\n🧪 Running tests for {self.module['name']}...")
        
        try:
            # Run pytest on compliance tests
            cmd = [
                sys.executable, "-m", "pytest", 
                f"tools/pytest_compliance.py::test_module_compliance[{self.module['id']}]",
                "-v", "--tb=short"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            
            if result.returncode == 0:
                print("✅ All tests passed!")
            else:
                print("❌ Some tests failed:")
                print(result.stdout)
                
        except Exception as e:
            print(f"💥 Error running tests: {e}")

def simple_watch_loop(module_info: Dict, run_tests: bool = False):
    """Simple file watching without watchdog dependency."""
    print("⚠️  Watchdog not available, using simple polling")
    print("Install with: pip install watchdog")
    print()
    
    watcher = ModuleWatcher(module_info, run_tests)
    module_path = Path(module_info['path'])
    
    # Track file modification times
    file_times = {}
    
    def get_file_times():
        times = {}
        for pattern in ['*.py', 'manifest.json']:
            for file_path in module_path.glob(pattern):
                if file_path.is_file():
                    times[file_path] = file_path.stat().st_mtime
        return times
    
    file_times = get_file_times()
    print("🔄 Polling for file changes (Ctrl+C to stop)...")
    
    try:
        while True:
            time.sleep(2)  # Poll every 2 seconds
            
            current_times = get_file_times()
            
            for file_path, mtime in current_times.items():
                if file_path not in file_times or file_times[file_path] != mtime:
                    print(f"\n🔄 File changed: {file_path.name} - Re-validating...")
                    watcher.check_compliance()
                    break
            
            file_times = current_times
            
    except KeyboardInterrupt:
        print("\n👋 Stopped watching")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Watch module for changes and provide real-time compliance feedback")
    parser.add_argument("--module", "-m", required=True, help="Module name to watch")
    parser.add_argument("--test", "-t", action="store_true", help="Also run pytest tests on changes")
    
    args = parser.parse_args()
    
    # Find the module
    modules = discover_modules()
    target_module = None
    
    for module in modules:
        if module['name'] == args.module or module['id'].endswith(f".{args.module}"):
            target_module = module
            break
    
    if not target_module:
        print(f"❌ Module '{args.module}' not found")
        print("\nAvailable modules:")
        for module in modules:
            print(f"  - {module['name']} ({module['id']})")
        sys.exit(1)
    
    print(f"🎯 Target module: {target_module['id']}")
    print(f"📁 Path: {target_module['path']}")
    print(f"🧪 Run tests: {'Yes' if args.test else 'No'}")
    print()
    
    if WATCHDOG_AVAILABLE:
        # Use watchdog for real-time watching
        event_handler = ModuleWatcher(target_module, args.test)
        observer = Observer()
        observer.schedule(event_handler, str(target_module['path']), recursive=True)
        observer.start()
        
        try:
            print("🔄 Watching for file changes (Ctrl+C to stop)...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Stopped watching")
            observer.stop()
        observer.join()
    else:
        # Fallback to simple polling
        simple_watch_loop(target_module, args.test)

if __name__ == "__main__":
    main()