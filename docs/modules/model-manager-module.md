# Model Manager Module

The Model Manager Module (`modules/core/model_manager/`) provides centralized management for AI models across the framework. It handles model lifecycle, memory management, reference counting, and cross-module sharing to optimize resource usage and provide a unified interface for various AI model types.

## Overview

The Model Manager Module is a core framework component that serves as the central hub for managing AI models throughout the application. It provides:

- **Multi-Model Support**: Handles embedding models, text generation models, and custom model types
- **Model Sharing**: Reference-counted model sharing across framework modules
- **Memory Management**: Intelligent GPU/CPU device management with configurable memory allocation
- **Caching System**: Configurable embedding cache for performance optimization
- **Lifecycle Management**: Automatic model loading, unloading, and cleanup based on usage patterns
- **Performance Optimization**: Batch processing and model reuse across requests

## Key Features

### 1. Multi-Model Architecture
- **SentenceTransformer Models**: For text embeddings and semantic similarity
- **T5/BERT Models**: For text generation, summarization, and NLP tasks
- **Custom Model Types**: Extensible architecture for additional model types
- **Dynamic Loading**: Models loaded on-demand and cached for efficiency

### 2. Resource Management
- **Reference Counting**: Tracks model usage across modules
- **Memory Optimization**: GPU/CPU allocation based on availability and configuration
- **Automatic Cleanup**: Idle model unloading after configurable timeouts
- **Device Management**: Intelligent device selection and fallback strategies

### 3. Performance Optimization
- **Embedding Cache**: In-memory caching with TTL and size limits
- **Batch Processing**: Efficient batch operations for multiple requests
- **Model Reuse**: Shared model instances across framework modules
- **Lazy Loading**: Models loaded only when needed

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Model Manager Module                     │
├─────────────────────────────────────────────────────────────┤
│ Model Management Layer                                      │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Model           │ │ Reference       │ │ Lifecycle       │ │
│ │ Registry        │ │ Tracking        │ │ Management      │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Model Types Layer                                           │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Embedding       │ │ Text Generation │ │ Custom Model    │ │
│ │ Models          │ │ Models          │ │ Types           │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Resource Management Layer                                   │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Device          │ │ Memory          │ │ Cache           │ │
│ │ Management      │ │ Allocation      │ │ Management      │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Performance Layer                                           │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Embedding       │ │ Batch           │ │ Model           │ │
│ │ Cache           │ │ Processing      │ │ Reuse           │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. ModelManagerService
The main service class that orchestrates all model management operations:

```python
class ModelManagerService:
    """Centralized model management service."""
    
    def __init__(self, app_context):
        self.app_context = app_context
        self._loaded_models = {}  # Model registry
        self._embedding_cache = {}  # Embedding cache
        self._cache_timestamps = {}  # Cache TTL tracking
    
    async def get_model(self, model_id: str) -> Result:
        """Get a shared model instance."""
        # Check cache, load if needed, return model
        
    async def generate_embeddings(self, texts, model_id) -> Result:
        """Generate embeddings with caching."""
        # Check cache, generate if needed, cache results
        
    async def release_model(self, model_id: str) -> Result:
        """Release a model reference."""
        # Decrement reference count, cleanup if needed
```

### 2. ModelReference
Tracks model usage and lifecycle:

```python
class ModelReference:
    """Tracks model usage and references."""
    
    def __init__(self, model_id, model_instance, model_config):
        self.model_id = model_id
        self.model_instance = model_instance
        self.model_config = model_config
        self.reference_count = 0
        self.last_accessed = time.time()
        self.created_at = time.time()
    
    def add_reference(self):
        """Add a reference to this model."""
        self.reference_count += 1
        self.last_accessed = time.time()
    
    def remove_reference(self):
        """Remove a reference from this model."""
        self.reference_count = max(0, self.reference_count - 1)
        self.last_accessed = time.time()
    
    def is_idle(self, idle_timeout: int) -> bool:
        """Check if model has been idle for too long."""
        return (time.time() - self.last_accessed) > idle_timeout
```

### 3. Device Management
Intelligent device selection and GPU management:

```python
async def _determine_device(self, model_id: str) -> str:
    """Determine the best device for a model."""
    device_preference = self.config.get("device_preference", "auto")
    model_device = self.config.get(f"models.{model_id}.device", "auto")
    
    # Check for force CPU
    if device_preference == "cpu" or model_device == "cpu":
        return "cpu"
    
    # Auto-detect best device
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    
    return "cpu"
```

