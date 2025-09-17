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
    """Individual worker that can load different model types dynamically."""
    
    def __init__(self, worker_id: str, device: str, model_manager_service):
        """Initialize model worker.
        
        Args:
            worker_id: Unique identifier for this worker
            device: Target device (e.g., 'cuda:0', 'cpu')
            model_manager_service: Reference to parent model manager
        """
        self.worker_id = worker_id
        self.device = device
        self.model_manager = model_manager_service
        self.logger = logging.getLogger(f"{MODULE_ID}.worker.{worker_id}")
        
        # State management
        self.state = WorkerState.IDLE
        self.current_model_id = None
        self.current_model = None
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
        
        self.logger.info(f"Worker {worker_id} created on device {device}")
    
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
                    if hasattr(self.model_manager, '_global_job_queue') and self.model_manager._global_job_queue is not None:
                        task = await asyncio.wait_for(
                            self.model_manager._global_job_queue.get(), 
                            timeout=self.model_manager.config.get("worker_pool.queue_timeout", 30)
                        )
                        self.model_manager._global_job_queue.task_done()
                        self.logger.debug(f"Worker {self.worker_id} got task from global queue")
                    else:
                        # No tasks available, continue loop
                        continue
                
                # Process the task
                result = await self._process_task(task)
                
                # Always use result queue for simplicity and reliability
                await self.model_manager._worker_result_queue.put(result)
                self.logger.debug(f"Routed result for task {result.task_id} via result queue")
                
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
                metadata={"device": self.device, "model_id": task.model_id}
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
        
        Args:
            model_id: ID of model to load
        """
        try:
            # Clear CUDA cache and synchronize before loading
            if self.device.startswith("cuda"):
                try:
                    import torch
                    device_idx = int(self.device.split(':')[1]) if ':' in self.device else 0
                    torch.cuda.set_device(device_idx)
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize(device_idx)
                except (ImportError, RuntimeError) as e:
                    self.logger.warning(f"Worker {self.worker_id} CUDA setup warning: {e}")
            
            # Prevent CPU usage - refuse to load models on CPU
            if self.device == "cpu" and self.model_manager.config.get("worker_pool.require_gpu", True):
                raise RuntimeError(f"REFUSING to load {model_id} on CPU - GPU required. Fix GPU issues first.")
            
            # Load model instance directly on this worker's device
            # Each worker needs its own model instance, not shared models
            if model_id == "embedding":
                model_result = await self._load_worker_embedding_model(model_id)
            elif model_id == "t5_summarizer":
                model_result = await self._load_worker_text_generation_model(model_id)
            else:
                raise ValueError(f"Unknown model_id: {model_id}")
            
            if not model_result.success:
                raise RuntimeError(f"Failed to load model {model_id}: {model_result.error}")
            
            self.current_model = model_result.data
            self.current_model_id = model_id
            self.last_activity = time.time()
            
            self.logger.info(f"Worker {self.worker_id} loaded model {model_id}")
            
        except Exception as e:
            self.logger.error(f"Worker {self.worker_id} failed to load model {model_id}: {e}")
            self.state = WorkerState.ERROR
            raise
    
    async def _unload_model(self):
        """Unload current model from this worker."""
        if self.current_model_id:
            self.state = WorkerState.UNLOADING
            
            # Actually move model to CPU to free GPU memory
            if self.current_model and self.device.startswith("cuda"):
                try:
                    if hasattr(self.current_model, 'to'):
                        self.current_model.to('cpu')
                        self.logger.info(f"Worker {self.worker_id} moved model {self.current_model_id} to CPU")
                    
                    import torch
                    torch.cuda.empty_cache()
                    self.logger.debug(f"Worker {self.worker_id} cleared CUDA cache")
                except Exception as e:
                    self.logger.warning(f"Worker {self.worker_id} failed to clear GPU memory: {e}")
            
            # Release model reference
            if self.current_model_id in self.model_manager._loaded_models:
                await self.model_manager.release_model(self.current_model_id)
            
            self.current_model = None
            self.current_model_id = None
            self.is_preloaded = False
            self.state = WorkerState.IDLE
            
            self.logger.info(f"Worker {self.worker_id} unloaded model completely")
    
    async def _load_worker_embedding_model(self, model_id: str):
        """Load embedding model instance specifically for this worker.
        
        Args:
            model_id: ID of the embedding model to load
            
        Returns:
            Result with model instance
        """
        try:
            from core.error_utils import Result
            
            # Get model configuration
            model_path = self.model_manager.config.get(f"models.{model_id}.local_path")
            if not model_path:
                return Result.error(
                    code="MODEL_PATH_NOT_CONFIGURED",
                    message=f"Model path not configured for {model_id}"
                )
            
            self.logger.info(f"Loading SentenceTransformer model from local path: {model_path} on {self.device}")
            
            # Load SentenceTransformer directly on this worker's device
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer(model_path, device=self.device)
            
            # Get model dimension for validation
            try:
                sample_embedding = model.encode(["test"], convert_to_tensor=True)
                dimension = sample_embedding.shape[1]
                self.logger.info(f"Successfully loaded embedding model: {model_id} (dimension: {dimension})")
            except Exception as e:
                self.logger.warning(f"Could not determine embedding dimension: {e}")
                dimension = None
            
            return Result.success(data={
                "model": model,
                "model_id": model_id,
                "dimension": dimension,
                "device": self.device,
                "worker_instance": True
            })
            
        except Exception as e:
            from core.error_utils import Result
            self.logger.error(f"Failed to load embedding model {model_id} on {self.device}: {e}")
            return Result.error(
                code="EMBEDDING_MODEL_LOAD_ERROR",
                message=f"Failed to load embedding model {model_id}",
                details={"error": str(e), "device": self.device}
            )
    
    async def _load_worker_text_generation_model(self, model_id: str):
        """Load text generation model instance specifically for this worker.
        
        Args:
            model_id: ID of the text generation model to load
            
        Returns:
            Result with model instance
        """
        try:
            from core.error_utils import Result
            
            # Get model configuration
            model_name = self.model_manager.config.get(f"models.{model_id}.name")
            if not model_name:
                return Result.error(
                    code="MODEL_NAME_NOT_CONFIGURED",
                    message=f"Model name not configured for {model_id}"
                )
            
            self.logger.info(f"Loading T5 model {model_name} on {self.device}")
            
            # Load T5 model directly on this worker's device
            from transformers import T5ForConditionalGeneration, AutoTokenizer
            
            model = T5ForConditionalGeneration.from_pretrained(model_name).to(self.device)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            self.logger.info(f"Successfully loaded T5 model: {model_id} on {self.device}")
            
            return Result.success(data={
                "model": model,
                "tokenizer": tokenizer,
                "model_id": model_id,
                "device": self.device,
                "worker_instance": True
            })
            
        except Exception as e:
            from core.error_utils import Result
            self.logger.error(f"Failed to load T5 model {model_id} on {self.device}: {e}")
            return Result.error(
                code="T5_MODEL_LOAD_ERROR",
                message=f"Failed to load T5 model {model_id}",
                details={"error": str(e), "device": self.device}
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
            if self.device.startswith("cuda"):
                import torch
                device_idx = int(self.device.split(':')[1]) if ':' in self.device else 0
                torch.cuda.set_device(device_idx)
            
            if isinstance(texts, str):
                embeddings = model.encode([texts])
                result_embeddings = embeddings[0].tolist()
            else:
                embeddings = model.encode(texts)
                result_embeddings = [emb.tolist() for emb in embeddings]
            
            # Synchronize CUDA operations after processing
            if self.device.startswith("cuda"):
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
            "device": self.device,
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