# ui/checklist_section.py (เวอร์ชันอัปเกรด: Dual Checklist System)

import streamlit as st
import pandas as pd
from supabase import Client
from datetime import datetime

# ==============================================================================
#                      ฟังก์ชันสำหรับแต่ละ Checklist
# ==============================================================================

def funnel_checklist():
    """แสดงผล Funnel Checklist และคืนค่าสถานะ"""
    st.markdown("##### **Phase 1: The Big Picture (ภาพรวม)**")
    p1_align = st.checkbox("Top-Down Alignment: ทิศทางใน H1/M15 สอดคล้องกัน", key="funnel_p1_align")
    p1_vwap = st.checkbox("Break: มีการเบรคแท่งเทียน m15 ", key="funnel_p1_break")
    
    st.markdown("<p style='text-align: center; font-size: 24px; margin: -5px 0;'>▼</p>", unsafe_allow_html=True)
    
    st.markdown("##### **Phase 2: The Setup (แผนการเทรด)**")
    p2_bos = st.checkbox("Valid Sweep: เกิดการกวาดสภาพคล่อง ใน TF15M+", key="funnel_p2_sweep")
    p2_retest = st.checkbox("Retest Confirmation: ราคาทดสอบโซนที่สำคัญแล้ว (S/R หรือ VWAP)", key="funnel_p2_retest")
    
    st.markdown("<p style='text-align: center; font-size: 24px; margin: -5px 0;'>▼</p>", unsafe_allow_html=True)

    st.markdown("##### **Phase 3: The Final Check (ตรวจสอบครั้งสุดท้าย)**")
    p3_sl = st.checkbox("Valid SL: SL อยู่ในจุดที่ทำลายโครงสร้างชัดเจน", key="funnel_p3_sl")
    p3_sizing = st.checkbox("Valid Sizing: ขนาด Position เหมาะสม (ไม่ Overtrade)", key="funnel_p3_sizing")
    p3_mindset = st.checkbox("Valid Mindset: ไม่ใช่การเทรดเพื่อเอาคืน (Not a Revenge Trade)", key="funnel_p3_mindset")

    core_met = all([p2_bos, p2_retest, p3_sl, p3_sizing, p3_mindset])
    conf_met = any([p1_align, p1_vwap])
    
    if core_met:
        status_message = "🌟 A+ Setup" if conf_met else "✅ Valid Setup"
        st.success(status_message)
    else:
        status_message = "❌ Invalid Setup"
        st.error(status_message)
        
    return core_met, {
        "checklist_type": "Funnel", "p1_align": p1_align, "p1_break": p1_vwap,
        "p2_valid_sweep": p2_bos, "p2_retest": p2_retest, "p3_valid_sl": p3_sl,
        "p3_valid_sizing": p3_sizing, "p3_valid_mindset": p3_mindset,
    }


# ==============================================================================
#                          ฟังก์ชันหลักที่เรียกใช้งาน
# ==============================================================================

