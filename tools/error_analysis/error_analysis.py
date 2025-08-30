#!/usr/bin/env python3
"""
tools/error_analysis.py
Tool for analyzing error patterns from the error_handler database
to identify potential compliance standards and development improvements
"""

import os
import sys
import argparse
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config import Config
import sqlite3

class ErrorAnalyzer:
    """Analyzes error patterns to identify potential compliance improvements."""
    
    def __init__(self):
        self.config = Config()
        self.db_path = os.path.join(self.config.DATA_DIR, "database", "framework.db")
        
    async def initialize(self):
        """Initialize the database connection."""
        # Check if database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        # Test connection
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
        except Exception as e:
            raise ConnectionError(f"Cannot connect to database: {e}")
    
    async def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get a summary of errors from the last N days."""
        await self.initialize()
        
        # Calculate date threshold
        since_date = datetime.now() - timedelta(days=days)
        
        # Get error summary data
        query = """
        SELECT 
            module_id,
            code,
            count,
            first_seen,
            last_seen,
            locations
        FROM error_codes 
        WHERE last_seen >= ?
        ORDER BY count DESC, last_seen DESC
        """
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, (since_date.isoformat(),))
            result = cursor.fetchall()
            
            errors = []
            for row in result:
                try:
                    locations = json.loads(row[5]) if row[5] else []
                except:
                    locations = []
                    
                errors.append({
                    'module_id': row[0],
                    'code': row[1],
                    'count': row[2],
                    'first_seen': row[3],
                    'last_seen': row[4],
                    'locations': locations
                })
            
            return {
                'period_days': days,
                'total_error_types': len(errors),
                'errors': errors
            }
        
        finally:
            conn.close()
    
    async def analyze_error_patterns(self, days: int = 7) -> Dict[str, Any]:
        """Analyze error patterns to identify potential compliance issues."""
        summary = await self.get_error_summary(days)
        
        # Group errors by module
        by_module = {}
        by_error_type = {}
        potential_standards = []
        
        for error in summary['errors']:
            module_id = error['module_id']
            code = error['code']
            count = error['count']
            
            # Group by module
            if module_id not in by_module:
                by_module[module_id] = {'errors': [], 'total_count': 0}
            by_module[module_id]['errors'].append(error)
            by_module[module_id]['total_count'] += count
            
            # Group by error type pattern
            error_category = self._categorize_error(code)
            if error_category not in by_error_type:
                by_error_type[error_category] = {'errors': [], 'total_count': 0}
            by_error_type[error_category]['errors'].append(error)
            by_error_type[error_category]['total_count'] += count
            
            # Identify potential compliance standards
            standard_suggestion = self._suggest_compliance_standard(error)
            if standard_suggestion:
                potential_standards.append(standard_suggestion)
        
        return {
            'summary': summary,
            'by_module': by_module,
            'by_error_type': by_error_type,
            'potential_standards': potential_standards
        }
    
    def _categorize_error(self, error_code: str) -> str:
        """Categorize an error code into a general pattern."""
        code_lower = error_code.lower()
        
        if 'validation' in code_lower or 'unknown_type' in code_lower:
            return 'validation_errors'
        elif 'connection' in code_lower or 'timeout' in code_lower:
            return 'connection_errors'
        elif 'database' in code_lower or 'db' in code_lower:
            return 'database_errors'
        elif 'import' in code_lower or 'module' in code_lower:
            return 'import_errors'
        elif 'config' in code_lower or 'setting' in code_lower:
            return 'configuration_errors'
        elif 'api' in code_lower or 'schema' in code_lower:
            return 'api_errors'
        else:
            return 'other_errors'
    
    def _suggest_compliance_standard(self, error: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Suggest a compliance standard based on an error pattern."""
        code = error['code']
        module_id = error['module_id']
        count = error['count']
        
        # Only suggest standards for recurring errors
        if count < 3:
            return None
        
        suggestions = []
        
        # Type validation errors
        if 'UNKNOWN_TYPE' in code:
            suggestions.append({
                'standard_name': 'Type Validation Standard',
                'description': 'Enforce correct type names in validation schemas',
                'pattern': 'VALIDATION_SCHEMA type validation',
                'target_modules': ['all'],
                'error_code': code,
                'frequency': count,
                'justification': f'Recurring type validation errors ({count} occurrences) suggest need for standardized type naming'
            })
        
        # Database connection errors
        elif 'CONNECTION' in code and 'DATABASE' in code:
            suggestions.append({
                'standard_name': 'Database Connection Resilience',
                'description': 'Standardize database connection handling and retry logic',
                'pattern': 'Database connection error handling',
                'target_modules': ['modules with database dependencies'],
                'error_code': code,
                'frequency': count,
                'justification': f'Database connection issues ({count} occurrences) suggest need for connection resilience standards'
            })
        
        # Import/module loading errors
        elif 'IMPORT' in code or 'MODULE' in code:
            suggestions.append({
                'standard_name': 'Module Import Standard',
                'description': 'Standardize module import patterns and error handling',
                'pattern': 'Import error handling and fallbacks',
                'target_modules': ['all'],
                'error_code': code,
                'frequency': count,
                'justification': f'Import errors ({count} occurrences) suggest need for standardized import patterns'
            })
        
        return suggestions[0] if suggestions else None
    
    async def generate_compliance_standard_draft(self, error_pattern: str) -> Dict[str, Any]:
        """Generate a draft compliance standard based on error patterns."""
        # Analyze errors matching the pattern
        summary = await self.get_error_summary(30)  # Look at last 30 days
        
        matching_errors = [
            error for error in summary['errors']
            if error_pattern.lower() in error['code'].lower()
        ]
        
        if not matching_errors:
            return {'error': f'No errors found matching pattern: {error_pattern}'}
        
        # Extract common patterns
        modules_affected = list(set(error['module_id'] for error in matching_errors))
        total_occurrences = sum(error['count'] for error in matching_errors)
        locations = []
        for error in matching_errors:
            locations.extend(error['locations'])
        
        # Generate standard draft
        standard_id = f"error_prevention_{error_pattern.lower().replace(' ', '_')}"
        
        draft = {
            "id": standard_id,
            "name": f"Error Prevention: {error_pattern}",
            "version": "1.0.0",
            "description": f"Standard to prevent recurring {error_pattern} errors",
            "owner_module": "core.compliance",
            "analysis": {
                "total_occurrences": total_occurrences,
                "affected_modules": modules_affected,
                "common_locations": list(set(locations)),
                "error_codes": [error['code'] for error in matching_errors]
            },
            "requirements": self._generate_requirements(matching_errors),
            "validation": self._generate_validation_rules(matching_errors),
            "section": "Error Prevention Standards",
            "documentation": f"This standard was generated based on analysis of {total_occurrences} error occurrences across {len(modules_affected)} modules."
        }
        
        return draft
    
    def _generate_requirements(self, errors: List[Dict[str, Any]]) -> List[str]:
        """Generate requirements based on error patterns."""
        requirements = []
        error_types = set(error['code'] for error in errors)
        
        for error_code in error_types:
            if 'UNKNOWN_TYPE' in error_code:
                requirements.extend([
                    "Use standard type names: string, bool, int, float",
                    "Validate schema type definitions before registration",
                    "Implement type validation in development tools"
                ])
            elif 'CONNECTION' in error_code:
                requirements.extend([
                    "Implement connection retry logic",
                    "Add connection timeout handling",
                    "Provide meaningful connection error messages"
                ])
            elif 'IMPORT' in error_code:
                requirements.extend([
                    "Use relative imports within modules",
                    "Implement graceful import fallbacks",
                    "Document module dependencies clearly"
                ])
        
        return list(set(requirements))  # Remove duplicates
    
    def _generate_validation_rules(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate validation rules based on error patterns."""
        # This would need to be customized based on specific error types
        # For now, return a basic structure
        return {
            "patterns": {},
            "file_targets": {},
            "match_requirements": {},
            "anti_patterns": []
        }

def print_error_summary(summary: Dict[str, Any]):
    """Print a formatted error summary."""
    print(f"\nError Summary (Last {summary['period_days']} days)")
    print("=" * 60)
    print(f"Total Error Types: {summary['total_error_types']}")
    
    if summary['errors']:
        print(f"\nTop 10 Most Frequent Errors:")
        print("-" * 60)
        
        for i, error in enumerate(summary['errors'][:10], 1):
            print(f"{i:2d}. {error['code']}")
            print(f"    Module: {error['module_id']}")
            print(f"    Count: {error['count']}")
            print(f"    Last Seen: {error['last_seen']}")
            if error['locations']:
                print(f"    Locations: {', '.join(error['locations'][:3])}")
            print()

def print_analysis(analysis: Dict[str, Any]):
    """Print formatted error analysis."""
    print("\nError Pattern Analysis")
    print("=" * 60)
    
    # Module analysis
    print("\nErrors by Module:")
    sorted_modules = sorted(
        analysis['by_module'].items(),
        key=lambda x: x[1]['total_count'],
        reverse=True
    )
    
    for module, data in sorted_modules[:5]:
        print(f"  {module}: {data['total_count']} total errors ({len(data['errors'])} types)")
    
    # Error type analysis
    print("\nErrors by Category:")
    sorted_types = sorted(
        analysis['by_error_type'].items(),
        key=lambda x: x[1]['total_count'],
        reverse=True
    )
    
    for error_type, data in sorted_types:
        print(f"  {error_type}: {data['total_count']} occurrences ({len(data['errors'])} types)")
    
    # Potential standards
    if analysis['potential_standards']:
        print("\nSuggested Compliance Standards:")
        for i, standard in enumerate(analysis['potential_standards'][:5], 1):
            print(f"  {i}. {standard['standard_name']}")
            print(f"     {standard['description']}")
            print(f"     Based on: {standard['error_code']} ({standard['frequency']} occurrences)")
            print()

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Analyze error patterns for compliance improvements')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    parser.add_argument('--summary', action='store_true', help='Show error summary')
    parser.add_argument('--analyze', action='store_true', help='Show error pattern analysis')
    parser.add_argument('--generate-standard', type=str, help='Generate compliance standard for error pattern')
    parser.add_argument('--all', action='store_true', help='Show all available analyses')
    
    args = parser.parse_args()
    
    if not any([args.summary, args.analyze, args.generate_standard, args.all]):
        args.all = True  # Default to showing all
    
    analyzer = ErrorAnalyzer()
    
    try:
        if args.summary or args.all:
            summary = await analyzer.get_error_summary(args.days)
            print_error_summary(summary)
        
        if args.analyze or args.all:
            analysis = await analyzer.analyze_error_patterns(args.days)
            print_analysis(analysis)
        
        if args.generate_standard:
            draft = await analyzer.generate_compliance_standard_draft(args.generate_standard)
            print(f"\nGenerated Compliance Standard Draft:")
            print("=" * 60)
            print(json.dumps(draft, indent=2))
            
            # Optionally save to file
            output_file = f"tools/compliance/drafts/{draft['id']}.json"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(draft, f, indent=2)
            print(f"\nDraft saved to: {output_file}")
    
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())