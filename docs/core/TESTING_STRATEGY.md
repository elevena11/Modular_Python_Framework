# Testing Strategy - Framework Interface Improvements

## Overview

This document outlines the comprehensive testing strategy for validating framework interface improvements. The strategy ensures that changes preserve functionality, maintain performance, and provide the expected benefits while allowing quick rollback if issues arise.

---

## Testing Philosophy

### **Safety First**
- Every change must be validated before proceeding
- Bootstrap sequence is sacred - never break startup
- Performance regressions are unacceptable
- Backwards compatibility is mandatory

### **Comprehensive Coverage**
- Unit tests for individual components
- Integration tests for module interactions
- System tests for complete functionality
- Performance tests for timing validation

### **Automated Validation**
- Automated test suites run after each change
- Continuous validation during development
- Clear pass/fail criteria for each phase
- Quick feedback loops for rapid iteration

---

## Test Categories

### **1. Bootstrap Sequence Tests**

**Purpose**: Ensure framework startup remains functional and timing is preserved

#### **Critical Bootstrap Tests**
```bash
#!/bin/bash
# bootstrap_tests.sh - Critical startup validation

echo "Testing bootstrap sequence..."

# Test 1: Basic startup
echo "Test 1: Framework startup"
timeout 30s python app.py &
APP_PID=$!
sleep 15  # Wait for bootstrap + model loading

# Check if process is running
if ! kill -0 $APP_PID 2>/dev/null; then
    echo "FAIL: Framework failed to start"
    exit 1
fi

# Test 2: API responsiveness
echo "Test 2: API endpoints"
curl -s http://localhost:8000/health >/dev/null
if [ $? -ne 0 ]; then
    echo "FAIL: API not responding"
    kill $APP_PID
    exit 1
fi

# Test 3: Database functionality
echo "Test 3: Database operations"
curl -s http://localhost:8000/api/v1/db/status | grep -q "connected"
if [ $? -ne 0 ]; then
    echo "FAIL: Database not connected"
    kill $APP_PID
    exit 1
fi

kill $APP_PID
echo "PASS: Bootstrap sequence tests completed"
```

#### **Timing Validation Tests**
```python
# test_bootstrap_timing.py
import time
import asyncio
from core.app_context import AppContext
from core.config import settings

async def test_bootstrap_timing():
    """Validate bootstrap phase timing remains within acceptable bounds."""
    
    start_time = time.time()
    
    # Phase 1: AppContext creation (should be < 50ms)
    phase1_start = time.time()
    app_context = AppContext(settings)
    app_context.initialize()
    phase1_duration = (time.time() - phase1_start) * 1000
    
    assert phase1_duration < 50, f"Phase 1 too slow: {phase1_duration}ms"
    
    # Database service should be available quickly
    db_service = app_context.get_service("core.database.service")
    assert db_service is not None, "Database service not available"
    
    total_duration = (time.time() - start_time) * 1000
    assert total_duration < 500, f"Bootstrap too slow: {total_duration}ms"
    
    print(f"Bootstrap timing: Phase1={phase1_duration:.1f}ms, Total={total_duration:.1f}ms")
```

### **2. Database Interface Tests**

**Purpose**: Validate new database interface functionality and compatibility

#### **Unit Tests**
```python
# test_database_interface.py
import pytest
from unittest.mock import Mock, AsyncMock
from core.database_interface import DatabaseInterface, DatabaseInterfaceError

class TestDatabaseInterface:
    
    def setup_method(self):
        self.mock_app_context = Mock()
        self.mock_db_service = Mock()
        self.mock_app_context.get_service.return_value = self.mock_db_service
        self.interface = DatabaseInterface(self.mock_app_context)
    
    async def test_session_creation(self):
        """Test session context manager creation."""
        # Mock session factory
        mock_session_factory = Mock()
        mock_session = AsyncMock()
        mock_session_factory.return_value = mock_session
        self.mock_db_service.get_database_session.return_value = mock_session_factory
        
        # Test session access
        async with self.interface.session("test_db") as session:
            assert session == mock_session
        
        # Verify proper calls
        self.mock_db_service.get_database_session.assert_called_once_with("test_db")
    
    async def test_database_not_found(self):
        """Test error handling for missing database."""
        self.mock_db_service.get_database_session.return_value = None
        
        with pytest.raises(DatabaseNotFoundError):
            async with self.interface.session("nonexistent_db"):
                pass
    
    def test_models_access(self):
        """Test model registry access."""
        expected_models = {"Document": Mock(), "Change": Mock()}
        self.mock_app_context.get_database_models.return_value = expected_models
        
        models = self.interface.models("test_db")
        assert models == expected_models
        self.mock_app_context.get_database_models.assert_called_once_with("test_db")
    
    def test_list_databases(self):
        """Test database listing functionality."""
        expected_dbs = ["framework", "semantic_core", "vector_operations"]
        self.mock_db_service.get_all_databases.return_value = {db: {} for db in expected_dbs}
        
        databases = self.interface.list_databases()
        assert databases == expected_dbs
```

