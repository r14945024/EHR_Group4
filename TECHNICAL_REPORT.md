# FHIR-Driven Intelligent Infectious Disease Notification and Syndromic Surveillance System

**Group Number:** 4  
**Member Names:** [Insert Names]

---

## Abstract
This project presents a functional prototype of a "Clinical-to-Public Health" pipeline designed to automate infectious disease reporting. By integrating a conversational AI front-end with a FHIR-native storage layer (Group 2) and a syndromic surveillance analysis layer (Group 4), we demonstrate how standardized health data can be transformed from individual triage entries into actionable population-level insights. The system utilizes HAPI FHIR for persistence, Bulk FHIR for large-scale extraction, and statistical clustering to detect outbreaks in real-time.

## Background & Unmet Need
Historically, public health surveillance has relied on manual, paper-based notification forms, leading to significant latency, data fragmentation, and administrative burden on clinicians. These delays often mean that outbreaks are identified only after laboratory confirmation, missing the critical window for early intervention. A FHIR-based automated solution is required to ensure semantic interoperability, reduce "clinical fatigue," and provide the CDC with a real-time "Source of Truth" for biosecurity.

## System Architecture
The system architecture follows a modular, layer-based approach:
1.  **Data Capture:** A digital avatar (Rasa-based) collects patient symptoms and travel history, mapping them to a `QuestionnaireResponse`.
2.  **Persistence Layer (Group 2):** The `QuestionnaireResponse` is transformed into discrete FHIR resources (`Patient`, `Observation`, `Condition`) and stored in a HAPI FHIR JPA Server via atomic transactions.
3.  **Analysis Layer (Group 4):** Clinical data is extracted using the Bulk FHIR `$export` protocol in NDJSON format. A Python-based pipeline applies the National Syndromic Surveillance Program (NSSP) framework to categorize syndromes and detect statistical anomalies.

## Technical Implementation

### Implementation Overview
1.  **Storage Layer Deployment:** Deployed a HAPI FHIR server using Docker to act as the centralized repository.
2.  **Data Standardization:** Developed logic to map raw symptoms to LOINC and SNOMED-CT codes (e.g., Fever: `8310-5`, COVID-19: `840539006`).
3.  **Simulation Engine:** Created a synthetic data generator to simulate **365 days (1 year)** of patient traffic, including a controlled "outbreak spike" for COVID-like symptoms, with added **geographic entropy (Zip Codes)** and **Facility IDs**.
4.  **Anomaly Detection & Visualization:** Built a Pandas-based pipeline that calculates a **14-day rolling baseline** to detect multi-season anomalies. Developed an **interactive Streamlit Dashboard** for real-time longitudinal surveillance.

### Technical Deep-Dive (Advanced Surveillance)
*   **Longitudinal Surveillance:** By simulating a full year of clinical encounters, the system demonstrates the ability to differentiate between seasonal background noise and acute infectious disease outbreaks.
*   **Live Bulk FHIR Export:** We implemented a client that utilizes the **Async $export** protocol and a **Smart Merge** deduplication logic.
*   **Automated eICR Alerting:** Upon anomaly detection, the system triggers the `generate_eicr.py` module, which packages the cluster data into a formal **HL7 FHIR Document Bundle (eICR)** for public health notification.
*   **Clinical Reasoning (CQL):** We authored a `covid_logic.cql` file that demonstrates how the system's "Brain" evaluates discrete observations (Fever + Cough) to flag suspected cases, ensuring semantic consistency between the storage and decision layers.
*   **Geographic Clustering:** The system parses patient `address.postalCode` and `device.display` (Facility ID) from FHIR resources to identify geographic hotspots.
*   **Persistent Data Archiving:** The analysis pipeline implements a "Smart Merge" logic during data extraction. It deduplicates incoming FHIR resources against the local archive, allowing for cumulative data growth and multi-month longitudinal analysis that persists even if the temporary FHIR server is reset.

## FHIR Standards Utilized
*   **HL7 FHIR R4 Resources:** Patient, Observation, Condition, Bundle.
*   **Bulk FHIR Access:** `$export` protocol for NDJSON retrieval.
*   **Terminology Standards:** LOINC (vitals/symptoms) and SNOMED-CT (diagnoses/conditions).
*   **NSSP Implementation Guide:** Framework for syndromic categorization.

## Test Cases

### 1. COVID-like Scenario
*   **Input:** Fever + Cough + Travel History.
*   **Expected FHIR Output:** 
    *   `Observation` (LOINC `8310-5` / `49727002`)
    *   `Condition` (SNOMED `840539006` - COVID-19)
*   **Analysis Result:** Correctly mapped to the "ILI" (Influenza-Like Illness) syndrome cluster.

### 2. Dengue-like Scenario
*   **Input:** Fever + Rash + Joint Pain.
*   **Expected FHIR Output:** 
    *   `Observation` (LOINC `8310-5` / `271757001`)
    *   `Condition` (SNOMED `38362002` - Dengue fever)
*   **Analysis Result:** Mapped to the "Febrile with Rash" syndrome cluster.

### 3. Flu-like Scenario
*   **Input:** Fever + Sore Throat + Muscle Aches.
*   **Expected FHIR Output:** 
    *   `Observation` (LOINC `8310-5` / `162357003`)
    *   `Condition` (SNOMED `6142004` - Influenza)
*   **Analysis Result:** Included in the baseline temporal analysis for respiratory trends.

## Conclusion & Future Policy Impact
This prototype demonstrates that a "born digital" approach to clinical triage is not only feasible but essential for modern biosecurity. By aligning with the "TW Core" national data platform and future CDC automated reporting mandates, this system provides a blueprint for a unified, real-time national health surveillance ecosystem.

## Project Success Criteria
The success of this implementation is measured by its ability to bridge the gap between individual clinical encounters and population-level situational awareness. The "One-Stop" architecture ensures that every clinical signal captured at the point of care is immediately available for AI-ready data aggregation, facilitating life-saving public health decisions.
