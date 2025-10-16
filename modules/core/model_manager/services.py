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
        self.settings = None  # Will be set in initialize()

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

        # Background task for idle model cleanup
        self._idle_checker_task = None

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

            # Start background task for idle model cleanup
            self._idle_checker_task = asyncio.create_task(self._idle_model_checker())
            self.logger.info("Started idle model checker background task")

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
        # Convert settings to dict for components that expect dict config
        config = self.settings.model_dump()

        # Initialize embedding cache
        self.embedding_cache = EmbeddingCache(config)

        # Initialize loader factory
        self.loader_factory = LoaderFactory(config)

        # Initialize worker pool
        self.worker_pool = WorkerPool(config, self)

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
                default_timeout = self.settings.worker_pool.model_idle_timeout
                return Result.success(data={
                    "preloaded": True,
                    "model_name": model_name,
                    "workers": num_workers,
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
        model_memory_gb = self._estimate_model_memory(model_name, model_type)

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
                if model_name in self.model_registry:
                    self.model_registry[model_name]["last_activity"] = time.time()
                    self.model_registry[model_name]["keep_alive_seconds"] = keep_alive_seconds

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
        if model_name not in self.model_registry:
            self.model_registry[model_name] = {
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
            self.model_registry[model_name].update({
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
                self.model_registry[model_name]["loaded"] = workers_created > 0
                self.logger.info(f"Created {workers_created} worker(s) for {model_name} (keep_alive: {keep_alive}min)")
            else:
                self.logger.error(f"Failed to create workers for {model_name}: {ensure_result.error}")
                raise RuntimeError(f"Failed to create workers: {ensure_result.error}")
        else:
            raise RuntimeError("Worker pool not enabled")

    async def _idle_model_checker(self):
        """Background task that checks for idle models and auto-releases them.

        Runs every 60 seconds, checks each loaded model's last_activity time,
        and releases models that have exceeded their keep_alive timeout.
        """
        import time

        self.logger.info("Idle model checker started")
        check_interval = 60  # Check every 60 seconds

        while self._initialized:
            try:
                await asyncio.sleep(check_interval)

                # Check each model in registry
                models_to_release = []
                current_time = time.time()

                for model_name, registration in list(self.model_registry.items()):
                    if not registration.get("loaded", False):
                        # Model not loaded, skip
                        continue

                    last_activity = registration.get("last_activity", current_time)
                    keep_alive_seconds = registration.get("keep_alive_seconds", 300)
                    idle_time = current_time - last_activity

                    if idle_time > keep_alive_seconds:
                        # Model has been idle too long
                        keep_alive_minutes = keep_alive_seconds // 60
                        models_to_release.append((model_name, idle_time, keep_alive_minutes))

                # Release idle models
                for model_name, idle_time, keep_alive_minutes in models_to_release:
                    idle_minutes = int(idle_time // 60)
                    self.logger.info(
                        f"Auto-releasing idle model {model_name} "
                        f"(idle: {idle_minutes}min, keep_alive: {keep_alive_minutes}min)"
                    )

                    release_result = await self.release_model(model_name)
                    if release_result.success:
                        self.logger.info(f"Successfully auto-released {model_name}, VRAM freed")
                    else:
                        self.logger.error(f"Failed to auto-release {model_name}: {release_result.error}")

            except asyncio.CancelledError:
                self.logger.info("Idle model checker cancelled (shutting down)")
                break
            except Exception as e:
                self.logger.error(f"Error in idle model checker: {e}")
                # Continue running even if one check fails

        self.logger.info("Idle model checker stopped")

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

    async def generate_embeddings(self, texts: Union[str, List[str]], model_name: str) -> Result:
        """Generate embeddings for text(s) using worker pool or direct loading.

        Args:
            texts: Text(s) to embed
            model_name: Model name (HuggingFace name, e.g., "sentence-transformers/all-MiniLM-L6-v2")

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
            cache_result = await self.embedding_cache.get_embeddings(texts, model_name)
            if cache_result.success:
                self.logger.debug(f"Cache hit for {len(texts) if isinstance(texts, list) else 1} text(s)")
                return cache_result

            # Use worker pool if available
            if self.worker_pool and self.worker_pool.is_enabled:
                return await self._generate_embeddings_worker_pool(texts, model_name)
            else:
                # Fallback to direct model loading
                return await self._generate_embeddings_direct(texts, model_name)

        except Exception as e:
            self.logger.error(f"Embedding generation error: {e}")
            return Result.error(
                code="EMBEDDING_GENERATION_ERROR",
                message="Failed to generate embeddings",
                details={"error": str(e), "model_name": model_name}
            )
    
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
    
    async def _generate_embeddings_direct(self, texts: Union[str, List[str]], model_name: str) -> Result:
        """Generate embeddings using direct model loading.
        
        Args:
            texts: Text(s) to embed
            model_name: Model identifier
            
        Returns:
            Result with embedding data
        """
        try:
            # Get or load model
            model_result = await self._get_or_load_model(model_name, "cuda:0")
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
            await self.embedding_cache.cache_embeddings(texts, result_embeddings, model_name)
            
            return Result.success(data={
                "embeddings": result_embeddings,
                "model_name": model_name,
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
    
    async def generate_text(self, input_text: str, model_name: str = "t5_summarizer", **kwargs) -> Result:
        """Generate text using specified model.
        
        Args:
            input_text: Input text for generation
            model_name: Model identifier for text generation
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
                return await self._generate_text_worker_pool(input_text, model_name, kwargs)
            else:
                # Fallback to direct model loading
                return await self._generate_text_direct(input_text, model_name, kwargs)
                
        except Exception as e:
            self.logger.error(f"Text generation error: {e}")
            return Result.error(
                code="TEXT_GENERATION_ERROR",
                message="Failed to generate text",
                details={"error": str(e), "model_name": model_name}
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
    
    async def _generate_text_direct(self, input_text: str, model_name: str, params: Dict[str, Any]) -> Result:
        """Generate text using direct model loading.
        
        Args:
            input_text: Input text
            model_name: Model identifier
            params: Generation parameters
            
        Returns:
            Result with generated text
        """
        try:
            # Get or load model
            model_result = await self._get_or_load_model(model_name, "cuda:0")
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
                "model_name": model_name,
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
    
    async def _get_or_load_model(self, model_name: str, device: str) -> Result:
        """Get existing model or load new one using loader factory.
        
        Args:
            model_name: Model identifier
            device: Target device
            
        Returns:
            Result with model data
        """
        try:
            # Check if model is already loaded
            if model_name in self._loaded_models:
                model_ref = self._loaded_models[model_name]
                model_ref.add_reference()
                return Result.success(data=model_ref.model_instance)
            
            # Load model using loader factory
            load_result = await self.loader_factory.load_model(model_name, device)
            if not load_result.success:
                return load_result
            
            # Create model reference and store
            model_data = load_result.data
            config = self.settings.model_dump()
            model_ref = ModelReference(model_name, model_data, config)
            self._loaded_models[model_name] = model_ref
            model_ref.add_reference()
            
            self.logger.info(f"Loaded and registered model: {model_name}")
            return Result.success(data=model_data)
            
        except Exception as e:
            self.logger.error(f"Model loading error: {e}")
            return Result.error(
                code="MODEL_LOAD_ERROR",
                message=f"Failed to load model {model_name}",
                details={"error": str(e), "device": device}
            )

    async def register_model(
        self,
        model_name: str,
        model_type: str,
        num_workers: int = 1,
        device: str = "gpu",
        requester_module_id: Optional[str] = None
    ) -> Result:
        """Register a model and create dedicated workers for it.

        This is the new simplified registration API. Workers are model-dedicated:
        they load one model on startup and never switch.

        Args:
            model_name: HuggingFace model name (e.g., "sentence-transformers/all-MiniLM-L6-v2")
            model_type: Model type - REQUIRED, determines which loader to use
                       - "embedding": For sentence transformers, embedding models
                       - "text_generation": For T5, GPT, LLaMA, etc.
            num_workers: Number of workers to create (default: 1)
                        - For device="gpu": Suggestion, capped by available GPUs
                        - For device="cpu": Exact count created
            device: "gpu" (default) or "cpu"
                   - "gpu": Fails if no GPU available (safe default)
                   - "cpu": Explicitly uses CPU (developer responsibility)
            requester_module_id: Optional module ID requesting the model (for tracking)

        Returns:
            Result with registration status and actual workers created

        Examples:
            # Minimal - model name and type (uses GPU, 1 worker)
            await model_manager.register_model(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_type="embedding"
            )

            # Recommended - specify workers for known load patterns
            await model_manager.register_model(
                model_name="mixedbread-ai/mxbai-embed-large-v1",
                model_type="embedding",
                num_workers=2  # Capped by available GPUs
            )

            # Text generation model
            await model_manager.register_model(
                model_name="t5-small",
                model_type="text_generation",
                num_workers=1
            )

            # Explicit CPU usage
            await model_manager.register_model(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_type="embedding",
                device="cpu",
                num_workers=2  # Exactly 2 CPU workers created
            )
        """
        try:
            # Check if model already registered
            if model_name in self.model_registry:
                # Model already registered - increment reference count
                registration = self.model_registry[model_name]
                if requester_module_id:
                    registration["requesters"].add(requester_module_id)
                registration["reference_count"] += 1

                self.logger.info(
                    f"Model {model_name} already registered with {len(registration['workers'])} worker(s), "
                    f"added requester: {requester_module_id or 'N/A'}"
                )

                return Result.success(data={
                    "registered": True,
                    "model_name": model_name,
                    "new_registration": False,
                    "workers": len(registration["workers"]),
                    "reference_count": registration["reference_count"],
                    "requesters": list(registration["requesters"])
                })

            # Validate model_type
            valid_types = ["embedding", "text_generation"]
            if model_type not in valid_types:
                return Result.error(
                    code="INVALID_MODEL_TYPE",
                    message=f"Invalid model_type '{model_type}'. Must be one of: {valid_types}",
                    details={"model_type": model_type, "valid_types": valid_types}
                )

            # Estimate model memory requirements
            # This is a rough estimation - actual memory will be tracked by workers
            model_memory_gb = self._estimate_model_memory(model_name, model_type)

            self.logger.info(
                f"Registering model {model_name} (type: {model_type}, "
                f"estimated memory: {model_memory_gb:.2f}GB, device: {device}, requested workers: {num_workers})"
            )

            # Create model registry entry
            self.model_registry[model_name] = {
                "model_type": model_type,
                "device": device,
                "requesters": {requester_module_id} if requester_module_id else set(),
                "reference_count": 1,
                "loaded": False,
                "load_time": None,
                "last_accessed": None,
                "workers": [],  # Will be populated by worker pool
                "num_workers_requested": num_workers,
                "model_memory_gb": model_memory_gb
            }

            # Create workers for this model (if worker pool enabled)
            workers_created = 0
            actual_workers = 0
            if self.worker_pool and self.worker_pool.is_enabled:
                self.logger.info(f"Creating workers for model {model_name}...")
                ensure_result = await self.worker_pool.ensure_workers(
                    model_name=model_name,
                    num_workers=num_workers,
                    model_memory_gb=model_memory_gb,
                    device=device
                )

                if ensure_result.success:
                    workers_created = ensure_result.data.get("workers_created", 0)
                    actual_workers = ensure_result.data.get("actual", workers_created)

                    self.model_registry[model_name]["loaded"] = workers_created > 0
                    self.model_registry[model_name]["load_time"] = time.time() if workers_created > 0 else None
                    self.model_registry[model_name]["workers"] = workers_created

                    if workers_created > 0:
                        self.logger.info(
                            f"Model {model_name} registered with {workers_created} worker(s) "
                            f"(requested: {num_workers}, device: {device})"
                        )
                    else:
                        self.logger.warning(f"Model {model_name} registered but no workers created")
                else:
                    # Worker creation failed
                    self.logger.error(
                        f"Failed to create workers for {model_name}: {ensure_result.error}"
                    )
                    # Still keep registration but mark as not loaded
                    return Result.error(
                        code="WORKER_CREATION_FAILED",
                        message=f"Failed to create workers for {model_name}: {ensure_result.error}",
                        details={
                            "model_name": model_name,
                            "error": ensure_result.error,
                            "registered": True,  # Model is registered even if workers failed
                            "workers_created": 0
                        }
                    )
            else:
                self.logger.warning(f"Worker pool not enabled, model {model_name} registered but no workers created")

            return Result.success(data={
                "registered": True,
                "model_name": model_name,
                "new_registration": True,
                "model_type": model_type,
                "device": device,
                "workers_requested": num_workers,
                "workers_created": workers_created,
                "actual_workers": actual_workers,
                "reference_count": 1,
                "model_memory_gb": model_memory_gb
            })

        except Exception as e:
            self.logger.error(f"Model registration error for {model_name}: {e}")
            return Result.error(
                code="MODEL_REGISTRATION_ERROR",
                message=f"Failed to register model {model_name}",
                details={"error": str(e), "model_name": model_name}
            )

    def _estimate_model_memory(self, model_name: str, model_type: str) -> float:
        """Estimate model memory requirements in GB.

        This is a rough estimation based on model name patterns.
        Actual memory usage will be tracked by workers after loading.

        Args:
            model_name: HuggingFace model name
            model_type: Model type

        Returns:
            Estimated memory in GB
        """
        model_name_lower = model_name.lower()

        # Sentence transformers / embeddings (typically small)
        if "all-minilm-l6" in model_name_lower:
            return 0.1  # ~100MB (all-MiniLM-L6-v2 is 23M params, ~60MB)
        elif "all-minilm-l12" in model_name_lower:
            return 0.2  # ~200MB
        elif "all-mpnet-base" in model_name_lower:
            return 0.5  # ~500MB
        elif "sentence-transformers" in model_name_lower or model_type == "embedding":
            return 0.3  # Default for unknown sentence transformers

        # Text generation models (typically larger)
        elif "t5-small" in model_name_lower:
            return 0.3  # ~300MB
        elif "t5-base" in model_name_lower:
            return 1.0  # ~1GB
        elif "t5-large" in model_name_lower:
            return 3.0  # ~3GB
        elif "gpt2" in model_name_lower and "medium" not in model_name_lower and "large" not in model_name_lower:
            return 0.5  # GPT-2 base ~500MB
        elif "gpt2-medium" in model_name_lower:
            return 1.5  # ~1.5GB
        elif "gpt2-large" in model_name_lower:
            return 3.0  # ~3GB
        elif "7b" in model_name_lower:
            return 14.0  # 7B models ~14GB (FP16)
        elif "13b" in model_name_lower:
            return 26.0  # 13B models ~26GB (FP16)

        # Default estimates by type
        elif model_type == "text_generation":
            return 1.0  # Conservative default for text generation
        else:
            return 0.5  # Conservative default for unknown models

    async def release_model(
        self,
        model_name: str,
        wait_for_tasks: bool = True,
        timeout: Optional[float] = None
    ) -> Result:
        """Stop workers for a model and free VRAM immediately.

        Removes registry entry completely. Next request will create fresh entry
        with its own config from the task() call.

        Args:
            model_name: Model identifier to release
            wait_for_tasks: If True, wait for pending tasks to complete before release
            timeout: Maximum seconds to wait for queue to drain (None = infinite)

        Returns:
            Result with release status
        """
        try:
            if model_name not in self.model_registry:
                return Result.success(data={
                    "message": f"Model {model_name} not in registry (nothing to release)"
                })

            registration = self.model_registry[model_name]

            # Check if model is already unloaded
            if not registration.get("loaded", False):
                self.logger.info(f"Model {model_name} already unloaded, removing registry entry")
                del self.model_registry[model_name]
                return Result.success(data={
                    "released": True,
                    "model_name": model_name,
                    "already_unloaded": True
                })

            # Wait for pending tasks to complete if requested
            if wait_for_tasks and self.worker_pool:
                model_queue = self.worker_pool._model_queues.get(model_name)
                if model_queue:
                    self.logger.info(f"Waiting for pending tasks to complete for {model_name}...")
                    start_time = time.time()

                    while not model_queue.empty():
                        if timeout and (time.time() - start_time) > timeout:
                            queue_size = model_queue.qsize()
                            self.logger.warning(
                                f"Timeout waiting for {model_name} queue to drain "
                                f"({queue_size} tasks remaining). Proceeding with release."
                            )
                            break
                        await asyncio.sleep(0.1)  # Check every 100ms

                    if model_queue.empty():
                        elapsed = time.time() - start_time
                        self.logger.info(f"Queue for {model_name} drained successfully ({elapsed:.2f}s)")

            # Stop all workers for this model (unloads model and frees VRAM)
            # Worker pool logging handles all details; we only log errors here
            if self.worker_pool and self.worker_pool.is_enabled:
                stop_result = await self.worker_pool.stop_workers_for_model(model_name)
                if not stop_result.success:
                    self.logger.error(f"Failed to stop workers for {model_name}: {stop_result.error}")

            # Remove registry entry completely (config comes from next request anyway)
            del self.model_registry[model_name]

            return Result.success(data={
                "released": True,
                "unloaded": True,
                "model_name": model_name,
                "vram_freed": True,
                "registry_cleared": True
            })

        except Exception as e:
            return Result.error(
                code="MODEL_RELEASE_ERROR",
                message=f"Failed to release model {model_name}",
                details={"error": str(e)}
            )

    async def drop_model_queue(
        self,
        model_name: str,
        reason: str = "Manual drop"
    ) -> Result:
        """Forcefully drop all pending tasks for a model.

        Use when a large batch was submitted by mistake and needs immediate cancellation.
        This will cancel all futures waiting for results, notifying callers of the cancellation.

        Args:
            model_name: Model identifier whose queue to drop
            reason: Reason for dropping (for logging)

        Returns:
            Result with number of tasks dropped
        """
        try:
            if not self.worker_pool:
                return Result.error(
                    code="WORKER_POOL_NOT_AVAILABLE",
                    message="Worker pool not available"
                )

            model_queue = self.worker_pool._model_queues.get(model_name)
            if not model_queue:
                return Result.error(
                    code="NO_QUEUE_FOR_MODEL",
                    message=f"No queue found for model {model_name}"
                )

            dropped_count = 0
            cancelled_futures = 0

            while not model_queue.empty():
                try:
                    task = model_queue.get_nowait()
                    dropped_count += 1

                    # Cancel any futures waiting for this task
                    if task.task_id in self.worker_pool._pending_tasks:
                        future = self.worker_pool._pending_tasks.pop(task.task_id)
                        if not future.done():
                            future.set_exception(
                                RuntimeError(f"Task dropped from queue: {reason}")
                            )
                            cancelled_futures += 1

                except asyncio.QueueEmpty:
                    break

            self.logger.warning(
                f"Dropped {dropped_count} pending task(s) for {model_name} "
                f"({cancelled_futures} futures cancelled). Reason: {reason}"
            )

            return Result.success(data={
                "dropped": dropped_count,
                "futures_cancelled": cancelled_futures,
                "model_name": model_name,
                "reason": reason
            })

        except Exception as e:
            self.logger.error(f"Error dropping queue for {model_name}: {e}")
            return Result.error(
                code="DROP_QUEUE_ERROR",
                message=f"Failed to drop queue for {model_name}",
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
            for model_name, model_ref in self._loaded_models.items():
                models_status[model_name] = {
                    "reference_count": model_ref.reference_count,
                    "last_accessed": model_ref.last_accessed,
                    "created_at": model_ref.created_at,
                    "source": "direct"
                }
            
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

            # Stop background idle checker task
            if self._idle_checker_task and not self._idle_checker_task.done():
                self._idle_checker_task.cancel()
                try:
                    await self._idle_checker_task
                except asyncio.CancelledError:
                    pass
                self.logger.info("Stopped idle model checker")

            # Log registered models before cleanup
            if self.model_registry:
                self.logger.info(f"Cleaning up {len(self.model_registry)} registered model(s)")
                for model_name, registration in self.model_registry.items():
                    requesters = registration.get("requesters", set())
                    if requesters:
                        requesters_str = ", ".join(requesters)
                        self.logger.info(f"  - {model_name} (requesters: {requesters_str})")
                    else:
                        self.logger.info(f"  - {model_name}")

            # Clear model registry (workers will unload models automatically during shutdown)
            self.model_registry.clear()

            # Shutdown worker pool (workers will unload their current models)
            if self.worker_pool:
                await self.worker_pool.shutdown()

            # Clear cache
            if self.embedding_cache:
                self.embedding_cache.clear_cache()

            # Clear loaded models from direct loading
            self._loaded_models.clear()

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
            # Clear model registry immediately
            self.model_registry.clear()

            # Clear loaded models immediately
            self._loaded_models.clear()

            # Clear cache if available
            if self.embedding_cache:
                self.embedding_cache.clear_cache()

            self._initialized = False

        except Exception as e:
            self.logger.error(f"Force cleanup error: {e}")