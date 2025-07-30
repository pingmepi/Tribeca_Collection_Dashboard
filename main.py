import streamlit as st
import pandas as pd
from pathlib import Path
import os
import sys
from salesforce.connect import connect_to_salesforce
from salesforce.report import get_salesforce_report
from utils.helper import render_svg
from components.dashboard import render_dashboard
from components.check import check
from utils.helper import get_column


# Page configuration
st.set_page_config(page_title="Tribeca Collection Dashboard", layout="wide", page_icon='assets/logo.webp')


# ------------------ Shared "Today" Input ------------------
st.sidebar.markdown("### 📅 Date Configuration")
today = pd.to_datetime(st.sidebar.date_input(
    "Calculate as of date",
    value=pd.to_datetime("today"),
    key="global_today"
))





# Setup
def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

logo_path = get_base_path() / "assets" / "TribecaLogo.svg"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
render_svg(str(logo_path))

# Initialize session state
if "data" not in st.session_state:
    st.session_state.data = None

# -------------------- SINGLE SOURCE SELECTION (TOP) --------------------
st.sidebar.header("📁 Data Source")

data_source = st.sidebar.radio("Select data source:", ["📡 Salesforce Report", "📄 Upload CSV"])


# Only show one upload/input UI depending on selection
if data_source == "📡 Salesforce Report":
    report_id = st.sidebar.text_input("Enter Salesforce Report ID:", key="report_id")
    if report_id and st.session_state.data is None:
        try:
            with st.spinner("Fetching Salesforce report..."):
                sf = connect_to_salesforce()
                df = get_salesforce_report(sf, report_id)
            if not df.empty:
                st.session_state.data = df
                st.success("✅ Report loaded successfully!")
            else:
                st.warning("⚠️ Report is empty.")
        except Exception as e:
            st.error(f"❌ Failed to load Salesforce report: {e}")

elif data_source == "📄 Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload Main Project File", type=["csv", "xlsx"])
    if uploaded_file and st.session_state.data is None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
            else:
                df = pd.read_excel(uploaded_file)
            st.session_state.data = df
            st.success("✅ File uploaded successfully!")
        except Exception as e:
            st.error(f"❌ Failed to read file: {e}")

# -------------------- TABS SECTION (Use loaded data) --------------------
if st.session_state.data is not None:
    df = st.session_state.data

    st.sidebar.header("🔢 Column Mappings")

    colmap = {
        "booking_col": get_column(df, "Booking Date", "Booking Date"),
        "reg_date_col": get_column(df, "Agreement Registration Date", "Agreement Registration Date"),
        "actual_payment_col": get_column(df, "Actual Payment Date", "Actual Payment Date"),
        "amount_due_col": get_column(df, "Total Amount Due", "Total Amount Due"),
        "payment_received_col": get_column(df, "Payment Received", "Payment Received"),
        "total_agreement_col": get_column(df, "Total Agreement Value", "Total Agreement Value"),
        "budgeted_date_col": get_column(df, "Budgeted Date", "Budgeted Date"),
        "demand_gen_col": get_column(df, "Demand generation date", "Demand Generation Date"),
        "milestone_status_col": get_column(df, "Is Milestone Completed", "Milestone Completion Status"),
        "property_name": get_column(df, "Property Name", "Unit/Property Name"),
        "customer_name": get_column(df, "Customer Name", "Customer Name"),
        "active": get_column(df, "Active", "Active"),
        "application_booking_id": get_column(df, "Application / Booking ID", "Application / Booking ID"),
        "tax": get_column(df, "Total Service Tax On PPD", "Total Service Tax On PPD"),
        "tower": get_column(df, "Tower", "Tower"),
        "type": get_column(df, "Type", "Type"),
        "milestone_name": get_column(df, "Milestone Name", "Milestone Name"),
    }

    st.session_state.column_map = colmap

# ------------------ TABS SECTION ------------------
tab1, tab2 = st.tabs(["Collection Dashboard", "Discrepancies Report"])

with tab1:
    st.title("Collection Dashboard")
    if st.session_state.data is not None:
        render_dashboard(st.session_state.data, today)
    else:
        st.info("ℹ️ Please upload a file or enter a report ID to proceed.")

with tab2:
    st.title("Discrepancies Report")
    if st.session_state.data is not None:
        check(st.session_state.data, today)
    else:
        st.info("ℹ️ Please upload a file or enter a report ID to proceed.")