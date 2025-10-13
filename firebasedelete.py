import os
import sys
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

def delete_collection(coll_ref, batch_size):
    """
    Deletes a collection in batches.
    """
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f"Deleting doc: {doc.id}")
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

def main():
    """
    Initializes Firebase and deletes all documents in the 'prompts' collection.
    """
    # --- Configuration ---
    load_dotenv()
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not GOOGLE_APPLICATION_CREDENTIALS:
        print("❌ ERROR: GOOGLE_APPLICATION_CREDENTIALS not found in .env file.")
        sys.exit(1)

    # --- Firebase & Auth ---
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase Admin SDK initialized for cleanup script.")
    except Exception as e:
        print(f"❌ Could not initialize Firebase Admin SDK: {e}")
        sys.exit(1)

    # --- Deletion ---
    prompts_collection_ref = db.collection('prompts')
    print("\n" + "="*20)
    print("DELETING ALL PROMPTS...")
    print("="*20 + "\n")
    
    delete_collection(prompts_collection_ref, 100) # Deletes 100 at a time

    print("\n" + "="*20)
    print("✅ Cleanup complete.")
    print("="*20 + "\n")


if __name__ == "__main__":
    main()