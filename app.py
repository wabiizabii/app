# app.py (ฉบับแก้ไข - ตัดระบบ Login ออก)

import streamlit as st
import pandas as pd
from datetime import datetime

# --- ตั้งค่าหน้าเว็บเป็นคำสั่งแรกสุด ---
st.set_page_config(
    page_title="Ultimate Chart Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Local Application Modules ---
from config import settings
from core import supabase_handler as db_handler, analytics_engine
from ui import (
    sidebar,
    portfolio_section,
    statement_section,
    entry_table_section,
    chart_section,
    log_viewer_section,
    ai_section
)

# ============================== SESSION STATE INITIALIZATION ==============================
# ลบการตั้งค่า session state ที่เกี่ยวข้องกับ Login ออก
# if 'user_logged_in' not in st.session_state:
#     st.session_state.user_logged_in = False
# if 'user_profile' not in st.session_state:
#     st.session_state.user_profile = None
# if 'is_admin_approved' not in st.session_state:
#     st.session_state.is_admin_approved = False
# if 'approval_status' not in st.session_state:
#     st.session_state.approval_status = "pending"
# if 'auth_flow_active' not in st.session_state:
#     st.session_state.auth_flow_active = False
# if 'pkce_code_verifier' not in st.session_state:
#     st.session_state['pkce_code_verifier'] = None
# if 'oauth_url' not in st.session_state:
#     st.session_state['oauth_url'] = None

if 'initial_portfolio_setup_done' not in st.session_state:
    st.session_state.initial_portfolio_setup_done = False
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

# ============================== HARDCODED USER ID ==============================
# User ID ที่ดึงมาจาก Screenshot ของคุณ
HARDCODED_USER_ID = "7bfef03f-22f5-404c-b946-2b3b77a28b91" # <<< อัปเดต User ID ตรงนี้

def initialize_session_state():
    """Centralized function to initialize all *other* session state variables."""
    states = {
        'mode': "FIBO",
        'drawdown_limit_pct': settings.DEFAULT_DRAWDOWN_LIMIT_PCT,
        'user_id': HARDCODED_USER_ID, # <<< เพิ่ม user_id เข้าไปใน session state
    }
    for key, value in states.items():
        if key not in st.session_state:
            st.session_state[key] = value

def main():
    """Main function to run the Streamlit application."""
    initialize_session_state()

    # กำหนด user_id ให้เป็นค่าคงที่ที่ใช้ในทุกการดำเนินการ
    current_user_id = st.session_state.get('user_id')

    if not current_user_id:
        st.error("Error: Hardcoded user ID not set. Please set HARDCODED_USER_ID in app.py.")
        st.stop() # หยุดการทำงานถ้าไม่มี user_id

    # ลบโค้ดทั้งหมดที่เกี่ยวข้องกับการ Login/Sign Up/OAuth
    # if st.session_state.user_logged_in == False:
    #     # โค้ดที่เกี่ยวข้องกับการ Login/Sign Up/OAuth ทั้งหมด
    #     # ... (ตัดออกไปทั้งหมด)
    #     st.stop()

    # --- โหลดข้อมูลทั้งหมดโดยใช้ user_id ---
    # แก้ไขการเรียก load_portfolios ให้ส่ง user_id เข้าไป
    df_portfolios_gs = db_handler.load_portfolios(user_id=current_user_id)

    if not st.session_state.initial_portfolio_setup_done and not df_portfolios_gs.empty:
        st.session_state.active_portfolio_id_gs = df_portfolios_gs.iloc[0]['PortfolioID']
        st.session_state.active_portfolio_name_gs = df_portfolios_gs.iloc[0]['PortfolioName']
        st.session_state.initial_portfolio_setup_done = True

    # --- ตรรกะการจัดการ BALANCE ---
    if st.session_state.active_portfolio_id_gs:
        current_portfolio_details_df = df_portfolios_gs[df_portfolios_gs['PortfolioID'] == st.session_state.active_portfolio_id_gs]
        st.session_state.current_portfolio_details = current_portfolio_details_df.iloc[0].to_dict() if not current_portfolio_details_df.empty else None

        latest_equity_from_sheet = None
        # แก้ไขการเรียก load_statement_summaries ให้ส่ง user_id เข้าไป
        df_summaries = db_handler.load_statement_summaries(user_id=current_user_id)

        if not df_summaries.empty:
            if 'PortfolioID' in df_summaries.columns:
                df_summaries['PortfolioID'] = df_summaries['PortfolioID'].astype(str)

            portfolio_summaries = df_summaries[df_summaries['PortfolioID'] == st.session_state.active_portfolio_id_gs].copy()

            if not portfolio_summaries.empty:
                portfolio_summaries['Timestamp'] = pd.to_datetime(portfolio_summaries['Timestamp'], errors='coerce')
                portfolio_summaries.dropna(subset=['Timestamp'], inplace=True)

                if not portfolio_summaries.empty:
                    latest_row = portfolio_summaries.sort_values(by='Timestamp', ascending=False).iloc[0]
                    equity_value = latest_row.get('Equity')
                    if equity_value is not None and str(equity_value).strip() != "":
                        latest_equity_from_sheet = equity_value

        if latest_equity_from_sheet is not None:
             st.session_state.latest_statement_equity = latest_equity_from_sheet

        final_equity_value = st.session_state.get('latest_statement_equity')

        if final_equity_value is not None:
            try:
                st.session_state.current_account_balance = float(str(final_equity_value).replace(',', '').replace(' ', ''))
            except (ValueError, TypeError):
                if st.session_state.current_portfolio_details and pd.notna(st.session_state.current_portfolio_details.get('InitialBalance')):
                    st.session_state.current_account_balance = float(str(st.session_state.current_portfolio_details['InitialBalance']).replace(',', '').replace(' ', ''))
                else:
                    st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
        elif st.session_state.current_portfolio_details and pd.notna(st.session_state.current_portfolio_details.get('InitialBalance')):
            st.session_state.current_account_balance = float(str(st.session_state.current_portfolio_details['InitialBalance']).replace(',', '').replace(' ', ''))
        else:
            st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
    else:
        st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
        st.session_state.latest_statement_equity = None
        st.session_state.current_portfolio_details = None
        st.session_state.active_portfolio_name_gs = ""

    # --- แสดงผล UI ทั้งหมด ---
    # ส่ง user_id เข้าไปใน sidebar
    sidebar.render_sidebar(df_portfolios=df_portfolios_gs, user_id=current_user_id)

    active_id = st.session_state.get('active_portfolio_id_gs')
    if active_id:
        # แก้ไขการเรียก load_actual_trades ให้ส่ง user_id เข้าไป
        df_actual_trades = db_handler.load_actual_trades(user_id=current_user_id)
        summary_message = analytics_engine.generate_weekly_summary(df_all_actual_trades=df_actual_trades, active_portfolio_id=active_id)
        if summary_message and not st.session_state.get(f"summary_shown_{datetime.now().isocalendar().week}", False):
            st.info(summary_message)
            st.session_state[f"summary_shown_{datetime.now().isocalendar().week}"] = True

    with st.container():
        # ส่ง user_id เข้าไปในแต่ละ section
        if hasattr(portfolio_section, 'render_portfolio_manager_expander'):
            portfolio_section.render_portfolio_manager_expander(user_id=current_user_id, db_handler=db_handler, df_portfolios=df_portfolios_gs)
        if hasattr(statement_section, 'render_statement_section'):
            statement_section.render_statement_section(user_id=current_user_id, df_portfolios_gs=df_portfolios_gs)
        if hasattr(entry_table_section, 'render_entry_table_section'):
            entry_table_section.render_entry_table_section()
        if hasattr(chart_section, 'render_chart_section'):
            chart_section.render_chart_section()
        if hasattr(ai_section, 'render_ai_section'):
            ai_section.render_ai_section(user_id=current_user_id)
        if hasattr(log_viewer_section, 'render_log_viewer_section'):
            log_viewer_section.render_log_viewer_section(user_id=current_user_id)

if __name__ == '__main__':
    main()
