import json
import uuid
from datetime import datetime

def generate_eicr(syndrome, case_count, date, facility="Facility-B"):
    """
    Generates a mock eICR (Electronic Initial Case Report) Bundle.
    This simulates the automated notification sent to the CDC (Group 5).
    """
    eicr_id = str(uuid.uuid4())
    
    eicr = {
        "resourceType": "Bundle",
        "id": eicr_id,
        "type": "document",
        "timestamp": datetime.now().isoformat(),
        "identifier": {
            "system": "http://healthit.gov/eicr",
            "value": f"EICR-{eicr_id}"
        },
        "entry": [
            {
                "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
                "resource": {
                    "resourceType": "Composition",
                    "status": "final",
                    "type": {
                        "coding": [{"system": "http://loinc.org", "code": "55751-2", "display": "Public Health Case Report"}]
                    },
                    "subject": {"display": "Population Cluster"},
                    "date": date,
                    "author": [{"display": "Group 4 Analysis Engine"}],
                    "title": f"Automated Alert: {syndrome} Outbreak Detected",
                    "section": [
                        {
                            "title": "Outbreak Details",
                            "text": {
                                "status": "generated",
                                "div": f"<div xmlns='http://www.w3.org/1999/xhtml'>Detected {case_count} cases of {syndrome} at {facility} on {date}. Threshold breached.</div>"
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    file_name = f"outputs/eICR_Alert_{syndrome}_{date}.json"
    with open(file_name, "w") as f:
        json.dump(eicr, f, indent=2)
    
    print(f"✅ eICR Public Health Alert generated: {file_name}")
    return eicr

if __name__ == "__main__":
    # Example trigger from analysis
    generate_eicr("ILI (COVID-like)", 24, "2026-05-24")
