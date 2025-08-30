"""
modules/core/scheduler/components/trigger_manager.py
Updated: April 6, 2025
Trigger manager component for handling different trigger types
"""

import logging
import calendar
from datetime import datetime, timedelta, time
from typing import Dict, Any, Optional, Union, List, Tuple

from core.error_utils import error_message

# Module identity - must match manifest.json
MODULE_ID = "core.scheduler"
# Component identity
COMPONENT_ID = f"{MODULE_ID}.trigger_manager"
logger = logging.getLogger(COMPONENT_ID)

class TriggerManager:
    """
    Manages trigger types and execution time calculations.
    
    This component handles the logic for different trigger types (date, interval, cron) 
    and calculates when events should be executed next.
    """
    
    def __init__(self, app_context):
        """
        Initialize the trigger manager.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.logger = logger
        self.initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the trigger manager.
        
        Returns:
            bool: Whether initialization was successful
        """
        if self.initialized:
            return True
            
        self.initialized = True
        self.logger.info("Trigger manager initialized")
        return True
    
    def validate_trigger(self, trigger_type: str, trigger_args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate trigger parameters.
        
        Args:
            trigger_type: Type of trigger (date, interval, cron)
            trigger_args: Trigger arguments
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if trigger_type == "date":
            # Validate date trigger
            if "run_date" not in trigger_args:
                return False, "run_date is required for date trigger"
                
            run_date = trigger_args.get("run_date")
            if not isinstance(run_date, (datetime, str)):
                return False, "run_date must be a datetime object or ISO format string"
                
            return True, None
            
        elif trigger_type == "interval":
            # Validate interval trigger
            if "interval" not in trigger_args:
                return False, "interval is required for interval trigger"
                
            interval = trigger_args.get("interval")
            if not isinstance(interval, (int, float)) or interval <= 0:
                return False, "interval must be a positive number"
                
            interval_unit = trigger_args.get("interval_unit", "minutes")
            if interval_unit not in ("minutes", "hours", "days", "weeks", "months"):
                return False, "interval_unit must be one of: minutes, hours, days, weeks, months"
                
            return True, None
            
        elif trigger_type == "cron":
            # Validate cron trigger
            if "cron_expression" not in trigger_args:
                return False, "cron_expression is required for cron trigger"
                
            cron_expression = trigger_args.get("cron_expression")
            if not isinstance(cron_expression, str):
                return False, "cron_expression must be a string"
                
            # Basic validation of cron expression format
            parts = cron_expression.split()
            if len(parts) != 5:
                return False, "cron_expression must have 5 fields: minute hour day month day_of_week"
                
            return True, None
            
        else:
            return False, f"Unsupported trigger type: {trigger_type}"
    
    def get_next_execution_time(
        self, 
        trigger_type: str, 
        trigger_args: Dict[str, Any],
        reference_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Calculate the next execution time for a trigger.
        
        Args:
            trigger_type: Type of trigger (date, interval, cron)
            trigger_args: Trigger arguments
            reference_time: Reference time for calculation (now if not provided)
            
        Returns:
            Optional[datetime]: Next execution time or None if invalid
        """
        # Validate trigger parameters first
        is_valid, error_message_str = self.validate_trigger(trigger_type, trigger_args)
        if not is_valid:
            self.logger.warning(error_message(
                module_id=COMPONENT_ID,
                error_type="INVALID_TRIGGER",
                details=error_message_str
            ))
            return None
        
        # Use current time if reference time not provided
        if reference_time is None:
            reference_time = datetime.now()
            
        if trigger_type == "date":
            # One-time execution at specific date/time
            return self._get_date_next_time(trigger_args, reference_time)
            
        elif trigger_type == "interval":
            # Recurring execution at fixed intervals
            return self._get_interval_next_time(trigger_args, reference_time)
            
        elif trigger_type == "cron":
            # Cron-style scheduling
            return self._get_cron_next_time(trigger_args, reference_time)
            
        return None
    
    def _get_date_next_time(
        self, 
        trigger_args: Dict[str, Any],
        reference_time: datetime
    ) -> datetime:
        """
        Get next execution time for a date trigger.
        
        Args:
            trigger_args: Trigger arguments
            reference_time: Reference time
            
        Returns:
            datetime: Next execution time
        """
        run_date = trigger_args.get("run_date")
        
        # Convert string to datetime if needed
        if isinstance(run_date, str):
            run_date = datetime.fromisoformat(run_date.replace('Z', '+00:00'))
            
        # If run_date is in the past, it won't run again
        if run_date <= reference_time:
            settings = self.app_context.get_settings().get("core.scheduler", {})
            if settings.get("allow_past_events", False):
                # If past events are allowed, use the specified time
                return run_date
            else:
                # Otherwise, schedule for same time tomorrow
                return run_date + timedelta(days=1)
                
        return run_date
    
    def _get_interval_next_time(
        self, 
        trigger_args: Dict[str, Any],
        reference_time: datetime
    ) -> datetime:
        """
        Get next execution time for an interval trigger.
        
        Args:
            trigger_args: Trigger arguments
            reference_time: Reference time
            
        Returns:
            datetime: Next execution time
        """
        interval = trigger_args.get("interval")
        interval_unit = trigger_args.get("interval_unit", "minutes")
        start_date = trigger_args.get("start_date")
        
        # If start_date not provided, use reference time
        if start_date is None:
            start_date = reference_time
        elif isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
        # If start_date is in the future, use it
        if start_date > reference_time:
            return start_date
            
        # Calculate how many intervals have passed since start_date
        if interval_unit == "minutes":
            delta = reference_time - start_date
            intervals_passed = delta.total_seconds() / 60 / interval
            intervals_to_add = int(intervals_passed) + 1
            return start_date + timedelta(minutes=intervals_to_add * interval)
            
        elif interval_unit == "hours":
            delta = reference_time - start_date
            intervals_passed = delta.total_seconds() / 3600 / interval
            intervals_to_add = int(intervals_passed) + 1
            return start_date + timedelta(hours=intervals_to_add * interval)
            
        elif interval_unit == "days":
            delta = reference_time - start_date
            intervals_passed = delta.days / interval
            intervals_to_add = int(intervals_passed) + 1
            return start_date + timedelta(days=intervals_to_add * interval)
            
        elif interval_unit == "weeks":
            delta = reference_time - start_date
            intervals_passed = delta.days / 7 / interval
            intervals_to_add = int(intervals_passed) + 1
            return start_date + timedelta(weeks=intervals_to_add * interval)
            
        elif interval_unit == "months":
            # Calculate months difference
            months_diff = (reference_time.year - start_date.year) * 12 + (reference_time.month - start_date.month)
            intervals_passed = months_diff / interval
            intervals_to_add = int(intervals_passed) + 1
            
            # Add months (a bit complex due to varying month lengths)
            months_to_add = intervals_to_add * interval
            year = start_date.year + ((start_date.month - 1 + months_to_add) // 12)
            month = ((start_date.month - 1 + months_to_add) % 12) + 1
            
            # Handle day overflow (e.g., Jan 31 -> Feb 28)
            day = min(start_date.day, calendar.monthrange(year, month)[1])
            
            return datetime(
                year=year,
                month=month,
                day=day,
                hour=start_date.hour,
                minute=start_date.minute,
                second=start_date.second,
                microsecond=start_date.microsecond
            )
            
        # Default fallback - shouldn't reach here due to validation
        return reference_time + timedelta(minutes=interval)
    
    def _get_cron_next_time(
        self, 
        trigger_args: Dict[str, Any],
        reference_time: datetime
    ) -> datetime:
        """
        Get next execution time for a cron trigger.
        
        Note: This is a simplified implementation. For a production system,
        consider using a dedicated cron parser library.
        
        Args:
            trigger_args: Trigger arguments
            reference_time: Reference time
            
        Returns:
            datetime: Next execution time
        """
        cron_expression = trigger_args.get("cron_expression")
        parts = cron_expression.split()
        
        # Parse cron parts (simplified)
        minute = self._parse_cron_field(parts[0], 0, 59)
        hour = self._parse_cron_field(parts[1], 0, 23)
        day = self._parse_cron_field(parts[2], 1, 31)
        month = self._parse_cron_field(parts[3], 1, 12)
        day_of_week = self._parse_cron_field(parts[4], 0, 6)  # 0 = Sunday, 6 = Saturday
        
        # Start from the next minute after reference time
        candidate = reference_time.replace(
            second=0, 
            microsecond=0
        ) + timedelta(minutes=1)
        
        # Simple implementation - just find the next time that matches
        # This is not a full cron implementation, just a basic approximation
        max_attempts = 1000  # Prevent infinite loops
        for _ in range(max_attempts):
            # Check if candidate matches all cron fields
            if (
                (minute == "*" or candidate.minute in minute) and
                (hour == "*" or candidate.hour in hour) and
                (month == "*" or candidate.month in month) and
                (
                    (day == "*" and day_of_week == "*") or
                    (day == "*" and candidate.weekday() in day_of_week) or
                    (day_of_week == "*" and candidate.day in day) or
                    (candidate.day in day and candidate.weekday() in day_of_week)
                )
            ):
                # Found a match
                return candidate
            
            # Move to next minute
            candidate += timedelta(minutes=1)
        
        # If we get here, something went wrong
        self.logger.warning(error_message(
            module_id=COMPONENT_ID,
            error_type="CRON_PARSE_ERROR",
            details=f"Could not find next execution time for cron expression: {cron_expression}"
        ))
        # Default to next day at midnight as fallback
        return datetime.combine(reference_time.date() + timedelta(days=1), time(0, 0))
    
    def _parse_cron_field(self, field: str, min_val: int, max_val: int) -> Union[str, List[int]]:
        """
        Parse a cron field into a list of valid values.
        
        Args:
            field: Cron field value
            min_val: Minimum valid value
            max_val: Maximum valid value
            
        Returns:
            Union[str, List[int]]: "*" for all values or list of specific values
        """
        if field == "*":
            return "*"
            
        # Handle comma-separated values
        if "," in field:
            values = []
            for part in field.split(","):
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    values.extend(range(start, end + 1))
                else:
                    values.append(int(part))
            return values
            
        # Handle ranges
        if "-" in field:
            start, end = map(int, field.split("-"))
            return list(range(start, end + 1))
            
        # Handle step values (simplified)
        if "/" in field:
            base, step = field.split("/")
            if base == "*":
                return list(range(min_val, max_val + 1, int(step)))
            else:
                # Not handling more complex cases
                return [int(base)]
                
        # Single value
        return [int(field)]
