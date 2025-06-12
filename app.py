# app.py

from datetime import datetime
import streamlit as st
import pandas as pd
from config import settings
from core import gs_handler
from core import analytics_engine

# Import UI modules
from ui import (
    sidebar,
    portfolio_section,
    statement_section,
    entry_table_section,
    chart_section,
    ai_section,
    log_viewer_section,
)

# Import necessary core modules for initial data loading in main()
from core.gs_handler import load_portfolios_from_gsheets, load_statement_summaries_from_gsheets


# ============================== SESSION STATE INITIALIZATION ==============================
# [แก้ไข] เปลี่ยนมาใช้ 'active_portfolio_id' เป็นตัวแปรหลักเพียงตัวเดียว
if 'active_portfolio_id' not in st.session_state:
    st.session_state['active_portfolio_id'] = None

# ส่วนที่เหลือส่วนใหญ่ยังคงเหมือนเดิม
if 'current_portfolio_details' not in st.session_state:
    st.session_state['current_portfolio_details'] = None
if 'current_account_balance' not in st.session_state:
    st.session_state['current_account_balance'] = settings.DEFAULT_ACCOUNT_BALANCE
if 'uploader_key_version' not in st.session_state:
    st.session_state.uploader_key_version = 0
if 'latest_statement_equity' not in st.session_state:
    st.session_state.latest_statement_equity = None
if 'plot_data' not in st.session_state:
    st.session_state.plot_data = None
if '_UPLOAD_PROCESSED_IN_THIS_CYCLE_v2' not in st.session_state:
    st.session_state['_UPLOAD_PROCESSED_IN_THIS_CYCLE_v2'] = False
if 'debug_statement_processing_v2' not in st.session_state:
    st.session_state['debug_statement_processing_v2'] = False

# [ลบออก] ลบตัวแปรเก่าที่ซ้ำซ้อนทิ้งเพื่อป้องกันการสับสน
if 'active_portfolio_id_gs' in st.session_state:
    del st.session_state['active_portfolio_id_gs']
if 'active_portfolio_name_gs' in st.session_state:
    del st.session_state['active_portfolio_name_gs']


def initialize_session_state():
    """
    ฟังก์ชันนี้ยังคงอยู่เหมือนเดิม สำหรับการตั้งค่า session state อื่นๆ
    """
    states = {
        'Symbol_fibo_val_v2': "XAUUSD",
        'risk_pct_fibo_val_v2': settings.DEFAULT_RISK_PERCENT,
        'direction_fibo_val_v2': "Long",
        'swing_high_fibo_val_v2': "",
        'swing_low_fibo_val_v2': "",
        'fibo_flags_v2': [True] * len(settings.FIBO_LEVELS_DEFINITIONS),
        'Symbol_custom_val_v2': "XAUUSD",
        'risk_pct_custom_val_v2': settings.DEFAULT_RISK_PERCENT,
        'n_entry_custom_val_v2': 2,
        'exp_pf_type_select_v8_key_form': "", 
        'mode': "FIBO",
        'drawdown_limit_pct': settings.DEFAULT_DRAWDOWN_LIMIT_PCT,
        'scaling_step': settings.DEFAULT_SCALING_STEP,
        'min_risk_pct': settings.DEFAULT_MIN_RISK_PERCENT,
        'max_risk_pct': settings.DEFAULT_MAX_RISK_PERCENT,
        'scaling_mode_radio_val': 'Manual',
        'save_fibo': False,
        'save_custom': False,
        'entry_data_for_saving': [],
    }
    for key, value in states.items():
        if key not in st.session_state:
            st.session_state[key] = value
    n_entries = st.session_state.get("n_entry_custom_val_v2", 2)
    for i in range(n_entries):
        if f"custom_entry_{i}_v3" not in st.session_state: st.session_state[f"custom_entry_{i}_v3"] = "0.00"
        if f"custom_sl_{i}_v3" not in st.session_state: st.session_state[f"custom_sl_{i}_v3"] = "0.00"
        if f"custom_tp_{i}_v3" not in st.session_state: st.session_state[f"custom_tp_{i}_v3"] = "0.00"


