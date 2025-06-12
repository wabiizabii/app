# core/gs_handler.py
import streamlit as st
import pandas as pd
import numpy as np
import gspread
from datetime import datetime
import uuid # For batch ID and other unique IDs

# Import constants from config.settings
from config import settings

# ============== GOOGLE SHEETS UTILITY FUNCTIONS ==============
# Functions taken from PART 1.5 and PART 1.6 and SEC 6 of main (1).py

@st.cache_resource # Use cache_resource for gspread client object
def get_gspread_client():
    """
    Initializes and returns a gspread client using Streamlit secrets, cached.
    Uses gspread.service_account_from_dict for authentication, matching main (1).py.
    """
    try:
        if "gcp_service_account" not in st.secrets:
            st.warning("⚠️ โปรดตั้งค่า 'gcp_service_account' ใน `.streamlit/secrets.toml` เพื่อเชื่อมต่อ Google Sheets.") # 
            return None
        # Using gspread's direct method for service account from dict, as in main (1).py 
        return gspread.service_account_from_dict(st.secrets["gcp_service_account"]) # 
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}") # 
        st.info("ตรวจสอบว่า 'gcp_service_account' ใน secrets.toml ถูกต้อง และได้แชร์ Sheet กับ Service Account แล้ว") # 
        return None

def setup_and_get_worksheets(gc_client):
    """
    Opens the main spreadsheet and ensures all required worksheets exist and have correct headers.
    Returns a dictionary of worksheet objects. This replaces the complex setup in SEC 6 of main (1).py.
    """
    if not gc_client:
        return None, "Google Sheets client not available."

    ws_dict = {}
    sh = None
    try:
        sh = gc_client.open(settings.GOOGLE_SHEET_NAME)
        # Iterate through all defined worksheets in settings to ensure they exist and have correct headers
        for ws_name, headers in settings.WORKSHEET_HEADERS.items():
            try:
                ws = sh.worksheet(ws_name)
                # Check and update headers
                current_ws_headers = []
                if ws.row_count > 0:
                    try:
                        current_ws_headers = ws.row_values(1)
                    except Exception:
                        pass # Ignore if row_values fails, likely empty sheet
                
                # Update headers if they are missing, empty, or don't match exactly
                if not current_ws_headers or all(h=="" for h in current_ws_headers) or set(current_ws_headers) != set(headers):
                    ws.update([headers], value_input_option='USER_ENTERED')
                    print(f"Info: Headers updated/written for worksheet '{ws_name}'.")
                ws_dict[ws_name] = ws
            except gspread.exceptions.WorksheetNotFound:
                print(f"Info: Worksheet '{ws_name}' not found. Creating it now...")
                try:
                    # Default rows/cols, can be made configurable if needed
                    new_ws = sh.add_worksheet(title=ws_name, rows="1000", cols="26") 
                    new_ws.update([headers], value_input_option='USER_ENTERED')
                    ws_dict[ws_name] = new_ws
                except Exception as e_add_ws:
                    return None, f"❌ Failed to create worksheet '{ws_name}': {e_add_ws}"
            except Exception as e_open_ws:
                return None, f"❌ Error accessing worksheet '{ws_name}': {e_open_ws}"
        return ws_dict, None # Return dict and no error
    except gspread.exceptions.APIError as e_api:
        return None, f"❌ Google Sheets API Error (Opening Spreadsheet): {e_api.args[0] if e_api.args else 'Unknown API error'}."
    except Exception as e_setup:
        return None, f"❌ เกิดข้อผิดพลาดในการเข้าถึง Spreadsheet: {type(e_setup).__name__} - {str(e_setup)[:200]}..."

