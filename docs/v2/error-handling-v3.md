# Error Handling v3.0.0 - Clean Separation Architecture

**Version: 3.0.0**  
**Updated: August 10, 2025**

## Overview

Error Handling v3.0.0 introduces a **clean separation architecture** that completely eliminates circular dependencies while providing powerful error management capabilities. The system is split into two distinct components that communicate via file-based data flow.

## Architecture Components

### 1. Pure Utilities (`core/error_utils.py`)
- **Zero framework dependencies**
- **Immediate availability** - can be imported anywhere, anytime
- **File-based logging** - writes structured JSONL error logs
- **No state management** - stateless utility functions

### 2. Service Module (`modules/core/error_handler/`)
- **Framework service module** - follows standard module patterns
- **JSONL processing** - reads and analyzes error log files
- **Analytics and monitoring** - error pattern detection and reporting
- **No circular dependencies** - uses direct logging instead of error_utils

## Clean Separation Pattern

```
Application Code → core/error_utils.py → JSONL Files → modules/core/error_handler/
       ↓                    ↓                ↓                    ↓
   Import utils        Write errors    File storage      Process & analyze
   Use Result         Log to JSONL      No direct        Generate insights
   Handle errors      Zero deps        connection        Monitor patterns
```

## Core Utilities (`core/error_utils.py`)

### Result Pattern

The Result pattern provides consistent success/error handling across all services:

```python
from core.error_utils import Result

# Success case - ALWAYS use data= keyword
def successful_operation():
    return Result.success(data={"id": 123, "name": "Example"})

# Error case
def failed_operation():
    return Result.error(
        code="MODULE_ERROR_TYPE",
        message="Human-readable error message",
        details={"additional": "context"}  # Optional
    )

# Usage
result = some_operation()
if result.success:
    data = result.data
    print(f"Success: {data}")
else:
    error = result.error
    print(f"Error {error['code']}: {error['message']}")
```

### Error Message Logging

Standardized error logging with automatic module detection:

```python
from core.error_utils import error_message
import logging

logger = logging.getLogger("standard.my_module")

# Automatic module and location detection
logger.error(error_message(
    "standard.my_module",           # Module ID
    "CONNECTION_FAILED",            # Error type
    "Unable to connect to database" # Details
))

# With explicit location
logger.error(error_message(
    "standard.my_module",
    "VALIDATION_ERROR", 
    "Missing required field",
    "validate_schema()"             # Location
))
```

**Generated log entry:**
```json
{
  "timestamp": "2025-08-10T10:30:15.123456Z",
  "module_id": "standard.my_module",
  "error_type": "CONNECTION_FAILED",
  "details": "Unable to connect to database",
  "location": "services.py:45",
  "session_id": "20250810_103000_abc12345"
}
```

### HTTP Error Responses

For API endpoints that need to return HTTP errors:

```python
from core.error_utils import create_error_response

@router.post("/process")
async def process_data(data: dict):
    # Validation error
    if not data:
        raise create_error_response(
            code="VALIDATION_ERROR",
            message="No data provided",
            status_code=422,
            details={"field": "data", "issue": "required"}
        )
    
    # Service error  
    result = await service.process(data)
    if not result.success:
        raise create_error_response(
            code=result.error["code"],
            message=result.error["message"], 
            status_code=400
        )
    
    return {"status": "success"}
```

## Service Layer Patterns

### Standard Service Method

```python
from core.error_utils import Result, error_message
import logging

MODULE_ID = "standard.my_module"
logger = logging.getLogger(MODULE_ID)

class MyService:
    async def process_item(self, item_id: int) -> Result:
        """Process an item by ID."""
        try:
            # Validate input
            if item_id <= 0:
                return Result.error(
                    "INVALID_ITEM_ID",
                    "Item ID must be positive"
                )
            
            # Business logic
            item = await self.get_item(item_id)
            if not item:
                return Result.error(
                    "ITEM_NOT_FOUND",
                    f"Item {item_id} not found"
                )
            
            # Process the item
            result = await self.perform_processing(item)
            
            return Result.success(data={
                "item_id": item_id,
                "processed": True,
                "result": result
            })
            
        except Exception as e:
            logger.error(error_message(
                MODULE_ID,
                "PROCESSING_FAILED",
                f"Failed to process item {item_id}: {str(e)}",
                "process_item()"
            ))
            return Result.error(
                "PROCESSING_FAILED",
                "Item processing failed"
            )
```

### Database Layer Pattern

