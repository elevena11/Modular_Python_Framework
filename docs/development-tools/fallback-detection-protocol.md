# Fallback Detection Protocol

This document provides a systematic protocol for detecting and eliminating fallbacks, simulations, and backward compatibility patterns in the VeritasForma Framework codebase.

## Background

Per CLAUDE.md, the framework **NEVER** implements:
- Backward compatibility mechanisms
- Fallback patterns or graceful degradation  
- Simulations or demo modes
- "Try X, if failed try Y" patterns

These patterns hide problems and prevent early detection of issues. Code must fail immediately and clearly when dependencies are unavailable.

## Detection Protocol

### 1. Keyword Search Patterns

Search the codebase for these suspicious patterns:

**Fallback Language:**
```
fallback|fall.back|fall-back
graceful.*degrad|degrad.*graceful
try.*else|else.*try
backup.*option|option.*backup
alternative.*method|method.*alternative
secondary.*approach|approach.*secondary
```

**Simulation Language:**
```
simulation|simulate|simulated
demo.*mode|mode.*demo
mock.*response|response.*mock
fake.*data|data.*fake
placeholder.*response|response.*placeholder
test.*mode|mode.*test
```

**Backward Compatibility:**
```
backward.*compat|compat.*backward
legacy.*support|support.*legacy
deprecated.*but.*still
old.*format|format.*old
previous.*version|version.*previous
maintain.*compat|compat.*maintain
```

### 2. Code Structure Analysis

#### A. Exception Handling Anti-Patterns

**VIOLATION:**
```python
try:
    use_preferred_method()
except:
    use_fallback_method()  # WRONG - fallback
```

**CORRECT:**
```python
if not dependency_available():
    raise Exception("Required dependency not available")
use_preferred_method()
```

#### B. Conditional Fallback Anti-Patterns

**VIOLATION:**
```python
if modern_api_available:
    return modern_api.process()
else:
    return legacy_api.process()  # WRONG - backward compatibility
```

**CORRECT:**
```python
if not modern_api_available:
    raise Exception("Modern API required but not available")
return modern_api.process()
```

#### C. Default Value Anti-Patterns

**VIOLATION:**
```python
model = get_gpu_model() or get_cpu_model()  # WRONG - silent degradation
```

**CORRECT:**
```python
model = get_gpu_model()
if not model:
    raise Exception("GPU model required but not available")
```

### 3. File-by-File Review Checklist

For each Python file, systematically check:

#### A. Import Sections
- [ ] No conditional imports with fallbacks
- [ ] No `try: import X except: import Y` patterns
- [ ] No `importlib` dynamic loading with alternatives

#### B. Class Initialization
- [ ] No fallback initialization paths
- [ ] No "degraded mode" constructors
- [ ] No default/placeholder implementations

#### C. Method Implementations
- [ ] No `try/except` blocks that silently switch methods
- [ ] No `if/else` chains providing alternative implementations
- [ ] No "compatibility layers" or adapters

#### D. Configuration Loading
- [ ] No default configurations for missing files
- [ ] No environment variable fallbacks
- [ ] No "safe mode" configurations

#### E. Service Integration
- [ ] No service unavailability fallbacks
- [ ] No mock/stub services for missing dependencies
- [ ] No "offline mode" implementations

### 4. Specific Violation Patterns

#### A. Model Loading Violations
```python
# WRONG - fallback to CPU
try:
    model = load_gpu_model()
except:
    model = load_cpu_model()

# CORRECT - fail fast
model = load_gpu_model()
if not model:
    raise Exception("GPU model loading failed")
```

#### B. Database Connection Violations
```python
# WRONG - fallback database
try:
    db = connect_primary_db()
except:
    db = connect_backup_db()

# CORRECT - fail fast  
db = connect_primary_db()
if not db:
    raise Exception("Primary database connection required")
```

#### C. API Integration Violations
```python
# WRONG - API fallback
def call_api():
    try:
        return external_api.call()
    except:
        return mock_response()  # Simulation

# CORRECT - fail fast
def call_api():
    if not external_api.available():
        raise Exception("External API required but not available")
    return external_api.call()
```

### 5. Detection Commands

Run these commands in the project root:

```bash
# Search for fallback patterns
rg -i "fallback|fall.back|graceful.*degrad|try.*else" --type py

# Search for simulation patterns  
rg -i "simulat|demo.*mode|mock.*response|fake.*data" --type py

# Search for compatibility patterns
rg -i "backward.*compat|legacy.*support|deprecated.*but" --type py

# Search for try/except fallbacks
rg -A 5 -B 2 "except.*:" --type py | grep -E "(else|alternative|fallback|backup)"

# Search for conditional alternatives
rg -A 3 "if.*available.*else" --type py
```

