# Feature Development Workflow - Usage Guide

## Quick Start

### Initialize a New Feature

```bash
# Method 1: Using Python script directly
python init_feature.py "Feature Name" "What triggered this idea"

# Method 2: Using shell wrapper (shorter)
./new-feature "Feature Name" "What triggered this idea"
```

### Examples

```bash
# Initialize a document deduplication feature
./new-feature "Smart Document Deduplication" "User mentioned they have duplicate documents"

# Initialize a visualization feature  
./new-feature "Cross-Reference Visualization" "Need interactive graph view of document relationships"

# Initialize a performance improvement
./new-feature "Batch Processing Optimization" "Analysis is too slow for large document collections"
```

## What Gets Created

When you run the initialization script, it creates:

```
docs/workflow/active_features/feature_name_001/
├── README.md                 # Feature overview and progress tracking
├── 01_SEED.md               # Pre-filled with your trigger
├── 02_BRAINSTORM.md         # Template for exploration phase
├── 03_PLAN.md               # Template for planning phase
└── 04_TECHNICAL_MAP.md      # Template for technical design
```

## Development Workflow

### 1. Complete the SEED Phase

Edit `01_SEED.md` to fill in the remaining sections:

```markdown
**Initial Vision**: [Raw idea in 1-2 sentences]
**Context**: [Why now? What problem does this solve?]
**Scope Hint**: [Rough size - small/medium/large]

## Background
[Any additional context, related issues, or background information]

## Initial Thoughts
[Any immediate thoughts about approach, challenges, or opportunities]
```

### 2. Move to BRAINSTORM Phase

Edit `02_BRAINSTORM.md` to explore:
- Different implementation approaches
- Edge cases and challenges
- System integration points
- Performance considerations
- Security implications

### 3. Create the PLAN

Edit `03_PLAN.md` to define:
- Exact scope (what will/won't be built)
- User stories
- Technical approach
- Dependencies and assumptions
- Success criteria

### 4. Design the Technical MAP

Edit `04_TECHNICAL_MAP.md` to specify:
- Components and functions needed
- Data flow and integration points
- Database changes
- API endpoints
- Testing strategy

### 5. Create Implementation TODO

Use the TodoWrite tool to create concrete tasks:

```python
TodoWrite([
    {"content": "Create core component class", "status": "pending", "priority": "high"},
    {"content": "Implement main processing function", "status": "pending", "priority": "high"},
    {"content": "Add API endpoint", "status": "pending", "priority": "medium"},
    {"content": "Create unit tests", "status": "pending", "priority": "medium"},
    {"content": "Add CLI command", "status": "pending", "priority": "low"}
])
```

### 6. Implement, Test, Document

Follow the standard development process:
- Implement components one at a time
- Test each component as you build
- Update TODO progress in real-time
- Document the final architecture

## Management Commands

### List Active Features

```bash
# Show all features currently in development
python init_feature.py --list
./new-feature --list
```

### Custom Author

```bash
# Set custom author name
python init_feature.py "Feature Name" "Trigger" --author "Your Name"
```

### Custom Workflow Directory

```bash
# Use different workflow directory
python init_feature.py "Feature Name" "Trigger" --workflow-dir /path/to/workflow
```

## Best Practices

### Feature Naming

✅ **Good Names**:
- "Smart Document Deduplication" 
- "Cross-Reference Visualization"
- "Batch Processing Optimization"
- "Real-time Progress Tracking"

❌ **Avoid**:
- "Fix bug" (too vague)
- "Make it faster" (not specific)
- "Add stuff" (meaningless)

### Trigger Descriptions

✅ **Good Triggers**:
- "User mentioned they have duplicate documents in their VEF collection"
- "Performance bottleneck observed during large batch processing"
- "Missing cross-reference visualization makes analysis difficult"

❌ **Avoid**:
- "We need this" (no context)
- "It would be nice" (no urgency)
- "Bug" (use bug tracker, not feature workflow)

### Directory Organization

- **Keep active features clean** - Move completed features to `completed_features/`
- **One feature per directory** - Don't mix multiple features
- **Use descriptive names** - Make it easy to find features later

## Feature Lifecycle

### Active Development

Features stay in `active_features/` while being developed:

```
active_features/
├── smart_deduplication_001/     # Currently in BRAINSTORM
├── visualization_enhancement_001/ # Currently in PLAN  
└── performance_optimization_001/  # Currently in IMPLEMENT
```

### Completion

When a feature is complete, move it to `completed_features/`:

```bash
# Move completed feature
mv active_features/smart_deduplication_001 completed_features/
```

### Archival Structure

```
completed_features/
└── smart_deduplication/
    ├── development_docs/        # All phase documents
    │   ├── 01_SEED.md
    │   ├── 02_BRAINSTORM.md
    │   ├── 03_PLAN.md
    │   └── 04_TECHNICAL_MAP.md
    ├── final_architecture.md    # Complete technical documentation
    └── README.md               # Feature summary and lessons learned
```

## Troubleshooting

### "Template not found" Error

Make sure you're running the script from the correct directory:

```bash
cd docs/workflow
python init_feature.py "Feature Name" "Trigger"
```

### Permission Denied

Make sure the script is executable:

```bash
chmod +x init_feature.py
chmod +x new-feature
```

### Feature Already Exists

The script automatically increments numbers:
- First feature: `smart_deduplication_001/`
- Second feature: `smart_deduplication_002/`

### Missing Templates

Ensure all templates exist in the `templates/` directory:

```
templates/
├── SEED_TEMPLATE.md
├── BRAINSTORM_TEMPLATE.md  
├── PLAN_TEMPLATE.md
└── TECHNICAL_MAP_TEMPLATE.md
```

## Integration with TodoWrite

The workflow integrates with the TodoWrite tool for task management:

```python
# After completing TECHNICAL_MAP phase
TodoWrite([
    {"content": "Create DuplicateDetector class", "status": "pending", "priority": "high"},
    {"content": "Implement calculate_similarity function", "status": "pending", "priority": "high"},
    {"content": "Add /duplicates API endpoint", "status": "pending", "priority": "medium"},
    {"content": "Create unit tests", "status": "pending", "priority": "medium"},
    {"content": "Add CLI command", "status": "pending", "priority": "low"}
])
```

Update progress as you implement:

```python
# Mark tasks as completed
TodoWrite([
    {"content": "Create DuplicateDetector class", "status": "completed", "priority": "high"},
    {"content": "Implement calculate_similarity function", "status": "in_progress", "priority": "high"},
    # ... rest of tasks
])
```

## Examples

### Complete Example: Smart Document Deduplication

```bash
# 1. Initialize feature
./new-feature "Smart Document Deduplication" "User mentioned they have duplicate documents"

# 2. Edit 01_SEED.md to complete SEED phase
# 3. Edit 02_BRAINSTORM.md to explore approaches
# 4. Edit 03_PLAN.md to define scope
# 5. Edit 04_TECHNICAL_MAP.md to design implementation

# 6. Create TODO list
# Use TodoWrite tool to create implementation tasks

# 7. Implement following the plan
# 8. Test thoroughly
# 9. Document final architecture
# 10. Move to completed_features/
```

This systematic approach ensures features are built thoughtfully and maintainably!