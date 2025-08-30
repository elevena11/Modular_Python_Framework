# Core Model Manager Module

Centralized model management service for loading, sharing, and managing AI models across the Modular Framework.

## Overview

The Core Model Manager provides a unified interface for managing various types of AI models including embedding models, text generation models, and custom model types. It handles model lifecycle, memory management, reference counting, and cross-module sharing to optimize resource usage.

## Features

- **Multi-Model Support**: SentenceTransformer embeddings, T5/BERT text generation, and custom model types
- **Model Sharing**: Reference-counted model sharing across framework modules
- **Memory Management**: GPU/CPU device management with configurable memory allocation
- **Embedding Cache**: Configurable caching system for embedding results
- **Lifecycle Management**: Automatic model loading, unloading based on usage patterns
- **Performance Optimization**: Batch processing and model reuse across requests

## Architecture

### Core Components

- **ModelManagerService**: Main service class managing model lifecycle
- **ModelReference**: Reference tracking for shared model instances
- **Device Management**: Automatic GPU/CPU allocation based on availability
- **Embedding Cache**: In-memory caching with TTL and size limits

### Supported Model Types

1. **Embedding Models** (`type: "embedding"`)
   - SentenceTransformer models for text embeddings
   - Configurable dimensions and batch processing
   - Shared across modules for memory efficiency

2. **Text Generation Models** (`type: "text2text"`)
   - T5, BERT, and similar transformer models
   - Local and remote model loading
   - CPU/GPU device management

## Service Access

```python
# Get the model manager service
model_manager = app_context.get_service("core.model_manager.service")

# Get an embedding model
result = await model_manager.get_model("embedding")
if result.success:
    model = result.data["model"]
    embeddings = model.encode(["text to embed"])

# Get a text generation model  
result = await model_manager.get_text_generation_model("t5_summarizer")
if result.success:
    model = result.data["model"]
    tokenizer = result.data["tokenizer"]
    device = result.data["device"]

# Generate embeddings with caching
result = await model_manager.generate_embeddings(
    texts=["hello world", "another text"],
    model_id="embedding"
)
if result.success:
    embeddings = result.data["embeddings"]

# Get model status and statistics
result = await model_manager.get_model_status()
if result.success:
    print(f"Loaded models: {result.data['loaded_models']}")
    print(f"Cache size: {result.data['cache_size']}")
```

## Configuration

Configuration is managed through the framework settings system with a flattened structure for UI compatibility:

### Embedding Model Settings
```python
"models.embedding.type": "embedding"
"models.embedding.name": "mixedbread-ai/mxbai-embed-large-v1"
"models.embedding.dimension": 1024
"models.embedding.device": "auto"
"models.embedding.batch_size": 32
"models.embedding.shared": True
"models.embedding.cache_embeddings": True
```

### Text Generation Model Settings
```python
"models.t5_summarizer.type": "text2text"
"models.t5_summarizer.name": "google/flan-t5-large"
"models.t5_summarizer.local_path": "./models/t5"
"models.t5_summarizer.device": "cpu"
"models.t5_summarizer.shared": True
"models.t5_summarizer.max_input_length": 512
"models.t5_summarizer.max_output_length": 128
```

### Global Settings
```python
"device_preference": "auto"  # auto, gpu, cpu
"gpu_memory_fraction": 0.8   # Reserve VRAM
"allow_gpu_growth": True

"sharing.enabled": True
"sharing.max_shared_models": 5
"sharing.unload_after_seconds": 1800  # 30 min idle timeout
"sharing.reference_counting": True

"embedding_cache.enabled": True
"embedding_cache.max_cache_size": 10000
"embedding_cache.ttl_seconds": 3600  # 1 hour
"embedding_cache.persist_to_disk": False
```

## API Methods

### Model Access
- `get_model(model_id: str) -> Result`: Get any configured model
- `get_embedding_model(model_id: str) -> Result`: Get embedding model specifically
- `get_text_generation_model(model_id: str) -> Result`: Get text generation model
- `get_model_config(model_id: str) -> Result`: Get model configuration

### Model Operations
- `generate_embeddings(texts, model_id) -> Result`: Generate embeddings with caching
- `release_model_reference(model_id: str) -> Result`: Release model reference
- `preload_model(model_id: str) -> Result`: Preload model for faster access

### Status and Management
- `get_model_status() -> Result`: Get loaded models and cache statistics
- `clear_embedding_cache() -> Result`: Clear embedding cache
- `get_available_models() -> Result`: List all configured models
- `cleanup_unused_models() -> Result`: Remove unused models from memory

## Integration Examples

### Using with LLM Memory Processing

```python
# In another module's service
async def process_memories(self, texts: List[str]):
    model_manager = self.app_context.get_service("core.model_manager.service")
    
    # Generate embeddings for similarity search
    result = await model_manager.generate_embeddings(
        texts=texts,
        model_id="embedding"
    )
    
    if result.success:
        embeddings = result.data["embeddings"]
        # Use embeddings for vector search...
        return embeddings
    else:
        logger.error(f"Failed to generate embeddings: {result.error}")
        return None
```

### Using with Knowledge Graph

```python
# Generate embeddings for graph nodes
async def embed_concepts(self, concepts: List[str]):
    model_manager = self.app_context.get_service("core.model_manager.service")
    
    result = await model_manager.get_model("embedding")
    if result.success:
        model = result.data["model"]
        embeddings = model.encode(concepts, batch_size=32)
        
        # Release reference when done
        await model_manager.release_model_reference("embedding")
        return embeddings
```

## Performance Considerations

### Memory Management
- Models are shared across modules using reference counting
- Automatic unloading after configurable idle timeout
- GPU memory fraction configuration prevents VRAM exhaustion
- CPU fallback for models when GPU unavailable

### Caching Strategy
- Embedding results cached in-memory with TTL
- Cache key based on text content hash
- Configurable cache size limits
- Optional disk persistence (disabled by default)

### Device Allocation
- Automatic GPU detection and allocation
- Fallback to CPU when GPU unavailable or full
- Per-model device configuration
- T5 models default to CPU to avoid VRAM conflicts

## Error Handling

The module implements comprehensive error handling with specific error codes:

- `MODEL_NOT_CONFIGURED`: Requested model not in configuration
- `MODEL_LOAD_ERROR`: Failed to load model from disk/remote
- `DEVICE_ERROR`: GPU/device allocation failed
- `CACHE_ERROR`: Embedding cache operation failed
- `REFERENCE_ERROR`: Model reference counting error

All methods return `Result` objects with detailed error information for proper error handling and debugging.

## Development

### Adding New Model Types

1. Add configuration in `module_settings.py`
2. Implement loader method in `ModelManagerService`
3. Update `get_model()` dispatch logic
4. Add API schemas if needed

### Testing

```bash
# Run model manager specific tests
pytest tests/modules/core/model_manager/

# Run compliance validation
python tools/compliance/compliance.py validate --module core.model_manager
```

### Performance Monitoring

The service provides detailed statistics on model usage, cache performance, and memory consumption through the `get_model_status()` method for monitoring and optimization.

## Dependencies

- **PyTorch**: For model loading and GPU management
- **SentenceTransformers**: For embedding models
- **Transformers**: For text generation models
- **Core Framework**: Settings, error handling, dependency injection

## Version History

- **1.0.0**: Initial implementation with embedding and T5 model support