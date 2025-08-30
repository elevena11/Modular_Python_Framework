# Framework Updates

The Modular Python Framework includes an automated update system that allows projects to easily update their core framework while preserving application-specific modules and data.

## Quick Start

```bash
# Check for framework updates
python tools/update_core.py

# Check only (don't update)
python tools/update_core.py --check-only

# Force update without prompts
python tools/update_core.py --force

# Create backup only
python tools/update_core.py --backup-only
```

## How It Works

The update system:

1. **Tracks Versions** - Uses `.framework_version` file to track current version
2. **Checks GitHub Releases** - Connects to GitHub API to check latest release
3. **Shows Changes** - Displays changelog and breaking change warnings
4. **Creates Backups** - Automatically backs up current framework before updating
5. **Safe Updates** - Only updates core framework files, preserves your modules

## What Gets Updated

The updater only touches these framework files:
- `core/` - Framework engine
- `modules/core/` - Essential framework modules
- `tools/` - Development tools
- `app.py` - Main entry point
- `setup_db.py` - Database setup
- `requirements.txt` - Framework dependencies
- `framework_version.json` - Version metadata

## What Stays Safe

Your application code is never touched:
- `modules/standard/` - Your application modules
- `data/` - Application data and databases
- `work/` - Development workspace
- `.env` - Environment configuration
- Custom files and directories

## Version Tracking

Each project maintains a `.framework_version` file:

```json
{
  "version": "1.0.0",
  "commit": "",
  "installed_date": "2025-08-30T22:30:00",
  "source": "github_release",
  "project_name": "MyProject"
}
```

## Backups

Before each update, the system creates a backup in `.framework_backups/`:

```
.framework_backups/
└── framework_v1.0.0_20250830_223000/
    ├── core/
    ├── modules/core/
    ├── tools/
    ├── app.py
    ├── setup_db.py
    └── .framework_version
```

## Breaking Changes

The update system warns about major version changes:

- **Major version change** (1.x.x → 2.x.x): May contain breaking changes
- **Minor version change** (1.0.x → 1.1.x): New features, backward compatible  
- **Patch version change** (1.0.0 → 1.0.1): Bug fixes, fully compatible

## Rollback

To rollback after an update:

1. Stop your application
2. Copy files from `.framework_backups/framework_vX.X.X_timestamp/`
3. Restore `.framework_version` file
4. Restart application

## Setting Up Updates for Your Project

When creating a new project from the framework:

1. **Copy framework files** to your project directory
2. **Create `.framework_version`** file with current version
3. **Install dependencies**: `pip install -r requirements.txt`
4. **Test update system**: `python tools/update_core.py --check-only`

## Example Workflow

```bash
# Starting a new project
git clone https://github.com/elevena11/Modular_Python_Framework.git MyProject
cd MyProject

# Set up for your project
python tools/scaffold_module.py --name my_app --type standard

# Later, check for framework updates
python tools/update_core.py
# Output: "New framework version available v1.0.0 → v1.1.0"
# Follow prompts to update

# Continue developing with updated framework
python app.py
```

## Troubleshooting

### "Unable to check remote version"
- Check internet connection
- Verify GitHub repository is accessible
- Check if GitHub API rate limits are exceeded

### "Framework update failed"
- Check disk space for backup and download
- Verify write permissions in project directory
- Try running with administrator/sudo privileges

### "Version comparison failed"
- Check `.framework_version` file format
- Delete file and run `--force` to recreate

## Advanced Usage

### Custom Repository
To update from a fork or custom repository, modify `tools/update_core.py`:

```python
self.repo_owner = "your-github-username"
self.repo_name = "your-framework-fork"
```

### Offline Updates
For air-gapped environments:
1. Download release zip from GitHub
2. Extract manually over framework files
3. Update `.framework_version` manually

### Automated Updates
For CI/CD pipelines:

```bash
# Check and update in scripts
python tools/update_core.py --force
if [ $? -eq 0 ]; then
    echo "Framework updated successfully"
else
    echo "Framework update failed"
    exit 1
fi
```