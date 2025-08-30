"""
modules/core/database/ui/ui_streamlit.py
Streamlit UI component for database viewing and management with SQLite support.
"""

import streamlit as st
import logging
import json
import pandas as pd
import traceback
from typing import Dict, List, Any

from modules.core.database.ui.services import DatabaseService

logger = logging.getLogger("modules.core.database.ui.streamlit")

def render_database_viewer(ui_context):
    """
    Render the Database Viewer UI components for Streamlit.
    
    Args:
        ui_context: UI context object
    """
    st.header("🗃️ Database Viewer")
    st.markdown("Browse multiple SQLite databases and their tables.")
    
    # Initialize session state
    if 'db_current_page' not in st.session_state:
        st.session_state.db_current_page = 1
    if 'db_selected_database' not in st.session_state:
        st.session_state.db_selected_database = None
    if 'db_selected_table' not in st.session_state:
        st.session_state.db_selected_table = None
    if 'db_filter_column' not in st.session_state:
        st.session_state.db_filter_column = None
    if 'db_filter_value' not in st.session_state:
        st.session_state.db_filter_value = ""
    if 'db_raw_data' not in st.session_state:
        st.session_state.db_raw_data = []
    
    # Database selection section
    st.subheader("Database Selection")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Get available databases
        databases = DatabaseService.get_databases()
        if databases:
            selected_database = st.selectbox(
                "Select Database:",
                options=[""] + sorted(databases),
                index=0 if not st.session_state.db_selected_database else 
                      (sorted(databases).index(st.session_state.db_selected_database) + 1 if st.session_state.db_selected_database in databases else 0),
                key="database_selector"
            )
            
            if selected_database and selected_database != st.session_state.db_selected_database:
                st.session_state.db_selected_database = selected_database
                st.session_state.db_selected_table = None  # Reset table selection
                st.session_state.db_current_page = 1
                st.session_state.db_filter_column = None
                st.session_state.db_filter_value = ""
                st.rerun()
        else:
            st.warning("No databases found.")
            return
    
    with col2:
        if st.button("🔄 Refresh Databases", use_container_width=True):
            st.rerun()
    
    if not st.session_state.db_selected_database:
        st.info("Please select a database to view its tables.")
        return
    
    # Table selection section
    st.subheader("Table Selection")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Get tables for selected database
        tables = DatabaseService.get_tables(st.session_state.db_selected_database)
        if tables:
            selected_table = st.selectbox(
                "Select Table:",
                options=[""] + sorted(tables),
                index=0 if not st.session_state.db_selected_table else 
                      (sorted(tables).index(st.session_state.db_selected_table) + 1 if st.session_state.db_selected_table in tables else 0),
                key="table_selector"
            )
            
            if selected_table and selected_table != st.session_state.db_selected_table:
                st.session_state.db_selected_table = selected_table
                st.session_state.db_current_page = 1
                st.session_state.db_filter_column = None
                st.session_state.db_filter_value = ""
                st.rerun()
        else:
            st.warning(f"No tables found in database '{st.session_state.db_selected_database}'.")
            return
    
    with col2:
        if st.button("🔄 Refresh Tables", use_container_width=True):
            st.rerun()
    
    if not st.session_state.db_selected_table:
        st.info("Please select a table to view its data.")
        return
    
    # Filtering section
    st.subheader("Filters")
    
    # Get schema for filter column options
    schema = DatabaseService.get_table_schema(st.session_state.db_selected_database, st.session_state.db_selected_table)
    column_names = []
    if "columns" in schema:
        column_names = [col["name"] for col in schema["columns"]]
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        filter_column = st.selectbox(
            "Filter Column:",
            options=[""] + column_names,
            index=0,
            key="filter_column_selector"
        )
    
    with col2:
        filter_value = st.text_input(
            "Filter Value:",
            value="",
            key="filter_value_input"
        )
    
    with col3:
        st.write("")  # Spacing
        apply_filter = st.button("Apply Filter", use_container_width=True)
    
    # Handle filter application
    if apply_filter or (filter_column != st.session_state.db_filter_column) or (filter_value != st.session_state.db_filter_value):
        st.session_state.db_filter_column = filter_column if filter_column else None
        st.session_state.db_filter_value = filter_value
        st.session_state.db_current_page = 1
    
    # Load and display data
    try:
        data, total = DatabaseService.get_table_data(
            st.session_state.db_selected_database,
            st.session_state.db_selected_table,
            page=st.session_state.db_current_page,
            page_size=50,
            filter_column=st.session_state.db_filter_column,
            filter_value=st.session_state.db_filter_value if st.session_state.db_filter_value else None
        )
        
        st.session_state.db_raw_data = data
        
        if not data:
            st.info("No data found for the selected table and filters.")
            return
        
        # Display table data
        st.subheader(f"Table Data - {st.session_state.db_selected_table}")
        
        # Prepare data for display
        display_data = []
        for i, row in enumerate(data):
            display_row = {"Row #": i + 1}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    display_row[key] = "[Complex Data]"
                else:
                    display_row[key] = value if value is not None else ""
            display_data.append(display_row)
        
        # Create DataFrame and display
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, height=400)
        
        # Pagination
        page_size = 50
        total_pages = max(1, (total + page_size - 1) // page_size)
        
        st.subheader("Navigation")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Previous", disabled=(st.session_state.db_current_page <= 1)):
                st.session_state.db_current_page = max(1, st.session_state.db_current_page - 1)
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.db_current_page} of {total_pages} ({total} records)")
        
        with col3:
            if st.button("Next ➡️", disabled=(st.session_state.db_current_page >= total_pages)):
                st.session_state.db_current_page = min(total_pages, st.session_state.db_current_page + 1)
                st.rerun()
        
        # Row details section
        st.subheader("Row Details")
        selected_row_num = st.number_input(
            "Select Row Number:",
            min_value=1,
            max_value=len(data),
            value=1,
            step=1,
            key="row_number_selector"
        )
        
        if st.button("View Details"):
            row_details = get_row_details(selected_row_num, st.session_state.db_raw_data)
            st.text_area(
                "Selected Row Details:",
                value=row_details,
                height=200,
                key="row_details_display"
            )
        
        # Table schema section
        with st.expander("📋 Table Schema", expanded=False):
            if "columns" in schema:
                schema_data = []
                for col in schema["columns"]:
                    schema_data.append({
                        "Column": col["name"],
                        "Type": col["type"],
                        "Nullable": "YES" if col.get("nullable", False) else "NO",
                        "Primary Key": "YES" if col.get("primary_key", False) else "NO"
                    })
                
                schema_df = pd.DataFrame(schema_data)
                st.dataframe(schema_df, use_container_width=True)
            else:
                st.info("No schema information available.")
        
        # Custom SQL query section
        with st.expander("🔍 Custom SQL Query", expanded=False):
            st.warning("⚠️ Use with caution. Incorrect queries can affect database integrity.")
            
            sql_query = st.text_area(
                "SQL Query:",
                placeholder="Enter SQL query here...",
                height=100,
                key="sql_query_input"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                is_write_query = st.checkbox(
                    "Modifies data",
                    value=False,
                    help="Check if query performs INSERT, UPDATE, DELETE, etc."
                )
            
            with col2:
                if st.button("Run Query", type="primary"):
                    if sql_query.strip():
                        query_result = execute_custom_query(sql_query, is_write_query)
                        
                        if query_result["success"]:
                            if "rows" in query_result:
                                st.success(f"Query executed successfully. Returned {query_result['row_count']} rows.")
                                if query_result["rows"]:
                                    result_df = pd.DataFrame(query_result["rows"])
                                    st.dataframe(result_df, use_container_width=True)
                                else:
                                    st.info("Query returned no results.")
                            else:
                                st.success(query_result["message"])
                        else:
                            st.error(f"Query error: {query_result['error']}")
                    else:
                        st.warning("Please enter a query.")
        
    except Exception as e:
        logger.error(f"Error loading table data: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error loading table data: {str(e)}")

def get_row_details(row_num: int, raw_data: List[Dict[str, Any]]) -> str:
    """
    Get detailed view of a specific row.
    
    Args:
        row_num: Row number (1-based)
        raw_data: List of raw row dictionaries
        
    Returns:
        Formatted string with row details
    """
    try:
        if not raw_data:
            return "No data available for this table"
        
        # Adjust for 0-based indexing
        row_index = int(row_num) - 1
        
        # Check if index is valid
        if row_index < 0 or row_index >= len(raw_data):
            return f"Invalid row number. Please enter a number between 1 and {len(raw_data)}"
        
        # Get the raw row data
        row_data = raw_data[row_index]
        
        # Format as a readable string
        formatted_details = []
        for key, value in row_data.items():
            # Try to parse JSON strings for better display
            if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    parsed_value = json.loads(value)
                    formatted_value = json.dumps(parsed_value, indent=2)
                    formatted_details.append(f"{key}:\n{formatted_value}")
                except:
                    # If parsing fails, just use the raw string
                    formatted_details.append(f"{key}: {value}")
            else:
                formatted_details.append(f"{key}: {value if value is not None else 'NULL'}")
        
        return "\n\n".join(formatted_details)
    except Exception as e:
        logger.error(f"Error getting row details: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error retrieving row details: {str(e)}"

def execute_custom_query(query: str, is_write: bool = False) -> Dict[str, Any]:
    """
    Execute a custom SQL query.
    
    Args:
        query: SQL query string
        is_write: Whether the query modifies data
        
    Returns:
        Dictionary with query results or error information
    """
    if not query.strip():
        return {"success": False, "error": "No query entered"}
    
    try:
        result = DatabaseService.execute_custom_query(query, is_write=is_write)
        return result
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

# Register UI components
def register_components(ui_context):
    """
    Register UI components for the database module in Streamlit.
    
    Args:
        ui_context: UI context object
    """
    logger.info("Registering Database Viewer Streamlit UI components")
    
    # Get the module ID from the context if available
    module_id = getattr(ui_context, 'module_id', 'core.database')
    
    # Register the Database Viewer tab
    ui_context.register_element({
        "type": "tab",
        "id": "database_viewer",
        "display_name": "Database Viewer",
        "description": "View and manage database tables and records",
        "priority": 10,
        "render_function": render_database_viewer
    })
    
    logger.info("Database Viewer Streamlit UI components registered")