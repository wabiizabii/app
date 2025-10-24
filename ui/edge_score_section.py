# ui/edge_score_section.py

import streamlit as st
import numpy as np

def render_edge_score_section(analytics_engine, db_handler):
    """
    แสดงผล Dashboard สำหรับติดตาม Metrics ที่เกี่ยวข้องกับ Edge Score
    """
    with st.expander("🚀 My Edge Score Dashboard", expanded=True):
        
        active_id = st.session_state.get('active_portfolio_id_gs')
        if not active_id:
            st.info("กรุณาเลือก Portfolio ที่ Sidebar เพื่อดูข้อมูล Edge Score")
            return
            
        # โหลดข้อมูลการเทรด
        df_actual_trades = db_handler.load_actual_trades()
        
        # คำนวณ Metrics
        metrics = analytics_engine.calculate_edge_score_metrics(df_actual_trades, active_id)

        if not metrics:
            st.info("ยังไม่มีข้อมูลการเทรดเพียงพอที่จะคำนวณ Edge Score Metrics")
            return

        st.markdown(f"**ข้อมูลคำนวณจากเทรดทั้งหมด `{metrics['total_trades']}` ครั้ง**")
        st.divider()

        # --- Pillar 1: SKILL ---
        st.subheader("🎓 Skill (ทักษะ)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
        col2.metric("Win Rate", f"{metrics['win_rate']:.2f}%")
        col3.metric("Expectancy", f"${metrics['expectancy']:,.2f}")
        st.divider()

        # --- Pillar 2: RISK MANAGEMENT ---
        st.subheader("🛡️ Risk (การบริหารความเสี่ยง)")
        col4, col5, col6 = st.columns(3)
        col4.metric("Max Drawdown", f"${metrics['max_drawdown']:,.2f}")
        col5.metric("Average Loss", f"${metrics['average_loss']:,.2f}")
        col6.metric("Average RR Ratio", f"1 : {metrics['average_rr_ratio']:.2f}" if metrics['average_rr_ratio'] != np.inf else "N/A")
        st.divider()

        # --- Pillar 3: CONSISTENCY ---
        st.subheader("🔁 Consistency (ความสม่ำเสมอ)")
        col7, col8 = st.columns(2)
        col7.metric("Best Day % of Total Profit", f"{metrics['profit_concentration']:.1f}%")
        col8.metric("Profit per Day (Std. Dev)", f"${metrics['daily_returns_std']:,.2f}")
        st.divider()

        # --- Pillar 4: EXPERIENCE ---
        st.subheader("⏳ Experience (ประสบการณ์)")
        col9, col10 = st.columns(2)
        col9.metric("Total Trades", f"{metrics['total_trades']}")
        col10.metric("Active Trading Days", f"{metrics['active_trading_days']}")