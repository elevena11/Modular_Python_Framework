"""
modules/core/model_manager/models/__init__.py
Model utility components and data structures.

Exports:
- ModelReference: Model metadata and reference management
- ModelLifecycleManager: Model lifecycle management (loading, registration, release)
"""

# Import extracted components
from .reference import ModelReference
from .lifecycle import ModelLifecycleManager

__all__ = [
    'ModelReference',
    'ModelLifecycleManager',
]