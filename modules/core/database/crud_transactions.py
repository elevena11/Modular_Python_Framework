"""
modules/core/database/crud_transactions.py
Updated: April 4, 2025
Transaction management for CRUD operations with standardized error handling
"""

import logging
import contextlib
from typing import Dict, Any, List, Type, Optional, TypeVar, Callable, Union, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

# Import error handling utilities
from core.error_utils import error_message, Result

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType")

# Component ID for consistent error codes
COMPONENT_ID = "core.database.crud"

class Transaction:
    """
    Class representing an active database transaction.
    Provides transaction-bound CRUD operations that return Result objects.
    """
    
    def __init__(self, session: AsyncSession, operations):
        """
        Initialize a transaction.
        
        Args:
            session: SQLAlchemy async session
            operations: CRUDOperations instance for delegating operations
        """
        self.session = session
        self._operations = operations
        self.logger = logging.getLogger(f"{COMPONENT_ID}.transaction")
    
    async def create(self, model_class: Type[ModelType], obj_data: Dict[str, Any],
                    params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Create a new database record within the transaction.
        
        Args:
            model_class: SQLAlchemy model class
            obj_data: Data for the new record
            
        Returns:
            Result object with created object or error information
        """

        try:
            # Create record using operations
            obj = await self._operations.create(self.session, model_class, obj_data)
            
            if obj is None:
                return Result.error(
                    code="TRANSACTION_CREATE_FAILED",
                    message=f"Failed to create {model_class.__name__} in transaction",
                    details={"obj_data": obj_data}
                )
            
            return Result.success(data=obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TRANSACTION_CREATE_ERROR",
                details=f"Error creating {model_class.__name__} in transaction: {str(e)}",
                location="create()"
            ))
            
            return Result.error(
                code="TRANSACTION_CREATE_ERROR",
                message=f"Error creating {model_class.__name__} in transaction",
                details={"error": str(e), "obj_data": obj_data}
            )
    
    async def read(self, model_class: Type[ModelType], id: Any,
                 columns: Optional[List[str]] = None,
                 as_dict: bool = False,
                 params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Read a single record by ID within the transaction.
        
        Args:
            model_class: SQLAlchemy model class
            id: Record ID
            columns: Specific columns to retrieve (None for all)
            as_dict: Whether to return result as dictionary
            
        Returns:
            Result object with found object or error information
        """

        try:
            # Read record using operations
            obj = await self._operations.read(self.session, model_class, id, columns, as_dict)
            
            if obj is None:
                return Result.error(
                    code="TRANSACTION_RECORD_NOT_FOUND",
                    message=f"{model_class.__name__} with ID {id} not found in transaction",
                    details={"id": id, "model": model_class.__name__}
                )
            
            return Result.success(data=obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TRANSACTION_READ_ERROR",
                details=f"Error reading {model_class.__name__} with ID {id} in transaction: {str(e)}",
                location="read()"
            ))
            
            return Result.error(
                code="TRANSACTION_READ_ERROR",
                message=f"Error reading {model_class.__name__} with ID {id} in transaction",
                details={"error": str(e), "id": id}
            )
    
    async def read_many(self, model_class: Type[ModelType],
                      filters: Optional[Dict[str, Any]] = None,
                      skip: int = 0, limit: int = 100,
                      order_by: Optional[List[str]] = None,
                      columns: Optional[List[str]] = None,
                      as_dict: bool = False,
                      params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Read multiple records with filtering, pagination and sorting within the transaction.
        
        Args:
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters or operator-based filters
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field(s) to order by (list of strings)
            columns: Specific columns to retrieve (None for all)
            as_dict: Whether to return results as dictionaries
            
        Returns:
            Result object with list of matching objects or error information
        """

        try:
            # Read records using operations
            results = await self._operations.read_many(
                self.session, model_class, filters, skip, limit, order_by, columns, as_dict
            )
            
            return Result.success(data=results)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TRANSACTION_READ_MANY_ERROR",
                details=f"Error reading multiple {model_class.__name__} records in transaction: {str(e)}",
                location="read_many()"
            ))
            
            return Result.error(
                code="TRANSACTION_READ_MANY_ERROR",
                message=f"Error reading multiple {model_class.__name__} records in transaction",
                details={"error": str(e), "filters": filters}
            )
    
    async def update(self, model_class: Type[ModelType],
                   id: Any, obj_data: Dict[str, Any],
                   params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Update an existing record within the transaction.
        
        Args:
            model_class: SQLAlchemy model class
            id: Record ID
            obj_data: Updated data
            
        Returns:
            Result object with updated object or error information
        """

        try:
            # Update record using operations
            updated_obj = await self._operations.update(self.session, model_class, id, obj_data)
            
            if updated_obj is None:
                return Result.error(
                    code="TRANSACTION_RECORD_NOT_FOUND",
                    message=f"{model_class.__name__} with ID {id} not found for update in transaction",
                    details={"id": id, "model": model_class.__name__}
                )
            
            return Result.success(data=updated_obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TRANSACTION_UPDATE_ERROR",
                details=f"Error updating {model_class.__name__} with ID {id} in transaction: {str(e)}",
                location="update()"
            ))
            
            return Result.error(
                code="TRANSACTION_UPDATE_ERROR",
                message=f"Error updating {model_class.__name__} with ID {id} in transaction",
                details={"error": str(e), "id": id}
            )
    
    async def delete(self, model_class: Type[ModelType], id: Any,
                    params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Delete a record by ID within the transaction.
        
        Args:
            model_class: SQLAlchemy model class
            id: Record ID
            
        Returns:
            Result object with success status or error information
        """

        try:
            # Delete record using operations
            success = await self._operations.delete(self.session, model_class, id)
            
            if not success:
                return Result.error(
                    code="TRANSACTION_DELETE_FAILED",
                    message=f"Failed to delete {model_class.__name__} with ID {id} in transaction",
                    details={"id": id, "model": model_class.__name__}
                )
            
            return Result.success(data={"deleted": True, "id": id})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TRANSACTION_DELETE_ERROR",
                details=f"Error deleting {model_class.__name__} with ID {id} in transaction: {str(e)}",
                location="delete()"
            ))
            
            return Result.error(
                code="TRANSACTION_DELETE_ERROR",
                message=f"Error deleting {model_class.__name__} with ID {id} in transaction",
                details={"error": str(e), "id": id}
            )
    
    async def bulk_create(self, model_class: Type[ModelType],
                        objects_data: List[Dict[str, Any]],
                        params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Create multiple records in the transaction.
        
        Args:
            model_class: SQLAlchemy model class
            objects_data: List of data dictionaries for the new records
            
        Returns:
            Result object with list of created objects or error information
        """

        try:
            # Create records using operations
            created_objects = await self._operations.bulk_create(self.session, model_class, objects_data)
            
            if not created_objects:
                return Result.error(
                    code="TRANSACTION_BULK_CREATE_FAILED",
                    message=f"Failed to bulk create {model_class.__name__} records in transaction",
                    details={"count": len(objects_data)}
                )
            
            return Result.success(data=created_objects)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TRANSACTION_BULK_CREATE_ERROR",
                details=f"Error in bulk_create for {model_class.__name__} in transaction: {str(e)}",
                location="bulk_create()"
            ))
            
            return Result.error(
                code="TRANSACTION_BULK_CREATE_ERROR",
                message=f"Error in bulk_create for {model_class.__name__} in transaction",
                details={"error": str(e), "count": len(objects_data)}
            )
    
    async def count(self, model_class: Type[ModelType],
                  filters: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Count records with optional filtering within the transaction.
        
        Args:
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters or operator-based filters
            
        Returns:
            Result object with count or error information
        """

        try:
            # Count records using operations
            count = await self._operations.count(self.session, model_class, filters)
            
            return Result.success(data=count)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TRANSACTION_COUNT_ERROR",
                details=f"Error counting {model_class.__name__} records in transaction: {str(e)}",
                location="count()"
            ))
            
            return Result.error(
                code="TRANSACTION_COUNT_ERROR",
                message=f"Error counting {model_class.__name__} records in transaction",
                details={"error": str(e), "filters": filters}
            )
    
    async def get_by_field(self, model_class: Type[ModelType],
                          field: str, value: Any,
                          params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Get a record by a specific field value within the transaction.
        
        Args:
            model_class: SQLAlchemy model class
            field: Field name
            value: Field value
            
        Returns:
            Result object with found object or error information
        """

        try:
            # Get record by field using operations
            obj = await self._operations.get_by_field(self.session, model_class, field, value)
            
            if obj is None:

                return Result.error(
                    code="TRANSACTION_RECORD_NOT_FOUND_BY_FIELD",
                    message=f"{model_class.__name__} with {field}={value} not found in transaction",
                    details={"field": field, "value": value, "model": model_class.__name__}
                )
            
            return Result.success(data=obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="TRANSACTION_GET_BY_FIELD_ERROR",
                details=f"Error getting {model_class.__name__} by {field}={value} in transaction: {str(e)}",
                location="get_by_field()"
            ))
            
            return Result.error(
                code="TRANSACTION_GET_BY_FIELD_ERROR",
                message=f"Error getting {model_class.__name__} by {field}={value} in transaction",
                details={"error": str(e), "field": field, "value": value}
            )


