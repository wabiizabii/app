# core/gs_handler.py (แก้ไข StreamlitSetPageConfigMustBeFirstCommandError อย่างเด็ดขาด)
import streamlit as st
import pandas as pd
import numpy as np
import gspread
import traceback
from datetime import datetime, timedelta
import uuid
from functools import cache
# IMPORT STREAMLIT ONLY FOR CACHE DECORATORS AND SECRETS, NOT FOR DISPLAY COMMANDS IN CORE LOGIC
import streamlit as st 

from config import settings
from config.settings import (
    WORKSHEET_STATEMENT_SUMMARIES, WORKSHEET_ACTUAL_ORDERS,
    WORKSHEET_ACTUAL_POSITIONS, WORKSHEET_ACTUAL_TRADES,
    WORKSHEET_PORTFOLIOS, WORKSHEET_PLANNED_LOGS, WORKSHEET_UPLOAD_HISTORY,
    WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS
)

# ============== GOOGLE SHEETS UTILITY FUNCTIONS ==============

@st.cache_resource
def get_gspread_client():
    """
    Initializes and returns a gspread client using Streamlit secrets.
    """
    try:
        if "gcp_service_account" not in st.secrets:
            # Removed st.error. Will print to console.
            print("ERROR: [get_gspread_client] 'gcp_service_account' not set in .streamlit/secrets.toml")
            return None
        return gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    except Exception as e:
        print(f"ERROR: [get_gspread_client] เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
        traceback.print_exc()
        return None

_GS_WORKSHEETS_GLOBAL_SETUP_DONE = False

def setup_and_get_worksheets(gc_client):
    """
    [เวอร์ชันสมบูรณ์] เปิด Spreadsheet และตรวจสอบว่าชีตทั้งหมดที่กำหนดใน settings.WORKSHEET_HEADERS มีอยู่จริง
    ถ้าไม่มี จะสร้างขึ้นมาใหม่พร้อมกับ Header ที่ถูกต้อง
    """
    global _GS_WORKSHEETS_GLOBAL_SETUP_DONE 

    if _GS_WORKSHEETS_GLOBAL_SETUP_DONE:
        ws_dict = {}
        try:
            sh = gc_client.open(settings.GOOGLE_SHEET_NAME)
            for ws_name in settings.WORKSHEET_HEADERS.keys():
                ws_dict[ws_name] = sh.worksheet(ws_name)
            # print(f"DEBUG: [setup] Setup previously done. Re-fetched worksheets.") # Optional debug
            return ws_dict, None
        except Exception as e:
            _GS_WORKSHEETS_GLOBAL_SETUP_DONE = False # Reset if re-fetching fails
            print(f"WARNING: [setup] Re-fetching worksheets failed ({e}). Attempting full setup again.")


    if not gc_client:
        return None, "Google Sheets client not available."
    
    ws_dict = {}
    try:
        sh = gc_client.open(settings.GOOGLE_SHEET_NAME)
        print(f"DEBUG: [setup] เชื่อมต่อกับ Google Sheet: '{settings.GOOGLE_SHEET_NAME}' สำเร็จ.")
        
        for ws_name, headers in settings.WORKSHEET_HEADERS.items():
            try:
                worksheet = sh.worksheet(ws_name)
                ws_dict[ws_name] = worksheet
                print(f"DEBUG: [setup] พบชีต '{ws_name}'.")
                
                current_headers = worksheet.row_values(1)
                if not current_headers or set(current_headers) != set(headers):
                    print(f"DEBUG: [setup] Header ของชีต '{ws_name}' ไม่ตรงกับที่คาดหวัง. กำลังอัปเดต Header...")
                    worksheet.update([headers], value_input_option='USER_ENTERED')
                    print(f"DEBUG: [setup] อัปเดต Header ชีต '{ws_name}' สำเร็จ.")
                else:
                    print(f"DEBUG: [setup] Header ชีต '{ws_name}' ตรงกับที่คาดหวัง.")

            except gspread.exceptions.WorksheetNotFound:
                print(f"DEBUG: [setup] ไม่พบชีต '{ws_name}' กำลังสร้างขึ้นมาใหม่พร้อม Header...")
                new_worksheet = sh.add_worksheet(title=ws_name, rows="1", cols=len(headers))
                new_worksheet.update([headers], value_input_option='USER_ENTERED')
                ws_dict[ws_name] = new_worksheet
                print(f"DEBUG: [setup] สร้างชีต '{ws_name}' สำเร็จ!")

        _GS_WORKSHEETS_GLOBAL_SETUP_DONE = True
        return ws_dict, None
        
    except gspread.exceptions.SpreadsheetNotFound:
        error_msg = f"ไม่พบ Google Sheet ที่ชื่อ '{settings.GOOGLE_SHEET_NAME}'. โปรดตรวจสอบชื่อและสิทธิ์การเข้าถึง."
        print(f"ERROR: [setup] {error_msg}")
        traceback.print_exc()
        return None, error_msg
    except Exception as e:
        print(f"ERROR: [setup] เกิดข้อผิดพลาดร้ายแรงในการตั้งค่า Google Sheets: {e}")
        traceback.print_exc()
        return None, str(e)


# --- WRAPPER FOR LOAD FUNCTIONS TO ENSURE SHEETS EXIST ---
@cache
def _load_data_with_sheet_check(worksheet_name, load_func_callback):
    """
    A wrapper to ensure a worksheet exists before attempting to load data.
    If WorksheetNotFound, it triggers setup_and_get_worksheets once.
    """
    try:
        return load_func_callback()
    except gspread.exceptions.WorksheetNotFound:
        print(f"DEBUG: [LoadWrapper] ชีต '{worksheet_name}' ไม่พบเมื่อโหลดข้อมูล. กำลังลองสร้าง/ตั้งค่าชีตทั้งหมด...")
        gc = get_gspread_client()
        if gc:
            global _GS_WORKSHEETS_GLOBAL_SETUP_DONE
            _GS_WORKSHEETS_GLOBAL_SETUP_DONE = False # Temporarily reset to force full setup
            ws_dict, setup_error = setup_and_get_worksheets(gc)
            if setup_error:
                print(f"ERROR: [LoadWrapper] ข้อผิดพลาดในการตั้งค่าชีต '{worksheet_name}' หลังการโหลด: {setup_error}")
                return pd.DataFrame()
            else:
                print(f"DEBUG: [LoadWrapper] ชีต '{worksheet_name}' และอื่นๆ ถูกตั้งค่าแล้ว. กำลังล้างแคชและลองโหลดข้อมูลอีกครั้ง...")
                # Clear all inner load caches
                load_portfolios_from_gsheets_inner.clear()
                load_all_planned_trade_logs_from_gsheets_inner.clear()
                load_actual_trades_from_gsheets_inner.clear()
                load_statement_summaries_from_gsheets_inner.clear()
                load_upload_history_from_gsheets_inner.clear()
                load_deposit_withdrawal_logs_from_gsheets_inner.clear()
                
                return load_func_callback()
        else:
            print("ERROR: [LoadWrapper] ไม่สามารถเชื่อมต่อ Google Client เพื่อสร้างชีตได้.")
            return pd.DataFrame()
    except Exception as e:
        print(f"ERROR: [LoadWrapper] เกิดข้อผิดพลาดในการโหลดข้อมูลสำหรับชีต '{worksheet_name}': {e}")
        traceback.print_exc()
        return pd.DataFrame()


# --- LOAD FUNCTIONS (Now wrapped with _load_data_with_sheet_check) ---
@st.cache_data(ttl=300)
def load_portfolios_from_gsheets_inner():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME)
        worksheet = sh.worksheet(settings.WORKSHEET_PORTFOLIOS)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
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
        print(f"Warning loading portfolios: {e}")
        return pd.DataFrame()
