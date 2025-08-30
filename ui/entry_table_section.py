# ui/entry_table_section.py

import streamlit as st
import pandas as pd
import numpy as np
from core.supabase_handler import SupabaseHandler
from datetime import datetime
import uuid

def render_entry_table_section(db_handler: SupabaseHandler):
    """
    Renders the trade planning results table and summary.
    This section is active when on the 'Planned Trades' tab.
    """
    st.title("📊 Planned Trades")
    st.markdown("---")

    planning_result = st.session_state.get('current_planning_result')
    active_portfolio_id = st.session_state.get('active_portfolio_id')
    active_portfolio_name = st.session_state.get('active_portfolio_name')

    if not planning_result:
        st.info("No trade plan has been calculated yet. Please use the sidebar to input your planning data and click 'คำนวณแผนเทรด'.")
        return

    if 'error_message' in planning_result:
        st.error(f"Error during calculation: {planning_result['error_message']}")
        return

    # --- Display Calculation Summary ---
    st.subheader("Plan Summary")
    
    summary = planning_result.get('summary', {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Risk", f"{summary.get('total_risk_amount', 0.0):,.2f} USD")
    with col2:
        st.metric("Total Profit (TP1)", f"{summary.get('total_tp_amount', 0.0):,.2f} USD")
    with col3:
        st.metric("Risk/Reward Ratio", f"{summary.get('risk_reward_ratio', 0.0):.2f}")
    with col4:
        st.metric("Total Entry Lots", f"{summary.get('total_lots', 0.0):.2f}")

    st.markdown("---")

    # --- Display Entry Table ---
    st.subheader("Entry Details")

    df_entries = pd.DataFrame(planning_result.get('entries', []))
    
    if not df_entries.empty:
        df_entries = df_entries.set_index('entry_point')
        st.dataframe(df_entries, use_container_width=True)
    else:
        st.warning("No entry points were calculated.")
        
    st.markdown("---")

    # --- Save to Database Button ---
    st.subheader("Save This Plan")
    if st.button("💾 Save Plan to Database", key='save_plan_button', type='primary'):
        if not active_portfolio_id:
            st.error("Cannot save without an active portfolio.")
        elif df_entries.empty:
            st.error("Cannot save an empty trade plan.")
        else:
            try:
                # Prepare data for saving
                plan_id = str(uuid.uuid4())
                current_timestamp = datetime.now().isoformat()
                
                # Create a list of dictionaries to save to Supabase
                records_to_save = []
                for index, row in df_entries.iterrows():
                    record = {
                        "PlanID": plan_id,
                        "PortfolioID": active_portfolio_id,
                        "PortfolioName": active_portfolio_name,
                        "Asset": planning_result['asset'],
                        "Direction": planning_result['direction'],
                        "RiskPct": planning_result['risk_pct'],
                        "EntryPrice": row['entry_price'],
                        "StopLoss": row['sl_price'],
                        "TakeProfit": row['tp_price'],
                        "LotSize": row['lot_size'],
                        "CreatedAt": current_timestamp,
                        "Status": "Planned" # Initial status
                    }
                    records_to_save.append(record)
                
                # Use a handler function to save to Supabase
                success, message = db_handler.save_planned_trades(pd.DataFrame(records_to_save))

                if success:
                    st.success(f"✅ Trade plan successfully saved with Plan ID: `{plan_id}`!")
                    # Clear the planning result to avoid re-saving the same plan
                    st.session_state['planning_result'] = None
                else:
                    st.error(f"❌ Failed to save the trade plan: {message}")
                
            except Exception as e:
                st.error(f"An unexpected error occurred while saving the plan: {e}")
                st.exception(e)