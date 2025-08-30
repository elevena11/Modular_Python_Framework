"""
modules/core/database/crud_utils.py
Updated: April 4, 2025
Utility functions for CRUD operations with standardized error handling
"""

import logging
from typing import Type, Optional, Dict, Any, List, TypeVar, Union
from sqlalchemy import inspect

# Import error handling utilities
from core.error_utils import error_message

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType")

# Component ID for consistent error codes
COMPONENT_ID = "core.database.crud"

class ModelUtils:
    """Utility functions for working with SQLAlchemy models."""
    
    def __init__(self):
        """Initialize the model utilities."""
        self.logger = logging.getLogger(f"{COMPONENT_ID}.utils")
    
    def get_primary_key(self, model_class: Type[ModelType]) -> Optional[str]:
        """
        Get the name of the primary key column for a model class.
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            Name of primary key column or None if not found
        """
        try:
            # Get primary key columns
            primary_key_cols = []
            for key in model_class.__table__.primary_key.columns:
                primary_key_cols.append(key.name)
            
            # Return the name of the first primary key column
            if primary_key_cols:
                return primary_key_cols[0]
            
            return None
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="PRIMARY_KEY_ERROR",
                details=f"Error getting primary key for {model_class.__name__}: {str(e)}",
                location="get_primary_key()"
            ))
            return None
    
    def to_dict(self, model_instance: ModelType) -> Dict[str, Any]:
        """
        Convert a SQLAlchemy model instance to a dictionary.
        
        Args:
            model_instance: SQLAlchemy model instance
            
        Returns:
            Dictionary representation of the model
        """
        if model_instance is None:
            return None
            
        try:
            # Use SQLAlchemy inspection to get model attributes
            return {c.key: getattr(model_instance, c.key)
                    for c in inspect(model_instance).mapper.column_attrs}
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="MODEL_TO_DICT_ERROR",
                details=f"Error converting model to dict: {str(e)}",
                location="to_dict()"
            ))
            return {}
    
    def model_instances_to_dicts(self, model_instances: List[ModelType]) -> List[Dict[str, Any]]:
        """
        Convert a list of SQLAlchemy model instances to dictionaries.
        
        Args:
            model_instances: List of SQLAlchemy model instances
            
        Returns:
            List of dictionary representations
        """
        if not model_instances:
            return []
            
        return [self.to_dict(instance) for instance in model_instances]
    
    def get_model_columns(self, model_class: Type[ModelType]) -> List[str]:
        """
        Get a list of column names for a model class.
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            List of column names
        """
        try:
            return [c.name for c in model_class.__table__.columns]
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_COLUMNS_ERROR",
                details=f"Error getting columns for {model_class.__name__}: {str(e)}",
                location="get_model_columns()"
            ))
            return []
    
    def validate_columns(self, model_class: Type[ModelType], columns: List[str]) -> List[str]:
        """
        Validate that requested columns exist in the model.
        
        Args:
            model_class: SQLAlchemy model class
            columns: List of column names to validate
            
        Returns:
            List of valid column names (invalid ones are removed)
        """
        if not columns:
            return []
            
        valid_columns = self.get_model_columns(model_class)
        return [col for col in columns if col in valid_columns]
    
    def get_model_info(self, model_class: Type[ModelType]) -> Dict[str, Any]:
        """
        Get detailed information about a model class.
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            Dictionary with model information
        """
        try:
            model_info = {
                "name": model_class.__name__,
                "table_name": model_class.__tablename__,
                "columns": self.get_model_columns(model_class),
                "primary_key": self.get_primary_key(model_class)
            }
            return model_info
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_MODEL_INFO_ERROR",
                details=f"Error getting model info for {model_class.__name__}: {str(e)}",
                location="get_model_info()"
            ))
            return {"name": model_class.__name__, "error": str(e)}
    
    def get_relationships(self, model_class: Type[ModelType]) -> Dict[str, Any]:
        """
        Get information about relationships for a model class.
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            Dictionary with relationship information
        """
        try:
            inspector = inspect(model_class)
            relationships = {}
            
            for rel_name, rel in inspector.relationships.items():
                relationships[rel_name] = {
                    "target": rel.target.name,
                    "direction": rel.direction.name,
                    "uselist": rel.uselist,  # True for one-to-many, False for one-to-one
                    "backref": rel.back_populates
                }
            
            return relationships
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_RELATIONSHIPS_ERROR",
                details=f"Error getting relationships for {model_class.__name__}: {str(e)}",
                location="get_relationships()"
            ))
            return {}
    
    def get_full_model_schema(self, model_class: Type[ModelType]) -> Dict[str, Any]:
        """
        Get complete schema information for a model including columns,
        primary keys, foreign keys, relationships, and indices.
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            Dictionary with complete schema information
        """
        try:
            # Get basic model info
            schema = self.get_model_info(model_class)
            
            # Get relationships
            schema["relationships"] = self.get_relationships(model_class)
            
            # Get column details including types and constraints
            column_details = []
            for column in model_class.__table__.columns:
                column_info = {
                    "name": column.name,
                    "type": str(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "unique": column.unique,
                    "default": str(column.default) if column.default is not None else None,
                    "autoincrement": column.autoincrement,
                    "foreign_key": None
                }
                
                # Check for foreign key
                if column.foreign_keys:
                    for fk in column.foreign_keys:
                        column_info["foreign_key"] = {
                            "target_table": fk.column.table.name,
                            "target_column": fk.column.name
                        }
                        break  # We only need the first one for basic info
                
                column_details.append(column_info)
            
            schema["column_details"] = column_details
            
            # Get index information
            indices = []
            for index in model_class.__table__.indexes:
                index_info = {
                    "name": index.name,
                    "columns": [col.name for col in index.columns],
                    "unique": index.unique
                }
                indices.append(index_info)
            
            schema["indices"] = indices
            
            return schema
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_SCHEMA_ERROR",
                details=f"Error getting full schema for {model_class.__name__}: {str(e)}",
                location="get_full_model_schema()"
            ))
            return {"name": model_class.__name__, "error": str(e)}
