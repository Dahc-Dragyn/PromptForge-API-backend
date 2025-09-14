import os
from google.cloud import firestore
from datetime import datetime, timezone

# --- Authentication ---
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"

db = firestore.Client()

# --- Pricing Data ---
# Source: Official pricing pages for Google Gemini and OpenAI GPT as of Sept 2025.
PRICING_DATA = [
    {
        "id": "gemini-2.5-flash-lite", # <-- CORRECTED
        "provider": "Google",
        "price_per_million_input_tokens_usd": 0.35,
        "price_per_million_output_tokens_usd": 0.70,
    },
    {
        "id": "gpt-4o-mini",
        "provider": "OpenAI",
        "price_per_million_input_tokens_usd": 0.15,
        "price_per_million_output_tokens_usd": 0.60,
    }
]

def seed_database():
    """
    Creates or overwrites the pricing documents in the llm_pricing collection
    with the corrected model IDs.
    """
    print("🚀 Starting to seed the pricing database with corrected model IDs...")
    
    collection_ref = db.collection("llm_pricing")
    
    for model_data in PRICING_DATA:
        doc_id = model_data.pop("id")
        
        data_to_write = {
            **model_data,
            "last_updated": datetime.now(timezone.utc)
        }
        
        try:
            print(f" -> Seeding price for '{doc_id}'...")
            collection_ref.document(doc_id).set(data_to_write)
            print(f"   ... Success!")
        except Exception as e:
            print(f"   !!! FAILED to seed '{doc_id}': {e} !!!")
            
    print("\n✅ Database seeding complete.")

if __name__ == "__main__":
    seed_database()