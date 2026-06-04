import os
import pandas as pd
import streamlit as st
import plotly.express as px

# =====================================================
# Page Config
# =====================================================
st.set_page_config(
    page_title="FHIR Syndromic Surveillance Dashboard",
    layout="wide"
)

st.title("🏥 FHIR-Driven Syndromic Surveillance Dashboard")
st.markdown("### Population Health Monitoring & Outbreak Detection (Group 4)")


# =====================================================
# Load Data
# =====================================================
@st.cache_data
def load_data():

    mapping_path = "outputs/syndromic_mapping.csv"
    patient_path = "outputs/patient_classifications.csv"

    if not os.path.exists(mapping_path):
        return None, None

    if not os.path.exists(patient_path):
        return None, None

    analysis_df = pd.read_csv(mapping_path)
    patient_df = pd.read_csv(patient_path)

    return analysis_df, patient_df


analysis_df, patient_df = load_data()

if analysis_df is None or patient_df is None:
    st.error(
        "Required files not found.\n\n"
        "Please run your analysis pipeline first."
    )
    st.stop()

# =====================================================
# Date Processing
# =====================================================
analysis_df["date"] = pd.to_datetime(
    analysis_df["date"],
    errors="coerce"
)

patient_df["date"] = pd.to_datetime(
    patient_df["date"],
    errors="coerce"
)

analysis_df = analysis_df.dropna(subset=["date"])
patient_df = patient_df.dropna(subset=["date"])

# =====================================================
# Sidebar
# =====================================================
st.sidebar.header("Filters")

exclude_cols = [
    "date",
    "total_visits"
]

scenarios = [
    c for c in analysis_df.columns
    if (
        not c.endswith("_threshold")
        and not c.endswith("_mean")
        and not c.endswith("_std")
        and not c.endswith("_anomaly")
        and c not in exclude_cols
    )
]


def sort_scenarios(s):

    s_lower = s.lower()

    if "confirmed" in s_lower:
        return (0, s)

    if "suspected" in s_lower:
        return (1, s)

    return (2, s)


scenarios = sorted(scenarios, key=sort_scenarios)

if len(scenarios) == 0:
    st.error("No clinical scenarios found.")
    st.stop()

selected_scenario = st.sidebar.selectbox(
    "Select Clinical Scenario",
    scenarios
)

# =====================================================
# Date Range Filter
# =====================================================
min_date = analysis_df["date"].min().date()
max_date = analysis_df["date"].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date)
)

if len(date_range) == 2:

    start_date = pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[1])

    filtered_analysis = analysis_df[
        (analysis_df["date"] >= start_date)
        &
        (analysis_df["date"] <= end_date)
    ]

    filtered_patients = patient_df[
        (patient_df["date"] >= start_date)
        &
        (patient_df["date"] <= end_date)
    ]

else:
    filtered_analysis = analysis_df.copy()
    filtered_patients = patient_df.copy()

# =====================================================
# Main Layout
# =====================================================
col1, col2 = st.columns([2, 1])

# =====================================================
# Temporal Trend
# =====================================================
with col1:

    st.subheader(
        f"📈 Temporal Analysis: {selected_scenario}"
    )

    fig = px.line(
        filtered_analysis,
        x="date",
        y=selected_scenario,
        title=f"Daily Observed {selected_scenario} Cases",
        labels={
            selected_scenario: "Number of Patients",
            "date": "Date"
        },
        line_shape="hv"
    )

    threshold_col = f"{selected_scenario}_threshold"

    if threshold_col in filtered_analysis.columns:

        fig.add_scatter(
            x=filtered_analysis["date"],
            y=filtered_analysis[threshold_col],
            name="Threshold (3 SD)",
            line=dict(
                color="rgba(255,75,75,0.5)",
                dash="dash"
            )
        )

    anomaly_col = f"{selected_scenario}_anomaly"

    if anomaly_col in filtered_analysis.columns:

        anomalies = filtered_analysis[
            filtered_analysis[anomaly_col]
        ]

        if not anomalies.empty:

            fig.add_scatter(
                x=anomalies["date"],
                y=anomalies[selected_scenario],
                mode="markers",
                marker=dict(
                    color="#FF4B4B",
                    size=12,
                    symbol="star"
                ),
                name="Alert"
            )

    fig.update_layout(
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# Alerts
# =====================================================
with col2:

    st.subheader("🚨 Active Alerts")

    all_anomalies = []

    for scenario in scenarios:

        anomaly_col = f"{scenario}_anomaly"

        if anomaly_col not in analysis_df.columns:
            continue

        tmp = analysis_df[
            analysis_df[anomaly_col]
        ].copy()

        if len(tmp):

            tmp["scenario"] = scenario
            all_anomalies.append(tmp)

    if len(all_anomalies):

        recent_anomalies = pd.concat(
            all_anomalies,
            ignore_index=True
        )

        recent_anomalies = recent_anomalies.sort_values(
            "date",
            ascending=False
        )

        for _, row in recent_anomalies.head(5).iterrows():

            st.error(
                f"{row['scenario']} outbreak "
                f"({row['date'].date()})"
            )

    else:
        st.success("No active anomalies detected.")

# =====================================================
# Scenario Patient Filter
# =====================================================
if "classification" in filtered_patients.columns:

    scenario_patients = filtered_patients[
        filtered_patients["classification"]
        .fillna("")
        .astype(str)
        .str.contains(
            selected_scenario,
            case=False,
            na=False
        )
    ]

else:
    scenario_patients = pd.DataFrame()

# =====================================================
# Geographic Hotspots
# =====================================================
st.divider()

geo_container = st.container()

with geo_container:

    st.subheader(
        f"📍 Geographic Hotspots ({selected_scenario})"
    )

    if (
        not scenario_patients.empty
        and "zip_code" in scenario_patients.columns
    ):

        zip_counts = (
            scenario_patients["zip_code"]
            .value_counts()
            .reset_index()
        )

        zip_counts.columns = [
            "zip_code",
            "count"
        ]

        fig_zip = px.bar(
            zip_counts,
            x="zip_code",
            y="count",
            color="count",
            title=f"{selected_scenario} Cases by ZIP Code"
        )

        st.plotly_chart(
            fig_zip,
            use_container_width=True
        )

    else:
        st.info("No geographic data available.")

# =====================================================
# Facility Distribution
# =====================================================
facility_container = st.container()

with facility_container:

    st.subheader(
        "🏢 Facility Load (Syndromic Distribution)"
    )

    if (
        not scenario_patients.empty
        and "facility" in scenario_patients.columns
    ):

        facility_counts = (
            scenario_patients["facility"]
            .value_counts()
            .reset_index()
        )

        facility_counts.columns = [
            "facility",
            "count"
        ]

        fig_facility = px.pie(
            facility_counts,
            values="count",
            names="facility",
            hole=0.4,
            title=f"{selected_scenario} Cases by Facility"
        )

        st.plotly_chart(
            fig_facility,
            use_container_width=True
        )

    else:
        st.info("No facility data available.")

# =====================================================
# Footer
# =====================================================
st.markdown("---")

st.info(
    f"""
    Technical Note:
    
    This dashboard extracts data from FHIR resources and applies
    CDC/TW Core syndromic classification criteria for
    {selected_scenario}.
    
    Outbreak detection uses a rolling 14-day mean + 3 SD threshold.
    """
)
