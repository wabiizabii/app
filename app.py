# app.py

import streamlit as st
import sys
import os
import pandas as pd

# --- Path Management ---
trading_dashboard_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(trading_dashboard_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# --- Imports from our project ---
from trading_dashboard.ui.sidebar import build_sidebar
from trading_dashboard.ui.main_components.realtime_dashboard import realtime_dashboard_component
from trading_dashboard.config.settings import SUPABASE_URL, SUPABASE_KEY, ASSET_SPECIFICATIONS
from trading_dashboard.core.supabase_handler import SupabaseHandler
from trading_dashboard.core.mt5_handler import MT5Handler
from trading_dashboard.core.planning_logic import create_trade_plan
from signal_analyzer.src.signal_generator import generate_signal_for_symbol

# --- Main App Logic ---
def main():
    st.set_page_config(layout="wide", page_title="AI Trading Assistant")

    # --- Initialize Handlers in Session State ---
    if 'db_handler' not in st.session_state:
        st.session_state.db_handler = SupabaseHandler(SUPABASE_URL, SUPABASE_KEY)
    if 'mt5_handler' not in st.session_state:
        st.session_state.mt5_handler = MT5Handler()
        st.session_state.mt5_handler.initialize_connection()
    if 'websocket_data_key' not in st.session_state:
        st.session_state['websocket_data_key'] = 0
    
    # --- Real-time Component (ทำงานเบื้องหลัง) ---
    session_state_from_js = realtime_dashboard_component()

    if isinstance(session_state_from_js, dict):
        for key in ['risk_available_today', 'daily_loss_limit_amount', 'total_open_risk']:
             if key in session_state_from_js:
                  session_state_from_js[key] = float(session_state_from_js.get(key, 0.0))

        st.session_state.update(session_state_from_js)
        st.session_state['websocket_data_key'] += 1
        st.rerun()

    # --- UI Rendering ---
    build_sidebar()
    
    is_link_valid = st.session_state.get('is_link_valid', False)
    data_streamer_status = st.session_state.get('data_streamer_status', 'Waiting')

    if is_link_valid:
        st.sidebar.success("✅ Link Active")
        
        tab1, tab2, tab3 = st.tabs(["📊 Main Dashboard", "💡 Trade Planner", "⚙️ Settings"])

        with tab1:
            st.header("📊 Main Dashboard")
            st.write("Live data is being displayed by the real-time component.")

        with tab2:
            st.header("💡 Trade Planner")
            col1, col2 = st.columns([1, 3])

            with col1:
                st.subheader("Controls")
                
                st.info("Daily Risk Status")
                risk_available = st.session_state.get('risk_available_today', 0.0)
                risk_limit = st.session_state.get('daily_loss_limit_amount', 0.0)
                risk_used = st.session_state.get('total_open_risk', 0.0)
                
                if risk_available <= 0:
                    st.metric(label="Risk Available", value=f"${risk_available:,.2f}", delta="STOP TRADING", delta_color="inverse")
                else:
                    st.metric(label="Risk Available", value=f"${risk_available:,.2f}")
                
                st.caption(f"Limit: ${risk_limit:,.2f} | Used: ${risk_used:,.2f}")
                st.divider()

                # --- START: แก้ไขการสร้าง Selectbox ---
                account_type = st.session_state.get('account_type', 'STANDARD').upper()
                available_symbols = list(ASSET_SPECIFICATIONS.get(account_type, {}).keys())
                selected_symbol = st.selectbox("Select Symbol:", available_symbols) 
                # --- END: แก้ไขการสร้าง Selectbox ---
                
                if st.button("🚀 Generate New Plan"):
                    with st.spinner("Analyzing market and generating plan..."):
                        try:
                            mt5 = st.session_state.mt5_handler
                            
                            signal = generate_signal_for_symbol(symbol=selected_symbol, mt5_handler=mt5)
                            st.write(f"Generated Signal: **{signal['signal_text']}**")

                            live_account_info = mt5.get_account_info()
                            risk_available = st.session_state.get('risk_available_today', 0.0)
                            
                            trade_plan = create_trade_plan(
                                signal=signal['signal_code'],
                                symbol=selected_symbol,
                                account_info=live_account_info,
                                risk_available=risk_available
                            )
                            
                            st.session_state['generated_plan'] = trade_plan
                        except Exception as e:
                            st.error(f"An error occurred: {e}")
                else:
                    if 'generated_plan' not in st.session_state:
                         st.session_state['generated_plan'] = None

            with col2:
                st.subheader("Generated Trade Plan")
                plan_placeholder = st.container()
                
                if st.session_state.get('generated_plan'):
                    plan = st.session_state['generated_plan']
                    with plan_placeholder:
                        st.dataframe(pd.DataFrame([plan]))
                        if st.button("💾 Save Plan to Log"):
                            st.success("Plan saved! (This feature is coming soon)")
                        if st.button("🔥 Execute via EA", type="primary"):
                            st.warning("Executing via EA! (This feature is coming soon)")
                else:
                    with plan_placeholder:
                        st.info("Click 'Generate New Plan' to get started.")

        with tab3:
            st.header("⚙️ Portfolio & Connection Settings")
            st.write("ส่วนตั้งค่า Portfolio และการเชื่อมต่อจะอยู่ที่นี่")
            
    else:
        if data_streamer_status == 'Waiting' and not session_state_from_js:
            st.info("⌛ กำลังรอข้อมูลจาก Data Streamer...")
            st.warning("กรุณาตรวจสอบว่า Service 'mt5_data_streamer.py' กำลังทำงานอยู่")
        else:
            st.sidebar.error("❌ Link Inactive")
            st.error("ไม่สามารถแสดงผลข้อมูลได้: กรุณาตรวจสอบการตั้งค่าใน Sidebar และสถานะของ Data Streamer")

if __name__ == "__main__":
    main()