"""
tools/compliance/core/cli.py
Updated: March 17, 2025
Implemented simplified CLI commands and error-driven knowledge system
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from .scanner import StandardsScanner, ModuleScanner
from .validator import ComplianceValidator
from .reporter import ComplianceReporter
from .template import TemplateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("compliance")

def init_modules(verbose: bool = False) -> bool:
    """
    Initialize compliance files for all modules that don't have them.
    Never overwrites existing files.
    
    Args:
        verbose: Whether to enable verbose output
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        # Also set all subloggers to DEBUG
        for name in ["compliance.scanner", "compliance.validator", "compliance.reporter", "compliance.template"]:
            logging.getLogger(name).setLevel(logging.DEBUG)
        
    logger.info("Initializing compliance files for all modules")
    
    # Scan for modules
    module_scanner = ModuleScanner()
    modules = module_scanner.discover_modules()
    
    if not modules:
        logger.error("No modules found")
        return False
    
    # Get template manager
    template_manager = TemplateManager()
    
    # Initialize compliance files for modules that don't have them
    initialized_count = 0
    skipped_count = 0
    for module in modules:
        module_id = module["id"]
        module_path = module["path"]
        compliance_path = os.path.join(module_path, "compliance.md")
        
        # Double-check file existence to be extra safe
        if os.path.exists(compliance_path) and os.path.isfile(compliance_path):
            logger.info(f"Skipping module {module_id}: compliance file already exists")
            skipped_count += 1
            continue
        
        # Create compliance file from template
        if template_manager.create_compliance_file(module):
            initialized_count += 1
            logger.info(f"Created compliance file for {module_id}")
        else:
            logger.error(f"Failed to create compliance file for {module_id}")
    
    logger.info(f"Initialized {initialized_count} compliance files, skipped {skipped_count} existing files")
    return True

