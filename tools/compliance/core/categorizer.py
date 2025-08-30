"""
tools/compliance/core/categorizer.py
Smart categorization of compliance violations for comprehensive scanning
"""

import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path

logger = logging.getLogger("compliance.categorizer")

class ViolationCategorizer:
    """Categorizes compliance violations based on context and severity."""
    
    # Standards that are almost always critical violations
    CRITICAL_STANDARDS = {
        "ascii_console_output",  # Unicode/emoji issues are rarely intentional
        "module_dependency",     # Import violations are usually mistakes
    }
    
    # Standard explanations to provide context
    STANDARD_EXPLANATIONS = {
        "openapi_documentation": {
            "purpose": "Ensures API endpoints have proper documentation with parameter descriptions",
            "missing_pattern": "parameter_documentation",
            "reason": "API endpoints need documentation for maintainability and auto-generated docs"
        },
        "api_schema_validation": {
            "purpose": "Ensures API endpoints use Pydantic models for request/response validation",
            "missing_pattern": "response_model_usage", 
            "reason": "Type safety and automatic validation require response models"
        },
        "module_structure": {
            "purpose": "Ensures modules follow the standard file structure",
            "missing_file": "readme.md",
            "reason": "Every module needs documentation for developers to understand its purpose"
        },
        "migration_support": {
            "purpose": "Ensures database modules can handle schema migrations",
            "missing_file": "db_models.py",
            "reason": "Database modules need model definitions for Alembic migrations"
        },
        "async_database_operations": {
            "purpose": "Ensures database operations use async patterns for performance",
            "missing_pattern": "async_db_methods",
            "reason": "Database operations should be non-blocking in async applications"
        },
        "sqlitejson_complex_types": {
            "purpose": "Ensures complex data types are stored as JSON in SQLite",
            "missing_file": "db_models.py", 
            "reason": "Complex types need proper JSON serialization for database storage"
        }
    }
    
    # Standards that depend heavily on file context
    CONTEXT_DEPENDENT_STANDARDS = {
        "openapi_documentation": [
            # Files that typically don't need API documentation
            "pipeline_stages", "components", "ui", "utils", "tests"
        ],
        "api_schema_validation": [
            # Files that typically don't have REST APIs
            "pipeline_stages", "components", "ui", "utils", "tests"
        ],
        "sqlitejson_complex_types": [
            # Files that typically don't use database
            "ui", "pipeline_stages", "components", "utils", "tests"
        ],
        "migration_support": [
            # Files that typically don't handle migrations
            "ui", "pipeline_stages", "components", "utils", "tests"
        ],
        "async_database_operations": [
            # Files that typically don't do database operations
            "ui", "pipeline_stages", "components", "utils", "tests"
        ]
    }
    
    # Standards that require careful review but may be intentional
    REVIEW_REQUIRED_STANDARDS = {
        "layered_error_handling",  # May vary in pipeline stages
        "service_registration",    # Not all components are services
        "settings_api",           # Utility classes may not need settings
        "two_phase_initialization_phase1", # Helpers may not need phases
        "two_phase_initialization_phase2", # Helpers may not need phases
        "module_structure",       # Specialized files may deviate
        "two_phase_db_operations" # Some components may not use database
    }
    
    def __init__(self):
        """Initialize the categorizer."""
        pass
    
    def categorize_violation(self, standard_id: str, file_path: str, module_path: str) -> str:
        """
        Categorize a compliance violation.
        
        Args:
            standard_id: The ID of the failed standard
            file_path: Path to the file with the violation
            module_path: Path to the module directory
            
        Returns:
            One of: "critical", "review_required", "context_dependent"
        """
        # Convert file path to relative path from module
        try:
            rel_path = Path(file_path).relative_to(Path(module_path))
            path_parts = rel_path.parts
        except ValueError:
            # If relative path fails, use the full path
            path_parts = Path(file_path).parts
        
        # Check for critical violations first
        if standard_id in self.CRITICAL_STANDARDS:
            return "critical"
        
        # Check for context-dependent violations
        if standard_id in self.CONTEXT_DEPENDENT_STANDARDS:
            excluded_dirs = self.CONTEXT_DEPENDENT_STANDARDS[standard_id]
            # Check if file is in any of the excluded directories
            for part in path_parts:
                if part in excluded_dirs:
                    return "context_dependent"
        
        # Check for review required violations
        if standard_id in self.REVIEW_REQUIRED_STANDARDS:
            return "review_required"
        
        # Default to review required for unknown standards
        return "review_required"
    
    def get_category_description(self, category: str) -> str:
        """Get a description for a violation category."""
        descriptions = {
            "critical": "Likely mistakes that should be fixed",
            "review_required": "May be intentional, needs developer verification",
            "context_dependent": "Architectural decisions that may be valid"
        }
        return descriptions.get(category, "Unknown category")
    
    def get_category_action(self, category: str) -> str:
        """Get the recommended action for a violation category."""
        actions = {
            "critical": "Developer should fix these",
            "review_required": "Developer needs to verify if intentional and document reasoning",
            "context_dependent": "Architectural review, may be valid design decisions"
        }
        return actions.get(category, "Review and determine appropriate action")
    
    def enhance_violation_detail(self, standard_id: str, detail: str) -> str:
        """
        Enhance a violation detail with explanatory context.
        
        Args:
            standard_id: The standard that failed
            detail: The original detail message
            
        Returns:
            Enhanced detail message with context
        """
        if standard_id not in self.STANDARD_EXPLANATIONS:
            return detail
        
        explanation = self.STANDARD_EXPLANATIONS[standard_id]
        
        # Just return the detail as-is, following the same simple format as compliance.md
        return detail

    def categorize_violations(self, violations: List[Dict[str, Any]], module_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize a list of violations with enhanced details.
        
        Args:
            violations: List of violation dictionaries
            module_path: Path to the module directory
            
        Returns:
            Dictionary with violations grouped by category
        """
        categorized = {
            "critical": [],
            "review_required": [],
            "context_dependent": []
        }
        
        for violation in violations:
            category = self.categorize_violation(
                violation["standard_id"],
                violation["file_path"],
                module_path
            )
            
            # Enhance the violation detail with explanatory context
            enhanced_detail = self.enhance_violation_detail(
                violation["standard_id"],
                violation["detail"]
            )
            
            # Create enhanced violation
            enhanced_violation = violation.copy()
            enhanced_violation["detail"] = enhanced_detail
            
            categorized[category].append(enhanced_violation)
        
        return categorized