#!/usr/bin/env python3
"""
Clear logs script for semantic analyzer framework.

Removes log files to start with clean logs for testing.
"""

import os
import glob
from pathlib import Path

def clear_logs():
    """Clear all log files."""
    framework_root = Path(__file__).parent.parent
    
    log_files_to_remove = [
        "data/logs/app.log",
        "data/logs/module_loader.log",
        "data/logs/ui_streamlit.log",
        "data/logs/ui.log"
    ]
    
    # Remove specific log files
    for log_file in log_files_to_remove:
        log_path = framework_root / log_file
        if log_path.exists():
            try:
                log_path.unlink()
                print(f"Removed: {log_file}")
            except Exception as e:
                print(f"Failed to remove {log_file}: {e}")
        else:
            print(f"Not found: {log_file}")
    
    # Remove error log files (*.jsonl in data/error_logs/)
    error_logs_dir = framework_root / "data/error_logs"
    if error_logs_dir.exists():
        jsonl_files = list(error_logs_dir.glob("*.jsonl"))
        if jsonl_files:
            for jsonl_file in jsonl_files:
                try:
                    jsonl_file.unlink()
                    print(f"Removed: {jsonl_file.relative_to(framework_root)}")
                except Exception as e:
                    print(f"Failed to remove {jsonl_file.name}: {e}")
        else:
            print("No *.jsonl files found in data/error_logs/")
    else:
        print("Error logs directory does not exist: data/error_logs/")
    
    print("\nLog cleanup completed.")

if __name__ == "__main__":
    clear_logs()