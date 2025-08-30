"""
modules/core/settings/settings.py
Pydantic settings model for core.settings module.

Following the same pattern core.settings enforces on other modules:
- Environment variable support with CORE_SETTINGS_ prefix
- Type validation and default values
- Self-configuration using the settings system it provides
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


class SettingsModuleSettings(BaseModel):
    """
    Pydantic settings model for core.settings module self-configuration.
    
    Replaces hardcoded values throughout the settings system with
    configurable parameters following the same pattern as other modules.
    """
    
    model_config = ConfigDict(
        env_prefix="CORE_SETTINGS_",
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "title": "Settings Module Configuration",
            "description": "Configuration for the core.settings module itself"
        }
    )
    
    # Database Configuration
    default_database_name: str = Field(
        default="settings",
        description="Default database name for user preferences storage",
        json_schema_extra={
            "ui_component": "text",
            "ui_category": "Database",
            "ui_help": "Database name used for storing user preference overrides"
        }
    )
    
    default_user_id: str = Field(
        default="default",
        min_length=1,
        max_length=50,
        description="Default user identifier for preference storage",
        json_schema_extra={
            "ui_component": "text", 
            "ui_category": "Database",
            "ui_help": "Default user ID when no specific user is provided"
        }
    )
    
    default_changed_by: str = Field(
        default="user",
        min_length=1,
        max_length=100,
        description="Default value for who made preference changes",
        json_schema_extra={
            "ui_component": "text",
            "ui_category": "Database", 
            "ui_help": "Default attribution for user preference changes"
        }
    )
    
    # Timeout Configuration
    graceful_shutdown_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout in seconds for graceful shutdown",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Timeouts",
            "ui_help": "Maximum time to wait for graceful cleanup during shutdown"
        }
    )
    
    force_shutdown_timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Timeout in seconds for forced shutdown",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Timeouts",
            "ui_help": "Maximum time for forced cleanup if graceful shutdown fails"
        }
    )
    
    # Environment Parsing Configuration
    environment_parse_timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Timeout in seconds for environment variable parsing",
        json_schema_extra={
            "ui_component": "number",
            "ui_category": "Performance",
            "ui_help": "Maximum time to spend parsing environment variables"
        }
    )
    
    # Performance Configuration
    baseline_cache_enabled: bool = Field(
        default=True,
        description="Enable caching of resolved baseline settings in memory",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Performance",
            "ui_help": "Cache baseline settings in memory for faster access"
        }
    )
    
    # Behavior Configuration
    strict_validation: bool = Field(
        default=True,
        description="Enable strict validation of Pydantic models during registration",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Behavior",
            "ui_help": "Enforce strict validation when registering module settings models"
        }
    )
    
    log_environment_parsing: bool = Field(
        default=False,
        description="Enable detailed logging of environment variable parsing",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Behavior", 
            "ui_help": "Log detailed information about environment variable processing"
        }
    )
    
    log_baseline_creation: bool = Field(
        default=True,
        description="Enable logging of baseline settings creation process",
        json_schema_extra={
            "ui_component": "checkbox",
            "ui_category": "Behavior",
            "ui_help": "Log information about baseline settings creation during Phase 2"
        }
    )
    
    # API Configuration  
    api_router_prefix: str = Field(
        default="/settings",
        description="API router prefix for settings endpoints",
        json_schema_extra={
            "ui_component": "text",
            "ui_category": "API",
            "ui_readonly": True,
            "ui_help": "URL prefix for all settings API endpoints (requires restart to change)"
        }
    )
    
    api_router_tags: list[str] = Field(
        default=["settings"],
        description="API router tags for OpenAPI documentation",
        json_schema_extra={
            "ui_component": "text",
            "ui_category": "API",
            "ui_readonly": True,
            "ui_help": "Tags used in OpenAPI documentation for settings endpoints"
        }
    )
    
    def get_database_config(self) -> dict:
        """
        Get database-related configuration as a dictionary.
        
        Returns:
            Dictionary of database configuration parameters
        """
        return {
            "default_database_name": self.default_database_name,
            "default_user_id": self.default_user_id,
            "default_changed_by": self.default_changed_by
        }
    
    def get_timeout_config(self) -> dict:
        """
        Get timeout-related configuration as a dictionary.
        
        Returns:
            Dictionary of timeout configuration parameters
        """
        return {
            "graceful_shutdown_timeout": self.graceful_shutdown_timeout,
            "force_shutdown_timeout": self.force_shutdown_timeout,
            "environment_parse_timeout": self.environment_parse_timeout
        }
    
    def get_performance_config(self) -> dict:
        """
        Get performance-related configuration as a dictionary.
        
        Returns:
            Dictionary of performance configuration parameters
        """
        return {
            "baseline_cache_enabled": self.baseline_cache_enabled
        }
    
    def get_behavior_config(self) -> dict:
        """
        Get behavior-related configuration as a dictionary.
        
        Returns:
            Dictionary of behavior configuration parameters
        """
        return {
            "strict_validation": self.strict_validation,
            "log_environment_parsing": self.log_environment_parsing,
            "log_baseline_creation": self.log_baseline_creation
        }