# core/gs_handler.py (เวอร์ชันสมบูรณ์สุดท้าย)
class GSHandlerError(Exception):
    pass
import streamlit as st
import pandas as pd
import numpy as np
import gspread
import traceback
from datetime import datetime
import uuid
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
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("⚠️ โปรดตั้งค่า 'gcp_service_account' ใน `.streamlit/secrets.toml`")
            return None
        return gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
        return None

def setup_and_get_worksheets(gc_client):
    if not gc_client:
        return None, "Google Sheets client not available."
    
    ws_dict = {}
    try:
        sh = gc_client.open(settings.GOOGLE_SHEET_NAME)
        for ws_name, headers in settings.WORKSHEET_HEADERS.items():
            try:
                worksheet = sh.worksheet(ws_name)
                ws_dict[ws_name] = worksheet
            except gspread.exceptions.WorksheetNotFound:
                new_worksheet = sh.add_worksheet(title=ws_name, rows="1", cols=len(headers))
                new_worksheet.update([headers], value_input_option='USER_ENTERED')
                ws_dict[ws_name] = new_worksheet
        return ws_dict, None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดร้ายแรงในการตั้งค่า Google Sheets: {e}")
        traceback.print_exc()
        return None, str(e)

# --- LOAD FUNCTIONS ---
@st.cache_data(ttl=300)
def load_portfolios_from_gsheets():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_PORTFOLIOS)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
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
        df = pd.DataFrame(records) if records else pd.DataFrame()
        if not df.empty and 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=180)
def load_actual_trades_from_gsheets():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(WORKSHEET_ACTUAL_TRADES)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        return pd.DataFrame(records) if records else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=180)
def load_statement_summaries_from_gsheets():
    gc = get_gspread_client()
    if gc is None: return pd.DataFrame()
    try:
        worksheet = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(WORKSHEET_STATEMENT_SUMMARIES)
        records = worksheet.get_all_records(numericise_ignore=['all'])
        return pd.DataFrame(records) if records else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# --- SAVE / UPDATE / DELETE FUNCTIONS ---

def save_new_portfolio_to_gsheets(portfolio_data_dict):
    gc = get_gspread_client()
    if not gc: return False
    try:
        ws = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_PORTFOLIOS)
        headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_PORTFOLIOS]
        new_row = [str(portfolio_data_dict.get(h, "")).strip() for h in headers]
        ws.append_row(new_row, value_input_option='USER_ENTERED')
        load_portfolios_from_gsheets.clear()
        return True, "Portfolio saved successfully!"
        # <<<< สิ้นสุดการแก้ไข Return >>>>
    except Exception as e:
        # <<<< แก้ไข Return ตรงนี้: ให้คืนค่า False และข้อความข้อผิดพลาด >>>>
        return False, f"Error saving portfolio: {e}"

def update_portfolio_in_gsheets(portfolio_id, updated_data_dict):
    gc = get_gspread_client()
    if not gc: return False
    try:
        ws = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_PORTFOLIOS)
        cell = ws.find(portfolio_id, in_column=1)
        if not cell: return False
        headers = ws.row_values(1)
        updated_row = [str(updated_data_dict.get(h, "")).strip() for h in headers]
        ws.update(f'A{cell.row}', [updated_row], value_input_option='USER_ENTERED')
        load_portfolios_from_gsheets.clear()
        return True, "Portfolio updated successfully!"
        # <<<< สิ้นสุดการแก้ไข Return >>>>
    except Exception as e:
        # <<<< แก้ไข Return ตรงนี้: ให้คืนค่า False และข้อความข้อผิดพลาด >>>>
        return False, f"Error updating portfolio: {e}"

def update_portfolio_account_id(gc, portfolio_id_to_find, new_account_id):
    if not gc: return False, "Google Sheets client is not available."
    try:
        ws = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_PORTFOLIOS)
        cell = ws.find(portfolio_id_to_find, in_column=1)
        if not cell: return False, f"Portfolio with ID '{portfolio_id_to_find}' not found."
        headers = ws.row_values(1)
        if 'AccountID' not in headers: return False, "'AccountID' column not found."
        account_id_col_index = headers.index('AccountID') + 1
        ws.update_cell(cell.row, account_id_col_index, str(new_account_id))
        load_portfolios_from_gsheets.clear()
        return True, "Successfully registered Account ID."
    except Exception as e:
        return False, f"An unexpected error occurred: {e}"

