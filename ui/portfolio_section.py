# ui/portfolio_section.py
import streamlit as st
import pandas as pd
import uuid
from datetime import date
from .ai_section import render_ai_insights
# Import functions and settings from other modules
from core import gs_handler, portfolio_logic, analytics_engine

# =============================================================================
# Helper & Rendering Functions
# =============================================================================

def _render_portfolio_header(details: dict, df_actual_trades: pd.DataFrame, df_summaries: pd.DataFrame):
    """
    [v9 Final Corrected] แก้ไข IndentationError และจัดวาง Layout ทั้งหมดให้ถูกต้อง
    """
    if not details:
        st.info("กรุณาเลือกพอร์ตจาก Sidebar เพื่อดูข้อมูล")
        return

    # --- ดึงข้อมูลสถิติทั้งหมด ---
    active_id = st.session_state.get('active_portfolio_id_gs')
    advanced_stats = analytics_engine.get_advanced_statistics(df_all_actual_trades=df_actual_trades, active_portfolio_id=active_id)
    full_stats = analytics_engine.get_full_dashboard_stats(
        df_all_actual_trades=df_actual_trades,
        df_all_summaries=df_summaries,
        active_portfolio_id=active_id
    )

    # --- ส่วนที่ 1: กล่องหัวข้อและรายละเอียด ---
    with st.container(border=True):
        portfolio_name = details.get('PortfolioName', 'N/A')
        account_size = float(details.get('InitialBalance', 0))
        prog_type = details.get('ProgramType', 'N/A')
        profit_target = details.get('ProfitTargetPercent', 0)
        status = details.get('Status', 'N/A')

        title_part = f"<h5 style='margin: 0; padding: 0;'>ภาพรวมพอร์ต: {portfolio_name}</h5>"
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

    # --- ส่วนที่ 2: สองคอลัมน์หลัก ---
    main_col1, main_col2 = st.columns([1.5, 1.8])

    # คอลัมน์ซ้าย (Advanced Statistics)
    with main_col1:
        st.markdown("##### Advanced Statistics")
        with st.container(border=True, height=310):
            if not advanced_stats:
                st.info("ไม่มีข้อมูลสถิติขั้นสูง")
            else:
                adv_col1, adv_col2 = st.columns(2)
                with adv_col1:
                    st.markdown("**ฟอร์ม 5 เทรดล่าสุด:**")
                    st.code(f"Long : {advanced_stats.get('recent_form_long', 'N/A')}\nShort: {advanced_stats.get('recent_form_short', 'N/A')}")
                    st.markdown("**ชนะ/แพ้ติดต่อกัน:**")
                    wins = advanced_stats.get('max_consecutive_wins')
                    loss = advanced_stats.get('max_consecutive_losses')
                    st.markdown(f"• ชนะ: `{int(wins)} ครั้ง`" if pd.notna(wins) else "• ชนะ: `N/A`")
                    st.markdown(f"• แพ้: `{int(loss)} ครั้ง`" if pd.notna(loss) else "• แพ้: `N/A`")
                
                with adv_col2: # <--- บรรทัดนี้คือจุดที่เคยมีปัญหา
                    st.markdown("**กำไร/ขาดทุนสูงสุด:**")
                    # ตรรกะการแสดงผล Long Win/Loss
                    win_l = advanced_stats.get('biggest_win_long')
                    loss_l = advanced_stats.get('biggest_loss_long')
                    win_l_display = f"<font color='#28a745'>{win_l:,.2f}</font>" if pd.notna(win_l) else "N/A"
                    loss_l_display = f"<font color='#dc3545'>{loss_l:,.2f}</font>" if pd.notna(loss_l) else "N/A"
                    if win_l_display == "N/A" and loss_l_display == "N/A":
                        st.markdown("• Long: `N/A`", unsafe_allow_html=True)
                    else:
                        st.markdown(f"• Long: {win_l_display} / {loss_l_display}", unsafe_allow_html=True)

                    # ตรรกะการแสดงผล Short Win/Loss
                    win_s = advanced_stats.get('biggest_win_short')
                    loss_s = advanced_stats.get('biggest_loss_short')
                    win_s_display = f"<font color='#28a745'>{win_s:,.2f}</font>" if pd.notna(win_s) else "N/A"
                    loss_s_display = f"<font color='#dc3545'>{loss_s:,.2f}</font>" if pd.notna(loss_s) else "N/A"
                    if win_s_display == "N/A" and loss_s_display == "N/A":
                        st.markdown("• Short: `N/A`", unsafe_allow_html=True)
                    else:
                        st.markdown(f"• Short: {win_s_display} / {loss_s_display}", unsafe_allow_html=True)

                    st.markdown("**ความสม่ำเสมอ:**")
                    conc = advanced_stats.get('profit_concentration', 0)
                    days = advanced_stats.get('active_trading_days', 0)
                    st.markdown(f"• Profit Conc.: `{conc:.1f}%`" if conc > 0 else "• Profit Conc.: `N/A`")
                    st.markdown(f"• Active Days: `{days} วัน`")


    # คอลัมน์ขวา (Performance Metrics)
    with main_col2:
        st.markdown("##### Performance Metrics")
        with st.container(border=True, height=310):
            if not full_stats:
                st.info("ไม่มีข้อมูลสถิติ")
            else:
                def format_metric(label, value, currency=False, percent=False, ratio=False, color_cond=False):
                    if pd.isna(value) or value == '':
                        return f"<div style='display: flex; justify-content: space-between;'><span><b>{label}:</b></span> <span>N/A</span></div>"
                    if not isinstance(value, (int, float)):
                        return f"<div style='display: flex; justify-content: space-between;'><span><b>{label}:</b></span> <span>{value}</span></div>"
                    
                    color = "white"
                    if color_cond:
                        color = "#28a745" if value >= 0 else "#dc3545"

                    if currency:
                        val_str = f"${value:,.2f}"
                        if not color_cond: color = "#28a745" if value > 0 else "#dc3545" if value < 0 else "white"
                    elif percent: val_str = f"{value:.2f}%"
                    elif ratio: val_str = f"{value:.2f}"
                    else: val_str, color = str(int(value)), "white"
                    return f"<div style='display: flex; justify-content: space-between;'><span><b>{label}:</b></span> <span style='color: {color};'>{val_str}</span></div>"

                sub_col1, sub_col2 = st.columns(2)
                with sub_col1:
                    st.markdown(format_metric("Total Trades", full_stats.get('total_trades')), unsafe_allow_html=True)
                    st.markdown(format_metric("Profit Trades", full_stats.get('profit_trades')), unsafe_allow_html=True)
                    st.markdown(format_metric("Loss Trades", full_stats.get('loss_trades')), unsafe_allow_html=True)
                    st.markdown(format_metric("Breakeven Trades", full_stats.get('breakeven_trades')), unsafe_allow_html=True)
                    st.markdown(format_metric("Long Trades", full_stats.get('long_trades')), unsafe_allow_html=True)
                    st.markdown(format_metric("Short Trades", full_stats.get('short_trades')), unsafe_allow_html=True)      
                    st.markdown(format_metric("Best Profit", full_stats.get('best_profit'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Biggest Loss", full_stats.get('biggest_loss'), currency=True), unsafe_allow_html=True)
                    st.markdown(f"<div style='display: flex; justify-content: space-between;'><span><b>Avg. Trade Duration:</b></span> <span>{full_stats.get('avg_trade_duration_str', 'N/A')}</span></div>", unsafe_allow_html=True)
                with sub_col2:    
                    st.markdown(format_metric("Avg. Profit", full_stats.get('avg_profit'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Loss", full_stats.get('avg_loss'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Trade Size", full_stats.get('avg_trade_size'), ratio=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Gross Profit", full_stats.get('gross_profit'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Gross Loss", full_stats.get('gross_loss'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Total Net Profit", full_stats.get('total_net_profit'), currency=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Profit Factor", full_stats.get('profit_factor'), ratio=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Win Rate", full_stats.get('win_rate'), percent=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Expectancy", full_stats.get('expectancy'), currency=True, color_cond=True), unsafe_allow_html=True)

   # --- เพิ่มส่วนนี้: ผลตอบแทนและรายการเงินทุนพอร์ต ---
    st.markdown("---")
    st.subheader("📊 ผลตอบแทนและรายการเงินทุนพอร์ต")

    # ดึงค่าจาก session_state ที่ app.py คำนวณและเก็บไว้
    realized_net_profit = st.session_state.get('realized_profit_loss')
    total_deposit = st.session_state.get('total_deposit_amount')
    total_withdrawal = st.session_state.get('total_withdrawal_amount')
    total_net_profit_from_sheet = st.session_state.get('total_net_profit_from_sheet')

    if realized_net_profit is not None:
        col_rp, col_dep, col_wit, col_net_from_sheet = st.columns(4) # เพิ่ม col_net_from_sheet

        with col_rp:
            st.metric(
                "กำไร/ขาดทุนรวมทั้งหมด",
                f"{realized_net_profit:,.2f} USD"
            )
        with col_dep:
            st.metric(
                "ยอดฝากรวม",
                f"{total_deposit:,.2f} USD"
            )
        with col_wit:
            st.metric(
                "ยอดถอนรวม",
                f"{total_withdrawal:,.2f} USD"
            )
        with col_net_from_sheet: # แสดง Net Profit จาก Sheet ด้วย
            st.metric(
                "กำไร/ขาดทุนจากการเทรด (จาก Sheet)",
                f"{total_net_profit_from_sheet:,.2f} USD"
            )
    else:
        st.info("ไม่พบข้อมูลผลตอบแทนพอร์ต กรุณาเลือกพอร์ตที่ใช้งาน")

    # --- กราฟ True Equity Curve ---
    df_equity_curve_data = st.session_state.get('df_equity_curve_data')
    if df_equity_curve_data is not None and not df_equity_curve_data.empty:
        st.markdown("---")
        st.markdown("#### กราฟ True Equity Curve")
        # ตรวจสอบว่า df_equity_curve_data มีคอลัมน์ 'Timestamp' และ 'Equity For Chart'
        if 'Timestamp' in df_equity_curve_data.columns and 'Equity For Chart' in df_equity_curve_data.columns:
            st.line_chart(df_equity_curve_data, x='Timestamp', y='Equity For Chart')
        else:
            st.warning("ข้อมูลกราฟ True Equity Curve ไม่สมบูรณ์ (ขาดคอลัมน์ Timestamp หรือ Equity For Chart)")
    else:
        st.info("ไม่มีข้อมูลสำหรับสร้างกราฟ True Equity Curve")

         # --- ส่วนที่ 3: AI-Powered Insights ---
    #st.divider()
    st.subheader("🤖 AI-Powered Insights")
    with st.container(border=True):
        # --- [แก้ไข] เปลี่ยน active_portfolio_id เป็น active_id ---
        insights = analytics_engine.get_ai_powered_insights(df_actual_trades, active_id)
        
        # เพิ่ม import ของ render_ai_insights ที่ด้านบนของไฟล์ด้วย
        # from ui.ai_section import render_ai_insights
        
        if not insights:
            st.info("มีข้อมูลไม่เพียงพอสำหรับสร้าง Insights")
        else:
            render_ai_insights(insights)

def _render_portfolio_form(is_edit_mode, portfolio_to_edit_data={}, df_portfolios_gs=pd.DataFrame()):
    """
    แสดงฟอร์มสำหรับเพิ่มหรือแก้ไขพอร์ต (ฉบับรวมและแก้ไข Key สมบูรณ์)
    """
    # <<< แก้ไข: ใช้ Logic การจัดการ State ที่ดีที่สุด เพื่อป้องกัน Key ชนกันและ State ปนกัน >>>
    mode_suffix = "edit" if is_edit_mode else "add"
    
    # แยก session_state ของแต่ละฟอร์มออกจากกันโดยสิ้นเชิง
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
        "ประเภทพอร์ต (Program Type)*",
        options=program_type_options,
        index=type_index,
        key=widget_key_program_type,
        on_change=on_program_type_change
    )
    
    selected_program_type = st.session_state.get(session_key_program_type)

    with st.form(key=f"portfolio_form_{mode_suffix}", clear_on_submit=False):
        st.markdown(f"**กรอกข้อมูลพอร์ต (สำหรับประเภท: {selected_program_type or 'ยังไม่ได้เลือก'})**")

        key_prefix = mode_suffix
        
        # --- ส่วนของฟอร์มทั้งหมด ---
        # <<< แก้ไข: เพิ่ม Key ที่ถูกต้องและไม่ซ้ำกันให้กับวิดเจ็ตทุกตัว >>>
        form_c1, form_c2 = st.columns(2)
        with form_c1:
            form_new_portfolio_name = st.text_input("ชื่อพอร์ต (Portfolio Name)*", value=portfolio_to_edit_data.get("PortfolioName", ""), key=f"{key_prefix}_name")
        with form_c2:
            form_new_initial_balance = st.number_input("บาลานซ์เริ่มต้น (Initial Balance)*", min_value=0.01, value=float(portfolio_to_edit_data.get("InitialBalance", 10000.0)), format="%.2f", key=f"{key_prefix}_balance")

        form_status_options = ["Active", "Inactive", "Pending", "Passed", "Failed"]
        status_default = portfolio_to_edit_data.get("Status", "Active")
        status_index = form_status_options.index(status_default) if status_default in form_status_options else 0
        form_new_status = st.selectbox("สถานะพอร์ต (Status)*", options=form_status_options, index=status_index, key=f"{key_prefix}_status")

        form_new_evaluation_step_widget = ""
        if selected_program_type == "Prop Firm Challenge":
            evaluation_step_options = ["", "Phase 1", "Phase 2", "Phase 3", "Verification"]
            eval_default = portfolio_to_edit_data.get("EvaluationStep", "")
            eval_index = evaluation_step_options.index(eval_default) if eval_default in evaluation_step_options else 0
            form_new_evaluation_step_widget = st.selectbox("ขั้นตอนการประเมิน (Evaluation Step)", options=evaluation_step_options, index=eval_index, key=f"{key_prefix}_eval_step")
        
        prop_profit_target_widget, prop_daily_loss_widget, prop_total_stopout_widget, prop_leverage_widget, prop_min_days_widget = (None,) * 5
        comp_end_date_widget, comp_profit_target_widget, comp_goal_metric_widget, comp_daily_loss_widget, comp_total_stopout_widget = (None,) * 5
        pers_overall_profit_widget, pers_weekly_profit_widget, pers_max_dd_overall_widget, pers_target_end_date_widget, pers_daily_profit_widget, pers_max_dd_daily_widget = (None,) * 6
        scaling_freq_val_widget, su_wr_val_widget, sd_loss_val_widget, min_risk_val_widget, su_gain_val_widget, sd_wr_val_widget, max_risk_val_widget, su_inc_val_widget, sd_dec_val_widget, current_risk_s_val_widget = (None,) * 10
        
        if selected_program_type in ["Prop Firm Challenge", "Funded Account"]:
            st.markdown("**กฎเกณฑ์ Prop Firm/Funded:**")
            f_pf1, f_pf2, f_pf3 = st.columns(3)
            with f_pf1: prop_profit_target_widget = st.number_input("เป้าหมายกำไร %*", value=float(portfolio_to_edit_data.get("ProfitTargetPercent", 8.0)), format="%.1f", key=f"{key_prefix}_prop_profit")
            with f_pf2: prop_daily_loss_widget = st.number_input("จำกัดขาดทุนต่อวัน %*", value=float(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f", key=f"{key_prefix}_prop_daily_loss")
            with f_pf3: prop_total_stopout_widget = st.number_input("จำกัดขาดทุนรวม %*", value=float(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f", key=f"{key_prefix}_prop_total_loss")
            f_pf_col1, f_pf_col2 = st.columns(2)
            with f_pf_col1: prop_leverage_widget = st.number_input("Leverage", value=float(portfolio_to_edit_data.get("Leverage", 100.0)), format="%.0f", key=f"{key_prefix}_prop_leverage")
            with f_pf_col2: prop_min_days_widget = st.number_input("จำนวนวันเทรดขั้นต่ำ", value=int(portfolio_to_edit_data.get("MinTradingDays", 0)), step=1, key=f"{key_prefix}_prop_min_days")

        if selected_program_type == "Trading Competition":
            st.markdown("**ข้อมูลการแข่งขัน:**")
            f_tc1, f_tc2 = st.columns(2)
            with f_tc1:
                comp_end_date_widget = st.date_input("วันสิ้นสุดการแข่งขัน", value=pd.to_datetime(portfolio_to_edit_data.get("CompetitionEndDate")).date() if pd.notna(portfolio_to_edit_data.get("CompetitionEndDate")) else None, key=f"{key_prefix}_comp_date")
                comp_profit_target_widget = st.number_input("เป้าหมายกำไร % (Comp)", value=float(portfolio_to_edit_data.get("ProfitTargetPercent", 20.0)), format="%.1f", key=f"{key_prefix}_comp_profit")
            with f_tc2:
                comp_goal_metric_widget = st.text_input("ตัวชี้วัดเป้าหมาย (Comp)", value=portfolio_to_edit_data.get("GoalMetric", ""), help="เช่น %Gain, ROI", key=f"{key_prefix}_comp_goal")
                comp_daily_loss_widget = st.number_input("จำกัดขาดทุนต่อวัน % (Comp)", value=float(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f", key=f"{key_prefix}_comp_daily_loss")
                comp_total_stopout_widget = st.number_input("จำกัดขาดทุนรวม % (Comp)", value=float(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f", key=f"{key_prefix}_comp_total_stopout")

        if selected_program_type == "Personal Account":
            st.markdown("**เป้าหมายส่วนตัว (Optional):**")
            f_ps1, f_ps2 = st.columns(2)
            with f_ps1:
                pers_overall_profit_widget = st.number_input("เป้าหมายกำไรโดยรวม ($)", value=float(portfolio_to_edit_data.get("OverallProfitTarget", 0.0)), format="%.2f", key=f"{key_prefix}_pers_profit")
                pers_weekly_profit_widget = st.number_input("เป้าหมายกำไรรายสัปดาห์ ($)", value=float(portfolio_to_edit_data.get("WeeklyProfitTarget", 0.0)), format="%.2f", key=f"{key_prefix}_pers_weekly_profit")
                pers_max_dd_overall_widget = st.number_input("Max DD รวมที่ยอมรับได้ ($)", value=float(portfolio_to_edit_data.get("MaxAcceptableDrawdownOverall", 0.0)), format="%.2f", key=f"{key_prefix}_pers_dd_overall")
            with f_ps2:
                pers_target_end_date_widget = st.date_input("วันที่คาดว่าจะถึงเป้าหมายรวม", value=pd.to_datetime(portfolio_to_edit_data.get("TargetEndDate")).date() if pd.notna(portfolio_to_edit_data.get("TargetEndDate")) else None, key=f"{key_prefix}_pers_end_date")
                pers_daily_profit_widget = st.number_input("เป้าหมายกำไรรายวัน ($)", value=float(portfolio_to_edit_data.get("DailyProfitTarget", 0.0)), format="%.2f", key=f"{key_prefix}_pers_daily_profit")
                pers_max_dd_daily_widget = st.number_input("Max DD ต่อวันที่ยอมรับได้ ($)", value=float(portfolio_to_edit_data.get("MaxAcceptableDrawdownDaily", 0.0)), format="%.2f", key=f"{key_prefix}_pers_dd_daily")

        st.markdown("**การตั้งค่า Scaling Manager (Optional):**")
        enable_scaling_checkbox_val = st.checkbox("เปิดใช้งาน Scaling Manager?", value=str(portfolio_to_edit_data.get("EnableScaling", "False")).upper() == 'TRUE', key=f"{key_prefix}_scaling_cb")

        if enable_scaling_checkbox_val:
            f_sc1, f_sc2, f_sc3 = st.columns(3)
            with f_sc1:
                scaling_freq_options = ["Weekly", "Monthly"]
                scaling_freq_default = portfolio_to_edit_data.get("ScalingCheckFrequency", "Weekly")
                scaling_freq_index = scaling_freq_options.index(scaling_freq_default) if scaling_freq_default in scaling_freq_options else 0
                scaling_freq_val_widget = st.selectbox("ความถี่ตรวจสอบ Scaling", options=scaling_freq_options, index=scaling_freq_index, key=f"{key_prefix}_scaling_freq")
                su_wr_val_widget = st.number_input("Scale Up: Min Winrate %", value=float(portfolio_to_edit_data.get("ScaleUp_MinWinRate", 55.0)), format="%.1f", key=f"{key_prefix}_su_wr")
                sd_loss_val_widget = st.number_input("Scale Down: Max Loss %", value=float(portfolio_to_edit_data.get("ScaleDown_MaxLossPercent", -5.0)), format="%.1f", key=f"{key_prefix}_sd_loss")
            with f_sc2:
                min_risk_val_widget = st.number_input("Min Risk % Allowed", value=float(portfolio_to_edit_data.get("MinRiskPercentAllowed", 0.25)), min_value=0.01, format="%.2f", key=f"{key_prefix}_min_risk")
                su_gain_val_widget = st.number_input("Scale Up: Min Gain %", value=float(portfolio_to_edit_data.get("ScaleUp_MinGainPercent", 2.0)), format="%.1f", key=f"{key_prefix}_su_gain")
                sd_wr_val_widget = st.number_input("Scale Down: Low Winrate %", value=float(portfolio_to_edit_data.get("ScaleDown_LowWinRate", 40.0)), format="%.1f", key=f"{key_prefix}_sd_wr")
            with f_sc3:
                max_risk_val_widget = st.number_input("Max Risk % Allowed", value=float(portfolio_to_edit_data.get("MaxRiskPercentAllowed", 2.0)), min_value=0.01, format="%.2f", key=f"{key_prefix}_max_risk")
                su_inc_val_widget = st.number_input("Scale Up: Risk Increment %", value=float(portfolio_to_edit_data.get("ScaleUp_RiskIncrementPercent", 0.25)), format="%.2f", key=f"{key_prefix}_su_inc")
                sd_dec_val_widget = st.number_input("Scale Down: Risk Decrement %", value=float(portfolio_to_edit_data.get("ScaleDown_RiskDecrementPercent", 0.25)), format="%.2f", key=f"{key_prefix}_sd_dec")
            current_risk_s_val_widget = st.number_input("Current Risk % (สำหรับ Scaling)", value=float(portfolio_to_edit_data.get("CurrentRiskPercent", 1.0)), min_value=0.01, format="%.2f", key=f"{key_prefix}_current_risk")
        
        notes_val_area_widget = st.text_area("หมายเหตุเพิ่มเติม (Notes)", value=portfolio_to_edit_data.get("Notes", ""), key=f"{key_prefix}_notes")

        submit_button_label = "💾 อัปเดตข้อมูลพอร์ต" if is_edit_mode else "💾 บันทึกพอร์ตใหม่"
        submitted = st.form_submit_button(submit_button_label)

        if submitted:
            if not form_new_portfolio_name or not selected_program_type or not form_new_status or form_new_initial_balance <= 0:
                st.warning("กรุณากรอกข้อมูลที่จำเป็น (*) ให้ครบถ้วนและถูกต้อง")
            else:
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
                    with st.spinner("กำลังอัปเดต..."): 
                        success = gs_handler.update_portfolio_in_gsheets(portfolio_id_to_update, data_to_save)
                    if success:
                        st.success(f"อัปเดตข้อมูลพอร์ต '{form_new_portfolio_name}' สำเร็จ!")
                        
                    else: 
                        st.error("การอัปเดตข้อมูลพอร์ตล้มเหลว")
                else:
                    if not df_portfolios_gs.empty and form_new_portfolio_name in df_portfolios_gs['PortfolioName'].astype(str).values:
                        st.error(f"ชื่อพอร์ต '{form_new_portfolio_name}' มีอยู่แล้ว กรุณาใช้ชื่ออื่น")
                    else:
                        with st.spinner("กำลังบันทึก..."): 
                            success_save = gs_handler.save_new_portfolio_to_gsheets(data_to_save)
                        if success_save:
                            st.success(f"เพิ่มพอร์ต '{form_new_portfolio_name}' สำเร็จ!")
                            if session_key_program_type in st.session_state:
                                del st.session_state[session_key_program_type]
                            
                        else: 
                            st.error("เกิดข้อผิดพลาดในการบันทึกพอร์ตใหม่")


def render_portfolio_manager_expander(df_portfolios):
    """
    สร้าง Expander หลักและแท็บสำหรับจัดการพอร์ต (ใช้ชื่อนี้เป็นมาตรฐานตามที่ app.py เรียก)
    """
    with st.expander("💼 จัดการพอร์ต (ดูแดชบอร์ด/เพิ่ม/แก้ไข)", expanded=True):
        
        
        tab1, tab2, tab3 = st.tabs(["📊 แดชบอร์ดพอร์ต", "➕ เพิ่มพอร์ตใหม่", "✏️ แก้ไข/ลบพอร์ต"])

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
                    st.error("ไม่พบข้อมูลสำหรับพอร์ตที่เลือก")
            else:
                st.info("กรุณาเลือกพอร์ตที่ใช้งานจากแถบข้าง (Sidebar) เพื่อแสดงข้อมูล")

        with tab2:
            st.subheader("➕ เพิ่มพอร์ตใหม่")
            _render_portfolio_form(is_edit_mode=False, df_portfolios_gs=df_portfolios)

        with tab3:
            st.subheader("✏️ แก้ไข/ลบพอร์ต")
            if df_portfolios.empty: 
                st.info("ยังไม่มีพอร์ตให้แก้ไข")
            else:
                edit_dict = dict(zip(df_portfolios['PortfolioName'], df_portfolios['PortfolioID']))
                name_to_edit = st.selectbox("เลือกพอร์ตที่ต้องการแก้ไข:", options=[""] + list(edit_dict.keys()), key="edit_sel")
                if name_to_edit:
                    id_to_edit = edit_dict[name_to_edit]
                    data_to_edit = df_portfolios[df_portfolios['PortfolioID'] == id_to_edit].iloc[0].to_dict()
                    _render_portfolio_form(is_edit_mode=True, portfolio_to_edit_data=data_to_edit, df_portfolios_gs=df_portfolios)