# Error Handler Module

The Error Handler Module (`modules/core/error_handler/`) provides standardized error handling and logging capabilities for the framework. It implements consistent error patterns, structured logging, and error response generation that ensures all modules handle errors uniformly.

## Overview

The Error Handler Module is a core framework component that standardizes error handling across all modules. It provides:

- **Result Pattern**: Consistent return pattern for all service operations
- **Standardized Error Responses**: Uniform HTTP error response format
- **Structured Logging**: JSON-based error logging with detailed context
- **Error Registry**: Centralized error code management and documentation
- **Automatic Location Detection**: Pinpoints where errors occur in code
- **HTTPException Integration**: Seamless FastAPI error handling

## Key Features

### 1. Result Pattern
- **Consistent Returns**: All service methods return Result objects
- **Success/Error Handling**: Clear distinction between success and error cases
- **Type Safety**: Prevents mixed return types and improves code clarity
- **Usage Validation**: Detects and warns about incorrect usage patterns

### 2. Standardized Error Responses
- **HTTP Error Format**: Consistent error response structure for APIs
- **Error Code Generation**: Automatic generation of prefixed error codes
- **Context Preservation**: Maintains error context throughout the stack
- **Status Code Mapping**: Appropriate HTTP status codes for different error types

### 3. Structured Logging
- **JSON-Based**: Machine-readable error logs
- **Daily Rotation**: Automatic log file rotation by date
- **Detailed Context**: Location, module, timestamp, and error details
- **Performance Optimized**: Minimal overhead for error logging

### 4. Error Registry
- **Centralized Management**: Single source of truth for error codes
- **Documentation**: Automatic documentation of error codes and examples
- **Validation**: Prevents duplicate error codes across modules
- **Knowledge Building**: Accumulates error patterns and solutions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Error Handler Module                       │
├─────────────────────────────────────────────────────────────┤
│ Core Components                                             │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Result Pattern  │ │ Error Response  │ │ Error Registry  │ │
│ │ (Result class)  │ │ Generation      │ │ Service         │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Logging System                                              │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Structured      │ │ Location        │ │ Daily Log       │ │
│ │ JSON Logging    │ │ Detection       │ │ Rotation        │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Error Database                                              │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Error Codes     │ │ Error           │ │ Error           │ │
│ │ Registry        │ │ Documentation   │ │ Examples        │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Result Pattern

### 1. Result Class Design
```python
class Result:
    """Standard result object for all service operations."""
    
    def __init__(self, success=False, data=None, error=None):
        self.success = success
        self.data = data
        self.error = error or {}
    
    @classmethod
    def success(cls, data=None):
        """Create a success result."""
        return cls(success=True, data=data)
    
    @classmethod
    def error(cls, code, message, details=None):
        """Create an error result."""
        return cls(success=False, error={
            "code": code,
            "message": message,
            "details": details
        })
```

### 2. Usage Patterns
```python
# ✅ CORRECT: Success case
async def create_user(user_data):
    try:
        user = await database.create_user(user_data)
        return Result.success(data=user)
    except Exception as e:
        return Result.error(
            code="USER_CREATION_FAILED",
            message="Failed to create user",
            details={"error": str(e)}
        )

# ✅ CORRECT: Error case
async def get_user(user_id):
    user = await database.get_user(user_id)
    if not user:
        return Result.error(
            code="USER_NOT_FOUND",
            message=f"User with ID {user_id} not found"
        )
    return Result.success(data=user)
```

### 3. Result Consumption
```python
# ✅ CORRECT: Check result before using
result = await service.create_user(user_data)
if result.success:
    user = result.data
    print(f"Created user: {user.id}")
else:
    error = result.error
    print(f"Error: {error['code']} - {error['message']}")

# ❌ WRONG: Direct data access without checking
result = await service.create_user(user_data)
user = result.data  # May be None if error occurred
```

### 4. Usage Validation
```python
# The Result class includes validation to catch common mistakes:

# ✅ CORRECT: Use data= keyword
return Result.success(data={"user_id": 123})

# ❌ WRONG: Missing data= keyword (generates warning)
return Result.success({"user_id": 123})

# ❌ WRONG: Dictionary-style access (generates warning)
if result["success"]:  # Should be: if result.success:
    data = result["data"]  # Should be: data = result.data
```

## Error Response Generation

### 1. HTTP Error Responses
```python
def create_error_response(module_id, code, message, details=None, status_code=400):
    """Create standardized HTTP error response."""
    
    # Generate prefixed error code
    module_prefix = module_id.replace('.', '_')
    error_code = f"{module_prefix}_{code}"
    
    # Create error response
    error_response = {
        "status": "error",
        "code": error_code,
        "message": message
    }
    
    if details:
        error_response["details"] = details
    
    return HTTPException(status_code=status_code, detail=error_response)
```

### 2. Error Code Generation
```python
# Input: module_id="core.database", code="CONNECTION_FAILED"
# Output: "core_database_CONNECTION_FAILED"

# Examples:
"core.database" + "TABLE_NOT_FOUND" = "core_database_TABLE_NOT_FOUND"
"standard.user_auth" + "INVALID_TOKEN" = "standard_user_auth_INVALID_TOKEN"
"extensions.plugin" + "NOT_FOUND" = "extensions_plugin_NOT_FOUND"
```

