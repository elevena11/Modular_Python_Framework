# Pydantic v2 Migration Issues and Solutions

## Overview

This document covers common issues encountered when migrating from Pydantic v1 to v2 patterns within the framework's settings system. These are critical gotchas that can prevent module loading and should be avoided.

## Critical Issues

### 1. Config Class vs model_config Conflict

**Issue**: Using both the legacy `Config` class and the new `model_config` attribute simultaneously causes a fatal error.

**Error Message**:
```
pydantic.errors.PydanticUserError: "Config" and "model_config" cannot be used together

For further information visit https://errors.pydantic.dev/2.11/u/config-both
```

**Root Cause**: Pydantic v2 replaced the inner `Config` class pattern with the `model_config` attribute using `ConfigDict`.

#### **WRONG** - Causes Fatal Error:
```python
from pydantic import BaseModel, Field, ConfigDict

class MySettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_MODULE_",
        extra="forbid"
    )
    
    my_setting: str = Field(default="value")
    
    class Config:  # ❌ FATAL ERROR - Cannot use with model_config
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"
```

#### **CORRECT** - Pydantic v2 Pattern:
```python
from pydantic import BaseModel, Field, ConfigDict

class MySettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_MODULE_",
        use_enum_values=True,      # Moved from Config class
        validate_assignment=True,   # Moved from Config class  
        extra="forbid"             # Moved from Config class
    )
    
    my_setting: str = Field(default="value")
    
    # No Config class needed - all configuration in model_config
```

#### **Migration Steps:**
1. **Remove the `Config` class entirely**
2. **Move all Config options to `model_config`**
3. **Use `ConfigDict` for the model_config value**
4. **Test import** to ensure no conflicts

### 2. Common Configuration Options Migration

| Legacy Config Class | New model_config (ConfigDict) |
|-------------------|------------------------------|
| `use_enum_values = True` | `use_enum_values=True` |
| `validate_assignment = True` | `validate_assignment=True` |
| `extra = "forbid"` | `extra="forbid"` |
| `env_prefix = "MY_"` | `env_prefix="MY_"` |
| `allow_population_by_field_name = True` | `populate_by_name=True` |
| `case_sensitive = False` | `case_sensitive=False` |

### 3. Framework-Specific Patterns

#### **Environment Variable Prefixes**
Always use descriptive prefixes that match the module hierarchy:

```python
class ModelManagerSettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_MODEL_MANAGER_",  # Matches core.model_manager
        use_enum_values=True,
        extra="forbid"
    )
```

#### **Nested Model Configuration**
Each sub-model should have its own specific prefix:

```python
class EmbeddingModelConfig(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_MODEL_MANAGER_EMBEDDING_"
    )

class WorkerPoolConfig(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_MODEL_MANAGER_WORKER_POOL_"
    )

class ModelManagerSettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_MODEL_MANAGER_",
        use_enum_values=True,
        extra="forbid"
    )
    
    embedding: EmbeddingModelConfig = Field(default_factory=EmbeddingModelConfig)
    worker_pool: WorkerPoolConfig = Field(default_factory=WorkerPoolConfig)
```

## Debugging Tips

### 1. Import Testing
Always test imports after creating Pydantic models:

```bash
python -c "
import sys
sys.path.insert(0, '.')
try:
    from modules.core.my_module.settings_v2 import MySettings
    print('SUCCESS: Settings imported correctly')
    # Test instantiation
    settings = MySettings()
    print(f'Default values: {settings.model_dump()}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
"
```

### 2. Module Discovery Issues
If a module isn't being discovered, the Pydantic import error might be preventing the module from loading:

```bash
# Check if the API module can be imported
python -c "
from modules.core.my_module.api import MyModule
print('Module imports successfully')
"
```

### 3. Configuration Validation
Test that your configuration accepts expected values:

```python
# Test environment variable parsing
import os
os.environ['CORE_MY_MODULE_TEST_SETTING'] = 'test_value'

from modules.core.my_module.settings_v2 import MySettings
settings = MySettings()
print(f"Environment override worked: {settings.test_setting}")
```

## Framework Integration Checklist

When creating new Pydantic settings models:

- [ ] **Use only `model_config`** - Never mix with `Config` class
- [ ] **Set appropriate `env_prefix`** - Match module hierarchy
- [ ] **Configure `use_enum_values=True`** - For enum compatibility
- [ ] **Set `extra="forbid"`** - Prevent unknown fields
- [ ] **Test import independently** - Before framework integration
- [ ] **Use `Field()` for validation** - Add constraints and descriptions
- [ ] **Create nested models** - For complex configuration sections
- [ ] **Register in Phase 1** - Via `register_pydantic_model()`
- [ ] **Use explicit database** - Always specify database_name
- [ ] **Handle backward compatibility** - If existing code expects dict format

## Real-World Example: Model Manager

The `core.model_manager` module provides a complete example of proper Pydantic v2 patterns:

**File**: `modules/core/model_manager/settings_v2.py`

Key features:
- **Nested models** for complex configuration sections
- **Enum usage** with proper value handling
- **Environment variable support** with specific prefixes
- **Full validation** with Field constraints
- **Backward compatibility** via flattening method

This serves as the reference implementation for complex Pydantic settings models.

## Common Errors and Solutions

### Error: "Config and model_config cannot be used together"
**Solution**: Remove the `Config` class completely and move all options to `model_config`

### Error: "ImportError: cannot import name 'MySettings'"
**Solution**: Check for Pydantic syntax errors that prevent module loading

### Error: "TypeError: 'ConfigDict' object is not iterable"  
**Solution**: Ensure you're using `ConfigDict(...)` not `ConfigDict[...]`

### Error: Environment variables not working
**Solution**: Verify the `env_prefix` matches your variable naming pattern

---

**Remember**: Pydantic v2 uses `model_config = ConfigDict(...)` exclusively. The old `Config` class pattern is completely incompatible and will cause fatal import errors.