@cache
def load_portfolios_from_gsheets():
    return _load_data_with_sheet_check(settings.WORKSHEET_PORTFOLIOS, load_portfolios_from_gsheets_inner)


@st.cache_data(ttl=180)
def load_all_planned_trade_logs_from_gsheets_inner():
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

def load_all_planned_trade_logs_from_gsheets():
    return _load_data_with_sheet_check(settings.WORKSHEET_PLANNED_LOGS, load_all_planned_trade_logs_from_gsheets_inner)


@st.cache_data(ttl=180)
def load_actual_trades_from_gsheets_inner():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(WORKSHEET_ACTUAL_TRADES)
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
@cache
@st.cache_data(ttl=180)
def load_actual_trades_from_gsheets():
    # VVVV ส่วนนี้ทั้งหมดคือ "เนื้อหาของฟังก์ชัน" ที่คุณไม่ต้องแก้ไขอะไรเลย VVVV
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(WORKSHEET_ACTUAL_TRADES)
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
    # ^^^^ สิ้นสุด "เนื้อหาของฟังก์ชัน" ^^^^


@st.cache_data(ttl=180)
def load_statement_summaries_from_gsheets_inner():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(WORKSHEET_STATEMENT_SUMMARIES)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        if 'PortfolioID' in df.columns: df['PortfolioID'] = df['PortfolioID'].astype(str)
        numeric_cols_summary = [
            'Balance', 'Equity', 'Free_Margin', 'Margin', 'Floating_P_L', 'Margin_Level', 'Credit_Facility',
            'Deposit', 'Withdrawal', 'Gross_Profit', 'Gross_Loss', 'Total_Net_Profit', 'Profit_Factor',
            'Recovery_Factor', 'Expected_Payoff', 'Sharpe_Ratio', 'Balance_Drawdown_Absolute',
            'Maximal_Drawdown_Value', 'Maximal_Drawdown_Percent', 'Balance_Drawdown_Relative_Percent',
            'Balance_Drawdown_Relative_Value', 'Total_Trades', 'Profit_Trades_Count', 'Profit_Trades_Percent',
            'Loss_Trades_Count', 'Loss_Trades_Percent', 'Long_Trades_Count', 'Long_Trades_Won_Percent',
            'Short_Trades_Count', 'Short_Trades_Won_Percent', 'Largest_Profit_Trade', 'Average_Profit_Trade',
            'Largest_Loss_Trade', 'Average_Loss_Trade', 'Max_Consecutive_Wins_Count', 'Max_Consecutive_Wins_Profit',
            'Maximal_Consecutive_Profit_Value', 'Maximal_Consecutive_Profit_Count', 'Max_Consecutive_Losses_Count',
            'Max_Consecutive_Losses_Profit', 'Maximal_Consecutive_Loss_Value', 'Maximal_Consecutive_Loss_Count',
            'Average_Consecutive_Wins', 'Average_Consecutive_Losses'
        ]
        for col in numeric_cols_summary:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '', regex=False).replace('%', '', regex=False), errors='coerce').fillna(0)
        
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        return df
    except Exception as e:
        print(f"Warning loading summaries: {e}")
        traceback.print_exc()
        return pd.DataFrame()
