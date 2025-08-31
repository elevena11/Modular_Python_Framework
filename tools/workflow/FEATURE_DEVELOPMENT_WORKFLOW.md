# Feature Development Workflow - "Seed to Harvest"

## Overview

This workflow ensures systematic feature development from initial idea to production-ready implementation. It prevents the chaotic "jump straight to implementation" approach that leads to half-finished features and technical debt.

## Workflow Phases

### **Phase 1: SEED 🌱**

**Purpose**: Capture the initial idea/trigger  
**Output**: Seed documentation  
**Duration**: 5-10 minutes  

**Format**:
```markdown
## SEED: [Feature Name]
**Trigger**: [What sparked this idea - user request, bug, observation, etc.]
**Initial Vision**: [Raw idea in 1-2 sentences]
**Context**: [Why now? What problem does this solve?]
**Scope Hint**: [Rough size - small/medium/large]
```

**Examples**:
- Trigger: "User mentioned they have duplicate documents"
- Trigger: "Performance bottleneck observed during large batch processing"
- Trigger: "Missing cross-reference visualization in UI"

---

### **Phase 2: BRAINSTORM 🧠**

**Purpose**: Explore possibilities, edge cases, alternatives  
**Output**: Brainstorm notes  
**Duration**: 15-30 minutes for small features, 1-2 hours for large features  

**Activities**:
- What are different ways to implement this?
- What edge cases exist?
- How does this interact with existing systems?
- What are the user stories?
- What could go wrong?
- What are the performance implications?
- What security considerations exist?

**Decision Point**: "Are we ready to commit to planning this?"

**Quality Gates**:
- ✅ Multiple implementation approaches considered
- ✅ Major edge cases identified
- ✅ Integration points with existing systems understood
- ✅ Potential risks and challenges documented

---

### **Phase 3: PLAN 📋**

**Purpose**: Define scope, approach, and requirements  
**Output**: Structured plan document  
**Duration**: 30 minutes to 2 hours depending on complexity  

**Format**:
```markdown
## PLAN: [Feature Name]
**Scope**: [Exactly what we will/won't build]
**User Stories**: [Concrete use cases]
**Technical Approach**: [High-level architecture decisions]
**Dependencies**: [What needs to exist first]
**Assumptions**: [What we're assuming is true]
**Success Criteria**: [How we know it's done]
**Non-Goals**: [What we explicitly won't do]
**Risks**: [What could go wrong and mitigation strategies]
```

**Quality Gates**:
- ✅ Clear scope boundaries defined
- ✅ User stories are concrete and testable
- ✅ Technical approach is feasible
- ✅ Dependencies are identified and available
- ✅ Success criteria are measurable

---

### **Phase 4: MAP 🗺️**

**Purpose**: Break down into concrete functions and components  
**Output**: Technical specification  
**Duration**: 30 minutes to 3 hours depending on complexity  

**Activities**:
- Map out all functions/classes needed
- Define APIs and interfaces
- Identify data flows
- Plan integration points
- Design database schema changes (if needed)
- Plan testing strategy

**Format**:
```markdown
## TECHNICAL MAP: [Feature Name]
**Components**: [List of classes/modules to create/modify]
**Functions**: [Key functions with signatures]
**Data Flow**: [How data moves through the system]
**Integration Points**: [Where this touches existing code]
**Database Changes**: [Schema modifications needed]
**API Endpoints**: [New or modified endpoints]
**Testing Strategy**: [How we'll verify it works]
```

**Quality Gates**:
- ✅ All required components identified
- ✅ Function signatures defined
- ✅ Data flow is clear and logical
- ✅ Integration points are well-defined
- ✅ Testing approach is planned

---

### **Phase 5: TODO 📝**

**Purpose**: Create concrete implementation tasks  
**Output**: Prioritized task list using TodoWrite tool  
**Duration**: 15-30 minutes  

**Task Format**:
- **Specific**: "Implement fuzzy filename matching function"
- **Actionable**: "Add duplicate detection API endpoint"
- **Testable**: "Create unit tests for similarity calculation"
- **Prioritized**: High/Medium/Low based on dependencies

