# core/statement_processor.py (ฉบับแก้ไขสมบูรณ์และพร้อมใช้งาน)

import pandas as pd
import io
import re
from datetime import datetime
from config import settings
import numpy as np
import pytz
import uuid # เพิ่ม import uuid ตรงนี้

# --- NEW: Helper function to ensure datetime is timezone-aware and in UTC ---
def _ensure_utc_datetime(series: pd.Series) -> pd.Series:
    """
    Ensures a pandas Series of datetime objects is timezone-aware (UTC)
    for consistent comparisons.
    """
    if not pd.api.types.is_datetime64_any_dtype(series):
        series = pd.to_datetime(series, errors='coerce')

    series = series.dropna()

    if series.empty:
        return series

    if series.dt.tz is None:
        return series.dt.tz_localize(pytz.utc)
    elif series.dt.tz != pytz.utc:
        return series.dt.tz_convert(pytz.utc)
    return series

def extract_data_from_report_content(file_content_input: bytes):
    """
    Extracts data from a trading statement report content (CSV format).
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
        # Decode as utf-8-sig to handle BOM (Byte Order Mark) if present
        lines = file_content_input.strip().split('\n')
    elif isinstance(file_content_input, bytes):
        lines = file_content_input.decode('utf-8-sig', errors='replace').strip().split('\n')
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

    # These parse_summary_line_item and parse_results_section_line are currently unused
    def parse_summary_line_item(line, key_word): 
        match = re.search(r"Average consecutive wins:,\s*([-\s\d\.]+)(?:,*\s*)Average consecutive losses:,\s*([-\s\d\.]+)", line) 
        if match:
            val1 = clean_and_float(match.group(1))
            val2 = clean_and_float(match.group(2))
            return val1, val2
        return None, None

    def parse_results_section_line(line): 
        data = {}
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
            "Short Trades \(won %\):": r"Short Trades \(won %\):,,,\s*(\d+)\s*\(([-+]?\d*\.?\d+)%\)",
            "Long Trades \(won %\):": r"Long Trades \(won %\):,,,\s*(\d+)\s*\(([-+]?\d*\.?\d+)%\)",
            "Profit Trades \(% of total\):": r"Profit Trades \(% of total\):,,,\s*(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\)",
            "Loss Trades \(% of total\):": r"Loss Trades \(% of total\):,,,\s*(\d+)\s*\(([-+]?\s*\d*\.?\d+)%\)",
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
        
        for key_prefix, pattern_str in patterns.items():
            match = re.search(pattern_str, line)
            if match:
                if len(match.groups()) == 2:
                    val1 = match.group(1)
                    val2 = match.group(2)
                    if key_prefix == "Balance Drawdown Maximal":
                        data['Maximal_Drawdown_Value'] = clean_and_float(val1)
                        data['Maximal_Drawdown_Percent'] = clean_and_float(val2)
                    elif key_prefix == "Balance Drawdown Relative":
                        data['Balance_Drawdown_Relative_Percent'] = clean_and_float(val1)
                        data['Balance_Drawdown_Relative_Value'] = clean_and_float(val2)
                    elif key_prefix == "Maximum consecutive wins": 
                        data['Max_Consecutive_Wins_Count'] = int(clean_and_float(val1))
                        data['Max_Consecutive_Wins_Profit'] = clean_and_float(val2)
                    elif key_prefix == "Maximum consecutive losses": 
                        data['Max_Consecutive_Losses_Count'] = int(clean_and_float(val1))
                        data['Max_Consecutive_Losses_Profit'] = clean_and_float(val2)
                    elif key_prefix == "Maximal consecutive profit": 
                        data['Maximal_Consecutive_Profit_Value'] = clean_and_float(val1)
                        data['Maximal_Consecutive_Profit_Count'] = int(clean_and_float(val2))
                    elif key_prefix == "Maximal consecutive loss": 
                        data['Maximal_Consecutive_Loss_Value'] = clean_and_float(val1)
                        data['Maximal_Consecutive_Loss_Count'] = int(clean_and_float(val2))
                else: 
                    if key_prefix == "Total Trades":
                        data[key_prefix] = int(clean_and_float(match.group(1)))
                    elif key_prefix in ["Average consecutive wins", "Average consecutive losses"]:
                        data[key_prefix] = int(clean_and_float(match.group(1))) 
                    else:
                        data[key_prefix] = clean_and_float(match.group(1))
                break 
        return data

    has_open_positions_flag = False

    for line in lines:
        line_stripped = line.strip()
        
        if "Open Positions" in line_stripped and len(line_stripped) < 30:
            has_open_positions_flag = True

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
        
        if "Balance:" in line_stripped:
            match = re.search(r"Balance:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match: balance_summary_parsed_from_text['Balance'] = clean_and_float(match.group(1))
        
        if "Equity:" in line_stripped:
            match = re.search(r"Equity:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match: balance_summary_parsed_from_text['Equity'] = clean_and_float(match.group(1))

        if "Floating P/L:" in line_stripped:
            match = re.search(r"Floating P/L:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if match: balance_summary_parsed_from_text['Floating_P_L'] = clean_and_float(match.group(1))
        
        if "Credit Facility:" in line_stripped:
            val_match = re.search(r"Credit Facility:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if val_match: balance_summary_parsed_from_text['Credit_Facility'] = clean_and_float(val_match.group(1))
        
        if "Total Net Profit:" in line_stripped and "Gross Profit:" in line_stripped and "Gross Loss:" in line_stripped:
            match = re.search(r"Total Net Profit:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Gross Profit:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*),*?Gross Loss:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
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
            val_match = re.search(r"Balance Drawdown Absolute:,(?:,*?)([-+]?\s*\d[\d\s\.,-]*)", line_stripped)
            if val_match: results_summary_parsed_from_text['Balance_Drawdown_Absolute'] = clean_and_float(val_match.group(1))
        
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
                results_summary_parsed_from_text['Average_Consecutive_Wins'] = int(clean_and_float(match.group(1)))
                results_summary_parsed_from_text['Average_Consecutive_Losses'] = int(clean_and_float(match.group(2)))

    extracted_data['portfolio_details'] = portfolio_details
    extracted_data['balance_summary'].update(balance_summary_parsed_from_text) 
    extracted_data['results_summary'].update(results_summary_parsed_from_text)

    # --- 2 & 3: การหาและดึงข้อมูลตาราง ---
    section_headers_map = settings.SECTION_RAW_HEADERS_STATEMENT_PARSING
    expected_columns_map_from_settings = {
        "Positions": settings.WORKSHEET_HEADERS[settings.SUPABASE_TABLE_ACTUAL_POSITIONS],
        "Orders": settings.WORKSHEET_HEADERS[settings.SUPABASE_TABLE_ACTUAL_ORDERS],
        "Deals": settings.WORKSHEET_HEADERS[settings.SUPABASE_TABLE_ACTUAL_TRADES]
    }

    section_order = ["Positions", "Orders", "Deals"]
    header_indices = {name: -1 for name in section_order}

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        for name, header_text in section_headers_map.items():
            pattern = r'^' + re.escape(header_text).replace(r'\ ', r'\s*').replace(r'\,', ',') + r'\s*,*$' # เพิ่ม r'\s*,*$'
            if re.match(pattern, line_stripped):
                header_indices[name] = i
                break

    for i, section_name in enumerate(section_order):
        start_index = header_indices[section_name]
        if start_index == -1:
            continue

        data_start_line, data_end_line = start_index + 1, len(lines)
        
        for j, line_content in enumerate(lines[data_start_line:], start=data_start_line):
            line_stripped = line_content.strip()
            
            found_next_header = False
            for next_section_name in section_order[i+1:]:
                next_header_text = section_headers_map[next_section_name]
                next_pattern = r'^' + re.escape(next_header_text).replace(r'\ ', r'\s*').replace(r'\,', ',') + r'\s*,*$' # เพิ่ม r'\s*,*$'
                if re.match(next_pattern, line_stripped):
                    data_end_line = j
                    found_next_header = True
                    break
            if found_next_header:
                break
            
            summary_start_patterns_full = [
                r"^Balance:", r"^Credit Facility:", r"^Total Net Profit:", 
                r"^Open Positions", r"^Results"
            ]
            if any(re.match(pattern, line_stripped) for pattern in summary_start_patterns_full):
                data_end_line = j
                break
            
            if not line_stripped or re.fullmatch(r",*", line_stripped):
                if j + 1 < len(lines):
                    next_line_stripped = lines[j+1].strip()
                    if not next_line_stripped or re.fullmatch(r",*", next_line_stripped):
                        data_end_line = j
                        break

        section_lines = [line.strip() for line in lines[data_start_line:data_end_line] if line.strip() and ',' in line]
        
        if not section_lines:
            extracted_data[section_name.lower()] = pd.DataFrame(columns=expected_columns_map_from_settings[section_name])
            continue
        
        try:
            raw_header_line = lines[start_index].strip()
            
            df_parsed_raw = pd.read_csv(io.StringIO("\n".join([raw_header_line] + section_lines)), 
                                        header=0, 
                                        skipinitialspace=True, 
                                        dtype=str)
            
            column_rename_map = {}
            target_cols_settings = expected_columns_map_from_settings[section_name]
            
            temp_io = io.StringIO(section_headers_map[section_name])
            temp_df_for_pandas_headers = pd.read_csv(temp_io, nrows=0, skipinitialspace=True, dtype=str)
            pandas_inferred_headers_from_template = list(temp_df_for_pandas_headers.columns)

            for i, inferred_col in enumerate(pandas_inferred_headers_from_template):
                if i < len(target_cols_settings):
                    column_rename_map[inferred_col] = target_cols_settings[i]
                
            df_final = df_parsed_raw.rename(columns=column_rename_map)

            df_final = df_final.reindex(columns=expected_columns_map_from_settings[section_name])
            
            if not df_final.empty:
                if 'id' in df_final.columns:
                    df_final.drop(columns=['id'], inplace=True, errors='ignore')

                if section_name == "Deals":
                    for col in ['Volume_Deal', 'Price_Deal', 'Commission_Deal', 'Fee_Deal', 'Swap_Deal', 'Profit_Deal', 'Balance_Deal']:
                        if col in df_final.columns:
                            df_final[col] = pd.to_numeric(df_final[col].astype(str).str.replace(' ', '').str.replace(',', '').str.replace('–', '-').str.replace('—', '-'), errors='coerce').fillna(0)
                    
                    if 'Deal_ID' in df_final.columns:
                        df_final['Deal_ID'] = df_final['Deal_ID'].astype(str).replace('nan', '').apply(
                            lambda x: x if x.strip() else str(uuid.uuid4())
                        )

                    if 'Time_Deal' in df_final.columns:
                        df_final['Time_Deal'] = pd.to_datetime(df_final['Time_Deal'], format="%Y.%m.%d %H:%M:%S", errors='coerce')
                        df_final['Time_Deal'] = df_final['Time_Deal'].fillna(pd.to_datetime(df_final['Time_Deal'].astype(str), errors='coerce'))
                        df_final['Time_Deal'] = _ensure_utc_datetime(df_final['Time_Deal'])

                elif section_name == "Orders":
                    for col in ['Price_Ord', 'S_L_Ord', 'T_P_Ord']: 
                        if col in df_final.columns:
                            df_final[col] = pd.to_numeric(df_final[col].astype(str).str.replace(' ', '').str.replace(',', '').str.replace('–', '-').str.replace('—', '-'), errors='coerce').fillna(0)
                    
                    if 'Volume_Ord_Raw' in df_final.columns:
                        df_final['Volume_Ord'] = df_final['Volume_Ord_Raw'].astype(str).apply(
                            lambda x: pd.to_numeric(x.split(' ')[0], errors='coerce') if ' ' in x else pd.to_numeric(x, errors='coerce')
                        ).fillna(0.0) 
                        df_final.drop(columns=['Volume_Ord_Raw'], inplace=True, errors='ignore')
                    else: 
                        df_final['Volume_Ord'] = 0.0

                    if 'Order_ID_Ord' in df_final.columns:
                        df_final['Order_ID_Ord'] = df_final['Order_ID_Ord'].astype(str).replace('nan', '').apply(
                            lambda x: x if x.strip() else str(uuid.uuid4())
                        )

                    for col in ['Open_Time_Ord', 'Close_Time_Ord']:
                        if col in df_final.columns:
                            df_final[col] = pd.to_datetime(df_final[col], format="%Y.%m.%d %H:%M:%S", errors='coerce')
                            df_final[col] = df_final[col].fillna(pd.to_datetime(df_final[col].astype(str), errors='coerce')) 
                            df_final[col] = _ensure_utc_datetime(df_final[col])
                    
                    df_final.drop(columns=['Filler_Ord_1', 'Filler_Ord_2'], inplace=True, errors='ignore')

                elif section_name == "Positions":
                    for col in ['Volume_Pos', 'Price_Open_Pos', 'S_L_Pos', 'T_P_Pos', 'Price_Close_Pos', 'Commission_Pos', 'Swap_Pos', 'Profit_Pos']:
                        if col in df_final.columns:
                            df_final[col] = pd.to_numeric(df_final[col].astype(str).str.replace(' ', '').str.replace(',', '').str.replace('–', '-').str.replace('—', '-'), errors='coerce').fillna(0)
                    
                    if 'Position_ID' in df_final.columns:
                        df_final['Position_ID'] = df_final['Position_ID'].astype(str).replace('nan', '').apply(
                            lambda x: x if x.strip() else str(uuid.uuid4())
                        )

                    if 'Time_Pos' in df_final.columns:
                        df_final['Time_Pos'] = pd.to_datetime(df_final['Time_Pos'], format="%Y.%m.%d %H:%M:%S", errors='coerce')
                        df_final['Time_Pos'] = df_final['Time_Pos'].fillna(pd.to_datetime(df_final['Time_Pos'].astype(str), errors='coerce'))
                        df_final['Time_Pos'] = _ensure_utc_datetime(df_final['Time_Pos'])
                    
                    if 'Time_Close_Pos_Raw' in df_final.columns: 
                        df_final['Time_Close_Pos'] = pd.to_datetime(df_final['Time_Close_Pos_Raw'], format="%Y.%m.%d %H:%M:%S", errors='coerce')
                        df_final['Time_Close_Pos'] = df_final['Time_Close_Pos'].fillna(pd.to_datetime(df_final['Time_Close_Pos_Raw'].astype(str), errors='coerce')) 
                        df_final['Time_Close_Pos'] = _ensure_utc_datetime(df_final['Time_Close_Pos'])
                        df_final.drop(columns=['Time_Close_Pos_Raw'], inplace=True, errors='ignore')
                    else: 
                        df_final['Time_Close_Pos'] = pd.NaT 

                extracted_data[section_name.lower()] = df_final.dropna(how='all')

            else:
                extracted_data[section_name.lower()] = pd.DataFrame(columns=expected_columns_map_from_settings[section_name])

        except Exception as e: 
            print(f"Error parsing {section_name} section: {e}")
            extracted_data[section_name.lower()] = pd.DataFrame(columns=expected_columns_map_from_settings[section_name])

    deals_df_processed = extracted_data.get('deals', pd.DataFrame()) 

    if not deals_df_processed.empty:
        extracted_data['results_summary']['Total_Net_Profit'] = deals_df_processed[deals_df_processed['Type_Deal'].str.lower().isin(['buy', 'sell'])]['Profit_Deal'].sum()
        
        calculated_deposit = 0.0
        calculated_withdrawal = 0.0
        itemized_deposit_withdrawal_logs = []
        balance_deals = deals_df_processed[deals_df_processed['Type_Deal'].str.lower() == 'balance'].copy()
        
        for _, row in balance_deals.iterrows():
            comment = str(row.get('Comment_Deal', '')).lower()
            profit_val = pd.to_numeric(row['Profit_Deal'], errors='coerce')
            if pd.isna(profit_val):
                profit_val = 0.0
            transaction_type = 'Unknown'
            
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

        if itemized_deposit_withdrawal_logs:
            dw_df_raw = pd.DataFrame(itemized_deposit_withdrawal_logs)
            if 'DateTime' in dw_df_raw.columns:
                dw_df_raw['DateTime'] = pd.to_datetime(dw_df_raw['DateTime'], format="%Y.%m.%d %H:%M:%S", errors='coerce')
                dw_df_raw['DateTime'] = dw_df_raw['DateTime'].fillna(pd.to_datetime(dw_df_raw['DateTime'].astype(str), errors='coerce'))
                dw_df_raw['DateTime'] = _ensure_utc_datetime(dw_df_raw['DateTime'])
            
            if 'Amount' in dw_df_raw.columns:
                dw_df_raw['Amount'] = pd.to_numeric(dw_df_raw['Amount'], errors='coerce').fillna(0)
            
            if 'id' in dw_df_raw.columns:
                dw_df_raw.drop(columns=['id'], inplace=True, errors='ignore')

            extracted_data['deposit_withdrawal_logs'] = dw_df_raw
        else:
            extracted_data['deposit_withdrawal_logs'] = pd.DataFrame(columns=settings.WORKSHEET_HEADERS[settings.SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS])

    if not has_open_positions_flag:
        current_deals_df = extracted_data.get('deals', pd.DataFrame())
        if extracted_data['balance_summary'].get('Balance') is None and not current_deals_df.empty:
            extracted_data['balance_summary']['Balance'] = current_deals_df['Balance_Deal'].iloc[-1]
        
        if 'Balance' in extracted_data['balance_summary'] and extracted_data['balance_summary'].get('Equity') is None:
             extracted_data['balance_summary']['Equity'] = extracted_data['balance_summary']['Balance']
        elif 'Balance' in extracted_data['balance_summary'] and extracted_data['balance_summary'].get('Floating_P_L') is None:
             extracted_data['balance_summary']['Floating_P_L'] = 0.0

    final_summary_data = {h: 0.0 for h in settings.WORKSHEET_HEADERS[settings.SUPABASE_TABLE_STATEMENT_SUMMARIES]}
    final_summary_data['PortfolioID'] = extracted_data['portfolio_details'].get('account_id', '')
    final_summary_data['PortfolioName'] = extracted_data['portfolio_details'].get('account_name', '')
    
    combined_summary = {**extracted_data['balance_summary'], **extracted_data['results_summary']}
    
    for key, value in combined_summary.items():
        if key in final_summary_data: 
            final_summary_data[key] = value
        elif key == 'Total_Net_Profit_Text' and 'Total_Net_Profit' not in final_summary_data: 
            final_summary_data['Total_Net_Profit'] = value
    
    if 'Balance' in extracted_data['balance_summary']:
        final_summary_data['Balance'] = extracted_data['balance_summary']['Balance']
    if 'Equity' in extracted_data['balance_summary']:
        final_summary_data['Equity'] = extracted_data['balance_summary']['Equity']

    extracted_data['final_summary_data'] = final_summary_data
    
    print("\n--- DEBUG: Final extracted_data from statement_processor.py ---")
    for k, v in extracted_data.items():
        if isinstance(v, pd.DataFrame):
            print(f"  {k} (DataFrame, shape: {v.shape}):")
            print(v.head())
        elif isinstance(v, list):
            print(f"  {k} (List, len: {len(v)}):")
            print(v[:2])
        else:
            print(f"  {k} (Dict/Other): {v}")
    print("--------------------------------------------------\n")

    return extracted_data