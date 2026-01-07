# ui/sidebar.py (เวอร์ชันสมบูรณ์: แก้ปัญหาข้อมูลไม่ซิงค์และ AttributeError)

from config import settings
import streamlit as st
import pandas as pd
from core import supabase_handler as db_handler
from core import analytics_engine

def safe_float_convert(value, default=0.0):
    """ฟังก์ชันช่วยแปลงค่าเป็นตัวเลขอย่างปลอดภัย"""
    if value is None:
        return default
    if isinstance(value, str) and (value.strip().lower() == 'none' or value.strip() == ''):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def render_sidebar():
    """
    Renders the Sidebar and ensures data consistency between selection and calculation.
    """
    with st.sidebar:
        # 1. โหลดข้อมูล Portfolios ทั้งหมดจาก Supabase
        df_portfolios = db_handler.load_portfolios()
        st.markdown("---")
        st.subheader("Active Portfolio")

        if df_portfolios is None or df_portfolios.empty:
            st.warning("⚠️ ไม่พบข้อมูล Portfolio")
            st.session_state['active_portfolio_id_gs'] = None
            return 

        # 2. เตรียมตัวเลือกสำหรับ Selectbox
        portfolio_options = dict(zip(df_portfolios['PortfolioName'], df_portfolios['PortfolioID']))
        portfolio_names_with_placeholder = ["-- Please select a portfolio --"] + sorted(list(portfolio_options.keys()))
        
        active_id = st.session_state.get('active_portfolio_id_gs')
        active_name = next((name for name, pid in portfolio_options.items() if pid == active_id), "-- Please select a portfolio --")
        
        try:
            current_index = portfolio_names_with_placeholder.index(active_name)
        except ValueError:
            current_index = 0

        # --- ฟังก์ชันจัดการเมื่อมีการเปลี่ยนพอร์ต (หัวใจสำคัญ) ---
        def handle_portfolio_selection():
            # ดึงชื่อพอร์ตที่เลือกจาก Widget (ใช้ .get เพื่อกันแอปพัง)
            selected_name = st.session_state.get('sidebar_portfolio_selector')
            if not selected_name or selected_name == "-- Please select a portfolio --":
                return

            new_active_id = portfolio_options.get(selected_name)

            if st.session_state.get('active_portfolio_id_gs') != new_active_id:
                # 1. อัปเดต ID พอร์ตหลัก
                st.session_state['active_portfolio_id_gs'] = new_active_id
                st.session_state['active_portfolio_name_gs'] = selected_name
                
                # 2. ไปดึงข้อมูล Balance และ Profit Target จากตารางทันที
                row = df_portfolios[df_portfolios['PortfolioID'] == new_active_id]
                if not row.empty:
                    # ดึงเลขจากคอลัมน์ (รองรับทั้งตัวพิมพ์ใหญ่/เล็ก)
                    new_balance = safe_float_convert(row.iloc[0].get('InitialBalance') or row.iloc[0].get('initial_balance'), 10000.0)
                    new_target = safe_float_convert(row.iloc[0].get('ProfitTargetPercent') or row.iloc[0].get('profit_target_percent'), 10.0)
                    
                    # 3. !!! บังคับเขียนทับค่าใน Widget ทุกตัวเพื่อให้เลขเปลี่ยนทันที !!!
                    st.session_state['risk_calc_balance'] = float(new_balance)
                    st.session_state['sidebar_con_balance'] = float(new_balance)
                    st.session_state['sidebar_con_target_pct'] = float(new_target)
                    
                    # อัปเดตตัวแปรกลาง
                    st.session_state['current_account_balance'] = new_balance
                    st.session_state['active_profit_target_pct'] = new_target
                    
                # ล้างแคชข้อมูลเก่า
                st.session_state['current_portfolio_details'] = None 
                st.session_state['latest_statement_equity'] = None

        # แสดง Selectbox
        st.selectbox(
            "Select Portfolio:", 
            options=portfolio_names_with_placeholder, 
            index=current_index,
            key='sidebar_portfolio_selector',
            on_change=handle_portfolio_selection
        )
        
        # ดึงค่าปัจจุบันมาโชว์ใน UI
        active_balance_to_use = st.session_state.get('current_account_balance', settings.DEFAULT_ACCOUNT_BALANCE)
        active_profit_target_pct = st.session_state.get('active_profit_target_pct', 10.0)
        active_id = st.session_state.get('active_portfolio_id_gs')

        st.markdown("---")
        st.subheader("💰 Balance for Calculation")
        
        if not active_id:
            st.info("Please select a portfolio.")
            st.markdown(f"**{settings.DEFAULT_ACCOUNT_BALANCE:,.2f} USD** (Default Value)")
        else:
            st.markdown(f"<p style='color:gold; font-size:1.5em; font-weight:bold;'>{active_balance_to_use:,.2f} USD</p>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("⚖️ Risk Sizing Calculator")
        
        with st.expander("Show Calculator", expanded=True):
            # ดึงค่าจาก session_state มาเป็น value เริ่มต้น
            risk_calc_balance = st.number_input(
                "ยอดเงินในบัญชี ($)",
                min_value=0.0,
                value=float(st.session_state.get('risk_calc_balance', active_balance_to_use)),
                key="risk_calc_balance"
            )
            
            risk_calc_percent = st.number_input(
                "ความเสี่ยงทั้งหมด (%)",
                min_value=0.01,
                max_value=100.0,
                value=st.session_state.get('risk_calc_percent', 0.9),
                step=0.1,
                format="%.2f",
                key="risk_calc_percent"
            )

            if risk_calc_balance > 0:
                total_risk_usd = risk_calc_balance * (risk_calc_percent / 100)
                st.info(f"ความเสี่ยง {risk_calc_percent:.2f}% คือ: **${total_risk_usd:,.2f}**")

        st.markdown("---")
        st.subheader("🧮 Prop Firm Tools")

        with st.expander("Profit Consistency Planner", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.number_input(
                    "Initial Balance ($)", 
                    min_value=1.0, 
                    value=float(st.session_state.get('sidebar_con_balance', active_balance_to_use)),
                    format="%.2f", 
                    key="sidebar_con_balance"
                )
            with col_b:
                st.number_input(
                    "Profit Target (%)", 
                    min_value=1.0, 
                    value=float(st.session_state.get('sidebar_con_target_pct', active_profit_target_pct)),
                    format="%.1f", 
                    key="sidebar_con_target_pct"
                )

            # ส่วนอื่นๆ ของ Calculator (Current P/L, Consistency %)
            col_c, col_d = st.columns(2)
            with col_c:
                st.number_input("Current P/L ($)", value=0.0, format="%.2f", key="sidebar_con_total_pl")
            with col_d:
                st.number_input("Consistency (%)", value=0.0, format="%.2f", key="sidebar_con_consistency_pct")
            
            st.selectbox("เกณฑ์ของกฎ (%)", options=[19.99, 20.0, 30.0, 40.0, 50.0], key="sidebar_con_rule")