# core/gs_handler.py (ฉบับแก้ไขสมบูรณ์)
import streamlit as st
import pandas as pd
import numpy as np
import gspread
import traceback
from datetime import datetime, timedelta
import uuid
from config import settings
from config.settings import (
    WORKSHEET_STATEMENT_SUMMARIES, WORKSHEET_ACTUAL_ORDERS, 
    WORKSHEET_ACTUAL_POSITIONS, WORKSHEET_ACTUAL_TRADES,
    WORKSHEET_PORTFOLIOS, WORKSHEET_PLANNED_LOGS, WORKSHEET_UPLOAD_HISTORY
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
                   
                    sh.add_worksheet(title=ws_name, rows="1000", cols=len(headers) + 5)
                   
                    new_ws = sh.worksheet(ws_name)
                    
                    new_ws.update([headers], value_input_option='USER_ENTERED')
                    
                    ws_dict[ws_name] = new_ws
                    
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

@st.cache_data(ttl=180)
def load_statement_summaries_from_gsheets():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(WORKSHEET_STATEMENT_SUMMARIES)
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
# ในไฟล์ core/gs_handler.py
# วางฟังก์ชันนี้เพิ่มเข้าไป

def update_portfolio_in_gsheets(portfolio_id, updated_data_dict):
    """
    อัปเดตข้อมูลของพอร์ตที่มีอยู่แล้วใน Google Sheets
    :param portfolio_id: ID ของพอร์ตที่ต้องการอัปเดต
    :param updated_data_dict: Dictionary ที่มีข้อมูลใหม่
    :return: True ถ้าสำเร็จ, False ถ้าล้มเหลว
    """
    gc = get_gspread_client()
    if not gc:
        st.error("ไม่สามารถเชื่อมต่อ Google Sheets Client เพื่ออัปเดตพอร์ตได้")
        return False
    
    try:
        sh = gc.open(settings.GOOGLE_SHEET_NAME)
        ws = sh.worksheet(settings.WORKSHEET_PORTFOLIOS)
        
        # 1. ค้นหาแถวที่ต้องการอัปเดตโดยใช้ PortfolioID
        # สมมติว่า PortfolioID อยู่ในคอลัมน์ A (คอลัมน์ที่ 1)
        cell = ws.find(portfolio_id, in_column=1)
        
        if not cell:
            st.error(f"ไม่พบพอร์ตที่มี ID: {portfolio_id} สำหรับการอัปเดต")
            return False

        print(f"INFO: Found portfolio to update at row {cell.row}")

        # 2. เตรียมข้อมูลใหม่ตามลำดับของ Headers
        headers = ws.row_values(1)
        if not headers:
            st.error("ไม่พบคอลัมน์ Headers ในชีต Portfolios")
            return False

        updated_row = [str(updated_data_dict.get(h, "")).strip() for h in headers]
        
        # 3. อัปเดตข้อมูลทั้งแถว
        ws.update(f'A{cell.row}', [updated_row], value_input_option='USER_ENTERED')
        
        # 4. เคลียร์แคชเพื่อให้ UI โหลดข้อมูลใหม่
        load_portfolios_from_gsheets.clear()
        
        print(f"INFO: Portfolio ID {portfolio_id} updated successfully.")
        return True

    except gspread.exceptions.CellNotFound:
        st.error(f"ไม่พบพอร์ตที่มี ID: {portfolio_id} สำหรับการอัปเดต")
        return False
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการอัปเดตพอร์ต: {e}")
        import traceback
        traceback.print_exc()
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
    st.dataframe(df_deals_input)
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_TRADES]
    return _save_transactional_data(ws, df_deals_input, "Deal_ID", expected_headers, "Deals", portfolio_id, portfolio_name, source_file_name, import_batch_id)

def save_orders_to_actul_orders(ws, df_orders_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    st.dataframe(df_orders_input)
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_ORDERS]
    return _save_transactional_data(ws, df_orders_input, "Order_ID_Ord", expected_headers, "Orders", portfolio_id, portfolio_name, source_file_name, import_batch_id)

def save_positions_to_actul_positions(ws, df_positions_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    st.dataframe(df_positions_input)
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_POSITIONS]
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
    


def save_upload_history(ws, history_data):
    """
    (เวอร์ชันเรียบง่ายสุดๆ) บันทึกประวัติโดยไม่มีการตรวจสอบที่ซับซ้อน
    """
    try:
        # **ข้อเสีย:** ต้องเรียงลำดับข้อมูลให้ตรงกับคอลัมน์ในชีตด้วยตัวเอง
        row_to_insert = [
            history_data.get("Timestamp"),
            history_data.get("Filename"),
            history_data.get("Status"),
            history_data.get("Details"),
            history_data.get("Import Batch ID")
        ]
        
        ws.append_row(row_to_insert)
        return True, "History saved."

    except Exception as e:
        # **ข้อเสีย:** บอกแค่ว่า Error แต่ไม่รู้ว่าเป็น Error เพราะอะไร
        print(f"!!! ERROR saving history: {e}")
        return False, "Failed to save history."



#---------------------------------------------
def get_today_drawdown(df_logs: pd.DataFrame) -> float:
   
    if df_logs is None or df_logs.empty:
        return 0.0

    today_str = datetime.now().strftime("%Y-%m-%d")
    df_logs_cleaned = df_logs.copy()

    # Ensure 'Timestamp' column exists and is of datetime type
    if 'Timestamp' not in df_logs_cleaned.columns:
        return 0.0
    if not pd.api.types.is_datetime64_any_dtype(df_logs_cleaned['Timestamp']):
        df_logs_cleaned['Timestamp'] = pd.to_datetime(df_logs_cleaned['Timestamp'], errors='coerce')

    # Drop rows where timestamp conversion failed
    df_logs_cleaned.dropna(subset=['Timestamp'], inplace=True)

    if 'Risk $' not in df_logs_cleaned.columns:
        return 0.0
        
    df_today = df_logs_cleaned[df_logs_cleaned["Timestamp"].dt.strftime("%Y-%m-%d") == today_str]
    drawdown = df_today["Risk $"].sum()
    
    return float(drawdown) if pd.notna(drawdown) else 0.0


