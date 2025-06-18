# core/gs_handler.py (ฉบับแก้ไขสมบูรณ์)
import streamlit as st
import pandas as pd
import numpy as np
import gspread
from datetime import datetime
import uuid

from config import settings
from config.settings import (
    WORKSHEET_STATEMENT_SUMMARIES,
    WORKSHEET_ACTUAL_ORDERS,
    WORKSHEET_ACTUAL_POSITIONS,
    WORKSHEET_ACTUAL_TRADES,
    WORKSHEET_PORTFOLIOS,
    WORKSHEET_PLANNED_LOGS
)

# ============== GOOGLE SHEETS UTILITY FUNCTIONS ==============

@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" not in st.secrets:
            st.warning("⚠️ โปรดตั้งค่า 'gcp_service_account' ใน `.streamlit/secrets.toml` เพื่อเชื่อมต่อ Google Sheets.")
            return None
        return gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
        st.info("ตรวจสอบว่า 'gcp_service_account' ใน secrets.toml ถูกต้อง และได้แชร์ Sheet กับ Service Account แล้ว")
        return None

def setup_and_get_worksheets(gc_client):
    """
    Opens the main spreadsheet and ensures all required worksheets exist and have correct headers.
    Returns a dictionary of worksheet objects.
    [แก้ไข] เพิ่มการ re-fetch worksheet object หลังจากการสร้างใหม่ เพื่อความเสถียร
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
                    # VVVVVV [ส่วนที่แก้ไข] VVVVVV
                    # 1. สร้างชีตใหม่
                    sh.add_worksheet(title=ws_name, rows="1000", cols=len(headers) + 5)
                    # 2. **เรียกชีตที่เพิ่งสร้างอีกครั้ง** เพื่อให้ได้ object ที่สมบูรณ์
                    new_ws = sh.worksheet(ws_name)
                    # 3. อัปเดต Headers ใน object ใหม่
                    new_ws.update([headers], value_input_option='USER_ENTERED')
                    # 4. เก็บ object ใหม่ที่สมบูรณ์แล้ว
                    ws_dict[ws_name] = new_ws
                    # ^^^^^^ [สิ้นสุดส่วนที่แก้ไข] ^^^^^^
                except Exception as e_add_ws:
                    return None, f"❌ Failed to create worksheet '{ws_name}': {e_add_ws}"
            except Exception as e_open_ws:
                return None, f"❌ Error accessing worksheet '{ws_name}': {e_open_ws}"
        return ws_dict, None # Return dict and no error
    except Exception as e_setup:
        return None, f"❌ เกิดข้อผิดพลาดในการเข้าถึง Spreadsheet: {e_setup}"

# --- LOAD FUNCTIONS ---
@st.cache_data(ttl=300)
def load_portfolios_from_gsheets():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME)
        worksheet = sh.worksheet(settings.WORKSHEET_PORTFOLIOS)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        # Data type conversions...
        cols_to_numeric = {
            'InitialBalance': float, 'ProfitTargetPercent': float, 'DailyLossLimitPercent': float, 
            'TotalStopoutPercent': float, 'Leverage': float, 'MinTradingDays': int,
            'OverallProfitTarget': float, 'WeeklyProfitTarget': float, 'DailyProfitTarget': float,
            'MaxAcceptableDrawdownOverall': float, 'MaxAcceptableDrawdownDaily': float,
            'ScaleUp_MinWinRate': float, 'ScaleUp_MinGainPercent': float, 'ScaleUp_RiskIncrementPercent': float,
            'ScaleDown_MaxLossPercent': float, 'ScaleDown_LowWinRate': float, 'ScaleDown_RiskDecrementPercent': float,
            'MinRiskPercentAllowed': float, 'MaxRiskPercentAllowed': float, 'CurrentRiskPercent': float
        }
        for col, target_type in cols_to_numeric.items():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].replace('', np.nan), errors='coerce').fillna(0)
                if target_type == int: df[col] = df[col].astype(int)
        if 'EnableScaling' in df.columns:
            df['EnableScaling'] = df['EnableScaling'].astype(str).str.upper().map({'TRUE': True, 'YES': True, '1': True, 'FALSE': False, 'NO': False, '0': False}).fillna(False)
        for col in ['CompetitionEndDate', 'TargetEndDate', 'CreationDate']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        return df
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการโหลด Portfolios: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=180)
def load_all_planned_trade_logs_from_gsheets():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_PLANNED_LOGS)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        if 'Timestamp' in df.columns: df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        for col in ['Risk $', 'RR', 'Entry', 'SL', 'TP', 'Lot', 'Risk %']:
            if col in df.columns: df[col] = pd.to_numeric(df[col].replace('', np.nan), errors='coerce')
        if 'PortfolioID' in df.columns: df['PortfolioID'] = df['PortfolioID'].astype(str)
        return df
    except Exception as e:
        print(f"Warning loading planned logs: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=180)
def load_actual_trades_from_gsheets():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_ACTUAL_TRADES)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        if 'Time_Deal' in df.columns: df['Time_Deal'] = pd.to_datetime(df['Time_Deal'], errors='coerce')
        for col in ['Volume_Deal', 'Price_Deal', 'Commission_Deal', 'Fee_Deal', 'Swap_Deal', 'Profit_Deal', 'Balance_Deal']:
            if col in df.columns: df[col] = pd.to_numeric(df[col].replace('', np.nan), errors='coerce')
        if 'PortfolioID' in df.columns: df['PortfolioID'] = df['PortfolioID'].astype(str)
        return df
    except Exception as e:
        print(f"Warning loading actual trades: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=180)
def load_statement_summaries_from_gsheets():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_STATEMENT_SUMMARIES)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        if 'PortfolioID' in df.columns: df['PortfolioID'] = df['PortfolioID'].astype(str)
        if 'Equity' in df.columns: df['Equity'] = pd.to_numeric(df['Equity'].astype(str).str.replace(',', '', regex=False), errors='coerce')
        if 'Timestamp' in df.columns: df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        return df
    except Exception as e:
        print(f"Warning loading summaries: {e}")
        return pd.DataFrame()

# --- SAVE FUNCTIONS ---

def save_new_portfolio_to_gsheets(portfolio_data_dict):
    gc = get_gspread_client()
    if not gc:
        st.error("ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่อบันทึกพอร์ตได้")
        return False
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME)
        ws = sh.worksheet(settings.WORKSHEET_PORTFOLIOS)
        headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_PORTFOLIOS]
        new_row = [str(portfolio_data_dict.get(h, "")).strip() for h in headers]
        ws.append_row(new_row, value_input_option='USER_ENTERED')
        load_portfolios_from_gsheets.clear()
        return True
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกพอร์ตใหม่: {e}")
        return False

def save_plan_to_gsheets(plan_data_list, trade_mode_arg, asset_name, risk_percentage, trade_direction, portfolio_id, portfolio_name):
    gc = get_gspread_client()
    if not gc:
        st.error("ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่อบันทึกแผนได้")
        return False
    try:
        ws = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_PLANNED_LOGS)
        headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_PLANNED_LOGS]
        ts_now = datetime.now()
        rows_to_append = []
        for i, entry in enumerate(plan_data_list):
            log_id = f"{ts_now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}-{i}"
            row_dict = {
                "LogID": log_id, "PortfolioID": str(portfolio_id), "PortfolioName": str(portfolio_name),
                "Timestamp": ts_now.strftime("%Y-%m-%d %H:%M:%S"), "Asset": str(asset_name),
                "Mode": str(trade_mode_arg), "Direction": str(trade_direction),
                "Risk %": str(risk_percentage), **entry
            }
            rows_to_append.append([str(row_dict.get(h, "")) for h in headers])
        if rows_to_append:
            ws.append_rows(rows_to_append, value_input_option='USER_ENTERED')
            load_all_planned_trade_logs_from_gsheets.clear()
            return True
        return False
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกแผน: {e}")
        return False

# --- STATEMENT SAVE FUNCTIONS (CLEANED UP) ---

def _save_transactional_data(ws, df_input, unique_id_col, expected_headers_with_portfolio, data_type_name, portfolio_id, portfolio_name, source_file_name="N/A", import_batch_id="N/A"):
    """
    [Original Robust Logic] Saves transactional data to a worksheet, with robust deduplication.
    This version reads existing records into a DataFrame to ensure accurate type comparison.
    """
    if df_input is None or df_input.empty:
        return True, 0, 0
    try:
        if ws is None:
            st.error(f"Worksheet for {data_type_name} is not available.")
            return False, 0, 0
            
        # Check and write headers if necessary
        current_headers = ws.row_values(1) if ws.row_count > 0 else []
        if not current_headers or set(current_headers) != set(expected_headers_with_portfolio):
            ws.update([expected_headers_with_portfolio], value_input_option='USER_ENTERED')

        # [LOGIC เดิม] ใช้ get_all_records และ .astype(str).str.strip() เพื่อความแม่นยำในการเช็คซ้ำ
        existing_ids = set()
        if ws.row_count > 1:
            try:
                all_sheet_records = ws.get_all_records(expected_headers=expected_headers_with_portfolio, numericise_ignore=['all'])
                if all_sheet_records:
                    df_existing = pd.DataFrame(all_sheet_records)
                    if 'PortfolioID' in df_existing.columns and unique_id_col in df_existing.columns:
                        df_existing['PortfolioID'] = df_existing['PortfolioID'].astype(str)
                        df_portfolio_data = df_existing[df_existing['PortfolioID'] == str(portfolio_id)]
                        if not df_portfolio_data.empty:
                            # Standardize to clean strings before creating the set
                            existing_ids = set(df_portfolio_data[unique_id_col].astype(str).str.strip().tolist())
            except Exception as e:
                st.warning(f"Could not get existing IDs for {data_type_name} to check duplicates: {e}")

        df_to_check = df_input.copy()
        
        # Standardize the incoming data's ID column to clean string for comparison
        df_to_check[unique_id_col] = df_to_check[unique_id_col].astype(str).str.strip()
        
        new_df = df_to_check[~df_to_check[unique_id_col].isin(existing_ids)]
        
        num_new = len(new_df)
        num_skipped = len(df_to_check) - num_new

        if new_df.empty:
            return True, 0, num_skipped

        new_df_to_save = new_df.copy()
        new_df_to_save["PortfolioID"] = str(portfolio_id)
        new_df_to_save["PortfolioName"] = str(portfolio_name)
        new_df_to_save["SourceFile"] = str(source_file_name)
        new_df_to_save["ImportBatchID"] = str(import_batch_id)
        
        # Ensure all columns exist before converting to list
        final_df = pd.DataFrame(columns=expected_headers_with_portfolio)
        for col in expected_headers_with_portfolio:
            if col in new_df_to_save.columns:
                final_df[col] = new_df_to_save[col]
            else:
                final_df[col] = ""
                
        list_of_lists = final_df.astype(str).replace('nan', '').replace('None', '').fillna("").values.tolist()
        
        if list_of_lists:
            ws.append_rows(list_of_lists, value_input_option='USER_ENTERED')
            
        return True, num_new, num_skipped
    except Exception as e:
        st.error(f"Error saving {data_type_name} to GSheets: {e}")
        return False, 0, 0

def save_deals_to_actual_trades(ws, df_deals_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    st.info("DEBUG: DataFrame being sent to save 'Deals':") # <-- [เพิ่ม] บรรทัดดีบัก 1
    st.dataframe(df_deals_input)
    expected_headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_ACTUAL_TRADES]
    return _save_transactional_data(ws, df_deals_input, "Deal_ID", expected_headers, "Deals", portfolio_id, portfolio_name, source_file_name, import_batch_id)

def save_orders_to_gsheets(ws, df_orders_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    expected_headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_ACTUAL_ORDERS]
    return _save_transactional_data(ws, df_orders_input, "Order_ID_Ord", expected_headers, "Orders", portfolio_id, portfolio_name, source_file_name, import_batch_id)

def save_positions_to_gsheets(ws, df_positions_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    # This function is kept for structural consistency, even if 'positions' are processed into 'deals' earlier.
    # It will simply receive an empty DataFrame and do nothing, which is correct.
    expected_headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_ACTUAL_POSITIONS]
    return _save_transactional_data(ws, df_positions_input, "Position_ID", expected_headers, "Positions", portfolio_id, portfolio_name, source_file_name, import_batch_id)

def save_results_summary_to_gsheets(ws, balance_summary_data, results_summary_data, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    # This function is also ported from the robust original version
    try:
        if ws is None: return False, "Worksheet object is None"
        
        expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_STATEMENT_SUMMARIES]
        current_headers = ws.row_values(1) if ws.row_count > 0 else []
        if not current_headers or set(current_headers) != set(expected_headers):
            ws.update([expected_headers], value_input_option='USER_ENTERED')

        new_row_data = {h: "" for h in expected_headers}
        new_row_data.update({
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "PortfolioID": str(portfolio_id), "PortfolioName": str(portfolio_name),
            "SourceFile": str(source_file_name), "ImportBatchID": str(import_batch_id)
        })

        if isinstance(balance_summary_data, dict):
             # Mapping to match the Google Sheet headers
            balance_key_map = {
                "balance": "Balance", "equity": "Equity", "free_margin": "Free_Margin",
                "margin": "Margin", "floating_p_l": "Floating_P_L", "margin_level": "Margin_Level",
                "credit_facility": "Credit_Facility"
            }
            for k_extract, k_gsheet in balance_key_map.items():
                if k_extract in balance_summary_data:
                    new_row_data[k_gsheet] = balance_summary_data[k_extract]
        
        if isinstance(results_summary_data, dict):
            for key, value in results_summary_data.items():
                if key in new_row_data:
                    new_row_data[key] = value

        # Deduplication logic for summaries can be added here if necessary
        # For now, we append the new summary.
        
        final_row_values = [str(new_row_data.get(h, "")).strip() for h in expected_headers]
        ws.append_row(final_row_values, value_input_option='USER_ENTERED')
        
        load_statement_summaries_from_gsheets.clear()
        return True, "saved_new"
    except Exception as e:
        st.error(f"Error saving results summary: {e}")
        return False, str(e)
