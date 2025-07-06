# core/statement_processor.py (The Definitive Final Version - Based on Original Full Code)

import pandas as pd
import io
import re
from datetime import datetime
from config import settings 

def extract_data_from_report_content(file_content_input: bytes):
    """
    [The Definitive Final Version]
    This version uses the full, original code as its base and makes only the
    necessary corrections to the Balance/Equity parsing and the final decision logic,
    ensuring all statistics are captured correctly across all scenarios.
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
    portfolio_details = {}
    balance_summary_parsed_from_text = {} 
    results_summary_parsed_from_text = {} 
    
    def clean_and_float(value_str):
        if value_str is None: return 0.0
        s = str(value_str).strip().replace(' ', '').replace(',', '').replace('–', '-').replace('—', '-')
        if s.endswith('%'): s = s[:-1]
        try: return float(s)
        except (ValueError, TypeError): return 0.0

    def parse_summary_line_item(line, key_word):
        match = re.search(r"Average consecutive wins:,\s*([-\s\d\.]+)(?:,*\s*)Average consecutive losses:,\s*([-\s\d\.]+)", line_stripped)
        if match:
            val1 = clean_and_float(match.group(1)); val2 = None; is_percent = False
            if match.group(2): val2 = clean_and_float(match.group(2)); is_percent = bool(match.group(3))
            return val1, val2, is_percent
        return None, None, False

    def parse_count_and_percent(line, key_word):
        match = re.search(rf"{key_word}:,(?:,*?)(\d+)\s*\(([-+]?\d*\.?\d+)%\)", line)
        if match:
            try: return int(clean_and_float(match.group(1))), clean_and_float(match.group(2))
            except ValueError: pass
        return None, None
    
    def parse_count_and_value(line, key_word):
        match = re.search(rf"{key_word}:,(?:,*?)(\d+)\s*\(([-+]?\d*\.?\d+)\)", line)
        if match:
            try: return int(clean_and_float(match.group(1))), clean_and_float(match.group(2))
            except ValueError: pass
        return None, None

    def parse_value_and_count(line, key_word):
        match = re.search(rf"{key_word}:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)\s*\(([-+]?\s*\d+)\)", line)
        if match:
            try: return clean_and_float(match.group(1)), int(clean_and_float(match.group(2)))
            except ValueError: pass
        return None, None

    def parse_results_section_line(line):
        data = {}
        # Patterns for key-value pairs in the Results section
        # Note: These patterns are designed to capture the specific format in your raw CSV
        # โดยการปรับปรุง Pattern ให้ครอบคลุมคอลัมน์พิเศษใน Results ที่อาจจะมี commas เพิ่มเติม
        patterns = {
            "Total Net Profit": r"Total Net Profit:,,,\s*([-\s\d\.]+)",
            "Gross Profit": r"Gross Profit:,,,\s*([-\s\d\.]+)",
            "Gross Loss": r"Gross Loss:,,,\s*([-\s\d\.]+)",
            "Profit Factor": r"Profit Factor:,,,\s*([-\s\d\.]+)",
            "Expected Payoff": r"Expected Payoff:,,,\s*([-\s\d\.]+)",
            "Recovery Factor": r"Recovery Factor:,,,\s*([-\s\d\.]+)",
            "Sharpe Ratio": r"Sharpe Ratio:,,,\s*([-\s\d\.]+)",
            "Balance Drawdown Absolute": r"Balance Drawdown Absolute:,,,\s*([-\s\d\.]+)",
            "Balance Drawdown Maximal": r"Balance Drawdown Maximal:,,,\s*([-\s\d\.]+)\s*\(([-+]?\s*\d[\d\s\.,-]*)\%\)",
            "Balance Drawdown Relative": r"Balance Drawdown Relative:,,,\s*([-\s\d\.]+)\%\s*\(([-+]?\s*\d[\d\s\.,-]*)\)",
            "Total Trades": r"Total Trades:,,,\s*(\d+)",
            "Short Trades \(won %\):": r"Short Trades \(won %\):,,,\s*(\d+)\s*\(([-+]?\d*\.?\d+)%\)", # แยก Total, %
            "Long Trades \(won %\):": r"Long Trades \(won %\):,,,\s*(\d+)\s*\(([-+]?\d*\.?\d+)%\)", # แยก Total, %
            "Profit Trades \(% of total\):": r"Profit Trades \(% of total\):,,,\s*(\d+)\s*\(([-+]?\d*\.?\d+)%\)", # แยก Total, %
            "Loss Trades \(% of total\):": r"Loss Trades \(% of total\):,,,\s*(\d+)\s*\(([-+]?\d*\.?\d+)%\)", # แยก Total, %
            "Largest profit trade": r"Largest profit trade:,,,\s*([-\s\d\.]+)",
            "Largest loss trade": r"Largest loss trade:,,,\s*([-\s\d\.]+)",
            "Average profit trade": r"Average profit trade:,,,\s*([-\s\d\.]+)",
            "Average loss trade": r"Average loss trade:,,,\s*([-\s\d\.]+)",
            "Maximum consecutive wins": r"Maximum consecutive wins \(\$\):,,,\s*(\d+)\s*\(([-+]?\s*\d[\d\s\.,-]*)\)",
            "Maximum consecutive losses": r"Maximum consecutive losses \(\$\):,,,\s*(\d+)\s*\(([-+]?\s*\d[\d\s\.,-]*)\)",
            "Maximal consecutive profit": r"Maximal consecutive profit \(count\):,,,\s*([-\s\d\.]+)\s*\(([-+]?\s*\d+)\)",
            "Maximal consecutive loss": r"Maximal consecutive loss \(count\):,,,\s*([-\s\d\.]+)\s*\(([-+]?\s*\d+)\)",
            "Average consecutive wins": r"Average consecutive wins:,,,\s*([-\s\d\.]+)",
            "Average consecutive losses": r"Average consecutive losses:,,,\s*([-\s\d\.]+)"
        }

        # ใช้ clean_and_float จากโค้ดของคุณ
        def local_clean_and_float(value_str):
            if value_str is None: return 0.0
            s = str(value_str).strip().replace(' ', '').replace(',', '').replace('–', '-').replace('—', '-')
            if s.endswith('%'): s = s[:-1]
            try: return float(s)
            except (ValueError, TypeError): return 0.0

        for key_prefix, pattern_str in patterns.items():
            match = re.search(pattern_str, line)
            if match:
                # Handle cases with two captured groups (e.g., "Count (Percentage)" or "Value (Count)")
                if len(match.groups()) == 2:
                    val1 = match.group(1)
                    val2 = match.group(2)

                    # Special handling for specific fields to match desired output format or type
                    if key_prefix == "Balance Drawdown Maximal":
                        data['Maximal_Drawdown_Value'] = local_clean_and_float(val1)
                        data['Maximal_Drawdown_Percent'] = local_clean_and_float(val2)
                        # Display format as "VALUE (PERCENTAGE%)"
                        data[key_prefix] = f"{val1} ({val2}%)" 
                    elif key_prefix == "Balance Drawdown Relative":
                        data['Balance_Drawdown_Relative_Percent'] = local_clean_and_float(val1)
                        data['Balance_Drawdown_Relative_Value'] = local_clean_and_float(val2)
                        # Display format as "PERCENTAGE% (VALUE)"
                        data[key_prefix] = f"{val1}% ({val2})"
                    elif key_prefix in ["Short Trades \(won %\):", "Long Trades \(won %\):",
                                        "Profit Trades \(% of total\):", "Loss Trades \(% of total\):"]:
                        # For "Total Trades: 76,Short Trades (won %):,,,\s*39\s*(17.95%),Long Trades (won %):,,,\s*37\s*(24.32%),,"
                        # The original regex in extract_data_from_report_content already handles these specific lines.
                        # This function parse_results_section_line will only be called per line for other Results
                        # So, these patterns won't typically be fully matched by line.
                        # We will make sure the main loop handles it.
                        pass # This function specifically will not process these from a single line
                    elif key_prefix == "Maximum consecutive wins": # 4 (1 445.58)
                        data['Max_Consecutive_Wins_Count'] = int(local_clean_and_float(val1))
                        data['Max_Consecutive_Wins_Profit'] = local_clean_and_float(val2)
                        data[key_prefix + ' ($)'] = f"{val1} ({val2})" # Use original format
                    elif key_prefix == "Maximum consecutive losses": # 25 (-6 874.60)
                        data['Max_Consecutive_Losses_Count'] = int(local_clean_and_float(val1))
                        data['Max_Consecutive_Losses_Profit'] = local_clean_and_float(val2)
                        data[key_prefix + ' ($)'] = f"{val1} ({val2})" # Use original format
                    elif key_prefix == "Maximal consecutive profit": # 1 715.10 (2)
                        data['Maximal_Consecutive_Profit_Value'] = local_clean_and_float(val1)
                        data['Maximal_Consecutive_Profit_Count'] = int(local_clean_and_float(val2))
                        data[key_prefix + ' (count)'] = f"{val1} ({val2})" # Use original format
                    elif key_prefix == "Maximal consecutive loss": # -6 874.60 (25)
                        data['Maximal_Consecutive_Loss_Value'] = local_clean_and_float(val1)
                        data['Maximal_Consecutive_Loss_Count'] = int(local_clean_and_float(val2))
                        data[key_prefix + ' (count)'] = f"{val1} ({val2})" # Use original format
                else: # Handle cases with a single captured group (most numeric values)
                    # Specific names for direct mapping
                    if key_prefix == "Total Trades":
                        data[key_prefix] = int(local_clean_and_float(match.group(1)))
                    elif key_prefix in ["Average consecutive wins", "Average consecutive losses"]:
                        data[key_prefix] = int(local_clean_and_float(match.group(1))) # Assuming these are always integers
                    else:
                        data[key_prefix] = local_clean_and_float(match.group(1))
                break # Stop after first match on a line

        return data

    # ### เพิ่มเติมจุดที่ 1: ตัวแปรสำหรับปักธงสถานการณ์พิเศษ ###
    has_open_positions_flag = False

    for line in lines:
        line_stripped = line.strip()
        
        # ### เพิ่มเติมจุดที่ 2: ตรวจจับ "ป้าย" Open Positions ###
        if "Open Positions" in line_stripped and len(line_stripped) < 30:
            has_open_positions_flag = True

        # (โค้ดการ parse ทั้งหมดในลูปนี้ คือของเดิมที่คุณเขียนไว้ทั้งหมด)
        if line_stripped.startswith("Account:"):
            match = re.search(r"Account:.*?,*?\"?(\d+)(?:\s*\(.*?\))?\"?", line_stripped)
            if match: portfolio_details['account_id'] = match.group(1)
        if line_stripped.startswith("Name:"):
            match = re.search(r"Name:,(?:,*?)([^,]+)", line_stripped)
            if match: portfolio_details['account_name'] = match.group(1).strip()
            else:
                match = re.search(r"Name:\s*(.+)", line_stripped)
                if match: portfolio_details['account_name'] = match.group(1).strip()
        if line_stripped.startswith("Client:"):
            match = re.search(r"Client:\s*(.+)", line_stripped)
            if match: portfolio_details['client_name'] = match.group(1).strip()
        
        # ### แก้ไขจุดที่ 3: ทลาย "กฎเหล็ก" และค้นหาแต่ละค่าอย่างอิสระ ###
        # ลบ if เดิมที่เช็ค "Balance:" และ "Equity:" พร้อมกันทิ้งไป
        
        if "Balance:" in line_stripped:
            match = re.search(r"Balance:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match: balance_summary_parsed_from_text['Balance'] = clean_and_float(match.group(1))
        
        if "Equity:" in line_stripped:
            match = re.search(r"Equity:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match: balance_summary_parsed_from_text['Equity'] = clean_and_float(match.group(1))

        if "Floating P/L:" in line_stripped:
            match = re.search(r"Floating P/L:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match: balance_summary_parsed_from_text['Floating_P_L'] = clean_and_float(match.group(1))
        
        # (โค้ดการ parse สถิติที่เหลือทั้งหมด คือของเดิมที่คุณเขียนไว้ ไม่มีการเปลี่ยนแปลง)
        if "Credit Facility:" in line_stripped:
            val, _, _ = parse_summary_line_item(line_stripped, "Credit Facility")
            if val is not None: balance_summary_parsed_from_text['Credit_Facility'] = val
        if "Total Net Profit:" in line_stripped and "Gross Profit:" in line_stripped and "Gross Loss:" in line_stripped:
            match = re.search(r"Total Net Profit:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Gross Profit:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Gross Loss:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*", line_stripped)
            if match:
                results_summary_parsed_from_text['Total_Net_Profit_Text'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Gross_Profit'] = clean_and_float(match.group(2))
                results_summary_parsed_from_text['Gross_Loss'] = clean_and_float(match.group(3))
        if "Profit Factor:" in line_stripped and "Expected Payoff:" in line_stripped:
            match = re.search(r"Profit Factor:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Expected Payoff:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match:
                results_summary_parsed_from_text['Profit_Factor'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Expected_Payoff'] = clean_and_float(match.group(2))
        if "Recovery Factor:" in line_stripped and "Sharpe Ratio:" in line_stripped:
            match = re.search(r"Recovery Factor:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Sharpe Ratio:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match:
                results_summary_parsed_from_text['Recovery_Factor'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Sharpe_Ratio'] = clean_and_float(match.group(2))
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
        if "Total Trades:" in line_stripped and "Short Trades (won %):" in line_stripped:
            match = re.search(r"Total Trades:(?:,+)\s*(\d+)(?:,+)\s*Short Trades \(won %\):(?:\s*,+)\s*(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\)(?:,+)\s*Long Trades \(won %\):(?:\s*,+)\s*(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Total_Trades'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Short_Trades_Count'] = int(clean_and_float(match.group(2)))
                results_summary_parsed_from_text['Short_Trades_Won_Percent'] = clean_and_float(match.group(3))
                results_summary_parsed_from_text['Long_Trades_Count'] = int(clean_and_float(match.group(4)))
                results_summary_parsed_from_text['Long_Trades_Won_Percent'] = clean_and_float(match.group(5))
        if "Profit Trades (% of total):" in line_stripped and "Loss Trades (% of total):" in line_stripped:
            match = re.search(r"Profit Trades \(\% of total\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\),*?Loss Trades \(\% of total\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Profit_Trades_Count'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Profit_Trades_Percent'] = clean_and_float(match.group(2))
                results_summary_parsed_from_text['Loss_Trades_Count'] = int(clean_and_float(match.group(3)))
                results_summary_parsed_from_text['Loss_Trades_Percent'] = clean_and_float(match.group(4))
        if "Largest profit trade:" in line_stripped and "Largest loss trade:" in line_stripped:
            match = re.search(r"Largest profit trade:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Largest loss trade:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match:
                results_summary_parsed_from_text['Largest_Profit_Trade'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Largest_Loss_Trade'] = clean_and_float(match.group(2))
        if "Average profit trade:" in line_stripped and "Average loss trade:" in line_stripped:
            match = re.search(r"Average profit trade:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Average loss trade:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match:
                results_summary_parsed_from_text['Average_Profit_Trade'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Average_Loss_Trade'] = clean_and_float(match.group(2))
        if "Maximum consecutive wins ($):" in line_stripped and "Maximum consecutive losses ($):" in line_stripped:
            match = re.search(r"Maximum consecutive wins \(\$\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d[\d\s\.,-]*)\),*?Maximum consecutive losses \(\$\):,(?:,*?)(\d+)\s*\(([-+]?\s*\d[\d\s\.,-]*)\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Max_Consecutive_Wins_Count'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Max_Consecutive_Wins_Profit'] = clean_and_float(match.group(2))
                results_summary_parsed_from_text['Max_Consecutive_Losses_Count'] = int(clean_and_float(match.group(3)))
                results_summary_parsed_from_text['Max_Consecutive_Losses_Profit'] = clean_and_float(match.group(4))
        if "Maximal consecutive profit (count):" in line_stripped and "Maximal consecutive loss (count):" in line_stripped:
            match = re.search(r"Maximal consecutive profit \(count\):,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)\s*\(([-+]?\s*\d+)\),*?Maximal consecutive loss \(count\):,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)\s*\(([-+]?\s*\d+)\)", line_stripped)
            if match:
                results_summary_parsed_from_text['Maximal_Consecutive_Profit_Value'] = clean_and_float(match.group(1))
                results_summary_parsed_from_text['Maximal_Consecutive_Profit_Count'] = int(clean_and_float(match.group(2)))
                results_summary_parsed_from_text['Maximal_Consecutive_Loss_Value'] = clean_and_float(match.group(3))
                results_summary_parsed_from_text['Maximal_Consecutive_Loss_Count'] = int(clean_and_float(match.group(4)))
        if "Average consecutive wins:" in line_stripped and "Average consecutive losses:" in line_stripped:
            match = re.search(r"(?:,*\s*)Average consecutive wins:(?:,+)\s*([-\s\d\.]+)(?:,+)\s*Average consecutive losses:(?:,+)\s*([-\s\d\.]+)", line_stripped)
            if match:
                # ใช้ int(float(...)) เพื่อให้แน่ใจว่าค่าถูกแปลงเป็นตัวเลขก่อนและเป็นจำนวนเต็ม
                results_summary_parsed_from_text['Average_Consecutive_Wins'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Average_Consecutive_Losses'] = int(clean_and_float(match.group(2)))

    extracted_data['portfolio_details'] = portfolio_details
    extracted_data['balance_summary'].update(balance_summary_parsed_from_text) 
    extracted_data['results_summary'].update(results_summary_parsed_from_text)

    # --- 2 & 3: การหาและดึงข้อมูลตาราง (คงไว้ตามเดิม) ---
    section_headers_map = {"Positions": "Time,Position,Symbol,Type,Volume,Price,S / L,T / P,Time,Price,Commission,Swap,Profit", "Orders": "Open Time,Order,Symbol,Type,Volume,Price,S / L,T / P,Time,State,,Comment", "Deals": "Time,Deal,Symbol,Type,Direction,Volume,Price,Order,Commission,Fee,Swap,Profit,Balance,Comment"}
    expected_columns_map = {"Positions": ["Time_Pos", "Position_ID", "Symbol_Pos", "Type_Pos", "Volume_Pos", "Price_Open_Pos", "S_L_Pos", "T_P_Pos", "Time_Close_Pos", "Price_Close_Pos", "Commission_Pos", "Swap_Pos", "Profit_Pos"], "Orders": ["Open_Time_Ord", "Order_ID_Ord", "Symbol_Ord", "Type_Ord", "Volume_Ord", "Price_Ord", "S_L_Ord", "T_P_Ord", "Close_Time_Ord", "State_Ord", "Filler_Ord", "Comment_Ord"], "Deals": ["Time_Deal", "Deal_ID", "Symbol_Deal", "Type_Deal", "Direction_Deal", "Volume_Deal", "Price_Deal", "Order_ID_Deal", "Commission_Deal", "Fee_Deal", "Swap_Deal", "Profit_Deal", "Balance_Deal", "Comment_Deal"]}
    section_order = ["Positions", "Orders", "Deals"]
    header_indices = {name: -1 for name in section_order}
    for i, line in enumerate(lines):
        for name, header_text in section_headers_map.items():
            if header_text in line: header_indices[name] = i; break
    for i, section_name in enumerate(section_order):
        start_index = header_indices[section_name]
        if start_index == -1: continue
        data_start_line, data_end_line = start_index + 1, len(lines)
        for next_section_name in section_order[i+1:]:
            if header_indices[next_section_name] != -1 and header_indices[next_section_name] > start_index: data_end_line = header_indices[next_section_name]; break
        summary_start_patterns = [r"^Balance:", r"^Credit Facility:", r"^Total Net Profit:", r"Open Positions"]
        for j in range(data_start_line, data_end_line):
            if any(re.match(r"^(?:,*?)\s*" + pattern, lines[j].strip()) for pattern in summary_start_patterns): data_end_line = j; break
        section_lines = [line.strip() for line in lines[data_start_line:data_end_line] if line.strip() and ',' in line]
        if not section_lines: continue
        try:
            df = pd.read_csv(io.StringIO("\n".join(section_lines)), header=None, names=expected_columns_map[section_name], skipinitialspace=True, dtype=str)
            extracted_data[section_name.lower()] = df.dropna(how='all')
        except Exception as e: print(f"Error parsing {section_name} section: {e}")

    # --- 4. การคำนวณจาก Deals ---
    deals_df = extracted_data.get('deals', pd.DataFrame())
    if not deals_df.empty:
        deals_df_copy = deals_df.copy()
        for col in ['Profit_Deal', 'Balance_Deal']: deals_df_copy[col] = pd.to_numeric(deals_df_copy[col].astype(str).str.replace(' ', '').str.replace('–', '-').replace('—', '-'), errors='coerce').fillna(0)
        
        extracted_data['results_summary']['Total_Net_Profit'] = deals_df_copy[deals_df_copy['Type_Deal'].str.lower().isin(['buy', 'sell'])]['Profit_Deal'].sum()
        
        # ### แก้ไข: ใช้ "กฎ" การอ่าน Comment ในการคำนวณยอดรวม D/W ###
        calculated_deposit = 0.0
        calculated_withdrawal = 0.0
        itemized_deposit_withdrawal_logs = []
        balance_deals = deals_df_copy[deals_df_copy['Type_Deal'].str.lower() == 'balance'].copy()
        for _, row in balance_deals.iterrows():
            comment = str(row.get('Comment_Deal', '')).lower()
            profit_val = row['Profit_Deal']
            transaction_type = 'Unknown'
            # ใช้กฎ D/W ที่เราสรุปกัน
            if 'w' in comment or 'withdraw' in comment:
                transaction_type = 'Withdrawal'
                calculated_withdrawal += profit_val
            elif 'd' in comment or 'deposit' in comment or 'create' in comment:
                transaction_type = 'Deposit'
                calculated_deposit += profit_val
            
            if transaction_type != 'Unknown':
                itemized_deposit_withdrawal_logs.append({
                    "TransactionID": str(row.get('Deal_ID', '')), 
                    "DateTime": str(row.get('Time_Deal', '')), 
                    "Type": transaction_type, 
                    "Amount": profit_val, 
                    "Comment": row.get('Comment_Deal', '')
                })
        extracted_data['balance_summary']['Deposit'] = calculated_deposit
        extracted_data['balance_summary']['Withdrawal'] = calculated_withdrawal

        # --- จุดที่แก้ไข ---
        # แปลง list of dictionaries ให้เป็น DataFrame ที่ถูกต้องก่อนส่งต่อ
        if itemized_deposit_withdrawal_logs:
            # ถ้ามีข้อมูล ให้สร้าง DataFrame จาก list นั้น
            extracted_data['deposit_withdrawal_logs'] = itemized_deposit_withdrawal_logs
        else:
            # ถ้าไม่มีข้อมูล ก็ให้เป็น DataFrame ที่ว่างเปล่า
            extracted_data['deposit_withdrawal_logs'] = pd.DataFrame()

    # --- 5. การตัดสินใจสุดท้าย (FINAL DECISION LOGIC) ---
    if has_open_positions_flag:
        pass 
    else:
        if extracted_data['balance_summary'].get('Balance') is None and 'deals' in extracted_data and not extracted_data['deals'].empty:
            extracted_data['balance_summary']['Balance'] = deals_df_copy['Balance_Deal'].iloc[-1]
        if 'Balance' in extracted_data['balance_summary']:
             extracted_data['balance_summary']['Equity'] = extracted_data['balance_summary']['Balance']

    # --- 6. ประกอบร่างสุดท้าย (โค้ดที่แก้ไขสมบูรณ์แล้ว) ---
    final_summary_data = {h: 0.0 for h in settings.WORKSHEET_HEADERS[settings.WORKSHEET_STATEMENT_SUMMARIES]}
    final_summary_data['PortfolioID'] = extracted_data['portfolio_details'].get('account_id', '')
    final_summary_data['PortfolioName'] = extracted_data['portfolio_details'].get('account_name', '')
    
    combined_summary = {**extracted_data['balance_summary'], **extracted_data['results_summary']}
    
    for key, value in combined_summary.items():
        if key in final_summary_data: 
            final_summary_data[key] = value
        elif key == 'Total_Net_Profit_Text' and 'Total_Net_Profit' not in final_summary_data: 
            final_summary_data['Total_Net_Profit'] = value
    
    # ===================================================================
    # ===== บรรทัดแก้ไขที่สำคัญที่สุด: บังคับให้ใส่ค่า Balance และ Equity =====
    # ===================================================================
    if 'Balance' in extracted_data['balance_summary']:
        final_summary_data['Balance'] = extracted_data['balance_summary']['Balance']
    if 'Equity' in extracted_data['balance_summary']:
        final_summary_data['Equity'] = extracted_data['balance_summary']['Equity']
    # ===================================================================

    extracted_data['final_summary_data'] = final_summary_data
    
    return extracted_data