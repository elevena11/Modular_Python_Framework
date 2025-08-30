# Proposed Development Workflow

## Overview
**Purpose**: Comprehensive module development pipeline that maintains infrastructure stability while enabling safe module development  
**Philosophy**: Static core structure with rigorous testing before production integration  
**Goal**: Eliminate runtime loading risks while providing fast, reliable development feedback

## Development Pipeline Architecture

### Three-Phase Testing Approach

```
Phase 1: Static Analysis     →    Phase 2: Isolated Testing    →    Phase 3: Production
(1-2 seconds)                     (15-30 seconds)                    (Clean restart)
├─ Compliance validation          ├─ Minimal framework copy         ├─ Add to main app
├─ Service documentation          ├─ Integration testing            ├─ Full system test
├─ Unit tests                     ├─ API endpoint testing           └─ Deploy confidence
└─ Fast feedback                  └─ Database operations
```

## Complete Development Workflow

### Step 1: Module Creation & Implementation
```bash
# 1. Scaffold new module with compliant structure
python tools/scaffold_module.py --name new_feature --type standard --features api,database,settings

# 2. Implement business logic
# Edit modules/standard/new_feature/services.py
# Edit modules/standard/new_feature/api.py  
# Edit modules/standard/new_feature/settings.py
```

### Step 2: Static Analysis & Compliance (Phase 1)
```bash
# 3. Fast validation (1-2 seconds)
python tools/compliance/compliance.py validate --module standard.new_feature

# 4. Run unit tests
python -m pytest tests/modules/standard/new_feature/ --fast

# 5. Verify service documentation complete
python tools/compliance/compliance.py check-service-methods --module standard.new_feature
```

### Step 3: Isolated Integration Testing (Phase 2)
```bash
# 6. Test in minimal environment copy (15-30 seconds)
python tools/test_environment.py --module standard.new_feature --run-tests

# 7. Integration testing with core services
python tools/test_environment.py --module standard.new_feature --integration

# 8. API endpoint testing (if module has API)
python tools/test_environment.py --module standard.new_feature --test-api
```

### Step 4: Production Integration (Phase 3)
```bash
# 9. Only after all tests pass - add to main app
python app.py  # Clean restart with new module

# 10. Verify production integration
curl -X GET "http://localhost:8000/api/v1/new_feature/status"
```

## Required Tooling Infrastructure

### 1. Enhanced Compliance Tool

#### Current State
- Basic decorator validation exists in `tools/compliance/compliance.py`

#### Required Enhancements
```python
# tools/compliance/compliance.py (enhanced)
class ModuleComplianceValidator:
    """Comprehensive module validation for development pipeline."""
    
    async def validate_module(self, module_path: str) -> ComplianceResult:
        """Run all compliance checks for a module."""
        checks = [
            self._validate_decorator_compliance(),      # @register_service with methods
            self._validate_service_documentation(),     # ServiceMethod completeness  
            self._validate_pydantic_settings(),         # Settings schema compliance
            self._validate_database_patterns(),         # integrity_session usage
            self._validate_api_schemas(),              # Response model compliance
            self._validate_error_handling(),           # Result pattern usage
            self._validate_phase1_phase2_separation(), # No service access in Phase 1
            self._validate_import_patterns(),          # Correct import paths
            self._validate_test_coverage(),           # Basic test coverage
            self._validate_manifest_json(),           # Dependency declarations
        ]
        return await self._run_all_checks(checks)
    
    def check_service_methods(self, module_path: str) -> ServiceMethodResult:
        """Validate service method documentation completeness."""
        # Check that all public methods have ServiceMethod definitions
        # Verify parameters match actual method signatures
        # Ensure examples are valid and executable
        
    def validate_dependencies(self, module_path: str) -> DependencyResult:
        """Validate all declared dependencies are available."""
        # Parse manifest.json dependencies
        # Check that required services exist in framework
        # Validate dependency versions if specified
```

#### Compliance Check Categories
1. **Decorator Compliance**: Enhanced @register_service with methods parameter
2. **Service Documentation**: Complete ServiceMethod definitions for all public methods
3. **Settings Compliance**: Proper Pydantic schema with validation
4. **Database Patterns**: integrity_session usage, proper models
5. **API Schema Compliance**: Response models, proper endpoint structure
6. **Error Handling**: Result pattern usage throughout
7. **Phase Separation**: No Phase 1 violations (service access during infrastructure setup)
8. **Import Patterns**: Correct core imports, no deprecated patterns
9. **Test Coverage**: Basic unit tests for service methods
10. **Manifest Validation**: Dependencies declared correctly

### 2. Test Environment Tool (New)

