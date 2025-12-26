# core/supabase_handler.py (ฉบับแก้ไขสมบูรณ์)

import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, date
from config import settings
import numpy as np
import pytz 
import uuid 
# --- การเชื่อมต่อ (Connection) ---
@st.cache_resource
def get_supabase_client() -> Client:
    """
    สร้างและคืนค่า Supabase client โดยใช้ข้อมูลจาก st.secrets
    ใช้ cache_resource เพื่อให้เชื่อมต่อเพียงครั้งเดียวต่อ session
    """
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อ Supabase ได้: {e}")
        return None

# --- ฟังก์ชัน LOAD (อ่านข้อมูล) ---
@st.cache_data(ttl=300) # Cache for 5 minutes
def load_data_from_table(table_name: str) -> pd.DataFrame:
    """
    ฟังก์ชันกลางสำหรับโหลดข้อมูลทั้งหมดจากตารางที่ระบุ
    """
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table(table_name).select('*').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ Supabase Error (load {table_name}): {e}")
        return pd.DataFrame()

def load_portfolios():
    return load_data_from_table("Portfolios")

def load_all_planned_trade_logs():
    return load_data_from_table("PlannedTradeLogs")

def load_actual_trades():
    return load_data_from_table("ActualTrades")

def load_deposit_withdrawal_logs():
    return load_data_from_table("DepositWithdrawalLogs")

def load_upload_history():
    return load_data_from_table("UploadHistory")

def load_statement_summaries():
    return load_data_from_table("StatementSummaries")


# --- ฟังก์ชัน SAVE / UPDATE / DELETE ---

def clear_all_caches():
    """
    ฟังก์ชันสำหรับล้าง cache ทั้งหมดหลังจากมีการเปลี่ยนแปลงข้อมูล
    """
    load_data_from_table.clear()


# Helper function to convert various datetime types to ISO format string
def _convert_datetime_to_iso_string(value):
    if isinstance(value, (datetime, pd.Timestamp, np.datetime64)):
        # Ensure it's a pandas Timestamp for .isoformat() then remove timezone if it's there (Supabase likes naive for 'timestamp' type)
        # Or keep timezone if the Supabase column is 'timestamptz'
        # For simplicity and broad compatibility with 'timestamp' or 'timestamptz' in Supabase:
        # Convert to UTC and then to ISO format string.
        if isinstance(value, np.datetime64):
            value = pd.Timestamp(value)
        
        if value.tz is not None: # If timezone-aware, convert to UTC then naive
             return value.tz_convert(None).isoformat() # Convert to naive UTC and then ISO string
        else: # If timezone-naive, assume UTC for now and convert
             return value.isoformat()
    return value


def _convert_datetime_to_iso_string(value):
    if pd.isna(value):
        return None
    
    if isinstance(value, (datetime, pd.Timestamp, np.datetime64)):
        # --- แก้ไขตรงนี้: ทำให้ value เป็น pandas Timestamp เสมอ ---
        value = pd.Timestamp(value) # แปลงให้เป็น pandas Timestamp เสมอ

        if value.tz is None: # ถ้าไม่มี timezone (naive)
            # โลคัลไลซ์เป็น UTC โดยตรง
            value = value.tz_localize(pytz.utc)
        elif value.tz != pytz.utc: # ถ้ามี timezone แต่ไม่ใช่ UTC ให้แปลงเป็น UTC
            value = value.tz_convert(pytz.utc)
            
        iso_string = value.isoformat(timespec='milliseconds')
        
        # แก้ไขรูปแบบ ISO string เพื่อให้ Supabase รับได้
        if iso_string.endswith('+00:00'):
            return iso_string[:-6] + 'Z' 
        elif iso_string.endswith('Z'):
             return iso_string
        return iso_string + 'Z' # ถ้าไม่มี timezone (หลังแปลงแล้ว) ให้เพิ่ม Z
            
    # ถ้าไม่ใช่ datetime type เลย ให้คืนค่าเดิม
    return value


