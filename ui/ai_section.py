# ui/ai_section.py
import streamlit as st
import pandas as pd

# Import functions and settings from other modules
from config import settings
from core import supabase_handler as db_handler
from core import analytics_engine

def render_ai_section():
    """
    ฟังก์ชันสำหรับแสดงผล AI Assistant และ Dashboard
    (ฉบับสมบูรณ์ที่เพิ่มการดักจับ Error และใช้ session_state key ที่ถูกต้อง)
    """
    with st.expander("🤖 AI Assistant & Performance Dashboard", expanded=False):
        
        # --- ใช้ Key ที่ถูกต้องจาก Sidebar ---
        active_portfolio_id_for_ai = st.session_state.get('active_portfolio_id', None)
        portfolio_details = st.session_state.get('current_portfolio_details') or {}
        active_portfolio_name_for_ai = portfolio_details.get('PortfolioName', "ทั่วไป (ไม่ได้เลือกพอร์ต)")
        balance_for_ai_simulation = st.session_state.get('current_account_balance', settings.DEFAULT_ACCOUNT_BALANCE)

        if active_portfolio_id_for_ai:
            st.info(f"AI Assistant กำลังวิเคราะห์ข้อมูลสำหรับพอร์ต: **'{active_portfolio_name_for_ai}'**")
        else:
            st.info(f"AI Assistant กำลังวิเคราะห์ข้อมูลจากแผนเทรดและผลการเทรดจริงทั้งหมด (กรุณาเลือก Active Portfolio)")

        # --- Tab interface ---
        tab1, tab2, tab3 = st.tabs([
            "📊 วิเคราะห์จากแผน (Planned)", 
            "📈 วิเคราะห์จากผลเทรดจริง (Actual)",
            "🧠 AI วิเคราะห์เชิงลึก (Combined)"
        ])

        # --- Planned Analysis Tab with Error Handling ---
        with tab1:
            st.markdown("### 📝 AI Intelligence Report (จากแผนเทรด)")
            try:
                df_ai_planned_logs = db_handler.load_all_planned_trade_logs()
                
                planned_analysis_results = analytics_engine.analyze_planned_trades_for_ai(
                    df_all_planned_logs=db_handler.load_all_planned_trade_logs(),
                    active_portfolio_id=active_portfolio_id_for_ai,
                    active_portfolio_name=active_portfolio_name_for_ai,
                    balance_for_simulation=balance_for_ai_simulation
                )

                if planned_analysis_results.get("error_message") and not planned_analysis_results.get("data_found"):
                    st.info(planned_analysis_results["error_message"])
                elif planned_analysis_results.get("data_found"):
                    st.write(f"- **จำนวนแผนเทรดที่วิเคราะห์:** {planned_analysis_results['total_trades']:,}")
                    st.write(f"- **Winrate (ตามแผน):** {planned_analysis_results['win_rate']:.2f}%")
                    st.write(f"- **กำไร/ขาดทุนสุทธิ (ตามแผน):** {planned_analysis_results['gross_pnl']:,.2f} USD")
                    st.write(f"- **RR เฉลี่ย (ตามแผน, >0):** {planned_analysis_results['avg_rr']}")
                    st.write(f"- **Max Drawdown (จำลองจากแผน):** {planned_analysis_results['max_drawdown_simulated']:,.2f} USD")
                    
                    st.markdown("#### 🤖 AI Insight (จากแผนเทรด)")
                    insights_planned = planned_analysis_results.get("insights", [])
                    if not insights_planned and planned_analysis_results['total_trades'] > 0:
                         insights_planned = ["ข้อมูลแผนเทรดที่วิเคราะห์ยังไม่มีจุดที่น่ากังวลเป็นพิเศษ หรือมีข้อมูลไม่เพียงพอสำหรับ Insight เชิงลึก"]

                    for msg in insights_planned:
                        st.info(msg)
                else:
                    st.info("ไม่พบข้อมูลแผนเทรดสำหรับ AI Assistant")
            except Exception as e:
                st.error("❌ เกิดข้อผิดพลาดระหว่างการวิเคราะห์ 'แผนการเทรด'")
                st.exception(e)

        # --- Actual Analysis Tab with Error Handling ---
        with tab2:
            st.subheader("Dashboard วิเคราะห์ผลการเทรดจริง")
            try:
                df_ai_actual_trades_all = db_handler.load_actual_trades()
                df_all_statement_summaries = db_handler.load_statement_summaries()
                dashboard_results = analytics_engine.get_dashboard_analytics_for_actual(
                    df_all_actual_trades=df_ai_actual_trades_all,
                    df_all_statement_summaries=df_all_statement_summaries,
                    active_portfolio_id=active_portfolio_id_for_ai
                )
                if not dashboard_results.get("data_found"):
                    st.warning(dashboard_results.get("error_message", "ไม่พบข้อมูลการเทรดจริงในพอร์ตที่เลือก (โปรดอัปโหลด Statement ก่อน)"))
                else:
                    metrics = dashboard_results.get("metrics", {})
                    st.markdown("#### ภาพรวมประสิทธิภาพ")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Net Profit", f"{metrics.get('Total Net Profit', 0):,.2f} USD")
                    col2.metric("Win Rate", f"{metrics.get('Win Rate (%)', 0):.2f}%")
                    col3.metric("Profit Factor", f"{metrics.get('Profit Factor', 0):.2f}")
                    col4.metric("Total Deals", f"{metrics.get('Total Deals', 0):,}")
                    st.markdown("#### Balance Curve")
                    balance_curve_data = dashboard_results.get("balance_curve_data")
                    if balance_curve_data is not None and not balance_curve_data.empty:
                        st.line_chart(balance_curve_data)
                    else:
                        st.info("ไม่พบข้อมูลสำหรับสร้างกราฟ Balance Curve")
            except Exception as e:
                st.error("❌ เกิดข้อผิดพลาดระหว่างการวิเคราะห์ 'ผลการเทรดจริง'")
                st.exception(e)

        # --- Combined Analysis Tab with Error Handling ---
        with tab3:
            st.subheader("วิเคราะห์เปรียบเทียบแผนและผลเทรดจริง")
            st.write("คลิกปุ่มด้านล่างเพื่อให้ AI เริ่มทำการวิเคราะห์ข้อมูลเชิงลึก")
            if st.button("🚀 เริ่มการวิเคราะห์เชิงลึก!"):
                try:
                    df_planned_logs = db_handler.load_all_planned_trade_logs()
                    df_actual_trades = db_handler.load_actual_trades()

                    if df_ai_planned_logs.empty or df_ai_actual_trades.empty:
                        st.warning("ไม่พบข้อมูล 'แผนการเทรด' หรือ 'ผลการเทรดจริง'")
                    else:
                        with st.spinner("AI กำลังประมวลผล..."):
                            combined_results = analytics_engine.analyze_combined_trades_for_ai(
                                df_planned=df_ai_planned_logs,
                                df_actual=df_ai_actual_trades,
                                active_portfolio_id=active_portfolio_id_for_ai,
                                active_portfolio_name=active_portfolio_name_for_ai
                            )
                            st.markdown("#### 💡 AI Insights")
                            if combined_results.get("error_message"):
                                st.error(combined_results["error_message"])
                            elif not combined_results.get("insights"):
                                st.info("ไม่พบ Insight ที่น่าสนใจจากข้อมูลชุดนี้")
                            else:
                                for insight in combined_results["insights"]:
                                    st.info(insight)
                except Exception as e:
                    st.error("❌ เกิดข้อผิดพลาดระหว่างการวิเคราะห์เชิงลึก")
                    st.exception(e)

