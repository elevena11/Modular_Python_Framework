# Core Framework Code Summary

This document summarizes the actual code and design patterns found in the core/ directory of the Reality Anchor Hub (RAH) Modular Framework. It focuses on the main files and highlights opportunities for improvement and standardization in how the core framework and modules interact.

---

## app_context.py

- **AppContext** is the central service container and state manager for the application.
- Handles:
  - Configuration and logging setup
  - Unique session ID and session info
  - API router creation
  - SQLite database engine/session setup (async, with retry logic for locked DBs)
  - Service registration and lookup (dependency injection)
  - Post-initialization hooks (for two-phase module init)
  - Model and database registration for modules
  - Module setup hooks (secondary init)
  - Startup warnings and logging
  - Settings management (register, get, update, reset, migration) via a settings service
  - Shutdown handler registration and execution
  - Force shutdown for all registered services

**Key patterns:**
- Explicit service registration and lookup
- Async database/session management
- Post-init hooks for module lifecycle
- Settings and migration hooks for modules
- Shutdown and force-shutdown support

---

## module_loader.py

- **ModuleLoader** discovers, loads, and manages all modules (core, standard, extensions).
- Handles:
  - Logging (dedicated file, not terminal)
  - Module discovery (one level of nesting, manifest.json required)
  - Dependency resolution (topological sort, warns on missing/circular deps)
  - Two-phase initialization: Phase 1 (register services/hooks), Phase 2 (complex ops via post-init hooks)
  - Async module loading (requires async initialize(app_context) in each module)
  - API route registration if present
  - Requirements auto-install (if enabled)
  - Module context registration and lookup
  - Startup warnings

**Key patterns:**
- Async, dependency-aware module loading
- Manifest-driven module metadata and requirements
- Dedicated logging and error handling
- Explicit API and service registration

---

## config.py

- **Settings** (Pydantic-based) for all core framework and app options.
- Handles:
  - App name, version, debug mode
  - Network and port config
  - Data directory, database URL, settings file
  - LLM API config
  - Session timeout, module directories, disabled modules, auto-install
  - CORS, API prefix, SQLite PRAGMAs, logging
  - Project-specific and federation settings

**Key patterns:**
- All config is environment-variable driven, with sensible defaults
- Pydantic validation and .env support

---

## paths.py

- Path management utilities for consistent access to data, logs, databases, and module data.
- Handles:
  - Finding the framework root (by searching for modules/ directory)
  - Getting/ensuring paths for data, logs, databases, memory, and per-module data
  - Exports constants for common root paths

**Key patterns:**
- Robust, cross-platform path resolution
- Ensures directories exist as needed

---

## Opportunities for Improvement & Standardization

1. **Service Registration/Discovery:**
   - The pattern is explicit but could be further standardized (e.g., required interface for all services, auto-discovery of services in modules).
2. **Module Lifecycle:**
   - Two-phase init is robust, but the interface for post-init hooks and setup hooks could be formalized (e.g., base class or decorator).
3. **Settings Management:**
   - Settings registration is async and robust, but modules must call it explicitly. Consider a convention or decorator for auto-registration.
4. **Database Registration:**
   - Model/database registration is explicit. Could standardize the interface for modules to declare their models/databases.
5. **Error Handling:**
   - Logging and error handling are explicit, but could be further standardized with a core error interface or base exception.
6. **Module API Exposure:**
   - Route registration is optional. Could require a standard method or decorator for all modules exposing APIs.
7. **Testing/Compliance:**
   - Consider enforcing a compliance check or test registration for all modules at load time.

---

> This summary is based on direct analysis of the actual code in the core/ directory and is intended as a source of truth for future improvements and standardization efforts.
