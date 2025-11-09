# ui/statement_section.py (เวอร์ชันใหม่ v2: ใช้ Active Portfolio จาก Sidebar)

import streamlit as st
import pandas as pd
from core import statement_processor, supabase_handler as db_handler
import hashlib
from datetime import datetime
import time
from config import settings # Ensure settings is imported

def render_statement_section():
    """
    แสดงผล Section การอัปโหลดไฟล์ Statement ที่เรียบง่าย
    *** อัปเกรด: ใช้ Active Portfolio จาก Sidebar โดยตรง ***
    """
    with st.expander("⬆️ Upload Trading Statement", expanded=False):

        # --- 1. ดึง Active Portfolio จาก session_state ---
        active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
        active_portfolio_name = st.session_state.get('active_portfolio_name_gs')

        if not active_portfolio_id:
            st.warning("⚠️ **โปรดเลือก 'Active Portfolio' ในเมนูด้านข้างก่อน** เพื่อระบุว่าจะอัปเดตข้อมูลให้พอร์ตใด")
            return # หยุดการทำงานของ Section นี้ทั้งหมดถ้ายังไม่มี Active Portfolio

        st.success(f"**คุณกำลังจะอัปเดตข้อมูลสำหรับ Portfolio:** `{active_portfolio_name}`")
        st.divider()

        # --- 2. อัปโหลดไฟล์ Statement ---
        st.markdown("##### อัปโหลดไฟล์ Statement (.csv หรือ .html):")
        uploaded_file = st.file_uploader(
            "ลากไฟล์มาวาง หรือกดเพื่อเลือกไฟล์",
            type=["csv", "html"],
            label_visibility="collapsed"
        )

        st.divider()

        # --- 3. ปุ่มยืนยันและ Logic การทำงาน ---
        if st.button("💾 บันทึกข้อมูลลงใน Portfolio ที่เลือก", use_container_width=True, type="primary"):
            
            # --- Logic ตรวจสอบความถูกต้อง ---
            if not uploaded_file:
                st.warning("⚠️ โปรดอัปโหลดไฟล์ Statement ก่อน")
                return # หยุดการทำงานทันที

            with st.spinner("กำลังตรวจสอบและประมวลผลไฟล์..."):
                file_content_bytes = uploaded_file.getvalue()
                file_hash = hashlib.sha256(file_content_bytes).hexdigest()

                # --- Logic ตรวจสอบไฟล์ซ้ำ ---
                is_duplicate, duplicate_details = db_handler.check_duplicate_file(file_hash, active_portfolio_id)
                if is_duplicate:
                    st.error(f"❌ **ไฟล์ซ้ำ!** เนื้อหาของไฟล์นี้เคยถูกอัปโหลดสำหรับ Portfolio '{active_portfolio_name}' ไปแล้วเมื่อ {duplicate_details.get('UploadTimestamp')}")
                    return # หยุดการทำงานทันที

                # --- ถ้าผ่านทุกอย่าง ให้เริ่มการประมวลผลและบันทึก ---
                try:
                    # (ส่วนที่เหลือของโค้ดเหมือนเดิมทุกประการ)
                    extracted_data = statement_processor.extract_data_from_report_content(file_content_bytes)
                    
                    if not extracted_data or extracted_data.get('deals', pd.DataFrame()).empty:
                        st.error("❌ ไม่สามารถดึงข้อมูลการเทรด (Deals) จากไฟล์ได้ โปรดตรวจสอบรูปแบบไฟล์")
                        return

                    data_to_save = {}
                    import_batch_id = str(int(datetime.now().timestamp()))
                    
                    # Loop through main dataframes
                    for key, table_name in settings.WORKSHEET_HEADERS_MAPPER.items():
                        df = extracted_data.get(key, pd.DataFrame())
                        df_to_save = pd.DataFrame() # สร้าง DataFrame ว่างๆ ไว้ก่อน
                        if not df.empty:
                            df_to_save = df.copy()
                            df_to_save['PortfolioID'] = str(active_portfolio_id)
                            df_to_save['PortfolioName'] = active_portfolio_name
                            df_to_save['SourceFile'] = uploaded_file.name
                            df_to_save['ImportBatchID'] = import_batch_id
                        data_to_save[table_name] = df_to_save
                    
                    # Prepare summary data
                    summary_data = extracted_data.get('final_summary_data', {})
                    if summary_data:
                        summary_data['PortfolioID'] = str(active_portfolio_id)
                        summary_data['PortfolioName'] = active_portfolio_name
                        summary_data['SourceFile'] = uploaded_file.name
                        summary_data['ImportBatchID'] = import_batch_id
                        summary_data['Timestamp'] = datetime.now()
                    data_to_save[settings.SUPABASE_TABLE_STATEMENT_SUMMARIES] = summary_data

                    # Prepare upload history
                    upload_history_data = {
                        "UploadTimestamp": datetime.now(), "PortfolioID": str(active_portfolio_id),
                        "PortfolioName": active_portfolio_name, "FileName": uploaded_file.name,
                        "FileSize": len(file_content_bytes), "FileHash": file_hash, "Status": "Success",
                        "ImportBatchID": import_batch_id, "Notes": "Uploaded via Streamlit app"
                    }
                    data_to_save[settings.SUPABASE_TABLE_UPLOAD_HISTORY] = upload_history_data
                    
                    st.info("กำลังบันทึกข้อมูลลงฐานข้อมูล...")
                    success, message = db_handler.save_statement_data(data_to_save)

                    if success:
                        st.success(f"✔️ บันทึกข้อมูลสำหรับ Portfolio '{active_portfolio_name}' สำเร็จ!")
                        st.balloons()
                        db_handler.clear_all_caches()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ เกิดข้อผิดพลาดในการบันทึก: {message}")

                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดรุนแรงระหว่างการประมวลผลไฟล์: {e}")