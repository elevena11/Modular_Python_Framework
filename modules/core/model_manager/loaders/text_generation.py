"""
modules/core/model_manager/loaders/text_generation.py
T5, BERT, and text generation model loading implementation.

Extracted from services.py as part of module refactoring.
"""

import logging
from typing import Dict, Any
from .base import BaseLoader
from core.error_utils import Result
from core.paths import ensure_data_path

# Module identity for logging
MODULE_ID = "core.model_manager.loaders"


class TextGenerationLoader(BaseLoader):
    """Loader for T5 and other text generation models."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize text generation loader.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.logger = logging.getLogger(f"{MODULE_ID}.text_generation")
    
    def supports_model(self, model_id: str) -> bool:
        """Check if this loader supports the given model.
        
        Args:
            model_id: Model identifier to check
            
        Returns:
            True if this is a text generation model
        """
        # Check if model is configured as text generation type
        model_type = self._get_model_config(model_id, "type")
        return model_type == "text_generation" or model_id in ["t5_summarizer"]
    
    def get_model_type(self) -> str:
        """Get the model type this loader handles.
        
        Returns:
            Model type identifier
        """
        return "text_generation"
    
    async def load_model(self, model_id: str, device: str) -> Result:
        """Load a T5 or other text generation model.
        
        Args:
            model_id: Identifier for the text generation model to load
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

            # Get model name from configuration
            # With new simplified API, model_id IS the HuggingFace model name if no config exists
            model_name = self._get_model_config(model_id, "name")
            if not model_name:
                # New simplified API: model_id is the HuggingFace model name directly
                model_name = model_id
                self.logger.info(f"Using model_id as HuggingFace model name: {model_id}")

            # Set up CUDA device if needed
            if device.startswith("cuda"):
                self._setup_cuda_device(device)

            self.logger.info(f"Loading T5 model {model_name} on {device}")

            # Load T5 model and tokenizer with framework's cache directory
            from transformers import T5ForConditionalGeneration, AutoTokenizer

            # Get cache directory from config (defaults to "models" if not set)
            cache_dir_name = self.config.get("models_cache_dir", "models")
            models_cache_dir = ensure_data_path(cache_dir_name)

            model = T5ForConditionalGeneration.from_pretrained(
                model_name,
                cache_dir=models_cache_dir
            ).to(device)
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=models_cache_dir
            )
            
            # Test model with sample input to validate loading
            try:
                import torch

                test_input = "test input"
                inputs = tokenizer(test_input, return_tensors="pt", truncation=True, max_length=32)
                inputs = {k: v.to(device) for k, v in inputs.items()}

                # Use torch.no_grad() for inference (correct PyTorch pattern)
                model.eval()  # Set to evaluation mode
                with torch.no_grad():
                    # Quick forward pass to validate
                    _ = model.generate(**inputs, max_length=40, num_beams=2, early_stopping=True)

                self.logger.info(f"Successfully validated T5 model: {model_id} on {device}")
            except Exception as e:
                self.logger.warning(f"Model validation warning: {e}")
            
            return Result.success(data={
                "model": model,
                "tokenizer": tokenizer,
                "model_id": model_id,
                "model_type": self.get_model_type(),
                "device": device,
                "loader_type": self.__class__.__name__,
                "model_name": model_name
            })
            
        except ImportError as e:
            return Result.error(
                code="DEPENDENCY_MISSING",
                message="Transformers library not available",
                details={"error": str(e)}
            )
        except Exception as e:
            self.logger.error(f"Failed to load T5 model {model_id} on {device}: {e}")
            return Result.error(
                code="T5_MODEL_LOAD_ERROR",
                message=f"Failed to load T5 model {model_id}",
                details={"error": str(e), "device": device}
            )
    
    async def download_only(self, model_id: str) -> Result:
        """Download text generation model files without loading into memory.

        Uses HuggingFace's snapshot_download to download model files to cache.
        If model is already cached, returns immediately without downloading.

        Args:
            model_id: Identifier for the text generation model to download

        Returns:
            Result with download status and cache location
        """
        try:
            # Get model name from configuration
            # With new simplified API, model_id IS the HuggingFace model name if no config exists
            model_name = self._get_model_config(model_id, "name")
            if not model_name:
                # New simplified API: model_id is the HuggingFace model name directly
                model_name = model_id
                self.logger.info(f"Using model_id as HuggingFace model name: {model_id}")

            # Check if this is a local path or HuggingFace model
            from pathlib import Path
            if Path(model_name).exists():
                # Local model - already exists
                self.logger.info(f"Model {model_id} found locally at {model_name}")
                return Result.success(data={
                    "model_id": model_id,
                    "cached": True,
                    "location": model_name,
                    "source": "local"
                })

            # HuggingFace model - use snapshot_download to cache it
            try:
                from huggingface_hub import snapshot_download

                # Get cache directory from config (defaults to "models" if not set)
                cache_dir_name = self.config.get("models_cache_dir", "models")
                models_cache_dir = ensure_data_path(cache_dir_name)

                self.logger.info(f"Downloading model {model_name} to {models_cache_dir} (if not already cached)...")

                # Download to cache (or verify cache if already exists)
                # This does NOT load the model into memory
                cache_dir = snapshot_download(
                    repo_id=model_name,
                    cache_dir=models_cache_dir,
                    local_files_only=False,  # Allow download if not cached
                    resume_download=True,     # Resume if interrupted
                )

                self.logger.info(f"Model {model_id} cached at {cache_dir}")

                return Result.success(data={
                    "model_id": model_id,
                    "cached": True,
                    "location": cache_dir,
                    "source": "huggingface",
                    "model_name": model_name
                })

            except Exception as e:
                self.logger.error(f"Failed to download model {model_name}: {e}")
                return Result.error(
                    code="MODEL_DOWNLOAD_FAILED",
                    message=f"Failed to download model {model_id}",
                    details={"error": str(e), "model_name": model_name}
                )

        except Exception as e:
            self.logger.error(f"Failed to download model {model_id}: {e}")
            return Result.error(
                code="MODEL_DOWNLOAD_ERROR",
                message=f"Failed to download model {model_id}",
                details={"error": str(e)}
            )

    def get_loader_info(self) -> Dict[str, Any]:
        """Get text generation loader information.
        
        Returns:
            Dictionary with loader metadata
        """
        info = super().get_loader_info()
        info.update({
            "supported_formats": ["T5", "BERT", "AutoModel"],
            "output_format": "text",
            "requires_tokenizer": True,
        })
        return info