@cache
def load_statement_summaries_from_gsheets():
    return _load_data_with_sheet_check(settings.WORKSHEET_STATEMENT_SUMMARIES, load_statement_summaries_from_gsheets_inner)


@st.cache_data(ttl=180)
def load_upload_history_from_gsheets_inner():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(WORKSHEET_UPLOAD_HISTORY)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        if 'PortfolioID' in df.columns: df['PortfolioID'] = df['PortfolioID'].astype(str)
        if 'FileHash' in df.columns: df['FileHash'] = df['FileHash'].astype(str)
        return df
    except Exception as e:
        print(f"Warning loading upload history: {e}")
        return pd.DataFrame()
@cache
def load_upload_history_from_gsheets():
    return _load_data_with_sheet_check(settings.WORKSHEET_UPLOAD_HISTORY, load_upload_history_from_gsheets_inner)


@st.cache_data(ttl=180)
def load_deposit_withdrawal_logs_from_gsheets_inner():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        if 'DateTime' in df.columns: df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        for col in ['Amount']: # Changed from ['Amount'] to ['Amount']
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'PortfolioID' in df.columns: df['PortfolioID'] = df['PortfolioID'].astype(str)
        if 'TransactionID' in df.columns: df['TransactionID'] = df['TransactionID'].astype(str)
        return df
    except Exception as e:
        print(f"Warning loading deposit/withdrawal logs: {e}")
        return pd.DataFrame()
@cache
def load_deposit_withdrawal_logs_from_gsheets():
    return _load_data_with_sheet_check(settings.WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS, load_deposit_withdrawal_logs_from_gsheets_inner)

# --- SAVE FUNCTIONS ---

def save_new_portfolio_to_gsheets(portfolio_data_dict):
    gc = get_gspread_client()
    if not gc:
        print("ERROR: ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่อบันทึกพอร์ตได้.")
        return False
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME)
        ws = sh.worksheet(settings.WORKSHEET_PORTFOLIOS)
        headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_PORTFOLIOS]
        new_row = [str(portfolio_data_dict.get(h, "")).strip() for h in headers]
        ws.append_row(new_row, value_input_option='USER_ENTERED')
        load_portfolios_from_gsheets.cache_clear()
        return True
    except Exception as e:
        print(f"ERROR: เกิดข้อผิดพลาดในการบันทึกพอร์ตใหม่: {e}")
        traceback.print_exc()
        return False

def update_portfolio_in_gsheets(portfolio_id, updated_data_dict):
    """
    อัปเดตข้อมูลของพอร์ตที่มีอยู่แล้วใน Google Sheets
    """
    gc = get_gspread_client()
    if not gc:
        print("ERROR: ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่ออัปเดตพอร์ตได้.")
        return False
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME)
        ws = sh.worksheet(settings.WORKSHEET_PORTFOLIOS)
        cell = ws.find(portfolio_id, in_column=1)
        if not cell:
            print(f"ERROR: ไม่พบพอร์ตที่มี ID: {portfolio_id} สำหรับการอัปเดต.")
            return False
        print(f"INFO: Found portfolio to update at row {cell.row}")
        headers = ws.row_values(1)
        if not headers:
            print("ERROR: ไม่พบคอลัมน์ Headers ในชีต Portfolios.")
            return False
        updated_row = [str(updated_data_dict.get(h, "")).strip() for h in headers]
        ws.update(f'A{cell.row}', [updated_row], value_input_option='USER_ENTERED')
        load_portfolios_from_gsheets.clear()
        print(f"INFO: Portfolio ID {portfolio_id} updated successfully.")
        return True
    except gspread.exceptions.CellNotFound:
        print(f"ERROR: ไม่พบพอร์ตที่มี ID: {portfolio_id} สำหรับการอัปเดต.")
        return False
    except Exception as e:
        print(f"ERROR: เกิดข้อผิดพลาดในการอัปเดตพอร์ต: {e}")
        traceback.print_exc()
        return False
    
def save_plan_to_gsheets(plan_data_list, trade_mode_arg, asset_name, risk_percentage, trade_direction, portfolio_id, portfolio_name):
    gc = get_gspread_client()
    if not gc:
        print("ERROR: ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่อบันทึกแผนได้.")
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
        print(f"ERROR: เกิดข้อผิดพลาดในการบันทึกแผน: {e}")
        traceback.print_exc()
        return False

