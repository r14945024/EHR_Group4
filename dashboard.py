import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="FHIR Syndromic Surveillance Dashboard", layout="wide")

st.title("🏥 FHIR-Driven Syndromic Surveillance Dashboard")
st.markdown("### Population Health Monitoring & Outbreak Detection (Group 4)")

# Load Data
@st.cache_data
def load_data():
    if not os.path.exists('outputs/syndromic_mapping.csv'):
        return None, None
    analysis_df = pd.read_csv('outputs/syndromic_mapping.csv')
    patient_df = pd.read_csv('outputs/patient_classifications.csv')
    return analysis_df, patient_df

analysis_df, patient_df = load_data()

if analysis_df is None:
    st.error("Data not found. Please run `python run_analysis.py` first.")
else:
    # Sidebar Filters
    st.sidebar.header("Filters")
    
    # Scenario Selection
    scenarios = ['COVID-like', 'Dengue-like', 'Flu-like']
    selected_scenario = st.sidebar.selectbox("Select Syndrome Scenario", scenarios)
    
    # Date Filter
    analysis_df['date'] = pd.to_datetime(analysis_df['date'])
    patient_df['date'] = pd.to_datetime(patient_df['date'])
    
    min_date = analysis_df['date'].min()
    max_date = analysis_df['date'].max()
    
    date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])

    # Filter Data based on selection
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_analysis = analysis_df[(analysis_df['date'].dt.date >= start_date) & 
                                        (analysis_df['date'].dt.date <= end_date)]
        filtered_patients = patient_df[(patient_df['date'].dt.date >= start_date) & 
                                       (patient_df['date'].dt.date <= end_date)]
    else:
        filtered_analysis = analysis_df
        filtered_patients = patient_df

    # Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"📈 Temporal Analysis: Actual {selected_scenario} Case Counts")
        
        # Plotting actual cases and the anomaly threshold
        # We use absolute counts to give the user a direct sense of the population burden
        fig = px.line(filtered_analysis, x='date', y=selected_scenario, 
                     title=f"Daily Observed {selected_scenario} Cases",
                     labels={selected_scenario: 'Number of Patients', 'date': 'Date'},
                     line_shape='hv') # Step-like line for count data
        
        # Add the Anomaly Threshold as a faint reference line
        fig.add_scatter(x=filtered_analysis['date'], y=filtered_analysis[f'{selected_scenario}_threshold'], 
                        name='Statistical Threshold (3 SD)', 
                        line=dict(color='rgba(255, 75, 75, 0.5)', dash='dash'),
                        fill='tonexty', fillcolor='rgba(255, 75, 75, 0.1)') # Highlight area above baseline

        # Highlight Anomalies with distinct markers
        anomalies = filtered_analysis[filtered_analysis[f'{selected_scenario}_anomaly']]
        if not anomalies.empty:
            fig.add_scatter(x=anomalies['date'], y=anomalies[selected_scenario], 
                            mode='markers', marker=dict(color='#FF4B4B', size=12, symbol='star'),
                            name='Alert: Outbreak Detected')
        
        fig.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🚨 Active Alerts")
        all_anomalies = []
        for s in scenarios:
            s_anom = analysis_df[analysis_df[f'{s}_anomaly']].copy()
            s_anom['scenario'] = s
            all_anomalies.append(s_anom)
        
        recent_anomalies = pd.concat(all_anomalies).sort_values(by='date', ascending=False)
        
        if not recent_anomalies.empty:
            for _, row in recent_anomalies.head(5).iterrows():
                st.error(f"**{row['scenario']} OUTBREAK** on {row['date'].date()}! Count: {row[row['scenario']]}")
        else:
            st.success("No active anomalies detected.")

    st.divider()

    col3, col4 = st.columns(2)

    # Filter patients for selected scenario
    scenario_patients = filtered_patients[filtered_patients['classification'].apply(lambda x: selected_scenario in x)]

    with col3:
        st.subheader(f"📍 Geographic Hotspots ({selected_scenario})")
        if not scenario_patients.empty:
            zip_counts = scenario_patients['zip_code'].value_counts().reset_index()
            zip_counts.columns = ['zip_code', 'count']
            fig_zip = px.bar(zip_counts, x='zip_code', y='count', 
                            title=f"{selected_scenario} Cases by Patient Zip Code",
                            color='count', color_continuous_scale='Reds')
            st.plotly_chart(fig_zip, use_container_width=True)
        else:
            st.write("No cases for selected scenario in this period.")

    with col4:
        st.subheader("🏢 Facility Load (Syndromic Distribution)")
        if not scenario_patients.empty:
            facility_counts = scenario_patients['facility'].value_counts().reset_index()
            facility_counts.columns = ['facility', 'count']
            fig_facility = px.pie(facility_counts, values='count', names='facility', 
                                 title=f"{selected_scenario} Cases by Facility ID",
                                 hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_facility, use_container_width=True)
        else:
            st.write("No cases for selected scenario in this period.")

    st.markdown("---")
    st.info(f"💡 **Technical Note:** This dashboard extracts data from FHIR resources and applies CDC/TW Core criteria for {selected_scenario} classification. Anomaly detection uses a 14-day rolling 3-SD threshold.")