def save_planned_trade_logs(plan_data_list: list, trade_mode: str, asset_name: str, risk_percentage: float, trade_direction: str, portfolio_id: str, portfolio_name: str) -> tuple[bool, str]:
    """
    บันทึก Trade Plan ใหม่ (อาจมีหลาย entries) ลงในตาราง PlannedTradeLogs
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
        
    try:
        rows_to_insert = []
        ts_now = datetime.now()
        for i, entry_data in enumerate(plan_data_list):
            log_id = f"PLAN-{ts_now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}-{i}"
            
            full_log_entry = {
                "LogID": log_id,
                "PortfolioID": str(portfolio_id),
                "PortfolioName": str(portfolio_name),
                "Timestamp": ts_now.isoformat(), # แปลงเป็น ISO string ตรงนี้
                "Asset": str(asset_name),
                "Mode": str(trade_mode),
                "Direction": str(trade_direction),
                "Risk %": risk_percentage,
                **entry_data
            }
            # Clean values before insertion (e.g., NaN/None/empty string to None, and datetime to ISO string)
            cleaned_entry = {}
            for k, v in full_log_entry.items():
                if pd.isna(v) or v == '':
                    cleaned_entry[k] = None
                else:
                    cleaned_entry[k] = _convert_datetime_to_iso_string(v) # ใช้ helper function
            rows_to_insert.append(cleaned_entry)

        if rows_to_insert:
            response = supabase.table("PlannedTradeLogs").insert(rows_to_insert).execute()
        
        clear_all_caches()
        return True, "บันทึก Trade Plan สำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการบันทึก Trade Plan: {e}"


def update_portfolio(portfolio_id: str, updated_data: dict) -> tuple[bool, str]:
    """
    อัปเดตข้อมูล Portfolio ที่มีอยู่
    """
    supabase = get_supabase_client()
    try:
        # Clean data (e.g., NaN/None/empty string to None, and datetime to ISO string)
        cleaned_data = {}
        for k, v in updated_data.items():
            if pd.isna(v) or v == '':
                cleaned_data[k] = None
            else:
                cleaned_data[k] = _convert_datetime_to_iso_string(v) # ใช้ helper function
        
        response = supabase.table("Portfolios").update(cleaned_data).eq("PortfolioID", portfolio_id).execute()
        clear_all_caches()
        return True, "อัปเดต Portfolio สำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการอัปเดต Portfolio: {e}"


def save_statement_data(data_map: dict) -> tuple[bool, str]:
    overall_success = True
    overall_messages = []

    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้ โปรดตรวจสอบการตั้งค่า"

    # กำหนดลำดับการบันทึกเพื่อจัดการ Foreign Key dependencies (ถ้ามี)
    # ควรบันทึก Portfolios ก่อน ถ้ามีการสร้าง Portfolio ใหม่
    # แล้วค่อยตามด้วย Summary, History, และ Transactional Data
    save_order = [
        settings.SUPABASE_TABLE_PORTFOLIOS, # ถ้ามี portfolio ใหม่
        settings.SUPABASE_TABLE_STATEMENT_SUMMARIES,
        settings.SUPABASE_TABLE_UPLOAD_HISTORY,
        settings.SUPABASE_TABLE_ACTUAL_TRADES,
        settings.SUPABASE_TABLE_ACTUAL_ORDERS,
        settings.SUPABASE_TABLE_ACTUAL_POSITIONS,
        settings.SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS,
        # settings.SUPABASE_TABLE_PLANNED_LOGS, # ถ้ามีบันทึก PlannedLogs ในฟังก์ชันนี้
    ]

    try:
        for table_name in save_order:
            records_data = data_map.get(table_name) # ดึงข้อมูลสำหรับตารางปัจจุบัน

            # ถ้าไม่มีข้อมูลสำหรับตารางนี้ใน data_map ให้ข้ามไป
            if records_data is None:
                continue

            # --- เริ่มต้นการเตรียม records_list_to_insert ให้เป็น list ของ dict เสมอ ---
            records_list_to_insert = []
            
            # Scenario 1: Input records_data is a Pandas DataFrame
            if isinstance(records_data, pd.DataFrame):
                if not records_data.empty:
                    # เลือกเฉพาะคอลัมน์ที่คาดหวังจาก settings เพื่อป้องกันคอลัมน์ที่ไม่รู้จัก
                    expected_headers = settings.WORKSHEET_HEADERS.get(table_name, [])
                    temp_df = records_data.reindex(columns=expected_headers)
                    # ลบแถวที่ว่างเปล่าทั้งหมด (อาจเกิดขึ้นได้หลัง reindex)
                    temp_df = temp_df.dropna(how='all') 
                    
                    # แปลงเป็น list ของ dictionarys ก็ต่อเมื่อ DataFrame ไม่ว่างเปล่า
                    if not temp_df.empty:
                        records_list_to_insert = temp_df.to_dict(orient='records')
                # ถ้า records_data เป็น DataFrame ว่างเปล่า, records_list_to_insert ก็จะยังคงเป็น []

            # Scenario 2: Input records_data is already a list (of dicts)
            elif isinstance(records_data, list):
                records_list_to_insert = records_data

            # Scenario 3: Input records_data is a single dictionary
            elif isinstance(records_data, dict):
                records_list_to_insert = [records_data]

            # Scenario 4: Unexpected type of records_data
            else:
                print(f"Warning: Unexpected data type for {table_name}: {type(records_data)}. Skipping this table.")
                overall_success = False
                overall_messages.append(f"ข้อมูล {table_name} มีชนิดไม่ถูกต้อง")
                continue # ข้ามไปที่ตารางถัดไปในลูป

            # --- สิ้นสุดการเตรียม records_list_to_insert ---

            # ถ้า records_list_to_insert ว่างเปล่า (ไม่มีข้อมูลให้บันทึก) ให้ข้ามไป
            if not records_list_to_insert: # ณ จุดนี้ records_list_to_insert จะเป็น list เสมอ
                print(f"No records to insert for table: {table_name} (List was empty).")
                overall_messages.append(f"ไม่มีข้อมูลสำหรับ {table_name} ที่จะบันทึก")
                continue # ข้ามไปที่ตารางถัดไปในลูป
            
            # ทำความสะอาดข้อมูลในแต่ละ dict เพื่อจัดการ NaN/None ให้ Supabase รับได้
            cleaned_records_to_insert = []
            for row in records_list_to_insert:
                cleaned_row = {}
                for k, v in row.items():
                    # แปลง numpy dtypes (เช่น np.float64, np.int64) เป็น Python native types
                    if isinstance(v, (np.float64, np.int64)):
                        v = float(v) if isinstance(v, np.float64) else int(v)
                    
                    # จัดการ NaN, None, หรือสตริงว่าง ให้เป็น None สำหรับฐานข้อมูล
                    if pd.isna(v) or v == '' or v is None:
                        cleaned_row[k] = None
                    else:
                        # แปลง datetime-like objects เป็น ISO 8601 strings
                        cleaned_row[k] = _convert_datetime_to_iso_string(v)
                cleaned_records_to_insert.append(cleaned_row)
            
            # ถ้า cleaned_records_to_insert ว่างเปล่าหลังจากทำความสะอาด (เช่น ทุกแถวกลายเป็น None) ให้ข้ามไป
            if not cleaned_records_to_insert:
                print(f"No valid records to insert for table: {table_name} after cleaning.")
                overall_messages.append(f"ไม่มีข้อมูลที่ถูกต้องสำหรับ {table_name} ที่จะบันทึก")
                continue


            print(f"Attempting to save {len(cleaned_records_to_insert)} records to {table_name}...")
            
            response = None # ประกาศตัวแปร response
            try:
                # --- เลือกใช้ upsert หรือ insert ตามชื่อตารางและ Unique Key ---
                if table_name == settings.SUPABASE_TABLE_ACTUAL_TRADES:
                    response = supabase.table(table_name).upsert(cleaned_records_to_insert, on_conflict="Deal_ID").execute()
                elif table_name == settings.SUPABASE_TABLE_ACTUAL_ORDERS:
                    response = supabase.table(table_name).upsert(cleaned_records_to_insert, on_conflict="Order_ID_Ord").execute()
                elif table_name == settings.SUPABASE_TABLE_ACTUAL_POSITIONS:
                    response = supabase.table(table_name).upsert(cleaned_records_to_insert, on_conflict="Position_ID").execute()
                elif table_name == settings.SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS:
                    response = supabase.table(table_name).upsert(cleaned_records_to_insert, on_conflict="TransactionID").execute() 
                elif table_name == settings.SUPABASE_TABLE_UPLOAD_HISTORY:
                    response = supabase.table(table_name).upsert(cleaned_records_to_insert, on_conflict="FileHash").execute()
                elif table_name == settings.SUPABASE_TABLE_STATEMENT_SUMMARIES:
                    response = supabase.table(table_name).upsert(cleaned_records_to_insert, on_conflict="PortfolioID").execute()
                elif table_name == settings.SUPABASE_TABLE_PORTFOLIOS: # สำหรับสร้าง/อัปเดตรายละเอียด Portfolio
                    response = supabase.table(table_name).upsert(cleaned_records_to_insert, on_conflict="PortfolioID").execute()
                else: # ใช้ insert เป็นค่าเริ่มต้นสำหรับตารางอื่นๆ
                    response = supabase.table(table_name).insert(cleaned_records_to_insert).execute()
                
                # --- ตรวจสอบผลลัพธ์จาก Supabase API อย่างละเอียด ---
                if hasattr(response, 'error') and response.error is not None:
                    error_detail = response.error.get('message', str(response.error)) if isinstance(response.error, dict) else str(response.error)
                    print(f"Supabase error for {table_name}: {error_detail}")
                    overall_success = False
                    overall_messages.append(f"บันทึกข้อมูล {table_name} ไม่สำเร็จ: {error_detail}")
                elif hasattr(response, 'data') and response.data is not None:
                    if isinstance(response.data, list) and len(response.data) > 0:
                        print(f"Successfully saved {len(response.data)} records to {table_name}.")
                        overall_messages.append(f"บันทึก {len(response.data)} รายการใน {table_name} สำเร็จ")
                    else: # ไม่มีข้อมูลส่งกลับ, แต่ไม่มี error ก็ถือว่าสำเร็จ
                        print(f"Successfully processed {table_name} (no data returned or empty list).")
                        overall_messages.append(f"ประมวลผล {table_name} สำเร็จ (ไม่มีข้อมูลส่งกลับ)")
                else: # response ไม่มีทั้ง 'data' และ 'error' (อาจเป็น APIResponse บางประเภท)
                    print(f"Supabase response for {table_name} had no 'data' or 'error' attribute. Assuming success if no exception raised.")
                    overall_messages.append(f"ประมวลผล {table_name} สำเร็จ")

            except Exception as e_inner: # ดักจับ Python exception ที่อาจเกิดขึ้นระหว่างการเรียก Supabase
                print(f"Python exception during Supabase operation for {table_name}: {e_inner}")
                overall_success = False
                overall_messages.append(f"เกิดข้อผิดพลาดรุนแรงในการบันทึกข้อมูล {table_name}: {e_inner}")
            
        final_overall_message = "บันทึกข้อมูล Statement สำเร็จ!" if overall_success else "บันทึกข้อมูล Statement บางส่วนไม่สำเร็จ:"
        final_overall_message += "\n" + "\n".join(overall_messages) if overall_messages else " (ไม่มีข้อมูลที่จะบันทึก)"

        clear_all_caches()
        return overall_success, final_overall_message
    except Exception as e: # ดักจับ Python exception นอกเหนือจาก Supabase operation
        print(f"Python exception in save_statement_data (outer block): {e}") 
        return False, f"เกิดข้อผิดพลาดในการบันทึกข้อมูล Statement: {e}"

def save_statement_summary(summary_data: dict) -> tuple[bool, str]:
    """
    บันทึกข้อมูลสรุป Statement ลงในตาราง StatementSummaries
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
    try:
        # Clean data (e.g., NaN/None/empty string to None, and datetime to ISO string)
        clean_data = {}
        for k, v in summary_data.items():
            if pd.isna(v) or v == '':
                clean_data[k] = None
            else:
                clean_data[k] = _convert_datetime_to_iso_string(v) # ใช้ helper function

        response = supabase.table("StatementSummaries").insert(clean_data).execute()
        clear_all_caches()
        return True, "บันทึกข้อมูลสรุป Statement สำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการบันทึกข้อมูลสรุป Statement: {e}"

