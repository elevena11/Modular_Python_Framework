"""
modules/core/model_manager/loaders/factory.py
Loader factory pattern for automatic model loader selection.

Extracted from services.py as part of module refactoring.
"""

import logging
from typing import Dict, Any, List, Optional
from .base import BaseLoader
from .embedding import EmbeddingLoader
from .text_generation import TextGenerationLoader
from core.error_utils import Result

# Module identity for logging
MODULE_ID = "core.model_manager.loaders"


class LoaderFactory:
    """Factory for automatic model loader selection and instantiation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize loader factory.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(f"{MODULE_ID}.factory")
        
        # Initialize all available loaders
        self._loaders: List[BaseLoader] = [
            EmbeddingLoader(config),
            TextGenerationLoader(config),
        ]
        
        self.logger.info(f"Loader factory initialized with {len(self._loaders)} loaders")
    
    def get_loader_for_model(self, model_id: str) -> Optional[BaseLoader]:
        """Get the appropriate loader for a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Loader instance that supports the model, or None if not found
        """
        for loader in self._loaders:
            if loader.supports_model(model_id):
                self.logger.debug(f"Selected {loader.__class__.__name__} for model {model_id}")
                return loader
        
        self.logger.warning(f"No loader found for model {model_id}")
        return None
    
    async def load_model(self, model_id: str, device: str) -> Result:
        """Load a model using the appropriate loader.

        Args:
            model_id: Model identifier
            device: Target device

        Returns:
            Result with loaded model or error
        """
        try:
            # Find appropriate loader
            loader = self.get_loader_for_model(model_id)
            if not loader:
                return Result.error(
                    code="NO_LOADER_FOUND",
                    message=f"No loader available for model {model_id}",
                    details={"available_loaders": [l.__class__.__name__ for l in self._loaders]}
                )

            # Load model using selected loader
            self.logger.info(f"Loading model {model_id} on {device} using {loader.__class__.__name__}")
            return await loader.load_model(model_id, device)

        except Exception as e:
            self.logger.error(f"Factory model loading error: {e}")
            return Result.error(
                code="FACTORY_LOAD_ERROR",
                message=f"Factory failed to load model {model_id}",
                details={"error": str(e), "device": device}
            )

    async def download_only(self, model_id: str) -> Result:
        """Download model files without loading into memory.

        Uses the appropriate loader to download/verify model files without
        loading them into memory. If model is already cached, returns immediately.

        Args:
            model_id: Model identifier

        Returns:
            Result with download status
        """
        try:
            # Find appropriate loader
            loader = self.get_loader_for_model(model_id)
            if not loader:
                return Result.error(
                    code="NO_LOADER_FOUND",
                    message=f"No loader available for model {model_id}",
                    details={"available_loaders": [l.__class__.__name__ for l in self._loaders]}
                )

            # Download model using selected loader (no memory loading)
            self.logger.info(f"Downloading/verifying model {model_id} using {loader.__class__.__name__}")
            return await loader.download_only(model_id)

        except Exception as e:
            self.logger.error(f"Factory model download error: {e}")
            return Result.error(
                code="FACTORY_DOWNLOAD_ERROR",
                message=f"Factory failed to download model {model_id}",
                details={"error": str(e)}
            )
    
    def get_supported_models(self) -> Dict[str, List[str]]:
        """Get all models supported by available loaders.
        
        Returns:
            Dictionary mapping loader types to their capabilities
        """
        supported = {}
        for loader in self._loaders:
            loader_info = loader.get_loader_info()
            supported[loader.get_model_type()] = loader_info
        
        return supported
    
    def get_loader_by_type(self, model_type: str) -> Optional[BaseLoader]:
        """Get loader by model type.
        
        Args:
            model_type: Type of model (e.g., 'embedding', 'text_generation')
            
        Returns:
            Loader instance or None if not found
        """
        for loader in self._loaders:
            if loader.get_model_type() == model_type:
                return loader
        
        return None
    
    def register_loader(self, loader: BaseLoader):
        """Register a new loader with the factory.
        
        Args:
            loader: Loader instance to register
        """
        self._loaders.append(loader)
        self.logger.info(f"Registered new loader: {loader.__class__.__name__}")
    
    def get_factory_status(self) -> Dict[str, Any]:
        """Get factory status and loader information.
        
        Returns:
            Status information dictionary
        """
        return {
            "total_loaders": len(self._loaders),
            "loader_types": [loader.get_model_type() for loader in self._loaders],
            "loader_classes": [loader.__class__.__name__ for loader in self._loaders],
            "supported_models": self.get_supported_models()
        }