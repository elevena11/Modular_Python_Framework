# Testing Strategies

This guide covers comprehensive testing approaches for VeritasForma Framework modules, from unit testing to integration testing and continuous validation.

## 🎯 Testing Philosophy

### Framework Testing Layers

#### 1. **Compliance Testing** (Framework Standards)
- **Purpose:** Ensure modules follow framework patterns
- **Scope:** Two-phase initialization, service registration, file structure
- **Tools:** `pytest_compliance.py`, `compliance.py`
- **Frequency:** Every change

#### 2. **Unit Testing** (Business Logic)
- **Purpose:** Validate individual component functionality
- **Scope:** Service methods, utility functions, data transformations
- **Tools:** pytest, unittest, module-specific tests
- **Frequency:** Test-driven development

#### 3. **Integration Testing** (Component Interaction)
- **Purpose:** Verify modules work together correctly
- **Scope:** API endpoints, database operations, service dependencies
- **Tools:** pytest with fixtures, FastAPI test client
- **Frequency:** Feature completion

#### 4. **System Testing** (End-to-End)
- **Purpose:** Validate complete workflows and user scenarios
- **Scope:** Full application stack, UI interactions, data flow
- **Tools:** Selenium, API testing, manual validation
- **Frequency:** Release cycles

## 🧪 Test Structure and Organization

### Generated Test Structure
When using module scaffolding, tests are automatically generated:

```
tests/
├── modules/
│   ├── core/
│   ├── standard/
│   │   └── my_module/
│   │       ├── __init__.py
│   │       ├── test_service.py           # Unit tests
│   │       ├── test_compliance.py        # Compliance tests
│   │       ├── test_api.py              # API tests (if applicable)
│   │       ├── test_database.py         # Database tests (if applicable)
│   │       └── test_integration.py      # Integration tests
│   └── extensions/
├── fixtures/                            # Shared test fixtures
├── conftest.py                         # Pytest configuration
└── README.md                           # Testing documentation
```

### Test Categories by Module Features

#### Core Service Testing
**File:** `test_service.py`
**Focus:** Business logic validation

```python
import pytest
from unittest.mock import Mock, AsyncMock
from modules.standard.my_module.services import MyModuleService

@pytest.fixture
def mock_app_context():
    """Mock app context for testing"""
    context = Mock()
    return context

@pytest.fixture  
def service():
    """Create service instance for testing"""
    return MyModuleService()

@pytest.mark.asyncio
async def test_service_initialization(service, mock_app_context):
    """Test service initialization"""
    assert not service.is_ready()
    
    result = await service.initialize(mock_app_context)
    assert result is True
    assert service.is_ready()

@pytest.mark.asyncio
async def test_business_logic_method(service, mock_app_context):
    """Test specific business logic"""
    await service.initialize(mock_app_context)
    
    result = await service.process_data({"test": "data"})
    
    assert result["status"] == "success"
    assert "processed_data" in result
```

#### API Testing
**File:** `test_api.py`
**Focus:** Endpoint validation and request/response handling

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import your module's API router
from modules.standard.my_module.api import router

@pytest.fixture
def mock_app_context():
    """Mock app context with service"""
    context = Mock()
    service = Mock()
    service.is_ready.return_value = True
    context.get_service.return_value = service
    return context, service

@pytest.fixture
def client():
    """FastAPI test client"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

def test_status_endpoint(client, mock_app_context):
    """Test status endpoint"""
    app_context, service = mock_app_context
    
    with patch('modules.standard.my_module.api.get_service', return_value=service):
        response = client.get("/my_module/status")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"

@pytest.mark.asyncio
async def test_post_endpoint(client, mock_app_context):
    """Test POST endpoint with validation"""
    app_context, service = mock_app_context
    service.process_request.return_value = {"result": "processed"}
    
    test_data = {
        "name": "test_item",
        "description": "Test description"
    }
    
    with patch('modules.standard.my_module.api.get_service', return_value=service):
        response = client.post("/my_module/items", json=test_data)
    
    assert response.status_code == 200
    assert response.json()["result"] == "processed"
    service.process_request.assert_called_once()
```

#### Database Testing
**File:** `test_database.py`
**Focus:** Data persistence and retrieval operations

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from modules.standard.my_module.db_models import MyModuleItem, Base
from modules.standard.my_module.database import MyModuleDatabase

@pytest_asyncio.fixture
async def async_session():
    """Create test database session"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.fixture
def database():
    """Create database instance"""
    return MyModuleDatabase()

