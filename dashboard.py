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
    hotspots_df = pd.read_csv('outputs/geographic_hotspots.csv')
    return analysis_df, hotspots_df

analysis_df, hotspots_df = load_data()

if analysis_df is None:
    st.error("Data not found. Please run `python run_analysis.py` first.")
else:
    # Sidebar Filters
    st.sidebar.header("Filters")
    min_date = pd.to_datetime(analysis_df['date']).min()
    max_date = pd.to_datetime(analysis_df['date']).max()
    
    date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])

    # Filter Data based on selection
    if len(date_range) == 2:
        start_date, end_date = date_range
        analysis_df = analysis_df[(pd.to_datetime(analysis_df['date']).dt.date >= start_date) & 
                                  (pd.to_datetime(analysis_df['date']).dt.date <= end_date)]
        hotspots_df = hotspots_df[(pd.to_datetime(hotspots_df['date']).dt.date >= start_date) & 
                                  (pd.to_datetime(hotspots_df['date']).dt.date <= end_date)]

    # Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📈 Temporal Analysis (ILI Syndrome)")
        fig = px.line(analysis_df, x='date', y=['ili_cases', 'threshold'], 
                     title="Daily ILI Cases vs. Anomaly Threshold",
                     labels={'value': 'Case Count', 'date': 'Date'},
                     color_discrete_map={'ili_cases': '#007BFF', 'threshold': '#FF4B4B'})
        
        # Highlight Anomalies
        anomalies = analysis_df[analysis_df['is_anomaly']]
        fig.add_scatter(x=anomalies['date'], y=anomalies['ili_cases'], 
                        mode='markers', marker=dict(color='red', size=10),
                        name='Outbreak Detected')
        
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🚨 Active Alerts")
        recent_anomalies = anomalies.sort_values(by='date', ascending=False)
        if not recent_anomalies.empty:
            for _, row in recent_anomalies.head(3).iterrows():
                st.error(f"**OUTBREAK DETECTED** on {row['date']}! Count: {row['ili_cases']}")
        else:
            st.success("No active anomalies detected.")

    st.divider()

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📍 Geographic Hotspots (by Zip Code)")
        zip_counts = hotspots_df['zip_code'].value_counts().reset_index()
        zip_counts.columns = ['zip_code', 'count']
        fig_zip = px.bar(zip_counts, x='zip_code', y='count', 
                        title="ILI Cases by Patient Zip Code",
                        color='count', color_continuous_scale='Reds')
        st.plotly_chart(fig_zip, use_container_width=True)

    with col4:
        st.subheader("🏢 Facility Load (Syndromic Distribution)")
        facility_counts = hotspots_df['facility'].value_counts().reset_index()
        facility_counts.columns = ['facility', 'count']
        fig_facility = px.pie(facility_counts, values='count', names='facility', 
                             title="Cases by Facility ID",
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_facility, use_container_width=True)

    st.markdown("---")
    st.info("💡 **Technical Note:** This dashboard extracts data from Bulk FHIR NDJSON exports and applies NSSP statistical thresholds (2 SD) for real-time surveillance.")
