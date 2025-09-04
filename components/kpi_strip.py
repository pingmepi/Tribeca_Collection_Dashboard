import streamlit as st
from utils.types import KPIMetrics


def render_kpi_strip(kpis: KPIMetrics):
    """Render the 7-metric KPI header strip"""
    st.markdown("### 📊 Key Performance Indicators")

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    with col1:
        st.metric(
            label="Total Units",
            value=f"{kpis.total_units:,}",
            help="Total number of unique booking IDs in the system"
        )

    with col2:
        st.metric(
            label="Value of Units",
            value=f"₹{kpis.value_of_units_cr:.2f} Cr",
            help="Agreement Value + Corpus/Maintenance across all bookings"
        )

    with col3:
        st.metric(
            label="Total Units Sold",
            value=f"{kpis.total_units_sold:,}",
            help="Number of distinct booking IDs (same as Total Units)"
        )

    with col4:
        st.metric(
            label="Total Demand Generated",
            value=f"₹{kpis.total_demand_generated_cr:.2f} Cr",
            help="Sum of dues where Demand Generation Date < today"
        )

    with col5:
        st.metric(
            label="Total Collection",
            value=f"₹{kpis.total_collection_cr:.2f} Cr",
            help="Sum of Net Payment Received (Payment - Tax) per booking"
        )

    with col6:
        st.metric(
            label="Units Registered",
            value=f"{kpis.units_registered:,}",
            help="Bookings with Agreement Registration Date filled"
        )

    with col7:
        st.metric(
            label="Units Unregistered",
            value=f"{kpis.units_unregistered:,}",
            help="Bookings without Agreement Registration Date"
        )

    st.divider()

