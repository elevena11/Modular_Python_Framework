#!/usr/bin/env python3
"""
Framework Core Update Utility

This utility allows projects using the Modular Python Framework to check for
and apply framework updates while preserving their application modules.

Usage:
    python tools/update_core.py                # Check for updates
    python tools/update_core.py --force        # Force update without prompts
    python tools/update_core.py --check-only   # Only check, don't update
    python tools/update_core.py --backup-only  # Create backup of current framework
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
        
        # Framework core paths that will be updated
        self.core_paths = [
            "core/",
            "modules/core/",
            "tools/",
            "app.py",
            "setup_db.py",
            "requirements.txt",
            "framework_version.json"
        ]
    
    def get_current_version(self) -> Dict[str, Any]:
        """Get current framework version from local file."""
        if self.framework_version_file.exists():
            try:
                with open(self.framework_version_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print("Warning: Invalid or missing .framework_version file")
        
        # Try to read from framework_version.json as fallback
        framework_json = self.project_root / "framework_version.json"
        if framework_json.exists():
            try:
                with open(framework_json, 'r') as f:
                    version_data = json.load(f)
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
    
    def backup_current_framework(self) -> str:
        """Create backup of current framework."""
        current_version = self.get_current_version()["version"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"framework_v{current_version}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Creating backup: {backup_path}")
        
        # Backup core framework files
        for path_str in self.core_paths:
            source_path = self.project_root / path_str
            if source_path.exists():
                if source_path.is_dir():
                    shutil.copytree(source_path, backup_path / path_str)
                else:
                    backup_path.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, backup_path / path_str)
        
        # Backup version tracking file
        if self.framework_version_file.exists():
            shutil.copy2(self.framework_version_file, backup_path / ".framework_version")
        
        print(f"✅ Backup created: {backup_path}")
        return str(backup_path)
    
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
                
                # Extract and find the framework directory
                with zipfile.ZipFile(zip_path, 'r') as zip_file:
                    zip_file.extractall(temp_dir)
                
                # Find extracted directory (GitHub creates dirs like "user-repo-commit")
                extracted_dirs = [d for d in Path(temp_dir).iterdir() if d.is_dir() and d.name != "__pycache__"]
                if not extracted_dirs:
                    raise Exception("No extracted directory found")
                
                framework_dir = extracted_dirs[0]
                
                # Copy framework files to project
                self.copy_framework_files(framework_dir)
                
                # Update version tracking
                self.update_version_tracking(remote_info)
                
                print(f"✅ Framework updated to v{remote_info['version']}")
                return True
                
        except Exception as e:
            print(f"❌ Error downloading/extracting framework: {e}")
            return False
    
    def copy_framework_files(self, source_dir: Path):
        """Copy framework files from extracted directory to project."""
        for path_str in self.core_paths:
            source_path = source_dir / path_str
            target_path = self.project_root / path_str
            
            if not source_path.exists():
                continue
                
            if target_path.exists():
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
            
            if source_path.is_dir():
                shutil.copytree(source_path, target_path)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
    
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
        
        # Perform update
        backup_path = self.backup_current_framework()
        
        if self.download_and_extract_framework(remote_info):
            print("\n✅ Framework update completed successfully!")
            print(f"📦 Backup available at: {backup_path}")
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
    parser.add_argument("--project-root", type=str, default=".",
                       help="Path to project root (default: current directory)")
    
    args = parser.parse_args()
    
    updater = FrameworkUpdater(args.project_root)
    
    try:
        success = updater.run_update_check(
            force_update=args.force,
            check_only=args.check_only,
            backup_only=args.backup_only
        )
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Update cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()