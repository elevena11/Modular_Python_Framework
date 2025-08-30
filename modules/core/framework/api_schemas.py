"""
modules/core/framework/api_schemas.py
Pydantic schemas for Framework API request/response validation.

Provides session information and framework status schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
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