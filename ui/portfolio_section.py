# ui/portfolio_section.py (เวอร์ชันเต็มสมบูรณ์: แก้ไขให้ Save ทำงานได้)

import streamlit as st
import pandas as pd
from datetime import date
from core import portfolio_logic, analytics_engine
from config import settings

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

def _render_portfolio_header(details: dict, df_actual_trades: pd.DataFrame, df_summaries: pd.DataFrame):
    """
    Renders the portfolio dashboard header with all statistics.
    """
    if not details:
        st.info("Please select a portfolio from the sidebar to view details.")
        return

    active_id = st.session_state.get('active_portfolio_id_gs')
    advanced_stats = {} # Placeholder for future implementation
    full_stats = {}     # Placeholder for future implementation

    with st.container(border=True):
        portfolio_name = details.get('PortfolioName', 'N/A')
        account_size = safe_float_convert(details.get('InitialBalance', 0))
        prog_type = details.get('ProgramType', 'N/A')
        profit_target = safe_float_convert(details.get('ProfitTargetPercent', 0))
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

    main_col1, main_col2 = st.columns([1.5, 1.8])

    with main_col1:
        st.markdown("##### Advanced Statistics")
        with st.container(border=True, height=310):
            st.info("No advanced statistics available.")

    with main_col2:
        st.markdown("##### Performance Metrics")
        with st.container(border=True, height=310):
            st.info("No statistics available.")

    st.markdown("---")
    st.subheader("📊 Portfolio Returns & Equity")
    st.info("No portfolio return data available. Please select a portfolio.")
    
    st.subheader("🤖 AI-Powered Insights")
    with st.container(border=True):
        st.info("Not enough data to generate insights.")