# app.py

from datetime import datetime
import streamlit as st
import pandas as pd
from config import settings
from core import gs_handler
from core import analytics_engine

# Import UI modules
from ui import (
    sidebar,
    portfolio_section,
    statement_section,
    entry_table_section,
    chart_section,
    ai_section,
    log_viewer_section,
)

# Import necessary core modules for initial data loading in main()
from core.gs_handler import load_portfolios_from_gsheets, load_statement_summaries_from_gsheets


# ============================== SESSION STATE INITIALIZATION ==============================
# [แก้ไข] เปลี่ยนมาใช้ 'active_portfolio_id' เป็นตัวแปรหลักเพียงตัวเดียว
if 'active_portfolio_id' not in st.session_state:
    st.session_state['active_portfolio_id'] = None

# ส่วนที่เหลือส่วนใหญ่ยังคงเหมือนเดิม
if 'current_portfolio_details' not in st.session_state:
    st.session_state['current_portfolio_details'] = None
if 'current_account_balance' not in st.session_state:
    st.session_state['current_account_balance'] = settings.DEFAULT_ACCOUNT_BALANCE
if 'uploader_key_version' not in st.session_state:
    st.session_state.uploader_key_version = 0
if 'latest_statement_equity' not in st.session_state:
    st.session_state.latest_statement_equity = None
if 'plot_data' not in st.session_state:
    st.session_state.plot_data = None
if '_UPLOAD_PROCESSED_IN_THIS_CYCLE_v2' not in st.session_state:
    st.session_state['_UPLOAD_PROCESSED_IN_THIS_CYCLE_v2'] = False
if 'debug_statement_processing_v2' not in st.session_state:
    st.session_state['debug_statement_processing_v2'] = False

# [ลบออก] ลบตัวแปรเก่าที่ซ้ำซ้อนทิ้งเพื่อป้องกันการสับสน
if 'active_portfolio_id_gs' in st.session_state:
    del st.session_state['active_portfolio_id_gs']
if 'active_portfolio_name_gs' in st.session_state:
    del st.session_state['active_portfolio_name_gs']


