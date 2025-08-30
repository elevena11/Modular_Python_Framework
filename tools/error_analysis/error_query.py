#!/usr/bin/env python3
"""
tools/error_query.py
Quick query tool for exploring error patterns in the database
"""

import os
import sys
import sqlite3
import json
import argparse
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config import Config

class ErrorQuery:
    """Simple tool for querying error patterns."""
    
    def __init__(self):
        self.config = Config()
        self.db_path = os.path.join(self.config.DATA_DIR, "database", "framework.db")
    
    def query_errors(self, pattern: str = None, module: str = None, days: int = 7, limit: int = 20):
        """Query errors with optional filters."""
        
        # Build WHERE clause
        where_conditions = []
        params = []
        
        if days:
            since_date = datetime.now() - timedelta(days=days)
            where_conditions.append("last_seen >= ?")
            params.append(since_date.isoformat())
        
        if pattern:
            where_conditions.append("code LIKE ?")
            params.append(f"%{pattern}%")
        
        if module:
            where_conditions.append("module_id LIKE ?")
            params.append(f"%{module}%")
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
        SELECT 
            module_id,
            code,
            count,
            first_seen,
            last_seen,
            locations
        FROM error_codes 
        {where_clause}
        ORDER BY count DESC, last_seen DESC
        LIMIT ?
        """
        params.append(limit)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            errors = []
            for row in results:
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
            
            return errors
            
        finally:
            conn.close()
    
    def get_modules_with_errors(self, days: int = 7):
        """Get list of modules that have errors."""
        since_date = datetime.now() - timedelta(days=days)
        
        query = """
        SELECT 
            module_id,
            COUNT(*) as error_types,
            SUM(count) as total_occurrences,
            MAX(last_seen) as most_recent
        FROM error_codes 
        WHERE last_seen >= ?
        GROUP BY module_id
        ORDER BY total_occurrences DESC
        """
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, (since_date.isoformat(),))
            results = cursor.fetchall()
            
            modules = []
            for row in results:
                modules.append({
                    'module_id': row[0],
                    'error_types': row[1],
                    'total_occurrences': row[2],
                    'most_recent': row[3]
                })
            
            return modules
            
        finally:
            conn.close()
    
    def get_error_patterns(self, days: int = 7):
        """Get common error patterns."""
        since_date = datetime.now() - timedelta(days=days)
        
        query = """
        SELECT 
            code,
            COUNT(*) as modules_affected,
            SUM(count) as total_occurrences,
            GROUP_CONCAT(DISTINCT module_id) as affected_modules
        FROM error_codes 
        WHERE last_seen >= ?
        GROUP BY code
        HAVING modules_affected > 1 OR total_occurrences > 10
        ORDER BY total_occurrences DESC
        """
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, (since_date.isoformat(),))
            results = cursor.fetchall()
            
            patterns = []
            for row in results:
                patterns.append({
                    'code': row[0],
                    'modules_affected': row[1],
                    'total_occurrences': row[2],
                    'affected_modules': row[3].split(',') if row[3] else []
                })
            
            return patterns
            
        finally:
            conn.close()

def print_errors(errors, title="Error Query Results"):
    """Print formatted error results."""
    print(f"\n{title}")
    print("=" * 60)
    
    if not errors:
        print("No errors found matching criteria.")
        return
    
    for i, error in enumerate(errors, 1):
        print(f"{i:2d}. {error['code']}")
        print(f"    Module: {error['module_id']}")
        print(f"    Count: {error['count']}")
        print(f"    Last Seen: {error['last_seen']}")
        if error['locations']:
            print(f"    Locations: {', '.join(error['locations'][:3])}")
        print()

def print_modules(modules):
    """Print module error summary."""
    print("\nModules with Errors")
    print("=" * 60)
    
    for module in modules:
        print(f"  {module['module_id']}")
        print(f"    Error Types: {module['error_types']}")
        print(f"    Total Occurrences: {module['total_occurrences']}")
        print(f"    Most Recent: {module['most_recent']}")
        print()

def print_patterns(patterns):
    """Print error patterns."""
    print("\nCross-Module Error Patterns")
    print("=" * 60)
    
    for pattern in patterns:
        print(f"  {pattern['code']}")
        print(f"    Modules Affected: {pattern['modules_affected']}")
        print(f"    Total Occurrences: {pattern['total_occurrences']}")
        print(f"    Modules: {', '.join(pattern['affected_modules'])}")
        print()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Query error patterns from database')
    parser.add_argument('--pattern', type=str, help='Filter by error code pattern')
    parser.add_argument('--module', type=str, help='Filter by module name')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back (default: 7)')
    parser.add_argument('--limit', type=int, default=20, help='Maximum results to show (default: 20)')
    parser.add_argument('--modules', action='store_true', help='Show modules with errors')
    parser.add_argument('--patterns', action='store_true', help='Show cross-module error patterns')
    parser.add_argument('--all', action='store_true', help='Show all analyses')
    
    args = parser.parse_args()
    
    eq = ErrorQuery()
    
    try:
        # If specific filters provided, show filtered results
        if args.pattern or args.module:
            errors = eq.query_errors(
                pattern=args.pattern,
                module=args.module,
                days=args.days,
                limit=args.limit
            )
            
            filter_desc = []
            if args.pattern:
                filter_desc.append(f"pattern '{args.pattern}'")
            if args.module:
                filter_desc.append(f"module '{args.module}'")
            
            title = f"Errors matching {' and '.join(filter_desc)} (last {args.days} days)"
            print_errors(errors, title)
        
        # Show module summary
        if args.modules or args.all:
            modules = eq.get_modules_with_errors(args.days)
            print_modules(modules)
        
        # Show cross-module patterns
        if args.patterns or args.all:
            patterns = eq.get_error_patterns(args.days)
            print_patterns(patterns)
        
        # Default: show recent errors
        if not any([args.pattern, args.module, args.modules, args.patterns, args.all]):
            errors = eq.query_errors(days=args.days, limit=args.limit)
            print_errors(errors, f"Recent Errors (last {args.days} days)")
    
    except Exception as e:
        print(f"Error during query: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()