# --- Core Transactional Data Save Helper (for Deals, Orders, Positions) ---
def _save_transactional_data(ws, df_input, unique_id_col, expected_headers, data_type_name, portfolio_id, portfolio_name, source_file_name="N/A", import_batch_id="N/A"):
    """
    [Adapted from Old Version] - บันทึกข้อมูล Transactional โดยใช้โลจิกการเช็คข้อมูลซ้ำที่เรียบง่ายและเสถียร
    """
    if df_input is None or df_input.empty:
        return True, "No data to save.", 0, 0

    try:
        if ws is None:
            return False, f"Worksheet for {data_type_name} is not available.", 0, 0

        # --- โลจิกการตรวจสอบข้อมูลซ้ำแบบเวอร์ชันเก่า ---
        # 1. โหลดข้อมูลทั้งหมดที่มีอยู่แล้วในชีต
        existing_records = ws.get_all_records(numericise_ignore=['all'])
        existing_ids = set()

        if existing_records:
            df_existing = pd.DataFrame(existing_records)
            # 2. กรองให้เหลือเฉพาะพอร์ตที่สนใจ และสร้าง Set ของ ID ที่มีอยู่
            if not df_existing.empty and 'PortfolioID' in df_existing.columns and unique_id_col in df_existing.columns:
                df_portfolio_data = df_existing[df_existing['PortfolioID'].astype(str) == str(portfolio_id)]
                if not df_portfolio_data.empty:
                    existing_ids = set(df_portfolio_data[unique_id_col].astype(str).str.strip())
        
        # 3. คัดกรองเฉพาะข้อมูลใหม่ที่ยังไม่มี ID อยู่ในชีต
        df_to_check = df_input.copy()
        df_to_check[unique_id_col] = df_to_check[unique_id_col].astype(str).str.strip()
        new_df = df_to_check[~df_to_check[unique_id_col].isin(existing_ids)]
        
        num_new = len(new_df)
        num_skipped = len(df_to_check) - num_new

        if new_df.empty:
            return True, "Success", 0, num_skipped

        # 4. เตรียมข้อมูลใหม่เพื่อบันทึก
        df_to_save = new_df.copy()
        # VVVVV สำคัญ: ส่วนนี้จะทำให้มั่นใจว่า PortfolioID และ PortfolioName เป็นของระบบเสมอ VVVVV
        df_to_save["PortfolioID"] = str(portfolio_id) #
        df_to_save["PortfolioName"] = str(portfolio_name) #
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        df_to_save["SourceFile"] = str(source_file_name)
        df_to_save["ImportBatchID"] = str(import_batch_id)
        
        # จัดเรียงคอลัมน์และแปลงเป็น list เพื่อ append
        final_df = pd.DataFrame(columns=expected_headers)
        final_df = pd.concat([final_df, df_to_save], ignore_index=True)
        final_df_ordered = final_df[expected_headers] # จัดเรียงคอลัมน์ให้ตรงกับ Header
        
        list_of_lists = final_df_ordered.astype(str).replace('nan', '').fillna("").values.tolist()
        
        if list_of_lists:
            ws.append_rows(list_of_lists, value_input_option='USER_ENTERED')
            
        return True, "Success", num_new, num_skipped
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Error saving {data_type_name}: {e}", 0, len(df_input)


def save_deals_to_actual_trades(ws, df_deals_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    print(f"DEBUG: [save_deals_to_actual_trades] Called with {len(df_deals_input)} rows.")
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_TRADES]
    return _save_transactional_data(ws, df_deals_input, "Deal_ID", expected_headers, "Deals", portfolio_id, portfolio_name, source_file_name, import_batch_id)

def save_orders_to_actul_orders(ws, df_orders_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    print(f"DEBUG: [save_orders_to_actul_orders] Called with {len(df_orders_input)} rows.")
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_ORDERS]
    return _save_transactional_data(ws, df_orders_input, "Order_ID_Ord", expected_headers, "Orders", portfolio_id, portfolio_name, source_file_name, import_batch_id)

def save_positions_to_actul_positions(ws, df_positions_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    print(f"DEBUG: [save_positions_to_actul_positions] Called with {len(df_positions_input)} rows.")
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_POSITIONS]
    return _save_transactional_data(ws, df_positions_input, "Position_ID", expected_headers, "Positions", portfolio_id, portfolio_name, source_file_name, import_batch_id)