### 6. Review Process

#### A. Systematic File Review
1. Start with service files (`services.py`)
2. Review initialization files (`api.py`, `__init__.py`)
3. Check configuration files (`module_settings.py`)
4. Examine utility files (`utils.py`)
5. Review component files in order of dependency

#### B. Integration Points
Focus extra attention on:
- Service registration and discovery
- Model loading and management  
- Database connections
- External API integrations
- Configuration loading
- Error handling boundaries

#### C. Documentation Review
Check documentation for:
- "Fallback mode" instructions
- "Compatibility" sections
- "Graceful degradation" features
- "Demo/test mode" usage

### 7. Remediation Guidelines

#### A. Replace Fallbacks with Requirements
```python
# OLD - fallback pattern
def initialize():
    try:
        service = get_service()
        return service
    except:
        logger.warning("Service unavailable, using mock")
        return MockService()

# NEW - fail fast pattern  
def initialize():
    service = get_service()
    if not service:
        raise Exception("Required service not available")
    return service
```

#### B. Replace Simulations with Real Implementation
```python
# OLD - simulation pattern
def process_data(data):
    if DEMO_MODE:
        return fake_processing_result()
    return real_processing(data)

# NEW - real implementation only
def process_data(data):
    return real_processing(data)
```

#### C. Replace Compatibility with Modern Requirements
```python
# OLD - backward compatibility
def load_config():
    try:
        return load_new_format()
    except:
        return convert_old_format()

# NEW - modern format required
def load_config():
    config = load_new_format()
    if not config:
        raise Exception("Modern config format required")
    return config
```

### 8. Integration with Development Workflow

#### A. Pre-Commit Check
Add this to pre-commit hooks:
```bash
#!/bin/bash
# Check for fallback patterns
if rg -q "fallback|graceful.*degrad|try.*else.*:" --type py; then
    echo "ERROR: Fallback patterns detected"
    exit 1
fi
```

#### B. Code Review Checklist
- [ ] No fallback mechanisms identified
- [ ] No simulation/demo code present
- [ ] No backward compatibility layers
- [ ] All dependencies fail fast when unavailable
- [ ] Error messages clearly indicate what's missing

#### C. Testing Strategy
- Test dependency unavailability scenarios
- Verify clear error messages on failures
- Ensure no silent degradation occurs
- Confirm all integrations fail fast

## Common Violation Examples

### ChromaDB Manager Example (Fixed)
**BEFORE (violation):**
```python
try:
    model_manager = get_service("model_manager")
    if model_manager:
        return use_model_manager()
except:
    logger.warning("Model manager unavailable, using direct loading")
    return direct_model_loading()  # Silent CPU fallback
```

**AFTER (correct):**
```python
model_manager = get_service("model_manager")
if not model_manager:
    raise Exception("Model manager service required for ChromaDB")
return use_model_manager()
```

### Memory Pipeline Example
**BEFORE (violation):**
```python
def extract_triplets(text):
    try:
        return t5_extraction(text)
    except:
        return simple_regex_extraction(text)  # Fallback
```

**AFTER (correct):**
```python
def extract_triplets(text):
    if not t5_model_available():
        raise Exception("T5 model required for triplet extraction")
    return t5_extraction(text)
```

## Reporting Phase (MANDATORY)

**CRITICAL**: Before making ANY changes, create a comprehensive report for review.

### Report Structure

Create a report with the following sections:

#### 1. Executive Summary
```
FALLBACK DETECTION REPORT
Date: [DATE]
Reviewer: [NAME/AI]
Scope: [MODULE/FILES REVIEWED]
Total Issues Found: [NUMBER]
Severity Breakdown: Critical: X, Major: X, Minor: X
```

#### 2. Detection Results
```
SEARCH RESULTS:
- Fallback patterns found: X occurrences
- Simulation patterns found: X occurrences  
- Compatibility patterns found: X occurrences
- Try/except fallbacks found: X occurrences
```

#### 3. Issue Inventory

For each potential issue found:

```
ISSUE #[N]: [Brief Description]
Location: [file_path:line_number]
Severity: [Critical/Major/Minor]
Pattern Type: [Fallback/Simulation/Compatibility]
Code Context:
  [Relevant code snippet with line numbers]
Analysis:
  - What the code currently does
  - Why this might be a violation
  - What the proper behavior should be
  - Potential impact of changing it
Recommended Action:
  - [Specific fix recommendation]
  - [Alternative approach if needed]
Risk Assessment:
  - Breaking change potential: [High/Medium/Low]
  - Dependencies affected: [List]
  - Testing requirements: [Specific tests needed]
```

