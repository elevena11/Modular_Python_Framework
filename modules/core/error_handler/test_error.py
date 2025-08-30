"""
modules/core/error_handler/test_error.py
Updated: March 27, 2025
Test script to generate sample errors for demonstrating the error handler
python -m modules.core.error_handler.test_error
"""

import os
import sys
import time
import random
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("error_handler_test")

# Import error handler utilities
from core.error_utils import (
    Result, 
    create_error_response, 
    error_message,
    log_error
)

# Define some sample error types
ERROR_TYPES = [
    "CONNECTION_FAILED",
    "VALIDATION_ERROR",
    "PERMISSION_DENIED",
    "RESOURCE_NOT_FOUND",
    "TIMEOUT_ERROR",
    "DEPENDENCY_MISSING",
    "CONFIGURATION_ERROR",
    "DATA_FORMAT_ERROR",
    "SERVICE_UNAVAILABLE",
    "UNEXPECTED_ERROR"
]

# Define some sample error details
ERROR_DETAILS = [
    "Database connection refused",
    "Invalid input data provided",
    "User lacks required permissions",
    "Requested resource does not exist",
    "Operation timed out after waiting",
    "Required dependency not available",
    "Invalid configuration parameter",
    "Malformed data received",
    "External service unavailable",
    "An unexpected error occurred"
]

# Define some sample locations
LOCATIONS = [
    "initialize()",
    "process_data()",
    "validate_input()",
    "authorize_user()",
    "fetch_resource()",
    "connect_service()",
    "parse_config()",
    "format_data()",
    "call_external_api()"
]

def generate_random_error():
    """Generate a random error message and log it."""
    error_type = random.choice(ERROR_TYPES)
    error_detail = random.choice(ERROR_DETAILS)
    location = random.choice(LOCATIONS)
    
    # Log the error using error_message
    error_msg = # Direct logging instead of error_message(error_type, error_detail, location)
    logger.error(error_msg)
    
    return error_type, error_detail, location

def test_result_class():
    """Test the Result class."""
    # Test success result
    success_result = Result.success({"id": 123, "name": "Test Data"})
    logger.info(f"Success Result: {success_result}")
    
    # Test error result
    error_type, error_detail, location = generate_random_error()
    error_result = Result.error(
        error_type,
        error_detail,
        {"location": location, "timestamp": datetime.now().isoformat()}
    )
    logger.info(f"Error Result: {error_result}")

def test_create_error_response():
    """Test the create_error_response function."""
    error_type, error_detail, location = generate_random_error()
    try:
        # Simulate raising the error
        http_error = create_error_response(
            error_type,
            error_detail,
            {"location": location},
            status_code=400
        )
        logger.info(f"HTTP Error: {http_error.status_code} - {http_error.detail}")
        raise http_error
    except Exception as e:
        logger.info(f"Caught exception: {e}")

def test_log_error():
    """Test the direct log_error function."""
    for _ in range(3):
        error_type = random.choice(ERROR_TYPES)
        error_detail = random.choice(ERROR_DETAILS)
        location = random.choice(LOCATIONS)
        
        # Log the error directly
        log_error(
            error_type,
            error_detail,
            {"severity": random.choice(["low", "medium", "high"])},
            location
        )
        logger.info(f"Logged error: {error_type}")

def simulate_error_in_function():
    """Simulate an error occurring within a function."""
    try:
        # Simulate some operation that might fail
        if random.random() < 0.8:  # 80% chance of error
            raise ValueError("Simulated error in function")
        return "Operation completed successfully"
    except Exception as e:
        # Log the error using error_message
        logger.error(# Direct logging instead of error_message("RUNTIME_ERROR", str(e)))
        return None

def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description="Test the error handler module")
    parser.add_argument('--count', type=int, default=10, help='Number of random errors to generate')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--result', action='store_true', help='Test Result class')
    parser.add_argument('--response', action='store_true', help='Test create_error_response')
    parser.add_argument('--log', action='store_true', help='Test log_error directly')
    parser.add_argument('--simulate', action='store_true', help='Simulate errors in functions')
    
    args = parser.parse_args()
    
    # Default to --all if no specific test is requested
    run_all = args.all or not (args.result or args.response or args.log or args.simulate)
    
    print(f"Error Handler Test - Generating {args.count} errors")
    print(f"Error logs will be written to: {os.getenv('DATA_DIR', './data')}/error_logs/")
    
    # Run the requested tests
    if run_all or args.result:
        print("\n=== Testing Result Class ===")
        test_result_class()
    
    if run_all or args.response:
        print("\n=== Testing create_error_response ===")
        test_create_error_response()
    
    if run_all or args.log:
        print("\n=== Testing log_error ===")
        test_log_error()
    
    if run_all or args.simulate:
        print("\n=== Simulating Errors in Functions ===")
        for i in range(args.count):
            result = simulate_error_in_function()
            print(f"Function call {i+1}: {'Success' if result else 'Failed'}")
            time.sleep(0.1)  # Small delay between errors
    
    # Generate random errors
    if not args.simulate:
        print("\n=== Generating Random Errors ===")
        for i in range(args.count):
            error_type, error_detail, location = generate_random_error()
            print(f"Generated error {i+1}: {error_type}")
            time.sleep(0.1)  # Small delay between errors
    
    print("\nTest completed. Check the error logs for results.")

if __name__ == "__main__":
    main()
