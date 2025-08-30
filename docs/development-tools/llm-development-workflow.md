# LLM-Assisted Development Workflow

This guide covers best practices for using Large Language Models (LLMs) with the VeritasForma Framework development tools to create modules efficiently and correctly.

## [PURPOSE] Philosophy: Iterative Over "Oneshot"

### The Problem with "Oneshot" Development
When working with LLMs, it's tempting to try generating complete, working modules in a single prompt:

[INCORRECT] **Oneshot Approach Problems:**
- **Context limitations** - Complex frameworks exceed token limits
- **Hidden complexity** - Framework patterns not obvious from documentation
- **All-or-nothing** - Either everything works or nothing does
- **Difficult debugging** - Hard to isolate specific issues
- **Poor learning** - No understanding of what went wrong

[CORRECT] **Iterative Approach Benefits:**
- **Small, focused steps** - Each iteration has clear, testable goals
- **Immediate feedback** - Know instantly if changes work
- **Clear success criteria** - Tests define "done" for each step
- **Easy debugging** - Isolate issues to specific changes
- **Better results** - LLM gets precise feedback for corrections

## [LAUNCH] The Development Workflow

### Phase 1: Scaffolding (Start Compliant)
**Goal:** Generate a perfectly compliant module structure

```bash
# 1. Create module structure
python tools/scaffold_module.py

# Interactive prompts guide you through:
# - Module name and type
# - Feature selection
# - Dependency configuration
# - File generation

# Result: Fully compliant module skeleton
```

**Benefits:**
- [CORRECT] **Zero compliance issues** - Start with 100% framework compliance
- [CORRECT] **Complete structure** - All required files generated
- [CORRECT] **Working patterns** - Two-phase initialization implemented
- [CORRECT] **Test coverage** - Basic tests included

### Phase 2: Watch Mode Setup (Enable Feedback)
**Goal:** Get real-time feedback on all changes

```bash
# 2. Start development watch mode
python tools/dev_watch.py --module your_module_name --test

# This provides:
# - Real-time compliance checking
# - Automatic test execution
# - Clear progress indicators
# - Immediate failure feedback
```

**Benefits:**
- [PERFORMANCE] **Instant feedback** - See results of every change
- [PURPOSE] **Clear targets** - Know exactly what needs fixing
- [ANALYSIS] **Progress tracking** - Watch compliance score improve
- [PROCESS] **Continuous validation** - No manual test runs

### Phase 3: Iterative Development (Small Steps)
**Goal:** Build functionality incrementally with LLM assistance

#### 3.1 Business Logic Implementation
**Prompt Strategy:**
```
I have a scaffolded module with real-time compliance checking. 
The watch mode shows all compliance tests are passing.

Now I need to implement the core business logic in services.py.
The module should [specific functionality].

Current services.py has placeholder methods. Please:
1. Keep the existing initialize() method structure
2. Replace example_method() with actual business logic
3. Add 2-3 specific methods for [functionality]
4. Follow async patterns for any I/O operations

Here's the current services.py:
[paste file content]
```

**LLM Response Validation:**
- Save the changes
- Watch mode immediately shows compliance status
- Fix any issues before moving to next step

#### 3.2 API Endpoint Implementation
**Prompt Strategy:**
```
My module compliance is at 100% and core business logic is implemented.
Now I need to add API endpoints to api.py.

The watch mode currently shows API schema validation is skipped 
because no API functionality is detected.

Please add FastAPI routes to api.py that:
1. Keep existing initialize() and setup_module() functions unchanged
2. Add router with 3-4 endpoints for the business logic
3. Use proper response_model validation
4. Import from api_schemas.py

Current api.py:
[paste relevant sections]

Current api_schemas.py:
[paste file content]
```

**Expected Result:**
- Watch mode detects API functionality
- API schema validation tests activate
- Compliance score maintained or improved

#### 3.3 UI Implementation
**Prompt Strategy:**
```
Module compliance is excellent and API endpoints are working.
Need to implement the Streamlit UI in ui/ui_streamlit.py.

The UI should:
1. Keep the existing render_ui(app_context) function signature
2. Add specific UI components for [functionality]
3. Integrate with the service methods
4. Handle errors gracefully

Current ui_streamlit.py:
[paste file content]
```

