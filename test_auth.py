# ~/rankforge/test_auth.py

import requests
import os
import sys
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth

# --- Configuration ---
load_dotenv()
BASE_URL = "http://127.0.0.1:8000"
API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

ADMIN_USER_ID = os.getenv("ADMIN_USER_UID")
REGULAR_USER_ID = os.getenv("REGULAR_USER_UID")

# --- Initialize Firebase Admin SDK ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK initialized.")
except Exception as e:
    print(f"❌ Could not initialize Firebase Admin SDK: {e}")
    sys.exit(1)


def get_firebase_id_token(user_uid: str):
    """Generates an ID token for a specific user UID."""
    print(f"\n--- Authenticating User: {user_uid} ---")
    try:
        custom_token = auth.create_custom_token(user_uid)
        rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}"
        response = requests.post(rest_api_url, data={"token": custom_token, "returnSecureToken": True})
        response.raise_for_status()
        id_token = response.json().get("idToken")
        print(f"✅ Successfully retrieved ID Token.")
        return id_token
    except Exception as e:
        print(f"❌ Failed to get ID token for {user_uid}: {e}")
        if 'response' in locals():
            print(f"   Response: {response.text}")
        sys.exit(1)


def run_authenticated_test(name, method, url, token, payload=None, expected_status=200):
    """Helper function to run a test with an Authorization header."""
    print(f"\n--- Testing: {name} ---")
    headers = { "Content-Type": "application/json", "Authorization": f"Bearer {token}" }
    try:
        response = requests.request(method.upper(), url, headers=headers, data=json.dumps(payload) if payload else None)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        print(f"✅ Test Passed: Received expected status code {expected_status}.")
        if response.status_code != 204 and response.text:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        if 'response' in locals() and response.text: print(f"Error Body: {response.text}")
        sys.exit(1)


if __name__ == "__main__":
    if not all([API_KEY, ADMIN_USER_ID, REGULAR_USER_ID]):
        print("❌ ERROR: Ensure all required UIDs and Keys are in your .env file.")
        sys.exit(1)
        
    admin_token = get_firebase_id_token(ADMIN_USER_ID)
    regular_user_token = get_firebase_id_token(REGULAR_USER_ID)
    
    # === SCENARIO 1: A regular user CANNOT delete another user's prompt ===
    print("\n\n" + "="*10 + " SCENARIO 1: NON-OWNER CANNOT DELETE " + "="*10)
    prompt_payload = {"name": "Prompt Owned by Admin", "task_description": "Admin's prompt", "initial_prompt_text": "Text"}
    
    # 1. Admin creates a prompt
    admin_prompt = run_authenticated_test("Admin Creates Prompt", "POST", f"{BASE_URL}/prompts/", admin_token, prompt_payload, 201)
    admin_prompt_id = admin_prompt["id"]
    print(f"   > Admin Prompt ID: {admin_prompt_id}")

    # 2. Regular User tries to delete it (should fail)
    run_authenticated_test(
        "Regular User Tries to Delete Admin's Prompt (FAILURE)", "DELETE",
        f"{BASE_URL}/prompts/{admin_prompt_id}", regular_user_token, expected_status=403
    )

    # === SCENARIO 2: A regular user CAN delete their own prompt ===
    print("\n\n" + "="*10 + " SCENARIO 2: OWNER CAN DELETE " + "="*10)
    regular_prompt = run_authenticated_test("Regular User Creates Prompt", "POST", f"{BASE_URL}/prompts/", regular_user_token, prompt_payload, 201)
    regular_prompt_id = regular_prompt["id"]
    print(f"   > Regular User's Prompt ID: {regular_prompt_id}")
    
    run_authenticated_test(
        "Regular User Deletes Own Prompt (SUCCESS)", "DELETE",
        f"{BASE_URL}/prompts/{regular_prompt_id}", regular_user_token, expected_status=204
    )

    # === SCENARIO 3: An admin CAN delete another user's prompt ===
    print("\n\n" + "="*10 + " SCENARIO 3: ADMIN CAN DELETE " + "="*10)
    prompt_to_be_deleted_by_admin = run_authenticated_test(
        "Regular User Creates Another Prompt", "POST", f"{BASE_URL}/prompts/",
        regular_user_token, payload=prompt_payload, expected_status=201
    )["id"]
    print(f"   > Prompt to be deleted by Admin: {prompt_to_be_deleted_by_admin}")

    run_authenticated_test(
        "Admin Deletes Regular User's Prompt (SUCCESS)", "DELETE",
        f"{BASE_URL}/prompts/{prompt_to_be_deleted_by_admin}", admin_token, expected_status=204
    )
    
    # --- Cleanup Admin's initial prompt ---
    run_authenticated_test("Admin Cleans Up Own Prompt", "DELETE", f"{BASE_URL}/prompts/{admin_prompt_id}", admin_token, expected_status=204)

    print("\n\n🎉 All Role-Based Access Control tests passed successfully!")