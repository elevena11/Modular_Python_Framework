# Model Manager Documentation

## Overview

The Model Manager (`core.model_manager`) is a core framework service that provides AI model lifecycle management with dynamic model registration, GPU resource allocation, and model sharing capabilities. It acts as **infrastructure** that modules use to load and manage AI models through a **registry pattern**.

**Architecture Philosophy**: The model_manager defines **capabilities** (what types of models it can handle), while individual modules define **requirements** (which specific models they need). Models are registered at runtime during module initialization, not pre-configured.

**Model Source**: Currently supports **Hugging Face Hub** models (via `transformers` and `sentence-transformers` libraries). Models are downloaded and cached automatically in `data/models/`.

**Key Features**:
- Dynamic model registration from modules
- Reference counting for model lifecycle management
- Multi-GPU worker pool with load balancing
- Embedding result caching
- Automatic device detection (GPU/CPU)
- Model sharing between modules

---

## Architecture

### Dynamic Registry Pattern

Modules register their AI model requirements at runtime during Phase 2 initialization:

```
Module Phase 2 Initialization
  |
  +---> Registers ModelRequirement with model_manager
         |
         +---> model_manager: Tracks registration in registry
                |
                +---> On first use: Load model to GPU
                      |
                      +---> Subsequent uses: Reuse loaded model
                            |
                            +---> Module shutdown: Release reference
                                  |
                                  +---> No more references: Unload model
```

### Benefits

1. **Modularity**: Add modules with AI needs without modifying core
2. **Flexibility**: Each module specifies exactly what it needs
3. **Separation of Concerns**: model_manager handles "how", modules specify "what"
4. **Resource Optimization**: Shared models, GPU management, reference counting
5. **Type Safety**: Pydantic schema validation for all model configurations

---

## Model Types

The model_manager supports multiple AI model categories:

### 1. Embedding Models (`embedding`)

**Purpose**: Convert text to dense vector representations for semantic search, clustering, and similarity.

**Capabilities**:
- Text-to-vector transformation
- Batch processing
- Result caching
- Multi-GPU support

**Required Configuration**:
```python
from modules.core.model_manager.schemas import ModelRequirement

embedding_model = ModelRequirement(
    model_type="embedding",
    name="sentence-transformers/all-MiniLM-L6-v2",  # HuggingFace model name
    dimension=384,  # Output vector dimension
    device="auto",  # "auto", "cuda:0", "cuda:1", "cpu"
    batch_size=32,
    cache_embeddings=True
)
```

**Popular Models**:
- `sentence-transformers/all-MiniLM-L6-v2` (dimension: 384, fast)
- `mixedbread-ai/mxbai-embed-large-v1` (dimension: 1024, high quality)
- `intfloat/e5-large-v2` (dimension: 1024, multilingual)

### 2. Text-to-Text Models (`text2text`)

**Purpose**: Transform text to text (summarization, translation, paraphrasing).

**Required Configuration**:
```python
t5_model = ModelRequirement(
    model_type="text2text",
    name="google/flan-t5-large",
    max_input_length=512,  # Maximum input tokens
    max_output_length=128,  # Maximum output tokens
    device="auto"
)
```

**Popular Models**:
- `google/flan-t5-large` (summarization, Q&A)
- `facebook/bart-large-cnn` (summarization)
- `t5-base` (general text-to-text)

### 3. Text Generation Models (`text_generation`)

**Purpose**: Autoregressive text generation (completion, chat, creative writing).

**Required Configuration**:
```python
generation_model = ModelRequirement(
    model_type="text_generation",
    name="gpt2-large",
    temperature=0.7,
    top_k=50,
    top_p=0.9,
    streaming=False
)
```

### 4. Classification Models (`classification`)

**Purpose**: Text classification (sentiment, topic, intent detection).

**Required Configuration**:
```python
classifier = ModelRequirement(
    model_type="classification",
    name="distilbert-base-uncased-finetuned-sst-2-english",
    num_labels=2,  # Number of classes
    threshold=0.5
)
```

---

## Model Preloading Strategy

Modules control when and how their models are loaded through the `preload_workers` parameter in `ModelRequirement`.

### Preload Options

| preload_workers | Behavior | Use Case |
|-----------------|----------|----------|
| `0` (default) | Download/verify at startup, lazy load on first use | Most modules - efficient default |
| `1` | Download + preload to 1 worker | Performance-critical modules |
| `N` (2+) | Download + preload to N workers | High-throughput modules |

### How It Works

**preload_workers=0** (Default - Download Only):
```
Startup:    Download model → Verify → Unload (no memory usage)
First Use:  Load to worker → Process → Keep loaded
```

**preload_workers=1** (Preload Single Worker):
```
Startup:    Download model → Load to worker_0 → Keep loaded
First Use:  Use already-loaded model (instant)
```

**preload_workers=2+** (Preload Multiple Workers):
```
Startup:    Download model → Load to N workers → Keep loaded
First Use:  Use already-loaded model on available worker
```

### Configuration Example

```python
from modules.core.model_manager.schemas import ModelRequirement

# Default: Download only, lazy load (most efficient)
embedding_model = ModelRequirement(
    model_type="embedding",
    name="sentence-transformers/all-MiniLM-L6-v2",
    dimension=384,
    preload_workers=0  # Download at startup, load on first use
)

# Preload to 1 worker (performance-critical)
embedding_model = ModelRequirement(
    model_type="embedding",
    name="sentence-transformers/all-MiniLM-L6-v2",
    dimension=384,
    preload_workers=1  # Preload to 1 worker at startup
)

# Preload to multiple workers (high-throughput)
embedding_model = ModelRequirement(
    model_type="embedding",
    name="sentence-transformers/all-MiniLM-L6-v2",
    dimension=384,
    preload_workers=2  # Preload to 2 workers at startup
)
```

### Safety Features

- **Automatic Capping**: Requested workers capped at available workers (no 100+ CPU workers)
- **Graceful Degradation**: If preload fails, model loads on-demand
- **Fail-Fast**: Download issues detected at startup, not runtime
- **Memory Efficient**: Default (0) uses minimal memory until first use

### Performance Considerations

**When to use preload_workers=0** (default):
- Development environments
- Modules with infrequent model usage
- Memory-constrained systems
- Multiple models needed sporadically

**When to use preload_workers=1**:
- Production environments
- Modules with frequent model usage
- First-request performance is critical
- Single-worker deployments

**When to use preload_workers=2+**:
- High-throughput production systems
- Concurrent request handling
- Multi-GPU systems
- Mission-critical low-latency services

---

## Device Selection Strategy

Modules control device selection through the `device` parameter in `ModelRequirement`. This allows optimization of resource allocation based on model size and performance requirements.

### Device Options

| Device | Behavior | Use Case |
|--------|----------|----------|
| `"auto"` (default) | Auto-select best available GPU, fallback to CPU | Most models - let framework decide |
| `"cpu"` | Force CPU execution | Small models to save GPU memory |
| `"cuda"` | Use any available CUDA GPU | Model needs GPU but any GPU works |
| `"cuda:0"`, `"cuda:1"` | Use specific GPU device | Dedicate specific GPU for workload |

### How Device Selection Works

```
Module registers model with device preference
  |
  +---> Worker pool selects matching workers
         |
         +---> Model loaded on workers matching device preference
                |
                +---> Load balancing routes tasks to appropriate workers
```

**Key Principles**:
1. **Module-Controlled**: Each module specifies optimal device for its model size/needs
2. **Worker Matching**: Worker pool routes models to workers on matching devices
3. **Mixed Pools**: Framework supports mixed CPU + GPU worker pools
4. **Graceful Fallback**: If no matching workers, uses available workers

### Configuration Examples

