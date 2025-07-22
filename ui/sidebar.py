# ui/sidebar.py (Language changed to English)
from config import settings
import streamlit as st
import pandas as pd
import numpy as np
from core import supabase_handler as db_handler
from core import planning_logic, analytics_engine


def safe_float_convert(value, default=0.0):
    """Safely converts a value to a float, handling None, empty strings, or text."""
    if value is None:
        return default
    # จัดการกรณีที่ค่าเป็น string 'None' หรือค่าว่าง
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

def render_sidebar(df_portfolios: pd.DataFrame, user_id: str): # <<< แก้ไข: เพิ่ม user_id
    """
    Renders the entire Sidebar.
    """
   
    
    with st.sidebar:
        # แก้ไข: ส่ง user_id เข้าไปในการโหลด portfolios
        df_portfolios = db_handler.load_portfolios(user_id=user_id)
        st.markdown("---")
        st.subheader("Active Portfolio")

        if df_portfolios is None or df_portfolios.empty:
            st.warning("⚠️ ไม่พบข้อมูล Portfolio ใน Google Sheet. กรุณาเพิ่ม Portfolio ใหม่ หรือตรวจสอบชื่อชีท 'Portfolios'.")
            st.session_state['active_portfolio_id_gs'] = None # Clear active id if no portfolios found
            return

        portfolio_options = dict(zip(df_portfolios['PortfolioName'], df_portfolios['PortfolioID']))
        
        portfolio_names_with_placeholder = ["-- Please select a portfolio --"] + sorted(list(portfolio_options.keys()))
        
        active_id = st.session_state.get('active_portfolio_id_gs') 
        active_name = next((name for name, pid in portfolio_options.items() if pid == active_id), "-- Please select a portfolio --")
        
        try:
            current_index = portfolio_names_with_placeholder.index(active_name)
        except ValueError:
            current_index = 0
            st.session_state['active_portfolio_id_gs'] = None # Reset if name not found
        
        def handle_portfolio_selection():
            selected_name = st.session_state.sidebar_portfolio_selector
            new_active_id = portfolio_options.get(selected_name)

            if st.session_state.get('active_portfolio_id_gs') != new_active_id:
                st.session_state['active_portfolio_id_gs'] = new_active_id
                st.session_state['active_portfolio_name_gs'] = selected_name if new_active_id else ""
                
                # เมื่อเปลี่ยน Portfolio ให้รีเซ็ตรายละเอียดพอร์ตและโหลดใหม่
                st.session_state['current_portfolio_details'] = None 
                
                st.session_state['latest_statement_equity'] = None
                #st.rerun()

        st.selectbox(
            "Select Portfolio:", 
            options=portfolio_names_with_placeholder, 
            index=current_index,
            key='sidebar_portfolio_selector',
            on_change=handle_portfolio_selection
        )

        # เพิ่มโค้ดส่วนนี้ (หลังจาก st.selectbox) เพื่อดึงรายละเอียดของพอร์ตที่เลือก
        current_pf_details = None
        if active_id:
            # ดึงรายละเอียดของพอร์ตที่เลือกจาก df_portfolios
            current_pf_row = df_portfolios[df_portfolios['PortfolioID'] == active_id]
            if not current_pf_row.empty:
                current_pf_details = current_pf_row.iloc[0].to_dict()
                st.session_state['current_portfolio_details'] = current_pf_details
            else:
                st.session_state['current_portfolio_details'] = None # หากหาไม่เจอ

        # ดึง AccountType ของพอร์ตที่เลือก (ใช้ 'STANDARD' เป็นค่า Default หากไม่มีการระบุ)
        active_account_type = current_pf_details.get('AccountType', 'STANDARD').upper() if current_pf_details else 'STANDARD'
        
        st.markdown("---")
        st.subheader("💰 Balance for Calculation")
        active_balance_to_use = st.session_state.get('current_account_balance', settings.DEFAULT_ACCOUNT_BALANCE)
        
        if not active_id:
            st.info("Please select a portfolio.")
            st.markdown(f"**{settings.DEFAULT_ACCOUNT_BALANCE:,.2f} USD** (Default Value)")
        elif st.session_state.get('latest_statement_equity') is not None:
            st.markdown(f"<p style='color:lime; font-size:1.5em; font-weight:bold;'>{active_balance_to_use:,.2f} USD</p><p style='color:grey;margin-top:-10px;'>(from Statement)</p>", unsafe_allow_html=True)
        elif st.session_state.get('current_portfolio_details'):
            st.markdown(f"<p style='color:gold; font-size:1.5em; font-weight:bold;'>{active_balance_to_use:,.2f} USD</p><p style='color:grey;margin-top:-10px;'>(from Initial Balance)</p>", unsafe_allow_html=True)
        else: # Fallback
             st.markdown(f"**{active_balance_to_use:,.2f} USD**")


        user_strengths = []
        if active_id:
            # แก้ไข: ส่ง user_id เข้าไปในการโหลด actual trades
            df_actual_trades = db_handler.load_actual_trades(user_id=user_id)
            user_strengths = get_cached_strengths(df_actual_trades, active_id)
        
        st.markdown("---")
        st.subheader("⚙️ Trading Setup")
        
        risk_val_from_pf = current_pf_details.get('CurrentRiskPercent', settings.DEFAULT_RISK_PERCENT) if current_pf_details else settings.DEFAULT_RISK_PERCENT

        # ใช้ฟังก์ชันผู้ช่วยที่ปลอดภัยในการแปลงค่า
        initial_risk_pct = safe_float_convert(risk_val_from_pf, default=settings.DEFAULT_RISK_PERCENT)
        if initial_risk_pct <= 0.0: initial_risk_pct = settings.DEFAULT_RISK_PERCENT
        
        dd_limit_from_pf = current_pf_details.get('DailyLossLimitPercent', settings.DEFAULT_DRAWDOWN_LIMIT_PCT) if current_pf_details else settings.DEFAULT_DRAWDOWN_LIMIT_PCT

        # ใช้ฟังก์ชันผู้ช่วยที่ปลอดภัยในการแปลงค่า
        drawdown_limit_pct_default = safe_float_convert(dd_limit_from_pf, default=settings.DEFAULT_DRAWDOWN_LIMIT_PCT)
        if drawdown_limit_pct_default <= 0.0: drawdown_limit_pct_default = settings.DEFAULT_DRAWDOWN_LIMIT_PCT

        st.number_input("Daily Drawdown Limit (%)", 0.1, 100.0, drawdown_limit_pct_default, 0.1, "%.1f", key="drawdown_limit_pct")
                
        st.radio("Trade Mode", ["FIBO", "CUSTOM"], horizontal=True, key="mode")
        available_symbols_for_account = settings.ASSET_SPECIFICATIONS.get(active_account_type, {})
        symbol_options = sorted(list(available_symbols_for_account.keys()))
        if not symbol_options:
            symbol_options = ["NO_SYMBOLS_AVAILABLE"]
            
        # --- FIBO MODE ---
        if st.session_state.mode == "FIBO":
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 2])
                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    # <<<< แก้ไข Symbol Input ให้เป็น Selectbox >>>>
                    default_index_fibo = 0
                    if "XAUUSD" in symbol_options:
                        default_index_fibo = symbol_options.index("XAUUSD")
                    elif active_account_type == "CENT" and "XAUUSDc" in symbol_options: # ลองตั้งค่าเริ่มต้นสำหรับ Cent
                         default_index_fibo = symbol_options.index("XAUUSDc")
                    
                    st.selectbox(
                        "Symbol",
                        options=symbol_options,
                        index=default_index_fibo,
                        key="asset_fibo_val_v2"
                    )
                with col2:
                    st.number_input(
                        "Risk %",
                        0.01, 100.0, initial_risk_pct, 0.01, "%.2f",
                        key="risk_pct_fibo_val_v2"
                    )
                with col3:
                    st.radio(
                        "Direction", ["Long", "Short"], index=0, horizontal=True,
                        key="direction_fibo_val_v2"
                    )
                
                col4, col5, col6 = st.columns(3)
                with col4:
                    st.text_input(
                        "Swing High",
                        value=st.session_state.get("swing_high_fibo_val_v2", ""),
                        key="swing_high_fibo_val_v2",
                        placeholder="e.g., 2350.50"
                    )
                with col5:
                    st.text_input(
                        "Swing Low",
                        value=st.session_state.get("swing_low_fibo_val_v2", ""),
                        key="swing_low_fibo_val_v2",
                        placeholder="e.g., 2330.00"
    )
                with col6:
                    st.number_input(
                        "Spread",
                        value=float(st.session_state.get("fibo_spread", 0.0)),
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        key="fibo_spread"
                    )
                st.markdown("**📐 Entry Fibo Levels**")
                fibo_options = settings.FIBO_LEVELS_DEFINITIONS
                if 'fibo_flags_v2' not in st.session_state or len(st.session_state.fibo_flags_v2) != len(fibo_options):
                    st.session_state.fibo_flags_v2 = [True] * len(fibo_options)
                cols_cb = st.columns(len(fibo_options))
                st.session_state.fibo_flags_v2 = [c.checkbox(f"{lvl:.3f}", st.session_state.fibo_flags_v2[i], key=f"fibo_cb_{i}") for i, (c, lvl) in enumerate(zip(cols_cb, fibo_options))]

                asset_fibo = st.session_state.get("asset_fibo_val_v2", "XAUUSD").upper()
                direction_fibo = st.session_state.get("direction_fibo_val_v2", "Long")
                if asset_fibo and direction_fibo:
                    setup_str = f"{asset_fibo.upper()}-{direction_fibo}"
                    if setup_str in user_strengths:
                        st.success(f"💡 Excellent! You perform well with this Setup ({setup_str}).")

        # --- CUSTOM MODE ---
        elif st.session_state.mode == "CUSTOM":
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    default_index_custom = 0
                    if "XAUUSD" in symbol_options:
                        default_index_custom = symbol_options.index("XAUUSD")
                    elif active_account_type == "CENT" and "XAUUSDc" in symbol_options: # ลองตั้งค่าเริ่มต้นสำหรับ Cent
                        default_index_custom = symbol_options.index("XAUUSDc")

                    st.selectbox(
                        "Symbol",
                        options=symbol_options,
                        index=default_index_custom,
                        key="custom_asset"
                    )
                with col2: st.number_input("Risk %", 0.01, 100.0, initial_risk_pct, 0.01, "%.2f", key="custom_risk")
                with col3: st.number_input("Number of Entries", 1, 10, 2, 1, key="custom_n_entries")

                n_entries = st.session_state.get("custom_n_entries", 2)
                st.markdown("**Enter details for each entry**")
                for i in range(n_entries):
                    c1, c2, c3 = st.columns(3)
                    with c1: st.text_input(f"Entry {i+1}", key=f"cust_e_{i}", label_visibility="collapsed", placeholder=f"Entry {i+1}")
                    with c2: st.text_input(f"SL {i+1}", key=f"cust_sl_{i}", label_visibility="collapsed", placeholder=f"SL {i+1}")
                    with c3: st.text_input(f"TP {i+1}", key=f"cust_tp_{i}", label_visibility="collapsed", placeholder=f"TP {i+1}")
        asset_custom = st.session_state.get("custom_asset", "XAUUSD").upper()

        if st.button("🔄 Reset Plan Settings", use_container_width=True, type="secondary"):
            keys_to_reset = ["asset_fibo_val_v2", "risk_pct_fibo_val_v2", "direction_fibo_val_v2", "swing_high_fibo_val_v2", "swing_low_fibo_val_v2", "fibo_spread", "fibo_flags_v2", "custom_asset", "custom_risk", "custom_n_entries"]
            for i in range(10): keys_to_reset.extend([f"cust_e_{i}", f"cust_sl_{i}", f"cust_tp_{i}"])
            for key in keys_to_reset:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
        asset_custom = st.session_state.get("custom_asset", "XAUUSD").upper()

        with st.expander("⚖️ Scaling Manager Settings", expanded=False):
            def get_pf_param(param_name, default_value):
                if current_pf_details and isinstance(current_pf_details, dict):
                    val = current_pf_details.get(param_name)
                    if pd.notna(val) and str(val).strip() != "":
                        try: return float(val)
                        except (ValueError, TypeError): pass
                return default_value

            min_risk_default = get_pf_param('MinRiskPercentAllowed', settings.DEFAULT_MIN_RISK_PERCENT)
            max_risk_default = get_pf_param('MaxRiskPercentAllowed', settings.DEFAULT_MAX_RISK_PERCENT)
            
            if min_risk_default < 0.01:
                min_risk_default = settings.DEFAULT_MIN_RISK_PERCENT
            
            if max_risk_default < 0.01:
                max_risk_default = settings.DEFAULT_MAX_RISK_PERCENT

            st.number_input("Minimum Risk % Allowed", 0.01, 100.0, min_risk_default, 0.01, "%.2f", key='min_risk_pct')
            st.number_input("Maximum Risk % Allowed", 0.01, 100.0, max_risk_default, 0.01, "%.2f", key='max_risk_pct')
            st.radio("Scaling Mode", ["Manual", "Auto"], index=0, horizontal=True, key='scaling_mode_radio_val')

        st.markdown("---")
        
        min_risk_allowed = st.session_state.get('min_risk_pct', 0.01)
        max_risk_allowed = st.session_state.get('max_risk_pct', 100.0)
        drawdown_limit_pct_from_input = st.session_state.get('drawdown_limit_pct', 2.0)

        raw_risk = float(st.session_state.get('risk_pct_fibo_val_v2', initial_risk_pct) if st.session_state.mode == "FIBO" else st.session_state.get('custom_risk', initial_risk_pct))
        clamped_by_scaler = max(min_risk_allowed, min(raw_risk, max_risk_allowed))
        risk_to_use = min(clamped_by_scaler, float(drawdown_limit_pct_from_input))
        
        st.markdown("▶️ **Actual Risk for Calculation:**")
        st.info(f"**{risk_to_use:.2f}%**")

        if raw_risk != risk_to_use:
            if raw_risk < min_risk_allowed: st.warning(f"Risk adjusted to {min_risk_allowed:.2f}% (from minimum)")
            elif raw_risk > max_risk_allowed: st.warning(f"Risk adjusted to {max_risk_allowed:.2f}% (from maximum)")
            elif risk_to_use < raw_risk: st.warning(f"Risk capped by Daily DD Limit at {drawdown_limit_pct_from_input:.1f}%")
        
        planning_result = {}
        if active_id:
            if st.session_state.mode == "FIBO":
                if st.session_state.get("swing_high_fibo_val_v2") and st.session_state.get("swing_low_fibo_val_v2"):
                    planning_result = planning_logic.calculate_fibo_trade_plan(
                        swing_high_str=str(st.session_state.swing_high_fibo_val_v2),
                        swing_low_str=str(st.session_state.swing_low_fibo_val_v2),
                        risk_pct_fibo_input=st.session_state.risk_pct_fibo_val_v2,
                        fibo_levels_definitions=settings.FIBO_LEVELS_DEFINITIONS,
                        fibo_flags_selected=st.session_state.fibo_flags_v2,
                        direction=st.session_state.direction_fibo_val_v2,
                        current_active_balance=active_balance_to_use,
                        spread_str=str(st.session_state.fibo_spread),
                        asset_name=asset_fibo, # Symbol (เป็นตัวพิมพ์ใหญ่แล้ว)
                        account_type=active_account_type # AccountType ของพอร์ตที่เลือก
                    )
                else:
                    st.info("Please enter Swing High and Swing Low to calculate the plan.")
                   
            elif st.session_state.mode == "CUSTOM":
                custom_entries = [{"entry_str": st.session_state.get(f"cust_e_{i}", ""), "sl_str": st.session_state.get(f"cust_sl_{i}", ""), "tp_str": st.session_state.get(f"cust_tp_{i}", "")} for i in range(st.session_state.get("custom_n_entries", 0))]
                if any(e['entry_str'] and e['sl_str'] for e in custom_entries):
                    planning_result = planning_logic.calculate_custom_trade_plan(
                        num_entries_custom=st.session_state.get("custom_n_entries", 0),
                        risk_pct_custom_input=risk_to_use,
                        custom_entries_details=custom_entries,
                        current_active_balance=active_balance_to_use,
                        # asset_name=asset_custom, # ไม่จำเป็นต้องส่ง asset_name และ account_type ไปที่ calculate_custom_trade_plan
                        # account_type=active_account_type
                    )
        
        st.session_state.planning_result = planning_result
        st.session_state.entry_data_for_saving = planning_result.get('entry_data', [])
        
        if st.session_state.planning_result and st.session_state.planning_result.get('error_message'):
            st.error(st.session_state.planning_result['error_message'])

        st.markdown("---")
        st.subheader("💾 Save Plan & Check Drawdown")
        # แก้ไข: ส่ง user_id เข้าไปในการโหลด all planned trade logs
        all_logs = db_handler.load_all_planned_trade_logs(user_id=user_id)
        portfolio_logs = pd.DataFrame()
        if active_id and not all_logs.empty:
            portfolio_logs = all_logs[all_logs['PortfolioID'] == str(active_id)]
        
        drawdown_today = analytics_engine.get_today_drawdown(portfolio_logs)
        drawdown_limit_absolute = -abs(active_balance_to_use * (drawdown_limit_pct_from_input / 100.0))
        st.markdown(f"**Today's DD (from Plan):** <font color='{'red' if drawdown_today < 0 else 'white'}'>{drawdown_today:,.2f} USD</font>", unsafe_allow_html=True)
        st.markdown(f"**DD Limit ({drawdown_limit_pct_from_input:.1f}%):** {drawdown_limit_absolute:,.2f} USD")
        
        if st.button("💾 Save Plan", use_container_width=True, type="primary"):
            if not active_id: 
                st.error("❌ Please select a portfolio before saving.")
            elif not st.session_state.get('entry_data_for_saving'): 
                st.warning("⚠️ No plan data to save. Please enter details and calculate the plan first.")
            elif drawdown_today < 0 and abs(drawdown_today) >= abs(drawdown_limit_absolute): 
                st.error(f"‼️ Stop Trading! Today's loss limit has been exceeded ({drawdown_today:,.2f} / {drawdown_limit_absolute:,.2f})")
            else:
                current_mode = st.session_state.mode
                asset_to_save = st.session_state.get('asset_fibo_val_v2', "XAUUSD") if current_mode == "FIBO" else st.session_state.get('custom_asset', "XAUUSD")
                risk_pct_to_save = risk_to_use
                direction_to_save = planning_result.get('direction', 'N/A')
                
                success, msg = db_handler.save_planned_trade_logs(
                    plan_data_list=st.session_state.get('entry_data_for_saving', []), 
                    trade_mode=current_mode, 
                    asset_name=asset_to_save, 
                    risk_percentage=risk_to_use, # หมายเหตุ: risk_to_use ต้องถูกคำนวณมาก่อนหน้านี้
                    trade_direction=direction_to_save, 
                    portfolio_id=active_id, 
                    portfolio_name=st.session_state.get('active_portfolio_name_gs', 'N/A'),
                    user_id=user_id # <<< แก้ไข: เพิ่ม user_id
                )
                
                if success:
                    st.success(f"✔️ {msg}"); st.balloons()
                    # ไม่จำเป็นต้อง clear cache ของ gs_handler อีกต่อไป
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
