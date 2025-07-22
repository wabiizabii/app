# core/supabase_handler.py (ฉบับแก้ไขสมบูรณ์ - ไม่มีระบบ Login)

import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, date
from config import settings
import numpy as np
import pytz 
import uuid 
import hashlib 
import base64
import os
from typing import Optional, Any

# --- ส่วนนี้ถูกต้องแล้ว ไม่ต้องแก้ไข ---
USER_SPECIFIC_TABLES = [
    "Portfolios", "PlannedTradeLogs", "ActualTrades", "ActualOrders",
    "ActualPositions", "StatementSummaries", "UploadHistory", "DepositWithdrawalLogs",
    "user_profiles"
]

@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อ Supabase ได้: {e}")
        return None

# --- ลบฟังก์ชันที่เกี่ยวข้องกับการ Login/Authentication ออกทั้งหมด ---
# def _generate_pkce_verifier(length=64):
#     """Generates a high-entropy cryptographic random string for PKCE."""
#     return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8').replace('=', '')

# def _generate_pkce_challenge(verifier: str):
#     """Creates a SHA256 challenge from the verifier for PKCE."""
#     digest = hashlib.sha256(verifier.encode('utf-8')).digest()
#     return base64.urlsafe_b64encode(digest).decode('utf-8').replace('=', '')

# def sign_in_with_provider(provider: str) -> tuple[bool, str]:
#     """
#     Generates PKCE verifier/challenge, stores verifier in session state,
#     and returns the full authorization URL.
#     """
#     supabase = get_supabase_client()
#     if not supabase:
#         return False, "Supabase client not initialized."

#     try:
#         code_verifier = _generate_pkce_verifier()
#         st.session_state['pkce_code_verifier'] = code_verifier
#         print("DEBUG: Generated and stored 'pkce_code_verifier' in session state.")

#         code_challenge = _generate_pkce_challenge(code_verifier)

#         response = supabase.auth.sign_in_with_oauth({
#             "provider": provider,
#             "options": {
#                 "redirect_to": "http://localhost:8501", # Ensure this matches Supabase config
#                 "code_challenge": code_challenge,
#                 "code_challenge_method": "S256",
#             },
#         })
#         print(f"DEBUG: Generated OAuth URL: {response.url}")
#         return True, response.url
#     except Exception as e:
#         print(f"DEBUG: Error in sign_in_with_provider: {e}")
#         return False, f"Error starting login process: {e}"

# def complete_oauth_flow(auth_code: str, code_verifier: str) -> Optional[Any]:
#     """
#     Exchanges the authorization code and verifier for a user session.
#     Returns the user object on success, None on failure.
#     """
#     supabase = get_supabase_client()
#     if not supabase:
#         st.error("Supabase client not available for completing login.")
#         return None

#     try:
#         print("DEBUG: Attempting to exchange code for session with verifier.")
#         session = supabase.auth.exchange_code_for_session({
#             "auth_code": auth_code,
#             "code_verifier": code_verifier,
#         })
#         if session and session.user:
#             print(f"DEBUG: Code exchange successful for {session.user.email}")
#             return session.user
#         return None
#     except Exception as e:
#         print(f"DEBUG: Exception during code exchange: {e}")
#         st.error(f"Login failed during final step: {e}")
#         return None

# def get_current_user_session() -> Optional[Any]:
#     """
#     Simply gets the current user session from Supabase if one exists.
#     Does not handle any part of the OAuth flow.
#     """
#     try:
#         supabase = get_supabase_client()
#         session = supabase.auth.get_session()
#         if session and session.user:
#             return session.user
#         return None
#     except Exception:
#         return None

# def sign_in(email: str, password: str) -> tuple[bool, str, Optional[Any]]:
#     """Signs in a user with email and password."""
#     supabase = get_supabase_client()
#     if not supabase:
#         return False, "ไม่สามารถเชื่อมต่อ Supabase ได้", None
#     try:
#         response = supabase.auth.sign_in_with_password({"email": email, "password": password})
#         if response and response.user:
#             return True, "เข้าสู่ระบบสำเร็จ!", response.user
#         else:
#             error_message = "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
#             if response and hasattr(response, 'error') and response.error:
#                 error_message = response.error.message
#             return False, error_message, None
#     except Exception as e:
#         return False, f"เกิดข้อผิดพลาดในการเข้าสู่ระบบ: {e}", None

