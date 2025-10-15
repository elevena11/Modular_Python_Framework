"""
modules/core/model_manager/workers/worker.py
Individual worker for GPU model processing and task handling.

Extracted from services.py as part of module refactoring.
"""

import logging
import time
import asyncio
from typing import Optional, Any, Dict

# Import from parent module components
from .states import WorkerState
from .tasks import WorkerTask, WorkerResult
from core.error_utils import error_message, Result

# Module identity for logging
MODULE_ID = "core.model_manager"


class ModelWorker:
    """Worker that loads models on-demand, distributed across GPUs for load balancing.

    Each worker is assigned a preferred device from the available device pool.
    When a model requests "auto" device, it loads on the worker's assigned device.
    This enables true multi-GPU parallelism with automatic load distribution.
    """

    def __init__(self, worker_id: str, model_manager_service, assigned_device: Optional[str] = None):
        """Initialize model worker with device assignment.

        Args:
            worker_id: Unique identifier for this worker
            model_manager_service: Reference to parent model manager
            assigned_device: Preferred device for this worker (for load balancing across GPUs)
        """
        self.worker_id = worker_id
        self.model_manager = model_manager_service
        self.logger = logging.getLogger(f"{MODULE_ID}.worker.{worker_id}")

        # Device assignment for load balancing
        self.assigned_device = assigned_device  # Worker's preferred device from pool

        # State management
        self.state = WorkerState.IDLE
        self.current_model_id = None
        self.current_model = None
        self.current_device = None  # Track current device (determined by loaded model)
        self.is_preloaded = False  # Track if current model was preloaded
        self.last_activity = time.time()
        self.is_running = False
        self._worker_task = None

        # Performance tracking
        self.tasks_processed = 0
        self.total_processing_time = 0.0
        self.errors = 0
        self.model_switches = 0

        device_info = f" (assigned: {assigned_device})" if assigned_device else ""
        self.logger.info(f"Worker {worker_id} created{device_info}")
    
    async def start(self) -> bool:
        """Start the worker processing loop."""
        try:
            self.is_running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
            self.logger.info(f"Worker {self.worker_id} started")
            return True
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="WORKER_START_FAILED",
                details=f"Failed to start worker {self.worker_id}: {e}",
                location="ModelWorker.start()",
                context={"worker_id": self.worker_id, "error": str(e)}
            ))
            return False
    
    async def stop(self):
        """Stop the worker and clean up resources."""
        self.logger.info(f"Stopping worker {self.worker_id}")
        self.is_running = False
        self.state = WorkerState.SHUTDOWN
        
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        # Unload current model
        if self.current_model_id:
            await self._unload_model()
        
        self.logger.info(f"Worker {self.worker_id} stopped")
    
    async def _worker_loop(self):
        """Main worker processing loop - pulls from shared global job queue."""
        self.logger.info(f"Worker {self.worker_id} processing loop started")

        while self.is_running:
            try:
                # Pull from shared global queue - all workers compete for tasks
                if not (hasattr(self.model_manager, 'worker_pool') and
                       self.model_manager.worker_pool and
                       self.model_manager.worker_pool._global_job_queue is not None):
                    # No global queue available, sleep and retry
                    await asyncio.sleep(0.1)
                    continue

                # Wait for next task from shared queue (timeout for model idle checks)
                try:
                    task = await asyncio.wait_for(
                        self.model_manager.worker_pool._global_job_queue.get(),
                        timeout=self.model_manager.config.get("worker_pool.queue_timeout", 30)
                    )
                    self.model_manager.worker_pool._global_job_queue.task_done()
                    self.logger.info(f"Worker {self.worker_id} pulled task {task.task_id[:8]} from shared queue")
                except asyncio.TimeoutError:
                    # No tasks available, check for model timeout
                    await self._check_model_timeout()
                    continue

                # Process the task
                result = await self._process_task(task)

                # Post result to result queue for background processor
                if hasattr(self.model_manager, 'worker_pool') and self.model_manager.worker_pool:
                    await self.model_manager.worker_pool._worker_result_queue.put(result)
                    self.logger.info(f"Worker {self.worker_id} posted result for task {result.task_id[:8]} to result queue")
                else:
                    self.logger.error(f"Cannot route result for task {result.task_id} - worker_pool not available")

            except Exception as e:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="WORKER_PROCESSING_ERROR",
                    details=f"Worker {self.worker_id} error in processing loop: {e}",
                    location="ModelWorker._worker_loop()",
                    context={"worker_id": self.worker_id, "errors": self.errors, "error": str(e)}
                ))
                self.errors += 1
                continue

        self.logger.info(f"Worker {self.worker_id} processing loop ended")
    
    async def _process_task(self, task: WorkerTask) -> WorkerResult:
        """Process a single task.

        Args:
            task: Task to process

        Returns:
            Processing result
        """
        start_time = time.time()
        self.state = WorkerState.BUSY
        self.last_activity = start_time

        timing_breakdown = {
            "model_switch": 0.0,
            "actual_processing": 0.0,
            "overhead": 0.0
        }

        try:
            # Ensure correct model is loaded
            if self.current_model_id != task.model_id:
                switch_start = time.time()
                await self._switch_model(task.model_id)
                timing_breakdown["model_switch"] = time.time() - switch_start

            # Process based on task type
            process_start = time.time()
            if task.task_type == "embedding":
                result_data = await self._process_embedding_task(task)
            elif task.task_type == "text_generation":
                result_data = await self._process_text_generation_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            timing_breakdown["actual_processing"] = time.time() - process_start

            processing_time = time.time() - start_time
            timing_breakdown["overhead"] = processing_time - timing_breakdown["model_switch"] - timing_breakdown["actual_processing"]

            self.tasks_processed += 1
            self.total_processing_time += processing_time
            self.state = WorkerState.IDLE

            self.logger.info(f"Worker {self.worker_id} completed task {task.task_id} in {processing_time:.3f}s (model_switch: {timing_breakdown['model_switch']:.3f}s, processing: {timing_breakdown['actual_processing']:.3f}s, overhead: {timing_breakdown['overhead']:.3f}s)")

            return WorkerResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                success=True,
                data=result_data,
                processing_time=processing_time,
                metadata={
                    "device": self.current_device,
                    "model_id": task.model_id,
                    "timing_breakdown": timing_breakdown
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.errors += 1
            self.state = WorkerState.ERROR
            
            self.logger.error(f"Worker {self.worker_id} failed to process task {task.task_id}: {e}")
            
            return WorkerResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    async def _switch_model(self, model_id: str):
        """Switch to a different model.

        Args:
            model_id: ID of model to load
        """
        self.state = WorkerState.LOADING

        # Unload current model if any
        if self.current_model_id and self.current_model_id != model_id:
            await self._unload_model()

        # Load new model
        await self._load_model(model_id)
        self.model_switches += 1

        # Set back to IDLE so worker is available for task distribution
        self.state = WorkerState.IDLE

        self.logger.info(f"Worker {self.worker_id} switched to model {model_id}")
    
    async def switch_model(self, model_id: str):
        """Switch to a different model (public interface for preloading)."""
        await self._switch_model(model_id)
    
    async def _load_model(self, model_id: str):
        """Load a model on this worker with CUDA context management.

        Device selection is based entirely on model requirements, not worker assignment.

        Args:
            model_id: ID of model to load
        """
        try:
            # Get model's device preference from registry
            target_device = None
            if model_id in self.model_manager.model_registry:
                model_config = self.model_manager.model_registry[model_id]["config"]
                requested_device = model_config.device

                # Resolve device preference based on model requirements
                if requested_device == "cpu":
                    # Model explicitly requests CPU
                    target_device = "cpu"
                    self.logger.info(f"Model {model_id} requests CPU execution")
                elif requested_device == "auto":
                    # Auto-select best available device
                    target_device = self._auto_select_device()
                    self.logger.info(f"Model {model_id} auto-selected device: {target_device}")
                elif requested_device == "cuda":
                    # Model wants any available GPU
                    target_device = self._select_available_gpu() or "cpu"
                    self.logger.info(f"Model {model_id} requests GPU, using: {target_device}")
                elif requested_device.startswith("cuda:"):
                    # Model requests specific GPU
                    target_device = requested_device
                    self.logger.info(f"Model {model_id} requests specific GPU: {target_device}")
                else:
                    # Unknown device preference, use auto
                    self.logger.warning(f"Model {model_id} has unknown device '{requested_device}', using auto")
                    target_device = self._auto_select_device()
            else:
                # No registry info, use auto
                target_device = self._auto_select_device()

            # Clear CUDA cache and synchronize before loading
            if target_device.startswith("cuda"):
                try:
                    import torch
                    device_idx = int(target_device.split(':')[1]) if ':' in target_device else 0
                    torch.cuda.set_device(device_idx)
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize(device_idx)
                except (ImportError, RuntimeError) as e:
                    self.logger.warning(f"Worker {self.worker_id} CUDA setup warning: {e}")

            # Note: Removed CPU refusal check - models can explicitly request CPU now

            # Load model instance directly on target device
            # Each worker needs its own model instance, not shared models

            # Get model type from config (populated by register_model())
            model_type = self.model_manager.config.get(f"models.{model_id}.type")

            if not model_type:
                # Check if model is in registry
                if model_id in self.model_manager.model_registry:
                    model_type = self.model_manager.model_registry[model_id]["config"].model_type
                else:
                    raise ValueError(f"Unknown model_id: {model_id} - not found in registry")

            # Load model using LoaderFactory (single unified path for all model types)
            model_result = await self._load_model_via_factory(model_id, target_device)

            if not model_result.success:
                raise RuntimeError(f"Failed to load model {model_id}: {model_result.error}")

            self.current_model = model_result.data
            self.current_model_id = model_id
            self.current_device = target_device  # Track which device we loaded on
            self.last_activity = time.time()

            self.logger.info(f"Worker {self.worker_id} loaded model {model_id} on device {target_device}")

        except Exception as e:
            self.logger.error(f"Worker {self.worker_id} failed to load model {model_id}: {e}")
            self.state = WorkerState.ERROR
            raise

    def _auto_select_device(self) -> str:
        """Auto-select best available device for load balancing.

        Uses worker's assigned device if available (for multi-GPU load balancing).
        Otherwise falls back to first GPU or CPU.

        Returns:
            Device string (e.g., 'cuda:0', 'cuda:1', 'cpu')
        """
        # Use assigned device if worker has one (for load balancing)
        if self.assigned_device:
            return self.assigned_device

        # Fallback: select first available GPU
        try:
            import torch
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                return "cuda:0"
            else:
                return "cpu"
        except ImportError:
            return "cpu"

    def _select_available_gpu(self) -> Optional[str]:
        """Select an available GPU device for load balancing.

        Uses worker's assigned device if it's a GPU, otherwise selects first GPU.

        Returns:
            GPU device string (e.g., 'cuda:0', 'cuda:1') or None if no GPU available
        """
        # Use assigned device if it's a GPU
        if self.assigned_device and self.assigned_device.startswith("cuda"):
            return self.assigned_device

        # Fallback: select first available GPU
        try:
            import torch
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                return "cuda:0"
            else:
                return None
        except ImportError:
            return None

    async def _load_model_via_factory(self, model_id: str, target_device: str) -> Result:
        """Load model using LoaderFactory (unified path for all model types).

        Args:
            model_id: ID of the model to load
            target_device: Target device to load model on

        Returns:
            Result with model instance
        """
        # Use target_device (should always be provided in device-agnostic architecture)
        device = target_device if target_device else "cpu"

        # Get loader_factory from model_manager
        if not hasattr(self.model_manager, 'loader_factory'):
            return Result.error(
                code="LOADER_FACTORY_NOT_AVAILABLE",
                message="LoaderFactory not initialized in model_manager"
            )

        loader_factory = self.model_manager.loader_factory

        # Use factory to load model (automatically selects correct loader)
        self.logger.info(f"Loading model {model_id} on {device} via LoaderFactory")
        return await loader_factory.load_model(model_id, device)

    async def _unload_model(self):
        """Unload current model from this worker and free GPU memory."""
        if self.current_model_id:
            self.state = WorkerState.UNLOADING

            # Actually move model to CPU to free GPU memory
            if self.current_model and self.current_device and self.current_device.startswith("cuda"):
                try:
                    import torch

                    # Extract actual model from result data dictionary
                    model_obj = None
                    if isinstance(self.current_model, dict):
                        model_obj = self.current_model.get("model")

                    # Move model to CPU to free GPU memory
                    if model_obj and hasattr(model_obj, 'to'):
                        self.logger.debug(f"Worker {self.worker_id} moving model {self.current_model_id} to CPU...")
                        model_obj.to('cpu')
                        self.logger.info(f"Worker {self.worker_id} moved model {self.current_model_id} to CPU")

                    # Also handle tokenizer if present (for text generation models)
                    tokenizer_obj = None
                    if isinstance(self.current_model, dict):
                        tokenizer_obj = self.current_model.get("tokenizer")
                    if tokenizer_obj and hasattr(tokenizer_obj, 'to'):
                        tokenizer_obj.to('cpu')
                        self.logger.debug(f"Worker {self.worker_id} moved tokenizer to CPU")

                    # Clear CUDA cache to actually free memory
                    torch.cuda.empty_cache()
                    self.logger.info(f"Worker {self.worker_id} cleared CUDA cache for {self.current_model_id}")

                    # Explicitly delete model reference to help garbage collection
                    del model_obj
                    if tokenizer_obj:
                        del tokenizer_obj

                except Exception as e:
                    self.logger.error(f"Worker {self.worker_id} failed to free GPU memory: {e}", exc_info=True)

            # Release model reference from model manager
            if self.current_model_id in self.model_manager._loaded_models:
                await self.model_manager.release_model(self.current_model_id)

            # Clear worker's model reference
            self.current_model = None
            self.current_model_id = None
            self.current_device = None  # Clear device tracking
            self.is_preloaded = False
            self.state = WorkerState.IDLE

            self.logger.info(f"Worker {self.worker_id} unloaded model completely")

    async def _check_model_timeout(self):
        """Check if current model should be unloaded due to inactivity."""
        if not self.current_model_id:
            return
        
        # Don't unload preloaded models
        if self.is_preloaded:
            self.logger.debug(f"Worker {self.worker_id} keeping preloaded model {self.current_model_id}")
            return
        
        idle_timeout = self.model_manager.config.get("worker_pool.model_idle_timeout", 300)
        if (time.time() - self.last_activity) > idle_timeout:
            self.logger.info(f"Worker {self.worker_id} unloading idle model {self.current_model_id}")
            await self._unload_model()
    
    async def _process_embedding_task(self, task: WorkerTask):
        """Process an embedding task.

        Args:
            task: Embedding task

        Returns:
            Embedding results
        """
        if "model" not in self.current_model:
            raise RuntimeError("No embedding model loaded")

        model = self.current_model["model"]
        texts = task.input_data

        # Generate embeddings with CUDA synchronization
        try:
            # Ensure CUDA context is correct for this worker
            if self.current_device and self.current_device.startswith("cuda"):
                import torch
                device_idx = int(self.current_device.split(':')[1]) if ':' in self.current_device else 0
                torch.cuda.set_device(device_idx)

            # Generate embeddings with explicit numpy conversion
            # convert_to_numpy=True ensures we get numpy arrays that can be safely converted
            # Run in thread executor to avoid blocking event loop (enables true parallel processing)
            loop = asyncio.get_event_loop()

            if isinstance(texts, str):
                embeddings = await loop.run_in_executor(
                    None,  # Use default ThreadPoolExecutor
                    lambda: model.encode([texts], convert_to_numpy=True, show_progress_bar=False)
                )
                # Make a copy to avoid shared memory issues, then convert to list
                import numpy as np
                result_embeddings = np.array(embeddings[0], copy=True).tolist()
            else:
                embeddings = await loop.run_in_executor(
                    None,  # Use default ThreadPoolExecutor
                    lambda: model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
                )
                # Make copies to avoid shared memory issues, then convert to lists
                import numpy as np
                result_embeddings = [np.array(emb, copy=True).tolist() for emb in embeddings]

            # Synchronize CUDA operations after processing
            if self.current_device and self.current_device.startswith("cuda"):
                torch.cuda.synchronize(device_idx)

        except Exception as e:
            self.logger.error(f"Worker {self.worker_id} embedding error: {e}")
            raise

        return {
            "embeddings": result_embeddings,
            "model_id": task.model_id,
            "dimension": len(result_embeddings[0] if isinstance(result_embeddings[0], list) else result_embeddings)
        }
    
    async def _process_text_generation_task(self, task: WorkerTask):
        """Process a text generation task.
        
        Args:
            task: Text generation task
            
        Returns:
            Generation results
        """
        if "model" not in self.current_model or "tokenizer" not in self.current_model:
            raise RuntimeError("No text generation model loaded")
        
        model = self.current_model["model"]
        tokenizer = self.current_model["tokenizer"]
        device = self.current_model["device"]
        
        input_text = task.input_data
        max_length = task.metadata.get("max_length", 128)
        
        # Tokenize input
        inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate
        try:
            import torch
        except ImportError:
            raise RuntimeError("PyTorch required for text generation")
            
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
        
        return {
            "generated_text": generated_text,
            "model_id": task.model_id,
            "input_length": len(input_text),
            "output_length": len(generated_text)
        }
    
    def get_status(self):
        """Get worker status information.

        Returns:
            Worker status dictionary
        """
        avg_processing_time = (
            self.total_processing_time / max(1, self.tasks_processed)
        )

        return {
            "worker_id": self.worker_id,
            "assigned_device": self.assigned_device,  # Worker's assigned device for load balancing
            "device": self.current_device,  # Device of currently loaded model
            "state": self.state.value,
            "current_model_id": self.current_model_id,
            "is_running": self.is_running,
            "tasks_processed": self.tasks_processed,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_processing_time,
            "errors": self.errors,
            "model_switches": self.model_switches,
            "last_activity": self.last_activity
        }