def get_performance(df_logs, period="week"):
   
    if df_logs is None or df_logs.empty:
        return 0.0, 0.0, 0

    df_logs_cleaned = df_logs.copy()
    if 'Timestamp' not in df_logs_cleaned.columns or not pd.api.types.is_datetime64_any_dtype(df_logs_cleaned['Timestamp']):
        df_logs_cleaned['Timestamp'] = pd.to_datetime(df_logs_cleaned['Timestamp'], errors='coerce')
    
    df_logs_cleaned.dropna(subset=['Timestamp'], inplace=True)
    if 'Risk $' not in df_logs_cleaned.columns:
        return 0.0, 0.0, 0

    now = datetime.now()
    if period == "week":
        start_date = now - pd.Timedelta(days=now.weekday())
        df_period = df_logs_cleaned[df_logs_cleaned["Timestamp"] >= start_date.replace(hour=0, minute=0, second=0, microsecond=0)]
    else:  # month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        df_period = df_logs_cleaned[df_logs_cleaned["Timestamp"] >= start_date]
    
    win = df_period[df_period["Risk $"] > 0].shape[0]
    loss = df_period[df_period["Risk $"] <= 0].shape[0]
    total_trades = win + loss
    winrate = (100 * win / total_trades) if total_trades > 0 else 0.0
    gain = df_period["Risk $"].sum()
    return float(winrate), float(gain) if pd.notna(gain) else 0.0, int(total_trades)


def calculate_simulated_drawdown(df_trades: pd.DataFrame, starting_balance: float) -> float:
    
    if df_trades is None or df_trades.empty or 'Risk $' not in df_trades.columns:
        return 0.0

    max_dd = 0.0
    current_balance = starting_balance
    peak_balance = starting_balance
    
    df_calc = df_trades.copy()
    if "Timestamp" in df_calc.columns and pd.api.types.is_datetime64_any_dtype(df_calc['Timestamp']):
        df_calc = df_calc.sort_values(by="Timestamp", ascending=True)

    for pnl in df_calc["Risk $"]:
        current_balance += pnl
        if current_balance > peak_balance:
            peak_balance = current_balance
        drawdown = peak_balance - current_balance
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd


def analyze_planned_trades_for_ai(
    df_all_planned_logs: pd.DataFrame,
    active_portfolio_id: str = None,
    active_portfolio_name: str = "ทั่วไป (ไม่ได้เลือกพอร์ต)",
    balance_for_simulation: float = 10000.0
):
   
    results = {
        "report_title_suffix": "(จากข้อมูลแผนเทรดทั้งหมด)", "total_trades": 0, "win_rate": 0.0,
        "gross_pnl": 0.0, "avg_rr": "N/A", "max_drawdown_simulated": 0.0, "best_day": "-",
        "worst_day": "-", "insights": [], "error_message": None, "data_found": False
    }

    if active_portfolio_id:
        results["report_title_suffix"] = f"(พอร์ต: '{active_portfolio_name}' - จากแผน)"

    if df_all_planned_logs is None or df_all_planned_logs.empty:
        results["error_message"] = f"ไม่พบข้อมูลแผนเทรดใน Log สำหรับพอร์ต '{active_portfolio_name}'." if active_portfolio_id else "ยังไม่มีข้อมูลแผนเทรดใน Log สำหรับวิเคราะห์"
        return results

    df_to_analyze = df_all_planned_logs.copy()
    if active_portfolio_id and 'PortfolioID' in df_to_analyze.columns:
        df_to_analyze = df_to_analyze[df_to_analyze['PortfolioID'] == str(active_portfolio_id)]

    if df_to_analyze.empty:
        results["error_message"] = f"ไม่พบข้อมูลแผนเทรดที่ตรงเงื่อนไขสำหรับพอร์ต '{active_portfolio_name}'" if active_portfolio_id else "ไม่พบข้อมูลแผนเทรดที่ตรงเงื่อนไข"
        return results

    results["data_found"] = True
    if 'Risk $' not in df_to_analyze.columns: df_to_analyze['Risk $'] = 0.0
    df_to_analyze['Risk $'] = pd.to_numeric(df_to_analyze['Risk $'], errors='coerce').fillna(0.0)

    results["total_trades"] = df_to_analyze.shape[0]
    win_trades = df_to_analyze[df_to_analyze["Risk $"] > 0].shape[0]
    results["win_rate"] = (100 * win_trades / results["total_trades"]) if results["total_trades"] > 0 else 0.0
    results["gross_pnl"] = df_to_analyze["Risk $"].sum()

    if "RR" in df_to_analyze.columns:
        rr_series = pd.to_numeric(df_to_analyze["RR"], errors='coerce').dropna()
        if not rr_series.empty:
            avg_rr_val = rr_series[rr_series > 0].mean()
            if pd.notna(avg_rr_val): results["avg_rr"] = f"{avg_rr_val:.2f}"
    
    results["max_drawdown_simulated"] = calculate_simulated_drawdown(df_to_analyze, balance_for_simulation)

    if "Timestamp" in df_to_analyze.columns and pd.api.types.is_datetime64_any_dtype(df_to_analyze['Timestamp']):
        df_daily_pnl = df_to_analyze.dropna(subset=["Timestamp"])
        if not df_daily_pnl.empty:
            df_daily_pnl["Weekday"] = df_daily_pnl["Timestamp"].dt.day_name()
            daily_pnl_sum = df_daily_pnl.groupby("Weekday")["Risk $"].sum()
            if not daily_pnl_sum.empty:
                if daily_pnl_sum.max() > 0: results["best_day"] = daily_pnl_sum.idxmax()
                if daily_pnl_sum.min() < 0: results["worst_day"] = daily_pnl_sum.idxmin()

    # Generate insights
    if results["total_trades"] > 0:
        if results["win_rate"] >= 60: results["insights"].append(f"✅ Winrate (แผน: {results['win_rate']:.1f}%) สูง: ระบบการวางแผนมีแนวโน้มที่ดี")
        elif results["win_rate"] < 40 and results["total_trades"] >= 10: results["insights"].append(f"⚠️ Winrate (แผน: {results['win_rate']:.1f}%) ต่ำ: ควรทบทวนกลยุทธ์การวางแผน")
        try: avg_rr_numeric = float(results["avg_rr"])
        except (ValueError, TypeError): avg_rr_numeric = None
        if avg_rr_numeric is not None and avg_rr_numeric < 1.5 and results["total_trades"] >= 5: results["insights"].append(f"📉 RR เฉลี่ย (แผน: {results['avg_rr']}) ต่ำกว่า 1.5: อาจต้องพิจารณาการตั้ง TP/SL")
        if balance_for_simulation > 0 and results["max_drawdown_simulated"] > (balance_for_simulation * 0.10):
            dd_percent = (results['max_drawdown_simulated'] / balance_for_simulation) * 100
            results["insights"].append(f"🚨 Max Drawdown (จำลองจากแผน: {results['max_drawdown_simulated']:,.2f} USD) ค่อนข้างสูง ({dd_percent:.1f}% ของ Balance)")
    if not results["insights"] and results["data_found"]: results["insights"].append("ดูเหมือนว่าข้อมูลแผนเทรดที่วิเคราะห์ยังไม่มีจุดที่น่ากังวลเป็นพิเศษ")
    return results