```python
from core.error_utils import Result, error_message
import logging

logger = logging.getLogger("standard.my_module")

async def create_user(session, user_data) -> Result:
    """Create a new user in the database."""
    try:
        # Database operations
        user = User(**user_data)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        return Result.success(data={
            "user_id": user.id,
            "username": user.username
        })
        
    except IntegrityError as e:
        logger.error(error_message(
            "standard.my_module",
            "DUPLICATE_USER", 
            f"User already exists: {str(e)}",
            "create_user()"
        ))
        return Result.error(
            "DUPLICATE_USER",
            "Username already taken"
        )
        
    except Exception as e:
        logger.error(error_message(
            "standard.my_module",
            "DATABASE_ERROR",
            f"Database error creating user: {str(e)}",
            "create_user()"
        ))
        return Result.error(
            "DATABASE_ERROR", 
            "Failed to create user"
        )
```

## Error Handler Service Module

### Critical: Circular Dependency Prevention

**⚠️ IMPORTANT**: The error handler module **DOES NOT import core.error_utils** to prevent infinite loops:

```python
# ❌ NEVER DO THIS in error_handler module
from core.error_utils import error_message  # Creates circular dependency!

# ✅ DO THIS instead
logger.error(f"ERROR_TYPE - Description of error in function_name()")
```

**Why?**
- `core.error_utils` writes to JSONL files
- `error_handler` processes those same JSONL files  
- If error_handler used error_utils → circular dependency!

### Error Handler Service

The error handler service processes JSONL files for analytics:

```python
# modules/core/error_handler/services.py

class ErrorRegistry:
    """Pure JSONL processing service for error analysis."""
    
    async def process_error_logs(self) -> Result:
        """Process all error logs since last run."""
        try:
            # Process JSONL files
            log_files = glob.glob(os.path.join(self.log_dir, "*-error.jsonl"))
            
            for log_file in log_files:
                await self._process_log_file(log_file)
            
            return Result.success(data={
                "processed_files": len(log_files),
                "total_errors": len(self.errors)
            })
            
        except Exception as e:
            # Direct logging - no error_utils import!
            self.logger.error(f"LOG_PROCESSING_ERROR - Error processing logs: {str(e)} in process_error_logs()")
            return Result.error("LOG_PROCESSING_ERROR", "Failed to process logs")
```

### Service API Methods

```python
# Get prioritized errors for documentation
error_service = app_context.get_service("core.error_handler.service")

# Process new error logs
result = await error_service.process_error_logs()

# Get highest priority errors
result = await error_service.get_prioritized_errors(limit=10)

# Search for specific error patterns  
result = await error_service.search_errors("DATABASE", limit=5)
```

## Three-Tier Architecture

### API Layer (FastAPI Endpoints)
```python
from core.error_utils import create_error_response

@router.post("/users")
async def create_user(user_data: UserCreate):
    result = await user_service.create_user(user_data.dict())
    
    if not result.success:
        raise create_error_response(
            code=result.error["code"],
            message=result.error["message"],
            status_code=400
        )
    
    return result.data
```

### Service Layer (Business Logic)
```python
from core.error_utils import Result, error_message

async def create_user(self, user_data: dict) -> Result:
    try:
        # Business logic
        result = await self.database.create_user(user_data)
        return result
        
    except Exception as e:
        logger.error(error_message(
            MODULE_ID, 
            "SERVICE_ERROR",
            f"Service error: {str(e)}"
        ))
        return Result.error("SERVICE_ERROR", "User creation failed")
```

### Database Layer (Data Access)
```python  
from core.error_utils import Result, error_message

async def create_user(self, user_data: dict) -> Result:
    try:
        # Database operations
        user = User(**user_data)
        session.add(user)
        await session.commit()
        
        return Result.success(data={"user_id": user.id})
        
    except Exception as e:
        logger.error(error_message(
            MODULE_ID,
            "DATABASE_ERROR", 
            f"Database error: {str(e)}"
        ))
        return Result.error("DATABASE_ERROR", "Database operation failed")
```

## Error Code Conventions

### Naming Pattern
Use descriptive, action-oriented names:
```python
# Good examples
"CONNECTION_FAILED"
"VALIDATION_ERROR"  
"ITEM_NOT_FOUND"
"PERMISSION_DENIED"
"OPERATION_TIMEOUT"

# Avoid generic names
"ERROR"
"FAILED"
"BAD"
```

### Module Prefixes
The error logging automatically creates prefixed error codes:
```python
# Input
error_message("standard.user_manager", "VALIDATION_ERROR", "Invalid email")

# Generated error code in logs
"standard_user_manager_VALIDATION_ERROR"
```

### Recommended Categories

