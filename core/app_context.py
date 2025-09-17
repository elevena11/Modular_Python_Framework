"""
/core/app_context.py
Updated: April 1, 2025
Added shutdown handler support
"""

import logging
import asyncio
import random
import uuid
from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from typing import Dict, List, Any, Callable, Awaitable, Optional, Union
from core.error_utils import error_message

class AppContext:
    """Application context shared with all modules."""
    
    def __init__(self, config):
        """Initialize the application context with configuration."""
        self.config = config
        self.logger = logging.getLogger("app.context")
        
        # Generate unique session identifier for this app instance
        self.session_uuid = str(uuid.uuid4())
        self.session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.session_uuid[:8]}"
        self.session_start_time = datetime.now()
        
        self.api_router = None
        self.db_engine = None
        self.db_session = None
        self.services = {}
        self.module_loader = None  # Will be set after ModuleLoader is created
        self.post_init_hooks = {}  # Store post-initialization hooks
        self.startup_warnings = []  # Store warnings to display during startup
        self._shutdown_handlers = []  # Store shutdown handlers
        
        # SQLite retry configuration
        self.max_retries = 5
        self.retry_delay_base = 0.1  # Base delay in seconds
        self.retry_delay_max = 2.0   # Maximum delay in seconds
        
        # Log session start
        self.logger.info(f"Application session started: {self.session_id}")
        

    def initialize(self):
        """Initialize the application context."""
        # Setup SQLite database
        self._initialize_sqlite()
        
        # Create API router
        self.api_router = APIRouter(prefix=self.config.API_PREFIX)
        
    def _initialize_sqlite(self):
        """Initialize SQLite database with async engine."""
        # Check if database URL is empty and load from config or set default
        if not self.config.DATABASE_URL:
            self.config.DATABASE_URL = self._load_db_url_from_config()
            self.logger.info(f"Using database URL from config: {self.config.DATABASE_URL}")
        
        self.logger.info(f"Initializing SQLite database: {self.config.DATABASE_URL}")
        
        # Ensure database directory exists
        if self.config.DATABASE_URL.startswith("sqlite:///"):
            import os
            db_path = self.config.DATABASE_URL[10:]  # Remove 'sqlite:///' prefix
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
                self.logger.info(f"Created database directory: {db_dir}")
        
        # Set up async engine for the FastAPI application
        self._setup_sqlite_async_engine()
        
        self.logger.info("SQLite async database engine and session factory created")

    def _load_db_url_from_config(self):
        """Load database URL from config file or use default."""
        try:
            import os
            import json
            db_config_path = os.path.join(self.config.DATA_DIR, "db_config.json")
            if os.path.exists(db_config_path):
                with open(db_config_path, 'r') as f:
                    db_config = json.load(f)
                    if "database_url" in db_config and db_config["database_url"]:
                        return db_config["database_url"]
        except Exception as e:
            self.logger.error(error_message(
                module_id="core.app_context",
                error_type="DATABASE_URL_LOAD_FAILED",
                details=f"Error loading database URL from config: {str(e)}",
                location="initialize()",
                context={"exception_type": type(e).__name__}
            ))
        
        # Default SQLite path if config loading fails - directory for all databases
        # Build absolute directory path (no filename needed)
        import os
        data_dir = os.path.abspath(self.config.DATA_DIR)
        db_dir = os.path.join(data_dir, "database")
        default_url = f"sqlite:///{db_dir}/"
        self.logger.info(f"Using default database URL: {default_url}")
        return default_url
    
    def _setup_sqlite_async_engine(self):
        """Set up the asynchronous SQLite engine."""
        # Convert URL to aiosqlite format
        async_url = self.config.DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///')
        
        # Create async engine with proper pool configuration
        self.db_engine = create_async_engine(
            async_url,
            echo=False,               # Don't log all SQL
            future=True,
            # Connection pool configuration
            pool_size=20,             # Allow many concurrent connections
            max_overflow=10,          # Allow temporary overflow beyond pool_size
            pool_timeout=30,          # Wait up to 30 seconds for connection
            pool_recycle=3600,        # Recycle connections after an hour
            pool_pre_ping=True,       # Check connection health before using
            connect_args={
                "check_same_thread": False  # Allow multi-threaded access
            }
        )
        
        # Create async session factory
        self.db_session = async_sessionmaker(
            bind=self.db_engine,
            expire_on_commit=False,
            class_=AsyncSession
        )
    
    # PostgreSQL support has been removed - SQLite only
    
    async def execute_with_retry(self, coro, retries=None, retry_delay=None):
        """
        Execute a coroutine with retry logic for SQLite concurrent access issues.
        
        Args:
            coro: The coroutine to execute
            retries: Number of retries (uses self.max_retries if None)
            retry_delay: Base delay between retries (uses self.retry_delay_base if None)
            
        Returns:
            The result of the coroutine execution
            
        Raises:
            The last encountered exception if all retries fail
        """
        attempts = 0
        max_retries = self.max_retries if retries is None else retries
        delay_base = self.retry_delay_base if retry_delay is None else retry_delay
        last_error = None
        
        while attempts <= max_retries:
            try:
                return await coro
            except OperationalError as e:
                # Check if this is a database locked error
                if "database is locked" in str(e).lower():
                    attempts += 1
                    if attempts > max_retries:
                        self.logger.error(error_message(
                            module_id="core.app_context",
                            error_type="DATABASE_MAX_RETRIES_EXCEEDED",
                            details=f"Max retries exceeded ({max_retries}) for database operation",
                            location="with_retry()",
                            context={"max_retries": max_retries, "attempts": attempts}
                        ))
                        raise
                    
                    # Calculate exponential backoff with jitter
                    delay = min(delay_base * (2 ** (attempts - 1)) * (0.5 + random.random()), 
                               self.retry_delay_max)
                    
                    self.logger.warning(error_message(
                        module_id="core.app_context",
                        error_type="DATABASE_LOCKED_RETRY",
                        details=f"Database locked, retrying in {delay:.2f}s (attempt {attempts}/{max_retries})",
                        location="with_retry()",
                        context={"delay": delay, "attempts": attempts, "max_retries": max_retries}
                    ))
                    await asyncio.sleep(delay)
                    last_error = e
                else:
                    # Re-raise if it's not a locking issue
                    raise
            except Exception as e:
                # Re-raise other exceptions immediately
                self.logger.error(error_message(
                    module_id="core.app_context",
                    error_type="DATABASE_OPERATION_ERROR",
                    details=f"Error executing database operation: {str(e)}",
                    location="with_retry()",
                    context={"exception_type": type(e).__name__}
                ))
                raise
        
        # We shouldn't get here, but just in case
        if last_error:
            raise last_error
            
    async def get_db(self):
        """Database session dependency for FastAPI."""
        db = self.db_session()
        try:
            yield db
        finally:
            await db.close()  # Note the await
            
    def register_service(self, name, service):
        """Register a service for use by other modules."""
        # Extract module name from service name for consistent formatting
        module_name = name.split('.service')[0] if '.service' in name else name
        self.logger.info(f"{module_name}: Registering service")
        self.services[name] = service
        
    def register_pydantic_model(self, module_id: str, model_class):
        """
        Phase 1: Register Pydantic settings model from module.
        
        This collects all Pydantic models during Phase 1 so that the settings 
        service can request them all during Phase 2 initialization.
        
        Args:
            module_id: Module identifier (e.g., "core.model_manager")
            model_class: Pydantic model class with defaults and validation
        """
        if not hasattr(self, 'registered_pydantic_models'):
            self.registered_pydantic_models = {}
            
        self.registered_pydantic_models[module_id] = model_class
        self.logger.info(f"{module_id}: Registered Pydantic settings model")
        
    def get_registered_pydantic_models(self):
        """
        Phase 2: Get all registered Pydantic models for settings service.
        
        Returns:
            Dict[str, Type]: Dictionary of module_id -> Pydantic model class
        """
        if not hasattr(self, 'registered_pydantic_models'):
            self.registered_pydantic_models = {}
            
        return self.registered_pydantic_models.copy()
        
    def get_service(self, name):
        """Get a registered service by name."""
        if name not in self.services:
            self.logger.warning(error_message(
                module_id="core.app_context",
                error_type="SERVICE_NOT_FOUND",
                details=f"Service '{name}' not found",
                location="get_service()",
                context={"service_name": name, "available_services": list(self.services.keys())}
            ))
            return None
        return self.services[name]
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information for the current app instance."""
        uptime = datetime.now() - self.session_start_time
        return {
            "session_id": self.session_id,
            "session_uuid": self.session_uuid,
            "session_start_time": self.session_start_time.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime)
        }
    
    def register_post_init_hook(self, name: str, hook: Callable[[Any], Awaitable[None]],
                               priority: int = 100, dependencies: Optional[List[str]] = None):
        """
        Register a function to be called after all modules are initialized
        but before the application starts serving requests.
        
        Args:
            name: Unique name for the hook
            hook: Async function to call with the app_context as parameter
            priority: Priority (lower number = higher priority)
            dependencies: List of hook names this hook depends on
        """
        # Extract module name from hook name for consistent formatting
        if '.' in name:
            module_name = '.'.join(name.split('.')[:2])  # e.g., 'core.database' from 'core.database.setup'
            hook_type = name.split('.')[-1] if len(name.split('.')) > 2 else 'hook'
            self.logger.info(f"{module_name}: Registering post-initialization hook - {hook_type}")
        else:
            self.logger.info(f"{name}: Registering post-initialization hook")
        self.post_init_hooks[name] = {
            "function": hook,
            "priority": priority,
            "dependencies": dependencies or []
        }

    def register_models(self, model_classes, database="framework"):
        """
        Register SQLAlchemy model classes with a specific database.
        
        Args:
            model_classes: List of SQLAlchemy model classes
            database: Target database name ("framework", "llm_memory", etc.)
        """
        if not hasattr(self, 'registered_models'):
            self.registered_models = {}  # Changed to dict: {database_name: [models]}
        
        if database not in self.registered_models:
            self.registered_models[database] = []
        
        # Add detailed logging
        for model_class in model_classes:
            model_name = model_class.__name__
            table_name = getattr(model_class, '__tablename__', 'unknown')
            base_class = model_class.__base__.__name__
            
            self.logger.info(f"Registering model class: {model_name}, table: {table_name}, base class: {base_class}, database: {database}")
            
            # Check if it's using our Base
            if hasattr(self, 'db_base'):
                is_using_db_base = model_class.__base__ is self.db_base
                self.logger.info(f"Model {model_name} using app_context.db_base: {is_using_db_base}")
        
        self.registered_models[database].extend(model_classes)
        total_models = sum(len(models) for models in self.registered_models.values())
        self.logger.info(f"Registered {len(model_classes)} models for {database} database. Total registered models: {total_models}")
    
    def register_database_requirement(self, database_name: str):
        """
        Register that a module needs its own database.
        
        Args:
            database_name: Name of the required database
        """
        if not hasattr(self, 'required_databases'):
            self.required_databases = set()
        
        if database_name not in self.required_databases:
            self.required_databases.add(database_name)
            self.logger.info(f"Registered database requirement: {database_name}")
    
    def get_required_databases(self):
        """
        Get all databases that modules have requested.
        
        Returns:
            List of database names including framework
        """
        databases = ["framework"]  # Always include framework
        if hasattr(self, 'required_databases'):
            databases.extend(sorted(self.required_databases))
        return databases
    
    def get_module_instance(self, module_id: str):
        """
        Get the module instance for decorator-based modules.
        
        Args:
            module_id: ID of the module (e.g., 'core.database')
            
        Returns:
            Module instance if found, None otherwise
        """
        # New ModuleManager system
        if hasattr(self, 'module_manager') and self.module_manager:
            return self.module_manager.instances.get(module_id)
        
        # Legacy module_loader system (fallback)
        if hasattr(self, 'module_loader') and self.module_loader:
            if module_id in self.module_loader.modules:
                return self.module_loader.modules[module_id].get("instance")
        return None
    
    def register_module_setup_hook(self, module_id: str, setup_method: Callable, 
                                  priority: int = 100):
        """
        Register a module's secondary initialization method.
        
        Args:
            module_id: ID of the module (e.g., 'core.database')
            setup_method: Method to call for secondary initialization
            priority: Priority level (lower number = higher priority)
        """
        hook_name = f"{module_id}.setup"
        
        # No automatic dependencies - let modules specify their own dependencies
        dependencies = []
        
        self.register_post_init_hook(hook_name, setup_method, priority, dependencies)
        self.logger.info(f"{module_id}: Registered secondary initialization")
    
    def add_warning(self, message: str, level: str = "warning", module_id: str = None):
        """
        Add a warning message to be displayed during startup.
        
        Args:
            message: The warning message
            level: Message level (info, warning, critical)
            module_id: ID of the module registering the warning
        """
        self.startup_warnings.append({
            "message": message,
            "level": level,
            "module_id": module_id or "system"
        })
        
        # Also log it immediately
        log_level = logging.WARNING
        if level == "critical":
            log_level = logging.CRITICAL
        elif level == "info":
            log_level = logging.INFO
            
        self.logger.log(log_level, f"[{module_id or 'system'}] {message}")
    
    # Enhanced settings management methods - CONVERTED TO ASYNC
    async def register_module_settings(self, 
                                     module_id: str, 
                                     default_settings: Dict[str, Any],
                                     validation_schema: Optional[Dict[str, Any]] = None,
                                     ui_metadata: Optional[Dict[str, Any]] = None,
                                     version: Optional[str] = None) -> bool:
        """
        Register default settings for a module with enhanced features.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            default_settings: Dictionary of default settings
            validation_schema: Validation rules for settings
            ui_metadata: UI-specific metadata for settings
            version: Version string for settings schema
            
        Returns:
            True if settings were registered, False otherwise
            
        Raises:
            ValidationError: If settings fail validation
        """
        # Get the settings service
        settings_service = self.get_service("core.settings.service")
        
        if settings_service:
            try:
                return await settings_service.register_module_settings(
                    module_id, 
                    default_settings,
                    validation_schema,
                    ui_metadata,
                    version
                )
            except Exception as e:
                self.logger.error(error_message(
                    module_id="core.app_context",
                    error_type="SETTINGS_REGISTRATION_ERROR",
                    details=f"Error registering settings for {module_id}: {str(e)}",
                    location="register_pydantic_model()",
                    context={"target_module_id": module_id, "exception_type": type(e).__name__}
                ))
                return False
        else:
            self.logger.warning(error_message(
                module_id="core.app_context",
                error_type="SETTINGS_SERVICE_UNAVAILABLE_REGISTER",
                details=f"Cannot register settings for {module_id} - settings service not available",
                location="register_pydantic_model()",
                context={"target_module_id": module_id}
            ))
            
            # Add a post-init hook to register settings once the service is available
            if hasattr(self, 'post_init_hooks'):
                hook_name = f"{module_id}.register_settings"
                
                # Create an async function that will pass all parameters
                async def register_settings_hook(app_ctx):
                    settings_service = app_ctx.get_service("core.settings.service")
                    if settings_service:
                        return await settings_service.register_module_settings(
                            module_id, 
                            default_settings,
                            validation_schema,
                            ui_metadata,
                            version
                        )
                    return False
                
                self.register_post_init_hook(
                    hook_name,
                    register_settings_hook,
                    priority=10,  # High priority to ensure settings are registered early
                    dependencies=["settings_service.initialize"]  # Depend on settings service initialization
                )
                self.logger.info(f"Registered post-init hook for {module_id} settings")
            
            return False
    
    async def get_module_settings(self, module_id: str) -> Dict[str, Any]:
        """
        Get settings for a module with all overrides applied.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            
        Returns:
            Dictionary of settings or empty dict if settings service unavailable
        """
        settings_service = self.get_service("core.settings.service")
        
        if settings_service:
            return await settings_service.get_module_settings(module_id)
        else:
            self.logger.warning(error_message(
                module_id="core.app_context",
                error_type="SETTINGS_SERVICE_UNAVAILABLE_GET",
                details=f"Cannot get settings for {module_id} - settings service not available",
                location="get_settings()",
                context={"target_module_id": module_id}
            ))
            return {}
    
    async def update_module_setting(self, 
                                  module_id: str, 
                                  key: str, 
                                  value: Any, 
                                  use_client_config: bool = True,
                                  validate: bool = True) -> bool:
        """
        Update a setting value for a module with optional validation.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            key: Setting key
            value: Setting value
            use_client_config: If True, store in client config, otherwise in settings.json
            validate: Whether to validate the setting
            
        Returns:
            True if setting was updated, False otherwise
        """
        settings_service = self.get_service("core.settings.service")
        
        if settings_service:
            try:
                return await settings_service.update_module_setting(
                    module_id, key, value, use_client_config, validate
                )
            except Exception as e:
                self.logger.error(error_message(
                    module_id="core.app_context",
                    error_type="SETTING_UPDATE_ERROR",
                    details=f"Error updating setting {key} for {module_id}: {str(e)}",
                    location="update_setting()",
                    context={"target_module_id": module_id, "setting_key": key, "exception_type": type(e).__name__}
                ))
                return False
        else:
            self.logger.warning(error_message(
                module_id="core.app_context",
                error_type="SETTINGS_SERVICE_UNAVAILABLE_UPDATE",
                details=f"Cannot update setting for {module_id} - settings service not available",
                location="update_setting()",
                context={"target_module_id": module_id}
            ))
            return False
    
    async def reset_module_setting(self, module_id: str, key: str) -> bool:
        """
        Reset a module setting to its default value by removing any client overrides.
        
        Args:
            module_id: Module identifier (e.g., 'core.database')
            key: Setting key
            
        Returns:
            True if setting was reset, False otherwise
        """
        settings_service = self.get_service("core.settings.service")
        
        if settings_service:
            return await settings_service.reset_module_setting(module_id, key)
        else:
            self.logger.warning(error_message(
                module_id="core.app_context",
                error_type="SETTINGS_SERVICE_UNAVAILABLE_RESET",
                details=f"Cannot reset setting for {module_id} - settings service not available",
                location="reset_setting()",
                context={"target_module_id": module_id}
            ))
            return False
    
    async def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings for all modules.
        
        Returns:
            Dictionary of all settings or empty dict if settings service unavailable
        """
        settings_service = self.get_service("core.settings.service")
        
        if settings_service:
            return await settings_service.get_all_settings()
        else:
            self.logger.warning(error_message(
                module_id="core.app_context",
                error_type="SETTINGS_SERVICE_UNAVAILABLE_GET_ALL",
                details="Cannot get all settings - settings service not available",
                location="get_all_settings()",
                context={}
            ))
            return {}
    
    # UI Metadata methods - CONVERTED TO ASYNC
    async def get_settings_ui_metadata(self, module_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get UI metadata for module settings.
        
        Args:
            module_id: Optional module identifier for specific metadata
            
        Returns:
            Dictionary of UI metadata
        """
        settings_service = self.get_service("core.settings.service")
        
        if settings_service and hasattr(settings_service, "get_ui_metadata"):
            return await settings_service.get_ui_metadata(module_id)
        else:
            self.logger.warning(error_message(
                module_id="core.app_context",
                error_type="SETTINGS_SERVICE_UNAVAILABLE_UI_METADATA",
                details="Cannot get UI metadata - settings service not available or outdated",
                location="get_settings_ui_metadata()",
                context={}
            ))
            return {}
    
    # Migration methods - CONVERTED TO ASYNC
    async def register_settings_migration(self, 
                                        module_id: str,
                                        from_version: str,
                                        to_version: str,
                                        migration_function: Callable[[Dict[str, Any]], Dict[str, Any]]) -> bool:
        """
        Register a migration function for settings.
        
        Args:
            module_id: Module identifier
            from_version: Source version
            to_version: Target version
            migration_function: Function that transforms old settings to new format
            
        Returns:
            True if migration was registered, False otherwise
        """
        settings_service = self.get_service("core.settings.service")
        
        if settings_service and hasattr(settings_service, "register_settings_migration"):
            return await settings_service.register_settings_migration(
                module_id, from_version, to_version, migration_function
            )
        else:
            self.logger.warning(error_message(
                module_id="core.app_context",
                error_type="SETTINGS_SERVICE_UNAVAILABLE_MIGRATION",
                details="Cannot register settings migration - settings service not available or outdated",
                location="register_settings_migration()",
                context={}
            ))
            return False
    
    # Phase 4: Database integrity interface
    @property
    def database(self):
        """
        Phase 4: Clean database access interface.
        
        Provides access to database service through app_context.database.integrity_session()
        pattern, replacing deprecated get_database_session() calls.
        
        Returns:
            Database service with integrity_session method
        """
        database_service = self.get_service("core.database.service")
        if not database_service:
            raise RuntimeError("Database service not available. Ensure core.database module is loaded.")
        return database_service
    
    # Shutdown handler management
    def register_shutdown_handler(self, handler: Callable[[], Awaitable[None]]) -> None:
        """
        Register a handler to be called when the application shuts down.
        
        Args:
            handler: Async function to be called during shutdown
        """
        if not hasattr(self, "_shutdown_handlers"):
            self._shutdown_handlers = []
        
        self.logger.info(f"Registering shutdown handler: {handler.__name__ if hasattr(handler, '__name__') else 'anonymous'}")
        self._shutdown_handlers.append(handler)
    
    async def run_shutdown_handlers(self) -> None:
        """
        Run all registered shutdown handlers.
        
        This should be called by the application during shutdown.
        """
        # Log session end
        session_uptime = datetime.now() - self.session_start_time
        self.logger.info(f"Application session ending: {self.session_id} (uptime: {session_uptime})")
        
        if not hasattr(self, "_shutdown_handlers"):
            return
            
        self.logger.info(f"Running {len(self._shutdown_handlers)} shutdown handlers")
        
        for handler in self._shutdown_handlers:
            try:
                await handler()
            except Exception as e:
                self.logger.error(error_message(
                    module_id="core.app_context",
                    error_type="SHUTDOWN_HANDLER_ERROR",
                    details=f"Error in shutdown handler: {str(e)}",
                    location="shutdown()",
                    context={"exception_type": type(e).__name__}
                ))
                
        self.logger.info("All shutdown handlers completed")

    def force_shutdown(self):
        """
        Force shutdown of app context when the event loop is closing or closed.
        This calls synchronous force_shutdown methods on registered services.
        """
        self.logger.info("Performing force shutdown of app context")
        
        # Call force_shutdown on services that support it
        for name, service in self.services.items():
            if hasattr(service, 'force_shutdown'):
                try:
                    # Extract module name from service name for consistent formatting
                    module_name = name.split('.service')[0] if '.service' in name else name
                    self.logger.info(f"{module_name}: Force shutting down service")
                    service.force_shutdown()
                except Exception as e:
                    self.logger.error(error_message(
                        module_id="core.app_context",
                        error_type="FORCE_SHUTDOWN_ERROR",
                        details=f"Error during force shutdown of {name}: {str(e)}",
                        location="force_shutdown()",
                        context={"service_name": name, "exception_type": type(e).__name__}
                    ))
        
        self.logger.info("App context force shutdown completed")

    async def run_decorator_shutdown_handlers(self) -> None:
        """
        Execute decorator-configured shutdown methods with centralized logging.
        This implements the decorator-based shutdown architecture.
        """
        if not hasattr(self, '_shutdown_metadata'):
            self.logger.debug("No decorator-based shutdown handlers registered")
            return
            
        import asyncio
        from core.decorators import list_shutdown_modules
        
        # Get all modules with shutdown configuration, sorted by priority
        shutdown_modules = []
        for module_id, metadata in self._shutdown_metadata.items():
            module_class = metadata['module_class']
            shutdown_config = metadata['shutdown_config']
            
            shutdown_modules.append({
                'module_id': module_id,
                'class': module_class,
                'shutdown': shutdown_config
            })
        
        # Sort by priority (lower number = higher priority = shutdown earlier)
        shutdown_modules.sort(key=lambda x: x['shutdown'].get('graceful', {}).get('priority', 100))
        
        self.logger.info(f"Executing decorator-based shutdown for {len(shutdown_modules)} modules")
        
        # Execute graceful shutdown with centralized logging
        for module_info in shutdown_modules:
            module_id = module_info['module_id']
            shutdown_config = module_info['shutdown']
            
            # Skip if no graceful shutdown configured
            if 'graceful' not in shutdown_config:
                continue
                
            graceful_config = shutdown_config['graceful']
            method_name = graceful_config.get('method', 'shutdown')
            timeout = graceful_config.get('timeout', 30)
            
            # CENTRALIZED LOGGING - Start
            self.logger.info(f"{module_id}: Shutting down service gracefully...")
            
            try:
                # Get the service instance
                service_key = f"{module_id}.service"
                if service_key in self.services:
                    service_instance = self.services[service_key]
                    
                    # Get the shutdown method
                    if hasattr(service_instance, method_name):
                        shutdown_method = getattr(service_instance, method_name)
                        
                        # Execute with timeout
                        await asyncio.wait_for(shutdown_method(), timeout=timeout)
                        
                        # CENTRALIZED LOGGING - Success
                        self.logger.info(f"{module_id}: Service shutdown complete")
                    else:
                        self.logger.warning(error_message(
                            module_id="core.app_context",
                            error_type="SHUTDOWN_METHOD_NOT_FOUND",
                            details=f"Shutdown method '{method_name}' not found on service",
                            location="_shutdown_service()",
                            context={"target_module_id": module_id, "method_name": method_name}
                        ))
                else:
                    self.logger.warning(error_message(
                        module_id="core.app_context",
                        error_type="SHUTDOWN_SERVICE_NOT_FOUND",
                        details="Service not found for shutdown",
                        location="_shutdown_service()",
                        context={"target_module_id": module_id}
                    ))
                    
            except asyncio.TimeoutError:
                # CENTRALIZED LOGGING - Timeout
                self.logger.error(error_message(
                    module_id="core.app_context",
                    error_type="SERVICE_SHUTDOWN_TIMEOUT",
                    details=f"Service shutdown timed out after {timeout}s",
                    location="_shutdown_service()",
                    context={"target_module_id": module_id, "timeout": timeout}
                ))
            except Exception as e:
                # CENTRALIZED LOGGING - Error
                self.logger.error(error_message(
                    module_id="core.app_context",
                    error_type="SERVICE_SHUTDOWN_FAILED",
                    details=f"Service shutdown failed: {str(e)}",
                    location="_shutdown_service()",
                    context={"target_module_id": module_id, "exception_type": type(e).__name__}
                ))
        
        self.logger.info("Decorator-based shutdown handlers completed")

    def run_decorator_force_shutdown(self):
        """
        Execute decorator-configured force shutdown methods with centralized logging.
        This runs synchronously for use during event loop shutdown.
        """
        if not hasattr(self, '_shutdown_metadata'):
            self.logger.debug("No decorator-based force shutdown handlers registered")
            return
        
        self.logger.info("Executing decorator-based force shutdown")
        
        # Process all modules with force shutdown
        for module_id, metadata in self._shutdown_metadata.items():
            shutdown_config = metadata['shutdown_config']
            
            # Skip if no force shutdown configured
            if 'force' not in shutdown_config:
                continue
                
            force_config = shutdown_config['force']
            method_name = force_config.get('method', 'force_shutdown')
            timeout = force_config.get('timeout', 5)
            
            # CENTRALIZED LOGGING - Start
            self.logger.info(f"{module_id}: Force shutting down service")
            
            try:
                # Get the service instance
                service_key = f"{module_id}.service"
                if service_key in self.services:
                    service_instance = self.services[service_key]
                    
                    # Get the force shutdown method
                    if hasattr(service_instance, method_name):
                        force_method = getattr(service_instance, method_name)
                        
                        # Execute force shutdown (synchronous)
                        force_method()
                        
                        # CENTRALIZED LOGGING - Success
                        self.logger.info(f"{module_id}: Service force shutdown complete")
                    else:
                        self.logger.warning(error_message(
                            module_id="core.app_context",
                            error_type="FORCE_SHUTDOWN_METHOD_NOT_FOUND",
                            details=f"Force shutdown method '{method_name}' not found on service",
                            location="_force_shutdown_service()",
                            context={"target_module_id": module_id, "method_name": method_name}
                        ))
                else:
                    self.logger.warning(error_message(
                        module_id="core.app_context",
                        error_type="FORCE_SHUTDOWN_SERVICE_NOT_FOUND",
                        details="Service not found for force shutdown",
                        location="_force_shutdown_service()",
                        context={"target_module_id": module_id}
                    ))
                    
            except Exception as e:
                # CENTRALIZED LOGGING - Error
                self.logger.error(error_message(
                    module_id="core.app_context",
                    error_type="SERVICE_FORCE_SHUTDOWN_FAILED",
                    details=f"Service force shutdown failed: {str(e)}",
                    location="_force_shutdown_service()",
                    context={"target_module_id": module_id, "exception_type": type(e).__name__}
                ))
        
        self.logger.info("Decorator-based force shutdown completed")
