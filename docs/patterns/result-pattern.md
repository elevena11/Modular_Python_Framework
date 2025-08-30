# Result Pattern

The Result Pattern is a fundamental design pattern used throughout the framework to provide consistent, type-safe error handling. It ensures that all service operations return a standardized object that clearly indicates success or failure, along with relevant data or error information.

## Overview

The Result Pattern addresses the common problem of inconsistent error handling in applications by providing a unified way to handle operations that can succeed or fail. Instead of using exceptions, mixed return types, or unclear success indicators, all operations return a Result object that contains either success data or error information.

## The Problem

Without the Result Pattern, error handling becomes inconsistent and error-prone:

```python
# PROBLEMATIC: Inconsistent error handling
def get_user(user_id):
    try:
        user = database.get_user(user_id)
        return user  # Returns User object on success
    except NotFoundError:
        return None  # Returns None on not found
    except DatabaseError:
        raise  # Raises exception on database error

def create_user(user_data):
    try:
        user = database.create_user(user_data)
        return user  # Returns User object on success
    except ValidationError as e:
        return {"error": str(e)}  # Returns dict on validation error
    except DatabaseError:
        return False  # Returns boolean on database error
```

## The Solution

The Result Pattern provides a consistent, type-safe approach to error handling:

```python
# SOLUTION: Consistent Result pattern
async def get_user(user_id) -> Result:
    try:
        user = await database.get_user(user_id)
        if user:
            return Result.success(data=user)
        else:
            return Result.error(
                code="USER_NOT_FOUND",
                message=f"User with ID {user_id} not found"
            )
    except DatabaseError as e:
        return Result.error(
            code="DATABASE_ERROR",
            message="Database operation failed",
            details={"error": str(e)}
        )

async def create_user(user_data) -> Result:
    try:
        user = await database.create_user(user_data)
        return Result.success(data=user)
    except ValidationError as e:
        return Result.error(
            code="VALIDATION_ERROR",
            message="User data validation failed",
            details={"validation_errors": e.errors}
        )
    except DatabaseError as e:
        return Result.error(
            code="DATABASE_ERROR",
            message="Failed to create user",
            details={"error": str(e)}
        )
```

## Result Class Design

### Core Structure
```python
class Result:
    """Standard result object for all service operations."""
    
    def __init__(self, success=False, data=None, error=None):
        self.success = success  # Boolean: True for success, False for error
        self.data = data       # Any: Data returned on success
        self.error = error or {}  # Dict: Error information on failure
    
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

### Success Results
```python
# Simple success with data
result = Result.success(data={"user_id": 123, "name": "John"})

# Success with complex data
result = Result.success(data={
    "users": [user1, user2, user3],
    "total": 150,
    "page": 1
})

# Success with no data
result = Result.success(data=None)
```

### Error Results
```python
# Simple error
result = Result.error(
    code="USER_NOT_FOUND",
    message="User not found"
)

# Error with details
result = Result.error(
    code="VALIDATION_ERROR",
    message="Input validation failed",
    details={
        "field": "email",
        "value": "invalid-email",
        "reason": "Invalid email format"
    }
)

# Error with complex details
result = Result.error(
    code="DATABASE_ERROR",
    message="Database operation failed",
    details={
        "query": "SELECT * FROM users WHERE id = ?",
        "parameters": [123],
        "error": "Connection timeout",
        "retry_count": 3
    }
)
```

## Usage Patterns

### 1. Basic Service Method
```python
class UserService:
    async def get_user(self, user_id: int) -> Result:
        """Get a user by ID."""
        try:
            user = await self.database.get_user(user_id)
            if user:
                return Result.success(data=user)
            else:
                return Result.error(
                    code="USER_NOT_FOUND",
                    message=f"User with ID {user_id} not found"
                )
        except Exception as e:
            return Result.error(
                code="DATABASE_ERROR",
                message="Failed to retrieve user",
                details={"error": str(e)}
            )
```

### 2. Result Consumption
```python
# Consuming a Result
async def handle_user_request(user_id: int):
    result = await user_service.get_user(user_id)
    
    if result.success:
        user = result.data
        return {"status": "success", "user": user}
    else:
        error = result.error
        return {
            "status": "error",
            "code": error["code"],
            "message": error["message"]
        }
```

### 3. Chaining Operations
```python
async def create_user_with_profile(user_data: dict) -> Result:
    """Create user and profile in sequence."""
    
    # Create user
    user_result = await user_service.create_user(user_data)
    if not user_result.success:
        return user_result  # Return error from user creation
    
    user = user_result.data
    
    # Create profile
    profile_result = await profile_service.create_profile(user.id, user_data)
    if not profile_result.success:
        # Rollback user creation
        await user_service.delete_user(user.id)
        return profile_result  # Return error from profile creation
    
    # Return success with both user and profile
    return Result.success(data={
        "user": user,
        "profile": profile_result.data
    })
