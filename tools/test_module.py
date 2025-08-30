#!/usr/bin/env python3
"""
tools/test_module.py
Simple test runner for module compliance without pytest dependency issues.

Usage:
    python tools/test_module.py veritas_knowledge_graph
    python tools/test_module.py --watch veritas_knowledge_graph
"""

import sys
import argparse
from pytest_compliance import discover_modules, test_specific_module

def main():
    """Simple test runner."""
    parser = argparse.ArgumentParser(description="Test module compliance")
    parser.add_argument("module", help="Module name to test")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch for changes")
    
    args = parser.parse_args()
    
    if args.watch:
        # Import and run watch mode
        try:
            from dev_watch import main as watch_main
            sys.argv = ["dev_watch.py", "--module", args.module]
            watch_main()
        except ImportError:
            print("❌ Watch mode requires dev_watch.py")
            sys.exit(1)
    else:
        # Run compliance test
        success = test_specific_module(args.module)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()