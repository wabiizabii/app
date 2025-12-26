# ui/consistency_section.py (เวอร์ชันเต็มสมบูรณ์: ดึง Profit Target จาก Sidebar)

import streamlit as st
import math

# ==============================================================================
#                      ฟังก์ชันย่อยสำหรับแต่ละโหมด
# ==============================================================================

def render_analysis_section(initial_balance, profit_target_pct, total_pl, consistency_percent, rule_threshold):
    """แสดงผลส่วนวิเคราะห์สถานะปัจจุบัน (เมื่อมีกำไร)"""
    
    challenge_profit_target_usd = initial_balance * (profit_target_pct / 100)
    
    try:
        best_day = 0.0
        if consistency_percent > 0 and total_pl > 0:
            best_day = (consistency_percent / 100) * total_pl
        elif total_pl > 0 and consistency_percent == 0:
            best_day = total_pl
        
        if best_day <= 0:
            st.warning("ข้อมูล Consistency Percent อาจไม่ถูกต้อง หรือยังไม่มีกำไรที่ชัดเจน")
            return

        consistency_target_usd = best_day / (rule_threshold / 100) if rule_threshold > 0 else float('inf')
        final_target = max(challenge_profit_target_usd, consistency_target_usd)
        profit_needed = final_target - total_pl
        if profit_needed < 0: profit_needed = 0
        
        st.success(f"**สถานะปัจจุบัน:** มีกำไรสุทธิ **+${total_pl:,.2f}**")
        st.metric("🏆 เป้าหมายสุดท้ายที่ต้องไปให้ถึง", f"${final_target:,.2f}")
        
        speed_limit = best_day
        st.warning(f"**กฎเหล็ก (Speed Limit):** ห้ามทำกำไรในวันใดวันหนึ่งเกิน **${speed_limit:,.2f}** โดยเด็ดขาด!")
        
        st.divider()
        st.info("#### 📈 Interactive Scenario Simulator (จากสถานะปัจจุบัน)")
        
        if profit_needed > 0:
            min_days_possible = math.ceil(profit_needed / speed_limit) if speed_limit > 0 else 999
            
            sim_col1, sim_col2 = st.columns(2)
            with sim_col1:
                days_input = st.number_input("จำนวนวันที่ต้องการ (Days to Target)", 1, value=st.session_state.get('sim_days_input', min_days_possible), step=1, key='sim_days_input_analysis')
            with sim_col2:
                initial_daily_target = profit_needed / days_input if days_input > 0 else 0
                daily_target_input = st.number_input("เป้าหมายกำไรต่อวัน ($)", 0.01, value=initial_daily_target, step=50.0, format="%.2f", help="ปรับค่านี้ แล้ว 'จำนวนวัน' จะเปลี่ยนตาม", key='sim_daily_target_analysis')

            if daily_target_input != initial_daily_target:
                new_days_calculated = math.ceil(profit_needed / daily_target_input) if daily_target_input > 0 else 0
                if new_days_calculated != days_input:
                    st.session_state.sim_days_input = new_days_calculated
                    st.rerun()
            
            st.write(f"**แผนของคุณคือ:** ทำกำไร **${daily_target_input:,.2f}** ต่อวัน เป็นเวลา **{days_input} วัน**")
            
            if daily_target_input > speed_limit:
                simulated_new_best_day = daily_target_input
                simulated_new_total_pl = total_pl + daily_target_input
                simulated_consistency_target_usd = simulated_new_best_day / (rule_threshold / 100) if rule_threshold > 0 else float('inf')
                simulated_final_target = max(challenge_profit_target_usd, simulated_consistency_target_usd)
                simulated_profit_needed = simulated_final_target - simulated_new_total_pl
                if simulated_profit_needed < 0: simulated_profit_needed = 0
                
                with st.container(border=True):
                    st.error(f"⚠️ **แจ้งเตือน: แผนนี้จะทำลายสถิติ Speed Limit!**")
                    err_col1, err_col2 = st.columns(2)
                    with err_col1:
                        st.metric(label="'เป้าหมายสุดท้าย' ใหม่ของคุณจะกลายเป็น", value=f"${simulated_final_target:,.2f}")
                    with err_col2:
                        st.metric(label="และคุณจะยังต้องทำกำไรเพิ่มอีก", value=f"${simulated_profit_needed:,.2f}")
            
            progress_percent = int((total_pl / final_target) * 100) if final_target > 0 else 0
            st.progress(progress_percent, text=f"ความคืบหน้าปัจจุบัน: ${total_pl:,.2f} / ${final_target:,.2f}")

        else:
            st.balloons(); st.success("🎉 ยินดีด้วย! คุณบรรลุเป้าหมายสุดท้ายแล้ว!")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการคำนวณ [Analysis]: {e}")


