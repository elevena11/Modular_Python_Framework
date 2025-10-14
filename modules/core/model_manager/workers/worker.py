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
from core.error_utils import error_message

# Module identity for logging
MODULE_ID = "core.model_manager"


class ModelWorker:
    """Device-agnostic worker that loads models on-demand based on model requirements.

    Workers are generic execution contexts - they don't have pre-assigned devices.
    Device selection happens at model-load time based on the model's requirements.
    """

    def __init__(self, worker_id: str, model_manager_service):
        """Initialize model worker (device-agnostic).

        Args:
            worker_id: Unique identifier for this worker
            model_manager_service: Reference to parent model manager
        """
        self.worker_id = worker_id
        self.model_manager = model_manager_service
        self.logger = logging.getLogger(f"{MODULE_ID}.worker.{worker_id}")

        # State management
        self.state = WorkerState.IDLE
        self.current_model_id = None
        self.current_model = None
        self.current_device = None  # Track current device (determined by loaded model)
        self.is_preloaded = False  # Track if current model was preloaded
        self.last_activity = time.time()
        self.task_queue = asyncio.Queue()
        self.is_running = False
        self._worker_task = None

        # Performance tracking
        self.tasks_processed = 0
        self.total_processing_time = 0.0
        self.errors = 0
        self.model_switches = 0

        self.logger.info(f"Worker {worker_id} created")
    
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
    
    async def submit_task(self, task: WorkerTask) -> bool:
        """Submit a task to this worker.
        
        Args:
            task: Task to process
            
        Returns:
            True if task was accepted
        """
        if not self.is_running or self.state == WorkerState.SHUTDOWN:
            return False
        
        try:
            await self.task_queue.put(task)
            self.logger.debug(f"Task {task.task_id} submitted to worker {self.worker_id}")
            return True
        except Exception as e:
            self.logger.error(error_message(
                module_id=MODULE_ID,
                error_type="TASK_SUBMISSION_FAILED",
                details=f"Failed to submit task to worker {self.worker_id}: {e}",
                location="ModelWorker.submit_task()",
                context={"worker_id": self.worker_id, "task_id": task.task_id, "error": str(e)}
            ))
            return False
    
    async def _worker_loop(self):
        """Main worker processing loop - consumes from global job queue."""
        self.logger.info(f"Worker {self.worker_id} processing loop started")
        
        while self.is_running:
            try:
                # Try individual worker queue first (for direct worker assignment)
                try:
                    task = await asyncio.wait_for(
                        self.task_queue.get(), 
                        timeout=1.0  # Short timeout for individual queue
                    )
                    self.task_queue.task_done()
                    self.logger.debug(f"Worker {self.worker_id} got task from individual queue")
                except asyncio.TimeoutError:
                    # No individual tasks, try global job queue if available
                    if (hasattr(self.model_manager, 'worker_pool') and
                        self.model_manager.worker_pool and
                        self.model_manager.worker_pool._global_job_queue is not None):
                        task = await asyncio.wait_for(
                            self.model_manager.worker_pool._global_job_queue.get(),
                            timeout=self.model_manager.config.get("worker_pool.queue_timeout", 30)
                        )
                        self.model_manager.worker_pool._global_job_queue.task_done()
                        self.logger.debug(f"Worker {self.worker_id} got task from global queue")
                    else:
                        # No tasks available, continue loop
                        continue
                
                # Process the task
                result = await self._process_task(task)

                # Always use result queue for simplicity and reliability
                # Access result queue via worker_pool
                if hasattr(self.model_manager, 'worker_pool') and self.model_manager.worker_pool:
                    await self.model_manager.worker_pool._worker_result_queue.put(result)
                    self.logger.debug(f"Routed result for task {result.task_id} via result queue")
                else:
                    self.logger.error(f"Cannot route result for task {result.task_id} - worker_pool not available")
                
            except asyncio.TimeoutError:
                # No tasks available, check for model timeout
                await self._check_model_timeout()
                continue
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
        
        try:
            # Ensure correct model is loaded
            if self.current_model_id != task.model_id:
                await self._switch_model(task.model_id)
            
            # Process based on task type
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
            
            self.logger.debug(f"Worker {self.worker_id} completed task {task.task_id} in {processing_time:.3f}s")
            
            return WorkerResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                success=True,
                data=result_data,
                processing_time=processing_time,
                metadata={"device": self.current_device, "model_id": task.model_id}
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

            # Load based on model type (pass target_device to loader)
            if model_type == "embedding":
                model_result = await self._load_worker_embedding_model(model_id, target_device)
            elif model_type in ["text2text", "text_generation"]:
                model_result = await self._load_worker_text_generation_model(model_id, target_device)
            else:
                raise ValueError(f"Unsupported model type: {model_type} for model_id: {model_id}")

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
        """Auto-select best available device (prefers GPU over CPU).

        Returns:
            Device string (e.g., 'cuda:0', 'cpu')
        """
        try:
            import torch
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                # Select first available GPU
                return "cuda:0"
            else:
                return "cpu"
        except ImportError:
            return "cpu"

    def _select_available_gpu(self) -> Optional[str]:
        """Select an available GPU device.

        Returns:
            GPU device string (e.g., 'cuda:0') or None if no GPU available
        """
        try:
            import torch
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                # For now, just return first GPU
                # Could be enhanced to check GPU memory usage and select least loaded
                return "cuda:0"
            else:
                return None
        except ImportError:
            return None
    
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
    
    async def _load_worker_embedding_model(self, model_id: str, target_device: str = None):
        """Load embedding model instance specifically for this worker.

        Args:
            model_id: ID of the embedding model to load
            target_device: Target device to load model on

        Returns:
            Result with model instance
        """
        try:
            from core.error_utils import Result

            # Use target_device (should always be provided in device-agnostic architecture)
            device = target_device if target_device else "cpu"

            # Get model configuration - try local_path first, fallback to name
            model_path = self.model_manager.config.get(f"models.{model_id}.local_path")
            model_name = self.model_manager.config.get(f"models.{model_id}.name")

            # Use local_path if available, otherwise use name (HuggingFace path)
            model_path_or_name = model_path if model_path else model_name

            if not model_path_or_name:
                return Result.error(
                    code="MODEL_PATH_NOT_CONFIGURED",
                    message=f"Neither local_path nor name configured for {model_id}"
                )

            self.logger.info(f"Loading SentenceTransformer model {model_path_or_name} on {device}")

            # Load SentenceTransformer directly on target device
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(model_path_or_name, device=device)

            # Get model dimension from the model's architecture
            try:
                # Get dimension directly from model without encoding
                dimension = model.get_sentence_embedding_dimension()
                self.logger.info(f"Successfully loaded embedding model: {model_id} (dimension: {dimension})")
            except Exception as e:
                # Fallback: try a simple encoding without tensor conversion
                try:
                    sample_embedding = model.encode(["test"], convert_to_numpy=True)
                    dimension = sample_embedding.shape[1] if len(sample_embedding.shape) > 1 else sample_embedding.shape[0]
                    self.logger.info(f"Successfully loaded embedding model: {model_id} (dimension: {dimension})")
                except Exception as e2:
                    self.logger.warning(f"Could not determine embedding dimension: {e}, {e2}")
                    dimension = None
            
            return Result.success(data={
                "model": model,
                "model_id": model_id,
                "dimension": dimension,
                "device": device,
                "worker_instance": True
            })
            
        except Exception as e:
            from core.error_utils import Result
            device = target_device if target_device else "cpu"
            self.logger.error(f"Failed to load embedding model {model_id} on {device}: {e}")
            return Result.error(
                code="EMBEDDING_MODEL_LOAD_ERROR",
                message=f"Failed to load embedding model {model_id}",
                details={"error": str(e), "device": device}
            )
    
    async def _load_worker_text_generation_model(self, model_id: str, target_device: str = None):
        """Load text generation model instance specifically for this worker.

        Args:
            model_id: ID of the text generation model to load
            target_device: Target device to load model on

        Returns:
            Result with model instance
        """
        try:
            from core.error_utils import Result

            # Use target_device (should always be provided in device-agnostic architecture)
            device = target_device if target_device else "cpu"

            # Get model configuration
            model_name = self.model_manager.config.get(f"models.{model_id}.name")
            if not model_name:
                return Result.error(
                    code="MODEL_NAME_NOT_CONFIGURED",
                    message=f"Model name not configured for {model_id}"
                )

            self.logger.info(f"Loading T5 model {model_name} on {device}")

            # Load T5 model directly on target device
            from transformers import T5ForConditionalGeneration, AutoTokenizer

            model = T5ForConditionalGeneration.from_pretrained(model_name).to(device)
            tokenizer = AutoTokenizer.from_pretrained(model_name)

            self.logger.info(f"Successfully loaded T5 model: {model_id} on {device}")

            return Result.success(data={
                "model": model,
                "tokenizer": tokenizer,
                "model_id": model_id,
                "device": device,
                "worker_instance": True
            })

        except Exception as e:
            from core.error_utils import Result
            device = target_device if target_device else "cpu"
            self.logger.error(f"Failed to load T5 model {model_id} on {device}: {e}")
            return Result.error(
                code="T5_MODEL_LOAD_ERROR",
                message=f"Failed to load T5 model {model_id}",
                details={"error": str(e), "device": device}
            )
    
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
            if isinstance(texts, str):
                embeddings = model.encode([texts], convert_to_numpy=True, show_progress_bar=False)
                # Make a copy to avoid shared memory issues, then convert to list
                import numpy as np
                result_embeddings = np.array(embeddings[0], copy=True).tolist()
            else:
                embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
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
            "device": self.current_device,  # Device of currently loaded model
            "state": self.state.value,
            "current_model_id": self.current_model_id,
            "is_running": self.is_running,
            "tasks_processed": self.tasks_processed,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_processing_time,
            "errors": self.errors,
            "model_switches": self.model_switches,
            "last_activity": self.last_activity,
            "queue_size": self.task_queue.qsize()
        }