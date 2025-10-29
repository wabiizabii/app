# ui/consistency_section.py (เวอร์ชันอัปเกรด: Interactive Simulator)

import streamlit as st
import math

def render_consistency_section():
    """
    แสดงผล Section สำหรับเครื่องมือวิเคราะห์ Profit Consistency
    *** อัปเกรด: Simulator แบบ Interactive คำนวณสองทิศทาง ***
    """
    with st.expander("🎯 Profit Consistency Analysis & Plan", expanded=True):
        
        # --- 1. ดึงข้อมูลทั้งหมดจาก Sidebar ---
        initial_balance = st.session_state.get('consistency_initial_balance', 1.0)
        profit_target_pct = st.session_state.get('consistency_profit_target_pct', 10.0)
        total_pl = st.session_state.get('consistency_total_pl', 0.0)
        consistency_percent = st.session_state.get('consistency_percent', 0.0)
        rule_threshold = st.session_state.get('consistency_rule_threshold', 30)

        # --- 2. คำนวณค่าพื้นฐาน ---
        challenge_profit_target_usd = initial_balance * (profit_target_pct / 100)

        # --- 3. วิเคราะห์สถานะและคำนวณเป้าหมาย ---
        st.success("#### สถานะและเป้าหมายของคุณ:")
        
        # สถานะปัจจุบัน: ขาดทุน
        if total_pl < 0:
            # ... (ส่วนนี้เหมือนเดิม) ...
            profit_to_breakeven = abs(total_pl)
            profit_to_final_target = profit_to_breakeven + challenge_profit_target_usd
            st.error(f"**สถานะปัจจุบัน:** กำลังขาดทุนสุทธิอยู่ **${total_pl:,.2f}**")
            
            col1, col2 = st.columns(2)
            col1.metric("💰 ต้องทำกำไรเพื่อคืนทุน (Breakeven)", f"${profit_to_breakeven:,.2f}")
            col2.metric(f"🏁 ต้องทำกำไรเพื่อถึงเป้าหมาย {profit_target_pct}%", f"${profit_to_final_target:,.2f}")

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
                    # ... (ส่วนแสดงผลเป้าหมายเหมือนเดิม) ...
                    col1, col2, col3 = st.columns(3)
                    col1.metric("🏁 เป้าหมายกำไร Challenge", f"${challenge_profit_target_usd:,.2f}")
                    col2.metric("🎯 เป้าหมายกำไร Consistency", f"${consistency_target_usd:,.2f}")
                    col3.metric("🏆 เป้าหมายสุดท้ายที่ต้องไปให้ถึง", f"${final_target:,.2f}", delta="สูงกว่าคือเป้าหมายจริง")

                    speed_limit = best_day
                    st.warning(f"**กฎเหล็ก (Speed Limit):** ห้ามทำกำไรสุทธิในวันใดวันหนึ่งเกิน **${speed_limit:,.2f}** โดยเด็ดขาด!")

                    # --- START: อัปเกรดส่วน Simulator ทั้งหมด ---
                    st.divider()
                    st.info("#### 📈 Interactive Scenario Simulator")

                    if profit_needed > 0:
                        # คำนวณค่าเริ่มต้นที่เหมาะสม
                        min_days_possible = math.ceil(profit_needed / speed_limit) if speed_limit > 0 else 999
                        
                        # --- Input แบบสองทิศทาง ---
                        sim_col1, sim_col2 = st.columns(2)
                        
                        with sim_col1:
                            # Input: จำนวนวัน
                            days_input = st.number_input(
                                label="จำนวนวันที่ต้องการ (Days to Target)",
                                min_value=min_days_possible,
                                value=st.session_state.get('sim_days_input', min_days_possible),
                                step=1,
                                key='sim_days_input',
                                help=f"จำนวนวันที่น้อยที่สุดที่เป็นไปได้คือ {min_days_possible} วัน (ตาม Speed Limit ปัจจุบัน)"
                            )

                        with sim_col2:
                            # Input: เป้าหมายกำไรต่อวัน (คำนวณค่าเริ่มต้นจากจำนวนวัน)
                            if days_input > 0:
                                initial_daily_target = profit_needed / days_input
                            else:
                                initial_daily_target = 0
                            
                            daily_target_input = st.number_input(
                                label="เป้าหมายกำไรต่อวัน ($)",
                                min_value=0.01,
                                max_value=speed_limit,
                                value=initial_daily_target,
                                step=10.0,
                                format="%.2f",
                                help="ปรับค่านี้ แล้ว 'จำนวนวัน' จะเปลี่ยนตาม"
                            )

                        # --- Logic การคำนวณสองทิศทาง ---
                        # คำนวณจำนวนวันใหม่ ถ้ามีการเปลี่ยนแปลงเป้าหมายรายวัน
                        if daily_target_input != initial_daily_target:
                            new_days_calculated = math.ceil(profit_needed / daily_target_input) if daily_target_input > 0 else 0
                            if new_days_calculated != days_input:
                                st.session_state.sim_days_input = new_days_calculated
                                st.rerun() # รีเฟรชหน้าจอเพื่อแสดงผลค่าใหม่
                        
                        # --- แสดงผลการจำลอง ---
                        st.write(f"**แผนของคุณคือ:** ทำกำไร **${daily_target_input:,.2f}** ต่อวัน เป็นเวลา **{days_input} วัน**")

                        # ตรวจสอบและแสดงคำเตือน (เผื่อกรณีที่ User พยายามใส่ค่าที่ผิดพลาด)
                        if daily_target_input > speed_limit:
                            st.error(f"⚠️ **เป้าหมายกำไรต่อวัน (${daily_target_input:,.2f}) สูงกว่า Speed Limit (${speed_limit:,.2f})!** แผนนี้มีความเสี่ยงสูงที่จะสอบตก")
                        
                        if days_input < min_days_possible:
                            st.error(f"⚠️ **จำนวนวัน ({days_input}) น้อยเกินไป!** คุณต้องใช้เวลาอย่างน้อย **{min_days_possible} วัน** จึงจะทำได้โดยไม่ผิดกฎ")

                        progress_percent = int((total_pl / final_target) * 100) if final_target > 0 else 0
                        st.progress(progress_percent, text=f"ความคืบหน้าปัจจุบัน: ${total_pl:,.2f} / ${final_target:,.2f}")

                    else:
                        st.balloons()
                        st.success("🎉 ยินดีด้วย! คุณบรรลุเป้าหมายสุดท้ายแล้ว!")
                    # --- END: อัปเกรดส่วน Simulator ---

                else:
                    st.info("กรุณากรอกข้อมูลในเมนูด้านข้างเพื่อเริ่มการวิเคราะห์")
            
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")