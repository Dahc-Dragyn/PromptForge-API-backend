# test_master.py
import requests
import json
import sys
import time
import os
import math
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth

# --- Configuration ---
load_dotenv()
BASE_URL = "http://127.0.0.1:8000"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite" 
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
TEST_USER_ID = os.getenv("REGULAR_USER_UID", "test_suite_user_12345")
API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

# --- Firebase Admin SDK Initialization ---
try:
    if not firebase_admin._apps:
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not cred_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in .env file")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK initialized for test master.")
except Exception as e:
    print(f"❌ Could not initialize Firebase Admin SDK for test master: {e}")
    sys.exit(1)

# --- Auth Token Function ---
def get_auth_token(user_uid: str):
    """Generates an ID token for a specific user UID."""
    try:
        custom_token = auth.create_custom_token(user_uid)
        rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}"
        response = requests.post(rest_api_url, data={"token": custom_token, "returnSecureToken": True})
        response.raise_for_status()
        return response.json().get("idToken")
    except Exception as e:
        print(f"❌ Failed to get ID token for {user_uid}: {e}")
        sys.exit(1)

# --- Global Headers ---
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}

# --- Helper & Test Functions ---
def print_test_header(title):
    print("\n" + "="*15 + f" {title.upper()} " + "="*15 + "\n")

def print_success(message):
    print(f"  ✅ SUCCESS: {message}")

def run_test(name, method, url, payload=None, expected_status=None):
    """Helper function to run a single API test."""
    try:
        response = requests.request(method.upper(), url, headers=HEADERS, data=json.dumps(payload) if payload else None)
        if expected_status:
            assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        else:
            response.raise_for_status()
        
        print_success(name)
        
        if response.status_code != 204:
            return response.json()
        return None
    except (requests.exceptions.RequestException, AssertionError, json.JSONDecodeError) as e:
        print(f"  ❌ FAILED: {name} - {type(e).__name__}: {e}")
        if 'response' in locals() and response.text:
            print(f"      Error Body: {response.text}")
        sys.exit(1)

def test_health_check():
    print_test_header("Health Check")
    run_test("GET /", "GET", f"{BASE_URL}/")

def test_prompt_endpoints():
    print_test_header("Prompt & Versioning")
    create_payload = {"name": f"Test Prompt {int(time.time())}", "task_description": "A test prompt.", "initial_prompt_text": "This is version 1."}
    created_prompt = run_test("Create Prompt", "POST", f"{BASE_URL}/prompts/", create_payload, expected_status=201)
    prompt_id = created_prompt["id"]
    
    run_test("List All Prompts", "GET", f"{BASE_URL}/prompts/")
    run_test("Get Single Prompt", "GET", f"{BASE_URL}/prompts/{prompt_id}")
    run_test("Update Prompt", "PATCH", f"{BASE_URL}/prompts/{prompt_id}", payload={"name": "Updated Test Prompt Name"})
    run_test("Create New Version", "POST", f"{BASE_URL}/prompts/{prompt_id}/versions", payload={"prompt_text": "This is v2.", "commit_message": "v2 test"}, expected_status=201)
    run_test("List All Versions", "GET", f"{BASE_URL}/prompts/{prompt_id}/versions")
    return prompt_id

def test_ai_and_analysis_endpoints():
    print_test_header("AI & Analysis")
    execute_payload = {"prompt_text": "Summarize the plot of Hamlet in one sentence.", "model": DEFAULT_GEMINI_MODEL, "variables": {}}
    response = run_test("Execute Prompt (Platform Key)", "POST", f"{BASE_URL}/prompts/execute", payload=execute_payload)
    assert "final_text" in response and response["final_text"]
    assert "cost" in response and isinstance(response["cost"], float) and response["cost"] >= 0
    
    run_test("Optimize Prompt (APE)", "POST", f"{BASE_URL}/prompts/optimize", payload={"task_description": "Turn a statement into a question.", "examples": [{"input": "It is sunny.", "output": "Is it sunny?"}]})
    run_test("Benchmark Prompt", "POST", f"{BASE_URL}/prompts/benchmark", payload={"prompt_text": "Differences between Python and JS?", "models": [DEFAULT_GEMINI_MODEL]})
    run_test("Diagnose Prompt", "POST", f"{BASE_URL}/prompts/diagnose", payload={"prompt_text": "write code"})
    run_test("Breakdown Prompt", "POST", f"{BASE_URL}/prompts/breakdown", payload={"prompt_text": "You are a helpful assistant. Summarize this text."})

