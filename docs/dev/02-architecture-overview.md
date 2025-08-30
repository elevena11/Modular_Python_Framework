# 2. Framework Architecture Deep-Dive

This section provides a comprehensive overview of the Reality Anchor Hub (RAH) Modular Framework architecture, focusing on its layered structure, core design patterns, and system lifecycle. This is intended for LLMs and advanced developers seeking to understand or extend the framework.

## 2.1 High-Level Architecture Diagram

```
+-------------------------------+
|        Application Layer      |
|         (app.py, UI)          |
+-------------------------------+
|        Core Framework         |
|  +-------------------------+  |
|  | App Context             |  |
|  | Config System           |  |
|  | Module Loader           |  |
|  | Path Management         |  |
|  +-------------------------+  |
+-------------------------------+
|         Core Modules          |
|  +-------------------------+  |
|  | Database   | Settings   |  |
|  | Error      | Scheduler  |  |
|  | Global     | ModelMgr   |  |
|  +-------------------------+  |
+-------------------------------+
|      Extension Modules         |
|   (Custom, non-standard)       |
+-------------------------------+
|      Standard Modules          |
|   (App-specific logic)         |
+-------------------------------+
```

## 2.2 Layered Structure

- **Application Layer**: Entry points (e.g., `app.py`, UI) that orchestrate the system.
- **Core Framework**: Foundational services—dependency injection (App Context), configuration, module loading, and path management.
- **Core Modules**: Essential services (database, settings, error handling, scheduler, global, model manager) provided by the framework.
- **Extension Modules**: Optional, custom modules that extend core functionality (placed in `modules/extensions/`).
- **Standard Modules**: Application-specific modules (placed in `modules/standard/`).

## 2.3 Key Design Patterns

- **Dependency Injection (DI)**: All services and modules are registered in the App Context, enabling loose coupling and easy extension.
- **Two-Phase Initialization**: Modules are initialized in two phases—service registration (Phase 1) and complex setup (Phase 2)—to resolve dependencies and ensure correct startup order.
- **Result Pattern**: All operations return standardized result objects, enabling consistent error handling and propagation throughout the framework.

## 2.4 Data Flow & Lifecycle

1. **Startup**
   - The application entry point (`app.py`) initializes the App Context and loads configuration.
   - The Module Loader discovers and registers all modules (core, extension, standard).
   - Each module undergoes two-phase initialization:
     - **Phase 1**: Register services, dependencies, and configuration schemas.
     - **Phase 2**: Perform complex setup (e.g., database migrations, background tasks).

2. **Runtime**
   - API/UI requests are routed through the application layer.
   - The App Context provides dependency injection for all services and modules.
   - Modules interact via registered services, using the result pattern for error handling.
   - Background tasks and schedulers run as needed.

3. **Shutdown**
   - Graceful shutdown handlers ensure all resources (DB connections, background tasks) are properly closed.

## 2.5 LLM-Friendly Notes

- All extension points are explicit and documented in the following sections.
- The architecture is designed for modularity, testability, and ease of reasoning for both LLMs and human developers.
- Code samples and extension guides are provided in later sections.

---

Continue to [3. Core Concepts & Extension Points](03-core-concepts.md)