### Phase 4: Testing and Validation
**Goal:** Ensure everything works together

```bash
# Run comprehensive tests
python tools/pytest_compliance.py --module your_module

# Run module-specific tests
pytest tests/modules/[type]/your_module/ -v

# Final compliance check
python tools/compliance/compliance.py validate --module your_module
```

## [PURPOSE] LLM Prompting Best Practices

### Effective Prompt Structure

#### 1. Context Setting
```
I'm developing a module for the VeritasForma Framework using:
- Module scaffolding (generates compliant structure)
- Real-time watch mode (immediate compliance feedback)  
- Pytest-based testing (clear success criteria)

Current status: [compliance score and specific issues]
```

#### 2. Specific Requirements
```
I need you to [specific task] while:
- Maintaining framework compliance (watch mode will verify)
- Following existing patterns in the generated code
- Preserving the [specific functions/structures] that are already working
```

#### 3. Constraints and Preservation
```
IMPORTANT: Do not modify:
- The initialize() function in api.py (Phase 1 initialization)
- The setup_module() function in api.py (Phase 2 initialization)  
- The service registration patterns
- The existing test structure

Only modify: [specific sections]
```

#### 4. Success Criteria
```
Success will be measured by:
- Watch mode shows compliance score maintained or improved
- Specific tests pass: [list relevant tests]
- Functionality works as expected: [specific behaviors]
```

### Incremental Prompting Strategies

#### Strategy 1: Single File Focus
```
Focus only on services.py. Do not modify any other files.

Current services.py has placeholder business logic.
Replace the example_method() with actual functionality for [specific feature].

Add these specific methods:
1. async def method_a() -> ReturnType
2. async def method_b(param: Type) -> ReturnType  
3. def helper_method() -> Type

Keep all existing infrastructure (init, cleanup, etc.) unchanged.
```

#### Strategy 2: Feature Addition
```
The module structure is complete and compliant.
Now add [specific feature] by:

1. Adding new method to services.py
2. Adding corresponding API endpoint to api.py  
3. Adding UI component to ui_streamlit.py
4. Update schemas in api_schemas.py if needed

Make minimal changes to preserve existing functionality.
```

#### Strategy 3: Issue Resolution
```
Watch mode shows compliance issue: [specific error message]

Please fix this specific issue without changing anything else.
The error suggests: [interpretation of error]

Current relevant code:
[paste only the problematic section]
```

## [TOOLS] Common LLM Development Patterns

### Pattern 1: Service-First Development
1. **Start with business logic** in services.py
2. **Add API layer** in api.py and api_schemas.py
3. **Build UI** in ui/ui_streamlit.py
4. **Test integration** end-to-end

### Pattern 2: API-First Development  
1. **Define schemas** in api_schemas.py
2. **Implement endpoints** in api.py
3. **Add business logic** in services.py to support endpoints
4. **Create UI** to consume API

### Pattern 3: UI-Driven Development
1. **Design UI** in ui/ui_streamlit.py with mock data
2. **Identify needed methods** from UI requirements
3. **Implement business logic** in services.py
4. **Add API endpoints** if external access needed

## [PERFORMANCE] Real-Time Feedback Integration

### Watching LLM Changes
```bash
# Terminal 1: Watch mode
python tools/dev_watch.py --module my_module --test

# Terminal 2: Your development/LLM interaction
# - Paste LLM code suggestions
# - Save files
# - Check Terminal 1 for immediate feedback
# - Iterate based on results
```

### Feedback Interpretation

#### Success Indicators
```
[ANALYSIS] Compliance Status:
[CORRECT] Module Structure: All required files present
[CORRECT] Two-Phase Init Phase 1: Valid Phase 1 implementation  
[CORRECT] Two-Phase Init Phase 2: Valid Phase 2 implementation
[CORRECT] Service Registration: Service and shutdown handlers registered
[CORRECT] API Schema Validation: Pydantic schemas with response models

[ANALYSIS] Score: 5/5 (100%)
[PASS] All compliance checks passed!
```
**Action:** Continue to next development step