@pytest.mark.asyncio
async def test_create_item(database, async_session):
    """Test item creation"""
    # Initialize database
    mock_context = Mock()
    mock_context.get_service.return_value = Mock()
    await database.initialize(mock_context)
    
    # Create item
    item = await database.create_item(
        async_session,
        name="test_item",
        description="Test description"
    )
    
    assert item is not None
    assert item.name == "test_item"
    assert item.description == "Test description"
    assert item.is_active is True

@pytest.mark.asyncio
async def test_get_items(database, async_session):
    """Test item retrieval"""
    await database.initialize(Mock())
    
    # Create test data
    await database.create_item(async_session, "item1", "Description 1")
    await database.create_item(async_session, "item2", "Description 2")
    
    # Retrieve items
    items = await database.get_items(async_session, limit=10)
    
    assert len(items) == 2
    assert items[0].name == "item1"
    assert items[1].name == "item2"
```

#### Integration Testing
**File:** `test_integration.py`
**Focus:** Module interaction with framework and other modules

```python
import pytest
from unittest.mock import Mock, patch
import asyncio

from modules.standard.my_module.api import initialize, setup_module
from modules.standard.my_module.services import get_my_module_service

@pytest.fixture
def mock_app_context():
    """Mock complete app context"""
    context = Mock()
    context.register_service = Mock()
    context.register_shutdown_handler = Mock()
    context.register_module_setup_hook = Mock()
    context.get_service = Mock()
    return context

@pytest.mark.asyncio
async def test_two_phase_initialization_flow(mock_app_context):
    """Test complete initialization flow"""
    # Phase 1
    result = await initialize(mock_app_context)
    assert result is True
    
    # Verify Phase 1 registrations
    mock_app_context.register_service.assert_called_once()
    mock_app_context.register_shutdown_handler.assert_called_once()
    mock_app_context.register_module_setup_hook.assert_called_once()
    
    # Phase 2
    result = await setup_module(mock_app_context)
    assert result is True

@pytest.mark.asyncio
async def test_service_integration(mock_app_context):
    """Test service integration with app context"""
    # Mock dependencies
    mock_db_service = Mock()
    mock_settings_service = Mock()
    mock_app_context.get_service.side_effect = lambda name: {
        "core.database.service": mock_db_service,
        "core.settings.service": mock_settings_service
    }.get(name)
    
    # Initialize module
    await initialize(mock_app_context)
    await setup_module(mock_app_context)
    
    # Get service and test functionality
    service = get_my_module_service()
    assert service.is_ready()
    
    # Test service method that uses dependencies
    result = await service.complex_operation()
    assert result["status"] == "success"
```

## 🔧 Advanced Testing Patterns

### Property-Based Testing
Use hypothesis for generating test data:

```python
import pytest
from hypothesis import given, strategies as st
from modules.standard.my_module.services import MyModuleService

@given(
    name=st.text(min_size=1, max_size=100),
    value=st.integers(min_value=0, max_value=1000)
)
@pytest.mark.asyncio
async def test_data_processing_with_random_inputs(name, value):
    """Test data processing with random inputs"""
    service = MyModuleService()
    await service.initialize(Mock())
    
    result = await service.process_data({"name": name, "value": value})
    
    # Property: result should always be valid
    assert "status" in result
    assert result["status"] in ["success", "error"]
    
    # Property: name should be preserved (if valid)
    if result["status"] == "success":
        assert result["processed_name"] == name.strip()
```

### Parametrized Testing
Test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("input_data,expected_status,expected_count", [
    ({"items": []}, "success", 0),
    ({"items": [1, 2, 3]}, "success", 3),
    ({"items": ["a", "b"]}, "success", 2),
    ({}, "error", 0),
    ({"invalid": "data"}, "error", 0),
])
@pytest.mark.asyncio
async def test_process_items_various_inputs(service, input_data, expected_status, expected_count):
    """Test item processing with various inputs"""
    await service.initialize(Mock())
    
    result = await service.process_items(input_data)
    
    assert result["status"] == expected_status
    if expected_status == "success":
        assert len(result["processed_items"]) == expected_count
```

### Performance Testing
Monitor performance characteristics:

```python
import time
import pytest

@pytest.mark.performance
@pytest.mark.asyncio
async def test_service_performance(service):
    """Test service performance under load"""
    await service.initialize(Mock())
    
    # Test single operation performance
    start_time = time.time()
    result = await service.heavy_operation()
    duration = time.time() - start_time
    
    assert result["status"] == "success"
    assert duration < 1.0  # Should complete within 1 second
    
    # Test bulk operation performance
    start_time = time.time()
    results = await asyncio.gather(*[
        service.quick_operation() for _ in range(100)
    ])
    bulk_duration = time.time() - start_time
    
    assert len(results) == 100
    assert bulk_duration < 5.0  # 100 operations in under 5 seconds
```

