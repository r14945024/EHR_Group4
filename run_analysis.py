import pandas as pd
import json
import matplotlib.pyplot as plt
from datetime import datetime

def load_ndjson(file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def process_data(file_path):
    # Load NDJSON data
    raw_data = load_ndjson(file_path)
    
    # Let's simulate processing separate resource types
    observations = [r for r in raw_data if r.get('resourceType') == 'Observation']
    obs_df = pd.DataFrame(observations)
    
    # Normalize Dates
    if not obs_df.empty:
        obs_df['date'] = pd.to_datetime(obs_df['effectiveDateTime']).dt.date
        
        # Extract Facility and Zip Code safely
        if 'device' in obs_df.columns:
            obs_df['facility'] = obs_df['device'].apply(lambda x: x.get('display') if isinstance(x, dict) else 'Unknown')
        else:
            obs_df['facility'] = 'Unknown'
            
        if 'extension' in obs_df.columns:
            obs_df['zip_code'] = obs_df['extension'].apply(lambda x: x[0].get('valueString') if isinstance(x, list) and len(x) > 0 else 'Unknown')
        else:
            obs_df['zip_code'] = 'Unknown'
    
    # NSSP Mapping: Identify ILI (Influenza-Like Illness)
    if obs_df.empty:
        return pd.DataFrame(columns=['date', 'total_visits', 'ili_cases', 'is_anomaly', 'facility', 'zip_code'])

    # Filter for ILI symptoms
    ili_obs = obs_df[obs_df['code'].apply(lambda x: any(c['code'] in ['8310-5', '49727002', '162357003'] for c in x['coding']))]
    
    # Temporal Analysis
    daily_counts = obs_df.groupby('date').size().reset_index(name='total_visits')
    ili_counts = ili_obs.groupby('date').size().reset_index(name='ili_cases')
    analysis_df = pd.merge(daily_counts, ili_counts, on='date', how='left').fillna(0)
    
    # Anomaly Detection (14-day rolling window for longer trends)
    analysis_df['rolling_mean'] = analysis_df['ili_cases'].shift(1).rolling(window=14).mean()
    analysis_df['rolling_std'] = analysis_df['ili_cases'].shift(1).rolling(window=14).std()
    analysis_df['threshold'] = analysis_df['rolling_mean'] + (2 * analysis_df['rolling_std'])
    analysis_df['is_anomaly'] = analysis_df['ili_cases'] > analysis_df['threshold']
    
    # Return both temporal and raw ili data for dashboard
    return analysis_df, ili_obs

def visualize(df):
    plt.figure(figsize=(12, 6))
    plt.plot(df['date'], df['ili_cases'], label='ILI Cases', marker='o')
    plt.plot(df['date'], df['threshold'], label='Anomaly Threshold (2 SD)', linestyle='--', color='red')
    
    anomalies = df[df['is_anomaly']]
    plt.scatter(anomalies['date'], anomalies['ili_cases'], color='red', label='Outbreak Detected', zorder=5)
    
    plt.title('Syndromic Surveillance: ILI Temporal Analysis')
    plt.xlabel('Date')
    plt.ylabel('Case Count')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('outputs/anomaly_visualization.png')
    print("Visualization saved to outputs/anomaly_visualization.png")

from generate_eicr import generate_eicr
from report_eicr_to_fhir import report_eicr_to_fhir

def main():
    import os
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
        
    try:
        # In a real workflow, this file comes from Step 3
        analysis_df, ili_obs = process_data('exported_data.ndjson')
        print("Analysis complete. Anomaly detection results:")
        
        anomalies = analysis_df[analysis_df['is_anomaly']]
        print(anomalies)
        
        # Automatically generate eICR and persist audit trail for the latest anomaly
        if not anomalies.empty:
            latest = anomalies.iloc[-1]
            eicr_bundle = generate_eicr("ILI (Respiratory Cluster)", int(latest['ili_cases']), str(latest['date']))
            # Persistent Audit Trail (Fulfills Page 19 Requirement)
            report_eicr_to_fhir(eicr_bundle, "ILI (Respiratory Cluster)", str(latest['date']))
        
        visualize(analysis_df)
        analysis_df.to_csv('outputs/syndromic_mapping.csv', index=False)
        ili_obs.to_csv('outputs/geographic_hotspots.csv', index=False)
        print("Data exported to outputs/syndromic_mapping.csv and outputs/geographic_hotspots.csv")
    except FileNotFoundError:
        print("Error: exported_data.ndjson not found. Please run Step 3 or live_export.py first.")

if __name__ == "__main__":
    main()
