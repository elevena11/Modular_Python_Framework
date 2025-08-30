# Configuration System

The Configuration System (`core/config.py`) provides environment-based configuration management for the framework using Pydantic Settings.

## Overview

The configuration system handles all application settings through environment variables with sensible defaults. It uses Pydantic Settings for validation, type checking, and automatic environment variable loading.

## Key Features

- **Environment Variable Support**: All settings can be overridden via environment variables
- **Type Validation**: Automatic type checking and conversion
- **Default Values**: Sensible defaults for all settings
- **Pydantic Integration**: Full Pydantic validation and parsing
- **SQLite Configuration**: Optimized SQLite pragma statements

## Configuration Structure

### Application Settings
```python
# Core application configuration
APP_NAME: str = "Modular Framework"
APP_VERSION: str = "0.1.0"
DEBUG: bool = False  # From DEBUG environment variable
```

### Data Management
```python
# Data directory for all persistent data
DATA_DIR: str = "./data"  # From DATA_DIR environment variable

# Database configuration
DATABASE_URL: str = ""  # Auto-configured by AppContext if empty

# Settings file location
SETTINGS_FILE: str = "data/settings.json"  # Framework settings storage
```

### Module Configuration
```python
# Module system settings
MODULES_DIR: str = "modules"  # Module discovery directory
DISABLE_MODULES: List[str] = []  # Comma-separated list of modules to disable
AUTO_INSTALL_DEPENDENCIES: bool = True  # Automatic dependency installation
```

### API Configuration
```python
# API server settings
API_PREFIX: str = "/api/v1"  # API route prefix
CORS_ORIGINS: List[str] = [  # CORS allowed origins
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "*"  # Development mode - allow all
]
```

### Session Management
```python
# Session timeout in minutes
SESSION_TIMEOUT: int = 30
```

### SQLite Configuration
```python
# SQLite pragma statements for optimization
SQLITE_PRAGMA_STATEMENTS: List[str] = [
    "PRAGMA journal_mode=WAL",      # Write-Ahead Logging
    "PRAGMA synchronous=NORMAL",    # Balance safety/speed
    "PRAGMA cache_size=10000",      # 10MB cache
    "PRAGMA foreign_keys=ON",       # Enforce constraints
    "PRAGMA busy_timeout=10000"     # 10s lock timeout
]
```

### LLM Integration (Optional)
```python
# LLM API configuration
LLM_API_URL: str = "http://127.0.0.1:11434/api/generate"
LLM_API_KEY: Optional[str] = None
LLM_MODEL: str = "llama3"
LLM_TIMEOUT: int = 120
LLM_MAX_RETRIES: int = 3
LLM_RETRY_DELAY: int = 2
LLM_TEMPERATURE: float = 0.7
LLM_TOP_P: float = 0.9
```

## Environment Variables

All configuration can be overridden using environment variables:

### Core Settings
```bash
# Application
APP_NAME="My Application"
APP_VERSION="1.0.0"
DEBUG=true

# Data
DATA_DIR="/path/to/data"
DATABASE_URL="sqlite:///custom/path/database/"

# Modules
MODULES_DIR="custom_modules"
DISABLE_MODULES="module1,module2"
AUTO_INSTALL_DEPENDENCIES=false

# API
API_PREFIX="/api/v2"
SESSION_TIMEOUT=60
```

### LLM Settings
```bash
# LLM Configuration
LLM_API_URL="http://localhost:11434/api/generate"
LLM_API_KEY="your-api-key"
LLM_MODEL="llama3"
LLM_TIMEOUT=180
LLM_MAX_RETRIES=5
LLM_RETRY_DELAY=3
LLM_TEMPERATURE=0.8
LLM_TOP_P=0.95
```

### Application-Specific Settings
```bash
# Example: Crypto-specific settings
TELEGRAM_BOT_TOKEN="your-bot-token"
TELEGRAM_BOT_USERNAME="@yourbot"
BINANCE_API_KEY="your-api-key"
BINANCE_API_SECRET="your-secret"
CHROMADB_PATH="data/chroma_db/"
LOG_LEVEL="DEBUG"
```

## Configuration Loading

### Basic Usage
```python
from core.config import settings

# Access configuration
app_name = settings.APP_NAME
debug_mode = settings.DEBUG
data_dir = settings.DATA_DIR
```

### In Framework Components
```python
class AppContext:
    def __init__(self, config):
        self.config = config
        self.data_dir = config.DATA_DIR
        self.database_url = config.DATABASE_URL
        self.api_prefix = config.API_PREFIX
```

### Environment File Support
The configuration system automatically loads from `.env` files:

```bash
# .env file
DEBUG=true
DATA_DIR="/custom/data"
DATABASE_URL="sqlite:///custom/database/"
LLM_MODEL="llama3"
```

## Validation and Type Safety

### Automatic Type Conversion
```python
# Environment variables are strings, but automatically converted
DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "30"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
```

### List Handling
```python
# Comma-separated lists are automatically parsed
DISABLE_MODULES: List[str] = [
    x.strip() for x in os.getenv("DISABLE_MODULES", "").split(",") if x.strip()
]
```

### Optional Values
```python
# Optional settings with None defaults
LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
```

## Database Configuration

### SQLite Optimization
The framework includes optimized SQLite pragma statements:

```python
SQLITE_PRAGMA_STATEMENTS: List[str] = [
    "PRAGMA journal_mode=WAL",      # Better concurrency
    "PRAGMA synchronous=NORMAL",    # Performance/safety balance
    "PRAGMA cache_size=10000",      # Larger cache for better performance
    "PRAGMA foreign_keys=ON",       # Data integrity
    "PRAGMA busy_timeout=10000"     # Handle concurrent access
]
```

### Database URL Configuration
```python
# Default: Auto-configured by AppContext
DATABASE_URL: str = ""

# Custom: Override with environment variable
DATABASE_URL="sqlite:///custom/path/database/"
```

## Module Configuration

### Module Discovery
```python
# Default modules directory
MODULES_DIR: str = "modules"

# Custom modules directory
MODULES_DIR="custom_modules"
```

### Module Disabling
```python
# Disable specific modules
DISABLE_MODULES="module1,module2,module3"

# In code
disabled = settings.DISABLE_MODULES
# Returns: ["module1", "module2", "module3"]
```

### Dependency Management
```python
# Auto-install module dependencies
AUTO_INSTALL_DEPENDENCIES: bool = True

# Disable auto-installation
AUTO_INSTALL_DEPENDENCIES=false
```

## Best Practices

### 1. Environment Variables
- Use environment variables for deployment-specific settings
- Keep sensitive data in environment variables, not in code
- Use `.env` files for local development

### 2. Default Values
- Provide sensible defaults for all settings
- Make the application work out-of-the-box
- Document all configuration options

### 3. Type Safety
- Use proper type annotations
- Implement validation for complex settings
- Handle type conversion explicitly

### 4. Documentation
- Document all configuration options
- Provide examples for common use cases
- Explain the purpose of each setting

## Configuration Examples

### Development Environment
```bash
# .env for development
DEBUG=true
DATA_DIR="./dev_data"
LOG_LEVEL="DEBUG"
SESSION_TIMEOUT=60
LLM_MODEL="llama3"
```

### Production Environment
```bash
# Production environment variables
DEBUG=false
DATA_DIR="/app/data"
DATABASE_URL="sqlite:///app/data/database/"
LOG_LEVEL="INFO"
SESSION_TIMEOUT=30
API_PREFIX="/api/v1"
```

### Custom Application
```bash
# Custom application settings
APP_NAME="My Custom App"
APP_VERSION="2.0.0"
MODULES_DIR="custom_modules"
DISABLE_MODULES="scheduler,model_manager"
```

## Extending Configuration

### Adding New Settings
```python
class Settings(BaseSettings):
    # Add new settings with defaults
    NEW_SETTING: str = os.getenv("NEW_SETTING", "default_value")
    CUSTOM_TIMEOUT: int = int(os.getenv("CUSTOM_TIMEOUT", "300"))
    
    # Optional settings
    API_TOKEN: Optional[str] = os.getenv("API_TOKEN")
```

### Custom Validation
```python
from pydantic import validator

class Settings(BaseSettings):
    CUSTOM_SETTING: str = "default"
    
    @validator('CUSTOM_SETTING')
    def validate_custom_setting(cls, v):
        if v not in ['option1', 'option2', 'option3']:
            raise ValueError('Must be one of: option1, option2, option3')
        return v
```

## Integration with Framework

### AppContext Integration
```python
class AppContext:
    def __init__(self, config):
        self.config = config
        # Use config values throughout the framework
        self.debug = config.DEBUG
        self.data_dir = config.DATA_DIR
```

### Module Access
```python
def initialize(app_context):
    config = app_context.config
    
    # Access configuration in modules
    debug_mode = config.DEBUG
    data_dir = config.DATA_DIR
    api_prefix = config.API_PREFIX
```

## Related Documentation

- [Application Context](app-context.md) - Service container and lifecycle
- [Module Loader](module-loader.md) - Module discovery and loading
- [Settings Module](../modules/settings-module.md) - Runtime settings management
- [Path Management](path-management.md) - Path utilities

---

The configuration system provides a robust foundation for managing application settings with proper validation, type safety, and environment variable support.