#### **Integration Tests**  
```python
# test_database_integration.py
import pytest
from core.app_context import AppContext
from core.config import settings

class TestDatabaseIntegration:
    
    @pytest.fixture
    async def app_context(self):
        """Create real app context for integration testing."""
        ctx = AppContext(settings)
        ctx.initialize()
        
        # Wait for database service
        import asyncio
        await asyncio.sleep(0.1)  # Allow service registration
        
        yield ctx
        
        # Cleanup
        await ctx.shutdown()
    
    async def test_real_session_access(self, app_context):
        """Test database interface with real database service."""
        db = app_context.database
        
        # Test framework database access
        async with db.session("framework") as session:
            assert session is not None
            # Simple query test
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    async def test_multiple_database_access(self, app_context):
        """Test accessing multiple databases simultaneously."""
        db = app_context.database
        
        # Should be able to access multiple databases
        available_dbs = db.list_databases()
        assert "framework" in available_dbs
        
        # Test each available database
        for db_name in available_dbs[:3]:  # Test first 3 to avoid long test times
            async with db.session(db_name) as session:
                assert session is not None
```

### **3. Compatibility Tests**

**Purpose**: Ensure new and old patterns work together during transition

#### **Mixed Pattern Tests**
```python
# test_compatibility.py
class TestBackwardsCompatibility:
    
    async def test_old_pattern_still_works(self, app_context):
        """Verify old verbose database access pattern still functions."""
        # Old pattern
        database_service = app_context.get_service("core.database.service")
        assert database_service is not None
        
        session_factory = database_service.get_database_session("framework")
        assert session_factory is not None
        
        async with session_factory() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    async def test_new_pattern_works(self, app_context):
        """Verify new convenient database access pattern works."""
        # New pattern
        async with app_context.database.session("framework") as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    async def test_patterns_interchangeable(self, app_context):
        """Test that old and new patterns can be mixed in same module."""
        # Use both patterns in sequence
        
        # Old pattern first
        database_service = app_context.get_service("core.database.service") 
        session_factory = database_service.get_database_session("framework")
        async with session_factory() as session1:
            result1 = await session1.execute(text("SELECT 1"))
        
        # New pattern second
        async with app_context.database.session("framework") as session2:
            result2 = await session2.execute(text("SELECT 1"))
        
        assert result1.scalar() == result2.scalar() == 1
```

### **4. Performance Tests**

**Purpose**: Validate that improvements don't degrade performance

#### **Performance Benchmarks**
```python
# test_performance.py
import time
import asyncio
import statistics

class TestPerformance:
    
    async def benchmark_session_creation(self, app_context, pattern="new", iterations=100):
        """Benchmark database session creation performance."""
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            
            if pattern == "new":
                async with app_context.database.session("framework") as session:
                    pass
            else:  # old pattern
                db_service = app_context.get_service("core.database.service")
                session_factory = db_service.get_database_session("framework")
                async with session_factory() as session:
                    pass
            
            times.append((time.perf_counter() - start) * 1000)  # Convert to ms
        
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times)
        }
    
    async def test_performance_regression(self, app_context):
        """Test that new patterns aren't significantly slower."""
        old_stats = await self.benchmark_session_creation(app_context, "old")
        new_stats = await self.benchmark_session_creation(app_context, "new")
        
        # New pattern should be no more than 20% slower
        max_acceptable_slowdown = old_stats['mean'] * 1.2
        assert new_stats['mean'] <= max_acceptable_slowdown, \
            f"New pattern too slow: {new_stats['mean']:.2f}ms vs {old_stats['mean']:.2f}ms"
        
        print(f"Performance comparison:")
        print(f"  Old pattern: {old_stats['mean']:.2f}ms avg")
        print(f"  New pattern: {new_stats['mean']:.2f}ms avg")
        print(f"  Difference: {((new_stats['mean'] / old_stats['mean']) - 1) * 100:.1f}%")
```

