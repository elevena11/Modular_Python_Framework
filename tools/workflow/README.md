# Feature Development Workflow

This directory contains the systematic feature development workflow for projects using the Modular Python Framework.

## Directory Structure

```
docs/workflow/
├── FEATURE_DEVELOPMENT_WORKFLOW.md    # Complete workflow documentation
├── README.md                          # This file
├── templates/                         # Phase templates
│   ├── SEED_TEMPLATE.md
│   ├── BRAINSTORM_TEMPLATE.md
│   ├── PLAN_TEMPLATE.md
│   └── TECHNICAL_MAP_TEMPLATE.md
├── active_features/                   # Current development
│   └── [feature_name_###]/
│       ├── 01_SEED.md
│       ├── 02_BRAINSTORM.md
│       ├── 03_PLAN.md
│       └── 04_TECHNICAL_MAP.md
└── completed_features/                # Archived completed features
    └── [feature_name]/
        ├── development_docs/
        └── final_architecture.md
```

## Quick Start

### Starting a New Feature

**Automated Initialization** (Recommended):
```bash
# Method 1: Using Python script
python init_feature.py "Feature Name" "What triggered this idea"

# Method 2: Using shell wrapper (shorter)
./new-feature "Feature Name" "What triggered this idea"
```

**Manual Setup** (Alternative):
1. **Create Feature Directory**:
   ```bash
   mkdir docs/workflow/active_features/feature_name_001
   ```

2. **Copy Templates**:
   ```bash
   cp docs/workflow/templates/SEED_TEMPLATE.md docs/workflow/active_features/feature_name_001/01_SEED.md
   ```

3. **Follow the Workflow**:
   - Fill out SEED phase
   - Move to BRAINSTORM phase
   - Continue through all phases

### Workflow Phases

1. **SEED 🌱** - Capture initial idea
2. **BRAINSTORM 🧠** - Explore possibilities
3. **PLAN 📋** - Define scope and approach
4. **MAP 🗺️** - Design technical implementation
5. **TODO 📝** - Create task list
6. **IMPLEMENT 🔨** - Write code
7. **TEST ✅** - Verify functionality
8. **DOCUMENT 📚** - Create final documentation

## Rules

- **No skipping phases** - Each phase must be completed
- **Document everything** - All decisions and reasoning must be written down
- **Quality gates** - Each phase has specific completion criteria
- **Backward movement allowed** - Can return to previous phases if needed

## Benefits

✅ Prevents feature creep and scope drift  
✅ Reduces technical debt through systematic design  
✅ Improves code quality with built-in testing  
✅ Enables better collaboration through clear documentation  
✅ Facilitates maintenance with comprehensive records  

## Examples

See completed features in the `completed_features/` directory for examples of how the workflow has been applied to real features.

## Support

For questions about the workflow or help with implementation, refer to:

- **Complete Workflow**: `FEATURE_DEVELOPMENT_WORKFLOW.md`
- **Usage Guide**: `USAGE_GUIDE.md` 
- **Initialization Script**: `init_feature.py --help`