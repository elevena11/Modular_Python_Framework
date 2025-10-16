"""
modules/core/model_manager/loaders/embedding.py
SentenceTransformer and embedding model loading implementation.

Extracted from services.py as part of module refactoring.
"""

import logging
from typing import Dict, Any
from .base import BaseLoader
from core.error_utils import Result
from core.paths import ensure_data_path

# Module identity for logging
MODULE_ID = "core.model_manager.loaders"


class EmbeddingLoader(BaseLoader):
    """Loader for SentenceTransformer embedding models."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize embedding loader.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.logger = logging.getLogger(f"{MODULE_ID}.embedding")
    
    def supports_model(self, model_id: str) -> bool:
        """Check if this loader supports the given model.
        
        Args:
            model_id: Model identifier to check
            
        Returns:
            True if this is an embedding model
        """
        # Check if model is configured as embedding type
        model_type = self._get_model_config(model_id, "type")
        return model_type == "embedding" or model_id == "embedding"
    
    def get_model_type(self) -> str:
        """Get the model type this loader handles.
        
        Returns:
            Model type identifier
        """
        return "embedding"
    
    async def load_model(self, model_id: str, device: str) -> Result:
        """Load a SentenceTransformer embedding model.
        
        Args:
            model_id: Identifier for the embedding model to load
            device: Target device (e.g., 'cuda:0', 'cpu')
            
        Returns:
            Result with loaded model instance and metadata
        """
        try:
            # Validate device
            if not self._validate_device(device):
                return Result.error(
                    code="INVALID_DEVICE",
                    message=f"Invalid device format: {device}"
                )

            # Note: Removed CPU refusal check - models can explicitly request CPU now
            # This is part of device-agnostic architecture

            # Get model path from configuration - try local_path first, fallback to name
            model_path = self._get_model_config(model_id, "local_path")
            model_name = self._get_model_config(model_id, "name")

            # Use local_path if available, otherwise use name (HuggingFace path)
            # With new simplified API, model_id IS the HuggingFace model name if no config exists
            if model_path:
                model_path_or_name = model_path
            elif model_name:
                model_path_or_name = model_name
            else:
                # New simplified API: model_id is the HuggingFace model name directly
                model_path_or_name = model_id
                self.logger.info(f"Using model_id as HuggingFace model name: {model_id}")

            # Set up CUDA device if needed
            if device.startswith("cuda"):
                self._setup_cuda_device(device)

            self.logger.info(f"Loading SentenceTransformer model {model_path_or_name} on {device}")

            # Load SentenceTransformer model with framework's cache directory
            from sentence_transformers import SentenceTransformer

            # Get cache directory from config (defaults to "models" if not set)
            cache_dir_name = self.config.get("models_cache_dir", "models")
            models_cache_dir = ensure_data_path(cache_dir_name)

            model = SentenceTransformer(
                model_path_or_name,
                device=device,
                cache_folder=models_cache_dir
            )

            # Get model dimension from the model's architecture
            try:
                # Get dimension directly from model without encoding
                dimension = model.get_sentence_embedding_dimension()
                self.logger.info(f"Successfully loaded embedding model: {model_id} (dimension: {dimension})")
            except Exception as e:
                # Fallback: try a simple encoding with numpy conversion
                try:
                    sample_embedding = model.encode(["test"], convert_to_numpy=True)
                    dimension = sample_embedding.shape[1] if len(sample_embedding.shape) > 1 else sample_embedding.shape[0]
                    self.logger.info(f"Successfully loaded embedding model: {model_id} (dimension: {dimension})")
                except Exception as e2:
                    self.logger.warning(f"Could not determine embedding dimension: {e}, {e2}")
                    dimension = None
            
            return Result.success(data={
                "model": model,
                "model_id": model_id,
                "model_type": self.get_model_type(),
                "dimension": dimension,
                "device": device,
                "loader_type": self.__class__.__name__,
                "model_path": model_path
            })
            
        except ImportError as e:
            return Result.error(
                code="DEPENDENCY_MISSING",
                message="SentenceTransformers library not available",
                details={"error": str(e)}
            )
        except Exception as e:
            self.logger.error(f"Failed to load embedding model {model_id} on {device}: {e}")
            return Result.error(
                code="EMBEDDING_MODEL_LOAD_ERROR",
                message=f"Failed to load embedding model {model_id}",
                details={"error": str(e), "device": device}
            )
    
    async def download_only(self, model_id: str) -> Result:
        """Download embedding model files without loading into memory.

        Uses HuggingFace's snapshot_download to download model files to cache.
        If model is already cached, returns immediately without downloading.

        Args:
            model_id: Identifier for the embedding model to download

        Returns:
            Result with download status and cache location
        """
        try:
            # Get model path from configuration - try local_path first, fallback to name
            model_path = self._get_model_config(model_id, "local_path")
            model_name = self._get_model_config(model_id, "name")

            # Use local_path if available, otherwise use name (HuggingFace path)
            # With new simplified API, model_id IS the HuggingFace model name if no config exists
            if model_path:
                model_path_or_name = model_path
            elif model_name:
                model_path_or_name = model_name
            else:
                # New simplified API: model_id is the HuggingFace model name directly
                model_path_or_name = model_id
                self.logger.info(f"Using model_id as HuggingFace model name: {model_id}")

            # Check if this is a local path or HuggingFace model
            from pathlib import Path
            if Path(model_path_or_name).exists():
                # Local model - already exists
                self.logger.info(f"Model {model_id} found locally at {model_path_or_name}")
                return Result.success(data={
                    "model_id": model_id,
                    "cached": True,
                    "location": model_path_or_name,
                    "source": "local"
                })

            # HuggingFace model - check cache first, download if needed
            try:
                from huggingface_hub import snapshot_download

                # Get cache directory from config (defaults to "models" if not set)
                cache_dir_name = self.config.get("models_cache_dir", "models")
                models_cache_dir = ensure_data_path(cache_dir_name)

                # First, try to load from cache only (no network)
                try:
                    cache_dir = snapshot_download(
                        repo_id=model_path_or_name,
                        cache_dir=models_cache_dir,
                        local_files_only=True,  # Check cache only, no download
                    )
                    self.logger.info(f"Model {model_id} found in cache at {cache_dir}")

                    return Result.success(data={
                        "model_id": model_id,
                        "cached": True,
                        "location": cache_dir,
                        "source": "huggingface_cache",
                        "model_name": model_path_or_name
                    })

                except Exception:
                    # Not in cache, need to download
                    self.logger.info(f"Model {model_path_or_name} not in cache, downloading to {models_cache_dir}...")

                    cache_dir = snapshot_download(
                        repo_id=model_path_or_name,
                        cache_dir=models_cache_dir,
                        local_files_only=False,  # Allow download
                        resume_download=True,    # Resume if interrupted
                    )

                    self.logger.info(f"Model {model_id} downloaded to cache at {cache_dir}")

                    return Result.success(data={
                        "model_id": model_id,
                        "cached": True,
                        "location": cache_dir,
                        "source": "huggingface_download",
                        "model_name": model_path_or_name
                    })

            except Exception as e:
                self.logger.warning(f"Failed to download model {model_path_or_name}: {e}")
                # Don't fail - model might still load via SentenceTransformers' cache
                return Result.success(data={
                    "model_id": model_id,
                    "cached": "unknown",
                    "location": "unknown",
                    "source": "huggingface_cache_check_failed",
                    "model_name": model_path_or_name,
                    "warning": str(e)
                })

        except Exception as e:
            self.logger.error(f"Failed to download model {model_id}: {e}")
            return Result.error(
                code="MODEL_DOWNLOAD_ERROR",
                message=f"Failed to download model {model_id}",
                details={"error": str(e)}
            )

    def get_loader_info(self) -> Dict[str, Any]:
        """Get embedding loader information.
        
        Returns:
            Dictionary with loader metadata
        """
        info = super().get_loader_info()
        info.update({
            "supported_formats": ["SentenceTransformer"],
            "output_format": "embeddings",
            "requires_tokenizer": False,
        })
        return info