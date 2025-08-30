# Standards Development Guide

**Version: 2.0.2**  
**Updated: March 19, 2025**

This guide provides a comprehensive methodology for creating and maintaining standards for the Modular AI Framework. It's intended for those responsible for defining framework standards.

## 1. "Code First, Standards Second" Methodology

### Core Philosophy
Standards must reflect how the framework actually works, not how we think it should work. This means:

1. **Begin with Working Code**: Standards are derived from examining real implementations, not theoretical ideals
2. **Multiple References**: Examine 3-5 well-implemented modules to identify consistent patterns
3. **Intent Over Syntax**: Focus on the architectural purpose being served, not specific syntax
4. **Accommodate Variations**: Allow for valid implementation variations that serve the same purpose

### Practical Process
1. Identify modules that successfully implement a pattern
2. Analyze the commonalities and architectural principles
3. Draft a standard based on these real implementations
4. Validate the standard against existing code
5. Refine based on feedback and testing

## 2. Standards Development Process

### Step 1: Study Existing Code First
1. **Identify Working Implementations**: Find 3-5 well-designed modules implementing the pattern
2. **Extract Common Patterns**: Note how these modules address a specific architectural need
3. **Distinguish Intent from Syntax**: Identify the architectural purpose being served
4. **Note Variations**: Document different valid implementations that serve the same architectural purpose

### Step 2: Document the Standard
1. **Create Standard Documentation**: Write a zero-context markdown document
2. **Define JSON Validation**: Create the JSON standard definition for automated validation
3. **Test Validation**: Verify patterns correctly validate existing code
4. **Refine as Needed**: Adjust patterns to avoid false positives/negatives

### Step 3: Place Files
1. **Standard JSON**: Place in originating module's `standards/` directory
2. **Documentation File**: Place MD file with matching name in the same location

## 3. Zero-Context Documentation Principles

Each standard should be documented in a way that requires no prior knowledge:

1. **Completely Self-Contained**: All necessary information exists in one document
2. **Define All Terms**: Leave nothing implicit 
3. **Include Examples**: Show both correct and incorrect implementations
4. **Provide Rationale**: Explain why the standard exists
5. **Implementation Guide**: Clear step-by-step instructions
6. **Common Issues**: Address likely problems developers will face
7. **FAQ**: Answer common questions

### Standard Documentation Template

```markdown
# Standard Name

**Version: 1.0.0**

## Purpose
[Clear explanation of what problem this standard solves]

## Rationale
[Explain architectural reasons why this standard exists]

## Requirements
[Specific technical requirements for compliance]

## Implementation Guide
[Step-by-step guide with code examples]

## Common Issues and Solutions
[Address frequent implementation problems]

## Validation
[Explain how compliance is validated]

## FAQ
[Answers to common questions]
```

## 4. Standards Validation Status

The standards system is actively evolving:

1. **Implementation Status**:
   - **Active Standards**: Currently only few standards (e.g., ascii_console) are fully validated
   - **Draft Standards**: Most standards are in first draft form and undergoing refinement
   - **Incremental Development**: Standards are developed incrementally, focusing first on architecture

2. **Standard Maturity Levels**:
   - **Initial Draft**: First attempt at codifying a pattern, may need adjustment
   - **Working Draft**: Validated against multiple modules but still evolving
   - **Stable**: Well-tested pattern that accurately reflects framework architecture
   - **Deprecated**: Previously recommended pattern that is now outdated

3. **Current Focus**:
   - Getting architectural patterns right before enforcing strict validation
   - Refining validation patterns to accurately reflect real code patterns
   - Building a comprehensive library of examples for each standard

## 5. Creating Standard JSON Definitions

### Basic Structure

```json
{
  "id": "standard_id",
  "name": "Human-readable Standard Name",
  "version": "1.0.0",
  "description": "Brief description of the standard",
  "owner_module": "module.id",
  "requirements": [
    "Requirement 1",
    "Requirement 2"
  ],
  "validation": {
    "file_targets": {},
    "match_requirements": {},
    "patterns": {},
    "anti_patterns": []
  },
  "section": "Core Implementation Standards",
  "documentation": "Extended description of the standard"
}
```

### Defining Validation Rules

The `validation` section defines how compliance is verified:

#### File Targeting 
```json
"file_targets": {
  "pattern_name": ["api.py"],
  "another_pattern": ["services.py", "utils.py"],
  "ui_pattern": ["ui/*.py"]
}
```

Target only files where patterns should exist according to framework architecture.

#### Match Requirements
```json
"match_requirements": {
  "pattern_name": "all",
  "another_pattern": "either",
  "ui_pattern": "all"
}
```

- `all`: Pattern must exist in all targeted files (default for single file targets)
- `either`: Pattern must exist in at least one targeted file (use for true alternatives)

#### Validation Patterns
```json
"patterns": {
  "pattern_name": "regex_pattern_here",
  "another_pattern": "different_regex_pattern"
}
```

Regex patterns that implement validation checks.

