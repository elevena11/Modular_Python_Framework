"""
modules/core/scheduler/components/housekeeper.py
Updated: April 6, 2025
Housekeeper component for centralized cleanup management
"""

import os
import logging
import glob
import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from core.error_utils import error_message, Result

# Module identity - must match manifest.json
MODULE_ID = "core.scheduler"
# Component identity
COMPONENT_ID = f"{MODULE_ID}.housekeeper"
logger = logging.getLogger(COMPONENT_ID)

class Housekeeper:
    """
    Provides centralized management of temporary files and logs that require periodic cleanup.
    
    The Housekeeper component allows modules to register directories for periodic cleanup
    based on various retention policies (age, count, size). It maintains a registry of
    cleanup configurations in the database and executes cleanup operations according
    to the schedule.
    """
    
    def __init__(self, app_context, job_manager):
        """
        Initialize the housekeeper component.
        
        Args:
            app_context: Application context
            job_manager: Scheduler's job manager component
        """
        self.app_context = app_context
        self.job_manager = job_manager
        self.logger = logger
        self.db_ops = None  # Will be set during initialization
        self.initialized = False
    
    async def initialize(self, db_operations) -> bool:
        """
        Initialize the housekeeper with database operations.
        
        Args:
            db_operations: Database operations instance
                
        Returns:
            bool: Whether initialization was successful
        """
        if self.initialized:
            return True
                
        self.db_ops = db_operations
        if not self.db_ops:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_OPS_REQUIRED",
                details="Database operations required for Housekeeper initialization"
            ))
            return False
        
        # Get settings
        settings = await self.app_context.get_module_settings(MODULE_ID)
        
        # Check if housekeeper is enabled
        if not settings.get("housekeeper_enabled", True):
            self.logger.info("Housekeeper component disabled in settings")
            return True  # Still mark as initialized but won't run
        
        # First, check if the housekeeping job already exists
        schedule = settings.get("housekeeper_schedule", "0 3 * * *")  # Default: 3 AM daily
        
        existing_jobs_result = await self.db_ops.get_events({
            "name": "Job system_housekeeping",
            "function_name": "run_scheduled_cleanup"
        })

        existing_jobs_list = []
        job_count = 0

        if existing_jobs_result.success:
            existing_jobs_list = existing_jobs_result.data
            if isinstance(existing_jobs_list, list):
                job_count = len(existing_jobs_list)
                self.logger.info(f"Found {job_count} existing system housekeeping jobs")
            else:
                self.logger.warning(error_message(
                    module_id=COMPONENT_ID,
                    error_type="DB_DATA_MISMATCH",
                    details=f"get_events returned success but data is not a list: {type(existing_jobs_result.data)}"
                ))
        elif existing_jobs_result.error:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_READ_ERROR",
                details=f"Failed to get existing housekeeping jobs: {existing_jobs_result.error}"
            ))
            # If we can't check for existing jobs, we might fail initialization or proceed cautiously.
            # Let's proceed to potentially register a new one, but log the error.

        if job_count > 0:
            
            # If there are multiple jobs, clean up duplicates
            if job_count > 1:
                self.logger.warning(f"Found {job_count} duplicate housekeeping jobs, cleaning up duplicates")
                
                # Sort jobs by creation date (newest first)
                sorted_jobs = sorted(existing_jobs_list, key=lambda j: j.get("created_at", ""), reverse=True)
                
                # Keep the newest job (first in sorted list), delete the rest
                newest_job = sorted_jobs[0]
                self.logger.info(f"Keeping newest job created at {newest_job.get('created_at')}")
                
                # Delete all other duplicates
                for job in sorted_jobs[1:]:
                    job_id = job.get("id")
                    if job_id:
                        self.logger.info(f"Removing duplicate housekeeping job: {job_id} created at {job.get('created_at')}")
                        await self.db_ops.delete_event(job_id)
                
                # Make sure the remaining job is in "pending" state
                if newest_job.get("status") != "pending":
                    await self.db_ops.update_event(
                        event_id=newest_job.get("id"),
                        updates={"status": "pending"}
                    )
                    self.logger.info(f"Updated job {newest_job.get('id')} status to pending")
        elif job_count == 0: # Only register if no jobs were found AND the DB query succeeded
            # No existing job found, register a new one
            try:
                # Register the main cleanup job
                await self.job_manager.register_job(
                    job_id="system_housekeeping",
                    func=self.run_scheduled_cleanup,
                    trigger="cron",
                    cron_expression=schedule,
                    description="System-wide cleanup of temporary files"
                )
                self.logger.info(f"Registered system housekeeping job with schedule: {schedule}")
            except Exception as e:
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="JOB_REGISTRATION_FAILED",
                    details=f"Failed to register housekeeping job: {str(e)}"
                ))
                return False
        
        self.initialized = True
        self.logger.info("Housekeeper component initialized successfully")
        return True
    
    async def register_cleanup(
        self,
        directory: str,
        pattern: str = "*",
        retention_days: Optional[int] = None,
        max_files: Optional[int] = None,
        max_size_mb: Optional[int] = None,
        priority: int = 100,
        description: Optional[str] = None,
        module_id: Optional[str] = None
    ) -> str:
        """
        Register a directory for periodic cleanup.
        
        Args:
            directory: Path to directory containing files to clean
            pattern: File matching pattern (e.g., "*.log", "temp_*")
            retention_days: Maximum age of files to keep (None = no limit)
            max_files: Maximum number of files to keep (None = no limit)
            max_size_mb: Maximum total size in MB (None = no limit)
            priority: Cleanup priority (lower = higher priority)
            description: Human-readable description
            module_id: ID of the registering module (optional)
            
        Returns:
            str: Registration ID for reference
            
        Raises:
            ValueError: If directory doesn't exist or no retention policy specified
        """
        if not self.initialized:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="NOT_INITIALIZED",
                details="Housekeeper not initialized"
            ))
            raise RuntimeError("Housekeeper not initialized")
        
        # Validate directory
        if not os.path.exists(directory) or not os.path.isdir(directory):
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_DIRECTORY",
                details=f"Directory does not exist: {directory}"
            ))
            raise ValueError(f"Directory does not exist: {directory}")
        
        # Ensure at least one retention policy is specified
        if retention_days is None and max_files is None and max_size_mb is None:
            # Use default retention days from settings
            settings = await self.app_context.get_module_settings(MODULE_ID)
            retention_days = settings.get("housekeeper_default_retention", 30)
            self.logger.info(f"No retention policy specified, using default: {retention_days} days")
        
        # Determine module_id if not provided
        if not module_id:
            # Try to determine from calling context
            # This is simplified - in practice you might need a more robust method
            module_id = "unknown"
        
        # Create a unique ID for this registration
        registration_id = str(uuid.uuid4())
        
        # Register in database
        success = await self.db_ops.create_cleanup_config(
            id=registration_id,
            directory=directory,
            pattern=pattern,
            retention_days=retention_days,
            max_files=max_files,
            max_size_mb=max_size_mb,
            priority=priority,
            description=description,
            module_id=module_id
        )
        
        if not success:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="REGISTRATION_FAILED",
                details=f"Failed to register cleanup for {directory}"
            ))
            raise RuntimeError(f"Failed to register cleanup for {directory}")
        
        self.logger.info(f"Registered cleanup for {directory} with ID {registration_id}")
        return registration_id
    
    async def update_cleanup_config(self, registration_id: str, **config_updates) -> bool:
        """
        Update an existing cleanup configuration.
        
        Args:
            registration_id: ID of the registration to update
            **config_updates: Key-value pairs of settings to update
            
        Returns:
            bool: Whether the update was successful
        """
        if not self.initialized:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="NOT_INITIALIZED",
                details="Housekeeper not initialized"
            ))
            return False
        
        # Update in database
        success = await self.db_ops.update_cleanup_config(
            id=registration_id,
            **config_updates
        )
        
        if not success:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="UPDATE_FAILED",
                details=f"Failed to update cleanup config {registration_id}"
            ))
            return False
        
        self.logger.info(f"Updated cleanup config {registration_id}")
        return True
    
    async def remove_cleanup_config(self, registration_id: str) -> bool:
        """
        Remove a cleanup configuration from the registry.
        
        Args:
            registration_id: ID of the registration to remove
            
        Returns:
            bool: Whether the removal was successful
        """
        if not self.initialized:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="NOT_INITIALIZED",
                details="Housekeeper not initialized"
            ))
            return False
        
        # Remove from database
        success = await self.db_ops.delete_cleanup_config(registration_id)
        
        if not success:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="REMOVAL_FAILED",
                details=f"Failed to remove cleanup config {registration_id}"
            ))
            return False
        
        self.logger.info(f"Removed cleanup config {registration_id}")
        return True
    
    async def get_cleanup_configs(self, module_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all registered cleanup configurations. Returns an empty list on error or if none found.
        
        Args:
            module_id: Optional module ID to filter by
            
        Returns:
            List[Dict[str, Any]]: List of cleanup configurations
        """
        if not self.initialized:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="NOT_INITIALIZED",
                details="Housekeeper not initialized"
            ))
            return []
        
        # Get configs from database
        filters = {"module_id": module_id} if module_id else None
        configs_result = await self.db_ops.get_cleanup_configs(filters)

        if configs_result.success:
            return configs_result.data
        else:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="DB_READ_ERROR",
                details=f"Failed to get cleanup configs: {configs_result.error}"
            ))
            return []
    
    async def run_scheduled_cleanup(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Run all scheduled cleanup operations.
        
        This is called automatically by the scheduler job.
        
        Returns:
            Dict[str, Any]: Report of cleanup operations
        """
        self.logger.info("Starting scheduled system-wide cleanup")
        
        # Get settings
        settings = await self.app_context.get_module_settings(MODULE_ID)
        
        # Check if we're in dry run mode
        dry_run = settings.get("housekeeper_dry_run", False)
        if dry_run:
            self.logger.info("Running in DRY RUN mode - no files will be deleted")
        
        # Get all cleanup configurations
        configs = await self.get_cleanup_configs()
        
        # Sort by priority (lower number = higher priority)
        configs.sort(key=lambda c: c.get("priority", 100))
        
        # Run cleanup for each config
        results = []
        for config in configs:
            try:
                result = await self._run_single_cleanup(config, dry_run)
                results.append(result)
                
                # Update last_run timestamp
                await self.db_ops.update_cleanup_config(
                    id=config["id"],
                    last_run=datetime.now()
                )
                
                # Yield control periodically
                await asyncio.sleep(0)
            except Exception as e:
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type="CLEANUP_FAILED",
                    details=f"Error running cleanup for {config.get('directory')}: {str(e)}"
                ))
                results.append({
                    "id": config.get("id"),
                    "directory": config.get("directory"),
                    "success": False,
                    "error": str(e)
                })
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_configs": len(configs),
            "successful": sum(1 for r in results if r.get("success", False)),
            "failed": sum(1 for r in results if not r.get("success", False)),
            "total_files_deleted": sum(r.get("files_deleted", 0) for r in results if r.get("success", False)),
            "total_space_freed": sum(r.get("space_freed", 0) for r in results if r.get("success", False)),
            "dry_run": dry_run,
            "details": results
        }
        
        # Save report if enabled
        if settings.get("housekeeper_report_enabled", True):
            await self._save_cleanup_report(report)
        
        self.logger.info(f"System-wide cleanup complete: {report['total_files_deleted']} files deleted, {report['total_space_freed']} bytes freed")
        return report
    
    async def run_cleanup(self, registration_id: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run cleanup operations manually.
        
        Args:
            registration_id: Optional ID to clean specific registration only
            dry_run: If True, report what would be deleted without deleting
            
        Returns:
            Dict[str, Any]: Report of cleanup operation results
        """
        if not self.initialized:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="NOT_INITIALIZED",
                details="Housekeeper not initialized"
            ))
            return Result.error(
                code="NOT_INITIALIZED",
                message="Housekeeper not initialized"
            )
        
        # If specific ID provided, run only that cleanup
        if registration_id:
            config_result = await self.db_ops.get_cleanup_config(registration_id)
            if not config_result.success:
                error_details = config_result.error
                self.logger.error(error_message(
                    module_id=COMPONENT_ID,
                    error_type=error_details.get("code", "CONFIG_NOT_FOUND"),
                    details=f"Cleanup config not found or failed to retrieve: {registration_id}. Error: {error_details.get('message', 'Unknown')}"
                ))
                return Result.error(
                    code="CONFIG_NOT_FOUND",
                    message=f"Cleanup config not found or failed to retrieve: {registration_id}"
                )
            
            config = config_result.data
            result = await self._run_single_cleanup(config, dry_run)
            
            # Update last_run timestamp
            await self.db_ops.update_cleanup_config(
                id=config["id"],
                last_run=datetime.now()
            )
            
            return Result.success(data={"result": result})
        
        # Otherwise run all configs (same as scheduled cleanup)
        report = await self.run_scheduled_cleanup(dry_run=dry_run)
        return Result.success(data={"report": report})
    
    async def _run_single_cleanup(self, config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Run cleanup for a single configuration.
        
        Args:
            config: Cleanup configuration
            dry_run: If True, don't actually delete files
            
        Returns:
            Dict[str, Any]: Result of the cleanup operation
        """
        directory = config.get("directory")
        pattern = config.get("pattern", "*")
        retention_days = config.get("retention_days")
        max_files = config.get("max_files")
        max_size_mb = config.get("max_size_mb")
        
        self.logger.info(f"Running cleanup for {directory} with pattern {pattern}")
        
        # Prepare result
        result = {
            "id": config.get("id"),
            "directory": directory,
            "pattern": pattern,
            "success": True,
            "dry_run": dry_run,
            "files_deleted": 0,
            "space_freed": 0,
            "files_kept": 0
        }
        
        try:
            # Get all matching files
            path_pattern = os.path.join(directory, pattern)
            all_files = glob.glob(path_pattern)
            
            # Skip if no files found
            if not all_files:
                self.logger.info(f"No files matching {path_pattern}")
                result["message"] = "No matching files found"
                return result
            
            # Get file stats
            file_stats = []
            for file_path in all_files:
                try:
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        file_stats.append({
                            "path": file_path,
                            "size": stat.st_size,
                            "mtime": datetime.fromtimestamp(stat.st_mtime)
                        })
                except (PermissionError, FileNotFoundError) as e:
                    self.logger.warning(f"Error accessing file {file_path}: {str(e)}")
            
            # Sort by modification time (oldest first)
            file_stats.sort(key=lambda f: f["mtime"])
            
            # Apply cleanup policies
            files_to_delete = []
            
            # Age-based retention
            if retention_days is not None:
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                files_to_delete = [f for f in file_stats if f["mtime"] < cutoff_date]
            
            # Count-based retention (keep newest N files)
            if max_files is not None:
                # If we're already deleting some files based on age, respect that
                if files_to_delete:
                    # Keep the newest files that weren't already marked for deletion
                    files_to_keep = [f for f in file_stats if f not in files_to_delete]
                    if len(files_to_keep) > max_files:
                        # Add oldest files to the deletion list until we're within limit
                        additional_deletes = len(files_to_keep) - max_files
                        files_to_delete.extend(files_to_keep[:additional_deletes])
                else:
                    # No age-based deletion, so keep newest max_files
                    if len(file_stats) > max_files:
                        files_to_delete = file_stats[:-max_files]  # Delete all but the newest max_files
            
            # Size-based retention (reduce total size to under limit)
            if max_size_mb is not None:
                max_size_bytes = max_size_mb * 1024 * 1024
                
                # Calculate current total size
                current_total = sum(f["size"] for f in file_stats)
                
                if current_total > max_size_bytes:
                    # Need to delete files to get under the size limit
                    bytes_to_free = current_total - max_size_bytes
                    
                    # Keep track of files we've marked for deletion so far
                    already_marked = set(f["path"] for f in files_to_delete)
                    bytes_freed = sum(f["size"] for f in files_to_delete)
                    
                    # Add more files until we've freed enough space
                    if bytes_freed < bytes_to_free:
                        for file in file_stats:
                            if file["path"] not in already_marked:
                                files_to_delete.append(file)
                                bytes_freed += file["size"]
                                already_marked.add(file["path"])
                                
                                if bytes_freed >= bytes_to_free:
                                    break
            
            # Remove duplicates
            files_to_delete = {f["path"]: f for f in files_to_delete}.values()
            
            # Delete files (or simulate if dry_run)
            space_freed = 0
            files_deleted = 0
            
            for file in files_to_delete:
                if dry_run:
                    self.logger.info(f"[DRY RUN] Would delete: {file['path']}")
                    space_freed += file["size"]
                    files_deleted += 1
                else:
                    try:
                        os.remove(file["path"])
                        self.logger.info(f"Deleted: {file['path']}")
                        space_freed += file["size"]
                        files_deleted += 1
                    except (PermissionError, FileNotFoundError) as e:
                        self.logger.warning(f"Error deleting {file['path']}: {str(e)}")
            
            # Update result
            result["files_deleted"] = files_deleted
            result["space_freed"] = space_freed
            result["files_kept"] = len(file_stats) - files_deleted
            
            if dry_run:
                result["message"] = f"[DRY RUN] Would delete {files_deleted} files, freeing {space_freed} bytes"
            else:
                result["message"] = f"Deleted {files_deleted} files, freeing {space_freed} bytes"
                
            return result
            
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="CLEANUP_ERROR",
                details=f"Error cleaning up {directory}: {str(e)}"
            ))
            result["success"] = False
            result["error"] = str(e)
            return result
    
    async def _save_cleanup_report(self, report: Dict[str, Any]) -> bool:
        """
        Save cleanup report to file.
        
        Args:
            report: Cleanup report data
            
        Returns:
            bool: Whether the save was successful
        """
        # Get settings for report directory
        settings = await self.app_context.get_module_settings(MODULE_ID)
        report_dir = settings.get("housekeeper_report_directory", "")
        
        # If not specified, use default in DATA_DIR
        if not report_dir:
            report_dir = os.path.join(self.app_context.config.DATA_DIR, "cleanup_reports")
        
            # Create report directory if it doesn't exist
            os.makedirs(report_dir, exist_ok=True)
            
            # Create report filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(report_dir, f"cleanup_report_{timestamp}.json")
        
        try:
            import json
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Saved cleanup report to {report_file}")
            return True
        except Exception as e:
            self.logger.error(error_message(
                module_id=COMPONENT_ID,
                error_type="REPORT_SAVE_ERROR",
                details=f"Error saving cleanup report: {str(e)}"
            ))
            return False
