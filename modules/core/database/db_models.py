"""
modules/core/database/db_models.py
SQLAlchemy models for Database - Core framework system tables.

Framework database tables for module management, settings, and logging.
Standard table-driven database creation pattern.
"""

# Database configuration for file-based discovery
DATABASE_NAME = "framework"

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import DatabaseBase, SQLiteJSON

# Get database base for this module - creates framework.db
FrameworkBase = DatabaseBase(DATABASE_NAME)

class Module(FrameworkBase):
    """Represents a loaded module in the system."""
    __tablename__ = "modules"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(String(100), unique=True, index=True, nullable=False)  # e.g., 'core.database'
    name = Column(String(100), nullable=False)
    version = Column(String(20))
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    settings = relationship("DatabaseModuleSetting", back_populates="module")
    logs = relationship("ModuleLog", back_populates="module")
    
    def __repr__(self):
        return f"<Module(id={self.id}, module_id='{self.module_id}', name='{self.name}')>"


class DatabaseModuleSetting(FrameworkBase):
    """Stores settings for modules."""
    __tablename__ = "module_settings"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text)
    value_type = Column(String(20), nullable=False)  # string, integer, float, boolean, json
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    module = relationship("Module", back_populates="settings")
    
    def __repr__(self):
        return f"<DatabaseModuleSetting(module_id={self.module_id}, key='{self.key}')>"


class ModuleLog(FrameworkBase):
    """Logs module activities and errors."""
    __tablename__ = "module_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, etc.
    message = Column(Text, nullable=False)
    details = Column(SQLiteJSON, nullable=True)
    
    # Timestamps  
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    module = relationship("Module", back_populates="logs")
    
    def __repr__(self):
        return f"<ModuleLog(id={self.id}, module_id={self.module_id}, level='{self.level}')>"