## Model Types

### 1. Embedding Models
SentenceTransformer models for generating text embeddings:

```python
# Configuration
"models.embedding.type": "embedding"
"models.embedding.name": "mixedbread-ai/mxbai-embed-large-v1"
"models.embedding.dimension": 1024
"models.embedding.device": "auto"
"models.embedding.batch_size": 32
"models.embedding.shared": True
"models.embedding.cache_embeddings": True

# Usage
result = await model_manager.get_embedding_model("embedding")
if result.success:
    model = result.data["model"]
    embeddings = model.encode(["text to embed"])
```

### 2. Text Generation Models
T5, BERT, and similar transformer models:

```python
# Configuration
"models.t5_summarizer.type": "text2text"
"models.t5_summarizer.name": "google/flan-t5-large"
"models.t5_summarizer.local_path": "./models/t5"
"models.t5_summarizer.device": "auto"
"models.t5_summarizer.shared": True
"models.t5_summarizer.max_input_length": 512
"models.t5_summarizer.max_output_length": 128

# Usage
result = await model_manager.get_text_generation_model("t5_summarizer")
if result.success:
    model = result.data["model"]
    tokenizer = result.data["tokenizer"]
    device = result.data["device"]
```

### 3. Custom Model Types
Extensible architecture for additional model types:

```python
# Example custom model integration
async def get_custom_model(self, model_id: str) -> Result:
    """Get a custom model instance."""
    model_type = self.config.get(f"models.{model_id}.type")
    
    if model_type == "custom_vision":
        return await self._load_custom_vision_model(model_id)
    elif model_type == "custom_nlp":
        return await self._load_custom_nlp_model(model_id)
    
    return Result.error(
        code="UNSUPPORTED_MODEL_TYPE",
        message=f"Model type '{model_type}' not supported"
    )
```

## Service Integration

### 1. Basic Model Access
```python
# Get the model manager service
model_manager = app_context.get_service("core.model_manager.service")

# Get any configured model
result = await model_manager.get_model("embedding")
if result.success:
    model = result.data["model"]
    # Use model...
```

### 2. Embedding Generation
```python
# Generate embeddings with caching
result = await model_manager.generate_embeddings(
    texts=["hello world", "another text"],
    model_id="embedding"
)
if result.success:
    embeddings = result.data["embeddings"]
    dimension = result.data["dimension"]
    cached = result.data["cached"]
```

### 3. Text Generation
```python
# Get text generation model
result = await model_manager.get_text_generation_model("t5_summarizer")
if result.success:
    model = result.data["model"]
    tokenizer = result.data["tokenizer"]
    device = result.data["device"]
    
    # Generate text
    inputs = tokenizer.encode("summarize: " + text, return_tensors="pt")
    outputs = model.generate(inputs, max_length=128)
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
```

### 4. Model Status and Management
```python
# Get model status
result = await model_manager.get_model_status()
if result.success:
    loaded_models = result.data["loaded_models"]
    cache_size = result.data["cache_size"]
    models_info = result.data["models"]

# Release model reference
await model_manager.release_model("embedding")
```

## Configuration Management

### 1. Model Configuration
Models are configured using the framework's flat settings structure:

```python
# Embedding model configuration
"models.embedding.type": "embedding"
"models.embedding.name": "mixedbread-ai/mxbai-embed-large-v1"
"models.embedding.local_path": "./models/mixedbread/snapshots/..."
"models.embedding.dimension": 1024
"models.embedding.device": "auto"
"models.embedding.batch_size": 32
"models.embedding.shared": True
"models.embedding.cache_embeddings": True

# Text generation model configuration
"models.t5_summarizer.type": "text2text"
"models.t5_summarizer.name": "google/flan-t5-large"
"models.t5_summarizer.local_path": "./models/t5"
"models.t5_summarizer.device": "auto"
"models.t5_summarizer.shared": True
"models.t5_summarizer.max_input_length": 512
"models.t5_summarizer.max_output_length": 128
```

### 2. Global Settings
Framework-wide configuration for model management:

```python
# Device management
"device_preference": "auto"  # auto, gpu, cpu
"gpu_memory_fraction": 0.8   # Reserve VRAM
"allow_gpu_growth": True

# Model sharing
"sharing.enabled": True
"sharing.max_shared_models": 5
"sharing.unload_after_seconds": 1800  # 30 minutes
"sharing.reference_counting": True

# Embedding cache
"embedding_cache.enabled": True
"embedding_cache.max_cache_size": 10000
"embedding_cache.ttl_seconds": 3600  # 1 hour
"embedding_cache.persist_to_disk": False

# General settings
"enabled": True
"auto_initialize": True
"log_model_usage": True
"memory_monitoring": True
```

### 3. Environment Variables
Model paths and credentials can be configured via environment variables:

```bash
# Model paths
CORE_MODEL_MANAGER_MODELS_EMBEDDING_LOCAL_PATH="./models/embedding"
CORE_MODEL_MANAGER_MODELS_T5_SUMMARIZER_LOCAL_PATH="./models/t5"

# Device preferences
CORE_MODEL_MANAGER_DEVICE_PREFERENCE="gpu"
CORE_MODEL_MANAGER_GPU_MEMORY_FRACTION="0.9"
```

## API Methods

### 1. Model Access Methods
```python
# Get any configured model
async def get_model(self, model_id: str) -> Result

# Get embedding model specifically
async def get_embedding_model(self, model_id: str = "embedding") -> Result

# Get text generation model
async def get_text_generation_model(self, model_id: str = "t5_summarizer") -> Result

# Get model configuration
async def get_model_config(self, model_id: str) -> Result
```

### 2. Model Operations
```python
# Generate embeddings with caching
async def generate_embeddings(self, texts, model_id: str = "embedding") -> Result

# Release model reference
async def release_model(self, model_id: str) -> Result

# Get model status and statistics
async def get_model_status(self) -> Result

# Get service status
async def get_status(self) -> Result
```

### 3. Lifecycle Management
```python
# Initialize service
async def initialize(self, settings=None) -> Result

# Shutdown service and release resources
async def shutdown(self) -> Result

# Setup device management
async def _setup_device_management(self) -> Result
```

## Error Handling

### 1. Model-Specific Errors
```python
# Model configuration errors
MODEL_NOT_CONFIGURED = "Model not found in configuration"
INVALID_MODEL_TYPE = "Model type mismatch"
MODEL_NOT_FOUND = "Model files not found"

# Loading errors
MODEL_LOAD_ERROR = "Failed to load model"
T5_MODEL_LOAD_ERROR = "Failed to load T5 model"
MISSING_DEPENDENCY = "Required library not installed"

# Runtime errors
GENERATE_EMBEDDINGS_ERROR = "Failed to generate embeddings"
DEVICE_SETUP_ERROR = "Device setup failed"
CACHE_ERROR = "Cache operation failed"
```

### 2. Error Response Format
```python
# Example error response
{
    "success": False,
    "code": "MODEL_NOT_CONFIGURED",
    "message": "Model embedding not found in configuration",
    "details": {
        "model_id": "embedding",
        "error_type": "KeyError",
        "error": "Model configuration missing"
    }
}
```

### 3. Error Handling Patterns
```python
# Proper error handling
result = await model_manager.get_model("embedding")
if not result.success:
    if result.error["code"] == "MODEL_NOT_CONFIGURED":
        logger.error("Model not configured, check settings")
    elif result.error["code"] == "MISSING_DEPENDENCY":
        logger.error("Install required dependencies")
    else:
        logger.error(f"Model access failed: {result.error}")
    return None

model = result.data["model"]
```

## Performance Optimization

### 1. Memory Management
```python
# GPU memory optimization
"gpu_memory_fraction": 0.8    # Reserve 20% VRAM
"allow_gpu_growth": True      # Dynamic allocation

# Model sharing
"sharing.enabled": True       # Share models across modules
"sharing.max_shared_models": 5  # Limit loaded models
"sharing.unload_after_seconds": 1800  # 30 minute timeout
```

### 2. Caching Strategy
```python
# Embedding cache configuration
"embedding_cache.enabled": True
"embedding_cache.max_cache_size": 10000     # Cache entries
"embedding_cache.ttl_seconds": 3600         # 1 hour TTL
"embedding_cache.persist_to_disk": False    # Memory only

# Cache key generation
def _get_cache_key(self, text: str, model_id: str) -> str:
    content = f"{model_id}:{text}"
    return hashlib.md5(content.encode()).hexdigest()
```