**Use TodoWrite tool** to track implementation tasks:
```python
TodoWrite([
    {"content": "Create DuplicateDetector class", "status": "pending", "priority": "high"},
    {"content": "Implement calculate_similarity_score function", "status": "pending", "priority": "high"},
    {"content": "Add /duplicates API endpoint", "status": "pending", "priority": "medium"},
    {"content": "Create unit tests for duplicate detection", "status": "pending", "priority": "medium"},
    {"content": "Add CLI command for deduplication", "status": "pending", "priority": "low"}
])
```

**Quality Gates**:
- ✅ Tasks are specific and actionable
- ✅ Dependencies between tasks are clear
- ✅ Each task is small enough to complete in one session
- ✅ Testing tasks are included

---

### **Phase 6: IMPLEMENT 🔨**

**Purpose**: Write the actual code  
**Duration**: Variable based on feature complexity  

**Rules**:
- Follow the plan (if we deviate, update the plan)
- Implement one component at a time
- Test each component as we build it
- Update TODO list progress in real-time
- No shortcuts that compromise the plan

**Implementation Guidelines**:
- Start with core components
- Build incrementally
- Test as you go
- Document any deviations from the plan
- Keep the TODO list updated

**Quality Gates**:
- ✅ Code follows existing patterns and conventions
- ✅ All planned components are implemented
- ✅ Unit tests pass for implemented components
- ✅ No obvious bugs or regressions
- ✅ TODO list is kept up to date

---

### **Phase 7: TEST ✅**

**Purpose**: Verify the feature works end-to-end  
**Duration**: 20-30% of implementation time  

**Testing Activities**:
- Unit test individual components
- Integration test full workflow
- Test edge cases identified in brainstorm
- Performance test if relevant
- Security test if relevant
- User acceptance test against success criteria

**Testing Types**:
- **Unit Tests**: Individual function/class testing
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Full workflow testing
- **Performance Tests**: Load and stress testing
- **Edge Case Tests**: Boundary condition testing

**Quality Gates**:
- ✅ All unit tests pass
- ✅ Integration tests demonstrate feature works
- ✅ Edge cases are handled correctly
- ✅ Performance meets requirements
- ✅ Success criteria from plan are met

---

### **Phase 8: DOCUMENT 📚**

**Purpose**: Document the final implementation  
**Output**: Architecture documentation  
**Duration**: 15-20% of total feature time  

**Documentation Requirements**:
- How it works (architecture overview)
- How to use it (user guide)
- How to monitor it (metrics and logging)
- How to maintain it (troubleshooting guide)
- API documentation (if applicable)
- Configuration options

**Documentation Format**:
```markdown
# [Feature Name] Architecture Documentation

## Overview
[What the feature does and why it exists]

## Architecture
[How it works technically]

## Usage
[How users interact with it]

## Monitoring
[How to monitor and troubleshoot]

## Configuration
[Available settings and options]

## Performance Considerations
[Performance characteristics and optimization]
```

**Quality Gates**:
- ✅ Architecture is clearly explained
- ✅ Usage examples are provided
- ✅ Monitoring guidance is included
- ✅ Configuration options are documented
- ✅ Performance characteristics are described

---

## Workflow Rules & Guidelines

### **🚫 No Jumping Phases**
- Can't skip brainstorm and go straight to planning
- Can't start coding without a complete technical map
- Can't call something "done" without proper testing
- Each phase must produce its documented output

### **🔄 Backward Movement Allowed**
- If during planning we realize we need more brainstorming, go back
- If during implementation we discover plan flaws, update the plan
- If during testing we find architecture issues, fix the design
- But always be explicit about going backward and why

### **📋 Documentation Requirement**
- Every phase must produce its documented output
- Documents live in the project for future reference
- No "mental notes" - everything written down
- Documentation is part of the deliverable, not an afterthought

### **⏱️ Time Investment Guidelines**

**Small Features (1-2 days)**:
- 20% planning (Seed → Map)
- 60% implementation
- 20% testing/documentation

**Medium Features (3-7 days)**:
- 30% planning (Seed → Map)
- 50% implementation
- 20% testing/documentation

**Large Features (1-3 weeks)**:
- 40% planning (Seed → Map)
- 40% implementation
- 20% testing/documentation

### **🎯 Quality Standards**

**Code Quality**:
- Follow existing project patterns
- Include proper error handling
- Add appropriate logging
- Write maintainable code

