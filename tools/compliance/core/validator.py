"""
tools/compliance/core/validator.py
Updated: March 21, 2025
Enhanced with standard name-to-ID mapping for validate_claims functionality
"""

import os
import re
import logging
import glob
from typing import Dict, Any, List, Optional, Set, Tuple
from .scanner import StandardsScanner

logger = logging.getLogger("compliance.validator")

class ComplianceValidator:
    """Validator for checking module compliance with standards."""
    
    def __init__(self, standards: Dict[str, Dict[str, Any]]):
        """
        Initialize the compliance validator.
        
        Args:
            standards: Dictionary of standards with ID as key
        """
        self.standards = standards
        
        # Build a mapping between display names and standard IDs
        self.name_to_id_map = {}
        for standard_id, standard in standards.items():
            # Map standard name to ID (case insensitive)
            standard_name = standard.get("name", standard_id)
            self.name_to_id_map[standard_name.lower()] = standard_id
            # Also map ID to itself for direct matches
            self.name_to_id_map[standard_id.lower()] = standard_id
    
    def validate_module(self, module: Dict[str, Any], comprehensive: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Validate a module against all standards.
        
        Args:
            module: Module information dictionary
            comprehensive: Whether to scan all files recursively
            
        Returns:
            Dictionary of compliance results for each standard
        """
        module_id = module["id"]
        module_path = module["path"]
        
        logger.info(f"Validating module {module_id} against {len(self.standards)} standards")
        
        results = {}
        for standard_id, standard in self.standards.items():
            logger.debug(f"Validating {module_id} against standard {standard_id}")
            
            # Check if standard is applicable to this module
            if self._is_standard_applicable(standard, module):
                # Validate module against this standard
                result = self._validate_against_standard(module, standard, comprehensive=comprehensive)
                results[standard_id] = result
                
                # Log the result
                compliance_level = result["compliance_level"]
                if compliance_level == "Yes":
                    logger.info(f"  [PASS] {standard_id}: {compliance_level}")
                else:  # No
                    logger.info(f"  [FAIL] {standard_id}: {compliance_level}")
                
                # Log details if any
                for detail in result.get("details", []):
                    logger.debug(f"    - {detail}")
            else:
                logger.debug(f"  Skipping {standard_id}: Not applicable to {module_id}")
        
        return results
    
    def parse_compliance_file(self, compliance_path: str) -> Dict[str, Any]:
        """
        Parse a compliance file to extract compliance claims and exceptions.
        
        Args:
            compliance_path: Path to compliance file
            
        Returns:
            Dictionary with compliance claims and exceptions
        """
        result = {
            "claims": {},
            "exceptions": ""
        }
        
        try:
            with open(compliance_path, 'r') as f:
                content = f.read()
            
            # Extract standard compliance values
            for line in content.splitlines():
                # Match lines like "- Standard Name: Yes" or "- Standard Name: No"
                match = re.match(r'- (.+): (Yes|No)', line)
                if match:
                    standard_name = match.group(1).strip()
                    compliance_value = match.group(2).strip()
                    result["claims"][standard_name] = compliance_value
            
            # Extract exceptions section
            exceptions_match = re.search(r'## Exceptions\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
            if exceptions_match:
                result["exceptions"] = exceptions_match.group(1).strip()
            
        except Exception as e:
            logger.error(f"Error parsing compliance file {compliance_path}: {str(e)}")
        
        return result
    
    def validate_claims(self, module: Dict[str, Any], 
                      claims: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Validate compliance claims against code.
        
        Args:
            module: Module information dictionary
            claims: Dictionary of compliance claims (standard_name -> Yes/No)
            
        Returns:
            Dictionary of validation results for each claim
        """
        module_id = module["id"]
        logger.info(f"Validating compliance claims for module {module_id}")
        
        results = {}
        for standard_name, compliance in claims.items():
            # Try to map the standard name to a known standard ID
            standard_id = self._map_standard_name_to_id(standard_name)
            
            # Skip if standard doesn't exist
            if not standard_id:
                results[standard_name] = {
                    "valid": False,
                    "reason": "Standard not found in framework",
                    "claim": compliance,
                    "compliance_level": compliance
                }
                continue
            
            # Get standard definition
            standard = self.standards[standard_id]
            
            # If claimed as "No", always valid (no need to check code)
            if compliance.lower() == "no":
                results[standard_name] = {
                    "valid": True,
                    "reason": "Claim of non-compliance is always valid",
                    "claim": compliance,
                    "compliance_level": "No"
                }
                continue
            
            # If claimed as "Yes", validate against code
            if compliance.lower() == "yes":
                # Validate module against standard
                validation_result = self._validate_against_standard(module, standard)
                compliance_level = validation_result["compliance_level"]
                
                # Check if validation matches claim
                if compliance_level == "Yes":
                    results[standard_name] = {
                        "valid": True,
                        "reason": "Claim validated by code analysis",
                        "claim": compliance,
                        "compliance_level": "Yes"
                    }
                else:
                    results[standard_name] = {
                        "valid": False,
                        "reason": f"Claim of compliance not supported by code analysis (found: {compliance_level})",
                        "claim": compliance,
                        "compliance_level": "No",
                        "details": validation_result.get("details", [])
                    }
            
        return results
    
    def print_validation_results(self, module_id: str, results: Dict[str, Dict[str, Any]],
                               is_claim_validation: bool = False):
        """
        Print validation results in user-friendly format.
        
        Args:
            module_id: ID of the module
            results: Validation results
            is_claim_validation: Whether this is validating claims (not actual compliance)
        """
        print(f"Compliance validation results for {module_id}:")
        print("==================================================")
        
        # Check if module_dependency was tested (to show reminder)
        has_module_dependency = "module_dependency" in results
        
        # Track counts
        valid_count = 0
        invalid_count = 0
        
        for standard_name, result in sorted(results.items()):
            if is_claim_validation:
                # For claim validation, check if claim is valid
                is_valid = result.get("valid", False)
                status = "PASS" if is_valid else "FAIL"
                
                if is_valid:
                    valid_count += 1
                    print(f"[{status}] {standard_name}: Valid ({result.get('claim', 'Unknown')})")
                else:
                    invalid_count += 1
                    reason = result.get("reason", "Unknown reason")
                    print(f"[{status}] {standard_name}: {reason} ({result.get('claim', 'Unknown')})")
                    
                    # Print details if any
                    if "details" in result:
                        for detail in result["details"]:
                            print(f"  - {detail}")
            else:
                # For regular validation, check compliance level
                compliance_level = result.get("compliance_level", "No")
                
                if compliance_level == "Yes":
                    valid_count += 1
                    print(f"[PASS] {standard_name}: {compliance_level}")
                else:
                    invalid_count += 1
                    print(f"[FAIL] {standard_name}: {compliance_level}")
                    
                    # Print details if any
                    if "details" in result:
                        for detail in result["details"]:
                            print(f"  - {detail}")
        
        print("==================================================")
        print(f"Total: {valid_count + invalid_count} standards checked")
        
        if is_claim_validation:
            print(f"Valid: {valid_count}")
            print(f"Invalid: {invalid_count}")
        else:
            print(f"Compliant: {valid_count}")
            print(f"Non-compliant: {invalid_count}")
        
        # Add reminder about error_handler imports if module_dependency was checked
        if has_module_dependency and not is_claim_validation:
            print()
            print("NOTE: Direct imports from modules.core.error_handler are allowed")
            print("      and exempt from module dependency violations.")
    
    def _map_standard_name_to_id(self, standard_name: str) -> Optional[str]:
        """
        Map a standard name (or ID) to its standard ID.
        
        Args:
            standard_name: Name or ID of the standard
            
        Returns:
            Standard ID if found, None otherwise
        """
        # Try direct mapping (case insensitive)
        standard_key = standard_name.lower()
        if standard_key in self.name_to_id_map:
            return self.name_to_id_map[standard_key]
        
        # Try fuzzy matching for similar names
        for name, standard_id in self.name_to_id_map.items():
            # Check for significant overlaps in the names
            if (name in standard_key or standard_key in name or
                self._similarity_score(standard_key, name) > 0.7):
                return standard_id
        
        return None
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """
        Calculate a simple similarity score between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0 and 1
        """
        # Normalize strings
        str1 = str1.lower().replace(" ", "_").replace("-", "_")
        str2 = str2.lower().replace(" ", "_").replace("-", "_")
        
        # Get common words
        words1 = set(str1.split("_"))
        words2 = set(str2.split("_"))
        common_words = words1 & words2
        
        if not words1 or not words2:
            return 0
        
        # Score based on common words
        return len(common_words) / max(len(words1), len(words2))
    
   

    def _is_standard_applicable(self, standard: Dict[str, Any], module: Dict[str, Any]) -> bool:
        """
        Check if a standard is applicable to a module.
        
        Args:
            standard: Standard definition
            module: Module information dictionary
            
        Returns:
            True if applicable, False otherwise
        """
        # Check for module type exclusions
        if "applicable_to" in standard:
            applicable_to = standard["applicable_to"]
            module_type = module["type"]
            
            if isinstance(applicable_to, list) and module_type not in applicable_to:
                return False
        
        # Check if API-related standards should be skipped for modules without api_schemas.py
        api_related_standards = [
            "api_schema_validation", 
            "openapi_documentation"
        ]
        
        standard_id = standard.get("id", "")
        if standard_id in api_related_standards:
            # Check if module has api_schemas.py
            import os
            api_schemas_path = os.path.join(module["path"], "api_schemas.py")
            if not os.path.exists(api_schemas_path):
                logger.debug(f"  Skipping {standard_id}: Module has no api_schemas.py (no API endpoints)")
                return False
        
        # All standards are applicable by default
        return True
    
    def _validate_against_standard(self, module: Dict[str, Any], 
                                standard: Dict[str, Any], comprehensive: bool = False) -> Dict[str, Any]:
        """
        Validate a module against a specific standard.
        
        Args:
            module: Module information dictionary
            standard: Standard definition
            comprehensive: Whether to scan all files recursively
            
        Returns:
            Dictionary with validation results
        """
        standard_id = standard["id"]
        module_id = module["id"]
        module_path = module["path"]
        
        logger.debug(f"Validating module {module_id} against standard {standard_id}")
        
        # Initialize result variables
        compliance_level = "No"  # Default to No
        details = []  # List to store error details
        
        # Get validation rules from the standard definition
        if "validation" not in standard:
            details.append("No validation rules defined for this standard")
            logger.debug(f"  [UNKNOWN] No validation rules defined for standard {standard_id}")
            return {
                "standard_id": standard_id,
                "compliance_level": "No",
                "details": details
            }
                
        validation = standard["validation"]
        
        # REMOVED: manifest schema validation (obsolete pattern)
        
        # Special case: Check regex validation (for ASCII standard)
        if "regex" in validation:
            regex_result = self._validate_with_regex(module, standard, validation, comprehensive=comprehensive)
            return regex_result
        
        # Special case: Check two-mode validation (for layered error handling)
        if "standard_mode" in validation and "comprehensive_mode" in validation:
            mode_result = self._validate_with_modes(module, standard, validation, comprehensive=comprehensive)
            return mode_result
        
        # Get patterns to check
        patterns = validation.get("patterns", {})
        if not patterns:
            # Skip deprecated manifest-only validations
            if "manifest_schema" in validation and len(validation) == 1 and not details:
                return {
                    "standard_id": standard_id,
                    "compliance_level": "Yes",
                    "details": []
                }
            
            # Otherwise, if no patterns are defined, fail validation
            if not details:  # Only add this if no other details exist
                details.append("No patterns defined for validation")
                logger.debug(f"  [NO] No patterns defined for standard {standard_id}")
            
            return {
                "standard_id": standard_id,
                "compliance_level": "No",
                "details": details
            }
                
        # Get file targets for patterns
        file_targets = validation.get("file_targets", {})
        if not file_targets and patterns:
            details.append("No file targets defined for patterns")
            logger.debug(f"  [NO] No file targets defined for standard {standard_id}")
            return {
                "standard_id": standard_id,
                "compliance_level": "No",
                "details": details
            }
                
        # Get match requirements (defaults to "either")
        match_requirements = validation.get("match_requirements", {})
        
        # Check each pattern against its target files
        pattern_results = {}
        
        for pattern_name, pattern in patterns.items():
            # Skip if no file targets for this pattern
            if pattern_name not in file_targets:
                logger.debug(f"  [SKIP] No file targets for pattern '{pattern_name}'")
                continue
                    
            # Get target files for this pattern
            target_files = file_targets[pattern_name]
            
            # Determine match requirement for this pattern (default to "either")
            match_requirement = match_requirements.get(pattern_name, "either")
            
            # Validate pattern against target files
            pattern_result = self._validate_pattern(module_path, pattern_name, pattern, target_files, match_requirement, comprehensive=comprehensive)
            pattern_results[pattern_name] = pattern_result
            
            # If this pattern didn't match, add to details
            if not pattern_result["matches"]:
                for error in pattern_result["errors"]:
                    details.append(error)
        
        # Check for anti-patterns
        anti_patterns = validation.get("anti_patterns", [])
        exceptions = validation.get("exceptions", [])
        anti_pattern_results = {}
        
        if anti_patterns:
            # Check if we have a file target for anti-patterns
            anti_pattern_targets = file_targets.get("no_direct_imports", [])
            
            if not anti_pattern_targets:
                # If no specific target for anti-patterns, use all unique target files from patterns
                all_targets = set()
                for target_list in file_targets.values():
                    all_targets.update(target_list)
                anti_pattern_targets = list(all_targets)
                    
            # Check anti-patterns in target files
            anti_pattern_result = self._validate_anti_patterns(module_path, anti_patterns, anti_pattern_targets, exceptions)
            anti_pattern_results = anti_pattern_result.get("found_patterns", {})
            
            # If any anti-patterns found, add to details with line numbers
            for pattern_name, files_info in anti_pattern_results.items():
                for file_path, line_numbers in files_info.items():
                    lines_str = ", ".join(map(str, line_numbers))
                    details.append(f"Found anti-pattern '{pattern_name}' in {file_path} at line(s): {lines_str}")
        
        # Determine overall compliance
        if not details and all(result["matches"] for result in pattern_results.values()):
            compliance_level = "Yes"

        # Add note about exceptions if they were used
        if exceptions and compliance_level == "Yes":
            details.append("NOTE: error_handler imports are allowed as exceptions and were not flagged as violations")
                
        return {
            "standard_id": standard_id,
            "compliance_level": compliance_level,
            "details": details
        }
    
    def _validate_pattern(self, module_path: str, pattern_name: str, pattern: str, 
                         target_files: List[str], match_requirement: str, comprehensive: bool = False) -> Dict[str, Any]:
        """
        Validate a pattern against target files.
        
        Args:
            module_path: Path to module directory
            pattern_name: Name of the pattern being checked
            pattern: Regex pattern to check
            target_files: List of target files to check
            match_requirement: "all" or "either" - whether pattern must match all files or just one
            comprehensive: Whether to scan all files recursively
            
        Returns:
            Dictionary with validation results
        """
        # Special handling for custom patterns
        if pattern == "DEFAULT_SETTINGS_NESTED_CHECK":
            return self._validate_default_settings_flat_structure(module_path, target_files, match_requirement)
        elif pattern == "VALIDATION_TYPE_CHECK":
            return self._validate_validation_type_names(module_path, target_files, match_requirement)
        
        try:
            compiled_pattern = re.compile(pattern)
        except Exception as e:
            logger.error(f"Invalid pattern '{pattern_name}': {str(e)}")
            return {
                "matches": False,
                "errors": [f"Invalid pattern '{pattern_name}': {str(e)}"]
            }
            
        # Track missing files, matching files, and errors
        missing_files = []
        matching_files = []
        non_matching_files = []
        errors = []
        
        # For comprehensive scanning, expand target files to include all Python files
        if comprehensive and "*.py" in target_files:
            scanner = StandardsScanner()
            all_files = scanner.discover_module_files(module_path, comprehensive=True)
            # Convert absolute paths to relative paths like the original target files
            target_files = []
            for file_path in all_files:
                rel_path = os.path.relpath(file_path, module_path)
                target_files.append(rel_path)
        
        # Process each target file
        for target_file in target_files:
            # Check if this is a wildcard pattern
            if '*' in target_file:
                # Handle wildcard (only matches in specified directory level)
                wildcard_matches = self._find_files_with_wildcard(module_path, target_file)
                
                if not wildcard_matches:
                    # No files match this wildcard pattern
                    if match_requirement == "all":
                        errors.append(f"No files match wildcard pattern '{target_file}' for '{pattern_name}'")
                    continue
                    
                # Check each matching file
                for file_path in wildcard_matches:
                    rel_path = os.path.relpath(file_path, module_path)
                    
                    if not os.path.exists(file_path):
                        missing_files.append(rel_path)
                        continue
                        
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                            
                        if compiled_pattern.search(content):
                            matching_files.append(rel_path)
                        else:
                            non_matching_files.append(rel_path)
                    except Exception as e:
                        logger.error(f"Error checking pattern '{pattern_name}' in {file_path}: {str(e)}")
                        errors.append(f"Error checking '{pattern_name}' in {rel_path}: {str(e)}")
            else:
                # Handle exact file path
                file_path = os.path.join(module_path, target_file)
                rel_path = target_file  # Already relative
                
                if not os.path.exists(file_path):
                    missing_files.append(rel_path)
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        
                    if compiled_pattern.search(content):
                        matching_files.append(rel_path)
                    else:
                        non_matching_files.append(rel_path)
                except Exception as e:
                    logger.error(f"Error checking pattern '{pattern_name}' in {file_path}: {str(e)}")
                    errors.append(f"Error checking '{pattern_name}' in {rel_path}: {str(e)}")
        
        # Determine if pattern matches based on match requirement
        matches = False
        if match_requirement == "all":
            # Must match all target files - none can be missing or non-matching
            if not missing_files and not non_matching_files:
                matches = True
            else:
                # Report missing and non-matching files
                for file_path in missing_files:
                    errors.append(f"Missing required file: {file_path}")
                for file_path in non_matching_files:
                    errors.append(f"Missing pattern '{pattern_name}' in {file_path}")
        elif match_requirement == "none":
            # Must NOT match any target files - any matches should cause failure
            if not matching_files:
                matches = True  # Success if no matches found
            else:
                # Report files that matched when they shouldn't have
                for file_path in matching_files:
                    errors.append(f"Found unwanted pattern '{pattern_name}' in {file_path}")
        else:  # "either"
            # Must match at least one target file
            if matching_files:
                matches = True
            else:
                # Report that pattern wasn't found in any file
                if missing_files:
                    for file_path in missing_files:
                        errors.append(f"Missing required file: {file_path}")
                if non_matching_files:
                    for file_path in non_matching_files:
                        errors.append(f"Missing pattern '{pattern_name}' in {file_path}")
                if not missing_files and not non_matching_files:
                    errors.append(f"No target files found for pattern '{pattern_name}'")
        
        return {
            "matches": matches,
            "matching_files": matching_files,
            "missing_files": missing_files,
            "non_matching_files": non_matching_files,
            "errors": errors
        }
    
    def _find_files_with_wildcard(self, module_path: str, wildcard_pattern: str) -> List[str]:
        """
        Find files matching a wildcard pattern, limited to the specified directory level.
        
        Args:
            module_path: Base path to the module
            wildcard_pattern: Pattern with wildcards (e.g., "*.py" or "ui/*.py")
            
        Returns:
            List of matching file paths
        """
        # Check if this is a subdirectory pattern or root pattern
        if '/' in wildcard_pattern:
            # This is a subdirectory pattern (e.g., "ui/*.py")
            # Only check files in the specified subdirectory (not deeper)
            glob_pattern = os.path.join(module_path, wildcard_pattern)
            matching_files = glob.glob(glob_pattern)
        else:
            # This is a root pattern (e.g., "*.py")
            # Only check files in the module root directory
            glob_pattern = os.path.join(module_path, wildcard_pattern)
            matching_files = [f for f in glob.glob(glob_pattern) if os.path.dirname(f) == module_path]
            
        return matching_files
    
    def _find_anti_pattern_lines(self, content: str, pattern: re.Pattern) -> List[int]:
        """
        Find line numbers containing anti-pattern matches.
        
        Args:
            content: Content of the file
            pattern: Compiled regex pattern to match
            
        Returns:
            List of line numbers with anti-pattern matches
        """
        lines = content.splitlines()
        match_lines = []
        
        # First check line-by-line
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                match_lines.append(i)
        
        # If no matches found by line, check multiline patterns
        if not match_lines and pattern.search(content):
            # For multiline patterns, we need a different approach
            # Find the approximate line number by counting newlines
            match_obj = pattern.search(content)
            if match_obj:
                # Count newlines up to the match start position
                pos = match_obj.start()
                line_number = content[:pos].count('\n') + 1
                match_lines.append(line_number)
        
        return match_lines
    
    def _validate_anti_patterns(self, module_path: str, anti_patterns: List[str], 
                              target_files: List[str], exceptions: List[str] = None) -> Dict[str, Any]:
        """
        Check for anti-patterns in target files.
        
        Args:
            module_path: Path to module directory
            anti_patterns: List of anti-patterns to check
            target_files: List of files to check
            exceptions: List of exception patterns to ignore
            
        Returns:
            Dictionary with anti-pattern results
        """
        results = {
            "found_patterns": {}
        }
        
        # Compile anti-patterns
        compiled_patterns = {}
        for i, pattern in enumerate(anti_patterns):
            try:
                if isinstance(pattern, str):
                    compiled_patterns[f"anti_pattern_{i}"] = (pattern, re.compile(pattern))
            except Exception as e:
                logger.error(f"Invalid anti-pattern #{i}: {str(e)}")
        
        # Compile exception patterns
        compiled_exceptions = []
        if exceptions:
            for exception_pattern in exceptions:
                try:
                    compiled_exceptions.append(re.compile(exception_pattern))
                except Exception as e:
                    logger.error(f"Invalid exception pattern '{exception_pattern}': {str(e)}")
        
        # Check each target file for anti-patterns
        for target_file in target_files:
            # Handle wildcard patterns
            if '*' in target_file:
                matching_files = self._find_files_with_wildcard(module_path, target_file)
                
                for file_path in matching_files:
                    self._check_file_for_anti_patterns(file_path, module_path, compiled_patterns, results, compiled_exceptions)
            else:
                # Handle exact file path
                file_path = os.path.join(module_path, target_file)
                
                if os.path.exists(file_path):
                    self._check_file_for_anti_patterns(file_path, module_path, compiled_patterns, results, compiled_exceptions)
        
        return results
    
    def _check_file_for_anti_patterns(self, file_path: str, module_path: str, 
                                    compiled_patterns: Dict[str, tuple], results: Dict[str, Any], 
                                    compiled_exceptions: List = None):
        """
        Check a specific file for anti-patterns with line numbers.
        
        Args:
            file_path: Path to the file to check
            module_path: Base path to the module
            compiled_patterns: Dictionary of compiled anti-patterns
            results: Results dictionary to update
            compiled_exceptions: List of compiled exception patterns to ignore
        """
        rel_path = os.path.relpath(file_path, module_path)
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            
            # Check each anti-pattern
            for pattern_name, (raw_pattern, compiled_pattern) in compiled_patterns.items():
                # Find line numbers for this anti-pattern
                line_numbers = self._find_anti_pattern_lines(content, compiled_pattern)
                
                if line_numbers:
                    # Check if any exception patterns match and filter out those lines
                    filtered_line_numbers = []
                    
                    if compiled_exceptions:
                        lines = content.splitlines()
                        for line_num in line_numbers:
                            line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                            
                            # Check if this line matches any exception pattern
                            is_exception = False
                            for exception_pattern in compiled_exceptions:
                                if exception_pattern.search(line_content):
                                    is_exception = True
                                    logger.info(f"NOTE: Line {line_num} in {rel_path} matches allowed exception (error_handler import), skipping anti-pattern check")
                                    break
                            
                            if not is_exception:
                                filtered_line_numbers.append(line_num)
                    else:
                        filtered_line_numbers = line_numbers
                    
                    if filtered_line_numbers:
                        # Anti-pattern found (after filtering exceptions)
                        if pattern_name not in results["found_patterns"]:
                            results["found_patterns"][pattern_name] = {}
                        
                        # Store with line numbers
                        results["found_patterns"][pattern_name][rel_path] = filtered_line_numbers
                        logger.debug(f"Found anti-pattern '{pattern_name}' in {rel_path} at lines: {filtered_line_numbers}")
        except Exception as e:
            logger.error(f"Error checking anti-patterns in {file_path}: {str(e)}")
    
    def _get_files_to_scan(self, module_path: str, file_targets: Dict[str, List[str]], comprehensive: bool = False) -> List[str]:
        """
        Get list of files to scan based on mode and targets.
        
        Args:
            module_path: Path to module directory
            file_targets: File target patterns from standard
            comprehensive: Whether to scan all files recursively
            
        Returns:
            List of absolute file paths to scan
        """
        if comprehensive:
            # In comprehensive mode, scan ALL discovered files
            from .scanner import StandardsScanner
            scanner = StandardsScanner()
            all_files = scanner.discover_module_files(module_path, comprehensive=True)
            return all_files
        else:
            # Standard mode: use file_targets to filter
            files_to_scan = []
            for target_key, target_patterns in file_targets.items():
                for target_pattern in target_patterns:
                    if '*' in target_pattern:
                        matching_files = self._find_files_with_wildcard(module_path, target_pattern)
                        files_to_scan.extend(matching_files)
                    else:
                        file_path = os.path.join(module_path, target_pattern)
                        if os.path.exists(file_path):
                            files_to_scan.append(file_path)
            return files_to_scan

    def _validate_with_regex(self, module: Dict[str, Any], standard: Dict[str, Any], 
                          validation: Dict[str, Any], comprehensive: bool = False) -> Dict[str, Any]:
        """
        Validate a module using a regex pattern (special case for ASCII standard).
        
        Args:
            module: Module information dictionary
            standard: Standard definition
            validation: Validation rules from standard
            comprehensive: Whether to scan all files recursively
            
        Returns:
            Dictionary with validation results
        """
        standard_id = standard["id"]
        module_path = module["path"]
        
        # Initialize result variables
        compliance_level = "No"  # Default to No
        details = []  # List to store error details
        
        # Get regex pattern and file targets
        regex_pattern = validation["regex"]
        regex_explanation = validation.get("explanation", "does not match required pattern")
        file_targets = validation.get("file_targets", {})
        
        try:
            compiled_regex = re.compile(regex_pattern)
        except Exception as e:
            logger.error(f"Invalid regex pattern '{regex_pattern}': {str(e)}")
            details.append(f"Invalid regex pattern: {str(e)}")
            return {
                "standard_id": standard_id,
                "compliance_level": "No",
                "details": details
            }
        
        # Get files to scan using unified function
        files_to_scan = self._get_files_to_scan(module_path, file_targets, comprehensive)
        logger.debug(f"Regex scan ({standard_id}): checking {len(files_to_scan)} files")
        
        # Track files with violations
        violations = []
        
        # Check each file
        for file_path in files_to_scan:
            rel_path = os.path.relpath(file_path, module_path)
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                
                if not compiled_regex.fullmatch(content):
                    violations.append(rel_path)
                    
                    # For ASCII standard, find line numbers with violations
                    if "ascii" in standard_id.lower():
                        line_numbers = self._find_non_ascii_lines(content)
                        if line_numbers:
                            details.append(f"ASCII-error line(s) in {rel_path}: {', '.join(map(str, line_numbers))}")
                        else:
                            details.append(f"File {rel_path} {regex_explanation}")
                    else:
                        details.append(f"File {rel_path} {regex_explanation}")
            except Exception as e:
                logger.error(f"Error checking regex in {file_path}: {str(e)}")
                details.append(f"Error checking {rel_path}: {str(e)}")
        
        # Determine compliance level
        if not violations:
            compliance_level = "Yes"
        
        return {
            "standard_id": standard_id,
            "compliance_level": compliance_level,
            "details": details
        }
    
    def _find_non_ascii_lines(self, content: str) -> List[int]:
        """
        Find line numbers containing non-ASCII characters.
        
        Args:
            content: Content of the file
            
        Returns:
            List of line numbers with non-ASCII characters
        """
        lines = content.splitlines()
        non_ascii_lines = []
        
        for i, line in enumerate(lines, 1):
            # Check if line contains non-ASCII characters
            # Ignore ANSI color escape sequences
            # Remove ANSI escape sequences before checking
            cleaned_line = re.sub(r'\x1B\[[0-9;]*[mK]', '', line)
            
            if not all(ord(c) < 128 for c in cleaned_line):
                non_ascii_lines.append(i)
        
        return non_ascii_lines
    
    def _validate_default_settings_flat_structure(self, module_path: str, target_files: List[str], match_requirement: str) -> Dict[str, Any]:
        """
        Validate that DEFAULT_SETTINGS uses flat structure (no nested objects).
        
        Args:
            module_path: Path to module directory
            target_files: List of target files to check
            match_requirement: "all", "either", or "none"
            
        Returns:
            Dictionary with validation results
        """
        matching_files = []
        non_matching_files = []
        missing_files = []
        errors = []
        
        for target_file in target_files:
            file_path = os.path.join(module_path, target_file)
            
            if not os.path.exists(file_path):
                missing_files.append(target_file)
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                
                # Find the DEFAULT_SETTINGS block
                start_match = re.search(r'DEFAULT_SETTINGS\s*=\s*\{', content)
                if not start_match:
                    non_matching_files.append(target_file)
                    continue
                
                start_pos = start_match.start()
                
                # Find the matching closing brace
                brace_count = 0
                end_pos = start_pos
                for i, char in enumerate(content[start_pos:], start_pos):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                # Extract just the DEFAULT_SETTINGS block
                default_settings_block = content[start_pos:end_pos]
                
                # Check for nested objects within this block
                nested_pattern = r'\"[^\"]+\"\s*:\s*\{'
                nested_matches = re.findall(nested_pattern, default_settings_block)
                
                if nested_matches:
                    # Found nested objects - this is what we're checking for
                    matching_files.append(target_file)
                else:
                    # No nested objects found - flat structure
                    non_matching_files.append(target_file)
                    
            except Exception as e:
                logger.error(f"Error checking flat structure in {file_path}: {str(e)}")
                errors.append(f"Error checking flat structure in {target_file}: {str(e)}")
        
        # Determine if pattern matches based on match requirement
        matches = False
        if match_requirement == "all":
            # Must match all target files
            if not missing_files and not non_matching_files:
                matches = True
            else:
                for file_path in missing_files:
                    errors.append(f"Missing required file: {file_path}")
                for file_path in non_matching_files:
                    errors.append(f"File has flat structure (no nested objects): {file_path}")
        elif match_requirement == "none":
            # Must NOT match any target files (flat structure preferred)
            if not matching_files:
                matches = True
            else:
                for file_path in matching_files:
                    errors.append(f"Found nested objects in DEFAULT_SETTINGS in {file_path}")
        else:  # "either"
            # Must match at least one target file
            if matching_files:
                matches = True
            else:
                if missing_files:
                    for file_path in missing_files:
                        errors.append(f"Missing required file: {file_path}")
                if non_matching_files:
                    for file_path in non_matching_files:
                        errors.append(f"No nested objects found in {file_path}")
                if not missing_files and not non_matching_files:
                    errors.append("No target files found for flat structure check")
        
        return {
            "matches": matches,
            "matching_files": matching_files,
            "missing_files": missing_files,
            "non_matching_files": non_matching_files,
            "errors": errors
        }
    
    def _validate_validation_type_names(self, module_path: str, target_files: List[str], match_requirement: str) -> Dict[str, Any]:
        """
        Validate that VALIDATION_SCHEMA uses correct type names (string, bool, int, float).
        
        Args:
            module_path: Path to module directory
            target_files: List of target files to check
            match_requirement: "all", "either", or "none"
            
        Returns:
            Dictionary with validation results
        """
        matching_files = []
        non_matching_files = []
        missing_files = []
        errors = []
        
        # Incorrect type names that should be flagged
        incorrect_types = {"str", "boolean", "integer", "number"}
        
        for target_file in target_files:
            file_path = os.path.join(module_path, target_file)
            
            if not os.path.exists(file_path):
                missing_files.append(target_file)
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                
                # Find the VALIDATION_SCHEMA block
                start_match = re.search(r'VALIDATION_SCHEMA\s*=\s*\{', content)
                if not start_match:
                    non_matching_files.append(target_file)
                    continue
                
                start_pos = start_match.start()
                
                # Find the matching closing brace
                brace_count = 0
                end_pos = start_pos
                for i, char in enumerate(content[start_pos:], start_pos):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                # Extract just the VALIDATION_SCHEMA block
                validation_schema_block = content[start_pos:end_pos]
                
                # Check for incorrect type names
                found_incorrect_types = []
                for incorrect_type in incorrect_types:
                    # Pattern to match "type": "incorrect_type"
                    type_pattern = rf'"type"\s*:\s*"{re.escape(incorrect_type)}"'
                    if re.search(type_pattern, validation_schema_block):
                        found_incorrect_types.append(incorrect_type)
                
                if found_incorrect_types:
                    # Found incorrect type names - this is what we're checking for
                    matching_files.append(target_file)
                    errors.append(f"Found incorrect type names in VALIDATION_SCHEMA in {target_file}: {', '.join(found_incorrect_types)}")
                else:
                    # No incorrect type names found
                    non_matching_files.append(target_file)
                    
            except Exception as e:
                logger.error(f"Error checking type names in {file_path}: {str(e)}")
                errors.append(f"Error checking type names in {target_file}: {str(e)}")
        
        # Determine if pattern matches based on match requirement
        matches = False
        if match_requirement == "all":
            # Must match all target files
            if not missing_files and not non_matching_files:
                matches = True
            else:
                for file_path in missing_files:
                    errors.append(f"Missing required file: {file_path}")
                for file_path in non_matching_files:
                    errors.append(f"File uses correct type names: {file_path}")
        elif match_requirement == "none":
            # Must NOT match any target files (correct type names preferred)
            if not matching_files:
                matches = True
            # Errors already added above for matching files
        else:  # "either"
            # Must match at least one target file
            if matching_files:
                matches = True
            else:
                if missing_files:
                    for file_path in missing_files:
                        errors.append(f"Missing required file: {file_path}")
                if non_matching_files:
                    for file_path in non_matching_files:
                        errors.append(f"No incorrect type names found in {file_path}")
                if not missing_files and not non_matching_files:
                    errors.append("No target files found for type name check")
        
        return {
            "matches": matches,
            "matching_files": matching_files,
            "missing_files": missing_files,
            "non_matching_files": non_matching_files,
            "errors": errors
        }
    
    def _validate_with_modes(self, module: Dict[str, Any], standard: Dict[str, Any], 
                          validation: Dict[str, Any], comprehensive: bool = False) -> Dict[str, Any]:
        """
        Validate a module using mode-specific validation (standard vs comprehensive).
        
        Args:
            module: Module information dictionary
            standard: Standard definition
            validation: Validation rules from standard
            comprehensive: Whether to use comprehensive mode
            
        Returns:
            Dictionary with validation results
        """
        standard_id = standard["id"]
        module_path = module["path"]
        
        # Choose validation mode
        mode_key = "comprehensive_mode" if comprehensive else "standard_mode"
        mode_config = validation[mode_key]
        
        logger.debug(f"Validating {standard_id} using {mode_key}")
        
        # Initialize result variables
        compliance_level = "No"  # Default to No
        details = []  # List to store error details
        
        if comprehensive and "required_patterns" in mode_config:
            # Comprehensive mode: check imports AND usage AND anti-patterns
            compliance_level, details = self._validate_comprehensive_error_handling(
                module_path, mode_config, standard_id
            )
        else:
            # Standard mode: use legacy pattern validation
            patterns = mode_config.get("patterns", {})
            file_targets = mode_config.get("file_targets", {})
            match_requirements = mode_config.get("match_requirements", {})
            
            if not patterns or not file_targets:
                details.append("No patterns or file targets defined for validation mode")
                return {
                    "standard_id": standard_id,
                    "compliance_level": "No",
                    "details": details
                }
            
            # Use existing pattern validation logic
            pattern_results = {}
            for pattern_name, pattern in patterns.items():
                if pattern_name not in file_targets:
                    continue
                    
                target_files = file_targets[pattern_name]
                match_requirement = match_requirements.get(pattern_name, "either")
                
                pattern_result = self._validate_pattern(module_path, pattern_name, pattern, target_files, match_requirement, comprehensive=comprehensive)
                pattern_results[pattern_name] = pattern_result
                
                if not pattern_result["matches"]:
                    for error in pattern_result["errors"]:
                        details.append(error)
            
            # Determine overall compliance
            if not details and all(result["matches"] for result in pattern_results.values()):
                compliance_level = "Yes"
        
        return {
            "standard_id": standard_id,
            "compliance_level": compliance_level,
            "details": details
        }
    
    def _validate_comprehensive_error_handling(self, module_path: str, mode_config: Dict[str, Any], 
                                             standard_id: str) -> Tuple[str, List[str]]:
        """
        Validate comprehensive error handling with strict requirements.
        
        Args:
            module_path: Path to module directory
            mode_config: Comprehensive mode configuration
            standard_id: Standard identifier
            
        Returns:
            Tuple of (compliance_level, details)
        """
        details = []
        required_patterns = mode_config.get("required_patterns", {})
        required_pattern_targets = mode_config.get("required_pattern_targets", {})
        anti_patterns = mode_config.get("anti_patterns", [])
        anti_pattern_targets = mode_config.get("anti_pattern_targets", [])
        
        # Check required patterns (imports AND usage)
        for pattern_name, pattern in required_patterns.items():
            target_files = required_pattern_targets.get(pattern_name, ["*.py"])
            
            pattern_result = self._validate_pattern(
                module_path, pattern_name, pattern, target_files, "either", comprehensive=True
            )
            
            if not pattern_result["matches"]:
                if "imports" in pattern_name:
                    details.append(f"Missing required import: {pattern_name.replace('_', ' ')}")
                elif "usage" in pattern_name:
                    details.append(f"Missing required usage: {pattern_name.replace('_', ' ')}")
                else:
                    details.append(f"Missing required pattern: {pattern_name.replace('_', ' ')}")
        
        # Check anti-patterns
        files_to_scan = self._get_files_to_scan(module_path, {}, comprehensive=True)
        
        for anti_pattern in anti_patterns:
            try:
                compiled_pattern = re.compile(anti_pattern)
                for file_path in files_to_scan:
                    # Check if this file matches anti-pattern targets
                    rel_path = os.path.relpath(file_path, module_path)
                    if not self._file_matches_targets(rel_path, anti_pattern_targets):
                        continue
                    
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        
                        if compiled_pattern.search(content):
                            details.append(f"Found forbidden pattern '{anti_pattern}' in {rel_path}")
                    except Exception as e:
                        logger.error(f"Error checking anti-pattern in {file_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Invalid anti-pattern '{anti_pattern}': {str(e)}")
        
        # Determine compliance level
        compliance_level = "Yes" if not details else "No"
        
        return compliance_level, details
    
    def _file_matches_targets(self, file_path: str, targets: List[str]) -> bool:
        """Check if a file path matches any of the target patterns."""
        for target in targets:
            if target == "*.py" and file_path.endswith(".py"):
                return True
            elif target in file_path:
                return True
        return False
