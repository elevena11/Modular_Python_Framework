"""
modules/core/model_manager/settings.py
Pydantic settings model for core.model_manager module.

Defines comprehensive type-safe settings for AI model management including
worker pools, caching, and GPU configuration. Models are loaded on-demand
from HuggingFace, not pre-configured.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Literal, Optional
from enum import Enum

# Define enums for better type safety
class DeviceType(str, Enum):
    AUTO = "auto"
    CUDA_0 = "cuda:0"
    CUDA_1 = "cuda:1"
    CUDA_2 = "cuda:2"
    CUDA_3 = "cuda:3"
    CPU = "cpu"

class GlobalDevicePreference(str, Enum):
    AUTO = "auto"
    GPU = "gpu"
    CPU = "cpu"

# Sub-models for nested configurations
class SharingConfig(BaseModel):
    """Configuration for model sharing and lifecycle management."""
    model_config = ConfigDict(env_prefix="CORE_MODEL_MANAGER_SHARING_")
    
    enabled: bool = Field(
        default=True,
        description="Enable model sharing between modules"
    )
    max_shared_models: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of models to keep loaded"
    )
    unload_after_seconds: int = Field(
        default=1800,
        ge=60,
        le=7200,
        description="Unload models after seconds of inactivity"
    )
    reference_counting: bool = Field(
        default=True,
        description="Track model usage with reference counting"
    )

class EmbeddingCacheConfig(BaseModel):
    """Configuration for embedding caching system."""
    model_config = ConfigDict(env_prefix="CORE_MODEL_MANAGER_EMBEDDING_CACHE_")
    
    enabled: bool = Field(
        default=True,
        description="Enable embedding result caching"
    )
    max_cache_size: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum number of embeddings to cache"
    )
    ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Time to live for cached embeddings"
    )
    persist_to_disk: bool = Field(
        default=False,
        description="Persist embedding cache to disk"
    )

class WorkerPoolConfig(BaseModel):
    """Configuration for multi-GPU worker pool."""
    model_config = ConfigDict(env_prefix="CORE_MODEL_MANAGER_WORKER_POOL_")
    
    enabled: bool = Field(
        default=True,
        description="Enable multi-GPU worker pool"
    )
    num_workers: int = Field(
        default=3,
        ge=1,
        le=8,
        description="Number of worker processes for concurrent request handling"
    )
    devices: List[str] = Field(
        default=["auto", "cpu"],
        description=(
            "Device list for workers. Options:\n"
            "  - ['auto']: Auto-detect all GPUs (or CPU if no GPU)\n"
            "  - ['cuda:0', 'cuda:1']: Specific GPU devices\n"
            "  - ['cpu']: CPU-only workers\n"
            "  - ['auto', 'cpu']: Auto-detect GPUs + 1 CPU worker (recommended default)\n"
            "  - ['cuda:0', 'cpu']: Mixed GPU + CPU workers (for small models on CPU)"
        )
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        le=128,
        description="Batch size for worker processing"
    )
    queue_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Task queue timeout in seconds"
    )
    worker_timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Individual worker timeout in seconds"
    )
    require_gpu: bool = Field(
        default=False,
        description="Require GPU availability, fail if CPU-only"
    )
    memory_threshold: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="GPU memory threshold for model unloading"
    )
    model_idle_timeout: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Timeout before unloading idle models"
    )

# Main settings model
class ModelManagerSettings(BaseModel):
    """
    Comprehensive settings for the Model Manager module.
    
    Handles AI model configuration, GPU management, worker pools,
    caching, and performance optimization.
    """
    model_config = ConfigDict(
        env_prefix="CORE_MODEL_MANAGER_",
        use_enum_values=True,  # Use enum values instead of enum objects
        validate_assignment=True,  # Re-validate on assignment
        extra="forbid",  # Don't allow extra fields
        json_schema_extra={
            "title": "Model Manager Settings",
            "description": "Configuration for AI model management and GPU resources"
        }
    )

    # Note: Models now use default HuggingFace cache (~/.cache/huggingface/)
    # for better ecosystem compatibility and to avoid duplicate downloads

    # Global hardware settings
    device_preference: GlobalDevicePreference = Field(
        default=GlobalDevicePreference.AUTO,
        description="Global device preference for model execution"
    )
    gpu_memory_fraction: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="Fraction of GPU memory to reserve"
    )
    allow_gpu_growth: bool = Field(
        default=True,
        description="Allow gradual GPU memory allocation"
    )
    
    # Feature configurations
    sharing: SharingConfig = Field(
        default_factory=SharingConfig,
        description="Model sharing and lifecycle configuration"
    )
    embedding_cache: EmbeddingCacheConfig = Field(
        default_factory=EmbeddingCacheConfig,
        description="Embedding caching system configuration"
    )
    worker_pool: WorkerPoolConfig = Field(
        default_factory=WorkerPoolConfig,
        description="Multi-GPU worker pool configuration"
    )
    
    # General module settings - Framework infrastructure only
    enabled: bool = Field(
        default=True,
        description="Enable or disable the model manager service"
    )
    log_model_usage: bool = Field(
        default=True,
        description="Enable detailed logging of model usage"
    )
    memory_monitoring: bool = Field(
        default=True,
        description="Monitor GPU and system memory usage"
    )

    # Note: Configuration moved to model_config above for Pydantic v2 compatibility