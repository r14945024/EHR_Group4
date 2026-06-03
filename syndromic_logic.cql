library SyndromicSurveillanceLogic version '2.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1'

// ---------------------------------------------------------
// CODESYSTEMS
// ---------------------------------------------------------
codesystem "LOINC": 'http://loinc.org'
codesystem "SNOMED": 'http://snomed.info/sct'

// ---------------------------------------------------------
// COVID-19 CODES
// ---------------------------------------------------------
// LOINC
code "COVID_RNA_PCR": '94309-2' from "LOINC" display 'SARS-CoV-2 RNA qualitative test'
code "COVID_AG_RAPID": '97097-0' from "LOINC" display 'SARS-CoV-2 antigen rapid immunoassay'
code "COVID_AG_IMMUNO": '96119-3' from "LOINC" display 'SARS-CoV-2 antigen immunoassay'

// SNOMED
code "COVID_DX": '840539006' from "SNOMED" display 'COVID-19 disease'
code "COVID_PNEUMONIA": '882784691000119100' from "SNOMED" display 'COVID pneumonia'
code "COVID_ARDS": '674814021000119106' from "SNOMED" display 'COVID-related ARDS'
code "COVID_SUSPECTED": '840544004' from "SNOMED" display 'Suspected COVID-19'

// ---------------------------------------------------------
// DENGUE CODES
// ---------------------------------------------------------
// LOINC
code "DENGUE_NS1_AG": '75377-2' from "LOINC" display 'Dengue virus NS1 Ag'
code "DENGUE_RNA_SERUM": '7855-0' from "LOINC" display 'Dengue virus 1+2+3+4 RNA'
code "DENGUE_RNA_BLOOD": '88189-6' from "LOINC" display 'Dengue virus RNA in blood'

// SNOMED
code "DENGUE_DX": '38362002' from "SNOMED" display 'Dengue'
code "DENGUE_SEVERE": '20927009' from "SNOMED" display 'Severe dengue / DHF'

// ---------------------------------------------------------
// INFLUENZA CODES
// ---------------------------------------------------------
// LOINC
code "FLU_A_RNA": '92142-9' from "LOINC" display 'Influenza A RNA'
code "FLU_B_RNA": '92141-1' from "LOINC" display 'Influenza B RNA'
code "FLU_A_AG": '80382-5' from "LOINC" display 'Influenza A antigen'
code "FLU_B_AG": '80383-3' from "LOINC" display 'Influenza B antigen'

// SNOMED
code "FLU_DX": '6142004' from "SNOMED" display 'Influenza'
code "FLU_A_DX": '442438000' from "SNOMED" display 'Influenza A'
code "FLU_B_DX": '24662006' from "SNOMED" display 'Influenza B'
code "FLU_A_H1N1_DX": '442696006' from "SNOMED" display 'Influenza A H1N1'

// ---------------------------------------------------------
// CLASSIFICATION LOGIC
// ---------------------------------------------------------

context Patient

// --- COVID Logic ---
define "IsCOVIDConfirmed":
  exists([Observation: "COVID_RNA_PCR"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Observation: "COVID_AG_RAPID"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Observation: "COVID_AG_IMMUNO"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Condition: "COVID_DX"]) or
  exists([Condition: "COVID_PNEUMONIA"]) or
  exists([Condition: "COVID_ARDS"])

define "IsCOVIDSuspected":
  not "IsCOVIDConfirmed" and exists([Condition: "COVID_SUSPECTED"])

// --- Dengue Logic ---
define "IsDengueConfirmed":
  exists([Observation: "DENGUE_NS1_AG"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Observation: "DENGUE_RNA_SERUM"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Observation: "DENGUE_RNA_BLOOD"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Condition: "DENGUE_DX"]) or
  exists([Condition: "DENGUE_SEVERE"])

// --- Influenza Logic ---
define "IsFluA":
  exists([Observation: "FLU_A_RNA"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Observation: "FLU_A_AG"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Condition: "FLU_A_DX"]) or
  exists([Condition: "FLU_A_H1N1_DX"])

define "IsFluB":
  exists([Observation: "FLU_B_RNA"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Observation: "FLU_B_AG"] O where O.value ~ "Positive" or O.value ~ "Detected") or
  exists([Condition: "FLU_B_DX"])

define "IsFluUnspecified":
  not "IsFluA" and not "IsFluB" and (
    exists([Condition: "FLU_DX"])
  )

define "IsFluConfirmed":
  "IsFluA" or "IsFluB" or "IsFluUnspecified"

// --- Summary ---
define "InPopulation":
  "IsCOVIDConfirmed" or "IsDengueConfirmed" or "IsFluConfirmed"

define "CaseClassification":
  if "IsCOVIDConfirmed" then 'COVID-19'
  else if "IsDengueConfirmed" then 'Dengue'
  else if "IsFluA" then 'Influenza A'
  else if "IsFluB" then 'Influenza B'
  else if "IsFluConfirmed" then 'Influenza'
  else 'Negative'