@st.cache_data(ttl=300) # Cache ข้อมูลไว้ 5 นาที 
def load_portfolios_from_gsheets():
    gc = get_gspread_client() # 
    if gc is None:
        print("Error: GSpread client not available for loading portfolios.") # 
        return pd.DataFrame() # 
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME) # 
        worksheet = sh.worksheet(settings.WORKSHEET_PORTFOLIOS) # 
        records = worksheet.get_all_records(numericise_ignore=['all']) # 
        
        if not records:
            print(f"Info: No records found in Worksheet '{settings.WORKSHEET_PORTFOLIOS}'.") # 
            return pd.DataFrame() # 
        
        df_portfolios = pd.DataFrame(records) # 
        
        cols_to_numeric_type = {
            'InitialBalance': float, 'ProfitTargetPercent': float, 
            'DailyLossLimitPercent': float, 'TotalStopoutPercent': float,
            'Leverage': float, 'MinTradingDays': int,
            'OverallProfitTarget': float, 'WeeklyProfitTarget': float, 'DailyProfitTarget': float,
            'MaxAcceptableDrawdownOverall': float, 'MaxAcceptableDrawdownDaily': float,
            'ScaleUp_MinWinRate': float, 'ScaleUp_MinGainPercent': float, 'ScaleUp_RiskIncrementPercent': float,
            'ScaleDown_MaxLossPercent': float, 'ScaleDown_LowWinRate': float, 'ScaleDown_RiskDecrementPercent': float,
            'MinRiskPercentAllowed': float, 'MaxRiskPercentAllowed': float, 'CurrentRiskPercent': float
        } # 
        for col, target_type in cols_to_numeric_type.items():
            if col in df_portfolios.columns:
                df_portfolios[col] = df_portfolios[col].replace('', np.nan) # 
                df_portfolios[col] = pd.to_numeric(df_portfolios[col], errors='coerce').fillna(0) # 
                if target_type == int:
                    df_portfolios[col] = df_portfolios[col].astype(int) # 

        if 'EnableScaling' in df_portfolios.columns:
             df_portfolios['EnableScaling'] = df_portfolios['EnableScaling'].astype(str).str.upper().map({'TRUE': True, 'YES': True, '1': True, 'FALSE': False, 'NO': False, '0': False}).fillna(False) # 

        date_cols = ['CompetitionEndDate', 'TargetEndDate', 'CreationDate'] # 
        for col in date_cols:
            if col in df_portfolios.columns:
                df_portfolios[col] = pd.to_datetime(df_portfolios[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S') # 
        return df_portfolios
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ ไม่พบ Worksheet ชื่อ '{settings.WORKSHEET_PORTFOLIOS}' ใน Google Sheet '{settings.GOOGLE_SHEET_NAME}'.") # 
        return pd.DataFrame() # 
    except gspread.exceptions.APIError as e_api:
        if hasattr(e_api, 'response') and e_api.response and e_api.response.status_code == 429:
            st.error(f"❌ เกิดข้อผิดพลาดในการโหลด Portfolios (Quota Exceeded). ลองอีกครั้งในภายหลัง") # 
        else:
            st.error(f"❌ เกิดข้อผิดพลาดในการโหลด Portfolios (API Error): {e_api}") # 
        return pd.DataFrame() # 
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการโหลด Portfolios: {e}") # 
        return pd.DataFrame() # 

@st.cache_data(ttl=180) # 
def load_all_planned_trade_logs_from_gsheets():
    gc = get_gspread_client() # 
    if gc is None:
        print("Warning: GSpread client not available for loading planned trade logs.") # 
        return pd.DataFrame() # 
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME) # 
        worksheet = sh.worksheet(settings.WORKSHEET_PLANNED_LOGS) # 
        records = worksheet.get_all_records(numericise_ignore=['all']) # 
        
        if not records:
            return pd.DataFrame() # 
        
        df_logs = pd.DataFrame(records) # 
        
        if 'Timestamp' in df_logs.columns:
            df_logs['Timestamp'] = pd.to_datetime(df_logs['Timestamp'], errors='coerce') # 
        
        cols_to_numeric_planned = ['Risk $', 'RR', 'Entry', 'SL', 'TP', 'Lot', 'Risk %'] # 
        for col_viewer in cols_to_numeric_planned:
            if col_viewer in df_logs.columns:
                df_logs[col_viewer] = df_logs[col_viewer].replace('', np.nan) # 
                df_logs[col_viewer] = pd.to_numeric(df_logs[col_viewer], errors='coerce') # 
                if col_viewer == 'Risk $': df_logs[col_viewer] = df_logs[col_viewer].fillna(0) # 


        if 'PortfolioID' in df_logs.columns:
            df_logs['PortfolioID'] = df_logs['PortfolioID'].astype(str) # 
        
        return df_logs
    except gspread.exceptions.WorksheetNotFound:
        print(f"Warning: Worksheet '{settings.WORKSHEET_PLANNED_LOGS}' not found.") # 
        return pd.DataFrame() # 
    except gspread.exceptions.APIError as e_api:
        if hasattr(e_api, 'response') and e_api.response and e_api.response.status_code == 429:
            print(f"APIError (Quota Exceeded) loading planned trade logs: {e_api.args[0] if e_api.args else 'Unknown quota error'}") # 
        else:
            print(f"APIError loading planned trade logs: {e_api}") # 
        return pd.DataFrame() # 
    except Exception as e:
        print(f"Unexpected error loading all planned trade logs: {e}") # 
        return pd.DataFrame() # 

@st.cache_data(ttl=180) # 
def load_actual_trades_from_gsheets(): # Loads "Deals" 
    gc = get_gspread_client() # 
    if gc is None:
        print("Warning: GSpread client not available for loading actual trades (deals).") # 
        return pd.DataFrame() # 
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME) # 
        worksheet = sh.worksheet(settings.WORKSHEET_ACTUAL_TRADES) # 
        records = worksheet.get_all_records(numericise_ignore=['all']) # 
        
        if not records:
            return pd.DataFrame() # 
        
        df_actual_trades = pd.DataFrame(records) # 
        
        if 'Time_Deal' in df_actual_trades.columns:
            df_actual_trades['Time_Deal'] = pd.to_datetime(df_actual_trades['Time_Deal'], errors='coerce') # 

        numeric_cols_actual = [
            'Volume_Deal', 'Price_Deal', 'Commission_Deal', 
            'Fee_Deal', 'Swap_Deal', 'Profit_Deal', 'Balance_Deal'
        ] # 
        for col in numeric_cols_actual:
            if col in df_actual_trades.columns:
                df_actual_trades[col] = df_actual_trades[col].replace('', np.nan) # 
                df_actual_trades[col] = pd.to_numeric(df_actual_trades[col], errors='coerce') # 

        if 'PortfolioID' in df_actual_trades.columns:
            df_actual_trades['PortfolioID'] = df_actual_trades['PortfolioID'].astype(str) # 
        
        return df_actual_trades
    except gspread.exceptions.WorksheetNotFound:
        print(f"Warning: Worksheet '{settings.WORKSHEET_ACTUAL_TRADES}' not found.") # 
        return pd.DataFrame() # 
    except gspread.exceptions.APIError as e_api:
        if hasattr(e_api, 'response') and e_api.response and e_api.response.status_code == 429:
            print(f"APIError (Quota Exceeded) loading actual trades from '{settings.WORKSHEET_ACTUAL_TRADES}'.") # 
        else:
            print(f"APIError loading actual trades from '{settings.WORKSHEET_ACTUAL_TRADES}': {e_api}") # 
        return pd.DataFrame() # 
    except Exception as e:
        print(f"Unexpected error loading actual trades from '{settings.WORKSHEET_ACTUAL_TRADES}': {e}") # 
        return pd.DataFrame() # 

