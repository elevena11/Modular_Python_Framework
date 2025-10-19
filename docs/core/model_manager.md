# Model Manager Documentation

## Overview

The Model Manager (`core.model_manager`) provides a **unified task API** for AI model operations with automatic lifecycle management. All model configuration is passed with each request, making it simple and self-contained.

**Key Features**:
- **Unified task() API** - single entry point for all model operations
- **Self-contained requests** - all config in each call, no registration needed
- **Deferred loading** - models auto-load on first use, auto-reload after release
- **Pre-loading support** - optional pre-load with custom keep-alive timeouts
- **Auto-release** - models automatically freed after inactivity
- **VRAM management** - proper GPU memory cleanup with transparent reload
- **Multi-GPU support** - worker pool distributes load across devices

**Supported Models**: All models from **Hugging Face Hub** (downloaded and cached automatically in `data/models/`)

---

## Quick Start

### Basic Usage

```python
# Get model_manager service
model_manager = app_context.get_service("core.model_manager.service")

# Generate embeddings (auto-creates workers on first use)
result = await model_manager.task(
    task_data=["hello world", "test document"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)

if result.success:
    embeddings = result.data.get("embeddings", [])
    print(f"Generated {len(embeddings)} embeddings")
```

That's it! No registration, no setup - just call `task()` with your config.

---

## The Unified task() API

### Single Entry Point

The `task()` method is the **only** API you need for all model operations:

```python
await model_manager.task(
    task_data=<your_data>,        # Data to process (or None to pre-load)
    task_type="embedding",         # "embedding" or "text_generation"
    model_name="model-name",       # HuggingFace model name
    num_workers=1,                 # Number of workers to create
    device="gpu",                  # "gpu" or "cpu"
    keep_alive=5,                  # Minutes before auto-release (optional)
    **kwargs                       # Task-specific params (e.g., max_length)
)
```

### Self-Contained Requests

**All configuration is in each request** - no separate registration step:

```python
# First request - creates workers, loads model, processes
result = await model_manager.task(
    task_data=["hello"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)

# Second request - reuses existing workers
result = await model_manager.task(
    task_data=["world"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)

# Different config? No problem - each request is independent
result = await model_manager.task(
    task_data=["test"],
    task_type="embedding",
    model_name="sentence-transformers/all-MiniLM-L6-v2",  # Different model
    num_workers=1,  # Different worker count
    device="cpu"    # Different device
)
```

---

## Pre-Loading Models

### Why Pre-Load?

Pre-loading ensures models are ready before the first request:
- **Eliminates first-request latency** (no model download/load delay)
- **Warms up VRAM** for consistent performance
- **Custom keep-alive** per model

### How to Pre-Load

Set `task_data=None` to pre-load without processing:

```python
# Pre-load embedding model with 30 minute keep-alive
await model_manager.task(
    task_data=None,  # Pre-load only, no processing
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu",
    keep_alive=30  # Stay loaded for 30 minutes of inactivity
)

# Later requests use the pre-loaded model immediately
result = await model_manager.task(
    task_data=["instant processing!"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)
```

### Pre-Load at Startup

Pre-load models during module initialization:

```python
# modules/standard/my_module/services.py
async def initialize(self, settings) -> Result:
    """Phase 2: Pre-load models for instant first use."""
    model_manager = self.app_context.get_service("core.model_manager.service")

    # Pre-load embedding model
    await model_manager.task(
        task_data=None,
        task_type="embedding",
        model_name=settings.embedding_model_name,
        num_workers=2,
        device="gpu",
        keep_alive=30
    )

    # Pre-load text generation model
    await model_manager.task(
        task_data=None,
        task_type="text_generation",
        model_name=settings.t5_model_name,
        num_workers=1,
        device="gpu",
        keep_alive=10
    )

    logger.info("Models pre-loaded and ready")
    return Result.success(data={"initialized": True})
```

### Pre-Load Response

Pre-load returns confirmation (no embeddings/text):

