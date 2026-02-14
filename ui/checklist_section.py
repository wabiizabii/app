# ui/checklist_section.py

import streamlit as st
import pandas as pd
from supabase import Client
from datetime import datetime

# ==============================================================================
#                      COMPONENT: CALCULATOR (เครื่องมือคำนวณ)
# ==============================================================================
def render_calculator():
    """เครื่องคิดเลขพื้นฐาน"""
    if 'calc_input' not in st.session_state: st.session_state.calc_input = ""

    def handle_click(value):
        if value == "C": st.session_state.calc_input = ""
        elif value == "DEL": st.session_state.calc_input = st.session_state.calc_input[:-1]
        elif value == "=":
            try:
                st.session_state.calc_input = str(eval(st.session_state.calc_input.replace("×", "*").replace("÷", "/")))
            except: st.session_state.calc_input = "Error"
        else: st.session_state.calc_input += value

    st.text_input("Display", value=st.session_state.calc_input, key="calc_display", disabled=True, label_visibility="collapsed")
    buttons = [['7', '8', '9', '÷'], ['4', '5', '6', '×'], ['1', '2', '3', '-'], ['.', '0', '=', '+']]
    for row in buttons:
        cols = st.columns(4)
        for i, b in enumerate(row): cols[i].button(b, key=b, use_container_width=True, on_click=handle_click, args=(b,))
    c1, c2 = st.columns(2)
    c1.button("C", key="c", use_container_width=True, on_click=handle_click, args=("C",))
    c2.button("DEL", key="d", use_container_width=True, on_click=handle_click, args=("DEL",))

# ==============================================================================
#                      MAIN LOGIC: SITUATION HANDLER
# ==============================================================================

