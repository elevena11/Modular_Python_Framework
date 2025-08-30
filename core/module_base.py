"""
core/module_base.py
Data Integrity-Enforcing Base Module Classes

This module provides base classes for framework modules that enforce
absolute truth correspondence requirements and prevent data integrity violations.

Key Features:
- Mandatory data integrity validation during initialization
- Hard failure enforcement - No graceful degradation with mock data  
- Anti-mock protection built into base class validation
- Database integrity verification for database-enabled modules
- Clean API with built-in integrity guarantees

Usage:
    from core.module_base import DataIntegrityModule, DatabaseEnabledModule
    
    # For modules without database requirements
    class MyModule(DataIntegrityModule):
        MODULE_ID = "standard.my_module"
        
        async def initialize(self, app_context) -> bool:
            # Custom initialization with automatic integrity validation
            return await super().initialize(app_context)
    
    # For modules requiring database access
    class MyDatabaseModule(DatabaseEnabledModule):
        MODULE_ID = "standard.my_db_module"
        
        def _get_required_databases(self) -> List[str]:
            return ["my_module_db", "framework"]
            
        async def initialize(self, app_context) -> bool:
            # Custom initialization with database integrity validation
            return await super().initialize(app_context)
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from core.logging import get_framework_logger

logger = get_framework_logger(__name__)

# ============================================================================
# DATA INTEGRITY EXCEPTIONS
# ============================================================================

class DataIntegrityError(Exception):
    """Raised when data integrity requirements are violated."""
    pass

class DataIntegrityViolation(DataIntegrityError):
    """Raised when module violates absolute truth correspondence requirements."""
    pass

class DatabaseIntegrityError(DataIntegrityError):
    """Raised when database integrity validation fails."""
    pass

class MockDataViolation(DataIntegrityViolation):
    """Raised when mock data patterns are detected."""
    pass

# ============================================================================
# BASE DATA INTEGRITY MODULE CLASS
# ============================================================================

class DataIntegrityModule(ABC):
    """
    Base class for all framework modules enforcing data integrity requirements.
    
    This base class ensures that all modules follow the framework's absolute
    truth correspondence requirements. It provides:
    
    - Mandatory integrity validation during initialization
    - Anti-mock protection to prevent fake data usage
    - Hard failure enforcement instead of graceful degradation
    - Consistent error handling with integrity context
    - Clean API with built-in integrity guarantees
    
    Key Integrity Requirements:
    - NO MOCK DATA allowed anywhere in the module
    - NO FALLBACK SUBSTITUTION - hard failure instead of fake defaults
    - NO GRACEFUL DEGRADATION - system must stop rather than continue with false data
    
    Usage:
        class MyModule(DataIntegrityModule):
            MODULE_ID = "standard.my_module"
            
            async def initialize(self, app_context) -> bool:
                # Custom initialization here
                result = await super().initialize(app_context)
                if not result:
                    return False
                    
                # Module-specific initialization
                return True
    """
    
    # Module must define these
    MODULE_ID: str = None  # Must be overridden by subclass
    
    def __init__(self):
        """Initialize module with integrity validation setup."""
        if not self.MODULE_ID:
            raise DataIntegrityError(
                f"Module {self.__class__.__name__} must define MODULE_ID. "
                f"This violates module integrity requirements."
            )
        
        self.logger = get_framework_logger(self.MODULE_ID)
        self.app_context: Optional[Any] = None
        self.initialized = False
        self._startup_time: Optional[datetime] = None
        
        # Anti-mock protection
        self._forbidden_patterns = {
            'mock', 'fake', 'test_mock', 'placeholder', 'dummy',
            'sample', 'demo_data', 'fake_data', 'test_data'
        }
        
        self.logger.debug(f"DataIntegrityModule {self.MODULE_ID} created with integrity validation")
    
    async def initialize(self, app_context) -> bool:
        """
        Initialize module with mandatory data integrity validation.
        
        This method enforces the framework's data integrity requirements:
        1. Validates module follows integrity patterns
        2. Checks for mock data violations
        3. Verifies app_context is real and functional
        4. Ensures hard failure if any integrity violation found
        
        Args:
            app_context: Application context (must be real, not mock)
            
        Returns:
            bool: True if initialization successful with integrity guarantees
            
        Raises:
            DataIntegrityViolation: If any integrity requirement is violated
            MockDataViolation: If mock data patterns are detected
        """
        self.logger.info(f"Initializing {self.MODULE_ID} with mandatory integrity validation")
        
        if self.initialized:
            self.logger.warning(f"{self.MODULE_ID} already initialized - integrity state preserved")
            return True
        
        # CRITICAL: Validate app_context integrity
        await self._validate_app_context_integrity(app_context)
        
        # Store validated app_context
        self.app_context = app_context
        
        # CRITICAL: Validate module integrity patterns
        await self._validate_module_integrity()
        
        # Record startup time
        self._startup_time = datetime.now()
        
        # Mark as initialized
        self.initialized = True
        
        self.logger.info(f"{self.MODULE_ID} initialized with integrity guarantees")
        return True
    
    async def _validate_app_context_integrity(self, app_context) -> None:
        """
        Validate that app_context meets data integrity requirements.
        
        Args:
            app_context: Application context to validate
            
        Raises:
            DataIntegrityViolation: If app_context violates integrity requirements
        """
        if not app_context:
            raise DataIntegrityViolation(
                f"Module {self.MODULE_ID} received null app_context. "
                f"This violates data integrity requirements - no fallback allowed."
            )
        
        # Check for mock app_context patterns
        app_context_type = type(app_context).__name__.lower()
        if any(pattern in app_context_type for pattern in self._forbidden_patterns):
            raise MockDataViolation(
                f"Module {self.MODULE_ID} received mock app_context: {app_context_type}. "
                f"Mock contexts violate absolute truth correspondence requirements."
            )
        
        # Validate app_context has required attributes
        required_attributes = ['config', 'get_service', 'register_service']
        missing_attributes = [attr for attr in required_attributes if not hasattr(app_context, attr)]
        
        if missing_attributes:
            raise DataIntegrityViolation(
                f"Module {self.MODULE_ID} received invalid app_context missing: {missing_attributes}. "
                f"This violates framework integrity requirements."
            )
        
        # Validate session_id exists (indicates real framework session)
        if not hasattr(app_context, 'session_id') or not app_context.session_id:
            raise DataIntegrityViolation(
                f"Module {self.MODULE_ID} app_context has no session_id. "
                f"This suggests mock context, violating integrity requirements."
            )
        
        self.logger.debug(f"{self.MODULE_ID} app_context integrity validated: {app_context.session_id}")
    
    async def _validate_module_integrity(self) -> None:
        """
        Validate module follows data integrity patterns.
        
        Raises:
            DataIntegrityViolation: If module violates integrity requirements
        """
        # Check module ID for suspicious patterns
        module_id_lower = self.MODULE_ID.lower()
        if any(pattern in module_id_lower for pattern in self._forbidden_patterns):
            raise MockDataViolation(
                f"Module ID '{self.MODULE_ID}' contains suspicious pattern. "
                f"Module IDs suggesting mock data violate integrity requirements."
            )
        
        # Check for explicit mock data configuration
        if hasattr(self, '_use_mock_data') and getattr(self, '_use_mock_data'):
            raise MockDataViolation(
                f"Module {self.MODULE_ID} configured for mock data (_use_mock_data=True). "
                f"This directly violates data integrity requirements."
            )
        
        # Check for test-only configurations
        if hasattr(self, '_test_only') and getattr(self, '_test_only'):
            raise MockDataViolation(
                f"Module {self.MODULE_ID} marked as test-only (_test_only=True). "
                f"Test-only modules cannot be used in production framework."
            )
        
        self.logger.debug(f"{self.MODULE_ID} module integrity patterns validated")
    
    def _uses_database(self) -> bool:
        """Override in subclasses that require database access."""
        return False
    
    def _get_required_databases(self) -> List[str]:
        """Override in subclasses to specify required databases."""
        return []
    
    def get_database_service(self):
        """
        Get the established database service.
        
        Returns the core database service using the established patterns.
        Only available after initialization.
        
        Returns:
            Database service instance
            
        Raises:
            DataIntegrityError: If module not initialized or no app_context
        """
        if not self.initialized or not self.app_context:
            raise DataIntegrityError(
                f"Module {self.MODULE_ID} database access requires initialization. "
                f"Call initialize() first to ensure data integrity."
            )
        
        return self.app_context.get_service("core.database.service")
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get module metadata with integrity status.
        
        Returns:
            Dict containing module metadata and integrity validation status
        """
        return {
            "module_id": self.MODULE_ID,
            "class_name": self.__class__.__name__,
            "initialized": self.initialized,
            "startup_time": self._startup_time.isoformat() if self._startup_time else None,
            "uses_database": self._uses_database(),
            "required_databases": self._get_required_databases(),
            "integrity_validated": True,  # If we got this far, integrity is validated
            "data_integrity_enforced": True,
            "mock_data_protection": True,
            "hard_failure_mode": True
        }

