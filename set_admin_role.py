# ~/rankforge/set_admin_role.py

import sys
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth

# --- Configuration ---
load_dotenv()

def initialize_firebase_admin():
    """Initializes the Firebase Admin SDK using service account credentials."""
    try:
        if not firebase_admin._apps: # Prevent re-initializing
            cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
            firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"❌ ERROR: Could not initialize Firebase Admin SDK: {e}")
        sys.exit(1)

def set_admin_role(user_uid: str):
    """
    Sets a custom user claim on a Firebase user to grant them an 'admin' role.
    """
    print(f"\nAttempting to set 'admin' role for user: {user_uid}")
    try:
        # Set the custom claim. This will overwrite any existing claims.
        auth.set_custom_user_claims(user_uid, {'role': 'admin'})
        
        # Verify the claim was set
        user = auth.get_user(user_uid)
        if user.custom_claims and user.custom_claims.get('role') == 'admin':
            print(f"✅ Success! User {user.email} (UID: {user_uid}) has been granted the 'admin' role.")
            print("   The new role will be included in their ID token the next time they log in.")
        else:
            print("❌ Verification failed. The admin role was not set correctly.")

    except Exception as e:
        print(f"❌ ERROR: Failed to set custom claim for user {user_uid}.")
        print(f"   Please ensure the UID is correct and the user exists in Firebase Authentication.")
        print(f"   Error details: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure a user UID is provided as a command-line argument
    if len(sys.argv) != 2:
        print("Usage: python3 set_admin_role.py <USER_UID>")
        print("Example: python3 set_admin_role.py guIPYaSdv1TMvZ9nSA43t47Ssti2")
        sys.exit(1)
        
    target_user_uid = sys.argv[1]
    
    initialize_firebase_admin()
    set_admin_role(target_user_uid)