def analyze_actual_trades_for_ai(
    df_all_actual_trades: pd.DataFrame,
    active_portfolio_id: str = None,
    active_portfolio_name: str = "ทั่วไป (ไม่ได้เลือกพอร์ต)"
):
    
    results = {
        "report_title_suffix": "(จากข้อมูลผลการเทรดจริงทั้งหมด)", "total_deals": 0, "win_rate": 0.0,
        "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": "0.00", "avg_profit_deal": 0.0,
        "avg_loss_deal": 0.0, "insights": [], "error_message": None, "data_found": False
    }

    if active_portfolio_id:
        results["report_title_suffix"] = f"(พอร์ต: '{active_portfolio_name}' - จากผลจริง)"

    if df_all_actual_trades is None or df_all_actual_trades.empty:
        results["error_message"] = f"ไม่พบข้อมูลผลการเทรดจริงใน Log สำหรับพอร์ต '{active_portfolio_name}'." if active_portfolio_id else "ยังไม่มีข้อมูลผลการเทรดจริงใน Log สำหรับวิเคราะห์"
        return results

    df_to_analyze = df_all_actual_trades.copy()
    if active_portfolio_id and 'PortfolioID' in df_to_analyze.columns:
        df_to_analyze = df_to_analyze[df_to_analyze['PortfolioID'] == str(active_portfolio_id)]

    if df_to_analyze.empty:
        results["error_message"] = f"ไม่พบข้อมูลผลการเทรดจริงที่ตรงเงื่อนไขสำหรับพอร์ต '{active_portfolio_name}'" if active_portfolio_id else "ไม่พบข้อมูลผลการเทรดจริงที่ตรงเงื่อนไข"
        return results
    
    if 'Profit_Deal' not in df_to_analyze.columns:
        results["error_message"] = "AI (Actual): ไม่พบคอลัมน์ 'Profit_Deal' ในข้อมูลผลการเทรดจริง"
        return results

    df_to_analyze['Profit_Deal'] = pd.to_numeric(df_to_analyze['Profit_Deal'], errors='coerce').fillna(0.0)
    df_trading_deals = df_to_analyze[~df_to_analyze.get('Type_Deal', pd.Series(dtype=str)).str.lower().isin(['balance', 'credit', 'deposit', 'withdrawal'])].copy()

    if df_trading_deals.empty:
        results["error_message"] = "ไม่พบรายการ Deals ที่เป็นการซื้อขายจริงสำหรับวิเคราะห์"
        return results
    
    results["data_found"] = True
    results["total_deals"] = len(df_trading_deals)
    
    winning_deals_df = df_trading_deals[df_trading_deals['Profit_Deal'] > 0]
    losing_deals_df = df_trading_deals[df_trading_deals['Profit_Deal'] < 0]

    results["win_rate"] = (100 * len(winning_deals_df) / results["total_deals"]) if results["total_deals"] > 0 else 0.0
    results["gross_profit"] = winning_deals_df['Profit_Deal'].sum()
    results["gross_loss"] = abs(losing_deals_df['Profit_Deal'].sum())

    if results["gross_loss"] > 0: results["profit_factor"] = f"{results['gross_profit'] / results['gross_loss']:.2f}"
    elif results["gross_profit"] > 0: results["profit_factor"] = "∞ (No Losses)"
    
    results["avg_profit_deal"] = results["gross_profit"] / len(winning_deals_df) if len(winning_deals_df) > 0 else 0.0
    results["avg_loss_deal"] = results["gross_loss"] / len(losing_deals_df) if len(losing_deals_df) > 0 else 0.0

    # Generate insights
    if results["total_deals"] > 0:
        if results["win_rate"] >= 50: results["insights"].append(f"✅ Win Rate (ผลจริง: {results['win_rate']:.1f}%) อยู่ในเกณฑ์ดี")
        else: results["insights"].append(f"📉 Win Rate (ผลจริง: {results['win_rate']:.1f}%) ควรปรับปรุง")
        try: pf_numeric = float(results["profit_factor"])
        except (ValueError, TypeError): pf_numeric = 0.0
        if "∞" in results["profit_factor"] or pf_numeric > 1.5: results["insights"].append(f"📈 Profit Factor (ผลจริง: {results['profit_factor']}) อยู่ในระดับที่ดี")
        elif pf_numeric < 1.0 and results["total_deals"] >= 10: results["insights"].append(f"⚠️ Profit Factor (ผลจริง: {results['profit_factor']}) ต่ำกว่า 1 บ่งชี้ว่าขาดทุนมากกว่ากำไร")
    if not results["insights"] and results["data_found"]: results["insights"].append("ข้อมูลผลการเทรดจริงกำลังถูกรวบรวม โปรดตรวจสอบ Insights เพิ่มเติมในอนาคต")
    
    return results

# วางโค้ดนี้ต่อท้ายไฟล์ core/analytics_engine.py

