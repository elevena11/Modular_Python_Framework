# Development Watch Mode

The development watch mode tool (`tools/dev_watch.py`) provides real-time compliance feedback as you code, eliminating the need for manual validation runs during development.

## [PURPOSE]

**Problem with manual testing:**
- Must remember to run compliance checks
- Feedback comes only after significant code changes
- Difficult to track which changes broke compliance
- Slows down iterative development

**Solution:** Automatic file watching with:
- Instant feedback on file saves
- Clear compliance status display
- Real-time progress tracking
- Seamless development workflow

## [QUICK START]

### Basic Watch Mode
```bash
python tools/dev_watch.py --module veritas_knowledge_graph
```

### Watch Mode with Tests
```bash
python tools/dev_watch.py --module veritas_knowledge_graph --test
```

### Example Output
```
[TARGET] Target module: standard.veritas_knowledge_graph
[PATH] Path: /path/to/modules/standard/veritas_knowledge_graph
[TEST] Run tests: No

[WATCH] Watching standard.veritas_knowledge_graph at /path/to/modules/standard/veritas_knowledge_graph
[FILES] Files: api.py, services.py, manifest.json, *.py
============================================================

[TIME] [14:23:15] Checking compliance for standard.veritas_knowledge_graph

[STATUS] Compliance Status:
----------------------------------------
[PASS] Module Structure: All required files present
[PASS] Two-Phase Init Phase 1: Valid Phase 1 implementation
[PASS] Two-Phase Init Phase 2: Valid Phase 2 implementation
[PASS] Service Registration: Service and shutdown handlers registered
----------------------------------------
[SCORE] Score: 4/4 (100%)
[SUCCESS] All compliance checks passed!

[WATCH] Watching for file changes (Ctrl+C to stop)...
```

## [REAL-TIME FEEDBACK]

### File Change Detection
The tool watches for changes to:
- **Python files** (*.py)
- **Manifest file** (manifest.json)
- **Configuration files** (module_settings.py)

### Debounced Updates
- **2-second debounce** prevents spam during rapid file saves
- **Smart triggering** only on relevant file changes
- **Efficient checking** minimal performance impact

### Live Compliance Status

#### Successful Compliance
```
[CHANGE] File changed: api.py - Re-validating...

[TIME] [14:25:33] Checking compliance for standard.my_module

[STATUS] Compliance Status:
----------------------------------------
[PASS] Module Structure: All required files present
[PASS] Two-Phase Init Phase 1: Valid Phase 1 implementation
[PASS] Two-Phase Init Phase 2: Valid Phase 2 implementation
[PASS] Service Registration: Service and shutdown handlers registered
[PASS] API Schema Validation: Pydantic schemas with response models
----------------------------------------
[SCORE] Score: 5/5 (100%)
[SUCCESS] All compliance checks passed!
```

#### Compliance Issues
```
[CHANGE] File changed: api.py - Re-validating...

[TIME] [14:27:45] Checking compliance for standard.my_module

[STATUS] Compliance Status:
----------------------------------------
[PASS] Module Structure: All required files present
[FAIL] Two-Phase Init Phase 1: Missing initialize(app_context) function
[PASS] Two-Phase Init Phase 2: Valid Phase 2 implementation
[FAIL] Service Registration: Missing: service registration
[WARN] API Schema Validation: Schemas exist but no response_model usage
----------------------------------------
[SCORE] Score: 2/5 (40%)
[NEEDS_WORK] Needs work - focus on failed checks
```

## [COMPLIANCE CHECKS]

### Core Standards Monitoring

#### Module Structure
Validates:
- **Required files** - manifest.json, api.py, services.py
- **File accessibility** - Files can be read
- **Basic format** - JSON parsing for manifest

#### Two-Phase Initialization Phase 1
Checks:
- **Function existence** - `async def initialize(app_context):`
- **No database operations** - Forbidden patterns in Phase 1
- **Proper async syntax** - Correct function signature

#### Two-Phase Initialization Phase 2
Validates:
- **Setup hook registration** - `register_module_setup_hook()` call
- **Phase 2 function** - `async def setup_module(app_context):`
- **Proper integration** - Correct setup patterns

#### Service Registration
Monitors:
- **Service registration** - `register_service()` call
- **Shutdown handler** - `register_shutdown_handler()` call
- **Proper lifecycle** - Complete service management

### Conditional Standards

#### API Standards (when applicable)
- **Schema files** - api_schemas.py existence
- **Pydantic imports** - BaseModel imports
- **Response models** - response_model usage in endpoints

#### Database Standards (when applicable)
- **Database files** - database.py and db_models.py
- **Async operations** - Async function usage
- **SQLAlchemy patterns** - Proper ORM usage

## [TEST INTEGRATION]

### Automatic Test Execution
When using `--test` flag:
```bash
python tools/dev_watch.py --module my_module --test
```

The tool runs pytest compliance tests on every change:
```
[CHANGE] File changed: api.py - Re-validating...

[STATUS] Compliance Status:
[... compliance status ...]

[TEST] Running tests for my_module...
[PASS] All tests passed!
```

### Test Output Examples

#### Successful Tests
```
[TEST] Running tests for my_module...
================= test session starts =================
collected 8 items

tools/pytest_compliance.py::test_module_structure PASSED
tools/pytest_compliance.py::test_two_phase_initialization_phase1 PASSED  
tools/pytest_compliance.py::test_two_phase_initialization_phase2 PASSED
tools/pytest_compliance.py::test_service_registration PASSED

================= 4 passed in 0.12s =================
[PASS] All tests passed!
```

