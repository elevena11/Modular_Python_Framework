# Settings System

The framework provides a type-safe settings system using Pydantic v2 with environment variable overrides, user preferences, and module isolation.

## Core Concepts

### Three-Layer Configuration
1. **Default values** - Defined in Pydantic models
2. **Environment overrides** - Via environment variables
3. **User preferences** - Stored in database, highest priority

### Type Safety
All settings use Pydantic v2 models for:
- **Type validation** - Ensures correct data types
- **Field validation** - Custom validation rules
- **Automatic conversion** - String environment variables to proper types
- **Documentation** - Built-in field descriptions and examples

## Defining Module Settings

### Basic Settings Model

```python
# modules/standard/my_module/settings.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class MyModuleSettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_MY_MODULE_",    # Environment variable prefix
        use_enum_values=True,            # Use enum values instead of names
        validate_assignment=True,        # Validate on assignment
        extra="forbid"                   # Forbid extra fields
    )
    
    # Basic settings with defaults
    timeout_seconds: int = Field(
        default=30,
        ge=1,  # Greater than or equal to 1
        le=300,  # Less than or equal to 300
        description="Request timeout in seconds"
    )
    
    max_connections: int = Field(
        default=10,
        gt=0,  # Greater than 0
        description="Maximum number of concurrent connections"
    )
    
    debug_mode: bool = Field(
        default=False,
        description="Enable debug logging and detailed error messages"
    )
    
    api_base_url: str = Field(
        default="https://api.example.com",
        description="Base URL for external API calls"
    )
    
    # Optional settings
    api_key: Optional[str] = Field(
        default=None,
        description="API key for external service (if required)"
    )
```

### Advanced Settings with Validation

```python
from pydantic import BaseModel, Field, validator, ConfigDict
from enum import Enum
from typing import List, Optional

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class DatabaseMode(str, Enum):
    MEMORY = "memory"
    FILE = "file"
    CLUSTER = "cluster"

class AdvancedModuleSettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_ADVANCED_MODULE_",
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    # Enum settings
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level for the module"
    )
    
    database_mode: DatabaseMode = Field(
        default=DatabaseMode.FILE,
        description="Database storage mode"
    )
    
    # List settings
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Allowed hosts for API access"
    )
    
    # Complex validation
    worker_count: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of worker processes"
    )
    
    # Custom validation
    @validator('allowed_hosts')
    def validate_hosts(cls, v):
        if not v:
            raise ValueError('At least one allowed host must be specified')
        return v
    
    @validator('worker_count')
    def validate_worker_count(cls, v, values):
        # Validate based on other fields
        if values.get('database_mode') == DatabaseMode.MEMORY and v > 1:
            raise ValueError('Memory mode only supports single worker')
        return v
```

## Registering Settings in Your Module

### Registration in Module Initialization

```python
# modules/standard/my_module/api.py
from core.decorators import register_service
from core.module_base import DataIntegrityModule
from .settings import MyModuleSettings

@register_service("my_module.service")
class MyModule(DataIntegrityModule):
    MODULE_ID = "standard.my_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "Example module with settings"
    
    def register_settings(self):
        """Register Pydantic settings schema with the framework."""
        self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)
        self.logger.info(f"Registered settings schema for {self.MODULE_ID}")
    
    async def initialize_service(self):
        """Phase 2: Access settings after registration."""
        # Get typed settings
        settings = await self.get_module_settings()
        self.logger.info(f"Module initialized with timeout: {settings.timeout_seconds}s")
    
    async def get_module_settings(self) -> MyModuleSettings:
        """Get typed settings for this module."""
        settings_service = self.app_context.get_service("core.settings.service")
        return await settings_service.get_typed_settings(self.MODULE_ID, MyModuleSettings)
```

## Environment Variable Overrides

### Automatic Environment Mapping

Based on your `env_prefix` in the model config, environment variables are automatically mapped:

```python
# settings.py
class MyModuleSettings(BaseModel):
    model_config = ConfigDict(env_prefix="CORE_MY_MODULE_")
    
    timeout_seconds: int = Field(default=30)
    max_connections: int = Field(default=10)
    debug_mode: bool = Field(default=False)
```

**Environment Variables:**
```bash
# .env file or system environment
CORE_MY_MODULE_TIMEOUT_SECONDS=60
CORE_MY_MODULE_MAX_CONNECTIONS=20
CORE_MY_MODULE_DEBUG_MODE=true
```

**Result:**
- `timeout_seconds` = 60 (overridden from default 30)
- `max_connections` = 20 (overridden from default 10)  
- `debug_mode` = True (overridden from default False)

### Complex Environment Variables

```python
# List from environment (comma-separated)
CORE_MY_MODULE_ALLOWED_HOSTS=localhost,api.example.com,192.168.1.100

# Enum from environment
CORE_MY_MODULE_LOG_LEVEL=debug

# Optional values (empty string = None)
CORE_MY_MODULE_API_KEY=""  # Results in None
CORE_MY_MODULE_API_KEY="sk-1234567890"  # Results in "sk-1234567890"
```

## Using Settings in Your Code

### In Service Classes

```python
# modules/standard/my_module/services.py
from core.error_utils import Result
from .settings import MyModuleSettings

class MyModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
        self._settings = None
    
    async def get_settings(self) -> MyModuleSettings:
        """Get current settings (cached)."""
        if self._settings is None:
            settings_service = self.app_context.get_service("core.settings.service")
            self._settings = await settings_service.get_typed_settings(
                "standard.my_module", 
                MyModuleSettings
            )
        return self._settings
    
    async def make_api_call(self, endpoint: str) -> Result:
        """Make API call using configured settings."""
        settings = await self.get_settings()
        
        # Use settings values
        url = f"{settings.api_base_url}/{endpoint}"
        timeout = settings.timeout_seconds
        
        if settings.debug_mode:
            self.logger.debug(f"Making API call to {url} with timeout {timeout}s")
        
        try:
            # Make HTTP request with settings
            async with httpx.AsyncClient(timeout=timeout) as client:
                headers = {}
                if settings.api_key:
                    headers["Authorization"] = f"Bearer {settings.api_key}"
                
                response = await client.get(url, headers=headers)
                
                if settings.debug_mode:
                    self.logger.debug(f"API response: {response.status_code}")
                
                return Result.success(data=response.json())
                
        except Exception as e:
            return Result.error("API_CALL_FAILED", str(e))
```

### In API Endpoints

```python
# modules/standard/my_module/api.py
@self.router.get("/config")
async def get_module_config(request: Request):
    """Get current module configuration."""
    service = request.app.state.app_context.get_service("my_module.service")
    settings = await service.get_settings()
    
    # Return safe configuration (no sensitive data)
    return {
        "timeout_seconds": settings.timeout_seconds,
        "max_connections": settings.max_connections,
        "debug_mode": settings.debug_mode,
        "api_base_url": settings.api_base_url,
        "has_api_key": settings.api_key is not None  # Don't expose the key
    }

@self.router.post("/test-connection")
async def test_connection(request: Request):
    """Test external API connection using current settings."""
    service = request.app.state.app_context.get_service("my_module.service")
    result = await service.make_api_call("health")
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)
    
    return {"status": "connected", "response": result.data}
```

## User Preferences and Runtime Configuration

### Updating Settings at Runtime

```python
async def update_module_timeout(self, new_timeout: int) -> Result:
    """Update timeout setting for this module."""
    try:
        settings_service = self.app_context.get_service("core.settings.service")
        
        # Update user preference
        result = await settings_service.update_user_preference(
            module_id="standard.my_module",
            setting_key="timeout_seconds", 
            setting_value=new_timeout
        )
        
        if result.success:
            # Clear cached settings to force reload
            self._settings = None
            return Result.success(message="Timeout updated successfully")
        else:
            return result
            
    except Exception as e:
        return Result.error("UPDATE_FAILED", str(e))
```

