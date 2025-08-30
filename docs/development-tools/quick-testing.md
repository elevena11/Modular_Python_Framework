# Quick Testing Guide

This guide covers simple, fast ways to test module compliance and functionality during development, perfect for rapid iteration and validation.

## [PURPOSE] Purpose

**Quick testing enables:**
- **Rapid validation** - Get answers in seconds, not minutes
- **Focused feedback** - Test specific aspects without full compliance runs
- **Development flow** - Stay in coding mindset with minimal interruption
- **Confidence building** - Know your changes work before moving forward

## [LAUNCH] Quick Test Commands

### Single Module Testing
```bash
# Quick compliance check
python tools/test_module.py veritas_knowledge_graph

# Watch mode (real-time feedback)
python tools/test_module.py --watch veritas_knowledge_graph

# Detailed pytest output  
python tools/pytest_compliance.py --module veritas_knowledge_graph

# Traditional compliance check
python tools/compliance/compliance.py validate --module veritas_knowledge_graph
```

### Specific Test Categories
```bash
# Core standards only
python -m pytest tools/pytest_compliance.py::TestCoreStandards -v

# API standards (when applicable)
python -m pytest tools/pytest_compliance.py::TestAPIStandards -v

# Database standards (when applicable)  
python -m pytest tools/pytest_compliance.py::TestDatabaseStandards -v

# UI standards (when applicable)
python -m pytest tools/pytest_compliance.py::TestUIStandards -v
```

### All Modules Testing
```bash
# All modules compliance
python tools/compliance/compliance.py validate-all

# All modules with pytest
python -m pytest tools/pytest_compliance.py -v

# Quick status check
python tools/check_module_status.py
```

## [PERFORMANCE] Fast Validation Patterns

### Pattern 1: Code → Test → Fix Loop
```bash
# 1. Make code changes in your editor
# 2. Quick test
python tools/test_module.py my_module

# 3. If issues found, fix and repeat
# 4. When clean, continue development
```

### Pattern 2: Watch Mode Development
```bash
# 1. Start watch mode
python tools/test_module.py --watch my_module

# 2. Edit code in your editor
# 3. Save files - get automatic feedback
# 4. Address issues as they appear
# 5. Continue development with confidence
```

### Pattern 3: Targeted Testing
```bash
# Test specific functionality
python -m pytest tools/pytest_compliance.py::test_two_phase_initialization_phase1 -v

# Test specific module
python -m pytest "tools/pytest_compliance.py::test_module_compliance[standard.my_module]" -v

# Test with specific output
python tools/pytest_compliance.py --module my_module
```

## [ANALYSIS] Understanding Test Output

### Successful Test Run
```bash
$ python tools/test_module.py veritas_knowledge_graph

🧪 Testing module: standard.veritas_knowledge_graph
[PASS] test_module_structure
[PASS] test_two_phase_initialization_phase1  
[PASS] test_two_phase_initialization_phase2
[PASS] test_service_registration
[PASS] test_module_dependency_management
⏭️  test_api_schema_validation: Skipped - Module does not implement API functionality

📊 Results: 5/5 tests passed
```

**Interpretation:**
- [PASS] **Green checkmarks** - Tests passed
- ⏭️ **Skip indicators** - Tests not applicable (good)
- **5/5 passed** - Perfect score
- **Ready for next step** - Can continue development

### Failed Test Run
```bash
$ python tools/test_module.py broken_module

🧪 Testing module: standard.broken_module
[FAIL] test_module_structure: manifest.json missing required field: entry_point
[PASS] test_two_phase_initialization_phase1
[FAIL] test_two_phase_initialization_phase2: Missing: setup hook registration
[PASS] test_service_registration
[FAIL] test_api_schema_validation: api_schemas.py required for API modules

📊 Results: 2/5 tests passed
```

**Interpretation:**
- [FAIL] **Red X marks** - Specific failures with reasons
- **Clear error messages** - Know exactly what to fix
- **2/5 passed** - 40% compliance, needs work
- **Action required** - Fix failing tests before proceeding

