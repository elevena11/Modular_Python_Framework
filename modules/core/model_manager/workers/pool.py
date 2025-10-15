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
        self._available_devices = []  # Detected devices
        self._max_workers = 0  # Maximum workers allowed

        # Queue management
        self._worker_result_queue = None
        self._global_job_queue = None
        self._pending_tasks = {}  # task_id -> asyncio.Future for O(1) result delivery

        self.logger.info("Worker pool manager initialized")
    
    async def initialize(self) -> Result:
        """Initialize the worker pool for parallel processing.

        Detects available devices and sets up queues, but does NOT create workers yet.
        Workers are created lazily when first needed (on-demand or for preloading).

        Returns:
            Result with initialization status
        """
        try:
            num_workers = self.config.get("worker_pool.num_workers", 2)
            devices = self.config.get("worker_pool.devices", ["cuda:0", "cuda:1"])

            # Detect available devices (lightweight operation)
            self._available_devices = await self._validate_devices(devices)
            if not self._available_devices:
                return Result.error(
                    code="NO_DEVICES_AVAILABLE",
                    message="No suitable devices available for worker pool"
                )

            # Store max workers (will create lazily as needed)
            self._max_workers = min(num_workers, len(self._available_devices))

            # Create result queue and global job queue (needed for when workers are created)
            self._worker_result_queue = asyncio.Queue()
            self._global_job_queue = asyncio.Queue()

            # Enable worker pool (workers will be created on-demand)
            self._worker_pool_enabled = True

            # Start background task to process results from queue and deliver to futures
            self._result_processor_task = asyncio.create_task(self._process_results())

            self.logger.info(f"Worker pool initialized (lazy mode): max {self._max_workers} workers, devices: {self._available_devices}")

            # Preload models if configured (this will trigger worker creation)
            preloaded_workers = await self._preload_models()

            return Result.success(data={
                "worker_pool_enabled": True,
                "workers_created": len(self._workers),  # May be 0 if no preloading
                "workers_preloaded": preloaded_workers,
                "available_devices": self._available_devices,
                "max_workers": self._max_workers,
                "lazy_initialization": True
            })

        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="WORKER_POOL_INIT_ERROR",
                details=f"Error initializing worker pool: {e}",
                location="WorkerPool.initialize()",
                context={"error": str(e)}
            ))
            return Result.error(
                code="WORKER_POOL_INIT_ERROR",
                message="Failed to initialize worker pool",
                details={"error": str(e)}
            )
    
    async def _validate_devices(self, requested_devices: List[str]) -> List[str]:
        """Validate and filter available devices.

        Args:
            requested_devices: List of requested device strings

        Returns:
            List of available device strings
        """
        available_devices = []

        try:
            import torch
            has_cuda = torch.cuda.is_available()
            gpu_count = torch.cuda.device_count() if has_cuda else 0

            for device in requested_devices:
                if device == "auto":
                    # AUTO-DETECT: Use best available device
                    if has_cuda and gpu_count > 0:
                        # Add all available GPUs
                        for i in range(gpu_count):
                            available_devices.append(f"cuda:{i}")
                        self.logger.info(f"Auto-detected {gpu_count} GPU(s)")
                    else:
                        # Fallback to CPU
                        available_devices.append("cpu")
                        self.logger.info("Auto-detected CPU (no GPUs available)")

                elif device == "cpu":
                    available_devices.append(device)

                elif device.startswith("cuda:"):
                    if has_cuda:
                        gpu_idx = int(device.split(":")[1])
                        if gpu_idx < gpu_count:
                            available_devices.append(device)
                        else:
                            self.logger.warning(f"GPU {device} not available (only {gpu_count} GPUs)")
                    else:
                        self.logger.warning(f"GPU {device} requested but CUDA not available")
                else:
                    self.logger.warning(f"Unknown device type: {device}")
                    
        except ImportError:
            if self.config.get("worker_pool.require_gpu", True):
                self.logger.error("PyTorch not available and GPU required")
                return []
            else:
                self.logger.warning("PyTorch not available, using CPU fallback")
                available_devices = ["cpu"] * len(requested_devices)
        
        if not available_devices:
            available_devices = ["cpu"]
        
        return available_devices
    
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

    async def verify_model_download(self, model_id: str) -> Result:
        """Verify model exists and download if needed (without loading into memory).

        This is used when preload_workers=0, to ensure the model is downloaded
        during startup but not loaded into memory until first use.

        Uses LoaderFactory to download model files without loading them into memory.
        This is efficient even for large models (7B+ parameters) as it only downloads
        files to cache and never loads them into RAM/VRAM.

        Args:
            model_id: Model identifier to verify/download

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
            if model_id in self.model_manager.model_registry:
                device_preference = self.model_manager.model_registry[model_id]["config"].device

            # Use LoaderFactory to download without loading into memory
            # This is much more efficient than loading and unloading, especially for large models
            if not hasattr(self.model_manager, 'loader_factory'):
                return Result.error(
                    code="LOADER_FACTORY_NOT_AVAILABLE",
                    message="LoaderFactory not initialized in model_manager"
                )

            loader_factory = self.model_manager.loader_factory

            self.logger.info(f"Verifying/downloading model {model_id} (device={device_preference}) without loading into memory...")

            # Download model files without loading (instant if already cached)
            download_result = await loader_factory.download_only(model_id)

            if not download_result.success:
                self.logger.error(f"Model verification/download failed for {model_id}: {download_result.error}")
                return Result.error(
                    code="MODEL_VERIFICATION_FAILED",
                    message=f"Failed to verify/download model {model_id}",
                    details={"error": download_result.error}
                )

            # Model successfully downloaded/verified without loading into memory
            self.logger.info(f"Model {model_id} verified/downloaded successfully (cached={download_result.data.get('cached', False)})")

            return Result.success(data={
                "verified": True,
                "model_id": model_id,
                "downloaded": True,
                "loaded": False,
                "cached": download_result.data.get("cached", False),
                "location": download_result.data.get("location"),
                "source": download_result.data.get("source"),
                "device_preference": device_preference
            })

        except Exception as e:
            self.logger.error(f"Model verification error for {model_id}: {e}")
            return Result.error(
                code="MODEL_VERIFICATION_ERROR",
                message=f"Failed to verify model {model_id}",
                details={"error": str(e), "model_id": model_id}
            )

    async def preload_model(self, model_id: str, num_workers: int = 1) -> Result:
        """Preload a specific model to N workers (download if needed).

        This is called during model registration to ensure models are ready
        before operation begins. If the model needs to be downloaded from
        HuggingFace, it happens here during startup, not during runtime.

        Uses any available workers - device selection happens at model-load time
        based on model's device preference in registry.
        Creates workers on-demand if needed.

        Args:
            model_id: Model identifier to preload
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
            if model_id in self.model_manager.model_registry:
                device_preference = self.model_manager.model_registry[model_id]["config"].device

            # Select any available workers (up to num_workers)
            available_workers = list(self._workers.values())
            target_worker_list = available_workers[:num_workers]
            target_workers = len(target_worker_list)

            if target_workers == 0:
                return Result.error(
                    code="NO_WORKERS_AVAILABLE",
                    message="No workers available"
                )

            self.logger.info(f"Preloading model {model_id} (device={device_preference}) on {target_workers} worker(s)...")

            loaded_workers = []
            errors = []

            # Preload to selected workers (worker selects device based on model config)
            for worker in target_worker_list:
                try:
                    self.logger.debug(f"Preloading {model_id} on worker {worker.worker_id}...")
                    await worker.switch_model(model_id)
                    loaded_workers.append(worker.worker_id)
                    # Log actual device used after loading
                    actual_device = worker.current_device or "unknown"
                    self.logger.info(f"Model {model_id} preloaded on worker {worker.worker_id} (device={actual_device})")
                except Exception as e:
                    error_msg = f"Failed to preload on worker {worker.worker_id}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

            if not loaded_workers:
                return Result.error(
                    code="PRELOAD_FAILED",
                    message=f"Failed to preload model {model_id} on any workers",
                    details={"errors": errors}
                )

            self.logger.info(f"Model {model_id} preloaded successfully on {len(loaded_workers)}/{target_workers} worker(s)")

            return Result.success(data={
                "preloaded": True,
                "model_id": model_id,
                "workers_loaded": len(loaded_workers),
                "worker_ids": loaded_workers,
                "requested_workers": num_workers,
                "errors": errors if errors else None
            })

        except Exception as e:
            self.logger.error(f"Model preload error for {model_id}: {e}")
            return Result.error(
                code="MODEL_PRELOAD_ERROR",
                message=f"Failed to preload model {model_id}",
                details={"error": str(e), "model_id": model_id}
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
        """Submit a task to the shared global queue and return a future for the result.

        Workers pull from the shared global queue, providing natural load balancing.
        This is non-blocking - it submits the task and immediately returns a future.

        Args:
            task: Task to process

        Returns:
            Future that will contain the WorkerResult when complete
        """
        if not self._worker_pool_enabled:
            # Return a completed future with None
            future = asyncio.Future()
            future.set_result(None)
            return future

        # Create a future for this task (O(1) result delivery)
        future = asyncio.Future()
        self._pending_tasks[task.task_id] = future

        # Submit to global queue - workers will pull from it
        self.logger.info(f"Submitting task {task.task_id[:8]} to shared global queue")
        await self._global_job_queue.put(task)

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
            workers_status = {}
            for worker_id, worker in self._workers.items():
                workers_status[worker_id] = worker.get_status()
            
            total_tasks = sum(worker.tasks_processed for worker in self._workers.values())
            total_errors = sum(worker.errors for worker in self._workers.values())
            
            return Result.success(data={
                "enabled": self._worker_pool_enabled,
                "total_workers": len(self._workers),
                "workers_status": workers_status,
                "total_tasks_processed": total_tasks,
                "total_errors": total_errors,
                "global_queue_size": self._global_job_queue.qsize() if self._global_job_queue else 0,
                "result_queue_size": self._worker_result_queue.qsize() if self._worker_result_queue else 0
            })
            
        except Exception as e:
            return Result.error(
                code="WORKER_POOL_STATUS_ERROR",
                message="Failed to get worker pool status",
                details={"error": str(e)}
            )
    
    async def shutdown(self):
        """Shutdown the worker pool."""
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

        # Stop all workers
        for worker_id, worker in list(self._workers.items()):
            try:
                await worker.stop()
                self.logger.info(f"Stopped worker {worker_id}")
            except Exception as e:
                self.logger.error(f"Error stopping worker {worker_id}: {e}")

        self._workers.clear()

        # Clear queues
        if self._global_job_queue:
            while not self._global_job_queue.empty():
                try:
                    self._global_job_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        if self._worker_result_queue:
            while not self._worker_result_queue.empty():
                try:
                    self._worker_result_queue.get_nowait()
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