def validate_module(module_id: str, verbose: bool = False, comprehensive: bool = False) -> bool:
    """
    Validate and update the compliance file for a specific module.
    
    Args:
        module_id: ID of the module to validate
        verbose: Whether to enable verbose output
        comprehensive: Whether to perform comprehensive scan of all files
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        # Also set all subloggers to DEBUG
        for name in ["compliance.scanner", "compliance.validator", "compliance.reporter", "compliance.template"]:
            logging.getLogger(name).setLevel(logging.DEBUG)
        
    logger.info(f"Validating module {module_id}")
    
    # Find the module
    module_scanner = ModuleScanner()
    module = module_scanner.find_module(module_id)
    
    if not module:
        logger.error(f"Module {module_id} not found")
        return False
    
    # Scan for standards
    standards_scanner = StandardsScanner()
    standards = standards_scanner.discover_standards()
    
    if not standards:
        logger.error("No standards found")
        return False
    
    # Validate module against standards
    validator = ComplianceValidator(standards)
    compliance_results = validator.validate_module(module, comprehensive=comprehensive)
    
    # Check if compliance file exists
    compliance_path = os.path.join(module["path"], "compliance.md")
    if not os.path.exists(compliance_path):
        # Create new compliance file
        template_manager = TemplateManager()
        if not template_manager.create_compliance_file(module):
            logger.error(f"Failed to create compliance file for {module_id}")
            return False
    
    # Update compliance file with results
    reporter = ComplianceReporter()
    if comprehensive:
        updated = reporter.update_comprehensive_compliance_file(module, compliance_results, standards)
    else:
        updated = reporter.update_compliance_file(module, compliance_results, standards)
    
    # Add reminder about error_handler imports if module_dependency was checked
    if "module_dependency" in compliance_results:
        logger.info("NOTE: Direct imports from modules.core.error_handler are allowed and exempt from module dependency violations")
    
    if updated:
        logger.info(f"Updated compliance file for {module_id}")
        return True
    else:
        logger.error(f"Failed to update compliance file for {module_id}")
        return False

def validate_all_modules(verbose: bool = False, comprehensive: bool = False) -> bool:
    """
    Validate and update compliance files for all modules.
    
    Args:
        verbose: Whether to enable verbose output
        comprehensive: Whether to perform comprehensive scan of all files
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        # Also set all subloggers to DEBUG
        for name in ["compliance.scanner", "compliance.validator", "compliance.reporter", "compliance.template"]:
            logging.getLogger(name).setLevel(logging.DEBUG)
        
    logger.info("Validating all modules")
    
    # Scan for modules
    module_scanner = ModuleScanner()
    modules = module_scanner.discover_modules()
    
    if not modules:
        logger.error("No modules found")
        return False
    
    # Scan for standards
    standards_scanner = StandardsScanner()
    standards = standards_scanner.discover_standards()
    
    if not standards:
        logger.error("No standards found")
        return False
    
    # Display all discovered standards
    logger.info(f"Discovered {len(standards)} standards:")
    for standard_id, standard in standards.items():
        logger.info(f"  - {standard_id} ({standard.get('name', 'No name')})")
    
    # Process each module
    success_count = 0
    failure_count = 0
    
    for module in modules:
        module_id = module["id"]
        logger.info(f"Validating module {module_id}")
        
        try:
            # Validate module against standards
            validator = ComplianceValidator(standards)
            compliance_results = validator.validate_module(module, comprehensive=comprehensive)
            
            # Check if compliance file exists
            compliance_path = os.path.join(module["path"], "compliance.md")
            if not os.path.exists(compliance_path):
                # Create new compliance file
                template_manager = TemplateManager()
                if not template_manager.create_compliance_file(module):
                    logger.error(f"Failed to create compliance file for {module_id}")
                    failure_count += 1
                    continue
            
            # Update compliance file with results
            reporter = ComplianceReporter()
            if comprehensive:
                updated = reporter.update_comprehensive_compliance_file(module, compliance_results, standards)
            else:
                updated = reporter.update_compliance_file(module, compliance_results, standards)
            
            if updated:
                logger.info(f"Updated compliance file for {module_id}")
                success_count += 1
            else:
                logger.error(f"Failed to update compliance file for {module_id}")
                failure_count += 1
                
        except Exception as e:
            logger.error(f"Error processing module {module_id}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            failure_count += 1
    
    logger.info(f"Completed validating {len(modules)} modules")
    logger.info(f"Successfully updated {success_count} modules")
    
    if failure_count > 0:
        logger.warning(f"Failed to update {failure_count} modules")
    
    return failure_count == 0

def validate_claims(module_id: str, verbose: bool = False, comprehensive: bool = False) -> bool:
    """
    Validate compliance claims in a module's compliance file against actual code.
    Doesn't update the file.
    
    Args:
        module_id: ID of the module to validate
        verbose: Whether to enable verbose output
        comprehensive: Whether to perform comprehensive scan of all files
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        # Also set all subloggers to DEBUG
        for name in ["compliance.scanner", "compliance.validator", "compliance.reporter", "compliance.template"]:
            logging.getLogger(name).setLevel(logging.DEBUG)
        
    logger.info(f"Validating compliance claims for module {module_id}")
    
    # Find the module
    module_scanner = ModuleScanner()
    module = module_scanner.find_module(module_id)
    
    if not module:
        logger.error(f"Module {module_id} not found")
        return False
    
    # Scan for standards
    standards_scanner = StandardsScanner()
    standards = standards_scanner.discover_standards()
    
    if not standards:
        logger.error("No standards found")
        return False
    
    # Get current compliance status from file
    compliance_path = os.path.join(module["path"], "compliance.md")
    if not os.path.exists(compliance_path):
        logger.error(f"No compliance file found for {module_id}")
        return False
    
    reporter = ComplianceReporter()
    parsed_data = reporter.parse_compliance_file(compliance_path)
    
    # Validate claims against code
    validator = ComplianceValidator(standards)
    validation_results = validator.validate_claims(module, parsed_data["claims"])
    
    # Display results
    print(f"Compliance validation results for {module_id}:")
    print("=" * 50)
    
    valid_count = 0
    invalid_count = 0
    
    for standard_id, result in validation_results.items():
        status = result["valid"]
        claim = result.get("claim", "Unknown")
        
        if status:
            print(f"[PASS] {standard_id}: Valid ({claim})")
            valid_count += 1
        else:
            print(f"[FAIL] {standard_id}: Invalid - {result['reason']} ({claim})")
            invalid_count += 1
            
            # Display details if any
            if "details" in result and result["details"]:
                for detail in result["details"]:
                    print(f"      - {detail}")
    
    print("=" * 50)
    print(f"Total: {valid_count + invalid_count} standards checked")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {invalid_count}")
    
    return True

def generate_report(output_file: Optional[str] = None, verbose: bool = False) -> bool:
    """
    Generate a framework-wide compliance report.
    
    Args:
        output_file: File to write report to (defaults to 'compliance_report.md')
        verbose: Whether to enable verbose output
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        # Also set all subloggers to DEBUG
        for name in ["compliance.scanner", "compliance.validator", "compliance.reporter", "compliance.template"]:
            logging.getLogger(name).setLevel(logging.DEBUG)
        
    # If no output file specified, use a default
    if output_file is None:
        output_file = "compliance_report.md"
        
    logger.info(f"Generating framework compliance report to {output_file}")
    
    # Scan for modules
    module_scanner = ModuleScanner()
    modules = module_scanner.discover_modules()
    
    if not modules:
        logger.error("No modules found")
        return False
    
    # Scan for standards
    standards_scanner = StandardsScanner()
    standards = standards_scanner.discover_standards()
    
    if not standards:
        logger.error("No standards found")
        return False
    
    # Log all discovered standards
    logger.info(f"Discovered {len(standards)} standards:")
    for standard_id, standard in standards.items():
        logger.info(f"  - {standard_id} ({standard.get('name', 'No name')})")
    
    # Validate all modules
    validator = ComplianceValidator(standards)
    compliance_data = {}
    
    logger.info(f"Analyzing {len(modules)} modules against {len(standards)} standards...")
    
    for module in modules:
        module_id = module["id"]
        logger.debug(f"Validating module {module_id}")
        try:
            compliance_data[module_id] = validator.validate_module(module)
        except Exception as e:
            logger.error(f"Error validating module {module_id}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            compliance_data[module_id] = {}
    
    # Generate report
    reporter = ComplianceReporter()
    report = reporter.generate_report(modules, standards, compliance_data)
    
    # Output report to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Report written to {output_file}")
        print(f"\nCompliance report generated successfully!")
        print(f"Report saved to: {os.path.abspath(output_file)}")
        return True
    except Exception as e:
        logger.error(f"Failed to write report to {output_file}: {str(e)}")
        # Fall back to console output
        print("\nFailed to write to file. Showing report on console:\n")
        print(report)
        return False

def debug_standards(module_id: Optional[str] = None, verbose: bool = True) -> bool:
    """
    Debug standards discovery and validation.
    
    Args:
        module_id: Optional ID of a specific module to debug
        verbose: Whether to enable verbose output
        
    Returns:
        True if successful, False otherwise
    """
    # Always set to DEBUG for this command
    logger.setLevel(logging.DEBUG)
    for name in ["compliance.scanner", "compliance.validator", "compliance.reporter", "compliance.template"]:
        logging.getLogger(name).setLevel(logging.DEBUG)
    
    # Print header
    print("=" * 60)
    print("COMPLIANCE TOOL DEBUG INFORMATION".center(60))
    print("=" * 60)
    
    # Scan for standards
    print("\n1. STANDARDS DISCOVERY\n" + "-" * 40)
    standards_scanner = StandardsScanner()
    standards = standards_scanner.discover_standards()
    
    if not standards:
        print("No standards found!")
        return False
    
    # Print detailed information about each standard
    print(f"\nFound {len(standards)} standards:")
    for standard_id, standard in standards.items():
        print(f"\n  Standard: {standard_id}")
        print(f"    Name: {standard.get('name', 'No name')}")
        print(f"    Version: {standard.get('version', 'No version')}")
        print(f"    Owner: {standard.get('owner_module', 'No owner')}")
        print(f"    File: {standard.get('file_path', 'Unknown file')}")
        
        # Print validation configuration
        if "validation" in standard:
            validation = standard["validation"]
            print("    Validation:")
            
            # File targets
            if "file_targets" in validation:
                print(f"      File targets:")
                for pattern_name, target_files in validation["file_targets"].items():
                    print(f"        {pattern_name}: {', '.join(target_files)}")
            
            # Match requirements
            if "match_requirements" in validation:
                print(f"      Match requirements:")
                for pattern_name, requirement in validation["match_requirements"].items():
                    print(f"        {pattern_name}: {requirement}")
            
            # Patterns
            if "patterns" in validation:
                print(f"      Patterns:")
                for pattern_name, pattern in validation["patterns"].items():
                    print(f"        {pattern_name}: {pattern}")
            
            # Anti-patterns
            if "anti_patterns" in validation:
                print(f"      Anti-patterns:")
                if isinstance(validation["anti_patterns"], list):
                    for i, pattern in enumerate(validation["anti_patterns"]):
                        print(f"        Pattern {i}: {pattern}")
                else:
                    for name, pattern in validation["anti_patterns"].items():
                        print(f"        {name}: {pattern}")
            
            # Regex validation
            if "regex" in validation:
                print(f"      Regex: {validation['regex']}")
                if "explanation" in validation:
                    print(f"      Explanation: {validation['explanation']}")
        else:
            print("    No validation configuration found!")
    
    # If module_id specified, test validation on it
    if module_id:
        print("\n2. MODULE VALIDATION\n" + "-" * 40)
        
        # Find the module
        module_scanner = ModuleScanner()
        module = module_scanner.find_module(module_id)
        
        if not module:
            print(f"Module {module_id} not found!")
            return False
        
        # Validate module against all standards
        validator = ComplianceValidator(standards)
        compliance_results = validator.validate_module(module)
        
        # Display results
        print(f"\nValidation results for {module_id}:")
        for standard_id, result in compliance_results.items():
            compliance_level = result["compliance_level"]
            if compliance_level == "Yes":
                print(f"\n  [PASS] {standard_id}: {compliance_level}")
            else:  # No
                print(f"\n  [FAIL] {standard_id}: {compliance_level}")
            
            # Print details if any
            if "details" in result and result["details"]:
                for detail in result["details"]:
                    print(f"    - {detail}")
    
    print("\nDebug information complete.")
    return True

def validate_verbose(module_id: str, comprehensive: bool = False) -> bool:
    """
    Validate a module with verbose console output.
    
    Args:
        module_id: ID of the module to validate
        comprehensive: Whether to perform comprehensive scan of all files
        
    Returns:
        True if successful, False otherwise
    """
    # Configure logging to output to console as well
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add console handler to all loggers
    loggers = [
        logging.getLogger("compliance"),
        logging.getLogger("compliance.scanner"),
        logging.getLogger("compliance.validator"),
        logging.getLogger("compliance.reporter"),
        logging.getLogger("compliance.template")
    ]
    
    for logger in loggers:
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)
    
    try:
        result = validate_module(module_id, verbose=True, comprehensive=comprehensive)
        
        # Remove console handler after validation
        for logger in loggers:
            logger.removeHandler(console_handler)
            
        return result
    except Exception as e:
        # Make sure to remove console handler on error
        for logger in loggers:
            logger.removeHandler(console_handler)
        raise
"""
tools/compliance/compliance.py
Updated: March 17, 2025
Implemented simplified CLI commands based on the compliance tool redesign
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
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--output', '-o', metavar='FILE', help='Output file for report (default: compliance_report.md)')
    
    args = parser.parse_args()
    
    # Dispatch to appropriate handler
    if args.init:
        init_modules(verbose=args.verbose)
    elif args.validate:
        validate_module(args.validate, verbose=args.verbose)
    elif args.validate_all:
        validate_all_modules(verbose=args.verbose)
    elif args.validate_verbose:
        validate_verbose(args.validate_verbose)
    elif args.validate_claims:
        validate_claims(args.validate_claims, verbose=args.verbose)
    elif args.report:
        generate_report(output_file=args.output, verbose=args.verbose)
    elif args.tool_debug is not None or args.tool_debug == None:  # Handle both --tool-debug and --tool-debug MODULE_ID
        debug_standards(module_id=args.tool_debug, verbose=True)  # Always verbose for debug

if __name__ == "__main__":
    main()
