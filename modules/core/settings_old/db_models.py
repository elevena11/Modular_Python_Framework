"""
modules/core/settings/models/db_models.py
Updated: April 5, 2025
Database models for settings module with standardized error handling
"""

import logging
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from core.database import DatabaseBase, SQLiteJSON
from core.error_utils import error_message

# Define component identity
MODULE_ID = "core.settings"
COMPONENT_ID = f"{MODULE_ID}.models"
# Use component ID for the logger
logger = logging.getLogger(COMPONENT_ID)

# Declare which database this module's tables belong to
DATABASE_NAME = "framework"

# Get the appropriate database base for this module
FrameworkBase = DatabaseBase("framework")

class SettingsBackup(FrameworkBase):
    """
    Model for storing settings backups in the database.
    
    This model represents a full snapshot of the settings at a point in time,
    allowing restoration of previous configurations.
    
    Attributes:
        id: Unique identifier for the backup
        date_created: When the backup was created
        version: Version string (format: "module1@version1,module2@version2")
        settings_data: Complete settings data as a JSON object
        description: Optional user-provided description
    """
    __tablename__ = "settings_backups"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    date_created = Column(DateTime, default=func.now())
    version = Column(String(50), nullable=False)
    settings_data = Column(SQLiteJSON, nullable=False)  # Using SQLiteJSON for complex types
    description = Column(Text, nullable=True)
    
    def __repr__(self):
        """String representation for debugging."""
        try:
            return f"<SettingsBackup id={self.id} date_created={self.date_created} version={self.version}>"
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="REPR_ERROR",
                details=f"Error in SettingsBackup.__repr__: {str(e)}",
                location="SettingsBackup.__repr__()"
            ))
            return "<SettingsBackup (error in repr)>"
    
    def to_dict(self):
        """
        Convert the model to a dictionary for API responses.
        
        Returns:
            Dictionary representation of the backup
        """
        try:
            return {
                "id": self.id,
                "date_created": self.date_created.isoformat() if self.date_created else None,
                "version": self.version,
                "description": self.description,
                # Don't include settings_data by default as it could be large
            }
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TO_DICT_ERROR",
                details=f"Error converting SettingsBackup to dict: {str(e)}",
                location="SettingsBackup.to_dict()"
            ))
            return {"id": self.id, "error": "Error converting to dictionary"}

class SettingsEvent(FrameworkBase):
    """
    Model for tracking changes to individual settings.
    
    This model records each change to a setting, capturing the old and new values
    as well as metadata about the change event.
    
    Attributes:
        id: Unique identifier for the event
        date_created: When the change occurred
        module_id: Identifier of the module containing the setting
        setting_key: Key of the setting that was changed
        old_value: Previous value before the change
        new_value: New value after the change
        source: Origin of the change (e.g., "user", "api", "system")
    """
    __tablename__ = "settings_events"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    date_created = Column(DateTime, default=func.now())
    module_id = Column(String(100), nullable=False, index=True)
    setting_key = Column(String(100), nullable=False)
    old_value = Column(SQLiteJSON, nullable=True)  # Using SQLiteJSON for complex types
    new_value = Column(SQLiteJSON, nullable=True)  # Using SQLiteJSON for complex types
    source = Column(String(50), nullable=True)  # "user", "api", "system", etc.
    
    def __repr__(self):
        """String representation for debugging."""
        try:
            return f"<SettingsEvent id={self.id} module_id={self.module_id} setting_key={self.setting_key}>"
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="REPR_ERROR",
                details=f"Error in SettingsEvent.__repr__: {str(e)}",
                location="SettingsEvent.__repr__()"
            ))
            return "<SettingsEvent (error in repr)>"
    
    def to_dict(self):
        """
        Convert the model to a dictionary for API responses.
        
        Returns:
            Dictionary representation of the event
        """
        try:
            return {
                "id": self.id,
                "date_created": self.date_created.isoformat() if self.date_created else None,
                "module_id": self.module_id,
                "setting_key": self.setting_key,
                "old_value": self.old_value,
                "new_value": self.new_value,
                "source": self.source
            }
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TO_DICT_ERROR",
                details=f"Error converting SettingsEvent to dict: {str(e)}",
                location="SettingsEvent.to_dict()"
            ))
            return {"id": self.id, "error": "Error converting to dictionary"}

class ScheduledBackup(FrameworkBase):
    """
    Model for scheduled backup configuration.
    
    This model defines a recurring backup schedule, including frequency
    and retention parameters.
    
    Attributes:
        id: Unique identifier for the schedule
        date_created: When the schedule was created
        next_backup_time: When the next backup should occur
        frequency_days: Number of days between backups
        retention_count: Number of backups to keep
        enabled: Whether the schedule is active
        last_error: Error message from the last attempt, if any
    """
    __tablename__ = "scheduled_backups"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    date_created = Column(DateTime, default=func.now())
    next_backup_time = Column(DateTime, nullable=False)
    frequency_days = Column(Integer, nullable=False)
    retention_count = Column(Integer, nullable=False)
    enabled = Column(Boolean, default=True)
    last_error = Column(Text, nullable=True)
    
    def __repr__(self):
        """String representation for debugging."""
        try:
            return f"<ScheduledBackup id={self.id} next_backup_time={self.next_backup_time} frequency_days={self.frequency_days}>"
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="REPR_ERROR",
                details=f"Error in ScheduledBackup.__repr__: {str(e)}",
                location="ScheduledBackup.__repr__()"
            ))
            return "<ScheduledBackup (error in repr)>"
    
    def to_dict(self):
        """
        Convert the model to a dictionary for API responses.
        
        Returns:
            Dictionary representation of the scheduled backup
        """
        try:
            return {
                "id": self.id,
                "date_created": self.date_created.isoformat() if self.date_created else None,
                "next_backup_time": self.next_backup_time.isoformat() if self.next_backup_time else None,
                "frequency_days": self.frequency_days,
                "retention_count": self.retention_count,
                "enabled": self.enabled,
                "last_error": self.last_error
            }
        except Exception as e:
            logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TO_DICT_ERROR",
                details=f"Error converting ScheduledBackup to dict: {str(e)}",
                location="ScheduledBackup.to_dict()"
            ))
            return {"id": self.id, "error": "Error converting to dictionary"}

# Helper functions for model operations
def create_model_index(model_class, database_engine):
    """
    Create additional indexes for a model that aren't defined in the model class.
    
    Args:
        model_class: The SQLAlchemy model class
        database_engine: The database engine to use
    """
    try:
        # Example of adding complex indexes not handled by SQLAlchemy metadata
        table_name = model_class.__tablename__
        
        # Only add specialized indexes if needed
        if table_name == "settings_events":
            # Create composite index on module_id and setting_key
            with database_engine.connect() as conn:
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_module_setting ON {table_name} (module_id, setting_key)")
                
        logger.info(f"Created additional indexes for {table_name}")
    except Exception as e:
        logger.error(error_message(
            module_id=COMPONENT_ID,
            error_type="INDEX_CREATION_ERROR",
            details=f"Error creating indexes for {model_class.__name__}: {str(e)}",
            location="create_model_index()"
        ))
