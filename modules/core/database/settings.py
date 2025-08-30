"""
modules/core/database/settings.py
Pydantic settings model for core.database module.

Database configuration including connection settings, connection pool management,
and SQLite-specific optimizations for the modular framework.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from enum import Enum


class SQLiteJournalMode(str, Enum):
    """SQLite journal mode options."""
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    PERSIST = "PERSIST"
    MEMORY = "MEMORY"
    WAL = "WAL"
    OFF = "OFF"


class SQLiteSynchronousMode(str, Enum):
    """SQLite synchronous mode options."""
    OFF = "OFF"
    NORMAL = "NORMAL"
    FULL = "FULL"
    EXTRA = "EXTRA"


class DatabaseSettings(BaseModel):
    """
    Pydantic settings model for core.database with full validation.
    
    Manages database connection settings, connection pool configuration,
    retry behavior, and SQLite-specific performance optimizations.
    """
    
    model_config = ConfigDict(
        env_prefix="CORE_DATABASE_",
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "title": "Database Settings",
            "description": "Core database configuration and connection management"
        }
    )
    
    # Connection Settings
    database_url: str = Field(
        default="",
        description="Database connection URL (set during installation)",
        json_schema_extra={
            "ui_component": "text",
            "ui_category": "Connection",
            "ui_readonly": True,
            "ui_help": "Database connection URL is configured during framework installation"
        }
    )
    
    connection_timeout: int = Field(
        default=30,
        ge=1,
        le=3600,
        description="Connection timeout in seconds",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Connection",
            "ui_help": "Maximum time to wait when establishing a database connection"
        }
    )
    
    # Retry Configuration
    max_retries: int = Field(
        default=5,
        ge=0,
        le=100,
        description="Maximum number of retry attempts for database operations",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Retry Settings",
            "ui_help": "Number of times to retry failed database operations before giving up"
        }
    )
    
    retry_delay_base: float = Field(
        default=0.1,
        gt=0.0,
        le=10.0,
        description="Base delay between retries in seconds",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Retry Settings",
            "ui_help": "Initial delay before first retry attempt (increases exponentially)"
        }
    )
    
    retry_delay_max: float = Field(
        default=2.0,
        gt=0.0,
        le=60.0,
        description="Maximum delay between retries in seconds",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Retry Settings", 
            "ui_help": "Maximum time to wait between retry attempts"
        }
    )
    
    # Connection Pool Configuration
    pool_size: int = Field(
        default=20,
        ge=1,
        le=1000,
        description="Number of persistent connections to maintain in the pool",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Connection Pool",
            "ui_help": "Base number of database connections kept open for reuse"
        }
    )
    
    pool_overflow: int = Field(
        default=10,
        ge=0,
        le=1000,
        description="Additional connections beyond pool_size when needed",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Connection Pool",
            "ui_help": "Extra connections created temporarily under high load"
        }
    )
    
    pool_timeout: int = Field(
        default=30,
        ge=1,
        le=3600,
        description="Seconds to wait before timing out when getting a connection",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Connection Pool",
            "ui_help": "Maximum time to wait for an available connection from the pool"
        }
    )
    
    pool_recycle: int = Field(
        default=3600,
        ge=1,
        le=86400,
        description="Seconds after which a connection is recycled",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Connection Pool",
            "ui_help": "How long to keep connections before recreating them (prevents stale connections)"
        }
    )
    
    # SQLite-Specific Performance Settings
    sqlite_journal_mode: SQLiteJournalMode = Field(
        default=SQLiteJournalMode.WAL,
        description="SQLite journal mode for transaction handling",
        json_schema_extra={
            "ui_component": "select",
            "ui_category": "SQLite Settings",
            "ui_help": "WAL (Write-Ahead Logging) recommended for concurrent access and performance"
        }
    )
    
    sqlite_synchronous: SQLiteSynchronousMode = Field(
        default=SQLiteSynchronousMode.NORMAL,
        description="SQLite synchronous setting balancing safety and performance",
        json_schema_extra={
            "ui_component": "select", 
            "ui_category": "SQLite Settings",
            "ui_help": "NORMAL provides good balance of data safety and write performance"
        }
    )
    
    sqlite_cache_size: int = Field(
        default=10000,
        ge=100,
        le=1000000,
        description="SQLite cache size in database pages",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "SQLite Settings",
            "ui_help": "Higher values improve read performance but use more memory"
        }
    )
    
    sqlite_foreign_keys: bool = Field(
        default=True,
        description="Enable SQLite foreign key constraint enforcement",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "SQLite Settings",
            "ui_help": "Enforces referential integrity between related tables"
        }
    )
    
    sqlite_busy_timeout: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="SQLite busy timeout in milliseconds",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "SQLite Settings",
            "ui_help": "How long to wait for locks before timing out (higher values reduce contention errors)"
        }
    )
    
    def get_sqlite_pragmas(self) -> list[str]:
        """
        Generate SQLite PRAGMA statements from current settings.
        
        Returns:
            List of SQL PRAGMA statements for database optimization
        """
        return [
            f"PRAGMA journal_mode={self.sqlite_journal_mode}",
            f"PRAGMA synchronous={self.sqlite_synchronous}",
            f"PRAGMA cache_size={self.sqlite_cache_size}",
            f"PRAGMA foreign_keys={'ON' if self.sqlite_foreign_keys else 'OFF'}",
            f"PRAGMA busy_timeout={self.sqlite_busy_timeout}"
        ]
    
    def get_connection_params(self) -> dict:
        """
        Get connection parameters for SQLAlchemy engine creation.
        
        Returns:
            Dictionary of connection parameters
        """
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.pool_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": True,  # Validate connections before use
        }
    
    def get_retry_config(self) -> dict:
        """
        Get retry configuration for database operations.
        
        Returns:
            Dictionary of retry parameters
        """
        return {
            "max_retries": self.max_retries,
            "retry_delay_base": self.retry_delay_base,
            "retry_delay_max": self.retry_delay_max,
            "connection_timeout": self.connection_timeout
        }