```python
from modules.core.model_manager.schemas import ModelRequirement

# Small model on CPU (memory-efficient)
small_model = ModelRequirement(
    model_type="embedding",
    name="sentence-transformers/all-MiniLM-L6-v2",
    dimension=384,
    device="cpu",  # Small model - efficient on CPU, saves GPU memory
    batch_size=16,
    preload_workers=0
)

# Large model on GPU (performance-critical)
large_model = ModelRequirement(
    model_type="embedding",
    name="mixedbread-ai/mxbai-embed-large-v1",
    dimension=1024,
    device="auto",  # Auto-select best GPU
    batch_size=32,
    preload_workers=2
)

# Model pinned to specific GPU
pinned_model = ModelRequirement(
    model_type="text_generation",
    name="google/flan-t5-large",
    device="cuda:1",  # Dedicate GPU 1 for this workload
    max_input_length=512,
    max_output_length=128,
    preload_workers=1
)
```

### Worker Pool Configuration

Configure mixed CPU/GPU worker pool in model_manager settings:

```python
# modules/core/model_manager/settings.py
worker_pool: WorkerPoolConfig = Field(
    default_factory=lambda: WorkerPoolConfig(
        enabled=True,
        num_workers=3,
        devices=["auto", "cpu"],  # Auto-detect GPUs + 1 CPU worker
        # Or explicit configuration:
        # devices=["cuda:0", "cuda:1", "cpu"]  # 2 GPU workers + 1 CPU worker
    )
)
```

**Default Configuration**:
- `devices: ["auto", "cpu"]` - Auto-detect all available GPUs + 1 CPU worker
- `num_workers: 3` - 3 workers total
- Provides optimal mixed workload support out of the box

### Performance Guidelines

**Use device="cpu" for**:
- Small embedding models (<512 dimensions)
- Models used infrequently
- Development/testing workloads
- Saving GPU memory for larger models

**Use device="auto" or device="cuda" for**:
- Large embedding models (>512 dimensions)
- Text generation models
- Performance-critical operations
- High-throughput workloads

**Use device="cuda:N" for**:
- Dedicated GPU allocation per model type
- Load balancing across specific GPUs
- Multi-GPU systems with model affinity
- Avoiding GPU contention

### Real-World Example

```python
# modules/standard/document_processor/settings.py
class DocumentProcessorSettings(BaseModel):
    # Small model for keyword extraction - use CPU
    keyword_model: ModelRequirement = Field(
        default_factory=lambda: ModelRequirement(
            model_type="embedding",
            name="sentence-transformers/all-MiniLM-L6-v2",
            dimension=384,
            device="cpu",  # Efficient on CPU
            preload_workers=0
        )
    )

    # Large model for semantic search - use GPU
    semantic_model: ModelRequirement = Field(
        default_factory=lambda: ModelRequirement(
            model_type="embedding",
            name="mixedbread-ai/mxbai-embed-large-v1",
            dimension=1024,
            device="auto",  # Needs GPU performance
            preload_workers=2
        )
    )
```

**Benefits**:
- Small keyword model on CPU doesn't waste GPU memory
- Large semantic model gets GPU resources for performance
- Both models available simultaneously
- Optimal resource utilization

---

## Usage Pattern

### Step 1: Define Model Requirements in Module Settings

```python
# modules/standard/my_module/settings.py
from pydantic import BaseModel, Field
from modules.core.model_manager.schemas import ModelRequirement

class MyModuleSettings(BaseModel):
    enabled: bool = Field(default=True)

    # Define model requirements
    embedding_model: ModelRequirement = Field(
        default_factory=lambda: ModelRequirement(
            model_type="embedding",
            name="sentence-transformers/all-MiniLM-L6-v2",
            dimension=384,
            device="auto",
            batch_size=32,
            cache_embeddings=True
        )
    )
```

### Step 2: Register Model During Phase 2 Initialization

