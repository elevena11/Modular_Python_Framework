# CLAUDE.md - Modular Python Framework

## Purpose

This is a **generic modular Python framework** designed for rapid development of scalable applications with clean architecture patterns. The framework provides:

- **Modular architecture** with independent, reusable modules
- **Two-phase initialization** (service registration → complex setup)
- **Result pattern** for consistent error handling
- **Database-per-module** for clean separation
- **Pydantic v2 settings system** with validation and environment overrides
- **Database architecture** with integrity session pattern
- **Decorator-based service registration** for clean module integration

## Framework Architecture

### Core Philosophy
- **Modular architecture** with independent, reusable modules
- **Two-phase initialization** (service registration → complex setup)
- **Result pattern** for consistent error handling
- **Database-per-module** for clean separation
- **Settings-driven configuration** with validation
- **Post-initialization hooks** for dependency management

### **CRITICAL: Systems Thinking Architecture**

**This is INFRASTRUCTURE CODE, not application code. Follow systems thinking principles:**

#### **Infrastructure Development Principles:**
- **Single correct pattern** - No multiple ways to do the same thing
- **Natural failure** - Wrong patterns fail automatically, no artificial checks
- **Clean break** - No backwards compatibility or legacy support
- **Enforced correctness** - Make wrong usage impossible, not just documented
- **No fallbacks** - If the pattern is wrong, it should break immediately

#### **Systems Integrity Over User Convenience:**
When choosing between making something "easy to use wrong" vs "impossible to use wrong", always choose impossible. Infrastructure should be **opinionated and enforcing**, not flexible and forgiving.

### Key Framework Components

#### Core Modules (`modules/core/`)
- **database**: SQLite management with integrity_session pattern
- **settings**: Pydantic v2 configuration management with baseline + overrides
- **error_handler**: Standardized error patterns and logging
- **framework**: Application lifecycle and session management
- **model_manager**: Optional AI model management (disabled by default)

#### Module Structure Pattern
```
modules/standard/module_name/
├── api.py                 # Module initialization and FastAPI routes  
├── services.py            # Main business logic service class
├── settings.py            # Pydantic v2 configuration schema
├── database.py           # Database operations (if needed)
├── db_models.py          # SQLAlchemy models (if needed)
└── api_schemas.py        # Pydantic request/response models
```

## Database Architecture

### Framework Database (`data/database/framework.db`)
- Managed by `core.database` module
- Contains: modules, settings, logs, system status
- **Never write to this directly**

### Module Databases
- Each module can create its own SQLite database
- **Pattern**: Use `app_context.database.integrity_session()` for all database operations
- **Location**: `/data/database/module_name.db`
- **Registration**: Modules register databases with framework for utilities

### **Database Access Pattern**
```python
# CURRENT PATTERN - integrity_session
async with app_context.database.integrity_session("database_name", "purpose") as session:
    # Database operations with automatic session management
    result = await session.execute(query)
    await session.commit()
```

### Database Implementation Pattern

**For comprehensive database documentation, see: `docs/database.md`**

#### Quick Reference:
```python
# In db_models.py
DATABASE_NAME = "module_name"  # Required for discovery
ModuleBase = get_database_base(DATABASE_NAME)

class MyTable(ModuleBase):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)
```

```python
# In services.py - integrity_session pattern
async with app_context.database.integrity_session("module_name", "operation_purpose") as session:
    # Database operations here
```

## Configuration Management

### Environment Variables (.env)
**Only for sensitive credentials - API keys, tokens, secrets**
```bash
# Required API Keys and Tokens
API_KEY=your_api_key
API_SECRET=your_secret
BOT_TOKEN=your_bot_token
```

### Pydantic v2 Settings System
**All non-sensitive configuration goes through Pydantic v2 settings system**

- **Module Settings**: Each module defines `settings.py` with Pydantic v2 model
- **Environment Override**: `CORE_MODULE_NAME_SETTING_NAME=value`
- **Baseline Creation**: Defaults + environment variables merged once at startup
- **User Preferences**: Stored in database, merged at runtime
- **Type Safety**: Full Pydantic v2 validation and type checking

#### Example Pydantic Settings:
```python
# modules/core/framework/settings.py
class FrameworkSettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_FRAMEWORK_",
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    app_title: str = Field(default="Modular Python Framework")
    debug_mode: bool = Field(default=False)
    environment: EnvironmentType = Field(default=EnvironmentType.PRODUCTION)
```

