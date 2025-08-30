# Pydantic Settings Implementation Guide

## Overview

This guide provides the **complete, tested pattern** for converting modules to use the Pydantic settings system. The architecture has been proven with 2 core modules and is ready for widespread adoption.

## Architecture Summary

**Phase 1:** Modules register Pydantic models → app_context collects them  
**Phase 2:** Settings service requests registered models → creates baseline → applies .env overrides  
**Runtime:** Modules get type-safe, validated settings via settings service

## Step-by-Step Implementation

### Step 1: Create Pydantic Settings Model

Create `modules/{type}/{module_name}/settings_v2.py`:

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from enum import Enum

class MyModuleSettings(BaseModel):
    """Pydantic settings model for my_module with full validation"""
    
    # CRITICAL: Use model_config, NOT Config class (Pydantic v2)
    model_config = ConfigDict(
        env_prefix="CORE_MY_MODULE_",  # Match module hierarchy
        use_enum_values=True,          # Handle enums properly
        validate_assignment=True,      # Validate on assignment
        extra="forbid",                # Prevent unknown fields
        json_schema_extra={
            "title": "My Module Settings",
            "description": "Configuration for my module functionality"
        }
    )
    
    # Example settings with validation and metadata
    enabled: bool = Field(
        default=True,
        description="Enable my module functionality"
    )
    
    max_items: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of items to process"
    )
    
    processing_mode: Literal["fast", "thorough", "balanced"] = Field(
        default="balanced",
        description="Processing mode for operations"
    )
    
    timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=300.0,
        description="Operation timeout in seconds"
    )
    
    # Nested configuration example
    advanced_config: Optional[dict] = Field(
        default_factory=dict,
        description="Advanced configuration options"
    )
```

### Step 2: Update Module API (Phase 1 Registration)

In `modules/{type}/{module_name}/api.py`:

```python
# Import your settings model
from .settings_v2 import MyModuleSettings

@register_service("my_module.service", priority=30)
@inject_dependencies("app_context")
@auto_service_creation(service_class="MyModuleService")
@initialization_sequence("setup_infrastructure", "create_service", "register_settings", phase="phase1")
@phase2_operations("initialize_service", dependencies=["core.settings.service"], priority=40)
@enforce_data_integrity(strict_mode=True)
@graceful_shutdown(method="cleanup_resources", timeout=30)
class MyModuleModule(DataIntegrityModule):
    
    MODULE_ID = "my_module"
    MODULE_DEPENDENCIES = ["core.settings"]  # Require settings
    
    def register_settings(self):
        """Phase 1: Register Pydantic model with app_context (NO service calls)"""
        try:
            self.app_context.register_pydantic_model(self.MODULE_ID, MyModuleSettings)
            self.logger.info(f"{self.MODULE_ID}: Pydantic settings model registered with framework")
        except Exception as e:
            self.logger.error(f"{self.MODULE_ID}: Error registering settings: {str(e)}")
    
    async def initialize_service(self):
        """Phase 2: Get validated settings and initialize service"""
        self.logger.info(f"{self.MODULE_ID}: Phase 2 - Initializing service with typed settings")
        
        if self.service_instance:
            settings_service = self.app_context.get_service("core.settings.service")
            if settings_service:
                # Get fully validated Pydantic settings
                result = await settings_service.get_typed_settings(
                    module_id=self.MODULE_ID,
                    model_class=MyModuleSettings, 
                    database_name="settings"  # Explicit database selection
                )
                
                if result.success:
                    typed_settings = result.data  # MyModuleSettings instance
                    
                    # Initialize service with type-safe settings
                    if hasattr(self.service_instance, 'initialize'):
                        await self.service_instance.initialize(typed_settings)
                        self.logger.info(f"{self.MODULE_ID}: Service initialized with typed Pydantic settings")
                else:
                    self.logger.error(f"{self.MODULE_ID}: Failed to get typed settings: {result.message}")
            else:
                self.logger.error(f"{self.MODULE_ID}: Settings service not available in Phase 2")
```

### Step 3: Update Service Implementation

In `modules/{type}/{module_name}/services.py`:

```python
class MyModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.settings = None  # Will be set during initialize
        self.initialized = False
        
    async def initialize(self, settings: MyModuleSettings):
        """Initialize service with validated Pydantic settings"""
        self.settings = settings
        
        # Use type-safe settings with full IDE support
        if self.settings.enabled:
            self.max_items = self.settings.max_items
            self.timeout = self.settings.timeout_seconds
            self.mode = self.settings.processing_mode
            
            self.logger.info(f"Service configured: {self.mode} mode, "
                           f"max {self.max_items} items, {self.timeout}s timeout")
        
        self.initialized = True
        return True
