"""
modules/core/model_manager/module_settings.py
Settings definition for the model_manager module.

A centralized model management service for loading, sharing, and managing
various AI models (embeddings, LLMs, vision models, etc.)
"""

import logging
from core.error_utils import error_message

MODULE_ID = "core.model_manager"
logger = logging.getLogger(MODULE_ID)

# Default settings
DEFAULT_SETTINGS = {
    # Embedding model configuration (flattened)
    "models.embedding.type": "embedding",
    "models.embedding.name": "mixedbread-ai/mxbai-embed-large-v1", 
    "models.embedding.local_path": "./models/mixedbread/snapshots/db9d1fe0f31addb4978201b2bf3e577f3f8900d2",
    "models.embedding.dimension": 1024,
    "models.embedding.device": "auto",  # Configurable via settings interface
    "models.embedding.batch_size": 32,
    "models.embedding.shared": True,
    "models.embedding.cache_embeddings": True,
    
    # T5 summarizer model configuration (flattened)
    "models.t5_summarizer.type": "text2text",
    "models.t5_summarizer.name": "google/flan-t5-large",
    "models.t5_summarizer.local_path": "./models/t5",
    "models.t5_summarizer.device": "auto",  # Configurable via settings interface
    "models.t5_summarizer.shared": True,
    "models.t5_summarizer.max_input_length": 512,
    "models.t5_summarizer.max_output_length": 128,
    
    # Global device management
    "device_preference": "auto",  # auto, gpu, cpu
    "gpu_memory_fraction": 0.8,  # Reserve some VRAM
    "allow_gpu_growth": True,
    
    # Model sharing and caching (flattened for UI)
    "sharing.enabled": True,
    "sharing.max_shared_models": 5,
    "sharing.unload_after_seconds": 1800,  # 30 minutes idle
    "sharing.reference_counting": True,
    
    # Embedding cache (flattened for UI)
    "embedding_cache.enabled": True,
    "embedding_cache.max_cache_size": 10000,
    "embedding_cache.ttl_seconds": 3600,
    "embedding_cache.persist_to_disk": False,
    
    # Worker pool configuration
    "worker_pool.enabled": True,  # Enabled - using multi-GPU worker pool
    "worker_pool.num_workers": 2,
    "worker_pool.devices": ["cuda:0", "cuda:1"],
    "worker_pool.batch_size": 32,
    "worker_pool.queue_timeout": 30,
    "worker_pool.worker_timeout": 30,
    "worker_pool.preload_embeddings": True,  # Preload embedding models on startup
    "worker_pool.auto_scaling": False,  # No auto scaling - manual control only
    "worker_pool.load_balancing": "round_robin",  # round_robin, least_busy
    "worker_pool.require_gpu": True,  # FAIL if no GPUs available - CPU usage disabled
    
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
    
    # General Configuration
    "enabled": True,
    "auto_initialize": True,
    "log_model_usage": True,
    "memory_monitoring": True
}

