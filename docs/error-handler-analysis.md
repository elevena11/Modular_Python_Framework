# Error Handler Analysis - Standardized Error Management

## Overview

The core.error_handler module provides standardized error handling, logging, and analysis capabilities with a unique dual-access pattern supporting both direct imports and service registry.

**Location**: `modules/core/error_handler/`

## Dual Access Architecture

### 1. Direct Import Pattern (Primary Usage)
Most modules access error utilities through direct imports for immediate availability:

```python
# Direct imports - available immediately after module loading
from modules.core.error_handler.utils import error_message, create_error_response, Result
```

**Benefits**:
- ✅ Available during Phase 1 initialization
- ✅ No dependency on service registry
- ✅ Can be used by bootstrap modules (core.database)
- ✅ Immediate access for error handling

### 2. Service Registry Pattern (Advanced Features)
Advanced error analysis features available through service registry:

```python
# Service registry access - available after Phase 2
error_service = app_context.get_service("core.error_handler.service")
error_patterns = await error_service.analyze_error_patterns()
```

**Benefits**:
- ✅ Error pattern analysis
- ✅ Knowledge building from error logs
- ✅ Database storage of error metrics
- ✅ Background processing capabilities

## Core Utilities (Direct Import)

### 1. Result Class - Standardized Return Pattern

**Purpose**: Provides consistent success/error return pattern for all service methods.

```python
from modules.core.error_handler.utils import Result

# Success case - ALWAYS use 'data=' keyword
def get_data_from_api(identifier):
    try:
        data = fetch_data_from_api(identifier)
        return Result.success(data={"identifier": identifier, "value": data})
    except APIException as e:
        return Result.error(code="API_ERROR", message=f"Failed to fetch data: {str(e)}")

# Usage
result = get_data_from_api("example")
if result.success:
    retrieved_data = result.data
    logger.info(f"Retrieved data: {retrieved_data['value']}")
else:
    logger.error(f"Error: {result.error['code']} - {result.error['message']}")
```

**Critical Requirements**:
- Always use `data=` keyword when calling `Result.success()`
- Always check `result.success` before accessing `result.data`
- Never return raw dictionaries from service methods

### 2. error_message() - Standardized Error Logging

**Purpose**: Creates consistent, structured error messages across all modules.

```python
from modules.core.error_handler.utils import error_message

# Standard error logging
logger.error(error_message(
    module_id="standard.example_module",
    error_type="API_RATE_LIMIT",
    details="External API rate limit exceeded",
    location="fetch_data()",
    additional_data={"identifier": "example", "retry_count": 3}
))
```

**Output Format**:
```
[standard.example_module] API_RATE_LIMIT in fetch_data(): External API rate limit exceeded | Data: {"identifier": "example", "retry_count": 3}
```

### 3. create_error_response() - HTTP Error Responses

**Purpose**: Creates standardized HTTP error responses for FastAPI endpoints.

```python
from modules.core.error_handler.utils import create_error_response
from fastapi import HTTPException

# In FastAPI route handler
@router.get("/data/{identifier}")
async def get_data(identifier: str):
    try:
        result = await data_service.get_data(identifier)
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    module_id="standard.example_module",
                    code="DATA_NOT_FOUND",
                    message=f"Data not available for {identifier}",
                    status_code=400
                )
            )
        return result.data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                module_id="standard.example_module",
                code="INTERNAL_ERROR",
                message="Internal server error",
                status_code=500
            )
        )
```

## Service Registry Features (Advanced)

### ErrorRegistry Service

**Access Pattern**:
```python
# Get error registry service
error_service = app_context.get_service("core.error_handler.service")

# Advanced error analysis
patterns = await error_service.analyze_error_patterns()
recent_errors = await error_service.get_recent_errors(hours=24)
```

### Database Models

**ErrorCode**: Tracks error type definitions and frequency
```python
class ErrorCode(Base):
    __tablename__ = "error_codes"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, index=True)
    module_id = Column(String(100), index=True)
    description = Column(Text)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    occurrence_count = Column(Integer, default=1)
```

**ErrorDocument**: Stores error context and solutions
```python
class ErrorDocument(Base):
    __tablename__ = "error_documents"
    
    id = Column(Integer, primary_key=True)
    error_code_id = Column(Integer, ForeignKey("error_codes.id"))
    context = Column(SQLiteJSON)  # Error context data
    solution = Column(Text)       # Known solutions
    tags = Column(SQLiteJSON)     # Categorization tags
```

### Background Processing

**Error Log Analysis**:
- Monitors `data/error_logs/` directory
- Processes error patterns in background
- Builds knowledge base from recurring errors
- Generates alerts for critical error patterns

## Integration Patterns for Application Modules

### 1. Standard Error Handling in Services

