# ui/portfolio_header_section.py
import streamlit as st
import pandas as pd
from datetime import datetime
from ui.ai_section import render_ai_insights 

def _render_prop_firm_header(details: dict):
    """Renders the header for Prop Firm Challenge or Funded Account types."""
    
    header_title = details.get('PortfolioName', 'N/A')
    if pd.notna(details.get('EvaluationStep')):
        header_title += f" - {details['EvaluationStep']}"
    
    st.subheader(header_title)
    
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**ประเภท:** {details.get('ProgramType', 'N/A')}")
        st.markdown(f"**สถานะ:** {details.get('Status', 'N/A')}")
        
        initial_balance = float(details.get('InitialBalance', 0))
        current_equity = float(details.get('latest_statement_equity', initial_balance))
        
        net_pl = current_equity - initial_balance
        net_pl_percent = (net_pl / initial_balance) * 100 if initial_balance > 0 else 0
        
        st.metric(
            label="ยอดเงินปัจจุบัน (Equity)",
            value=f"{current_equity:,.2f} USD"
        )
        st.metric(
            label="กำไร/ขาดทุนสุทธิ (Net P/L)",
            value=f"{net_pl:,.2f} USD",
            delta=f"{net_pl_percent:.2f}%"
        )

    with col2:
        st.markdown("---")
        profit_target_pct = float(details.get('ProfitTargetPercent', 0))
        if profit_target_pct > 0:
            st.markdown(f"**🎯 เป้าหมายกำไร ({profit_target_pct:.1f}%)**")
            progress_value = (net_pl_percent / profit_target_pct) if profit_target_pct > 0 else 0
            st.progress(min(progress_value, 1.0))
            target_amount = initial_balance * (profit_target_pct / 100)
            st.caption(f"ทำได้แล้ว {net_pl_percent:.2f}% / เหลืออีก {max(profit_target_pct - net_pl_percent, 0):.2f}% ({net_pl:,.2f} / {target_amount:,.2f} USD)")

        st.markdown(f"**🚨 กฎ Drawdown:**")
        daily_loss_limit_pct = float(details.get('DailyLossLimitPercent', 0))
        total_stopout_pct = float(details.get('TotalStopoutPercent', 0))
        daily_limit_amount = initial_balance * (daily_loss_limit_pct / 100)
        total_limit_amount = initial_balance * (total_stopout_pct / 100)

        st.markdown(f"<ul><li>DD ต่อวัน ({daily_loss_limit_pct:.1f}%): <b>-{daily_limit_amount:,.2f} USD</b></li><li>DD รวม ({total_stopout_pct:.1f}%): <b>-{total_limit_amount:,.2f} USD</b></li></ul>", unsafe_allow_html=True)

def _render_competition_header(details: dict):
    """Renders the header for Trading Competition type."""
    st.subheader(details.get('PortfolioName', 'N/A'))
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**ประเภท:** {details.get('ProgramType', 'N/A')}")
        st.markdown(f"**สถานะ:** {details.get('Status', 'N/A')}")
        st.markdown(f"**ตัวชี้วัดหลัก:** {details.get('GoalMetric', 'N/A')}")
        current_performance = float(details.get('current_performance_metric', 0))
        st.metric(label="ผลงานปัจจุบัน", value=f"+{current_performance:.2f}%")
    with col2:
        st.markdown("---")
        st.markdown("**🗓️ สถานะการแข่งขัน**")
        end_date_str = details.get('CompetitionEndDate')
        if pd.notna(end_date_str):
            end_date = datetime.strptime(str(end_date_str).split(" ")[0], '%Y-%m-%d')
            time_left = end_date - datetime.now()
            if time_left.total_seconds() > 0:
                st.info(f"**สิ้นสุดใน: {time_left.days} วัน {time_left.seconds // 3600} ชั่วโมง**")
            else:
                st.error("**การแข่งขันสิ้นสุดแล้ว**")
        
        st.markdown(f"**🚨 กฎการแข่งขัน:**")
        daily_loss_limit_pct = float(details.get('DailyLossLimitPercent', 0))
        total_stopout_pct = float(details.get('TotalStopoutPercent', 0))
        initial_balance = float(details.get('InitialBalance', 1))
        daily_limit_amount = initial_balance * (daily_loss_limit_pct / 100)
        total_limit_amount = initial_balance * (total_stopout_pct / 100)
        st.markdown(f"<ul><li>DD ต่อวัน ({daily_loss_limit_pct:.1f}%): <b>-{daily_limit_amount:,.2f} USD</b></li><li>DD รวม ({total_stopout_pct:.1f}%): <b>-{total_limit_amount:,.2f} USD</b></li></ul>", unsafe_allow_html=True)


