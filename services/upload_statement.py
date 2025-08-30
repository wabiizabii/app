# services/upload_statement.py

import argparse
import os
import sys
from pprint import pprint

# --- Dynamic Path to access core modules ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from core.statement_processor import process_mt5_statement_html
from core.supabase_handler import SupabaseHandler # We use the original handler here
from config import settings

def main():
    """
    Main function to handle the statement upload from the command line.
    """
    # --- 1. Setup Command-Line Argument Parser ---
    parser = argparse.ArgumentParser(description="Process an MT5 statement and upload it to Supabase.")
    parser.add_argument("--file", required=True, help="Path to the MT5 statement .html file.")
    parser.add_argument("--portfolio-id", required=True, help="The PortfolioID from Supabase to associate this statement with.")
    
    args = parser.parse_args()
    
    file_path = args.file
    portfolio_id = args.portfolio_id

    print("-" * 50)
    print(f"🚀 Starting Statement Upload Process...")
    print(f"Portfolio ID: {portfolio_id}")
    print(f"File Path: {file_path}")
    print("-" * 50)

    # --- 2. Check if the file exists ---
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found at path: {file_path}")
        return

    # --- 3. Initialize Supabase Handler ---
    try:
        db_handler = SupabaseHandler(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        if not db_handler.client:
            print("❌ ERROR: Failed to initialize Supabase client. Check credentials.")
            return
        print("✅ Supabase client initialized successfully.")
    except Exception as e:
        print(f"❌ ERROR: Could not connect to Supabase. {e}")
        return
        
    # --- 4. Read and Process the HTML File ---
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        print("⏳ Processing HTML file... (This may take a moment)")
        processed_data = process_mt5_statement_html(file_content)

        # Check if processing was successful
        summary = processed_data.get('summary', {})
        deals_df = processed_data.get('deals', pd.DataFrame())

        if not summary or deals_df.empty:
            print("❌ ERROR: Failed to extract any meaningful data from the statement file.")
            return
        
        print("✅ File processed successfully!")
        print("\n--- Summary Data ---")
        pprint(summary) # pprint makes the dictionary easier to read
        print(f"\nFound {len(deals_df)} deals/trades in the statement.")

    except Exception as e:
        print(f"❌ ERROR: An error occurred during file processing: {e}")
        import traceback
        traceback.print_exc()
        return
        
    # --- 5. Save data to Supabase (Example: Saving Summary) ---
    # You can expand this to save deals, positions, etc. later
    try:
        print("\n⏳ Saving statement summary to Supabase...")
        
        # Add the PortfolioID to the summary data before saving
        summary_data_to_save = summary
        summary_data_to_save['PortfolioID'] = portfolio_id

        success, message = db_handler.save_statement_summary(summary_data_to_save)

        if success:
            print("🎉 SUCCESS: Statement summary data has been saved to Supabase!")
        else:
            print(f"❌ ERROR: Failed to save summary to Supabase. Reason: {message}")

    except Exception as e:
        print(f"❌ ERROR: An error occurred while saving to Supabase: {e}")


if __name__ == "__main__":
    main()