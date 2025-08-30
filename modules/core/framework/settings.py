"""
modules/core/framework/settings.py
Pydantic settings model for core.framework module.

Framework settings for application configuration, session management,
and global framework behavior.
"""

from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import Optional, Dict, Any
from enum import Enum


class LogLevel(str, Enum):
    """Log level options for framework logging."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EnvironmentType(str, Enum):
    """Environment type for framework operation."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class FrameworkSettings(BaseModel):
    """
    Pydantic settings model for core.framework with full validation.
    
    Manages global framework configuration including API settings,
    session management, logging preferences, and runtime environment.
    """
    
    model_config = ConfigDict(
        env_prefix="CORE_FRAMEWORK_",
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "title": "Framework Settings",
            "description": "Core framework configuration and global settings"
        }
    )
    
    # API Configuration
    api_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for the API server",
        json_schema_extra={
            "ui_component": "text",
            "ui_category": "API Configuration",
            "ui_help": "The base URL where the framework API is accessible"
        }
    )
    
    app_title: str = Field(
        default="Modular Python Framework",
        min_length=1,
        max_length=100,
        description="Application title displayed in the UI",
        json_schema_extra={
            "ui_component": "text",
            "ui_category": "Application",
            "ui_help": "The application name shown in UI headers and documentation"
        }
    )
    
    app_version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Application version in semver format",
        json_schema_extra={
            "ui_component": "text",
            "ui_category": "Application",
            "ui_help": "Semantic version of the application (major.minor.patch)"
        }
    )
    
    # Environment and Runtime
    environment: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT,
        description="Runtime environment type",
        json_schema_extra={
            "ui_component": "select",
            "ui_category": "Environment",
            "ui_help": "Current runtime environment affecting logging and error handling"
        }
    )
    
    debug_mode: bool = Field(
        default=True,
        description="Enable debug mode with detailed logging and error reporting",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Environment",
            "ui_help": "Enables verbose logging and detailed error messages"
        }
    )
    
    # Logging Configuration
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Global log level for framework components",
        json_schema_extra={
            "ui_component": "select",
            "ui_category": "Logging",
            "ui_help": "Minimum log level for framework-wide logging output"
        }
    )
    
    enable_request_logging: bool = Field(
        default=True,
        description="Enable HTTP request/response logging",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Logging",
            "ui_help": "Log all HTTP requests and responses for debugging"
        }
    )
    
    # Session Management
    session_timeout_minutes: int = Field(
        default=240,  # 4 hours
        ge=5,
        le=1440,  # Max 24 hours
        description="Session timeout in minutes",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Session",
            "ui_help": "How long sessions remain active without user interaction"
        }
    )
    
    max_concurrent_sessions: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum concurrent user sessions",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Session",
            "ui_help": "Maximum number of simultaneous user sessions allowed"
        }
    )
    
    # Performance and Resource Management
    request_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=300.0,
        description="HTTP request timeout in seconds",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Performance",
            "ui_help": "Maximum time to wait for HTTP requests to complete"
        }
    )
    
    max_request_size_mb: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum HTTP request size in megabytes",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Performance",
            "ui_help": "Maximum allowed size for incoming HTTP requests"
        }
    )
    
    # Framework Features
    enable_cors: bool = Field(
        default=True,
        description="Enable Cross-Origin Resource Sharing (CORS)",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Security",
            "ui_help": "Allow cross-origin requests from web browsers"
        }
    )
    
    enable_compression: bool = Field(
        default=True,
        description="Enable HTTP response compression",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Performance",
            "ui_help": "Compress HTTP responses to reduce bandwidth usage"
        }
    )
    
    # Development and Testing
    enable_hot_reload: bool = Field(
        default=False,
        description="Enable hot reload for development (requires restart)",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Development",
            "ui_help": "Automatically reload framework when code changes (development only)"
        }
    )
    
    enable_api_docs: bool = Field(
        default=True,
        description="Enable automatic API documentation generation",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "API Configuration",
            "ui_help": "Generate and serve interactive API documentation at /docs"
        }
    )
    
    # Custom Configuration Extension
    custom_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom configuration values for extensions",
        json_schema_extra={
            "ui_component": "json",
            "ui_category": "Advanced",
            "ui_help": "Custom configuration data for framework extensions and plugins"
        }
    )
    
    # Metadata
    framework_description: Optional[str] = Field(
        default="Generic modular Python framework for rapid application development",
        max_length=500,
        description="Framework description for documentation",
        json_schema_extra={
            "ui_component": "textarea",
            "ui_category": "Application",
            "ui_help": "Description of the framework purpose and functionality"
        }
    )