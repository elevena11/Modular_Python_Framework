# Error Handling System

The framework provides a standardized error handling system with three main utilities for different use cases.

## Three Error Handling Utilities

### 1. `Result` - Business Logic (Most Common)
```python
from core.error_utils import Result

async def create_user(name: str) -> Result:
    if not name:
        return Result.error("INVALID_NAME", "Name cannot be empty")
    # Success case
    return Result.success(data={"id": 123, "name": name})
```
**Use for**: Service methods, business logic, operations that can succeed or fail

### 2. `create_error_response()` - API Endpoints
```python
from core.error_utils import create_error_response

@router.post("/users")
async def create_user_endpoint():
    result = await user_service.create_user(name)
    if not result.success:
        raise create_error_response(
            module_id="user.service",
            code=result.code or "CREATE_FAILED",
            message=result.message or "User creation failed"
        )
    return result.data
```
**Use for**: Converting Result errors to HTTP exceptions in API endpoints

### 3. `error_message()` - Structured Error Logging with Context
```python
from core.error_utils import error_message

def process_file(file_path: str):
    if not os.path.exists(file_path):
        # error_message() writes to both JSONL logs AND returns formatted string
        # ALWAYS include context for structured debugging information
        logger.error(error_message(
            module_id="file.processor",
            error_type="FILE_NOT_FOUND",
            details=f"File {file_path} does not exist",
            location="process_file()",
            context={
                "file_path": file_path,
                "attempted_operation": "read",
                "error_type": "FILE_NOT_FOUND"
            }
        ))
        return Result.error("FILE_NOT_FOUND", "File not found")
```
**Use for**:
- Structured error tracking in JSONL format for analysis
- Human-readable logs in app.log for debugging
- Automatic location detection and error categorization
- Critical infrastructure and service errors
- **Always include context parameter** - provides structured debugging information logged separately in JSONL

---

## Core Concepts

### Result Pattern
Instead of throwing exceptions for business logic errors, the framework uses the Result pattern:

- **Explicit error handling** - Errors are values, not exceptions
- **Consistent structure** - All operations return Result objects
- **Rich error context** - Detailed error information for debugging
- **No hidden exceptions** - Business logic errors are visible in return types

### Error Types
- **System errors** - Framework and infrastructure failures (still use exceptions)
- **Business logic errors** - Domain-specific failures (use Result pattern)
- **Validation errors** - Input validation failures (use Result pattern)
- **External service errors** - API calls, database operations (use Result pattern)

## The Result Class

### Basic Usage

```python
from core.error_utils import Result

# Success case
def create_user(name: str, email: str) -> Result:
    if not name:
        return Result.error("INVALID_NAME", "Name cannot be empty")
    
    if not "@" in email:
        return Result.error("INVALID_EMAIL", "Email format is invalid")
    
    # Create user logic here
    user_data = {"id": 123, "name": name, "email": email}
    
    return Result.success(data=user_data)

# Using the result
result = create_user("John", "john@example.com")

if result.success:
    print(f"User created: {result.data}")
else:
    print(f"Error: {result.message} (Code: {result.code})")
```

### Result Properties

```python
class Result:
    # Core attributes
    success: bool          # True if operation succeeded
    data: Any             # Success data (None if error)
    error: dict           # Error dictionary with code, message, details (empty if success)

    # Intuitive property access (NEW)
    @property
    code: str             # Error code (None if success)
    @property
    message: str          # Error message (None if success)
    @property
    details: Any          # Error details (None if success)
```

### Creating Results

```python
# Success with data
result = Result.success(data={"id": 123, "name": "John"})
result = Result.success(data="Operation completed")
result = Result.success()  # Success with no data

# Error with code and message
result = Result.error("USER_NOT_FOUND", "User does not exist")

# Error with additional details
result = Result.error(
    code="VALIDATION_FAILED",
    message="Input validation failed",
    details={
        "field": "email",
        "value": "invalid-email",
        "constraint": "must contain @"
    }
)
```

## Error Handling Patterns

### Service Layer Error Handling