#### Failed Tests
```
[TEST] Running tests for my_module...
================= FAILURES =================
______ test_two_phase_initialization_phase1 ______

    def test_two_phase_initialization_phase1(self, compliance_checker):
        assert checker.check_pattern_in_file("api.py", r"async\s+def\s+initialize")
>       AssertionError: Missing initialize(app_context) function

[FAIL] Some tests failed:
[detailed test output]
```

## [DEVELOPMENT WORKFLOW]

### Typical Development Session

1. **Start watch mode**
   ```bash
   python tools/dev_watch.py --module my_new_module --test
   ```

2. **Initial status check**
   - See current compliance score
   - Identify areas needing work

3. **Iterative development**
   - Edit files in your IDE
   - Save changes
   - Watch real-time feedback
   - Fix issues as they appear

4. **Continuous improvement**
   - Monitor score progression
   - Address failing checks one by one
   - Validate with automatic tests

### LLM-Assisted Development

Perfect for working with Large Language Models:

1. **Start with scaffolded module**
   ```bash
   python tools/scaffold_module.py
   # [PASS] Creates compliant base structure
   ```

2. **Begin watch mode**
   ```bash
   python tools/dev_watch.py --module new_module --test
   # [PASS] Real-time feedback enabled
   ```

3. **Iterative LLM prompts**
   - "The compliance check shows 'Missing initialize function', please add it"
   - "Add the missing service registration in Phase 1"
   - "Fix the API schema validation by adding response_model"

4. **Immediate validation**
   - Each LLM response gets instant feedback
   - No need to remember to run tests
   - Clear success/failure indicators

## [ADVANCED CONFIGURATION]

### File Watching Options

#### Watchdog Integration (Recommended)
```bash
# Install for better performance
pip install watchdog

# Automatic detection and usage
python tools/dev_watch.py --module my_module
```

#### Fallback Polling Mode
If watchdog is not available:
```
[WARN] Watchdog not available, using simple polling
Install with: pip install watchdog

[POLL] Polling for file changes (Ctrl+C to stop)...
```

### Customizing Watch Behavior

#### Debounce Configuration
The tool uses a 2-second debounce by default. You can modify this in the code:
```python
class ModuleWatcher(FileSystemEventHandler):
    def __init__(self, module_info: Dict, run_tests: bool = False):
        self.debounce_seconds = 2  # Adjust this value
```

#### File Type Filtering
Currently watches:
- Python files (*.py)
- Manifest files (manifest.json)

To add more file types, modify the `on_modified` method:
```python
def on_modified(self, event):
    file_path = Path(event.src_path)
    # Add more extensions
    if not (file_path.suffix in ['.py', '.json', '.md'] or file_path.name == 'manifest.json'):
        return
```

## [STATUS INDICATORS]

### Compliance Score Interpretation

#### [EXCELLENT] (90-100%)
```
[SCORE] Score: 5/5 (100%)
[SUCCESS] All compliance checks passed!
```
- Module is framework compliant
- Ready for integration testing
- Can focus on business logic

#### [GOOD] (70-89%)
```
[SCORE] Score: 4/5 (80%)
[GOOD] Good progress, few issues remaining
```
- Minor compliance issues
- Close to completion
- Address remaining failures

#### [NEEDS_WORK] (Below 70%)
```
[SCORE] Score: 2/5 (40%)
[NEEDS_WORK] Needs work - focus on failed checks
```
- Significant compliance issues
- Focus on core standards first
- Consider reviewing framework docs

### Status Symbols

- **[PASS]** - Check passed
- **[FAIL]** - Check failed with clear reason
- **[WARN]** - Warning (partial compliance)
- **[SKIP]** - Skipped (not applicable)

## [PERFORMANCE CONSIDERATIONS]

### Efficient Watching
- **Minimal CPU usage** - Only processes relevant file changes
- **Fast validation** - Core checks complete in milliseconds
- **Memory efficient** - Small memory footprint

### Optimization Tips
1. **Use watchdog** - Much faster than polling
2. **Focus on specific modules** - Don't watch entire codebase
3. **Disable tests** if not needed - Use basic watch mode for faster feedback

### Scaling to Large Projects
- Works efficiently with modules containing 50+ files
- Handles concurrent development on multiple modules
- Suitable for team development environments

## [TROUBLESHOOTING]

### Common Issues

#### Module Not Found
```bash
[ERROR] Module 'my_module' not found

Available modules:
  - veritas_knowledge_graph (standard.veritas_knowledge_graph)
  - example_module (extensions.example_module)
```
**Solution:** Check module name and ensure it exists in modules directory.

#### Permission Errors
```
[ERROR] Error running tests: PermissionError
```
**Solution:** Ensure write permissions for test output and module directories.

#### File Watching Not Working
```
[WARN] Watchdog not available, using simple polling
```
**Solution:** Install watchdog for better performance:
```bash
pip install watchdog
```

### Debug Mode
For troubleshooting, modify the tool to add debug output:
```python
# Add to ModuleWatcher.__init__
import logging
logging.basicConfig(level=logging.DEBUG)
```

## [TIPS AND BEST PRACTICES]

### Effective Usage
1. **Start early** - Begin watch mode as soon as you start coding
2. **Keep it running** - Leave watch mode active during entire session
3. **Address issues immediately** - Fix compliance problems as they appear
4. **Use with IDE** - Split-screen with editor and terminal

### Team Development
- **Shared standards** - Everyone sees the same compliance requirements
- **Consistent feedback** - Same validation rules for all developers
- **Reduced code review time** - Compliance pre-validated

### Integration with Other Tools
- **Git hooks** - Run compliance check before commits
- **IDE plugins** - Integrate with VS Code tasks
- **CI/CD** - Use same compliance rules in pipelines

---

**Next Steps:**
- Start watch mode on an existing module
- Try making changes and observe real-time feedback
- Move on to [LLM Development Workflow](./llm-development-workflow.md) for AI-assisted development patterns