def save_upload_history(history_data: dict) -> tuple[bool, str]:
    """
    บันทึกประวัติการอัปโหลดไฟล์ลงในตาราง UploadHistory
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
    try:
        # Clean data (e.g., NaN/None/empty string to None, and datetime to ISO string)
        clean_data = {}
        for k, v in history_data.items():
            if pd.isna(v) or v == '':
                clean_data[k] = None
            else:
                clean_data[k] = _convert_datetime_to_iso_string(v) # ใช้ helper function

        response = supabase.table("UploadHistory").insert(clean_data).execute()
        clear_all_caches()
        return True, "บันทึกประวัติการอัปโหลดสำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการบันทึกประวัติการอัปโหลด: {e}"

def delete_portfolio(portfolio_id: str) -> tuple[bool, str]:
    """
    ลบ Portfolio ออกจากฐานข้อมูลตาม ID
    """
    supabase = get_supabase_client()
    try:
        response = supabase.table("Portfolios").delete().eq("PortfolioID", portfolio_id).execute()
        clear_all_caches()
        return True, "ลบ Portfolio สำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการลบ Portfolio: {e}"

def check_duplicate_file(file_hash: str, portfolio_id: str) -> tuple[bool, dict]:
    """
    ตรวจสอบว่า file_hash นี้มีอยู่ในตาราง UploadHistory สำหรับ PortfolioID นี้หรือไม่
    """
    supabase = get_supabase_client()
    try:
        response = supabase.table("UploadHistory") \
                           .select('PortfolioName, UploadTimestamp') \
                           .eq('FileHash', file_hash) \
                           .eq('PortfolioID', portfolio_id) \
                           .limit(1) \
                           .execute()
        if response.data:
            return True, response.data[0]
        return False, {}
    except Exception as e:
        st.error(f"Supabase error checking duplicate file: {e}")
        return False, {}