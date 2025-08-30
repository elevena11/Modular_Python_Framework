# Path Management System

The Path Management system (`core/paths.py`) provides consistent and reliable path handling throughout the framework. It ensures that all modules and components can access framework directories reliably, regardless of the current working directory or execution context.

## Overview

The path management system solves the common problem of relative path dependencies in Python applications by providing:

- **Framework Root Detection**: Automatically locates the framework root directory
- **Consistent Path Resolution**: Provides absolute paths for all framework directories
- **Directory Creation**: Automatically creates directories when needed
- **Module Integration**: Easy path access for modules without dependency injection
- **Cross-Platform Compatibility**: Works consistently across different operating systems

## Key Features

### 1. Framework Root Discovery
- **Automatic Detection**: Finds framework root by searching for `modules/` directory
- **Multi-Context Support**: Works from any directory within the framework
- **Robust Search**: Multiple fallback strategies for root detection
- **Single Calculation**: Root is determined once at import time

### 2. Data Directory Management
- **Standardized Layout**: All data stored in `data/` directory
- **Module Separation**: Each module can have its own data subdirectory
- **Automatic Creation**: Directories created on demand
- **Path Validation**: Ensures paths are within framework boundaries

### 3. Common Path Utilities
- **Logs Directory**: Centralized logging location
- **Database Directory**: Database file storage
- **Memory Directory**: LLM memory and embeddings storage
- **Module Data**: Module-specific data directories

## Architecture

```
Framework Root/
├── core/
│   └── paths.py           # Path management utilities
├── modules/               # Module discovery marker
├── data/                  # All persistent data
│   ├── database/          # Database files
│   ├── logs/              # Log files
│   ├── llm_memory/        # LLM memory storage
│   └── module_name/       # Module-specific data
└── app.py                 # Application entry point
```

## Core Functions

### 1. Framework Root Detection

```python
def find_framework_root() -> Path:
    """
    Find the framework root directory by looking for the 'modules' folder.
    
    Search Strategy:
    1. Start from core/paths.py location
    2. Navigate up directory tree looking for 'modules/'
    3. Check current working directory
    4. Search parent directories for framework markers
    
    Returns:
        Path object pointing to framework root
        
    Raises:
        ValueError: If framework root cannot be located
    """
```

### 2. Data Path Management

```python
def get_data_path(*path_parts: Union[str, Path]) -> Path:
    """
    Get a path within the framework's data directory.
    
    Args:
        *path_parts: Path components to join with data directory
        
    Returns:
        Path object pointing to requested location in data/
        
    Examples:
        get_data_path("logs", "app.log") -> /framework/data/logs/app.log
        get_data_path("database", "framework.db") -> /framework/data/database/framework.db
    """
```

### 3. Directory Creation

```python
def ensure_data_path(*path_parts: Union[str, Path]) -> Path:
    """
    Ensure a data directory path exists, creating it if necessary.
    
    Args:
        *path_parts: Path components to join with data directory
        
    Returns:
        Path object pointing to created directory
    """
```

## Usage Examples

### 1. Basic Path Access

```python
from core.paths import get_data_path, get_framework_root

# Get framework root
root = get_framework_root()
print(f"Framework root: {root}")

# Get data directory paths
config_path = get_data_path("config", "settings.json")
log_path = get_data_path("logs", "application.log")
db_path = get_data_path("database", "framework.db")
```

### 2. Module Data Management

```python
from core.paths import get_module_data_path, ensure_module_data_path

# Get module data directory
module_db = get_module_data_path("my_module", "database.db")
module_config = get_module_data_path("my_module", "config.json")

# Ensure module directory exists
data_dir = ensure_module_data_path("my_module")
cache_dir = ensure_module_data_path("my_module", "cache")
```

### 3. Common Directory Access

```python
from core.paths import get_logs_path, get_database_path, ensure_logs_path

# Access common directories
app_log = get_logs_path("app.log")
module_log = get_logs_path("my_module", "debug.log")
main_db = get_database_path("framework.db")

# Ensure directories exist
log_dir = ensure_logs_path("my_module")
```

### 4. File Operations

```python
from core.paths import get_data_path, ensure_data_path
import json

# Read configuration file
config_path = get_data_path("config", "settings.json")
if config_path.exists():
    with open(config_path, 'r') as f:
        config = json.load(f)

# Write data file
data_dir = ensure_data_path("exports")
export_path = data_dir / "export.json"
with open(export_path, 'w') as f:
    json.dump(data, f)
```

## Module Integration

### 1. Direct Import Pattern

```python
# Modules can import paths directly without dependency injection
from core.paths import get_module_data_path, ensure_logs_path

class MyModuleService:
    def __init__(self):
        # Get module-specific paths
        self.data_dir = ensure_module_data_path("my_module")
        self.log_path = ensure_logs_path("my_module", "service.log")
        
        # Setup module database
        self.db_path = get_module_data_path("my_module", "database.db")
```

### 2. Configuration File Management

```python
from core.paths import get_module_data_path, ensure_module_data_path
import json

class ModuleConfig:
    def __init__(self, module_name):
        self.module_name = module_name
        self.config_path = get_module_data_path(module_name, "config.json")
        
    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
        
    def save_config(self, config):
        # Ensure directory exists
        ensure_module_data_path(self.module_name)
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
```

### 3. Database Path Management