## Important Framework Patterns

### 1. Result Pattern (MANDATORY)
```python
from core.error_utils import Result

async def some_operation() -> Result:
    try:
        # ... operation logic
        return Result.success(data=result)
    except Exception as e:
        return Result.error(
            code="OPERATION_FAILED", 
            message="Description",
            details={"error": str(e)}
        )
```

### 2. Phase 1/Phase 2 Architecture
```python
# Phase 1: Registration Only
def setup_infrastructure(self):
    # Only infrastructure setup - NO service access
    self.logger.info(f"{self.MODULE_ID}: Setting up infrastructure")

def register_settings(self):
    # Register Pydantic model with app_context
    self.app_context.register_pydantic_model(self.MODULE_ID, SettingsModel)

# Phase 2: Complex Operations
async def initialize_service(self):
    # Access other services here (available in Phase 2)
    settings_service = self.app_context.get_service("core.settings.service")
    settings_result = await settings_service.get_typed_settings(...)
```

### 3. Database Access
```python
# Current pattern - use everywhere
async with app_context.database.integrity_session("database_name", "purpose") as session:
    # Database operations with automatic lifecycle management
    result = await session.execute(query)
    await session.commit()
```

### 4. Path Management
```python
# Use core/paths.py for consistent path handling
from core.paths import (
    get_framework_root,      # Framework root directory
    get_data_path,           # Framework data/ directory paths
    get_module_data_path,    # Module-specific data paths
    ensure_data_path,        # Create directory if needed
)
```

## API Endpoints

### Framework API
**Base URL**: `http://localhost:8000/api/v1/`

#### Core Framework Endpoints
- **Settings Management**: `GET/POST /api/v1/settings/`
- **System Status**: Framework provides core system status endpoints
- **API Documentation**: `GET /docs` (FastAPI auto-generated docs)

#### Current Testing Commands
```bash
# Framework status and settings
curl -X GET "http://localhost:8000/api/v1/settings/settings/core.framework"

# API documentation
curl -X GET "http://localhost:8000/docs"

# Health check
curl -X GET "http://localhost:8000/api/v1/"
```

## Development Workflow

### 1. Module Creation
```bash
# Use scaffolding tool for new modules
python tools/scaffold_module.py --name module_name --type standard --features database,api,settings

# Or interactive mode
python tools/scaffold_module.py
```

### 2. Development Process
1. **Configure MODULE_* constants** in api.py for module metadata
2. **Implement settings.py** with Pydantic v2 configuration schema
3. **Build services.py** with main business logic
4. **Add database operations** using `integrity_session()` pattern
5. **Create API endpoints** in api.py
6. **Test compliance**: `python tools/compliance/compliance.py --validate standard.module_name`

### 3. Framework Integration Testing
```bash
# Initialize database
python setup_db.py

# Test module loading
python app.py

# Check logs for initialization success
```

## Quick Reference Commands

```bash
# Setup
python setup_db.py                    # Initialize database (required first time)
python app.py                         # Start application

# Development  
python tools/scaffold_module.py       # Create new module
python tools/compliance/compliance.py --validate standard.module_name

# Log Management
python tools/clear_logs.py            # Clear all log files for clean testing

# Testing
python -m pytest                      # Run all tests
```

## Development Guidelines

### Code Standards
- **NO EMOJIS**: Never use emojis or Unicode symbols in code, documentation, README files, or any project files
- **ASCII-Only Text**: All text must be compatible with ASCII encoding for terminal compatibility
- **Phase 1/Phase 2 Compliance**: Never access services during Phase 1 methods
- **Database Access**: Always use `app_context.database.integrity_session()` pattern

### Framework Compliance
- Run compliance checks regularly: `python tools/compliance/compliance.py --validate standard.module_name`
- Address compliance issues promptly

### Documentation
- **Follow patterns**: Use established documentation in `docs/` directory
- **Update when changing core systems**: Keep documentation current with code changes
- **Security considerations**: Document any security implications of changes

### Database Pattern Notes
- **Current pattern**: Use `integrity_session()` for all database operations
- **Purpose logging**: Include descriptive purpose for debugging and monitoring
- **Session management**: Framework handles all lifecycle automatically

---

**This is a generic modular framework for building complex Python applications with clean architecture patterns. It provides the foundation for rapid development of maintainable, scalable applications.**