# def sign_up(email: str, password: str) -> tuple[bool, str]:
#     """Signs up a new user with email and password."""
#     supabase = get_supabase_client()
#     if not supabase:
#         return False, "Supabase client not available."
#     try:
#         response = supabase.auth.sign_up({"email": email, "password": password})
#         if response and response.user:
#             return True, "การลงทะเบียนสำเร็จ! กรุณาตรวจสอบอีเมลของคุณเพื่อยืนยันบัญชี"
#         elif response and response.error:
#             return False, response.error.message
#         return False, "การลงทะเบียนไม่สำเร็จ"
#     except Exception as e:
#         return False, str(e)

# def sign_out() -> tuple[bool, str]:
#     """Signs out the current user."""
#     supabase = get_supabase_client()
#     if not supabase: return False, "Supabase client not available."
#     try:
#         supabase.auth.sign_out()
#         return True, "Logout สำเร็จ!"
#     except Exception as e:
#         return False, str(e)

# --- Data Loading Functions ---
@st.cache_data(ttl=300)
def load_data_from_table(table_name: str, user_id: str = None) -> pd.DataFrame:
    """
    Central function to load data, optionally filtered by user_id.
    """
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    try:
        query = supabase.table(table_name).select('*')
        # If user_id is provided and table is user-specific, add filtering
        if user_id and table_name in USER_SPECIFIC_TABLES:
            query = query.eq('id', user_id) if table_name == "user_profiles" else query.eq('UserID', user_id)
            
        response = query.execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ Supabase Error (load {table_name}): {e}")
        return pd.DataFrame()

# Specific load functions (now pass user_id)
def load_portfolios(user_id: str) -> pd.DataFrame:
    return load_data_from_table(settings.SUPABASE_TABLE_PORTFOLIOS, user_id)

def load_all_planned_trade_logs(user_id: str) -> pd.DataFrame:
    return load_data_from_table(settings.SUPABASE_TABLE_PLANNED_LOGS, user_id)

def load_actual_trades(user_id: str) -> pd.DataFrame:
    return load_data_from_table(settings.SUPABASE_TABLE_ACTUAL_TRADES, user_id)

def load_deposit_withdrawal_logs(user_id: str) -> pd.DataFrame:
    return load_data_from_table(settings.SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS, user_id)

def load_upload_history(user_id: str) -> pd.DataFrame:
    return load_data_from_table(settings.SUPABASE_TABLE_UPLOAD_HISTORY, user_id)

def load_statement_summaries(user_id: str) -> pd.DataFrame:
    return load_data_from_table(settings.SUPABASE_TABLE_STATEMENT_SUMMARIES, user_id)

# Load all user profiles (for Admin Panel)
def load_all_user_profiles() -> pd.DataFrame: # No user_id filter, relies on RLS for Admin access
    return load_data_from_table("user_profiles")


# --- ลบฟังก์ชัน Authentication Functions ออกทั้งหมด ---
# def sign_in_with_provider(provider_name: str) -> tuple[bool, str]:
#     print(f"DEBUG: sign_in_with_provider called for provider: {provider_name}")
#     supabase = get_supabase_client()
#     if not supabase:
#         return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
#     try:
#         response = supabase.auth.sign_in_with_oauth({
#             "provider": provider_name,
#             "options": {
#                 # ตรวจสอบว่า URL นี้ถูกต้อง 100%
#                 "redirect_to": "http://localhost:8501"
#             }
#         })

#         if response and response.url:
#             print(f"DEBUG: Supabase OAuth URL generated: {response.url}")
#             return True, response.url # คืนค่า URL ออกไป
#         else:
#             error_message = "ไม่สามารถสร้าง OAuth URL ได้"
#             print(f"DEBUG: OAuth URL generation failed.")
#             return False, error_message

#     except Exception as e:
#         print(f"DEBUG: Exception during OAuth sign-in: {e}")
#         return False, f"เกิดข้อผิดพลาดในการ Login ({provider_name}): {e}"

# # แก้ไขฟังก์ชันนี้ให้ "โง่" ที่สุด คือแค่ไปเอา session มา ไม่ต้องมี logic ซับซ้อน

