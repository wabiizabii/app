# ui/statement_section.py
# เวอร์ชันสมบูรณ์แบบ: รวมการแสดงผลที่ละเอียด, การบันทึกที่สมบูรณ์, และการตรวจสอบที่ชัดเจน

import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
import uuid
import traceback

from config import settings
from core import gs_handler, statement_processor


def render_statement_section(df_portfolios_gs: pd.DataFrame):
    """
    ฟังก์ชันสำหรับแสดงผลหน้า "Import Statement" ทั้งหมด
    ตั้งแต่การอัปโหลด, การแสดงผลการวิเคราะห์, และการบันทึกข้อมูล
    """
    with st.expander("📂 Import & Processing", expanded=True):
        st.markdown("### 📊 จัดการ Statement และข้อมูลดิบ")
        st.markdown("---")

        # --- ส่วนที่ 1: อัปโหลดไฟล์ ---
        st.subheader("📤 ขั้นตอนที่ 1: อัปโหลด Statement Report (CSV)")

        if 'uploader_key' not in st.session_state:
            st.session_state.uploader_key = 0
        
        uploaded_file = st.file_uploader(
            "ลากและวางไฟล์ Statement Report (CSV) ที่นี่",
            type=["csv"],
            key=f"statement_uploader_{st.session_state.uploader_key}"
        )

        # --- ส่วนที่ 2: ประมวลผลไฟล์ที่อัปโหลด ---
        if uploaded_file:
            if st.session_state.get('processed_filename') != uploaded_file.name:
                st.session_state['extracted_data'] = None
                st.session_state['processed_filename'] = uploaded_file.name

            active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
            if not active_portfolio_id:
                st.warning("⚠️ กรุณาเลือกพอร์ตที่ Sidebar ก่อนทำการอัปโหลดไฟล์")
                st.stop()

            if st.session_state.get('extracted_data') is None:
                with st.spinner(f"กำลังวิเคราะห์ไฟล์ '{uploaded_file.name}'..."):
                    try:
                        file_content_bytes = uploaded_file.getvalue()
                        
                        st.session_state['file_info_to_save'] = {
                            "name": uploaded_file.name,
                            "hash": hashlib.md5(file_content_bytes).hexdigest(),
                            "content_bytes": file_content_bytes
                        }
                        
                        st.session_state['extracted_data'] = statement_processor.extract_data_from_report_content(file_content_bytes)
                        st.success("ไฟล์ถูกวิเคราะห์เรียบร้อย!")

                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
                        traceback.print_exc()
                        st.session_state['extracted_data'] = None

        # --- ส่วนที่ 3: แสดงผลลัพธ์การวิเคราะห์ (แบบละเอียด) ---
        if st.session_state.get('extracted_data'):
            st.markdown("---")
            st.subheader("📊 ขั้นตอนที่ 2: ผลการวิเคราะห์ไฟล์ (ยังไม่บันทึก)")

            extracted = st.session_state.get('extracted_data', {})
            deals_df = extracted.get('deals', pd.DataFrame())
            orders_df = extracted.get('orders', pd.DataFrame())
            positions_df = extracted.get('positions', pd.DataFrame())
            portfolio_details = extracted.get('portfolio_details', {})
            deposit_withdrawal_logs = extracted.get('deposit_withdrawal_logs', [])
            final_summary_data = extracted.get('final_summary_data', {})

            if deals_df.empty:
                st.error("ไม่สามารถดึงข้อมูล 'Deals' จากไฟล์ได้ กรุณาตรวจสอบรูปแบบไฟล์")
                return

            st.success(f"✅ วิเคราะห์ไฟล์สำเร็จ! รายงาน: **{st.session_state['file_info_to_save']['name']}**")
            
            st.markdown("##### ภาพรวมรายการที่พบ")
            col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
            col_c1.metric("Deals ที่พบ", f"{len(deals_df)} รายการ")
            col_c2.metric("Orders ที่พบ", f"{len(orders_df)} รายการ")
            col_c3.metric("Positions ที่พบ", f"{len(positions_df)} รายการ")
            col_c4.metric("Deposit ย่อย", f"{len([d for d in deposit_withdrawal_logs if d['Type'] == 'Deposit'])} รายการ")
            col_c5.metric("Withdrawal ย่อย", f"{len([d for d in deposit_withdrawal_logs if d['Type'] == 'Withdrawal'])} รายการ")
            st.markdown("---")

            st.markdown("##### สรุปข้อมูลการเงินและผลประกอบการ (Financial & Performance Summary)")
            
            # ### แก้ไข: ปรับปรุงการแสดงผลส่วนนี้ให้สวยงามขึ้น ###
            st.markdown("###### ยอดเงินและมาร์จิ้น (Balance & Margin)")
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            b_col1.metric("Balance", f"${final_summary_data.get('Balance', 0.0):,.2f}")
            b_col2.metric("Equity", f"${final_summary_data.get('Equity', 0.0):,.2f}")
            b_col3.metric("Floating P/L", f"${final_summary_data.get('Floating_P_L', 0.0):,.2f}")
            b_col4.metric("Credit Facility", f"${final_summary_data.get('Credit_Facility', 0.0):,.2f}")
            
            st.markdown("###### สรุปกำไร/ขาดทุน และยอดฝาก/ถอน")
            pnl_cols = st.columns(4)
            pnl_cols[0].metric("Net Profit (รวม)", f"${final_summary_data.get('Total_Net_Profit', 0.0):,.2f}", delta=f"{final_summary_data.get('Total_Net_Profit', 0.0):.2f}")
            pnl_cols[1].metric("Gross Profit", f"${final_summary_data.get('Gross_Profit', 0.0):,.2f}")
            pnl_cols[2].metric("Gross Loss", f"${final_summary_data.get('Gross_Loss', 0.0):,.2f}")
            pnl_cols[3].metric("Deposit/Withdrawal", f"${final_summary_data.get('Deposit', 0.0) + final_summary_data.get('Withdrawal', 0.0):,.2f}")

            st.markdown("---")
            
            # ### แก้ไข: ลบโค้ดแสดงผลสถิติแบบเดิมทิ้งทั้งหมด แล้วแทนที่ด้วยโค้ดใหม่นี้ ###
            st.subheader("สถิติผลงานเชิงลึก")
            
            # สร้าง Layout 3 คอลัมน์ตามที่คุณต้องการ
            col1, col2, col3 = st.columns(3)

            # --- คอลัมน์ที่ 1: กลุ่มสถิติการเทรด ---
            with col1:
                st.markdown("##### กลุ่มสถิติการเทรด")
                st.metric(label="Total Trades", value=f"{int(final_summary_data.get('Total_Trades', 0))}")
                
                profit_trades_count = int(final_summary_data.get('Profit_Trades_Count', 0))
                profit_trades_percent = final_summary_data.get('Profit_Trades_Percent', 0)
                st.metric(label="Profit Trades (% of total)", value=f"{profit_trades_count} ({profit_trades_percent:.2f}%)")
                
                loss_trades_count = int(final_summary_data.get('Loss_Trades_Count', 0))
                loss_trades_percent = final_summary_data.get('Loss_Trades_Percent', 0)
                st.metric(label="Loss Trades (% of total)", value=f"{loss_trades_count} ({loss_trades_percent:.2f}%)")
                
                short_trades_count = int(final_summary_data.get('Short_Trades_Count', 0))
                short_trades_won_percent = final_summary_data.get('Short_Trades_Won_Percent', 0)
                st.metric(label="Short Trades (won %)", value=f"{short_trades_count} ({short_trades_won_percent:.2f}%)")
                
                long_trades_count = int(final_summary_data.get('Long_Trades_Count', 0))
                long_trades_won_percent = final_summary_data.get('Long_Trades_Won_Percent', 0)
                st.metric(label="Long Trades (won %)", value=f"{long_trades_count} ({long_trades_won_percent:.2f}%)")

            # --- คอลัมน์ที่ 2: กลุ่มกำไร/ขาดทุน และสถิติเชิงคุณภาพ ---
            with col2:
                st.markdown("##### กลุ่มกำไร/ขาดทุน")
                st.metric(label="Largest profit trade", value=f"${final_summary_data.get('Largest_Profit_Trade', 0):,.2f}")
                st.metric(label="Largest loss trade", value=f"${final_summary_data.get('Largest_Loss_Trade', 0):,.2f}")
                st.metric(label="Average profit trade", value=f"${final_summary_data.get('Average_Profit_Trade', 0):,.2f}")
                st.metric(label="Average loss trade", value=f"${final_summary_data.get('Average_Loss_Trade', 0):,.2f}")

                st.markdown("##### กลุ่มสถิติเชิงคุณภาพ")
                st.metric(label="Average consecutive wins", value=f"{int(final_summary_data.get('Average_Consecutive_Wins', 0))}")
                st.metric(label="Average consecutive losses", value=f"{int(final_summary_data.get('Average_Consecutive_Losses', 0))}")


            # --- คอลัมน์ที่ 3: กลุ่มสถิติขั้นสูง และ Drawdown ---
            with col3:
                st.markdown("##### กลุ่มสถิติขั้นสูง")
                st.metric(label="Profit Factor", value=f"{final_summary_data.get('Profit_Factor', 0):.2f}")
                st.metric(label="Expected Payoff", value=f"${final_summary_data.get('Expected_Payoff', 0):,.2f}")
                st.metric(label="Recovery Factor", value=f"{final_summary_data.get('Recovery_Factor', 0):.2f}")
                st.metric(label="Sharpe Ratio", value=f"{final_summary_data.get('Sharpe_Ratio', 0):.2f}")
                
                st.markdown("##### กลุ่ม Drawdown")
                st.metric(label="Maximal Drawdown", value=f"${final_summary_data.get('Maximal_Drawdown_Value', 0):,.2f} ({final_summary_data.get('Maximal_Drawdown_Percent', 0):.2f}%)")
                st.metric(label="Balance Drawdown Absolute", value=f"${final_summary_data.get('Balance_Drawdown_Absolute', 0):,.2f}")


            st.markdown("---")
            st.markdown("##### รายละเอียดพอร์ต (จากรายงาน)")
            detail_cols = st.columns(3)
            account_id_from_report = portfolio_details.get('account_id', 'N/A')
            account_name_from_report = portfolio_details.get('account_name', 'N/A')
            client_name_from_report = portfolio_details.get('client_name', 'N/A')

            detail_cols[0].info(f"**Account ID:** {account_id_from_report}")
            detail_cols[1].info(f"**Account Name:** {account_name_from_report}")
            detail_cols[2].info(f"**Client Name:** {client_name_from_report}")
            
            st.info(f"**Credit (จากรายงาน):** ${final_summary_data.get('Credit_Facility', 0.0):,.2f}")


            st.markdown("---")
            st.warning("กรุณาตรวจสอบข้อมูลทั้งหมด หากถูกต้องให้กดยืนยันเพื่อบันทึก")

            # --- ส่วนที่ 4: ปุ่มยืนยันการบันทึก (เวอร์ชันสมบูรณ์) ---
            st.subheader("💾 ขั้นตอนที่ 3: ยืนยันการบันทึกข้อมูล")
            if st.button("✅ ยืนยันการบันทึกข้อมูล (Confirm & Save)"):
                with st.spinner("กำลังเตรียมการและตรวจสอบข้อมูล..."):
                    try:
                        # --- ดึงข้อมูลที่จำเป็นจาก Session State ---
                        extracted = st.session_state['extracted_data']
                        file_info = st.session_state['file_info_to_save']
                        active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
                        active_portfolio_name = st.session_state.get('active_portfolio_name_gs')
                        portfolio_details = extracted.get('portfolio_details', {})
                        account_id_from_report = portfolio_details.get('account_id', 'N/A')
                        
                        # --- Setup Google Sheets ---
                        gc = gs_handler.get_gspread_client()
                        if not gc:
                            st.error("ไม่สามารถเชื่อมต่อ Google Client ได้")
                            st.stop()
                        ws_dict, setup_error = gs_handler.setup_and_get_worksheets(gc)
                        if setup_error:
                            st.error(f"Setup GSheet Error: {setup_error}")
                            st.stop()
                        
                        final_portfolio_id_for_save = account_id_from_report if account_id_from_report not in ['N/A', '', None] else active_portfolio_id
                        portfolio_name_to_save = portfolio_details.get('account_name', active_portfolio_name)

                        st.info("ตรวจสอบข้อมูลเบื้องต้น...")

                        final_portfolio_id_for_save = active_portfolio_id
                        portfolio_name_to_save = active_portfolio_name

                        # แสดงผลเพื่อยืนยันว่าโปรแกรมกำลังจะบันทึกข้อมูลลงพอร์ตที่ถูกต้อง
                        st.info(f"กำลังจะบันทึกข้อมูลทั้งหมดภายใต้พอร์ต: '{portfolio_name_to_save}' (ID: {final_portfolio_id_for_save})")

                        # ด่านตรวจสอบเดียวที่ยังคงไว้ คือเช็คว่า "เนื้อหา" ของไฟล์ซ้ำกับที่เคยอัปโหลดไปแล้วหรือไม่
                        is_duplicate, details = gs_handler.is_file_already_uploaded(file_info['hash'], final_portfolio_id_for_save, gc)
                        if is_duplicate:
                            st.error(f"❌ ไฟล์ซ้ำ: เนื้อหาของไฟล์นี้เคยถูกอัปโหลดแล้วสำหรับพอร์ต '{details.get('PortfolioName', 'N/A')}'")
                            st.info("โปรดใช้ไฟล์ใหม่ หรือลบประวัติในชีต UploadHistory")
                            st.stop()

                        st.success("✅ ผ่านการตรวจสอบไฟล์ซ้ำ! เริ่มบันทึกข้อมูล...")
                        # --- เริ่มกระบวนการบันทึกข้อมูลจริง ---
                        has_errors = False
                        import_batch_id = str(uuid.uuid4())
                        
                        deals_df = extracted.get('deals', pd.DataFrame())
                        orders_df = extracted.get('orders', pd.DataFrame())
                        positions_df = extracted.get('positions', pd.DataFrame())
                        deposit_withdrawal_logs = extracted.get('deposit_withdrawal_logs', [])
                        final_summary_data = extracted.get('final_summary_data', {})
                        
                        # --- บันทึก Deals ---
                        st.write("--- กำลังบันทึก Deals ---")
                        ok_d, msg_d, num_d, skip_d = gs_handler.save_deals_to_actual_trades(
                            ws_dict.get(settings.WORKSHEET_ACTUAL_TRADES), deals_df,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_d: has_errors = True; st.error(f"Deals Error: {msg_d}")
                        else: st.write(f"Deals: บันทึกใหม่ {num_d}, ข้าม {skip_d} รายการ.")

                        # --- บันทึก Orders ---
                        st.write("--- กำลังบันทึก Orders ---")
                        ok_o, msg_o, num_o, skip_o = gs_handler.save_orders_to_actul_orders(
                            ws_dict.get(settings.WORKSHEET_ACTUAL_ORDERS), orders_df,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_o: has_errors = True; st.error(f"Orders Error: {msg_o}")
                        else: st.write(f"Orders: บันทึกใหม่ {num_o}, ข้าม {skip_o} รายการ.")

                        # --- บันทึก Positions ---
                        st.write("--- กำลังบันทึก Positions ---")
                        ok_p, msg_p, num_p, skip_p = gs_handler.save_positions_to_actul_positions(
                            ws_dict.get(settings.WORKSHEET_ACTUAL_POSITIONS), positions_df,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_p: has_errors = True; st.error(f"Positions Error: {msg_p}")
                        else: st.write(f"Positions: บันทึกใหม่ {num_p}, ข้าม {skip_p} รายการ.")
                        
                        # --- บันทึก Statement Summaries ---
                        st.write("--- กำลังบันทึก Statement Summaries ---")
                        ok_s, msg_s = gs_handler.save_results_summary_to_gsheets(
                            ws_dict.get(settings.WORKSHEET_STATEMENT_SUMMARIES), final_summary_data,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_s: has_errors = True; st.error(f"Summary Error: {msg_s}")
                        else: st.write("บันทึกข้อมูล Summary สำเร็จ.")

                        # --- บันทึก Deposit/Withdrawal Logs ---
                        st.write("--- กำลังบันทึก Deposit/Withdrawal Logs ---")
                        ok_dw, msg_dw, num_dw, skip_dw = gs_handler.save_deposit_withdrawal_logs(
                            ws_dict.get(settings.WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS), deposit_withdrawal_logs,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_dw: has_errors = True; st.error(f"Deposit/Withdrawal Logs Error: {msg_dw}")
                        else: st.write(f"บันทึก Deposit/Withdrawal Logs ใหม่ {num_dw}, ข้าม {skip_dw} รายการ.")

                        # --- บันทึกประวัติการอัปโหลด ---
                        st.write("--- กำลังบันทึก Upload History ---")
                        history_log = {
                            "UploadTimestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "PortfolioID": final_portfolio_id_for_save,
                            "PortfolioName": portfolio_name_to_save,
                            "FileName": file_info['name'],
                            "FileHash": file_info['hash'],
                            "Status": "Success" if not has_errors else "Failed with errors",
                            "ImportBatchID": import_batch_id,
                            "Notes": f"Deals:{num_d}, Orders:{num_o}, Positions:{num_p}"
                        }
                        gs_handler.save_upload_history(ws_dict.get(settings.WORKSHEET_UPLOAD_HISTORY), history_log)
                        st.write("บันทึกประวัติการอัปโหลดสำเร็จ.")
                        
                        if not has_errors:
                            st.success("บันทึกข้อมูลทั้งหมดเรียบร้อยแล้ว!")
                            st.balloons()
                        else:
                            st.warning("บันทึกข้อมูลสำเร็จ แต่มีข้อผิดพลาดบางส่วนเกิดขึ้น โปรดตรวจสอบข้อความด้านบน")

                        # เคลียร์ Cache และรีเซ็ตหน้าจอ
                        st.info("กำลังล้าง Cache และรีเซ็ตหน้าจอ...")
                        gs_handler.load_actual_trades_from_gsheets.cache_clear() 
                        gs_handler.load_statement_summaries_from_gsheets.cache_clear() 
                        gs_handler.load_deposit_withdrawal_logs_from_gsheets.cache_clear()
                        
                        
                        st.session_state['extracted_data'] = None
                        st.session_state.uploader_key += 1
                        st.rerun()

                    except Exception as e:
                        st.error("เกิดข้อผิดพลาดร้ายแรงระหว่างกระบวนการบันทึกข้อมูล")
                        st.exception(e)