def get_dashboard_analytics_for_actual(df_all_actual_trades, df_all_statement_summaries, active_portfolio_id):
    
    results = {
        "data_found": False,
        "error_message": "",
        "metrics": {},
        "balance_curve_data": pd.DataFrame()
    }

    # Filter data for the active portfolio
    if active_portfolio_id:
        if not df_all_actual_trades.empty:
            df_actual = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == str(active_portfolio_id)].copy()
        else:
            df_actual = pd.DataFrame()
    else:
        df_actual = df_all_actual_trades.copy()

    if df_actual.empty:
        results["error_message"] = "ไม่พบข้อมูล 'ผลการเทรดจริง' ในพอร์ตที่เลือก"
        return results

    results["data_found"] = True

    # Ensure 'Profit_Deal' is numeric
    df_actual['Profit_Deal'] = pd.to_numeric(df_actual['Profit_Deal'], errors='coerce').fillna(0)

    # Calculate metrics
    total_deals = len(df_actual)
    winning_deals = df_actual[df_actual['Profit_Deal'] > 0]
    losing_deals = df_actual[df_actual['Profit_Deal'] < 0]

    gross_profit = winning_deals['Profit_Deal'].sum()
    gross_loss = losing_deals['Profit_Deal'].sum()
    total_net_profit = gross_profit + gross_loss # gross_loss is negative

    win_rate = (len(winning_deals) / total_deals) * 100 if total_deals > 0 else 0
    
    profit_factor = 0
    if gross_loss != 0:
        profit_factor = abs(gross_profit / gross_loss)

    # Prepare data for balance curve chart
    if 'Time_Deal' in df_actual.columns and 'Balance_Deal' in df_actual.columns:
        df_actual['Time_Deal'] = pd.to_datetime(df_actual['Time_Deal'])
        balance_curve_df = df_actual.sort_values(by='Time_Deal')[['Time_Deal', 'Balance_Deal']].rename(
            columns={'Time_Deal': 'Time', 'Balance_Deal': 'Balance'}
        ).set_index('Time')
        results["balance_curve_data"] = balance_curve_df

    # Store calculated metrics
    results["metrics"] = {
        "Total Net Profit": total_net_profit,
        "Total Deals": total_deals,
        "Win Rate (%)": win_rate,
        "Profit Factor": profit_factor,
        "Gross Profit": gross_profit,
        "Gross Loss": gross_loss
    }

    # Get Max Drawdown from the latest statement summary for this portfolio
    if active_portfolio_id and not df_all_statement_summaries.empty:
        df_summary = df_all_statement_summaries[df_all_statement_summaries['PortfolioID'] == str(active_portfolio_id)].copy()
        if not df_summary.empty:
            # Assuming the summary sheet might have a Drawdown column from the report
            if 'Drawdown' in df_summary.columns:
                 # Get the latest non-null drawdown value
                latest_drawdown = df_summary.sort_values(by='Timestamp', ascending=False)['Drawdown'].dropna().iloc[0]
                results["metrics"]["Max Drawdown"] = pd.to_numeric(latest_drawdown, errors='coerce')

    return results

# ==============================================================================
# NEW: Combined Analysis Engine for Deeper AI Insights (As of June 2025)
# ==============================================================================

def analyze_combined_trades_for_ai(
    df_planned: pd.DataFrame,
    df_actual: pd.DataFrame,
    active_portfolio_id: str = None,
    active_portfolio_name: str = "ทั่วไป"
):
    
    results = {
        "report_title_suffix": f"(พอร์ต: '{active_portfolio_name}' - วิเคราะห์เชิงลึก)",
        "insights": [],
        "error_message": None,
        "data_found": False
    }

    # 1. Validate and Filter Data
    if df_planned is None or df_planned.empty or df_actual is None or df_actual.empty:
        results["error_message"] = "AI (Combined): ต้องการข้อมูลทั้ง 'แผนการเทรด' และ 'ผลเทรดจริง' เพื่อทำการวิเคราะห์เชิงลึก"
        return results

    df_p = df_planned.copy()
    df_a = df_actual.copy()

    if active_portfolio_id:
        if 'PortfolioID' in df_p.columns:
            df_p = df_p[df_p['PortfolioID'] == str(active_portfolio_id)]
        if 'PortfolioID' in df_a.columns:
            df_a = df_a[df_a['PortfolioID'] == str(active_portfolio_id)]

    if df_p.empty or df_a.empty:
        results["error_message"] = f"AI (Combined): ไม่พบข้อมูลแผนหรือผลการเทรดจริงสำหรับพอร์ต '{active_portfolio_name}'"
        return results

    results["data_found"] = True

    # 2. Prepare Data Columns
    df_a['Time_Deal'] = pd.to_datetime(df_a['Time_Deal'], errors='coerce')
    df_a['Profit_Deal'] = pd.to_numeric(df_a['Profit_Deal'], errors='coerce').fillna(0)
    df_a.dropna(subset=['Time_Deal'], inplace=True)
    
    df_p['Timestamp'] = pd.to_datetime(df_p['Timestamp'], errors='coerce')
    df_p['Risk $'] = pd.to_numeric(df_p['Risk $'], errors='coerce').fillna(0)
    
    # --- INSIGHT GENERATION ---

    # 3. Time-Based Performance Analysis (วิเคราะห์ประสิทธิภาพตามช่วงเวลา)
    if not df_a.empty:
        # By Day of Week
        df_a["Weekday"] = df_a["Time_Deal"].dt.day_name()
        daily_pnl = df_a.groupby("Weekday")['Profit_Deal'].sum()
        if not daily_pnl.empty:
            best_day = daily_pnl.idxmax()
            worst_day = daily_pnl.idxmin()
            if daily_pnl[best_day] > 0:
                results["insights"].append(f"📈 [เวลา] คุณทำกำไรได้ดีที่สุดในวัน '{best_day}' ({daily_pnl[best_day]:,.2f} USD)")
            if daily_pnl[worst_day] < 0:
                results["insights"].append(f"📉 [เวลา] คุณมักจะขาดทุนมากที่สุดในวัน '{worst_day}' ({daily_pnl[worst_day]:,.2f} USD)")

        # By Month
        df_a["Month"] = df_a["Time_Deal"].dt.strftime('%Y-%m')
        monthly_pnl = df_a.groupby("Month")['Profit_Deal'].sum()
        if not monthly_pnl.empty and len(monthly_pnl) > 1:
            best_month = monthly_pnl.idxmax()
            worst_month = monthly_pnl.idxmin()
            if monthly_pnl[best_month] > 0:
                 results["insights"].append(f"🗓️ [เวลา] เดือน '{best_month}' เป็นเดือนที่คุณทำกำไรได้ดีที่สุด")
            if monthly_pnl[worst_month] < 0:
                 results["insights"].append(f"🗓️ [เวลา] เดือน '{worst_month}' เป็นเดือนที่ควรระมัดระวังเป็นพิเศษ")


    # 4. Plan vs. Actual by Symbol (เปรียบเทียบผลงานตามสินทรัพย์)
    if 'Symbol' in df_p.columns and 'Symbol' in df_a.columns:
        plan_by_Symbol = df_p.groupby('Symbol')['Risk $'].sum()
        actual_by_Symbol = df_a.groupby('Symbol')['Profit_Deal'].sum()
        common_Symbols = set(plan_by_Symbol.index) & set(actual_by_Symbol.index)
        
        for Symbol in common_Symbols:
            plan_pnl = plan_by_Symbol.get(Symbol, 0)
            actual_pnl = actual_by_Symbol.get(Symbol, 0)
            if actual_pnl > plan_pnl and actual_pnl > 0:
                results["insights"].append(f"💡 [สินทรัพย์] ในคู่เงิน {Symbol}, ผลงานจริงของคุณ ({actual_pnl:,.2f} USD) ดีกว่าที่วางแผนไว้ ({plan_pnl:,.2f} USD)!")
            elif actual_pnl < 0 and actual_pnl < plan_pnl:
                 results["insights"].append(f"⚠️ [สินทรัพย์] ในคู่เงิน {Symbol}, ผลขาดทุนจริง ({actual_pnl:,.2f} USD) มากกว่าที่วางแผนไว้ ({plan_pnl:,.2f} USD)")

    # 5. Missed Trades Analysis (วิเคราะห์การ 'ตกรถ') - Approximation
    if 'Setup' in df_p.columns and 'Type_Deal' in df_a.columns:
        # Approximate by counting planned Long/Short vs actual buy/sell
        planned_shorts = df_p[df_p['Setup'].str.contains("Short", case=False, na=False)].shape[0]
        actual_sells = df_a[df_a['Type_Deal'].str.contains("sell", case=False, na=False)].shape[0]
        if planned_shorts > actual_sells + (planned_shorts * 0.2): # Allow for some variance
            results["insights"].append(f"🤔 [พฤติกรรม] คุณมีแนวโน้มที่จะ 'ตกรถ' (ไม่ได้เข้าเทรดตามแผน) ใน Setup ฝั่ง Short มากกว่าฝั่ง Long")

    if not results["insights"]:
        results["insights"].append("ยังไม่พบ Insight เชิงลึกที่ชัดเจนในขณะนี้ ระบบกำลังรวบรวมข้อมูลเพิ่มเติม")

    return results

