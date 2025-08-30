# Framework Separation Architecture Plan

## Current Situation

The Reality Anchor Hub (RAH) repository contains both:
- **Generic Modular Python Framework** (reusable across projects)
- **RAH-specific application code** (truth verification modules)

This creates problems:
- Framework improvements happen in RAH repo, hard to reuse elsewhere
- No clean way to update framework across multiple projects
- Core framework development mixed with application development

## Vision: Clean Framework Distribution

### Core Framework Repository Structure
**Repository Name**: `python-modular-framework` (or similar clean name)

```
python-modular-framework/
├── core/                        # Framework engine
│   ├── __init__.py
│   ├── app_context.py          # Application context management
│   ├── bootstrap.py            # Database bootstrap logic
│   ├── database.py             # Database base classes
│   ├── decorators.py           # Decorator system
│   ├── error_utils.py          # Error handling utilities
│   ├── logging.py              # Framework logging
│   ├── module_base.py          # Base module classes
│   ├── module_manager.py       # Module discovery and loading
│   ├── module_processor.py     # Module registration processing
│   └── paths.py                # Path management utilities
├── modules/core/               # Essential framework modules
│   ├── database/               # Database management module
│   ├── error_handler/          # Error registry and handling
│   ├── framework/              # Framework lifecycle management
│   ├── model_manager/          # ML model management (if needed)
│   └── settings/               # Pydantic settings system
├── tools/                      # Development and maintenance tools
│   ├── compliance/             # Compliance checking system
│   ├── scaffold_module.py      # Module scaffolding tool
│   └── clear_logs.py          # Log management utilities
├── docs/                       # Framework documentation
│   ├── architecture/           # Architecture documentation
│   ├── development-tools/      # Tool documentation
│   └── examples/              # Usage examples
├── examples/                   # Reference implementations
│   └── sample_modules/        # Example modules for learning
├── app.py                      # Framework entry point
├── run_ui.py                  # Optional UI runner (if applicable)
├── setup_db.py               # Database initialization
├── update_core.py             # Framework update utility
├── framework_version.json     # Version tracking metadata
├── requirements.txt           # Framework dependencies
├── CLAUDE.md                  # Framework usage instructions
└── README.md                  # Getting started guide
```

### User Project Repository Structure
**Example**: `my-awesome-app`, `reality-anchor-hub`, `data-processing-pipeline`

```
my-awesome-app/
├── framework/                  # Downloaded framework (gitignored)
│   ├── core/
│   ├── modules/core/
│   ├── tools/
│   ├── app.py
│   └── ...
├── modules/standard/          # User's application modules
│   ├── my_feature/
│   ├── data_processor/
│   └── custom_analytics/
├── modules/custom/            # Project-specific modules (optional)
│   └── specialized_module/
├── data/                      # Project data (gitignored)
├── config/                    # Project-specific configuration
├── .framework_version         # Tracks current framework version
├── .gitignore                # Includes framework/ directory
├── app.py -> framework/app.py # Symlink to framework entry point
├── requirements.txt           # Project-specific dependencies
├── CLAUDE.md                 # Project-specific instructions
└── README.md                 # Project documentation
```

## Implementation Plan

### Phase 1: Framework Repository Creation
1. **Extract Clean Framework**
   - Copy core framework files from RAH
   - Remove RAH-specific modules and dependencies
   - Create clean directory structure
   - Add framework_version.json with initial version

2. **Framework Version Tracking**
   ```json
   {
     "version": "1.0.0",
     "commit": "abc123def456",
     "release_date": "2025-08-30",
     "breaking_changes": false,
     "changelog": "Initial framework extraction from Reality Anchor Hub",
     "required_python": ">=3.8",
     "dependencies": ["fastapi", "pydantic", "sqlalchemy", "uvicorn"]
   }
   ```

3. **Documentation**
   - Framework usage guide
   - Module development tutorial
   - API reference
   - Migration guide from embedded framework

### Phase 2: Update System Implementation

#### Core Update Utility (`update_core.py`)
```python
class FrameworkUpdater:
    def check_updates(self):
        """Check remote version vs local version"""
        
    def show_changelog(self, from_version, to_version):
        """Display changes and breaking change warnings"""
        
    def confirm_update(self):
        """Ask user confirmation with warnings"""
        
    def backup_current(self):
        """Backup current framework version"""
        
    def download_framework(self, version):
        """Download and extract new framework"""
        
    def update_version_file(self, version_info):
        """Update local .framework_version"""
```

#### Workflow:
1. Run `python update_core.py`
2. Check current version in `.framework_version`
3. Fetch latest version from GitHub releases
4. Show changelog and breaking changes
5. Ask user: "Update from v1.2.0 to v1.3.0? (y/n)"
6. If yes: backup, download, extract, update version file
7. If breaking changes: warn about module compatibility

### Phase 3: Project Migration
1. **RAH Project Conversion**
   - Move RAH-specific modules to `modules/standard/`
   - Set up framework/ directory structure
   - Create `.framework_version` file
   - Update CLAUDE.md for RAH-specific instructions

2. **Template Creation**
   - Create project template repository
   - Include basic project structure
   - Pre-configured .gitignore
   - Sample modules for reference

### Phase 4: Distribution Strategy

#### Option A: GitHub Releases (Recommended)
- Framework tagged releases (v1.0.0, v1.1.0, etc.)
- Release assets include framework.zip
- update_core.py downloads from releases
- Simple, no authentication needed

#### Option B: Git Subtree/Submodule
- Framework as git submodule
- More complex but better version control integration
- Requires git knowledge from users

#### Option C: Package Distribution (Future)
- pip-installable framework package
- Standard Python package management
- More complex initial setup

## Benefits

### For Framework Development
- **Clean separation** of framework vs application concerns
- **Focused development** on framework core without RAH noise
- **Better testing** with framework-only test suites
- **Documentation clarity** for framework users

### For Project Development
- **Easy framework updates** without losing project work
- **Version control** - can stay on older framework if needed
- **Project focus** - work on features, not framework bugs
- **Reusability** - same framework for multiple projects

### For Users
- **Simple onboarding** - download template, start building
- **Upgrade safety** - backup and rollback capabilities
- **Clear separation** - framework vs application code
- **Community potential** - others can use and contribute

## Next Steps

1. **Create framework repository** on GitHub
2. **Extract clean framework** from current RAH codebase
3. **Implement update_core.py** utility
4. **Test with RAH conversion** as proof of concept
5. **Document and template** for future projects

## Technical Considerations

### Version Compatibility
- Semantic versioning (major.minor.patch)
- Breaking changes only in major versions
- Clear migration guides for breaking changes
- Deprecation warnings before removal

### Security
- Verify framework downloads (checksums)
- No automatic updates - always user confirmation
- Backup before updates
- Clear rollback procedures

### Maintenance
- Framework changelog maintenance
- Compatibility testing across Python versions
- Documentation updates with each release
- Community feedback integration

---

**Status**: Planning Phase
**Priority**: High - This architectural change will significantly improve development workflow
**Owner**: Framework Development Team