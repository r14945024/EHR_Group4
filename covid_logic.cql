library COVID19Logic version '1.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1'

codesystem "LOINC": 'http://loinc.org'
codesystem "SNOMED": 'http://snomed.info/sct'

code "Fever": '8310-5' from "LOINC" display 'Body temperature'
code "Cough": '49727002' from "SNOMED" display 'Cough'
code "COVID19": '840539006' from "SNOMED" display 'COVID-19'

context Patient

/* 
  Logic: Patient is a "Suspected Case" if they have:
  1. A Temperature Observation > 38.0 C
  2. A Cough Observation
*/

define "HasFever":
  exists([Observation: "Fever"] O
    where O.status = 'final'
      and O.value as Quantity > 38.0 'Cel'
  )

define "HasCough":
  exists([Observation: "Cough"] O
    where O.status = 'final'
  )

define "IsSuspectedCOVID":
  "HasFever" and "HasCough"

/* Trigger for Group 5 MedMorph Workflow */
define "NeedsNotification":
  "IsSuspectedCOVID"