def render_ai_insights(insights: dict):
    """
    แสดงผลข้อมูล AI-Powered Insights ที่คำนวณมาจาก analytics_engine
    """
    if not insights:
        st.info("มีข้อมูลไม่เพียงพอสำหรับสร้าง Insights")
        return

    col1, col2, col3 = st.columns(3)

    # ส่วนที่ 1: Performance by Day
    with col1:
        st.markdown("##### 📅 By Day")
        best_day, best_day_pnl = insights.get('best_day', ('N/A', 0))
        worst_day, worst_day_pnl = insights.get('worst_day', ('N/A', 0))
        
        # ตรวจสอบว่ามีข้อมูลหรือไม่ก่อนแสดงผล
        if best_day != 'N/A':
            st.metric(label=f"Best Day ({best_day})", value=f"${best_day_pnl:,.2f}")
        if worst_day != 'N/A':
            st.metric(label=f"Worst Day ({worst_day})", value=f"${worst_day_pnl:,.2f}", delta_color="inverse")

    # ส่วนที่ 2: Performance by Pair
    with col2:
        st.markdown("##### 💹 By Pair")
        best_pair, best_pair_pnl = insights.get('best_pair', ('N/A', 0))
        worst_pair, worst_pair_pnl = insights.get('worst_pair', ('N/A', 0))
        
        if best_pair != 'N/A':
            st.metric(label=f"Best Pair ({best_pair})", value=f"${best_pair_pnl:,.2f}")
        if worst_pair != 'N/A':
            st.metric(label=f"Worst Pair ({worst_pair})", value=f"${worst_pair_pnl:,.2f}", delta_color="inverse")

    # ส่วนที่ 3: Performance by Direction
    with col3:
        st.markdown("##### 📈 By Direction")
        long_pnl, short_pnl = insights.get('long_vs_short_pnl', (0, 0))
        st.metric(label="Long PnL", value=f"${long_pnl:,.2f}")
        st.metric(label="Short PnL", value=f"${short_pnl:,.2f}")