def render_checklist_section(supabase: Client):
    with st.expander("🛡️ Trade Management Assistant (ผู้ช่วยคุมวินัย)", expanded=True):
        
        col_main, col_tools = st.columns([2, 1])

        with col_main:
            st.markdown("### 🚦 ตอนนี้คุณอยู่ในสถานการณ์ไหน?")
            
            # 1. เลือกสถานการณ์ปัจจุบัน
            situation = st.radio(
                "เลือกสถานะปัจจุบันเพื่อรับแผนรับมือ:",
                [
                    "1. กำลังหาจังหวะเข้า (Pre-Trade)",
                    "2. เข้าออเดอร์แล้ว กราฟยึกยัก/ติดลบ (Zone A)",
                    "3. กำไรแล้ว 1:1 หรือพ้นโครงสร้างแรก (Zone B)",
                    "4. กำไรใกล้ถึงเป้า / ชนแนวต้านแข็ง (Zone C)",
                    "5. เพิ่งปิดออเดอร์ (Win/Loss/Miss)"
                ],
                label_visibility="collapsed"
            )

            st.divider()

            # 2. แสดงแผนการตามสถานการณ์ (Logic Map)
            decision_note = "" # ตัวแปรสำหรับเก็บข้อความที่จะบันทึก
            is_ready_to_log = False

            if "1. กำลังหาจังหวะเข้า" in situation:
                st.info("🟦 **Phase: Pre-Trade Checklist**")
                st.markdown("เช็คให้ชัวร์ก่อนกด ถ้าไม่ครบ **'ห้ามเข้า'**")
                c1 = st.checkbox("โครงสร้างราคาเป็นใจ (Trend/Structure)")
                c2 = st.checkbox("จุดเข้าได้เปรียบ (SL สั้น TP ไกล)")
                c3 = st.checkbox("ไม่ใช่การไล่ราคา (No FOMO)")
                
                if c1 and c2 and c3:
                    st.success("✅ Setup ผ่าน! เข้าตามแผนได้เลย")
                    decision_note = "Entry Valid: เข้าเทรดตามแผน (Structure + RR)"
                    is_ready_to_log = True
                else:
                    st.warning("⚠️ เงื่อนไขยังไม่ครบ: นั่งทับมือไว้ก่อน")

            elif "2. เข้าออเดอร์แล้ว" in situation: # Zone A
                st.warning("🟨 **Phase: Zone A (โซนวัดใจ)**")
                st.markdown("""
                **กฎเหล็ก:** ห้ามทำอะไรทั้งสิ้น!
                - ❌ ห้ามเลื่อน SL หนี
                - ❌ ห้ามรีบปิดหนีตาย
                - ✅ ให้ตลาดเฉลย (ยอมแพ้ที่ SL เท่านั้น)
                """)
                confirm = st.checkbox("ฉันจะปล่อยวาง และยอมรับความเสี่ยงที่คำนวณไว้แล้ว")
                if confirm:
                    decision_note = "Zone A: ถือครองออเดอร์ตามแผน ไม่แทรกแซง"
                    is_ready_to_log = True

            elif "3. กำไรแล้ว" in situation: # Zone B
                st.success("🟩 **Phase: Zone B (โซนปลอดภัย)**")
                st.markdown("""
                **Action Required:** ปกป้องทุนเดี๋ยวนี้!
                - ✅ เลื่อน SL มาบังทุน (Break Even) หรือ
                - ✅ แบ่งปิดกำไรบางส่วน (Partial Close)
                """)
                action = st.radio("คุณจะทำอะไร?", ["เลื่อน SL บังทุน", "แบ่งปิดไม้", "ยังไม่ทำอะไร (เสี่ยงต่อ)"])
                
                if action != "ยังไม่ทำอะไร (เสี่ยงต่อ)":
                    decision_note = f"Zone B Action: {action} เพื่อปกป้องทุน"
                    is_ready_to_log = True
                else:
                    st.error("ระวัง! กำไรอาจกลายเป็นขาดทุนได้")

            elif "4. กำไรใกล้ถึงเป้า" in situation: # Zone C
                st.success("💰 **Phase: Zone C (Harvest Time)**")
                st.markdown("""
                **Action Required:** อย่าโลภ! ตลาดให้เงินต้องเก็บ
                - ✅ ล็อคกำไรเข้ากระเป๋า (ปิด 50-80%)
                - ✅ Run Trend ส่วนที่เหลือ (Trailing Stop)
                """)
                c_act = st.checkbox("ฉันได้เก็บกำไรเข้ากระเป๋าแล้ว หรือ เลื่อน SL ล็อคกำไรแล้ว")
                if c_act:
                    decision_note = "Zone C Action: ล็อคกำไร/แบ่งปิด ตามแผน ลดความโลภ"
                    is_ready_to_log = True

            elif "5. เพิ่งปิดออเดอร์" in situation: # Post-Trade
                st.error("🛑 **Phase: Cool Down (พักก่อน)**")
                st.markdown("""
                - ถ้า **กำไร**: อย่าห้าว เดี๋ยวคืนตลาด -> พัก 15 นาที
                - ถ้า **ขาดทุน**: อย่าเอาคืน (Revenge) -> หยุดเทรด 1 ชม.
                - ถ้า **ขายหมู**: ห้ามไล่ราคา (No Chasing) -> ปิดกราฟ
                """)
                st.markdown("---")
                state = st.selectbox("สถานะจิตใจตอนนี้?", ["ปกติ (Neutral)", "เสียดาย (FOMO)", "โกรธ/อยากเอาคืน (Angry)", "มั่นใจเกินไป (Overconfidence)"])
                
                if state == "ปกติ (Neutral)":
                    st.success("เยี่ยม! จิตใจคุณพร้อมสำหรับการวิเคราะห์รอบถัดไป")
                    decision_note = "Post-Trade: จิตใจปกติ จบงานตามวินัย"
                    is_ready_to_log = True
                else:
                    st.warning(f"⚠️ คุณกำลัง {state} -> **หยุดเทรดเดี๋ยวนี้**")
                    decision_note = f"Post-Trade: หยุดเทรดชั่วคราวเนื่องจาก {state}"
                    is_ready_to_log = True

            # 3. ส่วนบันทึก (Logging) - ใช้ Supabase เดิม
            st.markdown("---")
            with st.form("action_logger"):
                pair = st.text_input("คู่เงิน (Pair)", placeholder="e.g. XAUUSD")
                # เอา decision_note มาใส่ใน notes อัตโนมัติ เพื่อบันทึกสิ่งที่ตัดสินใจทำ
                user_note = st.text_area("บันทึกเพิ่มเติม", value=decision_note, help="แผนหรือการตัดสินใจที่เลือกไว้จะถูกบันทึกที่นี่")
                img = st.text_input("รูปภาพ (Optional)")
                
                # ปุ่มบันทึก
                submitted = st.form_submit_button("💾 ยืนยันการตัดสินใจ (Record Action)", disabled=not is_ready_to_log, type="primary")
                
                if submitted and is_ready_to_log:
                    try:
                        active_pid = st.session_state.get('active_portfolio_id_gs')
                        if active_pid:
                            # ใช้โครงสร้างเดิมของ Supabase (pair, notes, image_url)
                            supabase.table("trades").insert({
                                "portfolio_id": active_pid,
                                "pair": pair if pair else "N/A",
                                "notes": user_note, # บันทึกการตัดสินใจลงช่อง notes
                                "image_url": img,
                                "created_at": datetime.now().isoformat()
                            }).execute()
                            st.success("บันทึกการตัดสินใจเรียบร้อย! ทำตามแผนต่อไป")
                        else:
                            st.error("กรุณาเลือก Portfolio ก่อน")
                    except Exception as e:
                        st.error(f"บันทึกไม่สำเร็จ: {e}")

        # --- RIGHT COLUMN: TOOLS ---
        with col_tools:
            st.caption("🧮 Calculator")
            render_calculator()
            st.divider()
            st.caption("📜 History (Last 5 Actions)")
            
            # Show simple history
            try:
                pid = st.session_state.get('active_portfolio_id_gs')
                if pid:
                    res = supabase.table("trades").select("pair, notes, created_at").eq("portfolio_id", pid).order("created_at", desc=True).limit(5).execute()
                    if res.data:
                        for item in res.data:
                            t = pd.to_datetime(item['created_at']).strftime('%H:%M')
                            st.text(f"[{t}] {item.get('pair','-')}")
                            st.caption(f"{item.get('notes')[:40]}...") # Show short note
                            st.divider()
            except:
                st.caption("No history.")