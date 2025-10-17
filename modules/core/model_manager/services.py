"""
modules/core/model_manager/services.py
Model Manager Service - Clean orchestration layer using modular components.

Refactored from monolithic services.py to use:
- workers/: Worker pool management and individual workers
- cache/: Embedding caching system
- loaders/: Model loading abstractions and implementations
- models/: Model lifecycle and metadata management

Provides high-level API for:
- Unified task() API - primary entry point for all model operations
- Worker pool coordination with auto-scaling
- Embedding generation with caching
- Text generation processing
- Resource management and lifecycle control
"""

import asyncio
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
from .models import ModelReference, ModelLifecycleManager

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
        self.settings = None  # Will be set in initialize()

        # Initialize modular components
        self.worker_pool = None
        self.embedding_cache = None
        self.loader_factory = None
        self.lifecycle_manager = None

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

            # Store settings - received from framework before initialize() is called
            if settings:
                self.settings = settings
                self.logger.info("Loaded settings from framework")
            else:
                self.logger.warning("No settings provided, using defaults")
                # Import settings model and create default instance
                from .settings import ModelManagerSettings
                self.settings = ModelManagerSettings()

            # Check if module is enabled
            if not self.settings.enabled:
                self.logger.info("Model manager disabled - no AI features active")
                return Result.success(data={"initialized": False, "reason": "disabled"})

            # Initialize components
            await self._initialize_components()

            # Initialize worker pool if enabled
            if self.settings.worker_pool.enabled:
                pool_result = await self.worker_pool.initialize()
                if not pool_result.success:
                    self.logger.warning(f"Worker pool initialization failed: {pool_result.error}")

            # Start background task for idle model cleanup (via lifecycle manager)
            await self.lifecycle_manager.start_idle_checker()

            self._initialized = True
            self.logger.info(f"{MODULE_ID}: Service initialization completed successfully")
            return Result.success(data={"initialized": True})

        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="SERVICE_INITIALIZATION_FAILED",
                details=f"Service initialization failed: {e}",
                location="ModelManagerService.initialize()"
            ))
            return Result.error(
                code="SERVICE_INIT_FAILED",
                message="Failed to initialize model manager service",
                details={"error": str(e)}
            )
    async def _initialize_components(self):
        """Initialize modular components."""
        # Pass Pydantic settings object directly (Pattern 1)
        # No model_dump() - components receive typed settings

        # Initialize embedding cache
        self.embedding_cache = EmbeddingCache(self.settings)

        # Initialize loader factory
        self.loader_factory = LoaderFactory(self.settings)

        # Initialize worker pool
        self.worker_pool = WorkerPool(self.settings, self)

        # Initialize lifecycle manager
        self.lifecycle_manager = ModelLifecycleManager(
            settings=self.settings,
            loader_factory=self.loader_factory,
            worker_pool=self.worker_pool
        )

        self.logger.info("Modular components initialized successfully")
    
    async def task(
        self,
        task_data: Optional[Any],
        task_type: str,
        model_name: str,
        num_workers: int = 1,
        device: str = "gpu",
        keep_alive: Optional[int] = None,
        **kwargs
    ) -> Result:
        """Unified task processing API - single entry point for all model operations.

        This is the primary API for using models. All configuration is passed with the request,
        making it self-contained. Workers are auto-created on first use and auto-recreated
        if they were previously stopped.

        Args:
            task_data: Data to process (texts for embeddings, text for generation, etc.)
                      Set to None for pre-loading only (loads model without processing)
            task_type: Type of task - "embedding" or "text_generation"
            model_name: HuggingFace model name (e.g., "mixedbread-ai/mxbai-embed-large-v1")
            num_workers: Number of workers to create (default: 1)
                        - For device="gpu": Suggestion, capped by available GPUs
                        - For device="cpu": Exact count created
            device: "gpu" (default) or "cpu"
            keep_alive: Minutes of inactivity before auto-release (default from settings)
                       Auto-release frees VRAM after inactivity. Next use recreates workers.
            **kwargs: Additional task-specific parameters (e.g., max_length for text generation)

        Returns:
            Result with task output (or confirmation if task_data=None for pre-load)

        Examples:
            # Regular embedding task
            await model_manager.task(
                task_data=["hello", "world"],
                task_type="embedding",
                model_name="mixedbread-ai/mxbai-embed-large-v1",
                num_workers=2,
                device="gpu"
            )

            # Pre-load model with 30 minute keep-alive
            await model_manager.task(
                task_data=None,  # Pre-load only, no processing
                task_type="embedding",
                model_name="mixedbread-ai/mxbai-embed-large-v1",
                num_workers=2,
                device="gpu",
                keep_alive=30  # Stay loaded for 30 minutes of inactivity
            )

            # Text generation with custom keep_alive
            await model_manager.task(
                task_data="Translate this text",
                task_type="text_generation",
                model_name="google-t5/t5-large",
                num_workers=1,
                device="gpu",
                keep_alive=10,  # Custom 10 minute timeout
                max_length=128
            )
        """
        try:
            if not self._initialized:
                return Result.error(
                    code="SERVICE_NOT_INITIALIZED",
                    message="Model manager service not initialized"
                )

            # Validate task type
            valid_types = ["embedding", "text_generation"]
            if task_type not in valid_types:
                return Result.error(
                    code="INVALID_TASK_TYPE",
                    message=f"Invalid task_type '{task_type}'. Must be one of: {valid_types}",
                    details={"task_type": task_type, "valid_types": valid_types}
                )

            # Ensure workers exist for this model (auto-create or auto-recreate)
            await self._ensure_model_workers(
                model_name=model_name,
                task_type=task_type,
                num_workers=num_workers,
                device=device,
                keep_alive=keep_alive
            )

            # If task_data is None, this is a pre-load request - just return success
            if task_data is None:
                # Get actual worker count after creation/scaling
                actual_workers = len(self.worker_pool._model_workers.get(model_name, []))

                default_timeout = self.settings.worker_pool.model_idle_timeout
                return Result.success(data={
                    "preloaded": True,
                    "model_name": model_name,
                    "workers": actual_workers,  # Return actual created workers
                    "device": device,
                    "keep_alive_minutes": keep_alive or (default_timeout // 60)
                })

            # Route to appropriate handler based on task type
            if task_type == "embedding":
                return await self._process_embedding_task(task_data, model_name, **kwargs)
            elif task_type == "text_generation":
                return await self._process_text_generation_task(task_data, model_name, **kwargs)
            else:
                return Result.error(
                    code="UNSUPPORTED_TASK_TYPE",
                    message=f"Task type '{task_type}' not yet implemented"
                )

        except Exception as e:
            self.logger.error(f"Task processing error: {e}")
            return Result.error(
                code="TASK_PROCESSING_ERROR",
                message="Failed to process task",
                details={"error": str(e), "task_type": task_type, "model_name": model_name}
            )

    async def _ensure_model_workers(
        self,
        model_name: str,
        task_type: str,
        num_workers: int,
        device: str,
        keep_alive: Optional[int] = None
    ):
        """Ensure workers exist for a model, creating or recreating them if needed.

        Args:
            model_name: Model identifier
            task_type: Task type (determines model_type for loader)
            num_workers: Number of workers requested
            device: Device specification ("gpu" or "cpu")
            keep_alive: Minutes of inactivity before auto-release (None = use default)
        """
        import time

        # Map task_type to model_type for loader
        task_to_model_type = {
            "embedding": "embedding",
            "text_generation": "text_generation"
        }
        model_type = task_to_model_type.get(task_type, task_type)

        # Estimate model memory early - needed for both scaling and creation paths
        model_memory_gb = self.lifecycle_manager.estimate_model_memory(model_name, model_type)

        # Get default keep_alive from settings (in seconds, convert to minutes)
        if keep_alive is None:
            keep_alive_seconds = self.settings.worker_pool.model_idle_timeout
            keep_alive = keep_alive_seconds // 60  # Convert to minutes

        keep_alive_seconds = keep_alive * 60  # Convert minutes to seconds for storage

        # Check if workers exist
        if self.worker_pool and model_name in self.worker_pool._model_workers:
            workers = self.worker_pool._model_workers[model_name]
            current_worker_count = len(workers)
            if current_worker_count > 0:
                # Workers exist and are running
                if model_name in self.lifecycle_manager.model_registry:
                    self.lifecycle_manager.model_registry[model_name]["last_activity"] = time.time()
                    self.lifecycle_manager.model_registry[model_name]["keep_alive_seconds"] = keep_alive_seconds

                # Check if num_workers changed from request
                if num_workers != current_worker_count:
                    # Scale workers to match requested count (add or remove as needed)
                    scale_result = await self.worker_pool.scale_model_workers(
                        model_name=model_name,
                        target_workers=num_workers,
                        model_memory_gb=model_memory_gb,
                        device=device
                    )

                    if scale_result.success:
                        self.logger.info(
                            f"Scaled {model_name} workers: {current_worker_count} -> {num_workers} "
                            f"(added: {scale_result.data.get('workers_added', 0)}, "
                            f"removed: {scale_result.data.get('workers_removed', 0)})"
                        )
                        return
                    else:
                        self.logger.error(f"Failed to scale workers for {model_name}: {scale_result.error}")
                        return  # Return on scaling error
                else:
                    # Worker count matches request - just reuse existing workers
                    self.logger.debug(f"Reusing {current_worker_count} existing worker(s) for {model_name}")
                    return

        # Workers don't exist or were stopped - create them
        self.logger.info(f"Creating workers for {model_name} on first use...")

        # Store/update config in registry for future recreations (model_memory_gb already estimated at line 381)
        if model_name not in self.lifecycle_manager.model_registry:
            self.lifecycle_manager.model_registry[model_name] = {
                "model_type": model_type,
                "device": device,
                "num_workers_requested": num_workers,
                "model_memory_gb": model_memory_gb,
                "loaded": False,
                "last_activity": time.time(),
                "keep_alive_seconds": keep_alive_seconds
            }
        else:
            # Update config (user might have changed num_workers or device)
            self.lifecycle_manager.model_registry[model_name].update({
                "model_type": model_type,
                "device": device,
                "num_workers_requested": num_workers,
                "model_memory_gb": model_memory_gb,
                "last_activity": time.time(),
                "keep_alive_seconds": keep_alive_seconds
            })

        # Create workers
        if self.worker_pool and self.worker_pool.is_enabled:
            ensure_result = await self.worker_pool.ensure_workers(
                model_name=model_name,
                num_workers=num_workers,
                model_memory_gb=model_memory_gb,
                device=device
            )

            if ensure_result.success:
                workers_created = ensure_result.data.get("workers_created", 0)
                self.lifecycle_manager.model_registry[model_name]["loaded"] = workers_created > 0
                self.logger.info(f"Created {workers_created} worker(s) for {model_name} (keep_alive: {keep_alive}min)")
            else:
                self.logger.error(f"Failed to create workers for {model_name}: {ensure_result.error}")
                raise RuntimeError(f"Failed to create workers: {ensure_result.error}")
        else:
            raise RuntimeError("Worker pool not enabled")


    async def _process_embedding_task(self, texts: Union[str, List[str]], model_name: str, **kwargs) -> Result:
        """Process an embedding task using worker pool.

        Args:
            texts: Text(s) to embed
            model_name: Model name
            **kwargs: Additional parameters

        Returns:
            Result with embeddings
        """
        # Check cache first if enabled
        cache_result = await self.embedding_cache.get_embeddings(texts, model_name)
        if cache_result.success:
            self.logger.debug(f"Cache hit for {len(texts) if isinstance(texts, list) else 1} text(s)")
            return cache_result

        # Use worker pool
        return await self._generate_embeddings_worker_pool(texts, model_name)

    async def _process_text_generation_task(self, input_text: str, model_name: str, **kwargs) -> Result:
        """Process a text generation task using worker pool.

        Args:
            input_text: Input text
            model_name: Model name
            **kwargs: Additional parameters (e.g., max_length)

        Returns:
            Result with generated text
        """
        # Use worker pool
        return await self._generate_text_worker_pool(input_text, model_name, kwargs)

    async def _generate_embeddings_worker_pool(self, texts: Union[str, List[str]], model_name: str) -> Result:
        """Generate embeddings using worker pool.

        Args:
            texts: Text(s) to embed
            model_name: Model name (HuggingFace name, e.g., "sentence-transformers/all-MiniLM-L6-v2")

        Returns:
            Result with embedding data
        """
        try:
            task_id = str(uuid.uuid4())
            task = WorkerTask(
                task_id=task_id,
                task_type="embedding",
                model_name=model_name,
                input_data=texts,
                metadata={},
                created_at=time.time()
            )

            # Submit task to worker pool (returns future immediately)
            future = await self.worker_pool.submit_task(task)

            # Wait for result
            result = await future

            if result and result.success:
                # Cache the results
                await self.embedding_cache.cache_embeddings(texts, result.data["embeddings"], model_name)

                return Result.success(data={
                    "embeddings": result.data["embeddings"],
                    "model_name": model_name,
                    "cached": False,
                    "processing_time": result.processing_time,
                    "worker_id": result.worker_id,
                    "metadata": result.metadata  # Include device info from worker
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

    async def _generate_text_worker_pool(self, input_text: str, model_name: str, params: Dict[str, Any]) -> Result:
        """Generate text using worker pool.

        Args:
            input_text: Input text
            model_name: Model name (HuggingFace name)
            params: Generation parameters

        Returns:
            Result with generated text
        """
        try:
            # model_name is actually the model_name in new API
            model_name = model_name

            task_id = str(uuid.uuid4())
            task = WorkerTask(
                task_id=task_id,
                task_type="text_generation",
                model_name=model_name,
                input_data=input_text,
                metadata=params,
                created_at=time.time()
            )
            
            # Submit task to worker pool (returns future immediately)
            future = await self.worker_pool.submit_task(task)

            # Wait for result
            result = await future

            if result and result.success:
                return Result.success(data={
                    "generated_text": result.data["generated_text"],
                    "model_name": model_name,
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

    async def _get_or_load_model(self, model_name: str, device: str) -> Result:
        """Get existing model or load new one - delegates to lifecycle manager.

        Args:
            model_name: Model identifier
            device: Target device

        Returns:
            Result with model data
        """
        return await self.lifecycle_manager.get_or_load_model(model_name, device)

    async def register_model(
        self,
        model_name: str,
        model_type: str,
        num_workers: int = 1,
        device: str = "gpu",
        requester_module_id: Optional[str] = None
    ) -> Result:
        """Register a model and create dedicated workers - delegates to lifecycle manager.

        Args:
            model_name: HuggingFace model name
            model_type: Model type (embedding, text_generation)
            num_workers: Number of workers to create
            device: Device specification (gpu, cpu)
            requester_module_id: Optional module ID requesting the model

        Returns:
            Result with registration status
        """
        return await self.lifecycle_manager.register_model(
            model_name, model_type, num_workers, device, requester_module_id
        )

    async def release_model(
        self,
        model_name: str,
        wait_for_tasks: bool = True,
        timeout: Optional[float] = None
    ) -> Result:
        """Release a model and free VRAM - delegates to lifecycle manager.

        Args:
            model_name: Model identifier to release
            wait_for_tasks: If True, wait for pending tasks to complete before release
            timeout: Maximum seconds to wait for queue to drain

        Returns:
            Result with release status
        """
        return await self.lifecycle_manager.release_model(model_name, wait_for_tasks, timeout)

    async def drop_model_queue(
        self,
        model_name: str,
        reason: str = "Manual drop"
    ) -> Result:
        """Drop all pending tasks for a model - delegates to lifecycle manager.

        Args:
            model_name: Model identifier whose queue to drop
            reason: Reason for dropping

        Returns:
            Result with number of tasks dropped
        """
        return await self.lifecycle_manager.drop_model_queue(model_name, reason)
    
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
            
            # Get loaded models status from lifecycle manager
            models_status = self.lifecycle_manager.get_loaded_models_status() if self.lifecycle_manager else {}
            
            # Add models from worker pool
            if worker_status.success and "workers_status" in worker_status.data:
                for worker_id, worker_info in worker_status.data["workers_status"].items():
                    if worker_info.get("current_model_name"):
                        model_name = worker_info["current_model_name"]
                        if model_name not in models_status:  # Don't duplicate if already in direct loading
                            models_status[model_name] = {
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
        """Clean up all service resources.

        Automatically unloads ALL models and clears the registry so individual
        modules don't need to manually call release_model() during shutdown.
        """
        try:
            self.logger.info("Starting resource cleanup...")

            # Stop lifecycle manager (stops idle checker and cleans up lifecycle state)
            if self.lifecycle_manager:
                await self.lifecycle_manager.stop_idle_checker()

                # Log registered models before cleanup
                if self.lifecycle_manager.model_registry:
                    self.logger.info(f"Cleaning up {len(self.lifecycle_manager.model_registry)} registered model(s)")
                    for model_name, registration in self.lifecycle_manager.model_registry.items():
                        requesters = registration.get("requesters", set())
                        if requesters:
                            requesters_str = ", ".join(requesters)
                            self.logger.info(f"  - {model_name} (requesters: {requesters_str})")
                        else:
                            self.logger.info(f"  - {model_name}")

                # Clean up lifecycle manager
                self.lifecycle_manager.cleanup()

            # Shutdown worker pool (workers will unload their current models)
            if self.worker_pool:
                await self.worker_pool.shutdown()

            # Clear cache
            if self.embedding_cache:
                self.embedding_cache.clear_cache()

            self._initialized = False
            self.logger.info("Resource cleanup completed - all models unloaded, registry cleared")

        except Exception as e:
            self.logger.error(f"Resource cleanup error: {e}")
    
    def force_cleanup(self):
        """
        Force cleanup of resources - logging handled by decorator.
        Called during emergency shutdown via @force_shutdown decorator.
        """
        try:
            # Clean up lifecycle manager immediately
            if self.lifecycle_manager:
                self.lifecycle_manager.cleanup()

            # Clear cache if available
            if self.embedding_cache:
                self.embedding_cache.clear_cache()

            self._initialized = False

        except Exception as e:
            self.logger.error(f"Force cleanup error: {e}")