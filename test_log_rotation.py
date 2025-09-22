# ~/rankforge/tests/test_log_rotation.py
import os
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

LOG_FILE = "./logs/app.log"
MAX_LOG_SIZE = 1024  # 1KB for testing
BACKUP_COUNT = 3

def test_log_rotation():
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # Clear existing logs if any
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    for i in range(1, BACKUP_COUNT + 2):
        if os.path.exists(f"{LOG_FILE}.{i}"):
            os.remove(f"{LOG_FILE}.{i}")

    # Write more than MAX_LOG_SIZE to trigger rotation
    large_log_message = "a" * (MAX_LOG_SIZE + 100)
    client.post("/prompts/execute", json={"prompt_text": large_log_message})

    # Allow a moment for the rotation to occur
    time.sleep(1)

    # Verification
    # 1. The original log file should now be smaller than the max size
    assert os.path.exists(LOG_FILE)
    assert os.path.getsize(LOG_FILE) < MAX_LOG_SIZE

    # 2. A backup file should have been created
    assert os.path.exists(f"{LOG_FILE}.1")

    # 3. Trigger multiple rotations to test backup count limit
    for i in range(BACKUP_COUNT + 1):
        client.post("/prompts/execute", json={"prompt_text": large_log_message})
        time.sleep(0.2) # Quick sleep between logs

    # 4. Verify the correct number of backup files exist
    log_files = [f for f in os.listdir("./logs") if f.startswith("app.log.")]
    assert len(log_files) <= BACKUP_COUNT
    assert os.path.exists(f"{LOG_FILE}.{BACKUP_COUNT}")
    assert not os.path.exists(f"{LOG_FILE}.{BACKUP_COUNT + 1}")

    print("\nLog rotation test passed successfully!")