```python
from core.paths import get_database_path, ensure_data_path
from sqlalchemy import create_engine

class DatabaseManager:
    def __init__(self, db_name):
        # Ensure database directory exists
        ensure_data_path("database")
        
        # Get database path
        self.db_path = get_database_path(f"{db_name}.db")
        
        # Create database engine
        self.engine = create_engine(f"sqlite:///{self.db_path}")
```

## Constants and Convenience

### 1. Pre-calculated Paths

```python
# Available as module constants
from core.paths import (
    FRAMEWORK_ROOT,  # Framework root directory
    DATA_ROOT,       # data/ directory
    LOGS_ROOT,       # data/logs/ directory
    DATABASE_ROOT,   # data/database/ directory
    MEMORY_ROOT      # data/llm_memory/ directory
)

# Use in module initialization
log_file = LOGS_ROOT / "my_module.log"
db_file = DATABASE_ROOT / "my_module.db"
```

### 2. Specialized Path Functions

```python
from core.paths import (
    get_logs_path,      # Access logs directory
    get_database_path,  # Access database directory
    get_memory_path,    # Access LLM memory directory
    ensure_logs_path,   # Create logs directory
    ensure_memory_path  # Create memory directory
)

# Usage examples
error_log = get_logs_path("errors.log")
vector_db = get_memory_path("vectordb")
app_db = get_database_path("app.db")
```

## Error Handling

### 1. Framework Root Detection Failure

```python
try:
    from core.paths import get_framework_root
    root = get_framework_root()
except ValueError as e:
    print(f"Framework root not found: {e}")
    # Handle gracefully or exit
```

### 2. Path Validation

```python
from core.paths import get_data_path
import os

def safe_path_access(path_parts):
    try:
        path = get_data_path(*path_parts)
        
        # Validate path is within framework
        if not str(path).startswith(str(FRAMEWORK_ROOT)):
            raise ValueError("Path outside framework boundaries")
            
        return path
    except Exception as e:
        print(f"Path error: {e}")
        return None
```

## Best Practices

### 1. Always Use Path Functions

```python
# ✅ CORRECT: Use path functions
from core.paths import get_data_path
config_path = get_data_path("config", "settings.json")

# ❌ WRONG: Hardcoded paths
config_path = "./data/config/settings.json"
```

### 2. Ensure Directories Before Writing

```python
# ✅ CORRECT: Ensure directory exists
from core.paths import ensure_data_path
data_dir = ensure_data_path("exports")
export_file = data_dir / "data.json"

# ❌ WRONG: Assume directory exists
from core.paths import get_data_path
export_file = get_data_path("exports", "data.json")  # May fail if directory doesn't exist
```

### 3. Use Module-Specific Paths

```python
# ✅ CORRECT: Module-specific data directory
from core.paths import get_module_data_path
module_db = get_module_data_path("my_module", "database.db")

# ❌ WRONG: Generic data directory
from core.paths import get_data_path
module_db = get_data_path("database", "my_module.db")  # Clutters shared directory
```

### 4. Handle Path Objects Properly

```python
# ✅ CORRECT: Use Path methods
from core.paths import get_data_path
config_path = get_data_path("config.json")

if config_path.exists():
    content = config_path.read_text()

# ❌ WRONG: Convert to string unnecessarily
config_str = str(config_path)
if os.path.exists(config_str):
    with open(config_str, 'r') as f:
        content = f.read()
```

## Common Patterns

### 1. Module Initialization Pattern

```python
from core.paths import ensure_module_data_path, get_module_data_path

class ModuleService:
    def __init__(self, module_name):
        self.module_name = module_name
        
        # Ensure module data directory exists
        self.data_dir = ensure_module_data_path(module_name)
        
        # Define module-specific paths
        self.config_path = get_module_data_path(module_name, "config.json")
        self.cache_dir = get_module_data_path(module_name, "cache")
        self.log_path = get_module_data_path(module_name, "module.log")
```

### 2. Database Setup Pattern

```python
from core.paths import get_database_path, ensure_data_path
from sqlalchemy import create_engine

def setup_database(db_name):
    # Ensure database directory exists
    ensure_data_path("database")
    
    # Get database path
    db_path = get_database_path(f"{db_name}.db")
    
    # Create engine with absolute path
    engine = create_engine(f"sqlite:///{db_path}")
    
    return engine, db_path
```

### 3. Log File Pattern

```python
from core.paths import ensure_logs_path
import logging

def setup_module_logging(module_name):
    # Ensure module log directory exists
    log_dir = ensure_logs_path(module_name)
    
    # Create log file path
    log_file = log_dir / "module.log"
    
    # Setup logging
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
```

## Performance Considerations

### 1. Framework Root Caching

```python
# Framework root is calculated once at import time
FRAMEWORK_ROOT = find_framework_root()

# All subsequent calls use cached value
def get_framework_root() -> Path:
    return FRAMEWORK_ROOT  # No recalculation
```

### 2. Path Object Efficiency

```python
# Path objects are efficient for multiple operations
from core.paths import get_data_path

data_path = get_data_path("large_dataset")
if data_path.exists():
    size = data_path.stat().st_size
    modified = data_path.stat().st_mtime
    is_dir = data_path.is_dir()
```

## Related Documentation

- [Application Context](app-context.md) - Service container and dependency injection
- [Configuration System](config-system.md) - Configuration file management
- [Database Module](../modules/database-module.md) - Database path management
- [Module Creation Guide](../module-creation-guide-v2.md) - Using paths in modules

---

The Path Management system provides the foundation for consistent file and directory access throughout the framework, enabling modules to work reliably regardless of execution context while maintaining clean separation of data.