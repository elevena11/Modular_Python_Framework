"""
modules/core/settings/services/validation_service.py
Updated: April 5, 2025
Validation service for settings module with standardized error handling
"""

import re
import logging
from typing import Dict, Any, Tuple, List, Optional, Union, Type

from core.error_utils import error_message, Result
from ..utils.error_helpers import handle_result_operation

# Define component identity
MODULE_ID = "core.settings"
COMPONENT_ID = f"{MODULE_ID}.validation"
# Use component ID for the logger
logger = logging.getLogger(COMPONENT_ID)

class ValidationError(Exception):
    """Exception raised when settings validation fails."""
    def __init__(self, module_id: str, errors: Dict[str, str]):
        self.module_id = module_id
        self.errors = errors
        error_msg = [f"Settings validation failed for module '{module_id}':"]
        for key, message in errors.items():
            error_msg.append(f"  - {key}: {message}")
        super().__init__("\n".join(error_msg))

class ValidationService:
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
                               schema: Dict[str, Any]) -> Result:
        """
        Validate settings against schema.
        
        Args:
            module_id: Module identifier
            settings: Settings to validate
            schema: Validation schema
            
        Returns:
            Result with success or error details
        """
        async def _validate():
            errors = {}
            
            # Check each setting that has a schema
            for key, key_schema in schema.items():
                if key in settings:
                    # Validate the setting
                    validation_result = await self.validate_setting(key, settings[key], key_schema)
                    
                    # If validation failed, add to errors
                    if not validation_result.success:
                        errors[key] = validation_result.error.get("message")
            
            # Return errors if any
            if errors:
                return {"success": False, "errors": errors}
            
            # Return success
            return {"success": True}
            
        result = await handle_result_operation(
            _validate,
            COMPONENT_ID,
            "VALIDATION_ERROR",
            f"Error validating settings for module {module_id}",
            "validate_settings()",
            {"module_id": module_id}
        )
        
        # Check validation result
        if result.success:
            validation_result = result.data
            if validation_result.get("success", False):
                return Result.success(data=True)
            else:
                return Result.error(
                    code="VALIDATION_ERROR",
                    message=f"Settings validation failed for module {module_id}",
                    details={"errors": validation_result.get("errors", {})}
                )
        
        # Return error from operation
        return result
    
    async def validate_setting(self, 
                              key: str, 
                              value: Any, 
                              schema: Dict[str, Any]) -> Result:
        """
        Validate a single setting against its schema.
        
        Args:
            key: Setting key
            value: Setting value
            schema: Validation schema for the setting
            
        Returns:
            Result with success or error details
        """
        async def _validate():
            current_value = value # Use a local variable to track the value being processed

            # Type validation
            if "type" in schema:
                type_result = await self._validate_type(key, current_value, schema)
                if not type_result.success:
                    return {"valid": False, "error": type_result.error.get("message")}

                # Use the potentially converted value for further validation
                current_value = type_result.data

            # Type-specific validations
            if isinstance(current_value, str):
                string_result = await self._validate_string(key, current_value, schema)
                if not string_result.success:
                    return {"valid": False, "error": string_result.error.get("message")}
            elif isinstance(current_value, (int, float)):
                number_result = await self._validate_number(key, current_value, schema)
                if not number_result.success:
                    return {"valid": False, "error": number_result.error.get("message")}
            elif isinstance(current_value, list):
                list_result = await self._validate_list(key, current_value, schema)
                if not list_result.success:
                    return {"valid": False, "error": list_result.error.get("message")}
            elif isinstance(current_value, dict):
                object_result = await self._validate_object(key, current_value, schema)
                if not object_result.success:
                    return {"valid": False, "error": object_result.error.get("message")}

            # Custom validation if present
            if "validator" in schema:
                validator_result = await self._run_custom_validator(key, current_value, schema)
                if not validator_result.success:
                    return {"valid": False, "error": validator_result.error.get("message")}

            # All validations passed
            return {"valid": True, "value": current_value}
        
        result = await handle_result_operation(
            _validate,
            COMPONENT_ID,
            "SETTING_VALIDATION_ERROR",
            f"Error validating setting {key}",
            "validate_setting()",
            {"key": key}
        )
        
        # Check validation result
        if result.success:
            validation_result = result.data
            if validation_result.get("valid", False):
                return Result.success(data=validation_result.get("value", value))
            else:
                return Result.error(
                    code="VALIDATION_ERROR",
                    message=validation_result.get("error", f"Validation failed for {key}"),
                    details={"key": key}
                )
        
        # Return error from operation
        return result
    
    async def _validate_type(self, 
                            key: str, 
                            value: Any, 
                            schema: Dict[str, Any]) -> Result:
        """
        Validate and potentially convert type.
        
        Args:
            key: Setting key
            value: Setting value
            schema: Validation schema
            
        Returns:
            Result with converted value or error details
        """
        try:
            expected_type = schema["type"].lower()
            
            # Check if type is supported
            if expected_type not in self.VALID_TYPES:
                logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="UNKNOWN_TYPE",
                    details=f"Unknown type {expected_type} in validation schema for {key}",
                    location="_validate_type()"
                ))
                return Result.success(data=value)
                
            expected_type_class = self.VALID_TYPES[expected_type]
            
            # If already correct type, return success
            if isinstance(value, expected_type_class):
                return Result.success(data=value)
                
            # Try to convert to expected type
            original_type_name = type(value).__name__
            converted = False
            converted_value = value
            
            # Handle type conversions for compatible types
            if expected_type == "float" and isinstance(value, int):
                converted_value = float(value)
                converted = True
            elif expected_type == "int" and isinstance(value, float) and value.is_integer():
                converted_value = int(value)
                converted = True
            elif expected_type == "bool" and isinstance(value, str):
                if value.lower() in ("true", "yes", "1"):
                    converted_value = True
                    converted = True
                elif value.lower() in ("false", "no", "0"):
                    converted_value = False
                    converted = True
                else:
                    return Result.error(
                        code="TYPE_CONVERSION_ERROR",
                        message=f"Cannot convert string '{value}' to boolean",
                        details={"value": value, "expected_type": "bool"}
                    )
            elif expected_type == "string" and not isinstance(value, (dict, list)):
                # Convert simple types to string
                converted_value = str(value)
                converted = True
            
            # If conversion succeeded, return success
            if converted:
                logger.info(f"Converted setting '{key}' from {original_type_name} to {expected_type}")
                return Result.success(data=converted_value)
            
            # Conversion failed
            return Result.error(
                code="TYPE_ERROR",
                message=f"Expected type {expected_type} for '{key}', got {type(value).__name__}",
                details={"expected_type": expected_type, "actual_type": type(value).__name__}
            )
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TYPE_VALIDATION_ERROR",
                details=f"Error validating type for {key}: {str(e)}",
                location="_validate_type()"
            ))
            return Result.error(
                code="TYPE_VALIDATION_ERROR",
                message=f"Failed to validate type for {key}: {str(e)}",
                details={"key": key, "error": str(e)}
            )
            
    async def _validate_string(self, 
                              key: str, 
                              value: str, 
                              schema: Dict[str, Any]) -> Result:
        """
        Validate string-specific constraints.
        
        Args:
            key: Setting key
            value: String value
            schema: Validation schema
            
        Returns:
            Result with success or error details
        """
        try:
            # Check pattern constraint
            if "pattern" in schema and not re.match(schema["pattern"], value):
                return Result.error(
                    code="PATTERN_ERROR",
                    message=f"Value does not match pattern {schema['pattern']}",
                    details={"pattern": schema["pattern"], "value": value}
                )
                
            # Check min_length constraint
            if "min_length" in schema and len(value) < schema["min_length"]:
                return Result.error(
                    code="MIN_LENGTH_ERROR",
                    message=f"Value length {len(value)} is less than minimum {schema['min_length']}",
                    details={"min_length": schema["min_length"], "actual_length": len(value)}
                )
                
            # Check max_length constraint
            if "max_length" in schema and len(value) > schema["max_length"]:
                return Result.error(
                    code="MAX_LENGTH_ERROR",
                    message=f"Value length {len(value)} is greater than maximum {schema['max_length']}",
                    details={"max_length": schema["max_length"], "actual_length": len(value)}
                )
                
            # Check enum constraint
            if "enum" in schema:
                enum_result = await self._validate_enum(key, value, schema)
                if not enum_result.success:
                    return enum_result
                
            # All checks passed
            return Result.success(data=value)
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="STRING_VALIDATION_ERROR",
                details=f"Error validating string for {key}: {str(e)}",
                location="_validate_string()"
            ))
            return Result.error(
                code="STRING_VALIDATION_ERROR",
                message=f"Failed to validate string for {key}: {str(e)}",
                details={"key": key, "error": str(e)}
            )
    
    async def _validate_enum(self, 
                           key: str, 
                           value: Any, 
                           schema: Dict[str, Any]) -> Result:
        """
        Validate enum values.
        
        Args:
            key: Setting key
            value: Any value
            schema: Validation schema
            
        Returns:
            Result with success or error details
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
                return Result.success(data=value)
                
            # 2. Direct match with original value
            if value in valid_values:
                return Result.success(data=value)
                
            # 3. Case-insensitive match with processed value
            if str(processed_value).lower() in valid_values_lower:
                return Result.success(data=value)
                
            # 4. Case-insensitive match with original value
            if str(value).lower() in valid_values_lower:
                return Result.success(data=value)
                
            # If all checks fail, return validation error
            return Result.error(
                code="ENUM_ERROR",
                message=f"Value must be one of: {', '.join(str(v) for v in valid_values)}",
                details={"valid_values": valid_values, "provided_value": value}
            )
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="ENUM_VALIDATION_ERROR",
                details=f"Error validating enum for {key}: {str(e)}",
                location="_validate_enum()"
            ))
            return Result.error(
                code="ENUM_VALIDATION_ERROR",
                message=f"Failed to validate enum for {key}: {str(e)}",
                details={"key": key, "error": str(e)}
            )
    
    async def _validate_number(self, 
                              key: str, 
                              value: Union[int, float], 
                              schema: Dict[str, Any]) -> Result:
        """
        Validate numeric constraints.
        
        Args:
            key: Setting key
            value: Numeric value
            schema: Validation schema
            
        Returns:
            Result with success or error details
        """
        try:
            # Check min constraint
            if "min" in schema and value < schema["min"]:
                return Result.error(
                    code="MIN_VALUE_ERROR",
                    message=f"Value {value} is less than minimum {schema['min']}",
                    details={"min": schema["min"], "value": value}
                )
                
            # Check max constraint
            if "max" in schema and value > schema["max"]:
                return Result.error(
                    code="MAX_VALUE_ERROR",
                    message=f"Value {value} is greater than maximum {schema['max']}",
                    details={"max": schema["max"], "value": value}
                )
                
            # Check multiple_of constraint
            if "multiple_of" in schema and value % schema["multiple_of"] != 0:
                return Result.error(
                    code="MULTIPLE_OF_ERROR",
                    message=f"Value {value} is not a multiple of {schema['multiple_of']}",
                    details={"multiple_of": schema["multiple_of"], "value": value}
                )
                
            # All checks passed
            return Result.success(data=value)
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="NUMBER_VALIDATION_ERROR",
                details=f"Error validating number for {key}: {str(e)}",
                location="_validate_number()"
            ))
            return Result.error(
                code="NUMBER_VALIDATION_ERROR",
                message=f"Failed to validate number for {key}: {str(e)}",
                details={"key": key, "error": str(e)}
            )
    
    async def _validate_list(self, 
                            key: str, 
                            value: List[Any], 
                            schema: Dict[str, Any]) -> Result:
        """
        Validate list constraints.
        
        Args:
            key: Setting key
            value: List value
            schema: Validation schema
            
        Returns:
            Result with success or error details
        """
        try:
            # Check min_items constraint
            if "min_items" in schema and len(value) < schema["min_items"]:
                return Result.error(
                    code="MIN_ITEMS_ERROR",
                    message=f"List has {len(value)} items, less than minimum {schema['min_items']}",
                    details={"min_items": schema["min_items"], "actual_items": len(value)}
                )
                
            # Check max_items constraint
            if "max_items" in schema and len(value) > schema["max_items"]:
                return Result.error(
                    code="MAX_ITEMS_ERROR",
                    message=f"List has {len(value)} items, more than maximum {schema['max_items']}",
                    details={"max_items": schema["max_items"], "actual_items": len(value)}
                )
                
            # Validate individual items if schema provided
            if "items" in schema and value:
                for i, item in enumerate(value):
                    item_result = await self.validate_setting(f"{key}[{i}]", item, schema["items"])
                    if not item_result.success:
                        return Result.error(
                            code="ITEM_VALIDATION_ERROR",
                            message=f"Item at index {i}: {item_result.error.get('message')}",
                            details={"index": i, "item_error": item_result.error}
                        )
                        
            # Check uniqueness if required
            if schema.get("unique_items", False):
                try:
                    unique_items = set(value)
                    if len(unique_items) != len(value):
                        return Result.error(
                            code="UNIQUENESS_ERROR",
                            message="List contains duplicate items",
                            details={"items": value}
                        )
                except Exception:
                    # If items aren't hashable, we can't easily check uniqueness
                    pass
                        
            # All checks passed
            return Result.success(data=value)
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="LIST_VALIDATION_ERROR",
                details=f"Error validating list for {key}: {str(e)}",
                location="_validate_list()"
            ))
            return Result.error(
                code="LIST_VALIDATION_ERROR",
                message=f"Failed to validate list for {key}: {str(e)}",
                details={"key": key, "error": str(e)}
            )
    
    async def _validate_object(self, 
                              key: str, 
                              value: Dict[str, Any], 
                              schema: Dict[str, Any]) -> Result:
        """
        Validate object constraints.
        
        Args:
            key: Setting key
            value: Dictionary value
            schema: Validation schema
            
        Returns:
            Result with success or error details
        """
        try:
            # Check min_properties constraint
            if "min_properties" in schema and len(value) < schema["min_properties"]:
                return Result.error(
                    code="MIN_PROPERTIES_ERROR",
                    message=f"Object has {len(value)} properties, less than minimum {schema['min_properties']}",
                    details={"min_properties": schema["min_properties"], "actual_properties": len(value)}
                )
                
            # Check max_properties constraint
            if "max_properties" in schema and len(value) > schema["max_properties"]:
                return Result.error(
                    code="MAX_PROPERTIES_ERROR",
                    message=f"Object has {len(value)} properties, more than maximum {schema['max_properties']}",
                    details={"max_properties": schema["max_properties"], "actual_properties": len(value)}
                )
                
            # Validate properties if schema provided
            if "properties" in schema and value:
                for prop_key, prop_schema in schema["properties"].items():
                    if prop_key in value:
                        prop_result = await self.validate_setting(f"{key}.{prop_key}", value[prop_key], prop_schema)
                        if not prop_result.success:
                            return Result.error(
                                code="PROPERTY_VALIDATION_ERROR",
                                message=f"Property '{prop_key}': {prop_result.error.get('message')}",
                                details={"property": prop_key, "property_error": prop_result.error}
                            )
                
                # Check for required properties
                if "required" in schema:
                    # Handle both object-level required lists and property-level required booleans
                    required_props = schema["required"]
                    if isinstance(required_props, list):
                        # Object-level required properties (list of property names)
                        for req_prop in required_props:
                            if req_prop not in value:
                                return Result.error(
                                    code="REQUIRED_PROPERTY_ERROR",
                                    message=f"Missing required property '{req_prop}'",
                                    details={"required_property": req_prop}
                                )
                    elif isinstance(required_props, bool):
                        # Property-level required flag - not applicable for object validation
                        # This is handled at the individual property level
                        pass
                        
            # All checks passed
            return Result.success(data=value)
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="OBJECT_VALIDATION_ERROR",
                details=f"Error validating object for {key}: {str(e)}",
                location="_validate_object()"
            ))
            return Result.error(
                code="OBJECT_VALIDATION_ERROR",
                message=f"Failed to validate object for {key}: {str(e)}",
                details={"key": key, "error": str(e)}
            )
    
    async def _run_custom_validator(self, 
                                   key: str, 
                                   value: Any, 
                                   schema: Dict[str, Any]) -> Result:
        """
        Run custom validator function from app_context.
        
        Args:
            key: Setting key
            value: Setting value
            schema: Validation schema
            
        Returns:
            Result with success or error details
        """
        try:
            validator_name = schema["validator"]
            
            # Custom validator not supported without app_context
            # Will be handled by the main SettingsService
            return Result.success(data=value)
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="CUSTOM_VALIDATOR_ERROR",
                details=f"Error running custom validator for {key}: {str(e)}",
                location="_run_custom_validator()"
            ))
            return Result.error(
                code="CUSTOM_VALIDATOR_ERROR",
                message=f"Failed to run custom validator for {key}: {str(e)}",
                details={"key": key, "error": str(e)}
            )