@st.cache_data(ttl=180) # Cache for 3 minutes 
def load_statement_summaries_from_gsheets():
    gc = get_gspread_client() # 
    if gc is None:
        print("Error: GSpread client not available for loading statement summaries.") # 
        return pd.DataFrame() # 
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME) # 
        worksheet = sh.worksheet(settings.WORKSHEET_STATEMENT_SUMMARIES) # 
        records = worksheet.get_all_records(numericise_ignore=['all']) # 
        
        if not records:
            print(f"Info: No records found in Worksheet '{settings.WORKSHEET_STATEMENT_SUMMARIES}'.") # 
            return pd.DataFrame() # 
        
        df_summaries = pd.DataFrame(records) # 
        
        if 'PortfolioID' in df_summaries.columns:
            df_summaries['PortfolioID'] = df_summaries['PortfolioID'].astype(str) # 
        
        if 'Equity' in df_summaries.columns:
            df_summaries['Equity'] = df_summaries['Equity'].astype(str).str.replace(',', '', regex=False) # 
            df_summaries['Equity'] = pd.to_numeric(df_summaries['Equity'], errors='coerce') # 
        
        if 'Timestamp' in df_summaries.columns:
            df_summaries['Timestamp'] = pd.to_datetime(df_summaries['Timestamp'], errors='coerce') # 
            
        return df_summaries
    except gspread.exceptions.WorksheetNotFound:
        print(f"Warning: Worksheet '{settings.WORKSHEET_STATEMENT_SUMMARIES}' not found during summary load.") # 
        return pd.DataFrame() # 
    except gspread.exceptions.APIError as e_api:
        if hasattr(e_api, 'response') and e_api.response and e_api.response.status_code == 429:
            print(f"APIError (Quota Exceeded) loading statement summaries: {e_api.args[0] if e_api.args else 'Unknown quota error'}") # 
        else:
            print(f"APIError loading statement summaries: {e_api}") # 
        return pd.DataFrame() # 
    except Exception as e:
        print(f"Unexpected error loading statement summaries: {e}") # 
        return pd.DataFrame() # 