### **5. Module Discovery & Auto-Discovery Tests**

**Purpose**: Ensure manifest.json elimination and auto-discovery work correctly

#### **Auto-Discovery Tests**
```python
# test_auto_discovery.py
import ast
import tempfile
from pathlib import Path
from core.module_discovery import ModuleDiscovery

class TestAutoDiscovery:
    
    def setup_method(self):
        self.discovery = ModuleDiscovery()
    
    def test_module_constants_extraction(self):
        """Test extraction of MODULE_* constants from api.py."""
        api_content = '''
"""Test module docstring."""

MODULE_ID = "test_module"
MODULE_NAME = "Test Module"
MODULE_VERSION = "1.0.0"
MODULE_AUTHOR = "Test Author"
MODULE_DESCRIPTION = __doc__.strip()
'''
        
        metadata = self.discovery._extract_module_constants(api_content)
        
        assert metadata['id'] == "test_module"
        assert metadata['name'] == "Test Module"
        assert metadata['version'] == "1.0.0"
        assert metadata['author'] == "Test Author"
    
    def test_decorator_extraction(self):
        """Test extraction of decorator metadata using AST."""
        api_content = '''
@register_service("test.service")
@register_database("test_db")
@register_models(["Model1", "Model2"])
@requires_modules(["core.database", "core.settings"])
class TestModule(BaseModule):
    pass
'''
        
        metadata = self.discovery._extract_decorators(api_content)
        
        assert "test.service" in metadata['services']
        assert "test_db" in metadata['databases']
        assert "Model1" in metadata['models']
        assert "Model2" in metadata['models']
        assert "core.database" in metadata['dependencies']
        assert "core.settings" in metadata['dependencies']
    
    def test_endpoint_extraction(self):
        """Test extraction of API endpoints from router."""
        api_content = '''
router = APIRouter(prefix="/api/v1/test", tags=["test"])

@router.get("/status")
async def get_status():
    pass

@router.post("/create")
async def create_item():
    pass
'''
        
        metadata = self.discovery._extract_endpoints(api_content)
        
        endpoints = metadata['api_endpoints']
        assert any(ep['method'] == 'GET' and ep['path'] == '/status' for ep in endpoints)
        assert any(ep['method'] == 'POST' and ep['path'] == '/create' for ep in endpoints)
    
    def test_full_discovery_integration(self):
        """Test complete discovery from actual api.py file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='api.py', delete=False) as f:
            f.write('''
"""Test Integration Module
Complete test module for auto-discovery."""

MODULE_ID = "test_integration"
MODULE_NAME = "Test Integration Module"
MODULE_VERSION = "2.1.0"
MODULE_AUTHOR = "Integration Test"
MODULE_DESCRIPTION = __doc__.strip()

from fastapi import APIRouter
from core.database import register_service, register_database, requires_modules

@register_service("test_integration.service")
@register_database("test_integration")
@requires_modules(["core.database"])
class TestIntegrationModule(BaseModule):
    pass

router = APIRouter(prefix="/api/v1/test-integration", tags=["test"])

@router.get("/health")
async def health_check():
    return {"status": "ok"}
''')
            f.flush()
            
            api_path = Path(f.name)
            metadata = self.discovery.discover_module(api_path)
            
            # Verify all metadata extracted correctly
            assert metadata['id'] == "test_integration"
            assert metadata['name'] == "Test Integration Module"
            assert metadata['version'] == "2.1.0"
            assert "test_integration.service" in metadata['services']
            assert "test_integration" in metadata['databases']
            assert "core.database" in metadata['dependencies']
            
            endpoints = metadata['api_endpoints']
            assert any(ep['method'] == 'GET' and ep['path'] == '/health' for ep in endpoints)
            
        api_path.unlink()  # Cleanup

class TestMixedDiscovery:
    """Test discovery with both api.py and manifest.json methods."""
    
    def test_api_priority_over_manifest(self):
        """Test that api.py discovery takes priority over manifest.json."""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            module_path = Path(temp_dir) / "test_module"
            module_path.mkdir()
            
            # Create api.py
            (module_path / "api.py").write_text('''
MODULE_ID = "from_api"
MODULE_NAME = "From API Discovery"
MODULE_VERSION = "1.0.0"
''')
            
            # Create manifest.json
            (module_path / "manifest.json").write_text('''
{
    "id": "from_manifest",
    "name": "From Manifest Discovery",
    "version": "0.9.0"
}
''')
            
            # Discovery should prefer api.py
            discovery = ModuleDiscovery()
            
            # Test api.py discovery
            api_metadata = discovery.discover_module(module_path / "api.py")
            assert api_metadata['id'] == "from_api"
            assert api_metadata['name'] == "From API Discovery"
    
    def test_manifest_fallback(self):
        """Test fallback to manifest.json when api.py has no MODULE_* constants."""
        with tempfile.TemporaryDirectory() as temp_dir:
            module_path = Path(temp_dir) / "test_module"
            module_path.mkdir()
            
            # Create api.py without MODULE_* constants
            (module_path / "api.py").write_text('''
# Just some regular Python code
class SomeClass:
    pass
''')
            
            # Create manifest.json
            (module_path / "manifest.json").write_text('''
{
    "id": "fallback_manifest",
    "name": "Fallback Discovery",
    "version": "1.0.0"
}
''')
            
            # Should fall back to manifest.json when api.py lacks metadata
            # (This would be handled by ModuleLoader, not ModuleDiscovery directly)
```

