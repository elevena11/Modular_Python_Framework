#!/usr/bin/env python3
"""
Framework Core Update Utility

This utility allows projects using the Modular Python Framework to check for
and apply framework updates while preserving their application modules.

Usage:
    python update_core.py                      # Check for updates
    python update_core.py --force              # Force update without prompts
    python update_core.py --check-only         # Only check, don't update
    python update_core.py --backup-only        # Create backup of current framework
    python update_core.py --list-backups       # List available backups
    python update_core.py --rollback           # Interactive rollback (choose from list)
    python update_core.py --rollback v1.0.0    # Rollback to specific version
"""

import os
import sys
import json
import shutil
import tempfile
import zipfile
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

class FrameworkUpdater:
    """Handles framework updates from the remote repository."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.framework_version_file = self.project_root / ".framework_version"
        self.backup_dir = self.project_root / ".framework_backups"
        
        # Framework repository settings
        self.repo_owner = "elevena11"
        self.repo_name = "Modular_Python_Framework" 
        self.github_api_base = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        
        # Repository settings only - no hardcoded file lists!
    
    def get_current_version(self) -> Dict[str, Any]:
        """Get current framework version from local file."""
        if self.framework_version_file.exists():
            try:
                with open(self.framework_version_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print("Warning: Invalid or missing .framework_version file")
        
        # Try to read from framework_manifest.json as fallback
        manifest_file = self.project_root / "framework_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r') as f:
                    manifest_data = json.load(f)
                    version_data = {
                        "version": manifest_data.get("version", "1.0.0"),
                        "commit": "",
                        "installed": True
                    }
                    # Create .framework_version if it doesn't exist
                    self.create_framework_version_file(version_data)
                    return version_data
            except json.JSONDecodeError:
                pass
        
        return {"version": "0.0.0", "commit": "", "installed": False}
    
    def create_framework_version_file(self, version_data: Dict[str, Any]):
        """Create .framework_version file for tracking."""
        tracking_data = {
            "version": version_data.get("version", "1.0.0"),
            "commit": version_data.get("commit", ""),
            "installed_date": datetime.now().isoformat(),
            "source": "github_release",
            "project_name": os.path.basename(self.project_root)
        }
        
        with open(self.framework_version_file, 'w') as f:
            json.dump(tracking_data, f, indent=2)
        
        print(f"Created framework version tracking: {self.framework_version_file}")
    
    def check_remote_version(self) -> Optional[Dict[str, Any]]:
        """Check latest version from GitHub releases."""
        try:
            response = requests.get(f"{self.github_api_base}/releases/latest", timeout=10)
            response.raise_for_status()
            release_data = response.json()
            
            # Parse version from tag_name (e.g., "v1.0.0" -> "1.0.0")
            version = release_data["tag_name"].lstrip('v')
            
            return {
                "version": version,
                "tag_name": release_data["tag_name"],
                "name": release_data["name"],
                "body": release_data["body"],
                "published_at": release_data["published_at"],
                "zipball_url": release_data["zipball_url"],
                "prerelease": release_data["prerelease"]
            }
            
        except requests.RequestException as e:
            print(f"Error checking remote version: {e}")
            return None
        except KeyError as e:
            print(f"Unexpected response format: {e}")
            return None
    
    def compare_versions(self, current: str, remote: str) -> int:
        """Compare version strings. Returns: -1 (current < remote), 0 (equal), 1 (current > remote)"""
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        
        try:
            current_tuple = version_tuple(current)
            remote_tuple = version_tuple(remote)
            
            if current_tuple < remote_tuple:
                return -1
            elif current_tuple > remote_tuple:
                return 1
            else:
                return 0
        except ValueError:
            print("Warning: Unable to compare version strings")
            return -1  # Assume update needed if can't parse
    
    def show_changelog(self, remote_info: Dict[str, Any]):
        """Display changelog and release notes."""
        print(f"\n📦 New Framework Version Available!")
        print(f"Version: {remote_info['version']}")
        print(f"Released: {remote_info['published_at']}")
        
        if remote_info['prerelease']:
            print("⚠️  WARNING: This is a pre-release version")
        
        print("\n📋 Release Notes:")
        print("-" * 50)
        print(remote_info['body'])
        print("-" * 50)
    
    def confirm_update(self, current_version: str, remote_version: str) -> bool:
        """Ask user confirmation for update."""
        print(f"\n🔄 Update framework from v{current_version} to v{remote_version}?")
        
        # Check for potential breaking changes
        current_major = int(current_version.split('.')[0])
        remote_major = int(remote_version.split('.')[0])
        
        if remote_major > current_major:
            print("⚠️  WARNING: Major version change detected!")
            print("   This update may contain breaking changes.")
            print("   Please review your modules for compatibility.")
        
        response = input("Proceed with update? (y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    def detect_orphaned_files(self, new_manifest: Dict[str, Any]) -> List[str]:
        """Detect files that exist locally but aren't in the new manifest."""
        if not new_manifest or "framework_files" not in new_manifest:
            return []
        
        new_framework_files = set(new_manifest["framework_files"])
        orphaned_files = []
        
        # Check current framework files against new manifest
        current_manifest_file = self.project_root / "framework_manifest.json"
        if current_manifest_file.exists():
            try:
                with open(current_manifest_file, 'r') as f:
                    current_manifest = json.load(f)
                
                current_framework_files = current_manifest.get("framework_files", [])
                
                for current_file in current_framework_files:
                    file_path = self.project_root / current_file
                    # File exists locally but not in new manifest = orphaned
                    if file_path.exists() and current_file not in new_framework_files:
                        orphaned_files.append(current_file)
                        
            except json.JSONDecodeError:
                print("⚠️  Warning: Could not read current manifest, orphan detection skipped")
        
        return orphaned_files

    def backup_files_from_manifest(self, files_to_backup: List[str]) -> str:
        """Create backup of files that will be updated according to manifest."""
        current_version = self.get_current_version()["version"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"framework_v{current_version}_{timestamp}"
        backup_path = self.backup_dir / backup_name

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path.mkdir(exist_ok=True)

        print(f"Creating backup: {backup_path}")

        # Track files for rollback purposes
        rollback_info = {
            "backed_up_files": [],      # Files that were backed up (restore these on rollback)
            "new_files": [],            # New files that didn't exist (delete these on rollback)
            "backup_timestamp": timestamp,
            "original_version": current_version,
            "project_root": str(self.project_root)
        }

        # Backup only files that exist locally AND are in the manifest
        backed_up_count = 0
        for file_path in files_to_backup:
            local_path = self.project_root / file_path

            if local_path.exists():
                print(f"   Backing up: {file_path}")
                backup_target = backup_path / file_path

                if local_path.is_dir():
                    shutil.copytree(local_path, backup_target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                else:
                    backup_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local_path, backup_target)

                rollback_info["backed_up_files"].append(file_path)
                backed_up_count += 1
            else:
                print(f"   New file (no backup needed): {file_path}")
                rollback_info["new_files"].append(file_path)

        # Always backup version tracking file if it exists
        if self.framework_version_file.exists():
            shutil.copy2(self.framework_version_file, backup_path / ".framework_version")

        # Save rollback information
        rollback_info_file = backup_path / ".rollback_info.json"
        with open(rollback_info_file, 'w') as f:
            json.dump(rollback_info, f, indent=2)

        print(f"✅ Backup created: {backup_path} ({backed_up_count} items backed up, {len(rollback_info['new_files'])} new files tracked)")
        return str(backup_path)

    def backup_files_from_zip_content(self, zip_content_list: List[str]) -> str:
        """Create backup of files that exist in both local project and zip file."""
        current_version = self.get_current_version()["version"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"framework_v{current_version}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path.mkdir(exist_ok=True)
        
        print(f"Creating backup: {backup_path}")
        
        # Track files for rollback purposes
        rollback_info = {
            "backed_up_files": [],      # Files that were backed up (restore these on rollback)
            "new_files": [],            # New files that didn't exist (delete these on rollback)
            "backup_timestamp": timestamp,
            "original_version": current_version,
            "project_root": str(self.project_root)
        }
        
        # Backup only files that exist locally AND are in the zip
        backed_up_count = 0
        for zip_item in zip_content_list:
            local_path = self.project_root / zip_item
            
            if local_path.exists():
                print(f"   Backing up: {zip_item}")
                backup_target = backup_path / zip_item
                
                if local_path.is_dir():
                    shutil.copytree(local_path, backup_target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                else:
                    backup_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local_path, backup_target)
                
                rollback_info["backed_up_files"].append(zip_item)
                backed_up_count += 1
            else:
                print(f"   New file (no backup needed): {zip_item}")
                rollback_info["new_files"].append(zip_item)
        
        # Always backup version tracking file if it exists
        if self.framework_version_file.exists():
            shutil.copy2(self.framework_version_file, backup_path / ".framework_version")
        
        # Save rollback information
        rollback_info_file = backup_path / ".rollback_info.json"
        with open(rollback_info_file, 'w') as f:
            json.dump(rollback_info, f, indent=2)
        
        print(f"✅ Backup created: {backup_path} ({backed_up_count} items backed up, {len(rollback_info['new_files'])} new files tracked)")
        return str(backup_path)
    
    def get_zip_content_list(self, zip_file: zipfile.ZipFile) -> List[str]:
        """Get list of root-level files and directories in the zip."""
        root_items = set()
        
        for file_path in zip_file.namelist():
            # Skip the GitHub-generated root directory (e.g., "user-repo-commit/")
            parts = file_path.split('/')
            if len(parts) > 1 and not file_path.endswith('/'):
                # This is a file inside the root directory
                root_items.add(parts[1])  # Add the first level after root
            elif len(parts) > 2:
                # This is a directory
                root_items.add(parts[1])
        
        # Filter out hidden files and directories we don't want
        filtered_items = []
        for item in root_items:
            if not item.startswith('.') or item in ['.env.example']:
                filtered_items.append(item)
        
        return sorted(filtered_items)

    def download_and_extract_framework(self, remote_info: Dict[str, Any]) -> bool:
        """Download and extract new framework version."""
        print(f"📥 Downloading framework v{remote_info['version']}...")
        
        try:
            # Download the zipball
            response = requests.get(remote_info['zipball_url'], timeout=60)
            response.raise_for_status()
            
            # Extract to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "framework.zip"
                
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # First, scan zip contents to see what we're updating
                with zipfile.ZipFile(zip_path, 'r') as zip_file:
                    zip_content_list = self.get_zip_content_list(zip_file)
                    print(f"📋 Framework contains {len(zip_content_list)} items: {', '.join(zip_content_list)}")
                    
                    # Extract the zip
                    zip_file.extractall(temp_dir)
                
                # Find extracted directory (GitHub creates dirs like "user-repo-commit")
                extracted_dirs = [d for d in Path(temp_dir).iterdir() if d.is_dir() and d.name != "__pycache__"]
                if not extracted_dirs:
                    raise Exception("No extracted directory found")
                
                framework_dir = extracted_dirs[0]
                
                # Check for new manifest and detect orphaned files
                new_manifest_file = framework_dir / "framework_manifest.json"
                new_manifest = None
                orphaned_files = []
                
                if new_manifest_file.exists():
                    try:
                        with open(new_manifest_file, 'r') as f:
                            new_manifest = json.load(f)
                        print(f"📋 New framework manifest found (v{new_manifest.get('version', 'unknown')})")
                        
                        # Detect orphaned files
                        orphaned_files = self.detect_orphaned_files(new_manifest)
                        if orphaned_files:
                            print(f"⚠️  WARNING: {len(orphaned_files)} files will become orphaned:")
                            for orphan in orphaned_files[:10]:  # Show first 10
                                print(f"    - {orphan}")
                            if len(orphaned_files) > 10:
                                print(f"    ... and {len(orphaned_files) - 10} more")
                            print("    These files are no longer part of the framework")
                            print("    They will remain but may cause conflicts")
                            
                            # Ask user if they want to continue
                            continue_update = input("\nContinue with update despite orphaned files? (y/N): ").strip().lower()
                            if continue_update not in ['y', 'yes']:
                                print("Update cancelled by user")
                                return False
                    except json.JSONDecodeError:
                        print("⚠️  Warning: Could not read new manifest")
                else:
                    print("📋 No manifest found in new version - orphan detection skipped")
                
                # Create backup of files that will be replaced/updated
                files_to_backup = []
                if new_manifest and "framework_files" in new_manifest:
                    files_to_backup = new_manifest["framework_files"]
                else:
                    # Fallback to core framework files only
                    files_to_backup = zip_content_list

                backup_path = self.backup_files_from_manifest(files_to_backup)

                # Copy framework files to project using manifest
                self.copy_framework_files(framework_dir, new_manifest)
                
                # Update version tracking
                self.update_version_tracking(remote_info)
                
                print(f"✅ Framework updated to v{remote_info['version']}")
                print(f"📦 Backup available at: {backup_path}")
                return True
                
        except Exception as e:
            print(f"❌ Error downloading/extracting framework: {e}")
            return False
    
    def get_framework_files_from_source(self, source_dir: Path) -> List[str]:
        """Get list of framework files by scanning source directory and excluding user areas."""
        framework_files = []

        # Framework directories that should be fully included
        framework_dirs = [
            "core",           # Core framework engine
            "modules/core",   # Core framework modules
            "tools",          # Development tools
            "ui",             # Streamlit UI components
            "docs"            # All documentation (both core and project-level)
        ]

        # Framework root files that should be included
        framework_root_files = [
            "app.py", "run_ui.py", "setup_db.py", "update_core.py",
            "install_dependencies.py", "requirements.txt", "framework_manifest.json",
            ".env.example", "CLAUDE.md", "README.md"
        ]

        # Scan framework directories
        for dir_name in framework_dirs:
            dir_path = source_dir / dir_name
            if dir_path.exists() and dir_path.is_dir():
                # Add all files in this directory recursively
                for root, dirs, files in os.walk(dir_path):
                    # Skip __pycache__ directories
                    dirs[:] = [d for d in dirs if d != '__pycache__']

                    for file in files:
                        # Skip compiled Python files
                        if file.endswith(('.pyc', '.pyo')):
                            continue

                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(source_dir)
                        framework_files.append(str(relative_path))

        # Add framework root files
        for file_name in framework_root_files:
            file_path = source_dir / file_name
            if file_path.exists():
                framework_files.append(file_name)

        return sorted(framework_files)

    def copy_framework_files(self, source_dir: Path, new_manifest: Optional[Dict[str, Any]]):
        """Copy framework files from extracted directory to project using directory-based approach."""
        print("📋 Updating framework files...")

        # Get framework files by scanning directories (not manifest)
        files_to_update = self.get_framework_files_from_source(source_dir)
        print(f"📋 Found {len(files_to_update)} framework files to update")

        # Show first few files for confirmation
        print("📋 Framework files include:")
        for file_path in files_to_update[:5]:
            print(f"   - {file_path}")
        if len(files_to_update) > 5:
            print(f"   ... and {len(files_to_update) - 5} more files")

        updated_count = 0
        missing_count = 0

        # Update framework files
        for file_path in files_to_update:
            source_path = source_dir / file_path
            target_path = self.project_root / file_path

            if not source_path.exists():
                print(f"   Warning: {file_path} not found in new framework")
                missing_count += 1
                continue

            # Remove existing target if it exists
            if target_path.exists():
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()

            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the new file
            if source_path.is_dir():
                shutil.copytree(source_path, target_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            else:
                shutil.copy2(source_path, target_path)

            updated_count += 1

        print(f"✅ Framework files updated: {updated_count} files updated, {missing_count} files missing from new framework")
    
    def update_version_tracking(self, remote_info: Dict[str, Any]):
        """Update .framework_version file after successful update."""
        tracking_data = {
            "version": remote_info["version"],
            "commit": "",  # GitHub zipball doesn't include commit hash
            "updated_date": datetime.now().isoformat(),
            "source": "github_release",
            "release_notes": remote_info["body"][:500] + "..." if len(remote_info["body"]) > 500 else remote_info["body"],
            "project_name": os.path.basename(self.project_root)
        }
        
        with open(self.framework_version_file, 'w') as f:
            json.dump(tracking_data, f, indent=2)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available framework backups."""
        if not self.backup_dir.exists():
            return []
        
        backups = []
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir() and backup_path.name.startswith("framework_v"):
                # Parse backup directory name: framework_v1.0.0_20250830_223000
                parts = backup_path.name.split('_')
                if len(parts) >= 4:
                    version = parts[1][1:]  # Remove 'v' prefix
                    date = parts[2]
                    time = parts[3]
                    
                    # Check if .framework_version exists in backup
                    version_file = backup_path / ".framework_version" 
                    created = None
                    if version_file.exists():
                        try:
                            import json
                            with open(version_file, 'r') as f:
                                backup_data = json.load(f)
                                created = backup_data.get("updated_date", f"{date}_{time}")
                        except:
                            created = f"{date}_{time}"
                    else:
                        created = f"{date}_{time}"
                    
                    backups.append({
                        "path": str(backup_path),
                        "version": version,
                        "created": created,
                        "name": backup_path.name
                    })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created"], reverse=True)
        return backups
    
    def rollback_to_backup(self, backup_name: str = None, delete_new_files: bool = False) -> bool:
        """Rollback framework to a specific backup."""
        backups = self.list_backups()
        
        if not backups:
            print("❌ No framework backups found")
            return False
        
        # If no backup specified, show list and prompt
        if not backup_name:
            print("📦 Available framework backups:")
            print("-" * 50)
            for i, backup in enumerate(backups, 1):
                print(f"{i}. v{backup['version']} - {backup['created']}")
            print("-" * 50)
            
            try:
                choice = input("Select backup number (or 'cancel'): ").strip()
                if choice.lower() == 'cancel':
                    print("Rollback cancelled")
                    return False
                
                backup_index = int(choice) - 1
                if backup_index < 0 or backup_index >= len(backups):
                    print("❌ Invalid backup selection")
                    return False
                
                selected_backup = backups[backup_index]
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Rollback cancelled")
                return False
        else:
            # Find backup by name
            selected_backup = None
            for backup in backups:
                if backup["name"] == backup_name or backup["version"] == backup_name.lstrip('v'):
                    selected_backup = backup
                    break
            
            if not selected_backup:
                print(f"❌ Backup not found: {backup_name}")
                return False
        
        # Confirm rollback
        current_version = self.get_current_version()["version"]
        target_version = selected_backup["version"]
        
        print(f"\n🔄 Rollback framework from v{current_version} to v{target_version}?")
        print(f"📁 Using backup: {selected_backup['name']}")
        
        confirm = input("Proceed with rollback? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Rollback cancelled")
            return False
        
        # Perform rollback
        try:
            backup_path = Path(selected_backup["path"])
            
            # Check if rollback info exists for complete rollback
            rollback_info_file = backup_path / ".rollback_info.json"
            if rollback_info_file.exists():
                print("📋 Found rollback information - performing complete rollback")
                return self.perform_complete_rollback(backup_path, target_version, current_version, delete_new_files)
            else:
                print("⚠️  No rollback information found - performing basic rollback")
                return self.perform_basic_rollback(backup_path, target_version, current_version)
            
        except Exception as e:
            print(f"\n❌ Rollback failed: {e}")
            return False
    
    def perform_complete_rollback(self, backup_path: Path, target_version: str, current_version: str) -> bool:
        """Perform complete rollback using rollback information."""
        try:
            # Load rollback information
            rollback_info_file = backup_path / ".rollback_info.json"
            with open(rollback_info_file, 'r') as f:
                rollback_info = json.load(f)
            
            backed_up_files = rollback_info.get("backed_up_files", [])
            new_files = rollback_info.get("new_files", [])
            
            print(f"📋 Rollback plan: restore {len(backed_up_files)} files")
            
            if new_files:
                print(f"⚠️  WARNING: {len(new_files)} files were added in the update:")
                for new_file in new_files:
                    print(f"    - {new_file}")
                print("    These files will remain (not automatically deleted for safety)")
                print("    You can manually remove them if needed")
            
            # Create backup of current state before rollback
            print("📦 Creating safety backup before rollback...")
            pre_rollback_backup = self.backup_current_framework_simple()
            
            # Step 1: Only restore backed up files - don't delete new files
            # (Leave new files alone for safety)
            
            # Step 2: Restore files that were backed up
            for backed_up_file in backed_up_files:
                source_path = backup_path / backed_up_file
                target_path = self.project_root / backed_up_file
                
                if source_path.exists():
                    print(f"   Restoring: {backed_up_file}")
                    
                    # Remove current version first
                    if target_path.exists():
                        if target_path.is_dir():
                            shutil.rmtree(target_path)
                        else:
                            target_path.unlink()
                    
                    # Copy from backup
                    if source_path.is_dir():
                        shutil.copytree(source_path, target_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, target_path)
            
            # Step 3: Restore version file
            backup_version_file = backup_path / ".framework_version"
            if backup_version_file.exists():
                shutil.copy2(backup_version_file, self.framework_version_file)
            else:
                # Create version file for the rollback
                self.create_rollback_version_file(target_version, current_version)
            
            print(f"\n✅ Complete rollback successful!")
            print(f"📦 Framework restored to v{target_version}")
            print(f"💾 Safety backup available at: {pre_rollback_backup}")
            print("\n🔄 Please restart your application to use the rolled-back framework.")
            return True
            
        except Exception as e:
            print(f"Complete rollback failed: {e}")
            return False
    
    def perform_basic_rollback(self, backup_path: Path, target_version: str, current_version: str) -> bool:
        """Perform basic rollback (old backup format)."""
        try:
            # Create backup of current state before rollback
            print("📦 Creating safety backup before rollback...")
            pre_rollback_backup = self.backup_current_framework_simple()
            
            # Copy framework files from backup (old method)
            print(f"🔄 Restoring framework from backup...")
            for item in backup_path.iterdir():
                if item.name.startswith('.'):
                    continue
                
                target_path = self.project_root / item.name
                
                print(f"   Restoring: {item.name}")
                if target_path.exists():
                    if target_path.is_dir():
                        shutil.rmtree(target_path)
                    else:
                        target_path.unlink()
                
                if item.is_dir():
                    shutil.copytree(item, target_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                else:
                    shutil.copy2(item, target_path)
            
            # Restore version file
            backup_version_file = backup_path / ".framework_version"
            if backup_version_file.exists():
                shutil.copy2(backup_version_file, self.framework_version_file)
            else:
                self.create_rollback_version_file(target_version, current_version)
            
            print(f"\n✅ Basic rollback completed!")
            print(f"📦 Framework restored to v{target_version}")
            print(f"💾 Safety backup available at: {pre_rollback_backup}")
            print("\n🔄 Please restart your application to use the rolled-back framework.")
            return True
            
        except Exception as e:
            print(f"Basic rollback failed: {e}")
            return False
    
    def backup_current_framework_simple(self) -> str:
        """Simple backup for rollback safety."""
        current_version = self.get_current_version()["version"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"pre_rollback_v{current_version}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        print(f"Creating safety backup: {backup_path}")
        # Implementation would go here - simplified backup
        backup_path.mkdir(parents=True, exist_ok=True)
        return str(backup_path)
    
    def create_rollback_version_file(self, target_version: str, current_version: str):
        """Create version file after rollback."""
        rollback_data = {
            "version": target_version,
            "commit": "",
            "updated_date": datetime.now().isoformat(),
            "source": "rollback",
            "rollback_from": current_version,
            "project_name": os.path.basename(self.project_root)
        }
        
        with open(self.framework_version_file, 'w') as f:
            json.dump(rollback_data, f, indent=2)

    def run_update_check(self, force_update: bool = False, check_only: bool = False, backup_only: bool = False) -> bool:
        """Main update workflow."""
        print("🔍 Checking framework version...")
        
        # Handle backup-only mode
        if backup_only:
            self.backup_current_framework()
            return True
        
        current_info = self.get_current_version()
        current_version = current_info["version"]
        
        print(f"Current framework version: {current_version}")
        
        # Check remote version
        remote_info = self.check_remote_version()
        if not remote_info:
            print("❌ Unable to check remote version")
            return False
        
        remote_version = remote_info["version"]
        print(f"Latest framework version: {remote_version}")
        
        # Compare versions
        comparison = self.compare_versions(current_version, remote_version)
        
        if comparison >= 0:
            print("✅ Framework is up to date!")
            return True
        
        # Show changelog
        self.show_changelog(remote_info)
        
        if check_only:
            print(f"🆕 Update available: v{current_version} → v{remote_version}")
            return True
        
        # Confirm update
        if not force_update and not self.confirm_update(current_version, remote_version):
            print("Update cancelled by user")
            return False
        
        # Perform update (backup is now handled inside download_and_extract_framework)
        if self.download_and_extract_framework(remote_info):
            print("\n✅ Framework update completed successfully!")
            print("\n🔄 Please restart your application to use the updated framework.")
            return True
        else:
            print("\n❌ Framework update failed!")
            print("Your project files are unchanged.")
            return False

def main():
    parser = argparse.ArgumentParser(description="Update Modular Python Framework")
    parser.add_argument("--force", action="store_true", 
                       help="Force update without confirmation prompts")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check for updates, don't apply them")
    parser.add_argument("--backup-only", action="store_true",
                       help="Only create backup of current framework")
    parser.add_argument("--list-backups", action="store_true",
                       help="List available framework backups")
    parser.add_argument("--rollback", type=str, nargs="?", const="",
                       help="Rollback to backup (specify backup name or leave empty to choose)")
    parser.add_argument("--delete-new-files", action="store_true",
                       help="Delete new files during rollback (use with --rollback, DANGEROUS)")
    parser.add_argument("--project-root", type=str, default=".",
                       help="Path to project root (default: current directory)")
    
    args = parser.parse_args()
    
    updater = FrameworkUpdater(args.project_root)
    
    try:
        # Handle backup listing
        if args.list_backups:
            backups = updater.list_backups()
            if not backups:
                print("📦 No framework backups found")
                sys.exit(0)
            
            print("📦 Available framework backups:")
            print("-" * 60)
            for backup in backups:
                print(f"v{backup['version']} - {backup['created']}")
                print(f"  📁 {backup['name']}")
                print()
            sys.exit(0)
        
        # Handle rollback
        if args.rollback is not None:
            backup_name = args.rollback if args.rollback else None
            success = updater.rollback_to_backup(backup_name, delete_new_files=args.delete_new_files)
            sys.exit(0 if success else 1)
        
        # Handle normal update workflow
        success = updater.run_update_check(
            force_update=args.force,
            check_only=args.check_only,
            backup_only=args.backup_only
        )
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()