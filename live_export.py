import requests
import time
import json
import os

FHIR_SERVER_URL = "http://localhost:8081/fhir"

def trigger_export():
    """Initiates the Bulk FHIR $export operation."""
    headers = {
        "Prefer": "respond-async",
        "Accept": "application/fhir+json"
    }
    url = f"{FHIR_SERVER_URL}/$export?_type=Observation,Patient"
    
    print(f"Triggering Bulk Export: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 202:
        content_location = response.headers.get("Content-Location")
        # Fix port if server returns internal 8080
        if "localhost:8080" in content_location:
            content_location = content_location.replace("localhost:8080", "localhost:8081")
        print(f"Export started. Status URL: {content_location}")
        return content_location
    else:
        print(f"Failed to start export: {response.status_code} - {response.text}")
        return None

def poll_status(status_url):
    """Polls the status URL until the export is complete."""
    print(f"Waiting for export to complete (Polling: {status_url})...")
    while True:
        try:
            response = requests.get(status_url)
            if response.status_code == 200:
                print("Export complete!")
                return response.json().get("output", [])
            elif response.status_code == 202:
                print("...still processing...")
                time.sleep(2)
            else:
                print(f"Error polling status: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Connection error during polling: {e}")
            time.sleep(5)

def download_ndjson(output_files):
    """
    Downloads new NDJSON files and merges them with existing data 
    to ensure accumulation without duplicates (Smart Merge).
    """
    combined_file = "exported_data.ndjson"
    existing_data = {}

    # 1. Load existing data if available
    if os.path.exists(combined_file):
        print(f"📂 Loading existing records from {combined_file}...")
        with open(combined_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        res = json.loads(line)
                        # Key by Type + ID to prevent duplicates
                        key = f"{res['resourceType']}/{res['id']}"
                        existing_data[key] = res
                    except: continue
        print(f"Found {len(existing_data)} existing records.")

    # 2. Download and merge new data
    print(f"📥 Preparing to download {len(output_files)} files from server...")
    new_count = 0
    for file_info in output_files:
        url = file_info.get("url")
        if "localhost:8080" in url:
            url = url.replace("localhost:8080", "localhost:8081")
        
        res = requests.get(url)
        if res.status_code == 200:
            for line in res.text.splitlines():
                if line.strip():
                    resource = json.loads(line)
                    key = f"{resource['resourceType']}/{resource['id']}"
                    if key not in existing_data:
                        new_count += 1
                    existing_data[key] = resource
        else:
            print(f"❌ Failed to download {url}")

    # 3. Write everything back to the file
    with open(combined_file, "w") as outfile:
        for res in existing_data.values():
            outfile.write(json.dumps(res) + '\n')
                
    print(f"✨ Accumulation Complete: {len(existing_data)} total records ({new_count} new added).")
    print(f"💾 Persistent archive updated: {combined_file}")

def main():
    status_url = trigger_export()
    if status_url:
        output = poll_status(status_url)
        if output:
            download_ndjson(output)

if __name__ == "__main__":
    main()
