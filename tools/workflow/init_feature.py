#!/usr/bin/env python3
"""
Feature Development Workflow Initializer

This script creates a new feature directory with pre-filled templates
to kickstart the systematic feature development workflow.

Usage:
    python init_feature.py "Smart Document Deduplication" "User mentioned they have duplicate documents"
    python init_feature.py "Cross-Reference Visualization" "Need interactive graph view of document relationships"
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import re


class FeatureInitializer:
    """Initializes a new feature development workflow directory."""
    
    def __init__(self, workflow_dir: str = None):
        """Initialize the feature initializer.
        
        Args:
            workflow_dir: Path to workflow directory. Auto-detects if None.
        """
        if workflow_dir is None:
            # Auto-detect workflow directory
            script_dir = Path(__file__).parent
            self.workflow_dir = script_dir
        else:
            self.workflow_dir = Path(workflow_dir)
        
        self.templates_dir = self.workflow_dir / "templates"
        self.active_features_dir = self.workflow_dir / "active_features"
        
        # Ensure directories exist
        self.active_features_dir.mkdir(exist_ok=True)
    
    def sanitize_feature_name(self, feature_name: str) -> str:
        """Convert feature name to filesystem-safe directory name.
        
        Args:
            feature_name: Human-readable feature name
            
        Returns:
            Sanitized directory name
        """
        # Convert to lowercase and replace spaces/special chars with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', feature_name.lower())
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        return sanitized
    
    def get_next_feature_number(self, base_name: str) -> int:
        """Get the next available feature number.
        
        Args:
            base_name: Base feature name
            
        Returns:
            Next available number
        """
        existing_dirs = list(self.active_features_dir.glob(f"{base_name}_*"))
        numbers = []
        
        for dir_path in existing_dirs:
            dir_name = dir_path.name
            if '_' in dir_name:
                try:
                    number = int(dir_name.split('_')[-1])
                    numbers.append(number)
                except ValueError:
                    continue
        
        return max(numbers) + 1 if numbers else 1
    
    def create_feature_directory(self, feature_name: str) -> Path:
        """Create feature directory with proper naming.
        
        Args:
            feature_name: Human-readable feature name
            
        Returns:
            Path to created directory
        """
        base_name = self.sanitize_feature_name(feature_name)
        feature_number = self.get_next_feature_number(base_name)
        
        dir_name = f"{base_name}_{feature_number:03d}"
        feature_dir = self.active_features_dir / dir_name
        
        feature_dir.mkdir(exist_ok=True)
        return feature_dir
    
    def fill_seed_template(self, feature_name: str, trigger: str, author: str = "Development Team") -> str:
        """Fill the SEED template with provided information.
        
        Args:
            feature_name: Name of the feature
            trigger: What sparked this idea
            author: Author name
            
        Returns:
            Filled template content
        """
        template_path = self.templates_dir / "SEED_TEMPLATE.md"
        
        if not template_path.exists():
            raise FileNotFoundError(f"SEED template not found at {template_path}")
        
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Replace placeholders
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        filled_content = template_content.replace("[Feature Name]", feature_name)
        filled_content = filled_content.replace("[YYYY-MM-DD]", current_date)
        filled_content = filled_content.replace("[Your Name]", author)
        filled_content = filled_content.replace("[What sparked this idea - user request, bug, observation, etc.]", trigger)
        
        return filled_content
    
    def copy_remaining_templates(self, feature_dir: Path) -> None:
        """Copy remaining phase templates to feature directory.
        
        Args:
            feature_dir: Feature directory path
        """
        templates = [
            ("BRAINSTORM_TEMPLATE.md", "02_BRAINSTORM.md"),
            ("PLAN_TEMPLATE.md", "03_PLAN.md"),
            ("TECHNICAL_MAP_TEMPLATE.md", "04_TECHNICAL_MAP.md")
        ]
        
        for template_name, target_name in templates:
            template_path = self.templates_dir / template_name
            target_path = feature_dir / target_name
            
            if template_path.exists():
                with open(template_path, 'r') as f:
                    content = f.read()
                
                # Replace feature name placeholder
                content = content.replace("[Feature Name]", feature_dir.name.replace('_', ' ').title())
                
                with open(target_path, 'w') as f:
                    f.write(content)
            else:
                print(f"Warning: Template {template_name} not found")
    
    def create_feature_readme(self, feature_dir: Path, feature_name: str, trigger: str) -> None:
        """Create a README file for the feature.
        
        Args:
            feature_dir: Feature directory path
            feature_name: Human-readable feature name
            trigger: What sparked this idea
        """
        readme_content = f"""# {feature_name}

**Status**: 🌱 SEED  
**Created**: {datetime.now().strftime("%Y-%m-%d")}  
**Current Phase**: SEED  

## Overview

{trigger}

