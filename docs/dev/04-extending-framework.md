# 4. How to Extend the Framework

This section provides a step-by-step guide for LLMs and developers to extend the RAH Modular Framework by creating new modules, integrating with the API/UI, and ensuring compliance and testability.

## 4.1 Types of Modules

- **Core Modules:** Essential framework services (e.g., database, settings, scheduler). Only modify or extend if you are enhancing the framework itself.
- **Extension Modules:** Custom, optional modules that add new features or integrations. Placed in `modules/extensions/`.
- **Standard Modules:** Application-specific modules for business logic. Placed in `modules/standard/`.

## 4.2 Module Structure & Required Files

Each module should follow this structure:

```
module_name/
├── manifest.json           # Metadata, dependencies, capabilities
├── api.py                  # FastAPI routes and module initialization
├── services.py             # Main business logic/service class
├── module_settings.py      # Configuration schema and defaults
├── database.py             # Database operations (if needed)
├── db_models.py            # SQLAlchemy models (if needed)
└── api_schemas.py          # Pydantic request/response models
```

- **manifest.json:** Declares module metadata, dependencies, and capabilities for the loader.
- **api.py:** Entry point for module initialization and API route registration.
- **services.py:** Contains the main logic and service classes.
- **module_settings.py:** Defines configuration options using Pydantic.
- **database.py/db_models.py:** (Optional) For modules with persistent storage needs.
- **api_schemas.py:** (Optional) For API request/response validation.

## 4.3 Registering Services & Dependencies

- Register new services in the App Context during module initialization (see Section 3.1).
- Declare dependencies in `manifest.json` for automatic resolution.
- Use dependency injection for accessing other services or modules.

**Example:**
```python
# In api.py
from core.app_context import app_context
from .services import MyService
app_context.register_service('my_service', MyService())
```

## 4.4 Adding New Database Models

- Define SQLAlchemy models in `db_models.py` using the database-per-module pattern (see Section 3.4).
- Use the core database utilities for migrations and access.

**Example:**
```python
from core.database import get_database_base
DATABASE_NAME = "my_module"
ModuleBase = get_database_base(DATABASE_NAME)
class MyTable(ModuleBase):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)
```

## 4.5 Integrating with the API/UI

- Register FastAPI routes in `api.py` for module-specific endpoints.
- Use Pydantic models in `api_schemas.py` for request/response validation.
- For UI integration, expose endpoints or services that the UI layer can consume.

**Example:**
```python
# In api.py
from fastapi import APIRouter
router = APIRouter()
@router.get("/my-endpoint")
async def my_endpoint():
    ...
```

## 4.6 Compliance & Testing

- Use the provided scaffolding and compliance tools to ensure your module meets framework standards.
- Write unit and integration tests for all public APIs and services.
- Run compliance checks before integration.

**Best Practices:**
- Follow the established patterns in existing modules.
- Document all public interfaces and configuration options.
- Use the result pattern for error handling.
- Test thoroughly, including edge cases and failure modes.

---

Continue to [5. Advanced Topics](05-advanced-topics.md)
