#!/usr/bin/env python3
"""
Framework Core Update Utility - Rewritten v2.0

This utility allows projects using the Modular Python Framework to check for
and apply framework updates while preserving their application modules.

Architecture:
- VersionManager: Version detection and comparison
- ManifestManager: Manifest loading and comparison
- GitHubClient: GitHub API communication
- BackupManager: Backup operations and rollback metadata
- FileUpdater: Atomic file operations
- UpdateOrchestrator: Main workflow coordination

Usage:
    python update_core.py                      # Check and apply updates
    python update_core.py --check              # Check for updates only
    python update_core.py --dry-run            # Show what would change
    python update_core.py --force              # Update without prompts
    python update_core.py --backup             # Create backup only
    python update_core.py --list-backups       # List available backups
    python update_core.py --rollback           # Interactive rollback
    python update_core.py --rollback v1.0.5    # Rollback to specific version
    python update_core.py --version            # Show version info
"""

import os
import sys
import json
import shutil
import tempfile
import zipfile
import argparse
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import requests


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ReleaseInfo:
    """GitHub release information."""
    version: str
    tag_name: str
    release_notes: str
    published_at: str
    zipball_url: str
    prerelease: bool


@dataclass
class ManifestDiff:
    """Difference between two manifests."""
    added: List[str]        # New files in new manifest
    modified: List[str]     # Files in both (may have changed)
    removed: List[str]      # Files in old manifest but not new (orphans)


@dataclass
class BackupInfo:
    """Backup metadata."""
    path: str
    version: str
    created: str
    name: str


# ============================================================================
# Component 1: VersionManager
# ============================================================================

class VersionManager:
    """Manages framework version detection, comparison, and tracking."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.version_file = project_root / ".framework_version"
        self.manifest_file = project_root / "framework_manifest.json"

    def get_current_version(self) -> str:
        """Get current framework version.

        Priority:
        1. .framework_version file
        2. framework_manifest.json
        3. Default "0.0.0"
        """
        # Priority 1: .framework_version file
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r') as f:
                    data = json.load(f)
                    return data.get("version", "0.0.0")
            except (json.JSONDecodeError, KeyError):
                pass

        # Priority 2: framework_manifest.json
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r') as f:
                    data = json.load(f)
                    return data.get("version", "0.0.0")
            except (json.JSONDecodeError, KeyError):
                pass

        # Priority 3: Default
        return "0.0.0"

    def parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """Parse semantic version string to tuple.

        Args:
            version_str: Version string like "1.0.5"

        Returns:
            Tuple of (major, minor, patch)
        """
        try:
            # Remove 'v' prefix if present
            version_str = version_str.lstrip('v')
            parts = version_str.split('.')

            # Pad with zeros if needed
            while len(parts) < 3:
                parts.append('0')

            return tuple(int(p) for p in parts[:3])
        except (ValueError, AttributeError):
            return (0, 0, 0)

    def compare_versions(self, current: str, remote: str) -> int:
        """Compare version strings.

        Args:
            current: Current version string
            remote: Remote version string

        Returns:
            -1 if current < remote (update available)
             0 if current == remote (up to date)
             1 if current > remote (ahead of remote)
        """
        current_tuple = self.parse_version(current)
        remote_tuple = self.parse_version(remote)

        if current_tuple < remote_tuple:
            return -1
        elif current_tuple > remote_tuple:
            return 1
        else:
            return 0

    def update_version_file(self, version: str, metadata: Dict[str, Any] = None):
        """Create or update .framework_version file.

        Args:
            version: New version string
            metadata: Additional metadata to store
        """
        version_data = {
            "version": version,
            "updated_date": datetime.now().isoformat(),
            "project_name": os.path.basename(self.project_root)
        }

        # Merge additional metadata
        if metadata:
            version_data.update(metadata)

        with open(self.version_file, 'w') as f:
            json.dump(version_data, f, indent=2)


# ============================================================================
# Component 2: ManifestManager
# ============================================================================

class ManifestManager:
    """Manages framework manifest loading, comparison, and filtering."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.manifest_file = project_root / "framework_manifest.json"
        self.gitignore_patterns = self._load_gitignore()

    def _load_gitignore(self) -> List[str]:
        """Load and parse .gitignore file."""
        gitignore_file = self.project_root / ".gitignore"
        patterns = []

        if not gitignore_file.exists():
            return patterns

        try:
            with open(gitignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception:
            pass

        return patterns

    def _matches_gitignore(self, file_path: str) -> bool:
        """Check if file matches any gitignore pattern."""
        for pattern in self.gitignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith('/'):
                dir_pattern = pattern.rstrip('/')
                if file_path.startswith(dir_pattern + '/'):
                    return True
                # Check any path component
                for part in Path(file_path).parts:
                    if fnmatch.fnmatch(part, dir_pattern):
                        return True
            else:
                # File/glob patterns
                if fnmatch.fnmatch(file_path, pattern):
                    return True
                # Check filename
                if fnmatch.fnmatch(Path(file_path).name, pattern):
                    return True
                # Check any path component
                for part in Path(file_path).parts:
                    if fnmatch.fnmatch(part, pattern):
                        return True

        return False

    def load_local_manifest(self) -> Dict[str, Any]:
        """Load local framework_manifest.json."""
        if not self.manifest_file.exists():
            return {"version": "0.0.0", "framework_files": []}

        try:
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"version": "0.0.0", "framework_files": []}

    def load_source_manifest(self, source_dir: Path) -> Dict[str, Any]:
        """Load manifest from downloaded source directory."""
        manifest_file = source_dir / "framework_manifest.json"

        if not manifest_file.exists():
            return {"version": "0.0.0", "framework_files": []}

        try:
            with open(manifest_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"version": "0.0.0", "framework_files": []}

    def compare_manifests(self, old: Dict[str, Any], new: Dict[str, Any]) -> ManifestDiff:
        """Compare two manifests and return differences.

        Args:
            old: Old manifest (current local)
            new: New manifest (from download)

        Returns:
            ManifestDiff with added, modified, and removed files
        """
        old_files = set(old.get("framework_files", []))
        new_files = set(new.get("framework_files", []))

        added = list(new_files - old_files)
        modified = list(new_files & old_files)
        removed = list(old_files - new_files)

        return ManifestDiff(
            added=sorted(added),
            modified=sorted(modified),
            removed=sorted(removed)
        )

    def filter_orphans_by_framework_paths(self, orphans: List[str]) -> List[str]:
        """Filter orphans to only include framework-owned paths.

        Framework-owned paths:
        - core/
        - modules/core/
        - tools/
        - ui/
        - docs/core/

        User space (NOT checked):
        - Project root
        - docs/ (root only)
        - modules/standard/
        - data/
        """
        framework_owned_paths = (
            "core/",
            "modules/core/",
            "tools/",
            "ui/",
            "docs/core/"
        )

        filtered = []
        for file_path in orphans:
            if file_path.startswith(framework_owned_paths):
                filtered.append(file_path)
            # Root and docs/ root files ignored - might be user files

        return filtered


