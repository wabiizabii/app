# ui/chart_section.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.supabase_handler import SupabaseHandler # แก้ไข: Import คลาส SupabaseHandler แทนการ import ฟังก์ชันโดยตรง

# NEW: สร้างและ cache SupabaseHandler object เพื่อใช้ในส่วนนี้โดยเฉพาะ
@st.cache_resource
def get_db_handler_for_chart():
    return SupabaseHandler()

def render_chart_section(df_portfolios: pd.DataFrame):
    """
    Renders the chart visualization section.
    """
    st.markdown("---")
    st.subheader("📈 Trade Chart Visualization")

    # Ensure current_portfolio_id is in session state
    if 'current_portfolio_id' not in st.session_state or not st.session_state['current_portfolio_id']:
        st.info("Please select or create a Portfolio in the sidebar to view charts.")
        return

    current_portfolio_id = st.session_state['current_portfolio_id']
    current_portfolio_name = st.session_state['current_portfolio_name']

    st.markdown(f"**Viewing Charts for Portfolio:** `{current_portfolio_name}` (`{current_portfolio_id}`)")

    # NEW: เรียกใช้ db_handler object ที่สร้างไว้
    db_handler = get_db_handler_for_chart()

    # NEW: ใช้ db_handler object เพื่อเรียก method load_actual_trades() และ load_planned_trade_logs()
    df_actual_trades = db_handler.load_actual_trades(portfolio_id=current_portfolio_id)
    df_planned_logs = db_handler.load_planned_trade_logs(portfolio_id=current_portfolio_id)

    # Convert date columns to datetime objects for plotting
    if not df_actual_trades.empty and 'CloseTime' in df_actual_trades.columns:
        df_actual_trades['CloseTime'] = pd.to_datetime(df_actual_trades['CloseTime'])
    if not df_planned_logs.empty and 'TradeDate' in df_planned_logs.columns:
        df_planned_logs['TradeDate'] = pd.to_datetime(df_planned_logs['TradeDate'])

    # --- Plotting Net Profit Over Time (from Actual Trades) ---
    st.markdown("#### Net Profit Over Time (Actual Trades)")
    if not df_actual_trades.empty:
        # Calculate cumulative net profit
        df_actual_trades = df_actual_trades.sort_values(by='CloseTime')
        df_actual_trades['CumulativeNetProfit'] = df_actual_trades['Profit'].cumsum()

        fig_profit = go.Figure()
        fig_profit.add_trace(go.Scatter(
            x=df_actual_trades['CloseTime'],
            y=df_actual_trades['CumulativeNetProfit'],
            mode='lines+markers',
            name='Cumulative Net Profit',
            line=dict(color='green')
        ))
        fig_profit.update_layout(
            title='Cumulative Net Profit Over Time',
            xaxis_title='Date',
            yaxis_title='Net Profit',
            hovermode="x unified"
        )
        st.plotly_chart(fig_profit, use_container_width=True)
    else:
        st.info("No actual trade data available for this portfolio to plot net profit.")

    # --- Plotting Trade Outcomes (Win/Loss Ratio) ---
    st.markdown("#### Trade Outcomes (Actual Trades)")
    if not df_actual_trades.empty:
        win_count = df_actual_trades[df_actual_trades['Profit'] > 0].shape[0]
        loss_count = df_actual_trades[df_actual_trades['Profit'] <= 0].shape[0] # Consider zero profit as non-win

        labels = ['Wins', 'Losses']
        values = [win_count, loss_count]
        colors = ['#28a745', '#dc3545'] # Green for wins, Red for losses

        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=colors, hole=.3)])
        fig_pie.update_layout(title_text='Win/Loss Ratio')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No actual trade data available for this portfolio to plot trade outcomes.")

    # --- Plotting Planned vs. Actual Trades (Example - by Symbol) ---
    st.markdown("#### Planned vs. Actual Trades (by Symbol)")
    if not df_planned_logs.empty or not df_actual_trades.empty:
        # Count planned trades per symbol
        planned_counts = df_planned_logs['Symbol'].value_counts().reset_index()
        planned_counts.columns = ['Symbol', 'PlannedCount']

        # Count actual trades per symbol
        actual_counts = df_actual_trades['Symbol'].value_counts().reset_index()
        actual_counts.columns = ['Symbol', 'ActualCount']

        # Merge data
        merged_counts = pd.merge(planned_counts, actual_counts, on='Symbol', how='outer').fillna(0)

        fig_bar = go.Figure(data=[
            go.Bar(name='Planned Trades', x=merged_counts['Symbol'], y=merged_counts['PlannedCount'], marker_color='skyblue'),
            go.Bar(name='Actual Trades', x=merged_counts['Symbol'], y=merged_counts['ActualCount'], marker_color='orange')
        ])
        fig_bar.update_layout(
            barmode='group',
            title='Planned vs. Actual Trades by Symbol',
            xaxis_title='Symbol',
            yaxis_title='Number of Trades'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No planned or actual trade data available for this portfolio to compare.")

    st.markdown("---")
    st.info("More chart visualizations coming soon!")