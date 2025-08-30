"""
modules/core/error_handler/services.py
Refactored: August 10, 2025
Pure JSONL processing service - no direct database operations

This service now functions like a normal module:
- Processes JSONL files from core.error_utils
- Provides in-memory analytics and search
- Uses centralized database service for any database needs
- No direct database model imports
"""

import os
import json
import time
import glob
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

# NO ERROR_UTILS IMPORT - would create circular dependency!
# Error_handler processes JSONL files created by error_utils, so it cannot use error_utils
# Use direct logging to app.log to avoid infinite loops

# Import database operations for SQL storage
from .database import ErrorHandlerDatabaseOperations

# Module identity
MODULE_ID = "core.error_handler"
logger = logging.getLogger(MODULE_ID)

# Local Result class to avoid circular dependency
class Result:
    """Local Result class to avoid importing from core.error_utils"""
    def __init__(self, success=False, data=None, error=None):
        self.success = success
        self.data = data
        self.error = error or {}
    
    @classmethod
    def success(cls, data=None):
        return cls(success=True, data=data)
    
    @classmethod 
    def error(cls, code, message, details=None):
        return cls(success=False, error={
            "code": code,
            "message": message,
            "details": details or {}
        })

class ErrorRegistry:
    """
    Pure JSONL processing service for error analysis.
    
    Processes error logs written by core.error_utils to provide:
    - In-memory error tracking and analytics
    - Error pattern detection
    - Priority scoring
    - Search capabilities
    
    Database operations (if needed) are handled through the centralized
    database service, maintaining clean separation.
    """
    
    def __init__(self, app_context=None):
        """
        Initialize the registry.
        
        Args:
            app_context: Optional application context
        """
        self.app_context = app_context
        self.initialized = False
        self.log_dir = None
        
        # Database operations for SQL storage
        self.db_operations = None  # Will be initialized in Phase 2
        
        # Background tasks tracking
        self._background_tasks = []
        self._is_running = True
        
        # Logger initialized with MODULE_ID
        self.logger = logger
        
        self.logger.info(f"{MODULE_ID} service instance created (pre-Phase 2)")
        
    async def initialize(self, app_context=None, settings=None):
        """
        Phase 2 initialization.
        
        Args:
            app_context: Optional application context
            settings: Optional settings dictionary
            
        Returns:
            bool: True if initialization successful
        """
        if self.initialized:
            return True
            
        self.logger.info(f"Initializing {MODULE_ID} registry service")
        
        try:
            # Determine log directory
            context = app_context or self.app_context
            self.log_dir = os.path.join(
                context.config.DATA_DIR if context else "data",
                "error_logs"
            )
            
            # Initialize database operations
            self.db_operations = ErrorHandlerDatabaseOperations(context)
            db_initialized = await self.db_operations.initialize()
            
            if db_initialized:
                self.logger.info("Error_handler initialized with database operations")
            else:
                self.logger.warning("Error_handler initialized with JSONL-only mode (database not available)")
            
            # Apply Pydantic settings if provided
            if settings:
                # Store settings for future use if needed
                self.settings = settings
                
                # Clean Pydantic-only implementation - use attributes directly
                self.max_errors_per_category = settings.max_errors_per_category
                self.max_examples_per_error = settings.max_examples_per_error
            
            # Process existing error logs
            try:
                await self._process_logs()
            except Exception as e:
                self.logger.error(f"LOG_PROCESSING_ERROR - Error processing logs during initialization: {str(e)} in initialize()")
                
            # Start background task for periodic processing
            self._create_background_task(
                self._periodic_log_processing(),
                name="error_registry_log_processor"
            )
                
            self.initialized = True
            self.logger.info(f"{MODULE_ID} registry service initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"INITIALIZATION_ERROR - Failed to initialize registry service: {str(e)} in initialize()")
            return False
    
    async def shutdown(self):
        """
        Graceful async shutdown of the registry service.
        Called during normal application shutdown.
        """
        self.logger.info(f"{MODULE_ID}: Shutting down registry service gracefully...")
        
        # Signal background tasks to stop
        self._is_running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
        
        self.logger.info(f"{MODULE_ID}: Registry service shutdown complete")
    
    async def cleanup_resources(self):
        """
        Graceful resource cleanup - logging handled by decorator.
        Called during normal application shutdown via @graceful_shutdown decorator.
        """
        # Delegate to existing shutdown logic
        await self.shutdown()
    
    def force_cleanup(self):
        """
        Force cleanup of resources - logging handled by decorator.
        Called during emergency shutdown via @force_shutdown decorator.
        """
        # Force cleanup - stop background tasks immediately
        self._is_running = False
    
    def _create_background_task(self, coroutine, name=None):
        """Create a tracked background task with cleanup handling."""
        task = asyncio.create_task(coroutine, name=name)
        
        # Register cleanup callback
        def _task_done_callback(task):
            # Handle task completion
            if task in self._background_tasks:
                self._background_tasks.remove(task)
                # Check for exceptions
                if task.done() and not task.cancelled():
                    try:
                        task.result()
                    except Exception as e:
                        self.logger.error(f"BACKGROUND_TASK_ERROR - Background task {name} failed: {str(e)} in _create_background_task()")
        
        task.add_done_callback(_task_done_callback)
        self._background_tasks.append(task)
        return task
    
    async def _periodic_log_processing(self):
        """Background task for periodically processing logs."""
        while self._is_running:
            try:
                # Sleep first to avoid processing logs twice during initialization
                await asyncio.sleep(3600)  # Process hourly
                
                if not self._is_running:
                    break
                    
                # Process logs
                await self._process_logs()
                
                # Refresh priority scores
                await self.calculate_priority_scores()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"PERIODIC_PROCESSING_ERROR - Error in periodic log processing: {str(e)} in _periodic_log_processing()")
                # Wait before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def _process_logs(self):
        """Internal method to process logs without recursion checks."""
        # Ensure log directory exists
        if not os.path.exists(self.log_dir):
            self.logger.info(f"Error log directory {self.log_dir} does not exist yet")
            return
            
        # Get all error log files
        log_files = glob.glob(os.path.join(self.log_dir, "*-error.jsonl"))
        
        if not log_files:
            self.logger.info("No error log files found")
            return
            
        # Sort files by date
        log_files.sort()
        
        # Track statistics
        processed_files = 0
        
        # Process each file
        for log_file in log_files:
            self.logger.info(f"Processing error log file: {os.path.basename(log_file)}")
            processed_files += 1
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            # Parse the JSONL entry
                            error_entry = json.loads(line)
                            
                            # Register the error directly to database
                            await self._register_error_from_log(error_entry)
                        except json.JSONDecodeError:
                            self.logger.warning(f"JSON_DECODE_ERROR - Invalid JSON in {os.path.basename(log_file)}: {line[:100]}... in _process_logs()")
                            continue
            except Exception as e:
                self.logger.error(f"LOG_PROCESSING_ERROR - Exception processing log file {os.path.basename(log_file)}: {str(e)} in _process_logs()")
                continue
                
        self.logger.info(f"Processed {processed_files} error log files")
    
    async def _register_error_from_log(self, error_entry):
        """
        Register an error from a log entry directly to database.
        
        Args:
            error_entry: Error log entry from JSONL
        """
        # Extract fields from log entry (new JSONL format from core.error_utils)
        error_type = error_entry.get("error_type")
        module_id = error_entry.get("module_id")
        details = error_entry.get("details")
        location = error_entry.get("location")
        session_id = error_entry.get("session_id")
        timestamp = error_entry.get("timestamp")
        
        if not error_type or not module_id:
            return
        
        # Create full error code
        error_code = f"{module_id.replace('.', '_')}_{error_type}"
        
        # Write to database if available
        if self.db_operations and self.db_operations.initialized:
            try:
                # Get or create error code in database
                error_code_id = await self.db_operations.get_or_create_error_code(
                    module_id=module_id, 
                    code=error_code
                )
                
                if error_code_id:
                    # Update error code statistics
                    await self.db_operations.update_error_code(
                        module_id=module_id,
                        code=error_code, 
                        location=location
                    )
                    
                    # Add example if we have meaningful details
                    if details and len(str(details).strip()) > 0:
                        await self.db_operations.add_error_example(
                            error_code_id=error_code_id,
                            message=str(details)[:500],  # Limit message length
                            module_id=module_id,
                            location=location or "unknown",
                            context={
                                "session_id": session_id,
                                "error_type": error_type,
                                "timestamp": timestamp
                            }
                        )
                        
            except Exception as e:
                # Don't let database errors break JSONL processing
                self.logger.warning(f"DATABASE_WRITE_ERROR - Failed to write error to database: {str(e)} in _register_error_from_log()")
        else:
            # Log that database isn't available
            self.logger.warning(f"DATABASE_UNAVAILABLE - Cannot store error {error_code}: database operations not initialized")
    
    
    # ============================================================================
    # PUBLIC API METHODS
    # ============================================================================
    
    async def process_error_logs(self, params=None):
        """
        Process all error logs since last run.
        
        Returns:
            Result with processing statistics
        """
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message="Registry not initialized"
            )
        
        try:
            initial_error_count = await self.get_error_count()
            
            # Process logs using internal method
            await self._process_logs()
            
            # Calculate new errors
            final_error_count = await self.get_error_count()
            new_errors = final_error_count - initial_error_count
            
            return Result.success(data={
                "new_errors": new_errors,
                "total_errors": final_error_count,
                "total_occurrences": await self.get_total_occurrences()
            })
        except Exception as e:
            self.logger.error(f"LOG_PROCESSING_ERROR - Error processing error logs: {str(e)} in process_error_logs()")
            return Result.error(
                code="PROCESSING_ERROR", 
                message="Failed to process error logs",
                details={"error": str(e)}
            )
    
    async def calculate_priority_scores(self, params=None) -> Result:
        """
        Calculate priority scores for errors to determine documentation priority.
        
        Returns:
            Result with dictionary mapping error codes to priority scores
        """
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message="Registry not initialized"
            )
                        
        try:
            priority_scores = {}
            
            # Use defaults since database settings are not available in pure JSONL mode
            frequency_weight = 0.5
            recency_weight = 0.3
            impact_weight = 0.2
            min_threshold = 3
            
            # Get all errors from database
            all_errors = await self.get_all_errors()
            
            for error_data in all_errors:
                code = error_data.get("code", "")
                count = error_data.get("count", 0)
                
                # Skip errors that don't meet minimum threshold
                if count < min_threshold:
                    priority_scores[code] = 0
                    continue
                    
                # Calculate count score (0-10 based on occurrence count)
                count_score = min(10, count / 5)
                
                # Calculate recency score
                try:
                    last_seen_str = error_data.get("last_seen", "")
                    if last_seen_str:
                        last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                        days_since_last = (datetime.now() - last_seen.replace(tzinfo=None)).days
                        recency_score = 10 * (1 / (1 + days_since_last))  # 0-10, decaying with time
                    else:
                        recency_score = 5
                except:
                    recency_score = 5  # Default if dates can't be parsed
                
                # Calculate impact score based on number of affected modules
                # For now, assume 1 module per error (database stores module_id)
                impact_score = min(10, 1 * 2)  # 0-10 based on module count
                
                # Combined score using configurable weights
                priority_scores[code] = (count_score * frequency_weight) + (recency_score * recency_weight) + (impact_score * impact_weight)
            
            return Result.success(data=priority_scores)
        except Exception as e:
            self.logger.error(f"CALCULATION_ERROR - Error calculating priority scores: {str(e)} in calculate_priority_scores()")
            return Result.error(
                code="CALCULATION_ERROR",
                message="Failed to calculate priority scores",
                details={"error": str(e)}
            )
    
    async def get_prioritized_errors(self, limit: int = 10, params=None) -> Result:
        """
        Get errors sorted by priority score.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            Result with list of error entries with priority scores
        """
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message="Registry not initialized"
            )
                    
        try:
            # Pure JSONL processing - use in-memory data only
            priority_scores_result = await self.calculate_priority_scores()
            if not priority_scores_result.success:
                return priority_scores_result  # Propagate error
                
            priority_scores = priority_scores_result.data
            
            # Create list of errors with scores using database data
            errors_with_scores = []
            all_errors = await self.get_all_errors()
            
            for error_data in all_errors:
                code = error_data.get("code", "")
                
                # Skip errors with zero priority score
                if priority_scores.get(code, 0) <= 0:
                    continue
                    
                # Create serializable representation
                error_entry = {
                    "code": code,
                    "count": error_data.get("count", 0),
                    "first_seen": error_data.get("first_seen", ""),
                    "last_seen": error_data.get("last_seen", ""),
                    "priority_score": priority_scores.get(code, 0),
                    "modules": [error_data.get("module_id", "")],  # Database stores single module
                    "example_messages": [],  # Would need to query error_examples for this
                    "locations": error_data.get("locations", [])
                }
                errors_with_scores.append(error_entry)
            
            # Sort by priority score (highest first)
            errors_with_scores.sort(key=lambda x: x["priority_score"], reverse=True)
            
            # Limit the results
            return Result.success(data=errors_with_scores[:limit])
        except Exception as e:
            self.logger.error(f"RETRIEVAL_ERROR - Error getting prioritized errors: {str(e)} in get_prioritized_errors()")
            return Result.error(
                code="RETRIEVAL_ERROR",
                message="Failed to get prioritized errors",
                details={"error": str(e)}
            )
    
    async def search_errors(self, query: str, limit: int = 10, params=None) -> Result:
        """
        Search for errors matching the query.
        
        Args:
            query: Search term
            limit: Maximum number of results
            
        Returns:
            Result with list of matching errors
        """
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message="Registry not initialized"
            )
                    
        try:
            # Use database operations for search
            if self.db_operations and self.db_operations.initialized:
                # Use database search
                results = await self.db_operations.search_error_codes(query)
                return Result.success(data=results[:limit])
            else:
                # Database not available
                return Result.error(
                    code="DB_NOT_AVAILABLE",
                    message="Database operations not available for search"
                )
        except Exception as e:
            self.logger.error(f"SEARCH_ERROR - Error searching for errors: {str(e)} in search_errors()")
            return Result.error(
                code="SEARCH_ERROR",
                message="Failed to search for errors",
                details={"error": str(e)}
            )
    
    
    # ============================================================================
    # DATABASE METHODS (Now return errors - use centralized database service)
    # ============================================================================
    
    async def get_error_document(self, error_code: str, params=None) -> Result:
        """
        Get documentation for an error code.
        
        Args:
            error_code: The error code to get documentation for
            
        Returns:
            Result with error documentation or error
        """
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message="Registry not initialized"
            )
            
        if not self.db_operations or not self.db_operations.initialized:
            return Result.error(
                code="DB_NOT_AVAILABLE",
                message="Database operations not available"
            )
        
        try:
            # First get the error code ID from database
            error_codes = await self.db_operations.search_error_codes(error_code)
            if not error_codes:
                return Result.error(
                    code="ERROR_CODE_NOT_FOUND",
                    message=f"Error code '{error_code}' not found"
                )
            
            error_code_id = error_codes[0]["id"]
            document = await self.db_operations.get_document(error_code_id)
            
            if document:
                return Result.success(data=document)
            else:
                return Result.error(
                    code="DOCUMENT_NOT_FOUND",
                    message=f"No documentation found for error code '{error_code}'"
                )
                
        except Exception as e:
            self.logger.error(f"DOCUMENT_RETRIEVAL_ERROR - Error getting error document: {str(e)} in get_error_document()")
            return Result.error(
                code="DOCUMENT_RETRIEVAL_ERROR",
                message="Failed to get error document",
                details={"error": str(e)}
            )
    
    async def get_error_examples(self, error_code: str, limit: int = 5, params=None) -> Result:
        """
        Get examples for an error code.
        
        Args:
            error_code: The error code to get examples for
            limit: Maximum number of examples to return
            
        Returns:
            Result with error examples or error
        """
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message="Registry not initialized"
            )
            
        if not self.db_operations or not self.db_operations.initialized:
            return Result.error(
                code="DB_NOT_AVAILABLE",
                message="Database operations not available"
            )
        
        try:
            # First get the error code ID from database
            error_codes = await self.db_operations.search_error_codes(error_code)
            if not error_codes:
                return Result.error(
                    code="ERROR_CODE_NOT_FOUND",
                    message=f"Error code '{error_code}' not found"
                )
            
            error_code_id = error_codes[0]["id"]
            examples = await self.db_operations.get_error_examples(error_code_id, limit)
            
            return Result.success(data=examples)
                
        except Exception as e:
            self.logger.error(f"EXAMPLES_RETRIEVAL_ERROR - Error getting error examples: {str(e)} in get_error_examples()")
            return Result.error(
                code="EXAMPLES_RETRIEVAL_ERROR",
                message="Failed to get error examples",
                details={"error": str(e)}
            )
    
    async def update_error_document(self, error_code: str, data: Dict[str, Any], params=None) -> Result:
        """
        Update documentation for an error code.
        
        Args:
            error_code: The error code to update documentation for
            data: Documentation data to update
            
        Returns:
            Result with updated documentation or error
        """
        if not self.initialized and not await self.initialize():
            return Result.error(
                code="SERVICE_NOT_INITIALIZED",
                message="Registry not initialized"
            )
            
        if not self.db_operations or not self.db_operations.initialized:
            return Result.error(
                code="DB_NOT_AVAILABLE",
                message="Database operations not available"
            )
        
        try:
            # First get the error code ID from database
            error_codes = await self.db_operations.search_error_codes(error_code)
            if not error_codes:
                return Result.error(
                    code="ERROR_CODE_NOT_FOUND",
                    message=f"Error code '{error_code}' not found"
                )
            
            error_code_id = error_codes[0]["id"]
            
            # Get or create document
            document_id = await self.db_operations.get_or_create_document(error_code_id)
            if not document_id:
                return Result.error(
                    code="DOCUMENT_CREATE_ERROR",
                    message="Failed to create or get document"
                )
            
            # Update the document
            updated_doc = await self.db_operations.update_document(document_id, data)
            
            if updated_doc:
                return Result.success(data=updated_doc)
            else:
                return Result.error(
                    code="DOCUMENT_UPDATE_ERROR", 
                    message="Failed to update document"
                )
                
        except Exception as e:
            self.logger.error(f"DOCUMENT_UPDATE_ERROR - Error updating error document: {str(e)} in update_error_document()")
            return Result.error(
                code="DOCUMENT_UPDATE_ERROR",
                message="Failed to update error document",
                details={"error": str(e)}
            )
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    async def get_error_data(self, code: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific error code from database."""
        if not self.db_operations or not self.db_operations.initialized:
            return None
            
        error_codes = await self.db_operations.search_error_codes(code)
        return error_codes[0] if error_codes else None
    
    async def get_all_errors(self) -> List[Dict[str, Any]]:
        """Get all error data from database."""
        if not self.db_operations or not self.db_operations.initialized:
            return []
            
        return await self.db_operations.get_error_codes(limit=1000)
    
    async def get_error_count(self) -> int:
        """Get the total number of unique error codes from database."""
        all_errors = await self.get_all_errors()
        return len(all_errors)
    
    async def get_total_occurrences(self) -> int:
        """Get the total number of error occurrences from database."""
        all_errors = await self.get_all_errors()
        return sum(error.get("count", 0) for error in all_errors)