#### Anti-Patterns
```json
"anti_patterns": [
  "regex_pattern_that_should_not_exist",
  "another_bad_pattern"
]
```

Patterns that should NOT be found in any target files.

## 6. Pattern Writing Best Practices

### 1. Study Working Code First
- Examine how the pattern is implemented in actual modules
- Identify the common elements and variations
- Note where the pattern is implemented (which files)
- Test your patterns against real code before finalizing

### 2. Write Patterns That Match Intent
```json
// Recognize both styles of dependency checking
"dependency_check": "(app_context\\.get_service\\s*\\([^)]*\\)[\\s\\S]*?if\\s+not|if\\s+not\\s+app_context\\.get_service\\s*\\([^)]*\\))"
```

This matches both:
```python
service = app_context.get_service("name")
if not service:
    # Handle

# AND

if not app_context.get_service("name"):
    # Handle
```

### 3. Handle Multiline Code
- Use `[\\s\\S]*?` instead of `.*` to match across lines
- The non-greedy `?` prevents overmatching
- Standard regex dot `.` doesn't match newlines by default

### 4. Use Precise Pattern Elements
- Use `[^)]*` to match content inside parentheses
- Use `[a-zA-Z_][a-zA-Z0-9_]*` to match variable names
- Avoid overly general patterns that might cause false positives

### 5. Be Flexible with Whitespace
- Use `\\s*` for flexible whitespace matching
- Don't require exact formatting to pass validation

### 6. Escape Special Characters
- Use double backslashes in JSON: `\\` not `\`
- Escape dots with `\\.` to match literal dots

### 7. Test Patterns Thoroughly
- Test against both compliant and non-compliant code
- Verify patterns don't create false positives or negatives
- Test with real code variations, including multiline code
- When validation failures occur, review the pattern first, not just the code

### 8. Revise Standards When Needed
- When well-designed code doesn't validate, consider updating the standard
- Document pattern revisions and their rationale
- Focus on validating intent rather than enforcing specific syntax

## 7. Common Validation Pattern Types

### 1. Function Definition Patterns

```json
"initialize_pattern": "def\\s+initialize\\s*\\(\\s*app_context\\s*\\)\\s*:"
```

Matches:
```python
def initialize(app_context):
```

### 2. Method Call Patterns

```json
"service_registration": "app_context\\.register_service\\s*\\(\\s*['\"][a-z0-9_.]+['\"]\\s*,"
```

Matches:
```python
app_context.register_service("service_name", service_instance)
```

### 3. Import Prohibition Patterns (Anti-patterns)

```json
"anti_patterns": [
  "from\\s+modules\\.[a-z]+\\.[a-z_]+\\s+import",
  "import\\s+modules\\.[a-z]+\\.[a-z_]+"
]
```

Catches forbidden imports:
```python
from modules.core.database import models  # Not allowed!
```

### 4. Conditional Logic Patterns

```json
"dependency_check": "(app_context\\.get_service\\s*\\([^)]*\\)[\\s\\S]*?if\\s+not|if\\s+not\\s+app_context\\.get_service\\s*\\([^)]*\\)|[a-zA-Z_][a-zA-Z0-9_]*\\s*=\\s*app_context\\.get_service\\s*\\([^)]*\\)[\\s\\S]*?if\\s+not\\s+[a-zA-Z_][a-zA-Z0-9_]*)"
```

Matches service existence checks.

### 5. Error Handling Patterns

```json
"error_handling": "try\\s*:[\\s\\S]*?except\\s+"
```

Matches try/except blocks including multiline blocks.

## 8. Error-Driven Knowledge System

Standards should create unique, searchable error messages that guide developers:

1. **Pattern Recognition Errors**: 
   - Format: "Missing pattern '[pattern_name]' in [file]"
   - Make pattern names descriptive and searchable

2. **Anti-Pattern Detection**:
   - Format: "Found anti-pattern '[pattern_name]' in [file]"
   - Use descriptive anti-pattern names

3. **File Requirements**:
   - Format: "Missing required file: [filename]"
   - Be specific about which file is required

### Designing Searchable Error Messages
- Create messages unique enough to be searchable
- Keep messages consistent across similar standards
- Focus on the architectural concept, not just syntax
- Use terminology consistent with documentation

### Connecting Errors to Documentation
- Ensure documentation explains each possible error message
- Include examples of how to fix specific error messages
- Group related errors in documentation sections
- Consider future tooling to directly map errors to solutions

## 9. Standards Improvement Process

Standards should evolve based on real-world feedback:

1. **Validation Testing**: Test against real modules to identify false positives/negatives
2. **Developer Feedback**: Collect feedback from module developers about clarity and usefulness
3. **Pattern Refinement**: Adjust patterns based on new understanding or evolving practices
4. **Documentation Updates**: Continuously improve documentation based on common questions
5. **Version Control**: Document and communicate changes to standards

Remember that the goal is to help developers understand and implement framework architecture correctly, not to enforce rigid syntax or structure.