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
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite" # Corrected model
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
def print_failure(message): print(f"  ❌ FAILED: {message}")

def run_test(name, method, url, payload=None, expected_status=None, exit_on_fail=True):
    """
    Helper function to run a single API test with strict JSON parsing.
    """
    try:
        response = requests.request(method.upper(), url, headers=HEADERS, data=json.dumps(payload) if payload else None)
        if expected_status:
            assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        else:
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        print_success(name)

        if response.status_code != 204 and response.text: # Check if there's content
             # Attempt to parse JSON only if there's text
             try:
                 parsed_json = json.loads(response.text)
                 return parsed_json
             except json.JSONDecodeError:
                 print(f"  ⚠️ WARNING: Non-JSON response for {name}: {response.text[:100]}...")
                 return response.text # Return raw text if not JSON
        return None # Return None for 204 No Content or empty body
    except (requests.exceptions.RequestException, AssertionError, requests.exceptions.HTTPError) as e:
        print_failure(f"{name} - {type(e).__name__}: {e}")
        # Try to print error body if available
        error_body = ""
        if 'response' in locals() and hasattr(response, 'text') and response.text:
            error_body = response.text
            try: # Try to pretty print if JSON
                 error_body = json.dumps(json.loads(response.text), indent=2)
            except json.JSONDecodeError:
                 pass # Keep raw text if not JSON
            print(f"      Error Body: {error_body}")
        if exit_on_fail:
            sys.exit(1)
        return None # Return None on a non-exiting failure


# --- Test Functions ---
def test_health_check():
    print_test_header("Health Check")
    run_test("GET /", "GET", "http://127.0.0.1:8000/")

def test_prompt_endpoints():
    print_test_header("Prompt & Versioning")
    create_payload = {"name": f"Test Prompt {int(time.time())}", "task_description": "A test prompt.", "initial_prompt_text": "This is version 1."}
    created_prompt = run_test("Create Prompt", "POST", f"{BASE_URL}/prompts", create_payload, expected_status=201) # No slash

    created_at = created_prompt.get("created_at")
    iso_format_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'
    assert re.match(iso_format_pattern, str(created_at)), f"FAIL: created_at '{created_at}' is not a valid ISO 8601 string."
    print_success("Date Format Validation")

    prompt_id = created_prompt["id"]
    run_test("List User Prompts", "GET", f"{BASE_URL}/prompts") # No slash
    run_test("Get Single Prompt (No Slash)", "GET", f"{BASE_URL}/prompts/{prompt_id}")
    run_test("Update Prompt", "PATCH", f"{BASE_URL}/prompts/{prompt_id}", payload={"name": "Updated Test Prompt Name"})
    run_test("Create New Version", "POST", f"{BASE_URL}/prompts/{prompt_id}/versions", payload={"prompt_text": "This is v2.", "commit_message": "v2 test"}, expected_status=201)
    run_test("List All Versions", "GET", f"{BASE_URL}/prompts/{prompt_id}/versions")
    return prompt_id

