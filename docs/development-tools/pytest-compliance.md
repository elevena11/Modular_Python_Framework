# Pytest Compliance Testing

The pytest compliance testing tool (`tools/pytest_compliance.py`) provides test-driven validation of framework compliance, replacing the JSON-based compliance system with familiar pytest assertions.

## [PURPOSE] Purpose

**Problem with traditional compliance.py:**
- Complex JSON configuration files
- Regex patterns hard to understand
- All-or-nothing validation
- Poor developer experience
- Difficult to debug failures

**Solution:** Pytest-based testing with:
- Clear, readable test cases
- Individual assertion failures
- Familiar testing ecosystem
- Easy debugging and development

## [LAUNCH] Quick Start

### Test a Specific Module
```bash
python tools/pytest_compliance.py --module veritas_knowledge_graph
```

### Run All Compliance Tests
```bash
python -m pytest tools/pytest_compliance.py -v
```

### Run Specific Test Categories
```bash
# Core standards only
python -m pytest tools/pytest_compliance.py::TestCoreStandards -v

# API standards only  
python -m pytest tools/pytest_compliance.py::TestAPIStandards -v

# Database standards only
python -m pytest tools/pytest_compliance.py::TestDatabaseStandards -v
```

## [ANALYSIS] Test Categories

### Core Implementation Standards
Tests fundamental framework compliance:

#### Module Structure
```python
def test_module_structure(self, compliance_checker):
    """Test basic module structure requirements."""
    # Required files
    assert checker.check_file_exists("manifest.json")
    assert checker.check_file_exists("api.py") 
    assert checker.check_file_exists("services.py")
    
    # Manifest validation
    manifest = checker.module['manifest']
    assert "entry_point" in manifest
    assert manifest["entry_point"] == "api.py"
```

#### Two-Phase Initialization Phase 1
```python
def test_two_phase_initialization_phase1(self, compliance_checker):
    """Test Phase 1 initialization compliance."""
    # Phase 1 function must exist
    assert checker.check_pattern_in_file(
        "api.py", 
        r"async\s+def\s+initialize\s*\(\s*app_context\s*\):"
    )
    
    # No database operations in Phase 1
    phase1_body = checker.extract_function_body("api.py", "initialize")
    forbidden_patterns = ["db_session", "create_tables", "execute\\("]
    
    for pattern in forbidden_patterns:
        assert not re.search(pattern, phase1_body)
```

#### Two-Phase Initialization Phase 2
```python
def test_two_phase_initialization_phase2(self, compliance_checker):
    """Test Phase 2 initialization compliance."""
    # Setup hook registration in Phase 1
    assert checker.check_pattern_in_file(
        "api.py",
        r"app_context\.register_module_setup_hook\s*\("
    )
    
    # Phase 2 function exists
    assert checker.check_pattern_in_file(
        "api.py",
        r"async\s+def\s+setup_module\s*\(\s*app_context\s*\):"
    )
```

#### Service Registration
```python
def test_service_registration(self, compliance_checker):
    """Test service registration pattern."""
    # Service registration
    assert checker.check_pattern_in_file(
        "api.py",
        r"app_context\.register_service\s*\("
    )
    
    # Shutdown handler
    assert checker.check_pattern_in_file(
        "api.py", 
        r"app_context\.register_shutdown_handler\s*\("
    )
```

### API Standards
Tests API implementation when applicable:

#### API Schema Validation
```python
def test_api_schema_validation(self, compliance_checker):
    """Test API schema validation implementation."""
    # Skip if no API functionality
    if not self._has_api_functionality(checker):
        pytest.skip("Module does not implement API functionality")
    
    # Required files
    assert checker.check_file_exists("api_schemas.py")
    
    # Pydantic imports
    assert checker.check_pattern_in_file(
        "api_schemas.py",
        r"from pydantic import.*BaseModel"
    )
    
    # Response model usage
    assert checker.check_pattern_in_file(
        "api.py",
        r"response_model\s*="
    )
```

### Database Standards
Tests database implementation when applicable:

#### Async Database Operations
```python
def test_async_database_operations(self, compliance_checker):
    """Test async database operations implementation."""
    if not checker.check_file_exists("database.py"):
        pytest.skip("No database.py file")
    
    # Async methods
    assert checker.check_pattern_in_file(
        "database.py",
        r"async\s+def\s+\w+"
    )
    
    # AsyncSession usage
    assert checker.check_pattern_in_file(
        "database.py",
        r"AsyncSession"
    )
```

### UI Standards
Tests UI implementation when applicable:

#### Streamlit Implementation
```python
def test_streamlit_implementation(self, compliance_checker):
    """Test Streamlit UI implementation."""
    streamlit_file = checker.path / "ui" / "ui_streamlit.py"
    if not streamlit_file.exists():
        pytest.skip("No Streamlit UI implementation")
    
    # Required render_ui function
    assert checker.check_pattern_in_file(
        "ui/ui_streamlit.py",
        r"def\s+render_ui\s*\(\s*app_context\s*\)"
    )
```

## [TOOLS] ComplianceChecker Class

The `ComplianceChecker` provides methods for testing module compliance:

### File Operations
```python
checker = ComplianceChecker(module_info)

# Check if file exists
exists = checker.check_file_exists("api.py")

# Get file content safely
content = checker.get_file_content("api.py")

# Check for pattern in file
has_pattern = checker.check_pattern_in_file("api.py", r"async def initialize")

# Check for anti-pattern (returns True if found - bad)
has_antipattern = checker.check_anti_pattern_in_file("api.py", r"sync def")
```

