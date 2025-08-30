"""
modules/core/error_handler/database.py
Updated: April 6, 2025
Database operations for error handler knowledge system using proper execute_with_retry pattern
"""

import logging
import contextlib
from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple
from datetime import datetime, timedelta

from sqlalchemy import func, desc, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .db_models import ErrorCode, ErrorDocument, ErrorExample
# NO error_utils import - would create circular dependency

# Module identity
MODULE_ID = "core.error_handler"
COMPONENT_ID = f"{MODULE_ID}.database"
logger = logging.getLogger(COMPONENT_ID)

class ErrorHandlerDatabaseOperations:
    """Database operations for the error handler module."""
    
    def __init__(self, app_context):
        """Phase 1: Basic setup only - no service access."""
        self.app_context = app_context
        self.db_service = None      # Will be set in Phase 2
        self.crud_service = None    # Will be set in Phase 2
        self.initialized = False
        self.logger = logger
    
    async def initialize(self) -> bool:
        """Phase 2: Initialize database operations with service access."""
        if self.initialized:
            return True
        
        # Phase 2: Now it's safe to access other services
        self.db_service = self.app_context.get_service("core.database.service")
        self.crud_service = self.app_context.get_service("core.database.crud_service")
            
        if not self.db_service:
            # CRITICAL: Do not use # Direct logging instead of error_message() in error_handler to prevent loops
            self.logger.warning("Error handler: Database service not available - features disabled")
            return False
        
        if not self.db_service.initialized:
            # CRITICAL: Do not use # Direct logging instead of error_message() in error_handler to prevent loops
            self.logger.warning("Error handler: Database not initialized - features disabled")
            return False
        
        if not self.crud_service:
            # CRITICAL: Do not use # Direct logging instead of error_message() in error_handler to prevent loops
            self.logger.warning("Error handler: CRUD service not available - features disabled")
            return False
        
        self.initialized = True
        self.logger.info("Database operations initialized")
        return True
    
    @contextlib.asynccontextmanager
    async def _db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with initialization check."""
        if not self.initialized and not await self.initialize():
            # CRITICAL: Do not use # Direct logging instead of error_message() in error_handler to prevent loops
            err_msg = "Error handler: Database operations dependencies not initialized"
            self.logger.error(err_msg)
            raise RuntimeError(err_msg)

        # Use AsyncSession from the app context session factory
        async with self.app_context.db_session() as session:
            yield session
    
    async def _db_op(self, op_func, default=None):
        """
        Execute a database operation with standard error handling.
        
        Args:
            op_func: Async function to execute
            default: Default value to return on error
            
        Returns:
            Result of op_func or default if error occurs
        """
        try:
            return await op_func()
        except RuntimeError as e:
            # CRITICAL: Do not log error_handler's own database errors to prevent infinite loops
            # Just log to the regular Python logger without using # Direct logging instead of error_message()
            self.logger.error(f"Error handler database not ready: {str(e)}")
            return default
        except Exception as e:
            # CRITICAL: Do not log error_handler's own database errors to prevent infinite loops
            # The error_handler should not log errors about its own table creation/access
            # Just log to the regular Python logger without using # Direct logging instead of error_message()
            self.logger.error(f"Error handler database operation failed: {str(e)}")
            return default
    
    # ErrorCode Operations
    
    async def get_or_create_error_code(self, module_id: str, code: str) -> Optional[int]:
        """Get or create an error code entry, returning its ID."""
        async def _get_or_create():
            async with self._db_session() as session:
                # Check if code exists
                stmt = select(ErrorCode).where(
                    and_(
                        ErrorCode.module_id == module_id,
                        ErrorCode.code == code
                    )
                )
                result = await session.execute(stmt)
                error_code = result.scalars().first()
                
                if error_code:
                    return error_code.id
                
                # Create new record
                now = datetime.now()
                new_error = ErrorCode(
                    module_id=module_id,
                    code=code,
                    first_seen=now,
                    last_seen=now,
                    count=0,
                    locations=[],
                    priority_score=0.0
                )
                
                session.add(new_error)
                
                # Use execute_with_retry for commit operation
                await session.commit()
                await session.refresh(new_error)
                
                return new_error.id
        
        return await self._db_op(_get_or_create)
    
    async def update_error_code(self, module_id: str, code: str, location: Optional[str] = None) -> bool:
        """Update an error code with a new occurrence."""
        async def _update():
            async with self._db_session() as session:
                # Find the error code using execute_with_retry
                stmt = select(ErrorCode).where(
                    and_(
                        ErrorCode.module_id == module_id,
                        ErrorCode.code == code
                    )
                )
                result = await session.execute(stmt)
                error_code = result.scalars().first()
                
                if not error_code:
                    return False
                
                # Update the record
                error_code.last_seen = datetime.now()
                error_code.count += 1
                
                # Add location if provided and not already in list
                if location and location not in error_code.locations:
                    error_code.locations.append(location)
                
                # Recalculate priority score
                error_code.priority_score = self._calculate_priority_score(
                    count=error_code.count,
                    first_seen=error_code.first_seen,
                    last_seen=error_code.last_seen,
                    locations=len(error_code.locations)
                )
                
                # Use execute_with_retry for commit operation
                await session.commit()
                return True
        
        return await self._db_op(_update, False)
    
    def _calculate_priority_score(self, count: int, first_seen: datetime, 
                                 last_seen: datetime, locations: int) -> float:
        """Calculate priority score for an error."""
        # Get current time
        now = datetime.now()
        
        # Calculate frequency score (0-10)
        frequency_score = min(10, count / 5)
        
        # Calculate recency score (0-10)
        days_since_last = max(0.1, (now - last_seen).days)
        recency_score = 10 * (1 / (1 + days_since_last))
        
        # Calculate impact score (0-10)
        impact_score = min(10, locations * 2)
        
        # Calculate age score (newer errors get higher scores)
        days_since_first = max(0.1, (now - first_seen).days)
        age_factor = 1.0 if days_since_first < 30 else 0.8  # Recent errors are more relevant
        
        # Combined score (0-10)
        # Weights: frequency (50%), recency (30%), impact (20%)
        final_score = ((frequency_score * 0.5) + 
                       (recency_score * 0.3) + 
                       (impact_score * 0.2)) * age_factor
        
        return round(final_score, 2)
    
    async def get_error_codes(self, limit: int = 100, 
                             order_by: str = "priority") -> List[Dict[str, Any]]:
        """Get error codes ordered by specified criterion."""
        async def _get():
            async with self._db_session() as session:
                # Build query based on order criteria
                if order_by == "priority":
                    stmt = select(ErrorCode).order_by(desc(ErrorCode.priority_score))
                elif order_by == "count":
                    stmt = select(ErrorCode).order_by(desc(ErrorCode.count))
                elif order_by == "recent":
                    stmt = select(ErrorCode).order_by(desc(ErrorCode.last_seen))
                else:
                    stmt = select(ErrorCode).order_by(desc(ErrorCode.priority_score))
                
                # Add limit
                stmt = stmt.limit(limit)
                
                # Execute query with retry
                result = await session.execute(stmt)
                error_codes = result.scalars().all()
                
                # Convert to dictionaries
                return [
                    {
                        "id": code.id,
                        "module_id": code.module_id,
                        "code": code.code,
                        "count": code.count,
                        "first_seen": code.first_seen.isoformat(),
                        "last_seen": code.last_seen.isoformat(),
                        "locations": code.locations,
                        "priority_score": code.priority_score
                    }
                    for code in error_codes
                ]
        
        return await self._db_op(_get, [])
    
    async def search_error_codes(self, query: str) -> List[Dict[str, Any]]:
        """Search for error codes matching the query."""
        async def _search():
            async with self._db_session() as session:
                # Build search query with wildcards
                search_term = f"%{query}%"
                stmt = select(ErrorCode).where(
                    or_(
                        ErrorCode.code.ilike(search_term)
                    )
                ).order_by(desc(ErrorCode.priority_score))
                
                # Execute query with retry
                result = await session.execute(stmt)
                error_codes = result.scalars().all()
                
                # Convert to dictionaries
                return [
                    {
                        "id": code.id,
                        "module_id": code.module_id,
                        "code": code.code,
                        "count": code.count,
                        "priority_score": code.priority_score,
                        "last_seen": code.last_seen.isoformat()
                    }
                    for code in error_codes
                ]
        
        return await self._db_op(_search, [])
    
    # ErrorDocument Operations
    
    async def get_or_create_document(self, error_code_id: int) -> Optional[int]:
        """Get or create a documentation entry for an error code."""
        async def _get_or_create():
            async with self._db_session() as session:
                # Check if document exists
                stmt = select(ErrorDocument).where(ErrorDocument.error_code_id == error_code_id)
                result = await session.execute(stmt)
                document = result.scalars().first()
                
                if document:
                    return document.id
                
                # Get the error code
                stmt = select(ErrorCode).where(ErrorCode.id == error_code_id)
                result = await session.execute(stmt)
                error_code = result.scalars().first()
                
                if not error_code:
                    return None
                
                # Create new document with template
                now = datetime.now()
                new_doc = ErrorDocument(
                    error_code_id=error_code_id,
                    title=error_code.code,
                    what_it_means="This error occurs when...",
                    why_important="This pattern is important because...",
                    implementation="```python\n# Example implementation\n```",
                    common_mistakes="- First common mistake\n- Second common mistake",
                    related_patterns=[],
                    created_at=now,
                    updated_at=now,
                    status="draft"
                )
                
                session.add(new_doc)
                await session.commit()
                await session.refresh(new_doc)
                
                return new_doc.id
        
        return await self._db_op(_get_or_create)
    
    async def update_document(self, document_id: int, 
                             data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an error document."""
        async def _update():
            async with self._db_session() as session:
                # Get the document
                stmt = select(ErrorDocument).where(ErrorDocument.id == document_id)
                result = await session.execute(stmt)
                document = result.scalars().first()
                
                if not document:
                    return None
                
                # Update fields
                for key, value in data.items():
                    if hasattr(document, key):
                        setattr(document, key, value)
                
                # Always update the updated_at timestamp
                document.updated_at = datetime.now()
                
                await session.commit()
                await session.refresh(document)
                
                # Return updated document
                return {
                    "id": document.id,
                    "error_code_id": document.error_code_id,
                    "title": document.title,
                    "status": document.status,
                    "updated_at": document.updated_at.isoformat()
                }
        
        return await self._db_op(_update)
    
    async def get_document(self, error_code_id: int) -> Optional[Dict[str, Any]]:
        """Get documentation for an error code."""
        async def _get():
            async with self._db_session() as session:
                # Get the document with error code
                stmt = select(ErrorDocument).where(
                    ErrorDocument.error_code_id == error_code_id
                ).options(selectinload(ErrorDocument.error_code))
                
                result = await session.execute(stmt)
                document = result.scalars().first()
                
                if not document:
                    return None
                
                # Return document data
                return {
                    "id": document.id,
                    "error_code_id": document.error_code_id,
                    "error_code": document.error_code.code,
                    "title": document.title,
                    "what_it_means": document.what_it_means,
                    "why_important": document.why_important,
                    "implementation": document.implementation,
                    "common_mistakes": document.common_mistakes,
                    "related_patterns": document.related_patterns,
                    "created_at": document.created_at.isoformat(),
                    "updated_at": document.updated_at.isoformat(),
                    "status": document.status
                }
        
        return await self._db_op(_get)
    
    # ErrorExample Operations
    
    async def add_error_example(self, error_code_id: int, message: str,
                               module_id: str, location: str,
                               context: Dict[str, Any] = None) -> Optional[int]:
        """Add an example of an error occurrence."""
        async def _add():
            async with self._db_session() as session:
                # Create new example
                new_example = ErrorExample(
                    error_code_id=error_code_id,
                    message=message,
                    module_id=module_id,
                    location=location,
                    context=context or {},
                    timestamp=datetime.now()
                )
                
                session.add(new_example)
                await session.commit()
                await session.refresh(new_example)
                
                return new_example.id
        
        return await self._db_op(_add)
    
    async def get_error_examples(self, error_code_id: int, 
                                limit: int = 5) -> List[Dict[str, Any]]:
        """Get examples for an error code."""
        async def _get():
            async with self._db_session() as session:
                # Get the most recent examples
                stmt = select(ErrorExample).where(
                    ErrorExample.error_code_id == error_code_id
                ).order_by(desc(ErrorExample.timestamp)).limit(limit)
                
                result = await session.execute(stmt)
                examples = result.scalars().all()
                
                # Convert to dictionaries
                return [
                    {
                        "id": example.id,
                        "message": example.message,
                        "module_id": example.module_id,
                        "location": example.location,
                        "context": example.context,
                        "timestamp": example.timestamp.isoformat()
                    }
                    for example in examples
                ]
        
        return await self._db_op(_get, [])