# --- MODIFIED: Added Template security checks ---
def test_cross_user_security():
    print_test_header("Cross-User Security")

    # --- User A Creates Resources ---
    HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
    print(f"\n--- Creating resources as Primary User ({PRIMARY_TEST_USER_ID}) ---")
    prompt_payload_A = {"name": f"Security Prompt A {int(time.time())}", "task_description": "Owned by A.", "initial_prompt_text": "Content A"}
    created_prompt_A = run_test("Create Prompt (User A)", "POST", f"{BASE_URL}/prompts", prompt_payload_A, expected_status=201) # No slash
    prompt_id_A = created_prompt_A["id"]

    template_payload_A = {"name": f"Security Template A {int(time.time())}", "description": "Owned by A.", "content": "Template A", "tags": ["security_test_A"]}
    created_template_A = run_test("Create Template (User A)", "POST", f"{BASE_URL}/templates/", template_payload_A, expected_status=201) # Slash needed for create
    template_id_A = created_template_A["id"]

    # --- User B Attempts Access ---
    print(f"\n--- Switching to Second User ({SECOND_TEST_USER_ID}) for security tests ---")
    HEADERS["Authorization"] = f"Bearer {get_auth_token(SECOND_TEST_USER_ID)}"

    # Prompt Tests (Should Fail)
    run_test("Get Prompt A (as User B)", "GET", f"{BASE_URL}/prompts/{prompt_id_A}", expected_status=403, exit_on_fail=False)
    run_test("Update Prompt A (as User B)", "PATCH", f"{BASE_URL}/prompts/{prompt_id_A}", payload={"name": "Hijack Attempt B"}, expected_status=403, exit_on_fail=False)
    run_test("Delete Prompt A (as User B)", "DELETE", f"{BASE_URL}/prompts/{prompt_id_A}", expected_status=403, exit_on_fail=False)

    # Template Tests (Should Fail - Update/Delete)
    run_test("Get Template A (as User B - No Slash)", "GET", f"{BASE_URL}/templates/{template_id_A}", expected_status=403, exit_on_fail=False) # Check if GET is protected
    # run_test("Get Template A (as User B - With Slash)", "GET", f"{BASE_URL}/templates/{template_id_A}/", expected_status=403, exit_on_fail=False) # Optional: Check slashed route too
    run_test("Update Template A (as User B)", "PATCH", f"{BASE_URL}/templates/{template_id_A}", payload={"name": "Hijack Attempt B"}, expected_status=403, exit_on_fail=False) # No slash for update
    run_test("Delete Template A (as User B)", "DELETE", f"{BASE_URL}/templates/{template_id_A}", expected_status=403, exit_on_fail=False) # No slash for delete

    # --- NEW: List Templates Test (Should NOT show Template A) ---
    print("\n--- Checking Template List Isolation (as User B) ---")
    templates_list_B = run_test("List Templates (as User B)", "GET", f"{BASE_URL}/templates/") # Slash needed for list
    found_template_A = False
    if templates_list_B: # Check if list is not None
        for template in templates_list_B:
            if template.get("id") == template_id_A:
                found_template_A = True
                break
    if found_template_A:
        print_failure(f"List Templates Isolation FAILED: User B can see User A's template (ID: {template_id_A})")
        sys.exit(1) # Fail the test suite if isolation fails
    else:
        print_success("List Templates Isolation Check: User B cannot see User A's template.")

    # --- Cleanup (as User A) ---
    print(f"\n--- Switching back to Primary User ({PRIMARY_TEST_USER_ID}) for cleanup ---")
    HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
    run_test(f"Cleanup Prompt A (as User A)", "DELETE", f"{BASE_URL}/prompts/{prompt_id_A}", expected_status=204)
    run_test(f"Cleanup Template A (as User A)", "DELETE", f"{BASE_URL}/templates/{template_id_A}", expected_status=204) # No slash for delete

def test_ai_and_analysis_endpoints():
    print_test_header("AI & Analysis (under /prompts)")
    execute_payload = {"prompt_text": "Summarize Hamlet in one sentence.", "model": DEFAULT_GEMINI_MODEL, "variables": {}}
    response = run_test("Execute Prompt (Platform Key)", "POST", f"{BASE_URL}/prompts/execute", payload=execute_payload)
    assert response and "final_text" in response and response["final_text"], "Execute response missing 'final_text'"
    run_test("Diagnose Prompt", "POST", f"{BASE_URL}/prompts/diagnose", payload={"prompt_text": "write code"})
    run_test("Breakdown Prompt", "POST", f"{BASE_URL}/prompts/breakdown", payload={"prompt_text": "You are a helpful assistant."})


