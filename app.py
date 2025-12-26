# app.py (ฉบับแก้ไขสมบูรณ์)

import streamlit as st
import pandas as pd
from datetime import datetime

# --- ตั้งค่าหน้าเว็บเป็นคำสั่งแรกสุด ---
st.set_page_config(
    page_title="Ultimate Chart Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Local Application Modules (นำกลับมาทั้งหมด) ---
from config import settings
from core import supabase_handler as db_handler, analytics_engine
from ui import (
    sidebar,
    portfolio_section,
    statement_section,
    ai_section,
    consistency_section,
    edge_score_section,
    topstep_section,
    checklist_section  
)

# ============================== SESSION STATE INITIALIZATION ==============================
if 'initial_portfolio_setup_done' not in st.session_state:
    st.session_state.initial_portfolio_setup_done = False
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0
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

def initialize_session_state():
    """Centralized function to initialize all *other* session state variables."""
    states = {
        'mode': "FIBO",
        'drawdown_limit_pct': settings.DEFAULT_DRAWDOWN_LIMIT_PCT,
    }
    for key, value in states.items():
        if key not in st.session_state:
            st.session_state[key] = value

def main():
    """Main function to run the Streamlit application."""
    initialize_session_state()
    supabase_client = db_handler.get_supabase_client()
    df_portfolios_gs = db_handler.load_portfolios()  
    
    if not st.session_state.initial_portfolio_setup_done and not df_portfolios_gs.empty:
        st.session_state.active_portfolio_id_gs = df_portfolios_gs.iloc[0]['PortfolioID']
        st.session_state.active_portfolio_name_gs = df_portfolios_gs.iloc[0]['PortfolioName']
        st.session_state.initial_portfolio_setup_done = True

    # ======================================================================================
    # --- START: โค้ดที่แก้ไขตรรกะการจัดการ BALANCE ทั้งหมด ---
    # ======================================================================================
    if st.session_state.active_portfolio_id_gs:
        current_portfolio_details_df = df_portfolios_gs[df_portfolios_gs['PortfolioID'] == st.session_state.active_portfolio_id_gs]
        st.session_state.current_portfolio_details = current_portfolio_details_df.iloc[0].to_dict() if not current_portfolio_details_df.empty else None

        latest_equity_from_sheet = None
        df_summaries = db_handler.load_statement_summaries()
        
        if not df_summaries.empty:
            # ---- START: การแก้ไขที่สำคัญที่สุด ----
            # บังคับให้คอลัมน์ PortfolioID เป็นประเภท string เพื่อให้การเปรียบเทียบถูกต้องเสมอ
            if 'PortfolioID' in df_summaries.columns:
                df_summaries['PortfolioID'] = df_summaries['PortfolioID'].astype(str)
            # ---- END: การแก้ไขที่สำคัญที่สุด ----

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
                cleaned_equity_str = str(final_equity_value).replace(',', '').replace(' ', '')
                st.session_state.current_account_balance = float(cleaned_equity_str)
            except (ValueError, TypeError):
                if st.session_state.current_portfolio_details and pd.notna(st.session_state.current_portfolio_details.get('InitialBalance')):
                    cleaned_initial_balance = str(st.session_state.current_portfolio_details['InitialBalance']).replace(',', '').replace(' ', '')
                    st.session_state.current_account_balance = float(cleaned_initial_balance)
                else:
                    st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
        elif st.session_state.current_portfolio_details and pd.notna(st.session_state.current_portfolio_details.get('InitialBalance')):
            cleaned_initial_balance = str(st.session_state.current_portfolio_details['InitialBalance']).replace(',', '').replace(' ', '')
            st.session_state.current_account_balance = float(cleaned_initial_balance)
        else:
            st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
    else:
        st.session_state.current_account_balance = settings.DEFAULT_ACCOUNT_BALANCE
        st.session_state.latest_statement_equity = None
        st.session_state.current_portfolio_details = None
        st.session_state.active_portfolio_name_gs = ""
    # ======================================================================================
    # --- END: สิ้นสุดส่วนแก้ไขตรรกะ BALANCE ---
    # ======================================================================================
        
    sidebar.render_sidebar()
    
    active_id = st.session_state.get('active_portfolio_id_gs')
    #if active_id:
    #    df_actual_trades = db_handler.load_actual_trades()
    #    summary_message = analytics_engine.generate_weekly_summary(df_all_actual_trades=df_actual_trades, active_portfolio_id=active_id)
    #    if summary_message and not st.session_state.get(f"summary_shown_{datetime.now().isocalendar().week}", False):
    #        st.info(summary_message)
    #        st.session_state[f"summary_shown_{datetime.now().isocalendar().week}"] = True

    with st.container():
        if hasattr(checklist_section, 'render_checklist_section'):
            checklist_section.render_checklist_section(supabase_client)
        if hasattr(topstep_section, 'render_topstep_section'):
            topstep_section.render_topstep_section()    
        st.divider()      
        if hasattr(consistency_section, 'render_consistency_section'):
            consistency_section.render_consistency_section()
        if hasattr(edge_score_section, 'render_edge_score_section'):
            edge_score_section.render_edge_score_section(analytics_engine, db_handler)      
        if hasattr(portfolio_section, 'render_portfolio_manager_expander'):
            portfolio_section.render_portfolio_manager_expander(db_handler, df_portfolios_gs)   
        if hasattr(statement_section, 'render_statement_section'):
            statement_section.render_statement_section()
        if hasattr(ai_section, 'render_ai_section'):
            ai_section.render_ai_section()

if __name__ == '__main__':
    main()
 