# --- Save Statement Summaries (Updated parameter list) ---
def save_results_summary_to_gsheets(ws, combined_summary_data,
                                     portfolio_id_fallback, portfolio_name_fallback, source_file_name,
                                     import_batch_id, portfolio_details_fallback=None):
    print(f"DEBUG: [save_results_summary_to_gsheets] Called with data: {combined_summary_data.get('PortfolioID', 'N/A')} for {source_file_name}.")
    try:
        if ws is None:
            print("ERROR: StatementSummaries worksheet is None.")
            return False, "StatementSummaries worksheet is None"

        expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_STATEMENT_SUMMARIES]
        current_headers = ws.row_values(1) if ws.row_count > 0 else []

        if not current_headers or set(current_headers) != set(expected_headers):
            print(f"DEBUG: [save_results_summary_to_gsheets] Headers mismatch. Updating headers.")
            ws.update([expected_headers], value_input_option='USER_ENTERED')
            current_headers = ws.row_values(1)

        new_row_data = {h: "" for h in expected_headers}

        if isinstance(combined_summary_data, dict):
            for key, value in combined_summary_data.items():
                if key in new_row_data:
                    new_row_data[key] = value
        
        if not new_row_data.get("DateTime"): new_row_data["DateTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not new_row_data.get("SourceFile"): new_row_data["SourceFile"] = str(source_file_name)
        if not new_row_data.get("ImportBatchID"): new_row_data["ImportBatchID"] = str(import_batch_id)

        # VVVVV สำคัญ: ส่วนนี้จะทำให้มั่นใจว่า PortfolioID และ PortfolioName เป็นของระบบเสมอ VVVVV
        if not new_row_data.get("PortfolioID") or new_row_data.get("PortfolioID") == 'N/A': 
            new_row_data["PortfolioID"] = str(portfolio_id_fallback) #
        else: # หากมี PortfolioID มาจาก combined_summary_data (ซึ่งอาจมาจากไฟล์ดิบ) ให้ใช้ของระบบแทน
            new_row_data["PortfolioID"] = str(portfolio_id_fallback) #

        if not new_row_data.get("PortfolioName") or new_row_data.get("PortfolioName") == 'N/A':
            new_row_data["PortfolioName"] = str(portfolio_name_fallback) #
        else: # หากมี PortfolioName มาจาก combined_summary_data (ซึ่งอาจมาจากไฟล์ดิบ) ให้ใช้ของระบบแทน
            new_row_data["PortfolioName"] = str(portfolio_name_fallback) #
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        if not new_row_data.get("ClientName") and portfolio_details_fallback:
            new_row_data["ClientName"] = str(portfolio_details_fallback.get('client_name', ''))


        final_row_values = [str(new_row_data.get(h, "")).strip() for h in expected_headers]
        print(f"DEBUG: [save_results_summary_to_gsheets] Final row values prepared: {final_row_values}")

        existing_summaries_df = load_statement_summaries_from_gsheets()
        
        is_duplicate = False
        if not existing_summaries_df.empty:
            existing_summaries_df['PortfolioID'] = existing_summaries_df['PortfolioID'].astype(str)
            existing_summaries_df['SourceFile'] = existing_summaries_df['SourceFile'].astype(str)
            existing_summaries_df['ImportBatchID'] = existing_summaries_df['ImportBatchID'].astype(str)

            is_duplicate = ((existing_summaries_df['PortfolioID'] == new_row_data["PortfolioID"]) &
                            (existing_summaries_df['SourceFile'] == new_row_data["SourceFile"]) &
                            (existing_summaries_df['ImportBatchID'] == new_row_data["ImportBatchID"])).any()
            if is_duplicate:
                print(f"DEBUG: [save_results_summary_to_gsheets] Skipping duplicate Summary: {new_row_data['PortfolioID']}/{source_file_name}.")
                return False, "duplicate_summary"

        ws.append_row(final_row_values, value_input_option='USER_ENTERED')
        print(f"DEBUG: [save_results_summary_to_gsheets] Successfully appended summary row.")

        if 'load_statement_summaries_from_gsheets' in globals() and hasattr(load_statement_summaries_from_gsheets, 'clear'):
            load_statement_summaries_from_gsheets.clear()

        return True, "saved_new"
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR: Error saving results summary: {e}")
        return False, str(e)


# --- Save Upload History (Updated for consistency with settings) ---

def save_upload_history(ws, history_log_data):
    print(f"DEBUG: [save_upload_history] Called for {history_log_data.get('FileName', 'N/A')}.")
    try:
        if ws is None: 
            print("ERROR: UploadHistory worksheet is None.")
            return False, "UploadHistory worksheet is None"

        expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_UPLOAD_HISTORY]
        current_headers = ws.row_values(1)
        if not current_headers or set(current_headers) != set(expected_headers):
            print(f"DEBUG: [save_upload_history] Headers mismatch. Updating headers.")
            ws.update([expected_headers], value_input_option='USER_ENTERED')

        row_to_insert = [str(history_log_data.get(h, "")).strip() for h in expected_headers]
        ws.append_row(row_to_insert, value_input_option='USER_ENTERED')
        print(f"DEBUG: [save_upload_history] Successfully appended history row.")
        
        load_upload_history_from_gsheets.cache_clear()
        return True, "History saved"
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR: Error saving upload history: {e}")
        return False, str(e)


