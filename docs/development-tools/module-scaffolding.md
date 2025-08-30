# Module Scaffolding Tool

The module scaffolding tool (`tools/scaffold_module.py`) automatically generates compliant module structures, eliminating manual setup and ensuring framework compliance from the start.

## 🎯 Purpose

**Problem:** Creating a new module requires:
- Understanding complex framework patterns
- Following naming conventions properly
- Creating 8-12 files manually
- Writing boilerplate code correctly
- Ensuring compliance with 16+ standards
- Setting up proper two-phase initialization

**Solution:** Generate everything automatically with interactive configuration and proper naming.

## 🚀 Quick Start

### Interactive Mode
```bash
python tools/scaffold_module.py
```

This launches an interactive prompt that walks you through module configuration.

### Command-Line Mode (LLM-Friendly)
```bash
# Simple module with defaults
python tools/scaffold_module.py --name my_module

# Full-featured module (note: proper naming conventions)
python tools/scaffold_module.py --name user_analytics \
  --features database,api,ui_streamlit \
  --description "User analytics and tracking system" \
  --deps core.database,core.settings

# List available features
python tools/scaffold_module.py --list-features
```

### Common CLI Patterns
```bash
# API-only service
python tools/scaffold_module.py --name payment_service --features api

# Database-heavy module
python tools/scaffold_module.py --name data_store --features database,api,settings

# UI-focused extension
python tools/scaffold_module.py --name admin_panel --features ui_streamlit,ui_gradio --type extensions

# Background worker
python tools/scaffold_module.py --name task_processor --features scheduler,database
```

### Example Session
```
🏗️  VeritasForma Module Scaffolder
==================================================

📦 Module name (e.g., 'my_feature'): user_analytics

📂 Module type:
   core: Core framework modules (essential functionality)
   standard: Standard modules (general-purpose features)  
   extensions: Extension modules (specialized functionality)
Choose type [standard]: standard

📝 Description [A user_analytics module for the VeritasForma Framework]: User analytics and tracking system

👤 Author [VeritasForma Team]: Analytics Team

⚙️  Available features:
   database: Database operations with SQLAlchemy models
   api: FastAPI REST endpoints with schemas
   ui_streamlit: Streamlit UI interface
   ui_gradio: Gradio UI interface
   scheduler: Background task scheduling
   settings: Module-specific settings management

Select features (comma-separated) [api,ui_streamlit]: database,api,ui_streamlit,settings

🔗 Dependencies [core.database,core.settings]: core.database,core.settings

📋 Summary:
   Name: user_analytics
   Type: standard
   Features: database, api, ui_streamlit, settings
   Dependencies: core.database, core.settings

✅ Create this module? (y/n) [y]: y
```

## 📁 Generated Structure

After running the scaffolding tool, you get a complete module structure:

```
modules/standard/user_analytics/
├── manifest.json                 # Module metadata
├── api.py                       # Framework integration (Phase 1 & 2)
├── services.py                  # Business logic
├── api_schemas.py              # Pydantic request/response models
├── database.py                 # Async database operations
├── db_models.py               # SQLAlchemy models
├── module_settings.py         # Configuration management
├── readme.md                  # Documentation
├── compliance.md              # Compliance status
└── ui/
    ├── __init__.py
    └── ui_streamlit.py        # Streamlit interface

tests/modules/standard/user_analytics/
├── __init__.py
├── test_service.py           # Service unit tests
└── test_compliance.py        # Compliance tests
```

## 🔧 Feature Configuration

### Core Features (Always Included)
- **manifest.json** - Module metadata and dependencies
- **api.py** - Two-phase initialization and framework integration
- **services.py** - Business logic and service class
- **readme.md** - Module documentation
- **compliance.md** - Compliance tracking

### Optional Features

#### Database Operations (`database`)
When selected, generates:
- **db_models.py** - SQLAlchemy models with proper patterns
- **database.py** - Async CRUD operations
- Adds `core.database` dependency automatically

```python
# Example generated model
class UserAnalyticsItem(Base):
    __tablename__ = "user_analytics_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    metadata = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)
```

#### API Endpoints (`api`)
When selected, generates:
- **api_schemas.py** - Pydantic models for validation
- FastAPI routes in api.py
- Proper error handling and response models

```python
# Example generated schema
class UserAnalyticsRequest(BaseModel):
    name: str = Field(..., description="Name of the item")
    description: Optional[str] = Field(None, description="Optional description")
```

#### UI Interfaces (`ui_streamlit`, `ui_gradio`)
When selected, generates:
- **ui/ui_streamlit.py** or **ui/ui_gradio.py**
- Complete UI interface with service integration
- Status monitoring and testing components

#### Settings Management (`settings`)
When selected, generates:
- **module_settings.py** - Configuration management
- Environment variable support
- Settings validation and defaults

