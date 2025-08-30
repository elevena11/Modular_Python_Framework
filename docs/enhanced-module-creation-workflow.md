# Enhanced Module Creation Workflow Guide

**Version: 3.0**  
**Updated: June 11, 2025**  
**Status: Mandatory Implementation Guide**

## Overview

This guide establishes the MANDATORY workflow for creating modules in the VeritasForma Framework. Following this workflow ensures compliance with framework standards and prevents common implementation issues.

[WARNING] **CRITICAL**: This workflow is not optional. All modules MUST follow these steps to ensure framework compliance and prevent integration issues.

## Mandatory Workflow Steps

### Step 1: Use the Module Scaffolder
```bash
python tools/scaffold_module.py --name your_module --type standard --features database,api,settings
```

**Required**: Always use the scaffolder as it generates framework-compliant templates with proper error handling patterns.

### Step 2: Implement Your Business Logic
Write the actual functionality your module needs:

1. Implement service methods in `services.py`
2. Add API endpoints if needed - **MUST use dependency injection pattern**
3. Create database models if using database features
4. Build UI components if using UI features

**CRITICAL API Pattern**: For any FastAPI endpoints, you MUST use the dependency injection pattern:

```python
from fastapi import APIRouter, HTTPException, Depends, Request

def get_module_service():
    """Dependency to get the module service."""
    async def _get_module_service(request: Request):
        return request.app.state.app_context.get_service(f"{MODULE_ID}.service")
    
    return _get_module_service

@router.get("/status")
async def get_status(service = Depends(get_module_service())):
    if not service:
        raise HTTPException(status_code=503, detail="Service unavailable")
    return {"status": "active"}
```

**DO NOT use global service_instance patterns** - this will cause module_dependency compliance failures.

**Important**: Follow framework patterns as you implement (Result pattern, error handling, etc.)

### Step 3: Add Environment Variables (if handling sensitive data)
If your module handles sensitive data or configuration:

1. Create `.env` file in your module directory
2. Add environment variable loading following the veritas_knowledge_graph pattern
3. Use `os.getenv()` with secure fallbacks in module_settings.py

### Step 4: Test Your Implementation (Unit Tests)
```bash
# Run unit tests only
pytest tests/modules/standard/your_module/
```

### Step 5: Run Compliance Check (Before Framework Integration)
```bash
python tools/compliance/compliance.py validate --module standard.your_module
```

**CRITICAL**: Run this BEFORE testing with `python app.py`. Framework integration will fail with cryptic errors if compliance issues exist (wrong settings types, missing error handling, etc.).

### Step 6: Fix Compliance Issues
1. Open the generated `compliance.md` file in your module
2. Address each `No` item that applies to your module's functionality
3. For standards that don't apply, document in the **Exceptions** section:
   ```markdown
   ## Exceptions
   # Module does not use database functionality
   # Module has no API endpoints - uses direct service access only
   # Settings not needed for this utility module
   ```
4. Re-run compliance check until legitimate issues are resolved

**Why This Matters**: If you skip this step and go straight to `python app.py`, you'll get mysterious errors about "Unknown type boolean" or missing imports, and won't know these are standards violations.

### Step 7: Framework Integration Test
```bash
python app.py
```

**Now**: With compliance issues fixed, any remaining errors are actual integration problems, not standards violations.

## Critical Guidelines

### Settings Structure - MANDATORY FLAT STRUCTURE
All modules MUST use flat settings structure. Nested objects are FORBIDDEN:

**[INCORRECT] FORBIDDEN - Nested Structure:**
```python
DEFAULT_SETTINGS = {
    "database": {"host": "...", "port": 5432},  # NO!
    "cache": {"enabled": True, "size": 1000}    # NO!
}
```

**[CORRECT] REQUIRED - Flat Structure:**
```python
DEFAULT_SETTINGS = {
    "database.host": "localhost",
    "database.port": 5432,
    "cache.enabled": True,
    "cache.size": 1000
}
```

**Read**: `docs/development-tools/settings-structure-standard.md` for complete requirements.

### Error Handling - MANDATORY
Every module MUST implement these patterns:

1. **Import error_message utility**:
   ```python
   from modules.core.error_handler.utils import error_message, Result
   ```

2. **Service methods return Result objects**:
   ```python
   async def your_method(self, data: dict) -> Result:
       try:
           # Your logic here
           return Result.success(data={"status": "completed"})
       except Exception as e:
           logger.error(error_message(
               module_id=MODULE_ID,
               error_type="YOUR_ERROR_TYPE",
               details=f"Error description: {str(e)}",
               location="your_method()"
           ))
           return Result.error(
               code="YOUR_ERROR_CODE",
               message="User-friendly error message"
           )
   ```

3. **API endpoints use create_error_response**:
   ```python
   from modules.core.error_handler.utils import create_error_response
   
   @api_router.get("/endpoint")
   async def your_endpoint():
       try:
           # Your logic here
           return {"status": "success"}
       except Exception as e:
           return create_error_response(
               error_code="ENDPOINT_ERROR",
               message="User-friendly error message",
               details={"error": str(e)}
           )
   ```

### Settings Management - MANDATORY
If your module uses settings:

1. **Always include environment variable support**:
   ```python
   import os
   from pathlib import Path
   
   # Load .env file
   def load_env_file():
       env_file = Path(__file__).parent / ".env"
       if env_file.exists():
           # Implementation here
   
   load_env_file()
   
   DEFAULT_SETTINGS = {
       "database_uri": os.getenv("DB_URI", "default_value"),
       "api_key": os.getenv("API_KEY", ""),
   }
   ```

2. **Include UI_METADATA and VALIDATION_SCHEMA**
3. **Use correct type names**: `bool`, `int`, `float`, `str` (not `boolean`, `integer`, etc.)

### Two-Phase Initialization - MANDATORY
Every module MUST implement:

1. **Phase 1 (initialize)**: Register services, models, settings
2. **Phase 2 (setup_module)**: Initialize complex operations, database connections

## Common Mistakes to Avoid

### [INCORRECT] Skip compliance checks
- **Problem**: Issues compound and become harder to fix
- **Solution**: Always run compliance checks immediately after scaffolding

### [INCORRECT] Hardcode credentials
- **Problem**: Security vulnerability, inflexible configuration
- **Solution**: Always use environment variables with secure fallbacks

### [INCORRECT] Ignore error handling patterns
- **Problem**: Inconsistent error reporting, debugging difficulties
- **Solution**: Follow the mandatory error handling patterns above

### [INCORRECT] Wrong validation schema types
- **Problem**: Settings validation fails with cryptic errors
- **Solution**: Use `bool`, `int`, `float`, `str` (not JSON Schema types)

### [INCORRECT] Skip Result pattern
- **Problem**: Inconsistent service method interfaces
- **Solution**: All service methods MUST return Result objects

## Compliance Tool Integration

The compliance tool is your primary quality gate:

### Understanding Compliance Reports
```markdown
## Core Implementation Standards
- Settings API v2: No
  - Missing pattern 'environment_variable_loading' in module_settings.py
  - Missing UI_METADATA definition

## Error Handling Standards  
- Layered Error Handling v1: No
  - Missing pattern 'error_message_usage' in services.py
  - Missing create_error_response import in api.py
```

### Fixing Compliance Issues
1. **Read the specific error message**: Each tells you exactly what's missing
2. **Search framework docs**: Use the error text to find implementation examples
3. **Look at working modules**: Study similar modules for patterns
4. **Re-run validation**: Check your fixes immediately

## Tools and Commands

### Essential Commands
```bash
# Create module with compliance
python tools/scaffold_module.py --name your_module --features database,api,settings

# Check compliance (MANDATORY after scaffolding)
python tools/compliance/compliance.py validate --module standard.your_module

# Fix issues and re-check (repeat until 100% compliant)
python tools/compliance/compliance.py validate --module standard.your_module

# Test loading
python app.py

# Run tests
pytest tests/modules/standard/your_module/
```

### Compliance Commands
```bash
# Validate specific module
python tools/compliance/compliance.py validate --module standard.your_module

# Validate all modules
python tools/compliance/compliance.py validate-all

# Generate compliance report
python tools/compliance/compliance.py --report

# Verbose output for debugging
python tools/compliance/compliance.py validate-verbose --module standard.your_module
```

## Success Criteria

Your module is complete when:

1. [CORRECT] Scaffolded with proper structure
2. [CORRECT] Compliance for implemented features (with documented exceptions for unused features)
3. [CORRECT] Loads without errors in `python app.py`
4. [CORRECT] All tests pass
5. [CORRECT] Environment variables used for sensitive data
6. [CORRECT] Error handling patterns implemented where applicable
7. [CORRECT] Settings properly configured if module uses settings

**Note**: Not every module needs every feature. Use the Exceptions section in `compliance.md` to document why certain standards don't apply: "Module does not use database", "No API endpoints needed", etc.

## Framework Integration Points

### Required Imports
```python
# Error handling (MANDATORY)
from modules.core.error_handler.utils import error_message, Result, create_error_response

# Settings (if using settings)
from pathlib import Path
import os

# Logging
import logging
logger = logging.getLogger(MODULE_ID)
```

### Required Patterns
- Two-phase initialization
- Result pattern for service methods
- error_message for structured logging
- create_error_response for API errors
- Environment variable loading for sensitive data

## Getting Help

If you encounter issues:

1. **Check compliance.md**: Your module's compliance file shows specific issues
2. **Search framework docs**: Use exact error messages as search terms
3. **Study working modules**: Look at similar modules for implementation patterns
4. **Use verbose compliance**: `python tools/compliance/compliance.py validate-verbose --module your.module`

Remember: The compliance tool is designed to guide you to correct implementations. Trust its guidance and fix issues immediately rather than deferring them.