#### Issues to Address
```
[ANALYSIS] Compliance Status:
[CORRECT] Module Structure: All required files present
[INCORRECT] Two-Phase Init Phase 1: DB operations in Phase 1: ['db_session']
[CORRECT] Service Registration: Service and shutdown handlers registered
[INCORRECT] API Schema Validation: Missing api_schemas.py

[ANALYSIS] Score: 2/4 (50%)
[TOOLS] Needs work - focus on failed checks
```
**Action:** Fix specific issues before proceeding

### LLM Correction Prompts
When watch mode shows issues:

```
The watch mode detected these compliance issues:
- [specific error 1]
- [specific error 2]

Please fix these specific issues in the code you just provided.
The errors suggest [your interpretation].

Only show me the corrected sections, not the entire file.
```

## [LIBRARY] Advanced LLM Techniques

### Context Management
**Problem:** LLM context windows are limited
**Solution:** Use focused, incremental prompts

```
# Instead of this (too much context):
"Here's my entire 500-line module, please add feature X"

# Do this (focused context):  
"Here's the specific service method that needs feature X:
[paste only relevant 20-30 lines]
Please modify just this method to add feature X"
```

### Validation-Driven Development
**Technique:** Let compliance tests guide LLM corrections

```
I'm implementing [feature] and getting this compliance error:
"[exact error message from watch mode]"

Here's the relevant code that's causing the issue:
[paste minimal problematic code]

Please fix just this code to resolve the compliance error.
```

### Progressive Enhancement
**Technique:** Build complexity gradually

```
Phase 1 Prompt: "Add basic CRUD operations to services.py"
→ Validate with watch mode
→ Fix any issues

Phase 2 Prompt: "Add API endpoints for the CRUD operations" 
→ Validate with watch mode
→ Fix any issues

Phase 3 Prompt: "Add UI components for the CRUD operations"
→ Validate with watch mode
→ Final validation
```

### Error Recovery Strategies

#### When LLM Breaks Compliance
1. **Identify exact issue** from watch mode
2. **Revert to last working state** if needed
3. **Provide minimal context** for fix
4. **Validate fix immediately**

#### When LLM Suggests Wrong Patterns
```
The compliance check failed because your suggestion:
[specific issue]

The framework requires this pattern instead:
[correct pattern from scaffolded code]

Please modify your suggestion to follow the correct framework pattern.
```

## [ANALYSIS] Success Metrics

### Development Velocity
- **Time to first working module:** < 30 minutes (vs hours manually)
- **Compliance achievement:** 90%+ (vs often < 50% manual)
- **Iteration cycles:** 5-10 focused iterations (vs 1-2 large rewrites)

### Code Quality  
- **Framework compliance:** Automatic validation
- **Test coverage:** Generated with scaffolding
- **Documentation:** Included in scaffolding
- **Consistency:** Follows established patterns

### LLM Effectiveness
- **Context efficiency:** Smaller, focused prompts work better
- **Success rate:** Higher with iterative approach
- **Learning curve:** Faster feedback improves LLM performance
- **Error recovery:** Easier to fix specific issues

## [PURPOSE] Troubleshooting Common Issues

### LLM Overwhelm
**Symptom:** LLM provides overly complex or incorrect solutions
**Solution:** 
- Use smaller, more focused prompts
- Provide specific constraints
- Show successful patterns from scaffolded code

### Compliance Regression  
**Symptom:** LLM changes break previously working compliance
**Solution:**
- Always preserve working initialization functions
- Use incremental changes
- Validate after each LLM response

### Context Loss
**Symptom:** LLM forgets framework patterns mid-conversation
**Solution:**
- Restart conversation with fresh scaffolded code
- Provide framework patterns as examples
- Use shorter conversation chains

---

**Next Steps:**
- Try the complete workflow with a simple module
- Practice incremental prompting techniques
- Experiment with different development patterns
- Move on to [Testing Strategies](./testing-strategies.md) for comprehensive testing approaches