"""
modules/core/model_manager/workers/states.py
Worker state management and enumeration.

Extracted from services.py as part of module refactoring.
"""

from enum import Enum


class WorkerState(Enum):
    """Worker state enumeration."""
    IDLE = "idle"
    BUSY = "busy"
    LOADING = "loading"
    UNLOADING = "unloading"
    ERROR = "error"
    SHUTDOWN = "shutdown"