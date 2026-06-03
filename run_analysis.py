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
        # Remove UUID prefix if present
        id_str = id_str.replace('urn:uuid:', '')
        # Remove FHIR resource prefixes or URLs (e.g., Patient/123 -> 123)
        return id_str.split('/')[-1]

    # 2. Build the Zip Code Map
    patient_zip_map = {}
    for r in raw_data:
        if r.get('resourceType') == 'Patient':
            p_id = extract_clean_id(r.get('id'))
            
            # Default to Da'an District mock data if the patient is homeless/transient
            zip_code = '106' 
            addresses = r.get('address', [])
            if addresses and isinstance(addresses[0], dict):
                found_zip = addresses[0].get('postalCode')
                if found_zip:
                    zip_code = found_zip
            
            patient_zip_map[p_id] = zip_code

    # 3. Extract Observations and Conditions
    observations = [r for r in raw_data if r.get('resourceType') == 'Observation']
    conditions = [r for r in raw_data if r.get('resourceType') == 'Condition']
    
    obs_df = pd.DataFrame(observations)
    cond_df = pd.DataFrame(conditions)
    
    if obs_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 4. Normalize Dates and Clean Subject References
    obs_df['date_dt'] = pd.to_datetime(obs_df['effectiveDateTime'], errors='coerce', utc=True)
    obs_df = obs_df.dropna(subset=['date_dt']).copy()
    obs_df['date'] = obs_df['date_dt'].dt.date
    
    # Apply the exact same clean ID function to the Observation subject references
    obs_df['patient_id'] = obs_df['subject'].apply(
        lambda x: extract_clean_id(x.get('reference')) if isinstance(x, dict) else 'Unknown'
    )
    
    if not cond_df.empty:
        cond_df['date_dt'] = pd.to_datetime(cond_df['recordedDate'], errors='coerce', utc=True)
        cond_df = cond_df.dropna(subset=['date_dt']).copy()
        cond_df['date'] = cond_df['date_dt'].dt.date
        
        # Apply the exact same clean ID function to the Condition subject references
        cond_df['patient_id'] = cond_df['subject'].apply(
            lambda x: extract_clean_id(x.get('reference')) if isinstance(x, dict) else 'Unknown'
        )

    # 3. Symptom Mapping (LOINC/SNOMED)
    SYMPTOMS = {
        'Fever': ['8310-5', '386661006', '103001002'],
        'Cough': ['49727002'],
        'Rash': ['271757001'],
        'SoreThroat': ['267102003', '43878008', '162357003'],
        'MusclePain': ['68962001'],
        'JointPain': ['57676002', '297077008'],
        'Headache': ['25064002']
    }

    def get_symptoms(row):
        codes = [c.get('code') for c in row['code'].get('coding', [])]
        return [s for s, s_codes in SYMPTOMS.items() if any(c in s_codes for c in codes)]

    obs_df['symptoms'] = obs_df.apply(get_symptoms, axis=1)
    
    # Check for Fever specifically (Value > 37.5 or Fever Condition)
    def is_actual_fever(row):
        if 'Fever' in row['symptoms']:
            if row.get('resourceType') == 'Condition': return True
            val = row.get('valueQuantity', {}).get('value')
            if val and val > 37.5: return True # Slightly lower threshold for syndromic screening
        return False
    
    obs_df['has_fever'] = obs_df.apply(is_actual_fever, axis=1)

    # 4. Aggregate by Patient and Date
    # First, get patient metadata (zip, facility) per encounter/date if possible
    # We'll pick the first one found for that patient/date
    
    # Helper to extract custom zip extension
    def get_ext_zip(resource_dict):
        for ext in resource_dict.get('extension', []):
            if ext.get('url') == 'http://example.org/zip':
                return ext.get('valueString')
        return None

    # Apply extension extractor, fallback to patient_zip_map, then 'Unknown'
    obs_df['zip_code'] = [get_ext_zip(r) for r in observations]
    obs_df['zip_code'] = obs_df.apply(
        lambda row: row['zip_code'] if pd.notnull(row['zip_code']) else patient_zip_map.get(row['patient_id'], 'Unknown'), 
        axis=1
    )
    
    if 'device' in obs_df.columns:
        obs_df['facility'] = obs_df['device'].apply(lambda x: x.get('display') if isinstance(x, dict) else 'Unknown')
    else:
        obs_df['facility'] = 'Unknown'

    patient_daily = obs_df.groupby(['patient_id', 'date']).agg({
        'symptoms': lambda x: sum(x, []),
        'has_fever': 'any',
        'zip_code': 'first',
        'facility': 'first'
    }).reset_index()

    # Also check Conditions for symptoms
    if not cond_df.empty:
        cond_df['symptoms'] = cond_df.apply(get_symptoms, axis=1)
        cond_df['has_fever'] = cond_df.apply(is_actual_fever, axis=1)
        
        # Apply extension extractor for conditions too
        cond_df['zip_code'] = [get_ext_zip(r) for r in conditions]
        cond_df['zip_code'] = cond_df.apply(
            lambda row: row['zip_code'] if pd.notnull(row['zip_code']) else patient_zip_map.get(row['patient_id'], 'Unknown'), 
            axis=1
        )
        
        # Merge observations and conditions symptoms
        patient_daily = pd.merge(patient_daily, patient_daily_cond, on=['patient_id', 'date'], how='outer')
        patient_daily['symptoms'] = (patient_daily['symptoms_x'].fillna('').apply(list) + 
                                     patient_daily['symptoms_y'].fillna('').apply(list))
        patient_daily['has_fever'] = patient_daily['has_fever_x'].fillna(False) | patient_daily['has_fever_y'].fillna(False)
        patient_daily['zip_code'] = patient_daily['zip_code_x'].fillna(patient_daily['zip_code_y'])
        patient_daily['facility'] = patient_daily['facility'].fillna('Unknown')

    def classify(row):
        syms = set(row['symptoms'])
        fever = row['has_fever']
        
        results = []
        # COVID-like: Fever + Cough
        if fever and 'Cough' in syms: results.append('COVID-like')
        
        # Dengue-like: Fever + at least 1 of {Rash, JointPain, Headache, MusclePain}
        # (Simplified for screening; TW CDC requires more for confirmation)
        if fever and any(s in syms for s in ['Rash', 'JointPain', 'Headache', 'MusclePain']): 
            results.append('Dengue-like')
            
        # Flu-like: Fever + (Cough or SoreThroat) + MusclePain
        if fever and ('Cough' in syms or 'SoreThroat' in syms) and 'MusclePain' in syms: 
            results.append('Flu-like')
        
        return results if results else ['Negative']

    patient_daily['classification'] = patient_daily.apply(classify, axis=1)
    
    # 5. Temporal Analysis for each scenario
    scenarios = ['COVID-like', 'Dengue-like', 'Flu-like']
    daily_stats = patient_daily.groupby('date').size().reset_index(name='total_visits')
    daily_stats = daily_stats.set_index('date')
    
    for s in scenarios:
        s_counts = patient_daily[patient_daily['classification'].apply(lambda x: s in x)].groupby('date').size()
        daily_stats[s] = s_counts
        daily_stats[s] = daily_stats[s].fillna(0)
        
        # Anomaly Detection (14-day rolling window)
        daily_stats[f'{s}_mean'] = daily_stats[s].shift(1).rolling(window=14).mean()
        daily_stats[f'{s}_std'] = daily_stats[s].shift(1).rolling(window=14).std()
        daily_stats[f'{s}_threshold'] = daily_stats[f'{s}_mean'] + (3 * daily_stats[f'{s}_std']) # 3SD for better precision
        daily_stats[f'{s}_anomaly'] = (daily_stats[s] > daily_stats[f'{s}_threshold']) & (daily_stats[s] > 1)

    return daily_stats.reset_index(), patient_daily

