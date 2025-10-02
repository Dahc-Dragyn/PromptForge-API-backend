# test_master2.py
import requests
import json
import sys
import time
import os
import re
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth

# --- Configuration (Unchanged) ---
load_dotenv()
BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
PRIMARY_TEST_USER_ID = os.getenv("REGULAR_USER_UID", "test_suite_user_12345")
SECOND_TEST_USER_ID = os.getenv("SECOND_REGULAR_USER_UID", "test_suite_user_67890")

# --- Firebase & Auth (Unchanged) ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK initialized for test master.")
except Exception as e:
    print(f"❌ Could not initialize Firebase Admin SDK: {e}")
    sys.exit(1)

def get_auth_token(user_uid: str):
    try:
        custom_token = auth.create_custom_token(user_uid)
        rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}"
        response = requests.post(rest_api_url, data={"token": custom_token, "returnSecureToken": True})
        response.raise_for_status()
        return response.json().get("idToken")
    except Exception as e:
        print(f"❌ Failed to get ID token for {user_uid}: {e}")
        sys.exit(1)

# --- Global Headers (Mutable) ---
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}

# --- Helpers ---
def print_test_header(title): print("\n" + "="*15 + f" {title.upper()} " + "="*15 + "\n")
def print_success(message): print(f"  ✅ SUCCESS: {message}")

def run_test(name, method, url, payload=None, expected_status=None):
    """
    Helper function to run a single API test with strict JSON parsing.
    """
    try:
        response = requests.request(method.upper(), url, headers=HEADERS, data=json.dumps(payload) if payload else None)
        if expected_status:
            assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        else:
            response.raise_for_status()
        
        print_success(name)
        
        if response.status_code != 204:
            parsed_json = json.loads(response.text)
            return parsed_json
        return None
    except (requests.exceptions.RequestException, AssertionError, json.JSONDecodeError) as e:
        print(f"  ❌ FAILED: {name} - {type(e).__name__}: {e}")
        if 'response' in locals() and response.text: print(f"      Error Body: {response.text}")
        sys.exit(1)

# --- Test Functions (Unchanged sections are collapsed for brevity) ---
def test_health_check():
    print_test_header("Health Check")
    run_test("GET /", "GET", "http://127.0.0.1:8000/")

def test_prompt_endpoints():
    print_test_header("Prompt & Versioning")
    create_payload = {"name": f"Test Prompt {int(time.time())}", "task_description": "A test prompt.", "initial_prompt_text": "This is version 1."}
    created_prompt = run_test("Create Prompt", "POST", f"{BASE_URL}/prompts/", create_payload, expected_status=201)
    
    created_at = created_prompt.get("created_at")
    iso_format_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'
    assert re.match(iso_format_pattern, str(created_at)), f"FAIL: created_at '{created_at}' is not a valid ISO 8601 string."
    print_success("Date Format Validation")
    
    prompt_id = created_prompt["id"]
    run_test("List All Prompts", "GET", f"{BASE_URL}/prompts/")
    run_test("Get Single Prompt", "GET", f"{BASE_URL}/prompts/{prompt_id}")
    run_test("Update Prompt", "PATCH", f"{BASE_URL}/prompts/{prompt_id}", payload={"name": "Updated Test Prompt Name"})
    run_test("Create New Version", "POST", f"{BASE_URL}/prompts/{prompt_id}/versions", payload={"prompt_text": "This is v2.", "commit_message": "v2 test"}, expected_status=201)
    run_test("List All Versions", "GET", f"{BASE_URL}/prompts/{prompt_id}/versions")
    return prompt_id

def test_cross_user_security():
    # ... (Unchanged)
    print_test_header("Cross-User Security")
    HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
    create_payload = {"name": f"Security Test Prompt {int(time.time())}", "task_description": "Owned by primary user.", "initial_prompt_text": "Content"}
    created_prompt = run_test("Create Prompt (as Primary User)", "POST", f"{BASE_URL}/prompts/", create_payload, expected_status=201)
    prompt_id = created_prompt["id"]
    
    print("--- Switching to Second User for security tests ---")
    HEADERS["Authorization"] = f"Bearer {get_auth_token(SECOND_TEST_USER_ID)}"
    run_test("Update Prompt (as Second User)", "PATCH", f"{BASE_URL}/prompts/{prompt_id}", payload={"name": "Attempted Hijack"}, expected_status=403)
    run_test("Delete Prompt (as Second User)", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=403)
    
    print("--- Switching back to Primary User for cleanup ---")
    HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
    run_test("Cleanup Security Prompt (as Primary User)", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)

