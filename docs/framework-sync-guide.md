# Framework Sync Guide

This guide explains how to identify and sync framework changes from this development repository back to the main framework directory using GitHub.

## Quick Framework File Identification

### Core Framework Files (Always sync these)
```
modules/core/
├── database/
├── error_handler/
├── model_manager/
├── scheduler/
└── settings/
```

### Framework Infrastructure Files
```
run_ui.py
ui/streamlit_app.py
setup_db.py
app.py
core/
tools/scaffold_module.py
tools/compliance/
```

## Using GitHub to Track Framework Changes

### 1. View Changes in a Commit
```bash
# View files changed in specific commit
git show --name-only <commit-hash>

# View only core framework files changed
git show --name-only <commit-hash> | grep -E "(modules/core/|run_ui.py|ui/streamlit_app.py|setup_db.py|app.py|core/|tools/)"
```

### 2. Compare with Main Development Directory
```bash
# See what's different between this repo and main dev
git diff --name-only HEAD~1 HEAD | grep -E "(modules/core/|run_ui.py|ui/streamlit_app.py)"
```

### 3. GitHub Web Interface
- Go to commit history: `https://github.com/elevena11/semantic_analyzer_v2/commits/master`
- Click on any commit to see files changed
- Look for files in `modules/core/` or root framework files

### 4. Get Framework Changes Since Last Sync
```bash
# If you know the last synced commit
git diff --name-only <last-synced-commit> HEAD | grep -E "(modules/core/|run_ui.py|ui/streamlit_app.py|setup_db.py|app.py|core/|tools/)"

# Show actual changes
git diff <last-synced-commit> HEAD -- modules/core/
```

## Sync Process

### 1. Identify Framework Files to Sync
```bash
# From latest commit
git show --name-only HEAD | grep -E "(modules/core/|run_ui.py|ui/streamlit_app.py|setup_db.py|app.py|core/|tools/)"
```

### 2. Copy Files to Main Dev Directory
```bash
# Example for core settings
cp -r modules/core/settings/ /path/to/main/dev/modules/core/settings/

# Example for UI files
cp run_ui.py /path/to/main/dev/
cp ui/streamlit_app.py /path/to/main/dev/ui/
```

### 3. Verify Changes
```bash
# In main dev directory
git diff  # Review changes before committing
```

## Framework Change Patterns

### Always Sync These File Types:
- `modules/core/*/` - Core framework modules
- `run_ui.py` - UI entry point
- `ui/streamlit_app.py` - Main UI application
- `setup_db.py` - Database setup
- `app.py` - Main application
- `core/app_context.py` - Application context
- `tools/scaffold_module.py` - Module scaffolding
- `tools/compliance/` - Compliance tools

### Usually Don't Sync These:
- `modules/standard/*/` - Standard modules (unless framework integration)
- `data/` - Data files
- `docs/` - Documentation (unless framework docs)
- Test files in project root

### Maybe Sync These (Review First):
- `modules/standard/*/api.py` - If contains framework patterns
- `modules/standard/*/services.py` - If contains framework patterns
- `modules/standard/*/module_settings.py` - If contains framework patterns

## GitHub Integration Tips

### 1. Use GitHub's File Filter
In any commit view, add `?w=1` to URL to ignore whitespace changes.

### 2. Use GitHub's Compare View
`https://github.com/elevena11/semantic_analyzer_v2/compare/<old-commit>...<new-commit>`

### 3. Subscribe to Repository
Enable notifications for commits to stay updated on framework changes.

### 4. Use GitHub CLI (if available)
```bash
# View recent commits
gh repo view elevena11/semantic_analyzer_v2 --web

# View specific commit
gh api repos/elevena11/semantic_analyzer_v2/commits/<commit-hash>
```

## Example: Syncing Latest Changes

```bash
# 1. See what framework files changed in latest commit
git show --name-only HEAD | grep -E "(modules/core/|run_ui.py|ui/streamlit_app.py|setup_db.py|app.py|core/|tools/)"

# 2. Review the actual changes
git show HEAD -- modules/core/settings/api.py

# 3. Copy to main dev (adjust paths as needed)
cp modules/core/settings/api.py /path/to/main/dev/modules/core/settings/
cp run_ui.py /path/to/main/dev/
cp ui/streamlit_app.py /path/to/main/dev/ui/

# 4. In main dev directory, review and commit
cd /path/to/main/dev
git add .
git commit -m "Sync framework changes: settings API improvements and UI logging fixes"
```

This approach leverages GitHub's built-in tracking instead of maintaining separate documentation, making it easier to identify and sync framework changes.