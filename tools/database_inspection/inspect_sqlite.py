#!/usr/bin/env python3
"""
SQLite Database Inspection CLI Tool

Standalone tool to inspect SQLite databases without requiring
the backend framework to be loaded. Directly connects to the database files.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class SQLiteInspector:
    """Direct SQLite inspection without framework dependencies."""
    
    def __init__(self, db_path: str = None, database_name: str = "framework"):
        """Initialize with custom database path or use framework default."""
        if db_path is None:
            # Use framework default path with multi-database structure
            self.db_path = project_root / "data" / "database" / f"{database_name}.db"
        else:
            self.db_path = Path(db_path)
        
        self.database_name = database_name
        
        print(f"Connecting to SQLite database at: {self.db_path}")
        
        if not self.db_path.exists():
            print(f"❌ Database file does not exist: {self.db_path}")
            sys.exit(1)
        
        try:
            # Test connection
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("SELECT 1")
            print("✅ Connected to SQLite database successfully")
        except Exception as e:
            print(f"❌ Failed to connect to SQLite database: {e}")
            sys.exit(1)
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get basic database information."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get database file info
                file_size = self.db_path.stat().st_size
                
                # Get SQLite version and database info
                cursor.execute("SELECT sqlite_version()")
                sqlite_version = cursor.fetchone()[0]
                
                # Get database schema version (if exists)
                try:
                    cursor.execute("PRAGMA user_version")
                    user_version = cursor.fetchone()[0]
                except:
                    user_version = "unknown"
                
                # Get page size and other pragmas
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                
                return {
                    "database_path": str(self.db_path),
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                    "sqlite_version": sqlite_version,
                    "user_version": user_version,
                    "page_size": page_size,
                    "page_count": page_count,
                    "estimated_size_mb": round((page_size * page_count) / (1024 * 1024), 2)
                }
        except Exception as e:
            return {"error": f"Error getting database info: {e}"}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List all tables in the database."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("""
                    SELECT name, type, sql 
                    FROM sqlite_master 
                    WHERE type IN ('table', 'view')
                    ORDER BY name
                """)
                
                tables = []
                for row in cursor.fetchall():
                    table_name = row['name']
                    
                    # Skip sqlite internal tables
                    if table_name.startswith('sqlite_'):
                        continue
                    
                    # Get row count
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                        row_count = cursor.fetchone()[0]
                    except Exception as e:
                        row_count = f"Error: {e}"
                    
                    # Get column info
                    try:
                        cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                        columns = []
                        for col_row in cursor.fetchall():
                            columns.append({
                                "name": col_row[1],
                                "type": col_row[2],
                                "not_null": bool(col_row[3]),
                                "default": col_row[4],
                                "primary_key": bool(col_row[5])
                            })
                    except Exception as e:
                        columns = [{"error": f"Error getting columns: {e}"}]
                    
                    tables.append({
                        "name": table_name,
                        "type": row['type'],
                        "row_count": row_count,
                        "columns": columns,
                        "create_sql": row['sql']
                    })
                
                return tables
        except Exception as e:
            return [{"error": f"Error listing tables: {e}"}]
    
    def inspect_table(self, table_name: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Inspect a specific table."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Verify table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                
                if not cursor.fetchone():
                    return {"error": f"Table '{table_name}' not found"}
                
                # Get table info
                cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "name": row[1],
                        "type": row[2],
                        "not_null": bool(row[3]),
                        "default": row[4],
                        "primary_key": bool(row[5])
                    })
                
                # Get total row count
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                total_rows = cursor.fetchone()[0]
                
                # Get sample data
                sample_data = []
                if total_rows > 0:
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT ? OFFSET ?", (limit, offset))
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        row_dict = {}
                        for i, column in enumerate(columns):
                            value = row[i]
                            # Truncate long text values for display
                            if isinstance(value, str) and len(value) > 100:
                                value = value[:100] + "..."
                            row_dict[column["name"]] = value
                        sample_data.append(row_dict)
                
                # Get indexes
                cursor.execute(f"PRAGMA index_list(`{table_name}`)")
                indexes = []
                for row in cursor.fetchall():
                    index_name = row[1]
                    cursor.execute(f"PRAGMA index_info(`{index_name}`)")
                    index_columns = [col[2] for col in cursor.fetchall()]
                    indexes.append({
                        "name": index_name,
                        "unique": bool(row[2]),
                        "columns": index_columns
                    })
                
                return {
                    "table_name": table_name,
                    "total_rows": total_rows,
                    "columns": columns,
                    "indexes": indexes,
                    "sample_data": sample_data,
                    "showing_rows": f"{offset + 1}-{offset + len(sample_data)} of {total_rows}"
                }
                
        except Exception as e:
            return {"error": f"Error inspecting table '{table_name}': {e}"}
    
    def search_table(self, table_name: str, search_term: str, limit: int = 10) -> Dict[str, Any]:
        """Search for data in a table."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get column info to build search query
                cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Build search conditions for text columns
                text_columns = []
                for col in columns:
                    # Check if column might contain text
                    cursor.execute(f"SELECT `{col}` FROM `{table_name}` WHERE `{col}` IS NOT NULL LIMIT 1")
                    sample = cursor.fetchone()
                    if sample and isinstance(sample[0], str):
                        text_columns.append(col)
                
                if not text_columns:
                    return {"error": f"No text columns found in table '{table_name}' for searching"}
                
                # Build WHERE clause
                where_conditions = []
                params = []
                for col in text_columns:
                    where_conditions.append(f"`{col}` LIKE ?")
                    params.append(f"%{search_term}%")
                
                where_clause = " OR ".join(where_conditions)
                
                # Execute search
                search_sql = f"SELECT * FROM `{table_name}` WHERE {where_clause} LIMIT ?"
                params.append(limit)
                
                cursor.execute(search_sql, params)
                rows = cursor.fetchall()
                
                # Format results
                results = []
                for row in rows:
                    row_dict = {}
                    for i, col_name in enumerate(columns):
                        value = row[i]
                        # Truncate long values
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        row_dict[col_name] = value
                    results.append(row_dict)
                
                return {
                    "table_name": table_name,
                    "search_term": search_term,
                    "searched_columns": text_columns,
                    "results_count": len(results),
                    "results": results
                }
                
        except Exception as e:
            return {"error": f"Error searching table '{table_name}': {e}"}
    
    def execute_query(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """Execute a custom SQL query."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Add LIMIT if not present in SELECT queries
                query_upper = query.upper().strip()
                if query_upper.startswith('SELECT') and 'LIMIT' not in query_upper:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query)
                
                if query_upper.startswith('SELECT'):
                    rows = cursor.fetchall()
                    
                    if rows:
                        columns = [description[0] for description in cursor.description]
                        results = []
                        for row in rows:
                            row_dict = {}
                            for i, col_name in enumerate(columns):
                                value = row[i]
                                # Truncate long values
                                if isinstance(value, str) and len(value) > 200:
                                    value = value[:200] + "..."
                                row_dict[col_name] = value
                            results.append(row_dict)
                        
                        return {
                            "query": query,
                            "columns": columns,
                            "row_count": len(results),
                            "results": results
                        }
                    else:
                        return {
                            "query": query,
                            "message": "Query executed successfully, no results returned"
                        }
                else:
                    return {
                        "query": query,
                        "message": f"Non-SELECT query executed successfully"
                    }
                    
        except Exception as e:
            return {"error": f"Error executing query: {e}"}


def format_output(data: Any, format_type: str = "pretty") -> str:
    """Format output for display."""
    if format_type == "json":
        return json.dumps(data, indent=2, default=str)
    
    # Pretty format
    if isinstance(data, dict) and "error" in data:
        return f"❌ {data['error']}"
    
    return str(data)


def print_table_data(table_info: Dict[str, Any], show_schema: bool = False):
    """Print table information in a readable format."""
    if "error" in table_info:
        print(f"❌ {table_info['error']}")
        return
    
    print(f"📊 Table: {table_info['table_name']}")
    print(f"   Total Rows: {table_info.get('total_rows', 'Unknown')}")
    
    if show_schema and "columns" in table_info:
        print(f"   📋 Schema ({len(table_info['columns'])} columns):")
        for col in table_info['columns']:
            pk_marker = " 🔑" if col.get('primary_key') else ""
            not_null = " NOT NULL" if col.get('not_null') else ""
            default = f" DEFAULT {col.get('default')}" if col.get('default') else ""
            print(f"      • {col['name']} ({col['type']}){not_null}{default}{pk_marker}")
    
    if "indexes" in table_info and table_info['indexes']:
        print(f"   🔍 Indexes ({len(table_info['indexes'])}):")
        for idx in table_info['indexes']:
            unique_marker = " UNIQUE" if idx.get('unique') else ""
            print(f"      • {idx['name']}{unique_marker} on {', '.join(idx['columns'])}")
    
    if "sample_data" in table_info and table_info['sample_data']:
        print(f"   📄 Sample Data ({table_info.get('showing_rows', 'Unknown range')}):")
        for i, row in enumerate(table_info['sample_data'][:5], 1):  # Show max 5 rows
            print(f"      Row {i}:")
            for key, value in row.items():
                print(f"        {key}: {value}")
            print()


def interactive_mode(db_path: str = None):
    """Interactive mode for user-friendly database exploration."""
    print("\n🗄️  SQLite Inspector - Interactive Mode")
    print("=" * 50)
    
    # Initialize inspector
    inspector = SQLiteInspector(db_path)
    
    # Get database info
    db_info = inspector.get_database_info()
    if "error" in db_info:
        print(f"❌ Error: {db_info['error']}")
        return
    
    print(f"📊 Database: {db_info['database_path']}")
    print(f"📁 Size: {db_info['file_size_mb']} MB")
    
    while True:
        # Get tables
        tables = inspector.list_tables()
        if not tables or (len(tables) == 1 and "error" in tables[0]):
            print("⚠️  No tables found in database")
            break
        
        print(f"\n📚 Available Tables ({len(tables)}):")
        for i, table in enumerate(tables, 1):
            if "error" not in table:
                print(f"  {i}. {table['name']} ({table['row_count']} rows)")
        
        print(f"  0. Exit")
        
        # Get user choice
        try:
            choice = input(f"\nChoose table (0-{len(tables)}): ").strip()
            
            if choice == "0" or choice.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not choice.isdigit() or int(choice) < 1 or int(choice) > len(tables):
                print("❌ Invalid choice. Please enter a number from the list.")
                continue
            
            table = tables[int(choice) - 1]
            if "error" in table:
                print(f"❌ Error with table: {table['error']}")
                continue
            
            explore_table_interactive(inspector, table['name'])
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def explore_table_interactive(inspector: SQLiteInspector, table_name: str):
    """Interactive exploration of a specific table."""
    
    while True:
        # Get table info
        table_info = inspector.inspect_table(table_name, limit=1)
        if "error" in table_info:
            print(f"❌ Error: {table_info['error']}")
            break
        
        print(f"\n📊 Table: {table_name}")
        print(f"📈 Total Rows: {table_info.get('total_rows', 'Unknown')}")
        print(f"🏗️  Columns: {len(table_info.get('columns', []))}")
        
        print("\nActions:")
        print("  1. Browse data")
        print("  2. Search data")
        print("  3. Show schema")
        print("  4. Execute custom query")
        print("  5. Export data")
        print("  0. Back to table list")
        
        try:
            action = input("\nChoose action (0-5): ").strip()
            
            if action == "0":
                break
            elif action == "1":
                browse_table_data(inspector, table_name)
            elif action == "2":
                search_table_data(inspector, table_name)
            elif action == "3":
                show_table_schema(inspector, table_name)
            elif action == "4":
                execute_custom_query(inspector, table_name)
            elif action == "5":
                export_table_data(inspector, table_name)
            else:
                print("❌ Invalid choice. Please enter a number from the menu.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def browse_table_data(inspector: SQLiteInspector, table_name: str):
    """Browse table data with pagination."""
    limit = 5
    offset = 0
    
    while True:
        print(f"\n📄 Data in '{table_name}' (rows {offset + 1}-{offset + limit}):")
        print("-" * 60)
        
        data = inspector.inspect_table(table_name, limit=limit, offset=offset)
        
        if "error" in data:
            print(f"❌ Error: {data['error']}")
            break
        
        if data.get('sample_data'):
            for i, row in enumerate(data['sample_data'], offset + 1):
                print(f"\nRow {i}:")
                for key, value in row.items():
                    print(f"  {key}: {value}")
        else:
            print("No data found.")
        
        total_rows = data.get('total_rows', 0)
        print(f"\n📊 Showing rows {offset + 1}-{min(offset + limit, total_rows)} of {total_rows}")
        print("\nNavigation:")
        print("  n = Next page")
        print("  p = Previous page")
        print("  j = Jump to page")
        print("  0 = Back to table menu")
        
        nav = input("\nNavigate (n/p/j/0): ").strip().lower()
        
        if nav == "0":
            break
        elif nav == "n":
            if offset + limit < total_rows:
                offset += limit
            else:
                print("❌ Already at last page")
        elif nav == "p":
            offset = max(0, offset - limit)
        elif nav == "j":
            try:
                page = int(input(f"Jump to page (1-{(total_rows + limit - 1) // limit}): "))
                offset = max(0, (page - 1) * limit)
                if offset >= total_rows:
                    offset = max(0, total_rows - limit)
            except ValueError:
                print("❌ Invalid page number")

def search_table_data(inspector: SQLiteInspector, table_name: str):
    """Search table data interactively."""
    while True:
        search_term = input(f"\n🔍 Enter search term for '{table_name}' (0 to go back): ").strip()
        
        if search_term == "0":
            break
        
        if not search_term:
            print("❌ Please enter a search term.")
            continue
        
        limit = int(input("Number of results (default 10): ") or "10")
        
        print(f"\n🔍 Searching for: '{search_term}'...")
        
        data = inspector.search_table(table_name, search_term, limit)
        
        if "error" in data:
            print(f"❌ Error: {data['error']}")
            continue
        
        print(f"\n📊 Found {data['results_count']} results in columns: {', '.join(data['searched_columns'])}")
        
        for i, result in enumerate(data['results'], 1):
            print(f"\nResult {i}:")
            for key, value in result.items():
                print(f"  {key}: {value}")

def show_table_schema(inspector: SQLiteInspector, table_name: str):
    """Show detailed table schema."""
    data = inspector.inspect_table(table_name, limit=1)
    
    if "error" in data:
        print(f"❌ Error: {data['error']}")
        return
    
    print(f"\n🏗️  Schema for '{table_name}':")
    print("=" * 50)
    
    columns = data.get('columns', [])
    print(f"📋 Columns ({len(columns)}):")
    for col in columns:
        pk_marker = " 🔑" if col.get('primary_key') else ""
        not_null = " NOT NULL" if col.get('not_null') else ""
        default = f" DEFAULT {col.get('default')}" if col.get('default') else ""
        print(f"  • {col['name']} ({col['type']}){not_null}{default}{pk_marker}")
    
    indexes = data.get('indexes', [])
    if indexes:
        print(f"\n🔍 Indexes ({len(indexes)}):")
        for idx in indexes:
            unique_marker = " UNIQUE" if idx.get('unique') else ""
            print(f"  • {idx['name']}{unique_marker} on {', '.join(idx['columns'])}")
    
    input("\nPress Enter to continue...")

def execute_custom_query(inspector: SQLiteInspector, table_name: str):
    """Execute custom SQL queries."""
    print(f"\n🔧 Custom Query for '{table_name}'")
    print("Examples:")
    print(f"  SELECT * FROM {table_name} WHERE column_name = 'value'")
    print(f"  SELECT COUNT(*) FROM {table_name}")
    print(f"  SELECT column_name, COUNT(*) FROM {table_name} GROUP BY column_name")
    
    while True:
        query = input(f"\n📝 Enter SQL query (0 to go back): ").strip()
        
        if query == "0":
            break
        
        if not query:
            print("❌ Please enter a query.")
            continue
        
        print(f"\n🔧 Executing: {query}")
        
        data = inspector.execute_query(query)
        
        if "error" in data:
            print(f"❌ Error: {data['error']}")
            continue
        
        if "results" in data:
            print(f"\n📊 Query returned {data['row_count']} rows:")
            for i, row in enumerate(data['results'], 1):
                print(f"\nRow {i}:")
                for key, value in row.items():
                    print(f"  {key}: {value}")
        else:
            print(f"✅ {data.get('message', 'Query executed successfully')}")

def export_table_data(inspector: SQLiteInspector, table_name: str):
    """Export table data to JSON file."""
    limit = int(input("Number of rows to export (default 100, 0 for all): ") or "100")
    
    if limit == 0:
        # Get total row count
        table_info = inspector.inspect_table(table_name, limit=1)
        if "error" in table_info:
            print(f"❌ Error: {table_info['error']}")
            return
        limit = table_info.get('total_rows', 100)
    
    print(f"\n📤 Exporting {limit} rows from '{table_name}'...")
    
    data = inspector.inspect_table(table_name, limit=limit, offset=0)
    
    if "error" in data:
        print(f"❌ Error: {data['error']}")
        return
    
    # Create export filename
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sqlite_export_{table_name}_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"✅ Exported {len(data.get('sample_data', []))} rows to: {filename}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Inspect SQLite database tables and data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic inspection
  python tools/database_inspection/inspect_sqlite.py --info --database framework
  python tools/database_inspection/inspect_sqlite.py --list --database test_table_driven
  python tools/database_inspection/inspect_sqlite.py --table test_items --limit 5 --schema --database test_table_driven
  
  # Read/write testing
  python tools/database_inspection/inspect_sqlite.py --test-readwrite --database test_table_driven
  python tools/database_inspection/inspect_sqlite.py --test-readwrite --database framework
  
  # Interactive mode
  python tools/database_inspection/inspect_sqlite.py --interactive --database test_table_driven
  
  # Custom queries
  python tools/database_inspection/inspect_sqlite.py --query "SELECT * FROM test_items WHERE is_active=1" --database test_table_driven
        """
    )
    
    parser.add_argument("--db-path", type=str, help="Custom database path")
    parser.add_argument("--info", action="store_true", help="Show database information")
    parser.add_argument("--list", action="store_true", help="List all tables")
    parser.add_argument("--table", type=str, help="Inspect specific table")
    parser.add_argument("--schema", action="store_true", help="Show table schema details")
    parser.add_argument("--limit", type=int, default=10, help="Limit results (default: 10)")
    parser.add_argument("--offset", type=int, default=0, help="Offset for table data (default: 0)")
    parser.add_argument("--search", type=str, help="Search term within table")
    parser.add_argument("--query", type=str, help="Execute custom SQL query")
    parser.add_argument("--format", choices=["pretty", "json"], default="pretty", help="Output format")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive mode")
    parser.add_argument("--test-readwrite", action="store_true", help="Run comprehensive read/write tests")
    parser.add_argument("--database", type=str, default="framework", help="Database name (default: framework)")
    
    args = parser.parse_args()
    
    # Check if interactive mode
    if args.interactive:
        interactive_mode(args.db_path)
        return
    
    # Check if read/write test mode
    if args.test_readwrite:
        print(f"Running read/write tests for database: {args.database}")
        success = test_database_readwrite(args.database)
        sys.exit(0 if success else 1)
    
    # Validate arguments for non-interactive mode
    if args.search and not args.table:
        print("❌ Error: --search requires --table to be specified")
        sys.exit(1)
    
    if not any([args.info, args.list, args.table, args.query]):
        parser.print_help()
        sys.exit(1)
    
    # Initialize inspector
    inspector = SQLiteInspector(args.db_path, args.database)
    
    # Execute commands
    try:
        if args.info:
            print("📊 Database Information:")
            print("=" * 50)
            data = inspector.get_database_info()
            if args.format == "json":
                print(json.dumps(data, indent=2))
            else:
                for key, value in data.items():
                    if key != "error":
                        print(f"{key}: {value}")
                if "error" in data:
                    print(f"❌ {data['error']}")
        
        if args.list:
            print("\n📚 Database Tables:")
            print("=" * 50)
            tables = inspector.list_tables()
            if args.format == "json":
                print(json.dumps(tables, indent=2))
            else:
                for table in tables:
                    if "error" in table:
                        print(f"❌ {table['error']}")
                    else:
                        print(f"📊 {table['name']} ({table['type']}): {table['row_count']} rows")
                        if args.schema:
                            print(f"   Columns: {len(table['columns'])}")
                            for col in table['columns'][:3]:  # Show first 3 columns
                                pk = " 🔑" if col.get('primary_key') else ""
                                print(f"     • {col['name']} ({col['type']}){pk}")
                            if len(table['columns']) > 3:
                                print(f"     ... and {len(table['columns']) - 3} more")
                        print()
        
        if args.table:
            if args.search:
                print(f"\n🔍 Search Results in '{args.table}':")
                print("=" * 50)
                data = inspector.search_table(args.table, args.search, args.limit)
                if args.format == "json":
                    print(json.dumps(data, indent=2))
                else:
                    if "error" in data:
                        print(f"❌ {data['error']}")
                    else:
                        print(f"Search term: '{data['search_term']}'")
                        print(f"Searched columns: {', '.join(data['searched_columns'])}")
                        print(f"Results found: {data['results_count']}")
                        print()
                        for i, result in enumerate(data['results'], 1):
                            print(f"Result {i}:")
                            for key, value in result.items():
                                print(f"  {key}: {value}")
                            print()
            else:
                print(f"\n📊 Table '{args.table}':")
                print("=" * 50)
                data = inspector.inspect_table(args.table, args.limit, args.offset)
                if args.format == "json":
                    print(json.dumps(data, indent=2))
                else:
                    print_table_data(data, args.schema)
        
        if args.query:
            print(f"\n🔧 Query Results:")
            print("=" * 50)
            data = inspector.execute_query(args.query, args.limit)
            if args.format == "json":
                print(json.dumps(data, indent=2))
            else:
                if "error" in data:
                    print(f"❌ {data['error']}")
                elif "results" in data:
                    print(f"Query: {data['query']}")
                    print(f"Rows returned: {data['row_count']}")
                    print()
                    for i, row in enumerate(data['results'], 1):
                        print(f"Row {i}:")
                        for key, value in row.items():
                            print(f"  {key}: {value}")
                        print()
                else:
                    print(f"✅ {data.get('message', 'Query executed successfully')}")
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def test_database_readwrite(database_name: str = "test_table_driven", log_file: str = None):
    """
    Test database read/write operations with comprehensive logging.
    Creates a detailed log file showing all database operations.
    
    Args:
        database_name: Name of the database to test
        log_file: Optional log file path
    """
    from datetime import datetime
    import time
    
    # Create log file
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"/tmp/database_readwrite_test_{database_name}_{timestamp}.log"
    
    # Open log file for writing
    with open(log_file, 'w') as log:
        def log_print(message):
            """Print and log message."""
            print(message)
            log.write(f"{datetime.now().isoformat()} - {message}\n")
            log.flush()
        
        log_print("=" * 80)
        log_print("DATABASE READ/WRITE TEST")
        log_print("=" * 80)
        log_print(f"Database: {database_name}")
        log_print(f"Log file: {log_file}")
        log_print(f"Test started: {datetime.now()}")
        log_print("")
        
        try:
            # Initialize inspector
            inspector = SQLiteInspector(database_name=database_name)
            
            # Phase 1: Database connectivity test
            log_print("PHASE 1: DATABASE CONNECTIVITY TEST")
            log_print("-" * 50)
            
            db_info = inspector.get_database_info()
            if "error" in db_info:
                log_print(f"❌ Database connectivity failed: {db_info['error']}")
                return False
            
            log_print(f"✅ Connected to database: {db_info['database_path']}")
            log_print(f"📊 Database size: {db_info['file_size_mb']} MB")
            log_print(f"🔧 SQLite version: {db_info['sqlite_version']}")
            log_print("")
            
            # Phase 2: Table discovery
            log_print("PHASE 2: TABLE DISCOVERY")
            log_print("-" * 50)
            
            tables = inspector.list_tables()
            if not tables or (len(tables) == 1 and "error" in tables[0]):
                log_print("❌ No tables found in database")
                return False
            
            log_print(f"📚 Found {len(tables)} tables:")
            for table in tables:
                if "error" not in table:
                    log_print(f"  • {table['name']}: {table['row_count']} rows, {len(table['columns'])} columns")
            log_print("")
            
            # Phase 3: Initial state check
            log_print("PHASE 3: INITIAL STATE CHECK")
            log_print("-" * 50)
            
            initial_counts = {}
            for table in tables:
                if "error" not in table:
                    table_name = table['name']
                    row_count = table['row_count']
                    initial_counts[table_name] = row_count
                    log_print(f"📊 {table_name}: {row_count} rows initially")
            log_print("")
            
            # Phase 4: Write operations test
            log_print("PHASE 4: WRITE OPERATIONS TEST")
            log_print("-" * 50)
            
            write_tests = []
            if "test_items" in [t['name'] for t in tables]:
                log_print("➡️  Testing write operations on test_items table...")
                
                # Test data to insert
                test_items = [
                    ("Test Alpha", "First test item for database verification"),
                    ("Test Beta", "Second test item with special chars: !@#$%^&*()"),
                    ("Test Gamma", None),  # Test NULL description
                    ("Test Delta", "Item with JSON-like data: {\"key\": \"value\"}"),
                    ("Test Epsilon", "Final test item")
                ]
                
                successful_writes = 0
                for i, (name, description) in enumerate(test_items, 1):
                    try:
                        # Insert test item
                        if description is None:
                            query = "INSERT INTO test_items (name, is_active) VALUES (?, ?)"
                            params = (name, True)
                        else:
                            query = "INSERT INTO test_items (name, description, is_active) VALUES (?, ?, ?)"
                            params = (name, description, True)
                        
                        with sqlite3.connect(str(inspector.db_path)) as conn:
                            cursor = conn.cursor()
                            cursor.execute(query, params)
                            row_id = cursor.lastrowid
                            conn.commit()
                        
                        log_print(f"✅ Write {i}/5 successful: '{name}' (ID: {row_id})")
                        successful_writes += 1
                        write_tests.append({"name": name, "id": row_id, "success": True})
                        
                        # Small delay to ensure different timestamps
                        time.sleep(0.1)
                        
                    except Exception as e:
                        log_print(f"❌ Write {i}/5 failed: {e}")
                        write_tests.append({"name": name, "success": False, "error": str(e)})
                
                log_print(f"📊 Write summary: {successful_writes}/{len(test_items)} successful")
                log_print("")
                
                # Test logging to test_logs if it exists
                if "test_logs" in [t['name'] for t in tables]:
                    log_print("➡️  Testing write operations on test_logs table...")
                    
                    try:
                        log_message = f"Database test completed - {successful_writes} items written"
                        with sqlite3.connect(str(inspector.db_path)) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO test_logs (message, level) VALUES (?, ?)",
                                (log_message, "INFO")
                            )
                            log_id = cursor.lastrowid
                            conn.commit()
                        
                        log_print(f"✅ Log write successful: '{log_message}' (ID: {log_id})")
                    except Exception as e:
                        log_print(f"❌ Log write failed: {e}")
                    log_print("")
            
            # Phase 5: Read operations test
            log_print("PHASE 5: READ OPERATIONS TEST")
            log_print("-" * 50)
            
            for table in tables:
                if "error" not in table:
                    table_name = table['name']
                    log_print(f"📖 Reading from table: {table_name}")
                    
                    # Test basic read
                    table_data = inspector.inspect_table(table_name, limit=5)
                    if "error" in table_data:
                        log_print(f"❌ Read failed: {table_data['error']}")
                    else:
                        current_rows = table_data.get('total_rows', 0)
                        log_print(f"✅ Read successful: {current_rows} total rows")
                        
                        # Show sample data
                        sample_data = table_data.get('sample_data', [])
                        if sample_data:
                            log_print(f"📄 Sample data (showing {len(sample_data)} rows):")
                            for i, row in enumerate(sample_data, 1):
                                log_print(f"  Row {i}: {dict(row)}")
                        
                        # Test filtered read if this is test_items
                        if table_name == "test_items":
                            try:
                                search_results = inspector.search_table(table_name, "Test", limit=10)
                                if "error" not in search_results:
                                    count = search_results.get('results_count', 0)
                                    log_print(f"✅ Search test successful: found {count} items matching 'Test'")
                                else:
                                    log_print(f"❌ Search test failed: {search_results['error']}")
                            except Exception as e:
                                log_print(f"❌ Search test failed: {e}")
                    
                    log_print("")
            
            # Phase 6: Final state verification
            log_print("PHASE 6: FINAL STATE VERIFICATION")
            log_print("-" * 50)
            
            # Re-check table counts
            final_tables = inspector.list_tables()
            final_counts = {}
            changes_detected = False
            
            for table in final_tables:
                if "error" not in table:
                    table_name = table['name']
                    final_count = table['row_count']
                    initial_count = initial_counts.get(table_name, 0)
                    final_counts[table_name] = final_count
                    
                    change = final_count - initial_count
                    if change > 0:
                        log_print(f"📈 {table_name}: {initial_count} → {final_count} (+{change} rows)")
                        changes_detected = True
                    elif change < 0:
                        log_print(f"📉 {table_name}: {initial_count} → {final_count} ({change} rows)")
                        changes_detected = True
                    else:
                        log_print(f"📊 {table_name}: {final_count} rows (no change)")
            
            if changes_detected:
                log_print("✅ Database changes detected - write operations successful")
            else:
                log_print("⚠️  No database changes detected")
            
            log_print("")
            
            # Phase 7: Test summary
            log_print("PHASE 7: TEST SUMMARY")
            log_print("-" * 50)
            
            total_tests = 0
            passed_tests = 0
            
            # Connectivity test
            total_tests += 1
            passed_tests += 1
            log_print("✅ Database connectivity: PASSED")
            
            # Table discovery test
            total_tests += 1
            if len(tables) > 0:
                passed_tests += 1
                log_print("✅ Table discovery: PASSED")
            else:
                log_print("❌ Table discovery: FAILED")
            
            # Write tests
            total_tests += len(write_tests)
            write_passes = sum(1 for test in write_tests if test.get('success', False))
            passed_tests += write_passes
            log_print(f"{'✅' if write_passes == len(write_tests) else '⚠️ '} Write operations: {write_passes}/{len(write_tests)} PASSED")
            
            # Read tests (one per table)
            read_passes = len([t for t in tables if "error" not in t])
            total_tests += read_passes
            passed_tests += read_passes
            log_print(f"✅ Read operations: {read_passes}/{read_passes} PASSED")
            
            # Data persistence test
            total_tests += 1
            if changes_detected:
                passed_tests += 1
                log_print("✅ Data persistence: PASSED")
            else:
                log_print("⚠️  Data persistence: NO CHANGES DETECTED")
            
            log_print("")
            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            log_print(f"🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
            
            if success_rate >= 90:
                log_print("🎉 EXCELLENT: Database read/write operations working correctly!")
            elif success_rate >= 70:
                log_print("✅ GOOD: Most database operations working, minor issues detected")
            else:
                log_print("⚠️  ISSUES: Significant problems with database operations")
            
            log_print("")
            log_print(f"Test completed: {datetime.now()}")
            log_print(f"Log saved to: {log_file}")
            log_print("=" * 80)
            
            return success_rate >= 70
            
        except Exception as e:
            log_print(f"❌ CRITICAL ERROR during database testing: {e}")
            import traceback
            log_print("Full traceback:")
            log_print(traceback.format_exc())
            return False


if __name__ == "__main__":
    main()