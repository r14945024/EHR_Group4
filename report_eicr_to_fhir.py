import requests
import json
import base64

FHIR_SERVER_URL = "http://localhost:8081/fhir/fhir"

def report_eicr_to_fhir(eicr_bundle, syndrome, date):
    """
    Uploads an eICR report to the FHIR server as a Binary resource 
    and links it via a DocumentReference for a persistent audit trail.
    Ref: Page 19 of PDF (Document Versioning)
    """
    
    # 1. Create Binary Resource (The raw report content)
    eicr_json_str = json.dumps(eicr_bundle)
    encoded_content = base64.b64encode(eicr_json_str.encode('utf-8')).decode('utf-8')
    
    binary_res = {
        "resourceType": "Binary",
        "contentType": "application/fhir+json",
        "data": encoded_content
    }
    
    bin_response = requests.post(f"{FHIR_SERVER_URL}/Binary", json=binary_res)
    if bin_response.status_code not in [200, 201]:
        print(f"❌ Failed to create Binary audit: {bin_response.text}")
        return
    
    # Safely get ID from body or header
    binary_id = bin_response.json().get('id')
    if not binary_id and 'Location' in bin_response.headers:
        binary_id = bin_response.headers['Location'].split('/')[-3] # Location usually ends in /Binary/ID/_history/V
    
    if not binary_id:
        # Fallback for simple HAPI location header
        binary_id = bin_response.headers.get('Location', '').split('/')[-1]

    binary_url = f"Binary/{binary_id}"
    
    # 2. Create DocumentReference (The metadata/pointer)
    doc_ref = {
        "resourceType": "DocumentReference",
        "status": "current",
        "type": {
            "coding": [{"system": "http://loinc.org", "code": "55751-2", "display": "Public Health Case Report"}]
        },
        "subject": {"display": f"Population Cluster: {syndrome}"},
        "date": datetime.now().isoformat(),
        "description": f"Official eICR notification for {syndrome} detected on {date}.",
        "content": [
            {
                "attachment": {
                    "url": binary_url,
                    "contentType": "application/fhir+json",
                    "title": f"eICR_{syndrome}_{date}.json"
                }
            }
        ]
    }
    
    doc_response = requests.post(f"{FHIR_SERVER_URL}/DocumentReference", json=doc_ref)
    if doc_response.status_code in [200, 201]:
        doc_id = doc_response.json().get('id') or doc_response.headers.get('Location', '').split('/')[-1]
        print(f"📁 Audit Trail Persistent: DocumentReference/{doc_id} created.")
    else:
        print(f"❌ Failed to create DocumentReference: {doc_response.text}")

from datetime import datetime
