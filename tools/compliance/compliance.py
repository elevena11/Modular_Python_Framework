"""
tools/compliance/compliance.py
Updated: March 17, 2025
Fixed import statements to match renamed functions
"""

#!/usr/bin/env python

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import core modules
sys.path.append(str(Path(__file__).parent))

from core.cli import (
    init_modules,
    validate_module,
    validate_all_modules,
    validate_verbose,
    validate_claims,
    generate_report,
    debug_standards
)

def main():
    """Main entry point for the compliance tool."""
    parser = argparse.ArgumentParser(description="Module compliance validation tool")
    
    # Command groups
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--init', action='store_true', help='Initialize compliance files for modules that don\'t have them (never overwrites)')
    group.add_argument('--validate', metavar='MODULE_ID', help='Validate and update compliance file for a specific module')
    group.add_argument('--validate-all', action='store_true', help='Validate and update compliance files for all modules')
    group.add_argument('--validate-verbose', metavar='MODULE_ID', help='Validate with detailed console output')
    group.add_argument('--validate-claims', metavar='MODULE_ID', help='Validate compliance claims without updating')
    group.add_argument('--report', action='store_true', help='Generate framework compliance report')
    group.add_argument('--tool-debug', metavar='MODULE_ID', nargs='?', const=None, help='Debug standards discovery and validation')
    
    # Additional options
    parser.add_argument('--comprehensive', action='store_true', help='Perform comprehensive scan of all Python files in module')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--output', '-o', metavar='FILE', help='Output file for report (default: compliance_report.md)')
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.validate_all and args.comprehensive:
        parser.error("--comprehensive cannot be used with --validate-all. Use --validate MODULE_ID --comprehensive for individual module analysis.")
    
    # Dispatch to appropriate handler
    if args.init:
        init_modules(verbose=args.verbose)
    elif args.validate:
        validate_module(args.validate, verbose=args.verbose, comprehensive=args.comprehensive)
    elif args.validate_all:
        validate_all_modules(verbose=args.verbose, comprehensive=args.comprehensive)
    elif args.validate_verbose:
        validate_verbose(args.validate_verbose, comprehensive=args.comprehensive)
    elif args.validate_claims:
        validate_claims(args.validate_claims, verbose=args.verbose, comprehensive=args.comprehensive)
    elif args.report:
        generate_report(output_file=args.output, verbose=args.verbose)
    elif args.tool_debug is not None or args.tool_debug == None:  # Handle both --tool-debug and --tool-debug MODULE_ID
        debug_standards(module_id=args.tool_debug, verbose=True)  # Always verbose for debug

if __name__ == "__main__":
    main()