# def get_current_user_session() -> Optional[Any]:
#     """
#     Simply gets the current user session from Supabase.
#     The logic to handle the code exchange will be in app.py.
#     """
#     print("DEBUG: Attempting to get current user session...")
#     try:
#         supabase = get_supabase_client()
#         session = supabase.auth.get_session()
#         if session and session.user:
#             print(f"DEBUG: Session successfully retrieved for user: {session.user.email}")
#             return session.user
#         print("DEBUG: No active session found by get_session().")
#         return None
#     except Exception as e:
#         print(f"DEBUG: Exception in get_current_user_session: {e}")
#         return None
    
# def sign_up(email: str, password: str) -> tuple[bool, str]: # Added type hints, simplified return
#     """Signs up a new user with email and password."""
#     supabase = get_supabase_client()
#     if not supabase:
#         return False, "Supabase client not available."
#     try:
#         # res = supabase.auth.sign_up({"email": email, "password": password})
#         # For sign_up, Supabase now often returns data directly if no email confirmation is needed
#         # Or an error if email confirmation is required but fails.
#         # It's better to explicitly check for a user in the response for success.
#         response = supabase.auth.sign_up({"email": email, "password": password})
#         if response and response.user:
#             return True, "การลงทะเบียนสำเร็จ! กรุณาตรวจสอบอีเมลของคุณเพื่อยืนยันบัญชี"
#         elif response and response.error:
#             return False, response.error.message
#         return False, "การลงทะเบียนไม่สำเร็จ ไม่พบข้อผิดพลาดที่ชัดเจน."
#     except Exception as e:
#         return False, str(e)

# def sign_in(email: str, password: str) -> tuple[bool, str, Optional[Any]]:
#     """Signs in a user with email and password."""
#     supabase = get_supabase_client()
#     if not supabase:
#         return False, "ไม่สามารถเชื่อมต่อ Supabase ได้", None
#     try:
#         response = supabase.auth.sign_in_with_password({"email": email, "password": password})

#         print(f"Sign-in response: {response}")
#         if response and response.user:
#             print(f"User signed in: ID={response.user.id}, Email={response.user.email}")
#         else:
#             print(f"Sign-in failed: No user object in response or response is None.")

#         if response and response.user:
#             return True, "เข้าสู่ระบบสำเร็จ!", response.user
#         else:
#             error_message = "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง หรือเกิดข้อผิดพลาดอื่น ๆ"
#             if response and hasattr(response, 'error') and response.error:
#                 error_message = response.error.message
#             return False, error_message, None
#     except Exception as e:
#         print(f"Exception during sign-in: {e}")
#         return False, f"เกิดข้อผิดพลาดในการเข้าสู่ระบบ: {e}", None

# def sign_out() -> tuple[bool, str]: # Added return type
#     """Signs out the current user."""
#     supabase = get_supabase_client()
#     if not supabase: return False, "Supabase client not available."
#     try:
#         supabase.auth.sign_out()
#         return True, "Logout สำเร็จ!"
#     except Exception as e:
#         return False, str(e)

def clear_all_caches():
    """
    Function to clear all caches after data changes.
    """
    load_data_from_table.clear() # Calls .clear() on the cached function directly


# --- Helper for Datetime Conversion ---
def _convert_datetime_to_iso_string(value: Any) -> Optional[str]: # Added type hints
    """
    Helper function to convert various datetime types to ISO 8601 format string
    suitable for Supabase timestamp/timestamptz columns.
    """
    if pd.isna(value):
        return None
    
    if isinstance(value, (datetime, pd.Timestamp, np.datetime64)):
        value = pd.Timestamp(value) 

        if value.tz is None: 
            value = value.tz_localize(pytz.utc)
        elif value.tz != pytz.utc: 
            value = value.tz_convert(pytz.utc)
            
        iso_string = value.isoformat(timespec='milliseconds')
        
        if iso_string.endswith('+00:00'):
            return iso_string[:-6] + 'Z' 
        return iso_string

    return value

