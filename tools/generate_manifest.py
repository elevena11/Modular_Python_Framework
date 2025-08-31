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
            "framework_version.json",
            "framework_manifest.json",  # Include the manifest itself
            ".env.example",
            "CLAUDE.md",
            "core/",
            "modules/core/",
            "tools/",
            "ui/",
            "docs/"
        ]
        
        # Patterns to exclude from framework files
        self.exclude_patterns = [
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".DS_Store",
            "Thumbs.db",
            "*.log"
        ]
    
    def should_exclude(self, path: Path) -> bool:
        """Check if a file should be excluded from the manifest."""
        import fnmatch
        
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path.name, pattern):
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
    
    def generate_manifest(self) -> Dict[str, Any]:
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
        
        # Read current version
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
        """Get current version information."""
        version_file = self.project_root / "framework_version.json"
        if version_file.exists():
            try:
                with open(version_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        return {"version": "1.0.0"}
    
    def save_manifest(self, manifest: Dict[str, Any], output_file: str = "framework_manifest.json") -> None:
        """Save manifest to file."""
        output_path = self.project_root / output_file
        
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"💾 Manifest saved to: {output_path}")
    
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
    
    args = parser.parse_args()
    
    try:
        generator = ManifestGenerator(args.project_root)
        
        print("🚀 Generating Framework Manifest")
        print("=" * 50)
        
        # Generate manifest
        manifest = generator.generate_manifest()
        
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