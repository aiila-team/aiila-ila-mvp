import logging
import uuid
import sys
from pathlib import Path

# Ensure the backend directory is on sys.path when running this file directly.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import the top-level convenience functions from your actual files
from app.services.entity_extraction import extract_entities
from app.services.deduplication import check_duplicate

# Set up basic logging so we can see the loguru/logger outputs
logging.basicConfig(level=logging.INFO)

def run_integration_test():
    print("🚀 --- INITIATING PIPELINE INTEGRATION TEST --- 🚀\n")

    # 1. Simulate messy, unstructured text from a Telegram scrape
    mock_telegram_event = """
    URGENT: Drop the package at the location tonight. 
    If there are issues, contact Rahul Sharma immediately. 
    Do not use the old number. Call me at +91 98765 43210 or +91-9999988888. 
    Send the advance payment to shadow_ops@ybl or backup email burner123@protonmail.com.
    Ping @darkweb_seller on Telegram when done.
    """
    
    event_1_id = str(uuid.uuid4())

    # ==========================================================
    # TEST 1: ENTITY EXTRACTION
    # ==========================================================
    print("1️⃣ TESTING: Entity Extraction Service...")
    
    # Using your convenience function!
    extracted_items = extract_entities(text=mock_telegram_event, source_platform="Telegram")
    
    if not extracted_items:
        print("❌ FAILED: No entities extracted.")
    else:
        print(f"✅ SUCCESS: Extracted {len(extracted_items)} entities:")
        for item in extracted_items:
            # Based on your dataclass/pydantic model structure
            print(f"   -> [{item.entity_type}]: {item.value} (Confidence: {item.confidence})")

    print("\n" + "="*50 + "\n")

    # ==========================================================
    # TEST 2: DEDUPLICATION (LSH/MinHash)
    # ==========================================================
    print("2️⃣ TESTING: Deduplication Service...")
    
    # First pass: Should NOT be a duplicate, but should store the signature
    print(f"Processing Original Event ID: {event_1_id}")
    result_1 = check_duplicate(event_id=event_1_id, content=mock_telegram_event)
    
    if result_1.is_duplicate:
         print("❌ FAILED: Original event was flagged as a duplicate!")
    else:
         print("✅ SUCCESS: Original event processed and stored in LSH Index.")

    # Second pass: Simulate a spammer slightly altering the message
    spam_message = """
    URGENT: Drop the package at the location tonight. 
    If there are problems, contact Rahul Sharma immediately. 
    Do not use the old number. Call me at +91 98765 43210 or +91-9999988888. 
    Send the advance payment to shadow_ops@ybl or backup email burner123@protonmail.com.
    Message @darkweb_seller on Telegram when finished.
    """
    
    event_2_id = str(uuid.uuid4())
    print(f"\nProcessing Spam Event ID: {event_2_id}")
    
    result_2 = check_duplicate(event_id=event_2_id, content=spam_message)
    
    if result_2.is_duplicate:
        print(f"✅ SUCCESS: Spam successfully caught!")
        print(f"   -> Flagged as duplicate of: {result_2.duplicate_of}")
    else:
        print("❌ FAILED: Spam was not flagged as a duplicate.")

if __name__ == "__main__":
    run_integration_test()