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

## Installation

**Important:** Use the release ZIP files, not git clone. The framework includes an update system that manages versioning and file tracking.

1. **Download Latest Release**
   - Go to [Releases](../../releases)
   - Download the latest `Modular_Python_Framework-vX.X.X.zip`
   - Extract to your desired location

2. **Install Dependencies**
   ```bash
   python install_dependencies.py
   ```

3. **Initialize Database**
   ```bash
   python setup_db.py
   ```

4. **Start Framework**
   ```bash
   python app.py
   ```

## Quick Start

1. **Create New Module**
   ```bash
   python tools/scaffold_module.py --name my_module --type standard
   ```

2. **View API Documentation**
   ```
   http://localhost:8000/docs
   ```

3. **Update Framework**
   ```bash
   python update_core.py
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

### Core Framework Documentation
- **[Getting Started](docs/core/module-development-guide.md)** - Complete guide to creating modules
- **[Architecture](docs/core/architecture.md)** - Framework design and patterns
- **[Decorators](docs/core/decorators.md)** - Service registration and decorator patterns
- **[Error Handling](docs/core/error-handling.md)** - Result pattern and structured logging
- **[Database](docs/core/database.md)** - Database architecture and integration

### Developer Resources
- **[docs/](docs/)** - Complete documentation index
- **[CLAUDE.md](CLAUDE.md)** - Detailed framework instructions for Claude Code
- **[API Documentation](http://localhost:8000/docs)** - Live API docs when running
