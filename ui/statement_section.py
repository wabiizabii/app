# ui/statement_section.py

import streamlit as st
import pandas as pd
import hashlib
import random
from datetime import datetime
import uuid

# Import functions and settings from other modules
from config import settings
from core import gs_handler
from core import statement_processor

def render_statement_section():
    """
    Renders the statement import and processing section in the main area.
    Corresponds to SEC 6 of main (1).py, preserving its original logic and flow.
    """
    with st.expander("📂 Ultimate Chart Dashboard Import & Processing", expanded=False):
        st.markdown("### 📊 จัดการ Statement และข้อมูลดิบ")
        st.markdown("---")
        st.subheader("📤 อัปโหลด Statement Report (CSV) เพื่อประมวลผลและบันทึก")

        uploaded_file_statement = st.file_uploader(
            "ลากและวางไฟล์ Statement Report (CSV) ที่นี่ หรือคลิกเพื่อเลือกไฟล์",
            type=["csv"],
            key=f"ultimate_stmt_uploader_v2_{st.session_state.uploader_key_version}"
        )

        st.checkbox("⚙️ เปิดโหมด Debug (แสดงข้อมูลที่แยกได้ + Log การทำงานบางส่วนใน Console)",
                    value=st.session_state.get("debug_statement_processing_v2", False),
                    key="debug_statement_processing_v2")

        active_portfolio_id_for_stmt_import = st.session_state.get('active_portfolio_id_gs', None)
        active_portfolio_name_for_stmt_import = st.session_state.get('active_portfolio_name_gs', None)

        _UPLOAD_PROCESSED_IN_THIS_CYCLE = "_upload_processed_in_this_cycle_v2" 

        if uploaded_file_statement is not None and not st.session_state.get(_UPLOAD_PROCESSED_IN_THIS_CYCLE, False):
            st.session_state[_UPLOAD_PROCESSED_IN_THIS_CYCLE] = True

            file_name_stmt = uploaded_file_statement.name
            file_size_stmt = uploaded_file_statement.size

            file_hash_stmt = ""
            try:
                uploaded_file_statement.seek(0)
                file_content_for_hash_stmt = uploaded_file_statement.read()
                uploaded_file_statement.seek(0)
                file_hash_stmt = hashlib.md5(file_content_for_hash_stmt).hexdigest()
            except Exception as e_hash_stmt:
                file_hash_stmt = f"hash_error_{random.randint(1000,9999)}"
                print(f"Warning: Could not compute MD5 hash for file: {e_hash_stmt}")

            _trigger_rerun_after_upload_handling = True
            _equity_updated_successfully_this_cycle = False

            if not active_portfolio_id_for_stmt_import:
                st.error("กรุณาเลือกพอร์ตที่ใช้งาน (Active Portfolio) ใน Sidebar ก่อนประมวลผล Statement.")
                # No st.stop() here as per original logic, let it continue to uploader reset.
            else:
                st.info(f"ไฟล์ที่อัปโหลด: {file_name_stmt} (ขนาด: {file_size_stmt} bytes, Hash: {file_hash_stmt})")

                gc_stmt = gs_handler.get_gspread_client()
                if not gc_stmt:
                    st.error("ไม่สามารถเชื่อมต่อ Google Sheets Client ได้")
                else:
                    ws_stmt_dict, setup_error_msg = gs_handler.setup_and_get_worksheets(gc_stmt)
                    
                    if setup_error_msg:
                        st.error(setup_error_msg)
                    elif not ws_stmt_dict:
                        st.error("ไม่สามารถเข้าถึง Worksheet ที่จำเป็นได้ (Statement Processing)")
                    else:
                        previously_processed_successfully = False
                        try:
                            ws_upload_history = ws_stmt_dict.get(settings.WORKSHEET_UPLOAD_HISTORY)
                            if ws_upload_history and ws_upload_history.row_count > 1:
                                history_records_stmt = ws_upload_history.get_all_records(numericise_ignore=['all'])
                                for record_stmt in history_records_stmt:
                                    try: record_file_size_stmt_val = int(float(str(record_stmt.get("FileSize","0")).replace(",","")))
                                    except: record_file_size_stmt_val = 0

                                    if str(record_stmt.get("PortfolioID","")) == str(active_portfolio_id_for_stmt_import) and \
                                       record_stmt.get("FileName","") == file_name_stmt and \
                                       record_file_size_stmt_val == file_size_stmt and \
                                       record_stmt.get("FileHash","") == file_hash_stmt and \
                                       str(record_stmt.get("Status","")).startswith("Success"):
                                        previously_processed_successfully = True
                                        break
                        except Exception as e_hist_read_stmt:
                            print(f"Warning: Could not read UploadHistory for duplicate file check: {e_hist_read_stmt}")

                        if previously_processed_successfully:
                            st.warning(f"⚠️ ไฟล์ '{file_name_stmt}' นี้ เคยถูกประมวลผลสำเร็จสำหรับพอร์ต '{active_portfolio_name_for_stmt_import}' ไปแล้ว จะไม่ดำเนินการใดๆ ซ้ำอีก")
                            # --- START MODIFICATION ---
                            # Add return to stop further processing if already processed successfully
                            return # <--- เพิ่มบรรทัดนี้เพื่อหยุดการทำงานต่อ
                            # --- END MODIFICATION ---
                        else:
                            import_batch_id_stmt = str(uuid.uuid4())
                            upload_timestamp_stmt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            initial_log_ok_stmt = False
                            try:
                                ws_upload_history.append_row([
                                    upload_timestamp_stmt, str(active_portfolio_id_for_stmt_import), str(active_portfolio_name_for_stmt_import),
                                    file_name_stmt, file_size_stmt, file_hash_stmt,
                                    "Processing", import_batch_id_stmt, "Attempting to process."
                                ])
                                initial_log_ok_stmt = True
                            except Exception as e_log_init_stmt:
                                st.error(f"ไม่สามารถบันทึก Log เริ่มต้นใน {settings.WORKSHEET_UPLOAD_HISTORY}: {e_log_init_stmt}")

                            if initial_log_ok_stmt:
                                st.markdown(f"--- \n**Import Batch ID: `{import_batch_id_stmt}`**")
                                st.info(f"กำลังประมวลผลไฟล์: {file_name_stmt}")

                                processing_errors_stmt = False
                                final_status_stmt = "Failed_Unknown"
                                processing_notes_stmt = []

                                try:
                                    uploaded_file_statement.seek(0)
                                    file_content_bytes_stmt = uploaded_file_statement.getvalue()

                                    with st.spinner(f"กำลังแยกส่วนข้อมูลจาก {file_name_stmt}..."):
                                        extracted_stmt_data = statement_processor.extract_data_from_report_content(file_content_bytes_stmt)

                                    if st.session_state.get("debug_statement_processing_v2", False):
                                        st.write("--- DEBUG: Extracted Statement Data ---")
                                        debug_display_data = {}
                                        for k, v in extracted_stmt_data.items():
                                            if isinstance(v, pd.DataFrame):
                                                debug_display_data[k] = f"DataFrame with {len(v)} rows" if not v.empty else "Empty DataFrame"
                                            else:
                                                debug_display_data[k] = v
                                        st.json(debug_display_data, expanded=False)
                                        st.write("--- END DEBUG ---")

                                    extraction_successful = extracted_stmt_data and \
                                                            (any(isinstance(df, pd.DataFrame) and not df.empty
                                                                 for name, df in extracted_stmt_data.items() if name in ['deals', 'orders', 'positions']) or \
                                                             extracted_stmt_data.get('balance_summary') or extracted_stmt_data.get('results_summary'))

                                    if not extraction_successful:
                                        st.warning("ไม่สามารถแยกข้อมูลที่มีความหมายจากไฟล์ได้ หรือไฟล์ไม่มีข้อมูล Transactional/Summary.")
                                        final_status_stmt = "Failed_Extraction"
                                        processing_notes_stmt.append("Failed to extract meaningful data.")
                                        processing_errors_stmt = True

                                    if not processing_errors_stmt:
                                        st.subheader("💾 กำลังบันทึกข้อมูลส่วนต่างๆไปยัง Google Sheets...")

                                        deals_data = extracted_stmt_data.get('deals', pd.DataFrame())
                                        ok_d_stmt, new_d_stmt, skip_d_stmt = gs_handler.save_deals_to_actual_trades_sec6(ws_stmt_dict.get(settings.WORKSHEET_ACTUAL_TRADES), deals_data, active_portfolio_id_for_stmt_import, active_portfolio_name_for_stmt_import, file_name_stmt, import_batch_id_stmt)
                                        processing_notes_stmt.append(f"Deals:New={new_d_stmt},Skip={skip_d_stmt},OK={ok_d_stmt}")
                                        if ok_d_stmt: st.write(f"✔️ ({settings.WORKSHEET_ACTUAL_TRADES}) Deals: เพิ่ม {new_d_stmt}, ข้าม {skip_d_stmt}.")
                                        else: st.error(f"❌ ({settings.WORKSHEET_ACTUAL_TRADES}) Deals: ล้มเหลว"); processing_errors_stmt = True

                                        orders_data = extracted_stmt_data.get('orders', pd.DataFrame())
                                        ok_o_stmt, new_o_stmt, skip_o_stmt = gs_handler.save_orders_to_gsheets_sec6(ws_stmt_dict.get(settings.WORKSHEET_ACTUAL_ORDERS), orders_data, active_portfolio_id_for_stmt_import, active_portfolio_name_for_stmt_import, file_name_stmt, import_batch_id_stmt)
                                        processing_notes_stmt.append(f"Orders:New={new_o_stmt},Skip={skip_o_stmt},OK={ok_o_stmt}")
                                        if ok_o_stmt: st.write(f"✔️ ({settings.WORKSHEET_ACTUAL_ORDERS}) Orders: เพิ่ม {new_o_stmt}, ข้าม {skip_o_stmt}.")
                                        else: st.error(f"❌ ({settings.WORKSHEET_ACTUAL_ORDERS}) Orders: ล้มเหลว"); processing_errors_stmt = True

                                        positions_data = extracted_stmt_data.get('positions', pd.DataFrame())
                                        ok_p_stmt, new_p_stmt, skip_p_stmt = gs_handler.save_positions_to_gsheets_sec6(ws_stmt_dict.get(settings.WORKSHEET_ACTUAL_POSITIONS), positions_data, active_portfolio_id_for_stmt_import, active_portfolio_name_for_stmt_import, file_name_stmt, import_batch_id_stmt)
                                        processing_notes_stmt.append(f"Positions:New={new_p_stmt},Skip={skip_p_stmt},OK={ok_p_stmt}")
                                        if ok_p_stmt: st.write(f"✔️ ({settings.WORKSHEET_ACTUAL_POSITIONS}) Positions: เพิ่ม {new_p_stmt}, ข้าม {skip_p_stmt}.")
                                        else: st.error(f"❌ ({settings.WORKSHEET_ACTUAL_POSITIONS}) Positions: ล้มเหลว"); processing_errors_stmt = True

                                        bal_summary_data = extracted_stmt_data.get('balance_summary', {})
                                        res_summary_data = extracted_stmt_data.get('results_summary', {})
                                        summary_ok_stmt, summary_note_stmt = False, "no_data_to_save"

                                        if bal_summary_data or res_summary_data:
                                            summary_ok_stmt, summary_note_stmt = gs_handler.save_results_summary_to_gsheets_sec6(
                                                ws_stmt_dict.get(settings.WORKSHEET_STATEMENT_SUMMARIES), bal_summary_data, res_summary_data,
                                                active_portfolio_id_for_stmt_import, active_portfolio_name_for_stmt_import,
                                                file_name_stmt, import_batch_id_stmt
                                            )
                                        processing_notes_stmt.append(f"Summary:Status={summary_note_stmt},OK={summary_ok_stmt}")
                                        if summary_note_stmt == "saved_new": st.write(f"✔️ ({settings.WORKSHEET_STATEMENT_SUMMARIES}) Summary: บันทึกใหม่")
                                        elif summary_note_stmt == "skipped_duplicate_content": st.info(f"({settings.WORKSHEET_STATEMENT_SUMMARIES}) Summary: ข้อมูลซ้ำ, ไม่บันทึกเพิ่ม")
                                        elif summary_note_stmt != "no_data_to_save": st.error(f"❌ ({settings.WORKSHEET_STATEMENT_SUMMARIES}) Summary: ล้มเหลว ({summary_note_stmt})"); processing_errors_stmt = True

                                        # ---- KEY UPDATE FOR BALANCE DISPLAY ----
                                        if not processing_errors_stmt and 'equity' in bal_summary_data and bal_summary_data['equity'] is not None:
                                            try:
                                                current_latest_equity = float(bal_summary_data['equity'])
                                                st.session_state.latest_statement_equity = current_latest_equity
                                                st.session_state.current_account_balance = current_latest_equity
                                                st.success(f"✔️ อัปเดต Balance สำหรับคำนวณจาก Statement Equity ล่าสุด: {current_latest_equity:,.2f} USD")
                                                processing_notes_stmt.append(f"Updated_Session_Equity={current_latest_equity}")
                                                if hasattr(gs_handler.load_statement_summaries_from_gsheets, 'clear'):
                                                    gs_handler.load_statement_summaries_from_gsheets.clear()
                                                    gs_handler.load_actual_trades_from_gsheets.clear()
                                            except ValueError:
                                                st.warning("⚠️ ไม่สามารถแปลงค่า Equity จาก Statement เป็นตัวเลขเพื่ออัปเดต session state.")
                                                processing_notes_stmt.append("Warning: Failed to convert Equity from Statement for session state.")
                                        elif not processing_errors_stmt:
                                            st.warning("⚠️ ไม่พบค่า 'Equity' ใน Statement ที่อัปโหลด หรือค่าไม่ถูกต้อง จะยังคงใช้ Balance ก่อนหน้า หรือ Initial Balance.")
                                            processing_notes_stmt.append("Warning: 'Equity' not found/valid in Statement for session update.")
                                        # ---- END KEY UPDATE ----

                                        if not processing_errors_stmt:
                                            final_status_stmt = "Success"
                                            st.balloons()
                                            st.success(f"ประมวลผลและบันทึกข้อมูลจากไฟล์ '{file_name_stmt}' (Batch ID '{import_batch_id_stmt}') เสร็จสิ้นสมบูรณ์!")
                                        else:
                                            final_status_stmt = "Failed_PartialSave"
                                            st.error(f"การประมวลผลไฟล์ '{file_name_stmt}' (Batch ID '{import_batch_id_stmt}') มีบางส่วนล้มเหลว โปรดตรวจสอบข้อความและ Log")

                                except UnicodeDecodeError as e_decode_stmt:
                                    st.error(f"เกิดข้อผิดพลาดในการ Decode ไฟล์: {e_decode_stmt}. กรุณาตรวจสอบ Encoding (ควรเป็น UTF-8).")
                                    final_status_stmt = "Failed_UnicodeDecode"; processing_notes_stmt.append(f"UnicodeDecodeError: {e_decode_stmt}")
                                except Exception as e_main_proc_stmt:
                                    st.error(f"เกิดข้อผิดพลาดระหว่างประมวลผลหลัก: {type(e_main_proc_stmt).__name__} - {str(e_main_proc_stmt)[:200]}...")
                                    final_status_stmt = f"Failed_MainProcessing_{type(e_main_proc_stmt).__name__}"; processing_notes_stmt.append(f"MainError: {type(e_main_proc_stmt).__name__}")

                                try:
                                    # Fetch history again after append to find row_count accurately
                                    hist_rows_update_stmt = ws_upload_history.get_all_values()
                                    row_idx_to_update_stmt = None
                                    for r_idx, r_val in reversed(list(enumerate(hist_rows_update_stmt))):
                                        if len(r_val) > 7 and r_val[7] == import_batch_id_stmt:
                                            row_idx_to_update_stmt = r_idx + 1; break
                                    if row_idx_to_update_stmt:
                                        notes_str_stmt = " | ".join(filter(None, processing_notes_stmt))[:49999]
                                        ws_upload_history.batch_update([
                                            {'range': f'G{row_idx_to_update_stmt}', 'values': [[final_status_stmt]]},
                                            {'range': f'I{row_idx_to_update_stmt}', 'values': [[notes_str_stmt]]}
                                        ])
                                        print(f"Info: Updated UploadHistory for ImportBatchID '{import_batch_id_stmt}' to '{final_status_stmt}'.")
                                except Exception as e_update_hist_final_stmt:
                                    print(f"Warning: Could not update final status in {settings.WORKSHEET_UPLOAD_HISTORY} for batch {import_batch_id_stmt}: {e_update_hist_final_stmt}")

        # Logic to reset the uploader and rerun to clear the uploaded file display
        if uploaded_file_statement is not None and st.session_state.get(_UPLOAD_PROCESSED_IN_THIS_CYCLE, False):
            st.session_state.uploader_key_version += 1
            if _trigger_rerun_after_upload_handling:
                st.rerun()
        elif uploaded_file_statement is None and st.session_state.get(_UPLOAD_PROCESSED_IN_THIS_CYCLE, False):
            st.session_state[_UPLOAD_PROCESSED_IN_THIS_CYCLE] = False

    st.markdown("---")