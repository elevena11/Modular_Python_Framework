"""
modules/core/scheduler/api_schemas.py
Updated: April 6, 2025
API schemas for scheduler module using Pydantic v2 compatible format
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Module identity - not required for error handling but added for consistency
MODULE_ID = "core.scheduler"

class EventResponse(BaseModel):
    """Schema for a scheduled event response."""
    id: str = Field(..., description="Unique identifier for the event")
    name: str = Field(..., description="Name of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    module_id: str = Field(..., description="ID of the module that registered the event")
    function_name: str = Field(..., description="Name of the function to execute")
    status: str = Field(..., description="Current status of the event (pending, running, completed, failed, paused)")
    recurring: bool = Field(..., description="Whether this is a recurring event")
    interval_type: Optional[str] = Field(None, description="For recurring events: minutes, hours, days, weeks, months, cron")
    interval_value: Optional[int] = Field(None, description="For recurring events: number of interval units (not used for cron)")
    next_execution: datetime = Field(..., description="When the event will next execute")
    last_execution: Optional[datetime] = Field(None, description="When the event was last executed")
    execution_count: int = Field(..., description="Number of times the event has executed")
    created_at: datetime = Field(..., description="When the event was created")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Daily Backup",
                "description": "Daily database backup at 3 AM",
                "module_id": "core.database",
                "function_name": "backup_database",
                "status": "pending",
                "recurring": True,
                "interval_type": "days",
                "interval_value": 1,
                "next_execution": "2025-03-31T03:00:00",
                "last_execution": "2025-03-30T03:00:00",
                "execution_count": 30,
                "created_at": "2025-03-01T00:00:00"
            }
        }
    }

class EventListResponse(BaseModel):
    """Schema for list of events response."""
    events: List[EventResponse] = Field(..., description="List of scheduled events")
    count: int = Field(..., description="Total number of events returned")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "events": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "Daily Backup",
                        "description": "Daily database backup at 3 AM",
                        "module_id": "core.database",
                        "function_name": "backup_database",
                        "status": "pending",
                        "recurring": True,
                        "interval_type": "days",
                        "interval_value": 1,
                        "next_execution": "2025-03-31T03:00:00",
                        "last_execution": "2025-03-30T03:00:00",
                        "execution_count": 30,
                        "created_at": "2025-03-01T00:00:00"
                    }
                ],
                "count": 1
            }
        }
    }

# Add more response/request schemas as needed for future endpoints.
# These would include:

class EventCreateRequest(BaseModel):
    """Schema for creating a new event."""
    name: str = Field(..., description="Name of the event")
    function_name: str = Field(..., description="Name of the function to execute")
    execution_time: datetime = Field(..., description="When to execute the event")
    description: Optional[str] = Field(None, description="Description of the event")
    recurring: bool = Field(False, description="Whether this is a recurring event")
    interval_type: Optional[str] = Field(None, description="For recurring events: minutes, hours, days, weeks, months, cron")
    interval_value: Optional[int] = Field(None, description="For recurring events: number of interval units")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters to pass to the function")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Daily Backup",
                "function_name": "backup_database",
                "execution_time": "2025-03-31T03:00:00",
                "description": "Daily database backup at 3 AM",
                "recurring": True,
                "interval_type": "days",
                "interval_value": 1,
                "parameters": {
                    "compress": True,
                    "destination": "/backups"
                }
            }
        }
    }

class CleanupConfigResponse(BaseModel):
    """Schema for a cleanup configuration response."""
    id: str = Field(..., description="Unique identifier for the configuration")
    directory: str = Field(..., description="Path to directory containing files to clean")
    pattern: str = Field("*", description="File matching pattern (e.g., '*.log', 'temp_*')")
    retention_days: Optional[int] = Field(None, description="Maximum age of files to keep in days")
    max_files: Optional[int] = Field(None, description="Maximum number of files to keep")
    max_size_mb: Optional[int] = Field(None, description="Maximum total size in MB")
    priority: int = Field(100, description="Cleanup priority (lower = higher priority)")
    description: Optional[str] = Field(None, description="Human-readable description")
    module_id: str = Field(..., description="ID of the module that registered the config")
    created_at: datetime = Field(..., description="When the config was created")
    last_run: Optional[datetime] = Field(None, description="When the cleanup was last run")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "directory": "/app/logs",
                "pattern": "*.log",
                "retention_days": 30,
                "max_files": 100,
                "max_size_mb": 500,
                "priority": 100,
                "description": "Application logs cleanup",
                "module_id": "core.logger",
                "created_at": "2025-03-01T00:00:00",
                "last_run": "2025-03-30T03:00:00"
            }
        }
    }

# Status and info response schemas
class SchedulerStatusResponse(BaseModel):
    """Response schema for scheduler status endpoint."""
    status: str = Field(..., description="Scheduler module status")
    module: str = Field(..., description="Module name")
    events_count: Optional[int] = Field(None, description="Number of scheduled events")
    running_events: Optional[int] = Field(None, description="Number of currently running events")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "active",
                "module": "scheduler", 
                "events_count": 5,
                "running_events": 1
            }
        }
    }

class SchedulerInfoResponse(BaseModel):
    """Response schema for scheduler info endpoint."""
    name: str = Field(..., description="Module name")
    version: str = Field(..., description="Module version")
    description: str = Field(..., description="Module description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "scheduler",
                "version": "1.0.0",
                "description": "Core scheduler module for background task management"
            }
        }
    }