# UI metadata for settings interface
UI_METADATA = {
    "models.embedding.device": {
        "display_name": "Embedding Model Device",
        "description": "Device for embedding model (sentence transformers)",
        "type": "select",
        "options": [
            {"value": "auto", "label": "Auto-detect"},
            {"value": "cuda:0", "label": "cuda:0"},
            {"value": "cuda:1", "label": "cuda:1"},
            {"value": "cpu", "label": "CPU"}
        ],
        "category": "Model Devices"
    },
    "models.t5_summarizer.device": {
        "display_name": "T5 Summarizer Device",
        "description": "Device for T5 summarization model",
        "type": "select",
        "options": [
            {"value": "auto", "label": "Auto-detect"},
            {"value": "cuda:0", "label": "cuda:0"},
            {"value": "cuda:1", "label": "cuda:1"},
            {"value": "cpu", "label": "CPU"}
        ],
        "category": "Model Devices"
    },
    "device_preference": {
        "display_name": "Global Device Preference",
        "description": "Default device preference for unspecified models",
        "type": "select",
        "options": [
            {"value": "auto", "label": "Auto-detect (Recommended)"},
            {"value": "gpu", "label": "Force GPU"},
            {"value": "cpu", "label": "Force CPU"}
        ],
        "category": "Hardware"
    },
    "gpu_memory_fraction": {
        "display_name": "GPU Memory Fraction",
        "description": "Fraction of GPU memory to use (0.1-1.0)",
        "type": "number",
        "category": "Hardware"
    },
    "allow_gpu_growth": {
        "display_name": "Allow GPU Memory Growth",
        "description": "Allow gradual GPU memory allocation",
        "type": "checkbox",
        "category": "Hardware"
    },
    "sharing.enabled": {
        "display_name": "Enable Model Sharing",
        "description": "Allow models to be shared between modules",
        "type": "checkbox",
        "category": "Performance"
    },
    "sharing.max_shared_models": {
        "display_name": "Max Shared Models",
        "description": "Maximum number of models to keep loaded",
        "type": "number",
        "category": "Performance"
    },
    "sharing.unload_after_seconds": {
        "display_name": "Idle Unload Time (seconds)",
        "description": "Unload models after this many seconds of inactivity",
        "type": "number",
        "category": "Performance"
    },
    "sharing.reference_counting": {
        "display_name": "Reference Counting",
        "description": "Track model usage with reference counting",
        "type": "checkbox",
        "category": "Performance"
    },
    "embedding_cache.enabled": {
        "display_name": "Enable Embedding Cache",
        "description": "Cache embedding results for faster repeated queries",
        "type": "checkbox",
        "category": "Performance"
    },
    "embedding_cache.max_cache_size": {
        "display_name": "Max Cache Size",
        "description": "Maximum number of embeddings to cache",
        "type": "number",
        "category": "Performance"
    },
    "embedding_cache.ttl_seconds": {
        "display_name": "Cache TTL (seconds)",
        "description": "Time to live for cached embeddings",
        "type": "number",
        "category": "Performance"
    },
    "embedding_cache.persist_to_disk": {
        "display_name": "Persist Cache to Disk",
        "description": "Save embedding cache to disk for persistence",
        "type": "checkbox",
        "category": "Performance"
    },
    "enabled": {
        "display_name": "Enable Model Manager",
        "description": "Enable or disable the model manager service",
        "type": "checkbox",
        "category": "General"
    },
    "auto_initialize": {
        "display_name": "Auto Initialize",
        "description": "Automatically initialize models on startup",
        "type": "checkbox",
        "category": "General"
    },
    "log_model_usage": {
        "display_name": "Log Model Usage",
        "description": "Enable detailed logging of model usage",
        "type": "checkbox",
        "category": "Debugging"
    },
    "memory_monitoring": {
        "display_name": "Memory Monitoring",
        "description": "Monitor GPU and system memory usage",
        "type": "checkbox",
        "category": "Debugging"
    },
    "worker_pool.enabled": {
        "display_name": "Enable Worker Pool",
        "description": "Enable multi-GPU worker pool for parallel processing",
        "type": "checkbox",
        "category": "Worker Pool"
    },
    "worker_pool.num_workers": {
        "display_name": "Number of Workers",
        "description": "Number of worker processes for parallel processing",
        "type": "number",
        "category": "Worker Pool"
    },
    "worker_pool.load_balancing": {
        "display_name": "Load Balancing Strategy",
        "description": "Strategy for distributing tasks across workers",
        "type": "select",
        "options": [
            {"value": "round_robin", "label": "Round Robin"},
            {"value": "least_busy", "label": "Least Busy"}
        ],
        "category": "Worker Pool"
    },
    "worker_pool.memory_threshold": {
        "display_name": "Memory Threshold",
        "description": "GPU memory threshold for model unloading (0.0-1.0)",
        "type": "number",
        "category": "Worker Pool"
    },
    "worker_pool.model_idle_timeout": {
        "display_name": "Model Idle Timeout (seconds)",
        "description": "Timeout before unloading idle models",
        "type": "number",
        "category": "Worker Pool"
    }
}