**Authentication & Authorization:**
- `AUTH_TOKEN_INVALID`
- `AUTH_TOKEN_EXPIRED`
- `PERMISSION_DENIED`
- `USER_NOT_AUTHENTICATED`

**Validation:**
- `VALIDATION_ERROR`
- `INVALID_INPUT_FORMAT`
- `REQUIRED_FIELD_MISSING`
- `VALUE_OUT_OF_RANGE`

**Database:**
- `DATABASE_CONNECTION_FAILED`
- `DATABASE_TIMEOUT`
- `RECORD_NOT_FOUND`
- `DUPLICATE_RECORD`
- `CONSTRAINT_VIOLATION`

**External Services:**
- `EXTERNAL_API_TIMEOUT`
- `EXTERNAL_SERVICE_UNAVAILABLE`
- `API_RATE_LIMIT_EXCEEDED`
- `INVALID_API_RESPONSE`

**Business Logic:**
- `INSUFFICIENT_BALANCE`
- `ITEM_OUT_OF_STOCK`
- `WORKFLOW_STATE_INVALID`
- `OPERATION_NOT_ALLOWED`

## Error Log Structure

### JSONL Format
Each error creates one line in the daily error log file:

```json
{
  "timestamp": "2025-08-10T10:30:15.123456Z",
  "module_id": "standard.user_manager", 
  "error_type": "VALIDATION_ERROR",
  "details": "Invalid email format: not-an-email",
  "location": "services.py:145",
  "session_id": "20250810_103000_abc12345"
}
```

### File Organization
```
data/error_logs/
├── 20250810-error.jsonl     # Today's errors
├── 20250809-error.jsonl     # Yesterday's errors
└── error_registry_state.json # Processing state
```

## Best Practices

### Do:
✅ **Use Result pattern** for all service methods that can fail
✅ **Import error_utils** in all modules except error_handler
✅ **Log errors immediately** when they occur
✅ **Use descriptive error codes** that explain what happened
✅ **Include context** in error details (IDs, values, etc.)
✅ **Handle errors gracefully** - don't let exceptions bubble up
✅ **Use appropriate HTTP status codes** for API errors

### Don't:  
❌ **Import core.error_utils** in the error_handler module
❌ **Skip error logging** - always log errors for analysis
❌ **Use generic error codes** like "ERROR" or "FAILED"
❌ **Expose internal details** in user-facing error messages
❌ **Log sensitive data** like passwords or API keys
❌ **Create circular dependencies** between error utilities and services
❌ **Ignore Result.success** checks - always check before using data

### Error Handler Module:
❌ **Never import core.error_utils** in error_handler service
✅ **Use direct logging** with explicit error format
✅ **Process JSONL files** for analytics and monitoring
✅ **Maintain clean separation** from utility functions

## Migration from v2

### Old Pattern (v2)
```python
# Old way - could create circular dependencies
from modules.core.error_handler.utils import error_message, Result
```

### New Pattern (v3.0.0)
```python
# New way - clean separation
from core.error_utils import error_message, Result, create_error_response

# For error_handler module only - no imports!
logger.error(f"ERROR_TYPE - Description in function_name()")
```

## Monitoring and Analytics

The error handler service provides:

- **Error frequency tracking** - which errors occur most often
- **Priority scoring** - based on frequency, recency, and impact
- **Pattern detection** - similar errors across modules
- **Real-time processing** - JSONL files processed continuously
- **Search capabilities** - find specific error patterns
- **Documentation scaffolding** - templates for error documentation

### Service Access
```python
error_service = app_context.get_service("core.error_handler.service")

# Get top errors that need documentation
priority_errors = await error_service.get_prioritized_errors(limit=10)

# Search for database-related errors
db_errors = await error_service.search_errors("DATABASE", limit=5)

# Process recent error logs
process_result = await error_service.process_error_logs()
```

## Benefits of v3.0.0 Architecture

1. **Zero Circular Dependencies** - Clean file-based data flow prevents loops
2. **Immediate Availability** - Core utilities available from import, no initialization required
3. **Powerful Analytics** - Service module provides sophisticated error analysis
4. **Framework Integration** - Follows standard module patterns and service container
5. **Performance** - Lightweight utilities, background processing for analytics
6. **Reliability** - Error logging works even if error handler service fails
7. **Scalability** - JSONL files can be processed by external tools if needed
8. **Maintainability** - Clear separation of concerns, well-defined interfaces

The v3.0.0 error handling architecture provides industrial-strength error management while maintaining clean code architecture and preventing the circular dependency issues that plagued earlier versions.