def _render_personal_header(details: dict):
    """Renders the detailed header for Personal Account type."""
    st.subheader(details.get('PortfolioName', 'N/A'))
    
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**ประเภท:** {details.get('ProgramType', 'N/A')}")
        st.markdown(f"**สถานะ:** {details.get('Status', 'N/A')}")
        
        initial_balance = float(details.get('InitialBalance', 0))
        current_equity = float(details.get('latest_statement_equity', initial_balance))
        
        net_pl = current_equity - initial_balance
        net_pl_percent = (net_pl / initial_balance) * 100 if initial_balance > 0 else 0
        
        st.metric(label="ยอดเงินปัจจุบัน (Equity)", value=f"{current_equity:,.2f} USD")
        st.metric(label="กำไร/ขาดทุนสุทธิ (Net P/L)", value=f"{net_pl:,.2f} USD", delta=f"{net_pl_percent:.2f}%")

    with col2:
        st.markdown("---")
        # --- Personal Goals ---
        st.markdown(f"**🎯 เป้าหมายส่วนตัว**")
        overall_profit_target = float(details.get('OverallProfitTarget', 0))
        if overall_profit_target > 0:
            progress_value = (net_pl / overall_profit_target) if overall_profit_target > 0 else 0
            st.progress(min(progress_value, 1.0))
            st.caption(f"เป้าหมายกำไรรวม: {net_pl:,.2f} / {overall_profit_target:,.2f} USD")
        else:
            st.caption("ยังไม่ได้ตั้งเป้าหมายกำไรรวม")
        
        # --- Personal Risk Limits ---
        st.markdown(f"**⚠️ ขีดจำกัดความเสี่ยงที่ตั้งไว้**")
        max_dd_overall = float(details.get('MaxAcceptableDrawdownOverall', 0))
        st.caption(f"ขาดทุนรวมที่ยอมรับได้: {max_dd_overall:,.2f} USD")

        # --- Scaling Manager ---
        enable_scaling = str(details.get('EnableScaling', "False")).upper() == 'TRUE'
        if enable_scaling:
            st.markdown(f"**⚙️ การตั้งค่า Scaling**")
            current_risk = float(details.get('CurrentRiskPercent', 0))
            st.caption(f"เปิดใช้งาน Scaling Manager | ความเสี่ยงปัจจุบัน: {current_risk:.2f}%")
        else:
            st.caption("ไม่ได้เปิดใช้งาน Scaling Manager")


def render_portfolio_header(portfolio_details: dict):
    """
    Main function to render the portfolio header.
    It dynamically calls the appropriate render function based on ProgramType.
    """
    if not portfolio_details:
        st.info("กรุณาเลือกพอร์ตที่ใช้งานเพื่อดูข้อมูลสรุป")
        return

    program_type = portfolio_details.get("ProgramType")

    with st.container(border=True):
        if program_type in ["Prop Firm Challenge", "Funded Account"]:
            _render_prop_firm_header(portfolio_details)
        elif program_type == "Trading Competition":
            _render_competition_header(portfolio_details)
        else: # Handles "Personal Account" and any other types
            _render_personal_header(portfolio_details)