```

### 4. Error Handling in APIs
```python
from modules.core.error_handler.utils import create_error_response

@router.get("/users/{user_id}")
async def get_user_endpoint(user_id: int):
    result = await user_service.get_user(user_id)
    
    if result.success:
        return {"user": result.data}
    else:
        # Convert Result error to HTTP error
        raise create_error_response(
            module_id="standard.user_management",
            code=result.error["code"],
            message=result.error["message"],
            details=result.error.get("details"),
            status_code=404 if result.error["code"] == "USER_NOT_FOUND" else 500
        )
```

## Error Code Conventions

### 1. Error Code Structure
```python
# Format: NOUN_VERB_ADJECTIVE or NOUN_STATE
"USER_NOT_FOUND"        # Resource not found
"VALIDATION_FAILED"     # Input validation error
"DATABASE_ERROR"        # Database operation error
"PERMISSION_DENIED"     # Authorization error
"OPERATION_TIMEOUT"     # Timeout error
"INVALID_PARAMETER"     # Parameter validation error
"RESOURCE_CONFLICT"     # Resource already exists
"EXTERNAL_API_ERROR"    # External service error
```

### 2. Error Code Categories
```python
# Not Found Errors
"USER_NOT_FOUND"
"RESOURCE_NOT_FOUND"
"ENDPOINT_NOT_FOUND"

# Validation Errors
"VALIDATION_FAILED"
"INVALID_INPUT"
"MISSING_PARAMETER"
"PARAMETER_TOO_LONG"

# Permission Errors
"PERMISSION_DENIED"
"AUTHENTICATION_REQUIRED"
"INSUFFICIENT_PRIVILEGES"

