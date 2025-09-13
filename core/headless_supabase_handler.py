# core/headless_supabase_handler.py
from supabase import create_client, Client
from datetime import datetime, timezone

class HeadlessSupabaseHandler:
    def __init__(self, url: str, key: str):
        try:
            self.client: Client = create_client(url, key)
            print("✅ HEADLESS Supabase client initialized successfully.")
        except Exception as e:
            self.client = None
            print(f"CRITICAL (HEADLESS): Supabase client connection failed. Error: {e}")

    def get_portfolio_by_mt5_account_id(self, mt5_id: str):
        if not self.client or not mt5_id: return None
        try:
            response = self.client.table("Portfolios").select("*").eq("mt5_account_id", mt5_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            print(f"ERROR (HEADLESS) in get_portfolio_by_mt5_account_id: {e}")
            return None
            
    def get_portfolio_with_broker(self, mt5_id: str, broker_name: str):
        if not self.client or not mt5_id or not broker_name: return None
        try:
            response = self.client.table("Portfolios").select("*").eq("mt5_account_id", mt5_id).eq("BrokerName", broker_name).single().execute()
            return response.data if response.data else None
        except Exception as e:
            # This is expected to fail if not found, so only print real errors.
            if "0 rows" not in str(e):
                print(f"ERROR (HEADLESS) in get_portfolio_with_broker: {e}")
            return None

    def insert_new_portfolio(self, portfolio_data: dict):
        if not self.client: return None, "Supabase client not initialized."
        try:
            response = self.client.table("Portfolios").insert(portfolio_data).execute()
            if response.data:
                print(f"SUCCESS (HEADLESS): Inserted new portfolio for MT5 ID {portfolio_data.get('mt5_account_id')}")
                return response.data[0], "Success"
            return None, "Failed to insert portfolio."
        except Exception as e:
            print(f"ERROR (HEADLESS) in insert_new_portfolio: {e}")
            return None, str(e)

    def update_portfolio_timezone(self, portfolio_id: str, offset: int):
        if not self.client: return False
        try:
            self.client.table("Portfolios").update({"TimezoneOffset": offset}).eq("PortfolioID", portfolio_id).execute()
            print(f"SUCCESS (HEADLESS): Updated timezone for PortfolioID {portfolio_id} to {offset}")
            return True
        except Exception as e:
            print(f"ERROR (HEADLESS) in update_portfolio_timezone: {e}")
            return False

    def get_daily_opening_balance(self, portfolio_id: str, mt5_account_id: str, broker_date_str: str):
        if not self.client: return None
        # [SYSTEM INTEGRITY FIX] Use the provided broker date string for lookup
        try:
            response = self.client.table("PortfolioDailyMetrics").select("OpeningBalance").eq("PortfolioID", portfolio_id).eq("mt5_account_id", str(mt5_account_id)).eq("Date", broker_date_str).single().execute()
            if response.data:
                balance = response.data.get('OpeningBalance')
                print(f"INFO (HEADLESS): Found existing opening balance in DB: {balance} for MT5 Account {mt5_account_id} on date {broker_date_str}")
                return balance
            print(f"INFO (HEADLESS): No existing opening balance found in DB for {broker_date_str}")
            return None
        except Exception as e:
            if "0 rows" not in str(e):
                 print(f"ERROR (HEADLESS) in get_daily_opening_balance: {e}")
            return None

    def set_daily_opening_balance(self, portfolio_id: str, mt5_account_id: str, opening_balance: float, broker_date_str: str):
        if not self.client: return False
        # [SYSTEM INTEGRITY FIX] Use the provided broker date string for saving
        try:
            record = { "PortfolioID": portfolio_id, "Date": broker_date_str, "OpeningBalance": opening_balance, "mt5_account_id": str(mt5_account_id) }
            self.client.table("PortfolioDailyMetrics").upsert(record, on_conflict='PortfolioID, Date').execute()
            print(f"SUCCESS (HEADLESS): Set opening balance for {broker_date_str} to {opening_balance}")
            return True
        except Exception as e:
            print(f"ERROR (HEADLESS) in set_daily_opening_balance: {e}")
            return False
        
    def get_broker_timezone(self, broker_name):
        """ค้นหา timezone offset จากชื่อโบรกเกอร์"""
        try:
            response = self.client.table('BrokerSettings').select('timezone_offset').eq('broker_name', broker_name).single().execute()
            return response.data.get('timezone_offset')
        except Exception:
            return None

    def set_broker_timezone(self, broker_name, offset):
        """บันทึก timezone offset สำหรับโบรกเกอร์ใหม่"""
        try:
            data_to_insert = {'broker_name': broker_name, 'timezone_offset': offset}
            self.client.table('BrokerSettings').upsert(data_to_insert, on_conflict='broker_name').execute()
            print(f"SUCCESS (HEADLESS): Set timezone for broker '{broker_name}' to {offset}")
            return True
        except Exception as e:
            print(f"Error saving broker timezone setting: {e}")
            return False
        
    def update_portfolio_settings(self, portfolio_id: str, settings_data: dict):
        """
        Updates specific settings for a given portfolio.
        """
        if not portfolio_id or not settings_data:
            print("ERROR: Portfolio ID or settings data is missing for update.")
            return False
        try:
            self.client.table('Portfolios').update(settings_data).eq('PortfolioID', portfolio_id).execute()
            print(f"Successfully updated settings for portfolio {portfolio_id}.")
            return True
        except Exception as e:
            print(f"EXCEPTION during portfolio settings update for {portfolio_id}: {e}")
            return False    