def test_ai_and_analysis_endpoints():
    # ... (Unchanged)
    print_test_header("AI & Analysis (under /prompts)")
    execute_payload = {"prompt_text": "Summarize Hamlet in one sentence.", "model": DEFAULT_GEMINI_MODEL, "variables": {}}
    response = run_test("Execute Prompt (Platform Key)", "POST", f"{BASE_URL}/prompts/execute", payload=execute_payload)
    assert "final_text" in response and response["final_text"], "Response body missing 'final_text' key"
    run_test("Diagnose Prompt", "POST", f"{BASE_URL}/prompts/diagnose", payload={"prompt_text": "write code"})
    run_test("Breakdown Prompt", "POST", f"{BASE_URL}/prompts/breakdown", payload={"prompt_text": "You are a helpful assistant."})


def test_template_and_sandbox_endpoints():
    # ... (Unchanged)
    print_test_header("Templates & Sandbox")
    unique_suffix = str(int(time.time()))
    template_payload = {"name": f"Test Persona: Pirate {unique_suffix}", "description": "A test persona.", "content": "You are a pirate who loves treasure.", "tags": ["persona", "pirate", "test_script"]}
    run_test("Create Template", "POST", f"{BASE_URL}/templates/", template_payload, expected_status=201)
    run_test("List All Templates", "GET", f"{BASE_URL}/templates/")
    run_test("Compose Prompt", "POST", f"{BASE_URL}/sandbox/compose", payload={"template_text": "Tell me a joke about a {{subject}}.", "variables": {"subject": "programmer"}})
    ai_gen_payload = {"style_description": f"A persona for a chef named Chef {unique_suffix}", "tags": ["persona", "chef", "test_script"]}
    run_test("AI Generate Template", "POST", f"{BASE_URL}/sandbox/generate-template", payload=ai_gen_payload, expected_status=201)
    run_test("Recommend Template", "POST", f"{BASE_URL}/sandbox/recommend-templates", payload={"task_description": "I need to write a professional email."})