#### **Import Unification Tests**
```python
# test_unified_imports.py
class TestUnifiedImports:
    
    def test_unified_database_imports(self):
        """Test that all database utilities available from core.database."""
        from core.database import (
            DatabaseInterface,
            DatabaseBase,
            JSON,
            register_service,
            register_database,
            register_models,
            requires_modules
        )
        
        # Verify all imports successful
        assert DatabaseInterface is not None
        assert DatabaseBase is not None  
        assert JSON is not None
        assert register_service is not None
        assert register_database is not None
        assert register_models is not None
        assert requires_modules is not None
    
    def test_backwards_compatibility(self):
        """Test that old import patterns still work during transition."""
        # Old patterns should still work
        from modules.core.database.db_models import get_database_base, SQLiteJSON
        
        assert get_database_base is not None
        assert SQLiteJSON is not None
        
        # Should be equivalent to new unified imports
        from core.database import DatabaseBase, JSON
        
        # These should be the same functions/classes
        assert get_database_base == DatabaseBase
        assert SQLiteJSON == JSON
```

### **6. System-Level Tests**

**Purpose**: Validate complete framework functionality with improvements

#### **End-to-End Tests**
```bash
#!/bin/bash
# system_tests.sh - Complete system validation

set -e  # Exit on any error

echo "Running system-level tests..."

# Test 1: Complete startup sequence
echo "Test 1: Full system startup"
python app.py &
APP_PID=$!
sleep 20  # Wait for full initialization including model loading

# Test API endpoints
echo "Test 2: API functionality"
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/db/status
curl -f http://localhost:8000/api/v1/semantic_cli/system-status

# Test database operations through API
echo "Test 3: Database operations via API"
curl -f -X GET http://localhost:8000/api/v1/db/tables

# Test module functionality
echo "Test 4: Module operations"
curl -f -X POST http://localhost:8000/api/v1/semantic_cli/analyze-documents \
     -H "Content-Type: application/json" \
     -d '{}'

# Cleanup
kill $APP_PID
echo "PASS: System tests completed successfully"
```

