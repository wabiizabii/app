# ui/statement_section.py
# Complete version: detailed display, comprehensive saving, and clear validation

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
    Function to display the entire "Import Statement" page,
    including file upload, analysis display, and data saving.
    """
    with st.expander("📂 Import & Processing", expanded=True):
        st.markdown("### 📊 Manage Statements & Raw Data")
        st.markdown("---")

        # --- Section 1: Upload File ---
        st.subheader("📤 Step 1: Upload Statement Report (CSV)")

        if 'uploader_key' not in st.session_state:
            st.session_state.uploader_key = 0
        
        uploaded_file = st.file_uploader(
            "Drag and drop your Statement Report (CSV) here",
            type=["csv"],
            key=f"statement_uploader_{st.session_state.uploader_key}"
        )

        # --- Section 2: Process Uploaded File ---
        if uploaded_file:
            if st.session_state.get('processed_filename') != uploaded_file.name:
                st.session_state['extracted_data'] = None
                st.session_state['processed_filename'] = uploaded_file.name

            active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
            active_portfolio_name = st.session_state.get('active_portfolio_name_gs') # Get active portfolio name here
            if not active_portfolio_id:
                st.warning("⚠️ Please select a portfolio in the Sidebar before uploading a file.")
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
                        st.error(f"Error reading file: {e}")
                        traceback.print_exc()
                        st.session_state['extracted_data'] = None

        # --- Section 3: Display Analysis Results (Detailed) ---
        if st.session_state.get('extracted_data'):
            st.markdown("---")
            st.subheader("📊 Step 2: File Analysis Results (Unsaved)")

            extracted = st.session_state.get('extracted_data', {})
            deals_df = extracted.get('deals', pd.DataFrame())
            orders_df = extracted.get('orders', pd.DataFrame())
            positions_df = extracted.get('positions', pd.DataFrame())
            portfolio_details = extracted.get('portfolio_details', {})
            deposit_withdrawal_logs = extracted.get('deposit_withdrawal_logs', [])
            final_summary_data = extracted.get('final_summary_data', {})

            if deals_df.empty:
                st.error("Could not extract 'Deals' data from file. Please check file format.")
                return

            st.success(f"✅ File analysis successful! Report: **{st.session_state['file_info_to_save']['name']}**")
            
            st.markdown("##### Overview of Items Found")
            col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
            col_c1.metric("Deals Found", f"{len(deals_df)}")
            col_c2.metric("Orders Found", f"{len(orders_df)}")
            col_c3.metric("Positions Found", f"{len(positions_df)}")
            col_c4.metric("Deposits", f"{len([d for d in deposit_withdrawal_logs if d['Type'] == 'Deposit'])}")
            col_c5.metric("Withdrawals", f"{len([d for d in deposit_withdrawal_logs if d['Type'] == 'Withdrawal'])}")
            st.markdown("---")

            st.markdown("##### Financial & Performance Summary")
            
            st.markdown("###### Balance & Margin")
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            b_col1.markdown(f"**Balance**<br><span style='font-size:1.2em;'>${final_summary_data.get('Balance', 0.0):,.2f}</span>", unsafe_allow_html=True)
            b_col2.markdown(f"**Equity**<br><span style='font-size:1.2em;'>${final_summary_data.get('Equity', 0.0):,.2f}</span>", unsafe_allow_html=True)
            b_col3.markdown(f"**Floating P/L**<br><span style='font-size:1.2em;'>${final_summary_data.get('Floating_P_L', 0.0):,.2f}</span>", unsafe_allow_html=True)
            b_col4.markdown(f"**Credit Facility**<br><span style='font-size:1.2em;'>${final_summary_data.get('Credit_Facility', 0.0):,.2f}</span>", unsafe_allow_html=True)
            
            st.markdown("###### Profit/Loss & Deposit/Withdrawal")
            pnl_cols = st.columns(4)
            pnl_cols[0].markdown(f"**Net Profit (Total)**<br><span style='font-size:1.2em;'>${final_summary_data.get('Total_Net_Profit', 0.0):,.2f}</span><br><span style='font-size:0.9em; color: {'green' if final_summary_data.get('Total_Net_Profit', 0.0) >= 0 else 'red'};'>{final_summary_data.get('Total_Net_Profit', 0.0):.2f}</span>", unsafe_allow_html=True)
            pnl_cols[1].markdown(f"**Gross Profit**<br><span style='font-size:1.2em;'>${final_summary_data.get('Gross_Profit', 0.0):,.2f}</span>", unsafe_allow_html=True)
            pnl_cols[2].markdown(f"**Gross Loss**<br><span style='font-size:1.2em;'>${final_summary_data.get('Gross_Loss', 0.0):,.2f}</span>", unsafe_allow_html=True)
            pnl_cols[3].markdown(f"**Deposit/Withdrawal**<br><span style='font-size:1.2em;'>${final_summary_data.get('Deposit', 0.0) + final_summary_data.get('Withdrawal', 0.0):,.2f}</span>", unsafe_allow_html=True)

            st.markdown("---")
            
            st.subheader("In-depth Performance Statistics")
            
            col1, col2, col3 = st.columns(3)

            # --- Column 1: Trade Statistics ---
            with col1:
                st.markdown("##### Trade Statistics")
                st.markdown(f"**Total Trades**<br><span style='font-size:1.1em;'>{int(final_summary_data.get('Total_Trades', 0))}</span>", unsafe_allow_html=True)
                
                profit_trades_count = int(final_summary_data.get('Profit_Trades_Count', 0))
                profit_trades_percent = final_summary_data.get('Profit_Trades_Percent', 0)
                st.markdown(f"**Profit Trades (% of total)**<br><span style='font-size:1.1em;'>{profit_trades_count} ({profit_trades_percent:.2f}%)</span>", unsafe_allow_html=True)
                
                loss_trades_count = int(final_summary_data.get('Loss_Trades_Count', 0))
                loss_trades_percent = final_summary_data.get('Loss_Trades_Percent', 0)
                st.markdown(f"**Loss Trades (% of total)**<br><span style='font-size:1.1em;'>{loss_trades_count} ({loss_trades_percent:.2f}%)</span>", unsafe_allow_html=True)
                
                short_trades_count = int(final_summary_data.get('Short_Trades_Count', 0))
                short_trades_won_percent = final_summary_data.get('Short_Trades_Won_Percent', 0)
                st.markdown(f"**Short Trades (won %)**<br><span style='font-size:1.1em;'>{short_trades_count} ({short_trades_won_percent:.2f}%)</span>", unsafe_allow_html=True)
                
                long_trades_count = int(final_summary_data.get('Long_Trades_Count', 0))
                long_trades_won_percent = final_summary_data.get('Long_Trades_Won_Percent', 0)
                st.markdown(f"**Long Trades (won %)**<br><span style='font-size:1.1em;'>{long_trades_count} ({long_trades_won_percent:.2f}%)</span>", unsafe_allow_html=True)

            # --- Column 2: Profit/Loss & Quality Statistics ---
            with col2:
                st.markdown("##### Profit/Loss")
                st.markdown(f"**Largest profit trade**<br><span style='font-size:1.1em;'>${final_summary_data.get('Largest_Profit_Trade', 0):,.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"**Largest loss trade**<br><span style='font-size:1.1em;'>${final_summary_data.get('Largest_Loss_Trade', 0):,.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"**Average profit trade**<br><span style='font-size:1.1em;'>${final_summary_data.get('Average_Profit_Trade', 0):,.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"**Average loss trade**<br><span style='font-size:1.1em;'>${final_summary_data.get('Average_Loss_Trade', 0):,.2f}</span>", unsafe_allow_html=True)

                st.markdown("##### Quality Statistics")
                st.markdown(f"**Avg. Consecutive Wins**<br><span style='font-size:1.1em;'>{int(final_summary_data.get('Average_Consecutive_Wins', 0))}</span>", unsafe_allow_html=True)
                st.markdown(f"**Avg. Consecutive Losses**<br><span style='font-size:1.1em;'>{int(final_summary_data.get('Average_Consecutive_Losses', 0))}</span>", unsafe_allow_html=True)


            # --- Column 3: Advanced Statistics & Drawdown ---
            with col3:
                st.markdown("##### Advanced Statistics")
                st.markdown(f"**Profit Factor**<br><span style='font-size:1.1em;'>{final_summary_data.get('Profit_Factor', 0):.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"**Expected Payoff**<br><span style='font-size:1.1em;'>${final_summary_data.get('Expected_Payoff', 0):,.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"**Recovery Factor**<br><span style='font-size:1.1em;'>{final_summary_data.get('Recovery_Factor', 0):.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"**Sharpe Ratio**<br><span style='font-size:1.1em;'>{final_summary_data.get('Sharpe_Ratio', 0):.2f}</span>", unsafe_allow_html=True)
                
                st.markdown("##### Drawdown")
                st.markdown(f"**Maximal Drawdown**<br><span style='font-size:1.1em;'>${final_summary_data.get('Maximal_Drawdown_Value', 0):,.2f} ({final_summary_data.get('Maximal_Drawdown_Percent', 0):.2f}%)</span>", unsafe_allow_html=True)
                st.markdown(f"**Balance Drawdown Absolute**<br><span style='font-size:1.1em;'>${final_summary_data.get('Balance_Drawdown_Absolute', 0):,.2f}</span>", unsafe_allow_html=True)


            st.markdown("---")
            st.markdown("##### Portfolio Details (from Report & Selected)")
            detail_cols = st.columns(3)
            
            # Account ID from Report
            account_id_from_report = portfolio_details.get('account_id', 'N/A')
            detail_cols[0].info(f"**Account ID (from Report):** {account_id_from_report}")
            
            # Account Name from Report
            account_name_from_report = portfolio_details.get('account_name', 'N/A')
            detail_cols[1].info(f"**Account Name (from Report):** {account_name_from_report}")
            
            # Selected Portfolio Name (ยืนยันพอร์ตที่เลือก)
            active_portfolio_name = st.session_state.get('active_portfolio_name_gs', 'Not Selected')
            detail_cols[2].info(f"**Selected Portfolio Name:** {active_portfolio_name}")
            
            st.info(f"**Credit (from Report):** ${final_summary_data.get('Credit_Facility', 0.0):,.2f}")


            st.markdown("---")
            st.warning("Please review all data. If correct, confirm to save.")

            # --- Section 4: Confirm Save Button (Complete Version) ---
            st.subheader("💾 Step 3: Confirm Data Save")
            if st.button("✅ Confirm & Save Data"):
                with st.spinner("Preparing and verifying data..."):
                    try:
                        # --- Retrieve necessary data from Session State ---
                        extracted = st.session_state['extracted_data']
                        file_info = st.session_state['file_info_to_save']
                        active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
                        active_portfolio_name = st.session_state.get('active_portfolio_name_gs')
                        portfolio_details = extracted.get('portfolio_details', {})
                        account_id_from_report = portfolio_details.get('account_id', '').strip() # Get and strip whitespace
                        account_name_from_report = portfolio_details.get('account_name', '').strip() # Get and strip whitespace
                        
                        # --- Setup Google Sheets ---
                        gc = gs_handler.get_gspread_client()
                        if not gc:
                            st.error("Could not connect to Google Client.")
                            st.stop()
                        ws_dict, setup_error = gs_handler.setup_and_get_worksheets(gc)
                        if setup_error:
                            st.error(f"Setup GSheet Error: {setup_error}")
                            st.stop()
                        
                        #
                        # --- 1. Set the CORRECT ID for saving PERMANENTLY ---
                        # The ID for saving data is ALWAYS the system's UUID from the sidebar.
                        final_portfolio_id_for_save = active_portfolio_id
                        portfolio_name_to_save = active_portfolio_name

                        # --- 2. Perform VALIDATION using the registered account number ---
                        all_portfolios_df = gs_handler.load_portfolios_from_gsheets()
                        active_portfolio_row = all_portfolios_df[all_portfolios_df['PortfolioID'] == active_portfolio_id]

                        if active_portfolio_row.empty:
                            st.error(f"Error: Cannot find the selected portfolio (ID: {active_portfolio_id}) in the database.")
                            st.stop()

                        registered_account_id = str(active_portfolio_row.iloc[0].get('RegisteredAccountID', '')).strip()
                        account_id_from_file = str(portfolio_details.get('account_id', '')).strip()

                        if not account_id_from_file or account_id_from_file.lower() == 'n/a':
                            st.error("The uploaded statement file does not contain a valid Account ID. Cannot proceed.")
                            st.stop()

                        # Case 1: Portfolio is already registered. We must VALIDATE.
                        if registered_account_id and registered_account_id not in ['nan', '']:
                            if registered_account_id != account_id_from_file:
                                st.error("ACCOUNT ID MISMATCH!")
                                st.warning(f"This portfolio is registered to Account ID: **{registered_account_id}**.")
                                st.warning(f"But the uploaded file is for Account ID: **{account_id_from_file}**.")
                                st.info("Operation cancelled to protect your data. Please select the correct portfolio or upload the correct file.")
                                st.stop()
                            else:
                                st.success(f"Account ID Matched: The file's Account ID ({account_id_from_file}) matches the registered ID.")

                        # Case 2: Portfolio is new. We must REGISTER it.
                        else:
                            st.info(f"This is the first upload for this portfolio. Registering it with Account ID: **{account_id_from_file}**")
                            update_ok, update_msg = gs_handler.update_portfolio_account_id(gc, active_portfolio_id, account_id_from_file)
                            if not update_ok:
                                st.error(f"Failed to register Account ID: {update_msg}")
                                st.stop()
                            st.success("Portfolio registered successfully.")

                        # --- 3. Final confirmation before saving ---
                        st.info(f"Data will be saved for portfolio: '{portfolio_name_to_save}' using internal system ID: **{final_portfolio_id_for_save}**")
                        # --- END: THE CORRECTED LOGIC BLOCK ---


                        # The only remaining check: whether the file's "content" is a duplicate of a previously uploaded file
                        is_duplicate, details = gs_handler.is_file_already_uploaded(file_info['hash'], gc)
                        if is_duplicate:
                            st.error(f"❌ Duplicate File: The content of this file has already been uploaded for portfolio '{details.get('PortfolioName', 'N/A')}'")
                            st.info("Please use a new file or delete the history in the UploadHistory sheet.")
                            st.stop()

                        st.success("✅ Duplicate file check passed! Starting data save...")
                        # --- Start actual data saving process ---
                        has_errors = False
                        import_batch_id = str(uuid.uuid4())
                        
                        deals_df = extracted.get('deals', pd.DataFrame())
                        orders_df = extracted.get('orders', pd.DataFrame())
                        positions_df = extracted.get('positions', pd.DataFrame())
                        deposit_withdrawal_logs = extracted.get('deposit_withdrawal_logs', [])
                        final_summary_data = extracted.get('final_summary_data', {})
                        
                        # --- Save all extracted data to respective sheets ---
                        st.markdown("<p style='font-size:14px;'>--- Saving Deals ---</p>", unsafe_allow_html=True)
                        ok_d, msg_d, num_d, skip_d = gs_handler.save_deals_to_actual_trades(
                            ws_dict.get(settings.WORKSHEET_ACTUAL_TRADES), deals_df,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_d: has_errors = True; st.error(f"Deals Error: {msg_d}")
                        else: st.markdown(f"<p style='font-size:14px;'>Deals: New {num_d}, Skipped {skip_d} items.</p>", unsafe_allow_html=True)

                        st.markdown("<p style='font-size:14px;'>--- Saving Orders ---</p>", unsafe_allow_html=True)
                        ok_o, msg_o, num_o, skip_o = gs_handler.save_orders_to_actul_orders(
                            ws_dict.get(settings.WORKSHEET_ACTUAL_ORDERS), orders_df,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_o: has_errors = True; st.error(f"Orders Error: {msg_o}")
                        else: st.markdown(f"<p style='font-size:14px;'>Orders: New {num_o}, Skipped {skip_o} items.</p>", unsafe_allow_html=True)

                        st.markdown("<p style='font-size:14px;'>--- Saving Positions ---</p>", unsafe_allow_html=True)
                        ok_p, msg_p, num_p, skip_p = gs_handler.save_positions_to_actul_positions(
                            ws_dict.get(settings.WORKSHEET_ACTUAL_POSITIONS), positions_df,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_p: has_errors = True; st.error(f"Positions Error: {msg_p}")
                        else: st.markdown(f"<p style='font-size:14px;'>Positions: New {num_p}, Skipped {skip_p} items.</p>", unsafe_allow_html=True)
                        
                        st.markdown("<p style='font-size:14px;'>--- Saving Statement Summaries ---</p>", unsafe_allow_html=True)
                        ok_s, msg_s = gs_handler.save_results_summary_to_gsheets(
                            ws_dict.get(settings.WORKSHEET_STATEMENT_SUMMARIES), final_summary_data,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_s: has_errors = True; st.error(f"Summary Error: {msg_s}")
                        else: st.markdown("<p style='font-size:14px;'>Summary data saved successfully.</p>", unsafe_allow_html=True)

                        st.markdown("<p style='font-size:14px;'>--- Saving Deposit/Withdrawal Logs ---</p>", unsafe_allow_html=True)
                        ok_dw, msg_dw, num_dw, skip_dw = gs_handler.save_deposit_withdrawal_logs(
                            ws_dict.get(settings.WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS), deposit_withdrawal_logs,
                            final_portfolio_id_for_save, portfolio_name_to_save, file_info['name'], import_batch_id
                        )
                        if not ok_dw: has_errors = True; st.error(f"Deposit/Withdrawal Logs Error: {msg_dw}")
                        else: st.markdown(f"<p style='font-size:14px;'>Deposit/Withdrawal Logs: New {num_dw}, Skipped {skip_dw} items.</p>", unsafe_allow_html=True)

                        st.markdown("<p style='font-size:14px;'>--- Saving Upload History ---</p>", unsafe_allow_html=True)
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
                        st.markdown("<p style='font-size:14px;'>Upload history saved successfully.</p>", unsafe_allow_html=True)
                        
                        # --- NEW: Update AccountID in TradeLog - Portfolios sheet ---
                        if final_portfolio_id_for_save and active_portfolio_id and \
                           final_portfolio_id_for_save != active_portfolio_id: # Only update if new ID is different from active portfolio ID
                            st.markdown("<p style='font-size:14px;'>--- Updating Portfolio Account ID ---</p>", unsafe_allow_html=True)
                            
                            # Use active_portfolio_id (from sidebar) to find the portfolio in the Portfolios sheet
                            # Use final_portfolio_id_for_save (prioritizing report ID) as the value to write
                            update_ok, update_msg = gs_handler.update_portfolio_account_id(
                                gc, active_portfolio_id, final_portfolio_id_for_save
                            )
                            if update_ok:
                                st.markdown(f"<p style='font-size:14px;'>{update_msg}</p>", unsafe_allow_html=True)
                            else:
                                st.error(f"Error updating AccountID in Portfolios sheet: {update_msg}")
                                has_errors = True # Flag as error for final status


                        if not has_errors:
                            st.success("All data saved successfully!")
                            st.balloons()
                        else:
                            st.warning("Data saved successfully, but some errors occurred. Please check the messages above.")

                        # Clear Cache and Reset Screen
                        st.info("Clearing Cache and resetting screen...")
                        gs_handler.load_actual_trades_from_gsheets.cache_clear() 
                        gs_handler.load_statement_summaries_from_gsheets.cache_clear() 
                        gs_handler.load_deposit_withdrawal_logs_from_gsheets.cache_clear()
                        gs_handler.load_portfolios_from_gsheets.cache_clear() # Clear portfolio cache as well
                        
                        st.session_state['extracted_data'] = None
                        st.session_state.uploader_key += 1
                        st.rerun()

                    except Exception as e:
                        st.error("A critical error occurred during the data saving process.")
                        st.exception(e)