# --- FINALIZED METRICS TEST FUNCTION ---
def test_metrics_endpoints():
    print_test_header("Metrics Endpoints")
    run_test("Get All Prompt Metrics (Initial)", "GET", f"{BASE_URL}/metrics/prompts/all")
    run_test("Get Recent Activity", "GET", f"{BASE_URL}/metrics/activity/recent")

    # --- Full Rating Lifecycle Test ---
    print("--- Testing Full Rating Lifecycle ---")
    
    # 1. Create a temporary prompt to rate
    create_payload = {"name": f"Rating Lifecycle Test {int(time.time())}", "task_description": "A prompt to test rating persistence.", "initial_prompt_text": "Version 1 text."}
    created_prompt = run_test("Create Prompt for Rating Test", "POST", f"{BASE_URL}/prompts/", create_payload, expected_status=201)
    prompt_id = created_prompt["id"]

    # 2. Rate version 1 of the new prompt with 5 stars
    rating_payload = {"prompt_id": prompt_id, "version_number": 1, "rating": 5}
    run_test("Rate Prompt (5 stars)", "POST", f"{BASE_URL}/metrics/rate", payload=rating_payload, expected_status=201)

    # 3. Fetch all prompts again to verify the rating "stuck"
    all_prompts = run_test("Verify Rating Persistence", "GET", f"{BASE_URL}/prompts/")
    
    # 4. Find our prompt and assert its values
    found_prompt = next((p for p in all_prompts if p['id'] == prompt_id), None)
    assert found_prompt, f"Rated prompt with ID {prompt_id} not found in list."
    
    rating_count = found_prompt.get('rating_count')
    avg_rating = found_prompt.get('average_rating')

    assert rating_count == 1, f"Expected rating_count to be 1, but got {rating_count}"
    assert avg_rating == 5.0, f"Expected average_rating to be 5.0, but got {avg_rating}"
    print_success("Rating count (1) and average (5.0) are correct")

    # 5. Clean up the temporary prompt
    run_test(f"Cleanup Rating Lifecycle Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)


def test_user_and_execution_endpoints():
    # ... (Unchanged)
    print_test_header("User & Managed Execution")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("--- SKIPPING OpenAI Managed Execution: OPENAI_API_KEY not found in .env ---")
    else:
        key_payload_openai = {"provider": "openai", "api_key": openai_api_key}
        run_test("Save User API Key (OpenAI)", "POST", f"{BASE_URL}/users/{PRIMARY_TEST_USER_ID}/keys", payload=key_payload_openai, expected_status=204)
        exec_payload_openai = {"user_id": PRIMARY_TEST_USER_ID, "model_name": DEFAULT_OPENAI_MODEL, "prompt_text": "What is the capital of Oregon?"}
        response_openai = run_test("Managed Execution (OpenAI)", "POST", f"{BASE_URL}/users/execute", payload=exec_payload_openai)
        assert "Salem" in response_openai.get("final_text", ""), "OpenAI managed execution response missing 'Salem'"
    
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("--- SKIPPING Google Managed Execution: GOOGLE_API_KEY not found in .env ---")
    else:
        key_payload_google = {"provider": "google", "api_key": google_api_key}
        run_test("Save User API Key (Google)", "POST", f"{BASE_URL}/users/{PRIMARY_TEST_USER_ID}/keys", payload=key_payload_google, expected_status=204)
        exec_payload_google = {"user_id": PRIMARY_TEST_USER_ID, "model_name": DEFAULT_GEMINI_MODEL, "prompt_text": "What is the largest planet in our solar system?"}
        response_google = run_test("Managed Execution (Google)", "POST", f"{BASE_URL}/users/execute", payload=exec_payload_google)
        assert "Jupiter" in response_google.get("final_text", ""), "Google managed execution response missing 'Jupiter'"


def cleanup(prompt_id):
    # ... (Unchanged)
    print_test_header("Cleaning Up Test Resources")
    if prompt_id:
        run_test(f"Delete Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)
    try:
        all_templates = run_test("List All Templates for Cleanup", "GET", f"{BASE_URL}/templates/")
        if all_templates:
            for t in all_templates:
                if "test_script" in t.get("tags", []):
                    run_test(f"Delete Template '{t['name']}'", "DELETE", f"{BASE_URL}/templates/{t['id']}", expected_status=204)
    except Exception as e:
        print(f"--- INFO: Cleanup of templates skipped: {e} ---")


# --- Main Execution Block (Unchanged) ---
if __name__ == "__main__":
    if not all([API_KEY, PRIMARY_TEST_USER_ID, SECOND_TEST_USER_ID, os.getenv("GOOGLE_APPLICATION_CREDENTIALS")]):
        print("❌ ERROR: Ensure required .env variables are set (API_KEY, REGULAR_USER_UID, SECOND_REGULAR_USER_UID, GOOGLE_APPLICATION_CREDENTIALS).")
        sys.exit(1)
    
    prompt_id_to_delete = None
    try:
        test_health_check()
        print(f"--- Authenticating primary test user: {PRIMARY_TEST_USER_ID} ---")
        HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
        print("✅ Authentication successful.")
        
        prompt_id_to_delete = test_prompt_endpoints()
        test_ai_and_analysis_endpoints()
        test_template_and_sandbox_endpoints()
        test_metrics_endpoints()
        test_user_and_execution_endpoints()
        test_cross_user_security()
        
    finally:
        if 'Authorization' not in HEADERS or get_auth_token(SECOND_TEST_USER_ID) in HEADERS.get('Authorization', ''):
            print("--- Re-authenticating as Primary User for cleanup ---")
            HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
            
        cleanup(prompt_id_to_delete)
        print("\n" + "="*20 + " TEST SUITE COMPLETE " + "="*20 + "\n")