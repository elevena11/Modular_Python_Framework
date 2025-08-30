#!/usr/bin/env python3
"""
Tool to create specifications from existing code or templates.
Supports documentation-driven development workflow.
"""

import os
import sys
import argparse
import ast
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

def parse_python_file(file_path: str) -> Dict[str, Any]:
    """Parse Python file and extract metadata for specification."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Extract classes and functions
        classes = []
        functions = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'docstring': ast.get_docstring(node) or '',
                    'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                })
            elif isinstance(node, ast.FunctionDef) and not any(node in cls.body for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef)):
                functions.append({
                    'name': node.name,
                    'docstring': ast.get_docstring(node) or '',
                    'args': [arg.arg for arg in node.args.args]
                })
            elif isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                imports.extend([f"{module}.{alias.name}" for alias in node.names])
        
        # Extract module docstring
        module_docstring = ast.get_docstring(tree) or ''
        
        return {
            'file_path': file_path,
            'module_docstring': module_docstring,
            'classes': classes,
            'functions': functions,
            'imports': imports
        }
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return {}

def get_relative_path(file_path: str, base_path: str = None) -> str:
    """Get relative path from project root."""
    if base_path is None:
        # Try to find project root by looking for common indicators
        current = Path(file_path).parent
        while current != current.parent:
            if any((current / indicator).exists() for indicator in ['.git', 'requirements.txt', 'CLAUDE.md']):
                base_path = str(current)
                break
            current = current.parent
        else:
            base_path = os.getcwd()
    
    return os.path.relpath(file_path, base_path)

def create_spec_from_code(code_file: str, template_file: str = None) -> str:
    """Create specification from existing code file."""
    
    # Default template
    if template_file is None:
        template_file = "docs-spec/templates/component.spec.md"
    
    # Parse the code file
    parsed = parse_python_file(code_file)
    if not parsed:
        return ""
    
    # Read template
    try:
        with open(template_file, 'r') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Template file not found: {template_file}")
        return ""
    
    # Extract component name from file path
    component_name = Path(code_file).stem.replace('_', ' ').title()
    relative_path = get_relative_path(code_file)
    
    # Generate content
    spec_content = template.replace('[Component Name]', component_name)
    spec_content = spec_content.replace('[path/to/implementation.py]', relative_path)
    spec_content = spec_content.replace('YYYY-MM-DD', datetime.now().strftime('%Y-%m-%d'))
    spec_content = spec_content.replace('[Draft | Active | Deprecated]', 'Active')
    
    # Add discovered classes and functions
    if parsed['classes']:
        classes_section = "\\n### Discovered Classes\\n\\n"
        for cls in parsed['classes']:
            classes_section += f"#### `{cls['name']}`\\n"
            if cls['docstring']:
                classes_section += f"```\\n{cls['docstring']}\\n```\\n\\n"
            if cls['methods']:
                classes_section += f"**Methods**: {', '.join(cls['methods'])}\\n\\n"
        
        # Insert after "### Classes" section
        spec_content = spec_content.replace("### Classes", f"### Classes\\n{classes_section}")
    
    if parsed['functions']:
        functions_section = "\\n### Discovered Functions\\n\\n"
        for func in parsed['functions']:
            functions_section += f"#### `{func['name']}()`\\n"
            if func['docstring']:
                functions_section += f"```\\n{func['docstring']}\\n```\\n\\n"
            if func['args']:
                functions_section += f"**Parameters**: {', '.join(func['args'])}\\n\\n"
        
        # Insert after "### Functions" section
        spec_content = spec_content.replace("### Functions", f"### Functions\\n{functions_section}")
    
    return spec_content

def create_spec_from_template(component_name: str, component_path: str, template_file: str = None) -> str:
    """Create specification from template for new component."""
    
    if template_file is None:
        template_file = "docs-spec/templates/component.spec.md"
    
    try:
        with open(template_file, 'r') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Template file not found: {template_file}")
        return ""
    
    # Replace placeholders
    spec_content = template.replace('[Component Name]', component_name)
    spec_content = spec_content.replace('[path/to/implementation.py]', component_path)
    spec_content = spec_content.replace('YYYY-MM-DD', datetime.now().strftime('%Y-%m-%d'))
    spec_content = spec_content.replace('[Draft | Active | Deprecated]', 'Draft')
    
    return spec_content

def get_spec_file_path(code_file: str) -> str:
    """Generate specification file path based on code file path."""
    
    # Convert code path to spec path
    # modules/core/database/api.py -> docs-spec/modules/core/database/api.spec.md
    
    relative_path = get_relative_path(code_file)
    
    # Remove file extension and add .spec.md
    path_parts = Path(relative_path).parts
    spec_path = Path("docs-spec") / Path(*path_parts)
    spec_path = spec_path.with_suffix('.spec.md')
    
    return str(spec_path)

def main():
    parser = argparse.ArgumentParser(description="Create component specifications")
    parser.add_argument('--from-code', help='Create spec from existing code file')
    parser.add_argument('--template', help='Create spec from template for new component')
    parser.add_argument('--name', help='Component name (for template mode)')
    parser.add_argument('--output', help='Output file path (auto-generated if not specified)')
    parser.add_argument('--template-file', help='Custom template file path')
    
    args = parser.parse_args()
    
    if not args.from_code and not args.template:
        print("Error: Must specify either --from-code or --template")
        sys.exit(1)
    
    spec_content = ""
    output_path = ""
    
    if args.from_code:
        if not os.path.exists(args.from_code):
            print(f"Error: Code file not found: {args.from_code}")
            sys.exit(1)
        
        spec_content = create_spec_from_code(args.from_code, args.template_file)
        output_path = args.output or get_spec_file_path(args.from_code)
        
    elif args.template:
        if not args.name:
            print("Error: --name required when using --template")
            sys.exit(1)
        
        spec_content = create_spec_from_template(args.name, args.template, args.template_file)
        output_path = args.output or f"docs-spec/{args.template.replace('.py', '.spec.md')}"
    
    if not spec_content:
        print("Error: Failed to generate specification content")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write specification file
    with open(output_path, 'w') as f:
        f.write(spec_content)
    
    print(f"Specification created: {output_path}")
    print(f"\\nNext steps:")
    print(f"1. Review and complete the specification: {output_path}")
    print(f"2. Use the specification for implementation guidance")
    print(f"3. Validate implementation matches specification")

if __name__ == "__main__":
    main()