# --- NEW: Save Itemized Deposit/Withdrawal Logs ---
def save_deposit_withdrawal_logs(ws, deposit_withdrawal_logs, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    print(f"DEBUG: [save_deposit_withdrawal_logs] Called with {len(deposit_withdrawal_logs)} items.")
    try:
        if ws is None: 
            print("ERROR: DepositWithdrawalLogs worksheet is None.")
            return False, "DepositWithdrawalLogs worksheet is None", 0, 0
        if not deposit_withdrawal_logs: 
            print("DEBUG: [save_deposit_withdrawal_logs] deposit_withdrawal_logs is empty. Skipping save.")
            return True, "No deposit/withdrawal logs to save", 0, 0

        expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS]
        current_headers = ws.row_values(1)
        if not current_headers or set(current_headers) != set(expected_headers):
            print(f"DEBUG: [save_deposit_withdrawal_logs] Headers mismatch. Updating headers.")
            ws.update([expected_headers], value_input_option='USER_ENTERED')

        logs_to_upload = []
        existing_logs_df = load_deposit_withdrawal_logs_from_gsheets()

        existing_composite_ids = set()
        if not existing_logs_df.empty:
            existing_logs_df['TransactionID'] = existing_logs_df['TransactionID'].astype(str)
            existing_logs_df['PortfolioID'] = existing_logs_df['PortfolioID'].astype(str)
            existing_logs_df['ImportBatchID'] = existing_logs_df['ImportBatchID'].astype(str)

            existing_logs_df['composite_id'] = existing_logs_df['TransactionID'] + '_' + \
                                               existing_logs_df['PortfolioID'] + '_' + \
                                               existing_logs_df['ImportBatchID']
            existing_composite_ids = set(existing_logs_df['composite_id'].tolist())
            print(f"DEBUG: [save_deposit_withdrawal_logs] Loaded {len(existing_composite_ids)} existing unique IDs for deduplication.")


        for log_entry in deposit_withdrawal_logs:
            transaction_id = str(log_entry.get('TransactionID', ''))
            if not transaction_id or transaction_id.strip() == '':
                transaction_id = str(uuid.uuid4())

            current_composite_id = f"{transaction_id}_{portfolio_id}_{import_batch_id}"

            if current_composite_id not in existing_composite_ids:
                row_for_gs = {h: "" for h in expected_headers}
                
                row_for_gs["TransactionID"] = transaction_id
                row_for_gs["DateTime"] = log_entry.get('DateTime', '')
                row_for_gs["Type"] = log_entry.get('Type', '')
                row_for_gs["Amount"] = log_entry.get('Amount', 0.0)
                row_for_gs["Comment"] = log_entry.get('Comment', '')

                # VVVVV สำคัญ: ส่วนนี้จะทำให้มั่นใจว่า PortfolioID และ PortfolioName เป็นของระบบเสมอ VVVVV
                row_for_gs["PortfolioID"] = str(portfolio_id) #
                row_for_gs["PortfolioName"] = str(portfolio_name) #
                # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                row_for_gs["SourceFile"] = str(source_file_name)
                row_for_gs["ImportBatchID"] = str(import_batch_id)
                
                logs_to_upload.append([str(row_for_gs.get(h, "")) for h in expected_headers])
            else:
                print(f"DEBUG: [save_deposit_withdrawal_logs] Skipping duplicate: {transaction_id}")

        num_new_saved = len(logs_to_upload)
        num_skipped = len(deposit_withdrawal_logs) - num_new_saved
        print(f"DEBUG: [save_deposit_withdrawal_logs] Preparing to upload {num_new_saved} new rows, skipped {num_skipped} duplicates.")

        if logs_to_upload:
            ws.append_rows(logs_to_upload, value_input_option='USER_ENTERED')
            print(f"DEBUG: [save_deposit_withdrawal_logs] Successfully appended {num_new_saved} rows.")
            load_deposit_withdrawal_logs_from_gsheets.cache_clear()
        
        return True, "Deposit/Withdrawal logs saved successfully", num_new_saved, num_skipped

    except Exception as e:
        traceback.print_exc()
        print(f"ERROR: Error saving deposit/withdrawal logs: {e}")
        return False, str(e), 0, 0

# --- Helper for checking portfolio ID mismatch ---
def is_portfolio_id_mismatch(account_id_from_report, active_portfolio_id_selected):
    """
    Checks if the account ID extracted from the report matches the selected portfolio ID.
    Returns True if there's a mismatch (and report ID is not N/A), False otherwise.
    """
    report_id_str = str(account_id_from_report).strip()
    selected_id_str = str(active_portfolio_id_selected).strip()

    if report_id_str and report_id_str.lower() != 'n/a' and report_id_str != selected_id_str:
        return True
    return False

# --- NEWLY ADDED: Helper for checking if a file (hash) is already uploaded ---
def is_file_already_uploaded(file_hash_to_check, portfolio_id, gc_client):
    """
    Checks the UploadHistory sheet to see if a file with the given hash
    has already been uploaded successfully for this portfolio.
    """
    print(f"DEBUG: [is_file_already_uploaded] Checking hash: {file_hash_to_check} for portfolio: {portfolio_id}")
    try:
        upload_history_df = load_upload_history_from_gsheets()

        if upload_history_df.empty:
            print("DEBUG: [is_file_already_uploaded] Upload history is empty.")
            return False, None

        upload_history_df['FileHash'] = upload_history_df['FileHash'].astype(str)
        upload_history_df['PortfolioID'] = upload_history_df['PortfolioID'].astype(str)
        
        filtered_history = upload_history_df[
            (upload_history_df['FileHash'] == file_hash_to_check) &
            (upload_history_df['PortfolioID'] == str(portfolio_id)) &
            (upload_history_df['Status'] == 'Success')
        ]
        
        if not filtered_history.empty:
            first_match = filtered_history.iloc[0]
            details = {
                "PortfolioName": first_match.get("PortfolioName", "N/A"),
                "UploadTimestamp": first_match.get("UploadTimestamp", "N/A"),
                "ImportBatchID": first_match.get("ImportBatchID", "N/A")
            }
            print(f"DEBUG: [is_file_already_uploaded] Duplicate found. Details: {details}")
            return True, details
        print("DEBUG: [is_file_already_uploaded] No duplicate found.")
        return False, None

    except Exception as e:
        print(f"ERROR: Error checking for duplicate file upload: {e}")
        traceback.print_exc()
        return False, None

