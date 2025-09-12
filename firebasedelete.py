import os
from google.cloud import firestore

# This script uses the same service account key your API uses.
# Ensure your .env file is present or that you are authenticated
# with gcloud in your terminal.
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"

# Initialize the Firestore client (using the synchronous client is easier for scripts)
db = firestore.Client()

# --- IDs to Delete ---
PROMPT_IDS_TO_DELETE = [
    "4V9zHNHxarJJ1Iwd6IvT", "Ahxcn3ESPoxiG5TyNwJN", "BhWcqtFehDPS9vG1d3UA",
    "DeppMrHK0JRJwmrPTtmI", "MjAJmldmdaw4xRPzF1Bj", "NkidffqSeeam6KPywPhV",
    "V7Q4niG0ylmoRdAL8A8S", "VFvk9b353AOMhoZtMX3j", "ZXNuUnb1MEgNXRwI9GbJ",
    "aa9XJk0w60E4JTkQZrqY", "eQJAsWRqk0XK8ePTQ9mx", "l3SWN28QAmu6bPz5COLc",
    "pMW6l15057Xu2XJOJ0P8", "vAyaOKE8OpH3p9BvCW0m", "xhk3q12G9XwfZOWkNrLa",
]

TEMPLATE_IDS_TO_DELETE = [
    "NMVP1tguGrLnXxbio2wW", "PdVGLyp0axXOIgCd2V2l", "QOm0rWjVuBbajd2Y9NAx",
    "V4fwdO9OrifCHzbTsUJY", "VNe39xOQD60sAk4ThF8q", "XatR4TpBhvG90NjOTKCr",
    "hfwDhSdlIix3CsLFoeKO", "krrRmkraIInBi8fjVoaX", "okPxFlv5WnX1q2t37E7i",
    "qPh6hUav4Po2KjhINgni", "yNzubOzcCat4DPsXY0x9", "z7kDc6CkKxHYhFxnoLMs",
    "OOvzFrZaKaLKONHxy69N", "mnkWnlVUCk9Pl9FCOpqG", "twIhZ5QIcWn405lWVynR",
]

def delete_collection(coll_ref, batch_size):
    """Deletes all documents in a collection in batches."""
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0
    for doc in docs:
        print(f"  - Deleting sub-document: {doc.id}")
        doc.reference.delete()
        deleted += 1
    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

def main():
    print("Starting database cleanup...\n")
    
    # --- Delete Prompts and their Versions ---
    print("--- Deleting Prompts ---")
    for prompt_id in PROMPT_IDS_TO_DELETE:
        try:
            prompt_ref = db.collection("prompts").document(prompt_id)
            # First, delete the 'versions' subcollection
            versions_ref = prompt_ref.collection("versions")
            delete_collection(versions_ref, 20)
            # Then, delete the parent prompt document
            prompt_ref.delete()
            print(f"-> DELETED Prompt: {prompt_id}\n")
        except Exception as e:
            print(f"Could not delete prompt {prompt_id}: {e}\n")

    # --- Delete Prompt Templates ---
    print("\n--- Deleting Prompt Templates ---")
    for template_id in TEMPLATE_IDS_TO_DELETE:
        try:
            db.collection("prompt_templates").document(template_id).delete()
            print(f"-> DELETED Template: {template_id}")
        except Exception as e:
            print(f"Could not delete template {template_id}: {e}")
    
    print("\nCleanup complete!")

if __name__ == "__main__":
    main()