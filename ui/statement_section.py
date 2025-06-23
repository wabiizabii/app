# ui/statement_section.py (เวอร์ชันสมบูรณ์ที่สุด)

import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
import uuid
import traceback

from config import settings
from core import gs_handler, statement_processor, analytics_engine

def render_statement_section():
    with st.expander("📂 Ultimate Chart Dashboard Import & Processing", expanded=False):
        st.markdown("### 📊 จัดการ Statement และข้อมูลดิบ")
        st.subheader("📤 ขั้นตอนที่ 1: อัปโหลด Statement Report (CSV)")

        if 'uploader_key' not in st.session_state:
            st.session_state.uploader_key = 0
        
        uploaded_file = st.file_uploader(
            "ลากและวางไฟล์ Statement Report (CSV) ที่นี่",
            type=["csv"],
            key=f"statement_uploader_{st.session_state.uploader_key}"
        )

        if uploaded_file:
            if st.session_state.get('processed_filename') != uploaded_file.name:
                st.session_state['extracted_data'] = None

            try:
                st.session_state['extracted_data'] = statement_processor.extract_data_from_report_content(uploaded_file.getvalue())
                st.session_state['processed_filename'] = uploaded_file.name
                file_content_bytes = uploaded_file.getvalue()
                st.session_state['file_info_to_save'] = {
                    "name": uploaded_file.name, 
                    "size": uploaded_file.size, 
                    "content_bytes": file_content_bytes,
                    "hash": hashlib.md5(file_content_bytes).hexdigest()
                }
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการอ่านและตรวจสอบไฟล์: {e}")
                st.session_state['extracted_data'] = None

        if st.session_state.get('extracted_data'):
            st.subheader("📊 ขั้นตอนที่ 2: ผลการวิเคราะห์ไฟล์ (ยังไม่บันทึก)")

            extracted = st.session_state.get('extracted_data', {})
            deals_df = extracted.get('deals', pd.DataFrame())
            orders_df = extracted.get('orders', pd.DataFrame())
            positions_df = extracted.get('positions', pd.DataFrame())
            balance_summary = extracted.get('balance_summary', {})
            results_summary = extracted.get('results_summary', {})

            if deals_df.empty:
                st.error("ไม่สามารถดึงข้อมูล 'Deals' จากไฟล์ได้ กรุณาตรวจสอบรูปแบบไฟล์")
                return

            st.success(f"✅ วิเคราะห์ไฟล์สำเร็จ!")
            
            deposit_deals_df = deals_df[deals_df['Comment_Deal'].str.lower().str.contains('deposit', na=False)] if 'Comment_Deal' in deals_df.columns else pd.DataFrame()
            withdrawal_deals_df = deals_df[deals_df['Comment_Deal'].str.lower().str.contains('withdraw', na=False)] if 'Comment_Deal' in deals_df.columns else pd.DataFrame()

            st.markdown("##### ภาพรวมรายการที่พบ")
            count_cols = st.columns(5)
            count_cols[0].metric("Deals ที่พบ", f"{len(deals_df)} รายการ")
            count_cols[1].metric("Orders ที่พบ", f"{len(orders_df)} รายการ")
            count_cols[2].metric("Positions ที่พบ", f"{len(positions_df)} รายการ")
            count_cols[3].metric("Deposit ที่พบ", f"{len(deposit_deals_df)} รายการ")
            count_cols[4].metric("Withdrawal ที่พบ", f"{len(withdrawal_deals_df)} รายการ")
            
            st.markdown("---")

            st.markdown("##### สรุปข้อมูลการเงิน (Financial Summary)")
            sum_cols = st.columns(5)
            sum_cols[0].metric("Equity", f"${balance_summary.get('equity', 0.0):,.2f}")
            sum_cols[1].metric("Balance", f"${balance_summary.get('balance', 0.0):,.2f}")
            sum_cols[2].metric("Profit", f"${results_summary.get('Total_Net_Profit', 0.0):,.2f}", delta=f"{results_summary.get('Total_Net_Profit', 0.0):,.2f}")
            sum_cols[3].metric("Deposit", f"${balance_summary.get('deposit', 0.0):,.2f}")
            sum_cols[4].metric("Withdrawal", f"${balance_summary.get('withdrawal', 0.0):,.2f}")

            st.info("กรุณาตรวจสอบข้อมูล หากถูกต้องให้กดยืนยันเพื่อบันทึก")

            st.markdown("---")
            st.subheader("💾 ขั้นตอนที่ 3: ยืนยันการบันทึกข้อมูล")
            if st.button("✅ ยืนยันการบันทึกข้อมูล (Confirm & Save)"):
                try:
                    active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
                    active_portfolio_name = st.session_state.get('active_portfolio_name_gs')
                    file_info = st.session_state.get('file_info_to_save', {})
                    import_batch_id = str(uuid.uuid4())
                    has_errors = False

                    if not active_portfolio_id:
                        st.error("กรุณาเลือกพอร์ตก่อนบันทึก")
                        st.stop()
                    
                    with st.spinner("กำลังตรวจสอบชีตและบันทึกข้อมูลทั้งหมด..."):
                        gc = gs_handler.get_gspread_client()
                        if not gc:
                            st.error("ไม่สามารถเชื่อมต่อกับ Google Client ได้")
                            st.stop()

                        ws_dict, setup_error = gs_handler.setup_and_get_worksheets(gc)
                        if setup_error:
                            st.error(f"เกิดข้อผิดพลาดในการตั้งค่าชีต: {setup_error}")
                            st.stop()
                        
                        ok_d, _, _ = gs_handler.save_deals_to_actual_trades(ws_dict.get(settings.WORKSHEET_ACTUAL_TRADES), deals_df, active_portfolio_id, active_portfolio_name, file_info.get('name'), import_batch_id)
                        ok_o, _, _ = gs_handler.save_orders_to_actul_orders(ws_dict.get(settings.WORKSHEET_ACTUAL_ORDERS), orders_df, active_portfolio_id, active_portfolio_name, file_info.get('name'), import_batch_id)
                        ok_p, _, _ = gs_handler.save_positions_to_actul_positions(ws_dict.get(settings.WORKSHEET_ACTUAL_POSITIONS), positions_df, active_portfolio_id, active_portfolio_name, file_info.get('name'), import_batch_id)
                        ok_s, _ = gs_handler.save_results_summary_to_gsheets(ws_dict.get(settings.WORKSHEET_STATEMENT_SUMMARIES), balance_summary, results_summary, active_portfolio_id, active_portfolio_name, file_info.get('name'), import_batch_id)
                        
                        if not all([ok_d, ok_o, ok_p, ok_s]): has_errors = True

                        history_log = {
                            "UploadTimestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "PortfolioID": active_portfolio_id, 
                            "PortfolioName": active_portfolio_name, "FileName": file_info.get('name'), 
                            "FileSize": file_info.get('size'), "FileHash": file_info.get('hash'),
                            "Status": "Success" if not has_errors else "Failed", "ImportBatchID": import_batch_id, "Notes": ""
                        }
                        gs_handler.save_upload_history(ws_dict.get(settings.WORKSHEET_UPLOAD_HISTORY), history_log)
                    st.success("บันทึกข้อมูลพื้นฐานทั้งหมดเรียบร้อยแล้ว!")

                    with st.spinner("กำลังคำนวณและอัปเดต Dashboard..."):
                        gs_handler.load_actual_trades_from_gsheets.clear()
                        gs_handler.load_statement_summaries_from_gsheets.clear()
                        gs_handler.load_portfolios_from_gsheets.clear()
                        all_trades_df = gs_handler.load_actual_trades_from_gsheets()
                        all_summaries_df = gs_handler.load_statement_summaries_from_gsheets()
                        all_portfolios_df = gs_handler.load_portfolios_from_gsheets()
                        
                        latest_stats = analytics_engine.get_full_dashboard_stats(all_trades_df, all_summaries_df, active_portfolio_id)
                        portfolio_details = all_portfolios_df[all_portfolios_df['PortfolioID'] == active_portfolio_id].iloc[0].to_dict() if not all_portfolios_df[all_portfolios_df['PortfolioID'] == active_portfolio_id].empty else {}
                        
                        dashboard_payload = {
                            "PortfolioID": active_portfolio_id, "PortfolioName": active_portfolio_name,
                            "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "ProgramType": portfolio_details.get("ProgramType", ""), "Status": portfolio_details.get("Status", ""),
                            "CurrentBalance": latest_stats.get('total_net_profit', 0) + float(portfolio_details.get("InitialBalance", 0)),
                            "TotalNetProfit": latest_stats.get('total_net_profit', 0),
                            "TotalDeposits": all_summaries_df[all_summaries_df['PortfolioID'] == active_portfolio_id]['Deposit'].sum(),
                            "TotalWithdrawals": all_summaries_df[all_summaries_df['PortfolioID'] == active_portfolio_id]['Withdrawal'].sum(),
                        }
                        
                        if gs_handler.update_dashboard_sheet(active_portfolio_id, dashboard_payload):
                            st.success("อัปเดต Dashboard สำเร็จ!")
                        else:
                            st.error("เกิดข้อผิดพลาดในการอัปเดต Dashboard")

                    st.balloons()
                    st.success("กระบวนการทั้งหมดเสร็จสมบูรณ์!")
                    
                    st.session_state['extracted_data'] = None
                    st.session_state.uploader_key += 1
                    st.rerun()

                except Exception as e:
                    st.error("เกิดข้อผิดพลาดร้ายแรงระหว่างการบันทึกข้อมูล")
                    st.exception(e)