# app.py (ฉบับแก้ไขและจัดระเบียบใหม่)

# --- ลำดับการ Import ที่ถูกต้อง ---
# 1. Standard & Third-Party Libraries
import streamlit as st
import pandas as pd
from datetime import datetime

# 2. ตั้งค่าหน้าเว็บเป็นคำสั่งแรกสุดของ Streamlit
# การย้าย st.set_page_config() มาไว้ที่นี่จะแก้ปัญหา StreamlitSetPageConfigMustBeFirstCommandError ได้อย่างถาวร
st.set_page_config(
    page_title="Ultimate Chart Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 3. Local Application Modules
from config import settings
from core import gs_handler, analytics_engine
from ui import (
    sidebar,
    portfolio_section,
    statement_section,
    entry_table_section,
    chart_section,
    log_viewer_section,
    ai_section
)

# ============================== SESSION STATE INITIALIZATION (GLOBAL SCOPE) ==============================
if 'initial_portfolio_setup_done' not in st.session_state:
    st.session_state.initial_portfolio_setup_done = False
if 'uploader_key_version' not in st.session_state:
    st.session_state.uploader_key_version = 0
if 'latest_statement_equity' not in st.session_state:
    st.session_state.latest_statement_equity = None
if 'current_account_balance' not in st.session_state:
    st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
if 'active_portfolio_name_gs' not in st.session_state:
    st.session_state.active_portfolio_name_gs = ""
if 'active_portfolio_id_gs' not in st.session_state:
    st.session_state.active_portfolio_id_gs = None
if 'current_portfolio_details' not in st.session_state:
    st.session_state.current_portfolio_details = None
if 'plot_data' not in st.session_state:
    st.session_state.plot_data = None
if 'debug_statement_processing_v2' not in st.session_state:
    st.session_state['debug_statement_processing_v2'] = False

def initialize_session_state():
    """Centralized function to initialize all *other* session state variables."""
    states = {
        'asset_fibo_val_v2': "XAUUSD", 'risk_pct_fibo_val_v2': settings.DEFAULT_RISK_PERCENT,
        'direction_fibo_val_v2': "Long", 'swing_high_fibo_val_v2': "", 'swing_low_fibo_val_v2': "",
        'fibo_flags_v2': [True] * len(settings.FIBO_LEVELS_DEFINITIONS),
        'asset_custom_val_v2': "XAUUSD", 'risk_pct_custom_val_v2': settings.DEFAULT_RISK_PERCENT,
        'n_entry_custom_val_v2': 2, 'exp_pf_type_select_v8_key_form': "", 'mode': "FIBO",
        'drawdown_limit_pct': settings.DEFAULT_DRAWDOWN_LIMIT_PCT, 'scaling_step': settings.DEFAULT_SCALING_STEP,
        'min_risk_pct': settings.DEFAULT_MIN_RISK_PERCENT, 'max_risk_pct': settings.DEFAULT_MAX_RISK_PERCENT,
        'scaling_mode_radio_val': 'Manual', 'save_fibo': False, 'save_custom': False, 'entry_data_for_saving': [],
        'fibo_spread': 0.0,
    }
    for key, value in states.items():
        if key not in st.session_state:
            st.session_state[key] = value

    n_entries = st.session_state.get("n_entry_custom_val_v2", 2)
    for i in range(n_entries):
        if f"custom_entry_{i}_v3" not in st.session_state: st.session_state[f"custom_entry_{i}_v3"] = "0.00"
        if f"custom_sl_{i}_v3" not in st.session_state: st.session_state[f"custom_sl_{i}_v3"] = "0.00"
        if f"custom_tp_{i}_v3" not in st.session_state: st.session_state[f"custom_tp_{i}_v3"] = "0.00"

def main():
    """Main function to run the Streamlit application."""
    initialize_session_state()

    # --- 1. Initial Data Loading & Portfolio Setup ---
    df_portfolios_gs = gs_handler.load_portfolios_from_gsheets() 

    
    if not st.session_state.initial_portfolio_setup_done and not df_portfolios_gs.empty:
        st.session_state.active_portfolio_id_gs = df_portfolios_gs.iloc[0]['PortfolioID']
        st.session_state.active_portfolio_name_gs = df_portfolios_gs.iloc[0]['PortfolioName']
        st.session_state.initial_portfolio_setup_done = True

     # --- 2. Set Current Balance based on Active Portfolio ---
    if st.session_state.active_portfolio_id_gs:
        current_portfolio_details_df = df_portfolios_gs[df_portfolios_gs['PortfolioID'] == st.session_state.active_portfolio_id_gs]
        if not current_portfolio_details_df.empty:
            st.session_state.current_portfolio_details = current_portfolio_details_df.iloc[0].to_dict()
            st.session_state.latest_statement_equity = None # รีเซ็ตค่าเริ่มต้น

            df_summaries = gs_handler.load_statement_summaries_from_gsheets()

            if not df_summaries.empty:
                df_curve, realized_pnl, total_dep, total_with, net_profit_sheet = analytics_engine.calculate_true_equity_curve(
                    df_summaries=df_summaries,
                    portfolio_id=st.session_state.active_portfolio_id_gs
                )

                # เก็บผลลัพธ์ไว้ใน session_state
                st.session_state['df_equity_curve_data'] = df_curve
                st.session_state['realized_profit_loss'] = realized_pnl
                st.session_state['total_deposit_amount'] = total_dep
                st.session_state['total_withdrawal_amount'] = total_with
                st.session_state['total_net_profit_from_sheet'] = net_profit_sheet

                # --- VVVV START EDIT (เพิ่มส่วนนี้เข้ามา) VVVV ---
                # ตรวจสอบว่า df_curve (ข้อมูลสรุปของพอร์ต) มีข้อมูลหรือไม่
                if not df_curve.empty and 'Equity' in df_curve.columns:
                    # ดึงค่า Equity ล่าสุด (จากแถวสุดท้ายที่ถูกเรียงตามเวลาแล้ว)
                    latest_equity_from_summary = df_curve['Equity'].iloc[-1]
                    # นำค่าที่ได้ไปอัปเดต session_state
                    st.session_state.latest_statement_equity = latest_equity_from_summary
                # --- ^^^^ END EDIT ^^^^ ---

            if st.session_state.latest_statement_equity is not None:
                st.session_state.current_account_balance = st.session_state.latest_statement_equity
            elif 'InitialBalance' in st.session_state.current_portfolio_details and pd.notna(st.session_state.current_portfolio_details['InitialBalance']):
                st.session_state.current_account_balance = float(st.session_state.current_portfolio_details['InitialBalance'])
            else:
                st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
    else:
        st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
        st.session_state.latest_statement_equity = None
        st.session_state.current_portfolio_details = None
        st.session_state.active_portfolio_name_gs = ""


        
    # --- 3. Render Sidebar (this also sets the active portfolio from user input) ---
    sidebar.render_sidebar()
    
    # --- 4. Proactive AI Section (runs before main UI) ---
    active_id = st.session_state.get('active_portfolio_id_gs')
    if active_id:
        # Weekly Summary
        df_actual_trades = gs_handler.load_actual_trades_from_gsheets()
        summary_message = analytics_engine.generate_weekly_summary(df_all_actual_trades=df_actual_trades, active_portfolio_id=active_id)
        if summary_message:
            current_week_key = f"summary_shown_{datetime.now().isocalendar().year}_{datetime.now().isocalendar().week}"
            if not st.session_state.get(current_week_key, False):
                with st.container(border=True):
                    st.markdown("##### 📝 Last Week's Performance Summary") 
                    st.info(summary_message)
                st.session_state[current_week_key] = True
        
        # Risk Alerts
        df_planned_logs = gs_handler.load_all_planned_trade_logs_from_gsheets()
        active_planned_logs = pd.DataFrame()
        if not df_planned_logs.empty and 'PortfolioID' in df_planned_logs.columns:
            active_planned_logs = df_planned_logs[df_planned_logs['PortfolioID'] == active_id]
        alerts = analytics_engine.generate_risk_alerts(
            df_planned_logs=active_planned_logs,
            daily_drawdown_limit_pct=st.session_state.get('drawdown_limit_pct', settings.DEFAULT_DRAWDOWN_LIMIT_PCT),
            current_balance=st.session_state.get('current_account_balance', settings.DEFAULT_ACCOUNT_BALANCE)
        )
        for alert in alerts:
            st.toast(alert['message'], icon="‼️" if alert['level'] == 'error' else "⚠️")

    # --- 5. Render Main Area Sections ---
    with st.container():
        portfolio_section.render_portfolio_manager_expander(df_portfolios_gs)
        statement_section.render_statement_section(df_portfolios_gs=df_portfolios_gs)
        entry_table_section.render_entry_table_section()
        chart_section.render_chart_section()
        ai_section.render_ai_section()
        log_viewer_section.render_log_viewer_section()

if __name__ == '__main__':
    main()