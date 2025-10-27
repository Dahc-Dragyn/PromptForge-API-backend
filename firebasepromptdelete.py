# Updated firebasedelete_deep_recursive.py
import os
import sys
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import time

# --- List of IDs ---
TARGET_IDS = [
    # "0oHOhWIBqX9UWS42PVkc", # Assuming this one is already gone from manual delete
    "phTyuQmc8QvCiSwR6QJe", "pwtwpdOVUbKNmmj72dy9",
    "q3KH4kyNwTjXwoGHmfnF", "qAGnCxou58IT3ReYkhnT", "qAhVLDzcTgO59vbO58eh",
    "qCt51IFAZiekzK96pT97", "qKdng2QN34aF6WH7bWaF", "qMNZ8XEfkTExBivy55NU",
    "qQ2cN72MoPO6wRP3GCuC", "qS6VGf8ibyCEdNfSj0Dm", "qaDYQtBXvo3YJUWZJUoD",
    "qtKUpDwcNLNw496QV56B", "qwZa3DYPYa8QbMVvtDbX", "qzrCZdAztIobcQZPjmIc",
    "r6NxjDnTjES1y36zDI5K", "rkRfk4SCAhiMUOFEU3Ql", "rrX7nhacpJELVRkKdSjr",
    "rwnCEzJKTpcdCT1lP2tO", "s0nBIch8xIigl8OGvz7n", "s48G7wLLqr5xGlP3ESem",
    "sETcW6jRIxA36o2vxPsV", "sK4zFxFIgwZKMjxR42jl", "sPWD1wm4YRfmgWkvjkN3",
    "sX32FE9RlBdJZE0v5IQE", "sY1j1nHzVuk50DGwp5jI", "skJ6ByuxqMj2j2hdlqAM",
    "spRIjg9oR2GwsQ4M1d3a", "stownFCLGtYmqxZpV9pR", "t1mD507IyJoLZ3MpmFcx",
    "t4CKSDgFpZUwOdycdahT", "tXM1PIyJeGNschskLyU8", "tgE3dzv4H6rqfQaulF34",
    "tholhERt07hzSQtEDjXq", "tqnfAN3W1Oj6Y3kDRFTu", "txIGQEiLx4ofmNysvWnE",
    "u3SDt4F3G2RrTbwFEpU9", "u4Eb6YJF47sZ1be9I9K8", "uIX6Twb3xuesk1zSkMXV",
    "uNpeUMpXxScZd6me1diA", "ueMfdi4GQb2GiRFcje2L", "ug2SXI6fi6yahSvctwVx",
    "ujz6p1UYbLGnujaHebpC", "usofkwkqFGzgsAolu5DR", "uuosm3G8manooWtvFazV",
    "uvH77XTFxASVQ5Ddo5k8", "v3WNAA2pTrNWMJ91j4Zi", "v5AKzBtP9bBo5GVSwrST",
    "vHfVijcmqiYZOXYvy1mx", "vM48R2L8hJm7672PuXZ0", "vdTDJy6tJ8fwPnbeSP7R",
    "vdq7YNISXrjqIvMzEcpN", "vptdhH0gOSaTfVZ9BohU", "w1cIeqqgUbN4cTjBcd1S",
    "w2n1wNtkQjGRXzgGrO6u", "w2vh66OcXRsCEz5h48oB", "w8jHWwATPRZP55QQx361",
    "wDGht9F8XNlL9xvsuh5L", "wJ06KWtyY2NpQNdtuYfU", "wU1q0600zWthYuZdHo8g",
    "wV0NnlID4Z402zY16hnc", "woamkE6vutyBf5K1CruN", "wyZCjyPSsEHkC5zpbMBw",
    "xQ516gSNrwQwqOaix8WQ", "xW2xZZtyRvjxphY6o0lI", "xdNTscuqS4ZkSDAfsCx1",
    "xqtYvIKTSShPcpNjygHo", "y0HSD6O4G3ZuCSmUP8Ws", "yGeEFSXAttMKLcZKBMgw",
    "yi1fAyjKdSCAbh0z9Et0", "ysn3NoBTw8blCPhkfDU7", "z0UMyQyOiIAWZjlcmiJ0",
    "z1w0ZtLR3QUDDCT6umw1", "z3JUTOaafJRgWAasSWQU", "z8EMhfPR16uqaza04Tyy",
    "zACy6tRHUz2QodaVc22O", "zIuczQDRf1bUlTQqj4ul", "zaXKOHDnqAcqF7cP1Wa2",
    "znuWtvE18OBrPU5fUCCK"
]
# --- END LIST ---