# --- Data Save/Update/Delete Functions ---
def save_planned_trade_logs(user_id: str, plan_data_list: list, trade_mode: str, asset_name: str, risk_percentage: float, trade_direction: str, portfolio_id: str, portfolio_name: str) -> tuple[bool, str]:
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
                "Timestamp": ts_now.isoformat(),
                "Asset": str(asset_name),
                "Mode": str(trade_mode),
                "Direction": str(trade_direction),
                "Risk %": risk_percentage,
                "UserID": user_id,
                **entry_data
            }
            cleaned_entry = {}
            for k, v in full_log_entry.items():
                if pd.isna(v) or v == '':
                    cleaned_entry[k] = None
                else:
                    cleaned_entry[k] = _convert_datetime_to_iso_string(v)
            rows_to_insert.append(cleaned_entry)

        if rows_to_insert:
            response = supabase.table(settings.SUPABASE_TABLE_PLANNED_LOGS).insert(rows_to_insert).execute() # Use settings constant here

        clear_all_caches()
        return True, "บันทึก Trade Plan สำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการบันทึก Trade Plan: {e}"

def save_portfolio(user_id: str, portfolio_data: dict) -> tuple[bool, str]:
    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
    try:
        cleaned_data = {}
        for k, v in portfolio_data.items():
            if pd.isna(v) or v == '':
                cleaned_data[k] = None
            else:
                cleaned_data[k] = _convert_datetime_to_iso_string(v)

        cleaned_data["UserID"] = user_id

        response = supabase.table(settings.SUPABASE_TABLE_PORTFOLIOS).upsert(cleaned_data, on_conflict="PortfolioID").execute() # Use settings constant here
        clear_all_caches()
        return True, f"บันทึก Portfolio '{portfolio_data.get('PortfolioName', '')}' สำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการบันทึก Portfolio: {e}"

def update_portfolio(user_id: str, portfolio_id: str, updated_data: dict) -> tuple[bool, str]:
    """
    Updates existing Portfolio data.
    """
    supabase = get_supabase_client()
    try:
        cleaned_data = {}
        for k, v in updated_data.items():
            if pd.isna(v) or v == '':
                cleaned_data[k] = None
            else:
                cleaned_data[k] = _convert_datetime_to_iso_string(v)

        cleaned_data["UserID"] = user_id

        response = supabase.table(settings.SUPABASE_TABLE_PORTFOLIOS).update(cleaned_data).eq("PortfolioID", portfolio_id).eq("UserID", user_id).execute() # Use settings constant here
        clear_all_caches()
        return True, "อัปเดต Portfolio สำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการอัปเดต Portfolio: {e}"

def delete_portfolio(user_id: str, portfolio_id: str) -> tuple[bool, str]:
    """Deletes a Portfolio and its related sub-data."""
    supabase = get_supabase_client()
    if not supabase: return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
    try:
        # Clear related data first (RLS applies here too)
        success_clear, msg_clear = clear_portfolio_specific_data(user_id, portfolio_id)
        if not success_clear:
            st.warning(f"⚠️ เกิดข้อผิดพลาดในการลบข้อมูลย่อยสำหรับ Portfolio '{portfolio_id}': {msg_clear}")

        # Delete the main portfolio record (RLS enforces owner deletion)
        response = supabase.table(settings.SUPABASE_TABLE_PORTFOLIOS).delete().eq("PortfolioID", portfolio_id).eq("UserID", user_id).execute() # Use settings constant here
        clear_all_caches()
        return True, f"ลบ Portfolio '{portfolio_id}' และข้อมูลที่เกี่ยวข้องสำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการลบ Portfolio: {e}"

