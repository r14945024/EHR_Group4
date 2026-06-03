# FHIR-Driven Intelligent Infectious Disease Notification and Syndromic Surveillance System

**Group 4** | **Member:** I-Chen Tsai

## Overview
This repository contains a functional prototype of a "Clinical-to-Public Health" pipeline designed to automate infectious disease reporting. It processes over 400,000 synthetic FHIR resources to transform individual emergency triage entries into actionable, population-level insights. 

The system utilizes a HAPI FHIR server for clinical data persistence, Bulk FHIR standards for large-scale extraction, and statistical clustering to detect temporal anomalies in real-time, aligning with the "TW Core" national data platform and NSSP guidelines.

## System Architecture

## Key Engineering Features
* **Resilient Data Ingestion (`upload_bundles.py`):** Automatically maps `urn:uuid:` placeholders to static IDs and sorts foundational resources (Organizations, Practitioners) first to maintain referential integrity. Includes a configurable **Two-Phase Multithreading** engine and "Safety Valve" chunking to prevent Java Heap exhaustion on massive payloads.
* **Robust Extraction (`live_export.py`):** Utilizes the Bulk FHIR `$export` operation with an automated "Crawl Fallback" mechanism to bypass H2 database locking issues, streaming data directly into a local NDJSON artifact without memory crashes.
* **Advanced Syndromic Surveillance (`run_analysis.py`):** Maps symptoms to LOINC and SNOMED-CT codes to identify COVID-like, Dengue-like, and Flu-like clusters. Implements an aggressive ID extraction protocol and reads custom FHIR extensions (`http://example.org/zip`) to ensure perfect geographic mapping. Outbreaks are detected using a 14-day rolling 3-SD baseline.
* **Automated Alerting & Audit Loop:** Upon detecting an anomaly, the system automatically generates an HL7 eICR Document Bundle (`generate_eicr.py`) and reports it back to the FHIR server (`report_eicr_to_fhir.py`) to maintain a persistent, searchable audit trail.
* **NSSP Compliance Validation (`validate_nssp.py`):** Scans the extracted NDJSON against Priority 1 Data Elements (Zip, DOB, Gender, LOINC), with built-in logic to handle synthetic data variances and custom extensions.

## Prerequisites
* **Docker Desktop** (Make sure it is running)
* **Python 3.8+**
* `pip install -r requirements.txt`

## Quick Start & Pipeline Execution

### 1. Initialize the FHIR Repository
Start the local HAPI FHIR server. This will deploy the database at `http://localhost:8081/fhir`.
```bash
docker-compose up -d

```

*(Wait ~60 seconds for the Spring Boot application to fully initialize).*

### 2. Ingest Synthetic Data

Upload the patient bundles to the repository.

```bash
python upload_bundles.py

```

*Note: To speed up ingestion, open `upload_bundles.py` and set `enable_multithreading=True` in the `__main__` block. This will sequentially upload foundational resources before launching a thread pool for clinical bundles.*

### 3. Extract Bulk Data

Extract the persisted data into an AI-ready NDJSON format.

```bash
python live_export.py

```

*This will generate (or append to) `exported_data.ndjson`.*

### 4. Run Syndromic Surveillance Analysis

Execute the anomaly detection pipeline.

```bash
python run_analysis.py

```

This script will:

1. Parse the NDJSON and map patient locations.
2. Calculate the 14-day 3-SD baseline.
3. Automatically generate an eICR alert if a cluster is detected and post it back to the server.
4. Output `anomaly_visualization.png`, `syndromic_mapping.csv`, and `patient_classifications.csv` into the `outputs/` folder.

### 5. Validate NSSP Compliance

Run the validation tool to ensure the extracted dataset meets Priority 1 completeness thresholds.

```bash
python validate_nssp.py

```

### 6. Launch the Dashboard

Start the interactive Streamlit UI for real-time situational awareness.

```bash
streamlit run dashboard.py

```

## Supported Scenarios (Test Cases)

1. **COVID-like Scenario:** Detects Fever + Cough (LOINC `8310-5`, SNOMED `49727002`).
2. **Dengue-like Scenario:** Detects Fever + Rash/Headache/Joint Pain/Muscle Pain.
3. **Flu-like Scenario:** Detects Fever + (Cough or Sore Throat) + Muscle Pain.