# Compliance Tool

A tool for managing and validating module compliance with framework standards in the Modular AI Framework.

## Purpose

The compliance tool helps developers maintain consistent implementation of framework standards across modules by:

1. Discovering framework standards automatically
2. Validating modules against standards through code analysis
3. Creating and updating compliance files
4. Generating framework-wide compliance reports

## Getting Started

### Install Dependencies

No additional packages are required beyond the standard framework dependencies.

### Basic Usage

```bash
# Initialize compliance files for modules that don't have them (never overwrites existing)
python compliance.py --init

# Validate and update a specific module
python compliance.py --validate core.database

# Validate and update all modules
python compliance.py --validate-all

# Generate a framework-wide compliance report
python compliance.py --report
```

## Command Reference

```bash
# Initialize compliance files for new modules (never overwrites existing files)
python compliance.py --init

# Validate and update compliance file for a specific module
python compliance.py --validate core.database

# Validate and update compliance files for all modules
python compliance.py --validate-all

# Validate with detailed console output for a specific module
python compliance.py --validate-verbose core.database

# Check compliance claims for a module without updating its file
python compliance.py --validate-claims core.database

# Generate a framework-wide compliance report
python compliance.py --report

# Debug tool functionality (standards discovery/validation)
python compliance.py --tool-debug [MODULE_ID]

# Enable verbose output with any command
python compliance.py --validate-all --verbose

# Save report to file instead of stdout
python compliance.py --report --output custom_report.md

# Generate comprehensive compliance report (includes all files and categorized violations)
python compliance.py --validate MODULE_ID --comprehensive
```

## Two-Tier Compliance System

The compliance tool provides two validation modes to balance learning with enforcement:

### Standard Mode (compliance.md)
- **Purpose**: Educational validation for learning framework patterns
- **Approach**: Encourages adoption of framework tools (import OR usage patterns)
- **Use Case**: Day-to-day development and teaching proper patterns
- **Command**: `python compliance.py --validate MODULE_ID` (default)

### Comprehensive Mode (compliance_comprehensive.md)
- **Purpose**: Production validation for architectural correctness
- **Approach**: Strict enforcement (import AND usage AND anti-pattern detection)
- **Use Case**: Pre-release validation and architectural reviews
- **Command**: `python compliance.py --validate MODULE_ID --comprehensive`

The comprehensive mode generates additional reports with:
- Complete file listing and violation categorization
- Context-aware violation explanations
- Smart categorization (Critical, Review Required, Context-Dependent)
- Detailed scanning of all module files including documentation

## Understanding Compliance Files

Each module in the framework includes a `compliance.md` file that documents which standards the module implements:

```markdown
# Module Compliance Status

## Module: core.database
## Version: 1.0.4

## Core Implementation Standards
- Settings API v2: Yes
- Error Handling v1: No
  - Missing pattern 'error_handling_pattern' in services.py
  - Missing required file: error_handler.py

## Database Standards
- SQLiteJSON for Complex Types: Yes
- Proper Transaction Handling: No
  - Found anti-pattern 'raw_transaction' in models.py

## Exceptions
# Custom database drivers can skip transaction handling guidance
# We implement a different approach to error handling based on DB specifics

## Last Compliance Review: 2025-03-16
## Reviewed By: Compliance Tool
```

### Key Components

1. **Module Information**: Identifies the module and its version
2. **Standards Sections**: Groups standards by their category
3. **Compliance Markers**: Each standard is marked as `Yes` or `No`
4. **Issue Details**: For `No` standards, specific issues are listed
5. **Exceptions Section**: Explains deliberate design decisions that differ from standards
6. **Review Information**: When the compliance was last checked and by whom

## Standards Discovery

The tool automatically discovers standards defined in JSON files within module directories:

```
modules/
  core/
    settings/
      standards/
        settings_api.json
    database/
      standards/
        database_transaction.json
```

Each standard contains:
- Basic identification (id, name, version)
- Pattern definitions for validation
- File targeting rules
- Anti-patterns to check for

## Understanding File Targeting

The tool uses a whitelist-based file targeting approach:

```json
"file_targets": {
  "pattern_name": ["api.py", "services.py"],
  "another_pattern": ["ui/*.py"]
}
```

File targeting rules:
- Root files: `api.py` checks only in module root
- Subdirectory paths: `ui/ui_gradio.py` checks specific file
- Root wildcards: `*.py` checks all Python files in root only
- Subdirectory wildcards: `ui/*.py` checks all Python files in ui/ only

## Match Requirements

Standards can specify whether patterns need to be in all target files or just one:

```json
"match_requirements": {
  "pattern_name": "either",  // At least one file must match
  "another_pattern": "all"   // All files must match
}
```

If not specified, the default is "either".

## Error Messages as Learning Tools

Error messages in the compliance file are designed to be searchable knowledge anchors:

1. Run validation on your module: `python compliance.py --validate your.module.id`
2. Look for detailed error messages in the compliance file
3. Search the framework documentation using the exact error text
4. Find specific implementation guidance for each issue

## Best Practices

1. **Regular Validation**: Check your module's compliance regularly during development
2. **Document Exceptions**: Explain any intentional deviations from standards
3. **Use Verbose Mode**: For detailed information, use `--validate-verbose`
4. **Generate Reports**: Create regular compliance reports to track progress
5. **Fix Recurring Issues**: Address common patterns of non-compliance in your development workflow

## Understanding Common Errors

### Missing Required Files

```
- Missing required file: error_handler.py
```

A file specified in the standard's `file_targets` was not found in your module. Create the file in the correct location.

### Missing Patterns

```
- Missing pattern 'service_registration' in api.py
```

A required pattern was not found in the specified file. Check the standard documentation for what this pattern should look like.

### Anti-Pattern Detection

```
- Found anti-pattern 'direct_import' in services.py
```

A pattern that should not be present was found. This often indicates improper implementation of a standard.

### ASCII Validation

```
- ASCII-error line(s) in helpers.py: 25, 124, 257
```

Non-ASCII characters were found in the specified file at these line numbers. The framework requires ASCII-only console output.

## Creating New Standards

To create a new standard, add a JSON file to your module's `standards/` directory:

```json
{
  "id": "your_standard_id",
  "name": "Your Standard Name",
  "version": "1.0.0",
  "description": "What your standard is about",
  "owner_module": "your.module.id",
  "requirements": [
    "List of requirements for compliance"
  ],
  "validation": {
    "file_targets": {
      "pattern_name": ["file1.py", "file2.py"]
    },
    "patterns": {
      "pattern_name": "regex_pattern"
    },
    "anti_patterns": [
      "regex_pattern_that_should_not_be_found"
    ]
  },
  "documentation": "Detailed explanation of the standard"
}
```

## Troubleshooting

### Standard Not Found

If your standard isn't being discovered, check:
- Is it in a `standards/` directory within a module?
- Does it have the required fields (id, name)?
- Is it valid JSON?

### False Negatives

If you're getting false negatives (standard not passing when it should):
- Check the file targeting patterns
- Verify that the regex patterns are correct
- Use `--tool-debug MODULE_ID` to see detailed validation

### False Positives

If you're getting false positives (standard passing when it shouldn't):
- Add anti-patterns to catch improper implementations
- Make sure "all" match requirement is used if needed
- Check if wildcards are matching unexpected files

## Contributing

When enhancing the compliance tool:
1. Keep the whitelist approach to file targeting
2. Maintain the binary Yes/No compliance model
3. Ensure error messages are searchable and specific
4. Keep the CLI simple and focused

## License

This tool is part of the Modular AI Framework and is subject to the same license terms.