def calculate_true_equity_curve(df_summaries: pd.DataFrame, portfolio_id: str):
    """
    คำนวณ True Equity Curve, Realized Net Profit, Total Deposit, Total Withdrawal
    จาก DataFrame สรุป Statement.
    """
    # กรองข้อมูลสำหรับ Portfolio ที่เลือกและเรียงตาม Timestamp
    df_filtered = df_summaries[df_summaries['PortfolioID'] == portfolio_id].sort_values(by='Timestamp').copy()

    if df_filtered.empty:
        return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0 # คืนค่าเริ่มต้นที่เหมาะสม

    # --- ตรวจสอบและแปลงประเภทข้อมูล (ซ้ำอีกครั้งเพื่อความชัวร์ใน Analytics Engine) ---
    numeric_cols = ['Balance', 'Deposit', 'Withdrawal', 'Net Profit', 'Equity']
    for col in numeric_cols:
        if col not in df_filtered.columns:
            # ถ้าคอลัมน์ไม่มี ให้สร้างและเติม 0 เพื่อป้องกัน Error ในการคำนวณ
            df_filtered[col] = 0.0
            # ใช้ st.warning เพื่อแสดงคำเตือนใน console หรือ UI ตอน debug
            st.warning(f"Analytics: คอลัมน์ '{col}' ไม่พบใน DataFrame สรุป Statement สำหรับ PortfolioID: {portfolio_id}. จะใช้ค่า 0")

    # มั่นใจว่าเป็น numeric
    df_filtered['Balance'] = pd.to_numeric(df_filtered['Balance'], errors='coerce').fillna(0)
    df_filtered['Deposit'] = pd.to_numeric(df_filtered['Deposit'], errors='coerce').fillna(0)
    df_filtered['Withdrawal'] = pd.to_numeric(df_filtered['Withdrawal'], errors='coerce').fillna(0)
    df_filtered['Net Profit'] = pd.to_numeric(df_filtered['Net Profit'], errors='coerce').fillna(0)
    df_filtered['Equity'] = pd.to_numeric(df_filtered['Equity'], errors='coerce').fillna(0)


    # --- คำนวณ Metrics ที่ต้องการ ---
    # Equity For Chart: คือ Balance ในแต่ละจุดเวลา
    df_filtered['Equity For Chart'] = df_filtered['Balance']

    # ยอดรวมเงินฝากและถอน
    total_deposit = df_filtered['Deposit'].sum()
    total_withdrawal = df_filtered['Withdrawal'].sum()

    # คำนวณ Realized Net Profit (กำไร/ขาดทุนสุทธิที่แท้จริง)
    # = (ยอด Balance สุดท้าย) - (ยอด Balance แรก) + (ยอดถอนรวม) - (ยอดฝากรวม)
    initial_balance = df_filtered['Balance'].iloc[0]
    final_balance = df_filtered['Balance'].iloc[-1]

    realized_net_profit = final_balance - initial_balance + total_withdrawal - total_deposit

    # ยอด Net Profit รวมจากคอลัมน์ Net Profit ใน Sheet (เพื่อแยกแสดง)
    total_net_profit_from_sheet = df_filtered['Net Profit'].sum()


    return df_filtered, realized_net_profit, total_deposit, total_withdrawal, total_net_profit_from_sheet

# (วางโค้ดนี้ต่อท้ายในไฟล์ core/gs_handler.py)

def link_account_id_to_portfolio(portfolios_ws, portfolio_id_to_update: str, account_id_to_link: str):
    """
    Finds a portfolio by its internal PortfolioID (UUID) and updates its AccountID field.
    This is used for the 'First-Time Link' feature.
    """
    if not portfolios_ws or not portfolio_id_to_update or not account_id_to_link:
        return False
    try:
        # Find the cell containing the portfolio's internal UUID
        cell = portfolios_ws.find(portfolio_id_to_update, in_column=1) # Assuming PortfolioID is in column 1
        if not cell:
            print(f"GS_HANDLER_ERROR: Could not find portfolio with PortfolioID '{portfolio_id_to_update}' to link.")
            return False

        # Find the column number for 'AccountID'
        headers = portfolios_ws.row_values(1)
        if 'AccountID' not in headers:
            print(f"GS_HANDLER_ERROR: 'AccountID' column not found in Portfolios sheet.")
            return False
        
        account_id_col_index = headers.index('AccountID') + 1

        # Update the AccountID cell in the found row
        portfolios_ws.update_cell(cell.row, account_id_col_index, str(account_id_to_link))
        print(f"GS_HANDLER_INFO: Successfully linked AccountID '{account_id_to_link}' to PortfolioID '{portfolio_id_to_update}'.")
        return True
        
    except Exception as e:
        print(f"GS_HANDLER_ERROR: Failed to link AccountID. Error: {e}")
        return False

def get_full_dashboard_stats(df_all_actual_trades: pd.DataFrame, df_all_summaries: pd.DataFrame, active_portfolio_id: str) -> dict:
    """
    [v2] Calculates comprehensive statistics, with robust data cleaning and fallback logic.
    - More flexible column name checking (e.g., 'Profit_Factor' vs 'Profit Factor').
    - Better data type conversion.
    - Falls back to calculated values if summary values are unavailable.
    """
    stats = {}

    # --- Part 1: Calculate core metrics from ActualTrades ---
    if not df_all_actual_trades.empty and active_portfolio_id:
        df_trades = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
        trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
        df_trades = df_trades[~df_trades['Type_Deal'].str.lower().isin(trade_types_to_exclude)]
        
        if not df_trades.empty:
            df_trades['Profit_Deal'] = pd.to_numeric(df_trades['Profit_Deal'], errors='coerce').fillna(0)
            
            # Populate basic stats from actual trades
            stats['total_trades'] = len(df_trades)
            stats['profit_trades'] = int((df_trades['Profit_Deal'] > 0).sum())
            stats['loss_trades'] = int((df_trades['Profit_Deal'] < 0).sum())
            stats['breakeven_trades'] = int((df_trades['Profit_Deal'] == 0).sum())
            
            stats['long_trades'] = int((df_trades['Direction'] == 'LONG').sum()) # Fixed from df_trades['Type_Deal'] to df_trades['Direction']
            stats['short_trades'] = int((df_trades['Direction'] == 'SHORT').sum()) # Fixed from df_trades['Type_Deal'] to df_trades['Direction']

            stats['gross_profit'] = df_trades[df_trades['Profit_Deal'] > 0]['Profit_Deal'].sum()
            stats['gross_loss'] = df_trades[df_trades['Profit_Deal'] < 0]['Profit_Deal'].sum() # This will be negative
            stats['total_net_profit'] = stats['gross_profit'] + stats['gross_loss']
            stats['win_rate'] = (stats['profit_trades'] / stats['total_trades']) * 100 if stats['total_trades'] > 0 else 0
            stats['profit_factor'] = abs(stats['gross_profit'] / stats['gross_loss']) if stats['gross_loss'] != 0 else 0.0
            stats['best_profit'] = df_trades['Profit_Deal'].max()
            stats['biggest_loss'] = df_trades['Profit_Deal'].min()
            stats['avg_profit'] = stats['gross_profit'] / stats['profit_trades'] if stats['profit_trades'] > 0 else 0
            stats['avg_loss'] = stats['gross_loss'] / stats['loss_trades'] if stats['loss_trades'] > 0 else 0
            win_rate_frac = stats.get('win_rate', 0) / 100
            stats['expectancy'] = (win_rate_frac * stats.get('avg_profit', 0)) - ((1 - win_rate_frac) * abs(stats.get('avg_loss', 0)))

            if 'Volume_Deal' in df_trades.columns:
                stats['avg_trade_size'] = pd.to_numeric(df_trades['Volume_Deal'], errors='coerce').mean()
            if 'DealDirection' in df_trades.columns and not df_trades['DealDirection'].isnull().all():
                df_trades['Direction'] = df_trades['DealDirection'].str.strip().str.upper()
            else:
                df_trades['Direction'] = np.where(df_trades['Type_Deal'].str.lower() == 'buy', 'LONG', 'SHORT')
            stats['long_trades'] = int((df_trades['Direction'] == 'LONG').sum())
            stats['short_trades'] = int((df_trades['Direction'] == 'SHORT').sum())
            if 'Time_Deal' in df_trades.columns:
                df_trades['Time_Deal'] = pd.to_datetime(df_trades['Time_Deal'], errors='coerce')
                durations = df_trades.groupby('Deal_ID')['Time_Deal'].agg(['min', 'max']) # Changed from Ticket_Deal to Deal_ID
                avg_duration_seconds = (durations['max'] - durations['min']).mean().total_seconds()
                hours, remainder = divmod(avg_duration_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                stats['avg_trade_duration_str'] = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    # --- Part 2: Override/Supplement with data from the LATEST StatementSummaries entry ---
    if not df_all_summaries.empty and active_portfolio_id:
        df_summary_filtered = df_all_summaries[df_all_summaries['PortfolioID'] == active_portfolio_id].copy()
        
        if not df_summary_filtered.empty and 'DateTime' in df_summary_filtered.columns:
            df_summary_filtered['DateTime'] = pd.to_datetime(df_summary_filtered['DateTime'], errors='coerce')
            df_summary_filtered.dropna(subset=['DateTime'], inplace=True)
            latest_summary_row = df_summary_filtered.sort_values(by='DateTime', ascending=False).iloc[0]

            # [REVISED] Helper to safely get numeric value from summary row
            def get_summary_value(keys, default_value=np.nan):
                for key in keys: # Check multiple possible column names
                    if key in latest_summary_row and pd.notna(latest_summary_row[key]):
                        val_str = str(latest_summary_row[key]).replace('$', '').replace('%', '').replace(',', '').strip()
                        if val_str: # Ensure not empty string after stripping
                            return pd.to_numeric(val_str, errors='coerce')
                return default_value

            # Override calculated stats with summary stats if they exist, otherwise keep calculated
            stats['total_trades'] = get_summary_value(['Total_Trades', 'Total Trades'], default_value=stats.get('total_trades'))
            stats['profit_trades'] = get_summary_value(['Profit_Trades_Count', 'Profit Trades'], default_value=stats.get('profit_trades'))
            stats['loss_trades'] = get_summary_value(['Loss_Trades_Count', 'Loss Trades'], default_value=stats.get('loss_trades'))
            stats['gross_profit'] = get_summary_value(['Gross_Profit', 'Gross Profit'], default_value=stats.get('gross_profit'))
            stats['gross_loss'] = get_summary_value(['Gross_Loss', 'Gross Loss'], default_value=stats.get('gross_loss'))
            stats['total_net_profit'] = get_summary_value(['Total_Net_Profit', 'Total Net Profit'], default_value=stats.get('total_net_profit'))
            stats['profit_factor'] = get_summary_value(['Profit_Factor', 'Profit Factor'], default_value=stats.get('profit_factor'))
            stats['win_rate'] = get_summary_value(['Profit_Trades_Percent', 'Win_Rate', 'Win Rate (%)'], default_value=stats.get('win_rate')) # Added Profit_Trades_Percent as primary source
            stats['expectancy'] = get_summary_value(['Expected_Payoff', 'Expected Payoff'], default_value=stats.get('expectancy'))
            stats['best_profit'] = get_summary_value(['Largest_Profit_Trade', 'Largest Profit Trade'], default_value=stats.get('best_profit'))
            stats['biggest_loss'] = get_summary_value(['Largest_Loss_Trade', 'Largest Loss Trade'], default_value=stats.get('biggest_loss'))

    return stats