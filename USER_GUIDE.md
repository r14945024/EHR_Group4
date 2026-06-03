# 📖 User & Operation Guide: FHIR Syndromic Surveillance System

This guide explains the function of each component in the **Group 4 Analysis Sandbox** and provides step-by-step instructions on how to operate the end-to-end pipeline.

---

## 🛠 File Overview

### 1. Data Management (The Foundation)
*   **`docker-compose.yml`**: Spins up the **HAPI FHIR Server**. This is your central database (Port 8081).
*   **`upload_bundles.py`**: The "Loader." Uploads all local FHIR JSON bundles from the `fhir/` directory to the FHIR server.

### 2. The Analysis Pipeline (Group 4 Core)
*   **`prepare_data.py`**: The "Preprocessor." Flattens local FHIR transaction bundles into NDJSON resources for faster analysis.
*   **`live_export.py`**: The "Extractor." Uses Bulk FHIR ($export) with **Smart Merge** logic to build a persistent local archive from the server.
*   **`validate_nssp.py`**: The "Validator." Checks data against **NSSP Priority 1** quality metrics.
*   **`run_analysis.py`**: The "Processor." Performs longitudinal analysis using **Rule-Based Phenotyping**:
    *   **COVID-19**: Lab-confirmed PCR/Antigen or specialized clinical diagnoses.
    *   **Dengue**: NS1 Antigen or clinical Dengue Hemorrhagic Fever detection.
    *   **Influenza (A & B)**: Explicit subtyping based on RNA and Antigen rapid tests.
    *   Detects anomalies using a **14-day rolling 3-SD window**.
*   **`dashboard.py`**: The "Visualizer." A Streamlit dashboard for real-time surveillance visualization.

### 3. Reporting & Logic (The Professional Layer)
*   **`report_eicr_to_fhir.py`**: The "Auditor." Saves generated eICR alerts back to the FHIR server for permanent, versioned storage.
*   **`generate_eicr.py`**: Generates formal **Electronic Initial Case Report (eICR)** JSON documents.
*   **`syndromic_logic.cql`**: Official **Clinical Quality Language** defining the suspected case criteria.

---

## 🚀 Step-by-Step Operation Manual

### Phase 1: Environment Setup
1.  **Start the FHIR Server:** `docker-compose up -d`
    *   This deploys a HAPI FHIR JPA server on `http://localhost:8081/fhir`.
2.  **Install Dependencies:**
    ```bash
    pip install requests flask pandas numpy matplotlib streamlit plotly
    ```

### Phase 2: Data Population (Ingestion)
Before running analysis, you need to populate your FHIR server with clinical data:
3.  **Upload Local Bundles:** `python upload_bundles.py`
    *   This script reads all files in the `fhir/` directory and uploads them as atomic transaction bundles. It includes a "Safety Valve" to split large files (up to 57MB) into smaller chunks.

### Phase 3: Extraction & Validation
Generate a high-performance dataset for the analysis engine:
4.  **Live Extraction (Recommended):** `python live_export.py`
    *   Uses Bulk FHIR ($export) to pull data from the server. Includes an automated "Crawl Fallback" if the Bulk engine is unavailable.
5.  **Offline Preprocessing (Optional):** `python prepare_data.py`
    *   Flattens local JSON bundles directly into `exported_data.ndjson` without using the server.
6.  **Validate Data Quality:** `python validate_nssp.py`
    *   Checks `exported_data.ndjson` against NSSP Priority 1 metrics (Completeness of Zip, DOB, Gender, and LOINC codes).

### Phase 4: Analysis & Automated Reporting
7.  **Run Syndromic Analysis:** `python run_analysis.py`
    *   **Clinical Mapping:** Categorizes cases into COVID-like, Dengue-like, and Flu-like clusters using SNOMED/LOINC logic.
    *   **Anomaly Detection:** Uses a 14-day rolling 3-SD window to detect statistical outbreaks.
    *   **Automated eICR:** If an anomaly is detected, it automatically triggers `generate_eicr.py` to create a public health alert.
    *   **Persistent Audit:** Automatically triggers `report_eicr_to_fhir.py` to save the alert back to the FHIR server for CDC auditing.

### Phase 5: Visualization
8.  **Launch the Dashboard:** `streamlit run dashboard.py`
    *   View real-time longitudinal trends, daily case counts, and flagged anomalies.

---

## 📈 Recent Simulation Results
A full end-to-end simulation was successfully performed on the local dataset:
*   **Data Volume:** 557 patient bundles processed, resulting in **409,973 FHIR resources** analyzed.
*   **Validation:** Achieved **100% completeness** for Gender, DOB, and Clinical Status.
*   **Detection:** Successfully identified a **COVID-like anomaly on 2021-04-17**.
*   **Reporting:** Automated eICR public health alert was successfully generated and saved to the FHIR server.

---

## 🔄 Dataset Update Workflow

If you want to analyze a new set of FHIR records, follow this sequence:

### 1. Data Replacement
*   Clear the existing files in the `fhir/` directory.
*   Place your new FHIR JSON Transaction Bundles into the `fhir/` folder.

### 2. Update Server & Export
```bash
python upload_bundles.py   # Upload new data to server
python live_export.py      # Extract and merge into exported_data.ndjson
```

### 3. Run Analysis
```bash
python run_analysis.py
```
*   **Outputs:** 
    *   `outputs/patient_classifications.csv`: Row-per-patient clinical classification.
    *   `outputs/syndromic_mapping.csv`: Daily statistical summary and anomaly alerts.
    *   `outputs/eICR_Alert_*.json`: Automated public health reports for detected outbreaks.
    *   `outputs/anomaly_visualization.png`: Static temporal charts.

---