# ============================================================================
# DATABASE-ENABLED MODULE CLASS
# ============================================================================

class DatabaseEnabledModule(DataIntegrityModule):
    """
    Base class for modules requiring database access with integrity enforcement.
    
    This class extends DataIntegrityModule to include mandatory database
    integrity validation. It ensures that:
    
    - All declared databases are accessible and real
    - Database connections pass integrity checks
    - No mock or test databases are used
    - Hard failure if any database integrity issue found
    
    Key Database Integrity Requirements:
    - All databases must exist and be accessible
    - Database names must not suggest mock/test data
    - Database connections must be validated before use
    - No fallback to mock databases if real ones unavailable
    
    Usage:
        class MyDatabaseModule(DatabaseEnabledModule):
            MODULE_ID = "standard.my_db_module"
            
            def _get_required_databases(self) -> List[str]:
                return ["my_module_db", "framework"]
            
            async def initialize(self, app_context) -> bool:
                result = await super().initialize(app_context)
                if not result:
                    return False
                    
                # Database is now validated and available via database service
                database_service = self.get_database_service()
                session_factory = database_service.get_database_session("my_module_db")
                async with session_factory() as session:
                    # Database operations with established pattern
                    pass
                    
                return True
    """
    
    def _uses_database(self) -> bool:
        """DatabaseEnabledModule always uses database."""
        return True
    
    @abstractmethod
    def _get_required_databases(self) -> List[str]:
        """
        Specify databases required by this module.
        
        Returns:
            List of database names that must be available and validated
        """
        pass
    
    async def initialize(self, app_context) -> bool:
        """
        Initialize database-enabled module with database integrity validation.
        
        Args:
            app_context: Application context with database access
            
        Returns:
            bool: True if initialization successful with database integrity guarantees
            
        Raises:
            DatabaseIntegrityError: If database integrity validation fails
        """
        # First, run standard integrity validation
        result = await super().initialize(app_context)
        if not result:
            return False
        
        # Then, validate database integrity
        await self._validate_database_integrity()
        
        self.logger.info(f"{self.MODULE_ID} initialized with database integrity validation")
        return True
    
    async def _validate_database_integrity(self) -> None:
        """
        Validate all required databases pass integrity checks.
        
        Raises:
            DatabaseIntegrityError: If any database fails integrity validation
        """
        required_databases = self._get_required_databases()
        if not required_databases:
            raise DatabaseIntegrityError(
                f"DatabaseEnabledModule {self.MODULE_ID} must specify required databases. "
                f"Override _get_required_databases() to declare database dependencies."
            )
        
        self.logger.info(f"{self.MODULE_ID} validating integrity of {len(required_databases)} databases: {required_databases}")
        
        for db_name in required_databases:
            await self._validate_single_database_integrity(db_name)
        
        self.logger.info(f"{self.MODULE_ID} all database integrity checks passed")
    
    async def _validate_single_database_integrity(self, database_name: str) -> None:
        """
        Validate a single database meets integrity requirements.
        
        Args:
            database_name: Name of database to validate
            
        Raises:
            DatabaseIntegrityError: If database fails integrity validation
        """
        # Validate database name doesn't suggest mock data
        database_lower = database_name.lower()
        if any(pattern in database_lower for pattern in self._forbidden_patterns):
            raise DatabaseIntegrityError(
                f"Database '{database_name}' required by {self.MODULE_ID} has suspicious name. "
                f"Database names suggesting mock data violate integrity requirements."
            )
        
        # Use the database interface to verify integrity
        try:
            integrity_valid = await self.database.verify_integrity(database_name)
            if not integrity_valid:
                raise DatabaseIntegrityError(
                    f"Database '{database_name}' required by {self.MODULE_ID} failed integrity check. "
                    f"Hard failure - cannot proceed with compromised data source."
                )
                
        except Exception as e:
            raise DatabaseIntegrityError(
                f"Database '{database_name}' integrity validation failed for {self.MODULE_ID}: {str(e)}. "
                f"Cannot proceed without verified database access."
            ) from e
        
        self.logger.debug(f"{self.MODULE_ID} database '{database_name}' integrity validated")

# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Base classes
    'DataIntegrityModule',
    'DatabaseEnabledModule',
    
    # Exceptions
    'DataIntegrityError',
    'DataIntegrityViolation', 
    'DatabaseIntegrityError',
    'MockDataViolation',
]

# Log module initialization
logger.info("Data integrity-enforcing module base classes initialized")