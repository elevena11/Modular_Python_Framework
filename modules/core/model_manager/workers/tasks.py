"""
modules/core/model_manager/workers/tasks.py
Worker task and result data structures.

Extracted from services.py as part of module refactoring.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class WorkerTask:
    """Task for worker processing."""
    task_id: str
    task_type: str  # "embedding", "text_generation"
    model_name: str  # HuggingFace model name (e.g., "sentence-transformers/all-MiniLM-L6-v2")
    input_data: Any
    metadata: Dict[str, Any]
    created_at: float
    priority: int = 5


@dataclass
class WorkerResult:
    """Result from worker processing."""
    task_id: str
    worker_id: str
    success: bool
    data: Any = None
    error: str = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None