# ============================================================================
# Component 3: GitHubClient
# ============================================================================

class GitHubClient:
    """Handles GitHub API communication and release downloads."""

    def __init__(self, repo_owner: str = "elevena11", repo_name: str = "Modular_Python_Framework"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_base = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

    def get_latest_release(self) -> Optional[ReleaseInfo]:
        """Get latest release information from GitHub.

        Returns:
            ReleaseInfo object or None if failed
        """
        try:
            response = requests.get(f"{self.api_base}/releases/latest", timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse version from tag_name (e.g., "v1.0.0" -> "1.0.0")
            version = data["tag_name"].lstrip('v')

            return ReleaseInfo(
                version=version,
                tag_name=data["tag_name"],
                release_notes=data.get("body", ""),
                published_at=data["published_at"],
                zipball_url=data["zipball_url"],
                prerelease=data.get("prerelease", False)
            )

        except requests.RequestException as e:
            print(f"Error fetching release info: {e}")
            return None
        except KeyError as e:
            print(f"Unexpected GitHub API response format: {e}")
            return None

    def download_release(self, release_info: ReleaseInfo) -> Optional[Path]:
        """Download and extract release to temporary directory.

        Args:
            release_info: Release information

        Returns:
            Path to extracted framework directory or None if failed
        """
        try:
            # Download zipball
            response = requests.get(release_info.zipball_url, timeout=60)
            response.raise_for_status()

            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix="framework_update_"))
            zip_path = temp_dir / "framework.zip"

            # Save zip file
            with open(zip_path, 'wb') as f:
                f.write(response.content)

            # Extract
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                zip_file.extractall(temp_dir)

            # Find extracted directory (GitHub creates dirs like "user-repo-commit")
            extracted_dirs = [d for d in temp_dir.iterdir()
                            if d.is_dir() and not d.name.startswith('.')]

            if not extracted_dirs:
                shutil.rmtree(temp_dir)
                return None

            return extracted_dirs[0]

        except Exception as e:
            print(f"Error downloading release: {e}")
            return None

    def check_rate_limit(self) -> Dict[str, Any]:
        """Check GitHub API rate limit status."""
        try:
            response = requests.get("https://api.github.com/rate_limit", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}


