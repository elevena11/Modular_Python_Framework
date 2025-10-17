"""
app.py
Updated: 2025-08-11
Clean Natural Module System Implementation
"""

import os
import logging
import uvicorn
import traceback
import importlib
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.app_context import AppContext
from core.module_manager import ModuleManager
from core.config import settings
from core.logging import setup_framework_logging
from core.bootstrap import run_bootstrap_phase
from core.version import get_framework_version

# Initialize framework-aware logging first
setup_framework_logging()

# Initialize logging - ensure logs directory exists
os.makedirs(os.path.join("data", "logs"), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(levelname)s %(asctime)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join("data", "logs", "app.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(settings.APP_NAME)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    try:
        # Startup
        logger.info(f"Starting {settings.APP_NAME} v{get_framework_version()}...")
        logger.info(f"Data directory: {settings.DATA_DIR}")
        
        # Create app context with clean service container
        app_context = AppContext(settings)
        app.state.app_context = app_context
        
        # Bootstrap phase: Create directories and databases
        logger.info("Running Bootstrap Phase...")
        bootstrap_success = await run_bootstrap_phase(app_context)
        if not bootstrap_success:
            logger.error("Bootstrap phase failed - cannot start application")
            raise RuntimeError("Bootstrap failed")
        
        # Load application modules
        logger.info("Starting Module System...")
        module_manager = ModuleManager(app_context)
        app_context.module_manager = module_manager  # Make it accessible to app_context methods
        
        # Discover available modules
        modules = await module_manager.discover_modules()
        logger.info(f"Discovered {len(modules)} modules")
        
        # Initialize discovered modules
        await module_manager.load_modules(modules)
        
        # Register module API routers with main FastAPI app
        routers = module_manager.processor.get_registered_routers()
        for router_info in routers:
            try:
                # Import the router from the module
                module_class = router_info['module_class']
                router_name = router_info['router_name']
                prefix = router_info['prefix']
                module_id = router_info['module_id']
                
                # Get the router from the module
                router = getattr(module_class.__module__, router_name, None)
                if router is None:
                    # Try to import from the module file
                    module_file = importlib.import_module(module_class.__module__)
                    router = getattr(module_file, router_name, None)
                
                if router is not None:
                    # Include the router in the main app
                    app.include_router(router, prefix=prefix)
                    logger.info(f"{module_id}: Registered API router '{router_name}' at '{prefix}'")
                else:
                    logger.warning(f"{module_id}: Router '{router_name}' not found in module")
                    
            except Exception as e:
                logger.error(f"{router_info['module_id']}: Failed to register router - {e}")
        
        logger.info(f"{settings.APP_NAME} v{get_framework_version()} started successfully")
        logger.info(f"Uvicorn server starting on http://{settings.HOST}:{settings.PORT}")
        logger.info("Application startup complete - Ready to serve requests")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        # Shutdown
        logger.info("Application shutting down...")
        
        # Execute decorator-based shutdown handlers for proper resource cleanup
        try:
            if hasattr(app, 'state') and hasattr(app.state, 'app_context'):
                app_context = app.state.app_context
                await app_context.run_decorator_shutdown_handlers()
        except Exception as e:
            logger.error(f"Error during decorator shutdown handlers: {e}")
            
        # Force cleanup in case of emergency
        try:
            if hasattr(app, 'state') and hasattr(app.state, 'app_context'):
                app_context = app.state.app_context
                app_context.run_decorator_force_shutdown()
        except Exception as e:
            logger.error(f"Error during force shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description=f"{settings.APP_NAME} - Truth Verification System",
    version=get_framework_version(),
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": get_framework_version(),
        "status": "running",
        "message": f"{settings.APP_NAME} API is operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": get_framework_version()
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )