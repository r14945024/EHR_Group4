import os
import json
import requests
import time
from collections import defaultdict

FHIR_SERVER = "http://localhost:8081/fhir"

# -----------------------------
# 1. Transform & Split Logic (The "Safety Valve" for 50MB+ files)
# -----------------------------
def transform_and_split(bundle, name):
    """
    Ensures IDs are consistent and splits massive bundles into chunks.
    This prevents the 'Java heap space' OutOfMemory error.
    """
    entries = bundle.get("entry", [])
    placeholder_map = {}
    
    # Map urn:uuid placeholders to permanent IDs
    for entry in entries:
        full_url = entry.get("fullUrl", "")
        resource = entry.get("resource", {})
        res_type = resource.get("resourceType")
        res_id = resource.get("id")
        if full_url.startswith("urn:uuid:") and res_type and res_id:
            placeholder_map[full_url] = f"{res_type}/{res_id}"

    # Rewrite bundle JSON to resolve references
    bundle_str = json.dumps(bundle)
    for placeholder, reference in placeholder_map.items():
        bundle_str = bundle_str.replace(f'"{placeholder}"', f'"{reference}"')
    
    processed_bundle = json.loads(bundle_str)
    entries = processed_bundle.get("entry", [])

    # Update to PUT (Upsert) for chunking reliability
    for entry in entries:
        resource = entry.get("resource", {})
        res_type = resource.get("resourceType")
        res_id = resource.get("id")
        if res_type and res_id:
            entry["request"] = {"method": "PUT", "url": f"{res_type}/{res_id}"}
            entry["fullUrl"] = f"{FHIR_SERVER}/{res_type}/{res_id}"

    # Split into chunks of 150 (small enough for the 2GB heap)
    chunk_size = 150
    chunks = [entries[i:i + chunk_size] for i in range(0, len(entries), chunk_size)]
    
    print(f" 📦 Massive file! Splitting into {len(chunks)} parts...")
    for i, chunk in enumerate(chunks):
        ok, msg = post(FHIR_SERVER, {"resourceType": "Bundle", "type": "transaction", "entry": chunk}, f"{name} [Part {i+1}]")
        if not ok: return False, msg
        time.sleep(0.5)
        
    return True, "All parts OK"

# -----------------------------
# 2. post to FHIR
# -----------------------------
def post(url, payload, name):
    headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=300)
            if r.status_code in (200, 201): return True, "OK"
            if r.status_code == 503:
                time.sleep(10)
                continue
            try:
                err_data = r.json()
                msg = err_data.get('issue', [{}])[0].get('diagnostics', r.text)[:200]
                return False, f"HTTP {r.status_code} - {msg}"
            except:
                return False, f"HTTP {r.status_code} - {r.text[:200]}"
        except Exception as e:
            if attempt == 2: return False, str(e)
            time.sleep(5)
    return False, "Max retries exceeded"

# -----------------------------
# 3. upload resource
# -----------------------------
def upload_resource(path, data):
    if data.get("resourceType") == "Bundle":
        # Only split if the bundle is truly massive (> 500 entries)
        if len(data.get("entry", [])) > 500:
            return transform_and_split(data, path)
        return post(FHIR_SERVER, data, path)
    else:
        return post(f"{FHIR_SERVER}/{data.get('resourceType')}", data, path)

def run(folder):
    if not os.path.exists(folder): return
    files = [(f, os.path.join(folder, f)) for f in os.listdir(folder) if f.endswith(".json")]
    
    # Priority Sort
    def sort_key(item):
        fn = item[0].lower()
        if 'hospital' in fn or 'organization' in fn: return 0
        if 'practitioner' in fn: return 1
        return 2
    files.sort(key=sort_key)

    print(f"🚀 Starting Upload of {len(files)} files...")
    success, fail = 0, 0

    for i, (f, path) in enumerate(files):
        print(f"[{i+1}/{len(files)}] {f}...", end="", flush=True)
        try:
            with open(path, "r",encoding='utf-8') as fp: data = json.load(fp)
            ok, msg = upload_resource(path, data)
            if ok:
                print(" ✅ [OK]")
                success += 1
            else:
                print(f" ❌ [FAIL] -> {msg}")
                fail += 1
        except Exception as e:
            print(f" ❌ [ERROR] -> {e}")
            fail += 1
        time.sleep(0.1)

    print(f"\n===== SUMMARY =====\nSuccess: {success}\nFailed : {fail}")

if __name__ == "__main__":
    run("fhir")