```python
# modules/standard/user_manager/services.py
from core.error_utils import Result
from sqlalchemy.exc import IntegrityError

class UserManagerService:
    
    async def create_user(self, name: str, email: str) -> Result:
        """Create a new user with comprehensive error handling."""
        
        # Input validation
        if not name or not name.strip():
            return Result.error(
                "INVALID_NAME",
                "Name is required and cannot be empty"
            )
        
        if not email or "@" not in email:
            return Result.error(
                "INVALID_EMAIL", 
                "Valid email address is required",
                details={"provided_email": email}
            )
        
        try:
            async with self.app_context.database.integrity_session("user_manager", "create_user") as session:
                # Check if user already exists
                existing = await session.execute(
                    select(User).where(User.email == email)
                )
                
                if existing.first():
                    return Result.error(
                        "USER_EXISTS",
                        f"User with email {email} already exists",
                        details={"email": email}
                    )
                
                # Create new user
                user = User(name=name.strip(), email=email.lower())
                session.add(user)
                await session.commit()
                
                return Result.success(data={
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "created_at": user.created_at.isoformat()
                })
                
        except IntegrityError as e:
            # Database constraint violation
            return Result.error(
                "DATABASE_CONSTRAINT",
                "Database constraint violation",
                details={"database_error": str(e)}
            )
            
        except Exception as e:
            # Unexpected system error
            self.logger.exception("Unexpected error creating user")
            return Result.error(
                "SYSTEM_ERROR",
                "An unexpected error occurred",
                details={"exception": str(e)}
            )
    
    async def get_user(self, user_id: int) -> Result:
        """Get user by ID."""
        if user_id <= 0:
            return Result.error(
                "INVALID_USER_ID",
                "User ID must be a positive integer",
                details={"provided_id": user_id}
            )
        
        try:
            async with self.app_context.database.integrity_session("user_manager", "get_user") as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                
                user = result.scalar_one_or_none()
                
                if not user:
                    return Result.error(
                        "USER_NOT_FOUND",
                        f"User with ID {user_id} not found",
                        details={"user_id": user_id}
                    )
                
                return Result.success(data={
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "is_active": user.is_active
                })
                
        except Exception as e:
            self.logger.exception(f"Error retrieving user {user_id}")
            return Result.error(
                "DATABASE_ERROR",
                "Failed to retrieve user",
                details={"user_id": user_id, "error": str(e)}
            )
    
    async def update_user(self, user_id: int, **updates) -> Result:
        """Update user with validation and error handling."""
        
        # Get current user first
        user_result = await self.get_user(user_id)
        if not user_result.success:
            return user_result  # Propagate the error
        
        # Validate updates
        if "email" in updates:
            email = updates["email"]
            if not email or "@" not in email:
                return Result.error(
                    "INVALID_EMAIL",
                    "Valid email address is required",
                    details={"provided_email": email}
                )
        
        if "name" in updates:
            name = updates["name"]
            if not name or not name.strip():
                return Result.error(
                    "INVALID_NAME",
                    "Name cannot be empty",
                    details={"provided_name": name}
                )
        
        try:
            async with self.app_context.database.integrity_session("user_manager", "update_user") as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                
                user = result.scalar_one_or_none()
                
                if not user:
                    return Result.error("USER_NOT_FOUND", f"User {user_id} not found")
                
                # Apply updates
                for field, value in updates.items():
                    if hasattr(user, field):
                        setattr(user, field, value)
                    else:
                        return Result.error(
                            "INVALID_FIELD",
                            f"Field '{field}' cannot be updated",
                            details={"field": field, "valid_fields": ["name", "email"]}
                        )
                
                await session.commit()
                
                return Result.success(data={
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "updated_fields": list(updates.keys())
                })
                
        except IntegrityError as e:
            return Result.error(
                "UPDATE_CONSTRAINT",
                "Update violates database constraint",
                details={"updates": updates, "error": str(e)}
            )
            
        except Exception as e:
            self.logger.exception(f"Error updating user {user_id}")
            return Result.error(
                "UPDATE_FAILED",
                "Failed to update user",
                details={"user_id": user_id, "updates": updates, "error": str(e)}
            )
```

### API Layer Error Handling