def clear_portfolio_specific_data(user_id: str, portfolio_id: str) -> tuple[bool, str]:
    """Clears all sub-data related to a specific Portfolio."""
    supabase = get_supabase_client()
    if not supabase: return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
    tables_to_clear = [
        settings.SUPABASE_TABLE_ACTUAL_TRADES, settings.SUPABASE_TABLE_ACTUAL_ORDERS,
        settings.SUPABASE_TABLE_ACTUAL_POSITIONS, settings.SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS,
        settings.SUPABASE_TABLE_STATEMENT_SUMMARIES, settings.SUPABASE_TABLE_UPLOAD_HISTORY,
        settings.SUPABASE_TABLE_PLANNED_LOGS,
    ]
    overall_success = True
    messages = []
    for table_name in tables_to_clear:
        try:
            # Ensure deletion is constrained by both PortfolioID and UserID for safety
            response = supabase.table(table_name).delete().eq("PortfolioID", portfolio_id).eq("UserID", user_id).execute()
            if hasattr(response, 'error') and response.error is not None: # Check for error object directly
                error_detail = response.error.get('message', str(response.error)) if isinstance(response.error, dict) else str(response.error)
                messages.append(f"❌ ลบข้อมูลจาก {table_name} ไม่สำเร็จ: {error_detail}")
                overall_success = False
            else:
                messages.append(f"✔️ ลบข้อมูลจาก {table_name} สำเร็จ")
        except Exception as e: # Catch any Python exceptions during the call
            messages.append(f"❌ เกิดข้อผิดพลาดในการลบข้อมูลจาก {table_name}: {e}")
            overall_success = False
    
    clear_all_caches()
    final_message = "การลบข้อมูล Portfolio เสร็จสมบูรณ์:" if overall_success else "เกิดข้อผิดพลาดในการลบข้อมูล Portfolio บางส่วน:"
    final_message += "\n" + "\n".join(messages)
    return overall_success, final_message

def save_statement_data(user_id: str, data_map: dict, file_account_id: str, uploaded_file_name: str, file_hash: str) -> tuple[bool, str]: # Added user_id
    overall_success = True
    overall_messages = []

    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้ โปรดตรวจสอบการตั้งค่า"

    save_order = [
        settings.SUPABASE_TABLE_STATEMENT_SUMMARIES,
        settings.SUPABASE_TABLE_UPLOAD_HISTORY,
        settings.SUPABASE_TABLE_ACTUAL_TRADES,
        settings.SUPABASE_TABLE_ACTUAL_ORDERS,
        settings.SUPABASE_TABLE_ACTUAL_POSITIONS,
        settings.SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS,
    ]

    try:
        for table_name in save_order:
            records_data = data_map.get(table_name) 

            if records_data is None:
                continue

            records_list_to_insert = []
            
            if isinstance(records_data, pd.DataFrame):
                if not records_data.empty:
                    expected_headers = settings.WORKSHEET_HEADERS.get(table_name, [])
                    temp_df = records_data.reindex(columns=expected_headers)
                    temp_df = temp_df.dropna(how='all') 
                    
                    if not temp_df.empty:
                        records_list_to_insert = temp_df.to_dict(orient='records')

            elif isinstance(records_data, list):
                records_list_to_insert = records_data

            elif isinstance(records_data, dict):
                records_list_to_insert = [records_data]

            else:
                print(f"Warning: Unexpected data type for {table_name}: {type(records_data)}. Skipping this table.")
                overall_success = False
                overall_messages.append(f"ข้อมูล {table_name} มีชนิดไม่ถูกต้อง")
                continue 

            if not records_list_to_insert: 
                print(f"No records to insert for table: {table_name} (List was empty).")
                overall_messages.append(f"ไม่มีข้อมูลสำหรับ {table_name} ที่จะบันทึก")
                continue 
            
            cleaned_records_to_insert = []
            for row in records_list_to_insert:
                cleaned_row = {}
                for k, v in row.items():
                    if isinstance(v, (np.float64, np.int64)):
                        v = float(v) if isinstance(v, np.float64) else int(v)
                    
                    if pd.isna(v) or v == '' or v is None:
                        cleaned_row[k] = None
                    else:
                        cleaned_row[k] = _convert_datetime_to_iso_string(v)
                # Add UserID to each record before insertion
                cleaned_row["UserID"] = user_id # <<< Added UserID here
                cleaned_records_to_insert.append(cleaned_row)
            
            if not cleaned_records_to_insert:
                print(f"No valid records to insert for table: {table_name} after cleaning.")
                overall_messages.append(f"ไม่มีข้อมูลที่ถูกต้องสำหรับ {table_name} ที่จะบันทึก")
                continue

            print(f"Attempting to save {len(cleaned_records_to_insert)} records to {table_name}...")
            
            response = None 
            try:
                # Use settings constants for table names
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
                else: 
                    response = supabase.table(table_name).insert(cleaned_records_to_insert).execute()
                
                if hasattr(response, 'error') and response.error is not None:
                    error_detail = response.error.get('message', str(response.error)) if isinstance(response.error, dict) else str(response.error)
                    print(f"Supabase error for {table_name}: {error_detail}")
                    overall_success = False
                    overall_messages.append(f"บันทึกข้อมูล {table_name} ไม่สำเร็จ: {error_detail}")
                elif hasattr(response, 'data') and response.data is not None:
                    if isinstance(response.data, list) and len(response.data) > 0:
                        print(f"Successfully saved {len(response.data)} records to {table_name}.")
                        overall_messages.append(f"บันทึก {len(response.data)} รายการใน {table_name} สำเร็จ")
                    else: 
                        print(f"Successfully processed {table_name} (no data returned or empty list).")
                        overall_messages.append(f"ประมวลผล {table_name} สำเร็จ (ไม่มีข้อมูลส่งกลับ)")
                else: 
                    print(f"Supabase response for {table_name} had no 'data' or 'error' attribute. Assuming success if no exception raised.")
                    overall_messages.append(f"ประมวลผล {table_name} สำเร็จ")

            except Exception as e_inner: 
                print(f"Python exception during Supabase operation for {table_name}: {e_inner}")
                overall_success = False
                overall_messages.append(f"เกิดข้อผิดพลาดรุนแรงในการบันทึกข้อมูล {table_name}: {e_inner}")
            
        final_overall_message = "บันทึกข้อมูล Statement สำเร็จ!" if overall_success else "บันทึกข้อมูล Statement บางส่วนไม่สำเร็จ:"
        final_overall_message += "\n" + "\n".join(overall_messages) if overall_messages else " (ไม่มีข้อมูลที่จะบันทึก)"

        clear_all_caches()
        return overall_success, final_overall_message
    except Exception as e: 
        print(f"Python exception in save_statement_data (outer block): {e}") 
        return False, f"เกิดข้อผิดพลาดในการบันทึกข้อมูล Statement: {e}"

