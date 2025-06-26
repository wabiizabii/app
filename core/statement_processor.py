# core/statement_processor.py (แก้ไข NameError: 'settings' not defined)

import pandas as pd
import io
import re
from datetime import datetime
from config import settings # <--- เพิ่มบรรทัดนี้

def extract_data_from_report_content(file_content_input: bytes):
    """
    [Final Complete Version] This version parses all three tables (Deals, Orders, Positions)
    and also calculates the final summary directly from the deals_df for maximum robustness.
    Includes extraction of Account #, Name, Client, Credit, Gross Profit,
    and all other detailed summary statistics from summary text lines.
    It also prepares itemized deposit/withdrawal logs.
    """
    extracted_data = {
        'deals': pd.DataFrame(),
        'orders': pd.DataFrame(),
        'positions': pd.DataFrame(),
        'balance_summary': {},
        'results_summary': {},
        'portfolio_details': {},
        'deposit_withdrawal_logs': []
    }
    
    lines = []
    if isinstance(file_content_input, str):
        lines = file_content_input.strip().split('\n')
    elif isinstance(file_content_input, bytes):
        lines = file_content_input.decode('utf-8', errors='replace').strip().split('\n')
    else:
        return extracted_data

    # --- 1. Extract Portfolio Details and other single-line summaries first ---
    # จะเก็บข้อมูลที่ดึงจากบรรทัดข้อความสรุปก่อน แล้วค่อยอัปเดตด้วยค่าที่คำนวณจาก Deals ถ้ามี
    portfolio_details = {}
    balance_summary_parsed_from_text = {} 
    results_summary_parsed_from_text = {} 
    
    # Helper to safely parse numeric values, handling spaces and commas in numbers
    def clean_and_float(value_str):
        if value_str is None: return 0.0
        s = str(value_str).strip().replace(' ', '').replace(',', '').replace('–', '-').replace('—', '-')
        if s.endswith('%'): s = s[:-1] # Remove % for percentage values
        try: return float(s)
        except ValueError: return 0.0

    # General pattern for "Key:,,, Value" or "Key:,,, Value (Percentage%)" etc.
    # Adjusted to handle multiple commas and optional parentheses values
    def parse_summary_line_item(line, key_word):
        # Regex to find 'key_word:,,,[value]' or 'key_word:,,,[value] (Value2%)'
        # (?:,*?) matches 0 or more commas non-greedily
        match = re.search(rf"{key_word}:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)(?:\s*\(([-+]?\s*\d[\d\s\.,-]*)(%)?\))?", line)
        if match:
            val1 = clean_and_float(match.group(1))
            val2 = None
            is_percent = False
            if match.group(2):
                val2 = clean_and_float(match.group(2))
                is_percent = bool(match.group(3))
            return val1, val2, is_percent
        return None, None, False

    # Helper for "Key: Count (Percentage%)" e.g. "Short Trades (won %):48 (79.17%)"
    def parse_count_and_percent(line, key_word):
        match = re.search(rf"{key_word}:,(?:,*?)(\d+)\s*\(([-+]?\d*\.?\d+)%\)", line)
        if match:
            try: return int(clean_and_float(match.group(1))), clean_and_float(match.group(2))
            except ValueError: pass
        return None, None
    
    # Helper for "Key: Count (Value)" e.g. "Maximum consecutive wins ($):20 (41.07)"
    def parse_count_and_value(line, key_word):
        match = re.search(rf"{key_word}:,(?:,*?)(\d+)\s*\(([-+]?\d*\.?\d+)\)", line)
        if match:
            try: return int(clean_and_float(match.group(1))), clean_and_float(match.group(2))
            except ValueError: pass
        return None, None

    # Helper for "Key: Value (Count)" e.g. "Maximal consecutive profit (count):163.65 (18)"
    def parse_value_and_count(line, key_word):
        match = re.search(rf"{key_word}:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)\s*\(([-+]?\s*\d+)\)", line)
        if match:
            try: return clean_and_float(match.group(1)), int(clean_and_float(match.group(2)))
            except ValueError: pass
        return None, None


    for line in lines:
        line_stripped = line.strip()
        
        # Extract Account Details (adjusted regex for "Account:,,," and "Name:,,,")
        # Account:,,,"80968260 (USD, FPMarketsSC-Live, real, Hedge)",,,,,,,,,,
        if line_stripped.startswith("Account:"):
            # Adjusted to capture the number before the first parenthesis, or just the number if no parenthesis
            match = re.search(r"Account:.*?,*?\"?(\d+)(?:\s*\(.*?\))?\"?", line_stripped)
            if match:
                portfolio_details['account_id'] = match.group(1)
            

        # Name:,,,Bhudit Samitachart,,,,,,,,,,
        if line_stripped.startswith("Name:"):
            # Capture content after "Name:,,," until next comma or end of line, then strip
            match = re.search(r"Name:,(?:,*?)([^,]+)", line_stripped)
            if match:
                portfolio_details['account_name'] = match.group(1).strip()
            else: # Fallback for simpler formats if any
                match = re.search(r"Name:\s*(.+)", line_stripped)
                if match: portfolio_details['account_name'] = match.group(1).strip()

        # Client: (Note: Based on sample, Client is N/A because it's not present)
        if line_stripped.startswith("Client:"):
            match = re.search(r"Client:\s*(.+)", line_stripped)
            if match:
                portfolio_details['client_name'] = match.group(1).strip()


        # Extract Financial Summary (usually at the very bottom of the report)
        # Balance:,,, 2.38,,,Free Margin:,,, 2.38,,,,
        # Credit Facility:,,,0.00,,,Margin:,,,0.00,,,,
        # Floating P/L:,,,0.00,,,Margin Level:,,,0.00%,,,,
        # Equity:,,, 2.38,,,,,,,,,,
        
        if "Balance:" in line_stripped and "Equity:" in line_stripped:
            balance_match = re.search(r"Balance:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Equity:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Free Margin:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Margin:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Floating P/L:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Margin Level:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*%)", line_stripped)
            if balance_match:
                try:
                    balance_summary_parsed_from_text['Balance'] = clean_and_float(balance_match.group(1))
                    balance_summary_parsed_from_text['Equity'] = clean_and_float(balance_match.group(2))
                    balance_summary_parsed_from_text['Free_Margin'] = clean_and_float(balance_match.group(3))
                    balance_summary_parsed_from_text['Margin'] = clean_and_float(balance_match.group(4))
                    balance_summary_parsed_from_text['Floating_P_L'] = clean_and_float(balance_match.group(5))
                    balance_summary_parsed_from_text['Margin_Level'] = clean_and_float(balance_match.group(6))
                except ValueError: pass

        if "Credit Facility:" in line_stripped:
            val, _, _ = parse_summary_line_item(line_stripped, "Credit Facility")
            if val is not None: balance_summary_parsed_from_text['Credit_Facility'] = val


        # --- Extract ALL other detailed summary statistics from text lines ---
        # Handling combined lines with multiple key-value pairs
        # Total Net Profit:,,, 302.43,Gross Profit:,,, 473.06,Gross Loss:,,,- 170.63,,
        if "Total Net Profit:" in line_stripped and "Gross Profit:" in line_stripped and "Gross Loss:" in line_stripped:
            match = re.search(r"Total Net Profit:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Gross Profit:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Gross Loss:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*", line_stripped)
            if match:
                results_summary_parsed_from_text['Total_Net_Profit_Text'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Gross_Profit'] = clean_and_float(match.group(2))
                results_summary_parsed_from_text['Gross_Loss'] = clean_and_float(match.group(3))

        # Profit Factor:,,, 2.77,Expected Payoff:,,, 1.49,,,,,,
        if "Profit Factor:" in line_stripped and "Expected Payoff:" in line_stripped:
            match = re.search(r"Profit Factor:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Expected Payoff:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*", line_stripped)
            if match:
                results_summary_parsed_from_text['Profit_Factor'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Expected_Payoff'] = clean_and_float(match.group(2))

        # Recovery Factor:,,, 3.09,Sharpe Ratio:,,, 0.24,,,,,,
        if "Recovery Factor:" in line_stripped and "Sharpe Ratio:" in line_stripped:
            match = re.search(r"Recovery Factor:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Sharpe Ratio:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*", line_stripped)
            if match:
                results_summary_parsed_from_text['Recovery_Factor'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Sharpe_Ratio'] = clean_and_float(match.group(2))
        
        # Balance Drawdown Maximal:,,,97.98 (19.58%),Balance Drawdown Relative:,,,21.61% (34.29),,
        if "Balance Drawdown Maximal:" in line_stripped and "Balance Drawdown Relative:" in line_stripped:
            match = re.search(r"Balance Drawdown Maximal:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)\s*\(([-+]?\s*\d[\d\s\.,-]*)\%\),*?Balance Drawdown Relative:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)\%\s*\(([-+]?\s*\d[\d\s\.,-]*)\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Maximal_Drawdown_Value'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Maximal_Drawdown_Percent'] = clean_and_float(match.group(2))
                results_summary_parsed_from_text['Balance_Drawdown_Relative_Percent'] = clean_and_float(match.group(3))
                results_summary_parsed_from_text['Balance_Drawdown_Relative_Value'] = clean_and_float(match.group(4))
        
        if "Balance Drawdown Absolute:" in line_stripped:
            val, _, _ = parse_summary_line_item(line_stripped, "Balance Drawdown Absolute")
            if val is not None: results_summary_parsed_from_text['Balance_Drawdown_Absolute'] = val
        
        # Total Trades:,,, 203,Short Trades (won %):,,,48 (79.17%),Long Trades (won %):,,,155 (72.90%),,
        if "Total Trades:" in line_stripped and "Short Trades (won %):" in line_stripped and "Long Trades (won %):" in line_stripped:
            match = re.search(r"Total Trades:,(?:,*?)(\d+),*?Short Trades \(won %\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\),*?Long Trades \(won %\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Total_Trades'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Short_Trades_Count'] = int(clean_and_float(match.group(2)))
                results_summary_parsed_from_text['Short_Trades_Won_Percent'] = clean_and_float(match.group(3))
                results_summary_parsed_from_text['Long_Trades_Count'] = int(clean_and_float(match.group(4)))
                results_summary_parsed_from_text['Long_Trades_Won_Percent'] = clean_and_float(match.group(5))
        
        # ,,,,Profit Trades (% of total):,,,151 (74.38%),Loss Trades (% of total):,,,52 (25.62%),,
        if "Profit Trades (% of total):" in line_stripped and "Loss Trades (% of total):" in line_stripped:
            match = re.search(r"Profit Trades \(\% of total\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\),*?Loss Trades \(\% of total\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Profit_Trades_Count'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Profit_Trades_Percent'] = clean_and_float(match.group(2))
                results_summary_parsed_from_text['Loss_Trades_Count'] = int(clean_and_float(match.group(3)))
                results_summary_parsed_from_text['Loss_Trades_Percent'] = clean_and_float(match.group(4))

        # ,,,,Largest profit trade:,,, 40.26,Largest loss trade:,,,- 13.51,,
        if "Largest profit trade:" in line_stripped and "Largest loss trade:" in line_stripped:
            match = re.search(r"Largest profit trade:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Largest loss trade:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*", line_stripped)
            if match:
                results_summary_parsed_from_text['Largest_Profit_Trade'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Largest_Loss_Trade'] = clean_and_float(match.group(2))

        # ,,,,Average profit trade:,,, 3.13,Average loss trade:,,,- 3.28,,
        if "Average profit trade:" in line_stripped and "Average loss trade:" in line_stripped:
            match = re.search(r"Average profit trade:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Average loss trade:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*", line_stripped)
            if match:
                results_summary_parsed_from_text['Average_Profit_Trade'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Average_Loss_Trade'] = clean_and_float(match.group(2))
        
        # ,,,,Maximum consecutive wins ($):,,,20 (41.07),Maximum consecutive losses ($):,,,10 (-55.84),,
        if "Maximum consecutive wins ($):" in line_stripped and "Maximum consecutive losses ($):" in line_stripped:
            match = re.search(r"Maximum consecutive wins \(\$\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d[\d\s\.,-]*)\),*?Maximum consecutive losses \(\$\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d[\d\s\.,-]*)\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Max_Consecutive_Wins_Count'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Max_Consecutive_Wins_Profit'] = clean_and_float(match.group(2))
                results_summary_parsed_from_text['Max_Consecutive_Losses_Count'] = int(clean_and_float(match.group(3)))
                results_summary_parsed_from_text['Max_Consecutive_Losses_Profit'] = clean_and_float(match.group(4))

        # ,,,,Maximal consecutive profit (count):,,,163.65 (18),Maximal consecutive loss (count):,,,-55.84 (10),,
        if "Maximal consecutive profit (count):" in line_stripped and "Maximal consecutive loss (count):" in line_stripped:
            match = re.search(r"Maximal consecutive profit \(count\):,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)\s*\(([-+]?\s*\d+)\),*?Maximal consecutive loss \(count\):,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)\s*\(([-+]?\s*\d+)\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Maximal_Consecutive_Profit_Value'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Maximal_Consecutive_Profit_Count'] = int(clean_and_float(match.group(2)))
                results_summary_parsed_from_text['Maximal_Consecutive_Loss_Value'] = clean_and_float(match.group(3))
                results_summary_parsed_from_text['Maximal_Consecutive_Loss_Count'] = int(clean_and_float(match.group(4)))
        
        # ,,,,Average consecutive wins:,,, 6,Average consecutive losses:,,, 2,,
        if "Average consecutive wins:" in line_stripped and "Average consecutive losses:" in line_stripped:
            match = re.search(r"Average consecutive wins:,(?:,*?)(\d+),*?Average consecutive losses:,(?:,*?)(\d+)", line_stripped)
            if match:
                results_summary_parsed_from_text['Average_Consecutive_Wins'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Average_Consecutive_Losses'] = int(clean_and_float(match.group(2)))
                

    extracted_data['portfolio_details'] = portfolio_details
    extracted_data['balance_summary'].update(balance_summary_parsed_from_text) 
    extracted_data['results_summary'].update(results_summary_parsed_from_text)

    # --- 2. Find all section headers for tables ---
    section_headers_map = {
        "Positions": "Time,Position,Symbol,Type,Volume,Price,S / L,T / P,Time,Price,Commission,Swap,Profit",
        "Orders": "Open Time,Order,Symbol,Type,Volume,Price,S / L,T / P,Time,State,,Comment",
        "Deals": "Time,Deal,Symbol,Type,Direction,Volume,Price,Order,Commission,Fee,Swap,Profit,Balance,Comment"
    }
    expected_columns_map = {
        "Positions": ["Time_Pos", "Position_ID", "Symbol_Pos", "Type_Pos", "Volume_Pos", "Price_Open_Pos", "S_L_Pos", "T_P_Pos", "Time_Close_Pos", "Price_Close_Pos", "Commission_Pos", "Swap_Pos", "Profit_Pos"],
        "Orders": ["Open_Time_Ord", "Order_ID_Ord", "Symbol_Ord", "Type_Ord", "Volume_Ord", "Price_Ord", "S_L_Ord", "T_P_Ord", "Close_Time_Ord", "State_Ord", "Filler_Ord", "Comment_Ord"],
        "Deals": ["Time_Deal", "Deal_ID", "Symbol_Deal", "Type_Deal", "Direction_Deal", "Volume_Deal", "Price_Deal", "Order_ID_Deal", "Commission_Deal", "Fee_Deal", "Swap_Deal", "Profit_Deal", "Balance_Deal", "Comment_Deal"]
    }
    section_order = ["Positions", "Orders", "Deals"]
    header_indices = {name: -1 for name in section_order}

    for i, line in enumerate(lines):
        for name, header_text in section_headers_map.items():
            if header_text in line:
                header_indices[name] = i
                break

    # --- 3. Parse each section into a DataFrame ---
    for i, section_name in enumerate(section_order):
        start_index = header_indices[section_name]
        if start_index == -1:
            continue

        data_start_line = start_index + 1
        data_end_line = len(lines)
        
        for next_section_name in section_order[i+1:]:
            if header_indices[next_section_name] != -1 and header_indices[next_section_name] > start_index:
                data_end_line = header_indices[next_section_name]
                break
        
        # Check for the start of any summary text as an end boundary for tables
        for j in range(data_start_line, data_end_line):
            # Combined regex for all potential summary starts (updated to include all new stats)
            # Make sure to handle leading commas and spaces in the regex pattern for these keywords
            summary_start_patterns = [
                r"^Balance:", r"^Credit Facility:", r"^Floating P/L:", r"^Equity:", r"^Free Margin:", r"^Margin:", r"^Margin Level:",
                r"^Total Net Profit:", r"^Gross Profit:", r"^Gross Loss:", r"^Profit Factor:",
                r"^Recovery Factor:", r"^Expected Payoff:", r"^Sharpe Ratio:", r"^Balance Drawdown:",
                r"^Balance Drawdown Absolute:", r"^Balance Drawdown Maximal:", r"^Balance Drawdown Relative:",
                r"^Total Trades:", r"^Short Trades \(won %\):", r"^Long Trades \(won %\):",
                r"^Profit Trades \(% of total\):", r"^Loss Trades \(% of total\):",
                r"^Largest profit trade:", r"^Average profit trade:", r"^Largest loss trade:",
                r"^Average loss trade:", r"^Maximum consecutive wins \(\$\):", r"^Maximal consecutive profit \(count\):",
                r"^Average consecutive wins:", r"^Maximum consecutive losses \(\$\):", r"^Maximal consecutive loss \(count\):",
                r"^Average consecutive losses:"
            ]
            # Match for lines that start with a known summary keyword, potentially with leading commas/spaces
            if any(re.match(r"^(?:,*?)\s*" + pattern, lines[j].strip()) for pattern in summary_start_patterns):
                data_end_line = j
                break

        # Filter out empty lines or lines without commas (which are usually non-data lines)
        section_lines = [line.strip() for line in lines[data_start_line:data_end_line] if line.strip() and ',' in line]

        if not section_lines:
            continue

        try:
            df = pd.read_csv(io.StringIO("\n".join(section_lines)), header=None, names=expected_columns_map[section_name], skipinitialspace=True, dtype=str)
            df.dropna(how='all', inplace=True)
            extracted_data[section_name.lower()] = df
        except Exception as e:
            print(f"Error parsing {section_name} section: {e}")
            pass

    # --- 4. Calculate summary directly from the 'deals' DataFrame for accuracy ---
    # And prepare itemized deposit/withdrawal logs
    deals_df = extracted_data.get('deals', pd.DataFrame())
    
    # Initialize calculated values. Prioritize calculated values from deals.
    # Note: Deposit/Withdrawal from text will be 'Deposit_Text'/'Withdrawal_Text' in results_summary_parsed_from_text.
    # Final 'Deposit'/'Withdrawal' in final_balance_summary will be calculated from deals.
    calculated_deposit = 0.0
    calculated_withdrawal = 0.0
    calculated_net_profit = 0.0 # This will always be calculated from deals.

    itemized_deposit_withdrawal_logs = [] # <--- List to store itemized D/W for DepositWithdrawalLogs sheet

    if not deals_df.empty:
        deals_df_copy = deals_df.copy()
        
        deals_df_copy['Profit_Deal'] = deals_df_copy['Profit_Deal'].astype(str).str.replace(' ', '').str.replace('–', '-').str.replace('—', '-')
        deals_df_copy['Profit_Deal'] = pd.to_numeric(deals_df_copy['Profit_Deal'], errors='coerce').fillna(0)
        deals_df_copy['Balance_Deal'] = pd.to_numeric(deals_df_copy['Balance_Deal'], errors='coerce').fillna(0)
        
        # Iterate through deals to calculate net profit and extract itemized D/W
        for index, row in deals_df_copy.iterrows():
            deal_type = str(row.get('Type_Deal', '')).lower().strip()
            comment = str(row.get('Comment_Deal', '')).lower().strip()
            profit_val = row['Profit_Deal']
            time_deal_str = row.get('Time_Deal', '') # Get DateTime string for D/W log

            if deal_type in ['buy', 'sell']:
                calculated_net_profit += profit_val
            elif deal_type == 'balance':
                # Identify deposit/withdrawal for itemized logs
                transaction_type = None
                if 'deposit' in comment:
                    calculated_deposit += profit_val # Add to total calculated deposit
                    transaction_type = 'Deposit'
                elif 'withdraw' in comment:
                    calculated_withdrawal += profit_val # Add to total calculated withdrawal
                    transaction_type = 'Withdrawal'
                
                # Add to itemized logs for DepositWithdrawalLogs sheet
                if transaction_type:
                    itemized_deposit_withdrawal_logs.append({
                        "TransactionID": str(row.get('Deal_ID', '')), # Use Deal_ID as TransactionID
                        "DateTime": time_deal_str, # Use Time_Deal for DateTime
                        "Type": transaction_type,
                        "Amount": profit_val,
                        "Comment": row.get('Comment_Deal', '')
                        # PortfolioID, PortfolioName, SourceFile, ImportBatchID will be added in gs_handler
                    })
        
        # Update results_summary and balance_summary with calculated values (prioritized)
        # These will override any _Text versions if present, and be used for final output
        extracted_data['results_summary']['Total_Net_Profit'] = calculated_net_profit
        # Ensure 'Deposit' and 'Withdrawal' keys are explicitly set for final_summary_data
        # even if they came from text parsing initially, now they are from calculation
        extracted_data['balance_summary']['Deposit'] = calculated_deposit # Using GSheet Header name
        extracted_data['balance_summary']['Withdrawal'] = calculated_withdrawal # Using GSheet Header name
        
        if not deals_df_copy.empty:
            # Update Balance and Equity from the last row of Deals_df if not already set or override
            # Ensure these are float/numeric
            extracted_data['balance_summary']['Balance'] = float(deals_df_copy['Balance_Deal'].iloc[-1]) # Using GSheet Header name
            extracted_data['balance_summary']['Equity'] = float(deals_df_copy['Balance_Deal'].iloc[-1]) # Using GSheet Header name
    
    extracted_data['deposit_withdrawal_logs'] = itemized_deposit_withdrawal_logs # <--- Store itemized logs

    # Ensure all expected summary keys exist, even if with default 0.0
    # Combine text-parsed and calculated values, prioritizing calculated where applicable
    # Mapping to settings.py headers for final output.
    # Note: Keys in final_summary_data must match GSheet Headers exactly now.
    
    # Initialize final_summary_data with all expected keys from settings.WORKSHEET_HEADERS[WORKSHEET_STATEMENT_SUMMARIES]
    final_summary_data = {h: 0.0 for h in settings.WORKSHEET_HEADERS[settings.WORKSHEET_STATEMENT_SUMMARIES]}
    
    # Fill in Portfolio Details (these are from the report header)
    final_summary_data['PortfolioID'] = extracted_data['portfolio_details'].get('account_id', '')
    final_summary_data['PortfolioName'] = extracted_data['portfolio_details'].get('account_name', '')
    final_summary_data['ClientName'] = extracted_data['portfolio_details'].get('client_name', '')

    # Fill in Balance Summary data (e.g., Balance, Equity, Free_Margin, Credit_Facility, Deposit, Withdrawal)
    for key, value in extracted_data['balance_summary'].items():
        if key in final_summary_data: # Ensure it's an expected header
            final_summary_data[key] = value

    # Fill in Results Summary data (e.g., Gross_Profit, Profit_Factor, Total_Net_Profit, etc.)
    for key, value in extracted_data['results_summary'].items():
        # Handle Total_Net_Profit: calculated from deals is preferred. If not available, use text-parsed.
        if key == 'Total_Net_Profit' and extracted_data['results_summary'].get('Total_Net_Profit') is not None and extracted_data['results_summary'].get('Total_Net_Profit') != 0.0:
            final_summary_data[key] = extracted_data['results_summary'].get(key)
        elif key == 'Total_Net_Profit_Text' and 'Total_Net_Profit' not in extracted_data['results_summary']: # Only use text if calculated is not present
             final_summary_data['Total_Net_Profit'] = extracted_data['results_summary'].get(key)
        elif key in final_summary_data: # For all other keys
            final_summary_data[key] = value

    extracted_data['final_summary_data'] = final_summary_data # Store the combined final summary

    return extracted_data