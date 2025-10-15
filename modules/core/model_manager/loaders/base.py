"""
modules/core/model_manager/loaders/base.py
Abstract base classes and common patterns for model loading.

Extracted from services.py as part of module refactoring.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from core.error_utils import Result

# Module identity for logging
MODULE_ID = "core.model_manager.loaders"


class BaseLoader(ABC):
    """Abstract base class for model loaders."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize base loader.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(f"{MODULE_ID}.{self.__class__.__name__.lower()}")
    
    @abstractmethod
    async def load_model(self, model_id: str, device: str) -> Result:
        """Load a model instance.

        Args:
            model_id: Identifier for the model to load
            device: Target device (e.g., 'cuda:0', 'cpu')

        Returns:
            Result with loaded model instance and metadata
        """
        pass

    @abstractmethod
    async def download_only(self, model_id: str) -> Result:
        """Download model files without loading into memory.

        This is used for model verification during startup. It checks if the model
        is already cached locally, and downloads it if needed, but never loads it
        into memory.

        Args:
            model_id: Identifier for the model to download

        Returns:
            Result with download status (cached=True if already exists)
        """
        pass

    @abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """Check if this loader supports the given model.
        
        Args:
            model_id: Model identifier to check
            
        Returns:
            True if this loader can handle the model
        """
        pass
    
    @abstractmethod
    def get_model_type(self) -> str:
        """Get the model type this loader handles.
        
        Returns:
            String identifier for model type (e.g., 'embedding', 'text_generation')
        """
        pass
    
    def _validate_device(self, device: str) -> bool:
        """Validate device string format.
        
        Args:
            device: Device string to validate
            
        Returns:
            True if device format is valid
        """
        if device == "cpu":
            return True
        
        if device.startswith("cuda:"):
            try:
                device_idx = int(device.split(':')[1])
                return device_idx >= 0
            except (IndexError, ValueError):
                return False
        
        return False
    
    def _setup_cuda_device(self, device: str):
        """Set up CUDA device context.
        
        Args:
            device: Target CUDA device
            
        Raises:
            RuntimeError: If CUDA setup fails
        """
        if device.startswith("cuda"):
            try:
                import torch
                device_idx = int(device.split(':')[1]) if ':' in device else 0
                torch.cuda.set_device(device_idx)
                torch.cuda.empty_cache()
                torch.cuda.synchronize(device_idx)
                self.logger.debug(f"CUDA device {device} ready")
            except (ImportError, RuntimeError) as e:
                raise RuntimeError(f"CUDA setup failed for {device}: {e}")
    
    def _get_model_config(self, model_id: str, key: str, default=None):
        """Get model-specific configuration value.
        
        Args:
            model_id: Model identifier
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        config_key = f"models.{model_id}.{key}"
        return self.config.get(config_key, default)
    
    def get_loader_info(self) -> Dict[str, Any]:
        """Get loader information and status.
        
        Returns:
            Dictionary with loader metadata
        """
        return {
            "loader_type": self.__class__.__name__,
            "model_type": self.get_model_type(),
            "supports_cuda": True,  # Most loaders support CUDA
            "supports_cpu": True,   # Most loaders support CPU
        }