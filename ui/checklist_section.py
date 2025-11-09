# ui/checklist_section.py (เวอร์ชันเต็มสมบูรณ์: Flexible Retest)

import streamlit as st
import pandas as pd
from supabase import Client
from datetime import datetime

def render_checklist_section(supabase: Client):
    """
    Renders the interactive checklist with Core & Confluence logic.
    *** อัปเกรด: เงื่อนไข Retest เป็นแบบ 'or' ***
    """
    with st.expander("📝 Trade Checklist & Logging System", expanded=True):
        
        col1, col2 = st.columns([1.5, 2])

        # ==============================================================================
        #                           COLUMN 1: CHECKLIST
        # ==============================================================================
        with col1:
            st.subheader("✅ Pre-Trade Checklist")

            st.markdown("##### **เงื่อนไขหลัก (Core Conditions)**")
            core_1_bos = st.checkbox("Break of Structure (BOS): เกิดการทำลายโครงสร้างในทิศทางเดียวกับ Bias แล้ว", key="log_core_1")
            
            st.markdown("**Retest Confirmation (เลือกอย่างน้อย 1 ข้อ):**")
            core_2a_retest_sr = st.checkbox("ราคาทดสอบแนวรับ-ต้านที่สำคัญ (เช่น Daily Open S/R) แล้ว", key="log_core_2a")
            core_2b_retest_vwap = st.checkbox("ราคาทดสอบเส้น VWAP แล้ว", key="log_core_2b")
            
            core_3_sl = st.checkbox("Valid SL: SL อยู่ในจุดที่ทำลายโครงสร้างอย่างชัดเจน", key="log_core_3")

            st.markdown("##### **เงื่อนไขเสริม (Confluence)**")
            conf_1_align = st.checkbox("H4/H1 alignment: อยู่ใน Mark Up / Mark Down Phase เดียวกัน", key="log_conf_1")
            conf_2_vwap_bias = st.checkbox("VWAP Bias: ราคายืนยันฝั่งได้เปรียบเทียบกับ VWAP", key="log_conf_2")

            # --- Logic การประเมินผลใหม่ ---
            retest_condition_met = core_2a_retest_sr or core_2b_retest_vwap
            core_conditions_met = all([core_1_bos, retest_condition_met, core_3_sl])
            confluence_conditions_met = any([conf_1_align, conf_2_vwap_bias])
            
            enable_save_button = core_conditions_met
            
            if core_conditions_met:
                if confluence_conditions_met:
                    st.success("🌟 A+ Setup: ผ่านเงื่อนไขหลักและมีเงื่อนไขเสริม")
                else:
                    st.success("✅ ผ่านเงื่อนไขหลัก (Core Conditions Met)")
            else:
                st.error("❌ ยังไม่ผ่านเงื่อนไขหลัก (Core Conditions Not Met)")

        # ==============================================================================
        #                           COLUMN 2: LOGGING FORM
        # ==============================================================================
        with col2:
            st.subheader("✍️ บันทึกการเทรด (Logging)")
            
            with st.form("trade_log_form"):
                notes = st.text_area("เหตุผลการเข้าเทรด / ข้อสังเกตเพิ่มเติม (Trade Notes)", height=100, placeholder="เช่น รอเกิด BOS ที่ FVG ของ H1...")
                image_url = st.text_input("ลิงก์รูปภาพจาก TradingView", placeholder="Copy link to chart image...")
                
                submitted = st.form_submit_button("💾 บันทึกการเทรดนี้", disabled=not enable_save_button, type="primary")

                if submitted:
                    try:
                        trade_data = {
                            "bos_confirm": core_1_bos,
                            "retest_sr": core_2a_retest_sr,
                            "retest_vwap": core_2b_retest_vwap,
                            "sl_valid": core_3_sl,
                            "h4_h1_align": conf_1_align,
                            "vwap_bias": conf_2_vwap_bias,
                            "notes": notes,
                            "image_url": image_url,
                            "portfolio_id": st.session_state.get('active_portfolio_id_gs')
                        }
                        supabase.table("trades").insert(trade_data).execute()
                        st.success(f"บันทึกข้อมูลการเทรดสำเร็จ! ({datetime.now().strftime('%H:%M:%S')})")
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