### Watch Mode Output
```bash
🔄 File changed: api.py - Re-validating...

⏰ [14:32:17] Checking compliance for standard.my_module

📊 Compliance Status:
----------------------------------------
[PASS] Module Structure: All required files present
[FAIL] Two-Phase Init Phase 1: Missing initialize(app_context) function
[PASS] Service Registration: Service and shutdown handlers registered
----------------------------------------
📈 Score: 2/3 (67%)
👍 Good progress, few issues remaining
```

**Interpretation:**
- **Real-time updates** - See changes immediately
- **Progress tracking** - Score improves over time
- **Specific guidance** - Know exactly what's broken
- **Motivation** - See progress toward 100%

## 🧪 Test Types and When to Use

### Quick Compliance Check
**When:** After making changes, want fast feedback
**Command:** `python tools/test_module.py my_module`
**Speed:** 1-2 seconds
**Output:** Pass/fail with specific error messages

### Watch Mode
**When:** Active development, want continuous feedback
**Command:** `python tools/test_module.py --watch my_module`
**Speed:** Real-time (automatic)
**Output:** Live compliance status on every file save

### Detailed Pytest
**When:** Need verbose output, debugging specific issues
**Command:** `python tools/pytest_compliance.py --module my_module`
**Speed:** 2-3 seconds
**Output:** Detailed test information with stack traces

### Traditional Compliance
**When:** Final validation, need comprehensive report
**Command:** `python tools/compliance/compliance.py validate --module my_module`
**Speed:** 3-5 seconds
**Output:** Full compliance report with line numbers

### Module Status Check
**When:** Want overview of all modules
**Command:** `python tools/check_module_status.py`
**Speed:** 5-10 seconds
**Output:** Dependency analysis and module overview

## [PURPOSE] Testing Strategies

### Test-Driven Development (TDD)
1. **Start with failing tests** - Understand requirements
2. **Make tests pass** - Implement minimum functionality
3. **Refactor** - Improve code while tests pass
4. **Repeat** - Add next feature

```bash
# 1. See what compliance requires
python tools/test_module.py new_module

# 2. Fix one test at a time
# 3. Validate each fix
python tools/test_module.py new_module

# 4. Move to next failing test
```

### Incremental Validation
1. **Make small changes** - One feature at a time
2. **Test immediately** - Validate before moving on
3. **Build confidence** - Each step works before next
4. **Avoid big failures** - Catch issues early

```bash
# After each small change:
python tools/test_module.py my_module
# [PASS] Passes? Continue
# [FAIL] Fails? Fix before proceeding
```

### Continuous Integration Workflow
1. **Local testing** - Validate before commits
2. **Pre-commit checks** - Ensure compliance  
3. **Shared standards** - Team uses same validation
4. **Automated feedback** - CI runs same tests

```bash
# Before git commit:
python tools/test_module.py my_module
# Only commit when tests pass
```

## [TOOLS] Customizing Quick Tests

### Creating Custom Test Runners
```bash
# Create project-specific test script
#!/bin/bash
# test-my-project.sh

echo "🧪 Testing Project Modules"
echo "========================="

for module in user_analytics content_manager data_processor; do
    echo "Testing $module..."
    python tools/test_module.py $module
    if [ $? -ne 0 ]; then
        echo "[FAIL] $module failed"
        exit 1
    fi
done

echo "[PASS] All modules passed!"
```

### Integrating with IDEs

