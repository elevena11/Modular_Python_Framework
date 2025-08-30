# CLAUDE.md - Modular Python Framework

## Purpose

This is a **generic modular Python framework** designed for rapid development of scalable applications with clean architecture patterns. The framework provides:

- **Modular architecture** with independent, reusable modules
- **Two-phase initialization** (service registration → complex setup)
- **Result pattern** for consistent error handling
- **Database-per-module** for clean separation
- **Pydantic settings system** with validation and environment overrides
- **Phase 4 database architecture** with integrity session pattern
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
- **database**: SQLite management, Phase 4 integrity_session pattern
- **settings**: Pydantic-first configuration management with baseline + overrides
- **error_handler**: Standardized error patterns and logging
- **framework**: Application lifecycle and session management
- **model_manager**: GPU worker pools and ML model management

#### Module Structure Pattern
```
modules/standard/module_name/
├── api.py                 # Module initialization and FastAPI routes  
├── services.py            # Main business logic service class
├── settings_v2.py         # Pydantic configuration schema (Phase 4)
├── database.py           # Database operations (if needed)
├── db_models.py          # SQLAlchemy models (if needed)
└── api_schemas.py        # Pydantic request/response models
```

## Database Architecture (Phase 4)

### Framework Database (`data/database/framework.db`)
- Managed by `core.database` module
- Contains: modules, settings, logs, system status
- **Never write to this directly**

### Module Databases
- Each module can create its own SQLite database
- **Pattern**: Use `app_context.database.integrity_session()` for all database operations
- **Location**: `/data/database/module_name.db`
- **Registration**: Modules register databases with framework for utilities

### **Phase 4 Database Access Pattern**
```python
# CURRENT PATTERN (Phase 4)
async with app_context.database.integrity_session("database_name", "purpose") as session:
    # Database operations with automatic session management
    result = await session.execute(query)
    await session.commit()

# DEPRECATED (still works with warnings)
session_factory = database_service.get_database_session("database_name")
async with session_factory() as session:
    # Old pattern - generates deprecation warnings
```

### Database Implementation Pattern

**For comprehensive database documentation, see: `docs/development-tools/current-database-implementation.md`**

**IMPORTANT**: Use the semantic_core module (`modules/standard/semantic_core/`) as the reference implementation. This pattern has been battle-tested with 566 documents, 159K+ comparisons, and complex database operations.

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
# In services.py - Phase 4 pattern
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

### Pydantic Settings System (Phase 4)
**All non-sensitive configuration goes through Pydantic settings system**

- **Module Settings**: Each module defines `settings_v2.py` with Pydantic model
- **Environment Override**: `CORE_MODULE_NAME_SETTING_NAME=value`
- **Baseline Creation**: Defaults + environment variables merged once at startup
- **User Preferences**: Stored in database, merged at runtime
- **Type Safety**: Full Pydantic validation and type checking

#### Example Pydantic Settings:
```python
# modules/core/framework/settings_v2.py
class FrameworkSettings(BaseModel):
    model_config = ConfigDict(
        env_prefix="CORE_FRAMEWORK_",
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    app_title: str = Field(default="Reality Anchor Hub")
    debug_mode: bool = Field(default=True)
    environment: EnvironmentType = Field(default=EnvironmentType.DEVELOPMENT)
```

## Important Framework Patterns

### 1. Result Pattern (MANDATORY)
```python
from modules.core.error_handler.utils import Result

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

### 3. Database Access (Phase 4)
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
2. **Implement settings_v2.py** with Pydantic configuration schema
3. **Build services.py** with main business logic
4. **Add database operations** using `integrity_session()` pattern
5. **Create API endpoints** in api.py
6. **Test compliance**: `python tools/compliance/compliance.py validate --module standard.module_name`

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
python tools/compliance/compliance.py validate --module standard.module_name

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

### Change Documentation (REQUIRED)
- **Document all changes**: Add entries to `docs/v2/development-journal/YYYY-MM-DD.md`
- **Standard format**: Technical context, architecture decisions, debugging insights
- **Document immediately**: Add entries right after implementing changes, not later
- **Focus on the "why"**: Capture reasoning behind changes for future reference

### Phase 4 Migration Notes
- **Active modules**: Use `integrity_session()` pattern (no warnings)
- **Disabled modules**: Will show deprecation warnings when enabled
- **Migration path**: Replace `get_database_session()` with `integrity_session()`
- **Purpose logging**: Include descriptive purpose for debugging

---

**This is a generic modular framework for building complex Python applications with clean architecture patterns. It provides the foundation for rapid development of maintainable, scalable applications.**