## Development Progress

- [x] **SEED** - Initial idea captured
- [ ] **BRAINSTORM** - Explore possibilities and challenges
- [ ] **PLAN** - Define scope and approach
- [ ] **MAP** - Design technical implementation
- [ ] **TODO** - Create implementation tasks
- [ ] **IMPLEMENT** - Write code
- [ ] **TEST** - Verify functionality
- [ ] **DOCUMENT** - Create final documentation

## Phase Files

- `01_SEED.md` - Initial idea and trigger
- `02_BRAINSTORM.md` - Exploration and analysis
- `03_PLAN.md` - Scope and approach definition
- `04_TECHNICAL_MAP.md` - Technical implementation design

## Next Steps

1. Fill out the SEED phase completely
2. Move to BRAINSTORM phase
3. Follow the workflow systematically

## Workflow Reference

See `../../FEATURE_DEVELOPMENT_WORKFLOW.md` for complete workflow documentation.
"""
        
        readme_path = feature_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(readme_content)
    
    def initialize_feature(self, feature_name: str, trigger: str, author: str = "Development Team") -> Path:
        """Initialize a complete feature development workflow.
        
        Args:
            feature_name: Human-readable feature name
            trigger: What sparked this idea
            author: Author name
            
        Returns:
            Path to created feature directory
        """
        print(f"🌱 Initializing feature: {feature_name}")
        
        # Create feature directory
        feature_dir = self.create_feature_directory(feature_name)
        print(f"📁 Created directory: {feature_dir.name}")
        
        # Create filled SEED template
        seed_content = self.fill_seed_template(feature_name, trigger, author)
        seed_path = feature_dir / "01_SEED.md"
        with open(seed_path, 'w') as f:
            f.write(seed_content)
        print(f"📝 Created SEED template: {seed_path.name}")
        
        # Copy remaining templates
        self.copy_remaining_templates(feature_dir)
        print(f"📋 Copied remaining templates")
        
        # Create feature README
        self.create_feature_readme(feature_dir, feature_name, trigger)
        print(f"📚 Created feature README")
        
        print(f"✅ Feature '{feature_name}' initialized successfully!")
        print(f"📍 Location: {feature_dir}")
        print(f"🚀 Next: Edit {seed_path} to complete the SEED phase")
        
        return feature_dir
    
    def list_active_features(self) -> None:
        """List all active features in development."""
        active_features = list(self.active_features_dir.glob("*"))
        
        if not active_features:
            print("No active features found.")
            return
        
        print("🚧 Active Features:")
        for feature_dir in sorted(active_features):
            if feature_dir.is_dir():
                # Try to determine current phase
                phases = ["01_SEED.md", "02_BRAINSTORM.md", "03_PLAN.md", "04_TECHNICAL_MAP.md"]
                current_phase = "SEED"
                
                for i, phase_file in enumerate(phases):
                    if (feature_dir / phase_file).exists():
                        current_phase = phase_file.split('_')[1].replace('.md', '')
                
                feature_name = feature_dir.name.replace('_', ' ').title()
                print(f"  📂 {feature_name} ({current_phase})")
                print(f"     Location: {feature_dir}")


def main():
    """Main entry point for the feature initializer."""
    parser = argparse.ArgumentParser(
        description="Initialize a new feature development workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init_feature.py "Smart Document Deduplication" "User mentioned they have duplicate documents"
  python init_feature.py "Cross-Reference Visualization" "Need interactive graph view of document relationships"
  python init_feature.py --list
        """
    )
    
    parser.add_argument(
        'feature_name',
        nargs='?',
        help='Human-readable name for the feature'
    )
    
    parser.add_argument(
        'trigger',
        nargs='?',
        help='What sparked this idea (user request, bug, observation, etc.)'
    )
    
    parser.add_argument(
        '--author',
        default='Development Team',
        help='Author name for the feature (default: Development Team)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all active features'
    )
    
    parser.add_argument(
        '--workflow-dir',
        help='Path to workflow directory (auto-detects if not provided)'
    )
    
    args = parser.parse_args()
    
    # Initialize the feature initializer
    try:
        initializer = FeatureInitializer(args.workflow_dir)
    except Exception as e:
        print(f"❌ Error initializing: {e}")
        return 1
    
    # Handle list command
    if args.list:
        initializer.list_active_features()
        return 0
    
    # Validate required arguments
    if not args.feature_name or not args.trigger:
        print("❌ Error: Both feature_name and trigger are required")
        print("Usage: python init_feature.py \"Feature Name\" \"Trigger description\"")
        print("Use --help for more information")
        return 1
    
    # Initialize the feature
    try:
        initializer.initialize_feature(args.feature_name, args.trigger, args.author)
        return 0
    except Exception as e:
        print(f"❌ Error initializing feature: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())