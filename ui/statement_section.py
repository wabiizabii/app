# ui/statement_section.py (ฉบับแก้ไขสำหรับ Multi-User - สมบูรณ์)

import streamlit as st
import pandas as pd
from core import statement_processor, supabase_handler as db_handler
from config import settings
import hashlib
import json # for pretty printing dict
from datetime import datetime
import uuid # Import uuid for batch id

def render_statement_section(user_id: str, df_portfolios_gs: pd.DataFrame): # <<< แก้ไข: เพิ่ม user_id
    """
    Renders the statement uploader section.
    (แก้ไขให้รับ user_id เพื่อใช้ในการบันทึกและตรวจสอบข้อมูล)
    """
    st.markdown("---")
    st.subheader("⬆️ อัปโหลด Trading Statement Report (CSV)")

    active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
    active_portfolio_name = st.session_state.get('active_portfolio_name_gs')

    if not active_portfolio_id:
        st.warning("⚠️ กรุณาเลือก Portfolio จาก Sidebar ก่อน")
        st.file_uploader("เลือกไฟล์ CSV Statement", type="csv", key=f"statement_uploader_{st.session_state.get('uploader_key', 0)}", disabled=True)
        return

    st.info(f"คุณกำลังทำงานกับ Portfolio: **{active_portfolio_name}** (ID: {active_portfolio_id})")
    
    uploaded_file = st.file_uploader("เลือกไฟล์ CSV Statement", type="csv", key=f"statement_uploader_{st.session_state.get('uploader_key', 0)}")

    allow_update_checkbox = st.checkbox("✅ ต้องการอัปเดตข้อมูล Statement ด้วยไฟล์นี้", value=False, help="เลือกช่องนี้หากคุณต้องการประมวลผลไฟล์ที่มีเนื้อหาซ้ำกับที่เคยอัปโหลดไปแล้วสำหรับ Portfolio นี้")

    # Initialize session state variables if they don't exist
    if 'uploaded_file_content_bytes' not in st.session_state: st.session_state.uploaded_file_content_bytes = None
    if 'current_file_hash' not in st.session_state: st.session_state.current_file_hash = None
    if 'file_account_id' not in st.session_state: st.session_state.file_account_id = None
    if 'is_duplicate_file_content' not in st.session_state: st.session_state.is_duplicate_file_content = False
    if 'extracted_data' not in st.session_state: st.session_state.extracted_data = None
    if 'analysis_results' not in st.session_state: st.session_state.analysis_results = None
    if 'show_confirm_save_button' not in st.session_state: st.session_state.show_confirm_save_button = False
    
    process_file_now = False
    duplicate_message = "" 

    if uploaded_file is not None:
        new_file_content_bytes = uploaded_file.getvalue()
        new_file_hash = hashlib.sha256(new_file_content_bytes).hexdigest()

        if new_file_hash != st.session_state.get('current_file_hash'):
            st.session_state.uploaded_file_content_bytes = new_file_content_bytes
            st.session_state.current_file_hash = new_file_hash
            
            for key in ['extracted_data', 'analysis_results', 'show_confirm_save_button', 'file_account_id', 'is_duplicate_file_content']:
                if key in st.session_state:
                    st.session_state[key] = None

            st.info(f"ไฟล์ที่อัปโหลด: {uploaded_file.name} (ขนาด: {len(st.session_state.uploaded_file_content_bytes)} bytes)")

            # --- แก้ไข: ส่ง user_id ไปตรวจสอบไฟล์ซ้ำ ---
            st.session_state.is_duplicate_file_content, duplicate_message = db_handler.check_duplicate_file(user_id, st.session_state.current_file_hash, active_portfolio_id)
            
            if st.session_state.is_duplicate_file_content and not allow_update_checkbox:
                st.warning(f"⚠️ {duplicate_message}")
                st.info("โปรดติ๊ก '✅ ต้องการอัปเดตข้อมูล Statement ด้วยไฟล์นี้' หากคุณต้องการประมวลผลไฟล์นี้ซ้ำ")
            else:
                process_file_now = True
    
    if process_file_now:
        with st.spinner("กำลังสกัดข้อมูลจากไฟล์..."):
            try:
                st.session_state.extracted_data = statement_processor.extract_data_from_report_content(st.session_state.uploaded_file_content_bytes)
                st.session_state.file_account_id = st.session_state.extracted_data.get('portfolio_details', {}).get('account_id')
                if not st.session_state.file_account_id:
                    st.error("❌ ไม่สามารถดึง Account ID จากไฟล์ Statement ได้ กรุณาตรวจสอบรูปแบบไฟล์")
                    st.session_state.extracted_data = None
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
                st.session_state.extracted_data = None

    if st.session_state.get('extracted_data') and st.session_state.get('file_account_id'):
        st.markdown("---")
        st.subheader("📊 ขั้นตอนที่ 2: ข้อมูลที่สกัดได้")
        
        extracted = st.session_state.get('extracted_data', {})
        deals_df = extracted.get('deals', pd.DataFrame())
        orders_df = extracted.get('orders', pd.DataFrame())
        positions_df = extracted.get('positions', pd.DataFrame())
        dw_df = extracted.get('deposit_withdrawal_logs', pd.DataFrame())

        st.markdown("##### ภาพรวมรายการที่พบในไฟล์")
        col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
        col_c1.metric("Deals Found", f"{len(deals_df)}")
        col_c2.metric("Orders Found", f"{len(orders_df)}")
        col_c3.metric("Positions Found", f"{len(positions_df)}")
        deposits_count = len(dw_df[dw_df['Type'] == 'Deposit']) if not dw_df.empty and 'Type' in dw_df.columns else 0
        withdrawals_count = len(dw_df[dw_df['Type'] == 'Withdrawal']) if not dw_df.empty and 'Type' in dw_df.columns else 0
        col_c4.metric("Deposits", f"{deposits_count}")
        col_c5.metric("Withdrawals", f"{withdrawals_count}")
        st.markdown("---")

        if st.session_state.get('analysis_results') is None:
            # --- แก้ไข: ส่ง user_id ไปตรวจสอบความเชื่อมโยงของบัญชี ---
            if not db_handler.check_portfolio_account_id_link(user_id, st.session_state.file_account_id, active_portfolio_id):
                st.error(f"❌ เลขบัญชี '{st.session_state.file_account_id}' ในไฟล์นี้เคยถูกใช้กับ Portfolio อื่น หรือ Portfolio '{active_portfolio_name}' เคยถูกใช้กับเลขบัญชีอื่น โปรดตรวจสอบความถูกต้อง")
                st.session_state.extracted_data = None
                return

            with st.spinner("กำลังวิเคราะห์การเปลี่ยนแปลงข้อมูล..."):
                # --- แก้ไข: ส่ง user_id ไปวิเคราะห์การเปลี่ยนแปลง ---
                analysis_results = db_handler.analyze_statement_changes(user_id, st.session_state['extracted_data'], active_portfolio_id)
            
            st.session_state.analysis_results = analysis_results
            st.session_state.show_confirm_save_button = True

    if st.session_state.get('show_confirm_save_button') and st.session_state.get('analysis_results'):
        st.markdown("---")
        st.subheader("✅ ขั้นตอนที่ 3: ยืนยันการบันทึกข้อมูล")
        
        analysis_results = st.session_state['analysis_results']
        st.write(f"**ภาพรวม:** เพิ่มรายการใหม่รวม: **{analysis_results.get('overall_new_count', 0)}** รายการ | อัปเดตรายการเดิมรวม: **{analysis_results.get('overall_updated_count', 0)}** รายการ")

        col_save, col_cancel = st.columns([1,1])
        with col_save:
            if st.button("✅ ยืนยันการบันทึกข้อมูล Statement", key="confirm_final_save_btn", type="primary", use_container_width=True):
                with st.spinner("กำลังบันทึกข้อมูล... โปรดรอสักครู่"):
                    data_to_save = {}
                    import_batch_id = f"BATCH-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
                    
                    # --- ส่วนเตรียม data_to_save ที่สมบูรณ์ ---
                    for key in ['deals', 'orders', 'positions', 'deposit_withdrawal_logs']:
                        df_key_name = settings.WORKSHEET_HEADERS_MAPPER.get(key)
                        if not df_key_name: continue
                        
                        df = st.session_state['extracted_data'].get(key, pd.DataFrame())
                        if not df.empty:
                            df_copy = df.copy()
                            df_copy['PortfolioID'] = str(active_portfolio_id)
                            df_copy['PortfolioName'] = active_portfolio_name
                            df_copy['SourceFile'] = uploaded_file.name if uploaded_file else "N/A"
                            df_copy['ImportBatchID'] = import_batch_id
                            data_to_save[df_key_name] = df_copy
                        else:
                            data_to_save[df_key_name] = pd.DataFrame(columns=settings.WORKSHEET_HEADERS[df_key_name])

                    final_summary_data = st.session_state['extracted_data'].get('final_summary_data', {})
                    if final_summary_data:
                        final_summary_data['PortfolioID'] = str(active_portfolio_id)
                        final_summary_data['PortfolioName'] = active_portfolio_name
                        final_summary_data['SourceFile'] = uploaded_file.name if uploaded_file else "N/A"
                        final_summary_data['ImportBatchID'] = import_batch_id
                        final_summary_data['Timestamp'] = datetime.now().isoformat()
                        data_to_save[settings.SUPABASE_TABLE_STATEMENT_SUMMARIES] = final_summary_data
                    
                    upload_history_data = {
                        "UploadTimestamp": datetime.now().isoformat(),
                        "PortfolioID": str(active_portfolio_id),
                        "PortfolioName": active_portfolio_name,
                        "FileName": uploaded_file.name if uploaded_file else "N/A",
                        "FileSize": len(st.session_state.uploaded_file_content_bytes) if st.session_state.uploaded_file_content_bytes else 0,
                        "FileHash": st.session_state.current_file_hash,
                        "Status": "Success", # Will be updated to Failed on error
                        "ImportBatchID": import_batch_id,
                        "Notes": "Uploaded via Streamlit app",
                        "FileAccountID": st.session_state.file_account_id
                    }
                    data_to_save[settings.SUPABASE_TABLE_UPLOAD_HISTORY] = upload_history_data
                    # --- สิ้นสุดส่วนเตรียม data_to_save ---

                    # --- แก้ไข: ส่ง user_id ตอนบันทึกข้อมูล Statement ---
                    success, message = db_handler.save_statement_data(
                        user_id=user_id,
                        data_map=data_to_save,
                        file_account_id=st.session_state.file_account_id,
                        uploaded_file_name=uploaded_file.name if uploaded_file else "N/A",
                        file_hash=st.session_state.current_file_hash
                    )

                    if success:
                        st.success("บันทึกข้อมูลสำเร็จ!")
                        st.balloons()
                        # Reset state after successful save
                        for key in ['extracted_data', 'analysis_results', 'show_confirm_save_button', 'uploaded_file_content_bytes', 'current_file_hash', 'file_account_id', 'is_duplicate_file_content']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.session_state.uploader_key += 1
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        with col_cancel:
            if st.button("ยกเลิก", key="cancel_save_btn", use_container_width=True):
                # Reset state on cancel
                for key in ['extracted_data', 'analysis_results', 'show_confirm_save_button', 'uploaded_file_content_bytes', 'current_file_hash', 'file_account_id', 'is_duplicate_file_content']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.uploader_key += 1
                st.info("ยกเลิกการบันทึกข้อมูล")
                st.rerun()

    if st.session_state.get('extracted_data'):
        st.markdown("---")
        st.subheader("🔍 Raw Extracted Data (สำหรับ Debugging)")
        # (โค้ดส่วนแสดง Raw Data เหมือนเดิม)
        if st.checkbox("แสดงข้อมูลดิบที่สกัดได้ (สำหรับ Debug)"):
            extracted = st.session_state['extracted_data']
            for key, value in extracted.items():
                if isinstance(value, pd.DataFrame) and not value.empty:
                    st.write(f"### {key.replace('_', ' ').title()}")
                    st.dataframe(value)
                elif isinstance(value, dict) and value:
                    st.write(f"### {key.replace('_', ' ').title()}")
                    st.json(value)