# System Errors
"DATABASE_ERROR"
"NETWORK_ERROR"
"TIMEOUT_ERROR"
"INTERNAL_ERROR"
```

## Advanced Usage

### 1. Custom Result Types
```python
class PaginatedResult(Result):
    """Result with pagination information."""
    
    @classmethod
    def success(cls, data=None, page=1, total=0, page_size=20):
        result = super().success(data=data)
        result.pagination = {
            "page": page,
            "total": total,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        return result

# Usage
result = PaginatedResult.success(
    data=users,
    page=1,
    total=150,
    page_size=20
)
```

### 2. Result Validation
```python
def validate_result(result: Result) -> None:
    """Validate a Result object."""
    if not isinstance(result, Result):
        raise TypeError("Expected Result object")
    
    if result.success:
        # Success validation
        if result.error:
            raise ValueError("Success result should not have error")
    else:
        # Error validation
        if not result.error:
            raise ValueError("Error result must have error information")
        
        if "code" not in result.error:
            raise ValueError("Error must have code")
        
        if "message" not in result.error:
            raise ValueError("Error must have message")
```

### 3. Result Logging
```python
def log_result(result: Result, operation: str, logger) -> None:
    """Log a Result object."""
    if result.success:
        logger.info(f"{operation} succeeded")
        if result.data:
            logger.debug(f"{operation} data: {result.data}")
    else:
        error = result.error
        logger.error(f"{operation} failed: {error['code']} - {error['message']}")
        if error.get("details"):
            logger.debug(f"{operation} error details: {error['details']}")
```

## Best Practices

### 1. Always Use Result for Operations That Can Fail
```python
# ✅ CORRECT: Use Result for operations that can fail
async def create_user(user_data: dict) -> Result:
    try:
        user = await database.create_user(user_data)
        return Result.success(data=user)
    except ValidationError as e:
        return Result.error(code="VALIDATION_ERROR", message=str(e))

# ❌ WRONG: Mix return types
async def create_user(user_data: dict):
    try:
        return await database.create_user(user_data)  # Returns User on success
    except ValidationError as e:
        return None  # Returns None on error
```

### 2. Use Descriptive Error Codes
```python
# ✅ CORRECT: Descriptive error codes
return Result.error(
    code="EMAIL_ALREADY_EXISTS",
    message="A user with this email already exists"
)

# ❌ WRONG: Generic error codes
return Result.error(
    code="ERROR",
    message="Something went wrong"
)
```

### 3. Include Relevant Error Details
```python
# ✅ CORRECT: Include helpful details
return Result.error(
    code="VALIDATION_ERROR",
    message="User data validation failed",
    details={
        "field": "email",
        "value": user_data.get("email"),
        "expected": "Valid email address",
        "validation_rules": ["required", "email_format", "max_length_255"]
    }
)

# ❌ WRONG: No details
return Result.error(
    code="VALIDATION_ERROR",
    message="Validation failed"
)
```

### 4. Check Success Before Accessing Data
```python
# ✅ CORRECT: Check success first
result = await user_service.get_user(user_id)
if result.success:
    user = result.data
    # Process user
else:
    error = result.error
    # Handle error

# ❌ WRONG: Direct data access
result = await user_service.get_user(user_id)
user = result.data  # May be None if error occurred
```

### 5. Use Proper Error Handling in Consumers
```python
# ✅ CORRECT: Proper error handling
async def handle_user_creation(user_data: dict):
    result = await user_service.create_user(user_data)
    
    if result.success:
        user = result.data
        logger.info(f"User created successfully: {user.id}")
        return {"user_id": user.id, "status": "created"}
    else:
        error = result.error
        logger.error(f"User creation failed: {error['code']} - {error['message']}")
        
        # Handle specific error types
        if error["code"] == "EMAIL_ALREADY_EXISTS":
            return {"error": "Email already in use", "status": "conflict"}
        elif error["code"] == "VALIDATION_ERROR":
            return {"error": "Invalid data", "details": error["details"], "status": "bad_request"}
        else:
            return {"error": "Internal error", "status": "internal_error"}
```

## Usage Validation

The Result class includes validation to catch common mistakes:

### 1. Data Keyword Warning
```python
# ✅ CORRECT: Use data= keyword
return Result.success(data={"user_id": 123})

# ❌ GENERATES WARNING: Missing data= keyword
return Result.success({"user_id": 123})
```

### 2. Dictionary Access Warning
```python
# ✅ CORRECT: Use attribute access
if result.success:
    data = result.data
    error = result.error

# ❌ GENERATES WARNING: Dictionary-style access
if result["success"]:
    data = result["data"]
    error = result["error"]
```

### 3. Result Wrapping Detection
```python
# ✅ CORRECT: Return Result directly
async def operation() -> Result:
    result = await some_other_operation()
    return result

# ❌ ERROR: Wrapping Result in Result
async def operation() -> Result:
    result = await some_other_operation()
    return Result.success(data=result)  # TypeError if result is Result
```

## Testing with Results

### 1. Testing Success Cases
```python
async def test_get_user_success():
    """Test successful user retrieval."""
    user_service = UserService()
    
    result = await user_service.get_user(123)
    
    assert result.success is True
    assert result.data is not None
    assert result.error == {}
    assert result.data["id"] == 123
```

### 2. Testing Error Cases
```python
async def test_get_user_not_found():
    """Test user not found error."""
    user_service = UserService()
    
    result = await user_service.get_user(999)
    
    assert result.success is False
    assert result.data is None
    assert result.error["code"] == "USER_NOT_FOUND"
    assert "not found" in result.error["message"]
```

### 3. Testing Error Details
```python
async def test_create_user_validation_error():
    """Test validation error with details."""
    user_service = UserService()
    
    result = await user_service.create_user({"email": "invalid"})
    
    assert result.success is False
    assert result.error["code"] == "VALIDATION_ERROR"
    assert "details" in result.error
    assert "email" in result.error["details"]
```

## Performance Considerations

### 1. Result Object Overhead
Result objects are lightweight and have minimal overhead:
```python
# Memory usage: ~200 bytes per Result object
result = Result.success(data=user)  # Small object
result = Result.error(code="ERROR", message="Failed")  # Small object
```

### 2. Error Information Size
Keep error details reasonable to avoid memory issues:
```python
# ✅ GOOD: Reasonable error details
return Result.error(
    code="VALIDATION_ERROR",
    message="Validation failed",
    details={"field": "email", "error": "Invalid format"}
)

# ❌ BAD: Excessive error details
return Result.error(
    code="VALIDATION_ERROR",
    message="Validation failed",
    details={"entire_request": large_object}  # Avoid large objects
)
```

## Related Patterns

- **[Two-Phase Initialization](two-phase-initialization.md)**: Using Result in initialization
- **[Error Handling Patterns](error-handling-patterns.md)**: Converting Results to HTTP errors
- **[Database Patterns](database-patterns.md)**: Using Result in database operations
- **[Service Registration](service-registration.md)**: Result pattern in service methods

---

The Result Pattern is fundamental to the framework's error handling strategy and ensures consistent, predictable behavior across all modules. Following this pattern is essential for creating robust, maintainable services.