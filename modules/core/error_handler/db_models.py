"""
modules/core/error_handler/db_models.py
Updated: March 27, 2025
Database models for error handler knowledge system
"""

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.orm import relationship
from core.database import DatabaseBase, SQLiteJSON
from datetime import datetime

# Declare which database this module's tables belong to
DATABASE_NAME = "framework"

# Get the appropriate database base for this module
FrameworkBase = DatabaseBase("framework")

class ErrorCode(FrameworkBase):
    """Tracks unique error types and their metadata."""
    __tablename__ = "error_codes"
    __table_args__ = (
        Index('idx_module_code', 'module_id', 'code', unique=True),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True)
    module_id = Column(String(100), nullable=False)  # Just the module part for filtering
    code = Column(String(200), nullable=False)  # The full error code (e.g., "DATABASE_CONNECTION_FAILED")
    first_seen = Column(DateTime, nullable=False, default=datetime.now)
    last_seen = Column(DateTime, nullable=False, default=datetime.now)
    count = Column(Integer, default=0)
    locations = Column(SQLiteJSON, nullable=False, default=list)  # List of code locations
    priority_score = Column(Float, default=0.0)
    
    # Relationships - direct references (no lambda needed in same file)
    documents = relationship("ErrorDocument", back_populates="error_code", cascade="all, delete-orphan")
    examples = relationship("ErrorExample", back_populates="error_code", cascade="all, delete-orphan")

class ErrorDocument(FrameworkBase):
    """Documentation for error codes."""
    __tablename__ = "error_documents"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    error_code_id = Column(Integer, ForeignKey("error_codes.id"), nullable=False)
    title = Column(String(200), nullable=False)
    what_it_means = Column(Text)
    why_important = Column(Text)
    implementation = Column(Text)
    common_mistakes = Column(Text)
    related_patterns = Column(SQLiteJSON, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
    status = Column(String(20), default="draft")  # draft, review, published
    
    # Relationships
    error_code = relationship("ErrorCode", back_populates="documents")

class ErrorExample(FrameworkBase):
    """Specific examples of error occurrences."""
    __tablename__ = "error_examples"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    error_code_id = Column(Integer, ForeignKey("error_codes.id"), nullable=False)
    message = Column(Text, nullable=False)  # Just the message part without the code or location
    module_id = Column(String(100))
    location = Column(String(200))  # Stored separately for context, not for display
    context = Column(SQLiteJSON)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    
    # Relationships
    error_code = relationship("ErrorCode", back_populates="examples")