#### **Load Testing**
```python
# test_load.py
import asyncio
import aiohttp
import time

async def load_test_database_interface(base_url, concurrent_requests=10, total_requests=100):
    """Load test database interface under concurrent access."""
    
    async def make_request(session, url):
        start = time.time()
        async with session.get(url) as response:
            await response.text()
            return time.time() - start
    
    connector = aiohttp.TCPConnector(limit=concurrent_requests)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        
        for _ in range(total_requests):
            task = make_request(session, f"{base_url}/api/v1/db/status")
            tasks.append(task)
        
        response_times = await asyncio.gather(*tasks)
    
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    
    print(f"Load test results:")
    print(f"  Average response time: {avg_response_time:.3f}s")
    print(f"  Max response time: {max_response_time:.3f}s")
    print(f"  Total requests: {total_requests}")
    
    # Assert reasonable performance
    assert avg_response_time < 0.1, f"Average response time too high: {avg_response_time}"
    assert max_response_time < 0.5, f"Max response time too high: {max_response_time}"
```

---

## Test Execution Strategy

### **Development Testing** (Continuous)
```bash
# Quick validation during development
pytest tests/unit/ -v                    # Unit tests
python tests/test_bootstrap_timing.py    # Bootstrap timing
./tests/bootstrap_tests.sh               # Quick startup test
```

### **Phase Validation** (Before proceeding to next phase)
```bash
# Comprehensive testing before phase completion
pytest tests/ -v                         # All unit and integration tests
./tests/system_tests.sh                  # End-to-end functionality
python tests/test_performance.py         # Performance validation
python tools/compliance/compliance.py validate --all
```

### **Pre-Production Testing** (Final validation)
```bash
# Complete test suite before deployment
pytest tests/ --cov=core --cov=modules   # Full test coverage
./tests/load_tests.py                    # Load testing
./tests/compatibility_tests.sh           # Backwards compatibility
python tests/benchmark_suite.py          # Performance benchmarking
```

---

## Test Data and Environment

### **Test Databases**
- **In-Memory SQLite**: For unit tests (fast, isolated)
- **File-Based SQLite**: For integration tests (realistic)
- **Test Data Sets**: Small, predictable datasets for validation

### **Mock Strategies**
- **Service Mocking**: Mock external services for unit tests
- **Database Mocking**: Mock database operations for speed
- **Time Mocking**: Control timing for bootstrap tests
- **Network Mocking**: Mock API calls for reliability

### **Test Configuration**
```python
# test_config.py
TEST_SETTINGS = {
    "DATABASE_URL": "sqlite:///:memory:",
    "DEBUG": True,
    "DISABLE_MODEL_LOADING": True,  # Speed up tests
    "LOG_LEVEL": "WARNING",         # Reduce test noise
    "TEST_MODE": True
}
```

---

## Automated Test Infrastructure

### **CI/CD Integration**
```yaml
# .github/workflows/test-framework.yml
name: Framework Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run unit tests
      run: pytest tests/unit/ -v
    
    - name: Run integration tests  
      run: pytest tests/integration/ -v
    
    - name: Bootstrap timing test
      run: python tests/test_bootstrap_timing.py
    
    - name: System tests
      run: ./tests/system_tests.sh
```

### **Test Reporting**
- **Coverage Reports**: Track test coverage percentage
- **Performance Trends**: Monitor performance over time
- **Compatibility Matrix**: Track old vs new pattern support
- **Failure Analysis**: Automated failure categorization

---

## Quality Gates

### **Phase 1 Quality Gate**
- [ ] All unit tests pass (100%)
- [ ] Bootstrap timing < 500ms (excluding models)
- [ ] New interface accessible via `app_context.database`
- [ ] Old patterns still work (backwards compatibility)
- [ ] No memory leaks detected
- [ ] Performance regression < 10%

### **Phase 2 Quality Gate**
- [ ] All modules use unified imports
- [ ] No import errors during bootstrap
- [ ] All integration tests pass
- [ ] Compliance checks pass for all modules
- [ ] Documentation updated and accurate

### **Final Quality Gate**
- [ ] Complete test suite passes (100%)
- [ ] Performance benchmarks meet requirements
- [ ] Load testing passes under expected traffic
- [ ] All rollback procedures tested and documented
- [ ] User acceptance criteria met

---

This comprehensive testing strategy ensures that framework improvements are validated thoroughly at every step, maintaining the reliability and performance of the RAH framework while adding valuable new capabilities.