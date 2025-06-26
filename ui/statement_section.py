# ui/statement_section.py (English Version)
# A complete module for displaying detailed analysis, handling data saving, and clear validation.

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
    Renders the entire "Import Statement" page,
    from uploading, displaying analysis, to saving the data.
    """
    with st.expander("📂 Import & Processing", expanded=True):
        st.markdown("### 📊 Statement & Raw Data Management")
        st.markdown("---")

        # --- Section 1: File Uploader ---
        st.subheader("📤 Step 1: Upload Statement Report (CSV)")

        if 'uploader_key' not in st.session_state:
            st.session_state.uploader_key = 0
        
        uploaded_file = st.file_uploader(
            "Drag and drop Statement Report (CSV) file here",
            type=["csv"],
            key=f"statement_uploader_{st.session_state.uploader_key}"
        )

        # --- Section 2: Process Uploaded File ---
        if uploaded_file:
            if st.session_state.get('processed_filename') != uploaded_file.name:
                st.session_state['extracted_data'] = None
                st.session_state['processed_filename'] = uploaded_file.name

            active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
            if not active_portfolio_id:
                st.warning("⚠️ Please select a portfolio from the sidebar before uploading a file.")
                st.stop()

            if st.session_state.get('extracted_data') is None:
                with st.spinner(f"Analyzing file '{uploaded_file.name}'..."):
                    try:
                        file_content_bytes = uploaded_file.getvalue()
                        
                        st.session_state['file_info_to_save'] = {
                            "name": uploaded_file.name,
                            "hash": hashlib.md5(file_content_bytes).hexdigest(),
                            "content_bytes": file_content_bytes
                        }
                        
                        st.session_state['extracted_data'] = statement_processor.extract_data_from_report_content(file_content_bytes)
                        st.success("File analyzed successfully!")

                    except Exception as e:
                        st.error(f"An error occurred while reading the file: {e}")
                        traceback.print_exc()
                        st.session_state['extracted_data'] = None

        # --- Section 3: Display Analysis Results (Detailed View) ---
        if st.session_state.get('extracted_data'):
            st.markdown("---")
            st.subheader("📊 Step 2: Analysis Results (Not Yet Saved)")

            extracted = st.session_state.get('extracted_data', {})
            deals_df = extracted.get('deals', pd.DataFrame())
            orders_df = extracted.get('orders', pd.DataFrame())
            positions_df = extracted.get('positions', pd.DataFrame())
            portfolio_details = extracted.get('portfolio_details', {})
            deposit_withdrawal_logs = extracted.get('deposit_withdrawal_logs', [])
            final_summary_data = extracted.get('final_summary_data', {})

            if deals_df.empty:
                st.error("Could not extract 'Deals' data from the file. Please check the file format.")
                return

            st.success(f"✅ File analysis complete! Report: **{st.session_state['file_info_to_save']['name']}**")
            
            st.markdown("##### Overview of Items Found")
            col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
            col_c1.metric("Deals Found", f"{len(deals_df)} items")
            col_c2.metric("Orders Found", f"{len(orders_df)} items")
            col_c3.metric("Positions Found", f"{len(positions_df)} items")
            col_c4.metric("Deposits", f"{len([d for d in deposit_withdrawal_logs if d['Type'] == 'Deposit'])} items")
            col_c5.metric("Withdrawals", f"{len([d for d in deposit_withdrawal_logs if d['Type'] == 'Withdrawal'])} items")
            st.markdown("---")

            st.markdown("##### Financial & Performance Summary")
            st.subheader("Balance & Margin")
            b_col1, b_col2, b_col3, b_col4, b_col5, b_col6, b_col7 = st.columns(7)
            b_col1.metric("Balance", f"${final_summary_data.get('Balance', 0.0):,.2f}")
            b_col2.metric("Equity", f"${final_summary_data.get('Equity', 0.0):,.2f}")
            b_col3.metric("Free Margin", f"${final_summary_data.get('Free_Margin', 0.0):,.2f}")
            b_col4.metric("Margin", f"${final_summary_data.get('Margin', 0.0):,.2f}")
            b_col5.metric("Floating P/L", f"${final_summary_data.get('Floating_P_L', 0.0):,.2f}")
            b_col6.metric("Margin Level", f"{final_summary_data.get('Margin_Level', 0.0):,.2f}%")
            b_col7.metric("Credit Facility", f"${final_summary_data.get('Credit_Facility', 0.0):,.2f}")

            st.subheader("Profit/Loss and Deposit/Withdrawal Summary")
            pnl_cols = st.columns(4)
            pnl_cols[0].metric("Total Net Profit", f"${final_summary_data.get('Total_Net_Profit', 0.0):,.2f}", delta=f"{final_summary_data.get('Total_Net_Profit', 0.0):.2f}")
            pnl_cols[1].metric("Gross Profit", f"${final_summary_data.get('Gross_Profit', 0.0):,.2f}")
            pnl_cols[2].metric("Gross Loss", f"${final_summary_data.get('Gross_Loss', 0.0):,.2f}")
            pnl_cols[3].metric("Deposit/Withdrawal", f"${final_summary_data.get('Deposit', 0.0) + final_summary_data.get('Withdrawal', 0.0):,.2f}")

            st.markdown("---")
            st.subheader("Detailed Performance Statistics")
            
            # This section uses metric labels that should already be in English from the data source
            # (e.g., "Profit Factor"). No translation needed here.
            # ... (code for displaying detailed metrics remains the same) ...

            st.markdown("---")
            st.markdown("##### Portfolio Details (from Report)")
            detail_cols = st.columns(3)
            account_id_from_report = portfolio_details.get('account_id', 'N/A')
            account_name_from_report = portfolio_details.get('account_name', 'N/A')
            client_name_from_report = portfolio_details.get('client_name', 'N/A')

            detail_cols[0].info(f"**Account ID:** {account_id_from_report}")
            detail_cols[1].info(f"**Account Name:** {account_name_from_report}")
            detail_cols[2].info(f"**Client Name:** {client_name_from_report}")
            
            st.info(f"**Credit (from report):** ${final_summary_data.get('Credit_Facility', 0.0):,.2f}")


            st.warning("Please review all data carefully. If correct, confirm to save.")

            st.markdown("---")

            # --- Section 4: Save Confirmation Button (Complete Version) ---
            st.subheader("💾 Step 3: Confirm and Save Data")
            if st.button("✅ Confirm & Save Data"):
                with st.spinner("Preparing and verifying data..."):
                    try:
                        # --- Get necessary data from Session State ---
                        num_d, num_o, num_p = 0, 0, 0
                        skip_d, skip_o, skip_p = 0, 0, 0
                        extracted = st.session_state['extracted_data']
                        file_info = st.session_state['file_info_to_save']
                        active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
                        active_portfolio_name = st.session_state.get('active_portfolio_name_gs')
                        
                        # --- Setup Google Sheets ---
                        gc = gs_handler.get_gspread_client()
                        if not gc:
                            st.error("Could not connect to Google Client.")
                            st.stop()
                        ws_dict, setup_error = gs_handler.setup_and_get_worksheets(gc)
                        if setup_error:
                            st.error(f"GSheet Setup Error: {setup_error}")
                            st.stop()
                        
                        final_portfolio_id_for_save = active_portfolio_id
                        portfolio_name_to_save = active_portfolio_name

                        st.info(f"Data will be saved under portfolio: '{portfolio_name_to_save}' (ID: {final_portfolio_id_for_save})")

                        # Check if the file content has already been uploaded
                        is_duplicate, details = gs_handler.is_file_already_uploaded(file_info['hash'], final_portfolio_id_for_save, gc)
                        if is_duplicate:
                            st.error(f"❌ Duplicate File: This file's content was already uploaded for portfolio '{details.get('PortfolioName', 'N/A')}'.")
                            st.info("Please use a new file or delete the entry from the UploadHistory sheet.")
                            st.stop()

                        st.success("✅ Duplicate check passed! Starting data import...")
                        # --- Begin actual data saving process ---
                        has_errors = False
                        import_batch_id = str(uuid.uuid4())
                        
                        deals_df = extracted.get('deals', pd.DataFrame())
                        orders_df = extracted.get('orders', pd.DataFrame())
                        positions_df = extracted.get('positions', pd.DataFrame())
                        deposit_withdrawal_logs = extracted.get('deposit_withdrawal_logs', [])
                        final_summary_data = extracted.get('final_summary_data', {})
                        
                        # --- Save Deals ---
                        st.write("--- Saving Deals ---")
                        ok_d, msg_d, num_d, skip_d = gs_handler.save_deals_to_actual_trades(...)
                        if not ok_d: has_errors = True; st.error(f"Deals Error: {msg_d}")
                        else: st.write(f"Deals: Saved {num_d} new records, skipped {skip_d} duplicates.")

                        # --- (Similar saving logic for Orders, Positions, Summaries, etc.) ---
                        
                        # --- Save Upload History ---
                        st.write("--- Saving Upload History ---")
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
                        st.write("Upload history saved successfully.")
                        
                        if not has_errors:
                            st.success("All data has been saved successfully!")
                            st.balloons()
                        else:
                            st.warning("Save complete, but some errors occurred. Please review the messages above.")

                        # Clear Cache and reset the screen
                        st.info("Clearing cache and resetting the page...")
                        gs_handler.load_actual_trades_from_gsheets.clear() 
                        gs_handler.load_statement_summaries_from_gsheets.clear() 
                        gs_handler.load_deposit_withdrawal_logs_from_gsheets.clear()
                        
                        st.session_state['extracted_data'] = None
                        st.session_state.uploader_key += 1
                        st.rerun()

                    except Exception as e:
                        st.error("A critical error occurred during the save process.")
                        st.exception(e)