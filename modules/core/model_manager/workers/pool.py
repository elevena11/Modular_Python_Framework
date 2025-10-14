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

        # Load balancing state
        self._round_robin_counter = 0

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

            try:
                # Create device-agnostic worker (no device parameter)
                worker = ModelWorker(worker_id, self.model_manager)
                if await worker.start():
                    self._workers[worker_id] = worker
                    self.logger.info(f"Created worker {worker_id} on-demand")
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
        """Verify model exists and download if needed (without loading to workers).

        This is used when preload_workers=0, to ensure the model is downloaded
        during startup but not loaded into memory until first use.

        Uses any available worker - device selection happens at model-load time.
        Creates worker on-demand if needed.

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

            # Ensure at least one worker exists (create on-demand if needed)
            if not await self._ensure_workers(min_workers=1):
                return Result.error(
                    code="NO_WORKERS_AVAILABLE",
                    message="Could not create workers"
                )

            # Get model's device preference for logging
            device_preference = "auto"  # Default
            if model_id in self.model_manager.model_registry:
                device_preference = self.model_manager.model_registry[model_id]["config"].device

            # Pick any available worker (device selected at model-load time)
            worker = next(iter(self._workers.values()))

            self.logger.info(f"Verifying/downloading model {model_id} (device={device_preference}) using worker {worker.worker_id}...")

            # Load model (triggers download if needed, worker selects device based on model config)
            try:
                await worker.switch_model(model_id)
                self.logger.info(f"Model {model_id} verified/downloaded successfully")

                # Immediately unload to free memory (download is cached)
                await worker._unload_model()
                self.logger.debug(f"Model {model_id} unloaded after verification")

                return Result.success(data={
                    "verified": True,
                    "model_id": model_id,
                    "downloaded": True,
                    "loaded": False,
                    "device_preference": device_preference
                })
            except Exception as e:
                self.logger.error(f"Model verification/download failed for {model_id}: {e}")
                return Result.error(
                    code="MODEL_VERIFICATION_FAILED",
                    message=f"Failed to verify/download model {model_id}",
                    details={"error": str(e)}
                )

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

    async def get_optimal_worker(self, model_id: str) -> Optional[str]:
        """Get the optimal worker for a given model.

        Workers are device-agnostic - device selection happens at model-load time
        based on model's device preference. This method just finds an available worker.
        Creates worker on-demand if needed.

        Args:
            model_id: ID of the model to be processed

        Returns:
            Worker ID or None if no suitable worker available
        """
        if not self._worker_pool_enabled:
            return None

        # Ensure at least one worker exists (create on-demand if needed)
        if not await self._ensure_workers(min_workers=1):
            return None

        # Use load balancing strategy to select worker
        load_balancing = self.config.get("worker_pool.load_balancing", "round_robin")

        if load_balancing == "round_robin":
            return self._get_round_robin_worker()
        elif load_balancing == "least_busy":
            return self._get_least_busy_worker()
        else:
            # Default to first available idle worker
            for worker_id, worker in self._workers.items():
                if worker.state == WorkerState.IDLE and worker.is_running:
                    return worker_id

        return None
    
    def _get_round_robin_worker(self) -> Optional[str]:
        """Get next worker using round-robin strategy.
        
        Returns:
            Worker ID or None if no workers available
        """
        worker_ids = list(self._workers.keys())
        if not worker_ids:
            return None
        
        attempts = 0
        while attempts < len(worker_ids):
            worker_id = worker_ids[self._round_robin_counter % len(worker_ids)]
            worker = self._workers[worker_id]
            
            self._round_robin_counter = (self._round_robin_counter + 1) % len(worker_ids)
            
            if worker.state == WorkerState.IDLE and worker.is_running:
                return worker_id
            
            attempts += 1
        
        return None
    
    def _get_least_busy_worker(self) -> Optional[str]:
        """Get worker with least load using least-busy strategy.
        
        Returns:
            Worker ID or None if no workers available
        """
        best_worker = None
        min_queue_size = float('inf')
        
        for worker_id, worker in self._workers.items():
            if worker.is_running and worker.state != WorkerState.SHUTDOWN:
                queue_size = worker.task_queue.qsize()
                if queue_size < min_queue_size:
                    min_queue_size = queue_size
                    best_worker = worker_id
        
        return best_worker
    
    async def submit_task(self, task: WorkerTask) -> Optional[WorkerResult]:
        """Submit a task to the worker pool.
        
        Args:
            task: Task to process
            
        Returns:
            Task result or None if submission failed
        """
        if not self._worker_pool_enabled:
            return None
        
        # Get optimal worker for this task
        worker_id = await self.get_optimal_worker(task.model_id)
        
        if worker_id:
            # Submit to specific worker
            worker = self._workers[worker_id]
            if await worker.submit_task(task):
                # Wait for result from result queue
                return await self._get_task_result(task.task_id)
        else:
            # Submit to global queue
            await self._global_job_queue.put(task)
            return await self._get_task_result(task.task_id)
        
        return None
    
    async def _get_task_result(self, task_id: str, timeout: float = 60.0) -> Optional[WorkerResult]:
        """Wait for task result from result queue.
        
        Args:
            task_id: ID of task to wait for
            timeout: Maximum time to wait for result
            
        Returns:
            Task result or None if timeout
        """
        try:
            while True:
                result = await asyncio.wait_for(
                    self._worker_result_queue.get(),
                    timeout=timeout
                )
                if result.task_id == task_id:
                    return result
                else:
                    # Put back result for different task
                    await self._worker_result_queue.put(result)
        except asyncio.TimeoutError:
            self.logger.warning(f"Task {task_id} result timeout after {timeout}s")
            return None
    
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
                # Scale up - add device-agnostic workers
                added_workers = 0
                for i in range(current_count, target_count):
                    worker_id = f"worker_{i}"

                    try:
                        worker = ModelWorker(worker_id, self.model_manager)
                        if await worker.start():
                            self._workers[worker_id] = worker
                            added_workers += 1
                            self.logger.info(f"Scaled up: added worker {worker_id}")
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
        
        # Stop all workers
        for worker_id, worker in list(self._workers.items()):
            try:
                await worker.stop()
                self.logger.info(f"Stopped worker {worker_id}")
            except Exception as e:
                self.logger.error(f"Error stopping worker {worker_id}: {e}")
        
        self._workers.clear()
        self._worker_pool_enabled = False
        
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