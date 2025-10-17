# Framework Updates

This guide explains how to keep your Modular Python Framework installation up to date.

## Table of Contents

- [Quick Start](#quick-start)
- [Update Commands](#update-commands)
- [Backup and Rollback](#backup-and-rollback)
- [How Updates Work](#how-updates-work)
- [Troubleshooting](#troubleshooting)

## Quick Start

Check for and apply framework updates:

```bash
# Check if updates are available
python update_core.py --check

# Apply updates (interactive)
python update_core.py

# Apply updates without prompts
python update_core.py --force
```

The update system automatically:
- Creates a backup before updating
- Only updates framework files (preserves your modules and data)
- Respects your .gitignore (never touches .env, data/, etc.)
- Handles removed framework files safely

## Update Commands

### Check for Updates

Check if a new framework version is available without making any changes:

```bash
python update_core.py --check
```

Output:
```
Checking for updates...
Current version: 1.0.6
Latest version:  1.0.7

New version available: v1.0.6 -> v1.0.7

Release Notes:
--------------------------------------------------
- Complete rewrite of update system
- Enhanced model_manager with parallel GPU support
- Improved error handling
--------------------------------------------------
```

### Preview Changes (Dry Run)

See what files would be updated without actually applying changes:

```bash
python update_core.py --dry-run
```

Output:
```
Update Summary:
  Files to add:    3
  Files to update: 12
  Files to remove: 2 (moved to backup)

Files to add:
  + core/new_feature.py
  + tools/new_tool.py
  ...

Files to update:
  ~ app.py
  ~ core/config.py
  ...

Files to remove (moved to backup):
  - docs/core/old_file.md
  ...

Run without --dry-run to apply these changes
```

### Apply Updates

Apply framework updates interactively (will ask for confirmation):

```bash
python update_core.py
```

Apply without confirmation prompts:

```bash
python update_core.py --force
```

The update process:
1. Downloads the latest framework version
2. Shows you what will change
3. Creates a backup of your current framework
4. Updates framework files
5. Moves orphaned files to backup (not deleted)
6. Updates version tracking

After update completes, restart your application:
```bash
python app.py
```

### Show Version Information

Display your current framework version and installation details:

```bash
python update_core.py --version
```

Output:
```
Framework Version: 1.0.6
Source: github_release
Installed: 2025-09-29T15:40:43
Updated: 2025-10-17T14:18:53
```

## Backup and Rollback

### Create Backup

Create a backup of your current framework without updating:

```bash
python update_core.py --backup
```

This creates a backup in `.framework_backups/` with the current version and timestamp.

### List Backups

See all available backups:

```bash
python update_core.py --list-backups
```

Output:
```
Available backups:
------------------------------------------------------------
v1.0.6 - 20251017_145558
  framework_v1.0.6_20251017_145558

v1.0.5 - 20251015_120000
  framework_v1.0.5_20251015_120000
```

### Rollback (Interactive)

Rollback to a previous version with interactive selection:

```bash
python update_core.py --rollback
```

You'll see a list of backups and can choose which one to restore.

### Rollback to Specific Version

Rollback directly to a specific version:

```bash
python update_core.py --rollback v1.0.5
```

The rollback process:
1. Shows you what will be restored
2. Creates a safety backup of your current state
3. Restores files from the selected backup
4. Restores orphaned files (if any)
5. Preserves files that were added in newer versions (safe)

After rollback completes, restart your application.

## How Updates Work

### What Gets Updated

The framework update system only updates framework-owned files:

**Framework-Owned (updated):**
- `core/` - Framework core engine
- `modules/core/` - Framework core modules
- `tools/` - Development tools
- `ui/` - UI components
- `docs/core/` - Framework documentation
- Root files: `app.py`, `setup_db.py`, `update_core.py`, etc.

**User Space (never touched):**
- `.env` - Your environment configuration
- `data/` - Your data directory
- `modules/standard/` - Your custom modules
- `docs/` (root) - Your project documentation
- Any files in `.gitignore`

### Manifest-Driven Updates

The framework uses `framework_manifest.json` to track which files belong to the framework. This ensures:
- Only framework files are updated
- User files are never modified
- No hardcoded file lists (uses manifest as single source of truth)

### Atomic Backup-Then-Overwrite

When updating a file, the system:
1. Backs up the existing file
2. Overwrites with the new version

This happens in a single operation to prevent sync issues. You cannot overwrite without backing up first.

### Orphaned Files

When framework files are removed from a new version:
- Files in framework-owned paths are moved to backup
- Root and `docs/` root files are left alone (might be user content)
- Nothing is permanently deleted

Example: If `docs/core/old_architecture.md` is removed from the framework, it gets moved to `.framework_backups/.../orphaned_files/docs/core/old_architecture.md`

### Backup Structure

Backups are stored in `.framework_backups/` with this structure:

```
.framework_backups/
  framework_v1.0.5_20251017_143022/
    updated_files/          # Files that were overwritten
      core/
      modules/
      ...
    orphaned_files/         # Files removed from manifest
      docs/core/old_file.md
    .rollback_info.json     # Rollback metadata
    .framework_version      # Original version file
```

The `.rollback_info.json` contains:
```json
{
  "original_version": "1.0.5",
  "target_version": "1.0.6",
  "backup_timestamp": "2025-10-17T14:30:22",
  "updated_files": ["core/config.py", "app.py"],
  "added_files": ["core/new_feature.py"],
  "orphaned_files": ["docs/core/old_file.md"]
}
```

## Troubleshooting

### Update Fails to Download

If you see "Error: Failed to download release":

1. Check your internet connection
2. Verify you can access GitHub: `curl -I https://api.github.com`
3. Check GitHub API rate limit: `curl https://api.github.com/rate_limit`

### Files Not Updating

If specific files don't update:

1. Check if file is in `.gitignore` (intentionally skipped)
2. Look for warnings in update output
3. Check file permissions
4. Review the backup to see what was captured

### Rollback Not Working

If rollback fails:

1. Check that the backup exists: `python update_core.py --list-backups`
2. Verify `.rollback_info.json` exists in the backup directory
3. Check file permissions in backup directory

### Major Version Changes

When updating across major versions (e.g., 1.x → 2.x):

- The system warns you about potential breaking changes
- Review the release notes carefully
- Consider testing in a development environment first
- Create a manual backup of your entire project before updating

### Recovery from Failed Update

If an update fails partway through:

1. Check the latest backup: `python update_core.py --list-backups`
2. Rollback to the backup: `python update_core.py --rollback`
3. Report the issue with error details

The system creates safety backups, so you should always be able to recover.

## Best Practices

### Before Updating

1. **Commit your changes**: Make sure your work is committed to git
2. **Check release notes**: Review what's changing
3. **Use dry-run first**: See what will change before applying
4. **Consider testing**: If you have a test environment, update there first

### After Updating

1. **Restart application**: The update doesn't restart services automatically
2. **Test functionality**: Verify your application still works
3. **Check logs**: Look for any new warnings or errors
4. **Keep backups**: Old backups can be deleted manually when no longer needed

### Regular Maintenance

- Check for updates weekly: `python update_core.py --check`
- Clean old backups periodically (manually delete from `.framework_backups/`)
- Keep at least one backup of each major version
- Document any customizations you make to framework files

## Version Compatibility

The framework uses semantic versioning:

- **Major version** (1.x.x → 2.x.x): Breaking changes, may require code updates
- **Minor version** (x.1.x → x.2.x): New features, backward compatible
- **Patch version** (x.x.1 → x.x.2): Bug fixes, backward compatible

The update system works across all version changes but warns you about major version upgrades.

## Advanced Usage

### Custom Project Root

Update framework in a different directory:

```bash
python update_core.py --project-root /path/to/project
```

### Automated Updates (CI/CD)

For automated environments:

```bash
# Check and apply updates without prompts
python update_core.py --force

# Or just check (exit code 1 if update available)
if python update_core.py --check; then
    echo "Framework is up to date"
else
    echo "Update available"
fi
```

### Manual Backup Before Major Changes

Before making major changes to your project:

```bash
python update_core.py --backup
```

This creates a restore point you can rollback to if needed.

## Getting Help

If you encounter issues:

1. Check this documentation
2. Review the [framework repository](https://github.com/elevena11/Modular_Python_Framework)
3. Create an issue with:
   - Current version (`python update_core.py --version`)
   - Error messages
   - Steps to reproduce

## Summary of Commands

```bash
# Check for updates
python update_core.py --check

# Preview changes
python update_core.py --dry-run

# Apply updates
python update_core.py
python update_core.py --force

# Backup and rollback
python update_core.py --backup
python update_core.py --list-backups
python update_core.py --rollback
python update_core.py --rollback v1.0.5

# Information
python update_core.py --version
python update_core.py --help
```