#### Architecture
```python
# tools/test_environment.py (new implementation)
class TestEnvironment:
    """Minimal framework copy for safe module testing."""
    
    def __init__(self, target_module: str):
        self.target_module = target_module
        self.temp_dir = tempfile.mkdtemp(prefix=f"test_env_{target_module}_")
        self.required_modules = self._calculate_dependencies()
        self.test_database_path = self.temp_dir + "/test.db"
        
    async def create_isolated_environment(self):
        """Create minimal environment with only required dependencies."""
        # Copy framework core files
        # Copy only essential modules: database, settings, error_handler + target
        # Create temporary database with required tables
        # Set up isolated logging system
        # Configure test-only settings
        
    async def startup_minimal_framework(self) -> FrameworkResult:
        """Start minimal framework with only essentials."""
        try:
            # Bootstrap with temporary database  
            # Initialize only required core modules
            # Load target module with full Phase 1/Phase 2
            # Verify service registration works
            # Set up API routing if module has endpoints
            return FrameworkResult.success()
        except Exception as e:
            await self.cleanup()
            return FrameworkResult.error("STARTUP_FAILED", str(e))
            
    async def run_integration_tests(self) -> TestResult:
        """Run comprehensive integration tests."""
        tests = [
            self._test_module_loads_successfully(),
            self._test_service_registration_works(),
            self._test_dependencies_resolved(),
            self._test_api_endpoints_respond(),
            self._test_database_operations(),
            self._test_settings_integration(),
            self._test_error_handling_patterns(),
        ]
        return await self._execute_test_suite(tests)
        
    async def cleanup(self):
        """Guaranteed clean shutdown and cleanup."""
        # Close all database connections
        # Shutdown framework gracefully
        # Remove temporary files and directories
        # Clear sys.modules entries for temporary imports
        # Reset logging configuration
        shutil.rmtree(self.temp_dir, ignore_errors=True)
```

#### Dependency Calculation
```python
def _calculate_minimal_dependencies(self, target_module: str) -> List[str]:
    """Calculate minimal required modules for testing target."""
    # Parse target module's manifest.json
    # Core essentials: always include database, settings, error_handler
    # Recursively resolve declared dependencies  
    # Exclude heavy modules: model_manager (unless required)
    # Return minimal set for fastest possible testing
    
    required_core = ["core.database", "core.settings", "core.error_handler"]
    declared_deps = self._parse_manifest_dependencies(target_module)
    resolved_deps = self._resolve_dependency_chain(declared_deps)
    
    return required_core + resolved_deps
```

### 3. Pytest Integration Enhancement

#### Test Structure
```python
# tests/framework/test_module_integration.py (new)
class TestModuleIntegration:
    """Integration tests for new modules using test environment."""
    
    @pytest.fixture
    def test_env(self, module_path):
        """Set up isolated test environment."""
        env = TestEnvironment(module_path)
        yield env
        asyncio.run(env.cleanup())
    
    async def test_module_loads_successfully(self, test_env):
        """Module loads without errors in minimal framework."""
        result = await test_env.startup_minimal_framework()
        assert result.success, f"Module failed to load: {result.message}"
        
    async def test_service_registration_works(self, test_env):
        """Services register correctly with app_context."""
        await test_env.startup_minimal_framework()
        
        # Verify services are registered
        services = test_env.framework.app_context.get_available_services()
        expected_service = f"{test_env.target_module}.service"
        assert expected_service in services
        
    async def test_dependencies_resolved(self, test_env):
        """All declared dependencies are available."""
        await test_env.startup_minimal_framework()
        
        # Verify dependency resolution
        deps_result = await test_env.validate_dependencies()
        assert deps_result.success, f"Dependencies failed: {deps_result.message}"
        
    async def test_api_endpoints_respond(self, test_env):
        """API endpoints return valid responses."""
        if not test_env.module_has_api():
            pytest.skip("Module has no API endpoints")
            
        await test_env.startup_minimal_framework()
        
        # Test standard endpoints
        client = test_env.get_test_client()
        endpoints = test_env.get_module_endpoints()
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 200
            
    async def test_database_operations(self, test_env):
        """Database operations work if module uses database."""
        if not test_env.module_has_database():
            pytest.skip("Module has no database operations")
            
        await test_env.startup_minimal_framework()
        
        # Test basic CRUD operations
        service = test_env.framework.app_context.get_service(f"{test_env.target_module}.service")
        
        # Test database connectivity
        async with test_env.framework.app_context.database.integrity_session(
            test_env.target_module, "test"
        ) as session:
            # Verify session works
            result = await session.execute(text("SELECT 1"))
            assert result is not None
```

