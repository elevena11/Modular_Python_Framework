# Standard Modules Directory

Application-specific modules that extend the core framework functionality.

## Purpose

- **Application Logic**: Module implementations for specific business requirements
- **Custom Features**: Application-specific functionality and services  
- **Domain Models**: Business domain implementations
- **Integration Modules**: Third-party service integrations

## Structure

Standard module structure:

```
modules/standard/my_module/
├── api.py                 # FastAPI endpoints (optional)
├── services.py            # Business logic service class
├── settings_v2.py         # Pydantic configuration schema
├── database.py           # Database operations (if needed)
├── db_models.py          # SQLAlchemy models (if needed)
└── api_schemas.py        # Request/response models (if API)
```

## Module Creation

Create a new module:
```bash
python tools/scaffold_module.py --name my_feature --type standard
```

## Framework Integration

Required patterns:
- Use decorators for registration (`@register_service`, `@register_api_endpoints`, etc.)
- Implement proper error handling with `Result` pattern
- Use Phase 1/Phase 2 initialization sequence
- Follow database integrity patterns if using databases

## Validation

Test module compliance:
```bash
python tools/compliance/compliance.py validate --module standard.my_feature
```

## Reference

- `modules/core/` - Framework core modules for architecture patterns
- `docs/` - Framework documentation and guides
- `tools/scaffold_module.py` - Module template generation

## Requirements

Modules are automatically discovered by the framework's module manager. Requirements:

- Follow decorator patterns for proper registration
- Implement required initialization methods
- Use framework error handling and logging systems