"""
Core Framework Version Management

Provides centralized version information reading from framework version files.
This is core infrastructure, not module logic.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def get_framework_version() -> str:
    """Get current framework version from version files.

    Priority order:
    1. .framework_version (tracks installation/updates)
    2. framework_manifest.json (tracks development state)
    3. Default fallback

    Returns:
        str: Version string (e.g., "1.0.5")
    """
    project_root = Path.cwd()

    # Priority 1: .framework_version (installation tracking)
    framework_version_file = project_root / ".framework_version"
    if framework_version_file.exists():
        try:
            with open(framework_version_file, 'r') as f:
                data = json.load(f)
                version = data.get("version", "unknown")
                if version != "unknown":
                    return version
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            pass

    # Priority 2: framework_manifest.json (development state)
    manifest_file = project_root / "framework_manifest.json"
    if manifest_file.exists():
        try:
            with open(manifest_file, 'r') as f:
                data = json.load(f)
                version = data.get("version", "unknown")
                if version != "unknown":
                    return version
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            pass

    # Fallback
    return "unknown"


def get_version_info() -> Dict[str, Any]:
    """Get comprehensive version information.

    Returns:
        Dict containing version, source, and metadata
    """
    project_root = Path.cwd()

    # Try .framework_version first
    framework_version_file = project_root / ".framework_version"
    if framework_version_file.exists():
        try:
            with open(framework_version_file, 'r') as f:
                data = json.load(f)
                return {
                    "version": data.get("version", "unknown"),
                    "source": ".framework_version",
                    "metadata": data
                }
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Try manifest as fallback
    manifest_file = project_root / "framework_manifest.json"
    if manifest_file.exists():
        try:
            with open(manifest_file, 'r') as f:
                data = json.load(f)
                return {
                    "version": data.get("version", "unknown"),
                    "source": "framework_manifest.json",
                    "metadata": {
                        "version": data.get("version", "unknown"),
                        "generated_at": data.get("generated_at"),
                        "file_count": data.get("file_count")
                    }
                }
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    return {
        "version": "unknown",
        "source": "fallback",
        "metadata": {}
    }


def get_framework_uptime() -> float:
    """Get framework uptime in seconds.

    Note: This is a placeholder. Real uptime tracking would need
    to be implemented in the application bootstrap/context.
    """
    # TODO: Implement actual uptime tracking
    import time
    return time.time()  # Placeholder


def get_session_info() -> Dict[str, Any]:
    """Get current session information.

    Returns:
        Dict with session ID, start time, version, uptime
    """
    # TODO: Implement actual session tracking
    return {
        "session_id": "framework_session",  # Should come from app context
        "session_start_time": datetime.now().isoformat(),
        "framework_version": get_framework_version(),
        "uptime_seconds": get_framework_uptime()
    }