#### 4. File-by-File Summary

```
FILES REVIEWED:
[file_path]
  - Issues found: X
  - Clean: [Yes/No]
  - Notes: [Any observations]
```

#### 5. Recommendations

```
IMMEDIATE ACTIONS REQUIRED:
1. [Priority 1 fixes]
2. [Priority 2 fixes]

FURTHER INVESTIGATION NEEDED:
1. [Areas needing deeper review]
2. [Unclear cases requiring discussion]

NO ACTION REQUIRED:
1. [False positives with justification]
2. [Acceptable patterns with rationale]
```

### Sample Report Template

```markdown
# Fallback Detection Report

**Date:** 2025-06-14
**Reviewer:** Claude Code
**Scope:** modules/standard/llm_memory_databases/
**Total Issues Found:** 3
**Severity:** Critical: 1, Major: 1, Minor: 1

## Detection Results
- Fallback patterns found: 2 occurrences
- Simulation patterns found: 0 occurrences
- Compatibility patterns found: 1 occurrence
- Try/except fallbacks found: 2 occurrences

## Issue Inventory

### ISSUE #1: ChromaDB Model Manager Fallback
**Location:** components/chroma_manager.py:178-210
**Severity:** Critical
**Pattern Type:** Fallback
**Code Context:**
```python
178: # Fallback to direct model loading if model manager not available
179: logger.warning("Model manager not available, falling back to direct model loading")
180: # Import here to avoid issues if not installed
181: from sentence_transformers import SentenceTransformer
```
**Analysis:**
- Code silently falls back to direct SentenceTransformer loading when model manager unavailable
- This bypasses proper GPU configuration and model sharing
- Violates CLAUDE.md "NO FALLBACKS" rule
- User discovered this was causing silent CPU usage instead of GPU

**Recommended Action:**
- Remove fallback entirely
- Require model manager service or fail with clear error
- Force proper dependency resolution

**Risk Assessment:**
- Breaking change potential: Low (proper dependencies should be available)
- Dependencies affected: Requires model manager service working
- Testing requirements: Test with model manager unavailable to verify clear failure

### ISSUE #2: Exception Handling with Continuation
**Location:** components/chroma_manager.py:594-604
**Severity:** Minor  
**Pattern Type:** Fallback
**Code Context:**
```python
594: except Exception as gpu_error:
595:     logger.warning(f"Error clearing GPU memory: {gpu_error}")
596: # ChromaDB client doesn't need explicit shutdown in current version
597: self.client = None
```
**Analysis:**
- GPU cleanup errors are caught and ignored, continuing with shutdown
- Could hide GPU memory management issues
- Might be acceptable for cleanup operations

**Recommended Action:**
- Review if GPU cleanup errors should be fatal
- Consider more specific exception handling
- Add clear documentation of expected behavior

**Risk Assessment:**  
- Breaking change potential: Medium (could make shutdown fail)
- Dependencies affected: GPU cleanup operations
- Testing requirements: Test GPU cleanup failure scenarios

## Recommendations

### IMMEDIATE ACTIONS REQUIRED:
1. Fix ChromaDB fallback (Issue #1) - remove model manager fallback entirely
2. Review GPU cleanup error handling (Issue #2) - determine proper behavior

### FURTHER INVESTIGATION NEEDED:
1. Verify model manager service is properly initialized before ChromaDB
2. Check if other modules have similar model loading patterns

### NO ACTION REQUIRED:
1. Standard try/catch for file operations (acceptable for I/O operations)
```

## Review Process

### Phase 1: Generate Report
1. Run detection protocol
2. Analyze each finding  
3. Create comprehensive report
4. **STOP - DO NOT MAKE CHANGES YET**

### Phase 2: Human Review
1. Present report to user
2. Discuss each issue and recommendation
3. Get approval for specific changes
4. Clarify any unclear cases
5. Agree on priority and approach

### Phase 3: Implementation (Only After Approval)
1. Make approved changes only
2. Test each change individually
3. Document what was changed and why
4. Verify no regressions introduced

## Enforcement

This protocol should be:
1. **Run manually** with report generation before any major commit
2. **Reviewed collaboratively** before implementing changes
3. **Integrated** into CI/CD pipeline as detection only (not auto-fix)
4. **Applied** during code reviews with mandatory reporting
5. **Documented** in module creation guides
6. **Verified** by compliance tools

**CRITICAL RULE:** Never implement fixes without generating and reviewing the report first. The report phase is mandatory and changes require explicit approval.

The goal is zero fallbacks, zero simulations, and zero backward compatibility - but achieved through careful analysis and deliberate action, not automatic changes.