def test_template_endpoints():
    print_test_header("Templates")
    unique_suffix = str(int(time.time()))
    template_payload = {"name": f"Test Persona: Pirate {unique_suffix}", "description": "A test persona.", "content": "You are a pirate who loves treasure.", "tags": ["persona", "pirate", "test_script"]}
    created_template = run_test("Create Template", "POST", f"{BASE_URL}/templates/", template_payload, expected_status=201)
    
    run_test("List All Templates", "GET", f"{BASE_URL}/templates/")
    run_test("Filter Templates by Tag", "GET", f"{BASE_URL}/templates/?tag=pirate")
    run_test("AI Generate Template", "POST", f"{BASE_URL}/templates/generate", payload={"style_description": f"A persona for a chef named Chef {unique_suffix}", "tags": ["persona", "chef", "test_script"]}, expected_status=201)
    run_test("Compose Prompt", "POST", f"{BASE_URL}/templates/compose", payload={"persona": "pirate", "task": "summarize"})
    run_test("Recommend Template", "POST", f"{BASE_URL}/templates/recommend", payload={"task_description": "I need to write a professional email."})

def test_sandbox_endpoints():
    print_test_header("Sandbox")
    run_test("A/B Test Sandbox", "POST", f"{BASE_URL}/sandbox/", payload={"prompts": [{"id": "v1", "text": "What is a CPU?"}, {"id": "v2", "text": "Explain a CPU to a 5th grader."}], "input_text": "", "model": DEFAULT_GEMINI_MODEL})

# --- ACTION: Pass prompt_id to this function ---
def test_metrics_endpoints(prompt_id: str):
    print_test_header("Metrics Endpoints")
    
    # --- ACTION: Add a test for submitting a rating ---
    rating_payload = {"prompt_id": prompt_id, "version_number": 1, "rating": 5}
    run_test("Submit Rating", "POST", f"{BASE_URL}/metrics/ratings", payload=rating_payload, expected_status=201)
    
    # Test the dashboard endpoints
    top_prompts = run_test("Get Top Prompts", "GET", f"{BASE_URL}/metrics/prompts/all")
    assert isinstance(top_prompts, list)
    
    recent_activity = run_test("Get Recent Activity", "GET", f"{BASE_URL}/metrics/activity/recent")
    assert isinstance(recent_activity, list)

    # Test cost calculation
    cost_payload = {"model_name": DEFAULT_GEMINI_MODEL, "input_token_count": 10000, "output_token_count": 5000}
    run_test("Calculate Cost", "POST", f"{BASE_URL}/metrics/calculate-cost", payload=cost_payload)

def test_user_and_execution_endpoints():
    print_test_header("User & Managed Execution")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("--- SKIPPING MANAGED EXECUTION TESTS: OPENAI_API_KEY not found in environment variables. ---")
        return

    key_payload = {"provider": "openai", "api_key": openai_api_key}
    run_test("Save User API Key", "POST", f"{BASE_URL}/users/{TEST_USER_ID}/keys", payload=key_payload, expected_status=204)
    
    exec_payload = {"user_id": TEST_USER_ID, "model_name": DEFAULT_OPENAI_MODEL, "prompt_text": "What is the capital of Oregon?"}
    response = run_test("Managed Execution (Success)", "POST", f"{BASE_URL}/users/execute", payload=exec_payload)
    assert "Salem" in response.get("final_text", "")
    
    fail_payload = {"user_id": "non-existent-user", "model_name": DEFAULT_OPENAI_MODEL, "prompt_text": "This should fail."}
    run_test("Managed Execution (Failure - No Key)", "POST", f"{BASE_URL}/users/execute", payload=fail_payload, expected_status=403)

def cleanup(prompt_id):
    print_test_header("Cleaning Up Test Resources")
    if prompt_id:
        run_test(f"Delete Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)
    
    try:
        templates = run_test("List All Templates for Cleanup", "GET", f"{BASE_URL}/templates/?tag=test_script")
        if templates:
            for t in templates:
                run_test(f"Delete Template '{t['name']}'", "DELETE", f"{BASE_URL}/templates/{t['id']}", expected_status=204)
    except Exception as e:
        print(f"--- INFO: Cleanup of templates skipped due to potential earlier failure: {e} ---")


if __name__ == "__main__":
    if not all([API_KEY, TEST_USER_ID]):
        print("❌ ERROR: Ensure FIREBASE_WEB_API_KEY and REGULAR_USER_UID are in your .env file.")
        sys.exit(1)

    print(f"--- Authenticating test user: {TEST_USER_ID} ---")
    auth_token = get_auth_token(TEST_USER_ID)
    HEADERS["Authorization"] = f"Bearer {auth_token}"
    print("✅ Authentication successful. Proceeding with tests.")

    prompt_id_to_delete = None
    try:
        test_health_check()
        prompt_id_to_delete = test_prompt_endpoints()
        test_ai_and_analysis_endpoints()
        test_template_endpoints()
        test_sandbox_endpoints()
        # --- ACTION: Pass the created prompt_id to the metrics tests ---
        test_metrics_endpoints(prompt_id_to_delete)
        test_user_and_execution_endpoints()
    finally:
        cleanup(prompt_id_to_delete)
        print("\n" + "="*20 + " TEST SUITE COMPLETE " + "="*20 + "\n")