### Advanced Pattern Matching
```python
# Extract function body for detailed analysis
function_body = checker.extract_function_body("api.py", "initialize")

# Analyze specific code sections
if "database" in function_body:
    # Check database usage patterns
    pass
```

### Module Information
```python
# Access module metadata
module_id = checker.module_id  # e.g., "standard.my_module"
module_path = checker.path     # Path object to module directory
manifest = checker.module['manifest']  # Parsed manifest.json
```

## [ANALYSIS] Example Test Output

### Successful Test Run
```bash
$ python tools/pytest_compliance.py --module veritas_knowledge_graph

[TEST] Testing module: standard.veritas_knowledge_graph
[CORRECT] test_module_structure
[CORRECT] test_two_phase_initialization_phase1
[CORRECT] test_two_phase_initialization_phase2
[CORRECT] test_service_registration
[CORRECT] test_module_dependency_management
[SKIP]  test_api_schema_validation: Skipped - Module does not implement API functionality
[SKIP]  test_database_files_exist: Skipped - Module does not use database functionality

[ANALYSIS] Results: 5/5 tests passed
```

### Failed Test Run
```bash
$ python tools/pytest_compliance.py --module broken_module

[TEST] Testing module: standard.broken_module
[INCORRECT] test_module_structure: manifest.json missing required field: entry_point
[INCORRECT] test_two_phase_initialization_phase1: Missing initialize(app_context) function
[CORRECT] test_service_registration
[INCORRECT] test_api_schema_validation: api_schemas.py required for API modules

[ANALYSIS] Results: 1/4 tests passed
```

## [PROCESS] Integration with Pytest

### Run with Standard Pytest
```bash
# All modules, verbose output
python -m pytest tools/pytest_compliance.py -v

# Specific module using parametrization
python -m pytest tools/pytest_compliance.py::test_module_compliance[standard.my_module] -v

# Only failed tests
python -m pytest tools/pytest_compliance.py --lf

# Stop on first failure
python -m pytest tools/pytest_compliance.py -x

# Run in parallel (with pytest-xdist)
python -m pytest tools/pytest_compliance.py -n auto
```

### Pytest Fixtures
The tool uses pytest fixtures for clean test organization:

```python
@pytest.fixture(params=discover_modules(), ids=lambda m: m['id'])
def module_info(request):
    """Parametrized fixture providing all discovered modules."""
    return request.param

@pytest.fixture
def compliance_checker(module_info):
    """Create compliance checker for module."""
    return ComplianceChecker(module_info)
```

### Custom Test Extensions
You can extend the compliance tests:

```python
# Add to pytest_compliance.py
class TestCustomStandards:
    """Custom compliance tests for your organization."""
    
    def test_coding_standards(self, compliance_checker):
        """Test custom coding standards."""
        # Your custom assertions
        assert checker.check_pattern_in_file("services.py", r"class.*Service:")
        
    def test_documentation_standards(self, compliance_checker):
        """Test documentation requirements."""
        assert checker.check_file_exists("README.md")
        assert checker.check_pattern_in_file("README.md", r"## Usage")
```

## [SEARCH] Debugging Failed Tests

### Understanding Test Failures

#### Pattern Matching Issues
```python
# Debug regex patterns
content = checker.get_file_content("api.py")
pattern = r"async\s+def\s+initialize\s*\(\s*app_context\s*\):"
matches = re.findall(pattern, content)
print(f"Found matches: {matches}")
```

#### Function Body Analysis
```python
# Extract and examine function body
body = checker.extract_function_body("api.py", "initialize")
print(f"Phase 1 function body:\n{body}")

# Check for specific patterns
if "db_session" in body:
    print("[INCORRECT] Found database operation in Phase 1")
```

#### File Content Inspection
```python
# Check what's actually in the file
content = checker.get_file_content("manifest.json")
print(f"Manifest content:\n{content}")

# Parse and validate
import json
manifest = json.loads(content)
print(f"Parsed manifest: {manifest}")
```

## [PURPOSE] Best Practices

### Test-Driven Development
1. **Run tests first** - See what compliance requires
2. **Fix one test at a time** - Focus on specific failures
3. **Re-run frequently** - Get immediate feedback
4. **Use watch mode** - Automate the feedback loop

### Writing Custom Tests
1. **Follow naming convention** - `test_*` functions
2. **Use descriptive messages** - Clear assertion errors
3. **Skip appropriately** - Use `pytest.skip()` for non-applicable tests
4. **Test incrementally** - Start with basic structure, add complexity

### Integration with Development
```bash
# Development workflow
python tools/dev_watch.py --module my_module --test
# ↳ Runs pytest compliance tests automatically on file changes
```

## [LAUNCH] Advanced Usage

### Continuous Integration
```yaml
# .github/workflows/compliance.yml
name: Module Compliance
on: [push, pull_request]
jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install pytest
      - name: Run compliance tests
        run: |
          python -m pytest tools/pytest_compliance.py -v
```

### Custom Reporting
```python
# Generate compliance report
python -m pytest tools/pytest_compliance.py --html=compliance_report.html
```

### Performance Testing
```bash
# Time compliance checking
time python tools/pytest_compliance.py --module my_module

# Profile with pytest-benchmark
python -m pytest tools/pytest_compliance.py --benchmark-only
```

---

**Next Steps:**
- Try testing an existing module with pytest compliance
- Compare results with traditional compliance.py
- Move on to [Development Watch Mode](./dev-watch.md) for real-time feedback