import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils.helper import to_cr


def render_monthly_trend(trend_df):
    """Render grouped double bar chart for expected vs actual collections"""
    st.subheader("📈 Monthly Collection Trend (Last 24 Months)")

    # Convert to Cr for display
    display_df = trend_df.copy()
    for col in ['Expected', 'Actuals', 'Misses']:
        display_df[f'{col}_Cr'] = display_df[col].apply(to_cr)

    display_df['Month_str'] = display_df.index.strftime('%b %Y')

    # Create grouped double bar chart for Expected vs Actuals
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Expected',
        x=display_df['Month_str'],
        y=display_df['Expected_Cr'],
        marker_color='#1f77b4'
    ))

    fig.add_trace(go.Bar(
        name='Actuals',
        x=display_df['Month_str'],
        y=display_df['Actuals_Cr'],
        marker_color='#2E8B57'
    ))

    fig.update_layout(
        title="Expected vs Actual Collections",
        xaxis_title="Month",
        yaxis_title="Amount (₹ Cr)",
        barmode='group',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # Expandable table
    with st.expander("📋 View Detailed Monthly Data"):
        table_df = display_df[['Expected_Cr', 'Actuals_Cr', 'Misses_Cr']].copy()
        table_df.columns = ['Expected (₹ Cr)', 'Actuals (₹ Cr)', 'Misses (₹ Cr)']
        st.dataframe(table_df, use_container_width=True)

        # Download button
        csv = table_df.to_csv()
        st.download_button(
            label="📥 Download Monthly Trend Data",
            data=csv,
            file_name="monthly_trend.csv",
            mime="text/csv"
        )

