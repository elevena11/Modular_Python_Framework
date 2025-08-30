# 3. Core Concepts & Extension Points

This section details the foundational concepts and extension points of the RAH Modular Framework. Each concept is described with its purpose, usage, and how it can be extended or customized by LLMs or developers.

## 3.1 App Context & Service Container

- **Purpose:** Central registry for all services, modules, and shared state.
- **How it works:**
  - On startup, the App Context is initialized and made globally accessible.
  - All core services (database, config, scheduler, etc.) and module services are registered here.
  - Dependency injection is performed by resolving services from the App Context.
- **Extension Point:**
  - Register new services or override existing ones by adding to the App Context during module initialization.
  - Example:
    ```python
    app_context.register_service('my_service', MyService())
    ```

## 3.2 Module Loader & Registration

- **Purpose:** Discovers, loads, and initializes all modules (core, extension, standard).
- **How it works:**
  - Scans module directories and loads modules based on manifest/config files.
  - Handles dependency resolution and initialization order.
  - Supports two-phase initialization (see Section 2).
- **Extension Point:**
  - Add new modules by placing them in the appropriate directory and providing a manifest/config.
  - Implement custom initialization hooks for advanced setup.

## 3.3 Configuration & Settings System

- **Purpose:** Centralized, environment-driven configuration for the framework and all modules.
- **How it works:**
  - Uses Pydantic-based schemas for type-safe, validated settings.
  - Supports environment variable overrides and module-specific settings.
- **Extension Point:**
  - Define new configuration schemas in your module and register them with the core config system.
  - Example:
    ```python
    class MyModuleSettings(BaseSettings):
        my_option: str = 'default'
    app_context.config.register('my_module', MyModuleSettings)
    ```

## 3.4 Database-Per-Module Pattern

- **Purpose:** Ensures clean separation of data and responsibilities between modules.
- **How it works:**
  - Each module can define its own SQLite database, managed via the core database utilities.
  - Databases are registered and discovered automatically at startup.
- **Extension Point:**
  - Add new database models in your module and use the provided utilities for migrations and access.
  - Example:
    ```python
    from core.database import get_database_base
    DATABASE_NAME = "my_module"
    ModuleBase = get_database_base(DATABASE_NAME)
    class MyTable(ModuleBase):
        __tablename__ = "my_table"
        id = Column(Integer, primary_key=True)
    ```

## 3.5 Error Handling & Logging

- **Purpose:** Provides consistent, structured error handling and logging across the framework.
- **How it works:**
  - Uses the Result pattern for all operations (success/failure with error info).
  - Centralized logging via the core logger, with support for module-specific loggers.
- **Extension Point:**
  - Implement custom error types or logging handlers in your module.
  - Always return Result objects for public APIs.

## 3.6 Background Tasks & Scheduler

- **Purpose:** Enables modules to run background jobs, periodic tasks, and async operations.
- **How it works:**
  - Core scheduler module manages task registration and execution.
  - Modules can register tasks to run at startup, on a schedule, or in response to events.
- **Extension Point:**
  - Register new background tasks in your module's initialization code.
  - Example:
    ```python
    from core.scheduler import register_task
    async def my_background_job():
        ...
    register_task('my_job', my_background_job, schedule='@hourly')
    ```

---

Continue to [4. How to Extend the Framework](04-extending-framework.md)