### 3. API Usage
```python
# In module API endpoints
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    result = await user_service.get_user(user_id)
    
    if not result.success:
        raise create_error_response(
            module_id="standard.user_management",
            code=result.error["code"],
            message=result.error["message"],
            details=result.error.get("details"),
            status_code=404
        )
    
    return result.data
```

## Structured Logging

### 1. Error Logging Format
```json
{
    "timestamp": 1721131234.567,
    "time": "2025-07-16T10:30:00.567000",
    "error_code": "core_database_CONNECTION_FAILED",
    "message": "Failed to connect to database",
    "module_id": "core.database",
    "location": "database.py:145",
    "context": "error",
    "details": {
        "connection_string": "sqlite:///data/database/",
        "retry_count": 3,
        "last_error": "database is locked"
    }
}
```

### 2. Automatic Location Detection
```python
def _detect_calling_location():
    """Detect where the error is being logged from."""
    stack = inspect.stack()
    
    # Find first frame not in error handler
    for frame in stack[1:]:
        if frame.filename != __file__:
            filename = os.path.basename(frame.filename)
            return f"{filename}:{frame.lineno}"
    
    return "unknown_location"
```

### 3. Daily Log Rotation
```python
# Log files are automatically rotated by date
# Format: YYYYMMDD-error.jsonl
# Examples:
# data/error_logs/20250716-error.jsonl
# data/error_logs/20250717-error.jsonl
# data/error_logs/20250718-error.jsonl
```

## Error Message Generation

### 1. Standardized Error Messages
```python
def error_message(module_id, error_type, details, location=None):
    """Create standardized error message and log it."""
    
    # Auto-detect location if not provided
    if location is None:
        location = _detect_calling_location()
    
    # Generate error code
    module_prefix = module_id.replace('.', '_')
    error_code = f"{module_prefix}_{error_type}"
    
    # Log to structured log
    log_error(
        module_id=module_id,
        code=error_type,
        message=details,
        location=location
    )
    
    # Return formatted message
    return f"{error_code} - {details} in {location}"
```

### 2. Usage in Modules
```python
# In module code
logger.error(error_message(
    module_id="core.database",
    error_type="CONNECTION_FAILED",
    details="Database connection timeout after 30 seconds",
    location="database.py:setup_connection()"
))

# Output: "core_database_CONNECTION_FAILED - Database connection timeout after 30 seconds in database.py:setup_connection()"
```

## Error Registry Service

### 1. Error Code Registration
```python
class ErrorRegistry:
    """Centralized error code management."""
    
    async def register_error_code(self, module_id, code, description, examples=None):
        """Register an error code with documentation."""
        
    async def get_error_codes(self, module_id=None):
        """Get all registered error codes."""
        
    async def validate_error_code(self, module_id, code):
        """Validate that an error code is registered."""
```

### 2. Error Documentation
```python
# Register error codes for documentation
await error_registry.register_error_code(
    module_id="core.database",
    code="CONNECTION_FAILED",
    description="Database connection could not be established",
    examples=[
        {
            "scenario": "Database locked",
            "details": {"timeout": 30, "retry_count": 3},
            "resolution": "Retry with exponential backoff"
        }
    ]
)
```

## Database Models

### 1. Error Code Model
```python
class ErrorCode(FrameworkBase):
    """Model for storing registered error codes."""
    __tablename__ = "error_codes"
    
    id = Column(Integer, primary_key=True)
    module_id = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('module_id', 'code'),
    )
```

### 2. Error Documentation Model
```python
class ErrorDocument(FrameworkBase):
    """Model for storing error documentation."""
    __tablename__ = "error_documents"
    
    id = Column(Integer, primary_key=True)
    error_code_id = Column(Integer, ForeignKey('error_codes.id'))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
```

### 3. Error Examples Model
```python
class ErrorExample(FrameworkBase):
    """Model for storing error examples and resolutions."""
    __tablename__ = "error_examples"
    
    id = Column(Integer, primary_key=True)
    error_code_id = Column(Integer, ForeignKey('error_codes.id'))
    scenario = Column(String(200), nullable=False)
    example_details = Column(SQLiteJSON, nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
```

## Module Integration

### 1. Basic Error Handling
```python
# In module services
from modules.core.error_handler.utils import Result, error_message

class MyModuleService:
    async def process_data(self, data):
        try:
            # Process data
            result = await self.complex_operation(data)
            return Result.success(data=result)
        except ValidationError as e:
            return Result.error(
                code="VALIDATION_FAILED",
                message="Data validation failed",
                details={"validation_errors": e.errors}
            )
        except Exception as e:
            # Log error with context
            self.logger.error(error_message(
                module_id="standard.my_module",
                error_type="PROCESSING_ERROR",
                details=f"Failed to process data: {str(e)}"
            ))
            
            return Result.error(
                code="PROCESSING_ERROR",
                message="Data processing failed",
                details={"error": str(e)}
            )
```