def initialize_session_state():
    """
    ฟังก์ชันนี้ยังคงอยู่เหมือนเดิม สำหรับการตั้งค่า session state อื่นๆ
    """
    states = {
        'Symbol_fibo_val_v2': "XAUUSD",
        'risk_pct_fibo_val_v2': settings.DEFAULT_RISK_PERCENT,
        'direction_fibo_val_v2': "Long",
        'swing_high_fibo_val_v2': "",
        'swing_low_fibo_val_v2': "",
        'fibo_flags_v2': [True] * len(settings.FIBO_LEVELS_DEFINITIONS),
        'Symbol_custom_val_v2': "XAUUSD",
        'risk_pct_custom_val_v2': settings.DEFAULT_RISK_PERCENT,
        'n_entry_custom_val_v2': 2,
        'exp_pf_type_select_v8_key_form': "", 
        'mode': "FIBO",
        'drawdown_limit_pct': settings.DEFAULT_DRAWDOWN_LIMIT_PCT,
        'scaling_step': settings.DEFAULT_SCALING_STEP,
        'min_risk_pct': settings.DEFAULT_MIN_RISK_PERCENT,
        'max_risk_pct': settings.DEFAULT_MAX_RISK_PERCENT,
        'scaling_mode_radio_val': 'Manual',
        'save_fibo': False,
        'save_custom': False,
        'entry_data_for_saving': [],
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
    """[แก้ไข] Main function to run the Streamlit application."""
    st.set_page_config(page_title="Ultimate-Chart", layout="wide")

    initialize_session_state()

    # --- 1. เรียก Sidebar เพื่อรับ Input จากผู้ใช้ (เช่น การเลือกพอร์ต) ---
    sidebar.render_sidebar()

    # --- 2. [เพิ่มกลับเข้ามา] Logic การโหลดข้อมูลหลักตามพอร์ตที่เลือก ---
    # app.py จะทำหน้าที่เป็นศูนย์กลางในการจัดการข้อมูลหลังจาก Sidebar กำหนด active_portfolio_id
    active_id = st.session_state.get('active_portfolio_id')
    if active_id:
        # โหลด details ของพอร์ตที่เลือก
        if not st.session_state.get('current_portfolio_details'):
            df_portfolios = gs_handler.load_portfolios_from_gsheets()
            if not df_portfolios.empty:
                details_df = df_portfolios[df_portfolios['PortfolioID'] == active_id]
                if not details_df.empty:
                    st.session_state.current_portfolio_details = details_df.iloc[0].to_dict()
        
        # โหลด Equity ล่าสุดและกำหนด Balance ที่จะใช้
        df_summaries = gs_handler.load_statement_summaries_from_gsheets()
        latest_equity = None
        if not df_summaries.empty:
            df_pf_summaries = df_summaries[df_summaries['PortfolioID'] == str(active_id)].copy()
            if not df_pf_summaries.empty:
                df_pf_summaries['Timestamp'] = pd.to_datetime(df_pf_summaries['Timestamp'], errors='coerce')
                df_pf_summaries.dropna(subset=['Equity', 'Timestamp'], inplace=True)
                if not df_pf_summaries.empty:
                    latest_equity = float(df_pf_summaries.sort_values(by='Timestamp', ascending=False).iloc[0]['Equity'])
        
        st.session_state.latest_statement_equity = latest_equity
        
        if latest_equity is not None:
            st.session_state.current_account_balance = latest_equity
        elif st.session_state.get('current_portfolio_details'):
            st.session_state.current_account_balance = float(st.session_state.current_portfolio_details.get('InitialBalance', settings.DEFAULT_ACCOUNT_BALANCE))
        else:
            st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE

    # --- 3. ส่วน Proactive AI (ทำงานโดยใช้ข้อมูลที่โหลดด้านบน) ---
    if active_id:
        # ส่วนแจ้งเตือนความเสี่ยง
        df_planned_logs = gs_handler.load_all_planned_trade_logs_from_gsheets()
        drawdown_limit = st.session_state.get('drawdown_limit_pct_input', 2.0)
        balance = st.session_state.get('current_account_balance', settings.DEFAULT_ACCOUNT_BALANCE)
        alerts = analytics_engine.generate_risk_alerts(
            df_planned_logs=df_planned_logs[df_planned_logs['PortfolioID'] == active_id] if not df_planned_logs.empty else pd.DataFrame(),
            daily_drawdown_limit_pct=drawdown_limit,
            current_balance=balance
        )
        for alert in alerts:
            st.toast(alert['message'], icon="‼️" if alert['level'] == 'error' else "⚠️")

        # ส่วนสรุปผลงานรายสัปดาห์
        df_actual_trades = gs_handler.load_actual_trades_from_gsheets()
        summary_message = analytics_engine.generate_weekly_summary(
            df_all_actual_trades=df_actual_trades,
            active_portfolio_id=active_id
        )
        if summary_message:
            current_week_key = f"summary_shown_{datetime.now().isocalendar().year}_{datetime.now().isocalendar().week}"
            if not st.session_state.get(current_week_key, False):
                with st.container(border=True):
                    st.subheader("📝 สรุปผลงานสัปดาห์ที่ผ่านมา")
                    st.info(summary_message)
                st.session_state[current_week_key] = True

    # --- 4. Render Main Area Sections ---
    with st.container():
        portfolio_section.render_portfolio_manager_expander()
        statement_section.render_statement_section()
        entry_table_section.render_entry_table_section()
        chart_section.render_chart_section()
        ai_section.render_ai_section()
        log_viewer_section.render_log_viewer_section()

if __name__ == '__main__':
    main()