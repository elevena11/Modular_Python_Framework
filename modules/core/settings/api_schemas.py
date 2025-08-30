"""
modules/core/settings/api_schemas.py
Pydantic schemas for Settings API request/response validation.

Simple schemas for the minimal settings management API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union

class SetUserPreferenceRequest(BaseModel):
    """Request schema for setting user preferences."""
    value: Any = Field(..., description="Setting value (any JSON-serializable type)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "value": 0.9
            }
        }
    }

class ModuleSettingsResponse(BaseModel):
    """Response schema for module settings."""
    module_id: str = Field(..., description="Module identifier")
    settings: Dict[str, Any] = Field(..., description="Effective settings (baseline + user overrides)")
    baseline_count: int = Field(..., description="Number of baseline settings")
    user_overrides_count: int = Field(..., description="Number of user overrides")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "module_id": "core.model_manager",
                "settings": {
                    "gpu_memory_fraction": 0.8,
                    "device_preference": "auto",
                    "batch_size": 32
                },
                "baseline_count": 3,
                "user_overrides_count": 0
            }
        }
    }

class AllSettingsResponse(BaseModel):
    """Response schema for all settings across modules."""
    modules: Dict[str, Dict[str, Any]] = Field(..., description="Settings by module ID")
    total_modules: int = Field(..., description="Total number of modules")
    total_user_overrides: int = Field(..., description="Total user overrides across all modules")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "modules": {
                    "core.model_manager": {
                        "settings": {"gpu_memory_fraction": 0.8},
                        "baseline_count": 1,
                        "user_overrides_count": 0
                    }
                },
                "total_modules": 1,
                "total_user_overrides": 0
            }
        }
    }

class UserPreferenceResponse(BaseModel):
    """Response schema for user preference operations."""
    success: bool = Field(..., description="Operation success status")
    module_id: str = Field(..., description="Module identifier")
    setting_key: str = Field(..., description="Setting key")
    value: Optional[Any] = Field(None, description="Setting value (for set operations)")
    action: Optional[str] = Field(None, description="Action performed (created/updated)")
    cleared: Optional[bool] = Field(None, description="Whether preference was cleared")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "module_id": "core.model_manager",
                "setting_key": "gpu_memory_fraction",
                "value": 0.9,
                "action": "updated"
            }
        }
    }

# Status and info response schemas
class StatusResponse(BaseModel):
    """Response schema for status endpoint."""
    status: str = Field(..., description="Module status")
    module: str = Field(..., description="Module name")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "active",
                "module": "settings"
            }
        }
    }

class InfoResponse(BaseModel):
    """Response schema for info endpoint."""
    name: str = Field(..., description="Module name")
    version: str = Field(..., description="Module version")
    description: str = Field(..., description="Module description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "settings",
                "version": "1.0.0",
                "description": "Settings - Pydantic-first settings with memory optimization"
            }
        }
    }

# Legacy schemas for compatibility (can be removed later)
class SettingsV2Response(BaseModel):
    """Legacy response schema."""
    name: str = Field(..., description="Module name")
    version: str = Field(..., description="Module version")
    description: str = Field(..., description="Module description")