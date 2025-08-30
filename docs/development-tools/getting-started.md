# Getting Started with Development Tools

Welcome to the VeritasForma Framework development tools! This guide will get you up and running with the new LLM-friendly development workflow in minutes.

## [PURPOSE] Quick Overview

The development tools solve the "oneshot coding" problem by providing:
- **Module scaffolding** - Generate compliant structures automatically
- **Real-time feedback** - See compliance status as you code
- **Test-driven development** - Clear success criteria for each change
- **LLM-friendly workflow** - Perfect for AI-assisted development

## [LAUNCH] 5-Minute Quick Start

### Step 1: Install Dependencies
```bash
# Install pytest for testing
pip install pytest

# Optional: Install watchdog for better file watching
pip install watchdog
```

### Step 2: Create Your First Module

#### Option A: Interactive Mode
```bash
# Run the scaffolding tool
python tools/scaffold_module.py

# Follow the interactive prompts:
# - Module name: my_first_module
# - Type: standard
# - Features: api,ui_streamlit
# - Dependencies: (accept defaults)
```

#### Option B: Command-Line Mode (LLM-Friendly)
```bash
# Create module with single command
python tools/scaffold_module.py --name my_first_module --features api,ui_streamlit
```

**Result:** Complete, compliant module structure generated in 30 seconds!

### Step 3: Start Development with Real-Time Feedback
```bash
# Start watch mode for instant feedback
python tools/dev_watch.py --module my_first_module

# You'll see:
# [CORRECT] Module Structure: All required files present
# [CORRECT] Two-Phase Init Phase 1: Valid Phase 1 implementation
# [CORRECT] Two-Phase Init Phase 2: Valid Phase 2 implementation
# [CORRECT] Service Registration: Service and shutdown handlers registered
# [ANALYSIS] Score: 4/4 (100%)
# [PASS] All compliance checks passed!
```

### Step 4: Make Your First Change
1. **Open** `modules/standard/my_first_module/services.py` in your editor
2. **Find** the `example_method()` function
3. **Replace** it with your business logic
4. **Save** the file
5. **Watch** the terminal update immediately with compliance status

### Step 5: Validate Everything Works
```bash
# Quick compliance test
python tools/test_module.py my_first_module

# Should show:
# [TEST] Testing module: standard.my_first_module
# [CORRECT] All tests passed!
```

**Congratulations!** You've successfully used the new development workflow.

## [LIBRARY] What You Just Learned

### Tool Overview
- **`scaffold_module.py`** - Creates compliant module structures
- **`dev_watch.py`** - Provides real-time compliance feedback
- **`test_module.py`** - Quick compliance testing
- **`pytest_compliance.py`** - Detailed test-driven validation

### Key Benefits You Experienced
1. **No manual setup** - Everything generated correctly
2. **Immediate feedback** - Saw compliance status in real-time
3. **Clear success criteria** - Knew exactly when things worked
4. **LLM-ready** - Perfect for iterative AI-assisted development

## [LIBRARY] Next Steps by Experience Level

### For Beginners
**Goal:** Learn the basic workflow

1. **Read:** [Module Scaffolding Guide](./module-scaffolding.md)
   - Understand feature options
   - Learn about different module types
   - Practice with different configurations

2. **Try:** Create 2-3 different modules
   - Simple module with just API
   - Module with database features
   - Module with UI components

3. **Practice:** [Quick Testing Guide](./quick-testing.md)
   - Learn different test commands
   - Understand test output
   - Set up development workflow

### For Experienced Developers
**Goal:** Master advanced workflows

1. **Explore:** [Pytest Compliance Testing](./pytest-compliance.md)
   - Understand test architecture
   - Learn debugging techniques
   - Integrate with existing test suites

2. **Master:** [Development Watch Mode](./dev-watch.md)
   - Configure advanced watching
   - Optimize for your workflow
   - Integrate with IDE

3. **Implement:** [Testing Strategies](./testing-strategies.md)
   - Set up comprehensive testing
   - Add performance testing
   - Create custom test patterns

### For LLM-Assisted Development
**Goal:** Optimize AI coding workflow

1. **Essential:** [LLM Development Workflow](./llm-development-workflow.md)
   - Learn iterative prompting strategies
   - Understand context management
   - Master feedback-driven development

