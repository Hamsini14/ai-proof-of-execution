import os
import sys
import datetime
import json
import hashlib

# Mock crypto_utils.generate_hash
def generate_hash(data):
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

def test_hashing():
    # Original creation
    timestamp = datetime.datetime.utcnow()
    decision_id = "TEST_ID"
    input_hash = "INPUT_HASH"
    model_version = "MODEL_V1"
    decision = "Loan Approved"
    confidence = 0.85
    
    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
    original_dict = {
        "decision_id": decision_id,
        "input_hash": input_hash,
        "model_version": model_version,
        "decision": decision,
        "confidence": float(confidence),
        "timestamp": ts_str,
    }
    original_hash = generate_hash(original_dict)
    
    print(f"Original TS Str: {ts_str}")
    print(f"Original Hash:   {original_hash}")
    
    # Simulate DB roundtrip (simplified)
    # Most common issue: string formatting differences
    # SQLAlchemy's DateTime on SQLite often returns a datetime object parsed from a string
    
    # Let's see what happens if we parse it back from its own strftime
    reparsed_ts = datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
    reparsed_ts_str = reparsed_ts.strftime("%Y-%m-%dT%H:%M:%S.%f")
    
    recomputed_dict = {
        "decision_id": str(decision_id),
        "input_hash": str(input_hash),
        "model_version": str(model_version),
        "decision": str(decision),
        "confidence": float(confidence),
        "timestamp": reparsed_ts_str,
    }
    recomputed_hash = generate_hash(recomputed_dict)
    
    print(f"Reparsed TS Str: {reparsed_ts_str}")
    print(f"Recomputed Hash: {recomputed_hash}")
    
    if original_hash == recomputed_hash:
        print("SUCCESS: Hashing is consistent via strftime!")
    else:
        print("FAILURE: Hashing mismatch detected!")

if __name__ == "__main__":
    test_hashing()
