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
    """Worker dedicated to a specific model, processing tasks from a shared model queue.

    Each worker loads one model on startup and never switches. Multiple workers
    for the same model compete for tasks from the shared model queue, providing
    natural load balancing across GPUs.
    """

    def __init__(self, worker_id: str, model_name: str, assigned_gpu: str, model_queue: asyncio.Queue, model_manager_service):
        """Initialize model-dedicated worker.

        Args:
            worker_id: Unique identifier for this worker
            model_name: Model to load (HuggingFace name, e.g., "sentence-transformers/all-MiniLM-L6-v2")
            assigned_gpu: GPU device for this worker (e.g., "cuda:0" or "cpu")
            model_queue: Shared queue for this model (workers compete for tasks)
            model_manager_service: Reference to parent model manager
        """
        self.worker_id = worker_id
        self.model_name = model_name  # NEVER changes
        self.assigned_gpu = assigned_gpu  # NEVER changes
        self.model_queue = model_queue  # Shared with other workers for this model
        self.model_manager = model_manager_service
        self.logger = logging.getLogger(f"{MODULE_ID}.worker.{worker_id}")

        # State management
        self.state = WorkerState.IDLE
        self.current_model = None  # Loaded model instance
        self.last_activity = time.time()
        self.is_running = False
        self._worker_task = None

        # Performance tracking
        self.tasks_processed = 0
        self.total_processing_time = 0.0
        self.errors = 0

        self.logger.info(f"Created for model {model_name} on {assigned_gpu}")
    
    async def start(self) -> bool:
        """Start the worker and load its dedicated model.

        Model is loaded once on startup and never unloaded/switched.
        """
        try:
            # Load the model once at startup
            self.logger.info(f"Loading model {self.model_name} on {self.assigned_gpu}...")
            await self._load_model()

            # Start processing loop
            self.is_running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
            self.logger.info("Started and ready for tasks")
            return True
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="WORKER_START_FAILED",
                details=f"Failed to start worker {self.worker_id} for model {self.model_name}: {e}",
                location="ModelWorker.start()"
            ))
            return False
    
    async def stop(self):
        """Stop the worker and clean up resources.

        Unloads the model and clears CUDA cache to free VRAM.
        """
        self.logger.info("Stopping and unloading model...")
        self.is_running = False
        self.state = WorkerState.SHUTDOWN

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        # Unload model and clear CUDA memory
        await self._unload_model()

        self.logger.info("Stopped and cleaned up")

    async def _unload_model(self):
        """Unload the current model and free GPU memory."""
        try:
            if self.current_model is None:
                self.logger.debug("No model loaded, skipping unload")
                return

            self.logger.info(f"Unloading model {self.model_name} from {self.assigned_gpu}")

            # Clear model reference
            self.current_model = None

            # If on GPU, clear CUDA cache to free VRAM
            if self.assigned_gpu.startswith("cuda"):
                try:
                    import torch
                    import gc

                    # Force garbage collection
                    gc.collect()

                    # Get device index
                    device_idx = int(self.assigned_gpu.split(':')[1]) if ':' in self.assigned_gpu else 0
                    torch.cuda.set_device(device_idx)

                    # Clear CUDA cache
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize(device_idx)

                    # Get memory stats after cleanup
                    allocated = torch.cuda.memory_allocated(device_idx) / (1024**3)
                    reserved = torch.cuda.memory_reserved(device_idx) / (1024**3)

                    self.logger.info(
                        f"Cleared CUDA cache for {self.assigned_gpu}: "
                        f"allocated={allocated:.2f}GB, reserved={reserved:.2f}GB"
                    )

                except Exception as e:
                    self.logger.error(f"Error clearing CUDA cache: {e}")

            self.logger.info(f"Model {self.model_name} unloaded from {self.assigned_gpu}")

        except Exception as e:
            self.logger.error(f"Error unloading model: {e}")
    
    async def _worker_loop(self):
        """Main worker processing loop - pulls from shared model queue.

        Multiple workers for the same model compete for tasks from the shared
        queue, providing natural load balancing.
        """
        self.logger.info("Processing loop started")

        while self.is_running:
            try:
                # Pull from shared model queue - workers for this model compete
                task = await self.model_queue.get()
                self.logger.info(f"Pulled task {task.task_id[:8]} from model queue")

                # Process the task (model already loaded, no switching needed)
                result = await self._process_task(task)

                # Mark task as done in queue
                self.model_queue.task_done()

                # Post result to result queue for background processor
                if hasattr(self.model_manager, 'worker_pool') and self.model_manager.worker_pool:
                    await self.model_manager.worker_pool._worker_result_queue.put(result)
                    self.logger.info(f"Posted result for task {result.task_id[:8]} to result queue")
                else:
                    self.logger.error(f"Cannot route result for task {result.task_id} - worker_pool not available")

            except asyncio.CancelledError:
                # Worker is shutting down
                self.logger.info("Processing loop cancelled")
                break
            except Exception as e:
                self.logger.error(error_message(
                    module_id=MODULE_ID,
                    error_type="WORKER_PROCESSING_ERROR",
                    details=f"Error in processing loop for worker {self.worker_id} (errors: {self.errors}): {e}",
                    location="ModelWorker._worker_loop()"
                ))
                self.errors += 1
                continue

        self.logger.info("Processing loop ended")
    
    async def _process_task(self, task: WorkerTask) -> WorkerResult:
        """Process a single task.

        Model is already loaded (no switching needed).

        Args:
            task: Task to process

        Returns:
            Processing result
        """
        start_time = time.time()
        self.state = WorkerState.BUSY
        self.last_activity = start_time

        try:
            # Process based on task type (model already loaded)
            if task.task_type == "embedding":
                result_data = await self._process_embedding_task(task)
            elif task.task_type == "text_generation":
                result_data = await self._process_text_generation_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            processing_time = time.time() - start_time
            self.tasks_processed += 1
            self.total_processing_time += processing_time
            self.state = WorkerState.IDLE

            self.logger.info(f"Completed task {task.task_id[:8]} in {processing_time:.3f}s")

            return WorkerResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                success=True,
                data=result_data,
                processing_time=processing_time,
                metadata={
                    "device": self.assigned_gpu,
                    "model_name": self.model_name
                }
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.errors += 1
            self.state = WorkerState.ERROR

            self.logger.error(f"Failed to process task {task.task_id[:8]}: {e}")

            return WorkerResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    
    async def _load_model(self):
        """Load this worker's dedicated model on its assigned GPU.

        Model and GPU are fixed at worker creation (never change).
        """
        try:
            self.state = WorkerState.LOADING

            # Clear CUDA cache and synchronize before loading (if using GPU)
            if self.assigned_gpu.startswith("cuda"):
                try:
                    import torch
                    device_idx = int(self.assigned_gpu.split(':')[1]) if ':' in self.assigned_gpu else 0
                    torch.cuda.set_device(device_idx)
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize(device_idx)
                except (ImportError, RuntimeError) as e:
                    self.logger.warning(f"CUDA setup warning: {e}")

            # Load model using LoaderFactory
            if not hasattr(self.model_manager, 'loader_factory'):
                raise RuntimeError("LoaderFactory not initialized in model_manager")

            loader_factory = self.model_manager.loader_factory

            # Get model_type from lifecycle_manager registry (required for explicit loader selection)
            model_type = None
            if (hasattr(self.model_manager, 'lifecycle_manager') and
                self.model_manager.lifecycle_manager and
                hasattr(self.model_manager.lifecycle_manager, 'model_registry') and
                self.model_name in self.model_manager.lifecycle_manager.model_registry):
                model_type = self.model_manager.lifecycle_manager.model_registry[self.model_name].get("model_type")
                self.logger.info(f"Retrieved model_type '{model_type}' from lifecycle_manager registry for {self.model_name}")
            else:
                self.logger.warning(f"Model {self.model_name} not found in lifecycle_manager registry, loader will auto-detect")

            # Load model on assigned GPU with explicit model_type
            self.logger.info(f"Loading model {self.model_name} (type: {model_type}) on {self.assigned_gpu} via LoaderFactory")
            model_result = await loader_factory.load_model(self.model_name, self.assigned_gpu, model_type=model_type)

            if not model_result.success:
                raise RuntimeError(f"Failed to load model {self.model_name}: {model_result.error}")

            self.current_model = model_result.data
            self.last_activity = time.time()
            self.state = WorkerState.IDLE

            self.logger.info(f"Loaded model {self.model_name} on {self.assigned_gpu}")

        except Exception as e:
            self.logger.error(f"Failed to load model {self.model_name}: {e}")
            self.state = WorkerState.ERROR
            raise

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
            if self.assigned_gpu.startswith("cuda"):
                import torch
                device_idx = int(self.assigned_gpu.split(':')[1]) if ':' in self.assigned_gpu else 0
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
            if self.assigned_gpu.startswith("cuda"):
                torch.cuda.synchronize(device_idx)

        except Exception as e:
            self.logger.error(f"Embedding error: {e}")
            raise

        return {
            "embeddings": result_embeddings,
            "model_name": self.model_name,
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

        input_text = task.input_data
        max_length = task.metadata.get("max_length", 128)

        # Tokenize input
        inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(self.assigned_gpu) for k, v in inputs.items()}

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
            "model_name": self.model_name,
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
            "assigned_gpu": self.assigned_gpu,  # Worker's assigned GPU
            "model_name": self.model_name,  # Dedicated model (never changes)
            "state": self.state.value,
            "is_running": self.is_running,
            "tasks_processed": self.tasks_processed,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_processing_time,
            "errors": self.errors,
            "last_activity": self.last_activity
        }