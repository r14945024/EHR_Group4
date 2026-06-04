import pandas as pd
import json
import matplotlib.pyplot as plt
from datetime import datetime
from generate_eicr import generate_eicr
from report_eicr_to_fhir import report_eicr_to_fhir

def load_ndjson(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def process_data(file_path):
    raw_data = load_ndjson(file_path)
    
    # 1. Ultra-Robust ID Extractor
    def extract_clean_id(raw_id):
        if not raw_id: return 'Unknown'
        id_str = str(raw_id)
        id_str = id_str.replace('urn:uuid:', '')
        return id_str.split('/')[-1]

    # 2. Build Maps (Zip and Facility)
    patient_zip_map = {}
    encounter_facility_map = {}
    
    for r in raw_data:
        rtype = r.get('resourceType')
        if rtype == 'Patient':
            p_id = extract_clean_id(r.get('id'))
            zip_code = '106' 
            addresses = r.get('address', [])
            if addresses and isinstance(addresses[0], dict):
                found_zip = addresses[0].get('postalCode')
                if found_zip: zip_code = found_zip
            patient_zip_map[p_id] = zip_code
            
        elif rtype == 'Encounter':
            e_id = extract_clean_id(r.get('id'))
            # Try serviceProvider display, then location display
            facility = r.get('serviceProvider', {}).get('display')
            if not facility:
                locations = r.get('location', [])
                if locations and isinstance(locations[0], dict):
                    loc_ref = locations[0].get('location', {})
                    facility = loc_ref.get('display')
            if facility:
                encounter_facility_map[e_id] = facility

    # 3. Extract Observations and Conditions
    observations = [r for r in raw_data if r.get('resourceType') == 'Observation']
    conditions = [r for r in raw_data if r.get('resourceType') == 'Condition']
    
    obs_df = pd.DataFrame(observations)
    cond_df = pd.DataFrame(conditions)
    
    if obs_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 4. Normalize Dates and Subject References
    obs_df['date_dt'] = pd.to_datetime(obs_df['effectiveDateTime'], errors='coerce', utc=True)
    obs_df = obs_df.dropna(subset=['date_dt']).copy()
    obs_df['date'] = obs_df['date_dt'].dt.date
    obs_df['patient_id'] = obs_df['subject'].apply(lambda x: extract_clean_id(x.get('reference')) if isinstance(x, dict) else 'Unknown')
    
    # Map Facility from Encounter
    obs_df['encounter_id'] = obs_df['encounter'].apply(lambda x: extract_clean_id(x.get('reference')) if isinstance(x, dict) else 'Unknown')
    obs_df['facility'] = obs_df['encounter_id'].map(encounter_facility_map).fillna('Unknown')

    if not cond_df.empty:
        cond_df['date_dt'] = pd.to_datetime(cond_df['recordedDate'], errors='coerce', utc=True)
        cond_df = cond_df.dropna(subset=['date_dt']).copy()
        cond_df['date'] = cond_df['date_dt'].dt.date
        cond_df['patient_id'] = cond_df['subject'].apply(lambda x: extract_clean_id(x.get('reference')) if isinstance(x, dict) else 'Unknown')

    # 5. Clinical Mapping (LOINC/SNOMED) - Enhanced with syndromic_logic.cql
    SYMPTOMS = {
        'Fever': ['8310-5', '386661006', '103001002'],
        'Cough': ['49727002'],
        'Rash': ['271757001'],
        'SoreThroat': ['267102003', '43878008', '162357003'],
        'MusclePain': ['68962001'],
        'JointPain': ['57676002', '297077008'],
        'Headache': ['25064002']
    }

    CONFIRMED_CODES = {
        'COVID': {
            'labs': ['94309-2', '97097-0', '96119-3'],
            'dx': ['840539006', '882784691000119100', '674814021000119106'],
            'suspected_labs': ['95941-1', '95422-2', '94769-7', '94505-5'],
            'suspected_dx': ['840544004', "1119303003", "1119304009"]
        },
        'Dengue': {
            'labs': ['75377-2', '7855-0', '88189-6'],
            'dx': ['38362002', '20927009', '409676000', '409677009', '409678004', '409679007'],
            'suspected_labs': ['101206-1', '88188-8', '75223-8', '104595-4'],

        },
        'Influenza_A': {
            'labs': ['92142-9', '34487-9', '80382-5'],
            'dx': ['442438000', '442696006']
        },
        'Influenza_B': {
            'labs': ['92141-1', '80383-3'],
            'dx': ['24662006']
        },
        'Influenza_Unspec': {
            'labs': ['80381-7', '72367-6', '85476-0', '81233-9', '95941-1'],
            'dx': ['6142004', '195878008']
        }
    }

    def get_clinical_markers(row):
        code_data = row.get('code')
        if not isinstance(code_data, dict): code_data = {}
        coding = code_data.get('coding', [])
        codes = [c.get('code') for c in coding if isinstance(c, dict)]
        symptoms = [s for s, s_codes in SYMPTOMS.items() if any(c in s_codes for c in codes)]
        
        markers = []
        is_positive = False
        if row.get('resourceType') == 'Observation':
            val_str = str(row.get('valueString', '')).lower()
            val_cc = row.get('valueCodeableConcept')
            if not isinstance(val_cc, dict): val_cc = {}
            val_text = str(val_cc.get('text', '')).lower()
            val_coding = val_cc.get('coding', [])
            is_positive = any(term in val_str or term in val_text for term in ['positive', 'detected']) or \
                          any(str(c.get('display', '')).lower() in ['positive', 'detected'] for c in val_coding if isinstance(c, dict))

        for category, config in CONFIRMED_CODES.items():
            if any(c in config.get('labs', []) for c in codes) and is_positive:
                markers.append(f"{category}_Confirmed")
            if any(c in config.get('dx', []) for c in codes):
                markers.append(f"{category}_Confirmed")
            if 'suspected_labs' in config and any(c in config['suspected_labs'] for c in codes) and is_positive:
                markers.append(f"{category}_Suspected")
            if 'suspected_dx' in config and any(c in config['suspected_dx'] for c in codes):
                markers.append(f"{category}_Suspected")
        return symptoms, markers

    obs_res = obs_df.apply(get_clinical_markers, axis=1)
    obs_df['symptoms'] = obs_res.apply(lambda x: x[0])
    obs_df['markers'] = obs_res.apply(lambda x: x[1])
    
    def is_actual_fever(row):
        if 'Fever' in row['symptoms']:
            if row.get('resourceType') == 'Condition': return True
            val_qty = row.get('valueQuantity')
            if isinstance(val_qty, dict):
                val = val_qty.get('value')
                if val and val > 37.5: return True 
        return False
    
    obs_df['has_fever'] = obs_df.apply(is_actual_fever, axis=1)

    # Helper for ZIP extension
    def get_ext_zip(resource_dict):
        for ext in resource_dict.get('extension', []):
            if ext.get('url') == 'http://example.org/zip':
                return ext.get('valueString')
        return None

    obs_df['zip_code'] = [get_ext_zip(r) for r in observations]
    obs_df['zip_code'] = obs_df.apply(lambda row: row['zip_code'] if pd.notnull(row['zip_code']) else patient_zip_map.get(row['patient_id'], 'Unknown'), axis=1)

    patient_daily = obs_df.groupby(['patient_id', 'date']).agg({
        'symptoms': lambda x: sum(x, []),
        'markers': lambda x: sum(x, []),
        'has_fever': 'any',
        'zip_code': 'first',
        'facility': 'first'
    }).reset_index()

    if not cond_df.empty:
        cond_res = cond_df.apply(get_clinical_markers, axis=1)
        cond_df['symptoms'] = cond_res.apply(lambda x: x[0])
        cond_df['markers'] = cond_res.apply(lambda x: x[1])
        cond_df['has_fever'] = cond_df.apply(is_actual_fever, axis=1)
        cond_df['zip_code'] = [get_ext_zip(r) for r in conditions]
        cond_df['zip_code'] = cond_df.apply(lambda row: row['zip_code'] if pd.notnull(row['zip_code']) else patient_zip_map.get(row['patient_id'], 'Unknown'), axis=1)
        
        patient_daily_cond = cond_df.groupby(['patient_id', 'date']).agg({
            'symptoms': lambda x: sum(x, []),
            'markers': lambda x: sum(x, []),
            'has_fever': 'any',
            'zip_code': 'first'
        }).reset_index()
        
        patient_daily = pd.merge(patient_daily, patient_daily_cond, on=['patient_id', 'date'], how='outer')
        patient_daily['symptoms'] = (patient_daily['symptoms_x'].fillna('').apply(list) + 
                                     patient_daily['symptoms_y'].fillna('').apply(list))
        patient_daily['markers'] = (patient_daily['markers_x'].fillna('').apply(list) + 
                                    patient_daily['markers_y'].fillna('').apply(list))
        patient_daily['has_fever'] = patient_daily['has_fever_x'].fillna(False) | patient_daily['has_fever_y'].fillna(False)
        patient_daily['zip_code'] = patient_daily['zip_code_x'].fillna(patient_daily['zip_code_y'])
        patient_daily['facility'] = patient_daily['facility'].fillna('Unknown')
        
        # Cleanup temporary columns
        patient_daily = patient_daily.drop(columns=[c for c in patient_daily.columns if c.endswith('_x') or c.endswith('_y')])

    def classify(row):
        syms = set(row['symptoms'])
        markers = set(row['markers'])
        fever = row['has_fever']
        
        results = []
        
        # Unified COVID-19 Category (Confirmed + Suspected + Syndromic Like)
        if 'COVID_Confirmed' in markers or 'COVID_Suspected' in markers or (fever and 'Cough' in syms):
            results.append('COVID-19')
            
        # Unified Dengue Category (Confirmed + Syndromic Like)
        if 'Dengue_Confirmed' in markers or (fever and any(s in syms for s in ['Rash', 'JointPain', 'Headache', 'MusclePain'])):
            results.append('Dengue')
            
        # Unified Influenza Category (A + B + Unspec + Syndromic Like)
        if ('Influenza_A_Confirmed' in markers or 'Influenza_B_Confirmed' in markers or 
            'Influenza_Unspec_Confirmed' in markers or 
            (fever and ('Cough' in syms or 'SoreThroat' in syms) and 'MusclePain' in syms)):
            results.append('Influenza')
        
        return results if results else ['Negative']

    patient_daily['classification'] = patient_daily.apply(classify, axis=1)
    
    # 5. Temporal Analysis for each unified scenario
    scenarios = ['COVID-19', 'Dengue', 'Influenza']
    daily_stats = patient_daily.groupby('date').size().reset_index(name='total_visits')
    daily_stats = daily_stats.set_index('date')
    
    for s in scenarios:
        s_counts = patient_daily[patient_daily['classification'].apply(lambda x: s in x)].groupby('date').size()
        daily_stats[s] = s_counts
        daily_stats[s] = daily_stats[s].fillna(0)
        
        # Anomaly Detection (14-day rolling window)
        if daily_stats[s].sum() > 0:
            daily_stats[f'{s}_mean'] = daily_stats[s].shift(1).rolling(window=14).mean()
            daily_stats[f'{s}_std'] = daily_stats[s].shift(1).rolling(window=14).std()
            daily_stats[f'{s}_threshold'] = daily_stats[f'{s}_mean'] + (3 * daily_stats[f'{s}_std'])
            daily_stats[f'{s}_anomaly'] = (daily_stats[s] > daily_stats[f'{s}_threshold']) & (daily_stats[s] > 1)
        else:
            daily_stats[f'{s}_mean'] = 0
            daily_stats[f'{s}_std'] = 0
            daily_stats[f'{s}_threshold'] = 0
            daily_stats[f'{s}_anomaly'] = False

    return daily_stats.reset_index(), patient_daily

def visualize(df):
    plt.figure(figsize=(15, 10))
    scenarios = ['COVID-19', 'Dengue', 'Influenza']
    colors = ['blue', 'orange', 'green']
    
    valid_scenarios = [s for s in scenarios if df[s].sum() > 0]
    if not valid_scenarios: valid_scenarios = scenarios
    
    for i, s in enumerate(valid_scenarios):
        plt.subplot(len(valid_scenarios), 1, i+1)
        plt.plot(df['date'], df[s], label=f'Unified {s} Cases', color=colors[i % len(colors)], marker='o')
        
        if f'{s}_threshold' in df.columns:
            plt.plot(df['date'], df[f'{s}_threshold'], label='Threshold', linestyle='--', color='red')
            anomalies = df[df[f'{s}_anomaly']]
            plt.scatter(anomalies['date'], anomalies[s], color='red', label='Anomaly', zorder=5)
        
        plt.title(f'Unified Temporal Analysis: {s} (Confirmed + Suspected + Syndromic)')
        plt.ylabel('Case Count')
        plt.legend()
        plt.grid(True)

    plt.xlabel('Date')
    plt.tight_layout()
    plt.savefig('outputs/anomaly_visualization.png')
    print("Visualization saved to outputs/anomaly_visualization.png")

def main():
    import os
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
        
    try:
        daily_stats, patient_daily = process_data('exported_data.ndjson')
        if daily_stats.empty:
            print("No data to analyze.")
            return

        print("Analysis complete. Anomaly detection results:")
        for s in ['COVID-19', 'Dengue', 'Influenza']:
            if f'{s}_anomaly' in daily_stats.columns:
                anomalies = daily_stats[daily_stats[f'{s}_anomaly']]
                if not anomalies.empty:
                    print(f"\n🚨 {s} Anomalies Detected (Unified):")
                    print(anomalies[['date', s, f'{s}_threshold']])
                    
                    # Generate eICR for the latest anomaly
                    latest = anomalies.iloc[-1]
                    eicr_bundle = generate_eicr(f"{s} Unified Cluster", int(latest[s]), str(latest['date']))
                    try:
                        report_eicr_to_fhir(eicr_bundle, f"{s} Unified Cluster", str(latest['date']))
                    except Exception as e:
                        print(f"⚠️ Could not report eICR to FHIR server")
        
        visualize(daily_stats)
        daily_stats.to_csv('outputs/syndromic_mapping.csv', index=False, encoding='utf-8')
        patient_daily.to_csv('outputs/patient_classifications.csv', index=False,encoding='utf-8')
        print("Data exported to outputs/syndromic_mapping.csv and outputs/patient_classifications.csv")
    except FileNotFoundError:
        print("Error: exported_data.ndjson not found.")


if __name__ == "__main__":
    main()