def delete_portfolio_from_gsheets(portfolio_id_to_delete: str):
    gc = get_gspread_client()
    if not gc: return False, "Connection to Google Sheets failed."
    try:
        ws = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_PORTFOLIOS)
        cell = ws.find(portfolio_id_to_delete, in_column=1)
        if cell:
            ws.delete_rows(cell.row)
            load_portfolios_from_gsheets.clear()
            return True, f"Portfolio has been deleted."
        else:
            return False, f"Portfolio ID not found."
    except Exception as e:
        return False, f"An error occurred during deletion: {e}"

def save_plan_to_gsheets(plan_data_list, trade_mode_arg, asset_name, risk_percentage, trade_direction, portfolio_id, portfolio_name):
    gc = get_gspread_client()
    if not gc: return False
    try:
        ws = gc.open(settings.GOOGLE_SHEET_NAME).worksheet(settings.WORKSHEET_PLANNED_LOGS)
        headers = settings.WORKSHEET_HEADERS[settings.WORKSHEET_PLANNED_LOGS]
        ts_now = datetime.now()
        rows_to_append = []
        for i, entry in enumerate(plan_data_list):
            log_id = f"{ts_now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}-{i}"
            row_dict = {"LogID": log_id, "PortfolioID": str(portfolio_id), "PortfolioName": str(portfolio_name), "Timestamp": ts_now.strftime("%Y-%m-%d %H:%M:%S"), "Asset": str(asset_name), "Mode": str(trade_mode_arg), "Direction": str(trade_direction), "Risk %": str(risk_percentage), **entry}
            rows_to_append.append([str(row_dict.get(h, "")) for h in headers])
        if rows_to_append:
            ws.append_rows(rows_to_append, value_input_option='USER_ENTERED')
            load_all_planned_trade_logs_from_gsheets.clear()
        return True
    except Exception:
        return False

# --- STATEMENT PROCESSING HELPER FUNCTIONS (Must be present) ---

def _save_transactional_data(ws, df_input, unique_id_col, expected_headers_with_portfolio, data_type_name, portfolio_id, portfolio_name, source_file_name="N/A", import_batch_id="N/A"):
    if df_input is None or df_input.empty:
        return True, 0, 0
    try:
        if ws.row_count > 1:
            all_sheet_records = ws.get_all_records(expected_headers=expected_headers_with_portfolio, numericise_ignore=['all'])
            df_existing = pd.DataFrame(all_sheet_records) if all_sheet_records else pd.DataFrame()
            if not df_existing.empty and 'PortfolioID' in df_existing.columns and unique_id_col in df_existing.columns:
                df_portfolio_data = df_existing[df_existing['PortfolioID'] == str(portfolio_id)]
                existing_ids = set(df_portfolio_data[unique_id_col].astype(str).str.strip().tolist()) if not df_portfolio_data.empty else set()
            else:
                existing_ids = set()
        else:
            existing_ids = set()

        df_to_check = df_input.copy()
        df_to_check[unique_id_col] = df_to_check[unique_id_col].astype(str).str.strip()
        new_df = df_to_check[~df_to_check[unique_id_col].isin(existing_ids)]
        
        if new_df.empty:
            return True, 0, len(df_to_check)

        new_df_to_save = new_df.copy()
        new_df_to_save["PortfolioID"] = str(portfolio_id)
        new_df_to_save["PortfolioName"] = str(portfolio_name)
        new_df_to_save["SourceFile"] = str(source_file_name)
        new_df_to_save["ImportBatchID"] = str(import_batch_id)
        
        final_df = pd.DataFrame(columns=expected_headers_with_portfolio)
        for col in expected_headers_with_portfolio:
            if col in new_df_to_save.columns: final_df[col] = new_df_to_save[col]
            else: final_df[col] = ""
                
        list_of_lists = final_df.astype(str).replace('nan', '').fillna("").values.tolist()
        
        if list_of_lists:
            ws.append_rows(list_of_lists, value_input_option='USER_ENTERED')
        return True, len(new_df), len(df_to_check) - len(new_df)
    except Exception as e:
        st.error(f"Error saving {data_type_name}: {e}")
        return False, 0, 0