def generate_risk_alerts(
    df_planned_logs: pd.DataFrame, 
    daily_drawdown_limit_pct: float, 
    current_balance: float
) -> list:
    
    alerts = []
    
    # 1. ดึงข้อมูล Drawdown ของแผนวันนี้ (ค่าจะเป็นลบถ้าขาดทุน)
    # เราจะใช้ฟังก์ชัน get_today_drawdown ที่เรามีอยู่แล้ว
    drawdown_today = get_today_drawdown(df_planned_logs)

    # ถ้าไม่ขาดทุน หรือกำไร ก็ไม่ต้องทำอะไรต่อ
    if drawdown_today >= 0:
        return alerts

    # 2. คำนวณลิมิตขาดทุนเป็นจำนวนเงิน (ค่าจะเป็นลบ)
    if current_balance <= 0 or daily_drawdown_limit_pct <= 0:
        return alerts # ไม่มีการแจ้งเตือนถ้า balance หรือ limit ไม่ถูกต้อง
        
    drawdown_limit_absolute = -abs(current_balance * (daily_drawdown_limit_pct / 100.0))

    # 3. ตรวจสอบเงื่อนไขเพื่อสร้างการแจ้งเตือน
    
    # เงื่อนไขที่ 1: ขาดทุนถึงลิมิตแล้ว
    if drawdown_today <= drawdown_limit_absolute:
        alert_message = (
            f"คุณถึงลิมิตขาดทุนรายวันแล้ว! "
            f"(ขาดทุน: {drawdown_today:,.2f} / ลิมิต: {drawdown_limit_absolute:,.2f} USD)"
        )
        alerts.append({'level': 'error', 'message': alert_message})
        return alerts # เมื่อถึงลิมิตแล้ว ไม่ต้องแสดงคำเตือนซ้ำ

    # เงื่อนไขที่ 2: ขาดทุนเข้าใกล้ลิมิต (เช่น เกิน 80% ของลิมิต)
    warning_threshold = drawdown_limit_absolute * 0.8
    if drawdown_today <= warning_threshold:
        alert_message = (
            f"โปรดระวัง! คุณใกล้ถึงลิมิตขาดทุนรายวันแล้ว "
            f"(ขาดทุน: {drawdown_today:,.2f} / ลิมิต: {drawdown_limit_absolute:,.2f} USD)"
        )
        alerts.append({'level': 'warning', 'message': alert_message})

    return alerts

