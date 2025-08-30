
INFO:     Application shutdown complete.
INFO:     Finished server process [29204]
2025-03-31 20:42:36,996 - asyncio - ERROR - Task was destroyed but it is pending!
task: <Task pending name='Task-24' coro=<SchedulerService._scheduler_loop() running at G:\github\Modular_AI\modules\core\scheduler\services.py:181> wait_for=<Future pending cb=[Task.task_wakeup()]>>

---------

I see a shutdown error related to the `scheduler` module. This is a common issue with background tasks in asynchronous applications. 

The scheduler has a background loop (`_scheduler_loop()`) that's still running when the application shuts down. This task isn't being properly canceled or awaited, which causes the "Task was destroyed but it is pending!" error.

To fix this, we need to implement proper cleanup in the `SchedulerService` class. The proper pattern for background tasks in Python async applications is:

```python
# In the service initialization
def __init__(self, ...):
    # Other initialization code
    self._shutdown_event = asyncio.Event()
    self._background_tasks = set()
    
# Start background task with tracking
def start_background_task(self, coro):
    task = asyncio.create_task(coro)
    self._background_tasks.add(task)
    task.add_done_callback(self._background_tasks.discard)
    return task

# The background loop with proper shutdown handling
async def _scheduler_loop(self):
    try:
        while not self._shutdown_event.is_set():
            # Do periodic work
            
            # Wait with timeout or until shutdown is requested
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.check_interval)
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                pass
    except asyncio.CancelledError:
        # Handle cancellation gracefully
        self.logger.info("Scheduler loop was cancelled")
        raise
    finally:
        # Cleanup code

# Shutdown method called during app lifecycle end
async def shutdown(self):
    # Signal all background tasks to stop
    self._shutdown_event.set()
    
    # Wait for all background tasks to complete
    if self._background_tasks:
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
```

This pattern ensures all background tasks are properly tracked and cleaned up during application shutdown, which would resolve the error you're seeing.

Should we implement this fix for the scheduler module, or do you want to focus on the system_monitor enhancements we were discussing with py-cpuinfo and sensors?