### 3. Batch Processing
```python
# Batch embedding generation
texts = ["text1", "text2", "text3"]
result = await model_manager.generate_embeddings(texts, "embedding")
if result.success:
    embeddings = result.data["embeddings"]  # List of embeddings
    
# Batch processing with model directly
result = await model_manager.get_embedding_model("embedding")
if result.success:
    model = result.data["model"]
    embeddings = model.encode(texts, batch_size=32)
```

## Integration Examples

### 1. Document Processing Module
```python
class DocumentProcessor:
    async def initialize(self):
        self.model_manager = self.app_context.get_service("core.model_manager.service")
    
    async def process_documents(self, documents: List[str]):
        # Generate embeddings for similarity search
        result = await self.model_manager.generate_embeddings(
            texts=documents,
            model_id="embedding"
        )
        
        if result.success:
            embeddings = result.data["embeddings"]
            # Store embeddings in vector database
            await self.store_embeddings(documents, embeddings)
            return embeddings
        else:
            logger.error(f"Failed to process documents: {result.error}")
            return None
```

### 2. Summarization Service
```python
class SummarizationService:
    async def summarize_text(self, text: str):
        # Get T5 model for summarization
        result = await self.model_manager.get_text_generation_model("t5_summarizer")
        if not result.success:
            return Result.error(
                code="MODEL_UNAVAILABLE",
                message="Summarization model not available"
            )
        
        model = result.data["model"]
        tokenizer = result.data["tokenizer"]
        device = result.data["device"]
        
        # Generate summary
        inputs = tokenizer.encode(
            f"summarize: {text}",
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to(device)
        
        outputs = model.generate(
            inputs,
            max_length=128,
            num_beams=4,
            early_stopping=True
        )
        
        summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Release model reference
        await self.model_manager.release_model("t5_summarizer")
        
        return Result.success(data={"summary": summary})
```

### 3. Semantic Search Module
```python
class SemanticSearchService:
    async def search_similar_content(self, query: str, corpus: List[str]):
        # Generate query embedding
        query_result = await self.model_manager.generate_embeddings(
            texts=query,
            model_id="embedding"
        )
        
        if not query_result.success:
            return Result.error(
                code="EMBEDDING_ERROR",
                message="Failed to generate query embedding"
            )
        
        query_embedding = query_result.data["embeddings"]
        
        # Generate corpus embeddings (cached if available)
        corpus_result = await self.model_manager.generate_embeddings(
            texts=corpus,
            model_id="embedding"
        )
        
        if not corpus_result.success:
            return Result.error(
                code="EMBEDDING_ERROR",
                message="Failed to generate corpus embeddings"
            )
        
        corpus_embeddings = corpus_result.data["embeddings"]
        
        # Calculate similarities
        similarities = self.calculate_cosine_similarities(
            query_embedding,
            corpus_embeddings
        )
        
        # Return top matches
        top_matches = self.get_top_matches(corpus, similarities, top_k=5)
        
        return Result.success(data={
            "query": query,
            "matches": top_matches,
            "cached": corpus_result.data.get("cached", False)
        })
```

## Best Practices

### 1. Model Lifecycle Management
```python
# ✅ CORRECT: Proper model lifecycle
async def process_data(self, data):
    # Get model
    result = await self.model_manager.get_model("embedding")
    if not result.success:
        return result
    
    model = result.data["model"]
    
    try:
        # Use model
        embeddings = model.encode(data)
        return Result.success(data=embeddings)
    finally:
        # Always release reference
        await self.model_manager.release_model("embedding")

# ❌ WRONG: Not releasing model reference
async def process_data(self, data):
    result = await self.model_manager.get_model("embedding")
    model = result.data["model"]
    return model.encode(data)  # Model reference never released
```

### 2. Error Handling
```python
# ✅ CORRECT: Comprehensive error handling
async def safe_embedding_generation(self, texts):
    try:
        result = await self.model_manager.generate_embeddings(
            texts=texts,
            model_id="embedding"
        )
        
        if not result.success:
            logger.error(f"Embedding generation failed: {result.error}")
            return None
        
        return result.data["embeddings"]
        
    except Exception as e:
        logger.error(f"Unexpected error in embedding generation: {e}")
        return None

# ❌ WRONG: No error handling
async def unsafe_embedding_generation(self, texts):
    result = await self.model_manager.generate_embeddings(texts, "embedding")
    return result.data["embeddings"]  # Will fail if result.success is False
```

