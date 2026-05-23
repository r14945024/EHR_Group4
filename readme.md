# Group 4 Sandbox: Syndromic Surveillance & Population Health

This repository contains the standalone development and testing environment for **Group 4 (Analysis Layer)** of the FHIR-Driven Intelligent Infectious Disease Notification System.

To enable independent development without waiting for upstream dependencies (Group 1 & Group 3), this sandbox bypasses the frontend triage layer. It generates synthetic clinical data (COVID-like, Dengue-like, and Flu-like scenarios) , packages them into FHIR Transaction Bundles , and injects them directly into a local HAPI FHIR server. This establishes the necessary "Source of Truth" to test Bulk FHIR extraction and population-level statistical clustering.

---

## 🏗 System Architecture (Testing Flow)

1. 
**Local FHIR Box:** Deployment of a HAPI FHIR JPA Server via Docker.


2. 
**Synthetic Data Injection:** A Python script generates patient encounters (`Patient`, `Observation`, `Condition` resources) mapped with SNOMED-CT/LOINC codes and posts them as atomic transactions.


3. 
**Large-Scale Data Extraction:** Utilizing the Bulk FHIR Access (`$export`) protocol to extract data in NDJSON format.


4. 
**The Analysis Layer:** Python (Pandas/NumPy) scripts applying the NSSP framework to categorize syndromes, detect anomalies, and visualize outbreaks.



---

## 🛠 Prerequisites

Ensure you have the following installed on your local machine:

* **Docker & Docker-Compose:** For running the local FHIR server.
* **Python 3.8+**
* **Required Python Packages:**
```bash
pip install requests pandas numpy matplotlib

```



---

## 🚀 Quick Start Guide

### Step 1: Deploy the Storage Layer (HAPI FHIR)

Before injecting data, spin up the foundational storage layer.

```bash
# Clone the official HAPI FHIR starter project
git clone https://github.com/hapifhir/hapi-fhir-jpaserver-starter.git
cd hapi-fhir-jpaserver-starter

# Start the server in detached mode
docker-compose up -d

```

> **Verification:** Navigate to `http://localhost:8080/fhir/metadata` in your browser. If a CapabilityStatement loads, the server is healthy.

### Step 2: Inject Synthetic Clinical Data

Run the mock data generator. This script mimics the output of Group 2 by creating `Patient`, `Observation`, and `Condition` resources, bundling them into transactions to ensure referential integrity, and POSTing them to the local server.

```bash
python inject_mock_data.py

```

*Note: This script intentionally spikes the volume of specific symptoms (e.g., Fever + Cough) in the latest simulated days to trigger the outbreak detection algorithms later.*

### Step 3: Trigger Bulk FHIR Extraction

Initiate the Bulk FHIR `$export` command to extract the dataset formatted for big data pipelines (NDJSON).

```bash
# Request the export for specific resource types
curl -H "Prefer: respond-async" -H "Accept: application/fhir+json" \
"http://localhost:8080/fhir/$export?_type=Patient,Observation,Condition" -i

```

1. Check the HTTP headers in the response for the `Content-Location` URL.
2. Send a `GET` request to that URL to download the generated `.ndjson` files.
3. Save the resulting file as `exported_data.ndjson` in your working directory.

### Step 4: Execute Syndromic Surveillance Analysis

Run your core Group 4 data science pipeline to perform syndromic mapping and temporal anomaly detection.

```bash
python run_analysis.py

```

**Expected Outputs:**

* 
**`syndromic_mapping.csv`**: A normalized table mapping raw clinical entries to NSSP clusters (e.g., ILI, GI).


* 
**`anomaly_visualization.png`**: A temporal line graph visualizing the historical baseline and highlighting the statistical threshold breach (the simulated outbreak).



---

## 📂 Project Structure

```text
├── README.md
├── inject_mock_data.py     # Generates & POSTs FHIR Transaction Bundles
├── run_analysis.py         # Pandas pipeline for NSSP mapping and clustering
├── exported_data.ndjson    # (Generated) Bulk export from HAPI FHIR
└── outputs/                # (Generated) Charts and population health insights

```# EHR_Group4
