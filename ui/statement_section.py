# ui/statement_section.py 

import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
import uuid
import traceback # เพิ่ม import นี้เผื่อไว้ใช้

from config import settings
from core import gs_handler, statement_processor

def render_statement_section():
    with st.expander("📂 Ultimate Chart Dashboard Import & Processing", expanded=False):
        st.markdown("### 📊 จัดการ Statement และข้อมูลดิบ")
        st.markdown("---")
        st.subheader("📤 ขั้นตอนที่ 1: อัปโหลด Statement Report (CSV)")

        if 'uploader_key' not in st.session_state:
            st.session_state.uploader_key = 0

        uploaded_file = st.file_uploader(
            "ลากและวางไฟล์ Statement Report (CSV) ที่นี่",
            type=["csv"],
            key=f"statement_uploader_{st.session_state.uploader_key}"
        )

        if uploaded_file and st.session_state.get('processed_filename') != uploaded_file.name:
            st.session_state['extracted_data'] = None
            st.session_state['processed_filename'] = uploaded_file.name

        if uploaded_file is not None:
            active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
            active_portfolio_name = st.session_state.get('active_portfolio_name_gs')

            if not active_portfolio_id:
                st.toast("กรุณาเลือกพอร์ตก่อนอัปโหลด", icon="⚠️")
                return

            with st.spinner(f"กำลังตรวจสอบไฟล์ '{uploaded_file.name}'..."):
                try:
                    # --- Pre-computation ---
                    file_content_bytes = uploaded_file.getvalue()
                    current_file_hash = hashlib.md5(file_content_bytes).hexdigest()
                    
                    # --- Duplicate File Check ---
                    gc = gs_handler.get_gspread_client()
                    ws_dict, setup_error = gs_handler.setup_and_get_worksheets(gc)
                    if setup_error:
                        st.error(f"Setup GSheet Error: {setup_error}")
                        return
                    
                    history_ws = ws_dict.get(settings.WORKSHEET_UPLOAD_HISTORY)
                    if history_ws:
                        is_duplicate, details = gs_handler.check_for_duplicate_file_hash(history_ws, current_file_hash)
                        if is_duplicate:
                            st.error(f"**ตรวจพบไฟล์ซ้ำ!**")
                            st.warning(f"ไฟล์นี้เคยถูกอัปโหลดสำหรับพอร์ต **'{details['PortfolioName']}'** แล้วเมื่อวันที่ **{details['UploadTimestamp']}**")
                            st.info("ระบบไม่อนุญาตให้อัปโหลดไฟล์เดียวกันซ้ำ เพื่อป้องกันข้อมูลที่ผิดพลาด หากต้องการดำเนินการต่อกรุณาใช้ไฟล์ Statement ฉบับใหม่")
                            st.stop() # หยุดการทำงานทั้งหมด
                    
                    # --- Extraction ---
                    st.session_state['extracted_data'] = statement_processor.extract_data_from_report_content(file_content_bytes)
                    st.session_state['file_info_to_save'] = {"name": uploaded_file.name, "size": uploaded_file.size, "content_bytes": file_content_bytes, "hash": current_file_hash}
                
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการอ่านและตรวจสอบไฟล์: {e}")
                    st.session_state['extracted_data'] = None

            if st.session_state.get('extracted_data'):
                st.markdown("---")
                st.subheader("📊 ขั้นตอนที่ 2: ผลการวิเคราะห์ไฟล์ (ยังไม่บันทึก)")
                
                extracted_data = st.session_state['extracted_data']
                deals_count = len(extracted_data.get('deals', pd.DataFrame()))
                orders_count = len(extracted_data.get('orders', pd.DataFrame()))
                positions_count = len(extracted_data.get('positions', pd.DataFrame()))
                balance_summary = extracted_data.get('balance_summary', {})
                results_summary = extracted_data.get('results_summary', {})

                st.success(f"✅ วิเคราะห์ไฟล์สำเร็จ! พบข้อมูลดังนี้:")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Deals ที่พบ", f"{deals_count} รายการ")
                col2.metric("Orders ที่พบ", f"{orders_count} รายการ")
                col3.metric("Positions ที่พบ", f"{positions_count} รายการ")
                
                # --- แสดงข้อมูล Summary ---
                st.markdown("#####  финансовые результаты (Financial Summary)")
                sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
                sum_col1.metric("Equity", f"${balance_summary.get('equity', 0.0):,.2f}")
                sum_col2.metric("Balance", f"${balance_summary.get('balance', 0.0):,.2f}")
                sum_col3.metric("Profit", f"${results_summary.get('profit', 0.0):,.2f}", delta=results_summary.get('profit', 0.0))
                sum_col4.metric("Deposit", f"${results_summary.get('deposit_load', 0.0):,.2f}")
                
                st.info("กรุณาตรวจสอบข้อมูล หากถูกต้องให้กดยืนยันเพื่อบันทึก")


        if st.session_state.get('extracted_data'):
            st.markdown("---")
            st.subheader("💾 ขั้นตอนที่ 3: ยืนยันการบันทึกข้อมูล")
            if st.button("✅ ยืนยันการบันทึกข้อมูล (Confirm & Save)"):
                try:
                    # ดึงข้อมูลที่จำเป็นจาก session_state กลับมาใช้
                    extracted_data = st.session_state['extracted_data']
                    file_info = st.session_state['file_info_to_save']
                    active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
                    active_portfolio_name = st.session_state.get('active_portfolio_name_gs')

                    has_errors = False
                    
                    # --- Setup GSheets ---
                    gc = gs_handler.get_gspread_client()
                    ws_dict, setup_error = gs_handler.setup_and_get_worksheets(gc)

                    if setup_error:
                        st.error(f"Setup GSheet Error: {setup_error}")
                        return

                    # --- เริ่มกระบวนการบันทึกข้อมูล พร้อมแสดงสถานะ ---
                    with st.spinner("กำลังบันทึกข้อมูล Deals..."):
                        deals_data = extracted_data.get('deals', pd.DataFrame())
                        ok_d, new_d, skip_d = gs_handler.save_deals_to_actual_trades(ws_dict.get(settings.WORKSHEET_ACTUAL_TRADES), deals_data, active_portfolio_id, active_portfolio_name, file_info['name'], "batch_id_placeholder")
                        if not ok_d: has_errors = True
                    st.write(f"Deals: บันทึกสำเร็จ! (ใหม่ {new_d}, ข้าม {skip_d})")

                    with st.spinner("กำลังบันทึกข้อมูล Orders..."):
                        orders_data = extracted_data.get('orders', pd.DataFrame())
                        ok_o, new_o, skip_o = gs_handler.save_orders_to_actul_orders(ws_dict.get(settings.WORKSHEET_ACTUAL_ORDERS), orders_data, active_portfolio_id, active_portfolio_name, file_info['name'], "batch_id_placeholder")
                        if not ok_o: has_errors = True
                    st.write(f"Orders: บันทึกสำเร็จ! (ใหม่ {new_o}, ข้าม {skip_o})")

                    with st.spinner("กำลังบันทึกข้อมูล Positions..."):
                        positions_data = extracted_data.get('positions', pd.DataFrame())
                        ok_p, new_p, skip_p = gs_handler.save_positions_to_actul_positions(ws_dict.get(settings.WORKSHEET_ACTUAL_POSITIONS), positions_data, active_portfolio_id, active_portfolio_name, file_info['name'], "batch_id_placeholder")
                        if not ok_p: has_errors = True
                    st.write(f"Positions: บันทึกสำเร็จ! (ใหม่ {new_p}, ข้าม {skip_p})")
                    
                    with st.spinner("กำลังบันทึกข้อมูล Summary..."):
                        bal_summary = extracted_data.get('balance_summary', {})
                        res_summary = extracted_data.get('results_summary', {})
                        ok_s, note_s = gs_handler.save_results_summary_to_gsheets(ws_dict.get(settings.WORKSHEET_STATEMENT_SUMMARIES), bal_summary, res_summary, active_portfolio_id, active_portfolio_name, file_info['name'], "batch_id_placeholder")
                        if not ok_s: has_errors = True
                    st.write(f"Summary: บันทึกสำเร็จ! (สถานะ: {note_s})")
                    
                    # --- ส่วนของการบันทึกประวัติ (History Log) ---
                    with st.spinner("กำลังบันทึกประวัติการอัปโหลด..."):
                        upload_status = "Success" if not has_errors else "Failed"
                        notes_message = f"Deals:New={new_d},Skip={skip_d},OK={ok_d} | Orders:New={new_o},Skip={skip_o},OK={ok_o} | Positions:New={new_p},Skip={skip_p},OK={ok_p} | Summary:Status={note_s},OK={ok_s}"
                        import_batch_id = str(uuid.uuid4())
                        history_log = {
                            "UploadTimestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "PortfolioID": active_portfolio_id, "PortfolioName": active_portfolio_name,
                            "FileName": file_info['name'], "FileSize": file_info['size'],
                            "FileHash": hashlib.md5(file_info['content_bytes']).hexdigest(),
                            "Status": upload_status, "ImportBatchID": import_batch_id, "Notes": notes_message
                        }
                        history_worksheet = ws_dict.get(settings.WORKSHEET_UPLOAD_HISTORY)
                        if history_worksheet:
                            save_ok, save_note = gs_handler.save_upload_history(history_worksheet, history_log)
                        else:
                            st.warning("ไม่ได้ตั้งค่า `WORKSHEET_UPLOAD_HISTORY` ใน settings")
                    st.write("ประวัติการอัปโหลด: บันทึกสำเร็จ!")
                    
                    # --- สรุปผลสุดท้าย ---
                    st.balloons()
                    st.success("บันทึกข้อมูลทั้งหมดลงในฐานข้อมูลเรียบร้อยแล้ว!")
                    
                    # ล้างข้อมูลใน session state และ reset uploader
                    st.session_state['extracted_data'] = None
                    st.session_state.uploader_key += 1
                    st.rerun() 

                except Exception as e:
                    st.error("เกิดข้อผิดพลาดร้ายแรงระหว่างการบันทึกข้อมูล")
                    st.exception(e)