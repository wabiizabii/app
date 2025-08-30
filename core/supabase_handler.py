import os
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, time, date, timedelta ,timezone
import numpy as np
import uuid
import pytz
import streamlit as st # Ensure streamlit is imported for st.error/st.warning
from config import settings
from config.settings import (
    SUPABASE_TABLE_PORTFOLIOS,
    SUPABASE_TABLE_PLANNED_LOGS,
    SUPABASE_TABLE_ACTUAL_TRADES,
    SUPABASE_TABLE_ACTUAL_ORDERS,
    SUPABASE_TABLE_ACTUAL_POSITIONS,
    SUPABASE_TABLE_STATEMENT_SUMMARIES,
    SUPABASE_TABLE_UPLOAD_HISTORY,
    SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS,
    SUPABASE_TABLE_PORTFOLIODAILYMETRICS,
    WORKSHEET_HEADERS,
    SECTION_RAW_HEADERS_STATEMENT_PARSING
)

def safe_float_convert(value, default=0.0):
    """
    Safely converts a value to a float, handling None, empty strings, and 'None' strings.
    """
    if value is None or (isinstance(value, str) and (value.strip().lower() == 'none' or value.strip() == '')) or pd.isna(value):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def _convert_datetime_to_iso_string(value):
    """Helper function to convert datetime/date objects to ISO 8601 string suitable for Supabase TIMESTAMP WITH TIME ZONE."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            # Assume UTC if no timezone info, then convert to ISO
            return value.isoformat(timespec='seconds') + 'Z'
        else:
            # Convert to UTC and then to ISO string
            return value.astimezone(pytz.utc).isoformat(timespec='seconds') + 'Z'
    elif isinstance(value, date):
        # For date objects, just return the ISO 8601 date string
        return value.isoformat()
    return value

def _clean_data_for_supabase(data: dict) -> dict:
    """Recursively cleans data to ensure all datetime/date objects are ISO strings."""
    cleaned_data = {}
    for k, v in data.items():
        if isinstance(v, dict):
            cleaned_data[k] = _clean_data_for_supabase(v)
        elif isinstance(v, list):
            cleaned_data[k] = [_clean_data_for_supabase(item) if isinstance(item, dict) else _convert_datetime_to_iso_string(item) for item in v]
        else:
            cleaned_data[k] = _convert_datetime_to_iso_string(v)
    return cleaned_data

def clear_all_caches():
    """
    Clear all Streamlit data caches.
    """
    st.cache_data.clear()
    st.cache_resource.clear()

class SupabaseHandler:
    """
    A class to handle all interactions with the Supabase database.
    It manages fetching, inserting, updating, and deleting data from various tables.
    """
    def __init__(self, supabase_url: str, supabase_key: str):
        print("SupabaseHandler: Initializing Supabase client (Full Update)")

        self._url = supabase_url
        self._key = supabase_key

        if not self._url:
            st.error("SUPABASE_URL is not set. Please set it in your environment variables or .env file.")
            self._client = None
            return
        if not self._key:
            st.error("SUPABASE_KEY is not set. Please set it in your environment variables or .env file.")
            self._client = None
            return
        
        try:
            self.client: Client = create_client(self._url, self._key)
            # No user ID check here, as per user's request for public access
            self.user_id = 'public_user' # Set a default user ID for public access
        except Exception as e:
            st.error(f"Error initializing Supabase client: {e}")
            self.client = None
            return

        self.table_names = {
            "portfolios": SUPABASE_TABLE_PORTFOLIOS,
            "planned_logs": SUPABASE_TABLE_PLANNED_LOGS,
            "actual_trades": SUPABASE_TABLE_ACTUAL_TRADES,
            "actual_orders": SUPABASE_TABLE_ACTUAL_ORDERS,
            "actual_positions": SUPABASE_TABLE_ACTUAL_POSITIONS,
            "statement_summaries": SUPABASE_TABLE_STATEMENT_SUMMARIES,
            "upload_history": SUPABASE_TABLE_UPLOAD_HISTORY,
            "deposit_withdrawal_logs": SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS,
            "portfolio_daily_metrics": SUPABASE_TABLE_PORTFOLIODAILYMETRICS,
        }
        self.worksheet_headers = WORKSHEET_HEADERS
        self.section_raw_headers = SECTION_RAW_HEADERS_STATEMENT_PARSING

        # New: Check for user portfolio on initialization (modified for public access)
        self._ensure_user_portfolio_exists()

    def get_all_portfolios(self):
        """Fetches all portfolios from the Supabase table."""
        try:
            # เลือกทุกแถว (*) จากตาราง Portfolios
            response = self.client.table("Portfolios").select("*").execute()
            if response.data:
                return response.data
            else:
                return [] # คืนค่าเป็น list ว่างถ้าไม่มีข้อมูล
        except Exception as e:
            print(f"ERROR: Supabase Error (fetch all portfolios): {e}")
            return None

    # --- New method to ensure a portfolio exists (modified for public access) ---
    def _create_default_portfolio(self) -> tuple[bool, str]:
        """Creates a default portfolio for a new user (public access)."""
        portfolio_data = {
            "PortfolioID": str(uuid.uuid4()),
            "UserID": self.user_id, # Still assign a UserID, even if it's 'public_user'
            "PortfolioName": "My First Portfolio",
            "InitialBalance": settings.DEFAULT_ACCOUNT_BALANCE,
            "CreationDate": datetime.now(),
            "mt5_account_id": None # Initialize mt5_account_id to None for new portfolios
        }
        return self._insert_data(self.table_names["portfolios"], portfolio_data)

    def _ensure_user_portfolio_exists(self):
        """Checks if the user has any portfolios and creates one if not (public access)."""
        # Only proceed if active_portfolio_id is NOT already set in session state
        # This prevents unnecessary re-initialization on every rerun if a portfolio is already active
        if 'active_portfolio_id' not in st.session_state or st.session_state['active_portfolio_id'] is None:
            portfolios = self.load_portfolios() # This is a cached call, so it's efficient
            
            if portfolios.empty:
                st.warning("ไม่พบ Portfolio ของคุณ ระบบกำลังสร้าง Portfolio เริ่มต้นให้...")
                success, message = self._create_default_portfolio()
                if success:
                    st.success("✅ สร้าง Portfolio เริ่มต้นสำเร็จ! กรุณารีเฟรชหน้าเว็บ")
                    # After creation, reload portfolios to get the new one and set it as active
                    updated_portfolios = self.load_portfolios() # This will fetch the newly created portfolio
                    if not updated_portfolios.empty:
                        first_portfolio = updated_portfolios.sort_values(by='PortfolioName').iloc[0]
                        st.session_state['active_portfolio_id'] = first_portfolio['PortfolioID']
                        st.session_state['active_portfolio_name'] = first_portfolio['PortfolioName'] # <--- สำคัญ: ตั้งค่าชื่อ Portfolio
                        st.session_state['current_portfolio_details'] = first_portfolio.to_dict() # <--- สำคัญ: ตั้งค่ารายละเอียด Portfolio
                    st.rerun() # Rerun เพื่อให้ UI อัปเดต
                else:
                    st.error(f"❌ ไม่สามารถสร้าง Portfolio ได้: {message}")
            else:
                # If portfolios exist, ensure an active one is set in session state
                # If active_portfolio_id was None or not set, pick the first one
                if st.session_state.get('active_portfolio_id') is None:
                    first_portfolio = portfolios.sort_values(by='PortfolioName').iloc[0]
                    st.session_state['active_portfolio_id'] = first_portfolio['PortfolioID']
                    st.session_state['active_portfolio_name'] = first_portfolio['PortfolioName'] # <--- สำคัญ: ตั้งค่าชื่อ Portfolio
                    st.session_state['current_portfolio_details'] = first_portfolio.to_dict() # <--- สำคัญ: ตั้งค่ารายละเอียด Portfolio
                    st.rerun() # Rerun เพื่อให้ UI อัปเดต
                else:
                    # If active_portfolio_id is already set, just ensure its name and details are also set
                    # This handles cases where active_portfolio_id might be set, but name/details are not
                    active_id = st.session_state['active_portfolio_id']
                    current_pf_row = portfolios[portfolios['PortfolioID'] == active_id]
                    if not current_pf_row.empty:
                        details = current_pf_row.iloc[0].to_dict()
                        st.session_state['active_portfolio_name'] = details['PortfolioName']
                        st.session_state['current_portfolio_details'] = details
                    else:
                        # If the active_portfolio_id in session state doesn't exist in DB (e.g., deleted)
                        # Reset and trigger re-initialization
                        st.session_state['active_portfolio_id'] = None
                        st.session_state['active_portfolio_name'] = None
                        st.session_state['current_portfolio_details'] = None
                        st.rerun()

    def log_daily_metric(self, portfolio_id: str, mt5_account_id: str, date_today: str, opening_balance: float):
        """
        Logs or updates the daily metric for a specific portfolio using mt5_account_id and date.
        """
        try:
            # Data to be inserted or updated, now includes mt5_account_id
            data_to_log = {
                "PortfolioID": portfolio_id,
                "mt5_account_id": mt5_account_id,
                "Date": date_today,
                "OpeningBalance": opening_balance
            }
            
            # THE FIX: We tell Supabase to check for conflicts on the 'mt5_account_id' and 'Date' columns
            # This is the correct composite key for your table structure.
            response = self.client.table(settings.SUPABASE_TABLE_PORTFOLIODAILYMETRICS)\
                                .upsert(data_to_log, on_conflict='mt5_account_id,Date').execute()

            if response.data:
                print(f"✅ Successfully logged/updated daily metric for MT5 ID {mt5_account_id} on {date_today}.")
                return {"status": "success", "data": response.data}
            else:
                print(f"⚠️ Supabase returned no data but no error for logging metric. Response: {response}")
                return {"status": "warning", "message": "Operation completed but returned no data."}

        except Exception as e:
            print(f"❌ DATABASE ERROR in log_daily_metric: {e}")
            return {"status": "error", "message": str(e)}

    # --- Generic CRUD Helpers ---
    #@st.cache_data(ttl=300)
    def _fetch_data(_self, table_name: str, columns: str = "*", filters: dict = None, order_by: str = None, ascending: bool = True, limit: int = None) -> pd.DataFrame:
        """Helper to fetch data from Supabase and return as DataFrame."""
        if _self.client is None:
            st.error("Supabase client not initialized. Cannot fetch data.")
            return pd.DataFrame()
        try:
            query = _self.client.table(table_name).select(columns)
            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)
            if order_by:
                query = query.order(order_by, desc=not ascending)
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            if response and response.data:
                df = pd.DataFrame(response.data)
                return df
            else:
                return pd.DataFrame() # Return empty DataFrame
        except Exception as e:
            st.error(f"❌ Supabase Error (fetch {table_name}): {e}")
            return pd.DataFrame() # Return empty DataFrame on error

    def _insert_data(self, table_name: str, data: dict) -> tuple[bool, str]:
        """Helper to insert data into Supabase."""
        if self.client is None:
            return False, "Supabase client not initialized. Cannot insert data."
        try:
            # Ensure mt5_account_id is handled as string before cleaning
            if 'mt5_account_id' in data and data['mt5_account_id'] is not None:
                data['mt5_account_id'] = str(data['mt5_account_id'])
            else:
                data['mt5_account_id'] = None

            clean_data = _clean_data_for_supabase(data) # Clean data before inserting
            response = self.client.table(table_name).insert(clean_data).execute()
            clear_all_caches() # Clear cache after write operation
            if response and response.data:
                return True, f"Data successfully inserted into '{table_name}'."
            else:
                return False, f"Failed to insert data into '{table_name}': No data returned from Supabase."
        except Exception as e:
            return False, f"Error inserting data into '{table_name}': {e}"

    def _update_data(self, table_name: str, record_id: str, data: dict, id_column: str = "id") -> tuple[bool, str]:
        """Helper to update data in Supabase based on a record ID."""
        if self.client is None:
            return False, "Supabase client not initialized. Cannot update data."
        try:
            # Ensure mt5_account_id is handled as string before cleaning
            if 'mt5_account_id' in data and data['mt5_account_id'] is not None:
                data['mt5_account_id'] = str(data['mt5_account_id'])
            else:
                data['mt5_account_id'] = None

            clean_data = _clean_data_for_supabase(data) # Clean data before updating
            response = self.client.table(table_name).update(clean_data).eq(id_column, record_id).execute()
            clear_all_caches() # Clear cache after write operation
            if response and response.data:
                return True, f"Data successfully updated in '{table_name}' for {id_column} '{record_id}'."
            else:
                return False, f"Failed to update data from '{table_name}': No data returned from Supabase."
        except Exception as e:
            return False, f"Error updating data into '{table_name}': {e}"

    def _delete_data(self, table_name: str, record_id: str, id_column: str = "id") -> tuple[bool, str]:
        """Helper to delete data from Supabase based on a record ID."""
        if self.client is None:
            return False, "Supabase client not initialized. Cannot delete data."
        try:
            response = self.client.table(table_name).delete().eq(id_column, record_id).execute()
            clear_all_caches() # Clear cache after write operation
            if response and response.data:
                return True, f"Data successfully deleted from '{table_name}' for {id_column} '{record_id}'."
            else:
                return False, f"Failed to delete data from '{table_name}': No data returned from Supabase."
        except Exception as e:
            return False, f"Error deleting data into '{table_name}': {e}"
            
    # =========================================================================================
    # PortfolioDailyMetrics related functions
    # =========================================================================================
    def save_portfolio_daily_metrics(self, data: dict):
        """
        Saves or updates daily metrics for a portfolio.
        Assumes data is a dict with required fields.
        """
        if self.client is None:
            st.error("Supabase client not initialized. Cannot save daily metrics.")
            return False, "Supabase client not initialized."
        
        try:
            if isinstance(data.get('Date'), datetime):
                data['Date'] = data['Date'].date()
            if isinstance(data.get('Date'), date):
                data['Date'] = data['Date'].isoformat()

            # Ensure mt5_account_id is handled as string
            if 'mt5_account_id' in data and data['mt5_account_id'] is not None:
                data['mt5_account_id'] = str(data['mt5_account_id'])
            else:
                data['mt5_account_id'] = None

            response = self.client.from_(SUPABASE_TABLE_PORTFOLIODAILYMETRICS).upsert([data]).execute()
            
            if response.data:
                return True, "Daily metrics saved/updated successfully."
            else:
                st.error(f"Failed to save daily metrics: {response.error}")
                return False, response.error
        
        except Exception as e:
            error_msg = f"Error inserting data into '{SUPABASE_TABLE_PORTFOLIODAILYMETRICS}': {e}"
            st.error(error_msg)
            return False, error_msg

    def load_daily_metrics(self, portfolio_id: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Loads daily metrics for a specific portfolio within a date range.
        Returns a DataFrame.
        """
        if self.client is None:
            return pd.DataFrame()

        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        try:
            response = self.client.from_(SUPABASE_TABLE_PORTFOLIODAILYMETRICS).select("*").eq("PortfolioID", portfolio_id).gte("Date", start_date_str).lte("Date", end_date_str).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                
                numeric_cols = [
                    'OpeningBalance', 'OpeningEquity', 'ClosingBalance', 'ClosingEquity', 'P_L_Daily',
                    'MaxDrawdownDaily', 'MaxDrawdownDailyPercent', 'MaximalDrawdownOverall',
                    'MaximalDrawdownOverallPercent'
                ]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
                return df.sort_values('Date')
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Failed to load daily metrics: {e}")
            return pd.DataFrame()

    def load_last_known_balance(self, portfolio_id: str) -> float:
        """
        Loads the last known balance for a portfolio, prioritizing daily metrics, then statement summaries, then initial balance.
        """
        try:
            # 1. Try to get the last recorded balance from PortfolioDailyMetrics. We will use OpeningBalance since ClosingBalance does not exist.
            response = self.client.from_(SUPABASE_TABLE_PORTFOLIODAILYMETRICS).select("OpeningBalance", "Date").eq("PortfolioID", portfolio_id).order("Date", desc=True).limit(1).execute()
            if response.data and response.data[0]['OpeningBalance'] is not None:
                return response.data[0]['OpeningBalance']
            
            # 2. If no daily metrics, try to get from StatementSummaries
            response = self.client.from_(SUPABASE_TABLE_STATEMENT_SUMMARIES).select("Balance").eq("PortfolioID", portfolio_id).order("Timestamp", desc=True).limit(1).execute()
            if response.data and response.data[0]['Balance'] is not None:
                return response.data[0]['Balance']

            # 3. If no statement summary, get from Portfolio's InitialBalance
            response = self.client.from_(SUPABASE_TABLE_PORTFOLIOS).select("InitialBalance").eq("PortfolioID", portfolio_id).limit(1).execute()
            if response.data and response.data[0]['InitialBalance'] is not None:
                return response.data[0]['InitialBalance']
                
            return settings.DEFAULT_ACCOUNT_BALANCE
        except Exception as e:
            st.warning(f"Warning: Failed to load last known balance. Using default. Error: {e}")
            return settings.DEFAULT_ACCOUNT_BALANCE
    
    def get_or_set_daily_opening_balance(self, portfolio_id: str, current_balance: float):
        if not self.client: return current_balance
        
        today_utc = datetime.now(timezone.utc)
        today_str = today_utc.strftime('%Y-%m-%d')

        try:
            # 1. Check if a record for today already exists
            response = self.client.table(settings.SUPABASE_TABLE_PORTFOLIODAILYMETRICS)\
                .select("OpeningBalance").eq("PortfolioID", portfolio_id).eq("Date", today_str).execute()
            
            if response.data:
                return response.data[0]['OpeningBalance']
            else:
                # 2. If not, find the last known balance from yesterday's deals
                yesterday_str = (today_utc - timedelta(days=1)).strftime('%Y-%m-%d')
                
                # Query the last deal from yesterday or before
                last_deal_response = self.client.table(settings.SUPABASE_TABLE_ACTUAL_TRADES)\
                    .select("Balance_Deal").eq("PortfolioID", portfolio_id)\
                    .lte("Time_Deal", today_str) \
                    .order("Time_Deal", desc=True).limit(1).execute()
                
                opening_balance = current_balance # Default to current if no history found
                if last_deal_response.data:
                    opening_balance = last_deal_response.data[0]['Balance_Deal']
                else:
                    # Fallback to initial balance if no deals found at all
                    portfolio_info = self.client.table("Portfolios").select("InitialBalance").eq("PortfolioID", portfolio_id).single().execute()
                    if portfolio_info.data:
                        opening_balance = portfolio_info.data['InitialBalance']

                print(f"No opening balance for today. Setting it to last known balance: {opening_balance}")
                
                # 3. Insert the new record for today
                self.client.table(settings.SUPABASE_TABLE_PORTFOLIODAILYMETRICS).insert({
                    "PortfolioID": portfolio_id,
                    "Date": today_str,
                    "OpeningBalance": opening_balance
                }).execute()
                
                return opening_balance
        except Exception as e:
            print(f"Error in get_or_set_daily_opening_balance: {e}")
            return current_balance

    # --- Data Loading Functions for Streamlit UI ---
    def load_drawdown(self, portfolio_id: str) -> pd.DataFrame:
        """Loads drawdown data for a specific portfolio from the 'StatementSummaries' table."""
        if not portfolio_id:
            return pd.DataFrame()

        filters = {"PortfolioID": portfolio_id}
        columns_to_select = "Timestamp, Maximal_Drawdown_Value, Maximal_Drawdown_Percent"
        
        df = self._fetch_data(self.table_names["statement_summaries"], columns=columns_to_select, filters=filters)
        
        if not df.empty:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
            df.rename(columns={
                'Maximal_Drawdown_Value': 'MaxDrawdownValue',
                'Maximal_Drawdown_Percent': 'MaxDrawdownPercent'
            }, inplace=True)
            df.sort_values(by='Timestamp', inplace=True)
        return df

    def get_open_positions(self, portfolio_id: str) -> pd.DataFrame:
        """Loads all open positions for a specific portfolio from the 'ActualPositions' table."""
        if not portfolio_id:
            return pd.DataFrame(columns=['OpenTime', 'Symbol', 'Type', 'Volume', 'Price', 'Profit'])

        filters = {"PortfolioID": portfolio_id, "Time_Close_Pos": None} # Filter for open positions
        columns_to_select = "Time_Pos, Symbol_Pos, Type_Pos, Volume_Pos, Price_Open_Pos, S_L_Pos, T_P_Pos, Profit_Pos, Comment"

        df = self._fetch_data(self.table_names["actual_positions"], columns=columns_to_select, filters=filters)

        if not df.empty:
            df.rename(columns={
                'Time_Pos': 'OpenTime',
                'Symbol_Pos': 'Symbol',
                'Type_Pos': 'Type',
                'Volume_Pos': 'Volume',
                'Price_Open_Pos': 'Price',
                'S_L_Pos': 'StopLoss',
                'T_P_Pos': 'TakeProfit',
                'Profit_Pos': 'Profit'
            }, inplace=True)
            
            df['OpenTime'] = pd.to_datetime(df['OpenTime'], errors='coerce')

        return df

    # --- Portfolio Management Functions ---
    def load_portfolios(self) -> pd.DataFrame:
        """Loads all portfolios from the 'Portfolios' table."""
        # No UserID filter here, as per user's request for public access
        filters = {}
        df = self._fetch_data(self.table_names["portfolios"], filters=filters)
        if not df.empty:
            if 'CreationDate' in df.columns:
                df['CreationDate'] = pd.to_datetime(df['CreationDate'], errors='coerce')
        return df

    def get_portfolio_details(self, portfolio_id: str) -> dict | None:
        """
        Fetches details for a specific portfolio by its ID.
        Returns the portfolio dictionary if found, otherwise None.
        """
        if not portfolio_id:
            return None
        filters = {'PortfolioID': portfolio_id}
        df = self._fetch_data(self.table_names["portfolios"], filters=filters, limit=1)
        if not df.empty:
            return df.iloc[0].to_dict()
        return None

    def add_portfolio(self, portfolio_data: dict) -> tuple[bool, str]:
        """Adds a new portfolio to the 'Portfolios' table."""
        portfolio_data["PortfolioID"] = str(uuid.uuid4())
        portfolio_data["CreationDate"] = datetime.now()
        portfolio_data["UserID"] = self.user_id # Assign the public_user ID
        # Ensure mt5_account_id is included and is lowercase
        if 'mt5_account_id' not in portfolio_data:
            portfolio_data['mt5_account_id'] = None
        return self._insert_data(self.table_names["portfolios"], portfolio_data)

    def update_portfolio(self, portfolio_id: str, data: dict) -> tuple[bool, str]:
        """Updates an existing portfolio in the 'Portfolios' table."""
        # Ensure mt5_account_id is included and is lowercase
        if 'mt5_account_id' not in data:
            data['mt5_account_id'] = None
        return self._update_data(self.table_names["portfolios"], portfolio_id, data, id_column="PortfolioID")

    def delete_portfolio(self, portfolio_id: str) -> tuple[bool, str]:
        """Deletes a portfolio from the 'Portfolios' table and all related data."""
        if self.client is None:
            return False, "Supabase client not initialized. Cannot delete data."
        
        try:
            # Delete related data first (no UserID filter needed for public access)
            self.client.table(self.table_names["planned_logs"]).delete().eq("PortfolioID", str(portfolio_id)).execute()
            self.client.table(self.table_names["actual_trades"]).delete().eq("PortfolioID", str(portfolio_id)).execute()
            self.client.table(self.table_names["actual_orders"]).delete().eq("PortfolioID", str(portfolio_id)).execute()
            self.client.table(self.table_names["actual_positions"]).delete().eq("PortfolioID", str(portfolio_id)).execute()
            self.client.table(self.table_names["statement_summaries"]).delete().eq("PortfolioID", str(portfolio_id)).execute()
            self.client.table(self.table_names["deposit_withdrawal_logs"]).delete().eq("PortfolioID", str(portfolio_id)).execute()
            self.client.table(self.table_names["upload_history"]).delete().eq("PortfolioID", str(portfolio_id)).execute()
            self.client.table(self.table_names["portfolio_daily_metrics"]).delete().eq("PortfolioID", str(portfolio_id)).execute()

            # Delete the portfolio itself
            response = self.client.table(self.table_names["portfolios"]).delete().eq("PortfolioID", portfolio_id).execute()
            
            if response and response.data:
                return True, f"Portfolio {portfolio_id} and all associated data deleted successfully."
            else:
                return False, f"Failed to delete portfolio {portfolio_id}: No data returned or permission denied."
        except Exception as e:
            return False, f"Error deleting portfolio: {e}"

    # --- Planned Trade Log Functions ---
    def save_planned_trade_log(self, log_data: dict) -> tuple[bool, str]:
        """Saves a single planned trade log entry to the 'PlannedTradeLogs' table."""
        log_data["LogID"] = str(uuid.uuid4())
        log_data["Timestamp"] = datetime.now()
        log_data["UserID"] = self.user_id # Assign the public_user ID
        if 'EntryTime' in log_data and not isinstance(log_data['EntryTime'], datetime):
            try:
                log_data['EntryTime'] = pd.to_datetime(log_data['EntryTime'])
            except ValueError:
                log_data['EntryTime'] = None
        # Ensure mt5_account_id is included and is lowercase
        if 'mt5_account_id' not in log_data:
            log_data['mt5_account_id'] = None
        return self._insert_data(self.table_names["planned_logs"], log_data)

    def load_all_planned_trade_logs(self, portfolio_id: str = None, mt5_account_id: str = None) -> pd.DataFrame: # <--- FIXED: Added mt5_account_id parameter
        """Loads all planned trade logs from the 'PlannedTradeLogs' table."""
        filters = {}
        if portfolio_id:
            filters['PortfolioID'] = portfolio_id
        if mt5_account_id: # <--- NEW: Filter by mt5_account_id
            filters['mt5_account_id'] = mt5_account_id
            
        df = self._fetch_data(self.table_names["planned_logs"], filters=filters)
        if not df.empty:
            for col in ['Timestamp', 'EntryTime']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            numeric_cols = ["Risk %", "Entry", "SL", "TP", "Lot", "Risk $", "RR"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    # --- Actual Trades Functions ---
    def load_actual_trades(self, portfolio_id: str = None, mt5_account_id: str = None) -> pd.DataFrame: # <--- FIXED: Added mt5_account_id parameter
        """Loads all actual trades from the 'ActualTrades' table."""
        filters = {}
        if portfolio_id:
            filters['PortfolioID'] = portfolio_id
        if mt5_account_id: # <--- NEW: Filter by mt5_account_id
            filters['mt5_account_id'] = mt5_account_id
        df = self._fetch_data(self.table_names["actual_trades"], filters=filters)
        if not df.empty:
            if 'Time_Deal' in df.columns:
                df['Time_Deal'] = pd.to_datetime(df['Time_Deal'], errors='coerce')
            numeric_cols = [
                "Volume_Deal", "Price_Deal", "Commission_Deal", "Fee_Deal", "Swap_Deal", "Profit_Deal", "Balance_Deal"
            ]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def save_actual_trades(self, trades_df: pd.DataFrame) -> tuple[bool, str]:
        """Saves a DataFrame of actual trades to the 'ActualTrades' table."""
        if trades_df.empty:
            return False, "No actual trades to save."
        
        trades_df['Deal_ID'] = [str(uuid.uuid4()) for _ in range(len(trades_df))]
        trades_df['UserID'] = self.user_id # Assign the public_user ID
        # Ensure mt5_account_id is included and is lowercase
        if 'mt5_account_id' not in trades_df.columns:
            trades_df['mt5_account_id'] = None # Add column if not present
        else: # Ensure existing mt5_account_id is string
            trades_df['mt5_account_id'] = trades_df['mt5_account_id'].apply(lambda x: str(x) if x is not None else None)

        records = [_clean_data_for_supabase(record) for record in trades_df.to_dict(orient='records')]
        try:
            response = self.client.table(self.table_names["actual_trades"]).insert(records).execute()
            clear_all_caches()
            if response and response.data:
                return True, f"Successfully saved {len(response.data)} actual trades."
            else:
                return False, "Failed to save actual trades: No data returned from Supabase."
        except Exception as e:
            return False, f"Error saving actual trades: {e}"

    # --- Statement Summary Functions ---
    def load_statement_summaries(self, portfolio_id: str = None) -> pd.DataFrame:
        """Loads all statement summaries from the 'StatementSummaries' table."""
        filters = {}
        if portfolio_id:
            filters['PortfolioID'] = portfolio_id
        df = self._fetch_data(self.table_names["statement_summaries"], filters=filters)
        if not df.empty:
            # Corrected line: use 'Timestamp' directly, not 'col'
            if 'Timestamp' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        return df

    def save_statement_summary(self, summary_data: dict) -> tuple[bool, str]:
        """Saves a single statement summary entry to the 'StatementSummaries' table."""
        summary_data["Timestamp"] = datetime.now()
        summary_data["UserID"] = self.user_id # Assign the public_user ID
        # Ensure mt5_account_id is included and is lowercase
        if 'mt5_account_id' not in summary_data:
            summary_data['mt5_account_id'] = None
        else: # Ensure existing mt5_account_id is string
            summary_data['mt5_account_id'] = str(summary_data['mt5_account_id']) if summary_data['mt5_account_id'] is not None else None

        return self._insert_data(self.table_names["statement_summaries"], summary_data)

    # --- Deposit/Withdrawal Logs Functions ---
    def load_deposit_withdrawal_logs(self, portfolio_id: str = None) -> pd.DataFrame:
        """Loads all deposit/withdrawal logs from the 'DepositWithdrawalLogs' table."""
        filters = {}
        if portfolio_id:
            filters['PortfolioID'] = portfolio_id
        df = self._fetch_data(self.table_names["deposit_withdrawal_logs"], filters=filters)
        if not df.empty:
            if 'DateTime' in df.columns:
                df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        return df

    # --- Actual Orders Functions ---
    def load_actual_orders(self, portfolio_id: str = None, mt5_account_id: str = None) -> pd.DataFrame: # <--- NEW: Added mt5_account_id parameter
        """Loads all actual orders from the 'ActualOrders' table."""
        filters = {}
        if portfolio_id:
            filters['PortfolioID'] = portfolio_id
        if mt5_account_id: # <--- NEW: Filter by mt5_account_id
            filters['mt5_account_id'] = mt5_account_id
        df = self._fetch_data(self.table_names["actual_orders"], filters=filters)
        if not df.empty:
            if 'Open_Time_Ord' in df.columns:
                df['Open_Time_Ord'] = pd.to_datetime(df['Open_Time_Ord'], errors='coerce')
            if 'Close_Time_Ord' in df.columns:
                df['Close_Time_Ord'] = pd.to_datetime(df['Close_Time_Ord'], errors='coerce')
            numeric_cols = ["Volume_Ord", "Price_Ord", "S_L_Ord", "T_P_Ord"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    # --- Actual Positions Functions ---
    def load_actual_positions(self, portfolio_id: str = None, mt5_account_id: str = None) -> pd.DataFrame: # <--- NEW: Added mt5_account_id parameter
        """Loads all actual positions from the 'ActualPositions' table."""
        filters = {}
        if portfolio_id:
            filters['PortfolioID'] = portfolio_id
        if mt5_account_id: # <--- NEW: Filter by mt5_account_id
            filters['mt5_account_id'] = mt5_account_id
        df = self._fetch_data(self.table_names["actual_positions"], filters=filters)
        if not df.empty:
            if 'Time_Pos' in df.columns:
                df['Time_Pos'] = pd.to_datetime(df['Time_Pos'], errors='coerce')
            if 'Time_Close_Pos' in df.columns:
                df['Time_Close_Pos'] = pd.to_datetime(df['Time_Close_Pos'], errors='coerce')
            numeric_cols = ["Volume_Pos", "Price_Open_Pos", "S_L_Pos", "T_P_Pos", "Price_Close_Pos", "Commission_Pos", "Swap_Pos", "Profit_Pos"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def get_daily_start_equity(self, portfolio_id: str) -> float:
        """
        Fetches the equity at the end of the previous day for the given portfolio.
        If not found, falls back to the initial balance of the portfolio.
        """
        today = date.today()
        
        df_summaries = self.load_statement_summaries(portfolio_id=portfolio_id)
        
        if not df_summaries.empty:
            df_portfolio_summaries = df_summaries[df_summaries['PortfolioID'] == portfolio_id].copy()
            
            if not df_portfolio_summaries.empty:
                df_portfolio_summaries['Timestamp'] = pd.to_datetime(df_portfolio_summaries['Timestamp'], errors='coerce')
                df_yesterday_summaries = df_portfolio_summaries[df_portfolio_summaries['Timestamp'].dt.date < today]
                
                if not df_yesterday_summaries.empty:
                    latest_prev_day_summary = df_yesterday_summaries.sort_values('Timestamp', ascending=False).iloc[0]
                    equity = safe_float_convert(latest_prev_day_summary.get('Equity'))
                    if equity is not None:
                        return equity

        df_portfolios = self.load_portfolios()
        if not df_portfolios.empty:
            current_pf_row = df_portfolios[df_portfolios['PortfolioID'] == portfolio_id]
            if not current_pf_row.empty:
                initial_balance = safe_float_convert(current_pf_row.iloc[0].get('InitialBalance'))
                if initial_balance is not None:
                    return initial_balance
        
        return None

    def load_upload_history(self, portfolio_id: str = None, mt5_account_id: str = None) -> pd.DataFrame: # <--- FIXED: Added mt5_account_id parameter
        """
        โหลดประวัติการอัปโหลดจากตาราง UploadHistory
        สามารถกรองตาม PortfolioID และ mt5_account_id ได้
        """
        filters = {}
        if portfolio_id:
            filters['PortfolioID'] = portfolio_id
        if mt5_account_id: # <--- NEW: Filter by mt5_account_id
            filters['mt5_account_id'] = mt5_account_id
            
        df = self._fetch_data(self.table_names["upload_history"], filters=filters, order_by='UploadTimestamp', ascending=False)
        
        if not df.empty and 'UploadTimestamp' in df.columns:
            df['UploadTimestamp'] = pd.to_datetime(df['UploadTimestamp'])
            df['UploadTimestamp'] = df['UploadTimestamp'].dt.tz_localize(None).dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')
        return df

    def save_upload_history(self, history_data: dict) -> tuple[bool, str]:
        """
        บันทึกประวัติการอัปโหลดไฟล์ Statement ลงในตาราง UploadHistory
        """
        history_data['UserID'] = self.user_id # Assign the public_user ID
        if 'UploadTimestamp' in history_data and isinstance(history_data['UploadTimestamp'], datetime):
            if history_data['UploadTimestamp'].tzinfo is None:
                bangkok_tz = pytz.timezone('Asia/Bangkok')
                history_data['UploadTimestamp'] = bangkok_tz.localize(history_data['UploadTimestamp']).astimezone(pytz.utc)
            else:
                history_data['UploadTimestamp'] = history_data['UploadTimestamp'].astimezone(pytz.utc)
        
        # Ensure mt5_account_id is included and is lowercase
        if 'mt5_account_id' not in history_data:
            history_data['mt5_account_id'] = None
        else: # Ensure existing mt5_account_id is string
            history_data['mt5_account_id'] = str(history_data['mt5_account_id']) if history_data['mt5_account_id'] is not None else None

        return self._insert_data(self.table_names["upload_history"], history_data)

    def check_duplicate_file(self, file_hash: str, portfolio_id: str) -> tuple[bool, dict]:
        """
        ตรวจสอบว่า file_hash นี้มีอยู่ในตาราง UploadHistory สำหรับ PortfolioID นี้หรือไม่
        """
        filters = {
            'FileHash': file_hash,
            'PortfolioID': portfolio_id,
        }
        response_df = self._fetch_data(self.table_names["upload_history"], filters=filters, limit=1)
        if not response_df.empty:
            return True, response_df.iloc[0].to_dict()
        return False, {}

    def get_portfolio_by_mt5_account_id(self, mt5_id: str):
        """
        Fetches a portfolio by its linked MT5 Account ID, using the correct column name 'mt5_account_id'.
        """
        # --- ชื่อคอลัมน์ที่ถูกต้องตามที่คุณยืนยัน ---
        COLUMN_NAME_TO_SEARCH = 'mt5_account_id'
        
        try:
            # 1. ตรวจสอบว่า mt5_id ไม่ใช่ค่าว่าง
            if not mt5_id:
                return None
            
            # 2. แปลง mt5_id ที่ได้รับมา (เป็น string) ให้เป็น integer ก่อนค้นหา
            account_id_to_search = int(mt5_id)

            print(f"DEBUG: Executing Supabase query: table=Portfolios, column={COLUMN_NAME_TO_SEARCH}, value={account_id_to_search}")

            # 3. ใช้ตัวแปรที่แปลงแล้ว และชื่อคอลัมน์ที่ถูกต้องในการค้นหา
            response = self.client.table('Portfolios').select('*').eq(COLUMN_NAME_TO_SEARCH, account_id_to_search).single().execute()
            
            # response.data จะเป็น dict โดยตรงถ้าเจอ หรือเป็น None ถ้าไม่เจอ
            return response.data if response.data else None

        except (ValueError, TypeError):
            # กรณีที่ mt5_id ที่ส่งมาไม่สามารถแปลงเป็นตัวเลขได้
            print(f"DEBUG: Invalid MT5 ID format received: {mt5_id}. Cannot convert to integer.")
            return None
        except Exception as e:
            # พิมพ์ error ที่ได้รับจาก Supabase ตรงๆ เพื่อการวิเคราะห์
            print(f"--- SUPABASE ERROR ---")
            print(f"Error fetching portfolio with column '{COLUMN_NAME_TO_SEARCH}'. Details: {e}")
            print(f"--- END SUPABASE ERROR ---")
            return None

    def update_portfolio_mt5_link(self, portfolio_id: str, mt5_account_id: str | None) -> tuple[bool, str]:
        """
        Updates the mt5_account_id for a given portfolio.
        Set mt5_account_id to None to unlink.
        """
        # First, check if the MT5 account ID is already linked to another portfolio
        if mt5_account_id is not None:
            mt5_account_id_str = str(mt5_account_id) # Ensure it's a string for comparison
            existing_link_portfolio = self.get_portfolio_by_mt5_account_id(mt5_account_id_str)
            if existing_link_portfolio and existing_link_portfolio['PortfolioID'] != portfolio_id:
                return False, f"MT5 Account ID '{mt5_account_id_str}' ถูกผูกกับ Portfolio อื่นอยู่แล้ว: '{existing_link_portfolio['PortfolioName']}'"

        data_to_update = {'mt5_account_id': str(mt5_account_id) if mt5_account_id is not None else None}
        return self._update_data(self.table_names["portfolios"], portfolio_id, data_to_update, id_column="PortfolioID")

    def check_statement_update_status(self, portfolio_id: str, mt5_account_id: str) -> tuple[bool, dict]:
        """
        ตรวจสอบว่า MT5 Account ID นี้เคยถูกอัปโหลดสำหรับ Portfolio นี้หรือไม่
        และดึงข้อมูลการอัปโหลดล่าสุดหากมี
        """
        filters = {
            'PortfolioID': portfolio_id,
            'mt5_account_id': str(mt5_account_id) # Ensure comparison is string to string
        }
        # Fetch the latest upload for this portfolio and MT5 account
        response_df = self._fetch_data(
            self.table_names["upload_history"], 
            filters=filters, 
            order_by='UploadTimestamp', 
            ascending=False, 
            limit=1
        )
        if not response_df.empty:
            return True, response_df.iloc[0].to_dict()
        return False, {}

    def save_planned_trades(self, planned_trades_df: pd.DataFrame) -> tuple[bool, str]:
        """
        Saves a DataFrame of planned trades to the 'PlannedTradeLogs' table.
        This function handles multiple records at once.
        """
        if self.client is None:
            return False, "Supabase client not initialized."
        if planned_trades_df.empty:
            return False, "No planned trades to save."

        try:
            records_to_insert = planned_trades_df.to_dict(orient='records')
            
            # Clean each record before inserting
            cleaned_records = [_clean_data_for_supabase(record) for record in records_to_insert]
            
            response = self.client.table(self.table_names["planned_logs"]).insert(cleaned_records).execute()
            
            clear_all_caches() # Clear cache after write operation

            if response.data and len(response.data) > 0:
                return True, f"Successfully saved {len(response.data)} planned trade entries."
            else:
                # Provide more detail if there's an error from Supabase
                error_info = response.error if hasattr(response, 'error') and response.error else "No data returned."
                return False, f"Failed to save planned trades: {error_info}"

        except Exception as e:
            return False, f"An error occurred while saving planned trades: {e}"