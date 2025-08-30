#!/usr/bin/env python3
"""
Test script for the framework update system.
This verifies the update system can connect to GitHub and parse version information.
"""

import sys
from pathlib import Path

# Add project root to path so we can import update_core
sys.path.insert(0, str(Path(__file__).parent))

from update_core import FrameworkUpdater

def test_version_tracking():
    """Test version tracking functionality."""
    print("🧪 Testing version tracking...")
    
    updater = FrameworkUpdater()
    
    # Test getting current version
    current = updater.get_current_version()
    print(f"   Current version: {current['version']}")
    
    # Test version comparison
    comparison = updater.compare_versions("1.0.0", "1.1.0")
    assert comparison == -1, "Version comparison failed"
    
    comparison = updater.compare_versions("1.1.0", "1.0.0")
    assert comparison == 1, "Version comparison failed"
    
    comparison = updater.compare_versions("1.0.0", "1.0.0")
    assert comparison == 0, "Version comparison failed"
    
    print("   ✅ Version tracking works")

def test_github_connection():
    """Test GitHub API connection."""
    print("🧪 Testing GitHub connection...")
    
    updater = FrameworkUpdater()
    
    # Test remote version check
    remote_info = updater.check_remote_version()
    
    if remote_info:
        print(f"   Remote version: {remote_info['version']}")
        print(f"   Release name: {remote_info['name']}")
        print("   ✅ GitHub connection works")
        return True
    else:
        print("   ❌ GitHub connection failed")
        return False

def test_backup_functionality():
    """Test backup creation (dry run)."""
    print("🧪 Testing backup functionality...")
    
    updater = FrameworkUpdater()
    
    # Test backup directory creation
    updater.backup_dir.mkdir(parents=True, exist_ok=True)
    
    if updater.backup_dir.exists():
        print(f"   Backup directory: {updater.backup_dir}")
        print("   ✅ Backup functionality ready")
        return True
    else:
        print("   ❌ Backup directory creation failed")
        return False

def main():
    """Run all update system tests."""
    print("🔧 Framework Update System Tests")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 3
    
    try:
        test_version_tracking()
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Version tracking test failed: {e}")
    
    if test_github_connection():
        tests_passed += 1
    
    if test_backup_functionality():
        tests_passed += 1
    
    print("\n" + "=" * 40)
    print(f"📊 Tests Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Update system is ready.")
        return True
    else:
        print("❌ Some tests failed. Check configuration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)