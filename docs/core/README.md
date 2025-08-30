# Core Framework Components

This directory contains documentation for the core framework components that provide the foundation for the modular framework.

## Core Framework Files

The core framework consists of several key components located in the `core/` directory:

### [Application Context](app-context.md)
**File**: `core/app_context.py`
- Service container and dependency injection
- Module lifecycle management
- Session management
- Database connection handling

### [Configuration System](config-system.md)
**File**: `core/config.py`
- Environment-based configuration
- Settings validation and management
- Default configuration values
- Environment variable handling

### [Module Loader](module-loader.md)
**File**: `core/module_loader.py`
- Module discovery and loading
- Dependency resolution
- Module initialization orchestration
- Error handling during module loading

### [Path Management](path-management.md)
**File**: `core/paths.py`
- Framework path utilities
- Data directory management
- Module-specific path handling
- Cross-platform path resolution

### [Framework Lifecycle](framework-lifecycle.md)
- Application startup sequence
- Module initialization phases
- Shutdown procedures
- Error recovery mechanisms

## Architecture Overview

The core framework follows a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│                     (app.py)                               │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 Core Framework Layer                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ App Context │ │ Config      │ │ Module      │          │
│  │             │ │ System      │ │ Loader      │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
│  ┌─────────────┐                                           │
│  │ Path        │                                           │
│  │ Management  │                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Core Modules Layer                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Database    │ │ Settings    │ │ Error       │          │
│  │ Module      │ │ Module      │ │ Handler     │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Scheduler   │ │ Global      │ │ Model       │          │
│  │ Module      │ │ Module      │ │ Manager     │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 Standard Modules Layer                      │
│                (Application-specific modules)               │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. **Dependency Injection**
The framework uses a service container pattern for dependency management, allowing modules to request services without tight coupling.

### 2. **Two-Phase Initialization**
- **Phase 1**: Service registration and basic setup
- **Phase 2**: Complex initialization with dependencies

### 3. **Result Pattern**
All operations return Result objects for consistent error handling and success indication.

### 4. **Modular Architecture**
Each component has a specific responsibility and well-defined interfaces.

### 5. **Configuration Management**
Centralized configuration with environment variable support and validation.

## Getting Started

To understand the framework:

1. Start with [Application Context](app-context.md) to understand the service container
2. Read [Configuration System](config-system.md) for configuration management
3. Study [Module Loader](module-loader.md) for module lifecycle
4. Review [Framework Lifecycle](framework-lifecycle.md) for startup/shutdown flow

## Development Guidelines

### Framework Development
- Follow the established patterns in existing core components
- Maintain backward compatibility for stable APIs
- Document all public interfaces
- Use the Result pattern for error handling

### Module Integration
- Register services through the application context
- Use two-phase initialization for complex setup
- Follow the dependency injection pattern
- Implement proper error handling and logging

## Related Documentation

- [Core Modules](../modules/README.md) - Framework-provided modules
- [Framework Patterns](../patterns/README.md) - Common patterns and practices
- [Module Creation Guide](../module-creation-guide-v2.md) - Creating new modules

---

The core framework provides a solid foundation for building modular applications with clean architecture, proper dependency management, and robust error handling.