#### VS Code Tasks
Create `.vscode/tasks.json`:
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Test Current Module",
            "type": "shell",
            "command": "python",
            "args": ["tools/test_module.py", "${input:moduleName}"],
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "Watch Current Module", 
            "type": "shell",
            "command": "python",
            "args": ["tools/test_module.py", "--watch", "${input:moduleName}"],
            "group": "test",
            "isBackground": true
        }
    ],
    "inputs": [
        {
            "id": "moduleName",
            "description": "Module name to test",
            "default": "my_module",
            "type": "promptString"
        }
    ]
}
```

#### VS Code Keybindings
Create `.vscode/keybindings.json`:
```json
[
    {
        "key": "ctrl+shift+t",
        "command": "workbench.action.tasks.runTask",
        "args": "Test Current Module"
    }
]
```

### Git Integration

#### Pre-commit Hook
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Pre-commit compliance check

echo "🧪 Running pre-commit compliance checks..."

# Get list of changed modules
changed_files=$(git diff --cached --name-only)
modules_to_test=()

for file in $changed_files; do
    if [[ $file == modules/*/[^/]* ]]; then
        module_path=$(dirname "$file")
        module_name=$(basename "$module_path")
        module_type=$(basename "$(dirname "$module_path")")
        
        if [[ ! " ${modules_to_test[@]} " =~ " ${module_type}.${module_name} " ]]; then
            modules_to_test+=("${module_type}.${module_name}")
        fi
    fi
done

# Test each modified module
for module in "${modules_to_test[@]}"; do
    echo "Testing $module..."
    python tools/test_module.py "$module"
    if [ $? -ne 0 ]; then
        echo "[FAIL] Commit blocked: $module failed compliance tests"
        echo "Fix issues and try again"
        exit 1
    fi
done

echo "[PASS] All compliance tests passed"
exit 0
```

## [ANALYSIS] Performance and Optimization

### Test Speed Comparison
| Test Type | Speed | Use Case |
|-----------|-------|----------|
| Quick test | 1-2s | Development iteration |
| Watch mode | Real-time | Active coding |
| Pytest detailed | 2-3s | Debugging issues |
| Full compliance | 3-5s | Final validation |
| All modules | 10-30s | CI/CD pipelines |

### Optimization Tips
1. **Use watch mode** for active development
2. **Quick tests** for iteration validation  
3. **Pytest** only when debugging needed
4. **Full compliance** for final checks
5. **All modules** for release validation

### Scaling to Large Projects
- **Module-specific testing** - Don't test everything every time
- **Parallel execution** - Use `pytest -n auto` for speed
- **Caching** - Tools cache results when possible
- **Smart triggering** - Only test changed modules

## [LEARNING] Best Practices

### Development Workflow
1. **Start with scaffolding** - Begin with passing tests
2. **Use watch mode** - Get continuous feedback
3. **Fix issues immediately** - Don't accumulate technical debt
4. **Test before commits** - Ensure shared standards

### Team Collaboration
1. **Shared test commands** - Everyone uses same validation
2. **Document test procedures** - Clear team guidelines
3. **Pre-commit hooks** - Prevent broken code
4. **CI integration** - Automated validation

### Continuous Improvement
1. **Monitor test performance** - Keep tests fast
2. **Update test coverage** - Add new compliance requirements
3. **Gather feedback** - Improve developer experience
4. **Automate repetitive tasks** - Reduce manual work

## [ANALYSIS] Troubleshooting

### Common Issues

#### Tests Not Finding Module
```bash
[FAIL] Module 'my_module' not found
```
**Solutions:**
- Check module name spelling
- Ensure manifest.json exists
- Verify module is in correct directory
- Use `python tools/check_module_status.py` to see available modules

#### Permission Errors
```bash
💥 Error running tests: PermissionError
```
**Solutions:**
- Check file permissions
- Ensure write access to test directories
- Run with appropriate user permissions

#### Slow Test Execution
```bash
Tests taking >10 seconds
```
**Solutions:**
- Use quick test instead of detailed pytest
- Check system resources
- Consider module complexity

### Debug Mode
Enable debug output for troubleshooting:
```bash
# Set debug environment variable
DEBUG=1 python tools/test_module.py my_module

# Or modify tool temporarily for more output
```

---

**Next Steps:**
- Try different quick test commands
- Set up watch mode for a module you're working on
- Configure IDE integration for your development environment
- Move on to [Testing Strategies](./testing-strategies.md) for comprehensive testing approaches