# ============================================================================
# Component 4: BackupManager
# ============================================================================

class BackupManager:
    """Manages backup creation, rollback metadata, and restoration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backup_root = project_root / ".framework_backups"

    def create_backup_dir(self, version: str) -> Path:
        """Create backup directory for a version.

        Args:
            version: Current version being backed up

        Returns:
            Path to created backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"framework_v{version}_{timestamp}"
        backup_dir = self.backup_root / backup_name

        # Create directory structure
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "updated_files").mkdir(exist_ok=True)
        (backup_dir / "orphaned_files").mkdir(exist_ok=True)

        return backup_dir

    def get_backup_path(self, backup_dir: Path, file_path: str, category: str = "updated_files") -> Path:
        """Get backup path for a specific file.

        Args:
            backup_dir: Backup directory
            file_path: Relative file path
            category: "updated_files" or "orphaned_files"

        Returns:
            Full path where file should be backed up
        """
        return backup_dir / category / file_path

    def save_rollback_info(self, backup_dir: Path, info: Dict[str, Any]):
        """Save rollback metadata to backup directory.

        Args:
            backup_dir: Backup directory
            info: Rollback information dictionary
        """
        rollback_file = backup_dir / ".rollback_info.json"
        with open(rollback_file, 'w') as f:
            json.dump(info, f, indent=2)

    def load_rollback_info(self, backup_dir: Path) -> Optional[Dict[str, Any]]:
        """Load rollback metadata from backup directory.

        Args:
            backup_dir: Backup directory

        Returns:
            Rollback info dictionary or None if not found
        """
        rollback_file = backup_dir / ".rollback_info.json"

        if not rollback_file.exists():
            return None

        try:
            with open(rollback_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None

    def list_backups(self) -> List[BackupInfo]:
        """List all available backups.

        Returns:
            List of BackupInfo objects, sorted by creation time (newest first)
        """
        if not self.backup_root.exists():
            return []

        backups = []

        for backup_dir in self.backup_root.iterdir():
            if not backup_dir.is_dir():
                continue

            if not backup_dir.name.startswith("framework_v"):
                continue

            # Parse backup name: framework_v1.0.5_20251017_143022
            parts = backup_dir.name.split('_')
            if len(parts) < 4:
                continue

            version = parts[1].lstrip('v')
            date_part = parts[2]
            time_part = parts[3]
            created = f"{date_part}_{time_part}"

            backups.append(BackupInfo(
                path=str(backup_dir),
                version=version,
                created=created,
                name=backup_dir.name
            ))

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.created, reverse=True)
        return backups


# ============================================================================
# Component 5: FileUpdater
# ============================================================================