# Validation schema
VALIDATION_SCHEMA = {
    # Embedding model validation
    "models.embedding.type": {"type": "string", "required": True},
    "models.embedding.name": {"type": "string", "required": True},
    "models.embedding.dimension": {"type": "int", "required": True, "min": 1, "max": 4096},
    "models.embedding.device": {
        "type": "string", 
        "required": True,
        "enum": ["auto", "cuda:0", "cuda:1", "cuda:2", "cuda:3", "cpu"]
    },
    "models.embedding.batch_size": {"type": "int", "required": True, "min": 1, "max": 128},
    "models.embedding.shared": {"type": "bool", "required": True},
    "models.embedding.cache_embeddings": {"type": "bool", "required": True},
    
    # T5 summarizer model validation
    "models.t5_summarizer.type": {"type": "string", "required": True},
    "models.t5_summarizer.name": {"type": "string", "required": True},
    "models.t5_summarizer.local_path": {"type": "string", "required": False},
    "models.t5_summarizer.device": {
        "type": "string", 
        "required": True,
        "enum": ["auto", "cuda:0", "cuda:1", "cuda:2", "cuda:3", "cpu"]
    },
    "models.t5_summarizer.shared": {"type": "bool", "required": True},
    "models.t5_summarizer.max_input_length": {"type": "int", "required": False, "min": 1, "max": 2048},
    "models.t5_summarizer.max_output_length": {"type": "int", "required": False, "min": 1, "max": 512},
    "device_preference": {
        "type": "string",
        "enum": ["auto", "gpu", "cpu"],
        "required": True
    },
    "gpu_memory_fraction": {
        "type": "float",
        "min": 0.1,
        "max": 1.0,
        "required": True
    },
    "allow_gpu_growth": {
        "type": "bool",
        "required": True
    },
    "sharing.enabled": {"type": "bool", "required": True},
    "sharing.max_shared_models": {"type": "int", "required": True, "min": 1, "max": 20},
    "sharing.unload_after_seconds": {"type": "int", "required": True, "min": 60, "max": 7200},
    "sharing.reference_counting": {"type": "bool", "required": True},
    "embedding_cache.enabled": {"type": "bool", "required": True},
    "embedding_cache.max_cache_size": {"type": "int", "required": True, "min": 100, "max": 100000},
    "embedding_cache.ttl_seconds": {"type": "int", "required": True, "min": 60, "max": 86400},
    "embedding_cache.persist_to_disk": {"type": "bool", "required": True},
    "enabled": {"type": "bool", "required": True},
    "auto_initialize": {"type": "bool", "required": True},
    "log_model_usage": {"type": "bool", "required": True},
    "memory_monitoring": {"type": "bool", "required": True},
    
    # Worker pool validation
    "worker_pool.enabled": {"type": "bool", "required": True},
    "worker_pool.num_workers": {"type": "int", "required": True, "min": 1, "max": 8},
    "worker_pool.batch_size": {"type": "int", "required": True, "min": 1, "max": 128},
    "worker_pool.queue_timeout": {"type": "int", "required": True, "min": 1, "max": 300},
    "worker_pool.worker_timeout": {"type": "int", "required": True, "min": 1, "max": 600},
    "worker_pool.model_switching": {"type": "bool", "required": True},
    "worker_pool.max_switches_per_hour": {"type": "int", "required": True, "min": 0, "max": 100},
    "worker_pool.load_balancing": {
        "type": "string", 
        "required": True,
        "enum": ["round_robin", "least_busy"]
    },
    "worker_pool.memory_threshold": {"type": "float", "required": True, "min": 0.1, "max": 1.0},
    "worker_pool.model_idle_timeout": {"type": "int", "required": True, "min": 60, "max": 3600}
}

async def get_settings():
    """
    Retrieve current module settings.
    """
    try:
        return DEFAULT_SETTINGS
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="SETTINGS_RETRIEVAL_ERROR",
            details=f"Error retrieving settings: {str(e)}",
            location="get_settings()"
        ))
        return None

async def update_settings(new_settings: dict):
    """
    Update module settings.
    """
    try:
        # Validate settings here if needed
        logger.info(f"Settings updated for {MODULE_ID}")
        return True
    except Exception as e:
        logger.error(error_message(
            module_id=MODULE_ID,
            error_type="SETTINGS_UPDATE_ERROR",
            details=f"Error updating settings: {str(e)}",
            location="update_settings()"
        ))
        return False