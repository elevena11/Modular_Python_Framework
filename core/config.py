"""
core/config.py
Updated: March 24, 2025
Simplified to SQLite-only with default settings
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    """Application settings."""
    
    # Application settings
    APP_NAME: str = os.getenv("APP_NAME", "Modular Python Framework")
    # Note: APP_VERSION removed - use get_framework_version() from core.version instead
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Network configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")  # localhost by default for security
    PORT: int = int(os.getenv("PORT", "8000"))
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))
    
    # Project identification (for multi-project deployments)
    PROJECT_ID: str = os.getenv("PROJECT_ID", "default")
    
    # Data directory for user data (database, settings, etc.)
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    
    # Database settings - default SQLite path, may be overridden in app_context
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Settings file path (in DATA_DIR)
    SETTINGS_FILE: str = os.getenv(
        "SETTINGS_FILE", 
        lambda data_dir: f"{data_dir}/settings.json")(os.getenv("DATA_DIR", "./data"))
    
    # LLM settings
    LLM_API_URL: str = os.getenv("LLM_API_URL", "http://127.0.0.1:11434/api/generate")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    LLM_RETRY_DELAY: int = int(os.getenv("LLM_RETRY_DELAY", "2"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_TOP_P: float = float(os.getenv("LLM_TOP_P", "0.9"))
  
    # Session timeout settings (in minutes)
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "30"))
    
    # Module settings
    MODULES_DIR: str = os.getenv("MODULES_DIR", "modules")
    DISABLE_MODULES: List[str] = [
        x.strip() for x in os.getenv("DISABLE_MODULES", "").split(",") if x.strip()
    ]
    AUTO_INSTALL_DEPENDENCIES: bool = os.getenv("AUTO_INSTALL_DEPENDENCIES", "True").lower() in ("true", "1", "yes")
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
        "*"  # Allow all origins in development
    ]
    
    # API settings
    API_PREFIX: str = "/api/v1"
    
    # SQLite settings - used for async engine configuration
    SQLITE_PRAGMA_STATEMENTS: List[str] = [
        "PRAGMA journal_mode=WAL",      # Use Write-Ahead Logging for better concurrency
        "PRAGMA synchronous=NORMAL",    # Good balance between safety and speed
        "PRAGMA cache_size=10000",      # Larger cache (about 10MB)
        "PRAGMA foreign_keys=ON",       # Enforce foreign key constraints
        "PRAGMA busy_timeout=10000"     # Wait up to 10s on locks
    ]
    
    # General logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Project-specific settings (configured via .env)
    INSTANCE_NAME: str = os.getenv("INSTANCE_NAME", "Framework Instance")
    FEDERATION_ENABLED: bool = os.getenv("FEDERATION_ENABLED", "False").lower() == "true"
    
    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra environment variables for flexibility

# Create settings instance
settings = Config()