def save_plan_to_gsheets(plan_data_list, trade_mode_arg, Symbol_name, risk_percentage, trade_direction, portfolio_id, portfolio_name):
    gc = get_gspread_client() # 
    if not gc:
        st.error("ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่อบันทึกแผนได้") # 
        return False # 
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME) # 
        ws = sh.worksheet(settings.WORKSHEET_PLANNED_LOGS) # 
        timestamp_now = datetime.now() # 
        rows_to_append = [] # 
        # Use expected headers from settings 
        expected_headers_plan = settings.WORKSHEET_HEADERS[settings.WORKSHEET_PLANNED_LOGS] # 
        current_headers_plan = [] # 
        if ws.row_count > 0:
            try: current_headers_plan = ws.row_values(1) # 
            except Exception: current_headers_plan = [] # 

        if not current_headers_plan or all(h == "" for h in current_headers_plan) or set(current_headers_plan) != set(expected_headers_plan): # 
            ws.update([expected_headers_plan], value_input_option='USER_ENTERED') # 

        for idx, plan_entry in enumerate(plan_data_list):
            log_id = f"{timestamp_now.strftime('%Y%m%d%H%M%S')}-{np.random.randint(1000,9999)}-{idx}" # Replaced random with np.random.randint as np is already imported 
            row_data = {
                "LogID": log_id, "PortfolioID": str(portfolio_id), "PortfolioName": str(portfolio_name), # 
                "Timestamp": timestamp_now.strftime("%Y-%m-%d %H:%M:%S"), "Symbol": str(Symbol_name), # 
                "Mode": str(trade_mode_arg), "Direction": str(trade_direction),  # 
                "Risk %": str(risk_percentage) if pd.notna(risk_percentage) else "", # 
                "Fibo Level": str(plan_entry.get("Fibo Level", "")),  # 
                "Entry": str(plan_entry.get("Entry", "")), # 
                "SL": str(plan_entry.get("SL", "")),  # 
                "TP": str(plan_entry.get("TP", "")), # 
                "Lot": str(plan_entry.get("Lot", "")),  # 
                "Risk $": str(plan_entry.get("Risk $", "")),  # 
                "RR": str(plan_entry.get("RR", "")) # 
            }
            rows_to_append.append([row_data.get(h, "") for h in expected_headers_plan]) # 
        if rows_to_append:
            ws.append_rows(rows_to_append, value_input_option='USER_ENTERED') # 
            if hasattr(load_all_planned_trade_logs_from_gsheets, 'clear'):
                load_all_planned_trade_logs_from_gsheets.clear() # 
            return True # 
        return False # 
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ ไม่พบ Worksheet ชื่อ '{settings.WORKSHEET_PLANNED_LOGS}'.") # 
        return False # 
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกแผน: {e}") # 
        return False # 

def save_new_portfolio_to_gsheets(portfolio_data_dict):
    gc = get_gspread_client() # 
    if not gc:
        st.error("ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่อบันทึกพอร์ตได้") # 
        return False # 
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME) # 
        ws = sh.worksheet(settings.WORKSHEET_PORTFOLIOS) # 

        # Use expected headers from settings 
        expected_gsheet_headers_portfolio = settings.WORKSHEET_HEADERS[settings.WORKSHEET_PORTFOLIOS] # 

        current_sheet_headers = [] # 
        if ws.row_count > 0:
            try: current_sheet_headers = ws.row_values(1) # 
            except Exception: pass # 

        if not current_sheet_headers or all(h == "" for h in current_sheet_headers) or set(current_sheet_headers) != set(expected_gsheet_headers_portfolio): # 
             ws.update([expected_gsheet_headers_portfolio], value_input_option='USER_ENTERED') # 

        new_row_values = [str(portfolio_data_dict.get(header, "")).strip() for header in expected_gsheet_headers_portfolio] # 
        ws.append_row(new_row_values, value_input_option='USER_ENTERED') # 
        if hasattr(load_portfolios_from_gsheets, 'clear'):
            load_portfolios_from_gsheets.clear() # 
        return True # 
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ ไม่พบ Worksheet ชื่อ '{settings.WORKSHEET_PORTFOLIOS}'. กรุณาสร้างชีตนี้ก่อน และใส่ Headers ให้ถูกต้อง") # 
        return False # 
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกพอร์ตใหม่ไปยัง Google Sheets: {e}") # 
        st.exception(e) # 
        return False # 