### 2. API Error Handling
```python
# In module API endpoints
from modules.core.error_handler.utils import create_error_response

@router.post("/process")
async def process_data(data: DataRequest):
    result = await service.process_data(data.dict())
    
    if not result.success:
        raise create_error_response(
            module_id="standard.my_module",
            code=result.error["code"],
            message=result.error["message"],
            details=result.error.get("details"),
            status_code=400
        )
    
    return {"success": True, "data": result.data}
```

### 3. Error Registry Integration
```python
# In module initialization
async def initialize(app_context):
    # Register error codes
    error_registry = app_context.get_service("core.error_handler.service")
    
    await error_registry.register_error_code(
        module_id="standard.my_module",
        code="VALIDATION_FAILED",
        description="Input data validation failed",
        examples=[{
            "scenario": "Missing required field",
            "details": {"field": "email", "value": null},
            "resolution": "Provide valid email address"
        }]
    )
```

## Best Practices

### 1. Result Pattern Usage
```python
# ✅ CORRECT: Always use Result pattern
async def create_user(user_data):
    try:
        user = await database.create_user(user_data)
        return Result.success(data=user)
    except Exception as e:
        return Result.error(code="CREATE_FAILED", message=str(e))

# ❌ WRONG: Mixed return types
async def create_user(user_data):
    try:
        return await database.create_user(user_data)  # Returns User object
    except Exception as e:
        return None  # Returns None
```

### 2. Error Code Conventions
```python
# ✅ CORRECT: Descriptive error codes
"USER_NOT_FOUND"
"VALIDATION_FAILED"
"DATABASE_CONNECTION_ERROR"
"AUTHENTICATION_REQUIRED"

# ❌ WRONG: Generic or unclear codes
"ERROR"
"FAILED"
"BAD_REQUEST"
"OOPS"
```

### 3. Error Context
```python
# ✅ CORRECT: Include relevant context
return Result.error(
    code="USER_NOT_FOUND",
    message=f"User with ID {user_id} not found",
    details={
        "user_id": user_id,
        "search_criteria": {"active": True},
        "total_users": 150
    }
)

# ❌ WRONG: No context
return Result.error(
    code="USER_NOT_FOUND",
    message="User not found"
)
```

### 4. Logging Best Practices
```python
# ✅ CORRECT: Use error_message for consistent logging
logger.error(error_message(
    module_id="standard.user_management",
    error_type="USER_CREATE_FAILED",
    details=f"Failed to create user {user_data.email}: {str(e)}"
))

# ❌ WRONG: Inconsistent logging
logger.error(f"Error creating user: {str(e)}")
```

## Performance Considerations

### 1. Error Logging Optimization
```python
# Minimal overhead for error logging
def log_error(module_id, code, message, details=None, location=None):
    # Simple file append - no complex formatting
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(error_entry) + "\n")
```

### 2. Result Object Efficiency
```python
# Result objects are lightweight
class Result:
    def __init__(self, success=False, data=None, error=None):
        self.success = success  # Boolean
        self.data = data       # Any type
        self.error = error or {}  # Dict or empty dict
```

### 3. Location Detection Caching
```python
# Location detection is cached per frame
def _detect_calling_location():
    # Uses inspect.stack() only when needed
    # Returns simple string representation
    return f"{filename}:{line_number}"
```

## Error Response Examples

### 1. API Error Response
```json
{
    "status": "error",
    "code": "core_database_CONNECTION_FAILED",
    "message": "Database connection failed",
    "details": {
        "connection_string": "sqlite:///data/database/",
        "timeout": 30,
        "retry_count": 3
    }
}
```

### 2. Validation Error Response
```json
{
    "status": "error",
    "code": "standard_user_auth_VALIDATION_FAILED",
    "message": "User registration data is invalid",
    "details": {
        "validation_errors": [
            {
                "field": "email",
                "message": "Invalid email format"
            },
            {
                "field": "password",
                "message": "Password must be at least 8 characters"
            }
        ]
    }
}
```

### 3. Service Error Response
```json
{
    "status": "error",
    "code": "extensions_payment_processor_PAYMENT_FAILED",
    "message": "Payment processing failed",
    "details": {
        "payment_id": "pay_123456",
        "amount": 99.99,
        "currency": "USD",
        "error_code": "CARD_DECLINED",
        "retry_allowed": false
    }
}
```

## Related Documentation

- [Result Pattern](../patterns/result-pattern.md) - Detailed Result pattern documentation
- [Two-Phase Initialization](../patterns/two-phase-initialization.md) - Error handling during initialization
- [Database Module](database-module.md) - Error handling in database operations
- [Module Creation Guide](../module-creation-guide-v2.md) - Error handling in new modules
- [API Design Guidelines](../patterns/api-design-patterns.md) - Error handling in APIs

---

The Error Handler Module provides a comprehensive foundation for consistent error handling throughout the framework, ensuring that all modules handle errors uniformly while providing detailed context and structured logging for debugging and monitoring purposes.