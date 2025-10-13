import os
import sys
import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth

def get_id_token(uid: str, api_key: str) -> str:
    """Creates a custom token for the given UID and exchanges it for a Firebase ID token."""
    try:
        custom_token = auth.create_custom_token(uid)
        rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
        response = requests.post(rest_api_url, data={"token": custom_token, "returnSecureToken": True})
        response.raise_for_status()
        return response.json().get("idToken")
    except Exception as e:
        print(f"❌ Failed to get ID token for {uid}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    Main function to initialize Firebase, get tokens for two test users,
    and print them as shell export commands.
    """
    # --- Configuration ---
    load_dotenv()
    required_vars = [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "FIREBASE_WEB_API_KEY",
        "REGULAR_USER_UID",
        "SECOND_REGULAR_USER_UID"
    ]
    if not all(os.getenv(var) for var in required_vars):
        print("❌ ERROR: Ensure all required .env variables are set:", file=sys.stderr)
        for var in required_vars:
            if not os.getenv(var):
                print(f"  - Missing: {var}", file=sys.stderr)
        sys.exit(1)

    api_key = os.getenv("FIREBASE_WEB_API_KEY")
    user_id_a = os.getenv("REGULAR_USER_UID")
    user_id_b = os.getenv("SECOND_REGULAR_USER_UID")

    # --- Firebase Initialization ---
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
            firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin SDK initialized.", file=sys.stderr)
    except Exception as e:
        print(f"❌ Could not initialize Firebase Admin SDK: {e}", file=sys.stderr)
        sys.exit(1)
        
    # --- Generate Tokens ---
    print("\n🔄 Generating fresh tokens...", file=sys.stderr)
    token_a = get_id_token(user_id_a, api_key)
    token_b = get_id_token(user_id_b, api_key)
    print("✅ Tokens generated successfully.", file=sys.stderr)

    # --- Print Output ---
    # The output is formatted as shell commands.
    # You can copy/paste this directly into test_container.sh or your terminal.
    print("\n# === Copy the lines below and paste them into your test script or terminal ===\n")
    print(f'FIREBASE_ID_TOKEN_USER_A="{token_a}"')
    print(f'USER_ID_A="{user_id_a}"')
    print("")
    print(f'FIREBASE_ID_TOKEN_USER_B="{token_b}"')
    print(f'USER_ID_B="{user_id_b}"')

if __name__ == "__main__":
    main()