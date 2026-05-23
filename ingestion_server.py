from flask import Flask, request, jsonify
import requests
import json
from triage_to_fhir import transform_questionnaire_response

app = Flask(__name__)

FHIR_SERVER_URL = "http://localhost:8081/fhir"

@app.route('/', methods=['GET'])
def health_check():
    return "🚀 FHIR Ingestion Server is running on port 5001. Use /ingest (POST) for data submission."

@app.route('/ingest', methods=['POST'])
def ingest_triage():
    """
    Endpoint for Group 1 to submit QuestionnaireResponse.
    Implements Group 2 logic: Ingest -> Transform -> Persist.
    """
    qr_data = request.json
    if not qr_data or qr_data.get('resourceType') != 'QuestionnaireResponse':
        return jsonify({"error": "Invalid FHIR QuestionnaireResponse"}), 400

    print("📥 Received QuestionnaireResponse. Transforming...")
    
    # Transform to Transaction Bundle
    transaction_bundle = transform_questionnaire_response(qr_data)
    
    # POST to HAPI FHIR
    try:
        response = requests.post(FHIR_SERVER_URL, json=transaction_bundle)
        if response.status_code in [200, 201]:
            print("✅ Data persisted to FHIR Server.")
            return jsonify({
                "message": "Triage data ingested and persisted successfully",
                "fhir_response": response.json()
            }), 201
        else:
            print(f"❌ FHIR Server Error: {response.status_code}")
            return jsonify({
                "error": "Failed to persist to FHIR server",
                "details": response.text
            }), 502
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Ingestion Server (Group 2) running on port 5001...")
    app.run(port=5001)
