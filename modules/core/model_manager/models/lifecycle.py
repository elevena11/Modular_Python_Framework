"""
modules/core/model_manager/models/lifecycle.py
Model lifecycle management - loading, registration, release, and monitoring.

Extracted from services.py to separate lifecycle concerns from service orchestration.
Handles both direct model loading and worker-pool-based model management.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, TYPE_CHECKING
from core.error_utils import Result

# Avoid circular imports
if TYPE_CHECKING:
    from ..settings import ModelManagerSettings
    from ..loaders import LoaderFactory
    from ..workers import WorkerPool

from .reference import ModelReference

MODULE_ID = "core.model_manager"


class ModelLifecycleManager:
    """Manages model lifecycle: loading, registration, release, and monitoring."""
    
    def __init__(
        self,
        settings: "ModelManagerSettings",
        loader_factory: "LoaderFactory",
        worker_pool: Optional["WorkerPool"] = None
    ):
        """Initialize lifecycle manager.
        
        Args:
            settings: Model manager settings
            loader_factory: Factory for loading models
            worker_pool: Optional worker pool for worker-based loading
        """
        self.settings = settings
        self.loader_factory = loader_factory
        self.worker_pool = worker_pool
        self.logger = logging.getLogger(MODULE_ID)
        
        # Model registry - tracks loaded model instances (direct loading)
        self._loaded_models: Dict[str, ModelReference] = {}
        
        # Model registry - tracks registered model requirements from modules
        self.model_registry: Dict[str, Dict[str, Any]] = {}
        
        # Background task for idle model cleanup
        self._idle_checker_task = None
        
        self.logger.info("Model Lifecycle Manager initialized")
    
    def estimate_model_memory(self, model_name: str, model_type: str) -> float:
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
    
    async def get_or_load_model(self, model_name: str, device: str) -> Result:
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
            # Pass Pydantic settings object directly (Pattern 1)
            model_ref = ModelReference(model_name, model_data, self.settings)
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
            await lifecycle.register_model(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_type="embedding"
            )

            # Recommended - specify workers for known load patterns
            await lifecycle.register_model(
                model_name="mixedbread-ai/mxbai-embed-large-v1",
                model_type="embedding",
                num_workers=2  # Capped by available GPUs
            )

            # Text generation model
            await lifecycle.register_model(
                model_name="t5-small",
                model_type="text_generation",
                num_workers=1
            )

            # Explicit CPU usage
            await lifecycle.register_model(
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
            model_memory_gb = self.estimate_model_memory(model_name, model_type)

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
    
    async def start_idle_checker(self):
        """Start background task that checks for idle models and auto-releases them."""
        if self._idle_checker_task is None or self._idle_checker_task.done():
            self._idle_checker_task = asyncio.create_task(self._idle_checker_loop())
            self.logger.info("Started idle model checker background task")
    
    async def stop_idle_checker(self):
        """Stop the idle model checker background task."""
        if self._idle_checker_task and not self._idle_checker_task.done():
            self._idle_checker_task.cancel()
            try:
                await self._idle_checker_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Stopped idle model checker")
    
    async def _idle_checker_loop(self):
        """Background task loop that checks for idle models and auto-releases them.

        Runs every 60 seconds, checks each loaded model's last_activity time,
        and releases models that have exceeded their keep_alive timeout.
        """
        self.logger.info("Idle model checker started")
        check_interval = 60  # Check every 60 seconds

        # Keep checking while lifecycle manager is active
        while True:
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
    
    def get_loaded_models_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all loaded models.
        
        Returns:
            Dictionary of model statuses
        """
        models_status = {}
        for model_name, model_ref in self._loaded_models.items():
            models_status[model_name] = {
                "reference_count": model_ref.reference_count,
                "last_accessed": model_ref.last_accessed,
                "created_at": model_ref.created_at,
                "source": "direct"
            }
        return models_status
    
    def cleanup(self):
        """Clean up lifecycle manager resources."""
        self.model_registry.clear()
        self._loaded_models.clear()
        self.logger.info("Lifecycle manager cleanup completed")
