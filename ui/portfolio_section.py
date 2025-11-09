# ui/portfolio_section.py (ฉบับแก้ไขสมบูรณ์ - แก้ไขทุกปัญหาที่พบ)

import streamlit as st
import pandas as pd
from datetime import date
# from .ai_section import render_ai_insights # Assuming this will be created later
from core import  portfolio_logic, analytics_engine
from config import settings # ตรวจสอบว่ามีบรรทัดนี้อยู่แล้ว (สำคัญ!)

# =============================================================================
# Helper & Rendering Functions
# =============================================================================

# <<<< เพิ่มฟังก์ชัน safe_float_convert ตรงนี้ (หากยังไม่มีในไฟล์นี้) >>>>
# ฟังก์ชัน safe_float_convert คัดลอกมาจาก ui/sidebar.py
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
# <<<< สิ้นสุดการเพิ่ม >>>>

def _render_portfolio_header(details: dict, df_actual_trades: pd.DataFrame, df_summaries: pd.DataFrame):
    """
    Renders the portfolio dashboard header with all statistics, translated to English.
    """
    if not details:
        st.info("Please select a portfolio from the sidebar to view details.")
        return

    # --- Fetch all statistics ---
    active_id = st.session_state.get('active_portfolio_id_gs')
    #advanced_stats = analytics_engine.get_advanced_statistics(df_all_actual_trades=df_actual_trades, active_portfolio_id=active_id)
    advanced_stats = {}
    #full_stats = analytics_engine.get_full_dashboard_stats(
    #    df_all_actual_trades=df_actual_trades,
    #    df_all_summaries=df_summaries,
    #    active_portfolio_id=active_id
    #)
    full_stats = {} 

    # --- Section 1: Title and Details Box ---
    with st.container(border=True):
        portfolio_name = details.get('PortfolioName', 'N/A')
        account_size = safe_float_convert(details.get('InitialBalance', 0)) # ใช้ safe_float_convert
        prog_type = details.get('ProgramType', 'N/A')
        profit_target = safe_float_convert(details.get('ProfitTargetPercent', 0)) # ใช้ safe_float_convert
        status = details.get('Status', 'N/A')

        title_part = f"<h5 style='margin: 0; padding: 0;'>Portfolio Overview: {portfolio_name}</h5>"
        detail_part = (
            f"**Account Size:** ${account_size:,.0f} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"**Program Type:** {prog_type} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"**Profit Target:** {profit_target}% &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"**Status:** {status}"
        )
        
        full_html = f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px;">
            <div>{title_part}</div>
            <div>{detail_part}</div>
        </div>
        """
        st.markdown(full_html, unsafe_allow_html=True)

    st.write("") 

    # --- Section 2: Two Main Columns ---
    main_col1, main_col2 = st.columns([1.5, 1.8])

    # Left Column (Advanced Statistics)
    with main_col1:
        st.markdown("##### Advanced Statistics")
        with st.container(border=True, height=310):
            if not advanced_stats:
                st.info("No advanced statistics available.")
            else:
                adv_col1, adv_col2 = st.columns(2)
                with adv_col1:
                    st.markdown("**Last 5 Trades Form:**")
                    st.code(f"Long : {advanced_stats.get('recent_form_long', 'N/A')}\nShort: {advanced_stats.get('recent_form_short', 'N/A')}")
                    st.markdown("**Consecutive Wins/Losses:**")
                    wins = advanced_stats.get('max_consecutive_wins')
                    loss = advanced_stats.get('max_consecutive_losses')
                    st.markdown(f"• Wins: `{int(safe_float_convert(wins))} trades`" if pd.notna(wins) else "• Wins: `N/A`") # ใช้ safe_float_convert
                    st.markdown(f"• Losses: `{int(safe_float_convert(loss))} trades`" if pd.notna(loss) else "• Losses: `N/A`") # ใช้ safe_float_convert
                
                with adv_col2:
                    st.markdown("**Biggest Win/Loss:**")
                    win_l = safe_float_convert(advanced_stats.get('biggest_win_long')) # ใช้ safe_float_convert
                    loss_l = safe_float_convert(advanced_stats.get('biggest_loss_long')) # ใช้ safe_float_convert
                    win_l_display = f"<font color='#28a745'>{win_l:,.2f}</font>" if pd.notna(win_l) else "N/A"
                    loss_l_display = f"<font color='#dc3545'>{loss_l:,.2f}</font>" if pd.notna(loss_l) else "N/A"
                    st.markdown(f"• Long: {win_l_display} / {loss_l_display}", unsafe_allow_html=True)

                    win_s = safe_float_convert(advanced_stats.get('biggest_win_short')) # ใช้ safe_float_convert
                    loss_s = safe_float_convert(advanced_stats.get('biggest_loss_short')) # ใช้ safe_float_convert
                    win_s_display = f"<font color='#28a745'>{win_s:,.2f}</font>" if pd.notna(win_s) else "N/A"
                    loss_s_display = f"<font color='#dc3545'>{loss_s:,.2f}</font>" if pd.notna(loss_s) else "N/A"
                    st.markdown(f"• Short: {win_s_display} / {loss_s_display}", unsafe_allow_html=True)

                    st.markdown("**Consistency:**")
                    conc = safe_float_convert(advanced_stats.get('profit_concentration', 0)) # ใช้ safe_float_convert
                    days = safe_float_convert(advanced_stats.get('active_trading_days', 0)) # ใช้ safe_float_convert
                    st.markdown(f"• Profit Conc.: `{conc:.1f}%`" if conc > 0 else "• Profit Conc.: `N/A`")
                    st.markdown(f"• Active Days: `{int(days)} days`" if pd.notna(days) else "• Active Days: `N/A`") # ใช้ int(days)

    # Right Column (Performance Metrics)
    with main_col2:
        st.markdown("##### Performance Metrics")
        with st.container(border=True, height=310):
            if not full_stats:
                st.info("No statistics available.")
            else:
                def format_metric(label, value, currency=False, percent=False, ratio=False, color_cond=False):
                    if pd.isna(value) or value == '':
                        val_str = "N/A"
                        color = "grey"
                    else:
                        color = "white"
                        val_str = str(value)
                        if isinstance(value, (int, float)):
                            if color_cond:
                                color = "#28a745" if value >= 0 else "#dc3545"
                            if currency:
                                val_str = f"${value:,.2f}"
                                if not color_cond:
                                    color = "#28a745" if value > 0 else "#dc3545" if value < 0 else "white"
                            elif percent:
                                val_str = f"{value:.2f}%"
                            elif ratio:
                                val_str = f"{value:.2f}"
                            else:
                                val_str = str(int(value))
                    return f"""
                    <div style="display: flex; justify-content: space-between; width: 100%; padding: 2px 0;">
                        <span style="text-align: left;"><b>{label}</b></span>
                        <span style="font-weight: bold; text-align: right; color: {color};">{val_str}</span>
                    </div>
                    """

                sub_col1, sub_col2 = st.columns(2)
                
                with sub_col1:
                    st.markdown(format_metric("Total Trades", safe_float_convert(full_stats.get('Total_Trades'))), unsafe_allow_html=True)
                    st.markdown(format_metric("Profit Trades", safe_float_convert(full_stats.get('Profit_Trades_Count'))), unsafe_allow_html=True)
                    st.markdown(format_metric("Loss Trades", safe_float_convert(full_stats.get('Loss_Trades_Count'))), unsafe_allow_html=True)
                    st.markdown(format_metric("Breakeven Trades", safe_float_convert(full_stats.get('Breakeven_Trades_Count'))), unsafe_allow_html=True)
                    st.markdown(format_metric("Long Trades", safe_float_convert(full_stats.get('Long_Trades_Count'))), unsafe_allow_html=True)
                    st.markdown(format_metric("Short Trades", safe_float_convert(full_stats.get('Short_Trades_Count'))), unsafe_allow_html=True)
                    st.markdown(format_metric("Best Profit", safe_float_convert(full_stats.get('Largest_Profit_Trade')), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Biggest Loss", safe_float_convert(full_stats.get('Largest_Loss_Trade')), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Trade Size", safe_float_convert(full_stats.get('Average_Trade_Size')), ratio=True), unsafe_allow_html=True)

                with sub_col2:    
                    st.markdown(format_metric("Total Net Profit", safe_float_convert(full_stats.get('Total_Net_Profit')), currency=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Gross Profit", safe_float_convert(full_stats.get('Gross_Profit')), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Gross Loss", safe_float_convert(full_stats.get('Gross_Loss')), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Win Rate", safe_float_convert(full_stats.get('Win_Rate')), percent=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Profit Factor", safe_float_convert(full_stats.get('Profit_Factor')), ratio=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Profit", safe_float_convert(full_stats.get('Average_Profit_Trade')), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Loss", safe_float_convert(full_stats.get('Average_Loss_Trade')), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Expectancy", safe_float_convert(full_stats.get('Expected_Payoff')), currency=True, color_cond=True), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📊 Portfolio Returns & Equity")
    realized_net_profit = st.session_state.get('realized_profit_loss')
    total_deposit = st.session_state.get('total_deposit_amount')
    total_withdrawal = st.session_state.get('total_withdrawal_amount')
    total_net_profit_from_sheet = st.session_state.get('total_net_profit_from_sheet')

    if realized_net_profit is not None:
        col_rp, col_dep, col_wit, col_net_from_sheet = st.columns(4)
        with col_rp:
            st.metric("Account Equity Change", f"{safe_float_convert(realized_net_profit):,.2f} USD")
        with col_dep:
            st.metric("Total Deposits", f"{safe_float_convert(total_deposit):,.2f} USD")
        with col_wit:
            st.metric("Total Withdrawals", f"{safe_float_convert(total_withdrawal):,.2f} USD")
        with col_net_from_sheet: 
            st.metric("Total Net Profit (from Trades)", f"{safe_float_convert(total_net_profit_from_sheet):,.2f} USD")
    else:
        st.info("No portfolio return data available. Please select a portfolio.")

    st.subheader("🤖 AI-Powered Insights")
    with st.container(border=True):
        # ดึงข้อมูล Insights จาก analytics_engine
        #insights = analytics_engine.get_ai_powered_insights(df_actual_trades, active_id)
        insights = {}
        
        if not insights:
            st.info("Not enough data to generate insights.")
        else:
            # จัดการแสดงผลให้สวยงาม
            best_day_data = insights.get('best_day')
            worst_day_data = insights.get('worst_day')
            best_pair_data = insights.get('best_pair')
            worst_pair_data = insights.get('worst_pair')
            pnl_data = insights.get('long_vs_short_pnl')

            if best_day_data and safe_float_convert(best_day_data[1]) > 0:
                st.markdown(f"📈 **วันทำกำไรดีที่สุด:** วัน{best_day_data[0]} (**+{safe_float_convert(best_day_data[1]):,.2f} USD**)")
            
            if worst_day_data and safe_float_convert(worst_day_data[1]) < 0:
                st.markdown(f"📉 **วันขาดทุนหนักที่สุด:** วัน{worst_day_data[0]} (**{safe_float_convert(worst_day_data[1]):,.2f} USD**)")

            if best_pair_data and safe_float_convert(best_pair_data[1]) > 0:
                st.markdown(f"💰 **สินทรัพย์ทำเงิน:** {best_pair_data[0]} (**+{safe_float_convert(best_pair_data[1]):,.2f} USD**)")

            if worst_pair_data and safe_float_convert(worst_pair_data[1]) < 0:
                st.markdown(f"⚠️ **สินทรัพย์ที่ควรระวัง:** {worst_pair_data[0]} (**{safe_float_convert(worst_pair_data[1]):,.2f} USD**)")
            
            if pnl_data:
                st.markdown(f"↕️ **กำไร/ขาดทุน (Long vs Short):** `{safe_float_convert(pnl_data[0]):,.2f}` vs `{safe_float_convert(pnl_data[1]):,.2f}`")


# =============================================================================            

def _render_portfolio_form(is_edit_mode, db_handler_instance, df_portfolios_gs, portfolio_to_edit_data={}):
    """
    Renders the form to add or edit a portfolio, with all labels in English.
    """
    mode_suffix = "edit" if is_edit_mode else "add"
    
    session_key_program_type = f'form_program_type_{mode_suffix}'
    widget_key_program_type = f'exp_pf_type_selector_widget_{mode_suffix}'

    def on_program_type_change():
        st.session_state[session_key_program_type] = st.session_state[widget_key_program_type]

    program_type_options = ["", "Personal Account", "Prop Firm Challenge", "Funded Account", "Trading Competition"]
    
    default_program_type = portfolio_to_edit_data.get("ProgramType", "")
    if session_key_program_type not in st.session_state: 
        st.session_state[session_key_program_type] = default_program_type
    
    current_value = st.session_state.get(session_key_program_type, "")
    type_index = program_type_options.index(current_value) if current_value in program_type_options else 0

    st.selectbox(
        "Program Type*",
        options=program_type_options,
        index=type_index,
        key=widget_key_program_type,
        on_change=on_program_type_change
    )
    
    selected_program_type = st.session_state.get(session_key_program_type)

    with st.form(key=f"portfolio_form_{mode_suffix}", clear_on_submit=False):
        st.markdown(f"**Enter Portfolio Details (for type: {selected_program_type or 'Not Selected'})**")

        key_prefix = mode_suffix
        
        form_c1, form_c2 = st.columns(2)
        with form_c1:
            form_new_portfolio_name = st.text_input("Portfolio Name*", value=portfolio_to_edit_data.get("PortfolioName", ""), key=f"{key_prefix}_name")
        with form_c2:
            form_new_initial_balance = st.number_input("Initial Balance*", min_value=0.01, value=safe_float_convert(portfolio_to_edit_data.get("InitialBalance", 10000.0)), format="%.2f", key=f"{key_prefix}_balance") # ใช้ safe_float_convert
        account_type_options = ["STANDARD", "CENT", "PROP_FIRM"] # เพิ่มตัวเลือกประเภทบัญชี
        default_account_type = portfolio_to_edit_data.get("AccountType", "STANDARD") # ดึงค่าเดิมถ้าเป็นโหมดแก้ไข
        account_type_index = account_type_options.index(default_account_type) if default_account_type in account_type_options else 0
        form_new_account_type = st.selectbox(
            "Account Type*",
            options=account_type_options,
            index=account_type_index,
            key=f"{key_prefix}_account_type"
        )
        form_status_options = ["Active", "Inactive", "Pending", "Passed", "Failed"]
        status_default = portfolio_to_edit_data.get("Status", "Active")
        status_index = form_status_options.index(status_default) if status_default in form_status_options else 0
        form_new_status = st.selectbox("Portfolio Status*", options=form_status_options, index=status_index, key=f"{key_prefix}_status")

        form_new_evaluation_step_widget = ""
        if selected_program_type == "Prop Firm Challenge":
            evaluation_step_options = ["", "Phase 1", "Phase 2", "Phase 3", "Verification"]
            eval_default = portfolio_to_edit_data.get("EvaluationStep", "")
            eval_index = evaluation_step_options.index(eval_default) if eval_default in evaluation_step_options else 0
            form_new_evaluation_step_widget = st.selectbox("Evaluation Step", options=evaluation_step_options, index=eval_index, key=f"{key_prefix}_eval_step")
        
        # Initialize widget value variables to a default (like 0.0 or None)
        # ตัวแปรเหล่านี้ต้องมีค่าเสมอ ไม่ว่าจะถูกแสดงใน UI หรือไม่
        prop_profit_target_widget, prop_leverage_widget, prop_min_days_widget = (0.0, 0.0, 0)
        prop_daily_loss_widget, prop_total_stopout_widget = (0.0, 0.0) # สำหรับ Prop Firm
        
        comp_end_date_widget, comp_goal_metric_widget = (None, "")
        comp_profit_target_widget, comp_daily_loss_widget, comp_total_stopout_widget = (0.0, 0.0, 0.0) # สำหรับ Trading Competition

        pers_overall_profit_widget, pers_weekly_profit_widget, pers_max_dd_overall_widget = (0.0, 0.0, 0.0)
        pers_target_end_date_widget, pers_daily_profit_widget = (None, 0.0) # สำหรับ Personal Account
        pers_daily_loss_limit_widget = safe_float_convert(portfolio_to_edit_data.get("DailyLossLimitPercent"), 2.0) # สำหรับ Personal Account
        
        scaling_freq_val_widget, su_wr_val_widget, sd_loss_val_widget, min_risk_val_widget, su_gain_val_widget, sd_wr_val_widget, max_risk_val_widget, su_inc_val_widget, sd_dec_val_widget, current_risk_s_val_widget = ("", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # <<<< แก้ไขตรงนี้: ใช้ safe_float_convert ใน input เลย >>>>
        if selected_program_type in ["Prop Firm Challenge", "Funded Account"]:
            st.markdown("**Prop Firm/Funded Rules:**")
            f_pf1, f_pf2, f_pf3 = st.columns(3)
            with f_pf1: prop_profit_target_widget = st.number_input("Profit Target %*", value=safe_float_convert(portfolio_to_edit_data.get("ProfitTargetPercent", 8.0)), format="%.1f", key=f"{key_prefix}_prop_profit")
            with f_pf2: prop_daily_loss_widget = st.number_input("Daily Loss Limit %*", value=safe_float_convert(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f", key=f"{key_prefix}_prop_daily_loss")
            with f_pf3: prop_total_stopout_widget = st.number_input("Total Stopout %*", value=safe_float_convert(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f", key=f"{key_prefix}_prop_total_loss")
            f_pf_col1, f_pf_col2 = st.columns(2)
            with f_pf_col1: prop_leverage_widget = st.number_input("Leverage", value=safe_float_convert(portfolio_to_edit_data.get("Leverage", 100.0)), format="%.0f", key=f"{key_prefix}_prop_leverage")
            with f_pf_col2: prop_min_days_widget = st.number_input("Min. Trading Days", value=int(safe_float_convert(portfolio_to_edit_data.get("MinTradingDays", 0))), step=1, key=f"{key_prefix}_prop_min_days")
        # <<<< สิ้นสุดการแก้ไข >>>>

        # <<<< แก้ไขตรงนี้: ใช้ safe_float_convert ใน input เลย >>>>
        if selected_program_type == "Trading Competition":
            st.markdown("**Competition Details:**")
            f_tc1, f_tc2 = st.columns(2)
            with f_tc1:
                comp_date_str = portfolio_to_edit_data.get("CompetitionEndDate")
                default_comp_date = None
                if comp_date_str and str(comp_date_str).strip() not in ["", "None", "nan"]:
                    try: default_comp_date = pd.to_datetime(comp_date_str).date()
                    except (ValueError, TypeError): default_comp_date = None
                comp_end_date_widget = st.date_input("Competition End Date", value=default_comp_date, key=f"{key_prefix}_comp_date")
                comp_profit_target_widget = st.number_input("Profit Target % (Comp)", value=safe_float_convert(portfolio_to_edit_data.get("ProfitTargetPercent", 20.0)), format="%.1f", key=f"{key_prefix}_comp_profit")           
            with f_tc2:
                comp_goal_metric_widget = st.text_input("Goal Metric (Comp)", value=portfolio_to_edit_data.get("GoalMetric", ""), help="e.g. %Gain, ROI", key=f"{key_prefix}_comp_goal")
                comp_daily_loss_widget = st.number_input("Daily Loss Limit % (Comp)", value=safe_float_convert(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f", key=f"{key_prefix}_comp_daily_loss")
                comp_total_stopout_widget = st.number_input("Total Stopout % (Comp)", value=safe_float_convert(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f", key=f"{key_prefix}_comp_total_stopout")
        # <<<< สิ้นสุดการแก้ไข >>>>

        # <<<< แก้ไขตรงนี้: ใช้ safe_float_convert ใน input เลย >>>>
        if selected_program_type == "Personal Account":
            st.markdown("**Personal Goals (Optional):**")
            f_ps1, f_ps2 = st.columns(2)
            with f_ps1:
                pers_overall_profit_widget = st.number_input("Overall Profit Target ($)", value=safe_float_convert(portfolio_to_edit_data.get("OverallProfitTarget"), 0.0), format="%.2f", key=f"{key_prefix}_pers_profit")
                pers_weekly_profit_widget = st.number_input("Weekly Profit Target ($)", value=safe_float_convert(portfolio_to_edit_data.get("WeeklyProfitTarget"), 0.0), format="%.2f", key=f"{key_prefix}_pers_weekly_profit")
                pers_max_dd_overall_widget = st.number_input("Max. Acceptable Overall DD ($)", value=safe_float_convert(portfolio_to_edit_data.get("MaxAcceptableDrawdownOverall"), 0.0), format="%.2f", key=f"{key_prefix}_pers_dd_overall")
            with f_ps2:
                target_date_str = portfolio_to_edit_data.get("TargetEndDate")
                default_target_date = None
                if target_date_str and str(target_date_str).strip() not in ["", "None", "nan"]:
                    try: default_target_date = pd.to_datetime(target_date_str).date()
                    except (ValueError, TypeError): default_target_date = None
                pers_target_end_date_widget = st.date_input("Target End Date", value=default_target_date, key=f"{key_prefix}_pers_end_date")
                pers_daily_profit_widget = st.number_input("Daily Profit Target ($)", value=safe_float_convert(portfolio_to_edit_data.get("DailyProfitTarget"), 0.0), format="%.2f", key=f"{key_prefix}_pers_daily_profit")
                
                pers_daily_loss_limit_widget = st.number_input(
                    "Daily Drawdown Limit (%)",
                    min_value=0.1, max_value=100.0,
                    value=safe_float_convert(portfolio_to_edit_data.get("DailyLossLimitPercent"), 2.0),
                    step=0.1, format="%.1f",
                    key=f"{key_prefix}_pers_daily_dd_limit"
                )
        # <<<< สิ้นสุดการแก้ไข >>>>

        st.markdown("**Scaling Manager Settings (Optional):**")
        enable_scaling_checkbox_val = st.checkbox("Enable Scaling Manager?", value=str(portfolio_to_edit_data.get("EnableScaling", "False")).upper() == 'TRUE', key=f"{key_prefix}_scaling_cb")

        # ... (โค้ดส่วน Notes และ Submit Button เหมือนเดิม)
        
        notes_val_area_widget = st.text_area("Additional Notes", value=portfolio_to_edit_data.get("Notes", ""), key=f"{key_prefix}_notes")

        submit_button_label = "💾 Update Portfolio" if is_edit_mode else "💾 Save New Portfolio"
        submitted = st.form_submit_button(submit_button_label)

        if submitted:
            if not form_new_portfolio_name or not selected_program_type or not form_new_status or form_new_initial_balance <= 0:
                st.warning("Please fill in all required fields (*) correctly.")
            else:
                data_to_save = portfolio_logic.prepare_new_portfolio_data_for_gsheet(
                    form_new_portfolio_name_in_form=form_new_portfolio_name,
                    selected_program_type_to_use_in_form=selected_program_type,
                    form_new_initial_balance_in_form=form_new_initial_balance,
                    form_new_status_in_form=form_new_status,
                    form_new_evaluation_step_val_in_form=form_new_evaluation_step_widget,
                    form_notes_val=notes_val_area_widget,
                    form_profit_target_val=prop_profit_target_widget,
                    # <<<< แก้ไขตรงนี้: ส่งค่า DailyLossLimitPercent ที่ถูกต้องตาม ProgramType >>>>
                    form_daily_loss_val=prop_daily_loss_widget if selected_program_type in ["Prop Firm Challenge", "Funded Account"] else \
                                        comp_daily_loss_widget if selected_program_type == "Trading Competition" else \
                                        pers_daily_loss_limit_widget if selected_program_type == "Personal Account" else \
                                        0.0, # <-- ส่งค่า DailyLossLimitPercent จาก widget ที่เกี่ยวข้อง
                    # <<<< สิ้นสุดการแก้ไข >>>>
                    form_total_stopout_val=prop_total_stopout_widget,
                    form_leverage_val=prop_leverage_widget,
                    form_min_days_val=prop_min_days_widget,
                    form_comp_end_date=comp_end_date_widget,
                    form_comp_goal_metric=comp_goal_metric_widget,
                    form_profit_target_val_comp=comp_profit_target_widget,
                    form_daily_loss_val_comp=comp_daily_loss_widget,
                    form_total_stopout_val_comp=comp_total_stopout_widget,
                    form_pers_overall_profit_val=pers_overall_profit_widget,
                    form_pers_target_end_date=pers_target_end_date_widget,
                    form_pers_weekly_profit_val=pers_weekly_profit_widget,
                    form_pers_daily_profit_val=pers_daily_profit_widget,
                    form_pers_max_dd_overall_val=pers_max_dd_overall_widget,
                    form_pers_max_dd_daily_val=pers_daily_loss_limit_widget if selected_program_type == "Personal Account" else 0.0, # <<<< แก้ไขตรงนี้: ต้องส่งค่าจาก widget pers_daily_loss_limit_widget >>>>
                    form_enable_scaling_checkbox_val=enable_scaling_checkbox_val,
                    form_scaling_freq_val=scaling_freq_val_widget,
                    form_su_wr_val=su_wr_val_widget,
                    form_su_gain_val=su_gain_val_widget,
                    form_su_inc_val=su_inc_val_widget,
                    form_sd_loss_val=sd_loss_val_widget,
                    form_sd_wr_val=sd_wr_val_widget,
                    form_sd_dec_val=sd_dec_val_widget,
                    form_min_risk_val=min_risk_val_widget,
                    form_max_risk_val=max_risk_val_widget,
                    form_current_risk_val=current_risk_s_val_widget,
                    account_type_in_form=form_new_account_type
                )

                if is_edit_mode:
                    portfolio_id_to_update = portfolio_to_edit_data.get("PortfolioID")
                    data_to_save["PortfolioID"] = portfolio_id_to_update
                    data_to_save["CreationDate"] = portfolio_to_edit_data.get("CreationDate", date.today().strftime('%Y-%m-%d %H:%M:%S'))
                    
                    with st.spinner("Updating..."): 
                        success, msg = db_handler_instance.update_portfolio(portfolio_id_to_update, data_to_save)
                    if success: st.success(msg)
                    else: st.error(msg)
                else:
                    if not df_portfolios_gs.empty and form_new_portfolio_name in df_portfolios_gs['PortfolioName'].astype(str).values:
                        st.error(f"Portfolio name '{form_new_portfolio_name}' already exists.")
                    else:
                        with st.spinner("Saving..."): 
                            success_save, msg_save = db_handler_instance.save_new_portfolio(data_to_save)
                        if success_save:
                            st.success(msg_save)
                            if session_key_program_type in st.session_state:
                                del st.session_state[session_key_program_type]
                        else: st.error(msg_save)


def render_portfolio_manager_expander(db_handler, df_portfolios):
    """
    Renders the main expander and tabs for portfolio management.
    """
    with st.expander("💼 Portfolio Manager (Dashboard/Add/Edit)", expanded=False):
        
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Add New Portfolio", "✏️ Edit/Delete Portfolio"])

        with tab1:
            # ===================================================================
            # ===== START: โค้ดส่วนแก้ไขที่เพิ่มเข้ามา =====
            # ===================================================================
            df_actual_trades = db_handler.load_actual_trades()
            df_summaries = db_handler.load_statement_summaries()
            active_portfolio_id = st.session_state.get('active_portfolio_id_gs')

            #if active_portfolio_id:
            #    (
            #        df_equity_curve_data,
            #        realized_net_profit,
            #        total_deposit,
            #        total_withdrawal,
            #        total_net_profit_from_sheet
            #    ) = analytics_engine.calculate_true_equity_curve(
            #        df_summaries=df_summaries,
            #        portfolio_id=active_portfolio_id
            #    )
            #    st.session_state['df_equity_curve_data'] = df_equity_curve_data
            #    st.session_state['realized_profit_loss'] = realized_net_profit
            #    st.session_state['total_deposit_amount'] = total_deposit
            #    st.session_state['total_withdrawal_amount'] = total_withdrawal
            #    st.session_state['total_net_profit_from_sheet'] = total_net_profit_from_sheet
            #else:
            #    st.session_state['df_equity_curve_data'] = None
            #    st.session_state['realized_profit_loss'] = None
            #    st.session_state['total_deposit_amount'] = None
            #    st.session_state['total_withdrawal_amount'] = None
            #    st.session_state['total_net_profit_from_sheet'] = None
            
            # ===================================================================
            # ===== END: สิ้นสุดโค้ดที่แก้ไข =====
            # ===================================================================

            if active_portfolio_id and not df_portfolios.empty:
                details_df = df_portfolios[df_portfolios['PortfolioID'] == active_portfolio_id]
                if not details_df.empty:
                    _render_portfolio_header(
                        details=details_df.iloc[0].to_dict(),
                        df_actual_trades=df_actual_trades,
                        df_summaries=df_summaries
                    )
                else:
                    st.error("Could not find data for the selected portfolio.")
            else:
                st.info("Please select an active portfolio from the sidebar to display data.")

        with tab2:
            st.subheader("➕ Add New Portfolio")
            _render_portfolio_form(
                is_edit_mode=False,
                db_handler_instance=db_handler,
                df_portfolios_gs=df_portfolios
            )

        with tab3:
            st.subheader("✏️ Edit/Delete Portfolio")
            if df_portfolios.empty: 
                st.info("No portfolios to edit or delete yet.")
            else:
                edit_dict = dict(zip(df_portfolios['PortfolioName'], df_portfolios['PortfolioID']))
                name_to_action = st.selectbox(
                    "Select portfolio to Edit or Delete:", 
                    options=[""] + list(edit_dict.keys()), 
                    key="action_sel"
                )
                
                if name_to_action:
                    portfolio_id = edit_dict[name_to_action]
                    data_to_action = df_portfolios[df_portfolios['PortfolioID'] == portfolio_id].iloc[0].to_dict()

                    st.markdown(f"### ✏️ Edit Details for '{name_to_action}'")
                    _render_portfolio_form(
                        is_edit_mode=True,
                        db_handler_instance=db_handler,
                        portfolio_to_edit_data=data_to_action, 
                        df_portfolios_gs=df_portfolios
                    )
                    st.markdown("---")                    
                    st.error(f"Danger Zone: Delete '{name_to_action}'")
                    
                    confirm_delete = st.checkbox(f"I understand and want to delete '{name_to_action}'", key=f"del_confirm_{portfolio_id}")
                    
                    if st.button(f"Confirm Deletion", type="primary", disabled=not confirm_delete):
                        success, msg = db_handler.delete_portfolio(portfolio_id)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)