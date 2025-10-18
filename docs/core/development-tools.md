# Development Tools

The framework provides a comprehensive set of development tools to help you create, validate, and maintain modules efficiently. These tools follow the framework's patterns and ensure consistency across all modules.

## Quick Reference

### Essential Tools
```bash
# Create a new module with interactive prompts
python tools/scaffold_module.py

# Validate module compliance
python tools/compliance/compliance.py --validate standard.my_module

# Update framework core files
python tools/update_core.py

# Clear all log files for clean testing
python tools/clear_logs.py
```

---

## Module Scaffolding

### `scaffold_module.py` - Module Creation Tool

**Purpose**: Creates framework-compliant module structures with all necessary files and patterns.

#### Interactive Mode
```bash
python tools/scaffold_module.py
```
The tool will prompt you for:
- **Module name** - Used for directory and service names
- **Module type** - `core`, `standard`, or `extensions`
- **Features** - Database, API, Streamlit UI, settings
- **Description** - Module purpose documentation

#### Command Line Mode
```bash
# Create a standard module with database and API
python tools/scaffold_module.py --name my_module --type standard --features database,api

# Create a core module with all features
python tools/scaffold_module.py --name auth_manager --type core --features database,api,ui_streamlit,settings
```

#### Generated Structure
```
modules/standard/my_module/
├── api.py              # Module class with decorators and API endpoints
├── services.py         # Business logic service class  
├── settings.py         # Pydantic configuration schema
├── database.py         # Database operations (if database feature selected)
├── db_models.py        # SQLAlchemy models (if database feature selected)
├── api_schemas.py      # API request/response models (if api feature selected)
└── ui.py              # Streamlit interface (if ui_streamlit feature selected)
```

#### Key Features
- **100% Framework Compliance** - ALL 12 mandatory decorators included
- **Mandatory-All-Decorators** - No missing decorators, guaranteed 14/14 processing steps
- **Error handling** - Result pattern implemented in all generated code
- **Two-phase initialization** - Proper `setup_infrastructure()` and `initialize_phase2()`
- **Complete decorator stack** - All 12 decorators in correct order:
  1. `@inject_dependencies('app_context')`
  2. `@register_service(...)`
  3. `@require_services([...])`
  4. `@initialization_sequence("setup_infrastructure", phase="phase1")`
  5. `@phase2_operations("initialize_phase2")`
  6. `@auto_service_creation(service_class="...")`
  7. `@register_api_endpoints(router_name="router")`
  8. `@register_database(database_name=...)`
  9. `@enforce_data_integrity(strict_mode=True, anti_mock=True)`
  10. `@module_health_check(check_function=None)`
  11. `@graceful_shutdown(method="cleanup_resources", timeout=30)`
  12. `@force_shutdown(method="force_cleanup", timeout=5)`
- **Lifecycle methods** - Includes `cleanup_resources()` and `force_cleanup()`
- **Database integration** - integrity_session pattern if database selected
- **Type safety** - Full type hints and Pydantic v2 validation
- **Settings registration** - Mandatory Phase 1 Pydantic settings registration

#### Available Features

| Feature | Description | Files Generated |
|---------|-------------|-----------------|
| `database` | Database operations with Result pattern | `database.py`, `db_models.py` |
| `api` | FastAPI endpoints with error handling | API routes in `api.py`, `api_schemas.py` |
| `ui_streamlit` | Streamlit interface components | `ui.py` |
| `settings` | Pydantic settings with validation | `settings.py` |

---

## Compliance Validation

### `compliance.py` - Code Standards Validation

**Purpose**: Validates modules against framework standards and patterns, ensuring consistency and catching common issues.

#### Basic Usage
```bash
# Validate a specific module
python tools/compliance/compliance.py --validate standard.my_module

# Validate all modules
python tools/compliance/compliance.py --validate-all

# Generate compliance report
python tools/compliance/compliance.py --report
```

#### Advanced Usage
```bash
# Verbose validation with detailed output
python tools/compliance/compliance.py --validate-verbose standard.my_module

# Check compliance without updating files
python tools/compliance/compliance.py --validate-claims standard.my_module

# Debug standards discovery
python tools/compliance/compliance.py --tool-debug standard.my_module
```

#### Validation Categories

**Core Implementation Standards**
- Terminal-compatible text encoding (ASCII-only)
- Service registration patterns (`@register_service`)
- Two-phase initialization compliance
- Module dependency management
- Service method documentation

**Database Standards** 
- Asynchronous database operations (integrity_session pattern)
- Proper database model definitions
- Database naming conventions

**API Standards**
- Proper error handling in endpoints
- Request/response schema validation
- Consistent API patterns

**Testing & Documentation**
- Module documentation completeness
- Test coverage requirements
- Example usage patterns

#### Understanding Results
```bash
## Core Implementation Standards
- Service Registration Pattern: Yes
- Two-Phase Initialization: Yes  
- Module Dependency Management: No
  - Missing required dependency declaration for 'core.database'

## Database Standards  
- Asynchronous Database Operations (Phase 4): No
  - Missing pattern 'integrity_session_pattern' in services.py
```

**Compliance Status**:
- ✅ **Yes** - Standard is properly implemented
- ❌ **No** - Standard is missing or incorrect (with specific details)
- ⚠️ **Partial** - Some aspects implemented, others need attention

---

## Framework Updates

