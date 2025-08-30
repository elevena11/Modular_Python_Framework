"""
modules/core/database/api_schemas.py
Updated: March 22, 2025
Pydantic schemas for API request and response validation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# Module schemas
class ModuleBase(BaseModel):
    """Base schema for module data."""
    module_id: str = Field(..., description="Unique module identifier (e.g., 'core.database')")
    name: str = Field(..., description="Human-readable module name")
    version: str = Field(..., description="Module version (semver format)")
    description: Optional[str] = Field(None, description="Module description")
    enabled: bool = Field(True, description="Whether the module is enabled")


class ModuleCreate(ModuleBase):
    """Schema for creating a new module."""
    pass


class ModuleResponse(ModuleBase):
    """Schema for module response data."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Module setting schemas
class ModuleSettingBase(BaseModel):
    """Base schema for module setting data."""
    module_id: int = Field(..., description="ID of the module this setting belongs to")
    key: str = Field(..., description="Setting key")
    value: str = Field(..., description="Setting value as string")
    value_type: str = Field(..., description="Data type of the value ('string', 'integer', 'float', 'boolean', 'json')")
    description: Optional[str] = Field(None, description="Setting description")


class ModuleSettingCreate(ModuleSettingBase):
    """Schema for creating a new module setting."""
    pass


class ModuleSettingResponse(ModuleSettingBase):
    """Schema for module setting response data."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Module log schemas
class ModuleLogBase(BaseModel):
    """Base schema for module log data."""
    module_id: int = Field(..., description="ID of the module this log belongs to")
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR, etc.)")
    message: str = Field(..., description="Log message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional log details")


class ModuleLogCreate(ModuleLogBase):
    """Schema for creating a new module log."""
    pass


class ModuleLogResponse(ModuleLogBase):
    """Schema for module log response data."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# File schemas
class FileBase(BaseModel):
    """Base schema for file data."""
    path: str = Field(..., description="File path relative to allowed directories")
    content_type: Optional[str] = Field(None, description="File content type/MIME type")
    size: int = Field(0, description="File size in bytes")
    created_by: Optional[str] = Field(None, description="Entity that created the file")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional file metadata")


class FileCreate(FileBase):
    """Schema for creating a new file record."""
    pass