def test_template_and_sandbox_endpoints():
    print_test_header("Templates & Sandbox")
    unique_suffix = str(int(time.time()))
    template_payload = {"name": f"Test Template {unique_suffix}", "description": "A test template.", "content": "Template content.", "tags": ["test_script"]}

    created_template = run_test("Create Template", "POST", f"{BASE_URL}/templates/", template_payload, expected_status=201) # Slash needed
    template_id = created_template["id"]

    run_test("List All Templates", "GET", f"{BASE_URL}/templates/") # Slash needed

    print("\n--- Running Template Detail Endpoint Diagnostics ---")
    # Test 1: Route WITHOUT slash (Should PASS with 200 OK after backend fix)
    run_test(
        name="Get Single Template (No Slash)",
        method="GET",
        url=f"{BASE_URL}/templates/{template_id}",
        expected_status=200, # Expect success now
        exit_on_fail=True # Fail immediately if this breaks
    )

    # Test 2: Route WITH slash (Should fail, likely 404, confirm backend doesn't accept it)
    run_test(
        name="Get Single Template (With Slash - Expect 404)",
        method="GET",
        url=f"{BASE_URL}/templates/{template_id}/",
        expected_status=404, # Expect 404 as backend route is likely specific
        exit_on_fail=False # Log failure but continue
    )
    print("--- End of Template Detail Diagnostics ---")

    run_test("Compose Prompt", "POST", f"{BASE_URL}/sandbox/compose", payload={"template_text": "Tell me a joke about a {{subject}}.", "variables": {"subject": "programmer"}})
    ai_gen_payload = {"style_description": f"A persona for a chef named Chef {unique_suffix}", "tags": ["persona", "chef", "test_script"]}
    run_test("AI Generate Template", "POST", f"{BASE_URL}/sandbox/generate-template", payload=ai_gen_payload, expected_status=201)
    run_test("Recommend Template", "POST", f"{BASE_URL}/sandbox/recommend-templates", payload={"task_description": "I need to write a professional email."})

    # Return the template_id for cleanup
    return template_id


def test_metrics_endpoints(prompt_id_to_rate: str): # Accept prompt_id
    print_test_header("Metrics Endpoints")
    run_test("Get All Prompt Metrics (Initial)", "GET", f"{BASE_URL}/metrics/prompts/all")
    run_test("Get Recent Activity", "GET", f"{BASE_URL}/metrics/activity/recent")

    # --- Full Rating Lifecycle Test ---
    print("\n--- Testing Full Rating Lifecycle ---")

    # Ensure a valid prompt_id exists
    if not prompt_id_to_rate:
         print("  ⚠️ SKIPPING Rating Lifecycle Test: No valid prompt ID provided.")
         return

    # 1. Rate version 1 of the provided prompt with 5 stars
    rating_payload = {"prompt_id": prompt_id_to_rate, "version_number": 1, "rating": 5}
    run_test("Rate Prompt (5 stars)", "POST", f"{BASE_URL}/metrics/rate", payload=rating_payload, expected_status=201)

    # 2. Fetch all prompts again to verify the rating "stuck"
    all_prompts = run_test("Verify Rating Persistence", "GET", f"{BASE_URL}/prompts/") # No slash

    # 3. Find our prompt and assert its values
    found_prompt = None
    if all_prompts: # Check if list is not None
        found_prompt = next((p for p in all_prompts if p['id'] == prompt_id_to_rate), None)

    assert found_prompt, f"Rated prompt with ID {prompt_id_to_rate} not found in list."

    rating_count = found_prompt.get('rating_count')
    avg_rating = found_prompt.get('average_rating')

    # Handle potential None values before assertion
    assert rating_count is not None and rating_count == 1, f"Expected rating_count to be 1, but got {rating_count}"
    assert avg_rating is not None and avg_rating == 5.0, f"Expected average_rating to be 5.0, but got {avg_rating}"
    print_success("Rating count (1) and average (5.0) are correct")

    # Note: Cleanup of the rated prompt happens in the main 'finally' block


