"""
Pydantic schemas for validating API requests and responses.
These schemas correspond to the database models but are separate to allow for API validation.
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


# Additional request/response schemas for specific operations

class FileWriteRequest(BaseModel):
    """Request schema for writing a file."""
    path: str = Field(..., description="Path to write (relative to allowed directories)")
    content: str = Field(..., description="Content to write to the file")
    create_dirs: bool = Field(True, description="Whether to create parent directories if they don't exist")


class FileReadResponse(BaseModel):
    """Response schema for reading a file."""
    success: bool = Field(..., description="Whether the operation was successful")
    path: str = Field(..., description="Path of the file")
    content: str = Field(..., description="Content of the file")


class ProcessOutputResponse(BaseModel):
    """Response schema for process output."""
    id: str = Field(..., description="Process ID")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    complete: bool = Field(..., description="Whether the process has completed")


class ModuleListResponse(BaseModel):
    """Response schema for listing modules."""
    modules: List[ModuleResponse] = Field(..., description="List of modules")
    count: int = Field(..., description="Total number of modules")


class TerminalOutputRequest(BaseModel):
    """Request schema for appending output to a terminal session."""
    output: str = Field(..., description="Text output to append to the terminal session")


class OperationResponse(BaseModel):
    """Generic response schema for operations."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(None, description="Operation message")
    error: Optional[str] = Field(None, description="Error message if operation failed")
