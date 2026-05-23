import requests
import json

FHIR_SERVER_URL = "http://localhost:8081/fhir"

def upload_resource(resource):
    res_type = resource['resourceType']
    res_id = resource.get('id', '')
    url = f"{FHIR_SERVER_URL}/{res_type}/{res_id}" if res_id else f"{FHIR_SERVER_URL}/{res_type}"
    
    method = "PUT" if res_id else "POST"
    response = requests.request(method, url, json=resource)
    
    if response.status_code in [200, 201]:
        print(f"✅ Successfully uploaded {res_type}: {response.json().get('id')}")
    else:
        print(f"❌ Failed to upload {res_type}: {response.status_code} - {response.text}")

def main():
    print("🚀 Initializing Clinical Decision Support (CDS) Resources...")

    # 1. ActivityDefinition: Define the Action (Isolation Protocol)
    # Ref: Page 17 of PDF
    activity_def = {
        "resourceType": "ActivityDefinition",
        "id": "isolate-patient-protocol",
        "status": "active",
        "description": "Protocol for immediate patient isolation upon suspected high-priority pathogen detection.",
        "kind": "ServiceRequest",
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": "170499009", "display": "Isolation procedure"}]
        },
        "intent": "order",
        "priority": "stat",
        "doNotPerform": False
    }

    # 2. PlanDefinition: Define the Trigger (The "Brain")
    # Ref: Page 15 of PDF
    plan_def = {
        "resourceType": "PlanDefinition",
        "id": "covid-surveillance-plan",
        "status": "active",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/plan-definition-type", "code": "workflow-definition"}]},
        "description": "Triggers isolation and public health reporting if COVID-19 criteria are met.",
        "action": [
            {
                "title": "Suspected COVID-19 Management",
                "condition": [
                    {
                        "kind": "applicability",
                        "expression": {
                            "language": "text/cql",
                            "expression": "IsSuspectedCOVID" # Linking to our covid_logic.cql
                        }
                    }
                ],
                "definitionCanonical": "ActivityDefinition/isolate-patient-protocol"
            }
        ]
    }

    upload_resource(activity_def)
    upload_resource(plan_def)

if __name__ == "__main__":
    main()
