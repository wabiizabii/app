# ui/log_viewer_section.py
import streamlit as st
import pandas as pd
from datetime import datetime, date

# NEW: Import SupabaseHandler and instantiate it
from core.supabase_handler import SupabaseHandler

@st.cache_resource
def get_db_handler():
    return SupabaseHandler()

db_handler = get_db_handler()

# Helper function to convert date columns to datetime objects
def convert_date_columns(df: pd.DataFrame, columns: list):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def render_log_viewer_section(db_handler):
    st.header("📋 Trade Log Viewer")
    st.write("Review and analyze your planned trade logs.")

    # Load all planned trade logs
    df_logs_viewer = db_handler.load_all_planned_trade_logs()

    if df_logs_viewer.empty:
        st.info("No planned trade logs available. Please plan some trades first!")
        return

    # Convert date columns for proper filtering and display
    df_logs_viewer = convert_date_columns(df_logs_viewer, ['Timestamp', 'PlannedDate', 'Time_Deal_Planned'])

    # Get unique portfolios for filtering
    unique_portfolio_ids = df_logs_viewer['PortfolioID'].unique().tolist()
    
    # Get portfolio names to display in the selectbox
    # Assuming PortfolioID is sufficient or you can load portfolio names from db_handler.load_portfolios()
    # For now, let's just use the ID or a placeholder if name isn't directly in logs
    portfolio_options = ["All Portfolios"] + sorted(unique_portfolio_ids)

    selected_portfolio_id = st.selectbox(
        "Select Portfolio to View Logs:",
        options=portfolio_options,
        key="log_viewer_portfolio_select"
    )

    filtered_logs = df_logs_viewer.copy()
    if selected_portfolio_id != "All Portfolios":
        filtered_logs = filtered_logs[filtered_logs['PortfolioID'] == selected_portfolio_id]

    if filtered_logs.empty:
        st.info(f"No planned trade logs found for {selected_portfolio_id}.")
        return

    # Date range filter
    min_date = filtered_logs['Timestamp'].min().date() if not filtered_logs['Timestamp'].isna().all() else date.today()
    max_date = filtered_logs['Timestamp'].max().date() if not filtered_logs['Timestamp'].isna().all() else date.today()

    date_range = st.date_input(
        "Filter by Date Range:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="log_viewer_date_range"
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
        # Filter by date part only
        filtered_logs = filtered_logs[
            (filtered_logs['Timestamp'].dt.date >= start_date) &
            (filtered_logs['Timestamp'].dt.date <= end_date)
        ]
    elif len(date_range) == 1:
        # If only one date is selected, filter for that specific day
        selected_date = date_range[0]
        filtered_logs = filtered_logs[filtered_logs['Timestamp'].dt.date == selected_date]

    if filtered_logs.empty:
        st.info("No logs found for the selected date range.")
        return

    st.subheader(f"Displaying {len(filtered_logs)} Planned Trade Logs")
    st.dataframe(filtered_logs.sort_values('Timestamp', ascending=False), use_container_width=True)

    # Optional: Download logs
    csv_data = filtered_logs.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Logs as CSV",
        data=csv_data,
        file_name=f"planned_trade_logs_{selected_portfolio_id}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