def generate_weekly_summary(df_all_actual_trades: pd.DataFrame, active_portfolio_id: str) -> str | None:
    
    if df_all_actual_trades.empty or not active_portfolio_id:
        return None

    # 1. กรองข้อมูลเฉพาะพอร์ตที่เลือก
    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()

    # 2. เปลี่ยนชื่อคอลัมน์ 'Symbol_Deal' เป็น 'Symbol' เพื่อให้เป็นมาตรฐาน
    if 'Symbol_Deal' in df.columns:
        df.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True)
    
    # 3. เตรียมข้อมูลสำหรับการวิเคราะห์
    df['Time_Deal'] = pd.to_datetime(df['Time_Deal'], errors='coerce')
    df.dropna(subset=['Time_Deal', 'Profit_Deal'], inplace=True)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    week_df = df[df['Time_Deal'] >= start_date]

    if week_df.empty or len(week_df) < 3:
        return None

    # 4. คำนวณ Metrics ที่สำคัญ
    net_profit = week_df['Profit_Deal'].sum()
    total_trades = len(week_df)
    win_trades = len(week_df[week_df['Profit_Deal'] > 0])
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0

    # 5. หาข้อมูลเชิงลึก
    week_df['Weekday'] = week_df['Time_Deal'].dt.day_name()
    daily_pnl = week_df.groupby('Weekday')['Profit_Deal'].sum()
    best_day = daily_pnl.idxmax()
    worst_day = daily_pnl.idxmin()

    best_Symbol = None
    # ตรวจสอบก่อนว่ามีคอลัมน์ 'Symbol' จริงๆ ก่อนจะเรียกใช้
    if 'Symbol' in week_df.columns:
        Symbol_pnl = week_df.groupby('Symbol')['Profit_Deal'].sum()
        if not Symbol_pnl.empty and Symbol_pnl.max() > 0:
            best_Symbol = Symbol_pnl.idxmax()
    
    # 6. สร้างข้อความสรุป
    summary_lines = []
    summary_lines.append(f"ภาพรวมสัปดาห์ที่ผ่านมา: กำไรสุทธิ {net_profit:,.2f} USD, Win Rate {win_rate:.1f}%.")
    
    if daily_pnl[best_day] > 0:
        summary_lines.append(f"🗓️ วันที่ดีที่สุดคือวัน **{best_day}** (กำไร {daily_pnl[best_day]:,.2f} USD).")
    
    if daily_pnl[worst_day] < 0:
        summary_lines.append(f"📉 วันที่ควรระวังคือวัน **{worst_day}** (ขาดทุน {daily_pnl[worst_day]:,.2f} USD).")

    if best_Symbol:
        summary_lines.append(f"💰 สินทรัพย์ที่ทำกำไรสูงสุดคือ **{best_Symbol}**.")

    return " ".join(summary_lines)


def find_user_strengths(
    df_all_actual_trades: pd.DataFrame,
    active_portfolio_id: str,
    min_trades_threshold: int = 5,
    win_rate_threshold: float = 60.0,
    profit_factor_threshold: float = 1.5
) -> list[str]:
   
    if df_all_actual_trades.empty or not active_portfolio_id:
        return []

    # 1. กรองข้อมูลและเปลี่ยนชื่อคอลัมน์
    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
    if 'Symbol_Deal' in df.columns:
        df.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True)
    
    df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
    
    # 2. วิเคราะห์เฉพาะรายการที่เป็นการเทรดจริงๆ
    trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
    df_trades = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)].copy()
    
    if len(df_trades) < min_trades_threshold:
        return []
        
    # 3. สร้างคอลัมน์ Direction และตรวจสอบว่ามีคอลัมน์ Symbol ก่อน Groupby
    if 'Symbol' not in df_trades.columns:
        return [] # ถ้าไม่มีคอลัมน์ Symbol ก็ไม่สามารถวิเคราะห์ต่อได้
        
    df_trades['Direction'] = np.where(df_trades['Type_Deal'].str.lower() == 'buy', 'Long', 'Short')

    # 4. จัดกลุ่มและคำนวณสถิติ
    agg_functions = {
        'Profit_Deal': [
            ('total_trades', 'count'),
            ('winning_trades', lambda x: (x > 0).sum()),
            ('gross_profit', lambda x: x[x > 0].sum()),
            ('gross_loss', lambda x: abs(x[x < 0].sum()))
        ]
    }
    grouped = df_trades.groupby(['Symbol', 'Direction']).agg(agg_functions)
    grouped.columns = grouped.columns.droplevel(0)

    # 5. คำนวณ Win Rate และ Profit Factor
    grouped['win_rate'] = (grouped['winning_trades'] / grouped['total_trades']) * 100
    grouped['profit_factor'] = grouped['gross_profit'] / grouped['gross_loss']
    grouped['profit_factor'].replace([np.inf, -np.inf], grouped['gross_profit'], inplace=True)
    grouped.fillna({'profit_factor': 0}, inplace=True)
    
    # 6. คัดเลือก "ท่าไม้ตาย"
    strong_setups_df = grouped[
        (grouped['total_trades'] >= min_trades_threshold) &
        (grouped['win_rate'] >= win_rate_threshold) &
        (grouped['profit_factor'] >= profit_factor_threshold)
    ]

    # 7. แปลงผลลัพธ์
    strengths = []
    if not strong_setups_df.empty:
        for index, row in strong_setups_df.iterrows():
            symbol, direction = index
            strengths.append(f"{symbol}-{direction}")

    return strengths



# (วางโค้ดนี้ต่อท้ายในไฟล์ core/analytics_engine.py)

