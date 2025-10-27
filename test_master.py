import requests
import json
import sys
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth

# --- Configuration ---
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000/api/v1")
API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
PRIMARY_TEST_USER_ID = os.getenv("REGULAR_USER_UID", "test_suite_user_12345")
SECOND_TEST_USER_ID = os.getenv("SECOND_REGULAR_USER_UID", "test_suite_user_67890")

# --- Firebase & Auth ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK initialized for master test.")
except Exception as e:
    print(f"❌ Could not initialize Firebase Admin SDK: {e}")
    sys.exit(1)

def get_auth_token(user_uid: str):
    """Generates a Firebase ID token for the given user UID."""
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
def print_success(message): print(f"   ✅ SUCCESS: {message}")
def print_info(message): print(f"   [*] INFO: {message}")

def run_test(name, method, url, payload=None, expected_status=200, headers=None):
    """A robust test runner that raises exceptions on failure."""
    test_headers = headers if headers is not None else HEADERS
    response = requests.request(method.upper(), url, headers=test_headers, data=json.dumps(payload) if payload else None)
    
    if response.status_code != expected_status:
        error_message = f"Expected status {expected_status}, but got {response.status_code}."
        try:
            error_body = response.json()
            error_message += f"\n         Response Body: {json.dumps(error_body, indent=2)}"
        except json.JSONDecodeError:
            error_message += f"\n         Response Body: {response.text}"
        raise AssertionError(f"Test '{name}' FAILED: {error_message}")

    print_success(name)
    if response.status_code in [200, 201] and response.text:
        return response.json()
    return None

def test_security_and_data_scoping():
    """The main test function with guaranteed cleanup."""
    print_test_header("Security & Data Scoping")

    prompts_to_delete = {"user_a": [], "user_b": []}
    
    try:
        # 1. Anonymous Access Tests
        print_info("Testing for anonymous data leaks...")
        anon_headers = {"Content-Type": "application/json", "accept": "application/json"}
        run_test("Anonymous GET /prompts/", "GET", f"{BASE_URL}/prompts/", expected_status=401, headers=anon_headers)
        run_test("Anonymous GET /metrics/activity/recent", "GET", f"{BASE_URL}/metrics/activity/recent", expected_status=401, headers=anon_headers)
        run_test("Anonymous GET /metrics/prompts/starred", "GET", f"{BASE_URL}/metrics/prompts/starred", expected_status=401, headers=anon_headers)
        print_success("All anonymous access tests passed (correctly denied).")

        # 2. Setup Test Data
        print_info("Setting up prompts for two different users...")
        
        HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
        prompt_a1_payload = {"name": "User A Prompt 1", "task_description": "Task for A1", "initial_prompt_text": "Content for A1"}
        prompt_a1 = run_test("Create User A's 1st Prompt", "POST", f"{BASE_URL}/prompts/", payload=prompt_a1_payload, expected_status=201)
        prompts_to_delete["user_a"].append(prompt_a1['id'])

        prompt_a2_payload = {"name": "User A Prompt 2", "task_description": "Task for A2", "initial_prompt_text": "Content for A2"}
        prompt_a2 = run_test("Create User A's 2nd Prompt", "POST", f"{BASE_URL}/prompts/", payload=prompt_a2_payload, expected_status=201)
        prompts_to_delete["user_a"].append(prompt_a2['id'])

        HEADERS["Authorization"] = f"Bearer {get_auth_token(SECOND_TEST_USER_ID)}"
        prompt_b1_payload = {"name": "User B Prompt 1", "task_description": "Task for B1", "initial_prompt_text": "Content for B1"}
        prompt_b1 = run_test("Create User B's Prompt", "POST", f"{BASE_URL}/prompts/", payload=prompt_b1_payload, expected_status=201)
        prompts_to_delete["user_b"].append(prompt_b1['id'])

        # 3. Test Data Scoping as User A
        print_info("Verifying data scoping for User A...")
        HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
        
        user_a_prompts = run_test("List Prompts (as User A)", "GET", f"{BASE_URL}/prompts/")
        assert len(user_a_prompts) == 2, f"Expected 2 prompts for User A, but got {len(user_a_prompts)}"
        assert {p['id'] for p in user_a_prompts} == set(prompts_to_delete["user_a"]), "User A's prompt list is incorrect."
        print_success("GET /prompts/ is correctly scoped to User A.")

    except AssertionError as e:
        print(f"\n--- TEST FAILED ---\n{e}")
        sys.exit(1)

    finally:
        # 4. GUARANTEED CLEANUP
        print_info("Cleaning up all created test prompts...")
        if prompts_to_delete["user_a"]:
            HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
            for prompt_id in prompts_to_delete["user_a"]:
                try:
                    run_test(f"Delete User A Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)
                except AssertionError as e:
                    print(f"      - Warning: Cleanup failed for prompt {prompt_id}: {e}")
        
        if prompts_to_delete["user_b"]:
            HEADERS["Authorization"] = f"Bearer {get_auth_token(SECOND_TEST_USER_ID)}"
            for prompt_id in prompts_to_delete["user_b"]:
                try:
                    run_test(f"Delete User B Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)
                except AssertionError as e:
                    print(f"      - Warning: Cleanup failed for prompt {prompt_id}: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    if not all([API_KEY, PRIMARY_TEST_USER_ID, SECOND_TEST_USER_ID, os.getenv("GOOGLE_APPLICATION_CREDENTIALS")]):
        print("❌ ERROR: Ensure required .env variables are set (FIREBASE_WEB_API_KEY, REGULAR_USER_UID, etc.).")
        sys.exit(1)
    
    test_security_and_data_scoping()

    print("\n" + "="*20 + " ALL TESTS PASSED " + "="*20 + "\n")