```

### Step 4: Environment Variables (Optional)

Add environment variable overrides in `.env`:

```bash
# Environment variables automatically parsed by Pydantic
CORE_MY_MODULE_ENABLED=true
CORE_MY_MODULE_MAX_ITEMS=500
CORE_MY_MODULE_PROCESSING_MODE=fast
CORE_MY_MODULE_TIMEOUT_SECONDS=60.0
```

### Step 5: Test Implementation

1. **Start application** and check logs for registration:
   ```bash
   python app.py
   # Look for: "my_module: Pydantic settings model registered with framework"
   # Look for: "Created baseline for N modules" (N should increase by 1)
   ```

2. **Test API endpoints**:
   ```bash
   # Get module settings
   curl "http://localhost:8000/api/v1/settings/settings/my_module" | jq
   
   # Set user preference
   curl -X PUT "http://localhost:8000/api/v1/settings/settings/my_module/max_items" \
        -H "Content-Type: application/json" -d '{"value": 200}'
   ```

3. **Verify environment variables**:
   ```bash
   # Set environment variable and restart
   export CORE_MY_MODULE_MAX_ITEMS=750
   python app.py
   # Check that settings reflect the environment override
   ```

## Migration Checklist

When converting a module to Pydantic settings:

### ✅ Pre-Implementation
- [ ] **Review existing settings** - Document current configuration
- [ ] **Choose appropriate validation** - Field constraints, types, enums
- [ ] **Plan environment variables** - Consistent naming with env_prefix
- [ ] **Design nested structures** - Group related settings logically

### ✅ Implementation
- [ ] **Create settings_v2.py** with proper Pydantic v2 patterns
- [ ] **Use model_config** - NEVER mix with Config class
- [ ] **Add comprehensive validation** - Field constraints and descriptions
- [ ] **Set correct env_prefix** - Match module hierarchy
- [ ] **Update api.py** - Add Phase 1 registration and Phase 2 resolution
- [ ] **Update services.py** - Accept typed Pydantic settings
- [ ] **Add dependencies** - Require core.settings in MODULE_DEPENDENCIES

### ✅ Testing
- [ ] **Import test** - Verify Pydantic model imports without errors
- [ ] **Registration test** - Check Phase 1 registration in logs
- [ ] **Baseline test** - Verify baseline creation includes new module
- [ ] **API test** - Test GET/PUT/DELETE endpoints
- [ ] **Environment test** - Verify .env variables work correctly
- [ ] **Service test** - Confirm service gets typed settings

### ✅ Cleanup
- [ ] **Remove legacy code** - Clean up old settings access patterns
- [ ] **Update imports** - Change from dict to Pydantic model access
- [ ] **Remove fallbacks** - No legacy compatibility in clean architecture
- [ ] **Update documentation** - Document new settings and their purposes

## Common Patterns

### Complex Nested Configuration

```python
class DatabaseConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(default="myapp")
    
class MyModuleSettings(BaseModel):
    model_config = ConfigDict(env_prefix="CORE_MY_MODULE_")
    
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    # Environment: CORE_MY_MODULE_DATABASE_HOST=production.db.example.com
```

### Enum Configuration

```python
class ProcessingMode(str, Enum):
    FAST = "fast"
    THOROUGH = "thorough"
    BALANCED = "balanced"

class MyModuleSettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_MY_MODULE_",
        use_enum_values=True  # CRITICAL for enum handling
    )
    
    mode: ProcessingMode = ProcessingMode.BALANCED
    # Environment: CORE_MY_MODULE_MODE=fast
```

### Backward Compatibility Helper

If you need to support legacy code temporarily:

```python
class MyModuleSettings(BaseModel):
    # ... Pydantic configuration ...
    
    def to_legacy_dict(self) -> dict:
        """Convert to legacy dict format for transition period"""
        return self.model_dump()
```

## Troubleshooting

### Module Not Appearing in Baseline

**Symptoms**: Module shows `baseline_count: 0` in API

**Solutions**:
1. Check Phase 1 registration logs for errors
2. Verify Pydantic model imports without errors
3. Ensure `register_settings()` is called in Phase 1
4. Check that settings service priority allows other modules to register first

### Settings Service Not Available

**Symptoms**: "Settings service not available in Phase 2"

**Solutions**:
1. Add `"core.settings"` to MODULE_DEPENDENCIES
2. Verify phase2_operations has correct dependencies
3. Check that module priority allows settings to initialize first

### Environment Variables Not Working

**Symptoms**: .env values not appearing in settings

**Solutions**:
1. Verify `env_prefix` matches variable naming exactly
2. Check variable naming: `CORE_MODULE_NAME_SETTING_NAME`
3. Ensure `model_config` has correct `env_prefix`
4. Restart application after changing .env

### Pydantic Import Errors

**Symptoms**: Module fails to load, import errors

**Solutions**:
1. Never mix `Config` class with `model_config`
2. Use `ConfigDict(...)` not `ConfigDict[...]`  
3. Import from `pydantic` not `pydantic.v1`
4. Check all Field constraints are valid

## Reference Implementation

The `core.model_manager` module serves as the **reference implementation** with:
- Complex nested configuration with 12+ settings
- Multiple configuration sections (embedding, worker_pool, etc.)
- Enum usage with proper validation
- Environment variable integration
- Full backward compatibility patterns

Study `modules/core/model_manager/settings_v2.py` for comprehensive examples.

---

## Success Criteria

A successful Pydantic settings implementation will show:

1. **Phase 1 Registration**: "Pydantic settings model registered with framework"
2. **Phase 2 Baseline**: "Created baseline for N modules" (N increased)
3. **Type-Safe Access**: Service receives validated Pydantic model instance
4. **API Integration**: Module appears in `/api/v1/settings/settings/` with rich data
5. **Environment Support**: .env variables properly override defaults

**The pattern is proven and production-ready. Follow this guide for consistent, reliable implementations.** ✅