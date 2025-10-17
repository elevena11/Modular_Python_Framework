#!/usr/bin/env python3
"""
Framework Manifest Generator

Generates a manifest of all framework files for release.
This manifest will be used by the next version's updater to detect orphaned files.

Usage:
    python tools/generate_manifest.py
    python tools/generate_manifest.py --output custom_manifest.json
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import argparse
import fnmatch

class ManifestGenerator:
    """Generates manifest of framework files for release."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()

        # Directories and files that are part of the framework
        self.framework_patterns = [
            "app.py",
            "run_ui.py",
            "setup_db.py",
            "update_core.py",
            "install_dependencies.py",
            "requirements.txt",
            "framework_manifest.json",  # Include the manifest itself
            ".env.example",
            "CLAUDE.md",
            "core/",
            "modules/core/",
            "tools/",
            "ui/",
            "docs/"
        ]

        # Load gitignore patterns
        self.gitignore_patterns = self._load_gitignore()

        # Additional patterns to exclude (beyond gitignore)
        self.additional_excludes = [
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "__pycache__"
        ]

    def _load_gitignore(self) -> List[str]:
        """Load and parse .gitignore file."""
        gitignore_file = self.project_root / ".gitignore"
        patterns = []

        if not gitignore_file.exists():
            print("⚠️  No .gitignore file found")
            return patterns

        try:
            with open(gitignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        patterns.append(line)

            print(f"📋 Loaded {len(patterns)} patterns from .gitignore")
        except Exception as e:
            print(f"⚠️  Error reading .gitignore: {e}")

        return patterns

    def should_exclude(self, path: Path) -> bool:
        """Check if a file should be excluded from the manifest."""
        # Get path relative to project root for gitignore matching
        try:
            rel_path = path.relative_to(self.project_root)
            rel_path_str = str(rel_path)
        except ValueError:
            # Path is outside project root
            return True

        # Check gitignore patterns
        for pattern in self.gitignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith('/'):
                dir_pattern = pattern.rstrip('/')
                # Match if path starts with this directory
                if rel_path_str.startswith(dir_pattern + '/') or rel_path_str == dir_pattern:
                    return True
                # Also match any part of the path
                for part in rel_path.parts:
                    if fnmatch.fnmatch(part, dir_pattern):
                        return True
            # Handle file/glob patterns
            else:
                # Check full path match
                if fnmatch.fnmatch(rel_path_str, pattern):
                    return True
                # Check filename match
                if fnmatch.fnmatch(path.name, pattern):
                    return True
                # Check if any path component matches (for patterns like .doc_index)
                for part in rel_path.parts:
                    if fnmatch.fnmatch(part, pattern):
                        return True

        # Check additional excludes
        for pattern in self.additional_excludes:
            if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(rel_path_str, pattern):
                return True

        return False
    
    def scan_directory(self, directory: Path, relative_to: Path) -> List[str]:
        """Recursively scan directory and return relative paths."""
        files = []
        
        if not directory.exists() or not directory.is_dir():
            return files
        
        for item in directory.rglob("*"):
            if self.should_exclude(item):
                continue
                
            # Get path relative to project root
            try:
                relative_path = item.relative_to(relative_to)
                files.append(str(relative_path))
            except ValueError:
                # Skip files outside project root
                continue
        
        return files
    
    def generate_manifest(self, version: str = None) -> Dict[str, Any]:
        """Generate complete framework manifest."""
        print("🔍 Scanning framework files...")

        all_files = []

        # Process each framework pattern
        for pattern in self.framework_patterns:
            pattern_path = self.project_root / pattern

            if pattern_path.exists():
                if pattern_path.is_file():
                    if not self.should_exclude(pattern_path):
                        all_files.append(pattern)
                        print(f"   Added file: {pattern}")
                elif pattern_path.is_dir():
                    # Scan directory recursively
                    dir_files = self.scan_directory(pattern_path, self.project_root)
                    all_files.extend(dir_files)
                    print(f"   Added directory: {pattern} ({len(dir_files)} files)")
            else:
                print(f"   Skipping missing: {pattern}")

        # Get version (either from arg or prompt)
        if version:
            version_info = {"version": version}
            print(f"🏷️  Using version: {version}")
        else:
            version_info = self.get_version_info()

        # Create manifest
        manifest = {
            "version": version_info.get("version", "1.0.0"),
            "generated_at": datetime.now().isoformat(),
            "framework_files": sorted(list(set(all_files))),  # Remove duplicates and sort
            "file_count": len(all_files),
            "generator": "tools/generate_manifest.py"
        }

        print(f"✅ Generated manifest with {manifest['file_count']} framework files")
        return manifest
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get version information from user input."""
        print("\n📝 Version Information")
        print("=" * 30)
        
        # Get current version from existing manifest if available
        current_version = "1.0.0"
        manifest_file = self.project_root / "framework_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r') as f:
                    current_manifest = json.load(f)
                    current_version = current_manifest.get("version", "1.0.0")
                    print(f"Current version: {current_version}")
            except json.JSONDecodeError:
                pass
        
        # Prompt for new version
        while True:
            new_version = input(f"Enter new version (current: {current_version}): ").strip()
            if not new_version:
                new_version = current_version
                break
            
            # Basic version validation (x.y.z format)
            if not new_version.replace('.', '').replace('-', '').replace('+', '').isalnum():
                print("❌ Invalid version format. Use semantic versioning (e.g., 1.2.3)")
                continue
            
            break
        
        print(f"🏷️  Using version: {new_version}")
        return {"version": new_version}
    
    def save_manifest(self, manifest: Dict[str, Any], output_file: str = "framework_manifest.json") -> None:
        """Save manifest to file."""
        output_path = self.project_root / output_file

        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"💾 Manifest saved to: {output_path}")

        # Also update .framework_version to match manifest version
        self.update_framework_version(manifest["version"])

    def update_framework_version(self, version: str) -> None:
        """Update .framework_version file to match manifest version."""
        framework_version_file = self.project_root / ".framework_version"

        # Read existing .framework_version if it exists
        existing_data = {}
        if framework_version_file.exists():
            try:
                with open(framework_version_file, 'r') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                pass  # Start fresh if corrupted

        # Update version data
        version_data = {
            "version": version,
            "commit": existing_data.get("commit", ""),
            "updated_date": datetime.now().isoformat(),
            "source": "manifest_generation",
            "project_name": existing_data.get("project_name", "Modular_Python_Framework")
        }

        # Preserve additional fields if they exist
        for key, value in existing_data.items():
            if key not in version_data:
                version_data[key] = value

        with open(framework_version_file, 'w') as f:
            json.dump(version_data, f, indent=2)

        print(f"🔄 Updated .framework_version to v{version}")
    
    def validate_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Validate that manifest files actually exist."""
        print("🔍 Validating manifest...")
        
        missing_files = []
        for file_path in manifest["framework_files"]:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Validation failed: {len(missing_files)} files missing:")
            for missing in missing_files[:10]:  # Show first 10
                print(f"   - {missing}")
            if len(missing_files) > 10:
                print(f"   ... and {len(missing_files) - 10} more")
            return False
        
        print("✅ Manifest validation passed")
        return True

def main():
    parser = argparse.ArgumentParser(description="Generate framework manifest for release")
    parser.add_argument("--output", type=str, default="framework_manifest.json",
                       help="Output manifest file name (default: framework_manifest.json)")
    parser.add_argument("--validate", action="store_true",
                       help="Validate manifest after generation")
    parser.add_argument("--project-root", type=str, default=".",
                       help="Path to project root (default: current directory)")
    parser.add_argument("--version", type=str, default=None,
                       help="Specify version directly (skip prompt)")

    args = parser.parse_args()
    
    try:
        generator = ManifestGenerator(args.project_root)
        
        print("🚀 Generating Framework Manifest")
        print("=" * 50)

        # Generate manifest
        manifest = generator.generate_manifest(version=args.version)
        
        # Validate if requested
        if args.validate:
            if not generator.validate_manifest(manifest):
                print("❌ Manifest validation failed")
                return 1
        
        # Save manifest
        generator.save_manifest(manifest, args.output)
        
        print(f"\n✅ Framework manifest generation completed!")
        print(f"📦 Version: {manifest['version']}")
        print(f"📁 Files tracked: {manifest['file_count']}")
        print(f"💾 Saved to: {args.output}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())