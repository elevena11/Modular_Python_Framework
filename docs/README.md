# Framework Documentation

Comprehensive documentation for the Modular Framework - a generic Python framework for building complex applications with clean architecture patterns.

## Documentation Structure

### 🏗️ [Core Framework](core/README.md)
Documentation for the core framework components that provide the foundation:
- **[Application Context](core/app-context.md)** - Service container and dependency injection system
- **[Configuration System](core/config-system.md)** - Environment-based configuration management
- **[Module Loader](core/module-loader.md)** - Module discovery, dependency resolution, and loading
- **[Path Management](core/path-management.md)** - Framework path utilities and directory management
- **[Framework Lifecycle](core/framework-lifecycle.md)** - Complete startup and shutdown processes

### 🔧 [Core Modules](modules/README.md)
Documentation for framework-provided modules that offer essential services:
- **[Database Module](modules/database-module.md)** - Multi-database architecture with SQLite support
- **[Settings Module](modules/settings-module.md)** - Hierarchical configuration management with validation
- **[Error Handler Module](modules/error-handler-module.md)** - Standardized error handling and logging
- **[Scheduler Module](modules/scheduler-module.md)** - Background task scheduling and execution
- **[Global Module](modules/global-module.md)** - Framework standards enforcement and compliance
- **[Model Manager Module](modules/model-manager-module.md)** - Centralized AI model management and lifecycle

### 📐 [Framework Patterns](patterns/README.md)
Documentation for key patterns and practices used throughout the framework:
- **[Two-Phase Initialization](patterns/two-phase-initialization.md)** - Dependency-aware module initialization
- **[Result Pattern](patterns/result-pattern.md)** - Consistent error handling and return values
- **[Service Registration](patterns/service-registration.md)** - Dependency injection and service management
- **[Database Patterns](patterns/database-patterns.md)** - Multi-database implementation patterns

## Quick Start Guides

### 🚀 [Getting Started](../README.md)
- Framework installation and setup
- Running your first application
- Basic configuration

### 📦 [Module Creation Guide](module-creation-guide-v2.md)
- Creating new modules with the scaffolding tool
- Module structure and patterns
- Framework integration

### 🔄 [Development Workflow](enhanced-module-creation-workflow.md)
- Step-by-step module development process
- Testing and validation
- Compliance checking

## Development Resources

### 🛠️ [Development Tools](development-tools/README.md)
- **[Module Scaffolding](development-tools/module-scaffolding.md)** - Automated module creation
- **[Compliance Checking](development-tools/compliance-checking.md)** - Module validation
- **[Testing Strategies](development-tools/testing-strategies.md)** - Testing approaches
- **[Debugging Guide](development-tools/debugging.md)** - Debugging techniques

### 📊 [Database Documentation](database/README.md)
- Database implementation patterns
- Migration strategies
- Multi-database coordination
- Performance optimization

### 🤖 [AI-Driven Development](AI_DRIVEN_MODULAR_ECOSYSTEM.md)
- AI-assisted development patterns
- Code generation strategies
- Framework evolution approaches

## Architecture Overview

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

## Key Features

### 🏗️ **Modular Architecture**
- Independent, reusable modules
- Clean separation of concerns
- Pluggable module system

### 🔧 **Dependency Injection**
- Service container pattern
- Automatic dependency resolution
- Loose coupling between components

### 🗄️ **Database Per Module**
- Clean database separation
- Multiple database patterns
- Automatic schema management

### ⚙️ **Configuration Management**
- Environment-based configuration
- Module-specific settings
- Validation and type checking

### 🛡️ **Error Handling**
- Result pattern for consistent errors
- Structured error information
- Comprehensive error logging

### 🔄 **Two-Phase Initialization**
- Dependency-aware startup
- Graceful error handling
- Proper resource management

## Best Practices

### Module Development
1. **Follow the established patterns** in existing modules
2. **Use the scaffolding tool** for consistent structure
3. **Implement proper error handling** with Result pattern
4. **Document all public interfaces** thoroughly
5. **Run compliance checks** before integration

### Framework Integration
1. **Use dependency injection** for service access
2. **Follow two-phase initialization** for complex modules
3. **Register services early** in Phase 1
4. **Handle errors gracefully** with proper logging
5. **Test thoroughly** with integration tests

### Performance Considerations
1. **Use async operations** for I/O-bound tasks
2. **Implement proper caching** where appropriate
3. **Optimize database queries** and connections
4. **Monitor resource usage** and cleanup properly
5. **Profile critical paths** for bottlenecks

## Getting Help

### Documentation Navigation
- Use the table of contents above to find specific topics
- Each section includes practical examples and code snippets
- Cross-references link related concepts

### Common Issues
- Check the [troubleshooting guide](development-tools/troubleshooting.md)
- Review [compliance documentation](development-tools/compliance-checking.md)
- Consult [testing strategies](development-tools/testing-strategies.md)

### Development Support
- Follow the [development workflow](enhanced-module-creation-workflow.md)
- Use the [scaffolding tool](development-tools/module-scaffolding.md)
- Run [compliance checks](development-tools/compliance-checking.md)

---

This documentation provides comprehensive guidance for understanding, using, and extending the modular framework. Whether you're building your first module or contributing to the framework core, these resources will help you succeed.

---

## Application-Specific Documentation

### 📁 architecture/
Core architectural decisions and patterns for this application:
- `SINGLE_SOURCE_OF_TRUTH_ARCHITECTURE.md` - Database responsibility boundaries and data ownership rules

### 📁 framework/
Application framework requirements and principles:
- `DATA_INTEGRITY_REQUIREMENTS.md` - Absolute requirements for data integrity (NO MOCK DATA)

### 📁 modules/semantic/
Semantic analyzer module collection documentation:
- `SEMANTIC_ANALYZER_MODULE_SCOPE.md` - Module scope and responsibilities
- `semantic_cli_architecture_fix.md` - CLI orchestrator architecture

### 📁 workflows/
Application process and workflow documentation:
- `DOCUMENT_PROCESSING_WORKFLOW.md` - Document processing orchestrator pattern
- `old_system_workflow.md` - Previous system workflow analysis

---

### Quick Reference for This Application

#### For New Developers
1. Start with `framework/DATA_INTEGRITY_REQUIREMENTS.md`
2. Read `architecture/SINGLE_SOURCE_OF_TRUTH_ARCHITECTURE.md`
3. Review `workflows/DOCUMENT_PROCESSING_WORKFLOW.md`

#### For Module Development
1. Check `modules/semantic/` for existing patterns
2. Follow `architecture/SINGLE_SOURCE_OF_TRUTH_ARCHITECTURE.md` for data boundaries
3. Use framework development tools for scaffolding and compliance