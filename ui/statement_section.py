# ui/statement_section.py

import streamlit as st
import pandas as pd
from core import statement_processor, supabase_handler # Ensure supabase_handler is imported
from config import settings
import hashlib
import json # for pretty printing dict
from datetime import datetime 
def render_statement_section(df_portfolios_gs: pd.DataFrame):
    st.markdown("---")
    st.subheader("⬆️ Step 1: Upload Trading Statement Report (CSV)")

    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    # Add a checkbox for allowing duplicate uploads (based on file content hash)
    allow_duplicate_upload = st.checkbox("✅ ต้องการอัปโหลดไฟล์ที่มีเนื้อหาซ้ำสำหรับ Portfolio นี้ (หากเป็นไฟล์เดิม โปรดตรวจสอบให้แน่ใจว่าต้องการบันทึกทับ)", value=False)

    # Portfolio selection
    portfolio_options = ["สร้าง Portfolio ใหม่"] + list(df_portfolios_gs['PortfolioName'].unique())
    selected_portfolio_name = st.selectbox("เลือก Portfolio ที่จะบันทึกข้อมูล:", portfolio_options, index=0)

    new_portfolio_id = None
    if selected_portfolio_name == "สร้าง Portfolio ใหม่":
        col_new_id, col_new_name = st.columns(2)
        with col_new_id:
            new_portfolio_id = st.text_input("รหัส Portfolio ใหม่ (ตัวเลขเท่านั้น):", value=None, max_chars=10) # Set default to None
            if new_portfolio_id and not new_portfolio_id.isdigit():
                st.error("รหัส Portfolio ใหม่ต้องเป็นตัวเลขเท่านั้น")
                new_portfolio_id = None # Invalidate if not digits
        with col_new_name:
            new_portfolio_name = st.text_input("ชื่อ Portfolio ใหม่:")
        
        if new_portfolio_id and new_portfolio_name:
            if new_portfolio_id in df_portfolios_gs['PortfolioID'].values:
                st.error(f"รหัส Portfolio '{new_portfolio_id}' มีอยู่แล้ว โปรดใช้รหัสอื่น")
                new_portfolio_id = None
            elif new_portfolio_name in df_portfolios_gs['PortfolioName'].values:
                st.error(f"ชื่อ Portfolio '{new_portfolio_name}' มีอยู่แล้ว โปรดใช้ชื่ออื่น")
                new_portfolio_id = None
            else:
                st.session_state['current_portfolio_id'] = new_portfolio_id # Set current ID for new portfolio
                st.session_state['current_portfolio_name'] = new_portfolio_name
                st.info(f"จะสร้าง Portfolio ใหม่: ID '{new_portfolio_id}', Name '{new_portfolio_name}'")
        else:
            st.session_state['current_portfolio_id'] = None
            st.session_state['current_portfolio_name'] = None
    else:
        # If an existing portfolio is selected
        selected_portfolio_row = df_portfolios_gs[df_portfolios_gs['PortfolioName'] == selected_portfolio_name]
        if not selected_portfolio_row.empty:
            st.session_state['current_portfolio_id'] = selected_portfolio_row['PortfolioID'].iloc[0]
            st.session_state['current_portfolio_name'] = selected_portfolio_name
        else:
            st.session_state['current_portfolio_id'] = None
            st.session_state['current_portfolio_name'] = None

    file_content_bytes = None
    file_hash = None

    if uploaded_file is not None:
        file_content_bytes = uploaded_file.getvalue()
        # Compute file hash
        file_hash = hashlib.sha256(file_content_bytes).hexdigest()

        st.info(f"ไฟล์ที่อัปโหลด: {uploaded_file.name} (ขนาด: {len(file_content_bytes)} bytes)")
        
        # Check for duplicate file content hash for the selected portfolio
        is_duplicate, duplicate_message = supabase_handler.check_duplicate_file(file_hash, st.session_state['current_portfolio_id'])

        if is_duplicate and not allow_duplicate_upload:
            st.warning(f"⚠️ {duplicate_message}. หากต้องการอัปโหลดซ้ำ โปรดติ๊ก '✅ ต้องการอัปโหลดไฟล์ที่มีเนื้อหาซ้ำ...'")
            st.session_state['extracted_data'] = None # Clear previous data if not allowed to upload duplicate
        elif is_duplicate and allow_duplicate_upload:
            st.info(f"ไฟล์นี้เคยถูกอัปโหลดสำหรับ Portfolio นี้แล้ว แต่คุณเลือกที่จะอัปโหลดซ้ำ")
            # Proceed to process and potentially overwrite/upsert
            st.session_state['extracted_data'] = statement_processor.extract_data_from_report_content(file_content_bytes)
        else:
            st.session_state['extracted_data'] = statement_processor.extract_data_from_report_content(file_content_bytes)

    # --- Section 2: Display Analysis Results (Detailed) ---
    if st.session_state.get('extracted_data'):
        st.markdown("---")
        st.subheader("📊 Step 2: File Analysis Results (Unsaved)")

        extracted = st.session_state.get('extracted_data', {})
        deals_df = extracted.get('deals', pd.DataFrame())
        orders_df = extracted.get('orders', pd.DataFrame())
        positions_df = extracted.get('positions', pd.DataFrame())
        portfolio_details = extracted.get('portfolio_details', {})
        
        # Ensure deposit_withdrawal_logs is a DataFrame
        deposit_withdrawal_logs_raw = extracted.get('deposit_withdrawal_logs', [])
        if isinstance(deposit_withdrawal_logs_raw, list):
            if not deposit_withdrawal_logs_raw:
                dw_df = pd.DataFrame(columns=settings.WORKSHEET_HEADERS[settings.SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS])
            else:
                dw_df = pd.DataFrame(deposit_withdrawal_logs_raw)
        else:
            dw_df = deposit_withdrawal_logs_raw

        final_summary_data = extracted.get('final_summary_data', {})

        if deals_df.empty:
            st.error("Could not extract 'Deals' data from file. Please check file format.")
        if orders_df.empty:
            st.error("Could not extract 'Orders' data from file. Please check file format.")
        if positions_df.empty:
            st.error("Could not extract 'Positions' data from file. Please check file format.")

        st.markdown("##### Overview of Items Found")
        col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
        col_c1.metric("Deals Found", f"{len(deals_df)}")
        col_c2.metric("Orders Found", f"{len(orders_df)}")
        col_c3.metric("Positions Found", f"{len(positions_df)}")
        
        deposits_count = len(dw_df[dw_df['Type'] == 'Deposit']) if not dw_df.empty and 'Type' in dw_df.columns else 0
        withdrawals_count = len(dw_df[dw_df['Type'] == 'Withdrawal']) if not dw_df.empty and 'Type' in dw_df.columns else 0

        col_c4.metric("Deposits", f"{deposits_count}")
        col_c5.metric("Withdrawals", f"{withdrawals_count}")
        st.markdown("---")

        # --- Section 3: Confirm and Save Data ---
        st.subheader("💾 Step 3: Confirm & Save Data to Database")

        if (st.session_state['current_portfolio_id'] and
            st.session_state['current_portfolio_name'] and
            uploaded_file is not None and
            st.session_state['extracted_data'] is not None and
            not is_duplicate or allow_duplicate_upload): # Only allow save if not duplicate OR duplicate allowed

            if st.button("Confirm & Save Data"):
                st.spinner("Saving data to Supabase... Please wait.")
                
                # Prepare data with PortfolioID, PortfolioName, SourceFile, ImportBatchID
                import_batch_id = int(datetime.now().timestamp()) # Simple batch ID
                source_file_name = uploaded_file.name

                data_to_save = {}

                # Loop through main dataframes (deals, orders, positions, deposit_withdrawal_logs)
                for key in ['deals', 'orders', 'positions', 'deposit_withdrawal_logs']:
                    df = st.session_state['extracted_data'].get(key, pd.DataFrame())
                    if not df.empty:
                        df_copy = df.copy() # Work on a copy to avoid SettingWithCopyWarning
                        df_copy['PortfolioID'] = str(st.session_state['current_portfolio_id'])
                        df_copy['PortfolioName'] = st.session_state['current_portfolio_name']
                        df_copy['SourceFile'] = source_file_name
                        df_copy['ImportBatchID'] = import_batch_id
                        data_to_save[settings.WORKSHEET_HEADERS_MAPPER[key]] = df_copy # Map 'deals' to 'ActualTrades' etc.
                    else:
                        data_to_save[settings.WORKSHEET_HEADERS_MAPPER[key]] = pd.DataFrame(columns=settings.WORKSHEET_HEADERS[settings.WORKSHEET_HEADERS_MAPPER[key]])


                # Prepare summary data
                final_summary_data = st.session_state['extracted_data'].get('final_summary_data', {})
                if final_summary_data:
                    final_summary_data['PortfolioID'] = str(st.session_state['current_portfolio_id'])
                    final_summary_data['PortfolioName'] = st.session_state['current_portfolio_name']
                    final_summary_data['SourceFile'] = source_file_name
                    final_summary_data['ImportBatchID'] = import_batch_id
                    final_summary_data['Timestamp'] = datetime.now() # Ensure timestamp is current datetime
                    data_to_save[settings.SUPABASE_TABLE_STATEMENT_SUMMARIES] = final_summary_data
                else:
                    data_to_save[settings.SUPABASE_TABLE_STATEMENT_SUMMARIES] = {} # Ensure it's not None

                # Prepare upload history data
                upload_history_data = {
                    "UploadTimestamp": datetime.now(),
                    "PortfolioID": str(st.session_state['current_portfolio_id']),
                    "PortfolioName": st.session_state['current_portfolio_name'],
                    "FileName": uploaded_file.name,
                    "FileSize": len(file_content_bytes),
                    "FileHash": file_hash,
                    "Status": "Success", # Default to success, update on error
                    "ImportBatchID": import_batch_id,
                    "Notes": "Uploaded via Streamlit app"
                }
                data_to_save[settings.SUPABASE_TABLE_UPLOAD_HISTORY] = upload_history_data

                # Check if new portfolio needs to be saved
                if new_portfolio_id and new_portfolio_name:
                    new_portfolio_record = {
                        "PortfolioID": str(new_portfolio_id),
                        "PortfolioName": new_portfolio_name,
                        "InitialBalance": final_summary_data.get('Balance', settings.DEFAULT_ACCOUNT_BALANCE), # Get balance from summary, else default
                        "CreationDate": datetime.now() # Or from statement if available
                        # Fill other default columns as needed from settings or user input
                    }
                    data_to_save[settings.SUPABASE_TABLE_PORTFOLIOS] = new_portfolio_record

                # Call the unified save function
                success, message = supabase_handler.save_statement_data(data_to_save)

                if success:
                    st.success(message)
                    supabase_handler.clear_all_caches() # Clear caches after successful save
                    st.session_state['extracted_data'] = None # Clear displayed data
                else:
                    st.error(message)
                    # You might want to update the status in upload_history_data to "Failed" here
                    # and save it again, or handle it in save_statement_data function itself.
                    # For now, the error message indicates failure.

        else:
            if uploaded_file is None:
                st.info("โปรดอัปโหลดไฟล์ Statement Report (CSV) เพื่อเริ่มต้นการวิเคราะห์")
            elif not st.session_state['current_portfolio_id']:
                st.info("โปรดเลือก Portfolio หรือสร้าง Portfolio ใหม่")
            elif is_duplicate and not allow_duplicate_upload:
                st.warning("โปรดติ๊ก '✅ ต้องการอัปโหลดไฟล์ที่มีเนื้อหาซ้ำ...' หากคุณต้องการบันทึกไฟล์นี้ซ้ำ")

    # --- Section 4: Display Raw Extracted Data (Optional for Debugging) ---
    st.markdown("---")
    st.subheader("🔍 Raw Extracted Data (For Debugging)")
    if st.session_state.get('extracted_data'):
        extracted = st.session_state['extracted_data']
        st.write("### Portfolio Details")
        st.json(extracted.get('portfolio_details', {}))
        st.write("### Balance Summary")
        st.json(extracted.get('balance_summary', {}))
        st.write("### Results Summary")
        st.json(extracted.get('results_summary', {}))
        st.write("### Deals (Trades)")
        st.dataframe(extracted.get('deals', pd.DataFrame()))
        st.write("### Orders")
        st.dataframe(extracted.get('orders', pd.DataFrame()))
        st.write("### Positions")
        st.dataframe(extracted.get('positions', pd.DataFrame()))
        st.write("### Deposit/Withdrawal Logs")
        st.dataframe(extracted.get('deposit_withdrawal_logs', pd.DataFrame()))
        st.write("### Final Summary Data")
        st.json(extracted.get('final_summary_data', {}))