### 3. Performance Optimization
```python
# ✅ CORRECT: Batch processing
async def process_large_dataset(self, texts):
    batch_size = 32
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = await self.model_manager.generate_embeddings(
            texts=batch,
            model_id="embedding"
        )
        
        if result.success:
            all_embeddings.extend(result.data["embeddings"])
    
    return all_embeddings

# ❌ WRONG: Individual processing
async def process_large_dataset_slow(self, texts):
    embeddings = []
    for text in texts:
        result = await self.model_manager.generate_embeddings(
            texts=[text],
            model_id="embedding"
        )
        embeddings.append(result.data["embeddings"][0])
    return embeddings
```

## Development Guidelines

### 1. Adding New Model Types
```python
# 1. Add configuration in module_settings.py
"models.new_model.type": "custom_type"
"models.new_model.name": "model_name"
"models.new_model.config_param": "value"

# 2. Implement loader method
async def _load_custom_model(self, model_id: str) -> Result:
    """Load a custom model type."""
    try:
        # Model loading logic
        model = load_custom_model(model_config)
        
        # Register model
        model_ref = ModelReference(model_id, model, model_config)
        model_ref.add_reference()
        self._loaded_models[model_id] = model_ref
        
        return Result.success(data={"model": model})
    except Exception as e:
        return Result.error(
            code="CUSTOM_MODEL_LOAD_ERROR",
            message=f"Failed to load custom model {model_id}",
            details={"error": str(e)}
        )

# 3. Update dispatch logic in get_model()
if model_type == "custom_type":
    return await self._load_custom_model(model_id)
```

### 2. Performance Monitoring
```python
# Monitor model usage
async def monitor_model_performance(self):
    status = await self.model_manager.get_model_status()
    if status.success:
        for model_id, info in status.data["models"].items():
            logger.info(f"Model {model_id}: {info['references']} refs, "
                       f"idle: {info['idle_time']:.1f}s")
```

### 3. Testing
```python
# Unit tests for model manager
class TestModelManager:
    async def test_embedding_generation(self):
        result = await self.model_manager.generate_embeddings(
            texts=["test text"],
            model_id="embedding"
        )
        assert result.success
        assert len(result.data["embeddings"]) > 0
        assert result.data["dimension"] > 0
    
    async def test_model_sharing(self):
        # Get model twice
        result1 = await self.model_manager.get_model("embedding")
        result2 = await self.model_manager.get_model("embedding")
        
        assert result1.success and result2.success
        assert result1.data["model"] is result2.data["model"]  # Same instance
```

## Troubleshooting

### 1. Common Issues
```python
# Model not loading
- Check model configuration in settings
- Verify model files exist at specified paths
- Ensure required dependencies are installed
- Check device availability (GPU/CPU)

# Out of memory errors
- Reduce gpu_memory_fraction
- Enable allow_gpu_growth
- Reduce batch_size
- Use CPU device for some models

# Cache issues
- Clear embedding cache
- Check cache size limits
- Verify TTL settings
- Monitor cache hit rates
```

### 2. Debug Information
```python
# Get detailed status
result = await model_manager.get_status()
if result.success:
    print(f"Loaded models: {result.data.get('loaded_models', 0)}")
    print(f"Cache size: {result.data.get('cache_size', 0)}")
    print(f"Models: {result.data.get('models', {})}")
```

## Related Documentation

- [Two-Phase Initialization](../patterns/two-phase-initialization.md) - Module initialization patterns
- [Result Pattern](../patterns/result-pattern.md) - Error handling and return values
- [Settings Module](settings-module.md) - Configuration management
- [Error Handler Module](error-handler-module.md) - Error handling patterns
- [Database Module](database-module.md) - Database integration patterns

---

The Model Manager Module provides a robust, scalable foundation for AI model management in the framework. It handles the complexities of model lifecycle, resource management, and performance optimization while providing a clean, consistent API for all model operations. This enables modules to focus on their core functionality while leveraging powerful AI capabilities through a unified interface.