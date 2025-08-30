"""
modules/core/database/crud.py
Updated: April 4, 2025
Generic CRUD operations for database models with enhanced filtering capabilities and standardized error handling
"""

import logging
import random
import asyncio
from typing import Dict, List, Any, Optional, Type, Union, TypeVar, Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

# Import components
from .crud_filters import FilterParser
from .crud_operations import CRUDOperations
from .crud_transactions import TransactionManager
from .crud_utils import ModelUtils

# Import utilities for error handling
from core.error_utils import Result, error_message

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType")

# Component ID for consistent error codes
COMPONENT_ID = "core.database.crud"

class CRUDService:
    """
    Generic CRUD operations service with enhanced filtering, transaction management,
    and result customization.
    """
    
    def __init__(self, app_context):
        """Initialize the CRUD service."""
        self.app_context = app_context
        self.logger = logging.getLogger(COMPONENT_ID)
        self.initialized = False
        
        # SQLite retry configuration
        self.max_retries = 5
        self.retry_delay_base = 0.1  # Base delay in seconds
        self.retry_delay_max = 2.0   # Maximum delay in seconds
        
        # Initialize dependency references (for lazy loading)
        self._model_utils = None
        self._filter_parser = None
        self._operations = None
        self._tx_manager = None
        
        self.logger.info(f"{COMPONENT_ID} service created (pre-Phase 2)")
    
    @property
    def model_utils(self):
        """Lazy load model utilities."""
        if self._model_utils is None:
            self._model_utils = ModelUtils()
        return self._model_utils
    
    @property
    def filter_parser(self):
        """Lazy load filter parser."""
        if self._filter_parser is None:
            self._filter_parser = FilterParser()
        return self._filter_parser
    
    @property
    def operations(self):
        """Lazy load CRUD operations."""
        if self._operations is None:
            self._operations = CRUDOperations(self.app_context, self.filter_parser, self.model_utils)
        return self._operations
    
    @property
    def tx_manager(self):
        """Lazy load transaction manager."""
        if self._tx_manager is None:
            self._tx_manager = TransactionManager(self.app_context, self.operations)
        return self._tx_manager
    
    async def initialize(self, app_context=None, settings=None):
        """
        Phase 2 initialization - Load settings and set up complex database state.
        
        Args:
            app_context: Optional application context
            settings: Optional pre-loaded settings
            
        Returns:
            bool: True if initialization successful
        """
        # Skip if already initialized
        if self.initialized:
            return True
        
        self.logger.info(f"Initializing {COMPONENT_ID} service")
        
        try:
            # Load or use provided settings
            if settings:
                self.config = settings
            else:
                # Load settings from app_context
                context = app_context or self.app_context
                self.config = await context.get_module_settings("core.database")
            
            # Apply settings if available
            if self.config:
                self.max_retries = self.config.get("max_retries", self.max_retries)
                self.retry_delay_base = self.config.get("retry_delay_base", self.retry_delay_base)
                self.retry_delay_max = self.config.get("retry_delay_max", self.retry_delay_max)
            
            # Initialize components that need it
            if self._operations:
                await self._operations.initialize(app_context=self.app_context)
            
            # Mark as initialized
            self.initialized = True
            self.logger.info(f"{COMPONENT_ID} service initialized")
            return True
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="INIT_ERROR",
                details=f"Error during initialization: {str(e)}",
                location="initialize()"
            ))
            return False
    
    async def shutdown(self):
        """
        Graceful async shutdown when event loop is available.
        Called during normal application shutdown.
        """
        self.logger.info(f"{COMPONENT_ID}: Shutting down service gracefully...")
        
        # Close any resources that need closing
        if self._operations and hasattr(self._operations, "shutdown"):
            await self._operations.shutdown()
        
        self.logger.info(f"{COMPONENT_ID}: Service shutdown complete")
    
    def force_shutdown(self):
        """
        Forced synchronous shutdown when event loop is closed.
        Called as fallback during application shutdown.
        """
        self.logger.info(f"{COMPONENT_ID}: Force shutting down service...")
        
        # Close any resources that need forceful closing
        if self._operations and hasattr(self._operations, "force_shutdown"):
            self._operations.force_shutdown()
        
        self.logger.info(f"{COMPONENT_ID}: Service force shutdown complete")
    
    # Basic CRUD operations
    
    async def create(self, db: AsyncSession, model_class: Type[ModelType], 
                    obj_data: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Create a new database record.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            obj_data: Data for the new record
            
        Returns:
            Result object with created object or error information
            
        Example:
            ```python
            result = await crud_service.create(session, User, {"name": "John", "email": "john@example.com"})
            if result.success:
                user = result.data
                print(f"Created user: {user.id}")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )
          
        try:
            # Create the record
            created_obj = await self.operations.create(db, model_class, obj_data)
            
            if created_obj is None:
                
                return Result.error(
                    code="CREATE_FAILED",
                    message=f"Failed to create {model_class.__name__}",
                    details={"obj_data": obj_data}
                )
            
            return Result.success(data=created_obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="CREATE_ERROR",
                details=f"Error creating {model_class.__name__}: {str(e)}",
                location="create()"
            ))
            
            return Result.error(
                code="CREATE_ERROR",
                message=f"Error creating {model_class.__name__}",
                details={"error": str(e), "obj_data": obj_data}
            )
    
    async def read(self, db: AsyncSession, model_class: Type[ModelType], id: Any,
                  columns: Optional[List[str]] = None, as_dict: bool = False,
                  params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Read a single record by ID.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            id: Record ID
            columns: Specific columns to retrieve (None for all)
            as_dict: Whether to return result as dictionary
            
        Returns:
            Result object with found object or error information
            
        Examples:
            ```python
            # Get full model
            result = await crud_service.read(session, User, 1)
            if result.success:
                user = result.data
                print(f"User: {user.name}")
            
            # Get specific columns
            result = await crud_service.read(session, User, 1, columns=["id", "name"])
            
            # Get as dictionary
            result = await crud_service.read(session, User, 1, as_dict=True)
            if result.success:
                user_dict = result.data
                print(f"User: {user_dict['name']}")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )
        
        try:
            # Read the record
            obj = await self.operations.read(db, model_class, id, columns, as_dict)
            
            if obj is None:
                return Result.error(
                    code="RECORD_NOT_FOUND",
                    message=f"{model_class.__name__} with ID {id} not found",
                    details={"id": id, "model": model_class.__name__}
                )
            
            return Result.success(data=obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="READ_ERROR",
                details=f"Error reading {model_class.__name__} with ID {id}: {str(e)}",
                location="read()"
            ))
            
            return Result.error(
                code="READ_ERROR",
                message=f"Error reading {model_class.__name__} with ID {id}",
                details={"error": str(e), "id": id}
            )
    
    async def read_many(self, db: AsyncSession, model_class: Type[ModelType], 
                      filters: Optional[Dict[str, Any]] = None,
                      skip: int = 0, limit: int = 100,
                      order_by: Optional[List[str]] = None,
                      columns: Optional[List[str]] = None,
                      as_dict: bool = False,
                      params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Read multiple records with filtering, pagination and sorting.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters or operator-based filters
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field(s) to order by (list of strings, prefix with "-" for descending)
            columns: Specific columns to retrieve (None for all)
            as_dict: Whether to return results as dictionaries
            
        Returns:
            Result object with list of matching objects or error information
            
        Examples:
            ```python
            # Simple equality filter
            result = await crud_service.read_many(session, User, {"is_active": True})
            
            # Operator-based filter
            result = await crud_service.read_many(session, User, {
                "age": {"gte": 18}
            })
            
            # Date range with between operator
            result = await crud_service.read_many(session, Task, {
                "due_date": {"between": [start_date, end_date]}
            })
            
            # Multiple conditions
            result = await crud_service.read_many(session, Product, {
                "category": "electronics",
                "price": {"lte": 500},
                "stock": {"gt": 0}
            })
            
            # Collection membership
            result = await crud_service.read_many(session, Order, {
                "status": {"in": ["pending", "processing"]}
            })
            
            # With specific columns and as dictionaries
            result = await crud_service.read_many(
                session, User, 
                {"is_active": True},
                columns=["id", "name", "email"],
                as_dict=True
            )
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )
        
        
        filter_info = None
        if filters:
            # Convert filters to a simpler format for tracing
            try:
                filter_info = {k: str(v) for k, v in filters.items()}
            except:
                filter_info = str(filters)

        try:
            # Read the records
            results = await self.operations.read_many(
                db, model_class, filters, skip, limit, order_by, columns, as_dict
            )
            
            return Result.success(data=results)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="READ_MANY_ERROR",
                details=f"Error reading multiple {model_class.__name__} records: {str(e)}",
                location="read_many()"
            ))
            
            return Result.error(
                code="READ_MANY_ERROR",
                message=f"Error reading multiple {model_class.__name__} records",
                details={"error": str(e), "filters": filters}
            )
    
    async def update(self, db: AsyncSession, model_class: Type[ModelType], 
                   id: Any, obj_data: Dict[str, Any],
                   params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Update an existing record.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            id: Record ID
            obj_data: Updated data
            
        Returns:
            Result object with updated object or error information
            
        Example:
            ```python
            result = await crud_service.update(session, User, 1, {"name": "New Name"})
            if result.success:
                updated_user = result.data
                print(f"Updated user: {updated_user.name}")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )
   
        try:
            # Update the record
            updated_obj = await self.operations.update(db, model_class, id, obj_data)
            
            if updated_obj is None:
                return Result.error(
                    code="RECORD_NOT_FOUND",
                    message=f"{model_class.__name__} with ID {id} not found for update",
                    details={"id": id, "model": model_class.__name__}
                )
            
            return Result.success(data=updated_obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPDATE_ERROR",
                details=f"Error updating {model_class.__name__} with ID {id}: {str(e)}",
                location="update()"
            ))
            
            return Result.error(
                code="UPDATE_ERROR",
                message=f"Error updating {model_class.__name__} with ID {id}",
                details={"error": str(e), "id": id}
            )
    
    async def delete(self, db: AsyncSession, model_class: Type[ModelType], id: Any,
                    params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Delete a record by ID.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            id: Record ID
            
        Returns:
            Result object with success status or error information
            
        Example:
            ```python
            result = await crud_service.delete(session, User, 1)
            if result.success:
                print("User deleted successfully")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )

        try:
            # Delete the record
            success = await self.operations.delete(db, model_class, id)
            
            if not success:
                return Result.error(
                    code="DELETE_FAILED",
                    message=f"Failed to delete {model_class.__name__} with ID {id}",
                    details={"id": id, "model": model_class.__name__}
                )
            
            return Result.success(data={"deleted": True, "id": id})
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DELETE_ERROR",
                details=f"Error deleting {model_class.__name__} with ID {id}: {str(e)}",
                location="delete()"
            ))
            
            return Result.error(
                code="DELETE_ERROR",
                message=f"Error deleting {model_class.__name__} with ID {id}",
                details={"error": str(e), "id": id}
            )
    
    # Additional operations
    
    async def count(self, db: AsyncSession, model_class: Type[ModelType], 
                  filters: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Count records with optional filtering.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters or operator-based filters
            
        Returns:
            Result object with count or error information
            
        Examples:
            ```python
            # Count all active users
            result = await crud_service.count(session, User, {"is_active": True})
            if result.success:
                active_count = result.data
                print(f"Active users: {active_count}")
            
            # Count with operator-based filters
            result = await crud_service.count(session, Order, {
                "status": "new",
                "created_at": {"gte": yesterday}
            })
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )
        try:
            # Count the records
            count = await self.operations.count(db, model_class, filters)
            
            return Result.success(data=count)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="COUNT_ERROR",
                details=f"Error counting {model_class.__name__} records: {str(e)}",
                location="count()"
            ))
            
            return Result.error(
                code="COUNT_ERROR",
                message=f"Error counting {model_class.__name__} records",
                details={"error": str(e), "filters": filters}
            )
    
    async def exists(self, db: AsyncSession, model_class: Type[ModelType], id: Any,
                    params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Check if a record exists by ID.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            id: Record ID
            
        Returns:
            Result object with existence boolean or error information
            
        Example:
            ```python
            result = await crud_service.exists(session, User, 1)
            if result.success:
                exists = result.data
                print(f"User exists: {exists}")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )
        try:
            # Check if the record exists
            exists = await self.operations.exists(db, model_class, id)
            
            return Result.success(data=exists)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="EXISTS_ERROR",
                details=f"Error checking existence of {model_class.__name__} with ID {id}: {str(e)}",
                location="exists()"
            ))
            
            return Result.error(
                code="EXISTS_ERROR",
                message=f"Error checking existence of {model_class.__name__} with ID {id}",
                details={"error": str(e), "id": id}
            )
    
    async def get_by_field(self, db: AsyncSession, model_class: Type[ModelType], 
                          field: str, value: Any,
                          params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Get a record by a specific field value.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            field: Field name
            value: Field value
            
        Returns:
            Result object with found object or error information
            
        Example:
            ```python
            result = await crud_service.get_by_field(session, User, "email", "user@example.com")
            if result.success:
                user = result.data
                print(f"Found user: {user.name}")
            else:
                print(f"Error: {result.error['message']}")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )

        try:
            # Get the record by field
            obj = await self.operations.get_by_field(db, model_class, field, value)
            
            if obj is None:
                return Result.error(
                    code="RECORD_NOT_FOUND_BY_FIELD",
                    message=f"{model_class.__name__} with {field}={value} not found",
                    details={"field": field, "value": value, "model": model_class.__name__}
                )
            
            return Result.success(data=obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_BY_FIELD_ERROR",
                details=f"Error getting {model_class.__name__} by {field}={value}: {str(e)}",
                location="get_by_field()"
            ))
            
            return Result.error(
                code="GET_BY_FIELD_ERROR",
                message=f"Error getting {model_class.__name__} by {field}={value}",
                details={"error": str(e), "field": field, "value": value}
            )
    
    async def create_or_update(self, db: AsyncSession, model_class: Type[ModelType], 
                              unique_field: str, obj_data: Dict[str, Any],
                              params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Create a record if it doesn't exist, or update it if it does.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            unique_field: Field to check for existence
            obj_data: Data for the new or updated record
            
        Returns:
            Result object with created or updated object or error information
            
        Example:
            ```python
            result = await crud_service.create_or_update(
                session, User, "email", 
                {"email": "user@example.com", "name": "User Name"}
            )
            if result.success:
                user = result.data
                print(f"User {'created' if user.id is None else 'updated'}: {user.name}")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )
        
        
        # Verify unique field is in obj_data
        if unique_field not in obj_data:
            return Result.error(
                code="MISSING_UNIQUE_FIELD",
                message=f"Unique field '{unique_field}' not found in data",
                details={"unique_field": unique_field, "available_fields": list(obj_data.keys())}
            )
        
        try:
            # Create or update the record
            obj = await self.operations.create_or_update(db, model_class, unique_field, obj_data)
            
            if obj is None:
                return Result.error(
                    code="CREATE_OR_UPDATE_FAILED",
                    message=f"Failed to create or update {model_class.__name__}",
                    details={"unique_field": unique_field, "unique_value": obj_data.get(unique_field)}
                )
            
            return Result.success(data=obj)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="CREATE_OR_UPDATE_ERROR",
                details=f"Error in create_or_update for {model_class.__name__}: {str(e)}",
                location="create_or_update()"
            ))
            
            return Result.error(
                code="CREATE_OR_UPDATE_ERROR",
                message=f"Error in create_or_update for {model_class.__name__}",
                details={
                    "error": str(e),
                    "unique_field": unique_field,
                    "unique_value": obj_data.get(unique_field)
                }
            )
    
    # Batch operations
    
    async def bulk_create(self, db: AsyncSession, model_class: Type[ModelType], 
                         objects_data: List[Dict[str, Any]],
                         params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Create multiple records in a single transaction.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            objects_data: List of data dictionaries for the new records
            
        Returns:
            Result object with list of created objects or error information
            
        Example:
            ```python
            result = await crud_service.bulk_create(session, User, [
                {"name": "User 1", "email": "user1@example.com"},
                {"name": "User 2", "email": "user2@example.com"}
            ])
            if result.success:
                users = result.data
                print(f"Created {len(users)} users")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )

        try:
            # Bulk create the records
            created_objects = await self.operations.bulk_create(db, model_class, objects_data)
            
            if not created_objects:
                return Result.error(
                    code="BULK_CREATE_FAILED",
                    message=f"Failed to bulk create {model_class.__name__} records",
                    details={"count": len(objects_data)}
                )
            
            return Result.success(data=created_objects)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_CREATE_ERROR",
                details=f"Error in bulk_create for {model_class.__name__}: {str(e)}",
                location="bulk_create()"
            ))
            
            return Result.error(
                code="BULK_CREATE_ERROR",
                message=f"Error in bulk_create for {model_class.__name__}",
                details={"error": str(e), "count": len(objects_data)}
            )
    
    async def bulk_update(self, db: AsyncSession, model_class: Type[ModelType],
                         ids: List[Any], obj_data: Dict[str, Any],
                         params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Update multiple records with the same changes.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            ids: List of record IDs to update
            obj_data: Data to update for all records
            
        Returns:
            Result object with number of records updated or error information
            
        Example:
            ```python
            result = await crud_service.bulk_update(
                session, User, [1, 2, 3], {"is_active": False}
            )
            if result.success:
                updated_count = result.data
                print(f"Updated {updated_count} users")
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )

        try:
            # Bulk update the records
            updated_count = await self.operations.bulk_update(db, model_class, ids, obj_data)
            
            return Result.success(data=updated_count)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_UPDATE_ERROR",
                details=f"Error in bulk_update for {model_class.__name__}: {str(e)}",
                location="bulk_update()"
            ))
            
            return Result.error(
                code="BULK_UPDATE_ERROR",
                message=f"Error in bulk_update for {model_class.__name__}",
                details={"error": str(e), "ids_count": len(ids)}
            )
    
    async def bulk_delete(self, db: AsyncSession, model_class: Type[ModelType], 
                        filters: Dict[str, Any],
                        params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Delete multiple records matching filters in a single transaction.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters or operator-based filters
            
        Returns:
            Result object with number of deleted records or error information
            
        Examples:
            ```python
            # Delete all inactive users
            result = await crud_service.bulk_delete(session, User, {"is_active": False})
            if result.success:
                deleted_count = result.data
                print(f"Deleted {deleted_count} users")
            
            # Delete with operator-based filters
            result = await crud_service.bulk_delete(session, Task, {
                "status": "completed",
                "completed_at": {"lt": last_month}
            })
            ```
        """
        # Check initialization
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message=f"{COMPONENT_ID} service not initialized"
            )

        try:
            # Bulk delete the records
            deleted_count = await self.operations.bulk_delete(db, model_class, filters)
            
            return Result.success(data=deleted_count)
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_DELETE_ERROR",
                details=f"Error in bulk_delete for {model_class.__name__}: {str(e)}",
                location="bulk_delete()"
            ))
            
            return Result.error(
                code="BULK_DELETE_ERROR",
                message=f"Error in bulk_delete for {model_class.__name__}",
                details={"error": str(e), "filters": filters}
            )
    
    # Transaction management
    
    def transaction(self, session: AsyncSession):
        """
        Create a transaction context manager for grouping operations.
        
        Args:
            session: SQLAlchemy async session
            
        Returns:
            Transaction context manager
            
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
        return self.tx_manager.transaction(session)
