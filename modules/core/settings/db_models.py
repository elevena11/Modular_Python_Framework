"""
modules/core/settings/db_models.py
SQLAlchemy models for Settings - Minimal user preferences storage.

Simple schema following docs/v2/settings_v2.md architecture:
- Single table for user preference overrides only
- Baseline (defaults + environment) stored in memory
"""

# Database configuration for file-based discovery
DATABASE_NAME = "settings"

from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from core.database import DatabaseBase, SQLiteJSON
from sqlalchemy.sql import func

# Get database base for this module - creates settings.db
SettingsBase = DatabaseBase(DATABASE_NAME)

class UserPreferences(SettingsBase):
    """
    User preference overrides table.
    
    Stores only user-customized settings. Baseline (defaults + environment)
    is resolved in memory for optimal performance.
    
    Schema matches docs/v2/settings_v2.md specification.
    """
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint('module_id', 'setting_key', 'user_id', name='unique_user_setting'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Setting identification
    module_id = Column(String(100), nullable=False, index=True)  # e.g., "core.model_manager"
    setting_key = Column(String(100), nullable=False, index=True)  # e.g., "gpu_memory_fraction"
    
    # User preference value (JSON serialized for type flexibility)
    value = Column(Text, nullable=False)  # JSON serialized value
    
    # User context (for future multi-user support)
    user_id = Column(String(50), nullable=False, default='default', index=True)
    
    # Audit fields
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    changed_by = Column(String(100), nullable=False, default='user')  # Who made the change
    
    def __repr__(self):
        return f"<UserPreferences(module_id='{self.module_id}', setting_key='{self.setting_key}', user_id='{self.user_id}')>"