def check_portfolio_account_id_link(user_id: str, file_account_id: str, active_portfolio_id: str) -> tuple[bool, str]: # Added user_id
    """
    ตรวจสอบความผูกพัน 1:1 ระหว่าง PortfolioID และ AccountID
    โดยดูจากประวัติการอัปโหลด (UploadHistory)
    คืนค่า True หากความสัมพันธ์ถูกต้อง (1:1), False หากไม่ถูกต้อง
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถตรวจสอบได้หากไม่มีการเชื่อมต่อ"

    try:
        # 1. ตรวจสอบว่า file_account_id นี้เคยถูกใช้กับ PortfolioID อื่นหรือไม่
        # (ที่ไม่ใช่ active_portfolio_id ปัจจุบัน) สำหรับ user_id นี้
        response_account_id = supabase.table(settings.SUPABASE_TABLE_UPLOAD_HISTORY) \
                                      .select('PortfolioID') \
                                      .eq('FileAccountID', file_account_id) \
                                      .neq('PortfolioID', active_portfolio_id) \
                                      .eq('UserID', user_id) \
                                      .limit(1) \
                                      .execute()
        if response_account_id.data:
            print(f"Account ID '{file_account_id}' already linked to another Portfolio ID: {response_account_id.data[0]['PortfolioID']}")
            return False, f"Account ID '{file_account_id}' เคยผูกกับ Portfolio ID: {response_account_id.data[0]['PortfolioID']} ของคุณแล้ว" # Improved message

        # 2. ตรวจสอบว่า active_portfolio_id นี้เคยถูกใช้กับ FileAccountID อื่นหรือไม่
        # (ที่ไม่ใช่ file_account_id ปัจจุบัน) สำหรับ user_id นี้
        response_portfolio_id = supabase.table(settings.SUPABASE_TABLE_UPLOAD_HISTORY) \
                                       .select('FileAccountID') \
                                       .eq('PortfolioID', active_portfolio_id) \
                                       .neq('FileAccountID', file_account_id) \
                                       .eq('UserID', user_id) \
                                       .limit(1) \
                                       .execute()
        if response_portfolio_id.data:
            print(f"Portfolio ID '{active_portfolio_id}' already linked to another Account ID: {response_portfolio_id.data[0]['FileAccountID']}")
            return False, f"Portfolio ID '{active_portfolio_id}' ของคุณเคยผูกกับ Account ID: {response_portfolio_id.data[0]['FileAccountID']} อื่นแล้ว" # Improved message

        return True, "" # ผ่านการตรวจสอบทั้งสองเงื่อนไข
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการตรวจสอบความผูกพัน Portfolio-Account ID: {e}")
        return False, f"เกิดข้อผิดพลาดในการตรวจสอบไฟล์ซ้ำ: {e}"

def save_statement_summary(user_id: str, summary_data: dict) -> tuple[bool, str]: # Added user_id
    """
    บันทึกข้อมูลสรุป Statement ลงในตาราง StatementSummaries
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
    try:
        clean_data = {}
        for k, v in summary_data.items():
            if pd.isna(v) or v == '':
                clean_data[k] = None
            else:
                clean_data[k] = _convert_datetime_to_iso_string(v)

        clean_data["UserID"] = user_id # <<< Added UserID here

        response = supabase.table(settings.SUPABASE_TABLE_STATEMENT_SUMMARIES).insert(clean_data).execute() # Use settings constant here
        clear_all_caches()
        return True, "บันทึกข้อมูลสรุป Statement สำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการบันทึกข้อมูลสรุป Statement: {e}"

