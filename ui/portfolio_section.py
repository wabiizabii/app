# ui/portfolio_section.py
import streamlit as st
import pandas as pd
import uuid
from datetime import date

# Import functions and settings from other modules
from core import gs_handler
from core import portfolio_logic
from core import analytics_engine

# ui/portfolio_section.py
import streamlit as st
import pandas as pd
from datetime import date

# Import functions and settings from other modules
from core import gs_handler, portfolio_logic, analytics_engine

# =============================================================================
# Helper & Rendering Functions
# =============================================================================

def _get_last_n_trades_string(df_all_actual_trades: pd.DataFrame, portfolio_id: str, n=5) -> dict:
    """สร้างสตริงผลลัพธ์ W/L/B สำหรับ n เทรดล่าสุด"""
    if df_all_actual_trades.empty or portfolio_id not in df_all_actual_trades['PortfolioID'].values:
        return {"long": "N/A", "short": "N/A"}
    trades = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == portfolio_id].sort_values(by='Time_Deal', ascending=False)
    def get_result(pnl):
        return 'W' if pnl > 0 else 'L' if pnl < 0 else 'B'
    long_trades = trades[trades['DealDirection'] == 'LONG'].head(n)
    short_trades = trades[trades['DealDirection'] == 'SHORT'].head(n)
    long_str = "-".join(long_trades['NetPL'].apply(get_result)) if not long_trades.empty else "No trades"
    short_str = "-".join(short_trades['NetPL'].apply(get_result)) if not short_trades.empty else "No trades"
    return {"long": long_str, "short": short_str}

