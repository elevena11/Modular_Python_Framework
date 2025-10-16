"""
modules/core/model_manager/workers/pool.py
Worker pool management and load balancing for model processing.

Extracted from services.py as part of module refactoring.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from .worker import ModelWorker
from .states import WorkerState
from .tasks import WorkerTask, WorkerResult
from core.error_utils import Result, error_message

# Module identity for logging
MODULE_ID = "core.model_manager.workers"


class WorkerPool:
    """Worker pool management with load balancing and scaling."""
    
    def __init__(self, config: Dict[str, Any], model_manager_service):
        """Initialize worker pool.

        Args:
            config: Configuration dictionary
            model_manager_service: Reference to parent model manager
        """
        self.config = config
        self.model_manager = model_manager_service
        self.logger = logging.getLogger(f"{MODULE_ID}.pool")

        # Worker management
        self._workers: Dict[str, ModelWorker] = {}
        self._worker_pool_enabled = False
        self._available_devices = []  # Detected devices (legacy, will be replaced)
        self._max_workers = 0  # Maximum workers allowed

        # GPU memory tracking (keyed by device name like "cuda:0")
        self._gpu_memory: Dict[str, Dict[str, Any]] = {}
        # Structure: {
        #     "cuda:0": {
        #         "total_vram_gb": 7.66,
        #         "used_vram_gb": 0.0,
        #         "free_vram_gb": 7.66,
        #         "loaded_models": {}  # {model_name: memory_gb}
        #     }
        # }

        # Per-model tracking
        self._model_queues: Dict[str, asyncio.Queue] = {}  # model_name -> Queue
        self._model_workers: Dict[str, List[ModelWorker]] = {}  # model_name -> [workers]
        self._gpu_assignments: Dict[str, List[ModelWorker]] = {}  # gpu -> [workers]

        # Queue management
        self._worker_result_queue = None
        self._global_job_queue = None
        self._pending_tasks = {}  # task_id -> asyncio.Future for O(1) result delivery

        self.logger.info("Worker pool manager initialized")
    
    async def initialize(self) -> Result:
        """Initialize the worker pool for parallel processing.

        Detects available GPUs with VRAM tracking and sets up queues.
        Workers are created lazily when first needed (on-demand or for preloading).

        Returns:
            Result with initialization status
        """
        try:
            # Detect GPU hardware and get VRAM info
            self._gpu_memory = await self._detect_gpu_hardware()

            # Log GPU detection results
            if self._gpu_memory:
                self.logger.info(f"Detected {len(self._gpu_memory)} GPU(s) with sufficient free VRAM:")
                for gpu_name, gpu_info in self._gpu_memory.items():
                    self.logger.info(f"  {gpu_name}: {gpu_info['free_vram_gb']:.2f}GB free / {gpu_info['total_vram_gb']:.2f}GB total")
            else:
                self.logger.warning("No GPUs detected with sufficient free VRAM - models must use device='cpu'")

            # Initialize GPU assignments dict
            for gpu_name in self._gpu_memory.keys():
                self._gpu_assignments[gpu_name] = []

            # Create result queue (needed for when workers are created)
            self._worker_result_queue = asyncio.Queue()

            # Enable worker pool (workers will be created on-demand)
            self._worker_pool_enabled = True

            # Start background task to process results from queue and deliver to futures
            self._result_processor_task = asyncio.create_task(self._process_results())

            self.logger.info(f"Worker pool initialized with {len(self._gpu_memory)} available GPU(s)")

            return Result.success(data={
                "worker_pool_enabled": True,
                "workers_created": 0,  # Workers created on-demand
                "available_gpus": list(self._gpu_memory.keys()),
                "gpu_memory": {
                    gpu: {
                        "total_gb": info["total_vram_gb"],
                        "free_gb": info["free_vram_gb"]
                    }
                    for gpu, info in self._gpu_memory.items()
                },
                "lazy_initialization": True
            })

        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="WORKER_POOL_INIT_ERROR",
                details=f"Error initializing worker pool: {e}",
                location="WorkerPool.initialize()"
            ))
            return Result.error(
                code="WORKER_POOL_INIT_ERROR",
                message="Failed to initialize worker pool",
                details={"error": str(e)}
            )
    
    async def _detect_gpu_hardware(self) -> Dict[str, Dict[str, Any]]:
        """Detect available GPUs and their VRAM at startup.

        Only GPUs with >= min_free_vram_gb are considered available.
        Returns empty dict if no GPUs available - failure happens at model registration.

        Returns:
            Dict mapping GPU names to their memory info:
            {
                "cuda:0": {
                    "total_vram_gb": 7.66,
                    "used_vram_gb": 0.0,
                    "free_vram_gb": 7.66,
                    "loaded_models": {}
                }
            }
        """
        min_free_vram_gb = self.config.get("worker_pool.min_free_vram_gb", 6.0)
        available_gpus = {}

        try:
            import torch

            if not torch.cuda.is_available():
                self.logger.warning("No CUDA GPUs available")
                return {}  # Empty dict - will fail at model registration unless device="cpu"

            gpu_count = torch.cuda.device_count()
            self.logger.info(f"Detecting GPU hardware ({gpu_count} CUDA device(s) found)...")

            for gpu_id in range(gpu_count):
                try:
                    # Get VRAM info for this GPU
                    device_props = torch.cuda.get_device_properties(gpu_id)
                    total_vram = device_props.total_memory / (1024**3)  # Convert to GB

                    # Calculate free VRAM
                    torch.cuda.set_device(gpu_id)
                    allocated_vram = torch.cuda.memory_allocated(gpu_id) / (1024**3)  # GB
                    reserved_vram = torch.cuda.memory_reserved(gpu_id) / (1024**3)  # GB
                    used_vram = max(allocated_vram, reserved_vram)  # Use max to be conservative
                    free_vram = total_vram - used_vram

                    # Only use GPUs with sufficient free memory
                    if free_vram >= min_free_vram_gb:
                        gpu_name = f"cuda:{gpu_id}"
                        available_gpus[gpu_name] = {
                            "total_vram_gb": round(total_vram, 2),
                            "used_vram_gb": round(used_vram, 2),
                            "free_vram_gb": round(free_vram, 2),
                            "loaded_models": {}  # Track which models are loaded: {model_name: memory_gb}
                        }
                        self.logger.info(
                            f"  GPU {gpu_id} ({device_props.name}): {free_vram:.2f}GB free / {total_vram:.2f}GB total "
                            f"(threshold: {min_free_vram_gb}GB) - AVAILABLE"
                        )
                    else:
                        self.logger.warning(
                            f"  GPU {gpu_id} ({device_props.name}): {free_vram:.2f}GB free / {total_vram:.2f}GB total "
                            f"(threshold: {min_free_vram_gb}GB) - SKIPPED (insufficient free memory)"
                        )

                except Exception as e:
                    self.logger.error(f"Error detecting GPU {gpu_id}: {e}")
                    continue

            if not available_gpus:
                self.logger.warning(
                    f"No GPUs with >= {min_free_vram_gb}GB free memory. "
                    f"Models must use device='cpu' or free up GPU memory."
                )

        except ImportError:
            self.logger.error("PyTorch not available - cannot detect GPU hardware")
        except Exception as e:
            self.logger.error(f"Unexpected error during GPU detection: {e}")

        return available_gpus

    def _select_gpu_for_model(self, model_name: str, model_memory_gb: float) -> Optional[str]:
        """Select best GPU for a model.

        Strategy:
        1. Find GPUs that DON'T already have this model loaded (one model per GPU max)
        2. Filter GPUs with enough free VRAM for the model
        3. Select GPU with most free VRAM

        Args:
            model_name: Model identifier (e.g., "sentence-transformers/all-MiniLM-L6-v2")
            model_memory_gb: Model size in GB for VRAM checking

        Returns:
            GPU device string (e.g., "cuda:0") or None if no suitable GPU found
        """
        # Find GPUs without this model already loaded
        available_gpus = [
            gpu for gpu in self._gpu_memory.keys()
            if model_name not in self._gpu_memory[gpu]["loaded_models"]
        ]

        if not available_gpus:
            # All GPUs already have this model loaded
            self.logger.warning(
                f"All {len(self._gpu_memory)} GPU(s) already have {model_name} loaded. "
                f"Cannot create more workers (would waste VRAM)."
            )
            return None

        # Filter GPUs with enough free VRAM
        suitable_gpus = [
            gpu for gpu in available_gpus
            if self._gpu_memory[gpu]["free_vram_gb"] >= model_memory_gb
        ]

        if not suitable_gpus:
            gpu_info = [(gpu, f"{self._gpu_memory[gpu]['free_vram_gb']:.2f}GB free") for gpu in available_gpus]
            self.logger.error(
                f"No GPU has {model_memory_gb:.2f}GB free VRAM for {model_name}. "
                f"Available GPUs: {gpu_info}"
            )
            return None

        # Select GPU with most free VRAM
        best_gpu = max(suitable_gpus, key=lambda g: self._gpu_memory[g]["free_vram_gb"])

        self.logger.info(
            f"Selected {best_gpu} for {model_name} "
            f"({self._gpu_memory[best_gpu]['free_vram_gb']:.2f}GB free / {self._gpu_memory[best_gpu]['total_vram_gb']:.2f}GB total)"
        )

        return best_gpu

    def _update_vram_on_load(self, gpu: str, model_name: str, model_memory_gb: float):
        """Update VRAM tracking when model is loaded.

        Args:
            gpu: GPU device name (e.g., "cuda:0")
            model_name: Model identifier
            model_memory_gb: Model size in GB
        """
        if gpu not in self._gpu_memory:
            self.logger.error(f"GPU {gpu} not in memory tracking dict")
            return

        self._gpu_memory[gpu]["used_vram_gb"] += model_memory_gb
        self._gpu_memory[gpu]["free_vram_gb"] -= model_memory_gb
        self._gpu_memory[gpu]["loaded_models"][model_name] = model_memory_gb

        self.logger.debug(
            f"VRAM updated for {gpu}: {model_name} loaded ({model_memory_gb:.3f}GB), "
            f"free: {self._gpu_memory[gpu]['free_vram_gb']:.2f}GB"
        )

    def _update_vram_on_unload(self, gpu: str, model_name: str):
        """Update VRAM tracking when model is unloaded.

        Args:
            gpu: GPU device name (e.g., "cuda:0")
            model_name: Model identifier
        """
        if gpu not in self._gpu_memory:
            self.logger.error(f"GPU {gpu} not in memory tracking dict")
            return

        if model_name in self._gpu_memory[gpu]["loaded_models"]:
            model_memory_gb = self._gpu_memory[gpu]["loaded_models"].pop(model_name)
            self._gpu_memory[gpu]["used_vram_gb"] -= model_memory_gb
            self._gpu_memory[gpu]["free_vram_gb"] += model_memory_gb

            self.logger.debug(
                f"VRAM updated for {gpu}: {model_name} unloaded ({model_memory_gb:.3f}GB), "
                f"free: {self._gpu_memory[gpu]['free_vram_gb']:.2f}GB"
            )
        else:
            self.logger.warning(f"Model {model_name} not found in {gpu} loaded_models tracking")

    async def ensure_workers(self, model_name: str, num_workers: int, model_memory_gb: float, device: str = "gpu") -> Result:
        """Create dedicated workers for a specific model.

        Workers are model-dedicated: they load one model on startup and never switch.
        Multiple workers for the same model share a queue and compete for tasks.

        Args:
            model_name: Model to load (HuggingFace name)
            num_workers: Number of workers to create
            model_memory_gb: Model size in GB (for VRAM checking)
            device: "gpu" (default) or "cpu"

        Returns:
            Result with worker creation status
        """
        try:
            # Check if model already has workers
            if model_name in self._model_workers:
                existing_count = len(self._model_workers[model_name])
                self.logger.warning(f"Model {model_name} already has {existing_count} workers")
                return Result.success(data={
                    "workers_created": 0,
                    "workers_existing": existing_count,
                    "message": f"Model {model_name} already has workers"
                })

            # Create queue for this model (shared by all workers)
            model_queue = asyncio.Queue()
            self._model_queues[model_name] = model_queue
            self._model_workers[model_name] = []

            if device == "cpu":
                # CPU mode: create exactly num_workers workers (no GPU limit)
                self.logger.info(f"Creating {num_workers} CPU worker(s) for {model_name}")
                workers_created = 0

                for i in range(num_workers):
                    worker_id = f"{model_name}_worker_{i}"
                    try:
                        worker = ModelWorker(worker_id, model_name, "cpu", model_queue, self.model_manager)
                        if await worker.start():
                            self._model_workers[model_name].append(worker)
                            workers_created += 1
                            self.logger.info(f"Created CPU worker {worker_id} for {model_name}")
                        else:
                            self.logger.error(f"Failed to start worker {worker_id}")
                    except Exception as e:
                        self.logger.error(f"Error creating worker {worker_id}: {e}")

                return Result.success(data={
                    "workers_created": workers_created,
                    "model_name": model_name,
                    "device": "cpu",
                    "requested": num_workers
                })

            else:  # device == "gpu" (default)
                # GPU mode: Find GPUs without this model loaded
                # Cap workers by number of available GPUs (one model per GPU max)
                available_gpus_for_model = [
                    gpu for gpu in self._gpu_memory.keys()
                    if model_name not in self._gpu_memory[gpu]["loaded_models"]
                    and self._gpu_memory[gpu]["free_vram_gb"] >= model_memory_gb
                ]

                if not available_gpus_for_model:
                    # No GPUs available for this model
                    return Result.error(
                        code="NO_GPU_AVAILABLE",
                        message=f"Cannot create GPU workers for {model_name}: No GPUs available. Use device='cpu' to explicitly run on CPU.",
                        details={
                            "model_name": model_name,
                            "model_memory_gb": model_memory_gb,
                            "available_gpus": len(self._gpu_memory)
                        }
                    )

                # Cap actual workers by available GPUs
                actual_workers = min(num_workers, len(available_gpus_for_model))

                if actual_workers < num_workers:
                    self.logger.warning(
                        f"Requested {num_workers} workers for {model_name}, but only {actual_workers} GPU(s) available without this model. "
                        f"Creating {actual_workers} worker(s) instead."
                    )

                self.logger.info(f"Creating {actual_workers} GPU worker(s) for {model_name} on {actual_workers} different GPU(s)")

                workers_created = 0
                for i in range(actual_workers):
                    # Select best GPU for this worker
                    assigned_gpu = self._select_gpu_for_model(model_name, model_memory_gb)
                    if not assigned_gpu:
                        self.logger.error(f"No suitable GPU found for worker {i} of {model_name}")
                        break

                    worker_id = f"{model_name}_worker_{i}"
                    try:
                        worker = ModelWorker(worker_id, model_name, assigned_gpu, model_queue, self.model_manager)
                        if await worker.start():
                            self._model_workers[model_name].append(worker)
                            self._gpu_assignments[assigned_gpu].append(worker)

                            # Update VRAM tracking
                            self._update_vram_on_load(assigned_gpu, model_name, model_memory_gb)

                            workers_created += 1
                            self.logger.info(f"Created GPU worker {worker_id} for {model_name} on {assigned_gpu}")
                        else:
                            self.logger.error(f"Failed to start worker {worker_id}")
                    except Exception as e:
                        self.logger.error(f"Error creating worker {worker_id}: {e}")

                return Result.success(data={
                    "workers_created": workers_created,
                    "model_name": model_name,
                    "device": "gpu",
                    "requested": num_workers,
                    "actual": actual_workers
                })

        except Exception as e:
            self.logger.error(f"Error ensuring workers for {model_name}: {e}")
            return Result.error(
                code="WORKER_CREATION_ERROR",
                message=f"Failed to create workers for {model_name}",
                details={"error": str(e), "model_name": model_name}
            )

    async def _ensure_workers(self, min_workers: int = 1) -> bool:
        """Ensure at least min_workers are available (create on-demand if needed).

        Args:
            min_workers: Minimum number of workers needed

        Returns:
            True if we have enough workers, False otherwise
        """
        if len(self._workers) >= min_workers:
            return True  # Already have enough workers

        # Need to create workers
        workers_needed = min(min_workers, self._max_workers) - len(self._workers)
        if workers_needed <= 0:
            return len(self._workers) > 0

        self.logger.info(f"Creating {workers_needed} worker(s) on-demand...")

        for i in range(workers_needed):
            worker_id = f"worker_{len(self._workers)}"

            # Assign device from available devices pool (round-robin distribution)
            assigned_device = self._available_devices[len(self._workers) % len(self._available_devices)]

            try:
                # Create worker with assigned device for load balancing
                worker = ModelWorker(worker_id, self.model_manager, assigned_device=assigned_device)
                if await worker.start():
                    self._workers[worker_id] = worker
                    self.logger.info(f"Created worker {worker_id} on-demand (assigned: {assigned_device})")
                else:
                    self.logger.error(f"Failed to start worker {worker_id}")
            except Exception as e:
                self.logger.error(f"Error creating worker {worker_id}: {e}")

        return len(self._workers) > 0
    
    async def _preload_models(self) -> int:
        """Preload models on workers if configured.

        Returns:
            Number of workers with preloaded models
        """
        preloaded_workers = 0

        if self.config.get("worker_pool.preload_embeddings", False):
            self.logger.info("Preloading embedding models on all workers...")
            for worker_id, worker in self._workers.items():
                try:
                    await worker.switch_model("embedding")
                    # Mark as preloaded to prevent auto-unloading
                    worker.is_preloaded = True
                    preloaded_workers += 1
                    self.logger.info(f"Preloaded embedding model on worker {worker_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to preload embedding on worker {worker_id}: {e}")

            self.logger.info(f"Preloaded embedding models on {preloaded_workers}/{len(self._workers)} workers")

        return preloaded_workers

    async def verify_model_download(self, model_name: str) -> Result:
        """Verify model exists and download if needed (without loading into memory).

        This is used when preload_workers=0, to ensure the model is downloaded
        during startup but not loaded into memory until first use.

        Uses LoaderFactory to download model files without loading them into memory.
        This is efficient even for large models (7B+ parameters) as it only downloads
        files to cache and never loads them into RAM/VRAM.

        Args:
            model_name: Model identifier to verify/download

        Returns:
            Result with verification status
        """
        try:
            if not self._worker_pool_enabled:
                return Result.error(
                    code="WORKER_POOL_DISABLED",
                    message="Worker pool not enabled"
                )

            # Get model's device preference for logging
            device_preference = "auto"  # Default
            if model_name in self.model_manager.model_registry:
                device_preference = self.model_manager.model_registry[model_name]["config"].device

            # Use LoaderFactory to download without loading into memory
            # This is much more efficient than loading and unloading, especially for large models
            if not hasattr(self.model_manager, 'loader_factory'):
                return Result.error(
                    code="LOADER_FACTORY_NOT_AVAILABLE",
                    message="LoaderFactory not initialized in model_manager"
                )

            loader_factory = self.model_manager.loader_factory

            self.logger.info(f"Verifying/downloading model {model_name} (device={device_preference}) without loading into memory...")

            # Download model files without loading (instant if already cached)
            download_result = await loader_factory.download_only(model_name)

            if not download_result.success:
                self.logger.error(f"Model verification/download failed for {model_name}: {download_result.error}")
                return Result.error(
                    code="MODEL_VERIFICATION_FAILED",
                    message=f"Failed to verify/download model {model_name}",
                    details={"error": download_result.error}
                )

            # Model successfully downloaded/verified without loading into memory
            self.logger.info(f"Model {model_name} verified/downloaded successfully (cached={download_result.data.get('cached', False)})")

            return Result.success(data={
                "verified": True,
                "model_name": model_name,
                "downloaded": True,
                "loaded": False,
                "cached": download_result.data.get("cached", False),
                "location": download_result.data.get("location"),
                "source": download_result.data.get("source"),
                "device_preference": device_preference
            })

        except Exception as e:
            self.logger.error(f"Model verification error for {model_name}: {e}")
            return Result.error(
                code="MODEL_VERIFICATION_ERROR",
                message=f"Failed to verify model {model_name}",
                details={"error": str(e), "model_name": model_name}
            )

    async def preload_model(self, model_name: str, num_workers: int = 1) -> Result:
        """Preload a specific model to N workers (download if needed).

        This is called during model registration to ensure models are ready
        before operation begins. If the model needs to be downloaded from
        HuggingFace, it happens here during startup, not during runtime.

        Uses any available workers - device selection happens at model-load time
        based on model's device preference in registry.
        Creates workers on-demand if needed.

        Args:
            model_name: Model identifier to preload
            num_workers: Number of workers to preload model on (default: 1)

        Returns:
            Result with preload status including number of workers loaded
        """
        try:
            if not self._worker_pool_enabled:
                return Result.error(
                    code="WORKER_POOL_DISABLED",
                    message="Worker pool not enabled"
                )

            # Ensure we have enough workers (create on-demand if needed)
            if not await self._ensure_workers(min_workers=num_workers):
                return Result.error(
                    code="NO_WORKERS_AVAILABLE",
                    message="Could not create workers"
                )

            # Get model's device preference for logging
            device_preference = "auto"  # Default
            if model_name in self.model_manager.model_registry:
                device_preference = self.model_manager.model_registry[model_name]["config"].device

            # Select any available workers (up to num_workers)
            available_workers = list(self._workers.values())
            target_worker_list = available_workers[:num_workers]
            target_workers = len(target_worker_list)

            if target_workers == 0:
                return Result.error(
                    code="NO_WORKERS_AVAILABLE",
                    message="No workers available"
                )

            self.logger.info(f"Preloading model {model_name} (device={device_preference}) on {target_workers} worker(s)...")

            loaded_workers = []
            errors = []

            # Preload to selected workers (worker selects device based on model config)
            for worker in target_worker_list:
                try:
                    self.logger.debug(f"Preloading {model_name} on worker {worker.worker_id}...")
                    await worker.switch_model(model_name)
                    loaded_workers.append(worker.worker_id)
                    # Log actual device used after loading
                    actual_device = worker.current_device or "unknown"
                    self.logger.info(f"Model {model_name} preloaded on worker {worker.worker_id} (device={actual_device})")
                except Exception as e:
                    error_msg = f"Failed to preload on worker {worker.worker_id}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

            if not loaded_workers:
                return Result.error(
                    code="PRELOAD_FAILED",
                    message=f"Failed to preload model {model_name} on any workers",
                    details={"errors": errors}
                )

            self.logger.info(f"Model {model_name} preloaded successfully on {len(loaded_workers)}/{target_workers} worker(s)")

            return Result.success(data={
                "preloaded": True,
                "model_name": model_name,
                "workers_loaded": len(loaded_workers),
                "worker_ids": loaded_workers,
                "requested_workers": num_workers,
                "errors": errors if errors else None
            })

        except Exception as e:
            self.logger.error(f"Model preload error for {model_name}: {e}")
            return Result.error(
                code="MODEL_PRELOAD_ERROR",
                message=f"Failed to preload model {model_name}",
                details={"error": str(e), "model_name": model_name}
            )

    async def _process_results(self):
        """Background task that processes results from queue and delivers to futures.

        This eliminates the O(n²) queue-shuffling problem by delivering results
        directly to the awaiting future for each task_id.
        """
        self.logger.info("Result processor background task started")
        while self._worker_pool_enabled:
            try:
                # Get result from queue
                result = await self._worker_result_queue.get()
                self.logger.debug(f"Result processor got result for task {result.task_id}")

                # Find the future waiting for this task
                future = self._pending_tasks.pop(result.task_id, None)
                if future and not future.done():
                    # Deliver result to the waiting future
                    future.set_result(result)
                    self.logger.debug(f"Result delivered to future for task {result.task_id}")
                else:
                    # No one waiting for this result (shouldn't happen)
                    self.logger.warning(f"Received result for task {result.task_id} but no future waiting (future={'exists' if future else 'None'}, done={future.done() if future else 'N/A'})")

            except asyncio.CancelledError:
                # Shutting down
                self.logger.info("Result processor task cancelled (shutting down)")
                break
            except Exception as e:
                self.logger.error(f"Error processing result: {e}", exc_info=True)

    async def submit_task(self, task: WorkerTask) -> asyncio.Future:
        """Submit a task to the model-specific queue and return a future for the result.

        Workers for the specific model pull from their shared model queue, providing
        natural load balancing. This is non-blocking - it submits the task and
        immediately returns a future.

        Args:
            task: Task to process (must have model_name attribute)

        Returns:
            Future that will contain the WorkerResult when complete
        """
        if not self._worker_pool_enabled:
            # Return a completed future with None
            future = asyncio.Future()
            future.set_result(None)
            return future

        # Get model name from task
        model_name = task.model_name

        if not model_name or model_name not in self._model_queues:
            # No queue for this model
            self.logger.error(f"No queue found for model {model_name}. Task {task.task_id[:8]} cannot be submitted.")
            future = asyncio.Future()
            future.set_exception(RuntimeError(f"No workers available for model {model_name}"))
            return future

        # Create a future for this task (O(1) result delivery)
        future = asyncio.Future()
        self._pending_tasks[task.task_id] = future

        # Submit to model-specific queue - workers for this model will pull from it
        model_queue = self._model_queues[model_name]
        self.logger.info(f"Submitting task {task.task_id[:8]} to queue for model {model_name}")
        await model_queue.put(task)

        # Return the future immediately (non-blocking!)
        return future
    
    async def scale_workers(self, target_count: int) -> Result:
        """Scale worker pool to target count.

        Creates device-agnostic workers - device selection happens at model-load time.

        Args:
            target_count: Target number of workers

        Returns:
            Result with scaling status
        """
        try:
            current_count = len(self._workers)

            if target_count > current_count:
                # Scale up - add workers with device distribution
                added_workers = 0
                for i in range(current_count, target_count):
                    worker_id = f"worker_{i}"

                    # Assign device from available devices pool (round-robin distribution)
                    assigned_device = self._available_devices[i % len(self._available_devices)]

                    try:
                        worker = ModelWorker(worker_id, self.model_manager, assigned_device=assigned_device)
                        if await worker.start():
                            self._workers[worker_id] = worker
                            added_workers += 1
                            self.logger.info(f"Scaled up: added worker {worker_id} (assigned: {assigned_device})")
                    except Exception as e:
                        self.logger.error(f"Failed to add worker {worker_id}: {e}")

                return Result.success(data={"added_workers": added_workers, "total_workers": len(self._workers)})

            elif target_count < current_count:
                # Scale down - remove workers
                workers_to_remove = list(self._workers.keys())[target_count:]
                removed_workers = 0

                for worker_id in workers_to_remove:
                    try:
                        worker = self._workers.pop(worker_id)
                        await worker.stop()
                        removed_workers += 1
                        self.logger.info(f"Scaled down: removed worker {worker_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to remove worker {worker_id}: {e}")

                return Result.success(data={"removed_workers": removed_workers, "total_workers": len(self._workers)})

            else:
                return Result.success(data={"message": "No scaling needed", "total_workers": len(self._workers)})

        except Exception as e:
            return Result.error(
                code="WORKER_SCALING_ERROR",
                message=f"Failed to scale workers to {target_count}",
                details={"error": str(e)}
            )
    
    async def get_status(self) -> Result:
        """Get worker pool status.

        Returns:
            Result with pool status information
        """
        try:
            # Get per-model worker status
            model_status = {}
            total_tasks = 0
            total_errors = 0

            for model_name, workers in self._model_workers.items():
                worker_info = []
                model_tasks = 0
                model_errors = 0

                for worker in workers:
                    status = worker.get_status()
                    worker_info.append(status)
                    model_tasks += status["tasks_processed"]
                    model_errors += status["errors"]

                total_tasks += model_tasks
                total_errors += model_errors

                model_status[model_name] = {
                    "workers": len(workers),
                    "queue_size": self._model_queues[model_name].qsize() if model_name in self._model_queues else 0,
                    "tasks_processed": model_tasks,
                    "errors": model_errors,
                    "worker_details": worker_info
                }

            return Result.success(data={
                "enabled": self._worker_pool_enabled,
                "total_models": len(self._model_workers),
                "total_workers": sum(len(workers) for workers in self._model_workers.values()),
                "total_tasks_processed": total_tasks,
                "total_errors": total_errors,
                "model_status": model_status,
                "result_queue_size": self._worker_result_queue.qsize() if self._worker_result_queue else 0
            })

        except Exception as e:
            return Result.error(
                code="WORKER_POOL_STATUS_ERROR",
                message="Failed to get worker pool status",
                details={"error": str(e)}
            )
    
    async def stop_workers_for_model(self, model_name: str) -> Result:
        """Stop all workers for a specific model and free VRAM.

        Called when a model is released with zero references.

        Args:
            model_name: Model identifier

        Returns:
            Result with cleanup status
        """
        try:
            if model_name not in self._model_workers:
                self.logger.warning(f"No workers found for model {model_name}")
                return Result.success(data={
                    "workers_stopped": 0,
                    "message": f"No workers found for model {model_name}"
                })

            workers = self._model_workers[model_name]
            workers_stopped = 0

            self.logger.info(f"Stopping {len(workers)} worker(s) for model {model_name}...")

            for worker in workers:
                try:
                    # Stop worker (includes model unloading and CUDA cleanup)
                    await worker.stop()
                    workers_stopped += 1
                    self.logger.info(f"Stopped worker {worker.worker_id}")

                    # Update VRAM tracking if worker was on GPU
                    if worker.assigned_gpu.startswith("cuda"):
                        self._update_vram_on_unload(worker.assigned_gpu, model_name)

                    # Remove from GPU assignments
                    if worker.assigned_gpu in self._gpu_assignments:
                        if worker in self._gpu_assignments[worker.assigned_gpu]:
                            self._gpu_assignments[worker.assigned_gpu].remove(worker)

                except Exception as e:
                    self.logger.error(f"Error stopping worker {worker.worker_id}: {e}")

            # Remove model from tracking
            del self._model_workers[model_name]

            # Clear model queue
            if model_name in self._model_queues:
                queue = self._model_queues[model_name]
                queue_size = queue.qsize()
                if queue_size > 0:
                    self.logger.warning(f"Clearing {queue_size} pending task(s) from queue for model {model_name}")
                    while not queue.empty():
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                del self._model_queues[model_name]

            self.logger.info(f"Stopped {workers_stopped} worker(s) for model {model_name} and freed VRAM")

            return Result.success(data={
                "workers_stopped": workers_stopped,
                "model_name": model_name,
                "vram_freed": True
            })

        except Exception as e:
            self.logger.error(f"Error stopping workers for model {model_name}: {e}")
            return Result.error(
                code="WORKER_STOP_ERROR",
                message=f"Failed to stop workers for model {model_name}",
                details={"error": str(e), "model_name": model_name}
            )

    async def scale_model_workers(
        self,
        model_name: str,
        target_workers: int,
        model_memory_gb: float,
        device: str = "gpu"
    ) -> Result:
        """Scale the number of workers for a specific model.

        If a model already has workers, this method can add or remove workers
        to reach the target count, without stopping all workers and recreating.
        This allows dynamic worker scaling without disrupting existing tasks.

        Args:
            model_name: Model identifier
            target_workers: Target number of workers
            model_memory_gb: Model size in GB (for VRAM checking when adding)
            device: "gpu" (default) or "cpu"

        Returns:
            Result with scaling status
        """
        try:
            if model_name not in self._model_workers:
                return Result.error(
                    code="NO_WORKERS_FOR_MODEL",
                    message=f"No workers found for model {model_name}",
                    details={"model_name": model_name}
                )

            current_workers = self._model_workers[model_name]
            current_count = len(current_workers)

            if target_workers == current_count:
                self.logger.debug(f"Model {model_name} already has {current_count} worker(s)")
                return Result.success(data={
                    "message": f"Model {model_name} already has {current_count} worker(s)",
                    "current_workers": current_count,
                    "target_workers": target_workers,
                    "workers_added": 0,
                    "workers_removed": 0
                })

            elif target_workers > current_count:
                # Add workers
                workers_to_add = target_workers - current_count
                self.logger.info(f"Scaling up {model_name}: adding {workers_to_add} worker(s) ({current_count} -> {target_workers})")

                workers_added = 0
                model_queue = self._model_queues[model_name]

                if device == "cpu":
                    # CPU mode: add exactly workers_to_add workers
                    for i in range(current_count, target_workers):
                        worker_id = f"{model_name}_worker_{i}"
                        try:
                            worker = ModelWorker(worker_id, model_name, "cpu", model_queue, self.model_manager)
                            if await worker.start():
                                self._model_workers[model_name].append(worker)
                                workers_added += 1
                                self.logger.info(f"Added CPU worker {worker_id} for {model_name}")
                            else:
                                self.logger.error(f"Failed to start worker {worker_id}")
                        except Exception as e:
                            self.logger.error(f"Error creating worker {worker_id}: {e}")

                else:  # GPU mode
                    for i in range(current_count, target_workers):
                        # Select best GPU for this worker
                        assigned_gpu = self._select_gpu_for_model(model_name, model_memory_gb)
                        if not assigned_gpu:
                            self.logger.error(f"No suitable GPU found for worker {i} of {model_name}")
                            break

                        worker_id = f"{model_name}_worker_{i}"
                        try:
                            worker = ModelWorker(worker_id, model_name, assigned_gpu, model_queue, self.model_manager)
                            if await worker.start():
                                self._model_workers[model_name].append(worker)
                                self._gpu_assignments[assigned_gpu].append(worker)

                                # Update VRAM tracking
                                self._update_vram_on_load(assigned_gpu, model_name, model_memory_gb)

                                workers_added += 1
                                self.logger.info(f"Added GPU worker {worker_id} for {model_name} on {assigned_gpu}")
                            else:
                                self.logger.error(f"Failed to start worker {worker_id}")
                        except Exception as e:
                            self.logger.error(f"Error creating worker {worker_id}: {e}")

                return Result.success(data={
                    "scaled": True,
                    "direction": "up",
                    "model_name": model_name,
                    "current_workers": current_count,
                    "target_workers": target_workers,
                    "workers_added": workers_added,
                    "workers_removed": 0
                })

            else:
                # Remove workers
                workers_to_remove = current_count - target_workers
                self.logger.info(f"Scaling down {model_name}: removing {workers_to_remove} worker(s) ({current_count} -> {target_workers})")

                workers_removed = 0
                workers_list = self._model_workers[model_name]

                # Remove from the end (newest workers first)
                for i in range(workers_to_remove):
                    if len(workers_list) > target_workers:
                        worker = workers_list.pop()
                        try:
                            await worker.stop()
                            workers_removed += 1
                            self.logger.info(f"Removed worker {worker.worker_id} for {model_name}")

                            # Update VRAM tracking if worker was on GPU
                            if worker.assigned_gpu.startswith("cuda"):
                                self._update_vram_on_unload(worker.assigned_gpu, model_name)

                            # Remove from GPU assignments
                            if worker.assigned_gpu in self._gpu_assignments:
                                if worker in self._gpu_assignments[worker.assigned_gpu]:
                                    self._gpu_assignments[worker.assigned_gpu].remove(worker)

                        except Exception as e:
                            self.logger.error(f"Error stopping worker {worker.worker_id}: {e}")

                return Result.success(data={
                    "scaled": True,
                    "direction": "down",
                    "model_name": model_name,
                    "current_workers": current_count,
                    "target_workers": target_workers,
                    "workers_added": 0,
                    "workers_removed": workers_removed
                })

        except Exception as e:
            self.logger.error(f"Error scaling workers for {model_name}: {e}")
            return Result.error(
                code="WORKER_SCALING_ERROR",
                message=f"Failed to scale workers for {model_name}",
                details={"error": str(e), "model_name": model_name}
            )

    async def shutdown(self):
        """Shutdown the worker pool and clean up all per-model resources."""
        self.logger.info("Shutting down worker pool...")

        # Disable worker pool first (stops result processor loop)
        self._worker_pool_enabled = False

        # Cancel background result processor
        if hasattr(self, '_result_processor_task') and self._result_processor_task:
            self._result_processor_task.cancel()
            try:
                await self._result_processor_task
            except asyncio.CancelledError:
                pass

        # Cancel any pending futures
        for task_id, future in list(self._pending_tasks.items()):
            if not future.done():
                future.cancel()
        self._pending_tasks.clear()

        # Stop all model-dedicated workers
        total_workers_stopped = 0
        for model_name, workers in list(self._model_workers.items()):
            self.logger.info(f"Stopping {len(workers)} worker(s) for model {model_name}...")
            for worker in workers:
                try:
                    await worker.stop()
                    total_workers_stopped += 1
                    self.logger.info(f"Stopped worker {worker.worker_id}")

                    # Update VRAM tracking if worker was on GPU
                    if worker.assigned_gpu.startswith("cuda"):
                        self._update_vram_on_unload(worker.assigned_gpu, model_name)

                except Exception as e:
                    self.logger.error(f"Error stopping worker {worker.worker_id}: {e}")

        self.logger.info(f"Stopped {total_workers_stopped} total workers across {len(self._model_workers)} models")

        # Clear per-model tracking dicts
        self._model_workers.clear()
        self._gpu_assignments.clear()

        # Clear all per-model queues
        for model_name, queue in list(self._model_queues.items()):
            queue_size = queue.qsize()
            if queue_size > 0:
                self.logger.warning(f"Clearing {queue_size} pending task(s) from queue for model {model_name}")
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

        self._model_queues.clear()

        # Clear result queue
        if self._worker_result_queue:
            result_queue_size = self._worker_result_queue.qsize()
            if result_queue_size > 0:
                self.logger.warning(f"Clearing {result_queue_size} unprocessed result(s) from result queue")
                while not self._worker_result_queue.empty():
                    try:
                        self._worker_result_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

        # Clear legacy tracking (will be fully removed in future)
        self._workers.clear()
        if self._global_job_queue:
            while not self._global_job_queue.empty():
                try:
                    self._global_job_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        self.logger.info("Worker pool shutdown complete")
    
    @property
    def is_enabled(self) -> bool:
        """Check if worker pool is enabled.
        
        Returns:
            True if worker pool is enabled
        """
        return self._worker_pool_enabled
    
    @property
    def worker_count(self) -> int:
        """Get current worker count.
        
        Returns:
            Number of active workers
        """
        return len(self._workers)
    
    def get_worker(self, worker_id: str) -> Optional[ModelWorker]:
        """Get worker by ID.
        
        Args:
            worker_id: Worker identifier
            
        Returns:
            Worker instance or None if not found
        """
        return self._workers.get(worker_id)