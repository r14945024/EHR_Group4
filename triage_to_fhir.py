import json
import uuid
import random
from datetime import datetime

def transform_questionnaire_response(qr_json):
    """
    Transforms a FHIR QuestionnaireResponse into discrete Patient, Observation, and Condition resources.
    This mimics the core logic of the Group 2 (Storage Layer).
    """
    patient_id = str(uuid.uuid4())
    resources = []
    
    # Extract the timestamp from the QuestionnaireResponse (Ref: Phase 2 Stress Test)
    authored_date = qr_json.get('authored', datetime.now().isoformat())

    # 1. Extract demographic and clinical answers
    answers = {}
    for item in qr_json.get('item', []):
        link_id = item.get('linkId')
        answer_list = item.get('answer', [])
        if answer_list:
            ans = answer_list[0]
            if 'valueString' in ans: answers[link_id] = ans['valueString']
            elif 'valueBoolean' in ans: answers[link_id] = ans['valueBoolean']
            elif 'valueDate' in ans: answers[link_id] = ans['valueDate']

    # 2. Create Patient Resource
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "name": [{"text": answers.get('patient-name', 'Anonymous')}],
        "gender": answers.get('patient-gender', 'unknown'),
        "birthDate": answers.get('patient-birthdate', '2000-01-01')
    }
    resources.append(patient)
    
    # 3. Create Observations based on symptoms
    zip_code = answers.get('patient-zip', 'Unknown')
    facility = f"Facility-{random.choice(['A', 'B', 'C', 'D', 'E', 'F'])}"
    
    if answers.get('symptom-fever'):
        resources.append({
            "resourceType": "Observation",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "effectiveDateTime": authored_date,
            "valueQuantity": {"value": 38.5, "unit": "C"},
            "device": {"display": facility},
            "extension": [{"url": "http://example.org/zip", "valueString": zip_code}]
        })
        
    if answers.get('symptom-cough'):
        resources.append({
            "resourceType": "Observation",
            "status": "final",
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "49727002", "display": "Cough"}]},
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "effectiveDateTime": authored_date,
            "device": {"display": facility},
            "extension": [{"url": "http://example.org/zip", "valueString": zip_code}]
        })

    if answers.get('symptom-rash'):
        resources.append({
            "resourceType": "Observation",
            "status": "final",
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "271757001", "display": "Rash"}]},
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "effectiveDateTime": authored_date,
            "device": {"display": facility},
            "extension": [{"url": "http://example.org/zip", "valueString": zip_code}]
        })
            
    # 4. Create Condition if symptoms match high-priority patterns
    if answers.get('symptom-fever') and answers.get('symptom-cough'):
        resources.append({
            "resourceType": "Condition",
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Suspected COVID-19"}]},
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "recordedDate": authored_date
        })
    elif answers.get('symptom-fever') and answers.get('symptom-rash'):
        resources.append({
            "resourceType": "Condition",
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "38362002", "display": "Suspected Dengue"}]},
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "recordedDate": authored_date
        })
            
    # Wrap in a Transaction Bundle
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": f"urn:uuid:{res.get('id', str(uuid.uuid4())) if res['resourceType'] == 'Patient' else str(uuid.uuid4())}",
                "resource": res,
                "request": {"method": "POST", "url": res['resourceType']}
            } for res in resources
        ]
    }
    
    # Fix Patient fullUrl to be consistent with references
    for entry in bundle['entry']:
        if entry['resource']['resourceType'] == 'Patient':
            entry['fullUrl'] = f"urn:uuid:{patient_id}"
            break
            
    return bundle