```python
{
    "preloaded": True,
    "model_name": "mixedbread-ai/mxbai-embed-large-v1",
    "workers": 2,
    "device": "gpu",
    "keep_alive_minutes": 30
}
```

---

## Automatic Lifecycle Management

### Auto-Loading (Deferred/Lazy)

**Models load on first use** - no explicit load step needed:

```python
# Model not loaded yet
result = await model_manager.task(
    task_data=["first request"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)
# Workers created, model loaded, task processed

# Model already loaded
result = await model_manager.task(
    task_data=["second request"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)
# Reuses existing workers, instant processing
```

### Auto-Release (Keep-Alive)

**Models automatically release after inactivity**:

```python
await model_manager.task(
    task_data=["process this"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu",
    keep_alive=5  # Auto-release after 5 minutes of inactivity
)

# After 5 minutes of no requests...
# Model is automatically released, VRAM freed

# Next request auto-recreates workers
result = await model_manager.task(
    task_data=["transparent reload!"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)
# Workers recreated, model reloaded, task processed
```

**Default keep_alive**: 5 minutes (configurable in model_manager settings)

### Manual Release

**Free VRAM immediately** without waiting for timeout:

```python
# Release model right now
await model_manager.release_model("mixedbread-ai/mxbai-embed-large-v1")

# VRAM is freed immediately
# Registry entry removed (no stale config)

# Next request creates fresh workers with new config
await model_manager.task(
    task_data=["new request"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=1,  # Can use different config
    device="cpu"    # Different device
)
```

---

## Model Types

### 1. Embedding Models

Convert text to dense vector representations:

```python
result = await model_manager.task(
    task_data=["hello world", "test document"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)

if result.success:
    embeddings = result.data.get("embeddings", [])
    # embeddings = [[0.1, 0.2, ...], [0.3, 0.4, ...]]
```

**Popular Models**:
- `mixedbread-ai/mxbai-embed-large-v1` (1024 dim, high quality)
- `sentence-transformers/all-MiniLM-L6-v2` (384 dim, fast)
- `intfloat/e5-large-v2` (1024 dim, multilingual)

### 2. Text Generation Models

Generate text from input text:

```python
result = await model_manager.task(
    task_data="Summarize this article: ...",
    task_type="text_generation",
    model_name="google-t5/t5-large",
    num_workers=1,
    device="gpu",
    max_length=128  # Task-specific parameter
)

if result.success:
    generated_text = result.data.get("generated_text", "")
```

**Popular Models**:
- `google-t5/t5-large` (summarization, Q&A)
- `google-t5/t5-base` (smaller, faster)
- `facebook/bart-large-cnn` (summarization)

---

## Device Selection

### Device Options

| Device | Behavior |
|--------|----------|
| `"gpu"` (default) | Auto-select best available GPU |
| `"cpu"` | Force CPU execution |
| `"cuda:0"`, `"cuda:1"` | Specific GPU device (not implemented yet) |

### Examples

```python
# Use GPU (auto-select best available)
await model_manager.task(
    task_data=["large model needs GPU"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    device="gpu"
)

# Force CPU (save GPU memory)
await model_manager.task(
    task_data=["small model on CPU"],
    task_type="embedding",
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cpu"
)
```

### When to Use Each Device

**Use device="gpu"**:
- Large embedding models (>512 dimensions)
- Text generation models
- Performance-critical operations
- High-throughput workloads

**Use device="cpu"**:
- Small embedding models (<512 dimensions)
- Development/testing
- Save GPU memory for larger models
- Models used infrequently

---

## Worker Configuration

### Number of Workers

`num_workers` controls parallel processing capacity:

```python
# Single worker (sequential processing)
await model_manager.task(
    task_data=texts,
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=1
)

# Multiple workers (parallel processing)
await model_manager.task(
    task_data=texts,
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2  # 2 workers can process in parallel
)
```