```python
# example_module/services.py
from modules.core.error_handler.utils import error_message, Result
import logging

MODULE_ID = "standard.example_module"
logger = logging.getLogger(MODULE_ID)

class ExampleModuleService:
    async def fetch_external_data(self, identifier: str):
        try:
            # API call logic
            data = await self.external_client.get_data(identifier=identifier)
            return Result.success(data={"identifier": identifier, "value": data["value"]})
            
        except ExternalAPIException as e:
            # Structured error logging
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="EXTERNAL_API_ERROR",
                details=f"External API error for {identifier}: {str(e)}",
                location="fetch_external_data()",
                additional_data={"identifier": identifier, "error_code": e.code}
            ))
            return Result.error(
                code="EXTERNAL_API_ERROR", 
                message=f"Failed to fetch {identifier} data from external source"
            )
            
        except Exception as e:
            # Unexpected error logging
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="UNEXPECTED_ERROR",
                details=f"Unexpected error in fetch_external_data: {str(e)}",
                location="fetch_external_data()",
                additional_data={"identifier": identifier}
            ))
            return Result.error(
                code="INTERNAL_ERROR", 
                message="Internal error occurred"
            )
```

### 2. FastAPI Route Error Handling

```python
# example_module/api.py
from fastapi import APIRouter, HTTPException
from modules.core.error_handler.utils import create_error_response, error_message
import logging

MODULE_ID = "standard.example_module"
logger = logging.getLogger(MODULE_ID)
router = APIRouter(prefix="/data", tags=["data"])

@router.get("/value/{identifier}")
async def get_data_value(identifier: str):
    try:
        result = await data_service.fetch_external_data(identifier)
        
        if not result.success:
            # Service returned error - log and convert to HTTP error
            logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="SERVICE_ERROR",
                details=f"Service error for {identifier}: {result.error.get('message')}",
                location="get_data_value()"
            ))
            
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    module_id=MODULE_ID,
                    code=result.error.get("code", "SERVICE_ERROR"),
                    message=result.error.get("message", "Service error"),
                    status_code=400
                )
            )
        
        return {"success": True, "data": result.data}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="ROUTE_ERROR",
            details=f"Unexpected error in get_data_value: {str(e)}",
            location="get_data_value()",
            additional_data={"identifier": identifier}
        ))
        
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                module_id=MODULE_ID,
                code="INTERNAL_ERROR",
                message="Internal server error",
                status_code=500
            )
        )
```

### 3. Error Recovery Patterns

```python
# Retry logic with error tracking
async def fetch_with_retry(self, operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = await operation()
            if result.success:
                return result
                
            # Log retry attempt
            logger.warning(error_message(
                module_id=MODULE_ID,
                error_type="RETRY_ATTEMPT",
                details=f"Retry attempt {attempt + 1}/{max_retries}",
                location="fetch_with_retry()",
                additional_data={"error": result.error}
            ))
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        except Exception as e:
            logger.error(error_message(
                module_id=MODULE_ID,
                error_type="RETRY_EXCEPTION",
                details=f"Exception on attempt {attempt + 1}: {str(e)}",
                location="fetch_with_retry()"
            ))
            
            if attempt == max_retries - 1:
                return Result.error(
                    code="MAX_RETRIES_EXCEEDED",
                    message=f"Operation failed after {max_retries} attempts"
                )
    
    return Result.error(code="RETRY_FAILED", message="All retry attempts failed")
```

## Common Error Categories

### 1. Data Collection Errors
- `API_RATE_LIMIT`: Rate limiting from external APIs
- `API_TIMEOUT`: API request timeouts
- `DATA_VALIDATION_ERROR`: Invalid data received from APIs
- `RESOURCE_NOT_FOUND`: Invalid resource identifier

### 2. Processing Errors  
- `INSUFFICIENT_DATA`: Not enough data for processing
- `CALCULATION_ERROR`: Mathematical computation errors
- `PROCESSING_FAILED`: Data processing failures
- `VALIDATION_ERROR`: Input validation errors

### 3. Communication Errors
- `MESSAGE_SEND_FAILED`: Failed to send messages
- `NOTIFICATION_RATE_LIMIT`: Too many notifications in time period
- `COMMUNICATION_ERROR`: General communication failures

### 4. Database Errors
- `DB_CONNECTION_FAILED`: Database connection issues
- `DB_QUERY_ERROR`: SQL query execution errors
- `DATA_INTEGRITY_ERROR`: Database constraint violations

## Configuration Settings

### Module Settings for Error Handler
```python
# error_handler module settings
{
    "log_retention_days": 30,
    "error_analysis_enabled": True,
    "background_processing": True,
    "alert_on_critical_errors": True,
    "max_error_reports_per_hour": 10
}
```

## Benefits for Crypto Project

### Immediate Benefits (Direct Import)
- ✅ Consistent error logging across all modules
- ✅ Standardized Result pattern for all operations
- ✅ Professional HTTP error responses
- ✅ Easy debugging with structured error messages

### Advanced Benefits (Service Registry)
- ✅ Error pattern analysis for system health monitoring
- ✅ Knowledge building from recurring issues
- ✅ Automated error categorization and tagging
- ✅ Historical error trend analysis

This error handling system provides both immediate utility and advanced analytics capabilities, essential for building robust applications on the framework.