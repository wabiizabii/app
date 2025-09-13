import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

# --- Standalone Connection Setup ---
# This part is to make the script runnable on its own.
# It assumes a similar config structure.
try:
    from config import settings
    BROKER_TZ_STR = settings.BROKER_TIMEZONE
except (ImportError, AttributeError):
    print("Could not import settings. Using default timezone 'Etc/GMT-3'.")
    BROKER_TZ_STR = 'Etc/GMT-3' # Default for many brokers

def initialize_mt5():
    """A simple, direct connection function."""
    if not mt5.initialize():
        print(f"CRITICAL FAIL: initialize() failed, error code = {mt5.last_error()}")
        return False
    
    account_info = mt5.account_info()
    if not account_info:
        print(f"CRITICAL FAIL: account_info() failed, error code = {mt5.last_error()}")
        mt5.shutdown()
        return False
    
    print(f"SUCCESS: Connected to MT5 Account: {account_info.login}")
    return True

def run_brute_force_check():
    """
    This function has one purpose: find and print all deals from the last 7 days.
    """
    print("\n" + "="*50)
    print("--- PROTOCOL: BRUTE FORCE INTERROGATION ---")
    print("="*50 + "\n")

    if not initialize_mt5():
        return

    try:
        # Define a very wide time window to ensure we don't miss anything.
        utc_now = datetime.now(pytz.utc)
        start_date = utc_now - timedelta(days=7)
        end_date = utc_now

        print(f"Interrogating MT5 for all deals between:")
        print(f"Start (UTC): {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End   (UTC): {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)

        # The most direct call to the MT5 API possible.
        deals = mt5.history_deals_get(start_date, end_date)

        if deals is None:
            print("\nRESULT: CRITICAL FAILURE")
            print("mt5.history_deals_get() returned 'None'.")
            print("This indicates a deep connection issue or a problem with the MT5 terminal itself.")
            return

        if len(deals) == 0:
            print("\nRESULT: INTERROGATION COMPLETE - NO DEALS FOUND")
            print("The MT5 API did not return any deals for the last 7 days.")
            print("This confirms the issue is NOT with our Python logic, but with what the MT5 API is providing to Python.")
            return

        # If we get here, we found something!
        print(f"\nRESULT: INTERROGATION SUCCESS - FOUND {len(deals)} DEALS!")
        print("-" * 50)
        
        df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        
        # Display the raw data exactly as MT5 sees it.
        print("--- RAW DEAL DATA ---")
        # pd.set_option('display.max_rows', None) # Uncomment to see all rows if there are many
        print(df.to_string())
        print("---------------------\n")

    except Exception as e:
        print(f"\nAn exception occurred during the check: {e}")
    finally:
        print("Shutting down MT5 connection.")
        mt5.shutdown()

if __name__ == "__main__":
    run_brute_force_check()