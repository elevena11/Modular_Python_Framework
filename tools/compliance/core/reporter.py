"""
tools/compliance/core/reporter.py
Updated: March 21, 2025
Improved compliance report formatting with right-aligned textual columns and alphabetical sorting
"""

import os
import re
import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple
from .categorizer import ViolationCategorizer

logger = logging.getLogger("compliance.reporter")

class ComplianceReporter:
    """Reporter for generating and updating compliance files."""
    
    def parse_compliance_file(self, compliance_path: str) -> Dict[str, Dict[str, Any]]:
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
    
    def update_compliance_file(self, module: Dict[str, Any], 
                             results: Dict[str, Dict[str, Any]],
                             standards: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        """
        Update a module's compliance file with validation results.
        
        Args:
            module: Module information dictionary
            results: Dictionary of validation results for each standard
            standards: Optional dictionary of standards definitions
            
        Returns:
            True if successful, False otherwise
        """
        module_id = module["id"]
        module_path = module["path"]
        compliance_path = os.path.join(module_path, "compliance.md")
        
        logger.info(f"Updating compliance file for {module_id}")
        
        # Existing exceptions section to preserve
        exceptions_content = "# Add explanations for intentional non-compliance here"
        
        # Read existing compliance file if it exists
        if os.path.exists(compliance_path):
            try:
                parsed_data = self.parse_compliance_file(compliance_path)
                if parsed_data["exceptions"]:
                    exceptions_content = parsed_data["exceptions"]
            except Exception as e:
                logger.error(f"Error reading compliance file {compliance_path}: {str(e)}")
                return False
        
        try:
            # Get version from module manifest
            version = module.get("version", module.get("manifest", {}).get("version", "1.0.0"))
            
            # Group standards by section
            standards_by_section = self._group_standards_by_section(results, standards)
            
            # Create new compliance file content
            content = [
                "# Module Compliance Status",
                "",
                f"## Module: {module_id}",
                f"## Version: {version}",
                "",
                "---",
                "**Note: These compliance checks are for guidance only, not hard requirements.**",
                "This tool helps catch potential issues and assists new developers in identifying",
                "common patterns and potential oversights. Use your best judgment when addressing findings.",
                "---",
                ""
            ]
            
            # Add each section with standards
            for section, section_standards in standards_by_section.items():
                content.append(f"## {section}")
                
                # Add standards in this section
                for standard_id, result in section_standards:
                    standard_name = self._get_standard_display_name(standard_id, standards)
                    compliance_level = result["compliance_level"]
                    content.append(f"- {standard_name}: {compliance_level}")
                    
                    # Add details for non-compliant standards
                    if compliance_level == "No" and "details" in result and result["details"]:
                        for detail in result["details"]:
                            content.append(f"  - {detail}")
                
                content.append("")
            
            # Add exceptions section
            content.append("## Exceptions")
            content.append(exceptions_content)
            content.append("")
            
            # Add review information
            review_date = datetime.datetime.now().strftime("%Y-%m-%d")
            content.append(f"## Last Compliance Review: {review_date}")
            content.append("## Reviewed By: Compliance Tool")
            content.append("")
            
            # Write content to file
            with open(compliance_path, 'w') as f:
                f.write("\n".join(content))
            
            logger.info(f"Updated compliance file for {module_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating compliance file for {module_id}: {str(e)}")
            return False
    
    def update_comprehensive_compliance_file(self, module: Dict[str, Any], 
                                           comprehensive_results: Dict[str, Dict[str, Any]],
                                           standards: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        """
        Update a module's comprehensive compliance file with validation results.
        
        Args:
            module: Module information dictionary
            comprehensive_results: Dictionary of comprehensive validation results for each standard
            standards: Optional dictionary of standards definitions
            
        Returns:
            True if successful, False otherwise
        """
        module_id = module["id"]
        module_path = module["path"]
        compliance_path = os.path.join(module_path, "compliance_comprehensive.md")
        
        logger.info(f"Updating comprehensive compliance file for {module_id}")
        
        # Run standard validation (non-comprehensive) for the standard compliance.md file
        from .validator import ComplianceValidator
        validator = ComplianceValidator(standards or {})
        standard_results = validator.validate_module(module, comprehensive=False)
        
        # Update standard compliance file with standard results
        standard_updated = self.update_compliance_file(module, standard_results, standards)
        if not standard_updated:
            logger.error(f"Failed to update standard compliance file for {module_id}")
            return False
        
        # Collect violations for categorization (using comprehensive results)
        violations = []
        for standard_id, result in comprehensive_results.items():
            if result.get("compliance_level") != "Yes":
                for detail in result.get("details", []):
                    violations.append({
                        "standard_id": standard_id,
                        "file_path": module_path,  # This will be refined in categorizer
                        "detail": detail
                    })
        
        # Categorize violations
        categorizer = ViolationCategorizer()
        categorized = categorizer.categorize_violations(violations, module_path)
        
        # Get scanned files information
        from .scanner import StandardsScanner
        scanner = StandardsScanner()
        scanned_files = scanner.discover_module_files(module_path, comprehensive=True)
        
        # Generate comprehensive report content (using standard results for summary, comprehensive for violations)
        content = self._generate_comprehensive_content(module, standard_results, standards, categorized, scanned_files)
        
        try:
            with open(compliance_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Successfully updated comprehensive compliance file: {compliance_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating comprehensive compliance file for {module_id}: {str(e)}")
            return False
    
    def _generate_comprehensive_content(self, module: Dict[str, Any], 
                                      results: Dict[str, Dict[str, Any]],
                                      standards: Optional[Dict[str, Dict[str, Any]]] = None,
                                      categorized: Dict[str, List[Dict[str, Any]]] = None,
                                      scanned_files: List[str] = None) -> str:
        """Generate comprehensive compliance report content."""
        module_id = module["id"]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        categorizer = ViolationCategorizer()
        
        # Count results
        total_standards = len(results)
        passing_standards = sum(1 for r in results.values() if r.get("compliance_level") == "Yes")
        failing_standards = total_standards - passing_standards
        
        # Count violations by category
        critical_count = len(categorized.get("critical", []))
        review_count = len(categorized.get("review_required", []))
        context_count = len(categorized.get("context_dependent", []))
        total_violations = critical_count + review_count + context_count
        
        content = f"""# Comprehensive Compliance Report for {module_id}

Generated: {timestamp}

## Standard Compliance Summary
[PASS] {passing_standards}/{total_standards} standards passing in core files
[FAIL] {failing_standards}/{total_standards} standards failing in core files
[INFO] See `compliance.md` for details

## Comprehensive Scan Results
[SCAN] Scanned {len(scanned_files or [])} Python files recursively in module directory
[WARN] Found {total_violations} potential standards deviations

### Files Scanned
"""
        
        if scanned_files:
            # Group files by directory for better organization
            from collections import defaultdict
            import os
            
            files_by_dir = defaultdict(list)
            for file_path in scanned_files:
                rel_path = os.path.relpath(file_path, module["path"])
                dir_name = os.path.dirname(rel_path) if os.path.dirname(rel_path) else "."
                file_name = os.path.basename(rel_path)
                files_by_dir[dir_name].append(file_name)
            
            for dir_name in sorted(files_by_dir.keys()):
                if dir_name == ".":
                    content += f"**Root directory:** {len(files_by_dir[dir_name])} files\n"
                else:
                    content += f"**{dir_name}/:** {len(files_by_dir[dir_name])} files\n"
                
                for file_name in sorted(files_by_dir[dir_name]):
                    content += f"  - {file_name}\n"
                content += "\n"
        else:
            content += "No files scanned\n"
        
        content += """
"""
        
        # Organize violations by standard sections like compliance.md
        violations_by_section = self._organize_violations_by_section(categorized, standards)
        
        if critical_count > 0:
            content += f"""## CRITICAL VIOLATIONS (Must Fix)
{categorizer.get_category_description("critical")}
[ACTION] {categorizer.get_category_action("critical")}

"""
            content += self._format_violations_by_section(violations_by_section.get("critical", {}), standards)
            content += "\n"
        
        if review_count > 0:
            content += f"""## REVIEW REQUIRED (Verify Intent)
{categorizer.get_category_description("review_required")}
[ACTION] {categorizer.get_category_action("review_required")}

"""
            content += self._format_violations_by_section(violations_by_section.get("review_required", {}), standards)
            content += "\n"
        
        if context_count > 0:
            content += f"""## CONTEXT-DEPENDENT (Architecture Decisions)
{categorizer.get_category_description("context_dependent")}
[ACTION] {categorizer.get_category_action("context_dependent")}

"""
            content += self._format_violations_by_section(violations_by_section.get("context_dependent", {}), standards)
            content += "\n"
        
        if total_violations == 0:
            content += """## No Additional Violations Found
All comprehensive scan results align with standard compliance patterns.
"""
        
        content += f"""
---

## Standard Compliance Details
For detailed information about core file compliance, see `compliance.md`.

## Usage Notes
- **Critical violations** should be fixed immediately
- **Review required** items need developer verification and documentation
- **Context-dependent** items may be valid architectural decisions

## Framework Integration
This comprehensive scan ensures that all components, pipeline stages, and utilities
follow framework standards consistently throughout the module.
"""
        
        return content
    
    def _organize_violations_by_section(self, categorized: Dict[str, List[Dict[str, Any]]], 
                                      standards: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Organize violations by category and then by standard section.
        
        Args:
            categorized: Violations already categorized by severity
            standards: Standards definitions for section mapping
            
        Returns:
            Dict with structure: {category: {section: [violations]}}
        """
        organized = {}
        
        for category, violations in categorized.items():
            organized[category] = {}
            
            for violation in violations:
                standard_id = violation["standard_id"]
                section = self._determine_section(standard_id, standards)
                
                if section not in organized[category]:
                    organized[category][section] = []
                
                organized[category][section].append(violation)
        
        return organized
    
    def _format_violations_by_section(self, violations_by_section: Dict[str, List[Dict[str, Any]]], 
                                    standards: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
        """
        Format violations organized by section in compliance.md style.
        
        Args:
            violations_by_section: Violations grouped by section
            standards: Standards definitions for display names
            
        Returns:
            Formatted string with section headers and violations
        """
        if not violations_by_section:
            return ""
        
        content = ""
        
        # Sort sections for consistent ordering
        for section in sorted(violations_by_section.keys()):
            violations = violations_by_section[section]
            
            content += f"### {section}\n"
            
            # Group violations by standard within the section
            violations_by_standard = {}
            for violation in violations:
                standard_id = violation["standard_id"]
                if standard_id not in violations_by_standard:
                    violations_by_standard[standard_id] = []
                violations_by_standard[standard_id].append(violation)
            
            # Format each standard's violations
            for standard_id in sorted(violations_by_standard.keys()):
                standard_violations = violations_by_standard[standard_id]
                standard_name = self._get_standard_display_name(standard_id, standards)
                
                content += f"- **{standard_name}**: Issues Found\n"
                
                for violation in standard_violations:
                    # Split multi-line details and indent properly
                    detail_lines = violation["detail"].split("\n")
                    for i, line in enumerate(detail_lines):
                        if i == 0:
                            content += f"  - {line}\n"
                        else:
                            content += f"    {line}\n"
                
            content += "\n"
        
        return content
    
    def _group_standards_by_section(self, results: Dict[str, Dict[str, Any]], 
                                  standards: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, List[Tuple[str, Dict[str, Any]]]]:
        """
        Group standards by section for better organization.
        
        Args:
            results: Dictionary of validation results for each standard
            standards: Optional dictionary of standards definitions
            
        Returns:
            Dictionary of standards grouped by section
        """
        sections = {
            "Core Implementation Standards": [],
            "UI Standards": [],
            "API Standards": [],
            "Database Standards": [],
            "Testing & Documentation": []
        }
        
        # Group standards by section based on their ID
        for standard_id, result in results.items():
            section = self._determine_section(standard_id, standards)
            sections[section].append((standard_id, result))
            
        # Sort standards alphabetically within each section
        for section in sections:
            sections[section].sort(key=lambda x: x[0])
            
        return sections
    
    def _determine_section(self, standard_id: str, 
                         standards: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
        """
        Determine which section a standard belongs to based on its ID.
        
        Args:
            standard_id: ID of the standard
            standards: Optional dictionary of standards definitions
            
        Returns:
            Section name
        """
        # If standards dictionary is available, check for explicit section
        if standards and standard_id in standards and "section" in standards[standard_id]:
            return standards[standard_id]["section"]
        
        # Use keyword-based logic as fallback
        standard_id = standard_id.lower()
        
        if any(keyword in standard_id for keyword in ["ui", "gradio", "streamlit", "component"]):
            return "UI Standards"
        elif any(keyword in standard_id for keyword in ["api", "endpoint", "validation", "schema"]):
            return "API Standards"
        elif any(keyword in standard_id for keyword in ["db", "database", "transaction", "migration"]):
            return "Database Standards"
        elif any(keyword in standard_id for keyword in ["test", "doc", "documentation"]):
            return "Testing & Documentation"
        else:
            return "Core Implementation Standards"
    
    def _get_standard_display_name(self, standard_id: str,
                                 standards: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
        """
        Get display name for a standard.
        
        Args:
            standard_id: ID of the standard
            standards: Optional dictionary of standards definitions
            
        Returns:
            Display name for the standard
        """
        if standards and standard_id in standards and "name" in standards[standard_id]:
            return standards[standard_id]["name"]
        
        return standard_id
    
    def generate_report(self, modules: List[Dict[str, Any]], 
                       standards: Dict[str, Dict[str, Any]],
                       compliance_data: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
        """
        Generate a framework-wide compliance report.
        
        Args:
            modules: List of module information dictionaries
            standards: Dictionary of standards with ID as key
            compliance_data: Dictionary of compliance results for each module
            
        Returns:
            Report content as string
        """
        # Sort modules by ID
        sorted_modules = sorted(modules, key=lambda m: m["id"])
        
        # Count modules
        total_modules = len(sorted_modules)
        
        # Calculate compliance percentages for each standard
        standard_stats = {}
        for standard_id, standard in standards.items():
            standard_stats[standard_id] = {
                "name": standard.get("name", standard_id),
                "yes": 0,
                "no": 0,
                "total": 0
            }
        
        # Count compliance levels
        for module_id, module_results in compliance_data.items():
            for standard_id, result in module_results.items():
                if standard_id in standard_stats:
                    standard_stats[standard_id]["total"] += 1
                    
                    compliance_level = result["compliance_level"].lower()
                    if compliance_level == "yes":
                        standard_stats[standard_id]["yes"] += 1
                    elif compliance_level == "no":
                        standard_stats[standard_id]["no"] += 1
        
        # Calculate compliance percentages
        for standard_id, stats in standard_stats.items():
            if stats["total"] > 0:
                stats["yes_percent"] = (stats["yes"] / stats["total"]) * 100
                stats["no_percent"] = (stats["no"] / stats["total"]) * 100
            else:
                stats["yes_percent"] = 0
                stats["no_percent"] = 0
        
        # Sort standards alphabetically by name instead of by compliance percentage
        sorted_standards = sorted(
            standard_stats.items(),
            key=lambda x: x[1]["name"]
        )
        
        # Generate report
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = [
            "# Modular AI Framework - Compliance Report",
            f"*Generated: {now}*",
            "",
            "## Overview",
            "",
            f"- **Total Modules**: {total_modules}",
            f"- **Total Standards**: {len(standards)}",
            "",
            "## Compliance Summary",
            "",
            "| Yes | No  |      % | Standard ",
            "|-----|-----|--------|----------"
        ]
        
        # Add standard statistics with revised column order
        for standard_id, stats in sorted_standards:
            standard_name = stats["name"] 
            yes_count = stats['yes']
            no_count = stats['no']
            compliance_pct = stats['yes_percent']
            
            report.append(
                f"| {yes_count:3} | "
                f"{no_count:3} | "
                f"{compliance_pct:5.1f}% | "
                f"**{standard_name}** "
            )
        
        # Add module groups
        report.extend([
            "",
            "## Module Compliance Details",
            ""
        ])
        
        # Group modules by type
        module_types = {}
        for module in sorted_modules:
            module_type = module["type"]
            if module_type not in module_types:
                module_types[module_type] = []
            module_types[module_type].append(module)
        
        # Sort by module type
        for module_type in sorted(module_types.keys()):
            report.append(f"### {module_type.capitalize()} Modules")
            report.append("")
            
            # Create a table for this module type with revised column order
            report.append("| Yes | No  |      % | Version | Module ")
            report.append("|-----|-----|--------|---------|--------")
            
            # Add each module in this type with the new column order
            for module in module_types[module_type]:
                module_id = module["id"]
                module_version = module.get("version", module.get("manifest", {}).get("version", "1.0.0"))
                
                # Calculate compliance percentage
                if module_id in compliance_data:
                    results = compliance_data[module_id]
                    yes_count = sum(1 for r in results.values() if r["compliance_level"] == "Yes")
                    no_count = sum(1 for r in results.values() if r["compliance_level"] == "No")
                    total_count = len(results)
                    
                    if total_count > 0:
                        compliance_pct = (yes_count / total_count) * 100
                    else:
                        compliance_pct = 0
                else:
                    yes_count = 0
                    no_count = 0
                    compliance_pct = 0
                
                # Add to table with revised column order and padded spacing
                report.append(
                    f"| {yes_count:3} | "
                    f"{no_count:3} | "
                    f"{compliance_pct:5.1f}% | "
                    f" {module_version:7}| "
                    f"{module_id} "
                )
            
            report.append("")
        
        # Add detailed module information
        report.extend([
            "## Module Details",
            ""
        ])
        
        for module in sorted_modules:
            module_id = module["id"]
            module_version = module.get("version", module.get("manifest", {}).get("version", "1.0.0"))
            
            report.append(f"### {module_id} (v{module_version})")
            report.append("")
            
            # Check if module has compliance data
            if module_id in compliance_data and compliance_data[module_id]:
                module_results = compliance_data[module_id]
                
                # Group standards by status
                standards_by_status = {
                    "Yes": [],
                    "No": []
                }
                
                for standard_id, result in module_results.items():
                    level = result["compliance_level"]
                    if level in standards_by_status:
                        standards_by_status[level].append((standard_id, result))
                
                # Show Yes standards
                if standards_by_status["Yes"]:
                    report.append("#### [YES] Compliant Standards")
                    for standard_id, _ in sorted(standards_by_status["Yes"], key=lambda x: x[0]):
                        standard_name = self._get_standard_display_name(standard_id, standards)
                        report.append(f"- {standard_name}")
                    report.append("")
                
                # Show No standards
                if standards_by_status["No"]:
                    report.append("#### [NO] Non-Compliant Standards")
                    for standard_id, result in sorted(standards_by_status["No"], key=lambda x: x[0]):
                        standard_name = self._get_standard_display_name(standard_id, standards)
                        report.append(f"- {standard_name}")
                        
                        # Include details if available
                        if "details" in result and result["details"]:
                            report.append("  - Issues:")
                            for detail in result["details"]:
                                report.append(f"    - {detail}")
                    report.append("")
            else:
                report.append("*No compliance data available for this module.*")
            
            report.append("")
        
        return "\n".join(report)
