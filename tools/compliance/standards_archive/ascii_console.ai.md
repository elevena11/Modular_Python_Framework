# STANDARD.ASCII_CONSOLE_OUTPUT [ID:STD-ASCII-001]
VERSION: 1.0.0
UPDATED: 2025-03-19
OWNER: core.framework

# HUMAN: This document defines the ASCII-only console output standard in AI-optimized format with maximum information density.

## STANDARD_DEFINITION [ID:STD-ASCII-DEF-001]
NAME: ASCII-only Console Output
PURPOSE: Ensure console output compatibility across all terminal environments
SCOPE: All console output in the system

## TECHNICAL_REQUIREMENTS [ID:STD-ASCII-REQ-001]
REQUIREMENT.ASCII_ONLY_OUTPUT: All console output must use ASCII characters only (codes 0-127)
REQUIREMENT.ASCII_ERROR_MESSAGES: Error messages must be in ASCII
REQUIREMENT.ASCII_LOG_MESSAGES: Log messages must be in ASCII
REQUIREMENT.ASCII_STATUS_MESSAGES: Status messages must be in ASCII
REQUIREMENT.ANSI_COLOR_PERMITTED: Standard ANSI color escape sequences are allowed

## VALIDATION_PATTERN [ID:STD-ASCII-VAL-001]
REGEX: ^([\\x00-\\x7F]|\\x1B\\[[0-9;]*[mK])*$
EXPLANATION: Matches ASCII characters (0-127) and ANSI color escape sequences
FILE_TARGETS: All Python files (*.py)

## IMPLEMENTATION_EXAMPLES [ID:STD-ASCII-IMPL-001]

EXAMPLE.CORRECT_IMPLEMENTATION [ID:STD-ASCII-IMPL-001-01]
```python
logger.info("Starting module initialization")
logger.warning("Database connection failed")
print("Processing complete: 100%")
# Using ANSI colors (allowed)
print("\033[31mError:\033[0m Connection failed")
```

EXAMPLE.INCORRECT_IMPLEMENTATION [ID:STD-ASCII-IMPL-001-02]
```python
logger.info("✅ Module initialization complete")  # Emoji not allowed
logger.warning("⚠️ Database connection failed")  # Emoji not allowed
print("Processing complete: 100% 🎉")  # Emoji not allowed
```

## COMPLIANCE_ISSUES [ID:STD-ASCII-ISS-001]

ISSUE.COPY_PASTED_CONTENT [ID:STD-ASCII-ISS-001-01]
DESCRIPTION: Text copied from websites or documents may contain invisible Unicode characters
DETECTION: Characters outside ASCII range in string literals
RESOLUTION: Manually review and replace non-ASCII characters

ISSUE.EMOJI_USE [ID:STD-ASCII-ISS-001-02]
DESCRIPTION: Emoji characters used in log or print statements
DETECTION: Visual identification or regex validation failure
RESOLUTION: Replace with ASCII-only alternatives (e.g., [SUCCESS], [WARNING])

ISSUE.UNICODE_SYMBOLS [ID:STD-ASCII-ISS-001-03]
DESCRIPTION: Non-ASCII symbols used for formatting or emphasis
DETECTION: Characters outside ASCII range in string literals
RESOLUTION: 
- Replace checkmark symbol with `[CHECK]` or `(done)`
- Replace right arrow symbol with `->` or `-->`
- Replace bullet point symbol with `*` or `-`

## REPLACEMENT_PATTERNS [ID:STD-ASCII-PAT-001]

PATTERN.EMOJI_REPLACEMENT [ID:STD-ASCII-PAT-001-01]
ORIGINAL: "✅ Operation complete"
REPLACEMENT: "[SUCCESS] Operation complete"

PATTERN.EMOJI_REPLACEMENT [ID:STD-ASCII-PAT-001-02]
ORIGINAL: "⚠️ Warning: connection timeout"
REPLACEMENT: "[WARNING] Warning: connection timeout"

PATTERN.EMOJI_REPLACEMENT [ID:STD-ASCII-PAT-001-03]
ORIGINAL: "🚫 Access denied"
REPLACEMENT: "[BLOCKED] Access denied"

PATTERN.SYMBOL_REPLACEMENT [ID:STD-ASCII-PAT-001-04]
ORIGINAL: "Step 1 → Step 2 → Step 3"
REPLACEMENT: "Step 1 -> Step 2 -> Step 3"

PATTERN.SYMBOL_REPLACEMENT [ID:STD-ASCII-PAT-001-05]
ORIGINAL: "• First item • Second item"
REPLACEMENT: "* First item * Second item"

## PERMITTED_PATTERNS [ID:STD-ASCII-PAT-002]

PATTERN.ANSI_COLOR_CODE [ID:STD-ASCII-PAT-002-01]
DESCRIPTION: Standard ANSI color escape sequences
EXAMPLE: "\033[31mError:\033[0m"
IS_VALID: true

PATTERN.STANDARD_ASCII [ID:STD-ASCII-PAT-002-02]
DESCRIPTION: Standard ASCII range (0-127)
EXAMPLE: "abcABC123!@#"
IS_VALID: true

## META_INFORMATION
DOCUMENT.ID: STD-ASCII-001
DOCUMENT.VERSION: 1.0.0
DOCUMENT.DATE: 2025-03-19
DOCUMENT.AUDIENCE: [AI developers, Human developers]
DOCUMENT.STATUS: Active
DOCUMENT.PURPOSE: Define standard for ASCII-only console output

# HUMAN: This document focuses specifically on the technical requirements and examples needed to shape code correctly, omitting more verbose explanations while retaining essential implementation patterns.