# --- Helper Functions from SEC 6 for saving statement data ---
# Renamed from save_transactional_data_to_gsheets_sec6 to remove SEC6 suffix for clarity. 
def save_transactional_data_to_gsheets(ws, df_input, unique_id_col, expected_headers_with_portfolio, data_type_name, portfolio_id, portfolio_name, source_file_name="N/A", import_batch_id="N/A"):
    """
    Generic function to save transactional data (Deals, Orders, Positions) to a specific worksheet.
    Handles header validation and deduplication based on a specified ID column.
    """
    if df_input is None or df_input.empty: return True, 0, 0 # 
    try:
        if ws is None: return False, 0, 0 # 
        current_headers = []; header_check_successful = False # 
        if ws.row_count > 0:
            try: current_headers = ws.row_values(1); header_check_successful = True # 
            except Exception: pass # 
        if not header_check_successful or not current_headers or all(h == "" for h in current_headers) or set(current_headers) != set(expected_headers_with_portfolio): # 
            try: ws.update([expected_headers_with_portfolio], value_input_option='USER_ENTERED') # 
            except Exception: return False, 0, 0 # 
        existing_ids = set() # 
        if ws.row_count > 1:
            try:
                # Use get_all_records with expected_headers for more robust reading
                all_sheet_records = ws.get_all_records(expected_headers=expected_headers_with_portfolio, numericise_ignore=['all']) # 
                if all_sheet_records:
                    df_existing_sheet_data = pd.DataFrame(all_sheet_records) # 
                    if 'PortfolioID' in df_existing_sheet_data.columns and unique_id_col in df_existing_sheet_data.columns: # 
                        df_existing_sheet_data['PortfolioID'] = df_existing_sheet_data['PortfolioID'].astype(str) # 
                        df_portfolio_data = df_existing_sheet_data[df_existing_sheet_data['PortfolioID'] == str(portfolio_id)] # 
                        if not df_portfolio_data.empty: existing_ids = set(df_portfolio_data[unique_id_col].astype(str).str.strip().tolist()) # 
            except Exception as e_get_existing_ids: print(f"Warning ({data_type_name}): Could not get existing IDs from '{ws.title}'. Deduplication incomplete: {e_get_existing_ids}") # 
        df_to_check = df_input.copy() # 
        if unique_id_col not in df_to_check.columns: new_df = df_to_check # 
        else:
            df_to_check[unique_id_col] = df_to_check[unique_id_col].astype(str).str.strip() # 
            new_df = df_to_check[~df_to_check[unique_id_col].isin(existing_ids)] # 
        num_new = len(new_df); num_duplicates_skipped = len(df_to_check) - num_new # 
        if new_df.empty: return True, num_new, num_duplicates_skipped # 
        new_df_to_save = new_df.copy(); new_df_to_save["PortfolioID"] = str(portfolio_id); new_df_to_save["PortfolioName"] = str(portfolio_name); new_df_to_save["SourceFile"] = str(source_file_name); new_df_to_save["ImportBatchID"] = str(import_batch_id) # 
        final_df_for_append = pd.DataFrame(columns=expected_headers_with_portfolio) # 
        for col_h in expected_headers_with_portfolio:
            if col_h in new_df_to_save.columns: final_df_for_append[col_h] = new_df_to_save[col_h] # 
            else: final_df_for_append[col_h] = "" # 
        list_of_lists = final_df_for_append.astype(str).replace('nan', '').replace('None','').fillna("").values.tolist() # 
        if list_of_lists: ws.append_rows(list_of_lists, value_input_option='USER_ENTERED') # 
        return True, num_new, num_duplicates_skipped # 
    except Exception as e_save_trans: print(f"Error saving {data_type_name} to GSheets: {e_save_trans}"); return False, 0, 0 # 

