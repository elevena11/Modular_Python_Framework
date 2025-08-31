#!/usr/bin/env python3
"""
install_dependencies.py - Framework Dependency Installer

Installs framework dependencies in a clear, transparent manner:
1. Core framework dependencies (requirements.txt)
2. Active module dependencies (modules/*/requirements.txt)
3. Shows exactly what's being installed and why

Usage:
    python install_dependencies.py                # Install all dependencies
    python install_dependencies.py --dry-run     # Show what would be installed
    python install_dependencies.py --skip-modules # Only core framework
    python install_dependencies.py --verbose     # Show detailed pip output
"""

import os
import subprocess
import sys
import argparse
from pathlib import Path

def run_pip_install(requirements_file, verbose=False):
    """Run pip install with optional verbose output."""
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
    
    if verbose:
        result = subprocess.run(cmd, check=True)
    else:
        # Capture output to keep it clean unless there's an error
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
    return result

def find_module_requirements():
    """Find all module requirements.txt files, excluding disabled modules."""
    module_requirements = []
    
    for req_file in Path("modules").glob("*/*/requirements.txt"):
        module_dir = req_file.parent
        module_path = str(req_file.parent.relative_to("modules"))
        
        # Skip if module is disabled
        if (module_dir / ".disabled").exists():
            print(f"  - Skipping {module_path}/requirements.txt (module disabled)")
            continue
            
        module_requirements.append((req_file, module_path))
        print(f"  - Found: {module_path}/requirements.txt")
    
    return module_requirements

def main():
    parser = argparse.ArgumentParser(
        description="Install framework and module dependencies transparently"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be installed without installing"
    )
    parser.add_argument(
        "--skip-modules", 
        action="store_true",
        help="Only install core framework dependencies"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show detailed pip installation output"
    )
    
    args = parser.parse_args()
    
    print("Framework Dependency Installer")
    print("=" * 50)
    
    if args.dry_run:
        print("DRY RUN MODE - No packages will be installed")
        print()
    
    # 1. Install core framework dependencies
    print("1. Installing core framework dependencies...")
    core_requirements = Path("requirements.txt")
    
    if core_requirements.exists():
        if args.dry_run:
            print(f"   Would install: {core_requirements}")
            # Show what's in the file
            with open(core_requirements, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        print(f"     - {line}")
        else:
            try:
                run_pip_install(core_requirements, args.verbose)
                print("   ✓ Core framework dependencies installed")
            except subprocess.CalledProcessError as e:
                print(f"   ✗ Failed to install core dependencies: {e}")
                return 1
    else:
        print("   ⚠ No requirements.txt found in root directory")
    
    # 2. Skip modules if requested
    if args.skip_modules:
        print("\n2. Skipping module dependencies (--skip-modules)")
        print("\n✓ Core framework dependencies complete!")
        return 0
    
    # 3. Find and install module dependencies
    print("\n2. Scanning for module dependencies...")
    
    if not Path("modules").exists():
        print("   ⚠ No modules directory found")
        print("\n✓ Installation complete!")
        return 0
    
    module_requirements = find_module_requirements()
    
    # 4. Install each module's requirements
    if module_requirements:
        print(f"\n3. Installing dependencies for {len(module_requirements)} active modules...")
        
        for req_file, module_path in module_requirements:
            print(f"   Installing dependencies for: {module_path}")
            
            if args.dry_run:
                print(f"     Would install: {req_file}")
                # Show what's in the file
                try:
                    with open(req_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                print(f"       - {line}")
                except Exception as e:
                    print(f"     ⚠ Could not read {req_file}: {e}")
            else:
                try:
                    run_pip_install(req_file, args.verbose)
                    print(f"     ✓ {module_path} dependencies installed")
                except subprocess.CalledProcessError as e:
                    print(f"     ✗ Failed to install {module_path} dependencies: {e}")
                    print(f"       You may need to install these manually: {req_file}")
                    # Continue with other modules
    else:
        print("\n3. No active module dependencies found")
    
    if args.dry_run:
        print(f"\n✓ Dry run complete - no packages were installed")
    else:
        print(f"\n✓ All dependencies installed successfully!")
        print("   If you encounter import errors, try running this script again.")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠ Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)