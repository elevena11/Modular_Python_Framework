"""
Database models for core.global module
Reserved for future global framework tables.
"""

# Database configuration for file-based discovery
DATABASE_NAME = "framework"

from core.database import DatabaseBase

# AI PATTERN: Table-driven database creation
# 1. Get database-specific base: GlobalBase = DatabaseBase("framework") 
# 2. Inherit from base: class MyTable(GlobalBase)
# 3. Framework automatically discovers and creates database
GlobalBase = DatabaseBase("framework")

# No tables currently defined - legacy tables removed
# This module is reserved for future global framework functionality