def save_deals_to_actual_trades(ws, df_deals_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_TRADES]
    ok, new, skipped = _save_transactional_data(ws, df_deals_input, "Deal_ID", expected_headers, "Deals", portfolio_id, portfolio_name, source_file_name, import_batch_id)
    return ok, f"New:{new}, Skipped:{skipped}", new, skipped

def save_orders_to_actul_orders(ws, df_orders_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_ORDERS]
    ok, new, skipped = _save_transactional_data(ws, df_orders_input, "Order_ID_Ord", expected_headers, "Orders", portfolio_id, portfolio_name, source_file_name, import_batch_id)
    return ok, f"New:{new}, Skipped:{skipped}", new, skipped

def save_positions_to_actul_positions(ws, df_positions_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_ACTUAL_POSITIONS]
    ok, new, skipped = _save_transactional_data(ws, df_positions_input, "Position_ID", expected_headers, "Positions", portfolio_id, portfolio_name, source_file_name, import_batch_id)
    return ok, f"New:{new}, Skipped:{skipped}", new, skipped

def save_deposit_withdrawal_logs(ws, df_dw_logs_input, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS]
    ok, new, skipped = _save_transactional_data(ws, df_dw_logs_input, "TransactionID", expected_headers, "D/W Logs", portfolio_id, portfolio_name, source_file_name, import_batch_id)
    return ok, f"New:{new}, Skipped:{skipped}", new, skipped