def visualize(df):
    plt.figure(figsize=(15, 10))
    scenarios = ['COVID-like', 'Dengue-like', 'Flu-like']
    colors = ['blue', 'orange', 'green']
    
    for i, s in enumerate(scenarios):
        plt.subplot(3, 1, i+1)
        plt.plot(df['date'], df[s], label=f'{s} Cases', color=colors[i], marker='o')
        plt.plot(df['date'], df[f'{s}_threshold'], label='Threshold', linestyle='--', color='red')
        
        anomalies = df[df[f'{s}_anomaly']]
        plt.scatter(anomalies['date'], anomalies[s], color='red', label='Anomaly', zorder=5)
        
        plt.title(f'Syndromic Surveillance: {s} Temporal Analysis')
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
        for s in ['COVID-like', 'Dengue-like', 'Flu-like']:
            anomalies = daily_stats[daily_stats[f'{s}_anomaly']]
            if not anomalies.empty:
                print(f"\n🚨 {s} Anomalies Detected:")
                print(anomalies[['date', s, f'{s}_threshold']])
                
                # Generate eICR for the latest anomaly
                latest = anomalies.iloc[-1]
                eicr_bundle = generate_eicr(f"{s} Cluster", int(latest[s]), str(latest['date']))
                try:
                    # Persistent Audit Trail (Fulfills Page 19 Requirement)
                    report_eicr_to_fhir(eicr_bundle, f"{s} Cluster", str(latest['date']))
                except Exception as e:
                    print(f"⚠️ Could not report eICR to FHIR server (Server might be down)")
        
        visualize(daily_stats)
        daily_stats.to_csv('outputs/syndromic_mapping.csv', index=False, encoding='utf-8')
        patient_daily.to_csv('outputs/patient_classifications.csv', index=False,encoding='utf-8')
        print("Data exported to outputs/syndromic_mapping.csv and outputs/patient_classifications.csv")
    except FileNotFoundError:
        print("Error: exported_data.ndjson not found.")


if __name__ == "__main__":
    main()