**Guidelines**:
- **1 worker**: Most use cases, simple sequential processing
- **2+ workers**: High-throughput scenarios, parallel requests
- **GPU**: Workers capped by available GPUs (can't exceed GPU count)
- **CPU**: Can create many workers (up to framework limit)

---

## High-Throughput Batch Processing

### Understanding the Queue System

When you call `model_manager.task()`, the request is submitted to a **per-model queue** that workers continuously pull from:

```
┌─────────────────────────────────────────────────┐
│  Your Code                                      │
│  ↓                                              │
│  task() calls → Model Queue → Workers (GPUs)   │
│                    ↓              ↓             │
│                  [Task1]      Worker 1 (GPU 0)  │
│                  [Task2]      Worker 2 (GPU 1)  │
│                  [Task3]                        │
│                  [...]                          │
└─────────────────────────────────────────────────┘
```

**Critical Insight**: Workers only process when the queue has work. Sequential `await` creates **gaps** where GPUs sit idle.

### Sequential vs Concurrent Processing

#### ❌ INEFFICIENT: Sequential (~50% GPU Utilization)

```python
# BAD: Creates gaps between tasks
for doc in documents:
    result = await model_manager.task(
        task_data=[doc],
        task_type="embedding",
        model_name="mixedbread-ai/mxbai-embed-large-v1",
        num_workers=2
    )
    # ↑ GPUs idle while waiting here
    await store_embedding(result)
```

**GPU utilization**: ~50% (workers frequently idle waiting for next task)

#### ✅ EFFICIENT: Concurrent (90%+ GPU Utilization)

```python
# GOOD: Floods queue, keeps GPUs saturated
import asyncio

batch_size = 15
batches = [documents[i:i+batch_size] for i in range(0, len(documents), batch_size)]

# Submit ALL batches at once
tasks = [
    model_manager.task(
        task_data=batch,
        task_type="embedding",
        model_name="mixedbread-ai/mxbai-embed-large-v1",
        num_workers=2
    )
    for batch in batches
]

# Workers pull continuously from full queue
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**GPU utilization**: 90%+ (workers continuously busy)

### Performance Impact

The difference in GPU utilization is dramatic:

```
Sequential: [██----][██----][██----]  50% utilized (gaps between tasks)
Concurrent: [██████][██████][██████]  90%+ utilized (continuous work)
```

**Real impact**: ~3-4x speedup for large datasets by eliminating idle time.

### Batch Size Guidelines

| Model Type | Recommended Batch Size | Rationale |
|------------|----------------------|-----------|
| **Small** (< 512 dim) | 20-30 docs | Low VRAM, fast inference |
| **Large** (> 1024 dim) | 10-15 docs | High VRAM, slower inference |
| **Default** | 15 docs | Good balance for most models |

### Common Mistakes to Avoid

```python
# ❌ DON'T: Sequential await (creates gaps)
for batch in batches:
    result = await model_manager.task(...)
    process(result)

# ❌ DON'T: Batch size = 1 (too much overhead)
batch_size = 1

# ❌ DON'T: Batch size = all docs (no concurrency)
batch_size = len(documents)

# ✅ DO: Concurrent batches with asyncio.gather()
results = await asyncio.gather(*[
    model_manager.task(task_data=batch, ...)
    for batch in batches
])
```

### Production Example

```python
import asyncio
from typing import List, Dict, Any
from core.error_utils import Result

async def embed_documents_efficiently(
    documents: List[Dict[str, Any]],
    model_manager,
    batch_size: int = 15
) -> Result:
    """Process documents with optimal GPU utilization."""

    # Create batches
    batches = [
        documents[i:i+batch_size]
        for i in range(0, len(documents), batch_size)
    ]

    # Submit all batches concurrently (floods queue)
    tasks = [
        model_manager.task(
            task_data=[doc["text"] for doc in batch],
            task_type="embedding",
            model_name="mixedbread-ai/mxbai-embed-large-v1",
            num_workers=2,
            device="gpu"
        )
        for batch in batches
    ]

    # Process concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect embeddings
    all_embeddings = []
    for batch_idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Batch {batch_idx} failed: {result}")
            continue

        if result.success:
            embeddings = result.data.get("embeddings", [])
            batch_docs = batches[batch_idx]

            for doc, emb in zip(batch_docs, embeddings):
                all_embeddings.append({
                    "document_id": doc["id"],
                    "embedding": emb
                })

    return Result.success(data={"embeddings": all_embeddings})
```

**Key Takeaway**: Use `asyncio.gather()` to flood the queue and achieve 90%+ GPU utilization instead of ~50% with sequential processing.

---

## Complete Example Module

Here's a complete module using the unified task() API:

### Module Settings

```python
# modules/standard/document_processor/settings.py
from pydantic import BaseModel, Field

class DocumentProcessorSettings(BaseModel):
    enabled: bool = Field(default=True)

    # Model names (no complex ModelRequirement schema needed)
    embedding_model_name: str = Field(
        default="mixedbread-ai/mxbai-embed-large-v1"
    )
    embedding_workers: int = Field(default=2)
    embedding_device: str = Field(default="gpu")
```

### Service Implementation

```python
# modules/standard/document_processor/services.py
from core.logging import get_framework_logger
from core.error_utils import Result

MODULE_ID = "standard.document_processor"
logger = get_framework_logger(MODULE_ID)

class DocumentProcessorService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.settings = None

    async def initialize(self, settings) -> Result:
        """Phase 2: Pre-load models for instant use."""
        self.settings = settings

        model_manager = self.app_context.get_service("core.model_manager.service")
        if not model_manager:
            return Result.error(
                code="MODEL_MANAGER_NOT_AVAILABLE",
                message="model_manager service not available"
            )

        # Pre-load embedding model
        await model_manager.task(
            task_data=None,  # Pre-load only
            task_type="embedding",
            model_name=settings.embedding_model_name,
            num_workers=settings.embedding_workers,
            device=settings.embedding_device,
            keep_alive=30  # 30 minutes before auto-release
        )

        logger.info("Document processor initialized with pre-loaded models")
        return Result.success(data={"initialized": True})

    async def embed_documents(self, documents: list[str]) -> Result:
        """Generate embeddings for documents."""
        try:
            model_manager = self.app_context.get_service("core.model_manager.service")

            # Use unified task() API
            result = await model_manager.task(
                task_data=documents,
                task_type="embedding",
                model_name=self.settings.embedding_model_name,
                num_workers=self.settings.embedding_workers,
                device=self.settings.embedding_device
            )

            if result.success:
                embeddings = result.data.get("embeddings", [])
                logger.info(f"Generated {len(embeddings)} document embeddings")
                return Result.success(data={"embeddings": embeddings})
            else:
                return result

        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return Result.error(
                code="EMBEDDING_ERROR",
                message="Failed to generate embeddings",
                details={"error": str(e)}
            )

    async def cleanup_resources(self):
        """Graceful shutdown - manually release models."""
        try:
            model_manager = self.app_context.get_service("core.model_manager.service")
            if model_manager and self.settings:
                # Release embedding model (frees VRAM immediately)
                await model_manager.release_model(
                    self.settings.embedding_model_name
                )
                logger.info("Models released")
        except Exception as e:
            logger.error(f"Error releasing models: {e}")
```

---

## API Reference

### task()

**Unified entry point for all model operations.**

```python
await model_manager.task(
    task_data: Optional[Any],
    task_type: str,
    model_name: str,
    num_workers: int = 1,
    device: str = "gpu",
    keep_alive: Optional[int] = None,
    **kwargs
) -> Result
```

**Parameters**:
- `task_data`: Data to process (texts for embeddings, text for generation, etc.)
  - Set to `None` for pre-loading only (loads model without processing)
- `task_type`: Type of task
  - `"embedding"` - Generate embeddings
  - `"text_generation"` - Generate text
- `model_name`: HuggingFace model name (e.g., `"mixedbread-ai/mxbai-embed-large-v1"`)
- `num_workers`: Number of workers to create (default: 1)
  - For `device="gpu"`: Suggestion, capped by available GPUs
  - For `device="cpu"`: Exact count created
- `device`: Device specification (default: `"gpu"`)
  - `"gpu"` - Auto-select best GPU
  - `"cpu"` - Force CPU execution
- `keep_alive`: Minutes of inactivity before auto-release (default: from settings)
  - Auto-release frees VRAM after inactivity
  - Next use transparently recreates workers
- `**kwargs`: Additional task-specific parameters
  - Embeddings: (none currently)
  - Text generation: `max_length`, etc.

**Returns**: `Result` with task output

**Examples**:

```python
# Regular embedding task
result = await model_manager.task(
    task_data=["hello", "world"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu"
)

# Pre-load model with 30 minute keep-alive
result = await model_manager.task(
    task_data=None,  # Pre-load only
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=2,
    device="gpu",
    keep_alive=30
)

# Text generation with custom parameters
result = await model_manager.task(
    task_data="Translate this text",
    task_type="text_generation",
    model_name="google-t5/t5-large",
    num_workers=1,
    device="gpu",
    keep_alive=10,
    max_length=128
)
```

---

### release_model()

**Manually release a model to free VRAM immediately.**

```python
await model_manager.release_model(model_name: str) -> Result
```

**Parameters**:
- `model_name`: Model identifier to release

**Behavior**:
- Stops all workers for this model
- Unloads model and frees VRAM immediately
- Removes registry entry completely (no stale config)
- Next request creates fresh workers with new config

**Example**:

```python
# Free VRAM immediately
await model_manager.release_model("mixedbread-ai/mxbai-embed-large-v1")

# Next request auto-recreates with new config
await model_manager.task(
    task_data=["new request"],
    task_type="embedding",
    model_name="mixedbread-ai/mxbai-embed-large-v1",
    num_workers=1,  # Can use different worker count
    device="cpu"    # Can use different device
)
```

---

### drop_model_queue()

**Forcefully drop all pending tasks for a model (emergency operation).**

Use this when a large batch was submitted by mistake and needs immediate cancellation. All queued tasks are discarded and callers are notified of the cancellation.

```python
await model_manager.drop_model_queue(
    model_name: str,
    reason: str = "Manual drop"
) -> Result
```

**Parameters**:
- `model_name`: Model identifier whose queue to drop
- `reason`: Reason for dropping (for logging/audit trail)

**Returns**: Result with:
- `dropped`: Number of tasks dropped from queue
- `futures_cancelled`: Number of futures cancelled (callers notified)
- `model_name`: Model affected
- `reason`: Reason provided

**Behavior**:
- Removes all pending tasks from the model's queue
- Cancels futures waiting for results with error
- Callers receive `RuntimeError` with cancellation reason
- Workers continue running and ready for new tasks
- Does NOT release the model

**Example**:

```python
# Large batch submitted by mistake
for i in range(1000):
    await model_manager.task(
        task_data=["text"],
        task_type="embedding",
        model_name="model-name"
    )
# Oops! Need to cancel all those tasks immediately

# Emergency drop
result = await model_manager.drop_model_queue(
    model_name="model-name",
    reason="User cancelled large batch"
)

if result.success:
    print(f"Dropped {result.data['dropped']} pending tasks")
    print(f"Cancelled {result.data['futures_cancelled']} futures")

# Model still loaded and ready
await model_manager.task(
    task_data=["normal request"],
    task_type="embedding",
    model_name="model-name"
)
```

**Common Use Cases**:
- User clicks "Cancel All" in UI
- Batch job submitted with wrong parameters
- Emergency stop of runaway task queue
- Testing queue cancellation behavior

**Comparison with release_model()**:

| Operation | Drops Queue | Releases Model | Use Case |
|-----------|-------------|----------------|----------|
| `drop_model_queue()` | Yes | No | Cancel pending tasks, keep model loaded |
| `release_model()` | Yes (pending done first) | Yes | Free VRAM and stop everything |

---

## Configuration

### Model Manager Settings

Framework-level settings in `modules/core/model_manager/settings.py`:

```python
class ModelManagerSettings(BaseModel):
    # Enable/disable entire model_manager
    enabled: bool = Field(default=True)

    # Worker pool configuration
    worker_pool: WorkerPoolConfig = Field(
        default_factory=lambda: WorkerPoolConfig(
            enabled=True,
            num_workers=2,
            devices=["auto"],  # Auto-detect GPUs
            queue_timeout=30,
            model_idle_timeout=300,  # 5 minutes default keep_alive
            load_balancing="round_robin"
        )
    )

    # Embedding cache configuration
    embedding_cache: EmbeddingCacheConfig = Field(
        default_factory=lambda: EmbeddingCacheConfig(
            enabled=True,
            max_cache_size=10000,
            ttl_seconds=3600
        )
    )
```

### Module Settings

Modules define their own model preferences in settings:

```python
# modules/standard/my_module/settings.py
class MyModuleSettings(BaseModel):
    embedding_model_name: str = Field(
        default="mixedbread-ai/mxbai-embed-large-v1"
    )
    embedding_workers: int = Field(default=2)
    embedding_device: str = Field(default="gpu")
    embedding_keep_alive: int = Field(default=30)  # minutes
```

---

## Best Practices

1. **Use task() for Everything**: Single API for all operations - simple and consistent
2. **Pre-Load at Startup**: Use `task_data=None` during initialization for instant first use
3. **Set Reasonable keep_alive**: Balance memory usage vs reload overhead
4. **Release on Shutdown**: Call `release_model()` during `cleanup_resources()` for clean shutdown
5. **Handle Result Pattern**: Always check `result.success` before using data
6. **Extract Data Safely**: Use `result.data.get("embeddings", [])` to avoid KeyError

---

## Troubleshooting

### Model Not Loading

**Symptoms**: `task()` fails with model loading error

**Solutions**:
- Verify model name is correct (check Hugging Face Hub)
- Check device availability (`nvidia-smi` for GPU)
- Ensure sufficient GPU/CPU memory
- Check logs for model download progress
- Try `device="cpu"` for testing

### Out of Memory Errors

**Symptoms**: GPU OOM during model loading or inference

**Solutions**:
- Use smaller model (e.g., `all-MiniLM-L6-v2` instead of `mxbai-embed-large-v1`)
- Set `device="cpu"` for smaller models
- Release unused models with `release_model()`
- Lower `keep_alive` to free memory sooner

### KeyError When Accessing Results

**Problem**:
```python
embeddings = result.data  # Wrong - result.data is a dict
dimension = len(embeddings[0])  # KeyError: '0'
```

**Solution**:
```python
embeddings = result.data.get("embeddings", [])  # Correct
dimension = len(embeddings[0]) if embeddings else 0
```

---

## Hugging Face Authentication

**Public Models**: Most models require no authentication.

**Private/Gated Models**: Some models require authentication (e.g., Llama 2, Mistral).

**Setup**:
1. Get your token from https://huggingface.co/settings/tokens
2. Set environment variable in `.env` file:
   ```bash
   HF_TOKEN=hf_your_token_here
   ```
3. Or use CLI login (one-time setup):
   ```bash
   huggingface-cli login
   ```

The framework automatically uses the token when loading models.

---

## Summary

The model_manager provides a **unified task() API** where:

- **One method does everything**: `task()` is the single entry point
- **Self-contained requests**: All config in each call, no registration step
- **Automatic lifecycle**: Models load on first use, auto-release after inactivity
- **Pre-loading support**: Use `task_data=None` for instant first use
- **Transparent reload**: Models auto-recreate after release with fresh config
- **Clean architecture**: Simple, predictable, LLM-friendly

This design eliminates complexity while providing powerful model management capabilities.
