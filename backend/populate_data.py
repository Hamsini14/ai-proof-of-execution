import requests
import random
import time
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000/api"

def populate():
    # Credit score ranges to sample from
    score_ranges = [
        (400, 549), # Poor
        (550, 650), # Fair
        (651, 750), # Good
        (751, 850)  # Excellent
    ]
    
    employment_statuses = ["employed", "self_employed", "unemployed"]
    
    print("Checking if backend server is up...")
    try:
        requests.get(f"{API_BASE}/system/status", timeout=5)
    except Exception:
        print("Error: Backend server is not reachable at", API_BASE)
        print("Please start the backend first.")
        return

    print("Populating database with test data...")
    
    for i in range(20):
        # Pick a random range but bias towards higher scores for some approvals
        r = random.choice(score_ranges)
        score = int(random.randint(r[0], r[1]))
        
        payload = {
            "credit_score": score,
            "income": float(random.randint(30000, 120000)),
            "loan_amount": float(random.randint(5000, 50000)),
            "existing_debt": float(random.randint(0, 20000)),
            "employment_status": str(random.choice(employment_statuses)),
            "loan_term": int(random.choice([12, 24, 36, 48, 60]))
        }
        
        try:
            res = requests.post(f"{API_BASE}/decision", json=payload, timeout=10)
            if res.ok:
                data = res.json()
                print(f"[{i+1}/20] Decision: {data['decision_id']} - {data['decision']} (Score: {score})")
            else:
                print(f"[{i+1}/20] API Error ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"[{i+1}/20] Request Error: {e}")
        
        time.sleep(0.05)

    print("\nPopulation complete!")

if __name__ == "__main__":
    populate()
