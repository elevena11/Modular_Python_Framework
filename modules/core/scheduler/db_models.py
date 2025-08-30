"""
modules/core/scheduler/db_models.py
Updated: April 6, 2025
Database models for scheduler module
"""

# Database configuration for file-based discovery
DATABASE_NAME = "framework"

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import DatabaseBase, SQLiteJSON

# AI PATTERN: Table-driven database creation
# 1. Get database-specific base: SchedulerBase = DatabaseBase("framework") 
# 2. Inherit from base: class MyTable(SchedulerBase)
# 3. Framework automatically discovers and creates database
SchedulerBase = DatabaseBase("framework")

# Module identity - not required for error handling but added for consistency
MODULE_ID = "core.scheduler"

class ScheduledEvent(SchedulerBase):
    """
    Model for scheduled events.
    
    This model stores information about tasks scheduled to run at specific times
    or on recurring intervals. It includes metadata about the task, scheduling
    information, and execution status.
    """
    __tablename__ = "scheduler_events"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    module_id = Column(String(100), nullable=False, index=True)  # Source module
    function_name = Column(String(100), nullable=False)
    parameters = Column(SQLiteJSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Scheduling info
    recurring = Column(Boolean, nullable=False, default=False)
    interval_type = Column(String(20), nullable=True)  # minutes, hours, days, weeks, months
    interval_value = Column(Integer, nullable=True)
    next_execution = Column(DateTime, nullable=False, index=True)
    
    # Status tracking
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed, paused
    last_execution = Column(DateTime, nullable=True)
    execution_count = Column(Integer, nullable=False, default=0)
    max_executions = Column(Integer, nullable=True)  # Optional limit
    last_error = Column(Text, nullable=True)
    
    # Relationships
    executions = relationship(lambda: EventExecution, back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScheduledEvent id={self.id} name={self.name} status={self.status}>"


class EventExecution(SchedulerBase):
    """
    Model for event execution records.
    
    This model stores the history of task executions, including start and end times,
    success status, results, and any errors that occurred.
    """
    __tablename__ = "scheduler_executions"
    
    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("scheduler_events.id", ondelete="CASCADE"), index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    success = Column(Boolean, nullable=True)  # Null means still running
    result = Column(SQLiteJSON, nullable=True)
    error = Column(Text, nullable=True)
    trace_session_id = Column(String(36), nullable=True)  # For linking to trace logs
    
    # Relationships
    event = relationship(lambda: ScheduledEvent, back_populates="executions")

    def __repr__(self):
        return f"<EventExecution id={self.id} event_id={self.event_id} success={self.success}>"


class CleanupConfig(SchedulerBase):
    """
    Model for cleanup configurations.
    
    This model stores configurations for the Housekeeper component, defining
    directories, patterns, and retention policies for periodic cleanup operations.
    """
    __tablename__ = "scheduler_cleanup_configs"
    
    id = Column(String(36), primary_key=True)
    directory = Column(String(512), nullable=False)
    pattern = Column(String(128), nullable=False, default="*")
    retention_days = Column(Integer, nullable=True)
    max_files = Column(Integer, nullable=True)
    max_size_mb = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=False, default=100)
    description = Column(String(256), nullable=True)
    module_id = Column(String(100), nullable=False, index=True)  # Source module
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    last_run = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<CleanupConfig id={self.id} directory={self.directory} pattern={self.pattern}>"
