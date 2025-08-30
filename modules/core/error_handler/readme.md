# Error Handler Module

**Version: 3.0.0**  
**Updated: August 10, 2025**  
**Status: Redesigned Architecture - Clean Separation**

## Purpose

The Error Handler module provides **pure JSONL processing and error analytics** for the Reality Anchor Hub Framework. Following a complete architectural redesign, it now operates with clean separation to prevent circular dependencies.

## ⚠️ **CRITICAL: Circular Dependency Prevention**

**The error handler module DOES NOT import `core.error_utils`** to prevent infinite loops:
- `core.error_utils` writes to JSONL files
- `error_handler` processes those same JSONL files
- If error_handler used error_utils → circular dependency!

**Solution**: Error handler uses direct logging to `app.log` only.

## New Architecture (v3.0.0)

### Clean Separation Pattern
```
core/error_utils.py          →  Pure utilities (zero dependencies)
   ↓ writes JSONL files
modules/core/error_handler/  →  JSONL processing service  
   ↓ uses direct logging only
data/logs/app.log            →  Error handler logs here
```

## Quick Reference

### For All Other Modules (NOT error_handler)
```python
from core.error_utils import Result, error_message, create_error_response
```

### For Error Handler Module Only
```python
# NO IMPORTS from core.error_utils! Use direct logging:
logger.error(f"ERROR_TYPE - Description of error in function_name()")
```

## What This Module Does

### Core Functionality
1. **JSONL File Processing**: Reads error logs from `data/error_logs/YYYYMMDD-error.jsonl`
2. **In-Memory Analytics**: Tracks error patterns, frequencies, and priorities
3. **Error Registry**: Maintains state of all error codes and their metadata
4. **Search & Analysis**: Provides API for error pattern analysis

### Service Methods Available
```python
error_service = app_context.get_service("core.error_handler.service")

# Process all error logs
result = await error_service.process_error_logs()

# Get prioritized errors for documentation
result = await error_service.get_prioritized_errors(limit=10)

# Search for specific error patterns
result = await error_service.search_errors("DATABASE", limit=5)
```

## Standard Error Patterns (For Other Modules)

### Service Layer Pattern
```python
from core.error_utils import Result, error_message

try:
    # Service logic here
    return Result.success(data=result_data)
except Exception as e:
    logger.error(error_message(
        module_id="standard.my_module",
        error_type="OPERATION_FAILED", 
        details=f"Operation failed: {str(e)}",
        location="method_name()"
    ))
    return Result.error(code="OPERATION_FAILED", message="Operation failed")
```

### API Layer Pattern
```python
from core.error_utils import create_error_response

# For API endpoints
if not valid_input:
    raise create_error_response(
        code="VALIDATION_ERROR",
        message="Invalid input data",
        status_code=422,
        details=validation_errors
    )
```

### Result Pattern
```python
from core.error_utils import Result

# Success case - ALWAYS use data= keyword
return Result.success(data={"id": 123, "name": "Example"})

# Error case
return Result.error(
    code="MODULE_ERROR_TYPE",
    message="Human-readable error message"
)
```

## Error Logging

Errors are automatically logged to structured JSONL files in `{DATA_DIR}/error_logs/` for analysis and pattern detection.

## Module Standards

### Module ID Format
Use dot notation: `"core.module_name"` or `"standard.module_name"`

### Error Types  
Use descriptive, action-oriented names:
- `"INITIALIZATION_FAILED"`
- `"VALIDATION_ERROR"`
- `"DEPENDENCY_MISSING"`
- `"OPERATION_TIMEOUT"`

### Location Format
Include function/method name: `"initialize()"`, `"process_data()"`

## Service Integration

The error handler provides a service for error analysis:
```python
error_service = app_context.get_service("core.error_handler.service")
```

## Three-Tier Architecture

- **API Layer**: Uses `create_error_response()` for HTTP responses
- **Service Layer**: Uses `Result` pattern + `error_message()` 
- **Database Layer**: Uses `error_message()` only (no Results or HTTP)

**Complete patterns and examples: [docs/error-handling-patterns.md](../../../docs/error-handling-patterns.md)**