2. **Practice:** Try this LLM workflow:
   ```
   1. Scaffold module → Start watch mode
   2. Small LLM prompt → Immediate feedback
   3. Fix issues → Continue iteration
   4. Build functionality incrementally
   ```

## [TOOLS] Common Workflows

### Daily Development Workflow
```bash
# Morning setup
python tools/dev_watch.py --module current_project

# Edit code in your IDE
# Watch terminal for real-time feedback
# Fix issues as they appear

# Before commits
python tools/test_module.py current_project
```

### New Module Creation Workflow
```bash
# 1. Generate structure
python tools/scaffold_module.py

# 2. Start feedback loop
python tools/dev_watch.py --module new_module --test

# 3. Implement iteratively
# - Edit business logic
# - Add API endpoints  
# - Build UI components
# - Watch compliance throughout

# 4. Final validation
python tools/test_module.py new_module
```

### LLM Collaboration Workflow
```bash
# 1. Start with compliant base
python tools/scaffold_module.py

# 2. Enable real-time validation
python tools/dev_watch.py --module ai_module --test

# 3. Iterative LLM prompts:
# "Add method X to services.py"
# → Save → Watch feedback → Fix issues
# "Add API endpoint for method X"  
# → Save → Watch feedback → Fix issues
# "Add UI component for feature X"
# → Save → Watch feedback → Complete!
```

## [PERFORMANCE] Power User Tips

### IDE Integration
Set up keyboard shortcuts:
- **Ctrl+Shift+T** → Run `python tools/test_module.py current_module`
- **Ctrl+Shift+W** → Start watch mode
- **Ctrl+Shift+S** → Scaffold new module

### Git Integration
Add pre-commit hook:
```bash
# .git/hooks/pre-commit
python tools/test_module.py changed_module_name
```

### Team Collaboration
Share consistent commands:
```bash
# Project Makefile
test-module:
	python tools/test_module.py $(MODULE)

watch-module:
	python tools/dev_watch.py --module $(MODULE) --test

new-module:
	python tools/scaffold_module.py
```

## [TOOLS] Troubleshooting

### Module Not Found
```bash
[INCORRECT] Module 'my_module' not found
```
**Solution:** Check module name and ensure manifest.json exists
```bash
python tools/check_module_status.py  # See available modules
```

### Tests Failing After Scaffolding
If scaffolded module fails tests, this indicates a tool bug:
```bash
# Debug with detailed output
python tools/pytest_compliance.py --module my_module
```
**Expected:** Scaffolded modules should always pass 100% of applicable tests.

### Watch Mode Not Detecting Changes
```bash
[WARNING]  Watchdog not available, using simple polling
```
**Solution:** Install watchdog for better performance
```bash
pip install watchdog
```

### Permission Errors
```bash
[ALERT] Error running tests: PermissionError
```
**Solution:** Check file permissions and ensure write access to module directories.

## [ANALYSIS] Success Metrics

After using these tools, you should see:

### Development Speed
- **New module creation:** < 5 minutes (vs hours manually)
- **Compliance achievement:** 90%+ immediately (vs 50% typical)
- **Issue resolution:** Minutes (vs hours debugging)

### Code Quality
- **Framework compliance:** Automatic validation
- **Test coverage:** Generated with module
- **Documentation:** Included in scaffolding
- **Consistency:** Follows established patterns

### Developer Experience
- **Faster iteration:** Real-time feedback
- **Clear objectives:** Tests define success
- **Reduced frustration:** Know exactly what to fix
- **Better LLM results:** Focused, incremental prompts

## [PASS] What's Next?

### Immediate Actions
1. **Create your first module** using scaffolding
2. **Try watch mode** during development
3. **Test LLM integration** with iterative prompts

### Learn More
- **Deep dive** into specific tool documentation
- **Explore** advanced testing strategies
- **Customize** tools for your workflow
- **Share** feedback and improvements

### Get Help
- **Check documentation** in this directory
- **Run diagnostic commands** for troubleshooting
- **Review example modules** for patterns
- **Ask questions** and provide feedback

---

**Ready to start?** Run `python tools/scaffold_module.py` and begin your first LLM-friendly development session!