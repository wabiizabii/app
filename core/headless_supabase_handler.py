# ==============================================================================
# FILE: core/headless_supabase_handler.py (VERSION: DEFINITIVE_FULL_SPEC)
# ==============================================================================
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timezone
import uuid
import traceback

class HeadlessSupabaseHandler:
    def __init__(self, url: str, key: str):
        try:
            self.client: Client = create_client(url, key)
            print("[OK] HEADLESS Supabase client initialized successfully.")
        except Exception as e:
            self.client = None
            print(f"CRITICAL (HEADLESS): Supabase client connection failed. Error: {e}")

    # --- PORTFOLIO CRUD OPERATIONS ---
    
    def get_all_portfolios(self):
        if not self.client: return []
        try:
            response = self.client.table("Portfolios").select("*").order("PortfolioName").execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"ERROR (HEADLESS) in get_all_portfolios: {e}")
            return []

    def get_portfolio_by_id(self, portfolio_id: str):
        if not self.client or not portfolio_id: return None
        try:
            response = self.client.table("Portfolios").select("*").eq("PortfolioID", portfolio_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            print(f"ERROR (HEADLESS) in get_portfolio_by_id: {e}")
            return None
            
    def get_portfolio_by_mt5_account_id(self, mt5_id: str):
        if not self.client or not mt5_id: return None
        try:
            response = self.client.table("Portfolios").select("*").eq("mt5_account_id", mt5_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            if "0 rows" not in str(e):
                print(f"ERROR (HEADLESS) in get_portfolio_by_mt5_account_id: {e}")
            return None
            
    def create_new_portfolio(self, portfolio_data: dict):
        if not self.client: return None, "Supabase client not initialized."
        try:
            if 'PortfolioID' not in portfolio_data or not portfolio_data['PortfolioID']:
                portfolio_data['PortfolioID'] = str(uuid.uuid4())
            response = self.client.table("Portfolios").insert(portfolio_data).execute()
            if response.data:
                return response.data[0], "Success"
            return None, "Failed to insert portfolio."
        except Exception as e:
            return None, str(e)

    def update_portfolio_details(self, portfolio_id: str, update_data: dict):
        if not self.client: return False, "Supabase client not initialized."
        try:
            self.client.table("Portfolios").update(update_data).eq("PortfolioID", portfolio_id).execute()
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def delete_portfolio(self, portfolio_id: str):
        if not self.client: return False, "Supabase client not initialized."
        try:
            self.client.table("Portfolios").delete().eq("PortfolioID", portfolio_id).execute()
            return True, "Success"
        except Exception as e:
            return False, str(e)

    # --- [RESTORED] BROKER & SESSION OPERATIONS ---
        
    def get_daily_opening_balance(self, portfolio_id: str, mt5_account_id: str, broker_date_str: str):
        if not self.client: return None
        try:
            response = self.client.table("PortfolioDailyMetrics").select("OpeningBalance").eq("PortfolioID", portfolio_id).eq("mt5_account_id", str(mt5_account_id)).eq("Date", broker_date_str).single().execute()
            if response.data:
                balance = response.data.get('OpeningBalance')
                print(f"INFO (HEADLESS): Found existing opening balance in DB: {balance}")
                return balance
            return None
        except Exception as e:
            if "0 rows" not in str(e): print(f"ERROR (HEADLESS) in get_daily_opening_balance: {e}")
            return None

    def set_daily_opening_balance(self, portfolio_id: str, mt5_account_id: str, opening_balance: float, broker_date_str: str):
        if not self.client: return False
        try:
            # This record now perfectly matches the new, correct database schema.
            record = {
                "PortfolioID": portfolio_id,
                "mt5_account_id": str(mt5_account_id),
                "Date": broker_date_str,
                "OpeningBalance": opening_balance,
                "OpeningEquity": opening_balance
            }
            # We use 'insert' to let the database handle the auto-incrementing 'MetricID'.
            self.client.table("PortfolioDailyMetrics").insert(record).execute()
            print(f"SUCCESS (HEADLESS): Set opening balance for {broker_date_str} to {opening_balance}")
            return True
        except Exception as e:
            print(f"ERROR (HEADLESS) in set_daily_opening_balance: {e}")
            traceback.print_exc()
            return False

    def get_broker_timezone(self, broker_name):
        if not self.client: return None
        try:
            response = self.client.table('BrokerSettings').select('timezone_offset').eq('broker_name', broker_name).single().execute()
            return response.data.get('timezone_offset')
        except Exception:
            return None

    def set_broker_timezone(self, broker_name, offset):
        """บันทึก timezone offset สำหรับโบรกเก-อร์ใหม่"""
        if not self.client: return False
        try:
            # โค้ดนี้ถูกต้องแล้ว และจะทำงานได้เมื่อ Schema ถูกต้อง
            data_to_insert = {'broker_name': broker_name, 'timezone_offset': offset}
            self.client.table('BrokerSettings').upsert(data_to_insert, on_conflict='broker_name').execute()
            print(f"SUCCESS (HEADLESS): Set timezone for broker '{broker_name}' to {offset}")
            return True
        except Exception as e:
            print(f"Error saving broker timezone setting: {e}")
            return False
                
    # --- [RESTORED] DATA INGESTION OPERATIONS ---

    def _save_bulk_data(self, table_name: str, records: list):
        if not self.client: return False, "Supabase client not initialized."
        if not records: return True, "No records to save."
        try:
            response = self.client.table(table_name).insert(records).execute()
            if hasattr(response, 'error') and response.error is not None:
                raise Exception(response.error.message)
            return True, f"Successfully saved {len(records)} records to {table_name}."
        except Exception as e:
            print(f"ERROR (HEADLESS) in _save_bulk_data for table {table_name}: {e}")
            return False, str(e)
            
    def save_statement_summary(self, summary_data: dict):
        if not summary_data: return False, "No summary data provided."
        # Add any necessary data cleaning/sanitization here before saving
        return self._save_bulk_data("StatementSummaries", [summary_data])

    def save_bulk_deals(self, deals_records: list):
        return self._save_bulk_data("ActualTrades", deals_records)

    def save_bulk_positions(self, positions_records: list):
        return self._save_bulk_data("ActualPositions", positions_records)

    def save_bulk_orders(self, orders_records: list):
        return self._save_bulk_data("ActualOrders", orders_records)