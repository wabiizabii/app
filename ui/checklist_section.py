# ui/checklist_section.py (เวอร์ชันออกแบบใหม่: The Funnel Checklist)

import streamlit as st
import pandas as pd
from supabase import Client
from datetime import datetime

def render_checklist_section(supabase: Client):
    """
    Renders the redesigned "Funnel Checklist" and logging system.
    """
    with st.expander("📝 Trade Checklist & Logging System", expanded=True):
        
        col1, col2 = st.columns([1.5, 2])

        # ==============================================================================
        #                           COLUMN 1: FUNNEL CHECKLIST
        # ==============================================================================
        with col1:
            st.subheader("✅ Pre-Trade Funnel Checklist")

            # --- Phase 1: The Big Picture ---
            with st.container(border=True):
                st.markdown("##### **Phase 1: The Big Picture (ภาพรวม)**")
                p1_align = st.checkbox("Top-Down Alignment: ทิศทางใน H4/H1 สอดคล้องกัน", key="p1_align")
                p1_vwap = st.checkbox("VWAP Bias: ราคาอยู่ฝั่งได้เปรียบเทียบกับ VWAP", key="p1_vwap")
            
            st.markdown("<p style='text-align: center; font-size: 24px; margin: -5px 0;'>▼</p>", unsafe_allow_html=True)
            
            # --- Phase 2: The Setup ---
            with st.container(border=True):
                st.markdown("##### **Phase 2: The Setup (แผนการเทรด)**")
                p2_bos = st.checkbox("Valid BOS: เกิดการทำลายโครงสร้าง (ปิดด้วยเนื้อเทียน) ใน TF15M+", key="p2_bos")
                p2_retest = st.checkbox("Retest Confirmation: ราคาทดสอบโซนที่สำคัญแล้ว (S/R หรือ VWAP)", key="p2_retest")
            
            st.markdown("<p style='text-align: center; font-size: 24px; margin: -5px 0;'>▼</p>", unsafe_allow_html=True)

            # --- Phase 3: The Final Check ---
            with st.container(border=True):
                st.markdown("##### **Phase 3: The Final Check (ตรวจสอบครั้งสุดท้าย)**")
                p3_sl = st.checkbox("Valid SL: SL อยู่ในจุดที่ทำลายโครงสร้างชัดเจน", key="p3_sl")
                p3_sizing = st.checkbox("Valid Sizing: ขนาด Position เหมาะสม (ไม่ Overtrade)", key="p3_sizing")
                p3_mindset = st.checkbox("Valid Mindset: ไม่ใช่การเทรดเพื่อเอาคืน (Not a Revenge Trade)", key="p3_mindset")

            # --- Logic การประเมินผล ---
            # เงื่อนไขหลักคือ Phase 2 และ 3 ต้องผ่านทั้งหมด
            core_conditions_met = all([p2_bos, p2_retest, p3_sl, p3_sizing, p3_mindset])
            # เงื่อนไขเสริมคือ Phase 1 ต้องผ่านอย่างน้อย 1 ข้อ
            confluence_conditions_met = any([p1_align, p1_vwap])
            
            enable_save_button = core_conditions_met

            st.divider()
            if core_conditions_met:
                if confluence_conditions_met:
                    st.success("🌟 **A+ Setup:** ผ่านทุกเงื่อนไขและภาพรวมดีเยี่ยม")
                else:
                    st.success("✅ **Valid Setup:** ผ่านเงื่อนไขหลัก พร้อมเทรด")
            else:
                st.error("❌ **Invalid Setup:** ยังไม่ผ่านเงื่อนไขหลัก")

        # ==============================================================================
        #                           COLUMN 2: LOGGING FORM
        # ==============================================================================
        with col2:
            st.subheader("✍️ บันทึกการเทรด (Logging)")
            
            with st.form("trade_log_form_v4"):
                notes = st.text_area("เหตุผลการเข้าเทรด / ข้อสังเกตเพิ่มเติม", height=125)
                image_url = st.text_input("ลิงก์รูปภาพจาก TradingView")
                
                submitted = st.form_submit_button("💾 บันทึกการเทรดนี้", disabled=not enable_save_button, type="primary")

                if submitted:
                    try:
                        trade_data = {
                            "p1_align": p1_align,
                            "p1_vwap_bias": p1_vwap,
                            "p2_valid_bos": p2_bos,
                            "p2_retest": p2_retest,
                            "p3_valid_sl": p3_sl,
                            "p3_valid_sizing": p3_sizing,
                            "p3_valid_mindset": p3_mindset,
                            "notes": notes,
                            "image_url": image_url,
                            "portfolio_id": st.session_state.get('active_portfolio_id_gs')
                        }
                        supabase.table("trades").insert(trade_data).execute()
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
                    display_columns = ['created_at', 'notes', 'image_url', 'bos_confirm', 'retest_sr', 'retest_vwap', 'sl_valid', 'h4_h1_align', 'vwap_bias']
                    columns_to_show = [col for col in display_columns if col in df.columns]
                    df_display = df[columns_to_show]
                    
                    # ตรวจสอบว่าคอลัมน์ 'created_at' มีอยู่จริงก่อนแปลง
                    if 'created_at' in df_display.columns:
                        df_display['created_at'] = pd.to_datetime(df_display['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                else:
                    st.info("ยังไม่มีข้อมูลการเทรดที่ถูกบันทึกไว้สำหรับ Portfolio นี้")
            else:
                st.warning("กรุณาเลือก Portfolio ที่ต้องการดูก่อน")
        except Exception as e:
            st.error(f"ไม่สามารถดึงข้อมูลย้อนหลังได้: {e}")