class FileUpdater:
    """Handles atomic file operations for updates."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.ignore_patterns = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo')

    def backup_then_overwrite(self, source: Path, target: Path, backup_dir: Path) -> bool:
        """Atomic operation: backup existing file then overwrite with new version.

        This is the ONLY way to overwrite files - backup and overwrite are
        tightly coupled to prevent sync issues.

        Args:
            source: Source file from download
            target: Target file in project
            backup_dir: Backup directory root

        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate backup location
            relative_path = target.relative_to(self.project_root)
            backup_target = backup_dir / "updated_files" / relative_path
            backup_target.parent.mkdir(parents=True, exist_ok=True)

            # Step 1: Backup existing file (if exists)
            if target.exists():
                if target.is_dir():
                    if backup_target.exists():
                        shutil.rmtree(backup_target)
                    shutil.copytree(target, backup_target, ignore=self.ignore_patterns)
                else:
                    shutil.copy2(target, backup_target)

            # Step 2: Overwrite with new file
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()

            target.parent.mkdir(parents=True, exist_ok=True)

            if source.is_dir():
                shutil.copytree(source, target, ignore=self.ignore_patterns)
            else:
                shutil.copy2(source, target)

            return True

        except Exception as e:
            print(f"Error in atomic operation for {target}: {e}")
            return False

    def copy_new_file(self, source: Path, target: Path) -> bool:
        """Copy new file that doesn't exist locally.

        Args:
            source: Source file from download
            target: Target file in project

        Returns:
            True if successful, False otherwise
        """
        try:
            target.parent.mkdir(parents=True, exist_ok=True)

            if source.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target, ignore=self.ignore_patterns)
            else:
                shutil.copy2(source, target)

            return True

        except Exception as e:
            print(f"Error copying new file {target}: {e}")
            return False

    def move_to_orphaned(self, file_path: str, backup_dir: Path) -> bool:
        """Move orphaned file to backup directory.

        Args:
            file_path: Relative path to orphaned file
            backup_dir: Backup directory root

        Returns:
            True if successful, False otherwise
        """
        try:
            source = self.project_root / file_path

            if not source.exists():
                return True  # Already gone

            # Move to orphaned_files in backup
            target = backup_dir / "orphaned_files" / file_path
            target.parent.mkdir(parents=True, exist_ok=True)

            if source.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target, ignore=self.ignore_patterns)
                shutil.rmtree(source)
            else:
                shutil.copy2(source, target)
                source.unlink()

            return True

        except Exception as e:
            print(f"Error moving orphaned file {file_path}: {e}")
            return False


# ============================================================================
# Component 6: UpdateOrchestrator
# ============================================================================

