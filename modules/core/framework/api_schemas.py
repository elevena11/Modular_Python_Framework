"""
modules/core/framework/api_schemas.py
Pydantic schemas for Framework API request/response validation.

Provides session information and framework status schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class SessionInfoResponse(BaseModel):
    """Response schema for session information endpoint."""
    session_id: str = Field(..., description="Current session identifier")
    session_start_time: str = Field(..., description="Session start timestamp")
    framework_version: str = Field(..., description="Framework version")
    uptime_seconds: float = Field(..., description="Framework uptime in seconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "20250814_143022_a7b9c8d1",
                "session_start_time": "2025-08-14T14:30:22.123456",
                "framework_version": "1.0.0",
                "uptime_seconds": 3600.5
            }
        }
    }

class FrameworkStatusResponse(BaseModel):
    """Response schema for framework status endpoint."""
    status: str = Field(..., description="Framework status")
    module: str = Field(..., description="Module name")
    initialized: bool = Field(..., description="Whether framework is initialized")
    services_loaded: Optional[int] = Field(None, description="Number of loaded services")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "active",
                "module": "framework",
                "initialized": True,
                "services_loaded": 5
            }
        }
    }

class FrameworkInfoResponse(BaseModel):
    """Response schema for framework info endpoint."""
    name: str = Field(..., description="Framework module name")
    version: str = Field(..., description="Framework version")
    description: str = Field(..., description="Framework description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "framework",
                "version": "1.0.0",
                "description": "Provides framework utilities and session management"
            }
        }
    }

class ActiveModuleInfo(BaseModel):
    """Schema for individual active module information."""
    id: str = Field(..., description="Module identifier")
    name: str = Field(..., description="Module display name")
    status: str = Field(..., description="Module status")
    version: str = Field(..., description="Module version")
    description: str = Field(..., description="Module description")
    initialization_time: Optional[str] = Field(None, description="Module initialization timestamp")
    services: List[str] = Field(default_factory=list, description="Active services in this module")
    phase1_complete: bool = Field(..., description="Whether Phase 1 initialization is complete")
    phase2_complete: bool = Field(..., description="Whether Phase 2 initialization is complete")

class SystemSummary(BaseModel):
    """Schema for system-wide summary information."""
    total_modules: int = Field(..., description="Total number of active modules")
    total_active_services: int = Field(..., description="Total number of active services")
    last_updated: str = Field(..., description="Last update timestamp")

class ActiveModulesResponse(BaseModel):
    """Response schema for active modules endpoint."""
    modules: Dict[str, ActiveModuleInfo] = Field(..., description="Dictionary of active modules")
    total_modules: int = Field(..., description="Total number of active modules")
    system_summary: SystemSummary = Field(..., description="System-wide summary")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "modules": {
                    "core.database": {
                        "id": "core.database",
                        "name": "Core Database",
                        "status": "active",
                        "version": "1.0.0",
                        "description": "Active core.database module",
                        "initialization_time": "2025-09-19T11:13:53.123456",
                        "services": ["core.database.service", "core.database.crud_service"],
                        "phase1_complete": True,
                        "phase2_complete": True
                    }
                },
                "total_modules": 5,
                "system_summary": {
                    "total_modules": 5,
                    "total_active_services": 10,
                    "last_updated": "2025-09-19T11:13:53.123456"
                },
                "last_updated": "2025-09-19T11:13:53.123456"
            }
        }
    }