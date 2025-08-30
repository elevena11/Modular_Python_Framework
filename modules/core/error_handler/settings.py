"""
modules/core/error_handler/settings.py
Pydantic settings model for core.error_handler module.

Conversion from legacy module_settings.py to settings_v2 Pydantic pattern.
Based on architecture documented in: docs/v2/settings_v2.md
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated

class ErrorHandlerSettings(BaseModel):
    """
    Pydantic model for core.error_handler settings.
    
    Provides type-safe configuration with validation and environment variable support.
    """
    model_config = ConfigDict(
        env_prefix="CORE_ERROR_HANDLER_",  # Environment variables: CORE_ERROR_HANDLER_MAX_LOG_FILES=200
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",  # Prevent unknown settings
        validate_assignment=True,  # Validate on assignment
        env_nested_delimiter="__",  # Support nested environment variables
        json_schema_extra={
            "title": "Error Handler Settings", 
            "description": "Configuration for error handling, logging, and analysis"
        }
    )
    
    # Log Management Settings
    max_log_files: Annotated[int, Field(
        default=100,
        ge=10,
        le=10000,
        description="Maximum number of error log files to retain",
        json_schema_extra={
            "ui_category": "Log Management",
            "ui_order": 10,
            "display_name": "Maximum Log Files"
        }
    )]
    
    retention_days: Annotated[int, Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to keep error log files",
        json_schema_extra={
            "ui_category": "Log Management",
            "ui_order": 20,
            "display_name": "Retention Period (Days)"
        }
    )]
    
    # Registry Settings  
    max_errors_per_category: Annotated[int, Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum number of unique errors to track per category",
        json_schema_extra={
            "ui_category": "Registry",
            "ui_order": 10,
            "display_name": "Max Errors Per Category"
        }
    )]
    
    max_examples_per_error: Annotated[int, Field(
        default=50,
        ge=5,
        le=1000,
        description="Maximum number of example occurrences to store per error",
        json_schema_extra={
            "ui_category": "Registry",
            "ui_order": 20,
            "display_name": "Max Examples Per Error"
        }
    )]
    
    priority_refresh_interval: Annotated[int, Field(
        default=24,
        ge=1,
        le=168,
        description="Hours between automatic refreshes of priority scores",
        json_schema_extra={
            "ui_category": "Registry", 
            "ui_order": 30,
            "display_name": "Priority Refresh Interval (Hours)"
        }
    )]
    
    # Analysis Settings
    min_occurrence_threshold: Annotated[int, Field(
        default=3,
        ge=1,
        le=100,
        description="Minimum number of occurrences to consider an error significant",
        json_schema_extra={
            "ui_category": "Analysis",
            "ui_order": 10,
            "display_name": "Minimum Occurrence Threshold"
        }
    )]
    
    recency_weight: Annotated[float, Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight of recency in priority calculation (0-1)",
        json_schema_extra={
            "ui_category": "Analysis",
            "ui_order": 20,
            "display_name": "Recency Weight",
            "ui_input_type": "slider",
            "ui_step": 0.1
        }
    )]
    
    frequency_weight: Annotated[float, Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight of frequency in priority calculation (0-1)",
        json_schema_extra={
            "ui_category": "Analysis",
            "ui_order": 30,
            "display_name": "Frequency Weight",
            "ui_input_type": "slider",
            "ui_step": 0.1
        }
    )]
    
    impact_weight: Annotated[float, Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight of impact in priority calculation (0-1)",
        json_schema_extra={
            "ui_category": "Analysis",
            "ui_order": 40,
            "display_name": "Impact Weight",
            "ui_input_type": "slider",
            "ui_step": 0.1
        }
    )]
    
    def model_post_init(self, __context):
        """Validate that weights sum to approximately 1.0"""
        total_weight = self.recency_weight + self.frequency_weight + self.impact_weight
        if not (0.95 <= total_weight <= 1.05):  # Allow small floating point errors
            raise ValueError(
                f"Analysis weights must sum to approximately 1.0, got {total_weight:.3f}. "
                f"Current: recency={self.recency_weight}, frequency={self.frequency_weight}, "
                f"impact={self.impact_weight}"
            )


# Convenience function for getting schema (useful for API endpoints)
def get_schema() -> dict:
    """Get JSON schema for UI form generation."""
    return ErrorHandlerSettings.model_json_schema()


# Example usage and testing
if __name__ == "__main__":
    import os
    import json
    
    # Test 1: Default settings
    print("=== Test 1: Default Settings ===")
    settings = ErrorHandlerSettings()
    print(json.dumps(settings.model_dump(), indent=2))
    
    # Test 2: Environment variable override
    print("\n=== Test 2: Environment Variable Override ===")
    os.environ["CORE_ERROR_HANDLER_MAX_LOG_FILES"] = "200"
    os.environ["CORE_ERROR_HANDLER_RETENTION_DAYS"] = "60"
    settings_with_env = ErrorHandlerSettings()
    print(json.dumps(settings_with_env.model_dump(), indent=2))
    
    # Test 3: Schema generation
    print("\n=== Test 3: JSON Schema ===")
    schema = get_schema()
    print(f"Schema title: {schema.get('title')}")
    print(f"Properties count: {len(schema.get('properties', {}))}")
    
    # Test 4: Validation error
    print("\n=== Test 4: Validation Test ===")
    try:
        invalid_settings = ErrorHandlerSettings(
            max_log_files=5,  # Too low (minimum is 10)
            recency_weight=0.8,
            frequency_weight=0.8,
            impact_weight=0.8  # Weights sum to 2.4, should fail validation
        )
    except Exception as e:
        print(f"Expected validation error: {e}")
    
    print("\nPydantic settings model testing complete!")