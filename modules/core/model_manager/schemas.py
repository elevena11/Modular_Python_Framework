"""
Model Manager Schemas

Defines Pydantic schemas for model registration and requirements.
These schemas allow modules to specify their AI model needs in a type-safe way.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


class ModelRequirement(BaseModel):
    """
    Schema for modules to specify AI model requirements.

    Modules define their model needs using this schema in their settings,
    then register with the model_manager during initialization.

    Example:
        class MyModuleSettings(BaseModel):
            embedding_model: ModelRequirement = Field(
                default_factory=lambda: ModelRequirement(
                    model_type="embedding",
                    name="mixedbread-ai/mxbai-embed-large-v1",
                    dimension=1024,
                    device="auto"
                )
            )
    """

    # Required fields
    model_type: Literal["embedding", "text2text", "text_generation", "classification"] = Field(
        ...,
        description="Type of AI model (determines loading strategy and capabilities)"
    )

    name: str = Field(
        ...,
        description="HuggingFace model name (e.g., 'sentence-transformers/all-MiniLM-L6-v2')"
    )

    # Common optional fields
    device: str = Field(
        default="auto",
        description=(
            "Device preference for model execution:\n"
            "  - 'auto': Use best available GPU, fallback to CPU\n"
            "  - 'cpu': Force CPU execution (good for small models)\n"
            "  - 'cuda': Use any available GPU\n"
            "  - 'cuda:0', 'cuda:1', etc.: Specific GPU device\n"
            "Module-controlled: each module specifies optimal device for its model size/needs"
        )
    )

    batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size for model inference"
    )

    local_path: Optional[str] = Field(
        default=None,
        description="Path to locally cached model (optional, will download if not found)"
    )

    # Type-specific fields for embedding models
    dimension: Optional[int] = Field(
        default=None,
        ge=1,
        le=4096,
        description="Output dimension for embedding models (required for embedding type)"
    )

    cache_embeddings: bool = Field(
        default=True,
        description="Cache embedding results for identical inputs"
    )

    # Type-specific fields for text2text models
    max_input_length: Optional[int] = Field(
        default=None,
        ge=1,
        le=8192,
        description="Maximum input token length for text2text models"
    )

    max_output_length: Optional[int] = Field(
        default=None,
        ge=1,
        le=2048,
        description="Maximum output token length for text2text models"
    )

    # Type-specific fields for text generation models
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for generation models"
    )

    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter for generation models"
    )

    top_k: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Top-k sampling parameter for generation models"
    )

    streaming: bool = Field(
        default=False,
        description="Enable token streaming for generation models"
    )

    # Type-specific fields for classification models
    num_labels: Optional[int] = Field(
        default=None,
        ge=2,
        le=1000,
        description="Number of classification labels"
    )

    threshold: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Classification threshold for binary/multi-label classification"
    )

    # Lifecycle management
    shared: bool = Field(
        default=True,
        description="Allow sharing this model with other modules (reference counting)"
    )

    preload_workers: int = Field(
        default=0,
        ge=0,
        description="Number of workers to preload model on at startup (0=download only, lazy load on first use)"
    )

    @field_validator("dimension")
    @classmethod
    def validate_embedding_dimension(cls, v, info):
        """Ensure dimension is provided for embedding models."""
        if info.data.get("model_type") == "embedding" and v is None:
            raise ValueError("dimension is required for embedding models")
        return v

    @field_validator("max_input_length", "max_output_length")
    @classmethod
    def validate_text2text_lengths(cls, v, info):
        """Ensure length parameters are provided for text2text models."""
        field_name = info.field_name
        if info.data.get("model_type") == "text2text" and v is None:
            raise ValueError(f"{field_name} is required for text2text models")
        return v

    @field_validator("num_labels")
    @classmethod
    def validate_classification_labels(cls, v, info):
        """Ensure num_labels is provided for classification models."""
        if info.data.get("model_type") == "classification" and v is None:
            raise ValueError("num_labels is required for classification models")
        return v


class ModelRegistration(BaseModel):
    """
    Internal schema tracking a registered model.

    Used by model_manager to track registered models, their requesters,
    and lifecycle state. Not exposed to modules directly.
    """

    model_id: str = Field(
        ...,
        description="Unique identifier for this model registration"
    )

    config: ModelRequirement = Field(
        ...,
        description="Model configuration from requester"
    )

    requesters: set[str] = Field(
        default_factory=set,
        description="Set of module IDs that requested this model"
    )

    loaded: bool = Field(
        default=False,
        description="Whether the model is currently loaded in memory"
    )

    reference_count: int = Field(
        default=0,
        ge=0,
        description="Number of active references to this model"
    )

    load_time: Optional[float] = Field(
        default=None,
        description="Timestamp when model was loaded"
    )

    last_accessed: Optional[float] = Field(
        default=None,
        description="Timestamp of last model access"
    )

    memory_usage: Optional[int] = Field(
        default=None,
        description="Approximate memory usage in bytes"
    )


class ModelStatusInfo(BaseModel):
    """
    Schema for model status information.

    Returned by get_model_status() API to provide information about
    loaded models and resource usage.
    """

    model_id: str = Field(..., description="Model identifier")
    model_type: str = Field(..., description="Model type")
    model_name: str = Field(..., description="HuggingFace model name")
    loaded: bool = Field(..., description="Whether model is loaded in memory")
    reference_count: int = Field(..., description="Number of active references")
    requesters: list[str] = Field(..., description="Module IDs using this model")
    device: str = Field(..., description="Device model is loaded on")
    memory_usage: Optional[int] = Field(None, description="Memory usage in bytes")
    last_accessed: Optional[float] = Field(None, description="Last access timestamp")
