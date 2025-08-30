# core/headless_supabase_handler.py (Final Corrected Logic Version)

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
        """
        [CORRECTED] Fetches a portfolio by its linked MT5 Account ID from the 'Portfolios' table.
        """
        if not self.client or not mt5_id: return None
        try:
            response = self.client.table("Portfolios").select("*").eq("mt5_account_id", mt5_id).single().execute()
            if response.data:
                return response.data
            return None
        except Exception as e:
            print(f"ERROR (HEADLESS) in get_portfolio_by_mt5_account_id: {e}")
            return None
        
    def insert_new_portfolio(self, portfolio_data: dict):
        """
        Inserts a new portfolio record into the 'Portfolios' table.
        """
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

    # --- [REBUILT] Enforces 1-to-1 Check ---
    def get_daily_opening_balance(self, portfolio_id: str, mt5_account_id: str):
        """
        [REBUILT] Gets the opening balance for today, strictly matching BOTH PortfolioID and mt5_account_id.
        """
        if not self.client: return None
        today_utc_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        try:
            response = self.client.table("PortfolioDailyMetrics") \
                .select("OpeningBalance") \
                .eq("PortfolioID", portfolio_id) \
                .eq("mt5_account_id", str(mt5_account_id)) \
                .eq("Date", today_utc_str) \
                .single() \
                .execute()
            
            if response.data:
                balance = response.data.get('OpeningBalance')
                print(f"INFO (HEADLESS): Found existing opening balance in DB: {balance} for MT5 Account {mt5_account_id}")
                return balance
            return None
        except Exception as e:
            # This will now correctly show "single query returned 0 rows" if not found, which is not an error.
            # We only print if it's a real database error.
            if "0 rows" not in str(e):
                 print(f"ERROR (HEADLESS) in get_daily_opening_balance: {e}")
            return None

    # --- [REBUILT] Enforces 1-to-1 Check ---
    def set_daily_opening_balance(self, portfolio_id: str, mt5_account_id: str, opening_balance: float):
        """
        [REBUILT] Sets or updates the opening balance for today using upsert,
        strictly matching BOTH PortfolioID and mt5_account_id.
        """
        if not self.client: return False
        today_utc_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        try:
            record = {
                "PortfolioID": portfolio_id,
                "Date": today_utc_str,
                "OpeningBalance": opening_balance,
                "mt5_account_id": str(mt5_account_id)
            }
            # The on_conflict parameter tells Supabase which columns define a "duplicate".
            # This MUST match the Composite Primary Key of the table.
            self.client.table("PortfolioDailyMetrics").upsert(
                record, 
                on_conflict='PortfolioID, Date'
            ).execute()
            return True
        except Exception as e:
            print(f"ERROR (HEADLESS) in set_daily_opening_balance: {e}")
            return False