```python
# modules/standard/user_manager/api.py
from fastapi import APIRouter, HTTPException, Request
from .api_schemas import CreateUserRequest, UserResponse, UpdateUserRequest

class UserManagerModule(DataIntegrityModule):
    
    def setup_routes(self):
        @self.router.post("/users", response_model=UserResponse)
        async def create_user(request: CreateUserRequest, http_request: Request):
            service = http_request.app.state.app_context.get_service("user_manager.service")
            
            result = await service.create_user(request.name, request.email)
            
            if not result.success:
                # Convert Result error to HTTP exception
                raise self.result_to_http_exception(result)
            
            return UserResponse(**result.data)
        
        @self.router.get("/users/{user_id}", response_model=UserResponse)
        async def get_user(user_id: int, http_request: Request):
            service = http_request.app.state.app_context.get_service("user_manager.service")
            
            result = await service.get_user(user_id)
            
            if not result.success:
                raise self.result_to_http_exception(result)
            
            return UserResponse(**result.data)
        
        @self.router.put("/users/{user_id}", response_model=UserResponse)
        async def update_user(user_id: int, request: UpdateUserRequest, http_request: Request):
            service = http_request.app.state.app_context.get_service("user_manager.service")
            
            # Convert request to dict, excluding None values
            updates = {k: v for k, v in request.dict(exclude_unset=True).items()}
            
            result = await service.update_user(user_id, **updates)
            
            if not result.success:
                raise self.result_to_http_exception(result)
            
            return UserResponse(**result.data)
    
    def result_to_http_exception(self, result: Result) -> HTTPException:
        """Convert Result error to appropriate HTTP exception."""

        # Map error codes to HTTP status codes
        status_code_map = {
            "USER_NOT_FOUND": 404,
            "USER_EXISTS": 409,
            "INVALID_NAME": 400,
            "INVALID_EMAIL": 400,
            "INVALID_USER_ID": 400,
            "VALIDATION_FAILED": 400,
            "DATABASE_CONSTRAINT": 409,
            "SYSTEM_ERROR": 500,
            "DATABASE_ERROR": 500,
            "UPDATE_FAILED": 500
        }

        status_code = status_code_map.get(result.code, 500)

        # Create detailed error response
        detail = {
            "error_code": result.code,
            "message": result.message,
            "timestamp": datetime.now().isoformat()
        }

        # Include details in development mode
        if self.debug_mode and result.details:
            detail["details"] = result.details

        return HTTPException(status_code=status_code, detail=detail)
```

## Chaining Operations

### Sequential Operations

```python
async def create_user_with_profile(self, name: str, email: str, bio: str) -> Result:
    """Create user and profile in sequence with proper error propagation."""
    
    # Step 1: Create user
    user_result = await self.create_user(name, email)
    if not user_result.success:
        return user_result  # Propagate error
    
    user_id = user_result.data["id"]
    
    # Step 2: Create profile
    profile_result = await self.create_profile(user_id, bio)
    if not profile_result.success:
        # Rollback: delete the user we just created
        await self.delete_user(user_id)
        
        return Result.error(
            "PROFILE_CREATION_FAILED",
            "Failed to create user profile, user creation rolled back",
            details={
                "user_creation": "success",
                "profile_error": profile_result.code,
                "profile_message": profile_result.message
            }
        )
    
    return Result.success(data={
        "user": user_result.data,
        "profile": profile_result.data
    })
```

### Parallel Operations with Error Aggregation

```python
async def get_user_summary(self, user_id: int) -> Result:
    """Get user data from multiple sources."""
    
    # Start all operations concurrently
    user_task = self.get_user(user_id)
    orders_task = self.get_user_orders(user_id) 
    preferences_task = self.get_user_preferences(user_id)
    
    # Wait for all to complete
    user_result, orders_result, preferences_result = await asyncio.gather(
        user_task, orders_task, preferences_task,
        return_exceptions=True
    )
    
    # Handle individual failures
    errors = []
    data = {}
    
    if isinstance(user_result, Result) and user_result.success:
        data["user"] = user_result.data
    else:
        errors.append({"source": "user", "error": user_result.code if isinstance(user_result, Result) else str(user_result)})

    if isinstance(orders_result, Result) and orders_result.success:
        data["orders"] = orders_result.data
    else:
        errors.append({"source": "orders", "error": orders_result.code if isinstance(orders_result, Result) else str(orders_result)})

    if isinstance(preferences_result, Result) and preferences_result.success:
        data["preferences"] = preferences_result.data
    else:
        errors.append({"source": "preferences", "error": preferences_result.code if isinstance(preferences_result, Result) else str(preferences_result)})
    
    # If user data failed, it's a critical error
    if "user" not in data:
        return Result.error(
            "USER_DATA_REQUIRED",
            "Could not retrieve required user data",
            details={"errors": errors}
        )
    
    # Return partial data with warnings about failed sources
    if errors:
        data["warnings"] = errors
    
    return Result.success(data=data)
```

## Error Logging and Monitoring

### Structured Error Logging with Context

For all errors that require tracking and analysis, use structured logging with the context parameter:

```python
from core.error_utils import error_message

# Always include context for structured debugging information
logger.error(error_message(
    module_id="core.database",
    error_type="CONNECTION_FAILED",
    details="Database connection failed during initialization",
    location="initialize_phase2()",
    context={
        "database_url": "sqlite:///data/framework.db",
        "attempt": 3,
        "retry_policy": "exponential_backoff",
        "error_type": "ConnectionError"
    }
))
```

**Output:**
- **JSONL file**: `data/error_logs/YYYYMMDD-error.jsonl` (structured data for analysis)
  - Includes context as separate field for querying and debugging
  - Timestamp, module_id, error_type, location automatically tracked
- **App log**: Human-readable formatted message in `app.log`
  - Message format: `module_database_CONNECTION_FAILED - Database connection failed during initialization in initialize_phase2() [database_url=sqlite:///data/framework.db, attempt=3, retry_policy=exponential_backoff, error_type=ConnectionError]`

**Use structured logging with context for:**
- Database connection failures
- Service initialization errors
- External API failures
- File system errors
- Critical business logic failures
- Model loading/inference errors
- Any error that needs debugging and analysis

**Key benefits of context parameter:**
- Structured debugging information separate from error message
- Enables querying error logs for specific conditions (e.g., all errors with attempt > 3)
- Makes log analysis and monitoring easier
- Automatic tracking in JSONL format for post-analysis

## Best Practices

### When to Use Result vs Exceptions

**Use Result for:**
- **Business logic errors** - Domain-specific failures
- **Validation errors** - Input validation failures  
- **External service errors** - API calls, database operations
- **Expected failures** - Operations that commonly fail

**Use Exceptions for:**
- **System errors** - Out of memory, file system errors
- **Programming errors** - Bug in code, assertion failures
- **Framework errors** - Configuration issues, dependency problems
- **Unexpected failures** - Should never happen in normal operation

### Error Code Conventions

```python
# Use descriptive, consistent error codes
"USER_NOT_FOUND"         # Entity not found
"INVALID_EMAIL"          # Validation error
"DATABASE_CONSTRAINT"    # Database constraint violation
"EXTERNAL_API_FAILED"    # External service error
"INSUFFICIENT_PERMISSIONS" # Authorization error
"RATE_LIMIT_EXCEEDED"    # Rate limiting
"SYSTEM_UNAVAILABLE"     # System-level issues
```

### Error Message Guidelines

```python
# Good: Clear, actionable messages
Result.error("INVALID_EMAIL", "Email must contain @ symbol")
Result.error("USER_NOT_FOUND", "User with ID 123 does not exist")
Result.error("INSUFFICIENT_FUNDS", "Account balance ($10.50) is insufficient for transaction ($25.00)")

# Avoid: Vague or technical messages
Result.error("ERROR", "Something went wrong")
Result.error("DB_ERR", "SQLIntegrityError: foreign key constraint")
```

### Error Context

```python
# Include relevant context for debugging
Result.error(
    "PAYMENT_FAILED",
    "Payment processing failed",
    details={
        "payment_id": "pay_123",
        "amount": 25.00,
        "currency": "USD",
        "gateway_response": "insufficient_funds",
        "user_id": 456,
        "timestamp": datetime.utcnow().isoformat()
    }
)
```

## Troubleshooting Common Patterns

### Nested Result Handling

```python
# Instead of nested if statements
result1 = await operation1()
if result1.success:
    result2 = await operation2(result1.data)
    if result2.success:
        result3 = await operation3(result2.data)
        if result3.success:
            return result3
        else:
            return result3
    else:
        return result2
else:
    return result1

# Use early returns
async def clean_operation() -> Result:
    result1 = await operation1()
    if not result1.success:
        return result1
    
    result2 = await operation2(result1.data)
    if not result2.success:
        return result2
    
    result3 = await operation3(result2.data)
    return result3  # Success or failure
```

### Result Transformation

```python
def transform_result(result: Result, transform_fn) -> Result:
    """Transform successful result data, preserve errors."""
    if result.success:
        try:
            transformed_data = transform_fn(result.data)
            return Result.success(data=transformed_data)
        except Exception as e:
            return Result.error("TRANSFORMATION_FAILED", str(e))
    else:
        return result  # Preserve original error

# Usage
user_result = await get_user(123)
public_user = transform_result(user_result, lambda user: {
    "id": user["id"],
    "name": user["name"]
    # Remove sensitive fields
})
```

The Result pattern provides explicit, consistent error handling that makes your code more reliable and easier to debug while maintaining clean separation between business logic errors and system failures.