#### Background Tasks (`scheduler`)
When selected, adds:
- Scheduler dependency
- Background task examples
- Task management patterns

## 📝 Generated Code Quality

### Framework Compliance
All generated code follows framework standards:
- ✅ **Two-Phase Initialization** - Proper Phase 1 and Phase 2 implementation
- ✅ **Service Registration** - Correct service and shutdown handler registration
- ✅ **Module Structure** - All required files and patterns
- ✅ **Dependency Management** - Proper dependency declaration
- ✅ **Error Handling** - Consistent error patterns

### Code Patterns
- **Async/await** throughout for database operations
- **Type hints** for better IDE support and validation
- **Logging** with proper module-specific loggers
- **Exception handling** with graceful degradation
- **Documentation** with examples and usage

### Testing Ready
- **Pytest structure** with fixtures and parametrized tests
- **Compliance tests** that validate framework requirements
- **Service tests** for business logic validation
- **Mock support** for isolated testing

## 🎨 Customization

### Module Types

#### Core Modules (`core`)
- Essential framework functionality
- High reliability requirements
- Strict compliance standards
- Minimal external dependencies

#### Standard Modules (`standard`)
- General-purpose features
- Balanced functionality and complexity
- Standard compliance requirements
- Moderate dependencies allowed

#### Extension Modules (`extensions`)
- Specialized functionality
- Domain-specific features
- Flexible compliance (with justification)
- External dependencies encouraged

### Dependency Management
The tool automatically suggests dependencies based on features:
- **Database** → `core.database`
- **Settings** → `core.settings`
- **Scheduler** → `core.scheduler`
- **Background tasks** → `core.scheduler`

### Custom Templates
You can extend the scaffolding by modifying the tool:
- Add new features to `available_features`
- Create custom file generators
- Add domain-specific patterns

## 🔄 Development Workflow

### 1. Scaffold Module
```bash
python tools/scaffold_module.py
# Interactive configuration
# ✅ Complete module structure generated
```

### 2. Validate Generation
```bash
python tools/pytest_compliance.py --module your_module
# ✅ All compliance tests pass
```

### 3. Start Development
```bash
python tools/dev_watch.py --module your_module
# ✅ Real-time feedback enabled
```

### 4. Implement Business Logic
Edit generated files:
- **services.py** - Add your business logic methods
- **api.py** - Add custom API endpoints  
- **ui/ui_streamlit.py** - Build your user interface
- **database.py** - Add specialized database operations

### 5. Test Continuously
```bash
pytest tests/modules/standard/your_module/
# ✅ Unit tests validate functionality
```

## 🎯 Best Practices

### Before Scaffolding
1. **Plan your module** - Know what features you need
2. **Check dependencies** - Understand what services you'll use
3. **Consider UI needs** - Streamlit, Gradio, or both?

### During Configuration
1. **Start minimal** - You can add features later
2. **Follow naming conventions** - Use lowercase with underscores
3. **Choose appropriate type** - Core, standard, or extension

### After Scaffolding
1. **Read generated README** - Understand the structure
2. **Run compliance tests** - Ensure everything works
3. **Start with services.py** - Implement core business logic first

## 🔧 Troubleshooting

### Common Issues

#### "Module directory already exists"
```bash
# The tool will ask if you want to overwrite
⚠️  Module directory /path/to/module already exists. Overwrite? (y/n):
```
Choose 'y' to replace or 'n' to cancel and use a different name.

#### "Invalid module name"
Module names must:
- Contain only letters, numbers, underscores, hyphens
- Be valid Python identifiers
- Follow framework naming conventions (see [naming-conventions.md](../naming-conventions.md))

#### "Dependency not found"
Ensure dependency modules exist:
```bash
# Check available modules
python tools/check_module_status.py
```

### Validation Failures
If generated module fails compliance:
```bash
# Check specific issues
python tools/pytest_compliance.py --module your_module

# Watch for real-time feedback
python tools/dev_watch.py --module your_module
```

## 🚀 Advanced Usage

### Non-Interactive Mode (Future)
```bash
# Planned feature
python tools/scaffold_module.py \
  --name analytics \
  --type standard \
  --features database,api,ui_streamlit \
  --deps core.database,core.settings
```

### Custom Feature Sets
Create reusable feature combinations:
```python
# In scaffold_module.py
FEATURE_PRESETS = {
    'web_service': ['database', 'api', 'ui_streamlit'],
    'background_worker': ['database', 'scheduler', 'settings'],
    'ui_only': ['ui_streamlit', 'ui_gradio'],
}
```

### Integration with IDEs
- Generated code works with VS Code Python extension
- Type hints enable IntelliSense
- Pytest integration for test discovery
- Git integration for version control

---

**Next Steps:**
- Try scaffolding a simple module
- Explore the generated code structure
- Move on to [Development Watch Mode](./dev-watch.md) for iterative development