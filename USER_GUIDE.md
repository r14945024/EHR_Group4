# 📖 User & Operation Guide: FHIR Syndromic Surveillance System

This guide explains the function of each component in the **Group 4 Analysis Sandbox** and provides step-by-step instructions on how to operate the end-to-end pipeline.

---

## 🛠 File Overview

### 1. Infrastructure & Simulation (The Foundation)
*   **`docker-compose.yml`**: Spins up the **HAPI FHIR Server**. This is your central database (Port 8081).
*   **`ingestion_server.py`**: The **Group 2 Ingestion Layer**. It listens for triage data (Port 5001), transforms it into clinical resources, and persists it to FHIR.
*   **`digital_avatar.py`**: The **Group 1 Data Collection Layer**. An interactive CLI that simulates a conversational AI triage session.
*   **`multi_triage_test.py`**: **Unified Stress Tester**. It generates **1 year (365 days)** of diverse patient records and sends them through the Ingestion Server to test long-term surveillance.
*   **`triage_to_fhir.py`**: Contains the logic used by the server to turn raw survey answers into standardized FHIR resources.

### 2. The Analysis Pipeline (Group 4 Core)
*   **`live_export.py`**: The "Extractor." Uses Bulk FHIR ($export) with **Smart Merge** logic to build a persistent local archive without duplicates.
*   **`run_analysis.py`**: The "Processor." Performs longitudinal analysis (14-day rolling window) to detect outbreaks and trigger alerts.
*   **`dashboard.py`**: The "Visualizer." A web-based dashboard built with **Streamlit** to show real-time trends and geographic hotspots.

### 3. Reporting, Logic & CDS (The Professional Layer)
*   **`setup_cds_logic.py`**: The "Programmer." Configures automated isolation protocols on the server.
*   **`report_eicr_to_fhir.py`**: The "Auditor." Saves generated eICR alerts back to the FHIR server for permanent, versioned storage.
*   **`generate_eicr.py`**: Generates formal **Electronic Initial Case Report (eICR)** JSON documents.
*   **`covid_logic.cql`**: Official **Clinical Quality Language** defining the suspected case criteria.

---

## 🚀 Step-by-Step Operation Manual

### Phase 1: Environment Setup
1.  **Start the FHIR Server:** `docker-compose up -d`
2.  **Start the Ingestion Server:** `python ingestion_server.py` (Separate terminal)
3.  **Initialize CDS Logic:** `python setup_cds_logic.py`
4.  **Install Dependencies:** `pip install requests flask pandas numpy matplotlib streamlit plotly`

### Phase 2: Live Data Entry & Simulation
5.  **Run a Triage Session (Manual):** `python digital_avatar.py` (you can skip this part!)
6.  **Run 1-Year Stress Test (Automated):** `python multi_triage_test.py`
    *Note: This takes ~5-8 minutes to ingest 1,500+ records.*

### Phase 3: Extraction & Analysis
7.  **Run Bulk Export:** `python live_export.py`
    *Uses Smart Merge to accumulate data into `exported_data.ndjson`.*
8.  **Run Syndromic Analysis:** `python run_analysis.py`

### Phase 4: Visualization
9.  **Launch the Dashboard:** `streamlit run dashboard.py`

---

## 📁 Output Directory
*   `exported_data.ndjson`: Your **Persistent Longitudinal Archive**.
*   `outputs/eICR_Alert_XXX.json`: Formal CDC notification documents.
*   `outputs/anomaly_visualization.png`: Static trend analysis chart.
