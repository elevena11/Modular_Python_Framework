"""
Compliance levels - Make compliance helpful, not annoying
"""

from enum import Enum
from typing import Dict, List, Any

class ComplianceLevel(Enum):
    """Different levels of compliance enforcement."""
    CRITICAL = "critical"      # Must fix - breaks framework
    WARNING = "warning"        # Should fix - best practices  
    SUGGESTION = "suggestion"  # Nice to have - improvements
    INFO = "info"             # Informational only

class ComplianceLevelManager:
    """Manages which standards are at which compliance levels."""
    
    def __init__(self):
        # Categorize standards by impact level
        self.level_mapping = {
            # CRITICAL - Framework won't work properly without these
            ComplianceLevel.CRITICAL: [
                "two_phase_initialization_phase1",
                "service_registration",
                "module_structure",  # Need basic files
                "manifest_validation"  # Need valid manifest
            ],
            
            # WARNING - Framework works but not optimal
            ComplianceLevel.WARNING: [
                "async_database_operations",
                "two_phase_db_operations", 
                "module_dependency",
                "layered_error_handling"
            ],
            
            # SUGGESTION - Nice to have for consistency
            ComplianceLevel.SUGGESTION: [
                "api_schema_validation",
                "openapi_documentation",
                "settings_api",
                "sqlitejson_complex_types"
            ],
            
            # INFO - Just informational
            ComplianceLevel.INFO: [
                "ascii_console_output",
                "ui_streamlit_implementation",
                "migration_support",
                "two_phase_initialization_phase2"
            ]
        }
    
    def get_level(self, standard_id: str) -> ComplianceLevel:
        """Get the compliance level for a standard."""
        for level, standards in self.level_mapping.items():
            if standard_id in standards:
                return level
        return ComplianceLevel.INFO  # Default to info level
    
    def get_standards_by_level(self, level: ComplianceLevel) -> List[str]:
        """Get all standards at a specific compliance level."""
        return self.level_mapping.get(level, [])
    
    def filter_results_by_level(self, results: Dict[str, Any], min_level: ComplianceLevel) -> Dict[str, Any]:
        """Filter compliance results to only show issues at or above a certain level."""
        level_order = [ComplianceLevel.CRITICAL, ComplianceLevel.WARNING, 
                      ComplianceLevel.SUGGESTION, ComplianceLevel.INFO]
        
        min_index = level_order.index(min_level)
        relevant_levels = level_order[:min_index + 1]
        
        filtered = {}
        for standard_id, result in results.items():
            standard_level = self.get_level(standard_id)
            if standard_level in relevant_levels:
                # Add level information to result
                result['compliance_level'] = standard_level.value
                filtered[standard_id] = result
        
        return filtered
    
    def get_summary_by_level(self, results: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
        """Get a summary of compliance results organized by level."""
        summary = {
            'critical': {'passed': 0, 'failed': 0, 'total': 0},
            'warning': {'passed': 0, 'failed': 0, 'total': 0},
            'suggestion': {'passed': 0, 'failed': 0, 'total': 0},
            'info': {'passed': 0, 'failed': 0, 'total': 0}
        }
        
        for standard_id, result in results.items():
            level = self.get_level(standard_id).value
            summary[level]['total'] += 1
            
            if result.get('status') == 'passed':
                summary[level]['passed'] += 1
            else:
                summary[level]['failed'] += 1
        
        return summary