def save_deals_to_actual_trades_sec6(ws, df_deals_input, portfolio_id, portfolio_name, source_file_name="N/A", import_batch_id="N/A"):
    # Use expected headers from settings 
    expected_headers_deals = settings.WORKSHEET_HEADERS[settings.WORKSHEET_ACTUAL_TRADES] # 
    return save_transactional_data_to_gsheets(ws, df_deals_input, "Deal_ID", expected_headers_deals, "Deals", portfolio_id, portfolio_name, source_file_name, import_batch_id) # 

def save_orders_to_gsheets_sec6(ws, df_orders_input, portfolio_id, portfolio_name, source_file_name="N/A", import_batch_id="N/A"):
    # Use expected headers from settings 
    expected_headers_orders = settings.WORKSHEET_HEADERS[settings.WORKSHEET_ACTUAL_ORDERS] # 
    return save_transactional_data_to_gsheets(ws, df_orders_input, "Order_ID_Ord", expected_headers_orders, "Orders", portfolio_id, portfolio_name, source_file_name, import_batch_id) # 

def save_positions_to_gsheets_sec6(ws, df_positions_input, portfolio_id, portfolio_name, source_file_name="N/A", import_batch_id="N/A"):
    # Use expected headers from settings 
    expected_headers_positions = settings.WORKSHEET_HEADERS[settings.WORKSHEET_ACTUAL_POSITIONS] # 
    return save_transactional_data_to_gsheets(ws, df_positions_input, "Position_ID", expected_headers_positions, "Positions", portfolio_id, portfolio_name, source_file_name, import_batch_id) # 