### Error Handling Testing
Validate error scenarios:

```python
@pytest.mark.asyncio
async def test_error_handling_database_failure(service, mock_app_context):
    """Test service behavior when database fails"""
    # Mock database service to raise exception
    mock_db = Mock()
    mock_db.get_session.side_effect = ConnectionError("Database unavailable")
    mock_app_context.get_service.return_value = mock_db
    
    await service.initialize(mock_app_context)
    
    # Service should handle database errors gracefully
    result = await service.get_data()
    
    assert result["status"] == "error"
    assert "database" in result["error"].lower()
    assert service.is_ready()  # Service should remain operational

@pytest.mark.asyncio
async def test_initialization_failure_recovery(service):
    """Test service recovery from initialization failures"""
    # First initialization fails
    bad_context = Mock()
    bad_context.get_service.return_value = None
    
    result = await service.initialize(bad_context)
    assert result is False
    assert not service.is_ready()
    
    # Second initialization succeeds
    good_context = Mock()
    good_context.get_service.return_value = Mock()
    
    result = await service.initialize(good_context)
    assert result is True
    assert service.is_ready()
```

## 📊 Test Data Management

### Fixtures and Test Data
Create reusable test data:

```python
# conftest.py
import pytest
from datetime import datetime

@pytest.fixture
def sample_items():
    """Sample items for testing"""
    return [
        {
            "name": "item_1",
            "description": "First test item",
            "metadata": {"type": "test", "priority": 1}
        },
        {
            "name": "item_2", 
            "description": "Second test item",
            "metadata": {"type": "test", "priority": 2}
        }
    ]

@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing"""
    with patch('modules.standard.my_module.services.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
        yield mock_dt
```

### Database Test Data
Manage test database state:

```python
@pytest.fixture
async def populated_database(async_session, database):
    """Database with test data"""
    await database.initialize(Mock())
    
    # Create test data
    items = [
        await database.create_item(async_session, f"item_{i}", f"Description {i}")
        for i in range(5)
    ]
    
    return database, items

@pytest.mark.asyncio
async def test_with_populated_data(populated_database, async_session):
    """Test using pre-populated database"""
    database, items = populated_database
    
    retrieved_items = await database.get_items(async_session)
    assert len(retrieved_items) == 5
    assert retrieved_items[0].name == "item_0"
```

## 🔄 Continuous Testing Strategies

### Test-Driven Development (TDD)
1. **Write failing test** - Define expected behavior
2. **Implement minimum code** - Make test pass
3. **Refactor** - Improve code quality
4. **Repeat** - Add next feature

```bash
# TDD Workflow
# 1. Write test
echo "def test_new_feature(): assert False" >> test_service.py

# 2. Run test (should fail)
pytest test_service.py::test_new_feature -v

# 3. Implement feature
# Edit services.py

# 4. Run test (should pass)
pytest test_service.py::test_new_feature -v

# 5. Refactor and repeat
```

### Behavior-Driven Development (BDD)
Use pytest-bdd for behavior specifications:

```python
# features/data_processing.feature
Feature: Data Processing
    As a user
    I want to process data through the module
    So that I can get consistent results

    Scenario: Process valid data
        Given I have a module service
        And I have valid input data
        When I process the data
        Then I should get a success result
        And the data should be transformed correctly

# test_bdd.py
from pytest_bdd import scenarios, given, when, then
scenarios('features/data_processing.feature')

@given('I have a module service')
def service(my_module_service):
    return my_module_service

@given('I have valid input data')
def input_data():
    return {"items": [1, 2, 3]}

@when('I process the data')
def process_data(service, input_data):
    return service.process_data(input_data)

@then('I should get a success result')
def check_success(process_result):
    assert process_result["status"] == "success"
```

### Mutation Testing
Validate test quality with mutation testing:

```bash
# Install mutation testing tool
pip install mutmut

# Run mutation tests
mutmut run --paths-to-mutate modules/standard/my_module/services.py

# Check results
mutmut show
```

## 📈 Test Metrics and Coverage

### Coverage Analysis
Track test coverage:

```bash
# Install coverage tools
pip install pytest-cov

# Run tests with coverage
pytest --cov=modules/standard/my_module tests/modules/standard/my_module/ --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Quality Metrics
Monitor test effectiveness:

```python
# Test metrics collection
import pytest