def save_results_summary_to_gsheets(ws, summary_data, portfolio_id, portfolio_name, source_file_name, import_batch_id):
    try:
        expected_headers = settings.WORKSHEET_HEADERS[WORKSHEET_STATEMENT_SUMMARIES]
        new_row_data = {h: "" for h in expected_headers}
        new_row_data.update({"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "PortfolioID": str(portfolio_id), "PortfolioName": str(portfolio_name), "SourceFile": str(source_file_name), "ImportBatchID": str(import_batch_id)})
        if isinstance(summary_data, dict):
            for key, value in summary_data.items():
                if key in new_row_data:
                    new_row_data[key] = value
        
        # 2. "บังคับเขียนทับ" ด้วย ID และ Name ที่ถูกต้องจาก Sidebar เสมอ
        # เพื่อป้องกันไม่ให้ Account ID จากไฟล์มาเขียนทับ ID ของระบบ
        new_row_data.update({
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "PortfolioID": str(portfolio_id),
            "PortfolioName": str(portfolio_name),
            "SourceFile": str(source_file_name),
            "ImportBatchID": str(import_batch_id)
        })
        final_row_values = [str(new_row_data.get(h, "")).strip() for h in expected_headers]
        ws.append_row(final_row_values, value_input_option='USER_ENTERED')
        load_statement_summaries_from_gsheets.clear()
        return True, "Summary saved."
    except Exception as e:
        return False, str(e)

def check_for_duplicate_file_hash(history_ws, file_hash_to_check):
    try:
        cell_list = history_ws.findall(file_hash_to_check, in_column=6)
        if cell_list:
            record = history_ws.row_values(cell_list[0].row)
            headers = history_ws.row_values(1)
            record_dict = dict(zip(headers, record))
            details = {"PortfolioName": record_dict.get("PortfolioName", "N/A"), "UploadTimestamp": record_dict.get("UploadTimestamp", "N/A")}
            return True, details
        return False, None
    except Exception:
        return False, None

def save_upload_history(ws, history_data):
    try:
        headers = ws.row_values(1)
        if not headers: headers = settings.WORKSHEET_HEADERS[WORKSHEET_UPLOAD_HISTORY]
        row_to_insert = [history_data.get(header, "") for header in headers]
        ws.append_row(row_to_insert, value_input_option='USER_ENTERED')
        return True, "History saved."
    except Exception as e:
        return False, str(e)

# --- THE ORCHESTRATOR FUNCTION (added in Phase 3) ---
def save_full_statement_data(gc, extracted_data, file_info, active_portfolio_id, active_portfolio_name):
    try:
        ws_dict, setup_error = setup_and_get_worksheets(gc)
        if setup_error: return False, f"GSheet Setup Error: {setup_error}"

        is_duplicate, details = check_for_duplicate_file_hash(ws_dict.get(WORKSHEET_UPLOAD_HISTORY), file_info['hash'])
        if is_duplicate: return False, f"Duplicate File: Already uploaded on {details.get('UploadTimestamp')} for '{details.get('PortfolioName', 'N/A')}'."
        
        has_errors = False
        error_messages = []
        import_batch_id = str(uuid.uuid4())
        
        deals_df = extracted_data.get('deals', pd.DataFrame())
        orders_df = extracted_data.get('orders', pd.DataFrame())
        positions_df = extracted_data.get('positions', pd.DataFrame())
        deposit_withdrawal_logs = extracted_data.get('deposit_withdrawal_logs', [])
        final_summary_data = extracted_data.get('final_summary_data', {})

        ok_d, msg_d, num_d, skip_d = save_deals_to_actual_trades(ws_dict.get(WORKSHEET_ACTUAL_TRADES), deals_df, active_portfolio_id, active_portfolio_name, file_info['name'], import_batch_id)
        if not ok_d: has_errors = True; error_messages.append("Deals")

        ok_o, msg_o, num_o, skip_o = save_orders_to_actul_orders(ws_dict.get(WORKSHEET_ACTUAL_ORDERS), orders_df, active_portfolio_id, active_portfolio_name, file_info['name'], import_batch_id)
        if not ok_o: has_errors = True; error_messages.append("Orders")

        ok_p, msg_p, num_p, skip_p = save_positions_to_actul_positions(ws_dict.get(WORKSHEET_ACTUAL_POSITIONS), positions_df, active_portfolio_id, active_portfolio_name, file_info['name'], import_batch_id)
        if not ok_p: has_errors = True; error_messages.append("Positions")
        
        ok_s, msg_s = save_results_summary_to_gsheets(ws_dict.get(WORKSHEET_STATEMENT_SUMMARIES), final_summary_data, active_portfolio_id, active_portfolio_name, file_info['name'], import_batch_id)
        if not ok_s: has_errors = True; error_messages.append(f"Summaries: {msg_s}")

        ok_dw, msg_dw, num_dw, skip_dw = save_deposit_withdrawal_logs(ws_dict.get(WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS), deposit_withdrawal_logs, active_portfolio_id, active_portfolio_name, file_info['name'], import_batch_id)
        if not ok_dw: has_errors = True; error_messages.append("D/W_Logs")

        history_log = {"UploadTimestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "PortfolioID": active_portfolio_id, "PortfolioName": active_portfolio_name, "FileName": file_info['name'], "FileHash": file_info['hash'], "Status": "Success" if not has_errors else "Failed", "ImportBatchID": import_batch_id, "Notes": "Completed" if not has_errors else f"Errors in: {', '.join(error_messages)}"}
        save_upload_history(ws_dict.get(WORKSHEET_UPLOAD_HISTORY), history_log)

        if has_errors: return False, "Data saved with some errors."
        return True, "All data saved successfully!"
    except Exception as e:
        traceback.print_exc()
        return False, f"A critical failure occurred in the saving orchestrator: {e}"
    
def is_file_already_uploaded(file_hash: str, gc: gspread.Client):
    """
    ตรวจสอบว่าไฟล์ที่มี hash นี้เคยถูกอัปโหลดไปแล้วหรือยัง

    Args:
        file_hash: รหัส MD5 ของไฟล์ใหม่
        gc: gspread client ที่เชื่อมต่อแล้ว

    Returns:
        A tuple (bool, dict): 
        - (True, details_dict) หากไฟล์ซ้ำ
        - (False, None) หากไฟล์ไม่ซ้ำ
    """
    try:
        # เปิด worksheet ที่เก็บประวัติการอัปโหลด
        spreadsheet = gc.open_by_key(settings.GOOGLE_SHEET_KEY)
        history_ws = spreadsheet.worksheet(settings.WORKSHEET_UPLOAD_HISTORY)
        
        # ดึงข้อมูลทั้งหมดมาตรวจสอบ
        records = history_ws.get_all_records()
        if not records:
            return False, None # ถ้ายังไม่มีประวัติ ก็ไม่ถือว่าซ้ำ

        # สร้าง set ของ hash ที่มีอยู่เพื่อการค้นหาที่รวดเร็ว
        existing_hashes = {str(record.get('FileHash')) for record in records}

        if file_hash in existing_hashes:
            # หากเจอไฟล์ที่ซ้ำ ให้ดึงรายละเอียดของไฟล์นั้นกลับไป
            for record in records:
                if str(record.get('FileHash')) == file_hash:
                    duplicate_details = {
                        "PortfolioName": record.get('PortfolioName'),
                        "UploadTimestamp": record.get('UploadTimestamp')
                    }
                    return True, duplicate_details
        
        # หากวนลูปจนครบแล้วไม่เจอ ก็ไม่ซ้ำ
        return False, None

    except gspread.exceptions.WorksheetNotFound:
        print(f"Warning: ไม่พบ Worksheet ชื่อ '{settings.WORKSHEET_UPLOAD_HISTORY}'")
        return False, None
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในฟังก์ชัน is_file_already_uploaded: {e}")
        # ในกรณีที่เกิด Error อื่นๆ ให้ถือว่าไม่ซ้ำไปก่อน เพื่อให้โปรแกรมทำงานต่อได้
        return False, None
    
def calculate_true_equity_curve(df_summaries: pd.DataFrame, portfolio_id: str):
    """
    คำนวณ True Equity Curve, Realized Net Profit, Total Deposit, Total Withdrawal
    จาก DataFrame สรุป Statement.
    """
    # ---- START: การแก้ไขที่สำคัญที่สุด ----
    # 1. ตรวจสอบก่อนว่า df_summaries มีข้อมูลและคอลัมน์ PortfolioID หรือไม่
    #    นี่คือการป้องกันข้อผิดพลาด KeyError เมื่อชีตว่าง
    if df_summaries is None or df_summaries.empty or 'PortfolioID' not in df_summaries.columns:
        # ถ้าไม่มีข้อมูล ให้คืนค่าเริ่มต้นทั้งหมดทันที เพื่อไม่ให้แอปแครช
        return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0
    
    # 2. บังคับให้คอลัมน์ PortfolioID เป็นประเภท string เพื่อป้องกันปัญหา Data Type
    df_summaries['PortfolioID'] = df_summaries['PortfolioID'].astype(str)
    # ---- END: การแก้ไขที่สำคัญที่สุด ----

    # กรองข้อมูลสำหรับ Portfolio ที่เลือกและเรียงตาม Timestamp
    df_filtered = df_summaries[df_summaries['PortfolioID'] == str(portfolio_id)].sort_values(by='Timestamp').copy()

    if df_filtered.empty:
        return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0

    # --- ตรวจสอบและแปลงประเภทข้อมูล ---
    numeric_cols = ['Balance', 'Deposit', 'Withdrawal', 'Total_Net_Profit', 'Equity']
    for col in numeric_cols:
        if col not in df_filtered.columns:
            df_filtered[col] = 0.0
        else:
            # ทำความสะอาดข้อมูลก่อนแปลงค่า
            df_filtered[col] = pd.to_numeric(
                df_filtered[col].astype(str).str.replace(',', '').str.replace(' ', ''), 
                errors='coerce'
            ).fillna(0)

    df_filtered['Timestamp'] = pd.to_datetime(df_filtered['Timestamp'], errors='coerce')
    df_filtered.dropna(subset=['Timestamp'], inplace=True)

    if df_filtered.empty:
        return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0

    # --- คำนวณ Metrics ที่ต้องการ ---
    df_filtered['Equity For Chart'] = df_filtered['Balance']
    total_deposit = df_filtered['Deposit'].sum()
    total_withdrawal = df_filtered['Withdrawal'].sum()
    initial_balance = df_filtered['Balance'].iloc[0] if not df_filtered.empty else 0
    final_balance = df_filtered['Balance'].iloc[-1] if not df_filtered.empty else 0
    realized_net_profit = final_balance - initial_balance + total_withdrawal - total_deposit
    total_net_profit_from_sheet = df_filtered['Total_Net_Profit'].iloc[-1] if not df_filtered.empty else 0.0

    return df_filtered, realized_net_profit, total_deposit, total_withdrawal, total_net_profit_from_sheet