def save_upload_history(user_id: str, history_data: dict) -> tuple[bool, str]: # Added user_id
    """
    บันทึกประวัติการอัปโหลดไฟล์ลงในตาราง UploadHistory
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
    try:
        clean_data = {}
        for k, v in history_data.items():
            if pd.isna(v) or v == '':
                clean_data[k] = None
            else:
                clean_data[k] = _convert_datetime_to_iso_string(v)
        
        clean_data["UserID"] = user_id # <<< Added UserID here

        response = supabase.table(settings.SUPABASE_TABLE_UPLOAD_HISTORY).upsert(clean_data, on_conflict="FileHash").execute() # Use settings constant here, using upsert on FileHash
        clear_all_caches()
        return True, "บันทึกประวัติการอัปโหลดสำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการบันทึกประวัติการอัปโหลด: {e}"


# --- Admin Approval Functions ---

def get_user_approval_status(user_id: str) -> tuple[bool, str]:
    """
    Fetches user's approval status from the user_profiles table.
    This version gracefully handles cases where the user profile doesn't exist yet.
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "error"
    try:
        # ใช้ .single() เพื่อดึงข้อมูลแค่แถวเดียว
        response = supabase.table("user_profiles").select("status, is_admin_approved").eq("id", user_id).single().execute()
        
        if response and response.data:
            status = response.data.get("status", "pending")
            is_approved = response.data.get("is_admin_approved", False)
            return is_approved and (status == 'active'), status
        else:
            # กรณีที่ไม่เจอข้อมูล แต่ไม่มี error (ซึ่งไม่น่าเกิดขึ้นกับ .single())
            return False, "pending"
            
    except Exception as e:
        # --- START: ส่วนที่แก้ไข ---
        # ถ้า Error บอกว่าไม่เจอแถวข้อมูล (no rows found) ให้ถือว่าเป็น pending
        if "PGRST116" in str(e) or "No rows found" in str(e) or "empty result" in str(e):
             print(f"DEBUG: User profile not found for {user_id}. Defaulting to 'pending' status.")
             return False, "pending"
        
        # ถ้าเป็น Error อื่นๆ ให้แสดงผลตามเดิม
        st.error(f"❌ Error fetching approval status: {e}")
        print(f"DEBUG: Exception fetching approval status: {e}")
        return False, "error"

def update_user_approval_status(target_user_id: str, new_status: str, new_approval_bool: bool) -> tuple[bool, str]:
    """
    Updates a user's approval status in the user_profiles table.
    This function is intended to be called by an Admin user.
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "ไม่สามารถเชื่อมต่อ Supabase ได้"
    try:
        # RLS Policy 'Allow admin to update profile status' controls who can call this.
        response = supabase.table("user_profiles").update({
            "status": new_status,
            "is_admin_approved": new_approval_bool,
            "updated_at": datetime.now().isoformat() # Manually update updated_at
        }).eq("id", target_user_id).execute()

        if response and hasattr(response, 'error') and response.error:
            error_message = response.error.get('message', str(response.error)) if isinstance(response.error, dict) else str(response.error)
            return False, error_message
        return True, "อัปเดตสถานะสำเร็จ"
    except Exception as e:
        return False, str(e)
