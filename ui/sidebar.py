# ui/sidebar.py (เวอร์ชันเต็มสมบูรณ์: แก้ไข Bug ข้อมูลไม่ตรงกัน)

from config import settings
import streamlit as st
import pandas as pd
from core import supabase_handler as db_handler
from core import analytics_engine

def safe_float_convert(value, default=0.0):
    """Safely converts a value to a float, handling None, empty strings, or text."""
    if value is None:
        return default
    if isinstance(value, str) and (value.strip().lower() == 'none' or value.strip() == ''):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

@st.cache_data
def get_cached_strengths(df_actual, portfolio_id):
    """Helper function to cache the results of finding user strengths."""
    if df_actual is None or df_actual.empty or not portfolio_id:
        return []
    return analytics_engine.find_user_strengths(df_all_actual_trades=df_actual, active_portfolio_id=portfolio_id)

def render_sidebar():
    """
    Renders the entire Sidebar, ensuring data consistency is driven by app.py.
    """
    with st.sidebar:
        df_portfolios = db_handler.load_portfolios()
        st.markdown("---")
        st.subheader("Active Portfolio")

        if df_portfolios is None or df_portfolios.empty:
            st.warning("⚠️ ไม่พบข้อมูล Portfolio. กรุณาเพิ่ม Portfolio ใหม่ในหน้า Dashboard")
            st.session_state['active_portfolio_id_gs'] = None
            return 

        portfolio_options = dict(zip(df_portfolios['PortfolioName'], df_portfolios['PortfolioID']))
        portfolio_names_with_placeholder = ["-- Please select a portfolio --"] + sorted(list(portfolio_options.keys()))
        
        active_id = st.session_state.get('active_portfolio_id_gs')
        active_name = next((name for name, pid in portfolio_options.items() if pid == active_id), "-- Please select a portfolio --")
        
        try:
            current_index = portfolio_names_with_placeholder.index(active_name)
        except ValueError:
            current_index = 0
            st.session_state['active_portfolio_id_gs'] = None
        
        def handle_portfolio_selection():
            # ใช้ .get() เพื่อความปลอดภัย
            selected_name = st.session_state.get('sidebar_portfolio_selector')
            if not selected_name or selected_name == "-- Please select a portfolio --":
                return

            new_active_id = portfolio_options.get(selected_name)

            if st.session_state.get('active_portfolio_id_gs') != new_active_id:
                st.session_state['active_portfolio_id_gs'] = new_active_id
                st.session_state['active_portfolio_name_gs'] = selected_name
                # ล้างค่าเก่าทิ้งเพื่อให้มันโหลดใหม่
                st.session_state['current_account_balance'] = None 
                st.session_state['active_profit_target_pct'] = None

        st.selectbox(
            "Select Portfolio:", 
            options=portfolio_names_with_placeholder, 
            index=current_index,
            key='sidebar_portfolio_selector',
            on_change=handle_portfolio_selection
        )
        
        # --- START: แก้ไขส่วนนี้ทั้งหมด (ดึงข้อมูลตรงจาก DataFrame) ---
        
        # ตั้งค่าเริ่มต้นเผื่อไว้
        active_balance_to_use = settings.DEFAULT_ACCOUNT_BALANCE
        active_profit_target_pct = 10.0
        active_id = st.session_state.get('active_portfolio_id_gs')

        # ถ้ามีการเลือกพอร์ต ให้ไปหยิบเลขจากตาราง df_portfolios มาโชว์ทันที
        if active_id and not df_portfolios.empty:
            # หาแถวข้อมูลที่ ID ตรงกัน
            row = df_portfolios[df_portfolios['PortfolioID'] == active_id]
            if not row.empty:
                active_balance_to_use = safe_float_convert(row.iloc[0].get('InitialBalance'), settings.DEFAULT_ACCOUNT_BALANCE)
                active_profit_target_pct = safe_float_convert(row.iloc[0].get('ProfitTargetPercent'), 10.0)
                
                # อัปเดตค่าเข้าหน่วยความจำเพื่อให้ Widget ด้านล่างเห็นเลขเดียวกัน
                st.session_state['current_account_balance'] = active_balance_to_use
                st.session_state['active_profit_target_pct'] = active_profit_target_pct


        st.markdown("---")
        st.subheader("💰 Balance for Calculation")
        
        if not active_id:
            st.info("Please select a portfolio.")
            st.markdown(f"**{settings.DEFAULT_ACCOUNT_BALANCE:,.2f} USD** (Default Value)")
        elif st.session_state.get('latest_statement_equity') is not None:
            st.markdown(f"<p style='color:lime; font-size:1.5em; font-weight:bold;'>{active_balance_to_use:,.2f} USD</p><p style='color:grey;margin-top:-10px;'>(from Statement)</p>", unsafe_allow_html=True)
        elif st.session_state.get('current_portfolio_details'):
            st.markdown(f"<p style='color:gold; font-size:1.5em; font-weight:bold;'>{active_balance_to_use:,.2f} USD</p><p style='color:grey;margin-top:-10px;'>(from Initial Balance)</p>", unsafe_allow_html=True)
        else:
             st.markdown(f"**{active_balance_to_use:,.2f} USD**")

        st.markdown("---")
        st.subheader("⚖️ Risk Sizing Calculator")
        
        with st.expander("Show Calculator", expanded=True):
            
            # --- แก้ไข: ให้ value ของ Widget ดึงมาจาก active_balance_to_use เสมอ ---
            risk_calc_balance = st.number_input(
                "ยอดเงินในบัญชี ($)",
                min_value=0.0,
                value=float(active_balance_to_use), # บังคับเป็น float เพื่อความปลอดภัย
                key="risk_calc_balance"
            )
            
            risk_calc_percent = st.number_input(
                "ความเสี่ยงทั้งหมด (%)",
                min_value=0.01,
                max_value=100.0,
                value=0.9,
                step=0.1,
                format="%.2f",
                key="risk_calc_percent"
            )

            st.divider()
            
            if risk_calc_balance > 0 and risk_calc_percent > 0:
                total_risk_usd = risk_calc_balance * (risk_calc_percent / 100)
                st.write("**ผลการคำนวณ:**")
                st.info(f"ความเสี่ยง **{risk_calc_percent:.2f}%** คือ: **${total_risk_usd:,.2f}**")
                st.divider()
                num_entries = st.slider(
                    "แบ่งความเสี่ยงออกเป็น (จำนวนไม้):",
                    min_value=1,
                    max_value=10,
                    value=2,
                    step=1,
                    key="risk_calc_num_entries"
                )
                risk_per_entry = total_risk_usd / num_entries
                st.success(f"**ความเสี่ยงต่อไม้:** **${risk_per_entry:,.2f}**")

        st.markdown("---")
        st.subheader("🧮 Prop Firm Tools")

        with st.expander("Profit Consistency Calculator", expanded=True):
            
            st.markdown("**1. Challenge Setup**")
            
            col_a, col_b = st.columns(2)
            with col_a:
                # --- แก้ไข: ให้ value ดึงมาจาก active_balance_to_use เสมอ ---
                st.session_state['consistency_initial_balance'] = st.number_input(
                    "Initial Balance ($)", 
                    min_value=1.0, 
                    value=float(active_balance_to_use), # บังคับเป็น float
                    step=1000.0, 
                    format="%.2f", 
                    key="sidebar_con_balance"
                )
            with col_b:
                # --- แก้ไข: ให้ value ดึงมาจาก active_profit_target_pct เสมอ ---
                st.session_state['consistency_profit_target_pct'] = st.number_input(
                    "Profit Target (%)", 
                    min_value=1.0, 
                    value=float(active_profit_target_pct), # บังคับเป็น float
                    step=1.0, 
                    format="%.1f", 
                    key="sidebar_con_target_pct"
                )

            st.markdown("**2. Current Dashboard Stats**")
            col_c, col_d = st.columns(2)
            with col_c:
                st.session_state['consistency_total_pl'] = st.number_input(
                    "Current Total P/L ($)", value=st.session_state.get('consistency_total_pl', 0.00), format="%.2f", key="sidebar_con_total_pl"
                )
            with col_d:
                st.session_state['consistency_percent'] = st.number_input(
                    "Current Consistency (%)", value=st.session_state.get('consistency_percent', 0.0), min_value=0.0, format="%.2f", key="sidebar_con_consistency_pct"
                )
            
            st.markdown("**3. Rule Definition**")
            options_consistency = [19.99, 20.0, 30.0, 40.0, 50.0]
            try:
                current_value = st.session_state.get('consistency_rule_threshold', 19.99)
                current_index = options_consistency.index(current_value)
            except ValueError:
                current_index = 0
            
            st.session_state['consistency_rule_threshold'] = st.selectbox(
                label="เกณฑ์ของกฎ (%)", 
                options=options_consistency, 
                index=current_index,
                key="sidebar_con_rule"
            ) 