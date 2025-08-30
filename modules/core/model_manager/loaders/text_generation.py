"""
modules/core/model_manager/loaders/text_generation.py
T5, BERT, and text generation model loading implementation.

Extracted from services.py as part of module refactoring.
"""

import logging
from typing import Dict, Any
from .base import BaseLoader
from core.error_utils import Result

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
            
            # Check if CPU usage is allowed
            if device == "cpu" and self.config.get("worker_pool.require_gpu", True):
                return Result.error(
                    code="CPU_NOT_ALLOWED",
                    message="GPU required for model loading, CPU usage disabled"
                )
            
            # Get model name from configuration
            model_name = self._get_model_config(model_id, "name")
            if not model_name:
                return Result.error(
                    code="MODEL_NAME_NOT_CONFIGURED",
                    message=f"Model name not configured for {model_id}"
                )
            
            # Set up CUDA device if needed
            if device.startswith("cuda"):
                self._setup_cuda_device(device)
            
            self.logger.info(f"Loading T5 model {model_name} on {device}")
            
            # Load T5 model and tokenizer
            from transformers import T5ForConditionalGeneration, AutoTokenizer
            
            model = T5ForConditionalGeneration.from_pretrained(model_name).to(device)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Test model with sample input to validate loading
            try:
                test_input = "test input"
                inputs = tokenizer(test_input, return_tensors="pt", truncation=True, max_length=32)
                inputs = {k: v.to(device) for k, v in inputs.items()}
                
                with model.no_grad_context() if hasattr(model, 'no_grad_context') else model.eval():
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