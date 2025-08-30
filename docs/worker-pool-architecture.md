# Worker Pool Architecture for Model Manager

## Overview

This document describes the planned worker pool implementation for the core.model_manager module. The worker pool will enable parallel processing across multiple GPUs while maintaining the ability to dynamically switch between different model types (embedding models, T5 text generation, etc.) based on demand.

**Baseline Commit**: `4d466da` - Model manager integration and comprehensive documentation  
**Implementation Target**: Multi-GPU worker pool with dynamic model switching

## Current State (Baseline)

As of the implementation before worker pool addition:

- **Model Manager**: Successfully preloads mixedbread-ai/mxbai-embed-large-v1 on CUDA:0
- **Vector Operations**: Migrated from ChromaDB embedding functions to model_manager
- **Centralized GPU Management**: Single shared model instance across all modules
- **Performance**: Working embeddings with 1024-dimensional mixedbread model
- **Architecture**: Clean modular separation with model_manager as central service

## Worker Pool Design Principles

### 1. Batch-Oriented Processing
- **Assumption**: Large batches of single work type (e.g., 1000 documents for embedding)
- **Optimization**: Workers optimized for sustained processing of same model type
- **Flexibility**: Can switch models between batches when needed

### 2. Multi-Model Support
- **Challenge**: Handle both embedding models (mixedbread) and text generation (T5)
- **Solution**: Dynamic model loading/unloading on workers
- **Strategy**: Intelligent assignment based on model requirements and hardware

### 3. Hardware Utilization
- **Target**: Dual GPU setup (CUDA:0, CUDA:1)
- **Goal**: Parallel processing across both GPUs
- **Fallback**: Graceful degradation to single GPU if needed

## Architecture Components

### Worker Pool Manager
```python
class ModelWorkerPool:
    """Multi-model worker pool with dynamic model switching."""
    
    def __init__(self):
        self.workers: Dict[str, ModelWorker] = {}
        self.model_assignments: Dict[str, str] = {}  # worker_id -> model_id
        self.model_usage: Dict[str, Set[str]] = {}   # model_id -> worker_ids
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.device_pool = ["cuda:0", "cuda:1"]
```

### Individual Workers
```python
class ModelWorker:
    """Individual worker that can load different model types."""
    
    def __init__(self, worker_id: str, device: str):
        self.worker_id = worker_id
        self.device = device
        self.current_model = None
        self.current_model_id = None
        self.is_busy = False
```

### Model Assignment Strategy
1. **Check existing assignments**: If model already loaded, use that worker
2. **Find available worker**: Look for idle worker on optimal device  
3. **Unload least-used model**: If no workers available, intelligently unload
4. **Scale up if needed**: Create new worker if resources allow

## Configuration Integration

### New Settings (model_manager/module_settings.py)
```python
# Worker pool configuration
"worker_pool.enabled": True,
"worker_pool.num_workers": 2,
"worker_pool.devices": ["cuda:0", "cuda:1"],
"worker_pool.batch_size": 32,
"worker_pool.queue_timeout": 30,
"worker_pool.model_switching": True,
"worker_pool.max_switches_per_hour": 10,

# Model priorities and device affinity
"worker_pool.model_priorities": {
    "embedding": 10,        # Highest priority (most frequent)
    "t5_summarizer": 5      # Lower priority
},

"worker_pool.device_affinity": {
    "embedding": ["cuda:0", "cuda:1"],  # Can use any GPU
    "t5_summarizer": ["cuda:1"]         # Prefer GPU 1 (T5 is larger)
},

# Performance and memory management
"worker_pool.memory_threshold": 0.8,   # Unload if >80% GPU memory
"worker_pool.model_idle_timeout": 300, # 5 minutes idle timeout
"worker_pool.load_balancing": "round_robin"  # round_robin, least_busy
```

## API Extensions

### Batch Processing
```python
async def generate_embeddings_batch(
    self, 
    text_batches: List[List[str]], 
    model_id: str = "embedding"
) -> Result:
    """Process multiple batches in parallel across workers."""
    
    # Distribute batches across available workers
    # Return results in original order
```

### Streaming Processing
```python
async def generate_embeddings_stream(
    self,
    texts: AsyncIterator[str],
    model_id: str = "embedding"
) -> AsyncIterator[List[float]]:
    """Process texts as they arrive, yield embeddings as generated."""
```

### Model Management
```python
async def preload_model_on_workers(
    self, 
    model_id: str, 
    num_workers: int = 1
) -> Result:
    """Preload specific model on designated number of workers."""

async def get_worker_pool_status(self) -> Result:
    """Get detailed status of all workers and their current models."""
```

## Implementation Phases

### Phase 1: Basic Worker Pool (Target Implementation)
**Goal**: Parallel processing with model switching capability

