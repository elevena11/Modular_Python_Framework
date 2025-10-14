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

import os
from pathlib import Path
from core.paths import get_data_path

# Configure HuggingFace cache location BEFORE any HuggingFace imports
# This must happen at module load time, not during initialization
MODELS_DIR = get_data_path("models")
os.makedirs(MODELS_DIR, exist_ok=True)
os.environ["HF_HOME"] = str(MODELS_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(MODELS_DIR / "transformers")
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(MODELS_DIR / "sentence-transformers")

# NOW import everything else
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from core.error_utils import Result, error_message

# Type checking imports (not executed at runtime to avoid circular imports)
if TYPE_CHECKING:
    from .schemas import ModelRequirement

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
        
        # Model registry - tracks loaded model instances
        self._loaded_models: Dict[str, ModelReference] = {}

        # Model registry - tracks registered model requirements from modules
        self.model_registry: Dict[str, Dict[str, Any]] = {}

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
            
            # Check if module is enabled
            if not self.config.get("enabled", True):
                self.logger.info("Model manager disabled - no AI features active")
                return Result.success(data={"initialized": False, "reason": "disabled"})

            # Initialize components
            await self._initialize_components()
            
            # Initialize worker pool if enabled
            if self.config.get("worker_pool.enabled", False):
                pool_result = await self.worker_pool.initialize()
                if not pool_result.success:
                    self.logger.warning(f"Worker pool initialization failed: {pool_result.error}")
            
            self._initialized = True
            self.logger.info(f"{MODULE_ID}: Service initialization completed successfully")
            return Result.success(data={"initialized": True})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SERVICE_INITIALIZATION_FAILED",
                details=f"Service initialization failed: {e}",
                location="ModelManagerService.initialize()",
                context={"error": str(e)}
            ))
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
                # Import the Pydantic model
                from .settings import ModelManagerSettings
                
                # Get model manager specific settings
                settings_result = await settings_service.get_typed_settings(
                    module_id=MODULE_ID,
                    model_class=ModelManagerSettings
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
        
        return {
            # Main module settings - Framework infrastructure only
            "enabled": getattr(settings, 'enabled', True),
            "log_model_usage": getattr(settings, 'log_model_usage', True),

            # Worker pool settings
            "worker_pool.enabled": getattr(worker_pool, 'enabled', True) if worker_pool else True,
            "worker_pool.num_workers": getattr(worker_pool, 'num_workers', 1) if worker_pool else 1,
            "worker_pool.devices": getattr(worker_pool, 'devices', ["auto"]) if worker_pool else ["auto"],
            "worker_pool.require_gpu": getattr(worker_pool, 'require_gpu', False) if worker_pool else False,
            "worker_pool.queue_timeout": getattr(worker_pool, 'queue_timeout', 30) if worker_pool else 30,
            "worker_pool.model_idle_timeout": getattr(worker_pool, 'model_idle_timeout', 300) if worker_pool else 300,
            "worker_pool.preload_embeddings": getattr(worker_pool, 'preload_embeddings', False) if worker_pool else False,
            "worker_pool.load_balancing": getattr(worker_pool, 'load_balancing', "round_robin") if worker_pool else "round_robin",

            # Embedding cache settings
            "embedding_cache.enabled": getattr(embedding_cache, 'enabled', True) if embedding_cache else True,
            "embedding_cache.max_cache_size": getattr(embedding_cache, 'max_cache_size', 10000) if embedding_cache else 10000,
            "embedding_cache.ttl_seconds": getattr(embedding_cache, 'ttl_seconds', 3600) if embedding_cache else 3600,
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            # Main module settings - Framework infrastructure only
            "enabled": True,
            "log_model_usage": True,

            # Worker pool settings - enabled by default with auto device detection
            "worker_pool.enabled": True,
            "worker_pool.num_workers": 1,
            "worker_pool.devices": ["auto"],
            "worker_pool.require_gpu": False,
            "worker_pool.queue_timeout": 30,
            "worker_pool.model_idle_timeout": 300,
            "worker_pool.preload_embeddings": False,
            "worker_pool.load_balancing": "round_robin",

            # Embedding cache settings
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
    
    async def register_model(self, model_id: str, model_config: 'ModelRequirement', requester_module_id: str) -> Result:
        """Register a model requirement from a module.

        Modules call this during initialization to register their model needs.
        The model is downloaded/verified at registration time to catch issues early.

        Args:
            model_id: Unique identifier for this model
            model_config: ModelRequirement schema with model configuration
            requester_module_id: Module ID requesting the model

        Returns:
            Result with registration status

        Example:
            from modules.core.model_manager.schemas import ModelRequirement

            model_req = ModelRequirement(
                model_type="embedding",
                name="sentence-transformers/all-MiniLM-L6-v2",
                dimension=384,
                device="auto"
            )
            result = await model_manager.register_model("my_embeddings", model_req, "standard.my_module")
        """
        try:
            # Import here to avoid circular imports
            from .schemas import ModelRequirement

            # Validate model_config is ModelRequirement
            if not isinstance(model_config, ModelRequirement):
                return Result.error(
                    code="INVALID_MODEL_CONFIG",
                    message="model_config must be a ModelRequirement instance"
                )

            # Check if model_id already exists
            if model_id in self.model_registry:
                # Model already registered - add requester if not already in set
                registration = self.model_registry[model_id]
                registration["requesters"].add(requester_module_id)
                registration["reference_count"] += 1

                self.logger.info(f"Model {model_id} already registered, added requester: {requester_module_id}")

                return Result.success(data={
                    "registered": True,
                    "model_id": model_id,
                    "new_registration": False,
                    "reference_count": registration["reference_count"],
                    "requesters": list(registration["requesters"])
                })

            # New registration
            self.model_registry[model_id] = {
                "config": model_config,
                "requesters": {requester_module_id},
                "reference_count": 1,
                "loaded": False,
                "load_time": None,
                "last_accessed": None
            }

            # Add to config dict for backwards compatibility with loaders
            # This flattens the ModelRequirement into config keys
            self.config[f"models.{model_id}.type"] = model_config.model_type
            self.config[f"models.{model_id}.name"] = model_config.name
            self.config[f"models.{model_id}.device"] = model_config.device
            self.config[f"models.{model_id}.batch_size"] = model_config.batch_size
            if model_config.local_path:
                self.config[f"models.{model_id}.local_path"] = model_config.local_path
            if model_config.dimension:
                self.config[f"models.{model_id}.dimension"] = model_config.dimension
            if model_config.cache_embeddings is not None:
                self.config[f"models.{model_id}.cache_embeddings"] = model_config.cache_embeddings
            if model_config.max_input_length:
                self.config[f"models.{model_id}.max_input_length"] = model_config.max_input_length
            if model_config.max_output_length:
                self.config[f"models.{model_id}.max_output_length"] = model_config.max_output_length

            self.logger.info(f"Registered model {model_id} from {requester_module_id}: {model_config.model_type} - {model_config.name}")

            # Preload model based on module's preload_workers setting
            preload_workers = model_config.preload_workers

            if self.worker_pool and self.worker_pool.is_enabled:
                if preload_workers > 0:
                    self.logger.info(f"Preloading model {model_id} to {preload_workers} worker(s)...")
                    preload_result = await self.worker_pool.preload_model(model_id, num_workers=preload_workers)

                    if preload_result.success:
                        self.model_registry[model_id]["loaded"] = True
                        self.model_registry[model_id]["load_time"] = time.time()
                        workers_loaded = preload_result.data.get("workers_loaded", 0)
                        self.logger.info(f"Model {model_id} preloaded to {workers_loaded} worker(s)")
                    else:
                        # Log warning but don't fail registration - model will load on first use
                        self.logger.warning(f"Model {model_id} preload failed (will load on-demand): {preload_result.error}")
                elif preload_workers == 0:
                    # Download/verify only - don't load to workers
                    self.logger.info(f"Verifying model {model_id} (download if needed, no worker preload)...")
                    verify_result = await self.worker_pool.verify_model_download(model_id)

                    if verify_result.success:
                        self.logger.info(f"Model {model_id} verified/downloaded successfully")
                    else:
                        self.logger.warning(f"Model {model_id} verification failed: {verify_result.error}")
            else:
                # No worker pool - just log
                if preload_workers > 0:
                    self.logger.warning(f"Worker pool not enabled, model {model_id} will load on-demand")

            return Result.success(data={
                "registered": True,
                "model_id": model_id,
                "new_registration": True,
                "model_type": model_config.model_type,
                "model_name": model_config.name,
                "reference_count": 1
            })

        except Exception as e:
            self.logger.error(f"Model registration error for {model_id}: {e}")
            return Result.error(
                code="MODEL_REGISTRATION_ERROR",
                message=f"Failed to register model {model_id}",
                details={"error": str(e), "model_id": model_id}
            )

    async def release_model(self, model_id: str, requester_module_id: Optional[str] = None) -> Result:
        """Release a model reference.

        Args:
            model_id: Model identifier to release
            requester_module_id: Module ID releasing the model (optional)

        Returns:
            Result with release status
        """
        try:
            # Decrement registry reference count if registered
            if model_id in self.model_registry:
                registration = self.model_registry[model_id]
                registration["reference_count"] = max(0, registration["reference_count"] - 1)

                # Remove requester if specified
                if requester_module_id and requester_module_id in registration["requesters"]:
                    registration["requesters"].remove(requester_module_id)

                # If no more references, consider removing from registry
                if registration["reference_count"] == 0:
                    del self.model_registry[model_id]
                    self.logger.info(f"Removed model {model_id} from registry (no more references)")

            # Release from loaded models if loaded
            if model_id in self._loaded_models:
                model_ref = self._loaded_models[model_id]
                model_ref.remove_reference()

                # If no more references and model is idle, consider unloading
                if model_ref.reference_count == 0 and model_ref.is_idle(300):  # 5 minute idle timeout
                    del self._loaded_models[model_id]
                    self.logger.info(f"Unloaded idle model: {model_id}")
                    return Result.success(data={"unloaded": True})

                return Result.success(data={"released": True, "references": model_ref.reference_count})

            return Result.success(data={"message": f"Model {model_id} not found in loaded models"})

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