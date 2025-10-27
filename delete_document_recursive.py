# Updated firebasedelete_robust.py
import os
import sys
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

def delete_document_recursive(doc_ref, batch_size):
    """
    Recursively deletes a document and all its subcollections.
    """
    print(f"Processing doc: {doc_ref.id}...")
    # Get all subcollections first
    collections = list(doc_ref.collections()) # Convert iterator to list
    if collections:
        print(f"  Found {len(collections)} subcollection(s) for doc: {doc_ref.id}")
        for coll_ref in collections:
            print(f"    Deleting subcollection: {coll_ref.id}")
            delete_collection_recursive(coll_ref, batch_size)
            print(f"    Finished deleting subcollection: {coll_ref.id}")
    else:
        print(f"  No subcollections found for doc: {doc_ref.id}")

    # Now, attempt to delete the document itself
    try:
        print(f"  Attempting to delete doc: {doc_ref.id}")
        doc_ref.delete()
        print(f"  Successfully deleted doc: {doc_ref.id}")
    except Exception as e:
        print(f"  ❌ ERROR deleting doc {doc_ref.id}: {e}") # Add error logging

def delete_collection_recursive(coll_ref, batch_size):
    """
    Deletes all documents in a collection recursively, including subcollections.
    """
    docs_stream = coll_ref.limit(batch_size).stream()
    docs_list = list(docs_stream) # Convert iterator to list to check count
    deleted_count = 0
    total_in_batch = len(docs_list)

    if total_in_batch > 0:
        print(f"    Found {total_in_batch} docs in current batch for collection: {coll_ref.id}")
        for doc in docs_list:
            print(f"      Processing sub-doc: {doc.id} in collection {coll_ref.id}")
            try:
                delete_document_recursive(doc.reference, batch_size) # Call recursive doc delete
                deleted_count += 1
            except Exception as e:
                print(f"      ❌ ERROR processing sub-doc {doc.id} in {coll_ref.id}: {e}") # Add error logging
    else:
         print(f"    No documents found in current batch for collection: {coll_ref.id}")


    # Recurse if the batch was full, indicating more might exist
    if total_in_batch >= batch_size:
        print(f"    Batch size reached for {coll_ref.id}, recursing...")
        return delete_collection_recursive(coll_ref, batch_size)
    else:
        print(f"    Finished processing batch for collection: {coll_ref.id} (deleted {deleted_count})")


def main():
    """
    Initializes Firebase and recursively deletes all documents and subcollections
    in the 'prompts' collection.
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
        print("✅ Firebase Admin SDK initialized for recursive cleanup script.")
    except Exception as e:
        print(f"❌ Could not initialize Firebase Admin SDK: {e}")
        sys.exit(1)

    # --- Deletion ---
    prompts_collection_ref = db.collection('prompts')
    print("\n" + "="*20)
    print("ROBUST RECURSIVE DELETION of 'prompts' collection...")
    print("="*20 + "\n")

    delete_collection_recursive(prompts_collection_ref, 100) # Start the robust recursive delete

    print("\n" + "="*20)
    print("✅ Robust recursive cleanup attempt complete.")
    print("="*20 + "\n")


if __name__ == "__main__":
    main()