def render_checklist_section(supabase: Client):
    """
    Renders the Dual Checklist System using tabs.
    """
    with st.expander("📝 Trade Checklist & Logging System", expanded=True):
        
        col1, col2 = st.columns([1.5, 2])

        with col1:
            st.subheader("✅ Pre-Trade Checklist")
            
            # --- สร้าง Tabs เพื่อสลับระหว่าง Checklist ---
            tab1, tab2 = st.tabs(["**Funnel Checklist** (เทรดตามโครงสร้าง)", "**Sweep Reversal** (เทรดกลับตัว)"])
            
            with tab1:
                enable_save_button_funnel, funnel_data = funnel_checklist()

            
            # --- กำหนดข้อมูลที่จะบันทึกตาม Tab ที่เลือก ---
            # (ตรวจสอบว่า Tab ไหนกำลัง Active - เป็น trick เล็กน้อย)
            if 'active_tab' not in st.session_state: st.session_state.active_tab = "Funnel Checklist"
            # Streamlit ไม่มีวิธีเช็ค tab ที่ active โดยตรง เราจึงต้องใช้ on_change
            # แต่เพื่อความเรียบง่าย เราจะบันทึกข้อมูลจากทั้งสองระบบ แต่จะใช้ enable_save_button จากระบบเดียว
            # นี่คือวิธีที่ง่ายที่สุดโดยไม่ต้องใช้ callback ที่ซับซ้อน
            # สมมติว่าผู้ใช้จะกดบันทึกในแท็บที่ตัวเองกำลังดูอยู่
            # เราจะรวมข้อมูลและใช้ enable_button ของทั้งสอง
            
            # วิธีที่ดีกว่า: ใช้ radio button แทน tab
            checklist_choice = st.radio("เลือกประเภท Checklist ที่จะใช้บันทึก:", 
                                        ["Funnel Checklist", "Sweep Reversal"], horizontal=True, label_visibility="collapsed")
            
            if checklist_choice == "Funnel Checklist":
                enable_save_button = enable_save_button_funnel
                data_to_save = funnel_data
            else: # Sweep Reversal
                enable_save_button = enable_save_button_sweep
                data_to_save = sweep_data

        with col2:
            # --- START: โค้ด Snippet สำหรับเครื่องคิดเลขมาตรฐาน (ครบทุกปุ่มและรองรับ Paste) ---
            with st.expander("🧮 Calculator"):
                
                # --- ฟังก์ชันสำหรับจัดการการกดปุ่ม (Callbacks) ---
                def handle_input(char):
                    if st.session_state.get('calc_display', '0') == "0" and char != ".":
                        st.session_state.calc_display = char
                    elif char == "." and "." in st.session_state.get('calc_display', '0'):
                        pass # ป้องกันการใส่จุดซ้ำ
                    else:
                        st.session_state.calc_display += char
                    st.session_state.calc_input = st.session_state.calc_display

                def handle_operator(op):
                    # ป้องกันการใส่ operator ซ้ำซ้อน
                    last_char = st.session_state.get('calc_display', '0')[-1:]
                    if last_char not in ['+', '-', '×', '÷']:
                        st.session_state.calc_display += op
                    st.session_state.calc_input = st.session_state.calc_display

                def calculate_result():
                    try:
                        expression = st.session_state.calc_input.replace("×", "*").replace("÷", "/")
                        result = eval(expression)
                        st.session_state.calc_display = str(result)
                        st.session_state.calc_input = st.session_state.calc_display
                    except:
                        st.session_state.calc_display = "Error"
                        st.session_state.calc_input = "Error"

                def clear_display():
                    st.session_state.calc_display = "0"
                    st.session_state.calc_input = "0"
                    
                def delete_last():
                    current_val = st.session_state.get('calc_input', '0')
                    if len(current_val) > 1:
                        st.session_state.calc_display = current_val[:-1]
                    else:
                        st.session_state.calc_display = "0"
                    st.session_state.calc_input = st.session_state.calc_display
                    
                def sync_display_with_input():
                    st.session_state.calc_display = st.session_state.get('calc_input', '0')

                # --- เริ่มต้น Session State ---
                if 'calc_display' not in st.session_state:
                    st.session_state.calc_display = "0"
                if 'calc_input' not in st.session_state:
                    st.session_state.calc_input = "0"

                # หน้าจอแสดงผล
                st.text_input(
                    "Calculator Display", 
                    key="calc_input",
                    value=st.session_state.calc_display,
                    on_change=sync_display_with_input,
                    label_visibility="collapsed"
                )
                
                # แป้นพิมพ์
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.button("7", on_click=handle_input, args=("7",), use_container_width=True)
                    st.button("4", on_click=handle_input, args=("4",), use_container_width=True)
                    st.button("1", on_click=handle_input, args=("1",), use_container_width=True)
                    st.button("0", on_click=handle_input, args=("0",), use_container_width=True)

                with c2:
                    st.button("8", on_click=handle_input, args=("8",), use_container_width=True)
                    st.button("5", on_click=handle_input, args=("5",), use_container_width=True)
                    st.button("2", on_click=handle_input, args=("2",), use_container_width=True)
                    st.button(".", on_click=handle_input, args=(".",), use_container_width=True)

                with c3:
                    st.button("9", on_click=handle_input, args=("9",), use_container_width=True)
                    st.button("6", on_click=handle_input, args=("6",), use_container_width=True)
                    st.button("3", on_click=handle_input, args=("3",), use_container_width=True)
                    st.button("=", on_click=calculate_result, use_container_width=True, type="primary")

                with c4:
                    st.button("C", on_click=clear_display, use_container_width=True)
                    st.button("DEL", on_click=delete_last, use_container_width=True)
                    # --- START: เพิ่มปุ่มที่ขาดไป ---
                    st.button("＋", on_click=handle_operator, args=("+",), use_container_width=True)
                    st.button("－", on_click=handle_operator, args=("-",), use_container_width=True)
                    st.button("×", on_click=handle_operator, args=("×",), use_container_width=True)
                    st.button("÷", on_click=handle_operator, args=("÷",), use_container_width=True)
                    # --- END: เพิ่มปุ่มที่ขาดไป ---

            st.divider()

            # --- END: โค้ด Snippet ---

            st.subheader("✍️ บันทึกการเทรด (Logging)")
            
            with st.form("trade_log_form_v7"):
                notes = st.text_area("ข้อสังเกตเพิ่มเติม / TP Plan", height=150)
                image_url = st.text_input("ลิงก์รูปภาพจาก TradingView")
                
                submitted = st.form_submit_button("💾 บันทึก Setup นี้", disabled=not enable_save_button, type="primary")

                if submitted:
                    try:
                        # เพิ่ม notes และ image_url เข้าไปใน data ที่จะบันทึก
                        data_to_save["notes"] = notes
                        data_to_save["image_url"] = image_url
                        data_to_save["portfolio_id"] = st.session_state.get('active_portfolio_id_gs')

                        supabase.table("trades").insert(data_to_save).execute()
                        st.success("บันทึกข้อมูลสำเร็จ!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

        # ==============================================================================
        #                       BELOW COLUMNS: PAST TRADES DISPLAY
        # ==============================================================================
        st.divider()
        st.subheader("📚 บันทึกการเทรดย้อนหลัง (ล่าสุด 10 รายการ)")
        try:
            active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
            if active_portfolio_id:
                response = supabase.table("trades").select("*").eq("portfolio_id", active_portfolio_id).order("created_at", desc=True).limit(10).execute()
                if response.data:
                    df = pd.DataFrame(response.data)
                    # อัปเดตคอลัมน์ที่จะแสดงผล
                    display_columns = [
                        'created_at', 'notes', 'image_url', 
                        'p2_valid_bos', 'p2_retest_location', 'p3_valid_sl' # แสดงเงื่อนไขหลักๆ บางส่วน
                    ]
                    columns_to_show = [col for col in display_columns if col in df.columns]
                    df_display = df[columns_to_show]
                    
                    if 'created_at' in df_display.columns:
                        df_display['created_at'] = pd.to_datetime(df_display['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                else:
                    st.info("ยังไม่มีข้อมูลการเทรดที่ถูกบันทึกไว้สำหรับ Portfolio นี้")
            else:
                st.warning("กรุณาเลือก Portfolio ที่ต้องการดูก่อน")
        except Exception as e:
            st.error(f"ไม่สามารถดึงข้อมูลย้อนหลังได้: {e}")