**Features**:
- 2 GPU workers (one per GPU device)
- Dynamic model loading/unloading
- Basic round-robin task distribution
- Memory management and cleanup

**Files to Modify**:
- `modules/core/model_manager/services.py` - Add worker pool management
- `modules/core/model_manager/module_settings.py` - Add worker pool config
- `modules/standard/vector_operations/services.py` - Use batch API

### Phase 2: Advanced Features (Future Enhancement)
**Features**:
- Smart model assignment based on usage patterns
- Performance-based load balancing
- Predictive model preloading
- Worker health monitoring and recovery

### Phase 3: Optimization (Future Enhancement)
**Features**:
- Model co-location optimization
- Cross-model batch optimization
- Dynamic worker scaling
- Advanced memory management

## Performance Expectations

### Throughput Improvements
- **Current**: Sequential processing on single GPU
- **Target**: 2x+ throughput with dual GPU parallel processing
- **Batch Size**: Optimal batching for memory utilization

### Memory Management
- **GPU Memory**: Intelligent model switching when memory constrained
- **Model Size**: mixedbread (~1GB), T5-large (~3GB)
- **Strategy**: LRU eviction with usage frequency weighting

### Latency Characteristics
- **Model Loading**: ~2-5 seconds overhead when switching models
- **Embedding Generation**: <100ms per batch (32 texts)
- **Batch Processing**: Parallelizable across workers

## Error Handling and Recovery

### Worker Failures
- **Detection**: Health checks and timeout monitoring
- **Recovery**: Automatic worker restart with exponential backoff
- **Fallback**: Graceful degradation to remaining workers

### GPU Memory Issues
- **Detection**: Monitor GPU memory usage per worker
- **Response**: Reduce batch sizes, switch to CPU if needed
- **Prevention**: Proactive model unloading when approaching limits

### Model Loading Failures
- **Handling**: Retry with backoff, fallback to CPU if GPU fails
- **Logging**: Detailed error reporting for debugging
- **Graceful**: Continue with available workers

## Migration Strategy

### From Current Model Manager
1. **Preserve existing API**: All current generate_embeddings() calls continue working
2. **Gradual enablement**: Worker pool disabled by default, opt-in via settings
3. **Fallback mode**: If worker pool fails, fall back to current single-model behavior
4. **Testing**: Comprehensive testing against current functionality

### Backward Compatibility
- **API**: No breaking changes to existing model_manager interface
- **Settings**: New worker pool settings are optional
- **Behavior**: Default behavior unchanged unless worker pool enabled

## Testing Strategy

### Unit Tests
- Worker pool initialization and shutdown
- Model loading and unloading on workers
- Task distribution and result collection

### Integration Tests
- End-to-end batch processing through vector_operations
- Model switching between embedding and T5 requests
- Resource cleanup and memory management

### Performance Tests
- Throughput comparison: single worker vs dual worker
- Memory usage profiling during model switches
- Stress testing with large document batches

## Monitoring and Metrics

### Worker Pool Metrics
```python
class WorkerPoolMetrics:
    active_workers: int
    total_tasks_processed: int
    average_task_time: float
    model_switch_count: int
    gpu_memory_usage: Dict[str, float]
    worker_utilization: Dict[str, float]
    queue_size: int
    error_count: int
```

### Logging Strategy
- **Worker lifecycle**: Start, stop, model loading events
- **Performance**: Task timing, throughput metrics
- **Errors**: Detailed error context for debugging
- **Memory**: GPU memory usage tracking

## Future Considerations

### Scalability
- **Multi-node**: Potential for distributed worker pools
- **Model types**: Easy addition of new model types (vision, audio)
- **Hardware**: Support for newer GPU architectures

### Optimization
- **Model sharing**: Shared memory for read-only model weights
- **Batch optimization**: Cross-request batching for efficiency  
- **Caching**: Intelligent caching of frequent model combinations

## Success Criteria

### Performance Targets
- **2x throughput improvement** for large embedding batches
- **<5% overhead** for single requests (compared to current)
- **<10 second** model switching time
- **>95% GPU utilization** during sustained workloads

### Reliability Targets
- **99% uptime** for worker pool service
- **Graceful degradation** when workers fail
- **Zero data loss** during model switches
- **Memory leak prevention** during extended operation

---

## Implementation Notes

This design prioritizes:
1. **Simplicity**: Clear, maintainable architecture 
2. **Reliability**: Robust error handling and recovery
3. **Performance**: Efficient resource utilization
4. **Flexibility**: Easy to extend and modify
5. **Compatibility**: Seamless integration with existing framework

The worker pool will integrate cleanly with the existing model_manager architecture while providing the performance benefits of parallel GPU processing and intelligent resource management.