def render_planning_section(initial_balance, profit_target_pct, rule_threshold, current_pl):
    """แสดงผลส่วนวางแผนล่วงหน้า พร้อม UI ที่ปรับปรุงใหม่"""
    
    challenge_profit_target_usd = initial_balance * (profit_target_pct / 100)

    if current_pl < 0:
        st.error(f"**สถานะปัจจุบัน:** กำลังขาดทุนสุทธิอยู่ **${current_pl:,.2f}**"); return

    st.success("**สถานะปัจจุบัน:** ยังไม่มีกำไร (P/L = $0.00)")
    st.info(f"**เป้าหมายกำไรของ Challenge นี้คือ:** **${challenge_profit_target_usd:,.2f}**")
    st.divider()
    
    st.subheader("วางแผนการเทรดของคุณ (Trading Plan)")

    plan_col1, _ = st.columns([1, 3])
    with plan_col1:
        days_to_target = st.number_input(
            "จำนวนวันที่คาดว่าจะใช้ (Days to Target)", 
            min_value=1, 
            value=5,
            step=1,
            key=f"plan_days_{initial_balance}_{profit_target_pct}"
        )

    avg_profit_needed_base = challenge_profit_target_usd / days_to_target if days_to_target > 0 else 0
    consistency_target_usd = avg_profit_needed_base / (rule_threshold / 100) if rule_threshold > 0 else float('inf')
    final_target = max(challenge_profit_target_usd, consistency_target_usd)
    final_avg_profit_per_day = final_target / days_to_target if days_to_target > 0 else 0
    safe_speed_limit = final_target * (rule_threshold / 100) if rule_threshold > 0 else 0
    
    st.markdown("---")
    
    st.markdown("##### **ผลการวิเคราะห์แผน:**")
    
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.metric(label="เป้าหมายสุดท้ายที่แท้จริงของคุณ", value=f"${final_target:,.2f}")
    with res_col2:
        st.metric(label=f"คุณต้องทำกำไรเฉลี่ยวันละ", value=f"${final_avg_profit_per_day:,.2f}")

    st.warning(f"**กฎเหล็กของคุณ (Your Speed Limit):** เพื่อให้แผนนี้สำเร็จ ห้ามทำกำไรเกิน **${safe_speed_limit:,.2f}** ต่อวัน")

# ==============================================================================
#                          ฟังก์ชันหลักที่เรียกใช้งาน
# ==============================================================================

def render_consistency_section():
    with st.expander("📅 Profit Consistency Planner & Analyzer", expanded=True):
        
        # --- START: โค้ดส่วนดึงข้อมูลที่เรียบง่ายที่สุด ---
        
        # 1. ดึงค่าจาก session_state ที่ Sidebar ตั้งไว้ให้
        initial_balance_from_sidebar = st.session_state.get('active_initial_balance', 10000.0)
        profit_target_from_sidebar = st.session_state.get('active_profit_target_pct', 10.0)

        # 2. นำค่าที่ดึงมาไปใส่ใน Widget ต่างๆ (ส่วนนี้จะอยู่ใน Sidebar)
        #    ดังนั้น ใน Section นี้ เราแค่ต้อง "อ่าน" ค่าสุดท้ายที่ถูกบันทึกไว้
        
        initial_balance = st.session_state.get('consistency_initial_balance', initial_balance_from_sidebar)
        profit_target_pct = st.session_state.get('consistency_profit_target_pct', profit_target_from_sidebar)
        total_pl = st.session_state.get('consistency_total_pl', 0.0)
        consistency_percent = st.session_state.get('consistency_percent', 0.0)
        rule_threshold = st.session_state.get('consistency_rule_threshold', 19.99)
        
        # --- END: สิ้นสุดโค้ดส่วนดึงข้อมูล ---
        
        # --- Logic การสลับโหมด (ไม่มีการเปลี่ยนแปลง) ---
        if total_pl > 0:
            render_analysis_section(initial_balance, profit_target_pct, total_pl, consistency_percent, rule_threshold)
        else:
            render_planning_section(initial_balance, profit_target_pct, rule_threshold, total_pl)