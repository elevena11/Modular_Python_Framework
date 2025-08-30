"""
modules/core/model_manager/__init__.py
Core Model Manager Module - Modular ML model management system.

Refactored Architecture:
- services.py: Clean orchestration layer
- workers/: Worker pool management and individual workers  
- cache/: Embedding caching system with TTL
- loaders/: Model loading abstractions and implementations
- models/: Model reference and metadata management

Key Components:
- ModelManagerService: Main orchestration service
- WorkerPool: Parallel processing management
- EmbeddingCache: Result caching with TTL
- LoaderFactory: Automatic model loader selection
- ModelReference: Model lifecycle tracking

Public API:
- generate_embeddings(): Text embedding generation
- generate_text(): Text generation processing
- get_service_status(): Comprehensive status reporting
"""

# Main service class
from .services import ModelManagerService

# Key modular components (optional direct access)
from .workers import WorkerPool, WorkerTask, WorkerResult, WorkerState, ModelWorker
from .cache import EmbeddingCache
from .loaders import LoaderFactory, BaseLoader, EmbeddingLoader, TextGenerationLoader
from .models import ModelReference

# Module metadata
__version__ = "2.0.0"
__author__ = "RAH Framework"

# Public API exports
__all__ = [
    # Main service
    'ModelManagerService',
    
    # Worker components
    'WorkerPool',
    'WorkerTask', 
    'WorkerResult',
    'WorkerState',
    'ModelWorker',
    
    # Caching
    'EmbeddingCache',
    
    # Loading system
    'LoaderFactory',
    'BaseLoader',
    'EmbeddingLoader',
    'TextGenerationLoader',
    
    # Model management
    'ModelReference',
]