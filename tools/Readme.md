
# Modular Framework Tools

This directory contains development and analysis tools for the Modular Framework.

## Tool Categories

### Error Analysis & Compliance Tools
**Location**: `error_analysis/`

Data-driven tools for analyzing error patterns and developing compliance standards:
- **Error Analysis Engine**: Pattern detection and compliance standard generation
- **Interactive Query Tool**: Filter and explore error data by module/pattern/timeframe  
- **Strategic Insights**: Prioritized compliance opportunities and weekly reports

See [`error_analysis/README.md`](error_analysis/README.md) for detailed documentation.

### Development & Debugging Tools

#### `check_module_status.py`
**Runtime diagnostic tool** that examines the current state of your running application.

```bash
# Check all modules
python tools/check_module_status.py

# Check a specific module  
python tools/check_module_status.py standard.ai_agent
```

**Features**:
- Reports which modules are loaded and their initialization status
- Lists registered services for each module
- Identifies dependency issues and missing dependencies
- Useful for troubleshooting module issues while the application is running

#### `module_dependency_test.py`  
**Static analysis tool** that scans your codebase without requiring the application to be running.

```bash
python tools/module_dependency_test.py
```

**Features**:
- Scans module manifests for declared dependencies
- Analyzes Python files to find service registrations and dependencies
- Identifies architectural inconsistencies (missing dependencies, mismatched service names, etc.)
- Helps maintain consistency and catch issues before runtime problems

### Compliance & Quality Tools

#### `compliance/compliance.py`
**Compliance validation system** that checks modules against framework standards.

```bash
# Validate all modules
python tools/compliance/compliance.py --validate-all

# Validate specific module
python tools/compliance/compliance.py --validate core.settings

# Generate compliance reports
python tools/compliance/compliance.py --report
```

**Features**:
- Validates modules against predefined standards
- Generates compliance reports and tracks improvements
- Supports custom validation patterns and requirements
- Integrates with error analysis for data-driven standard development

### Module Development Tools

#### `scaffold_module.py`
**Module scaffolding tool** for creating new modules with proper structure.

```bash
# Create new module with features
python tools/scaffold_module.py --name my_module --features api,database

# Create minimal module
python tools/scaffold_module.py --name simple_module
```

#### `dev_watch.py`
**Development monitoring tool** for watching module changes during development.

```bash
python tools/dev_watch.py --module my_module
```

#### `test_module.py`
**Module testing utility** for running module-specific tests.

```bash
python tools/test_module.py my_module
```

### Analysis & Monitoring Tools

#### `pytest_compliance.py`
**Pytest-based compliance testing** tool for structural validation during development.

```bash
# Test specific module
python tools/pytest_compliance.py --module veritas_knowledge_graph

# Run all modules with pytest
python -m pytest tools/pytest_compliance.py -v

# Integration with regular pytest
pytest tools/pytest_compliance.py::TestCoreStandards::test_module_structure -v
```

**Features**:
- Immediate feedback during development
- Tests architectural patterns (two-phase init, service registration)
- Integrates with existing pytest workflows
- Validates core framework requirements

#### `create_spec.py`
**Specification generation** tool for creating module documentation and specifications.

## Integrated Development Workflow

### Phase 1: Development
**During active development** - use for immediate feedback:

```bash
# 1. Test module structure as you develop
python tools/pytest_compliance.py --module my_module

# 2. Monitor for runtime issues  
python tools/check_module_status.py

# 3. Watch for dependency issues
python tools/module_dependency_test.py
```

### Phase 2: Pre-Commit Validation  
**Before committing code** - comprehensive validation:

```bash
# 1. Full architectural compliance
python tools/pytest_compliance.py --module my_module

# 2. Framework standards compliance  
python tools/compliance/compliance.py --validate my_module

# 3. Fix any issues before committing
```

### Phase 3: Post-Integration Monitoring
**After integration** - track system health:

```bash
# 1. Weekly error analysis
python tools/error_analysis/compliance_insights.py --report

# 2. Identify emerging patterns
python tools/error_analysis/error_query.py --days 7

# 3. System-wide compliance check
python tools/compliance/compliance.py --validate-all
```

## Quick Start Guide

### For New Developers
1. **Understand the codebase**: `python tools/module_dependency_test.py`
2. **Check system health**: `python tools/error_analysis/compliance_insights.py --report`
3. **Create new module**: `python tools/scaffold_module.py --name my_module`

### For Daily Development
1. **Quick structure check**: `python tools/pytest_compliance.py --module my_module`
2. **Monitor module status**: `python tools/check_module_status.py`
3. **Full compliance validation**: `python tools/compliance/compliance.py --validate my_module`

### For Quality Assurance
1. **Full compliance check**: `python tools/compliance/compliance.py --validate-all`
2. **Error pattern analysis**: `python tools/error_analysis/error_analysis.py --analyze`
3. **Generate compliance opportunities**: `python tools/error_analysis/compliance_insights.py --report`

## Tool Comparison & Selection

### Compliance Testing: When to Use Which Tool

| Scenario | Use `pytest_compliance.py` | Use `compliance/compliance.py` |
|----------|---------------------------|--------------------------------|
| **Active Development** | [YES] Fast feedback, structure validation | [NO] Too comprehensive for rapid iteration |
| **Pre-Commit Checks** | [YES] Quick architectural validation | [YES] Full standards compliance |
| **CI/CD Integration** | [YES] Standard pytest integration | [YES] Comprehensive validation |
| **New Module Creation** | [YES] Test basic structure immediately | [LATER] Run after basic implementation |
| **Framework Standards** | [NO] Limited to hardcoded patterns | [YES] Full JSON-based standards |
| **Custom Standards** | [NO] Requires code changes | [YES] Just add JSON files |
| **Error-Driven Standards** | [NO] Not connected to error data | [YES] Integrates with error analysis |
| **Legacy UI Support** | [YES] Properly skips deprecated Gradio | [YES] Supports current framework evolution |

### Error Analysis: Progressive Depth

| Tool | When to Use | Output | Time Investment |
|------|-------------|---------|-----------------|
| `error_query.py` | Daily spot checks | Quick filtered results | 30 seconds |
| `error_analysis.py` | Weekly deep dives | Comprehensive analysis | 2-3 minutes |
| `compliance_insights.py` | Strategic planning | Prioritized opportunities | 5 minutes |

## Best Practices

### Development Workflow
- **Use `pytest_compliance.py`** during active development for immediate feedback
- **Use `compliance/compliance.py`** before commits for comprehensive validation  
- **Monitor error patterns** weekly with `compliance_insights.py`
- **Quick health checks** with `error_query.py --days 1`

### Quality Assurance
- **Run both compliance tools** before merging branches
- **Generate error-driven standards** from `compliance_insights.py` monthly
- **Track compliance improvements** over time with regular validation
- **Use scaffolding tools** for consistent module structure

### Team Coordination
- **Share compliance insights** weekly with development team
- **Prioritize high-impact standards** identified by error analysis
- **Regular dependency analysis** to maintain architectural integrity
- **Document new patterns** discovered through error analysis

### Framework Evolution Support
- **Gradio UI support deprecated** - framework now uses Streamlit exclusively
- **Legacy dual-UI infrastructure remains** for compatibility but only Streamlit is actively used
- **Compliance tools updated** to reflect current framework state and skip deprecated patterns

---

*These tools support the Modular Framework's philosophy of data-driven development and AI-agent-ready code patterns.*