**Documentation Quality**:
- Clear and concise
- Includes examples
- Covers edge cases
- Explains architectural decisions

**Testing Quality**:
- Comprehensive test coverage
- Edge cases are tested
- Performance is validated
- Integration is verified

---

## File Organization

### **Feature Development Directory Structure**
```
docs/workflow/
├── FEATURE_DEVELOPMENT_WORKFLOW.md    # This file
├── templates/                          # Phase templates
│   ├── SEED_TEMPLATE.md
│   ├── PLAN_TEMPLATE.md
│   └── TECHNICAL_MAP_TEMPLATE.md
├── active_features/                    # Current development
│   ├── feature_name_001/
│   │   ├── 01_SEED.md
│   │   ├── 02_BRAINSTORM.md
│   │   ├── 03_PLAN.md
│   │   └── 04_TECHNICAL_MAP.md
│   └── feature_name_002/
└── completed_features/                 # Archived completed features
    └── [feature_name]/
        ├── development_docs/
        └── final_architecture.md
```

### **Naming Conventions**
- Feature directories: `feature_name_###` (e.g., `smart_deduplication_001`)
- Phase files: `##_PHASE_NAME.md` (e.g., `01_SEED.md`)
- Keep names short but descriptive
- Use underscores for spaces

---

## Example Workflow Application

### **SEED 🌱**
```markdown
## SEED: Smart Document Deduplication
**Trigger**: User mentioned they have duplicate documents in their VEF collection
**Initial Vision**: Automatically detect and flag documents that are near-duplicates
**Context**: Large document collections often have duplicates that waste analysis time
**Scope Hint**: Medium - needs embedding comparison and fuzzy matching
```

### **BRAINSTORM 🧠** 
**Questions Explored**:
- How do we define "duplicate"? Exact text match? Semantic similarity? Filename similarity?
- Should we auto-delete or just flag for review?
- What about different file formats with same content?
- How do we handle legitimate similar documents (like series parts)?
- Should this run during analysis or as separate tool?
- Performance implications for large collections?

**Decision**: Ready to plan - let's build a detection and flagging system

### **PLAN 📋**
```markdown
## PLAN: Smart Document Deduplication  
**Scope**: Detect near-duplicate documents using multiple signals (content, filename, metadata)
**User Stories**: 
- As an analyst, I want to see which documents might be duplicates
- As a user, I want to review flagged duplicates before deletion
**Technical Approach**: Combine semantic similarity, fuzzy filename matching, and content hashing
**Dependencies**: Existing embedding system, database storage
**Success Criteria**: Can detect 90%+ of obvious duplicates with <5% false positives
```

### **MAP 🗺️**
```markdown
## TECHNICAL MAP: Smart Document Deduplication
**Components**:
- DuplicateDetector class
- SimilarityCalculator class  
- DeduplicationReport class

**Functions**:
- detect_duplicates(documents) -> List[DuplicateGroup]
- calculate_similarity_score(doc1, doc2) -> float
- generate_dedup_report() -> DeduplicationReport

**Data Flow**: Documents → Embedding comparison → Filename fuzzy match → Combined scoring → Duplicate groups
**Integration Points**: Database queries, existing embedding system, new API endpoint
```

---

## Enforcement and Accountability

### **Phase Gate Reviews**
- Each phase must be reviewed and approved before moving to next
- Review criteria are the quality gates listed in each phase
- If quality gates aren't met, stay in current phase

### **Documentation Artifacts**
- All phase documents must be committed to version control
- No verbal agreements or "mental notes"
- Documentation is part of the feature, not separate

### **Retrospective Process**
- After each completed feature, review what worked and what didn't
- Update this workflow based on lessons learned
- Track metrics on planning accuracy and time estimates

---

## Benefits of This Workflow

✅ **Prevents Feature Creep**: Clear scope definition in planning phase  
✅ **Reduces Technical Debt**: Systematic design before implementation  
✅ **Improves Quality**: Built-in testing and documentation requirements  
✅ **Enables Collaboration**: Clear handoff points and documentation  
✅ **Facilitates Maintenance**: Comprehensive documentation of decisions  
✅ **Builds Institutional Knowledge**: Preserved reasoning and context  

This workflow ensures that features are built thoughtfully, thoroughly, and maintainably.