class FileResponse(FileBase):
    """Schema for file response data."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Process schemas
class ProcessBase(BaseModel):
    """Base schema for process data."""
    process_uuid: str = Field(..., description="Unique process identifier")
    command: str = Field(..., description="Command that was executed")
    status: str = Field(..., description="Process status (running, completed, error, timeout, terminated)")
    exit_code: Optional[int] = Field(None, description="Process exit code")
    working_dir: str = Field(..., description="Working directory where the process was executed")
    created_by: Optional[str] = Field(None, description="Entity that created the process")


class ProcessCreate(ProcessBase):
    """Schema for creating a new process record."""
    pass


class ProcessResponse(ProcessBase):
    """Schema for process response data."""
    id: int
    stdout: Optional[str] = Field(None, description="Standard output")
    stderr: Optional[str] = Field(None, description="Standard error")
    started_at: datetime = Field(..., description="When the process started")
    ended_at: Optional[datetime] = Field(None, description="When the process ended")

    class Config:
        from_attributes = True


# Process request schema (separate from database model)
class ProcessRequest(BaseModel):
    """Schema for process execution requests."""
    command: str = Field(..., description="Command to execute")
    working_dir: str = Field(".", description="Working directory")
    env_vars: Optional[Dict[str, str]] = Field({}, description="Environment variables")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")


# System status schemas
class SystemStatusBase(BaseModel):
    """Base schema for system status data."""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_percent: float = Field(..., description="Disk usage percentage")
    uptime_seconds: int = Field(..., description="System uptime in seconds")
    active_process_count: int = Field(..., description="Number of active processes")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional system details")


class SystemStatusCreate(SystemStatusBase):
    """Schema for creating a new system status record."""
    pass


class SystemStatusResponse(SystemStatusBase):
    """Schema for system status response data."""
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# Terminal session schemas
class TerminalSessionBase(BaseModel):
    """Base schema for terminal session data."""
    session_uuid: str = Field(..., description="Unique session identifier")
    name: str = Field(..., description="Session name")
    created_by: Optional[str] = Field(None, description="Entity that created the session")


class TerminalSessionCreate(TerminalSessionBase):
    """Schema for creating a new terminal session."""
    pass


class TerminalSessionResponse(TerminalSessionBase):
    """Schema for terminal session response data."""
    id: int
    created_at: datetime
    last_activity: datetime
    content: Optional[str] = Field(None, description="Terminal session content")

    class Config:
        from_attributes = True


# Database API response schemas
class DatabaseStatusResponse(BaseModel):
    """Response schema for database status endpoint."""
    status: str = Field(..., description="Database connection status")
    engine: str = Field(..., description="Database engine URL (redacted)")
    initialization: Dict[str, Any] = Field(..., description="Initialization status details")
    tables: Optional[List[str]] = Field(None, description="List of tables in the database")
    table_count: Optional[int] = Field(None, description="Number of tables in the database")
    tables_error: Optional[str] = Field(None, description="Error message if tables couldn't be retrieved")


class DatabaseReadyResponse(BaseModel):
    """Response schema for database ready check endpoint."""
    ready: bool = Field(..., description="Whether database is ready for use")
    status: str = Field(..., description="Status description (ready/initializing)")


class MigrationStatusResponse(BaseModel):
    """Response schema for migration status endpoint."""
    current_revision: Optional[str] = Field(None, description="Current migration revision")
    head_revision: Optional[str] = Field(None, description="Latest available revision")
    up_to_date: bool = Field(..., description="Whether database is up-to-date with migrations")
    available_revisions: List[Dict[str, Any]] = Field(..., description="List of available revisions")
    error: Optional[str] = Field(None, description="Error message if status check failed")


class MigrationGenerateRequest(BaseModel):
    """Request schema for generating a migration."""
    message: str = Field(..., description="Description of what the migration does")


class MigrationGenerateResponse(BaseModel):
    """Response schema for migration generation."""
    success: bool = Field(..., description="Whether the migration was successfully generated")
    migration_path: Optional[str] = Field(None, description="Path to the generated migration script")
    error: Optional[str] = Field(None, description="Error message if generation failed")


class MigrationRunRequest(BaseModel):
    """Request schema for running migrations."""
    target: str = Field("head", description="Target revision (default: head)")


class MigrationRunResponse(BaseModel):
    """Response schema for running migrations."""
    success: bool = Field(..., description="Whether migrations were successfully run")


class MigrationDowngradeRequest(BaseModel):
    """Request schema for downgrading migrations."""
    target: str = Field(..., description="Target revision to downgrade to")


class MigrationDowngradeResponse(BaseModel):
    """Response schema for downgrading migrations."""
    success: bool = Field(..., description="Whether downgrade was successful")


class TableDataRequest(BaseModel):
    """Request schema for getting table data."""
    page: int = Field(1, description="Page number")
    page_size: int = Field(50, description="Number of records per page")
    sort_by: Optional[str] = Field(None, description="Column to sort by")
    sort_desc: bool = Field(False, description="Sort in descending order")
    filter_column: Optional[str] = Field(None, description="Column to filter by")
    filter_value: Optional[str] = Field(None, description="Value to filter for")


class TableDataResponse(BaseModel):
    """Response schema for table data."""
    success: bool = Field(..., description="Whether the operation was successful")
    table: str = Field(..., description="Table name")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Records per page")
    total_records: int = Field(..., description="Total number of records")
    total_pages: int = Field(..., description="Total number of pages")
    records: List[Dict[str, Any]] = Field(..., description="Table records")


class TableSchemaResponse(BaseModel):
    """Response schema for table schema."""
    success: bool = Field(..., description="Whether the operation was successful")
    table: str = Field(..., description="Table name")
    schema_definition: Dict[str, Any] = Field(..., description="Table schema information")


class TablesListResponse(BaseModel):
    """Response schema for listing tables."""
    success: bool = Field(..., description="Whether the operation was successful")
    tables: List[str] = Field(..., description="List of tables in the database")


class ErrorResponse(BaseModel):
    """Standard error response."""
    status: str = Field("error", description="Error status marker")
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