def delete_document_recursive(doc_ref, batch_size):
    """ Deletes a document and ALL nested subcollections recursively. Returns True on success. """
    print(f"Processing doc for deep delete: {doc_ref.id}...")
    subcollections_cleared = True
    collections = list(doc_ref.collections())
    if collections:
        print(f"  Found {len(collections)} subcollection(s) for doc: {doc_ref.id}")
        for coll_ref in collections:
            print(f"    Recursively deleting subcollection: {coll_ref.id}")
            if not delete_collection_recursive(coll_ref, batch_size): # Recursive call
                subcollections_cleared = False
            print(f"    Finished recursive delete for subcollection: {coll_ref.id}")
    else:
        print(f"  No subcollections found for doc: {doc_ref.id}")

    if subcollections_cleared:
        try:
            print(f"  Attempting final delete of doc: {doc_ref.id}")
            doc_ref.delete()
            print(f"  Successfully called delete for doc: {doc_ref.id}")
            # Verification after delete call
            time.sleep(0.5) # Short delay
            check_doc = doc_ref.get()
            if check_doc.exists:
                print(f"  ❌ VERIFICATION FAILED: Doc {doc_ref.id} still exists!")
                return False
            else:
                print(f"  ✅ VERIFICATION SUCCEEDED: Doc {doc_ref.id} confirmed gone.")
                return True
        except Exception as e:
            print(f"  ❌ ERROR during final delete of doc {doc_ref.id}: {e}")
            return False
    else:
        print(f"  Skipping final delete of doc {doc_ref.id} due to subcollection errors.")
        return False

def delete_collection_recursive(coll_ref, batch_size):
    """ Recursively deletes all documents and their subcollections within a collection. Returns True on success."""
    print(f"    Starting recursive delete for collection: {coll_ref.id}")
    overall_success = True
    while True:
        docs_stream = coll_ref.limit(batch_size).stream()
        docs_list = list(docs_stream)
        if not docs_list:
            print(f"    No more documents found in collection: {coll_ref.id}.")
            break

        print(f"    Found {len(docs_list)} docs in batch for collection: {coll_ref.id}")
        batch_successful = True
        for doc in docs_list:
             print(f"      Processing sub-doc: {doc.id} in collection {coll_ref.id}")
             # Call the fully recursive document delete for each doc found
             if not delete_document_recursive(doc.reference, batch_size):
                  batch_successful = False # If any doc fails, mark batch as failed

        if not batch_successful:
             print(f"    ❌ ERROR: Batch for collection {coll_ref.id} encountered failures.")
             overall_success = False # Mark overall failure for the collection
             break # Stop processing this collection if a batch fails

        # If we processed fewer docs than the batch size, it was the last batch
        if len(docs_list) < batch_size:
             print(f"    Last batch processed for collection: {coll_ref.id}.")
             break

    if overall_success:
        print(f"    ✅ Successfully finished recursive delete for collection: {coll_ref.id}")
    return overall_success


def main():
    """ Initializes Firebase and uses targeted deep recursive deletion. """
    # --- Configuration & Firebase Init ---
    load_dotenv()
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not GOOGLE_APPLICATION_CREDENTIALS: sys.exit("❌ ERROR: GOOGLE_APPLICATION_CREDENTIALS not found.")
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase Admin SDK initialized for targeted deep recursive cleanup.")
    except Exception as e: sys.exit(f"❌ Could not initialize Firebase Admin SDK: {e}")

    prompts_collection_ref = db.collection('prompts')
    batch_size = 100
    overall_success = True

    # --- Targeted Deep Recursive Deletion ---
    print("\n" + "="*20)
    print(f"TARGETED DEEP RECURSIVE DELETION of {len(TARGET_IDS)} specific documents...")
    print("="*20 + "\n")

    if not TARGET_IDS:
        print("🟡 WARNING: TARGET_IDS list is empty.")
    else:
        for doc_id in TARGET_IDS:
            print(f"--- Targeting Document ID: {doc_id} ---")
            doc_ref = prompts_collection_ref.document(doc_id)
            try:
                # Call the most thorough recursive delete directly on the target doc
                success = delete_document_recursive(doc_ref, batch_size)
                print(f"--- Finished processing Document ID: {doc_id} (Success: {success}) ---\n")
                if not success:
                    overall_success = False
            except Exception as e:
                print(f"❌ MAJOR ERROR processing {doc_id}: {e}\n")
                overall_success = False

    print("\n" + "="*20)
    if overall_success:
        print("✅ Targeted deep recursive cleanup attempt complete. Check Firestore console.")
    else:
        print("❌ Targeted deep recursive cleanup attempt encountered errors or verification failures. Check logs and Firestore console.")
    print("="*20 + "\n")

if __name__ == "__main__":
    main()