def save_results_summary_to_gsheets_sec6(ws, balance_summary_data, results_summary_data, portfolio_id, portfolio_name, source_file_name="N/A", import_batch_id="N/A"):
    try:
        if ws is None: return False, "Worksheet object is None" # 
        # Use expected headers from settings 
        expected_headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_STATEMENT_SUMMARIES] # 
        current_headers_ws = [] # 
        if ws.row_count > 0:
            try: current_headers_ws = ws.row_values(1) # 
            except Exception: pass # 
        if not current_headers_ws or all(h == "" for h in current_headers_ws) or set(current_headers_ws) != set(expected_headers): ws.update([expected_headers], value_input_option='USER_ENTERED') # 
        new_summary_row_data = {h: None for h in expected_headers}; new_summary_row_data.update({"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "PortfolioID": str(portfolio_id), "PortfolioName": str(portfolio_name), "SourceFile": str(source_file_name), "ImportBatchID": str(import_batch_id)}) # 
        balance_key_map = {"balance":"Balance", "equity":"Equity", "free_margin":"Free_Margin", "margin":"Margin", "floating_p_l":"Floating_P_L", "margin_level":"Margin_Level", "credit_facility": "Credit_Facility"} # 
        if isinstance(balance_summary_data, dict):
            for k_extract, k_gsheet in balance_key_map.items():
                if k_extract in balance_summary_data: new_summary_row_data[k_gsheet] = balance_summary_data[k_extract] # 
        if isinstance(results_summary_data, dict):
            for k_gsheet_expected in expected_headers:
                if k_gsheet_expected in results_summary_data: new_summary_row_data[k_gsheet_expected] = results_summary_data[k_gsheet_expected] # 
        comparison_keys_summary = ["Balance", "Equity", "Total_Net_Profit", "Total_Trades", "ImportBatchID"] #ImportBatchID to ensure same file summary is not re-added if run twice 
        new_summary_fingerprint_values = [] # 
        for k_comp_sum in comparison_keys_summary:
            val_sum = new_summary_row_data.get(k_comp_sum) # 
            try: new_summary_fingerprint_values.append(f"{float(val_sum):.2f}" if pd.notna(val_sum) and isinstance(val_sum, (float, int)) else str(val_sum).strip()) # 
            except (ValueError, TypeError): new_summary_fingerprint_values.append(str(val_sum).strip() if pd.notna(val_sum) else "None") # 
        new_summary_fingerprint = tuple(new_summary_fingerprint_values) # 
        if ws.row_count > 1:
            try:
                existing_summaries_records = ws.get_all_records(expected_headers=expected_headers, numericise_ignore=['all']); df_existing_summaries = pd.DataFrame(existing_summaries_records) # 
                if not df_existing_summaries.empty and 'PortfolioID' in df_existing_summaries.columns: # 
                    df_portfolio_summaries = df_existing_summaries[df_existing_summaries['PortfolioID'].astype(str) == str(portfolio_id)] # 
                    for _, existing_row_sum in df_portfolio_summaries.iterrows():
                        existing_summary_comparable_values = [] # 
                        for k_comp_sum_exist in comparison_keys_summary:
                            val_exist = existing_row_sum.get(k_comp_sum_exist) # 
                            try: existing_summary_comparable_values.append(f"{float(val_exist):.2f}" if pd.notna(val_exist) and isinstance(val_exist, (float,int)) else str(val_exist).strip()) # 
                            except (ValueError, TypeError): existing_summary_comparable_values.append(str(val_exist).strip() if pd.notna(val_exist) else "None") # 
                        if tuple(existing_summary_comparable_values) == new_summary_fingerprint: return True, "skipped_duplicate_content" # 
            except Exception as e_get_sum_records_dedup: print(f"Warning (Summary Deduplication): Could not get existing summaries for deduplication: {e_get_sum_records_dedup}") # 
        final_row_values = [str(new_summary_row_data.get(h, "")).strip() for h in expected_headers]; ws.append_rows([final_row_values], value_input_option='USER_ENTERED') # 
        return True, "saved_new" # 
    except Exception as e_save_summary: print(f"Error saving results summary to GSheet: {e_save_summary}"); return False, f"Exception during save: {e_save_summary}" #

# วางโค้ดนี้ต่อท้ายไฟล์ core/gs_handler.py


def update_portfolio_in_gsheets(portfolio_id, updated_data_dict):
    """
    Finds a row by PortfolioID and updates it with new data.
    This function finds the specific row using the PortfolioID and updates all its values.
    
    Args:
        portfolio_id (str): The unique ID of the portfolio to update.
        updated_data_dict (dict): A dictionary containing the new data for the portfolio.
        
    Returns:
        bool: True if the update was successful, False otherwise.
    """
    gc = get_gspread_client()
    if not gc:
        st.error("ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่ออัปเดตพอร์ตได้")
        return False
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME)
        ws = sh.worksheet(settings.WORKSHEET_PORTFOLIOS)

        # ค้นหาแถวที่ต้องการอัปเดตโดยใช้ PortfolioID
        # ค้นหาในคอลัมน์ที่ 1 (A) ซึ่งเราคาดว่าเป็นคอลัมน์ของ PortfolioID
        cell = ws.find(str(portfolio_id), in_column=1)
        
        if not cell:
            st.error(f"ไม่พบ PortfolioID '{portfolio_id}' ที่จะแก้ไขใน Google Sheets")
            return False

        # ดึง Headers จากแถวแรกสุดของชีต
        headers = ws.row_values(1)
        # สร้าง list ของข้อมูลใหม่ตามลำดับของ header
        # เพื่อให้แน่ใจว่าข้อมูลจะถูกเขียนลงในคอลัมน์ที่ถูกต้อง
        updated_row_values = [str(updated_data_dict.get(header, "")).strip() for header in headers]
        
        # อัปเดตข้อมูลทั้งแถว โดยอ้างอิงจากหมายเลขแถวที่พบ
        ws.update(f'A{cell.row}', [updated_row_values], value_input_option='USER_ENTERED')

        # เคลียร์ cache เพื่อให้ครั้งต่อไปที่แอปโหลดข้อมูล จะได้ข้อมูลล่าสุด
        if hasattr(load_portfolios_from_gsheets, 'clear'):
            load_portfolios_from_gsheets.clear()
        
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอัปเดตพอร์ต: {e}")
        return False
# (วางโค้ดนี้ต่อท้ายในไฟล์ core/gs_handler.py)

def load_actual_positions_from_gsheets():
    """
    [ฟังก์ชันใหม่] โหลดข้อมูล Positions ทั้งหมดจาก Google Sheets
    """
    gc = get_gspread_client()
    if gc is None:
        print("Warning: GSpread client not available for loading actual positions.")
        return pd.DataFrame()
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME)
        worksheet = sh.worksheet(settings.WORKSHEET_ACTUAL_POSITIONS)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        
        if not records:
            return pd.DataFrame()
        
        df_positions = pd.DataFrame(records)
        
        if 'PortfolioID' in df_positions.columns:
            df_positions['PortfolioID'] = df_positions['PortfolioID'].astype(str)
            
        return df_positions
    except gspread.exceptions.WorksheetNotFound:
        print(f"Warning: Worksheet '{settings.WORKSHEET_ACTUAL_POSITIONS}' not found.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Unexpected error loading actual positions: {e}")
        return pd.DataFrame()