```python
# modules/standard/my_module/services.py
from core.logging import get_framework_logger

MODULE_ID = "standard.my_module"
logger = get_framework_logger(MODULE_ID)

class MyModuleService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.model_id = None
        self.initialized = False

    async def initialize(self, settings: MyModuleSettings) -> bool:
        """Phase 2 initialization - register model with model_manager."""
        try:
            # Get model_manager service
            model_manager = self.app_context.get_service("core.model_manager.service")
            if not model_manager:
                logger.error("model_manager service not available")
                return False

            # Register model requirement
            model_id = f"{MODULE_ID}_embeddings"

            register_result = await model_manager.register_model(
                model_id=model_id,
                model_config=settings.embedding_model,  # Pass ModelRequirement directly
                requester_module_id=MODULE_ID
            )

            if not register_result.success:
                logger.error(f"Failed to register model: {register_result.error}")
                return False

            self.model_id = register_result.data["model_id"]
            logger.info(f"Model registered successfully: {self.model_id}")

            self.initialized = True
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
```

### Step 3: Use Registered Model

```python
# modules/standard/my_module/services.py
async def embed_texts(self, texts: list[str]) -> Result:
    """Generate embeddings using registered model."""
    if not self.initialized or not self.model_id:
        return Result.error(
            code="NOT_INITIALIZED",
            message="Service not initialized"
        )

    try:
        model_manager = self.app_context.get_service("core.model_manager.service")

        # Generate embeddings
        result = await model_manager.generate_embeddings(
            texts=texts,
            model_id=self.model_id
        )

        if result.success:
            # Extract embeddings from result data
            embeddings = result.data.get("embeddings", [])
            logger.info(f"Generated {len(embeddings)} embeddings")
            return Result.success(data={"embeddings": embeddings})
        else:
            logger.error(f"Embedding generation failed: {result.error}")
            return result

    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        return Result.error(
            code="EMBEDDING_ERROR",
            message="Failed to generate embeddings",
            details={"error": str(e)}
        )
```

### Step 4: Release Model on Shutdown

```python
# modules/standard/my_module/services.py
async def cleanup_resources(self):
    """Graceful shutdown - release model reference."""
    if self.model_id:
        try:
            model_manager = self.app_context.get_service("core.model_manager.service")
            if model_manager:
                release_result = await model_manager.release_model(
                    model_id=self.model_id,
                    requester_module_id=MODULE_ID
                )

                if release_result.success:
                    logger.info("Model released successfully")
                else:
                    logger.warning(f"Model release warning: {release_result.error}")

                self.model_id = None

        except Exception as e:
            logger.error(f"Error releasing model: {e}")

    self.initialized = False
```

---

## API Reference

### `register_model(model_id: str, model_config: ModelRequirement, requester_module_id: str) -> Result`

Register a model requirement with the model_manager.

**Parameters**:
- `model_id`: Unique identifier for this model (e.g., "standard.my_module_embeddings")
- `model_config`: `ModelRequirement` instance with model configuration
- `requester_module_id`: Module ID making the request (e.g., "standard.my_module")

**Returns**: `Result` with registration data:
```python
{
    "registered": True,
    "model_id": "standard.my_module_embeddings",
    "new_registration": True,  # False if already registered
    "model_type": "embedding",
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "reference_count": 1
}
```

**Example**:
```python
from modules.core.model_manager.schemas import ModelRequirement

model_req = ModelRequirement(
    model_type="embedding",
    name="sentence-transformers/all-MiniLM-L6-v2",
    dimension=384,
    device="auto"
)

result = await model_manager.register_model(
    model_id="standard.my_module_embeddings",
    model_config=model_req,
    requester_module_id="standard.my_module"
)
```

---

### `generate_embeddings(texts: Union[str, List[str]], model_id: str) -> Result`

Generate vector embeddings for text using registered model.

**Parameters**:
- `texts`: Single text string or list of texts
- `model_id`: Model ID from registration

**Returns**: `Result` with embedding data:
```python
{
    "embeddings": [[0.1, 0.2, ...], ...],  # List of embedding vectors
    "model_id": "standard.my_module_embeddings",
    "cached": False,  # True if result came from cache
    "processing_time": 0.045,
    "worker_id": "worker_0"  # If worker pool is used
}
```

**Example**:
```python
result = await model_manager.generate_embeddings(
    texts=["hello world", "test document"],
    model_id="standard.my_module_embeddings"
)

if result.success:
    embeddings = result.data.get("embeddings", [])
    print(f"Generated {len(embeddings)} embeddings")
```

**Note**: Always extract embeddings using `.get("embeddings", [])` from the result data dictionary.

---

### `release_model(model_id: str, requester_module_id: str) -> Result`

Release a model reference (decrements reference count).

**Parameters**:
- `model_id`: Model ID to release
- `requester_module_id`: Module ID releasing the model

**Returns**: `Result` with release status:
```python
{
    "released": True,
    "references": 0  # Remaining reference count
}
```

**Example**:
```python
result = await model_manager.release_model(
    model_id="standard.my_module_embeddings",
    requester_module_id="standard.my_module"
)
```

---

### `get_service_status() -> Result`

Get comprehensive service status including loaded models, cache, and workers.

**Returns**: `Result` with status data:
```python
{
    "initialized": True,
    "worker_pool": {
        "enabled": True,
        "num_workers": 2,
        "active_workers": 2,
        "pending_tasks": 0
    },
    "embedding_cache": {
        "enabled": True,
        "cached_count": 150,
        "hit_rate": 0.67
    },
    "loaded_models": {
        "standard.my_module_embeddings": {
            "reference_count": 1,
            "last_accessed": 1697234567.89,
            "source": "worker_pool",
            "device": "cuda:0"
        }
    },
    "total_loaded_models": 1
}
```

---

## Resource Management

### Model Sharing

Multiple modules can share the same loaded model through reference counting:

```python
# Module A registers embedding model
await model_manager.register_model(
    model_id="embedding_384",
    model_config=ModelRequirement(
        model_type="embedding",
        name="sentence-transformers/all-MiniLM-L6-v2",
        dimension=384
    ),
    requester_module_id="standard.module_a"
)

# Module B registers same model - reuses loaded instance
await model_manager.register_model(
    model_id="embedding_384",
    model_config=ModelRequirement(
        model_type="embedding",
        name="sentence-transformers/all-MiniLM-L6-v2",
        dimension=384
    ),
    requester_module_id="standard.module_b"
)
# Reference count is now 2, model stays loaded
```

**Lifecycle**:
- Model loaded on first use (not at registration)
- Reference count incremented for each requester
- Model kept in memory while any module holds reference
- Unloaded when all references released and model idle

### GPU Allocation

The model_manager handles GPU resource allocation automatically:

**Device Selection**:
- `"auto"`: Automatically selects best available device (prefers GPU)
- `"cuda:0"`, `"cuda:1"`, etc.: Specific GPU device
- `"cpu"`: Force CPU execution

**Worker Pool**:
- Distributes models across multiple GPUs
- Round-robin or least-busy load balancing
- Each worker independently handles tasks
- Configured in model_manager settings

### Embedding Cache

Caches embedding results to avoid recomputation:

```python
# First call - generates embeddings
result1 = await model_manager.generate_embeddings(
    texts=["hello world"],
    model_id="my_embeddings"
)
# result1.data["cached"] = False

# Second call with same text - cached
result2 = await model_manager.generate_embeddings(
    texts=["hello world"],
    model_id="my_embeddings"
)
# result2.data["cached"] = True
```

**Configuration** (in `core.model_manager` settings):
- `enabled`: Enable/disable caching
- `max_cache_size`: Maximum cached entries (default: 10000)
- `ttl_seconds`: Time to live for cached entries (default: 3600)

