import pandas as pd
import streamlit as st
import base64
import streamlit as st

def add_discrepancy_block(title, df_block):
    if not df_block.empty:
        # Insert a header row (all columns blank except first with the title)
        header_row = pd.DataFrame([["⚠️ " + title] + [""] * (df_block.shape[1] - 1)], columns=df_block.columns)
        return pd.concat([header_row, df_block], ignore_index=True)
    else:
        return pd.DataFrame(columns=df_block.columns)

def get_column(df, default_col, label, key_prefix="shared"):
    """
    Returns a column from df.
    - If default_col is found, return it directly.
    - Else, show a selectbox to the user in the sidebar.
    - Uses session_state to avoid duplicate widgets.
    """
    session_key = f"{key_prefix}_{label}".replace(" ", "_")

    if default_col in df.columns:
        # Save it once to session state
        st.session_state[session_key] = default_col
        return default_col
    else:
        if session_key not in st.session_state:
            st.sidebar.warning(f"⚠️ `{default_col}` not found. Please select column for: {label}")
            st.session_state[session_key] = st.sidebar.selectbox(
                f"Select {label}",
                df.columns,
                key=session_key
            )
        return st.session_state[session_key]
def bucket(days):
    if pd.isna(days): return '> 90 Days'
    if days < 30: return '< 30 Days'
    elif days < 61: return '31 - 60 Days'
    elif days < 91: return '61 - 90 Days'
    else: return '> 90 Days'

def percent(val, total):
    val_cr = val / 1e7
    percent = (val / total * 100) if total else 0
    return f"₹ {val_cr:,.2f} Cr ({percent:.1f}%)"

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