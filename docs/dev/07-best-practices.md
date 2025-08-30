# 7. Best Practices & Gotchas

This section summarizes best practices, common pitfalls, and anti-patterns to avoid when developing or extending the RAH Modular Framework. These guidelines are designed for both LLMs and human developers.

## 7.1 Recommended Patterns

- **Follow the Module Structure:**
  - Use the standard directory and file layout for all modules (see Section 4.2).
- **Use Dependency Injection:**
  - Register and resolve all services via the App Context for loose coupling.
- **Leverage Two-Phase Initialization:**
  - Register services and dependencies in Phase 1, perform complex setup in Phase 2.
- **Return Result Objects:**
  - Use the Result pattern for all public APIs and error handling.
- **Type-Safe Configuration:**
  - Define settings with Pydantic schemas and validate on startup.
- **Write Tests and Run Compliance Checks:**
  - Ensure all modules pass the provided compliance and testing tools before integration.
- **Document Public Interfaces:**
  - Provide clear docstrings and markdown documentation for all APIs and extension points.
- **Use Async for I/O:**
  - Prefer async/await for database, network, and file operations.

## 7.2 Common Pitfalls

- **Circular Dependencies:**
  - Avoid modules that depend on each other directly; use service interfaces and explicit dependency declarations.
- **Blocking Operations in Async Code:**
  - Never run blocking code (e.g., heavy computation, file I/O) in async functions without offloading to a thread pool.
- **Unregistered Services:**
  - Always register new services in the App Context; missing registrations cause runtime errors.
- **Schema Drift:**
  - Keep database models and migration scripts in sync; always test migrations before deployment.
- **Silent Failures:**
  - Always log errors and return Result.failure for all error cases; never swallow exceptions silently.

## 7.3 Anti-Patterns to Avoid

- **Hardcoding Configuration:**
  - Never hardcode settings; always use the configuration system.
- **Direct Database Access:**
  - Avoid direct SQL or ORM access outside of module database utilities.
- **Global State:**
  - Do not use global variables for shared state; use the App Context.
- **Copy-Paste Code:**
  - Reuse existing utilities and patterns; avoid duplicating logic across modules.
- **Ignoring Compliance Tools:**
  - Always use the provided scaffolding, testing, and compliance tools to ensure framework compatibility.

## 7.4 LLM-Specific Guidance

- **Be Explicit:**
  - When generating code, always specify where new services, models, or routes should be registered.
- **Check for Extension Points:**
  - Before modifying core logic, look for explicit extension points or hooks.
- **Document All Changes:**
  - Add docstrings and markdown documentation for any new APIs or extension points.

---

Continue to [8. Changelog & Update Policy](08-changelog.md)