def test_user_and_execution_endpoints():
    print_test_header("User & Managed Execution")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("--- SKIPPING OpenAI Managed Execution: OPENAI_API_KEY not found in .env ---")
    else:
        key_payload_openai = {"provider": "openai", "api_key": openai_api_key}
        run_test("Save User API Key (OpenAI)", "POST", f"{BASE_URL}/users/{PRIMARY_TEST_USER_ID}/keys", payload=key_payload_openai, expected_status=204)
        exec_payload_openai = {"user_id": PRIMARY_TEST_USER_ID, "model_name": DEFAULT_OPENAI_MODEL, "prompt_text": "What is the capital of Oregon?"}
        response_openai = run_test("Managed Execution (OpenAI)", "POST", f"{BASE_URL}/users/execute", payload=exec_payload_openai)
        assert response_openai and "Salem" in response_openai.get("final_text", ""), "OpenAI managed execution response missing 'Salem'"

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("--- SKIPPING Google Managed Execution: GOOGLE_API_KEY not found in .env ---")
    else:
        key_payload_google = {"provider": "google", "api_key": google_api_key}
        run_test("Save User API Key (Google)", "POST", f"{BASE_URL}/users/{PRIMARY_TEST_USER_ID}/keys", payload=key_payload_google, expected_status=204)
        exec_payload_google = {"user_id": PRIMARY_TEST_USER_ID, "model_name": DEFAULT_GEMINI_MODEL, "prompt_text": "What is the largest planet in our solar system?"}
        response_google = run_test("Managed Execution (Google)", "POST", f"{BASE_URL}/users/execute", payload=exec_payload_google)
        assert response_google and "Jupiter" in response_google.get("final_text", ""), "Google managed execution response missing 'Jupiter'"


def cleanup(prompt_id: str | None, template_id: str | None): # Accept both IDs
    print_test_header("Cleaning Up Test Resources")
    # Ensure cleanup runs as the primary user
    print(f"--- Ensuring cleanup runs as Primary User ({PRIMARY_TEST_USER_ID}) ---")
    HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"

    # Cleanup prompt created in test_prompt_endpoints
    if prompt_id:
        run_test(f"Delete Main Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)
    else:
         print("  ⚠️ INFO: No main prompt ID to clean up.")

    # Cleanup template created in test_template_and_sandbox_endpoints
    if template_id:
        run_test(f"Delete Main Template {template_id}", "DELETE", f"{BASE_URL}/templates/{template_id}", expected_status=204) # No slash
    else:
         print("  ⚠️ INFO: No main template ID to clean up.")

    # Cleanup any remaining test_script templates (more robust)
    try:
        print("\n--- Cleaning up remaining 'test_script' tagged templates ---")
        all_templates = run_test("List All Templates for Tag Cleanup", "GET", f"{BASE_URL}/templates/") # Slash needed
        if all_templates:
            deleted_count = 0
            for t in all_templates:
                # Check if 'test_script' is in tags and belongs to the primary user
                if "test_script" in t.get("tags", []) and t.get("user_id") == PRIMARY_TEST_USER_ID:
                    run_test(f"Delete Tagged Template '{t['name']}' ({t['id']})", "DELETE", f"{BASE_URL}/templates/{t['id']}", expected_status=204, exit_on_fail=False) # No slash, don't exit on fail
                    deleted_count += 1
            print(f"  -> Deleted {deleted_count} tagged templates.")
        else:
            print("  -> No templates found for tag cleanup.")
    except Exception as e:
        print(f"--- INFO: Cleanup of tagged templates encountered an error: {e} ---")


# --- Main Execution Block ---
if __name__ == "__main__":
    if not all([API_KEY, PRIMARY_TEST_USER_ID, SECOND_TEST_USER_ID, os.getenv("GOOGLE_APPLICATION_CREDENTIALS")]):
        print("❌ ERROR: Ensure required .env variables are set (API_KEY, REGULAR_USER_UID, SECOND_REGULAR_USER_UID, GOOGLE_APPLICATION_CREDENTIALS).")
        sys.exit(1)

    # Variables to store IDs for cleanup
    main_prompt_id = None
    main_template_id = None

    try:
        test_health_check()

        print(f"\n--- Authenticating primary test user: {PRIMARY_TEST_USER_ID} ---")
        HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
        print("✅ Authentication successful.")

        main_prompt_id = test_prompt_endpoints() # Capture the main prompt ID
        test_ai_and_analysis_endpoints()
        main_template_id = test_template_and_sandbox_endpoints() # Capture the main template ID
        test_metrics_endpoints(main_prompt_id) # Pass prompt_id for rating test
        test_user_and_execution_endpoints()
        test_cross_user_security() # This now includes the template isolation check

    finally:
        # Cleanup ensures it runs as the primary user
        cleanup(main_prompt_id, main_template_id)
        print("\n" + "="*20 + " TEST SUITE COMPLETE " + "="*20 + "\n")