def get_advanced_statistics(df_all_actual_trades: pd.DataFrame, active_portfolio_id: str) -> dict:
   
    if df_all_actual_trades.empty or not active_portfolio_id:
        return {}

    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
    
    # --- เตรียมข้อมูลพื้นฐาน ---
    if 'Symbol_Deal' in df.columns:
        df.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True)
    
    trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
    df = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)].copy()
    
    if df.empty:
        return {}
        
    df['Time_Deal'] = pd.to_datetime(df['Time_Deal'])
    df = df.sort_values(by='Time_Deal', ascending=False) # เรียงจากล่าสุดไปเก่าสุด
    df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
    df['Direction'] = np.where(df['Type_Deal'].str.lower() == 'buy', 'Long', 'Short')

    # --- เริ่มการคำนวณสถิติต่างๆ ---
    results = {}

    # 1. ฟอร์ม 5 เทรดล่าสุด (แยก Long/Short)
    def _get_recent_form(df_direction, n=5):
        if df_direction.empty: return "N/A"
        recent_trades = df_direction.head(n)
        form = []
        for profit in recent_trades['Profit_Deal']:
            if profit > 0: form.append("W")
            elif profit < 0: form.append("L")
            else: form.append("B")
        return "-".join(form)

    df_long = df[df['Direction'] == 'Long']
    df_short = df[df['Direction'] == 'Short']
    
    results['recent_form_long'] = _get_recent_form(df_long)
    results['recent_form_short'] = _get_recent_form(df_short)

    # 2. กำไร/ขาดทุนสูงสุด (แยก Long/Short)
    results['biggest_win_long'] = df_long[df_long['Profit_Deal'] > 0]['Profit_Deal'].max()
    results['biggest_loss_long'] = df_long[df_long['Profit_Deal'] < 0]['Profit_Deal'].min()
    results['biggest_win_short'] = df_short[df_short['Profit_Deal'] > 0]['Profit_Deal'].max()
    results['biggest_loss_short'] = df_short[df_short['Profit_Deal'] < 0]['Profit_Deal'].min()

    # 3. Win Rate (แยก Long/Short)
    results['win_rate_long'] = (df_long['Profit_Deal'] > 0).sum() / len(df_long) * 100 if not df_long.empty else 0
    results['win_rate_short'] = (df_short['Profit_Deal'] > 0).sum() / len(df_short) * 100 if not df_short.empty else 0

    # 4. ชนะ/แพ้ติดต่อกันนานที่สุด (Overall)
    df_rev = df.iloc[::-1].copy() # เรียงจากเก่าไปใหม่เพื่อคำนวณ streak
    df_rev['outcome'] = np.sign(df_rev['Profit_Deal']) # 1 for win, -1 for loss, 0 for BE
    streaks = df_rev['outcome'].groupby((df_rev['outcome'] != df_rev['outcome'].shift()).cumsum()).cumcount() + 1
    results['max_consecutive_wins'] = streaks[df_rev['outcome'] == 1].max()
    results['max_consecutive_losses'] = streaks[df_rev['outcome'] == -1].max()

    # 5. Consistency Score
    total_profit = df[df['Profit_Deal'] > 0]['Profit_Deal'].sum()
    if total_profit > 0:
        daily_pnl = df.groupby(df['Time_Deal'].dt.date)['Profit_Deal'].sum()
        best_day_profit = daily_pnl[daily_pnl > 0].max()
        results['profit_concentration'] = (best_day_profit / total_profit) * 100
    else:
        results['profit_concentration'] = 0

    thirty_days_ago = datetime.now() - timedelta(days=30)
    results['active_trading_days'] = df[df['Time_Deal'] > thirty_days_ago]['Time_Deal'].dt.normalize().nunique()
    
    return results

# (วางโค้ดนี้ต่อท้ายในไฟล์ core/analytics_engine.py)

def get_full_dashboard_stats(df_all_actual_trades: pd.DataFrame, df_all_summaries: pd.DataFrame, active_portfolio_id: str) -> dict:
    """
    [Final & Complete Version] แก้ไขโค้ดส่วน Fallback ที่ขาดหายไป
    """
    # --- ตั้งค่าผลลัพธ์เริ่มต้น ---
    stats = {
        'total_trades': 'N/A', 'profit_trades': 'N/A', 'loss_trades': 'N/A',
        'long_trades': 'N/A', 'short_trades': 'N/A',
        'gross_profit': np.nan, 'gross_loss': np.nan, 'total_net_profit': np.nan,
        'profit_factor': np.nan, 'win_rate': np.nan,
        'best_profit': np.nan, 'biggest_loss': np.nan,
        'avg_profit': np.nan, 'avg_loss': np.nan,
        'expectancy': np.nan,
        'avg_trade_size': np.nan, 'avg_trade_duration_str': 'N/A',
        'today_pnl_actual': 0.0, 'active_trading_days_total': 0
    }

    # --- [ทางเลือกที่ 1] พยายามดึงข้อมูลจากชีท StatementSummaries ก่อน ---
    if not df_all_summaries.empty and active_portfolio_id:
        summary_row = df_all_summaries[df_all_summaries['PortfolioID'] == active_portfolio_id]
        
        if not summary_row.empty:
            summary_data = summary_row.iloc[0]
            
            def to_numeric(series_val):
                if pd.isna(series_val) or series_val == '': return np.nan
                if isinstance(series_val, (int, float)): return series_val
                cleaned_val = str(series_val).replace('$', '').replace('%', '').replace(',', '').strip()
                return pd.to_numeric(cleaned_val, errors='coerce')

            # ดึงค่าจากชีทสรุป
            stats['total_trades'] = to_numeric(summary_data.get('Total Trades'))
            stats['profit_trades'] = to_numeric(summary_data.get('Profit Trades'))
            stats['loss_trades'] = to_numeric(summary_data.get('Loss Trades'))
            stats['long_trades'] = to_numeric(summary_data.get('Total_Long_Trades'))
            stats['short_trades'] = to_numeric(summary_data.get('Total_Short_Trades'))
            stats['gross_profit'] = to_numeric(summary_data.get('Gross Profit'))
            stats['gross_loss'] = to_numeric(summary_data.get('Gross Loss'))
            stats['total_net_profit'] = to_numeric(summary_data.get('Total Net Profit'))
            stats['profit_factor'] = to_numeric(summary_data.get('Profit Factor'))
            stats['win_rate'] = to_numeric(summary_data.get('Win Rate'))
            stats['best_profit'] = to_numeric(summary_data.get('Best Profit'))
            stats['biggest_loss'] = to_numeric(summary_data.get('Biggest Loss'))
            stats['avg_profit'] = to_numeric(summary_data.get('Avg. Profit'))
            stats['avg_loss'] = to_numeric(summary_data.get('Avg. Loss'))
            stats['expectancy'] = to_numeric(summary_data.get('Expected Payoff'))
            stats['avg_trade_duration_str'] = summary_data.get('Avg. Trade Duration', 'N/A')

            # ตรรกะสำหรับ Avg. Trade Size
            avg_trade_size_summary = to_numeric(summary_data.get('Avg. Trade Size'))
            if pd.notna(avg_trade_size_summary):
                stats['avg_trade_size'] = avg_trade_size_summary
            elif not df_all_actual_trades.empty:
                df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
                if not df.empty and 'DealVolume' in df.columns:
                    trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
                    df = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)]
                    total_volume = pd.to_numeric(df['DealVolume'], errors='coerce').sum()
                    total_trades_val = stats.get('total_trades')
                    if pd.notna(total_trades_val) and total_trades_val > 0:
                        stats['avg_trade_size'] = total_volume / total_trades_val

            # คำนวณค่าที่ต้องทำสดๆ
            if not df_all_actual_trades.empty:
                df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
                if not df.empty:
                    df['Time_Deal'] = pd.to_datetime(df['Time_Deal'])
                    df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    stats['today_pnl_actual'] = df[df['Time_Deal'].dt.strftime('%Y-%m-%d') == today_str]['Profit_Deal'].sum()
                    stats['active_trading_days_total'] = df['Time_Deal'].dt.normalize().nunique()
            
            return stats

    # --- [ทางเลือกที่ 2] แผนสำรอง: ถ้าไม่มีข้อมูลสรุป ให้คำนวณทุกอย่างจาก Trade Log ---
    # vvvv [ส่วนที่แก้ไขให้สมบูรณ์] vvvv
    if df_all_actual_trades.empty or not active_portfolio_id:
        return stats

    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
    
    trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
    df = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)].copy()
    
    if df.empty:
        return stats
        
    df['Time_Deal'] = pd.to_datetime(df['Time_Deal'])
    df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
    # ใช้ DealDirection ถ้ามี, ถ้าไม่มีก็สร้างจาก Type_Deal
    if 'DealDirection' not in df.columns:
        df['DealDirection'] = np.where(df['Type_Deal'].str.lower() == 'buy', 'LONG', 'SHORT')

    stats['total_trades'] = len(df)
    stats['profit_trades'] = int((df['Profit_Deal'] > 0).sum())
    stats['loss_trades'] = int((df['Profit_Deal'] < 0).sum())
    stats['long_trades'] = int((df['DealDirection'] == 'LONG').sum())
    stats['short_trades'] = int((df['DealDirection'] == 'SHORT').sum())
    stats['gross_profit'] = df[df['Profit_Deal'] > 0]['Profit_Deal'].sum()
    stats['gross_loss'] = df[df['Profit_Deal'] < 0]['Profit_Deal'].sum()
    stats['total_net_profit'] = stats['gross_profit'] + stats['gross_loss']
    stats['win_rate'] = (stats['profit_trades'] / stats['total_trades']) * 100 if stats['total_trades'] > 0 else 0
    stats['profit_factor'] = stats['gross_profit'] / abs(stats['gross_loss']) if stats['gross_loss'] != 0 else 0
    stats['best_profit'] = df['Profit_Deal'].max()
    stats['biggest_loss'] = df['Profit_Deal'].min()
    stats['avg_profit'] = stats['gross_profit'] / stats['profit_trades'] if stats['profit_trades'] > 0 else 0
    stats['avg_loss'] = stats['gross_loss'] / stats['loss_trades'] if stats['loss_trades'] > 0 else 0
    win_rate_frac = stats['win_rate'] / 100
    stats['expectancy'] = (win_rate_frac * stats['avg_profit']) - ((1 - win_rate_frac) * abs(stats['avg_loss'])) if stats['total_trades'] > 0 else 0.0
    stats['avg_trade_size'] = pd.to_numeric(df['DealVolume'], errors='coerce').mean() if 'DealVolume' in df.columns else 0.0

    today_str = datetime.now().strftime('%Y-%m-%d')
    stats['today_pnl_actual'] = df[df['Time_Deal'].dt.strftime('%Y-%m-%d') == today_str]['Profit_Deal'].sum()
    stats['active_trading_days_total'] = df['Time_Deal'].dt.normalize().nunique()
    
    return stats