class TransactionContext:
    """Context manager for database transactions."""
    
    def __init__(self, session: AsyncSession, manager):
        """
        Initialize the transaction context.
        
        Args:
            session: SQLAlchemy async session
            manager: TransactionManager instance
        """
        self.session = session
        self.manager = manager
        self.logger = logging.getLogger(f"{COMPONENT_ID}.transaction")
    
    async def __aenter__(self) -> Transaction:
        """
        Enter the transaction context.
        
        Returns:
            Transaction object for transaction-bound operations
        """
        # Begin transaction (SQLAlchemy session is already in "begin" state by default)
        self.logger.debug("Entering transaction context")
        return Transaction(self.session, self.manager._operations)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the transaction context.
        Commit if no exception, rollback if exception occurred.
        
        Args:
            exc_type: Exception type, if any
            exc_val: Exception value, if any
            exc_tb: Exception traceback, if any
            
        Returns:
            False to propagate exceptions
        """
        if exc_type is not None:
            # Exception occurred, rollback
            self.logger.debug(f"Rolling back transaction due to exception: {exc_val}")
            await self.session.rollback()
        else:
            # No exception, commit
            self.logger.debug("Committing transaction")
            await self.session.commit()
            
        # Return False to propagate exceptions (if any)
        return False


class TransactionManager:
    """Manager for database transactions."""
    
    def __init__(self, app_context, operations):
        """
        Initialize the transaction manager.
        
        Args:
            app_context: Application context
            operations: CRUDOperations instance for delegating operations
        """
        self.app_context = app_context
        self._operations = operations
        self.logger = logging.getLogger(f"{COMPONENT_ID}.transaction")
    
    async def initialize(self, app_context=None, settings=None):
        """
        Initialize the transaction manager.
        
        Args:
            app_context: Optional application context
            settings: Optional pre-loaded settings
            
        Returns:
            bool: True if initialization successful
        """
        # No complex initialization needed for now, but method included for consistency
        return True
    
    def transaction(self, session: AsyncSession):
        """
        Create a transaction context manager for grouping operations.
        
        Args:
            session: SQLAlchemy async session
            
        Returns:
            TransactionContext object
            
        Example:
            ```python
            async def process_order(self, order_data):
                async def _operation():
                    async with self._db_session() as session:
                        # Start transaction that either completes fully or rolls back
                        async with self.crud_service.transaction(session) as tx:
                            # Create order
                            result = await tx.create(Order, order_data)
                            if not result.success:
                                return result
                            order = result.data
                            
                            # Create order items
                            for item in order_data["items"]:
                                item_data = {...}  # Prepare item data with order.id
                                result = await tx.create(OrderItem, item_data)
                                if not result.success:
                                    return result
                            
                            return Result.success(data={"order_id": order.id})
                
                return await self._db_op(_operation)
            ```
        """
        return TransactionContext(session, self)
    
    async def shutdown(self):
        """
        Graceful async shutdown when event loop is available.
        """
        self.logger.info(f"Shutting down {COMPONENT_ID} transaction manager")
        
        # No resources to clean up currently, but method is included for consistency
        
        self.logger.info(f"{COMPONENT_ID} transaction manager shutdown complete")
        
    def force_shutdown(self):
        """
        Forced synchronous shutdown when event loop is closed.
        """
        self.logger.info(f"Force shutting down {COMPONENT_ID} transaction manager")
        
        # No resources to clean up currently, but method is included for consistency
        
        self.logger.info(f"{COMPONENT_ID} transaction manager force shutdown complete")
