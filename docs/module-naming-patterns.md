# Module Naming and Service Access Patterns

## The Confusing Part: Two Different Naming Contexts

### 1. Manifest Definition (Short Names)
In `manifest.json`, use SHORT names without prefixes:

```json
{
  "id": "database",                    // Short name
  "name": "Database Module", 
  "dependencies": ["settings"]         // Short names in dependencies too? Need to verify
}
```

### 2. Service Registration and Access (Full Names)  
When modules are loaded, framework registers them with FULL names:

**Registration**: `core.database`, `standard.crypto_data_collector`, etc.

**Service Access**: Must use full names
```python
# Accessing core database service
db_service = app_context.get_service("core.database")

# Accessing crypto data collector from crypto analyzer
data_service = app_context.get_service("standard.crypto_data_collector") 
```

## Examples for Our Crypto Project

### Module Directory Structure
```
modules/standard/
├── crypto_data_collector/
│   └── manifest.json          # "id": "crypto_data_collector"
├── crypto_analyzer/  
│   └── manifest.json          # "id": "crypto_analyzer"
├── crypto_alerts/
│   └── manifest.json          # "id": "crypto_alerts"  
└── telegramBot/
    └── manifest.json          # "id": "telegramBot"
```

### Manifest Dependencies (Need to verify if these use short or full names)
```json
// crypto_analyzer/manifest.json
{
  "id": "crypto_analyzer",
  "dependencies": ["database", "crypto_data_collector"]  // Short or full names?
}
```

### Service Access in Code (Always Full Names)
```python
# In crypto_analyzer module
async def initialize(app_context):
    # Access database service
    db_service = app_context.get_service("core.database")
    
    # Access data collector service  
    data_service = app_context.get_service("standard.crypto_data_collector")
    
    # Register our own service
    app_context.register_service("standard.crypto_analyzer", analyzer_service)
```

## Questions to Resolve

1. **Dependencies in manifest.json**: Do they use short names or full names?
2. **Service registration patterns**: How exactly do modules register their services?
3. **Service naming convention**: Is it `core.database` or `core.database.services`?

## Why This is Confusing

- **Manifest files**: Use short, clean names (`"database"`)
- **Module loading**: Framework builds full names (`core.database`)  
- **Service access**: Must remember to use full names in code
- **Documentation**: Often doesn't clearly distinguish between these contexts

This dual naming system keeps manifests clean while ensuring no service name collisions at runtime.