### Settings Priority Order

The framework resolves settings in this order (highest priority first):

1. **User Preferences** (stored in database)
2. **Environment Variables** (CORE_MODULE_SETTING_NAME)
3. **Default Values** (defined in Pydantic model)

```python
# Example resolution:
# 1. Default: timeout_seconds = 30
# 2. Environment: CORE_MY_MODULE_TIMEOUT_SECONDS=60 → timeout_seconds = 60
# 3. User Preference: User sets timeout to 45 → timeout_seconds = 45 (final value)
```

## Settings Validation and Error Handling

### Handling Invalid Settings

```python
async def get_validated_settings(self) -> Result:
    """Get settings with validation error handling."""
    try:
        settings_service = self.app_context.get_service("core.settings.service")
        settings = await settings_service.get_typed_settings(
            "standard.my_module", 
            MyModuleSettings
        )
        
        return Result.success(data=settings)
        
    except ValidationError as e:
        # Handle Pydantic validation errors
        errors = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        
        return Result.error(
            "SETTINGS_VALIDATION_FAILED",
            f"Settings validation failed: {'; '.join(errors)}"
        )
    
    except Exception as e:
        return Result.error("SETTINGS_ACCESS_FAILED", str(e))
```

### Custom Validation Messages

```python
class MyModuleSettings(BaseModel):
    model_config = ConfigDict(env_prefix="CORE_MY_MODULE_")
    
    worker_count: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of worker processes"
    )
    
    @validator('worker_count')
    def validate_worker_count(cls, v):
        if v > 16:
            cls.logger.warning(f"High worker count ({v}) may impact performance")
        return v
```

## Best Practices

### Settings Organization
- **One settings file per module** - Keep settings focused
- **Clear field names** - Use descriptive setting names
- **Appropriate defaults** - Sensible defaults for most use cases
- **Good descriptions** - Document what each setting does

### Environment Variables
- **Consistent prefixes** - Use CORE_MODULE_NAME_ pattern
- **Uppercase names** - Follow environment variable conventions
- **Document variables** - List required/optional environment variables

### Validation
- **Validate ranges** - Use ge, le, gt, lt for numeric values
- **Validate formats** - Custom validators for complex formats
- **Meaningful errors** - Clear validation error messages
- **Fail fast** - Validate settings at startup, not during operation

### Security
- **Sensitive data in environment** - Never put secrets in code defaults
- **Careful logging** - Don't log sensitive settings values
- **API exposure** - Don't expose sensitive settings in API responses
- **Access control** - Consider who can modify settings

### Performance
- **Cache settings** - Don't fetch settings on every operation
- **Lazy loading** - Load settings when needed, not at import
- **Change detection** - Invalidate cache when settings change
- **Batch updates** - Update multiple settings in single operation

## Troubleshooting

### Settings Not Loading
```
Error: Settings not found for module 'standard.my_module'
```

**Cause:** Module settings not registered
**Solution:** Call `register_settings()` in your module and ensure `register_pydantic_model()` is called

### Environment Variables Not Working
```
Error: Environment variable CORE_MY_MODULE_TIMEOUT ignored
```

**Causes:**
- Wrong prefix in model config
- Typo in environment variable name
- Wrong data type (string to int conversion failed)

**Solution:** Check `env_prefix` matches your environment variables

### Validation Errors
```
Error: 1 validation error for MyModuleSettings
timeout_seconds: ensure this value is greater than 0
```

**Cause:** Invalid value provided (environment variable, user preference, or default)
**Solution:** Check the value meets the Field validation requirements

The settings system provides type-safe, flexible configuration management that grows with your application needs while maintaining simplicity for basic use cases.