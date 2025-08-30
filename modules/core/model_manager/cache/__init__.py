"""
modules/core/model_manager/cache/__init__.py
Caching system components for model results.

Exports:
- EmbeddingCache: Embedding result caching with TTL and memory management
"""

# Import extracted components
from .embedding_cache import EmbeddingCache

__all__ = [
    'EmbeddingCache',
]