def check_for_duplicate_file_hash(history_ws, file_hash_to_check):
    """
    (เวอร์ชันแก้ปัญหา definitiva) ตรวจสอบ FileHash โดยใช้ findall
    เพื่อให้เข้ากันได้กับ gspread ทุกเวอร์ชัน และหลีกเลี่ยง CellNotFound error
    """
    try:
        print(f"DEBUG: [DUPE_CHECK_V2] Checking for hash: {file_hash_to_check}")
        
        # ใช้ findall ซึ่งจะคืนค่าเป็น list ว่าง ถ้าไม่เจอ
        # ทำให้เข้ากันได้กับ gspread หลายเวอร์ชัน และไม่เกิด CellNotFound error
        # สมมติว่า FileHash อยู่คอลัมน์ที่ 6 ('F')
        cell_list = history_ws.findall(file_hash_to_check, in_column=6) 
        
        if cell_list:
            # ถ้าเจอ (list ไม่ว่าง) แสดงว่าซ้ำ
            first_found_cell = cell_list[0]
            print(f"INFO: [DUPE_CHECK_V2] Duplicate hash found at row {first_found_cell.row}")
            
            record = history_ws.row_values(first_found_cell.row)
            headers = history_ws.row_values(1)
            record_dict = dict(zip(headers, record))
            
            details = {
                "PortfolioName": record_dict.get("PortfolioName", "N/A"),
                "UploadTimestamp": record_dict.get("UploadTimestamp", "N/A")
            }
            return True, details
        else:
            # ถ้าไม่เจอ (list ว่าง)
            print("INFO: [DUPE_CHECK_V2] No duplicate hash found. It's a new file.")
            return False, None

    except Exception as e:
        print(f"!!! ERROR: [DUPE_CHECK_V2] An error occurred during duplicate check: {e}")
        traceback.print_exc()
        return False, None

# ฟังก์ชันที่ 2: (วางทับของเดิม) เวอร์ชันสั้นและเรียบง่ายที่แก้ไขแล้ว
def save_upload_history(ws, history_data):
    """
    (เวอร์ชันเรียบง่ายสุดๆ) บันทึกประวัติโดยไม่มีการตรวจสอบที่ซับซ้อน
    """
    try:
        headers = ws.row_values(1)
        if not headers:
            print("!!! ERROR saving history: Header row is empty!")
            return False, "Header row is empty."
            
        row_to_insert = [history_data.get(header, "") for header in headers]
        ws.append_row(row_to_insert)
        return True, "History saved."

    except Exception as e:
        import traceback
        print(f"!!! ERROR saving history: {e}")
        traceback.print_exc()
        return False, str(e)