class UpdateOrchestrator:
    """Coordinates the overall update and rollback workflows."""

    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path.cwd()

        self.project_root = Path(project_root).resolve()

        # Initialize all components
        self.version_mgr = VersionManager(self.project_root)
        self.manifest_mgr = ManifestManager(self.project_root)
        self.github_client = GitHubClient()
        self.backup_mgr = BackupManager(self.project_root)
        self.file_updater = FileUpdater(self.project_root)

    def check_for_updates(self) -> bool:
        """Check if updates are available.

        Returns:
            True if update available, False otherwise
        """
        print("Checking for updates...")

        # Get current version
        current_version = self.version_mgr.get_current_version()
        print(f"Current version: {current_version}")

        # Get latest release
        release_info = self.github_client.get_latest_release()
        if not release_info:
            print("Error: Could not check for updates")
            return False

        print(f"Latest version:  {release_info.version}")

        # Compare versions
        comparison = self.version_mgr.compare_versions(current_version, release_info.version)

        if comparison >= 0:
            print("Framework is up to date")
            return False

        # Show release notes
        print(f"\nNew version available: v{current_version} -> v{release_info.version}")

        if release_info.prerelease:
            print("WARNING: This is a pre-release version")

        print("\nRelease Notes:")
        print("-" * 50)
        print(release_info.release_notes)
        print("-" * 50)

        return True

    def apply_update(self, force: bool = False, dry_run: bool = False) -> bool:
        """Apply framework update.

        Args:
            force: Skip confirmation prompts
            dry_run: Show what would change without applying

        Returns:
            True if successful, False otherwise
        """
        # Get current version
        current_version = self.version_mgr.get_current_version()

        # Get latest release
        release_info = self.github_client.get_latest_release()
        if not release_info:
            return False

        # Check if update needed
        comparison = self.version_mgr.compare_versions(current_version, release_info.version)
        if comparison >= 0:
            print("Framework is already up to date")
            return True

        # Show release info
        print(f"\nUpdate available: v{current_version} -> v{release_info.version}")

        if release_info.prerelease:
            print("WARNING: This is a pre-release version")

        print("\nRelease Notes:")
        print("-" * 50)
        print(release_info.release_notes[:500])
        if len(release_info.release_notes) > 500:
            print("... (truncated)")
        print("-" * 50)

        # Confirm update
        if not force and not dry_run:
            # Check for major version change
            current_major = self.version_mgr.parse_version(current_version)[0]
            remote_major = self.version_mgr.parse_version(release_info.version)[0]

            if remote_major > current_major:
                print("\nWARNING: Major version change detected!")
                print("This update may contain breaking changes.")

            response = input(f"\nProceed with update? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Update cancelled")
                return False

        # Download and extract
        print(f"\nDownloading framework v{release_info.version}...")
        source_dir = self.github_client.download_release(release_info)

        if not source_dir:
            print("Error: Failed to download release")
            return False

        try:
            # Load manifests
            old_manifest = self.manifest_mgr.load_local_manifest()
            new_manifest = self.manifest_mgr.load_source_manifest(source_dir)

            # Compare manifests
            diff = self.manifest_mgr.compare_manifests(old_manifest, new_manifest)

            # Filter orphans to framework-owned paths only
            orphans = self.manifest_mgr.filter_orphans_by_framework_paths(diff.removed)

            # Show update summary
            print(f"\nUpdate Summary:")
            print(f"  Files to add:    {len(diff.added)}")
            print(f"  Files to update: {len(diff.modified)}")
            print(f"  Files to remove: {len(orphans)} (moved to backup)")

            if dry_run:
                self._show_dry_run_details(diff, orphans)
                return True

            # Create backup
            print(f"\nCreating backup...")
            backup_dir = self.backup_mgr.create_backup_dir(current_version)

            # Handle orphaned files
            print(f"\nHandling orphaned files...")
            for orphan_file in orphans:
                print(f"  Moving to backup: {orphan_file}")
                self.file_updater.move_to_orphaned(orphan_file, backup_dir)

            # Update files
            print(f"\nUpdating files...")
            updated_files = []
            added_files = []
            failed_files = []

            # Process modified files (exist in both)
            for file_path in diff.modified:
                source = source_dir / file_path
                target = self.project_root / file_path

                if not source.exists():
                    print(f"  Warning: {file_path} missing in new version")
                    failed_files.append(file_path)
                    continue

                if target.exists():
                    # Existing file - use atomic backup-then-overwrite
                    if self.file_updater.backup_then_overwrite(source, target, backup_dir):
                        updated_files.append(file_path)
                        print(f"  Updated: {file_path}")
                    else:
                        failed_files.append(file_path)
                else:
                    # File in manifest but doesn't exist locally - copy as new
                    if self.file_updater.copy_new_file(source, target):
                        added_files.append(file_path)
                        print(f"  Added: {file_path}")
                    else:
                        failed_files.append(file_path)

            # Process added files (new in manifest)
            for file_path in diff.added:
                source = source_dir / file_path
                target = self.project_root / file_path

                if not source.exists():
                    print(f"  Warning: {file_path} missing in new version")
                    failed_files.append(file_path)
                    continue

                if self.file_updater.copy_new_file(source, target):
                    added_files.append(file_path)
                    print(f"  Added: {file_path}")
                else:
                    failed_files.append(file_path)

            # Save rollback info
            rollback_info = {
                "original_version": current_version,
                "target_version": release_info.version,
                "backup_timestamp": datetime.now().isoformat(),
                "updated_files": updated_files,
                "added_files": added_files,
                "orphaned_files": orphans,
                "failed_files": failed_files,
                "project_root": str(self.project_root)
            }
            self.backup_mgr.save_rollback_info(backup_dir, rollback_info)

            # Update version file
            self.version_mgr.update_version_file(
                release_info.version,
                {
                    "source": "github_release",
                    "release_notes": release_info.release_notes[:500],
                    "commit": "",
                    "installed_date": datetime.now().isoformat()
                }
            )

            # Summary
            print(f"\nUpdate complete: v{current_version} -> v{release_info.version}")
            print(f"Backup available at: {backup_dir}")

            if failed_files:
                print(f"\nWarning: {len(failed_files)} files failed to update:")
                for file_path in failed_files[:10]:
                    print(f"  - {file_path}")
                if len(failed_files) > 10:
                    print(f"  ... and {len(failed_files) - 10} more")

            print("\nPlease restart your application to use the updated framework.")
            return True

        finally:
            # Clean up temporary directory
            if source_dir and source_dir.exists():
                shutil.rmtree(source_dir.parent)

    def _show_dry_run_details(self, diff: ManifestDiff, orphans: List[str]):
        """Show detailed dry-run information."""
        print("\nDry run mode - no changes will be made")
        print("\nFiles to add:")
        for file_path in diff.added[:10]:
            print(f"  + {file_path}")
        if len(diff.added) > 10:
            print(f"  ... and {len(diff.added) - 10} more")

        print("\nFiles to update:")
        for file_path in diff.modified[:10]:
            print(f"  ~ {file_path}")
        if len(diff.modified) > 10:
            print(f"  ... and {len(diff.modified) - 10} more")

        if orphans:
            print("\nFiles to remove (moved to backup):")
            for file_path in orphans[:10]:
                print(f"  - {file_path}")
            if len(orphans) > 10:
                print(f"  ... and {len(orphans) - 10} more")

        print("\nRun without --dry-run to apply these changes")

    def rollback_to_version(self, backup_name: str = None) -> bool:
        """Rollback framework to a previous backup.

        Args:
            backup_name: Backup name or version to rollback to (None for interactive)

        Returns:
            True if successful, False otherwise
        """
        # List available backups
        backups = self.backup_mgr.list_backups()

        if not backups:
            print("No backups found")
            return False

        # Select backup
        if backup_name is None:
            # Interactive selection
            print("\nAvailable backups:")
            print("-" * 60)
            for i, backup in enumerate(backups, 1):
                print(f"{i}. v{backup.version} - {backup.created}")
            print("-" * 60)

            try:
                choice = input("Select backup number (or 'cancel'): ").strip()
                if choice.lower() == 'cancel':
                    print("Rollback cancelled")
                    return False

                backup_index = int(choice) - 1
                if backup_index < 0 or backup_index >= len(backups):
                    print("Invalid backup selection")
                    return False

                selected_backup = backups[backup_index]
            except (ValueError, KeyboardInterrupt):
                print("\nRollback cancelled")
                return False
        else:
            # Find backup by name or version
            selected_backup = None
            for backup in backups:
                if backup.name == backup_name or backup.version == backup_name.lstrip('v'):
                    selected_backup = backup
                    break

            if not selected_backup:
                print(f"Backup not found: {backup_name}")
                return False

        # Load rollback info
        backup_dir = Path(selected_backup.path)
        rollback_info = self.backup_mgr.load_rollback_info(backup_dir)

        if not rollback_info:
            print("Error: No rollback information found in backup")
            return False

        # Confirm rollback
        current_version = self.version_mgr.get_current_version()
        target_version = rollback_info["original_version"]

        print(f"\nRollback Summary:")
        print(f"  From version: {current_version}")
        print(f"  To version:   {target_version}")
        print(f"  Files to restore: {len(rollback_info['updated_files'])}")

        if rollback_info.get("added_files"):
            print(f"  Files to preserve: {len(rollback_info['added_files'])} (added in update, will not be deleted)")

        response = input(f"\nProceed with rollback? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Rollback cancelled")
            return False

        # Create safety backup
        print("\nCreating safety backup of current state...")
        safety_backup = self.backup_mgr.create_backup_dir(f"pre_rollback_{current_version}")

        # Restore updated files
        print("\nRestoring files...")
        for file_path in rollback_info["updated_files"]:
            backup_source = backup_dir / "updated_files" / file_path
            target = self.project_root / file_path

            if not backup_source.exists():
                print(f"  Warning: Backup missing for {file_path}")
                continue

            # Backup current state to safety backup
            if target.exists():
                safety_target = safety_backup / "updated_files" / file_path
                safety_target.parent.mkdir(parents=True, exist_ok=True)

                if target.is_dir():
                    shutil.copytree(target, safety_target, ignore=self.file_updater.ignore_patterns)
                else:
                    shutil.copy2(target, safety_target)

            # Restore from backup
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()

            target.parent.mkdir(parents=True, exist_ok=True)

            if backup_source.is_dir():
                shutil.copytree(backup_source, target, ignore=self.file_updater.ignore_patterns)
            else:
                shutil.copy2(backup_source, target)

            print(f"  Restored: {file_path}")

        # Note about added files
        if rollback_info.get("added_files"):
            print(f"\nNote: {len(rollback_info['added_files'])} files added in update will remain:")
            for file_path in rollback_info["added_files"][:5]:
                print(f"  - {file_path}")
            if len(rollback_info["added_files"]) > 5:
                print(f"  ... and {len(rollback_info['added_files']) - 5} more")

        # Restore orphaned files
        if rollback_info.get("orphaned_files"):
            print("\nRestoring orphaned files...")
            for file_path in rollback_info["orphaned_files"]:
                orphan_source = backup_dir / "orphaned_files" / file_path
                target = self.project_root / file_path

                if not orphan_source.exists():
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)

                if orphan_source.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(orphan_source, target, ignore=self.file_updater.ignore_patterns)
                else:
                    shutil.copy2(orphan_source, target)

                print(f"  Restored: {file_path}")

        # Restore version file
        version_backup = backup_dir / ".framework_version"
        if version_backup.exists():
            shutil.copy2(version_backup, self.version_mgr.version_file)
        else:
            self.version_mgr.update_version_file(
                target_version,
                {"source": "rollback", "rollback_from": current_version}
            )

        print(f"\nRollback complete: v{current_version} -> v{target_version}")
        print(f"Safety backup at: {safety_backup}")
        print("\nPlease restart your application to use the rolled-back framework.")
        return True

    def create_backup_only(self) -> bool:
        """Create backup of current framework without updating.

        Returns:
            True if successful, False otherwise
        """
        current_version = self.version_mgr.get_current_version()
        print(f"Creating backup of framework v{current_version}...")

        backup_dir = self.backup_mgr.create_backup_dir(current_version)

        # Load current manifest
        manifest = self.manifest_mgr.load_local_manifest()
        framework_files = manifest.get("framework_files", [])

        print(f"Backing up {len(framework_files)} framework files...")

        backed_up = 0
        for file_path in framework_files:
            source = self.project_root / file_path

            if not source.exists():
                continue

            target = backup_dir / "updated_files" / file_path
            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                if source.is_dir():
                    # Remove existing target directory if it exists
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(source, target, ignore=self.file_updater.ignore_patterns)
                else:
                    shutil.copy2(source, target)
                backed_up += 1
            except Exception as e:
                print(f"  Warning: Could not backup {file_path}: {e}")

        # Backup version file
        if self.version_mgr.version_file.exists():
            shutil.copy2(self.version_mgr.version_file, backup_dir / ".framework_version")

        # Save metadata
        rollback_info = {
            "original_version": current_version,
            "backup_timestamp": datetime.now().isoformat(),
            "backed_up_files": framework_files,
            "project_root": str(self.project_root)
        }
        self.backup_mgr.save_rollback_info(backup_dir, rollback_info)

        print(f"\nBackup complete: {backed_up} files backed up")
        print(f"Backup location: {backup_dir}")
        return True

    def list_backups(self):
        """List all available backups."""
        backups = self.backup_mgr.list_backups()

        if not backups:
            print("No backups found")
            return

        print("\nAvailable backups:")
        print("-" * 60)
        for backup in backups:
            print(f"v{backup.version} - {backup.created}")
            print(f"  {backup.name}")
            print()

    def show_version_info(self):
        """Show current version information."""
        current_version = self.version_mgr.get_current_version()
        print(f"\nFramework Version: {current_version}")

        # Try to read full version file
        if self.version_mgr.version_file.exists():
            try:
                with open(self.version_mgr.version_file, 'r') as f:
                    data = json.load(f)

                print(f"Source: {data.get('source', 'unknown')}")

                if 'installed_date' in data:
                    print(f"Installed: {data['installed_date']}")

                if 'updated_date' in data:
                    print(f"Updated: {data['updated_date']}")
            except Exception:
                pass

        print()


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Modular Python Framework Update Utility v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--check", action="store_true",
                       help="Check for updates without applying")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would change without applying")
    parser.add_argument("--force", action="store_true",
                       help="Update without confirmation prompts")
    parser.add_argument("--backup", action="store_true",
                       help="Create backup only")
    parser.add_argument("--list-backups", action="store_true",
                       help="List available backups")
    parser.add_argument("--rollback", type=str, nargs="?", const="",
                       help="Rollback to backup (specify version or leave empty for interactive)")
    parser.add_argument("--version", action="store_true",
                       help="Show version information")
    parser.add_argument("--project-root", type=str, default=".",
                       help="Path to project root (default: current directory)")

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = UpdateOrchestrator(args.project_root)

    try:
        # Handle version info
        if args.version:
            orchestrator.show_version_info()
            sys.exit(0)

        # Handle backup listing
        if args.list_backups:
            orchestrator.list_backups()
            sys.exit(0)

        # Handle backup creation
        if args.backup:
            success = orchestrator.create_backup_only()
            sys.exit(0 if success else 1)

        # Handle rollback
        if args.rollback is not None:
            backup_name = args.rollback if args.rollback else None
            success = orchestrator.rollback_to_version(backup_name)
            sys.exit(0 if success else 1)

        # Handle check only
        if args.check:
            has_update = orchestrator.check_for_updates()
            sys.exit(0 if not has_update else 1)  # Exit 1 if update available

        # Handle update (default action)
        success = orchestrator.apply_update(force=args.force, dry_run=args.dry_run)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
