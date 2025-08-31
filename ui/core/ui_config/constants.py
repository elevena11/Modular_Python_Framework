"""
ui/core/ui_config/constants.py
Constants for UI configuration.
"""

# Protected elements that cannot be disabled
PROTECTED_ELEMENTS = [
    "core.database.database_viewer",      # Database Viewer
    "standard.llm_instruction.llm_instruction", # LLM Instruction Handler
    # Add other essential elements here
]

# Configuration defaults
DEFAULT_CONFIG_VERSION = "1.0.0"
DEFAULT_ELEMENT_ORDER = 100