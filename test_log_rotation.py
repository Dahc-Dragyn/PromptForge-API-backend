# ~/rankforge/test_log_rotation.py
import os
import time
import logging
from logging.handlers import RotatingFileHandler

# This import triggers the logging setup from our application
from app.main import app

LOG_FILE = "api_requests.log"
MAX_LOG_SIZE_FOR_TEST = 1024  # 1KB for testing
BACKUP_COUNT = 3

def test_log_rotation():
    logger = logging.getLogger()
    handler = None
    for h in logger.handlers:
        if isinstance(h, RotatingFileHandler) and 'api_requests.log' in h.baseFilename:
            handler = h
            break
    
    assert handler is not None, "FAIL: The RotatingFileHandler was not found on the root logger."

    # --- KEY FIX: Temporarily override the handler's size limit for the test ---
    original_max_bytes = handler.maxBytes
    handler.maxBytes = MAX_LOG_SIZE_FOR_TEST
    
    try:
        # --- Cleanup: Ensure a clean state before the test runs ---
        logger.removeHandler(handler)
        handler.close()
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        for i in range(1, BACKUP_COUNT + 5):
            backup_file = f"{LOG_FILE}.{i}"
            if os.path.exists(backup_file):
                os.remove(backup_file)
        logger.addHandler(handler)

        print(f"--- Triggering log rotation (test limit: {MAX_LOG_SIZE_FOR_TEST} bytes) ---")
        
        # Write enough data to exceed the test limit
        large_log_message = "A" * MAX_LOG_SIZE_FOR_TEST
        logger.info(large_log_message)
        logger.info("This second message will trigger the rotation.")
        
        # Force the rotation to complete by closing the handler
        logger.removeHandler(handler)
        handler.close()

        print("--- Verifying rotation results ---")
        
        backup_log = f"{LOG_FILE}.1"
        assert os.path.exists(backup_log), f"FAIL: Backup log '{backup_log}' was not created."
        print(f"  ✅ SUCCESS: Backup log '{backup_log}' found.")

        assert os.path.exists(LOG_FILE)
        with open(LOG_FILE, 'r') as f:
            content = f.read()
            assert "This second message" in content
        print(f"  ✅ SUCCESS: New log file is correct.")

    finally:
        # --- Teardown: Restore the original production value ---
        handler.maxBytes = original_max_bytes
        print(f"--- Restored log handler maxBytes to {original_max_bytes} ---")


if __name__ == "__main__":
    test_log_rotation()
    print("\n🎉 Log rotation test passed successfully!")