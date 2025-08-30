# Modular Python Framework

A generic modular Python framework designed for rapid development of scalable applications with clean architecture patterns.

## Features

- **Modular Architecture** - Independent, reusable modules with clean separation
- **Phase 4 Database Architecture** - Multi-database support with integrity_session pattern
- **Decorator-Based Registration** - Clean service and API endpoint registration
- **Pydantic Settings System** - Type-safe configuration with environment overrides
- **Two-Phase Initialization** - Service registration followed by complex setup
- **Result Pattern** - Consistent error handling across the framework
- **FastAPI Integration** - Automatic route discovery and API documentation
- **Compliance System** - Code quality validation and guidance tools

## Quick Start

1. **Initialize Database**
   ```bash
   python setup_db.py
   ```

2. **Start Framework**
   ```bash
   python app.py
   ```

3. **Create New Module**
   ```bash
   python tools/scaffold_module.py --name my_module --type standard
   ```

4. **View API Documentation**
   ```
   http://localhost:8000/docs
   ```

## Project Structure

```
Modular_Python_Framework/
├── core/                    # Framework engine
├── modules/core/            # Essential framework modules  
├── modules/standard/        # Your application modules (add here)
├── tools/                   # Development and maintenance tools
├── docs/                    # Framework documentation
├── app.py                  # Main framework entry point
├── setup_db.py             # Database initialization
├── framework_version.json  # Version tracking metadata
├── requirements.txt        # Framework dependencies
├── CLAUDE.md              # Detailed framework instructions
└── README.md              # This file
```

## Module Development

1. **Use Scaffolding Tool**
   ```bash
   python tools/scaffold_module.py
   ```

2. **Follow Framework Patterns**
   - Use `@register_service` and `@register_api_endpoints` decorators
   - Implement Pydantic settings in `settings.py`
   - Use `integrity_session()` pattern for database operations
   - Follow Result pattern for error handling

3. **Validate Compliance**
   ```bash
   python tools/compliance/compliance.py validate --module standard.my_module
   ```

## Architecture

- **Phase 1**: Service registration and infrastructure setup
- **Phase 2**: Complex initialization with service dependencies
- **Database per Module**: Clean separation with automatic discovery
- **Settings Management**: Pydantic models with environment variable overrides
- **Service Discovery**: Automatic registration with comprehensive documentation

## Requirements

- Python 3.8+
- FastAPI
- Pydantic 2.0+
- SQLAlchemy
- Uvicorn

## Documentation

See `CLAUDE.md` for comprehensive framework documentation and development guidelines.

## Version

Framework Version: 1.0.0  
Architecture Version: 4.0  
Release Date: 2025-08-30