### `update_core.py` - Framework Update System

**Purpose**: Updates framework core files while preserving your application modules and data.

#### Basic Usage
```bash
# Check for available updates
python tools/update_core.py --check-only

# Update to latest version
python tools/update_core.py

# View available versions
python tools/update_core.py --list-versions
```

#### Backup and Rollback
```bash
# List available backups
python tools/update_core.py --list-backups

# Rollback to previous version
python tools/update_core.py --rollback

# Rollback to specific backup
python tools/update_core.py --rollback backup_20250831_143022
```

#### What Gets Updated
- `core/` directory - All framework infrastructure
- `modules/core/` - Framework core modules  
- `tools/` directory - Development tools
- `ui/` directory - Streamlit interface components
- `app.py`, `run_ui.py` - Main application files

#### What Stays Safe
- `modules/standard/` - Your application modules
- `data/` directory - Your databases and user data
- `.env` file - Your environment configuration
- `work/` directory - Your private workspace

---

## Utility Tools

### Development and Testing

**`clear_logs.py`** - Log Management
```bash
# Clear all log files for clean testing
python tools/clear_logs.py
```
Removes all files from `data/logs/` directory for fresh testing sessions.

**Module Disabling** - Quick Module Control
```bash
# Disable a module (no tools needed - just file system)
touch modules/standard/my_module/.disabled

# Re-enable a module
rm modules/standard/my_module/.disabled

# Disable core modules (advanced - may break framework)
touch modules/core/model_manager/.disabled
```
Completely prevents module loading during framework startup. Useful for troubleshooting, testing, or removing unwanted functionality.

**`check_module_status.py`** - Module Status Inspector
```bash
# Check status of all modules
python tools/check_module_status.py
```
Provides detailed information about module loading, initialization, and health status.

**`dev_watch.py`** - Development File Watcher
```bash
# Watch for file changes and restart application
python tools/dev_watch.py
```
Monitors module files and automatically restarts the application when changes are detected.

### Database Tools

**`database_inspection/`** - Database Analysis Tools
```bash
# Inspect SQLite databases
python tools/database_inspection/inspect_sqlite.py

# Inspect ChromaDB collections (if using vector storage)
python tools/database_inspection/inspect_chromadb.py
```

### Error Analysis

**`error_analysis/`** - Error Log Analysis
```bash
# Analyze error patterns
python tools/error_analysis/error_analysis.py

# Query error logs
python tools/error_analysis/error_query.py

# Generate error insights
python tools/error_analysis/compliance_insights.py
```

---

## Best Practices

### Module Development Workflow

1. **Create Module Structure**
   ```bash
   python tools/scaffold_module.py --name my_feature --type standard --features database,api
   ```

2. **Implement Business Logic**
   - Edit `services.py` with your core functionality
   - Use Result pattern for all operations
   - Follow two-phase initialization

3. **Validate Compliance**
   ```bash
   python tools/compliance/compliance.py --validate standard.my_feature
   ```

4. **Test and Iterate**
   ```bash
   python tools/clear_logs.py  # Clean logs for testing
   python app.py               # Test your module
   ```

5. **Final Validation**
   ```bash
   python tools/compliance/compliance.py --validate-verbose standard.my_feature
   ```

### Compliance Guidelines

- **Run compliance checks frequently** during development
- **Address issues immediately** - Don't accumulate compliance debt
- **Use scaffolding** - Start with generated code that's already compliant
- **Follow patterns** - The tools enforce framework patterns for consistency

### Framework Updates

- **Check for updates regularly** - New features and fixes
- **Test after updates** - Verify your modules still work correctly
- **Keep backups** - The system automatically creates backups before updates
- **Read changelogs** - Check for breaking changes before updating

---

## Troubleshooting

### Common Scaffolding Issues

**"Module already exists"**
- Solution: Choose a different name or remove the existing module directory

**"Invalid module type"**
- Solution: Use `core`, `standard`, or `extensions`

### Common Compliance Issues

**"MODULE COMPLIANCE: Missing decorators"**
- Solution: Use scaffolding tool to generate modules with all 12 decorators
- Never manually create modules - always use `python tools/scaffold_module.py`

**"Service Registration Pattern: No"**
- Solution: Add `@register_service("module_name.service", methods=[...])` with full method documentation

**"Missing @require_services decorator"**
- Solution: Add `@require_services([])` even if module has no external dependencies

**"Missing @register_database decorator"**
- Solution: Add `@register_database(database_name=None)` if module doesn't use database

**"Missing @module_health_check decorator"**
- Solution: Add `@module_health_check(check_function=None)` for default health check

**"Missing integrity_session_pattern"**
- Solution: Use `async with app_context.database.integrity_session()` for database operations

**"Two-Phase Initialization: No"**
- Solution: Implement both `setup_infrastructure()` (Phase 1) and `initialize_phase2()` (Phase 2)
- Phase 1 MUST register Pydantic settings model

**"Missing cleanup methods"**
- Solution: Implement both `cleanup_resources()` (async) and `force_cleanup()` (sync)

### Update System Issues

**"No releases found"**
- Cause: Network issues or repository problems
- Solution: Check internet connection and try again later

**"Backup failed"**
- Cause: Disk space or permission issues  
- Solution: Ensure adequate disk space and proper file permissions

The development tools provide a complete toolkit for efficient framework-based development, from module creation through validation and maintenance.