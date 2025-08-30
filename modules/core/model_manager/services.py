"""
modules/core/model_manager/services.py
Model Manager Service - Clean orchestration layer using modular components.

Refactored from monolithic services.py to use:
- workers/: Worker pool management and individual workers
- cache/: Embedding caching system  
- loaders/: Model loading abstractions and implementations
- models/: Model reference and metadata management

Provides high-level API for:
- Model loading and management
- Embedding generation with caching
- Text generation processing
- Worker pool coordination
- Resource management
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Union
from core.error_utils import Result

# Import modular components
from .workers import WorkerPool, WorkerTask, WorkerResult
from .cache import EmbeddingCache
from .loaders import LoaderFactory
from .models import ModelReference

# Module identity (matches MODULE_ID in api.py)
MODULE_ID = "core.model_manager"
logger = logging.getLogger(MODULE_ID)


class ModelManagerService:
    """Centralized model management service using modular architecture."""
    
    def __init__(self, app_context):
        """Initialize model manager service.
        
        Args:
            app_context: Application context for framework integration
        """
        self.app_context = app_context
        self.logger = logging.getLogger(MODULE_ID)
        self.config = {}
        
        # Initialize modular components
        self.worker_pool = None
        self.embedding_cache = None
        self.loader_factory = None
        
        # Model registry
        self._loaded_models: Dict[str, ModelReference] = {}
        
        # Initialization state
        self._initialized = False
        
        self.logger.info("Model Manager Service initialized with modular architecture")
    
    def setup_infrastructure(self):
        """Phase 1: Set up infrastructure - NO service access."""
        self.logger.info(f"{MODULE_ID}: Setting up infrastructure")
    
    async def initialize(self, settings=None):
        """Phase 2: Initialize service with component orchestration."""
        try:
            self.logger.info(f"{MODULE_ID}: Initializing service with modular components")
            
            # Get configuration
            await self._load_configuration()
            
            # Initialize components
            await self._initialize_components()
            
            # Initialize worker pool if enabled
            if self.config.get("worker_pool.enabled", True):
                pool_result = await self.worker_pool.initialize()
                if not pool_result.success:
                    self.logger.warning(f"Worker pool initialization failed: {pool_result.error}")
            
            self._initialized = True
            self.logger.info(f"{MODULE_ID}: Service initialization completed successfully")
            return Result.success(data={"initialized": True})
            
        except Exception as e:
            self.logger.error(f"{MODULE_ID}: Service initialization failed: {e}")
            return Result.error(
                code="SERVICE_INIT_FAILED",
                message="Failed to initialize model manager service",
                details={"error": str(e)}
            )
    
    async def _load_configuration(self):
        """Load configuration from settings service."""
        try:
            settings_service = self.app_context.get_service("core.settings.service")
            if settings_service:
                # Get model manager specific settings
                # Import the Pydantic model
                from .settings import ModelManagerSettings
                
                # Get model manager specific settings
                settings_result = await settings_service.get_typed_settings(
                    module_id=MODULE_ID,
                    model_class=ModelManagerSettings,
                    database_name="settings"
                )
                if settings_result.success:
                    settings_data = settings_result.data
                    
                    # Convert Pydantic settings to config dictionary
                    self.config = self._convert_settings_to_config(settings_data)
                    self.logger.info("Loaded configuration from settings service")
                else:
                    self.logger.warning("Failed to load typed settings, using defaults")
                    self.config = self._get_default_config()
            else:
                self.logger.warning("Settings service not available, using defaults")
                self.config = self._get_default_config()
                
        except Exception as e:
            self.logger.error(f"Configuration loading error: {e}")
            self.config = self._get_default_config()
    
    def _convert_settings_to_config(self, settings) -> Dict[str, Any]:
        """Convert Pydantic settings to configuration dictionary.
        
        Args:
            settings: Pydantic settings object
            
        Returns:
            Configuration dictionary
        """
        # Extract nested settings from Pydantic model structure
        worker_pool = getattr(settings, 'worker_pool', None)
        embedding_cache = getattr(settings, 'embedding_cache', None)
        embedding_model = getattr(settings, 'embedding_model', None)
        t5_summarizer = getattr(settings, 't5_summarizer', None)
        
        return {
            # Worker pool settings
            "worker_pool.enabled": getattr(worker_pool, 'enabled', True) if worker_pool else True,
            "worker_pool.num_workers": getattr(worker_pool, 'num_workers', 2) if worker_pool else 2,
            "worker_pool.devices": getattr(worker_pool, 'devices', ["cuda:0", "cuda:1"]) if worker_pool else ["cuda:0", "cuda:1"],
            "worker_pool.require_gpu": getattr(worker_pool, 'require_gpu', True) if worker_pool else True,
            "worker_pool.queue_timeout": getattr(worker_pool, 'queue_timeout', 30) if worker_pool else 30,
            "worker_pool.model_idle_timeout": getattr(worker_pool, 'model_idle_timeout', 300) if worker_pool else 300,
            "worker_pool.preload_embeddings": getattr(worker_pool, 'preload_embeddings', False) if worker_pool else False,
            "worker_pool.load_balancing": getattr(worker_pool, 'load_balancing', "round_robin") if worker_pool else "round_robin",
            
            # Embedding cache settings
            "embedding_cache.enabled": getattr(embedding_cache, 'enabled', True) if embedding_cache else True,
            "embedding_cache.max_cache_size": getattr(embedding_cache, 'max_cache_size', 10000) if embedding_cache else 10000,
            "embedding_cache.ttl_seconds": getattr(embedding_cache, 'ttl_seconds', 3600) if embedding_cache else 3600,
            
            # Model settings
            "models.embedding.local_path": getattr(embedding_model, 'local_path', None) if embedding_model else None,
            "models.t5_summarizer.name": getattr(t5_summarizer, 'name', None) if t5_summarizer else None,
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "worker_pool.enabled": True,
            "worker_pool.num_workers": 2,
            "worker_pool.devices": ["cuda:0", "cuda:1"],
            "worker_pool.require_gpu": True,
            "worker_pool.queue_timeout": 30,
            "worker_pool.model_idle_timeout": 300,
            "worker_pool.preload_embeddings": True,
            "worker_pool.load_balancing": "round_robin",
            "embedding_cache.enabled": True,
            "embedding_cache.max_cache_size": 10000,
            "embedding_cache.ttl_seconds": 3600,
        }
    
    async def _initialize_components(self):
        """Initialize modular components."""
        # Initialize embedding cache
        self.embedding_cache = EmbeddingCache(self.config)
        
        # Initialize loader factory
        self.loader_factory = LoaderFactory(self.config)
        
        # Initialize worker pool
        self.worker_pool = WorkerPool(self.config, self)
        
        self.logger.info("Modular components initialized successfully")
    
    async def generate_embeddings(self, texts: Union[str, List[str]], model_id: str = "embedding") -> Result:
        """Generate embeddings for text(s) using worker pool or direct loading.
        
        Args:
            texts: Text(s) to embed
            model_id: Model identifier for embeddings
            
        Returns:
            Result with embedding data
        """
        try:
            if not self._initialized:
                return Result.error(
                    code="SERVICE_NOT_INITIALIZED",
                    message="Model manager service not initialized"
                )
            
            # Check cache first if enabled
            cache_result = await self.embedding_cache.get_embeddings(texts, model_id)
            if cache_result.success:
                self.logger.debug(f"Cache hit for {len(texts) if isinstance(texts, list) else 1} text(s)")
                return cache_result
            
            # Use worker pool if available
            if self.worker_pool and self.worker_pool.is_enabled:
                return await self._generate_embeddings_worker_pool(texts, model_id)
            else:
                # Fallback to direct model loading
                return await self._generate_embeddings_direct(texts, model_id)
                
        except Exception as e:
            self.logger.error(f"Embedding generation error: {e}")
            return Result.error(
                code="EMBEDDING_GENERATION_ERROR",
                message="Failed to generate embeddings",
                details={"error": str(e), "model_id": model_id}
            )
    
    async def _generate_embeddings_worker_pool(self, texts: Union[str, List[str]], model_id: str) -> Result:
        """Generate embeddings using worker pool.
        
        Args:
            texts: Text(s) to embed
            model_id: Model identifier
            
        Returns:
            Result with embedding data
        """
        try:
            task_id = str(uuid.uuid4())
            task = WorkerTask(
                task_id=task_id,
                task_type="embedding",
                model_id=model_id,
                input_data=texts,
                metadata={},
                created_at=time.time()
            )
            
            # Submit task to worker pool
            result = await self.worker_pool.submit_task(task)
            
            if result and result.success:
                # Cache the results
                await self.embedding_cache.cache_embeddings(texts, result.data["embeddings"], model_id)
                
                return Result.success(data={
                    "embeddings": result.data["embeddings"],
                    "model_id": model_id,
                    "cached": False,
                    "processing_time": result.processing_time,
                    "worker_id": result.worker_id
                })
            else:
                error_msg = result.error if result else "No result returned"
                return Result.error(
                    code="WORKER_POOL_PROCESSING_FAILED",
                    message=f"Worker pool processing failed: {error_msg}"
                )
                
        except Exception as e:
            self.logger.error(f"Worker pool embedding error: {e}")
            return Result.error(
                code="WORKER_POOL_ERROR",
                message="Worker pool embedding generation failed",
                details={"error": str(e)}
            )
    
    async def _generate_embeddings_direct(self, texts: Union[str, List[str]], model_id: str) -> Result:
        """Generate embeddings using direct model loading.
        
        Args:
            texts: Text(s) to embed
            model_id: Model identifier
            
        Returns:
            Result with embedding data
        """
        try:
            # Get or load model
            model_result = await self._get_or_load_model(model_id, "cuda:0")
            if not model_result.success:
                return model_result
            
            model_data = model_result.data
            model = model_data["model"]
            
            # Generate embeddings
            start_time = time.time()
            
            if isinstance(texts, str):
                embeddings = model.encode([texts])
                result_embeddings = embeddings[0].tolist()
            else:
                embeddings = model.encode(texts)
                result_embeddings = [emb.tolist() for emb in embeddings]
            
            processing_time = time.time() - start_time
            
            # Cache the results
            await self.embedding_cache.cache_embeddings(texts, result_embeddings, model_id)
            
            return Result.success(data={
                "embeddings": result_embeddings,
                "model_id": model_id,
                "cached": False,
                "processing_time": processing_time,
                "dimension": len(result_embeddings[0] if isinstance(result_embeddings[0], list) else result_embeddings)
            })
            
        except Exception as e:
            self.logger.error(f"Direct embedding generation error: {e}")
            return Result.error(
                code="DIRECT_EMBEDDING_ERROR",
                message="Direct embedding generation failed",
                details={"error": str(e)}
            )
    
    async def generate_text(self, input_text: str, model_id: str = "t5_summarizer", **kwargs) -> Result:
        """Generate text using specified model.
        
        Args:
            input_text: Input text for generation
            model_id: Model identifier for text generation
            **kwargs: Additional generation parameters
            
        Returns:
            Result with generated text
        """
        try:
            if not self._initialized:
                return Result.error(
                    code="SERVICE_NOT_INITIALIZED",
                    message="Model manager service not initialized"
                )
            
            # Use worker pool if available
            if self.worker_pool and self.worker_pool.is_enabled:
                return await self._generate_text_worker_pool(input_text, model_id, kwargs)
            else:
                # Fallback to direct model loading
                return await self._generate_text_direct(input_text, model_id, kwargs)
                
        except Exception as e:
            self.logger.error(f"Text generation error: {e}")
            return Result.error(
                code="TEXT_GENERATION_ERROR",
                message="Failed to generate text",
                details={"error": str(e), "model_id": model_id}
            )
    
    async def _generate_text_worker_pool(self, input_text: str, model_id: str, params: Dict[str, Any]) -> Result:
        """Generate text using worker pool.
        
        Args:
            input_text: Input text
            model_id: Model identifier
            params: Generation parameters
            
        Returns:
            Result with generated text
        """
        try:
            task_id = str(uuid.uuid4())
            task = WorkerTask(
                task_id=task_id,
                task_type="text_generation",
                model_id=model_id,
                input_data=input_text,
                metadata=params,
                created_at=time.time()
            )
            
            # Submit task to worker pool
            result = await self.worker_pool.submit_task(task)
            
            if result and result.success:
                return Result.success(data={
                    "generated_text": result.data["generated_text"],
                    "model_id": model_id,
                    "processing_time": result.processing_time,
                    "worker_id": result.worker_id,
                    "input_length": result.data.get("input_length", len(input_text)),
                    "output_length": result.data.get("output_length", len(result.data["generated_text"]))
                })
            else:
                error_msg = result.error if result else "No result returned"
                return Result.error(
                    code="WORKER_POOL_TEXT_GENERATION_FAILED",
                    message=f"Worker pool text generation failed: {error_msg}"
                )
                
        except Exception as e:
            self.logger.error(f"Worker pool text generation error: {e}")
            return Result.error(
                code="WORKER_POOL_TEXT_ERROR",
                message="Worker pool text generation failed",
                details={"error": str(e)}
            )
    
    async def _generate_text_direct(self, input_text: str, model_id: str, params: Dict[str, Any]) -> Result:
        """Generate text using direct model loading.
        
        Args:
            input_text: Input text
            model_id: Model identifier
            params: Generation parameters
            
        Returns:
            Result with generated text
        """
        try:
            # Get or load model
            model_result = await self._get_or_load_model(model_id, "cuda:0")
            if not model_result.success:
                return model_result
            
            model_data = model_result.data
            model = model_data["model"]
            tokenizer = model_data["tokenizer"]
            device = model_data["device"]
            
            # Generate text
            start_time = time.time()
            max_length = params.get("max_length", 128)
            
            # Tokenize input
            inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Generate
            import torch
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=4,
                    early_stopping=True,
                    do_sample=False
                )
            
            # Decode result
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            processing_time = time.time() - start_time
            
            return Result.success(data={
                "generated_text": generated_text,
                "model_id": model_id,
                "processing_time": processing_time,
                "input_length": len(input_text),
                "output_length": len(generated_text)
            })
            
        except Exception as e:
            self.logger.error(f"Direct text generation error: {e}")
            return Result.error(
                code="DIRECT_TEXT_GENERATION_ERROR",
                message="Direct text generation failed",
                details={"error": str(e)}
            )
    
    async def _get_or_load_model(self, model_id: str, device: str) -> Result:
        """Get existing model or load new one using loader factory.
        
        Args:
            model_id: Model identifier
            device: Target device
            
        Returns:
            Result with model data
        """
        try:
            # Check if model is already loaded
            if model_id in self._loaded_models:
                model_ref = self._loaded_models[model_id]
                model_ref.add_reference()
                return Result.success(data=model_ref.model_instance)
            
            # Load model using loader factory
            load_result = await self.loader_factory.load_model(model_id, device)
            if not load_result.success:
                return load_result
            
            # Create model reference and store
            model_data = load_result.data
            model_ref = ModelReference(model_id, model_data, self.config)
            self._loaded_models[model_id] = model_ref
            model_ref.add_reference()
            
            self.logger.info(f"Loaded and registered model: {model_id}")
            return Result.success(data=model_data)
            
        except Exception as e:
            self.logger.error(f"Model loading error: {e}")
            return Result.error(
                code="MODEL_LOAD_ERROR",
                message=f"Failed to load model {model_id}",
                details={"error": str(e), "device": device}
            )
    
    async def release_model(self, model_id: str) -> Result:
        """Release a model reference.
        
        Args:
            model_id: Model identifier to release
            
        Returns:
            Result with release status
        """
        try:
            if model_id in self._loaded_models:
                model_ref = self._loaded_models[model_id]
                model_ref.remove_reference()
                
                # If no more references and model is idle, consider unloading
                if model_ref.reference_count == 0 and model_ref.is_idle(300):  # 5 minute idle timeout
                    del self._loaded_models[model_id]
                    self.logger.info(f"Unloaded idle model: {model_id}")
                    return Result.success(data={"unloaded": True})
                
                return Result.success(data={"released": True, "references": model_ref.reference_count})
            
            return Result.success(data={"message": f"Model {model_id} not found in registry"})
            
        except Exception as e:
            return Result.error(
                code="MODEL_RELEASE_ERROR",
                message=f"Failed to release model {model_id}",
                details={"error": str(e)}
            )
    
    async def get_service_status(self) -> Result:
        """Get comprehensive service status.
        
        Returns:
            Result with service status information
        """
        try:
            # Get worker pool status
            worker_status = await self.worker_pool.get_status() if self.worker_pool else Result.success(data={"enabled": False})
            
            # Get cache status
            cache_status = self.embedding_cache.get_status() if self.embedding_cache else {}
            
            # Get loaded models status from direct loading
            models_status = {}
            for model_id, model_ref in self._loaded_models.items():
                models_status[model_id] = {
                    "reference_count": model_ref.reference_count,
                    "last_accessed": model_ref.last_accessed,
                    "created_at": model_ref.created_at,
                    "source": "direct"
                }
            
            # Add models from worker pool
            if worker_status.success and "workers_status" in worker_status.data:
                for worker_id, worker_info in worker_status.data["workers_status"].items():
                    if worker_info.get("current_model_id"):
                        model_id = worker_info["current_model_id"]
                        if model_id not in models_status:  # Don't duplicate if already in direct loading
                            models_status[model_id] = {
                                "reference_count": 1,  # Worker pool model
                                "last_accessed": worker_info.get("last_activity", 0),
                                "created_at": 0,  # Not tracked for worker pool models
                                "source": "worker_pool",
                                "worker_id": worker_id,
                                "device": worker_info.get("device", "unknown")
                            }
            
            total_loaded_models = len(models_status)
            
            return Result.success(data={
                "initialized": self._initialized,
                "worker_pool": worker_status.data if worker_status.success else {"error": worker_status.error},
                "embedding_cache": cache_status,
                "loaded_models": models_status,
                "total_loaded_models": total_loaded_models,
                "loader_factory": self.loader_factory.get_factory_status() if self.loader_factory else {}
            })
            
        except Exception as e:
            return Result.error(
                code="SERVICE_STATUS_ERROR",
                message="Failed to get service status",
                details={"error": str(e)}
            )
    
    async def get_worker_pool_status(self) -> Result:
        """Get worker pool status specifically.
        
        Returns:
            Result with worker pool status information
        """
        try:
            if not self.worker_pool:
                return Result.success(data={
                    "enabled": False,
                    "message": "Worker pool not initialized"
                })
            
            worker_status = await self.worker_pool.get_status()
            return worker_status
            
        except Exception as e:
            return Result.error(
                code="WORKER_POOL_STATUS_ERROR",
                message="Failed to get worker pool status",
                details={"error": str(e)}
            )
    
    async def cleanup_resources(self):
        """Clean up all service resources."""
        try:
            self.logger.info("Starting resource cleanup...")
            
            # Shutdown worker pool
            if self.worker_pool:
                await self.worker_pool.shutdown()
            
            # Clear cache
            if self.embedding_cache:
                self.embedding_cache.clear_cache()
            
            # Clear loaded models
            self._loaded_models.clear()
            
            self._initialized = False
            self.logger.info("Resource cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Resource cleanup error: {e}")
    
    def force_cleanup(self):
        """
        Force cleanup of resources - logging handled by decorator.
        Called during emergency shutdown via @force_shutdown decorator.
        """
        try:
            # Clear loaded models immediately
            self._loaded_models.clear()
            
            # Clear cache if available
            if self.embedding_cache:
                self.embedding_cache.clear_cache()
            
            self._initialized = False
            
        except Exception as e:
            self.logger.error(f"Force cleanup error: {e}")