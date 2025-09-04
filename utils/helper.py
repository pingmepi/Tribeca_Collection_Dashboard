import pandas as pd
import streamlit as st
import base64


def add_discrepancy_block(title, df_block):
    if not df_block.empty:
        # Insert a header row (all columns blank except first with the title)
        header_row = pd.DataFrame([["⚠️ " + title] + [""] * (df_block.shape[1] - 1)], columns=df_block.columns)
        return pd.concat([header_row, df_block], ignore_index=True)
    else:
        return pd.DataFrame(columns=df_block.columns)


def get_column(df, *candidates, label="", key_prefix="shared"):
    """
    Enhanced column resolver with multiple candidates.
    Returns the first column name that exists in df from candidates.
    If none found, prompts user to select via sidebar selectbox.
    """
    session_key = f"{key_prefix}_{label}".replace(" ", "_")

    # Find first existing column
    for candidate in candidates:
        if candidate and candidate in df.columns:
            st.session_state[session_key] = candidate
            return candidate

    # If none found, show selectbox
    if session_key not in st.session_state:
        missing_list = ", ".join([c for c in candidates if c]) or "<none>"
        st.sidebar.warning(f"⚠️ None of [{missing_list}] found. Please select column for: {label}")
        st.session_state[session_key] = st.sidebar.selectbox(
            f"Select {label}",
            df.columns,
            key=session_key
        )
    return st.session_state[session_key]


def to_cr(amount):
    """Convert amount to crores"""
    if amount is None or (isinstance(amount, float) and pd.isna(amount)):
        return 0.0
    return float(amount) / 1e7


def fmt_inr(amount):
    """Format amount in INR"""
    if amount is None or (isinstance(amount, float) and pd.isna(amount)):
        amount = 0.0
    return f"₹{float(amount):,.2f}"


def _to_numeric_inr(series):
    """Convert INR formatted series to numeric"""
    return pd.to_numeric(series.astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')


def bucket(days):
    """Age bucketing function"""
    if pd.isna(days): return '> 90 Days'
    if days < 30: return '< 30 Days'
    elif days < 61: return '31 - 60 Days'
    elif days < 91: return '61 - 90 Days'
    else: return '> 90 Days'


def percent(val, total):
    """Format percentage with INR"""
    val_cr = (val or 0) / 1e7
    pct = ((val or 0) / total * 100) if total else 0
    return f"₹ {val_cr:,.2f} Cr ({pct:.1f}%)"


def render_svg(svg_path):
    with open(svg_path, "r") as f:
        svg_data = f.read()
    b64 = base64.b64encode(svg_data.encode()).decode()
    html = f"""
    <div style="text-align:center; padding: 10px;">
        <img src='data:image/svg+xml;base64,{b64}' style='width:400px; height:auto;'>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def highlight_rows(row):
    color_map = {
        "Total Agreement Value": '#d1e7dd',  # Light green
        "Corpus+Maintenance": '#d1e7dd',
        "Total Agreement Value (Added Corpus+Maintenance)": '#cfe2ff',  # Light blue
        "Total Agreement Value (Sum of All Dues)": '#cfe2ff',
        "Total Demand Till Date": '#fff3cd',  # Light yellow
        "Expected Future Demand": '#fff3cd',
        "Budgeted Passed, Demand Not Raised": '#fff3cd',
        "Amount Collected (Without TAX)": '#f8d7da',  # Light red/pink
        "Amount Overdue": "#d3a2f0"
    }

    row_name = row['Metric']
    color = color_map.get(row_name, '')  # Default: no color
    return ['background-color: {}'.format(color) if color else '' for _ in row]