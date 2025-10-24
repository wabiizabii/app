# ui/consistency_section.py (เวอร์ชันสมบูรณ์: จัดการสถานะขาดทุนได้)

import streamlit as st
import math

def render_consistency_section():
    """
    แสดงผล Section สำหรับเครื่องมือวิเคราะห์ Profit Consistency
    *** อัปเกรด: สามารถจัดการสถานะขาดทุนและวางแผนได้ครบวงจร ***
    """
    with st.expander("🎯 Profit Consistency Analysis & Plan", expanded=True):
        
        # --- 1. ดึงข้อมูลทั้งหมดจาก Sidebar ---
        initial_balance = st.session_state.get('consistency_initial_balance', 1.0)
        profit_target_pct = st.session_state.get('consistency_profit_target_pct', 10.0)
        total_pl = st.session_state.get('consistency_total_pl', 0.0)
        consistency_percent = st.session_state.get('consistency_percent', 0.0)
        rule_threshold = st.session_state.get('consistency_rule_threshold', 30)
        daily_target = st.session_state.get('consistency_daily_target', 300.0)

        # --- 2. คำนวณค่าพื้นฐาน ---
        challenge_profit_target_usd = initial_balance * (profit_target_pct / 100)

        # --- 3. วิเคราะห์สถานะและคำนวณเป้าหมาย ---
        st.success("#### สถานะและเป้าหมายของคุณ:")
        
        # สถานะปัจจุบัน: ขาดทุน
        if total_pl < 0:
            profit_to_breakeven = abs(total_pl)
            profit_to_final_target = profit_to_breakeven + challenge_profit_target_usd
            st.error(f"**สถานะปัจจุบัน:** กำลังขาดทุนสุทธิอยู่ **${total_pl:,.2f}**")
            
            col1, col2 = st.columns(2)
            col1.metric("💰 ต้องทำกำไรเพื่อคืนทุน (Breakeven)", f"${profit_to_breakeven:,.2f}")
            col2.metric("🏁 ต้องทำกำไรเพื่อถึงเป้าหมาย 10%", f"${profit_to_final_target:,.2f}")

            st.info("💡 **แผนระยะแรก:** โฟกัสที่การเทรดเพื่อกลับมาที่จุดคุ้มทุนก่อน เมื่อมีกำไรสุทธิแล้ว ระบบจะเริ่มวิเคราะห์กฎ Consistency ให้")

        # สถานะปัจจุบัน: มีกำไร
        else:
            try:
                best_day = 0.0
                if consistency_percent > 0:
                    best_day = (consistency_percent / 100) * total_pl
                elif total_pl > 0 and consistency_percent == 0:
                    best_day = total_pl
                
                if best_day > 0:
                    consistency_target_usd = best_day / (rule_threshold / 100)
                    final_target = max(challenge_profit_target_usd, consistency_target_usd)
                    profit_needed = final_target - total_pl
                    if profit_needed < 0: profit_needed = 0

                    st.success(f"**สถานะปัจจุบัน:** มีกำไรสุทธิ **+${total_pl:,.2f}**")

                    col1, col2, col3 = st.columns(3)
                    col1.metric("🏁 เป้าหมายกำไร Challenge (10%)", f"${challenge_profit_target_usd:,.2f}")
                    col2.metric("🎯 เป้าหมายกำไร Consistency", f"${consistency_target_usd:,.2f}")
                    col3.metric("🏆 เป้าหมายสุดท้ายที่ต้องไปให้ถึง", f"${final_target:,.2f}", delta="สูงกว่าคือเป้าหมายจริง")

                    st.warning(f"**กฎเหล็ก (Speed Limit):** ห้ามทำกำไรสุทธิในวันใดวันหนึ่งเกิน **${best_day:,.2f}** โดยเด็ดขาด!")

                    # --- ส่วน Simulator (จะทำงานเมื่อมีกำไรเท่านั้น) ---
                    st.divider()
                    st.info("#### 📈 จำลองสถานการณ์ (Scenario Simulator)")

                    if daily_target > best_day:
                        st.error(f"⚠️ **คำเตือน:** เป้าหมายกำไรต่อวัน (${daily_target:,.2f}) สูงกว่า Speed Limit (${best_day:,.2f}) ซึ่งเสี่ยงต่อการสอบตก!")
                    
                    if profit_needed > 0:
                        days_to_target = math.ceil(profit_needed / daily_target) if daily_target > 0 else 0
                        st.write(f"ถ้าคุณทำกำไรเฉลี่ยวันละ **${daily_target:,.2f}**:")
                        
                        sim_col1, sim_col2 = st.columns(2)
                        sim_col1.metric("คุณจะไปถึงเป้าหมายสุดท้ายใน", f"~{days_to_target} วันทำการ" if days_to_target > 0 else "N/A")
                        sim_col2.metric("ยังต้องทำกำไรอีก", f"${profit_needed:,.2f}")

                        progress_percent = int((total_pl / final_target) * 100) if final_target > 0 else 0
                        st.progress(progress_percent, text=f"ความคืบหน้า: ${total_pl:,.2f} / ${final_target:,.2f}")
                    else:
                        st.balloons()
                        st.success("🎉 ยินดีด้วย! คุณบรรลุเป้าหมายสุดท้ายแล้ว!")
                else:
                    st.info("กรุณากรอกข้อมูลในเมนูด้านข้างเพื่อเริ่มการวิเคราะห์")
            
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")