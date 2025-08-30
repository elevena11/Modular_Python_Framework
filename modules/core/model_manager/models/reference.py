"""
modules/core/model_manager/models/reference.py
Model metadata and reference management.

Extracted from services.py as part of module refactoring.
"""

import time
from typing import Dict, Any


class ModelReference:
    """Tracks model usage and references."""
    def __init__(self, model_id: str, model_instance, model_config: Dict[str, Any]):
        self.model_id = model_id
        self.model_instance = model_instance
        self.model_config = model_config
        self.reference_count = 0
        self.last_accessed = time.time()
        self.created_at = time.time()
    
    def add_reference(self):
        """Add a reference to this model."""
        self.reference_count += 1
        self.last_accessed = time.time()
    
    def remove_reference(self):
        """Remove a reference from this model."""
        self.reference_count = max(0, self.reference_count - 1)
        self.last_accessed = time.time()
    
    def is_idle(self, idle_timeout: int) -> bool:
        """Check if model has been idle for too long."""
        return (time.time() - self.last_accessed) > idle_timeout