def _render_portfolio_form(is_edit_mode, db_handler_instance, df_portfolios_gs, portfolio_to_edit_data={}):
    """
    Renders the form to add or edit a portfolio, with working save logic.
    """
    mode_suffix = "edit" if is_edit_mode else "add"
    
    with st.form(key=f"portfolio_form_{mode_suffix}", clear_on_submit=False):
        
        program_type_options = ["", "Personal Account", "Prop Firm Challenge", "Funded Account", "Trading Competition"]
        default_program_type = portfolio_to_edit_data.get("ProgramType", "")
        type_index = program_type_options.index(default_program_type) if default_program_type in program_type_options else 0
        
        selected_program_type = st.selectbox(
            "Program Type*",
            options=program_type_options,
            index=type_index,
            key=f"form_program_type_{mode_suffix}"
        )
        
        st.markdown(f"**Enter Portfolio Details (for type: {selected_program_type or 'Not Selected'})**")
        
        key_prefix = mode_suffix
        
        form_c1, form_c2 = st.columns(2)
        with form_c1:
            form_new_portfolio_name = st.text_input("Portfolio Name*", value=portfolio_to_edit_data.get("PortfolioName", ""), key=f"{key_prefix}_name")
        with form_c2:
            form_new_initial_balance = st.number_input("Initial Balance*", min_value=0.01, value=safe_float_convert(portfolio_to_edit_data.get("InitialBalance", 10000.0)), format="%.2f", key=f"{key_prefix}_balance")
        
        account_type_options = ["STANDARD", "CENT", "PROP_FIRM"]
        default_account_type = portfolio_to_edit_data.get("AccountType", "STANDARD")
        account_type_index = account_type_options.index(default_account_type) if default_account_type in account_type_options else 0
        form_new_account_type = st.selectbox("Account Type*", options=account_type_options, index=account_type_index, key=f"{key_prefix}_account_type")
        
        form_status_options = ["Active", "Inactive", "Pending", "Passed", "Failed"]
        status_default = portfolio_to_edit_data.get("Status", "Active")
        status_index = form_status_options.index(status_default) if status_default in form_status_options else 0
        form_new_status = st.selectbox("Portfolio Status*", options=form_status_options, index=status_index, key=f"{key_prefix}_status")

        # --- Initialize all possible form variables with default values ---
        form_new_evaluation_step_widget = ""
        prop_profit_target_widget, prop_daily_loss_widget, prop_total_stopout_widget, prop_leverage_widget, prop_min_days_widget = 0.0, 0.0, 0.0, 0.0, 0
        comp_end_date_widget, comp_goal_metric_widget, comp_profit_target_widget, comp_daily_loss_widget, comp_total_stopout_widget = None, "", 0.0, 0.0, 0.0
        pers_overall_profit_widget, pers_target_end_date_widget, pers_weekly_profit_widget, pers_daily_profit_widget, pers_max_dd_overall_widget, pers_daily_loss_limit_widget = 0.0, None, 0.0, 0.0, 0.0, 0.0
        scaling_freq_val_widget, su_wr_val_widget, su_gain_val_widget, su_inc_val_widget, sd_loss_val_widget, sd_wr_val_widget, sd_dec_val_widget, min_risk_val_widget, max_risk_val_widget, current_risk_s_val_widget = "", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        
        # --- Display conditional form fields ---
        if selected_program_type == "Prop Firm Challenge":
            evaluation_step_options = ["", "Phase 1", "Phase 2", "Phase 3", "Verification"]
            eval_default = portfolio_to_edit_data.get("EvaluationStep", "")
            eval_index = evaluation_step_options.index(eval_default) if eval_default in evaluation_step_options else 0
            form_new_evaluation_step_widget = st.selectbox("Evaluation Step", options=evaluation_step_options, index=eval_index, key=f"{key_prefix}_eval_step")
        
        if selected_program_type in ["Prop Firm Challenge", "Funded Account"]:
            st.markdown("**Prop Firm/Funded Rules:**")
            f_pf1, f_pf2, f_pf3 = st.columns(3)
            with f_pf1: prop_profit_target_widget = st.number_input("Profit Target %*", value=safe_float_convert(portfolio_to_edit_data.get("ProfitTargetPercent", 8.0)), format="%.1f", key=f"{key_prefix}_prop_profit")
            with f_pf2: prop_daily_loss_widget = st.number_input("Daily Loss Limit %*", value=safe_float_convert(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f", key=f"{key_prefix}_prop_daily_loss")
            with f_pf3: prop_total_stopout_widget = st.number_input("Total Stopout %*", value=safe_float_convert(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f", key=f"{key_prefix}_prop_total_loss")
            f_pf_col1, f_pf_col2 = st.columns(2)
            with f_pf_col1: prop_leverage_widget = st.number_input("Leverage", value=safe_float_convert(portfolio_to_edit_data.get("Leverage", 100.0)), format="%.0f", key=f"{key_prefix}_prop_leverage")
            with f_pf_col2: prop_min_days_widget = st.number_input("Min. Trading Days", value=int(safe_float_convert(portfolio_to_edit_data.get("MinTradingDays", 0))), step=1, key=f"{key_prefix}_prop_min_days")
        
        st.markdown("**Scaling Manager Settings (Optional):**")
        enable_scaling_checkbox_val = st.checkbox("Enable Scaling Manager?", value=str(portfolio_to_edit_data.get("EnableScaling", "False")).upper() == 'TRUE', key=f"{key_prefix}_scaling_cb")
        
        notes_val_area_widget = st.text_area("Additional Notes", value=portfolio_to_edit_data.get("Notes", ""), key=f"{key_prefix}_notes")

        submit_button_label = "💾 Update Portfolio" if is_edit_mode else "💾 Save New Portfolio"
        submitted = st.form_submit_button(submit_button_label)

        if submitted:
            if not form_new_portfolio_name or not selected_program_type:
                st.warning("Please fill in all required fields (*) correctly.")
            else:
                try:
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
                        form_pers_max_dd_daily_val=pers_daily_loss_limit_widget,
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
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)
                    else:
                        if not df_portfolios_gs.empty and form_new_portfolio_name in df_portfolios_gs['PortfolioName'].astype(str).values:
                            st.error(f"Portfolio name '{form_new_portfolio_name}' already exists.")
                        else:
                            with st.spinner("Saving..."):
                                data_map = {
                                    settings.SUPABASE_TABLE_PORTFOLIOS: [data_to_save]
                                }
                                success_save, msg_save = db_handler_instance.save_statement_data(data_map)
                            if success_save:
                                st.success(msg_save)
                                st.rerun()
                            else:
                                st.error(msg_save)

                except AttributeError as e:
                     st.error(f"เกิดข้อผิดพลาด AttributeError: ฟังก์ชัน '{e.name}' อาจจะไม่มีอยู่ใน db_handler ของคุณ")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการเตรียมหรือบันทึกข้อมูล: {e}")

def render_portfolio_manager_expander(db_handler, df_portfolios):
    """
    Renders the main expander and tabs for portfolio management.
    """
    with st.expander("💼 Portfolio Manager (Dashboard/Add/Edit)", expanded=False):
        
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Add New Portfolio", "✏️ Edit/Delete Portfolio"])

        with tab1:
            df_actual_trades = db_handler.load_actual_trades()
            df_summaries = db_handler.load_statement_summaries()
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
                name_to_action = st.selectbox("Select portfolio to Edit or Delete:", options=[""] + list(edit_dict.keys()), key="action_sel")
                
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