# UI System Improvements

**Status**: Documentation of needed improvements for future refactoring  
**Priority**: Low (collect information for future implementation)

## Current State

The UI system is "very old" and hasn't been looked at much. It works but has inconsistencies and missing functionality that would make development easier.

## Issues Identified

### 1. API Client Missing Generic Methods

**Problem**: The API client (`ui/services/api_client.py`) only has specific methods like:
- `get_frontend_config()`
- `get_modules()`
- `submit_instruction()`

**Missing**: Generic `get()` and `post()` methods that would allow:
```python
api_client.get("/api/v1/some/endpoint")
api_client.post("/api/v1/some/endpoint", json=data)
```

**Current Workaround**: Each UI service uses direct `requests.get()` and `requests.post()` calls with manual error handling.

**Impact**: 
- Inconsistent patterns across UI services
- Duplicated error handling code
- No centralized request configuration (timeouts, headers, etc.)

### 2. Inconsistent Error Handling

**Problem**: Each UI service implements its own error handling pattern:
- Some check `response.status_code == 200`
- Some use `response.raise_for_status()`
- Different timeout values (30s, etc.)
- Different error response formats

**Impact**: Maintenance burden and inconsistent user experience.

### 3. No Centralized Configuration

**Problem**: Base URL, timeouts, and other API configuration scattered across services.

**Impact**: Hard to change API settings globally.

## Proposed Future Improvements

### Phase 1: Standardize API Client
- Add generic `get()`, `post()`, `put()`, `delete()` methods
- Centralize error handling and logging
- Consistent timeout and retry logic
- Standardized error response format

### Phase 2: Refactor UI Services
- Update all UI services to use standardized API client
- Remove duplicated error handling code
- Consistent response format expectations

### Phase 3: Configuration Management
- Centralized API configuration
- Environment-specific settings
- Connection pooling and caching

## Implementation Notes

**When implementing**: 
- Maintain backward compatibility during transition
- Update one UI service at a time
- Keep existing direct requests as fallback during migration
- Don't mix patterns - complete migration before release

**Testing Strategy**:
- Test all UI functionality after API client changes
- Verify error handling works correctly
- Check timeout behavior
- Ensure no JSON parsing errors

---

**Note**: This is a collection of improvement ideas. Implementation should be planned and executed as a separate refactoring effort when time permits.