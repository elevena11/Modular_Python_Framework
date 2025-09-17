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
        
        # Queue management
        self._worker_result_queue = None
        self._global_job_queue = None
        
        # Load balancing state
        self._round_robin_counter = 0
        
        self.logger.info("Worker pool manager initialized")
    
    async def initialize(self) -> Result:
        """Initialize the worker pool for parallel processing.
        
        Returns:
            Result with initialization status
        """
        try:
            num_workers = self.config.get("worker_pool.num_workers", 2)
            devices = self.config.get("worker_pool.devices", ["cuda:0", "cuda:1"])
            
            # Validate device availability
            available_devices = await self._validate_devices(devices)
            if not available_devices:
                return Result.error(
                    code="NO_DEVICES_AVAILABLE",
                    message="No suitable devices available for worker pool"
                )
            
            # Limit workers to available devices
            actual_workers = min(num_workers, len(available_devices))
            
            # Create result queue and global job queue
            self._worker_result_queue = asyncio.Queue()
            self._global_job_queue = asyncio.Queue()
            
            # Create workers
            created_workers = await self._create_workers(actual_workers, available_devices)
            
            if created_workers == 0:
                self.logger.warning("No workers created, worker pool disabled")
                self._worker_pool_enabled = False
                return Result.error(
                    code="WORKER_POOL_INIT_FAILED",
                    message="Failed to create any workers"
                )
            
            self._worker_pool_enabled = True
            self.logger.info(f"Worker pool initialized with {created_workers} workers")
            
            # Preload models if configured
            preloaded_workers = await self._preload_models()
            
            return Result.success(data={
                "worker_pool_enabled": True,
                "workers_created": created_workers,
                "workers_preloaded": preloaded_workers,
                "available_devices": available_devices,
                "workers": {worker_id: worker.device for worker_id, worker in self._workers.items()}
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
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                for device in requested_devices:
                    if device == "cpu":
                        available_devices.append(device)
                    elif device.startswith("cuda:"):
                        gpu_idx = int(device.split(":")[1])
                        if gpu_idx < gpu_count:
                            available_devices.append(device)
                        else:
                            self.logger.warning(f"GPU device {device} not available (only {gpu_count} GPUs)")
                    else:
                        self.logger.warning(f"Unknown device type: {device}")
            else:
                if self.config.get("worker_pool.require_gpu", True):
                    self.logger.error(error_message(
                        module_id=MODULE_ID,
                        error_type="GPU_REQUIREMENT_NOT_MET",
                        details="CUDA not available and GPU required - CPU usage disabled",
                        location="WorkerPool._validate_devices()",
                        context={"require_gpu": True, "cuda_available": False}
                    ))
                    return []
                else:
                    self.logger.warning("CUDA not available, using CPU fallback")
                    available_devices = ["cpu"] * len(requested_devices)
                    
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
    
    async def _create_workers(self, num_workers: int, available_devices: List[str]) -> int:
        """Create worker instances.
        
        Args:
            num_workers: Number of workers to create
            available_devices: Available device list
            
        Returns:
            Number of successfully created workers
        """
        created_workers = 0
        
        for i in range(num_workers):
            device = available_devices[i % len(available_devices)]
            worker_id = f"worker_{i}"
            
            try:
                worker = ModelWorker(worker_id, device, self.model_manager)
                if await worker.start():
                    self._workers[worker_id] = worker
                    created_workers += 1
                    self.logger.info(f"Created worker {worker_id} on device {device}")
                else:
                    self.logger.error(f"Failed to start worker {worker_id} on device {device}")
            except Exception as e:
                self.logger.error(f"Error creating worker {worker_id}: {e}")
        
        return created_workers
    
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
    
    async def get_optimal_worker(self, model_id: str) -> Optional[str]:
        """Get the optimal worker for a given model.
        
        Args:
            model_id: ID of the model to be processed
            
        Returns:
            Worker ID or None if no suitable worker available
        """
        if not self._worker_pool_enabled or not self._workers:
            return None
        
        # Find idle worker with device affinity
        device_affinity = self.config.get("worker_pool.device_affinity", {})
        preferred_devices = device_affinity.get(model_id, [])
        
        # First, try workers on preferred devices
        if preferred_devices:
            for worker_id, worker in self._workers.items():
                if (worker.device in preferred_devices and 
                    worker.state == WorkerState.IDLE and
                    worker.is_running):
                    return worker_id
        
        # Fall back to load balancing strategy
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
        
        Args:
            target_count: Target number of workers
            
        Returns:
            Result with scaling status
        """
        try:
            current_count = len(self._workers)
            
            if target_count > current_count:
                # Scale up - add workers
                devices = self.config.get("worker_pool.devices", ["cuda:0", "cuda:1"])
                available_devices = await self._validate_devices(devices)
                
                added_workers = 0
                for i in range(current_count, target_count):
                    device = available_devices[i % len(available_devices)]
                    worker_id = f"worker_{i}"
                    
                    try:
                        worker = ModelWorker(worker_id, device, self.model_manager)
                        if await worker.start():
                            self._workers[worker_id] = worker
                            added_workers += 1
                            self.logger.info(f"Scaled up: added worker {worker_id} on device {device}")
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