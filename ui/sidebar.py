# ui/sidebar.py
import streamlit as st
import pandas as pd
import numpy as np
from config import settings
from core import gs_handler, planning_logic, analytics_engine

@st.cache_data
def get_cached_strengths(df_actual, portfolio_id):
    """Helper function to cache the results of finding user strengths."""
    if df_actual is None or df_actual.empty or not portfolio_id:
        return []
    return analytics_engine.find_user_strengths(df_all_actual_trades=df_actual, active_portfolio_id=portfolio_id)

def render_sidebar():
    """
    [แก้ไขล่าสุด] นำปุ่ม RR=3 ออกจากโหมด CUSTOM
    """
    with st.sidebar:
        df_portfolios = gs_handler.load_portfolios_from_gsheets()
        st.markdown("---")
        st.subheader("เลือกพอร์ตที่ใช้งาน (Active Portfolio)")

        if df_portfolios is None or df_portfolios.empty:
            st.error("❌ ไม่พบข้อมูลพอร์ต")
            st.session_state['active_portfolio_id'] = None
            return

        portfolio_options = dict(zip(df_portfolios['PortfolioName'], df_portfolios['PortfolioID']))
        portfolio_names = [""] + sorted(list(portfolio_options.keys()))
        active_id = st.session_state.get('active_portfolio_id')
        active_name = next((name for name, pid in portfolio_options.items() if pid == active_id), "")
        try:
            current_index = portfolio_names.index(active_name)
        except ValueError:
            current_index = 0
        
        selected_name = st.selectbox(
            "เลือกพอร์ต:", 
            options=portfolio_names, 
            index=current_index,
            key='sidebar_portfolio_selector'
        )
        
        new_active_id = portfolio_options.get(selected_name) if selected_name else None
        if active_id != new_active_id:
            st.session_state['active_portfolio_id'] = new_active_id
            st.rerun()

        st.markdown("---")
        st.subheader("💰 Balance สำหรับคำนวณ")
        active_balance_to_use = st.session_state.get('current_account_balance', settings.DEFAULT_ACCOUNT_BALANCE)
        if st.session_state.get('latest_statement_equity') is not None:
            st.markdown(f"<font color='lime'>**{active_balance_to_use:,.2f} USD**</font> (จาก Statement)", unsafe_allow_html=True)
        elif st.session_state.get('current_portfolio_details'):
            st.markdown(f"<font color='gold'>**{active_balance_to_use:,.2f} USD**</font> (จาก Initial Balance พอร์ต)", unsafe_allow_html=True)
        else:
            st.info("กรุณาเลือกพอร์ตเพื่อเริ่มใช้งาน")
            st.markdown(f"**{active_balance_to_use:,.2f} USD** (ค่าเริ่มต้น)")

        user_strengths = []
        if new_active_id:
            df_actual_trades = gs_handler.load_actual_trades_from_gsheets()
            user_strengths = get_cached_strengths(df_actual_trades, new_active_id)
        
        st.markdown("---")
        st.subheader("⚙️ ตั้งค่าการเทรด")

        current_pf_details = st.session_state.get('current_portfolio_details')
        initial_risk_pct = float(current_pf_details.get('CurrentRiskPercent', settings.DEFAULT_RISK_PERCENT)) if current_pf_details else settings.DEFAULT_RISK_PERCENT
        drawdown_limit_pct_default = float(current_pf_details.get('DailyLossLimitPercent', 2.0)) if current_pf_details else 2.0
        drawdown_limit_pct = st.number_input("Drawdown Limit ต่อวัน (%)", 0.1, 100.0, drawdown_limit_pct_default, 0.1, "%.1f", key="drawdown_limit_pct_input")
        
        st.radio("Trade Mode", ["FIBO", "CUSTOM"], horizontal=True, key="mode")
        
        if st.session_state.mode == "FIBO":
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1: asset_fibo = st.text_input("Symbol", st.session_state.get("fibo_asset", "XAUUSD"), key="fibo_asset")
            with col2: risk_fibo = st.number_input("Risk %", 0.01, 100.0, initial_risk_pct, 0.01, "%.2f", key="fibo_risk")
            with col3: direction_fibo = st.radio("Direction", ["Long", "Short"], index=0, horizontal=True, key="fibo_direction")
            
            col4, col5, col6 = st.columns(3)
            with col4: swing_high = st.text_input("Swing High", key="fibo_swing_high")
            with col5: swing_low = st.text_input("Swing Low", key="fibo_swing_low")
            with col6: spread_fibo = st.text_input("Spread", st.session_state.get("fibo_spread", "0.0"), key="fibo_spread")

            st.markdown("**📐 Entry Fibo Levels**")
            fibo_options = settings.FIBO_LEVELS_DEFINITIONS
            if 'fibo_flags' not in st.session_state: st.session_state.fibo_flags = [True] * len(fibo_options)
            cols_cb = st.columns(len(fibo_options))
            st.session_state.fibo_flags = [c.checkbox(f"{lvl:.3f}", st.session_state.fibo_flags[i], key=f"fibo_cb_{i}") for i, (c, lvl) in enumerate(zip(cols_cb, fibo_options))]

            if asset_fibo and direction_fibo:
                setup_str = f"{asset_fibo.upper()}-{direction_fibo}"
                if setup_str in user_strengths:
                    st.success(f"💡 ยอดเยี่ยม! Setup ({setup_str}) นี้คุณทำได้ดี")

        elif st.session_state.mode == "CUSTOM":
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1: asset_custom = st.text_input("Symbol", st.session_state.get("custom_asset", "XAUUSD"), key="custom_asset")
            with col2: risk_custom = st.number_input("Risk %", 0.01, 100.0, initial_risk_pct, 0.01, "%.2f", key="custom_risk")
            with col3: n_entries = st.number_input("จำนวนไม้", 1, 10, st.session_state.get("custom_n_entries", 2), 1, key="custom_n_entries")

            st.markdown("**กรอกข้อมูลแต่ละไม้**")
            for i in range(n_entries):
                # --- [แก้ไข] ปรับ Layout กลับเป็น 3 คอลัมน์ และลบปุ่ม RR=3 ออก ---
                c1, c2, c3 = st.columns(3)
                with c1: st.text_input(f"Entry", key=f"cust_e_{i}", label_visibility="collapsed", placeholder=f"Entry {i+1}")
                with c2: st.text_input(f"SL", key=f"cust_sl_{i}", label_visibility="collapsed", placeholder=f"SL {i+1}")
                with c3: st.text_input(f"TP", key=f"cust_tp_{i}", label_visibility="collapsed", placeholder=f"TP {i+1}")
        
        if st.button("🔄 รีเซ็ตค่าการวางแผน", use_container_width=True, type="secondary"):
            keys_to_reset = ["fibo_asset", "fibo_risk", "fibo_direction", "fibo_swing_high", "fibo_swing_low", "fibo_spread", "fibo_flags", "custom_asset", "custom_risk", "custom_n_entries"]
            for i in range(10): keys_to_reset.extend([f"cust_e_{i}", f"cust_sl_{i}", f"cust_tp_{i}"])
            for key in keys_to_reset:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

        with st.expander("⚖️ Scaling Manager Settings", expanded=True):
            def get_pf_param(param_name, default_value):
                if current_pf_details and isinstance(current_pf_details, dict):
                    val = current_pf_details.get(param_name)
                    if pd.notna(val) and str(val).strip() != "":
                        try: return float(val)
                        except (ValueError, TypeError): pass
                return default_value

            min_risk_default = get_pf_param('MinRiskPercentAllowed', settings.DEFAULT_MIN_RISK_PERCENT)
            max_risk_default = get_pf_param('MaxRiskPercentAllowed', settings.DEFAULT_MAX_RISK_PERCENT)
            
            min_risk_allowed = st.number_input("Minimum Risk % Allowed", 0.01, 100.0, min_risk_default, 0.01, "%.2f", key='min_risk_pct')
            max_risk_allowed = st.number_input("Maximum Risk % Allowed", 0.01, 100.0, max_risk_default, 0.01, "%.2f", key='max_risk_pct')
            
            st.radio("Scaling Mode", ["Manual", "Auto"], index=0, horizontal=True, key='scaling_mode_radio_val')

        st.markdown("---")
        
        raw_risk = float(st.session_state.get('fibo_risk', initial_risk_pct) if st.session_state.mode == "FIBO" else st.session_state.get('custom_risk', initial_risk_pct))
        clamped_by_scaler = max(min_risk_allowed, min(raw_risk, max_risk_allowed))
        risk_to_use = min(clamped_by_scaler, float(drawdown_limit_pct))
        
        st.markdown("▶️ **Risk ที่จะใช้คำนวณจริง:**")
        st.info(f"**{risk_to_use:.2f}%**")

        if raw_risk < min_risk_allowed:
            st.warning(f"Risk ที่กรอก ({raw_risk:.2f}%) ต่ำกว่าขั้นต่ำ ({min_risk_allowed:.2f}%)")
        elif raw_risk > max_risk_allowed:
            st.warning(f"Risk ที่กรอก ({raw_risk:.2f}%) สูงกว่าสูงสุด ({max_risk_allowed:.2f}%)")
        elif risk_to_use < raw_risk:
            st.warning(f"Risk ถูกจำกัดด้วย Daily Drawdown Limit ที่ {drawdown_limit_pct:.1f}%")
        
        planning_result = {}
        if st.session_state.mode == "FIBO":
            if st.session_state.get("fibo_swing_high") and st.session_state.get("fibo_swing_low") and new_active_id:
                planning_result = planning_logic.calculate_fibo_trade_plan(swing_high_str=st.session_state.fibo_swing_high, swing_low_str=st.session_state.fibo_swing_low, risk_pct_fibo_input=risk_to_use, fibo_levels_definitions=settings.FIBO_LEVELS_DEFINITIONS, fibo_flags_selected=st.session_state.get("fibo_flags", []), direction=st.session_state.fibo_direction, current_active_balance=active_balance_to_use, spread_str=st.session_state.fibo_spread)
        elif st.session_state.mode == "CUSTOM":
            if new_active_id:
                custom_entries = [{"entry_str": st.session_state.get(f"cust_e_{i}", ""), "sl_str": st.session_state.get(f"cust_sl_{i}", ""), "tp_str": st.session_state.get(f"cust_tp_{i}", "")} for i in range(st.session_state.get("custom_n_entries", 0))]
                planning_result = planning_logic.calculate_custom_trade_plan(num_entries_custom=st.session_state.custom_n_entries, risk_pct_custom_input=risk_to_use, custom_entries_details=custom_entries, current_active_balance=active_balance_to_use)
        
        st.session_state.planning_result = planning_result
        st.session_state.entry_data_for_saving = planning_result.get('entry_data', [])
        
        st.markdown("---")
        st.subheader("💾 บันทึกแผน & ตรวจสอบ Drawdown")
        all_logs = gs_handler.load_all_planned_trade_logs_from_gsheets()
        portfolio_logs = pd.DataFrame()
        if new_active_id and not all_logs.empty:
            portfolio_logs = all_logs[all_logs['PortfolioID'] == str(new_active_id)]
        drawdown_today = analytics_engine.get_today_drawdown(portfolio_logs)
        drawdown_limit_absolute = -abs(active_balance_to_use * (drawdown_limit_pct / 100.0))
        st.markdown(f"**DD วันนี้ (จากแผน):** <font color='{'red' if drawdown_today < 0 else 'white'}'>{drawdown_today:,.2f} USD</font>", unsafe_allow_html=True)
        st.markdown(f"**DD Limit ({drawdown_limit_pct:.1f}%):** {drawdown_limit_absolute:,.2f} USD")
        
        if st.button("💾 Save Plan", use_container_width=True):
            if not new_active_id: st.error("❌ กรุณาเลือกพอร์ตก่อนบันทึก")
            elif not st.session_state.get('entry_data_for_saving'): st.warning("⚠️ ไม่มีข้อมูลแผนให้บันทึก")
            elif drawdown_today <= drawdown_limit_absolute: st.error(f"‼️ หยุดเทรด! ขาดทุนเกินลิมิต")
            else:
                current_mode = st.session_state.mode
                Symbol_to_save = st.session_state.get('fibo_asset') if current_mode == "FIBO" else st.session_state.get('custom_asset')
                risk_pct_to_save = risk_to_use
                direction_to_save = planning_result.get('direction', 'N/A')
                success = gs_handler.save_plan_to_gsheets(plan_data_list=st.session_state.entry_data_for_saving, trade_mode_arg=current_mode, Symbol_name=Symbol_to_save, risk_percentage=risk_pct_to_save, trade_direction=direction_to_save, portfolio_id=new_active_id, portfolio_name=selected_name)
                
                if success:
                    st.success("✔️ บันทึกแผนสำเร็จ!"); st.balloons(); st.rerun()
                else:
                    st.error("❌ เกิดข้อผิดพลาดในการบันทึกแผน")