#### Automated Test Pipeline
```python
# tests/conftest.py (enhanced)
def pytest_configure(config):
    """Configure pytest for module development workflow."""
    config.addinivalue_line(
        "markers", 
        "integration: marks tests as integration tests requiring test environment"
    )
    config.addinivalue_line(
        "markers",
        "module_dev: marks tests as part of module development workflow"
    )

@pytest.fixture(scope="session")
def development_workflow():
    """Fixture for full development workflow testing."""
    workflow = DevelopmentWorkflow()
    yield workflow
    workflow.cleanup()
```

## Benefits of This Approach

### 1. Fast Feedback Loop
- **Compliance check**: 1-2 seconds (static analysis)
- **Unit tests**: 5-10 seconds (isolated) 
- **Integration tests**: 15-30 seconds (minimal framework)
- **Full restart**: Only when everything passes

### 2. Risk Mitigation  
- **No production impact** until module proven working
- **Isolated testing** prevents interference with main app
- **Clean failure modes** - test environment can't corrupt main system
- **Rollback capability** - easy to remove failing modules

### 3. Developer Experience
- **Clear pass/fail gates** at each phase
- **Comprehensive validation** before production  
- **Fast iteration** during development
- **Confidence in deployment** after full pipeline passes

### 4. Infrastructure Integrity
- **Core stability maintained** - no runtime loading risks
- **Test isolation** - no state pollution between tests
- **Reproducible results** - clean environment every time
- **Memory safety** - test environment disposal prevents leaks

## Infrastructure Principles Applied

### Systems Thinking Architecture
- **Single correct pattern**: One way to develop modules (through this pipeline)
- **Natural failure**: Modules fail fast at appropriate pipeline stage
- **Clean break**: No backwards compatibility for non-compliant modules
- **Enforced correctness**: Pipeline makes wrong patterns impossible to deploy

### Quality Gates
1. **Compliance Gate**: Must pass all static analysis checks
2. **Testing Gate**: Must pass unit and integration tests  
3. **Documentation Gate**: Must have complete service method documentation
4. **Integration Gate**: Must work correctly in isolated environment

## Implementation Priority

### Phase 1: Enhanced Compliance Tool
**Timeline**: 1-2 days  
**Focus**: Extend existing compliance tool with comprehensive validation
- Enhance `tools/compliance/compliance.py`
- Add service method documentation validation
- Implement dependency checking
- Create fast static analysis pipeline

### Phase 2: Test Environment Infrastructure  
**Timeline**: 3-5 days
**Focus**: Build isolated testing framework
- Create `tools/test_environment.py`
- Implement minimal framework startup/shutdown
- Add dependency calculation logic
- Build integration testing capabilities

### Phase 3: Pytest Integration
**Timeline**: 2-3 days
**Focus**: Comprehensive automated testing
- Enhance test suites with integration tests
- Add automated pipeline integration
- Create development workflow fixtures
- Prepare for CI/CD integration

### Phase 4: Documentation & Training
**Timeline**: 1 day
**Focus**: Developer documentation and examples
- Complete developer workflow documentation
- Create example module development walkthrough
- Document troubleshooting guide
- Establish best practices

## Example Development Session

### Scenario: Creating a New Analytics Module

```bash
# 1. Create module structure
python tools/scaffold_module.py --name analytics --type standard --features api,database,settings

# 2. Implement business logic
# (Edit services, API endpoints, settings schema)

# 3. Fast validation (should pass in seconds)
python tools/compliance/compliance.py validate --module standard.analytics
✅ All compliance checks passed

# 4. Unit tests
python -m pytest tests/modules/standard/analytics/ --fast  
✅ 15 tests passed in 3.2s

# 5. Integration testing (isolated environment)
python tools/test_environment.py --module standard.analytics --integration
✅ Minimal framework startup: SUCCESS
✅ Service registration: SUCCESS  
✅ API endpoints: SUCCESS (3 endpoints tested)
✅ Database operations: SUCCESS
✅ Dependencies resolved: SUCCESS

# 6. Production integration (only after all passes)  
python app.py
✅ Module loaded successfully
✅ All services registered
✅ API endpoints available at /api/v1/analytics/*
```

## Long-Term Benefits

### Infrastructure Quality
- **Mature module ecosystem** with guaranteed compliance
- **Predictable development cycles** with clear validation steps
- **High-quality documentation** automatically enforced
- **Reduced production issues** through comprehensive pre-deployment testing

### Developer Productivity
- **Clear development path** with immediate feedback
- **Reduced debugging time** through early error detection
- **Confidence in deployments** after pipeline completion
- **Standardized patterns** across all modules

### Framework Evolution
- **Safe module development** without risking core stability  
- **Quality metrics** from automated compliance checking
- **Documentation completeness** from enforced service method documentation
- **Testing coverage** from integrated test pipeline

This workflow provides **infrastructure-grade reliability** with **developer-friendly processes**, ensuring the framework remains stable while enabling rapid, safe module development.