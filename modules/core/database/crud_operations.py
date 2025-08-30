"""
modules/core/database/crud_operations.py
Updated: April 4, 2025
Core CRUD operation implementations with standardized error handling
"""

import logging
import random
import asyncio
from typing import Dict, Any, List, Type, Optional, TypeVar, Union, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy import select, delete, update, func, inspect, text

# Import error handling utilities
from core.error_utils import error_message, Result

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType")

# Component ID for consistent error codes
COMPONENT_ID = "core.database.crud"

class CRUDOperations:
    """Implementation of CRUD operations."""
    
    def __init__(self, app_context, filter_parser, model_utils):
        """
        Initialize CRUD operations.
        
        Args:
            app_context: Application context
            filter_parser: FilterParser instance for processing filters
            model_utils: ModelUtils instance for model-related operations
        """
        self.app_context = app_context
        self.filter_parser = filter_parser
        self.model_utils = model_utils
        self.logger = logging.getLogger(f"{COMPONENT_ID}.operations")
        self.initialized = False
        
        # SQLite retry configuration (from database service)
        self.max_retries = 5
        self.retry_delay_base = 0.1  # Base delay in seconds
        self.retry_delay_max = 2.0   # Maximum delay in seconds
    
    async def initialize(self, app_context=None, settings=None):
        """
        Initialize the CRUD operations with settings.
        
        Args:
            app_context: Optional application context
            settings: Optional pre-loaded settings
            
        Returns:
            bool: True if initialization successful
        """
        if self.initialized:
            return True
            
        self.logger.info(f"Initializing {COMPONENT_ID} operations")
        
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
            
            # Get database service
            self.db_service = self.app_context.get_service("core.database.service")
            if not self.db_service:
                self.logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="DB_SERVICE_UNAVAILABLE",
                    details="Database service not available - using direct retry logic",
                    location="initialize()"
                ))
            
            self.initialized = True
            self.logger.info(f"{COMPONENT_ID} operations initialized")
            return True
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="INIT_ERROR",
                details=f"Error during initialization: {str(e)}",
                location="initialize()"
            ))
            return False
    
    async def execute_with_retry(self, func: Callable[..., Awaitable], *args, **kwargs):
        """
        Execute a database function with retry logic for SQLite locking errors.
        
        Args:
            func: The async function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function
            
        Raises:
            The last encountered exception if all retries fail
        """
        # If database service is available, use its retry function
        if hasattr(self, 'db_service') and self.db_service and hasattr(self.db_service, 'execute_with_retry'):
            return await self.db_service.execute_with_retry(func(*args, **kwargs))
        
        # Fallback to direct execution with our own retry logic
        attempts = 0
        max_retries = self.max_retries
        delay_base = self.retry_delay_base
        last_error = None
        
        while attempts <= max_retries:
            try:
                return await func(*args, **kwargs)
            except OperationalError as e:
                # Check if this is a database locked error
                if "database is locked" in str(e).lower():
                    attempts += 1
                    if attempts > max_retries:
                        self.logger.error(error_message(
                            module_id=COMPONENT_ID,
                            error_type="MAX_RETRIES_EXCEEDED",
                            details=f"Max retries exceeded ({max_retries}) for database operation",
                            location="execute_with_retry()"
                        ))
                        raise
                    
                    # Calculate exponential backoff with jitter
                    delay = min(delay_base * (2 ** (attempts - 1)) * (0.5 + random.random()), 
                               self.retry_delay_max)
                    
                    self.logger.warning(f"Database locked, retrying in {delay:.2f}s (attempt {attempts}/{max_retries})")
                    await asyncio.sleep(delay)
                    last_error = e
                else:
                    # Re-raise if it's not a locking issue
                    raise
            except Exception as e:
                # Re-raise other exceptions immediately
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="OPERATION_ERROR",
                    details=f"Error executing database operation: {str(e)}",
                    location="execute_with_retry()"
                ))
                raise
        
        # We shouldn't get here, but just in case
        if last_error:
            raise last_error
    
    async def create(self, db: AsyncSession, model_class: Type[ModelType], 
                    obj_data: Dict[str, Any]) -> Optional[ModelType]:
        """
        Create a new database record.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            obj_data: Data for the new record
            
        Returns:
            Created object or None if operation failed
        """
        try:
            # Create new instance of the model
            db_obj = model_class(**obj_data)
            
            # Add to session
            db.add(db_obj)
            
            # Commit with retry logic
            async def _commit_and_refresh():
                await db.commit()
                await db.refresh(db_obj)
                return db_obj
                
            return await self.execute_with_retry(_commit_and_refresh)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="CREATE_ERROR",
                details=f"Error creating {model_class.__name__}: {str(e)}",
                location="create()"
            ))
            await db.rollback()
            return None
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="CREATE_UNEXPECTED_ERROR",
                details=f"Unexpected error creating {model_class.__name__}: {str(e)}",
                location="create()"
            ))
            await db.rollback()
            return None
    
    async def read(self, db: AsyncSession, model_class: Type[ModelType], id: Any,
                  columns: Optional[List[str]] = None, 
                  as_dict: bool = False) -> Optional[Union[ModelType, Dict[str, Any]]]:
        """
        Read a single record by ID.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            id: Record ID
            columns: Specific columns to retrieve (None for all)
            as_dict: Whether to return result as dictionary
            
        Returns:
            Found object, dictionary, or None if not found
        """
        try:
            # Get the primary key column
            primary_key = self.model_utils.get_primary_key(model_class)
            if not primary_key:
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="NO_PRIMARY_KEY",
                    details=f"Could not determine primary key for {model_class.__name__}",
                    location="read()"
                ))
                return None
                
            # Build query
            query = None
            if columns:
                # Select specific columns
                valid_columns = self.model_utils.validate_columns(model_class, columns)
                if not valid_columns:
                    self.logger.warning(error_message(
                        module_id=COMPONENT_ID,
                        error_type="INVALID_COLUMNS",
                        details=f"No valid columns specified for {model_class.__name__}",
                        location="read()"
                    ))
                    # Fall back to selecting all columns
                    query = select(model_class)
                else:
                    # Select specific columns
                    query = select(*[getattr(model_class, col) for col in valid_columns])
            else:
                # Select all columns
                query = select(model_class)
                
            # Add filter by primary key
            query = query.filter(getattr(model_class, primary_key) == id)
            
            # Execute query with retry logic
            async def _execute_query():
                result = await db.execute(query)
                if columns and len(columns) > 0:
                    # When selecting specific columns, result is a Row object
                    row = result.first()
                    if not row:
                        return None
                    
                    if as_dict:
                        # Convert Row to dict using column names
                        return {col: getattr(row, col) for col in valid_columns}
                    else:
                        return row
                else:
                    # When selecting whole model, result is a model instance
                    obj = result.scalars().first()
                    if not obj:
                        return None
                    
                    if as_dict:
                        return self.model_utils.to_dict(obj)
                    else:
                        return obj
                
            return await self.execute_with_retry(_execute_query)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="READ_ERROR",
                details=f"Error reading {model_class.__name__}: {str(e)}",
                location="read()"
            ))
            return None
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="READ_UNEXPECTED_ERROR",
                details=f"Unexpected error reading {model_class.__name__}: {str(e)}",
                location="read()"
            ))
            return None
    
    async def read_many(self, db: AsyncSession, model_class: Type[ModelType], 
                      filters: Optional[Dict[str, Any]] = None,
                      skip: int = 0, limit: int = 100,
                      order_by: Optional[List[str]] = None,
                      columns: Optional[List[str]] = None,
                      as_dict: bool = False) -> List[ModelType]:
        """
        Read multiple records with filtering, pagination and sorting.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters or operator-based filters
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field(s) to order by (list of strings)
            columns: Specific columns to retrieve (None for all)
            as_dict: Whether to return results as dictionaries
            
        Returns:
            List of matching objects or dictionaries
        """
        try:
            # Build query
            query = None
            if columns:
                # Select specific columns
                valid_columns = self.model_utils.validate_columns(model_class, columns)
                if not valid_columns:
                    self.logger.warning(error_message(
                        module_id=COMPONENT_ID,
                        error_type="INVALID_COLUMNS",
                        details=f"No valid columns specified for {model_class.__name__}",
                        location="read_many()"
                    ))
                    # Fall back to selecting all columns
                    query = select(model_class)
                else:
                    # Select specific columns
                    query = select(*[getattr(model_class, col) for col in valid_columns])
            else:
                # Select all columns
                query = select(model_class)
            
            # Apply filters if provided
            if filters:
                filter_expr = self.filter_parser.parse_filters(model_class, filters)
                if filter_expr is not None:
                    query = query.filter(filter_expr)
            
            # Apply ordering if provided
            if order_by:
                for field in order_by:
                    desc_order = field.startswith("-")
                    field_name = field[1:] if desc_order else field
                    
                    if hasattr(model_class, field_name):
                        order_field = getattr(model_class, field_name)
                        if desc_order:
                            query = query.order_by(order_field.desc())
                        else:
                            query = query.order_by(order_field)
            
            # Apply pagination
            if limit > 0:
                query = query.offset(skip).limit(limit)
            
            # Execute query with retry logic
            async def _execute_query():
                result = await db.execute(query)
                
                if columns and len(columns) > 0:
                    # When selecting specific columns, result is a Row object
                    rows = result.all()
                    
                    if as_dict:
                        # Convert Rows to dicts
                        return [{col: getattr(row, col) for col in valid_columns} for row in rows]
                    else:
                        return rows
                else:
                    # When selecting whole model, result is a list of model instances
                    items = list(result.scalars().all())
                    
                    if as_dict:
                        return self.model_utils.model_instances_to_dicts(items)
                    else:
                        return items
                
            return await self.execute_with_retry(_execute_query)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="READ_MANY_ERROR",
                details=f"Error reading multiple {model_class.__name__}: {str(e)}",
                location="read_many()"
            ))
            return []
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="READ_MANY_UNEXPECTED_ERROR",
                details=f"Unexpected error reading multiple {model_class.__name__}: {str(e)}",
                location="read_many()"
            ))
            return []
    
    async def update(self, db: AsyncSession, model_class: Type[ModelType], 
                    id: Any, obj_data: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update an existing record.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            id: Record ID
            obj_data: Updated data
            
        Returns:
            Updated object or None if operation failed
        """
        try:
            # Get the record to update
            db_obj = await self.read(db, model_class, id)
            if not db_obj:
                self.logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="RECORD_NOT_FOUND",
                    details=f"Cannot update {model_class.__name__} with id {id}: record not found",
                    location="update()"
                ))
                return None
            
            # Update attributes
            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            # Commit changes with retry logic
            async def _commit_and_refresh():
                await db.commit()
                await db.refresh(db_obj)
                return db_obj
                
            return await self.execute_with_retry(_commit_and_refresh)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPDATE_ERROR",
                details=f"Error updating {model_class.__name__}: {str(e)}",
                location="update()"
            ))
            await db.rollback()
            return None
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPDATE_UNEXPECTED_ERROR",
                details=f"Unexpected error updating {model_class.__name__}: {str(e)}",
                location="update()"
            ))
            await db.rollback()
            return None
    
    async def delete(self, db: AsyncSession, model_class: Type[ModelType], id: Any) -> bool:
        """
        Delete a record by ID.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            id: Record ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Get the record to delete
            db_obj = await self.read(db, model_class, id)
            if not db_obj:
                self.logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="RECORD_NOT_FOUND",
                    details=f"Cannot delete {model_class.__name__} with id {id}: record not found",
                    location="delete()"
                ))
                return False
            
            # Delete and commit with retry logic
            async def _delete_and_commit():
                await db.delete(db_obj)
                await db.commit()
                return True
                
            return await self.execute_with_retry(_delete_and_commit)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DELETE_ERROR",
                details=f"Error deleting {model_class.__name__}: {str(e)}",
                location="delete()"
            ))
            await db.rollback()
            return False
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DELETE_UNEXPECTED_ERROR",
                details=f"Unexpected error deleting {model_class.__name__}: {str(e)}",
                location="delete()"
            ))
            await db.rollback()
            return False
    
    async def count(self, db: AsyncSession, model_class: Type[ModelType], 
                   filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filtering.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters or operator-based filters
            
        Returns:
            Count of matching records
        """
        try:
            # Start with base query
            stmt = select(func.count()).select_from(model_class)
            
            # Apply filters if provided
            if filters:
                filter_expr = self.filter_parser.parse_filters(model_class, filters)
                if filter_expr is not None:
                    stmt = stmt.filter(filter_expr)
            
            # Execute query with retry logic
            async def _execute_query():
                result = await db.execute(stmt)
                return result.scalar() or 0
                
            return await self.execute_with_retry(_execute_query)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="COUNT_ERROR",
                details=f"Error counting {model_class.__name__}: {str(e)}",
                location="count()"
            ))
            return 0
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="COUNT_UNEXPECTED_ERROR",
                details=f"Unexpected error counting {model_class.__name__}: {str(e)}",
                location="count()"
            ))
            return 0
    
    async def exists(self, db: AsyncSession, model_class: Type[ModelType], id: Any) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            id: Record ID
            
        Returns:
            True if exists, False otherwise
        """
        try:
            # Get the primary key column
            primary_key = self.model_utils.get_primary_key(model_class)
            if not primary_key:
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="NO_PRIMARY_KEY",
                    details=f"Could not determine primary key for {model_class.__name__}",
                    location="exists()"
                ))
                return False
                
            # Query existence by primary key with retry logic
            async def _execute_query():
                stmt = select(func.count()).select_from(model_class).filter(getattr(model_class, primary_key) == id)
                result = await db.execute(stmt)
                count = result.scalar() or 0
                return count > 0
                
            return await self.execute_with_retry(_execute_query)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="EXISTS_ERROR",
                details=f"Error checking existence of {model_class.__name__}: {str(e)}",
                location="exists()"
            ))
            return False
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="EXISTS_UNEXPECTED_ERROR",
                details=f"Unexpected error checking existence of {model_class.__name__}: {str(e)}",
                location="exists()"
            ))
            return False
    
    async def get_by_field(self, db: AsyncSession, model_class: Type[ModelType], 
                          field: str, value: Any) -> Optional[ModelType]:
        """
        Get a record by a specific field value.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            field: Field name
            value: Field value
            
        Returns:
            Found object or None if not found
        """
        try:
            if not hasattr(model_class, field):
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="FIELD_NOT_FOUND",
                    details=f"Field {field} not found in {model_class.__name__}",
                    location="get_by_field()"
                ))
                return None
                
            # Execute query with retry logic
            async def _execute_query():
                stmt = select(model_class).filter(getattr(model_class, field) == value)
                result = await db.execute(stmt)
                return result.scalars().first()
                
            return await self.execute_with_retry(_execute_query)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_BY_FIELD_ERROR",
                details=f"Error getting {model_class.__name__} by field: {str(e)}",
                location="get_by_field()"
            ))
            return None
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="GET_BY_FIELD_UNEXPECTED_ERROR",
                details=f"Unexpected error getting {model_class.__name__} by field: {str(e)}",
                location="get_by_field()"
            ))
            return None
    
    async def create_or_update(self, db: AsyncSession, model_class: Type[ModelType], 
                             unique_field: str, obj_data: Dict[str, Any]) -> Optional[ModelType]:
        """
        Create a record if it doesn't exist, or update it if it does.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            unique_field: Field to check for existence
            obj_data: Data for the new or updated record
            
        Returns:
            Created or updated object, or None if operation failed
        """
        try:
            if unique_field not in obj_data:
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="MISSING_UNIQUE_FIELD",
                    details=f"Unique field {unique_field} not found in data",
                    location="create_or_update()"
                ))
                return None
                
            # Check if record exists
            existing = await self.get_by_field(db, model_class, unique_field, obj_data[unique_field])
            
            if existing:
                # Update existing record
                for field, value in obj_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                
                # Commit with retry logic
                async def _commit_and_refresh():
                    await db.commit()
                    await db.refresh(existing)
                    return existing
                    
                return await self.execute_with_retry(_commit_and_refresh)
            else:
                # Create new record
                return await self.create(db, model_class, obj_data)
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="CREATE_OR_UPDATE_ERROR",
                details=f"Error in create_or_update for {model_class.__name__}: {str(e)}",
                location="create_or_update()"
            ))
            await db.rollback()
            return None
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="CREATE_OR_UPDATE_UNEXPECTED_ERROR",
                details=f"Unexpected error in create_or_update for {model_class.__name__}: {str(e)}",
                location="create_or_update()"
            ))
            await db.rollback()
            return None

    async def upsert(self, db: AsyncSession, model_class: Type[ModelType], 
                    filters: Dict[str, Any], obj_data: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update records matching filters or create if none exists (Update or Insert = Upsert).
        This is particularly useful for composite key situations where multiple fields 
        together form a unique constraint.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            filters: Filter conditions to identify existing records
            obj_data: Data for the new or updated record
            
        Returns:
            Created or updated object, or None if operation failed
        """
        try:
            # Check if records exist
            existing_records = await self.read_many(
                db, 
                model_class, 
                filters=filters, 
                limit=1
            )
            
            if existing_records and len(existing_records) > 0:
                # Update existing record
                record_id = existing_records[0].id
                self.logger.debug(f"Updating existing {model_class.__name__} with ID {record_id}")
                return await self.update(db, model_class, record_id, obj_data)
            else:
                # Create new record
                self.logger.debug(f"Creating new {model_class.__name__} record")
                return await self.create(db, model_class, obj_data)
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPSERT_ERROR",
                details=f"Database error in upsert for {model_class.__name__}: {str(e)}",
                location="upsert()"
            ))
            await db.rollback()
            return None
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPSERT_UNEXPECTED_ERROR",
                details=f"Unexpected error in upsert for {model_class.__name__}: {str(e)}",
                location="upsert()"
            ))
            await db.rollback()
            return None

    async def bulk_create(self, db: AsyncSession, model_class: Type[ModelType], 
                         objects_data: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in a single transaction.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            objects_data: List of data dictionaries for the new records
            
        Returns:
            List of created objects
        """
        try:
            created_objects = []
            
            for obj_data in objects_data:
                # Create new instance of the model
                db_obj = model_class(**obj_data)
                db.add(db_obj)
                created_objects.append(db_obj)
            
            # Commit all objects in a single transaction with retry logic
            async def _commit_and_refresh_all():
                await db.commit()
                
                # Refresh all objects
                for obj in created_objects:
                    await db.refresh(obj)
                
                return created_objects
                
            return await self.execute_with_retry(_commit_and_refresh_all)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_CREATE_ERROR",
                details=f"Error in bulk_create for {model_class.__name__}: {str(e)}",
                location="bulk_create()"
            ))
            await db.rollback()
            return []
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_CREATE_UNEXPECTED_ERROR",
                details=f"Unexpected error in bulk_create for {model_class.__name__}: {str(e)}",
                location="bulk_create()"
            ))
            await db.rollback()
            return []
    
    async def bulk_update(self, db: AsyncSession, model_class: Type[ModelType],
                         ids: List[Any], obj_data: Dict[str, Any]) -> int:
        """
        Update multiple records with the same changes.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            ids: List of record IDs to update
            obj_data: Data to update for all records
            
        Returns:
            Number of records updated
        """
        try:
            if not ids:
                return 0
                
            # Get the primary key column
            primary_key = self.model_utils.get_primary_key(model_class)
            if not primary_key:
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="NO_PRIMARY_KEY",
                    details=f"Could not determine primary key for {model_class.__name__}",
                    location="bulk_update()"
                ))
                return 0
            
            # Build update statement
            stmt = update(model_class).where(getattr(model_class, primary_key).in_(ids)).values(**obj_data)
            
            # Execute update with retry logic
            async def _execute_and_commit():
                result = await db.execute(stmt)
                await db.commit()
                return result.rowcount
            
            return await self.execute_with_retry(_execute_and_commit)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_UPDATE_ERROR",
                details=f"Error in bulk_update for {model_class.__name__}: {str(e)}",
                location="bulk_update()"
            ))
            await db.rollback()
            return 0
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_UPDATE_UNEXPECTED_ERROR",
                details=f"Unexpected error in bulk_update for {model_class.__name__}: {str(e)}",
                location="bulk_update()"
            ))
            await db.rollback()
            return 0
    
    async def bulk_delete(self, db: AsyncSession, model_class: Type[ModelType], 
                         filters: Dict[str, Any]) -> int:
        """
        Delete multiple records matching filters in a single transaction.
        
        Args:
            db: Database session
            model_class: SQLAlchemy model class
            filters: Dictionary of field:value filters or operator-based filters
            
        Returns:
            Number of deleted records
        """
        try:
            # Start with base query
            stmt = delete(model_class)
            
            # Apply filters
            filter_expr = self.filter_parser.parse_filters(model_class, filters)
            if filter_expr is not None:
                stmt = stmt.where(filter_expr)
            
            # Execute delete query and get count with retry logic
            async def _execute_and_commit():
                result = await db.execute(stmt)
                count = result.rowcount
                
                # Commit the transaction
                await db.commit()
                
                return count
                
            return await self.execute_with_retry(_execute_and_commit)
            
        except SQLAlchemyError as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_DELETE_ERROR",
                details=f"Error in bulk_delete for {model_class.__name__}: {str(e)}",
                location="bulk_delete()"
            ))
            await db.rollback()
            return 0
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="BULK_DELETE_UNEXPECTED_ERROR",
                details=f"Unexpected error in bulk_delete for {model_class.__name__}: {str(e)}",
                location="bulk_delete()"
            ))
            await db.rollback()
            return 0
            
    async def shutdown(self):
        """
        Graceful async shutdown when event loop is available.
        """
        self.logger.info(f"Shutting down {COMPONENT_ID} operations")
        
        # No resources to clean up currently, but method is included for consistency
        
        self.logger.info(f"{COMPONENT_ID} operations shutdown complete")
        
    def force_shutdown(self):
        """
        Forced synchronous shutdown when event loop is closed.
        """
        self.logger.info(f"{COMPONENT_ID}: Force shutting down operations")
        
        # No resources to clean up currently, but method is included for consistency
        
        self.logger.info(f"{COMPONENT_ID}: Operations force shutdown complete")
