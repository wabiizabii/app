# ui/portfolio_section.py (English Version)
import streamlit as st
import pandas as pd
import uuid
from datetime import date
from .ai_section import render_ai_insights # Assuming ai_section will be translated separately
from core import gs_handler, portfolio_logic, analytics_engine

# =============================================================================
# Helper & Rendering Functions
# =============================================================================

def _render_portfolio_header(details: dict, df_actual_trades: pd.DataFrame, df_summaries: pd.DataFrame):
    """
    Renders the portfolio dashboard header with all statistics, translated to English.
    """
    if not details:
        st.info("Please select a portfolio from the sidebar to view details.")
        return

    # --- Fetch all statistics ---
    active_id = st.session_state.get('active_portfolio_id_gs')
    advanced_stats = analytics_engine.get_advanced_statistics(df_all_actual_trades=df_actual_trades, active_portfolio_id=active_id)
    full_stats = analytics_engine.get_full_dashboard_stats(
        df_all_actual_trades=df_actual_trades,
        df_all_summaries=df_summaries,
        active_portfolio_id=active_id
    )

    # --- Section 1: Title and Details Box ---
    with st.container(border=True):
        portfolio_name = details.get('PortfolioName', 'N/A')
        account_size = float(details.get('InitialBalance', 0))
        prog_type = details.get('ProgramType', 'N/A')
        profit_target = details.get('ProfitTargetPercent', 0)
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
                    st.markdown(f"• Wins: `{int(wins)} trades`" if pd.notna(wins) else "• Wins: `N/A`")
                    st.markdown(f"• Losses: `{int(loss)} trades`" if pd.notna(loss) else "• Losses: `N/A`")
                
                with adv_col2:
                    st.markdown("**Biggest Win/Loss:**")
                    win_l = advanced_stats.get('biggest_win_long')
                    loss_l = advanced_stats.get('biggest_loss_long')
                    win_l_display = f"<font color='#28a745'>{win_l:,.2f}</font>" if pd.notna(win_l) else "N/A"
                    loss_l_display = f"<font color='#dc3545'>{loss_l:,.2f}</font>" if pd.notna(loss_l) else "N/A"
                    st.markdown(f"• Long: {win_l_display} / {loss_l_display}", unsafe_allow_html=True)

                    win_s = advanced_stats.get('biggest_win_short')
                    loss_s = advanced_stats.get('biggest_loss_short')
                    win_s_display = f"<font color='#28a745'>{win_s:,.2f}</font>" if pd.notna(win_s) else "N/A"
                    loss_s_display = f"<font color='#dc3545'>{loss_s:,.2f}</font>" if pd.notna(loss_s) else "N/A"
                    st.markdown(f"• Short: {win_s_display} / {loss_s_display}", unsafe_allow_html=True)

                    st.markdown("**Consistency:**")
                    conc = advanced_stats.get('profit_concentration', 0)
                    days = advanced_stats.get('active_trading_days', 0)
                    st.markdown(f"• Profit Conc.: `{conc:.1f}%`" if conc > 0 else "• Profit Conc.: `N/A`")
                    st.markdown(f"• Active Days: `{days} days`")

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
                    st.markdown(format_metric("Total Trades", full_stats.get('Total_Trades')), unsafe_allow_html=True)
                    st.markdown(format_metric("Profit Trades", full_stats.get('Profit_Trades_Count')), unsafe_allow_html=True)
                    st.markdown(format_metric("Loss Trades", full_stats.get('Loss_Trades_Count')), unsafe_allow_html=True)
                    st.markdown(format_metric("Breakeven Trades", full_stats.get('Breakeven_Trades_Count')), unsafe_allow_html=True)
                    st.markdown(format_metric("Long Trades", full_stats.get('Long_Trades_Count')), unsafe_allow_html=True)
                    st.markdown(format_metric("Short Trades", full_stats.get('Short_Trades_Count')), unsafe_allow_html=True)
                    st.markdown(format_metric("Best Profit", full_stats.get('Largest_Profit_Trade'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Biggest Loss", full_stats.get('Largest_Loss_Trade'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Trade Size", full_stats.get('Average_Trade_Size'), ratio=True), unsafe_allow_html=True)

                with sub_col2:    
                    st.markdown(format_metric("Total Net Profit", full_stats.get('Total_Net_Profit'), currency=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Gross Profit", full_stats.get('Gross_Profit'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Gross Loss", full_stats.get('Gross_Loss'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Win Rate", full_stats.get('Win_Rate'), percent=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Profit Factor", full_stats.get('Profit_Factor'), ratio=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Profit", full_stats.get('Average_Profit_Trade'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Loss", full_stats.get('Average_Loss_Trade'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Expectancy", full_stats.get('Expected_Payoff'), currency=True, color_cond=True), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📊 Portfolio Returns & Equity")
    realized_net_profit = st.session_state.get('realized_profit_loss')
    total_deposit = st.session_state.get('total_deposit_amount')
    total_withdrawal = st.session_state.get('total_withdrawal_amount')
    total_net_profit_from_sheet = st.session_state.get('total_net_profit_from_sheet')

    if realized_net_profit is not None:
        col_rp, col_dep, col_wit, col_net_from_sheet = st.columns(4)
        with col_rp:
            st.metric("Account Equity Change", f"{realized_net_profit:,.2f} USD")
        with col_dep:
            st.metric("Total Deposits", f"{total_deposit:,.2f} USD")
        with col_wit:
            st.metric("Total Withdrawals", f"{total_withdrawal:,.2f} USD")
        with col_net_from_sheet: 
            st.metric("Total Net Profit (from Trades)", f"{total_net_profit_from_sheet:,.2f} USD")
    else:
        st.info("No portfolio return data available. Please select a portfolio.")

    df_equity_curve_data = st.session_state.get('df_equity_curve_data')
    if df_equity_curve_data is not None and not df_equity_curve_data.empty:
        st.markdown("---")
        st.markdown("#### True Equity Curve Chart")
        if 'Timestamp' in df_equity_curve_data.columns and 'Equity For Chart' in df_equity_curve_data.columns:
            st.line_chart(df_equity_curve_data, x='Timestamp', y='Equity For Chart')
        else:
            st.warning("Equity curve data is incomplete (missing Timestamp or Equity For Chart column).")
    else:
        st.info("No data available to generate the equity curve chart.")

    st.subheader("🤖 AI-Powered Insights")
    with st.container(border=True):
        insights = analytics_engine.get_ai_powered_insights(df_actual_trades, active_id)
        if not insights:
            st.info("Not enough data to generate insights.")
        else:
            render_ai_insights(insights) # Note: this function also needs translation inside ai_section.py

# =============================================================================            

def _render_portfolio_form(is_edit_mode, portfolio_to_edit_data={}, df_portfolios_gs=pd.DataFrame()):
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
            form_new_initial_balance = st.number_input("Initial Balance*", min_value=0.01, value=float(portfolio_to_edit_data.get("InitialBalance", 10000.0)), format="%.2f", key=f"{key_prefix}_balance")

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
        
        prop_profit_target_widget, prop_daily_loss_widget, prop_total_stopout_widget, prop_leverage_widget, prop_min_days_widget = (None,) * 5
        comp_end_date_widget, comp_profit_target_widget, comp_goal_metric_widget, comp_daily_loss_widget, comp_total_stopout_widget = (None,) * 5
        pers_overall_profit_widget, pers_weekly_profit_widget, pers_max_dd_overall_widget, pers_target_end_date_widget, pers_daily_profit_widget, pers_max_dd_daily_widget = (None,) * 6
        scaling_freq_val_widget, su_wr_val_widget, sd_loss_val_widget, min_risk_val_widget, su_gain_val_widget, sd_wr_val_widget, max_risk_val_widget, su_inc_val_widget, sd_dec_val_widget, current_risk_s_val_widget = (None,) * 10
        
        if selected_program_type in ["Prop Firm Challenge", "Funded Account"]:
            st.markdown("**Prop Firm/Funded Rules:**")
            f_pf1, f_pf2, f_pf3 = st.columns(3)
            with f_pf1: prop_profit_target_widget = st.number_input("Profit Target %*", value=float(portfolio_to_edit_data.get("ProfitTargetPercent", 8.0)), format="%.1f", key=f"{key_prefix}_prop_profit")
            with f_pf2: prop_daily_loss_widget = st.number_input("Daily Loss Limit %*", value=float(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f", key=f"{key_prefix}_prop_daily_loss")
            with f_pf3: prop_total_stopout_widget = st.number_input("Total Stopout %*", value=float(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f", key=f"{key_prefix}_prop_total_loss")
            f_pf_col1, f_pf_col2 = st.columns(2)
            with f_pf_col1: prop_leverage_widget = st.number_input("Leverage", value=float(portfolio_to_edit_data.get("Leverage", 100.0)), format="%.0f", key=f"{key_prefix}_prop_leverage")
            with f_pf_col2: prop_min_days_widget = st.number_input("Min. Trading Days", value=int(portfolio_to_edit_data.get("MinTradingDays", 0)), step=1, key=f"{key_prefix}_prop_min_days")

        if selected_program_type == "Trading Competition":
            st.markdown("**Competition Details:**")
            f_tc1, f_tc2 = st.columns(2)
            with f_tc1:
                comp_end_date_widget = st.date_input("Competition End Date", value=pd.to_datetime(portfolio_to_edit_data.get("CompetitionEndDate")).date() if pd.notna(portfolio_to_edit_data.get("CompetitionEndDate")) else None, key=f"{key_prefix}_comp_date")
                comp_profit_target_widget = st.number_input("Profit Target % (Comp)", value=float(portfolio_to_edit_data.get("ProfitTargetPercent", 20.0)), format="%.1f", key=f"{key_prefix}_comp_profit")
            with f_tc2:
                comp_goal_metric_widget = st.text_input("Goal Metric (Comp)", value=portfolio_to_edit_data.get("GoalMetric", ""), help="e.g. %Gain, ROI", key=f"{key_prefix}_comp_goal")
                comp_daily_loss_widget = st.number_input("Daily Loss Limit % (Comp)", value=float(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f", key=f"{key_prefix}_comp_daily_loss")
                comp_total_stopout_widget = st.number_input("Total Stopout % (Comp)", value=float(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f", key=f"{key_prefix}_comp_total_stopout")

        if selected_program_type == "Personal Account":
            st.markdown("**Personal Goals (Optional):**")
            f_ps1, f_ps2 = st.columns(2)
            with f_ps1:
                pers_overall_profit_widget = st.number_input("Overall Profit Target ($)", value=float(portfolio_to_edit_data.get("OverallProfitTarget", 0.0)), format="%.2f", key=f"{key_prefix}_pers_profit")
                pers_weekly_profit_widget = st.number_input("Weekly Profit Target ($)", value=float(portfolio_to_edit_data.get("WeeklyProfitTarget", 0.0)), format="%.2f", key=f"{key_prefix}_pers_weekly_profit")
                pers_max_dd_overall_widget = st.number_input("Max. Acceptable Overall DD ($)", value=float(portfolio_to_edit_data.get("MaxAcceptableDrawdownOverall", 0.0)), format="%.2f", key=f"{key_prefix}_pers_dd_overall")
            with f_ps2:
                pers_target_end_date_widget = st.date_input("Target End Date", value=pd.to_datetime(portfolio_to_edit_data.get("TargetEndDate")).date() if pd.notna(portfolio_to_edit_data.get("TargetEndDate")) else None, key=f"{key_prefix}_pers_end_date")
                pers_daily_profit_widget = st.number_input("Daily Profit Target ($)", value=float(portfolio_to_edit_data.get("DailyProfitTarget", 0.0)), format="%.2f", key=f"{key_prefix}_pers_daily_profit")
                pers_max_dd_daily_widget = st.number_input("Max. Acceptable Daily DD ($)", value=float(portfolio_to_edit_data.get("MaxAcceptableDrawdownDaily", 0.0)), format="%.2f", key=f"{key_prefix}_pers_dd_daily")

        st.markdown("**Scaling Manager Settings (Optional):**")
        enable_scaling_checkbox_val = st.checkbox("Enable Scaling Manager?", value=str(portfolio_to_edit_data.get("EnableScaling", "False")).upper() == 'TRUE', key=f"{key_prefix}_scaling_cb")

        if enable_scaling_checkbox_val:
            # ... (labels inside scaling manager are mostly English already) ...
            pass
        
        notes_val_area_widget = st.text_area("Additional Notes", value=portfolio_to_edit_data.get("Notes", ""), key=f"{key_prefix}_notes")

        submit_button_label = "💾 Update Portfolio" if is_edit_mode else "💾 Save New Portfolio"
        submitted = st.form_submit_button(submit_button_label)

        if submitted:
            # --- VVVV START: โค้ดที่แก้ไขและแปลแล้ว VVVV ---
            if not form_new_portfolio_name or not selected_program_type or not form_new_status or form_new_initial_balance <= 0:
                st.warning("Please fill in all required fields (*) correctly.")
            else:
                # Data preparation logic remains the same
                data_to_save = portfolio_logic.prepare_new_portfolio_data_for_gsheet(
                    form_new_portfolio_name_in_form=form_new_portfolio_name,
                    selected_program_type_to_use_in_form=selected_program_type,
                    form_new_initial_balance_in_form=form_new_initial_balance,
                    form_new_status_in_form=form_new_status,
                    form_new_evaluation_step_val_in_form=form_new_evaluation_step_widget,
                    form_notes_val=notes_val_area_widget,
                    form_profit_target_val=prop_profit_target_widget,
                    form_daily_loss_val=prop_daily_loss_widget,
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
                    form_pers_max_dd_daily_val=pers_max_dd_daily_widget,
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
                    form_current_risk_val=current_risk_s_val_widget
                )

                if is_edit_mode:
                    portfolio_id_to_update = portfolio_to_edit_data.get("PortfolioID")
                    data_to_save["PortfolioID"] = portfolio_id_to_update
                    data_to_save["CreationDate"] = portfolio_to_edit_data.get("CreationDate", date.today().strftime('%Y-%m-%d %H:%M:%S'))
                    
                    with st.spinner("Updating..."): 
                        success = gs_handler.update_portfolio_in_gsheets(portfolio_id_to_update, data_to_save)
                    
                    if success:
                        st.success(f"Successfully updated portfolio '{form_new_portfolio_name}'!")
                    else: 
                        st.error("Failed to update the portfolio.")
                else: # This is for adding a new portfolio
                    if not df_portfolios_gs.empty and form_new_portfolio_name in df_portfolios_gs['PortfolioName'].astype(str).values:
                        st.error(f"Portfolio name '{form_new_portfolio_name}' already exists. Please use a different name.")
                    else:
                        with st.spinner("Saving..."): 
                            success_save = gs_handler.save_new_portfolio_to_gsheets(data_to_save)
                        
                        if success_save:
                            st.success(f"Successfully added portfolio '{form_new_portfolio_name}'!")
                            if session_key_program_type in st.session_state:
                                del st.session_state[session_key_program_type]
                        else: 
                            st.error("An error occurred while saving the new portfolio.")


def render_portfolio_manager_expander(df_portfolios):
    """
    Renders the main expander and tabs for portfolio management.
    """
    with st.expander("💼 Portfolio Manager (Dashboard/Add/Edit)", expanded=True):
        
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Add New Portfolio", "✏️ Edit/Delete Portfolio"])

        with tab1:
            df_actual_trades = gs_handler.load_actual_trades_from_gsheets()
            df_summaries = gs_handler.load_statement_summaries_from_gsheets()
            active_portfolio_id = st.session_state.get('active_portfolio_id_gs')

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
            _render_portfolio_form(is_edit_mode=False, df_portfolios_gs=df_portfolios)

        with tab3:
            st.subheader("✏️ Edit/Delete Portfolio")
            if df_portfolios.empty: 
                st.info("No portfolios to edit yet.")
            else:
                edit_dict = dict(zip(df_portfolios['PortfolioName'], df_portfolios['PortfolioID']))
                name_to_edit = st.selectbox("Select portfolio to edit:", options=[""] + list(edit_dict.keys()), key="edit_sel")
                if name_to_edit:
                    id_to_edit = edit_dict[name_to_edit]
                    data_to_edit = df_portfolios[df_portfolios['PortfolioID'] == id_to_edit].iloc[0].to_dict()
                    _render_portfolio_form(is_edit_mode=True, portfolio_to_edit_data=data_to_edit, df_portfolios_gs=df_portfolios)