---

## Configuration

### Framework-Level Settings

Model manager infrastructure settings in `modules/core/model_manager/settings.py`:

```python
class ModelManagerSettings(BaseModel):
    # Module enable/disable
    enabled: bool = Field(default=True)

    # Worker pool configuration
    worker_pool: WorkerPoolConfig = Field(
        default_factory=lambda: WorkerPoolConfig(
            enabled=True,
            num_workers=2,
            devices=["auto"],  # Auto-detect GPUs
            batch_size=32,
            queue_timeout=30,
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

    # Hardware preferences
    device_preference: str = Field(default="auto")
    gpu_memory_fraction: float = Field(default=0.8)
    allow_gpu_growth: bool = Field(default=True)
```

### Module-Level Requirements

Each module defines its own model requirements in its settings:

```python
# modules/standard/my_module/settings.py
class MyModuleSettings(BaseModel):
    embedding_model: ModelRequirement = Field(
        default_factory=lambda: ModelRequirement(
            model_type="embedding",
            name="sentence-transformers/all-MiniLM-L6-v2",
            dimension=384,
            device="auto",
            batch_size=32
        )
    )
```

---

## Complete Example: Document Processor Module

This example demonstrates a complete module using the model_manager:

### 1. Module Settings

```python
# modules/standard/document_processor/settings.py
from pydantic import BaseModel, Field
from modules.core.model_manager.schemas import ModelRequirement

class DocumentProcessorSettings(BaseModel):
    enabled: bool = Field(default=True)

    embedding_model: ModelRequirement = Field(
        default_factory=lambda: ModelRequirement(
            model_type="embedding",
            name="mixedbread-ai/mxbai-embed-large-v1",
            dimension=1024,
            device="auto",
            batch_size=32,
            cache_embeddings=True
        )
    )
```

### 2. Service Implementation

```python
# modules/standard/document_processor/services.py
from core.logging import get_framework_logger
from core.error_utils import Result

MODULE_ID = "standard.document_processor"
logger = get_framework_logger(MODULE_ID)

class DocumentProcessorService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.model_id = None
        self.initialized = False

    async def initialize(self, settings: DocumentProcessorSettings) -> bool:
        """Phase 2: Register model with model_manager."""
        try:
            model_manager = self.app_context.get_service("core.model_manager.service")
            if not model_manager:
                logger.error("model_manager service not available")
                return False

            # Register embedding model
            model_id = f"{MODULE_ID}_embeddings"

            register_result = await model_manager.register_model(
                model_id=model_id,
                model_config=settings.embedding_model,
                requester_module_id=MODULE_ID
            )

            if not register_result.success:
                logger.error(f"Failed to register model: {register_result.error}")
                return False

            self.model_id = register_result.data["model_id"]
            logger.info(f"Registered embedding model: {self.model_id}")

            self.initialized = True
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def embed_documents(self, documents: list[str]) -> Result:
        """Generate embeddings for documents."""
        if not self.initialized:
            return Result.error(
                code="NOT_INITIALIZED",
                message="Service not initialized"
            )

        try:
            model_manager = self.app_context.get_service("core.model_manager.service")

            result = await model_manager.generate_embeddings(
                texts=documents,
                model_id=self.model_id
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
        """Graceful shutdown - release model."""
        if self.model_id:
            try:
                model_manager = self.app_context.get_service("core.model_manager.service")
                if model_manager:
                    await model_manager.release_model(
                        model_id=self.model_id,
                        requester_module_id=MODULE_ID
                    )
                    logger.info("Model released")
                    self.model_id = None
            except Exception as e:
                logger.error(f"Error releasing model: {e}")

        self.initialized = False
```

---

## Hugging Face Authentication

**Public Models**: Most models on Hugging Face Hub are public and require no authentication.

**Private/Gated Models**: Some models require authentication:
- **Gated models**: Require accepting terms (e.g., Llama 2, Mistral)
- **Private models**: Organization-specific or user-uploaded private models

