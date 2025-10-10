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

# --- Configuration ---
load_dotenv()
BASE_URL = "http://127.0.0.1:8000/api/v1"
API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
PRIMARY_TEST_USER_ID = os.getenv("REGULAR_USER_UID", "test_suite_user_12345")
SECOND_TEST_USER_ID = os.getenv("SECOND_REGULAR_USER_UID", "test_suite_user_67890")

# --- Firebase & Auth ---
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
def print_info(message): print(f"  [*] INFO: {message}")

def run_test(name, method, url, payload=None, expected_status=200, headers=None):
    test_headers = headers if headers is not None else HEADERS
    try:
        response = requests.request(method.upper(), url, headers=test_headers, data=json.dumps(payload) if payload else None)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        print_success(name)
        if response.status_code != 204 and response.text:
            return response.json()
        return None
    except (requests.exceptions.RequestException, AssertionError, json.JSONDecodeError) as e:
        print(f"  ❌ FAILED: {name} - {type(e).__name__}: {e}")
        if 'response' in locals() and response.text: print(f"      Error Body: {response.text}")
        sys.exit(1)

# --- Test Functions ---

def test_security_and_data_scoping():
    print_test_header("Security & Data Scoping")

    # 1. Test for Anonymous Data Leak
    print_info("Testing for anonymous data leaks on all user-specific endpoints...")
    anon_headers = {"Content-Type": "application/json", "accept": "application/json"}
    run_test("Anonymous GET /prompts/", "GET", f"{BASE_URL}/prompts/", expected_status=401, headers=anon_headers)
    run_test("Anonymous GET /metrics/activity/recent", "GET", f"{BASE_URL}/metrics/activity/recent", expected_status=401, headers=anon_headers)
    run_test("Anonymous GET /metrics/prompts/starred", "GET", f"{BASE_URL}/metrics/prompts/starred", expected_status=401, headers=anon_headers)
    print_success("All anonymous access tests passed (correctly denied).")

    # 2. Setup: Create prompts for two different users
    print_info("Setting up prompts for two different users...")
    
    # User A's Prompts
    HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
    prompt_a1_payload = {"name": f"User A Prompt 1 (Rated 5)", "task_description": "User A's first prompt.", "initial_prompt_text": "Content A1"}
    prompt_a1 = run_test("Create User A's 1st Prompt", "POST", f"{BASE_URL}/prompts/", payload=prompt_a1_payload, expected_status=201)
    
    prompt_a2_payload = {"name": f"User A Prompt 2 (Rated 1)", "task_description": "User A's second prompt.", "initial_prompt_text": "Content A2"}
    prompt_a2 = run_test("Create User A's 2nd Prompt", "POST", f"{BASE_URL}/prompts/", payload=prompt_a2_payload, expected_status=201)
    
    # User B's Prompt
    HEADERS["Authorization"] = f"Bearer {get_auth_token(SECOND_TEST_USER_ID)}"
    prompt_b1_payload = {"name": f"User B Prompt 1 (Rated 5)", "task_description": "User B's only prompt.", "initial_prompt_text": "Content B1"}
    prompt_b1 = run_test("Create User B's Prompt", "POST", f"{BASE_URL}/prompts/", payload=prompt_b1_payload, expected_status=201)

    # 3. Rate the prompts (User B rates their own prompt)
    print_info("Rating prompts for each user...")
    run_test("Rate User B's Prompt (5 stars)", "POST", f"{BASE_URL}/metrics/rate", payload={"prompt_id": prompt_b1['id'], "version_number": 1, "rating": 5}, expected_status=201)
    
    # Switch back to User A to rate their prompts
    HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"
    run_test("Rate User A's 1st Prompt (5 stars)", "POST", f"{BASE_URL}/metrics/rate", payload={"prompt_id": prompt_a1['id'], "version_number": 1, "rating": 5}, expected_status=201)
    run_test("Rate User A's 2nd Prompt (1 star)", "POST", f"{BASE_URL}/metrics/rate", payload={"prompt_id": prompt_a2['id'], "version_number": 1, "rating": 1}, expected_status=201)

    # 4. Test Data Scoping as User A
    print_info("Verifying data scoping for User A...")
    HEADERS["Authorization"] = f"Bearer {get_auth_token(PRIMARY_TEST_USER_ID)}"

    # Test GET /prompts/
    user_a_prompts = run_test("List Prompts (as User A)", "GET", f"{BASE_URL}/prompts/")
    assert len(user_a_prompts) == 2, f"Expected 2 prompts for User A, but got {len(user_a_prompts)}"
    assert {p['id'] for p in user_a_prompts} == {prompt_a1['id'], prompt_a2['id']}, "User A's prompt list is incorrect."
    print_success("GET /prompts/ correctly scoped to User A.")

    # Test GET /metrics/prompts/starred
    user_a_starred = run_test("List Starred Prompts (as User A)", "GET", f"{BASE_URL}/metrics/prompts/starred")
    assert len(user_a_starred) == 1, f"Expected 1 starred prompt for User A, but got {len(user_a_starred)}"
    assert user_a_starred[0]['id'] == prompt_a1['id'], "User A's starred prompt is incorrect."
    print_success("GET /metrics/prompts/starred correctly scoped to User A.")

    # Test GET /metrics/activity/recent
    user_a_activity = run_test("Get Recent Activity (as User A)", "GET", f"{BASE_URL}/metrics/activity/recent")
    user_a_activity_ids = {a['promptId'] for a in user_a_activity}
    assert {prompt_a1['id'], prompt_a2['id']}.issubset(user_a_activity_ids), "User A's activity is missing created prompts."
    assert prompt_b1['id'] not in user_a_activity_ids, "User A's activity contains data from User B."
    print_success("GET /metrics/activity/recent correctly scoped to User A.")

    # 5. Cleanup
    print_info("Cleaning up test prompts...")
    run_test("Delete User A's 1st Prompt", "DELETE", f"{BASE_URL}/prompts/{prompt_a1['id']}", expected_status=204)
    run_test("Delete User A's 2nd Prompt", "DELETE", f"{BASE_URL}/prompts/{prompt_a2['id']}", expected_status=204)
    HEADERS["Authorization"] = f"Bearer {get_auth_token(SECOND_TEST_USER_ID)}"
    run_test("Delete User B's Prompt", "DELETE", f"{BASE_URL}/prompts/{prompt_b1['id']}", expected_status=204)

# --- Main Execution Block ---
if __name__ == "__main__":
    if not all([API_KEY, PRIMARY_TEST_USER_ID, SECOND_TEST_USER_ID, os.getenv("GOOGLE_APPLICATION_CREDENTIALS")]):
        print("❌ ERROR: Ensure required .env variables are set.")
        sys.exit(1)
    
    test_security_and_data_scoping()

    print("\n" + "="*20 + " ALL TESTS PASSED " + "="*20 + "\n")