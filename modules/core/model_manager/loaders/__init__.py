"""
modules/core/model_manager/loaders/__init__.py
Model loading system components.

Exports:
- BaseLoader: Abstract base class for model loaders
- EmbeddingLoader: SentenceTransformer and embedding model loading
- TextGenerationLoader: T5, BERT, and text generation model loading
- LoaderFactory: Model loader selection and instantiation
"""

# Import extracted components
from .base import BaseLoader
from .embedding import EmbeddingLoader
from .text_generation import TextGenerationLoader
from .factory import LoaderFactory

__all__ = [
    'BaseLoader',
    'EmbeddingLoader',
    'TextGenerationLoader',
    'LoaderFactory',
]