**Authentication Setup**:

1. Get your token from https://huggingface.co/settings/tokens
2. Set environment variable in `.env` file:
   ```bash
   HF_TOKEN=hf_your_token_here
   ```
3. Or use CLI login (one-time setup):
   ```bash
   huggingface-cli login
   ```

The framework automatically uses the token when loading models. No code changes needed.

---

## Best Practices

1. **Define Requirements in Settings**: Always specify model needs in module Pydantic settings
2. **Register During Phase 2**: Register models in `initialize()` method, never in `__init__()`
3. **Store Model IDs**: Keep model_id from registration for later use
4. **Release on Shutdown**: Call `release_model()` during `cleanup_resources()`
5. **Share Common Models**: Use same model names across modules for automatic sharing
6. **Handle Result Pattern**: Always check `result.success` before using data
7. **Extract Data Correctly**: Use `result.data.get("embeddings", [])` to extract embeddings
8. **Pass ModelRequirement Directly**: Don't call `.model_dump()` on ModelRequirement

---

## Troubleshooting

### Model Not Loading

**Symptoms**: `register_model()` succeeds but embedding generation fails

**Solutions**:
- Verify model name is correct (Hugging Face format)
- Check device availability (`nvidia-smi` for GPU)
- Ensure sufficient GPU/CPU memory
- Check logs for model download progress

### Out of Memory Errors

**Symptoms**: GPU OOM during model loading or inference

**Solutions**:
- Reduce `batch_size` in ModelRequirement
- Use smaller model variants (e.g., "all-MiniLM-L6-v2" instead of "mxbai-embed-large-v1")
- Release unused models with `release_model()`
- Enable worker pool to distribute across multiple GPUs

### KeyError When Accessing Results

**Symptoms**: `KeyError: '0'` or similar when processing results

**Solution**:
```python
# WRONG - treating result.data as list
embeddings = result.data
dimension = len(embeddings[0])  # KeyError: '0'

# CORRECT - extracting from dict
embeddings = result.data.get("embeddings", [])
dimension = len(embeddings[0]) if embeddings else 0
```

### Model Sharing Not Working

**Symptoms**: Same model loaded multiple times

**Solutions**:
- Verify exact same `name` in model configs across modules
- Use consistent `model_id` if you want explicit sharing
- Check reference counts with `get_service_status()`

---

## Migration from Old Pattern

If you have existing code using hardcoded model IDs, migrate to the registry pattern:

### Old Pattern (Deprecated)

```python
# Direct calling with hardcoded "embedding" model
result = await model_manager.generate_embeddings(
    texts=documents,
    model_id="embedding"  # Hardcoded core model
)
```

### New Pattern (Current)

```python
# 1. Define in module settings
class MyModuleSettings(BaseModel):
    embedding_model: ModelRequirement = Field(
        default_factory=lambda: ModelRequirement(
            model_type="embedding",
            name="sentence-transformers/all-MiniLM-L6-v2",
            dimension=384
        )
    )

# 2. Register during initialization
async def initialize(self, settings):
    result = await model_manager.register_model(
        model_id=f"{MODULE_ID}_embeddings",
        model_config=settings.embedding_model,
        requester_module_id=MODULE_ID
    )
    self.model_id = result.data["model_id"]

# 3. Use registered model
result = await model_manager.generate_embeddings(
    texts=documents,
    model_id=self.model_id  # Module-specific registration
)
```

---

## Summary

The model_manager uses a **dynamic registry pattern** where:
- Modules define their model requirements using `ModelRequirement` schema
- Models are registered during Phase 2 initialization
- Model loading happens on-demand on first use
- Reference counting tracks model lifecycle
- Multiple modules can share loaded models
- Worker pool distributes load across GPUs

This architecture provides clean separation between infrastructure (model_manager) and application logic (modules), while enabling efficient resource management and type-safe configuration.
