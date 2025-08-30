"""
modules/core/database/crud_filters.py
Updated: April 4, 2025
Filter parser for CRUD operations with standardized error handling
"""

import logging
from typing import Dict, Any, List, Type, Optional, Union, TypeVar
from sqlalchemy import and_, or_, not_, inspect
from sqlalchemy.sql import operators
from sqlalchemy.sql.expression import BinaryExpression, ColumnElement

# Import error handling utilities
from core.error_utils import error_message

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType")

# Component ID for consistent error codes
COMPONENT_ID = "core.database.crud"

class FilterParser:
    """Parser for converting dictionary filters to SQLAlchemy expressions."""
    
    def __init__(self):
        """Initialize the filter parser."""
        self.logger = logging.getLogger(f"{COMPONENT_ID}.filters")
        self.initialized = False
        
        # Register operators with their handler methods
        self.operators = {
            # Comparison operators
            "eq": self._op_eq,
            "ne": self._op_ne,
            "gt": self._op_gt,
            "lt": self._op_lt,
            "gte": self._op_gte,
            "ge": self._op_gte,  # Alias for gte
            "lte": self._op_lte,
            "le": self._op_lte,  # Alias for lte
            
            # Collection operators
            "in": self._op_in,
            "not_in": self._op_not_in,
            
            # Range operators
            "between": self._op_between,
            "not_between": self._op_not_between,
            
            # Text search
            "like": self._op_like,
            "not_like": self._op_not_like,
            "ilike": self._op_ilike,
            "not_ilike": self._op_not_ilike,
            
            # Null checking
            "is_null": self._op_is_null,
            "not_null": self._op_not_null
        }
        
        self.initialized = True
    
    def parse_filters(self, model_class: Type[ModelType], 
                      filters: Optional[Dict[str, Any]]) -> Optional[BinaryExpression]:
        """
        Convert dictionary filters to SQLAlchemy expressions.
        
        Args:
            model_class: SQLAlchemy model class
            filters: Dictionary of filters
            
        Returns:
            SQLAlchemy expression or None if no filters
        """
        if not filters:
            return None
            
        expressions = []
        for field_name, condition in filters.items():
            expr = self._process_field_condition(model_class, field_name, condition)
            if expr is not None:
                expressions.append(expr)
                
        # Combine with AND
        return and_(*expressions) if expressions else None
    
    def _process_field_condition(self, model_class: Type[ModelType], 
                               field_name: str, 
                               condition: Any) -> Optional[BinaryExpression]:
        """
        Process a field condition which could be a value or operator dict.
        
        Args:
            model_class: SQLAlchemy model class
            field_name: Name of the field
            condition: Value or dict with operators
            
        Returns:
            SQLAlchemy expression or None if invalid
        """
        # Special handling for OR conditions
        if field_name == "OR" and isinstance(condition, list):
            return self._process_or_condition(model_class, condition)
            
        # Special handling for AND conditions
        if field_name == "AND" and isinstance(condition, list):
            return self._process_and_condition(model_class, condition)
            
        # Skip if field doesn't exist in model
        if not hasattr(model_class, field_name):
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="UNKNOWN_FIELD",
                details=f"Field {field_name} not found in {model_class.__name__}",
                location="_process_field_condition()"
            ))
            return None
            
        field = getattr(model_class, field_name)
        
        # Simple equality condition (e.g., {"status": "active"})
        if not isinstance(condition, dict):
            return field == condition
            
        # Operator-based condition (e.g., {"count": {"gt": 10}})
        expressions = []
        for op_name, value in condition.items():
            if op_name in self.operators:
                expr = self.operators[op_name](field, value)
                if expr is not None:
                    expressions.append(expr)
            else:
                self.logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="UNKNOWN_OPERATOR",
                    details=f"Unknown operator '{op_name}' for {field_name}",
                    location="_process_field_condition()"
                ))
        
        # Combine with AND if multiple operators for same field
        return and_(*expressions) if expressions else None
    
    def _process_or_condition(self, model_class: Type[ModelType], conditions: List[Dict[str, Any]]) -> Optional[BinaryExpression]:
        """
        Process an OR condition with multiple subconditions.
        
        Args:
            model_class: SQLAlchemy model class
            conditions: List of condition dictionaries to OR together
            
        Returns:
            SQLAlchemy OR expression or None if invalid
        """
        if not conditions:
            return None
            
        expressions = []
        for condition_dict in conditions:
            if not isinstance(condition_dict, dict):
                self.logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="INVALID_OR_CONDITION",
                    details=f"OR condition items must be dictionaries: {condition_dict}",
                    location="_process_or_condition()"
                ))
                continue
                
            subconditions = []
            for field_name, condition in condition_dict.items():
                expr = self._process_field_condition(model_class, field_name, condition)
                if expr is not None:
                    subconditions.append(expr)
                    
            if subconditions:
                # Combine subconditions with AND
                expressions.append(and_(*subconditions) if len(subconditions) > 1 else subconditions[0])
        
        # Combine expressions with OR
        return or_(*expressions) if expressions else None
    
    def _process_and_condition(self, model_class: Type[ModelType], conditions: List[Dict[str, Any]]) -> Optional[BinaryExpression]:
        """
        Process an AND condition with multiple subconditions.
        
        Args:
            model_class: SQLAlchemy model class
            conditions: List of condition dictionaries to AND together
            
        Returns:
            SQLAlchemy AND expression or None if invalid
        """
        if not conditions:
            return None
            
        expressions = []
        for condition_dict in conditions:
            if not isinstance(condition_dict, dict):
                self.logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="INVALID_AND_CONDITION",
                    details=f"AND condition items must be dictionaries: {condition_dict}",
                    location="_process_and_condition()"
                ))
                continue
                
            subconditions = []
            for field_name, condition in condition_dict.items():
                expr = self._process_field_condition(model_class, field_name, condition)
                if expr is not None:
                    subconditions.append(expr)
                    
            if subconditions:
                # Combine subconditions with AND
                expressions.append(and_(*subconditions) if len(subconditions) > 1 else subconditions[0])
        
        # Combine expressions with AND
        return and_(*expressions) if expressions else None
    
    # Comparison operator handlers
    
    def _op_eq(self, field: ColumnElement, value: Any) -> BinaryExpression:
        """Equal operator."""
        return field == value
    
    def _op_ne(self, field: ColumnElement, value: Any) -> BinaryExpression:
        """Not equal operator."""
        return field != value
    
    def _op_gt(self, field: ColumnElement, value: Any) -> BinaryExpression:
        """Greater than operator."""
        return field > value
    
    def _op_lt(self, field: ColumnElement, value: Any) -> BinaryExpression:
        """Less than operator."""
        return field < value
    
    def _op_gte(self, field: ColumnElement, value: Any) -> BinaryExpression:
        """Greater than or equal operator."""
        return field >= value
    
    def _op_lte(self, field: ColumnElement, value: Any) -> BinaryExpression:
        """Less than or equal operator."""
        return field <= value
    
    # Collection operator handlers
    
    def _op_in(self, field: ColumnElement, value: List[Any]) -> Optional[BinaryExpression]:
        """In operator."""
        if not isinstance(value, (list, tuple)):
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_IN_VALUE",
                details=f"Invalid value for 'in' operator: {value}",
                location="_op_in()"
            ))
            return None
        return field.in_(value)
    
    def _op_not_in(self, field: ColumnElement, value: List[Any]) -> Optional[BinaryExpression]:
        """Not in operator."""
        if not isinstance(value, (list, tuple)):
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_NOT_IN_VALUE",
                details=f"Invalid value for 'not_in' operator: {value}",
                location="_op_not_in()"
            ))
            return None
        return ~field.in_(value)
    
    # Range operator handlers
    
    def _op_between(self, field: ColumnElement, value: List[Any]) -> Optional[BinaryExpression]:
        """Between operator."""
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_BETWEEN_VALUE",
                details=f"Invalid value for 'between' operator: {value}",
                location="_op_between()"
            ))
            return None
        
        min_val, max_val = value
        return field.between(min_val, max_val)
    
    def _op_not_between(self, field: ColumnElement, value: List[Any]) -> Optional[BinaryExpression]:
        """Not between operator."""
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_NOT_BETWEEN_VALUE",
                details=f"Invalid value for 'not_between' operator: {value}",
                location="_op_not_between()"
            ))
            return None
        
        min_val, max_val = value
        return ~field.between(min_val, max_val)
    
    # Text search operator handlers
    
    def _op_like(self, field: ColumnElement, value: str) -> Optional[BinaryExpression]:
        """Like operator."""
        if not isinstance(value, str):
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_LIKE_VALUE",
                details=f"Invalid value for 'like' operator: {value}",
                location="_op_like()"
            ))
            return None
        return field.like(value)
    
    def _op_not_like(self, field: ColumnElement, value: str) -> Optional[BinaryExpression]:
        """Not like operator."""
        if not isinstance(value, str):
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_NOT_LIKE_VALUE",
                details=f"Invalid value for 'not_like' operator: {value}",
                location="_op_not_like()"
            ))
            return None
        return ~field.like(value)
    
    def _op_ilike(self, field: ColumnElement, value: str) -> Optional[BinaryExpression]:
        """Case-insensitive like operator."""
        if not isinstance(value, str):
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_ILIKE_VALUE",
                details=f"Invalid value for 'ilike' operator: {value}",
                location="_op_ilike()"
            ))
            return None
        
        # Check if the field has the ilike method
        if hasattr(field, 'ilike'):
            return field.ilike(value)
        else:
            # Fallback for SQLite which doesn't have ilike
            return field.like(f"%{value}%")
    
    def _op_not_ilike(self, field: ColumnElement, value: str) -> Optional[BinaryExpression]:
        """Case-insensitive not like operator."""
        if not isinstance(value, str):
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_NOT_ILIKE_VALUE",
                details=f"Invalid value for 'not_ilike' operator: {value}",
                location="_op_not_ilike()"
            ))
            return None
            
        # Check if the field has the ilike method
        if hasattr(field, 'ilike'):
            return ~field.ilike(value)
        else:
            # Fallback for SQLite which doesn't have ilike
            return ~field.like(f"%{value}%")
    
    # Null checking operator handlers
    
    def _op_is_null(self, field: ColumnElement, value: bool) -> BinaryExpression:
        """Is null operator."""
        if value:
            return field.is_(None)
        return field.isnot(None)
    
    def _op_not_null(self, field: ColumnElement, value: bool) -> BinaryExpression:
        """Not null operator."""
        if value:
            return field.isnot(None)
        return field.is_(None)
