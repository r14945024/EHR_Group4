import requests
import json
import random
import time
from datetime import datetime, timedelta

INGESTION_SERVER_URL = "http://localhost:5001/ingest"

# Test Data Pools for Realism
NAMES = ["Alice Johnson", "Bob Smith", "Charlie Brown", "David Lee", "Eva Garcia", 
         "Frank Wang", "Grace Chen", "Henry Kim", "Ivy Taylor", "Jack Miller"]
ZIPS = ["100", "104", "106", "110", "114"]

def submit_triage(name, gender, dob, zip_code, fever, cough, rash, travel, date=None):
    """
    Submits a triage response to the Ingestion Server.
    Note: In a real FHIR system, 'date' would be handled by the server, 
    but we include it here to simulate historical data for the baseline.
    """
    qr = {
        "resourceType": "QuestionnaireResponse",
        "status": "completed",
        "authored": date if date else datetime.now().isoformat(),
        "item": [
            {"linkId": "patient-name", "answer": [{"valueString": name}]},
            {"linkId": "patient-gender", "answer": [{"valueString": gender}]},
            {"linkId": "patient-birthdate", "answer": [{"valueDate": dob}]},
            {"linkId": "patient-zip", "answer": [{"valueString": zip_code}]},
            {"linkId": "symptom-fever", "answer": [{"valueBoolean": fever}]},
            {"linkId": "symptom-cough", "answer": [{"valueBoolean": cough}]},
            {"linkId": "symptom-rash", "answer": [{"valueBoolean": rash}]},
            {"linkId": "travel-history", "answer": [{"valueBoolean": travel}]}
        ]
    }
    
    try:
        response = requests.post(INGESTION_SERVER_URL, json=qr)
        return response.status_code == 201
    except:
        return False

def generate_random_patient(date=None, scenario="Normal"):
    timestamp = datetime.now().strftime("%H:%M")
    name = random.choice(NAMES) + f"-{timestamp}-{random.getrandbits(8)}"
    gender = random.choice(["male", "female", "other"])
    dob = (datetime.now() - timedelta(days=random.randint(365*5, 365*80))).strftime("%Y-%m-%d")
    zip_code = random.choice(ZIPS)
    
    if scenario == "COVID":
        return submit_triage(name, gender, dob, "110", True, True, False, True, date)
    elif scenario == "Dengue":
        return submit_triage(name, gender, dob, zip_code, True, False, True, True, date)
    else: # Normal/Flu-ish
        fever = random.random() > 0.8
        cough = random.random() > 0.7
        return submit_triage(name, gender, dob, zip_code, fever, cough, False, False, date)

def main():
    print("🚀 Starting Unified End-to-End Stress Test (1-Year Dataset)...")
    print("This script sends ALL data through the Ingestion Server (Group 2).")
    
    # 1. Generate Historical Baseline (Last 365 days)
    print("Generating 365-day historical baseline...")
    for i in range(365, 3, -1):
        date = (datetime.now() - timedelta(days=i)).isoformat()
        daily_cases = random.randint(2, 5)
        success_count = 0
        for _ in range(daily_cases):
            if generate_random_patient(date, "Normal"):
                success_count += 1
        if i % 10 == 0:
            print(f"  Progress: {i} days remaining... (Ingested {success_count} for Day -{i})")

    # 2. Generate Outbreak Spike (Last 3 days)
    print("\n🚨 Simulating COVID Outbreak Spike (Concentrated in Zip 110)...")
    for i in range(3, 0, -1):
        date = (datetime.now() - timedelta(days=i)).isoformat()
        spike_cases = random.randint(15, 25)
        success_count = 0
        for _ in range(spike_cases):
            if generate_random_patient(date, "COVID"):
                success_count += 1
        print(f"  Day -{i}: Ingested {success_count} outbreak records")

    print("\n✨ Unified Stress Test Complete. 150+ patients sent through the Ingestion Layer.")
    print("Next steps: Run live_export.py and run_analysis.py")

if __name__ == '__main__':
    main()
