# Streamlined CLI Command Implementation Workflow

**Date**: 2025-07-15  
**Purpose**: Simplified workflow for well-defined CLI command implementations

## Why Streamlined Approach?

CLI commands are **implementation-focused tasks** with:
- ✅ Clear requirements (specific method signatures needed)
- ✅ Known expected outputs (JSON format defined)
- ✅ Obvious technical approach (database queries, vector searches)
- ✅ Minimal design decisions (follow existing patterns)

Unlike complex features that need exploration, these are **direct implementations** of missing methods.

## Streamlined 5-Phase Workflow

### **Phase 1: SEED → PLAN (Combined)**
**Duration**: 10-15 minutes  
**Purpose**: Capture requirements and define scope directly

**Template**:
```markdown
## CLI Command Implementation: [Command Name]

### Requirements
- **Missing Method**: `class.method_name()`
- **Expected Output**: [JSON structure]
- **Current Error**: [Specific error message]

### Implementation Plan
- **Method Location**: `src/[file].py`
- **Method Signature**: `async def method_name(self, params) -> dict`
- **Database/Vector Queries**: [Specific queries needed]
- **JSON Response**: [Response structure]

### Dependencies
- [List any prerequisites]

### Success Criteria
- [How to verify it works]
```

### **Phase 2: TECHNICAL MAP**
**Duration**: 15-30 minutes  
**Purpose**: Define exact implementation details

**Focus Areas**:
- Specific database queries needed
- Vector search parameters
- Error handling requirements
- Response formatting
- Integration points

### **Phase 3: TODO → IMPLEMENT (Combined)**
**Duration**: 1-3 hours  
**Purpose**: Create tasks and implement immediately

**TodoWrite Integration**:
```python
TodoWrite([
    {"content": "Add method signature to class", "status": "pending", "priority": "high"},
    {"content": "Implement core logic", "status": "pending", "priority": "high"},
    {"content": "Add error handling", "status": "pending", "priority": "medium"},
    {"content": "Test with CLI command", "status": "pending", "priority": "high"},
    {"content": "Verify JSON output format", "status": "pending", "priority": "medium"}
])
```

### **Phase 4: TEST**
**Duration**: 30-45 minutes  
**Purpose**: Verify functionality

**Testing Approach**:
- Test CLI command directly: `python analyze.py [command]`
- Verify JSON output matches expected format
- Test error conditions
- Verify performance (<30 seconds)

### **Phase 5: DOCUMENT**
**Duration**: 15-20 minutes  
**Purpose**: Update documentation

**Documentation Updates**:
- Update CLI_COMMAND_TEST_RESULTS.md (mark as working)
- Add command to working commands list
- Update any relevant architecture docs

## Skip These Phases for CLI Commands

### ❌ BRAINSTORM (Skip)
**Why**: Implementation approach is obvious
- Database query for `themes` → clear SQL needed
- Vector search for `similar` → ChromaDB query
- Concept search for `concept` → embedding similarity
- Fix metadata for `analyze` → clean None values

### ❌ Extended PLAN (Skip)
**Why**: Scope is predefined
- Input/output formats are specified
- Integration points are known
- No architectural decisions needed

## Implementation Pattern

### Standard CLI Command Method Template
```python
async def [method_name](self, [params]) -> dict:
    """
    [Brief description of what command does]
    
    Args:
        [param descriptions]
    
    Returns:
        dict: Standardized CLI response with success, processing_time, and data
    """
    start_time = time.time()
    
    try:
        # Core implementation logic
        result = await self._core_logic([params])
        
        # Format response
        response = {
            "success": True,
            "processing_time": time.time() - start_time,
            "[data_key]": result
        }
        
        return response
        
    except Exception as e:
        logger.error(f"[Command] failed: {e}")
        return {
            "success": False,
            "processing_time": time.time() - start_time,
            "error": str(e)
        }
```

### Standard Error Handling Pattern
```python
# All CLI commands should handle common errors
try:
    # Implementation
    pass
except DatabaseError as e:
    return {"success": False, "error": f"Database error: {e}"}
except VectorStoreError as e:
    return {"success": False, "error": f"Vector store error: {e}"}
except Exception as e:
    return {"success": False, "error": f"Unexpected error: {e}"}
```

## Priority Implementation Schedule

### Week 1: Critical Foundation
- **Day 1**: `analyze` - Fix ChromaDB metadata corruption
- **Day 2**: `similar` - Vector similarity search
- **Day 3**: `concept` - Semantic concept search
- **Day 4**: `themes` - Document theme enumeration

### Week 2: VEF Framework Completion
- **Day 5**: `cross-ref-analyze` - Cross-reference analysis
- **Day 6**: `incremental` - Incremental analysis
- **Day 7**: `cluster-info` - Detailed cluster information

### Week 3: Enhancement Features
- **Day 8**: `cross-ref-stats` - Cross-reference statistics
- **Day 9**: `query` - SQL database query
- **Day 10**: `cross-ref-query` + `cluster-assign` - Final features

## Success Metrics

### Per Command Success
- ✅ CLI command executes without error
- ✅ JSON output matches expected format
- ✅ Processing time < 30 seconds
- ✅ Error handling works correctly

### Overall Success
- ✅ 17/17 commands working (100% functionality)
- ✅ Consistent JSON response format
- ✅ Complete test coverage
- ✅ Updated documentation

## Benefits of Streamlined Approach

### ✅ **Faster Implementation**
- No time wasted on obvious design decisions
- Direct path from requirements to implementation
- Focus on coding, not planning

### ✅ **Consistent Quality**
- Standard patterns for all commands
- Uniform error handling
- Consistent JSON response format

### ✅ **Clear Progress Tracking**
- Simple pass/fail testing
- Obvious completion criteria
- Direct user value delivery

### ✅ **Reduced Overhead**
- Minimal documentation burden
- No unnecessary brainstorming sessions
- Focus on shipping working features

This streamlined approach recognizes that CLI commands are **implementation tasks**, not **design challenges**, and optimizes the workflow accordingly.