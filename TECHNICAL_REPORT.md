# FHIR-Driven Intelligent Infectious Disease Notification and Syndromic Surveillance System

**Group Number:** 4  
**Member Names:** I-Chen Tsai

---

## Abstract
This project presents a functional prototype of a "Clinical-to-Public Health" pipeline designed to automate infectious disease reporting. By processing over **400,000 FHIR resources** extracted from **557 patient bundles**, we demonstrate how standardized health data can be transformed from individual triage entries into actionable population-level insights. The system utilizes HAPI FHIR for persistence, Bulk FHIR for large-scale extraction, and statistical clustering to detect outbreaks in real-time.

## Background & Unmet Need
Historically, public health surveillance has relied on manual, paper-based notification forms, leading to significant latency and administrative burden. A FHIR-based automated solution ensures semantic interoperability, reduces "clinical fatigue," and provides a real-time "Source of Truth" for biosecurity, allowing for intervention before laboratory confirmation.

## System Architecture
The system architecture follows a modular approach:
1.  **Data Capture:** Ingestion of FHIR transaction bundles (Patient, Observation, Condition).
2.  **Persistence Layer:** HAPI FHIR JPA Server acting as the clinical repository.
3.  **Analysis Layer (Group 4):** Extraction via Bulk FHIR ($export), rule-based phenotyping (LOINC/SNOMED), and temporal anomaly detection.

### Technical Implementation

### Implementation Overview
1.  **Storage Layer Deployment:** Deployed a HAPI FHIR server using Docker.
2.  **Data Standardization:** Mapped symptoms to LOINC and SNOMED-CT codes.
3.  **High-Fidelity Simulation:** Integrated 557 patient bundles (409,973 resources) to test scale and longitudinal accuracy.
4.  **NSSP Validation:** Implemented `validate_nssp.py` to monitor Priority 1 Data Elements (Zip, DOB, Gender, LOINC).
5.  **Anomaly Detection:** Built a Pandas pipeline calculating a 14-day rolling 3-SD baseline.
6.  **Interactive Dashboard:** Developed a Streamlit interface for real-time surveillance.

### Technical Deep-Dive (Advanced Surveillance)
*   **Surgical Data Ingestion:** `upload_bundles.py` implements "Safety Valve" logic to split large bundles (up to 57MB) while maintaining transaction integrity.
*   **Resilient Extraction:** `live_export.py` utilizes Bulk FHIR with an automated "Crawl Fallback" mechanism to ensure data availability even if the bulk engine is unstable.
*   **Rule-Based Phenotyping:**
    *   **COVID-19:** Fever + Cough (LOINC `8310-5`, SNOMED `49727002`).
    *   **Dengue:** Fever + Rash/Headache/Joint Pain/Muscle Pain.
    *   **Influenza:** Fever + (Cough or Sore Throat) + Muscle Pain.
*   **Automated eICR Alerting:** Upon detecting an anomaly, `run_analysis.py` triggers `generate_eicr.py` to create a formal HL7 FHIR Document Bundle.
*   **Persistent Audit Trail:** The system automatically executes `report_eicr_to_fhir.py` to save generated alerts back to the FHIR server. This ensures that every public health notification is versioned, searchable, and available for federal auditing.
*   **Clinical Reasoning (CQL):** Authored `syndromic_logic.cql` (v2.0.0) to align with professional classification standards.

## FHIR Standards Utilized
*   **HL7 FHIR R4 Resources:** Patient, Observation, Condition, Bundle, Binary (for eICR storage).
*   **Terminology Standards:** LOINC (vitals) and SNOMED-CT (diagnoses/symptoms).
*   **TW Core IG:** Alignment with Taiwan's national profiles for infectious disease reporting.

## Test Cases

### 1. COVID-like Scenario
*   **Input:** Patient with Temperature > 37.5°C and Cough Observation.
*   **Result:** Correctly identified as "COVID-like" cluster. Anomaly detected on 2021-04-17 in the synthetic dataset.

### 2. Dengue-like Scenario
*   **Input:** Patient with Fever and Headache or Rash.
*   **Result:** Mapped to "Dengue-like" cluster. System detected scattered occurrences across the longitudinal archive.

### 3. Flu-like Scenario
*   **Input:** Patient with Fever, Sore Throat, and Muscle Aches.
*   **Result:** Mapped to "Flu-like" cluster, representing severe respiratory cases requiring closer monitoring.

## Conclusion & Future Policy Impact
This prototype demonstrates that a "born digital" approach to clinical triage is not only feasible but essential for modern biosecurity. By aligning with the "TW Core" national data platform and future CDC automated reporting mandates, this system provides a blueprint for a unified, real-time national health surveillance ecosystem.

## Project Success Criteria
The success of this implementation is measured by its ability to bridge the gap between individual clinical encounters and population-level situational awareness. The "One-Stop" architecture ensures that every clinical signal captured at the point of care is immediately available for AI-ready data aggregation, facilitating life-saving public health decisions.
