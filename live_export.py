import requests
import time
import json
import os

FHIR_SERVER_URL = "http://localhost:8081/fhir/fhir"

def trigger_export():
    """Initiates the Bulk FHIR $export operation."""
    headers = {
        "Prefer": "respond-async",
        "Accept": "application/fhir+json"
    }
    url = f"{FHIR_SERVER_URL}/\$export?_type=Observation,Patient,Condition"
    
    print(f"📡 Attempting Bulk Export: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 202:
            content_location = response.headers.get("Content-Location")
            if "localhost:8080" in content_location:
                content_location = content_location.replace("localhost:8080", "localhost:8081")
            print(f"✅ Export started. Status URL: {content_location}")
            return content_location
        else:
            print(f"⚠️ Bulk Export failed (HTTP {response.status_code}). Switching to Crawl Fallback...")
            return "FALLBACK"
    except Exception as e:
        print(f"⚠️ Connection error: {e}. Switching to Crawl Fallback...")
        return "FALLBACK"

def crawl_resources():
    """
    Fallback method: Crawls the server using standard FHIR search and paging.
    Much slower than $export, but 100% reliable for small/medium databases.
    """
    print("🕵️ Starting Crawl Fallback (Downloading resources page by page)...")
    resources = []
    types = ["Patient", "Observation", "Condition"]
    
    for rtype in types:
        url = f"{FHIR_SERVER_URL}/{rtype}?_count=100"
        while url:
            # Fix port if needed
            if "localhost:8080" in url: url = url.replace("localhost:8080", "localhost:8081")
            
            try:
                res = requests.get(url, timeout=30)
                if res.status_code != 200: break
                
                bundle = res.json()
                entries = bundle.get("entry", [])
                for entry in entries:
                    if "resource" in entry:
                        resources.append(entry["resource"])
                
                # Get next page link
                url = None
                for link in bundle.get("link", []):
                    if link.get("relation") == "next":
                        url = link.get("url")
                
                if url: print(f"  ..{rtype}: {len(resources)} resources collected..")
            except: break
            
    return resources

def poll_status(status_url):
    """Polls the status URL until the export is complete."""
    print(f"⏳ Waiting for export to complete (Polling: {status_url})...")
    start_time = time.time()
    while True:
        try:
            response = requests.get(status_url)
            if response.status_code == 200:
                print("✨ Export complete!")
                return response.json().get("output", [])
            elif response.status_code == 202:
                elapsed = int(time.time() - start_time)
                print(f"  ..still processing ({elapsed}s)..")
                time.sleep(5)
            else:
                print(f"❌ Error polling status: {response.status_code}. Switching to Crawl...")
                return "FALLBACK"
        except Exception as e:
            print(f"❌ Connection error: {e}. Switching to Crawl...")
            return "FALLBACK"

def smart_merge(new_resources):
    """Merges new resources into the local NDJSON file without duplicates."""
    combined_file = "exported_data.ndjson"
    existing_data = {}

    if os.path.exists(combined_file):
        print(f"📂 Loading existing records from {combined_file}...")
        with open(combined_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        res = json.loads(line)
                        key = f"{res['resourceType']}/{res['id']}"
                        existing_data[key] = res
                    except: continue
        print(f"Found {len(existing_data)} existing records.")

    new_count = 0
    for resource in new_resources:
        key = f"{resource['resourceType']}/{resource['id']}"
        if key not in existing_data:
            new_count += 1
        existing_data[key] = resource

    with open(combined_file, "w") as outfile:
        for res in existing_data.values():
            outfile.write(json.dumps(res) + '\n')
                
    print(f"🚀 Accumulation Complete: {len(existing_data)} total records ({new_count} new added).")
    print(f"💾 Persistent archive updated: {combined_file}")

def main():
    status_url = trigger_export()
    
    if status_url == "FALLBACK":
        resources = crawl_resources()
        smart_merge(resources)
    elif status_url:
        output_files = poll_status(status_url)
        if output_files == "FALLBACK":
            resources = crawl_resources()
            smart_merge(resources)
        elif output_files:
            # Download from NDJSON URLs
            all_resources = []
            for file_info in output_files:
                url = file_info.get("url")
                if "localhost:8080" in url: url = url.replace("localhost:8080", "localhost:8081")
                res = requests.get(url)
                if res.status_code == 200:
                    for line in res.text.splitlines():
                        if line.strip():
                            all_resources.append(json.loads(line))
            smart_merge(all_resources)

if __name__ == "__main__":
    main()