class TestMetrics:
    def __init__(self):
        self.test_count = 0
        self.assertion_count = 0
        self.mock_count = 0
    
    def count_test(self):
        self.test_count += 1
    
    def count_assertion(self):
        self.assertion_count += 1

# Usage in tests
metrics = TestMetrics()

def test_with_metrics(service):
    metrics.count_test()
    
    result = service.method()
    assert result is not None
    metrics.count_assertion()
    
    assert result["status"] == "success"
    metrics.count_assertion()
```

### Performance Benchmarking
Track performance over time:

```bash
# Install benchmark plugin
pip install pytest-benchmark

# Run benchmarks
pytest --benchmark-only tests/modules/standard/my_module/

# Save benchmark results
pytest --benchmark-only --benchmark-json=benchmark.json
```

## 🎯 Best Practices

### Test Organization
1. **Group related tests** - Use classes and descriptive names
2. **Test one thing** - Each test should have single responsibility
3. **Clear test names** - Describe what is being tested
4. **Arrange-Act-Assert** - Follow clear test structure

### Mock and Fixture Usage
1. **Mock external dependencies** - Database, APIs, file systems
2. **Use fixtures for setup** - Reusable test configuration
3. **Isolate tests** - Each test should be independent
4. **Mock at boundaries** - Mock at module interfaces

### Error Testing
1. **Test happy path first** - Ensure basic functionality works
2. **Test error conditions** - Invalid inputs, failures, edge cases
3. **Test boundary conditions** - Empty data, maximum values
4. **Test recovery scenarios** - How system handles failures

### Performance Considerations
1. **Fast unit tests** - Should run in milliseconds
2. **Moderate integration tests** - Can take seconds
3. **Slow system tests** - Reserved for comprehensive validation
4. **Parallel execution** - Use pytest-xdist for speed

## 🔍 Debugging Test Failures

### Common Test Issues

#### Async Test Problems
```python
# ❌ Wrong: Calling async function without await
def test_async_method(service):
    result = service.async_method()  # Returns coroutine, not result
    assert result["status"] == "success"  # Will fail

# ✅ Correct: Proper async test
@pytest.mark.asyncio
async def test_async_method(service):
    result = await service.async_method()
    assert result["status"] == "success"
```

#### Mock Configuration Issues
```python
# ❌ Wrong: Mock not configured properly
def test_with_broken_mock(service):
    mock_service = Mock()
    # Mock returns Mock() by default, not expected data
    result = service.use_dependency(mock_service)
    assert result["count"] == 5  # Will fail

# ✅ Correct: Mock configured with expected return
def test_with_proper_mock(service):
    mock_service = Mock()
    mock_service.get_count.return_value = 5
    result = service.use_dependency(mock_service)
    assert result["count"] == 5
```

#### Test Isolation Problems
```python
# ❌ Wrong: Tests affecting each other
class TestService:
    def setup_class(self):
        self.service = MyService()
    
    def test_first(self):
        self.service.set_value(10)
        assert self.service.get_value() == 10
    
    def test_second(self):
        # Fails because first test modified service state
        assert self.service.get_value() == 0

# ✅ Correct: Proper test isolation
class TestService:
    @pytest.fixture
    def service(self):
        return MyService()  # Fresh instance for each test
    
    def test_first(self, service):
        service.set_value(10)
        assert service.get_value() == 10
    
    def test_second(self, service):
        assert service.get_value() == 0  # Clean slate
```

### Debugging Techniques

#### Verbose Test Output
```bash
# Run with verbose output
pytest -v tests/modules/standard/my_module/

# Show print statements
pytest -s tests/modules/standard/my_module/

# Stop on first failure
pytest -x tests/modules/standard/my_module/

# Run specific test
pytest tests/modules/standard/my_module/test_service.py::test_specific_method -v
```

#### Using pdb for Debugging
```python
import pytest

def test_complex_logic(service):
    data = {"complex": "input"}
    
    # Set breakpoint
    pytest.set_trace()
    
    result = service.complex_method(data)
    assert result["status"] == "success"
```

#### Test Data Inspection
```python
def test_with_inspection(service, caplog):
    """Test with logging inspection"""
    with caplog.at_level(logging.DEBUG):
        result = service.method_with_logging()
    
    # Inspect logs
    assert "Processing started" in caplog.text
    assert result["status"] == "success"
    
    # Print for debugging
    print(f"Captured logs: {caplog.text}")
    print(f"Result: {result}")
```

---

**Next Steps:**
- Set up comprehensive testing for your modules
- Implement test automation in your development workflow
- Integrate testing with CI/CD pipelines
- Explore advanced testing techniques for complex scenarios