def _render_portfolio_header(details: dict, df_actual_trades: pd.DataFrame, df_summaries: pd.DataFrame):
    """แสดงผลแดชบอร์ดหลักของพอร์ต"""
    if not details:
        st.info("กรุณาเลือกพอร์ตจาก Sidebar เพื่อดูข้อมูล")
        return

    active_id = st.session_state.get('active_portfolio_id')
    advanced_stats = analytics_engine.get_advanced_statistics(df_all_actual_trades=df_actual_trades, active_portfolio_id=active_id)
    full_stats = analytics_engine.get_full_dashboard_stats(df_all_actual_trades=df_actual_trades, df_all_summaries=df_summaries, active_portfolio_id=active_id)

    st.subheader(f"ภาพรวมพอร์ต: {details.get('PortfolioName', 'N/A')}")
    st.markdown("---")

    main_col1, main_col2 = st.columns([1.5, 1.8])

    with main_col1:
        st.markdown("##### Advanced Statistics")
        with st.container(border=True, height=280):
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
                with adv_col2:
                    st.markdown("**กำไร/ขาดทุนสูงสุด:**")
                    win_l, loss_l = advanced_stats.get('biggest_win_long'), advanced_stats.get('biggest_loss_long')
                    win_s, loss_s = advanced_stats.get('biggest_win_short'), advanced_stats.get('biggest_loss_short')
                    st.markdown(f"• Long: <font color='green'>{win_l:,.2f}</font> / <font color='red'>{loss_l:,.2f}</font>" if pd.notna(win_l) and pd.notna(loss_l) else "• Long: `N/A`", unsafe_allow_html=True)
                    st.markdown(f"• Short: <font color='green'>{win_s:,.2f}</font> / <font color='red'>{loss_s:,.2f}</font>" if pd.notna(win_s) and pd.notna(loss_s) else "• Short: `N/A`", unsafe_allow_html=True)
                    st.markdown("**ความสม่ำเสมอ:**")
                    conc = advanced_stats.get('profit_concentration', 0)
                    days = advanced_stats.get('active_trading_days', 0)
                    st.markdown(f"• Profit Conc.: `{conc:.1f}%`" if conc > 0 else "• Profit Conc.: `N/A`")
                    st.markdown(f"• Active Days: `{days} วัน`")

    with main_col2:
        st.markdown("##### Performance Metrics")
        with st.container(border=True, height=280):
            if not full_stats:
                st.info("ไม่มีข้อมูลสถิติ")
            else:
                def format_metric(label, value, currency=False, percent=False, ratio=False, color_cond=False):
                    if not pd.notna(value) or value == '': return f"<div style='display: flex; justify-content: space-between;'><span><b>{label}:</b></span> <span>N/A</span></div>"
                    color = "#28a745" if value >= 0 else "#dc3545" if color_cond else "white"
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
                    st.markdown(format_metric("Long Trades", full_stats.get('long_trades')), unsafe_allow_html=True)
                    st.markdown(format_metric("Short Trades", full_stats.get('short_trades')), unsafe_allow_html=True)
                    st.markdown(format_metric("Gross Profit", full_stats.get('gross_profit'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Gross Loss", full_stats.get('gross_loss'), currency=True), unsafe_allow_html=True)
                with sub_col2:
                    st.markdown(format_metric("Best Profit", full_stats.get('best_profit'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Biggest Loss", full_stats.get('biggest_loss'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Profit", full_stats.get('avg_profit'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Loss", full_stats.get('avg_loss'), currency=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Expectancy", full_stats.get('expectancy'), currency=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Avg. Trade Size", full_stats.get('avg_trade_size'), ratio=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Total Net Profit", full_stats.get('total_net_profit'), currency=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Profit Factor", full_stats.get('profit_factor'), ratio=True, color_cond=True), unsafe_allow_html=True)
                    st.markdown(format_metric("Win Rate", full_stats.get('win_rate'), percent=True), unsafe_allow_html=True)


def _render_portfolio_form(is_edit_mode, portfolio_to_edit_data={}, df_portfolios_gs=pd.DataFrame()):
    """แสดงฟอร์มสำหรับเพิ่มหรือแก้ไขพอร์ต"""
    mode_suffix = "edit" if is_edit_mode else "add"
    def on_program_type_change():
        st.session_state[f'form_program_type_{mode_suffix}'] = st.session_state[f'exp_pf_type_selector_widget_{mode_suffix}']

    program_type_options = ["", "Personal Account", "Prop Firm Challenge", "Funded Account", "Trading Competition"]
    session_key = f'form_program_type_{mode_suffix}'
    default_program_type = portfolio_to_edit_data.get("ProgramType", "")
    if session_key not in st.session_state: st.session_state[session_key] = default_program_type
    
    current_value = st.session_state.get(session_key, "")
    type_index = program_type_options.index(current_value) if current_value in program_type_options else 0

    st.selectbox("ประเภทพอร์ต (Program Type)*", options=program_type_options, index=type_index, key=f"exp_pf_type_selector_widget_{mode_suffix}", on_change=on_program_type_change)
    selected_program_type = st.session_state.get(session_key)

    with st.form(key=f"portfolio_form_{mode_suffix}", clear_on_submit=False):
        st.markdown(f"**กรอกข้อมูลพอร์ต (สำหรับประเภท: {selected_program_type or 'ยังไม่ได้เลือก'})**")
        # ... (ส่วนที่เหลือของฟอร์มเหมือนเดิม) ...
        # (The rest of the form fields go here, no changes needed)
        st.form_submit_button("💾 บันทึกข้อมูล")


# =============================================================================
# Main Expander Function
# =============================================================================

def render_portfolio_manager_expander():
    """สร้าง Expander หลักและแท็บสำหรับจัดการพอร์ต"""
    with st.expander("💼 จัดการพอร์ต (ดูแดชบอร์ด/เพิ่ม/แก้ไข)", expanded=True):
        df_portfolios = gs_handler.load_portfolios_from_gsheets()
        tab1, tab2, tab3 = st.tabs(["📊 แดชบอร์ดพอร์ต", "➕ เพิ่มพอร์ตใหม่", "✏️ แก้ไข/ลบพอร์ต"])

        with tab1:
            df_actual_trades = gs_handler.load_actual_trades_from_gsheets()
            df_summaries = gs_handler.load_statement_summaries_from_gsheets()
            active_portfolio_id = st.session_state.get('active_portfolio_id')
            if active_portfolio_id and not df_portfolios.empty:
                details_df = df_portfolios[df_portfolios['PortfolioID'] == active_portfolio_id]
                if not details_df.empty:
                    _render_portfolio_header(details=details_df.iloc[0].to_dict(), df_actual_trades=df_actual_trades, df_summaries=df_summaries)
                else: st.error("ไม่พบข้อมูลสำหรับพอร์ตที่เลือก")
            else: st.info("กรุณาเลือกพอร์ตที่ใช้งานจาก Sidebar เพื่อแสดงข้อมูล")

        with tab2:
            st.subheader("➕ เพิ่มพอร์ตใหม่")
            _render_portfolio_form(is_edit_mode=False, df_portfolios_gs=df_portfolios)

        with tab3:
            st.subheader("✏️ แก้ไข/ลบพอร์ต")
            if df_portfolios.empty: st.info("ยังไม่มีพอร์ตให้แก้ไข")
            else:
                edit_dict = dict(zip(df_portfolios['PortfolioName'], df_portfolios['PortfolioID']))
                name_to_edit = st.selectbox("เลือกพอร์ตที่ต้องการแก้ไข:", options=[""] + list(edit_dict.keys()), key="edit_sel_v3")
                if name_to_edit:
                    id_to_edit = edit_dict[name_to_edit]
                    data_to_edit = df_portfolios[df_portfolios['PortfolioID'] == id_to_edit].iloc[0].to_dict()
                    _render_portfolio_form(is_edit_mode=True, portfolio_to_edit_data=data_to_edit, df_portfolios_gs=df_portfolios)

            st.markdown("---")
            st.markdown(format_metric("Win Rate", full_stats.get('win_rate'), percent=True), unsafe_allow_html=True)
def render_portfolio_manager_expander():
    with st.expander("💼 จัดการพอร์ต (ดูแดชบอร์ด/เพิ่ม/แก้ไข)", expanded=True): # เปิดไว้เป็นค่าเริ่มต้น
        df_portfolios = gs_handler.load_portfolios_from_gsheets()
        tab1, tab2, tab3 = st.tabs(["📊 แดชบอร์ดพอร์ต", "➕ เพิ่มพอร์ตใหม่", "✏️ แก้ไข/ลบพอร์ต"])

        with tab1:
            df_actual_trades = gs_handler.load_actual_trades_from_gsheets()
            df_summaries = gs_handler.load_statement_summaries_from_gsheets()
            active_portfolio_id = st.session_state.get('active_portfolio_id')

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
            # --- แก้ไข: ส่ง df_portfolios เข้าไปในฟังก์ชัน ---
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
                    # --- แก้ไข: ส่ง df_portfolios เข้าไปในฟังก์ชัน ---
                    _render_portfolio_form(is_edit_mode=True, portfolio_to_edit_data=data_to_edit, df_portfolios_gs=df_portfolios)


def _render_portfolio_form(is_edit_mode, portfolio_to_edit_data={}, df_portfolios_gs=pd.DataFrame()):
    """แสดงฟอร์มสำหรับเพิ่มหรือแก้ไขพอร์ต (แก้ไข key ซ้ำซ้อน)"""

    # 1. สร้าง "คำต่อท้าย" ที่ไม่ซ้ำกันสำหรับ key ตามโหมด (add หรือ edit)
    mode_suffix = "edit" if is_edit_mode else "add"

    def on_program_type_change():
        # 2. อัปเดต session_state โดยใช้ key ที่ไม่ซ้ำกัน
        st.session_state[f'form_program_type_{mode_suffix}'] = st.session_state[f'exp_pf_type_selector_widget_{mode_suffix}']

    program_type_options = ["", "Personal Account", "Prop Firm Challenge", "Funded Account", "Trading Competition"]
    
    # 3. กำหนด key สำหรับ session state ให้ไม่ซ้ำกัน
    session_key = f'form_program_type_{mode_suffix}'

    # ตั้งค่าเริ่มต้นให้ session state
    default_program_type = portfolio_to_edit_data.get("ProgramType", "")
    if session_key not in st.session_state:
        st.session_state[session_key] = default_program_type
    
    current_value = st.session_state.get(session_key, "")
    type_index = program_type_options.index(current_value) if current_value in program_type_options else 0

    st.selectbox(
        "ประเภทพอร์ต (Program Type)*",
        options=program_type_options,
        index=type_index,
        key=f"exp_pf_type_selector_widget_{mode_suffix}",  # 4. ใช้ key ของ selectbox ที่ไม่ซ้ำกัน
        on_change=on_program_type_change
    )
    
    selected_program_type = st.session_state.get(session_key)

    # 5. ใช้ key ของฟอร์มที่ไม่ซ้ำกันด้วย
    with st.form(key=f"portfolio_form_{mode_suffix}", clear_on_submit=False):
        st.markdown(f"**กรอกข้อมูลพอร์ต (สำหรับประเภท: {selected_program_type or 'ยังไม่ได้เลือก'})**")
        
        form_c1, form_c2 = st.columns(2)
        with form_c1:
            form_name = st.text_input("ชื่อพอร์ต*", value=portfolio_to_edit_data.get("PortfolioName", ""))
        with form_c2:
            form_balance = st.number_input("บาลานซ์เริ่มต้น*", min_value=0.01, value=float(portfolio_to_edit_data.get("InitialBalance", 10000.0)), format="%.2f")
        
        statuses = ["Active", "Inactive", "Pending", "Passed", "Failed"]
        status_default = portfolio_to_edit_data.get("Status", "Active")
        status_idx = statuses.index(status_default) if status_default in statuses else 0
        form_status = st.selectbox("สถานะ*", options=statuses, index=status_idx)
        
        form_eval_step = None
        if selected_program_type == "Prop Firm Challenge":
            eval_opts = ["", "Phase 1", "Phase 2", "Phase 3", "Verification"]
            eval_default = portfolio_to_edit_data.get("EvaluationStep", "")
            eval_idx = eval_opts.index(eval_default) if eval_default in eval_opts else 0
            form_eval_step = st.selectbox("ขั้นตอน", options=eval_opts, index=eval_idx)
        
        prop_profit, prop_daily_loss, prop_total_loss, prop_leverage, prop_min_days = (None,) * 5
        if selected_program_type in ["Prop Firm Challenge", "Funded Account"]:
            st.markdown("**กฎเกณฑ์ Prop Firm/Funded:**")
            f1, f2, f3 = st.columns(3)
            f4, f5 = st.columns(2)
            with f1: prop_profit = st.number_input("เป้าหมายกำไร %*", value=float(portfolio_to_edit_data.get("ProfitTargetPercent", 8.0)), format="%.1f")
            with f2: prop_daily_loss = st.number_input("จำกัดขาดทุนต่อวัน %*", value=float(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f")
            with f3: prop_total_loss = st.number_input("จำกัดขาดทุนรวม %*", value=float(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f")
            with f4: prop_leverage = st.number_input("Leverage", value=float(portfolio_to_edit_data.get("Leverage", 100.0)), format="%.0f")
            with f5: prop_min_days = st.number_input("วันเทรดขั้นต่ำ", value=int(portfolio_to_edit_data.get("MinTradingDays", 0)), step=1)
        
        notes = st.text_area("หมายเหตุ", value=portfolio_to_edit_data.get("Notes", ""), key=f"notes_{mode_suffix}")
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if not form_name or not selected_program_type or not form_status or form_balance <= 0:
                st.warning("กรุณากรอกข้อมูลที่จำเป็น (*)")
                return

            # Note: The logic for saving data (portfolio_logic.prepare...) is assumed to be correct and is not modified.
            # You might need to adjust it if it depends on non-existent widget values from other form types.
            data_to_save = portfolio_logic.prepare_new_portfolio_data_for_gsheet(
                form_new_portfolio_name_in_form=form_name,
                selected_program_type_to_use_in_form=selected_program_type,
                form_new_initial_balance_in_form=form_balance,
                form_new_status_in_form=form_status,
                form_new_evaluation_step_val_in_form=form_eval_step,
                form_notes_val=notes,
                form_profit_target_val=prop_profit,
                form_daily_loss_val=prop_daily_loss,
                form_total_stopout_val=prop_total_loss,
                form_leverage_val=prop_leverage,
                form_min_days_val=prop_min_days
                # Pass None for other form types' widgets to avoid errors
                # ... other arguments set to None ...
            )
            
            if is_edit_mode:
                pid = portfolio_to_edit_data.get("PortfolioID")
                data_to_save["PortfolioID"] = pid
                with st.spinner("กำลังอัปเดต..."):
                    success = gs_handler.update_portfolio_in_gsheets(pid, data_to_save)
                if success:
                    st.success("อัปเดตสำเร็จ!")
                    st.rerun()
                else:
                    st.error("อัปเดตล้มเหลว")
            else:
                if not df_portfolios_gs.empty and form_name in df_portfolios_gs['PortfolioName'].astype(str).values:
                    st.error(f"ชื่อพอร์ต '{form_name}' มีอยู่แล้ว")
                    return
                with st.spinner("กำลังบันทึก..."):
                    success = gs_handler.save_new_portfolio_to_gsheets(data_to_save)
                if success:
                    st.success(f"เพิ่มพอร์ต '{form_name}' สำเร็จ!")
                    st.rerun()
                else:
                    st.error("บันทึกล้มเหลว")

def render_portfolio_section():
    with st.expander("💼 จัดการพอร์ต (เพิ่ม/แก้ไข/ดูพอร์ต)", expanded=False):
        
        df_portfolios_gs = gs_handler.load_portfolios_from_gsheets()
        
        tab_keys = ["overview", "add", "edit"]
        tab_captions = ["📊 ภาพรวมพอร์ตทั้งหมด", "➕ เพิ่มพอร์ตใหม่", "✏️ แก้ไข / ลบพอร์ต"]
        
        # Set default tab
        if 'active_portfolio_tab' not in st.session_state:
            st.session_state.active_portfolio_tab = tab_keys[0]

        # Create buttons that look like tabs to control state
        cols = st.columns(len(tab_keys))
        for i, col in enumerate(cols):
            if col.button(tab_captions[i], use_container_width=True, type="primary" if st.session_state.active_portfolio_tab == tab_keys[i] else "secondary"):
                st.session_state.active_portfolio_tab = tab_keys[i]
                st.rerun()

        # Render content based on active tab state
        if st.session_state.active_portfolio_tab == "overview":
            st.subheader("พอร์ตทั้งหมดของคุณ")
            if df_portfolios_gs.empty:
                st.info("ยังไม่มีข้อมูลพอร์ต")
            else:
                cols_to_display = ['PortfolioID', 'PortfolioName', 'ProgramType', 'EvaluationStep', 'Status', 'InitialBalance']
                cols_exist = [col for col in cols_to_display if col in df_portfolios_gs.columns]
                st.dataframe(df_portfolios_gs[cols_exist], use_container_width=True, hide_index=True)

        elif st.session_state.active_portfolio_tab == "add":
            st.subheader("➕ เพิ่มพอร์ตใหม่")
            if st.session_state.get('form_mode') != 'add':
                st.session_state.form_mode = 'add'
                if 'form_program_type' in st.session_state: del st.session_state['form_program_type']
                st.rerun()
            _render_portfolio_form(is_edit_mode=False, df_portfolios_gs=df_portfolios_gs)

        elif st.session_state.active_portfolio_tab == "edit":
            st.subheader("✏️ แก้ไข / ลบพอร์ต")
            if st.session_state.get('form_mode') != 'edit':
                st.session_state.form_mode = 'edit'
                if 'form_program_type' in st.session_state: del st.session_state['form_program_type']
                
            if df_portfolios_gs.empty:
                st.info("ไม่มีพอร์ตให้แก้ไข")
            else:
                portfolio_dict = dict(zip(df_portfolios_gs['PortfolioName'], df_portfolios_gs['PortfolioID']))
                # Use a unique key for the selectbox to avoid state conflicts
                selected_name = st.selectbox(
                    "เลือกพอร์ตที่ต้องการแก้ไข:",
                    options=[""] + list(portfolio_dict.keys()),
                    index=0,
                    key="edit_portfolio_selector_v2"
                )

                if selected_name:
                    selected_id = portfolio_dict[selected_name]
                    
                    if st.session_state.get('current_edit_id') != selected_id:
                        st.session_state.current_edit_id = selected_id
                        # When a new portfolio is selected for editing, reset the form's program type
                        if 'form_program_type' in st.session_state: del st.session_state['form_program_type']
                        st.rerun()

                    portfolio_data = df_portfolios_gs[df_portfolios_gs['PortfolioID'] == selected_id].iloc[0].to_dict()
                    _render_portfolio_form(is_edit_mode=True, portfolio_to_edit_data=portfolio_data)
    default_program_type = portfolio_to_edit_data.get("ProgramType", "")
    if 'form_program_type' not in st.session_state: st.session_state.form_program_type = default_program_type
    type_index = program_type_options.index(st.session_state.form_program_type) if st.session_state.form_program_type in program_type_options else 0
    st.selectbox("ประเภทพอร์ต (Program Type)*", options=program_type_options, index=type_index, key="exp_pf_type_selector_widget", on_change=on_program_type_change)
    selected_program_type = st.session_state.get('form_program_type')

    with st.form(key=f"portfolio_form_{'edit' if is_edit_mode else 'add'}", clear_on_submit=False):
        st.markdown(f"**กรอกข้อมูลพอร์ต (สำหรับประเภท: {selected_program_type or 'ยังไม่ได้เลือก'})**")
        form_c1, form_c2 = st.columns(2)
        with form_c1: form_name = st.text_input("ชื่อพอร์ต*", value=portfolio_to_edit_data.get("PortfolioName", ""))
        with form_c2: form_balance = st.number_input("บาลานซ์เริ่มต้น*", min_value=0.01, value=float(portfolio_to_edit_data.get("InitialBalance", 10000.0)), format="%.2f")
        statuses = ["Active", "Inactive", "Pending", "Passed", "Failed"]; status_default = portfolio_to_edit_data.get("Status", "Active"); status_idx = statuses.index(status_default) if status_default in statuses else 0; form_status = st.selectbox("สถานะ*", options=statuses, index=status_idx)
        
        # --- [แก้ไข] ประกาศตัวแปรทั้งหมดให้เป็น None ก่อน ---
        form_eval_step, prop_profit, prop_daily_loss, prop_total_loss, prop_leverage, prop_min_days = (None,) * 6
        comp_end_date, comp_profit, comp_goal, comp_daily_loss, comp_total_loss = (None,) * 5
        pers_profit, pers_weekly_profit, pers_max_dd, pers_end_date, pers_daily_profit, pers_daily_dd = (None,) * 6
        enable_scaling = str(portfolio_to_edit_data.get("EnableScaling", "False")).upper() == 'TRUE'
        scaling_freq, su_wr, sd_loss, min_risk, su_gain, sd_wr, max_risk, su_inc, sd_dec, current_risk = (None,) * 10
        # ---
        
        if selected_program_type == "Prop Firm Challenge":
            eval_opts = ["", "Phase 1", "Phase 2", "Phase 3", "Verification"]; eval_default = portfolio_to_edit_data.get("EvaluationStep", ""); eval_idx = eval_opts.index(eval_default) if eval_default in eval_opts else 0; form_eval_step = st.selectbox("ขั้นตอน", options=eval_opts, index=eval_idx)
        if selected_program_type in ["Prop Firm Challenge", "Funded Account"]:
            f1, f2, f3 = st.columns(3); f4, f5 = st.columns(2)
            with f1: prop_profit = st.number_input("เป้าหมายกำไร %*", value=float(portfolio_to_edit_data.get("ProfitTargetPercent", 8.0)), format="%.1f")
            with f2: prop_daily_loss = st.number_input("จำกัดขาดทุนต่อวัน %*", value=float(portfolio_to_edit_data.get("DailyLossLimitPercent", 5.0)), format="%.1f")
            with f3: prop_total_loss = st.number_input("จำกัดขาดทุนรวม %*", value=float(portfolio_to_edit_data.get("TotalStopoutPercent", 10.0)), format="%.1f")
            with f4: prop_leverage = st.number_input("Leverage", value=float(portfolio_to_edit_data.get("Leverage", 100.0)), format="%.0f")
            with f5: prop_min_days = st.number_input("วันเทรดขั้นต่ำ", value=int(portfolio_to_edit_data.get("MinTradingDays", 0)), step=1)
        
        notes = st.text_area("หมายเหตุ", value=portfolio_to_edit_data.get("Notes", ""), key=f"notes_{'edit' if is_edit_mode else 'add'}")
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if not form_name or not selected_program_type or not form_status or form_balance <= 0: st.warning("กรุณากรอกข้อมูลที่จำเป็น (*)"); return
            data_to_save = portfolio_logic.prepare_new_portfolio_data_for_gsheet(form_new_portfolio_name_in_form=form_name,selected_program_type_to_use_in_form=selected_program_type,form_new_initial_balance_in_form=form_balance,form_new_status_in_form=form_status,form_new_evaluation_step_val_in_form=form_eval_step,form_notes_val=notes,form_profit_target_val=prop_profit,form_daily_loss_val=prop_daily_loss,form_total_stopout_val=prop_total_loss,form_leverage_val=prop_leverage,form_min_days_val=prop_min_days,form_comp_end_date=comp_end_date,form_comp_goal_metric=comp_goal,form_profit_target_val_comp=comp_profit,form_daily_loss_val_comp=comp_daily_loss,form_total_stopout_val_comp=comp_total_loss,form_pers_overall_profit_val=pers_profit,form_pers_target_end_date=pers_end_date,form_pers_weekly_profit_val=pers_weekly_profit,form_pers_daily_profit_val=pers_daily_profit,form_pers_max_dd_overall_val=pers_max_dd,form_pers_max_dd_daily_val=pers_daily_dd,form_enable_scaling_checkbox_val=enable_scaling,form_scaling_freq_val=scaling_freq,form_su_wr_val=su_wr,form_su_gain_val=su_gain,form_su_inc_val=su_inc,form_sd_loss_val=sd_loss,form_sd_wr_val=sd_wr,form_sd_dec_val=sd_dec,form_min_risk_val=min_risk,form_max_risk_val=max_risk,form_current_risk_val=current_risk)
            if is_edit_mode:
                pid = portfolio_to_edit_data.get("PortfolioID"); data_to_save["PortfolioID"] = pid
                with st.spinner("กำลังอัปเดต..."): success = gs_handler.update_portfolio_in_gsheets(pid, data_to_save)
                if success: st.success("อัปเดตสำเร็จ!"); st.rerun()
                else: st.error("อัปเดตล้มเหลว")
            else:
                if not df_portfolios_gs.empty and form_name in df_portfolios_gs['PortfolioName'].astype(str).values: st.error(f"ชื่อพอร์ต '{form_name}' มีอยู่แล้ว"); return
                with st.spinner("กำลังบันทึก..."): success = gs_handler.save_new_portfolio_to_gsheets(data_to_save)
                if success: st.success(f"เพิ่มพอร์ต '{form_name}' สำเร็จ!"); st.rerun()
                else: st.error("บันทึกล้มเหลว")

    with st.expander("💼 จัดการพอร์ต (เพิ่ม/แก้ไข/ดูพอร์ต)", expanded=False):
        
        df_portfolios_gs = gs_handler.load_portfolios_from_gsheets()
        
        tab_keys = ["overview", "add", "edit"]
        tab_captions = ["📊 ภาพรวมพอร์ตทั้งหมด", "➕ เพิ่มพอร์ตใหม่", "✏️ แก้ไข / ลบพอร์ต"]
        
        # Set default tab
        if 'active_portfolio_tab' not in st.session_state:
            st.session_state.active_portfolio_tab = tab_keys[0]

        # Create buttons that look like tabs to control state
        cols = st.columns(len(tab_keys))
        for i, col in enumerate(cols):
            if col.button(tab_captions[i], use_container_width=True, type="primary" if st.session_state.active_portfolio_tab == tab_keys[i] else "secondary"):
                st.session_state.active_portfolio_tab = tab_keys[i]
                st.rerun()

        # Render content based on active tab state
        if st.session_state.active_portfolio_tab == "overview":
            st.subheader("พอร์ตทั้งหมดของคุณ")
            if df_portfolios_gs.empty:
                st.info("ยังไม่มีข้อมูลพอร์ต")
            else:
                cols_to_display = ['PortfolioID', 'PortfolioName', 'ProgramType', 'EvaluationStep', 'Status', 'InitialBalance']
                cols_exist = [col for col in cols_to_display if col in df_portfolios_gs.columns]
                st.dataframe(df_portfolios_gs[cols_exist], use_container_width=True, hide_index=True)

        elif st.session_state.active_portfolio_tab == "add":
            st.subheader("➕ เพิ่มพอร์ตใหม่")
            if st.session_state.get('form_mode') != 'add':
                st.session_state.form_mode = 'add'
                if 'form_program_type' in st.session_state: del st.session_state['form_program_type']
                st.rerun()
            _render_portfolio_form(is_edit_mode=False, df_portfolios_gs=df_portfolios_gs)

        elif st.session_state.active_portfolio_tab == "edit":
            st.subheader("✏️ แก้ไข / ลบพอร์ต")
            if st.session_state.get('form_mode') != 'edit':
                st.session_state.form_mode = 'edit'
                if 'form_program_type' in st.session_state: del st.session_state['form_program_type']
                
            if df_portfolios_gs.empty:
                st.info("ไม่มีพอร์ตให้แก้ไข")
            else:
                portfolio_dict = dict(zip(df_portfolios_gs['PortfolioName'], df_portfolios_gs['PortfolioID']))
                # Use a unique key for the selectbox to avoid state conflicts
                selected_name = st.selectbox(
                    "เลือกพอร์ตที่ต้องการแก้ไข:",
                    options=[""] + list(portfolio_dict.keys()),
                    index=0,
                    key="edit_portfolio_selector_v2"
                )

                if selected_name:
                    selected_id = portfolio_dict[selected_name]
                    
                    if st.session_state.get('current_edit_id') != selected_id:
                        st.session_state.current_edit_id = selected_id
                        # When a new portfolio is selected for editing, reset the form's program type
                        if 'form_program_type' in st.session_state: del st.session_state['form_program_type']
                        st.rerun()

                    portfolio_data = df_portfolios_gs[df_portfolios_gs['PortfolioID'] == selected_id].iloc[0].to_dict()
                    _render_portfolio_form(is_edit_mode=True, portfolio_to_edit_data=portfolio_data)