"""
modules/core/settings/components/validation_service.py
Updated: April 4, 2025
Handles validation of settings against schema definitions with standardized error handling
"""

import re
import logging
from typing import Dict, Any, Tuple, List, Optional, Union, Type

from core.error_utils import error_message, Result

# Define MODULE_ID matching manifest.json at the top of the file
MODULE_ID = "core.settings"
# Use module hierarchy for component logger
logger = logging.getLogger(f"{MODULE_ID}.validation")

class ValidationError(Exception):
    """Exception raised when settings validation fails."""
    def __init__(self, module_id: str, errors: Dict[str, str]):
        self.module_id = module_id
        self.errors = errors
        error_msg = [f"Settings validation failed for module '{module_id}':"]
        for key, message in errors.items():
            error_msg.append(f"  - {key}: {message}")
        super().__init__("\n".join(error_msg))

class SettingsValidationService:
    """
    Service for validating settings against schemas.
    
    Handles type validation, constraints checking, and conversion
    of values to appropriate types when possible.
    """
    
    # Supported types for validation
    VALID_TYPES = {
        "string": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "array": list,
        "object": dict
    }
    
    def __init__(self):
        """Initialize the validation service."""
        self.logger = logger
        self.initialized = True  # This service is always initialized upon creation
    
    async def initialize(self, app_context=None, settings=None) -> bool:
        """
        Initialize the validation service.
        
        Args:
            app_context: Optional application context
            settings: Optional pre-loaded settings
            
        Returns:
            True if initialization successful, always True for this service
        """
        return self.initialized
    
    async def validate_settings(self, 
                               module_id: str, 
                               settings: Dict[str, Any], 
                               schema: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate settings against schema.
        
        Args:
            module_id: Module identifier
            settings: Settings to validate
            schema: Validation schema
            
        Returns:
            Dictionary of errors by field name (empty if validation passed)
        """
        try:
            errors = {}
            
            # Check each setting that has a schema
            for key, key_schema in schema.items():
                if key in settings:
                    valid, error = await self.validate_setting(key, settings[key], key_schema)
                    if not valid:
                        errors[key] = error
            
            return errors
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="VALIDATION_ERROR",
                details=f"Error validating settings for module {module_id}: {str(e)}",
                location="validate_settings()"
            ))
            # Return the error as a validation error
            return {"_general": f"Validation system error: {str(e)}"}
    
    async def validate_setting(self, 
                              key: str, 
                              value: Any, 
                              schema: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a single setting against its schema.
        
        Args:
            key: Setting key
            value: Setting value
            schema: Validation schema for the setting
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            # Type validation
            if "type" in schema:
                valid, error, converted_value = await self._validate_type(key, value, schema)
                if not valid:
                    return False, error
                value = converted_value
            
            # Type-specific validations
            if isinstance(value, str):
                return await self._validate_string(key, value, schema)
            elif isinstance(value, (int, float)):
                return await self._validate_number(key, value, schema)
            elif isinstance(value, list):
                return await self._validate_list(key, value, schema)
            elif isinstance(value, dict):
                return await self._validate_object(key, value, schema)
            
            # Custom validation if present
            if "validator" in schema:
                return await self._run_custom_validator(key, value, schema)
            
            return True, ""
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SETTING_VALIDATION_ERROR",
                details=f"Error validating setting {key}: {str(e)}",
                location="validate_setting()"
            ))
            return False, f"Validation system error: {str(e)}"
    
    async def _validate_type(self, 
                            key: str, 
                            value: Any, 
                            schema: Dict[str, Any]) -> Tuple[bool, str, Any]:
        """
        Validate and potentially convert type.
        
        Args:
            key: Setting key
            value: Setting value
            schema: Validation schema
            
        Returns:
            Tuple of (valid, error_message, converted_value)
        """
        try:
            expected_type = schema["type"].lower()
            if expected_type not in self.VALID_TYPES:
                self.logger.warning(error_message(
                    module_id=MODULE_ID,
                    error_type="UNKNOWN_TYPE",
                    details=f"Unknown type {expected_type} in validation schema for {key}",
                    location="_validate_type()"
                ))
                return True, "", value
                
            expected_type_class = self.VALID_TYPES[expected_type]
            if isinstance(value, expected_type_class):
                return True, "", value
                
            # Handle type conversion for compatible types
            try:
                converted = False
                original_type_name = type(value).__name__
                
                if expected_type == "float" and isinstance(value, int):
                    value = float(value)
                    converted = True
                elif expected_type == "int" and isinstance(value, float) and value.is_integer():
                    value = int(value)
                    converted = True
                elif expected_type == "bool" and isinstance(value, str):
                    if value.lower() in ("true", "yes", "1"):
                        value = True
                        converted = True
                    elif value.lower() in ("false", "no", "0"):
                        value = False
                        converted = True
                    else:
                        return False, f"Cannot convert string '{value}' to boolean", value
                elif expected_type == "string" and not isinstance(value, (dict, list)):
                    # Convert simple types to string
                    value = str(value)
                    converted = True
                
                if converted:
                    self.logger.info(f"Converted setting '{key}' from {original_type_name} to {expected_type}")
                    return True, "", value
                else:
                    return False, f"Expected type {expected_type} for '{key}', got {type(value).__name__}", value
                    
            except Exception as e:
                return False, f"Failed to convert {key} to {expected_type}: {str(e)}", value
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="TYPE_VALIDATION_ERROR",
                details=f"Error validating type for {key}: {str(e)}",
                location="_validate_type()"
            ))
            return False, f"Type validation error: {str(e)}", value
            
    async def _validate_string(self, 
                              key: str, 
                              value: str, 
                              schema: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate string-specific constraints.
        
        Args:
            key: Setting key
            value: String value
            schema: Validation schema
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            if "pattern" in schema and not re.match(schema["pattern"], value):
                return False, f"Value does not match pattern {schema['pattern']}"
                
            if "min_length" in schema and len(value) < schema["min_length"]:
                return False, f"Value length {len(value)} is less than minimum {schema['min_length']}"
                
            if "max_length" in schema and len(value) > schema["max_length"]:
                return False, f"Value length {len(value)} is greater than maximum {schema['max_length']}"
                
            if "enum" in schema:
                return await self._validate_enum(key, value, schema)
                
            return True, ""
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="STRING_VALIDATION_ERROR",
                details=f"Error validating string for {key}: {str(e)}",
                location="_validate_string()"
            ))
            return False, f"String validation error: {str(e)}"
    
    async def _validate_enum(self, 
                           key: str, 
                           value: Any, 
                           schema: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate enum values.
        
        Args:
            key: Setting key
            value: Any value
            schema: Validation schema
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            valid_values = schema["enum"]
            valid_values_lower = [str(v).lower() for v in valid_values]
            
            # Pre-process value for dropdown selections with descriptions
            processed_value = value
            if isinstance(value, str) and " (" in value:
                processed_value = value.split(" (")[0]
            
            # Try multiple validation approaches
            # 1. Direct match with processed value
            if processed_value in valid_values:
                return True, ""
                
            # 2. Direct match with original value
            if value in valid_values:
                return True, ""
                
            # 3. Case-insensitive match with processed value
            if str(processed_value).lower() in valid_values_lower:
                return True, ""
                
            # 4. Case-insensitive match with original value
            if str(value).lower() in valid_values_lower:
                return True, ""
                
            # If all checks fail, return validation error
            return False, f"Value must be one of: {', '.join(str(v) for v in valid_values)}"
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="ENUM_VALIDATION_ERROR",
                details=f"Error validating enum for {key}: {str(e)}",
                location="_validate_enum()"
            ))
            return False, f"Enum validation error: {str(e)}"
    
    async def _validate_number(self, 
                              key: str, 
                              value: Union[int, float], 
                              schema: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate numeric constraints.
        
        Args:
            key: Setting key
            value: Numeric value
            schema: Validation schema
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            if "min" in schema and value < schema["min"]:
                return False, f"Value {value} is less than minimum {schema['min']}"
                
            if "max" in schema and value > schema["max"]:
                return False, f"Value {value} is greater than maximum {schema['max']}"
                
            if "multiple_of" in schema and value % schema["multiple_of"] != 0:
                return False, f"Value {value} is not a multiple of {schema['multiple_of']}"
                
            return True, ""
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="NUMBER_VALIDATION_ERROR",
                details=f"Error validating number for {key}: {str(e)}",
                location="_validate_number()"
            ))
            return False, f"Number validation error: {str(e)}"
    
    async def _validate_list(self, 
                            key: str, 
                            value: List[Any], 
                            schema: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate list constraints.
        
        Args:
            key: Setting key
            value: List value
            schema: Validation schema
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            if "min_items" in schema and len(value) < schema["min_items"]:
                return False, f"List has {len(value)} items, less than minimum {schema['min_items']}"
                
            if "max_items" in schema and len(value) > schema["max_items"]:
                return False, f"List has {len(value)} items, more than maximum {schema['max_items']}"
                
            # Validate individual items if schema provided
            if "items" in schema and value:
                for i, item in enumerate(value):
                    valid, error = await self.validate_setting(f"{key}[{i}]", item, schema["items"])
                    if not valid:
                        return False, f"Item at index {i}: {error}"
                        
            # Check uniqueness if required
            if schema.get("unique_items", False):
                try:
                    unique_items = set(value)
                    if len(unique_items) != len(value):
                        return False, "List contains duplicate items"
                except Exception:
                    # If items aren't hashable, we can't easily check uniqueness
                    pass
                        
            return True, ""
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="LIST_VALIDATION_ERROR",
                details=f"Error validating list for {key}: {str(e)}",
                location="_validate_list()"
            ))
            return False, f"List validation error: {str(e)}"
    
    async def _validate_object(self, 
                              key: str, 
                              value: Dict[str, Any], 
                              schema: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate object constraints.
        
        Args:
            key: Setting key
            value: Dictionary value
            schema: Validation schema
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            if "min_properties" in schema and len(value) < schema["min_properties"]:
                return False, f"Object has {len(value)} properties, less than minimum {schema['min_properties']}"
                
            if "max_properties" in schema and len(value) > schema["max_properties"]:
                return False, f"Object has {len(value)} properties, more than maximum {schema['max_properties']}"
                
            # Validate properties if schema provided
            if "properties" in schema and value:
                for prop_key, prop_schema in schema["properties"].items():
                    if prop_key in value:
                        valid, error = await self.validate_setting(f"{key}.{prop_key}", value[prop_key], prop_schema)
                        if not valid:
                            return False, f"Property '{prop_key}': {error}"
                
                # Check for required properties
                if "required" in schema:
                    for req_prop in schema["required"]:
                        if req_prop not in value:
                            return False, f"Missing required property '{req_prop}'"
                        
            return True, ""
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="OBJECT_VALIDATION_ERROR",
                details=f"Error validating object for {key}: {str(e)}",
                location="_validate_object()"
            ))
            return False, f"Object validation error: {str(e)}"
    
    async def _run_custom_validator(self, 
                                   key: str, 
                                   value: Any, 
                                   schema: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Run custom validator function from app_context.
        
        Args:
            key: Setting key
            value: Setting value
            schema: Validation schema
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            validator_name = schema["validator"]
            
            # Custom validator not supported without app_context
            # Will be handled by the main SettingsService
            return True, ""
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="CUSTOM_VALIDATOR_ERROR",
                details=f"Error running custom validator for {key}: {str(e)}",
                location="_run_custom_validator()"
            ))
            return False, f"Custom validator error: {str(e)}"
