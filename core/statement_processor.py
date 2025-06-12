# core/statement_processor.py

import pandas as pd
import numpy as np
import io
import re # Import regular expression module
from config import settings # Import settings for header definitions and parsing templates

def extract_data_from_report_content(file_content_input):
    """
    Parses raw byte or string content from a statement report file into structured data.
    This version includes a more robust way to handle 'balance' type rows within the 'Deals' section
    and improved number parsing for summary data.
    Corresponds to extract_data_from_report_content_sec6 in main (1).py.
    """
    extracted_data = {'deals': pd.DataFrame(), 'orders': pd.DataFrame(), 'positions': pd.DataFrame(), 'balance_summary': {}, 'results_summary': {}}

    def safe_float_convert(value_str):
        """
        Helper function to safely convert a string value to float, handling various formats.
        Improved to use regex to extract numbers robustly.
        """
        if isinstance(value_str, (int, float)):
            return value_str
        try:
            # Enhanced regex:
            # - Handles optional currency symbols ($ or similar) or other non-numeric chars before/after number.
            # - Handles optional thousands comma.
            # - Handles optional decimal point.
            # - This specifically targets the number part, not the whole string.
            # Example: "4.00 USD" -> "4.00", "4,708.56" -> "4708.56", "-100.50" -> "-100.50"
            match = re.search(r"[-+]?\s*\d{1,3}(?:[,\s]?\d{3})*(?:\.\d+)?", str(value_str))
            if match:
                clean_value = match.group(0).strip().replace(",", "").replace(" ", "") # Remove spaces and commas
                return float(clean_value)
            return None # Return None if no valid number pattern is found
        except (ValueError, TypeError, AttributeError):
            return None

    lines = []
    if isinstance(file_content_input, str):
        lines = file_content_input.strip().split('\n')
    elif isinstance(file_content_input, bytes):
        lines = file_content_input.decode('utf-8', errors='replace').strip().split('\n')
    else:
        return extracted_data

    if not lines: return extracted_data

    section_raw_headers = settings.SECTION_RAW_HEADERS_STATEMENT_PARSING
    expected_cleaned_columns = settings.EXPECTED_CLEANED_COLUMNS_STATEMENT_PARSING
    section_order = ["Positions", "Orders", "Deals"]

    section_indices = {}
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        for section_name, header_template in section_raw_headers.items():
            first_col_of_template = header_template.split(',')[0].strip()
            if section_name not in section_indices and stripped_line.startswith(first_col_of_template) and header_template in stripped_line:
                section_indices[section_name] = i; break

    for i, section_name in enumerate(section_order):
        section_key_lower = section_name.lower()
        if section_name in section_indices:
            header_line_num = section_indices[section_name]
            data_start_line_num = header_line_num + 1
            data_end_line_num = len(lines)

            for next_table_name_idx in range(i + 1, len(section_order)):
                next_table_section_name = section_order[next_table_name_idx]
                if next_table_section_name in section_indices: data_end_line_num = section_indices[next_table_section_name]; break
            
            current_table_data_lines = []
            for line_num_for_data in range(data_start_line_num, data_end_line_num):
                line_content_for_data = lines[line_num_for_data].strip()
                if not line_content_for_data:
                    if any(current_table_data_lines): pass
                    else: continue

                if line_content_for_data.startswith(("Balance:", "Credit Facility:", "Floating P/L:", "Equity:", "Results", "Total Net Profit:")): break
                
                is_another_header_line = False
                for other_sec_name, other_raw_hdr_template in section_raw_headers.items():
                    if other_sec_name != section_name and line_content_for_data.startswith(other_raw_hdr_template.split(',')[0]) and other_raw_hdr_template in line_content_for_data:
                        is_another_header_line = True; break
                if is_another_header_line: break

                if section_name == "Deals":
                    cols_in_line = [col.strip() for col in line_content_for_data.split(',')]; is_balance_type_row = False
                    if len(cols_in_line) > 3 and str(cols_in_line[3]).lower() in ['balance', 'credit', 'initial_deposit', 'deposit', 'withdrawal', 'correction']: is_balance_type_row = True
                    
                    missing_essential_identifiers = False
                    if len(cols_in_line) < 3: missing_essential_identifiers = True
                    elif not cols_in_line[0] or not cols_in_line[1] or not cols_in_line[2]: missing_essential_identifiers = True
                    
                    # Also check if the line looks like a summary line which may be mixed in
                    if line_content_for_data.startswith(("Balance:", "Equity:", "Free Margin:", "Margin:")):
                        is_balance_type_row = True # Treat as summary line within deals section if it starts with these
                    
                    if is_balance_type_row or missing_essential_identifiers: continue
                
                current_table_data_lines.append(line_content_for_data)

            if current_table_data_lines:
                csv_data_str = "\n".join(current_table_data_lines)
                try:
                    col_names_for_df = expected_cleaned_columns[section_name]; df_section = pd.read_csv(io.StringIO(csv_data_str), header=None, names=col_names_for_df, skipinitialspace=True, on_bad_lines='warn', engine='python', dtype=str)
                    df_section.dropna(how='all', inplace=True); final_cols = expected_cleaned_columns[section_name]
                    for col in final_cols:
                        if col not in df_section.columns: df_section[col] = ""
                    df_section = df_section[final_cols]
                    
                    if section_name == "Deals" and not df_section.empty and "Symbol_Deal" in df_section.columns: df_section = df_section[df_section["Symbol_Deal"].astype(str).str.strip() != ""]
                    
                    if not df_section.empty: extracted_data[section_key_lower] = df_section
                except Exception as e_parse_section:
                    print(f"Error parsing section '{section_name}': {e_parse_section}")

    # Parse Balance and Results Summary (based on main (1).py logic)
    balance_summary_dict = {}; balance_start_line_idx = -1
    for i, line in enumerate(lines):
        # Look for "Balance:" specifically to start the summary section
        if line.strip().lower().startswith("balance:"): balance_start_line_idx = i; break
    
    if balance_start_line_idx != -1:
        # Loop through lines after "Balance:" to capture summary data
        # Increase the range to ensure all summary lines are captured if the structure varies slightly
        for i_bal in range(balance_start_line_idx, min(balance_start_line_idx + 15, len(lines))): # Increased range to 15 lines
            line_stripped = lines[i_bal].strip()
            if not line_stripped : continue
            
            # Stop if "Results" section starts, and it's not the very first line of the summary block itself
            if line_stripped.startswith(("Results", "Total Net Profit:")) and i_bal > balance_start_line_idx + 1: # Added +1 to ensure it processes the "Balance:" and "Equity:" lines
                break 
            
            parts_raw = line_stripped.split(',')
            
            # --- Extract Balance and Equity directly if line starts with them ---
            if line_stripped.lower().startswith("balance:"):
                # Take the part after "Balance:" and try to convert it.
                # Example: "Balance: 4,708.56 USD" -> "4,708.56 USD" -> 4708.56
                balance_value_part = line_stripped[len("Balance:"):].strip()
                val_from_parts = safe_float_convert(balance_value_part)
                if val_from_parts is not None: balance_summary_dict['balance'] = val_from_parts
            elif line_stripped.lower().startswith("equity:"):
                equity_value_part = line_stripped[len("Equity:"):].strip()
                val_from_parts = safe_float_convert(equity_value_part)
                if val_from_parts is not None: balance_summary_dict['equity'] = val_from_parts
            
            # --- Generic key-value pair parsing for other balance summary items ---
            temp_key = ""; val_expected_next = False
            for part_val in parts_raw:
                part_val_clean = part_val.strip()
                if not part_val_clean: continue
                if ':' in part_val_clean:
                    key_str, val_str = part_val_clean.split(':', 1)
                    key_clean = key_str.strip().replace(" ", "_").replace(".", "").replace("/","_").lower()
                    val_strip = val_str.strip()
                    
                    if val_strip:
                        num_val = safe_float_convert(val_strip) # Pass the full stripped value to safe_float_convert
                        if num_val is not None and (key_clean not in balance_summary_dict or balance_summary_dict[key_clean] is None): balance_summary_dict[key_clean] = num_val
                        val_expected_next = False; temp_key = ""
                    else: # If value part is empty, expect it in next cell
                        temp_key = key_clean; val_expected_next = True
                elif val_expected_next and temp_key: # Value for a previously found key
                    num_val = safe_float_convert(part_val_clean) # Pass the full cleaned part to safe_float_convert
                    if num_val is not None and (temp_key not in balance_summary_dict or balance_summary_dict[temp_key] is None): balance_summary_dict[temp_key] = num_val
                    temp_key = ""; val_expected_next = False
    
    essential_balance_keys = ["balance", "equity", "free_margin", "margin", "floating_p_l", "margin_level", "credit_facility"]
    for k_b in essential_balance_keys:
        if k_b not in balance_summary_dict: balance_summary_dict[k_b] = None
    extracted_data['balance_summary'] = balance_summary_dict

    results_summary_dict = {}; 
    stat_definitions_map = {
        "Total Net Profit": "Total_Net_Profit", "Gross Profit": "Gross_Profit", "Gross Loss": "Gross_Loss", "Profit Factor": "Profit_Factor", 
        "Expected Payoff": "Expected_Payoff", "Recovery Factor": "Recovery_Factor", "Sharpe Ratio": "Sharpe_Ratio", 
        "Balance Drawdown Absolute": "Balance_Drawdown_Absolute", "Balance Drawdown Maximal": "Balance_Drawdown_Maximal", 
        "Balance Drawdown Relative": "Balance_Drawdown_Relative_Percent", # This maps to %
        "Total Trades": "Total_Trades", "Short Trades (won %)": "Short_Trades", 
        "Long Trades (won %)": "Long_Trades", "Profit Trades (% of total)": "Profit_Trades", 
        "Loss Trades (% of total)": "Loss_Trades", "Largest profit trade": "Largest_profit_trade", 
        "Largest loss trade": "Largest_loss_trade", "Average profit trade": "Average_profit_trade", 
        "Average loss trade": "Average_loss_trade", 
        "Maximum consecutive wins (count)": "Maximum_consecutive_wins_Count", # Added count explicitly
        "Maximum consecutive wins ($)": "Maximum_consecutive_wins_Profit", 
        "Maximal consecutive profit (count)": "Maximal_consecutive_profit_Count", # Added count explicitly
        "Average consecutive wins": "Average_consecutive_wins", 
        "Maximum consecutive losses (count)": "Maximum_consecutive_losses_Count", # Added count explicitly
        "Maximum consecutive losses ($)": "Maximum_consecutive_losses_Profit", 
        "Maximal consecutive loss (count)": "Maximal_consecutive_loss_Count", # Added count explicitly
        "Average consecutive losses": "Average_consecutive_losses"
    }

    results_start_line_idx = -1; results_section_processed_lines = 0; max_lines_for_results = 35
    for i_res, line_res in enumerate(lines):
        if results_start_line_idx == -1 and (line_res.strip().startswith("Results") or line_res.strip().startswith("Total Net Profit:")):
            results_start_line_idx = i_res
            if line_res.strip().startswith("Total Net Profit:"): results_start_line_idx -=1
            continue
        
        if results_start_line_idx != -1 and results_section_processed_lines < max_lines_for_results:
            line_stripped_res = line_res.strip()
            if not line_stripped_res:
                if results_section_processed_lines > 2: break
                else: continue
            
            results_section_processed_lines += 1; row_cells = [cell.strip() for cell in line_stripped_res.split(',')]
            for c_idx, cell_content in enumerate(row_cells):
                if not cell_content: continue
                current_label = cell_content.replace(':', '').strip()
                if current_label in stat_definitions_map:
                    gsheet_key = stat_definitions_map[current_label]
                    for k_val_search in range(1, 5):
                        if (c_idx + k_val_search) < len(row_cells):
                            raw_value_from_cell = row_cells[c_idx + k_val_search]
                            if raw_value_from_cell:
                                value_part_before_paren = raw_value_from_cell.split('(')[0].strip()
                                numeric_value = safe_float_convert(value_part_before_paren)
                                if numeric_value is not None:
                                    results_summary_dict[gsheet_key] = numeric_value
                                    if '(' in raw_value_from_cell and ')' in raw_value_from_cell:
                                        try:
                                            paren_content_str = raw_value_from_cell[raw_value_from_cell.find('(')+1:raw_value_from_cell.find(')')].strip().replace('%','')
                                            paren_numeric_value = safe_float_convert(paren_content_str)
                                            if paren_numeric_value is not None:
                                                if current_label == "Balance Drawdown Maximal": 
                                                    results_summary_dict["Balance_Drawdown_Maximal_Percent"] = paren_numeric_value
                                                    # Added for "Balance Drawdown Relative Amount" - it was missing a dedicated line.
                                                    if "Balance_Drawdown_Relative_Amount" not in results_summary_dict and "Balance Drawdown Relative" in stat_definitions_map:
                                                        # Look for "Balance Drawdown Relative" in the same line or nearby.
                                                        # This is a heuristic to try to catch it if it's placed differently.
                                                        # The previous code assigned the *numeric_value* of "Balance Drawdown Relative"
                                                        # to "Balance_Drawdown_Relative_Percent" and the *paren_numeric_value* to "Balance_Drawdown_Relative_Amount"
                                                        # This logic needs to be precise.
                                                        # Based on original main(1).py: Balance Drawdown Relative (e.g. -10.00 (0.10%))
                                                        # It assigns the value to 'Balance_Drawdown_Relative_Percent' and the (paren)value to 'Balance_Drawdown_Relative_Amount'.
                                                        # My map 'Balance Drawdown Relative' -> 'Balance_Drawdown_Relative_Percent' is correct for the primary value.
                                                        # For the (Amount) part:
                                                        if current_label == "Balance Drawdown Relative":
                                                            if paren_numeric_value is not None: # This is the percentage part
                                                                results_summary_dict["Balance_Drawdown_Relative_Amount"] = numeric_value # The main numeric value is the amount here.
                                                                results_summary_dict["Balance_Drawdown_Relative_Percent"] = paren_numeric_value
                                                
                                                elif current_label == "Short Trades (won %)": results_summary_dict["Short_Trades_won_Percent"] = paren_numeric_value
                                                elif current_label == "Long Trades (won %)": results_summary_dict["Long_Trades_won_Percent"] = paren_numeric_value
                                                elif current_label == "Profit Trades (% of total)": results_summary_dict["Profit_Trades_Percent_of_total"] = paren_numeric_value
                                                elif current_label == "Loss Trades (% of total)": results_summary_dict["Loss_Trades_Percent_of_total"] = paren_numeric_value
                                                elif current_label == "Largest profit trade": results_summary_dict["Largest_profit_trade"] = paren_numeric_value
                                                elif current_label == "Largest loss trade": results_summary_dict["Largest_loss_trade"] = paren_numeric_value
                                                elif current_label == "Average profit trade": results_summary_dict["Average_profit_trade"] = paren_numeric_value
                                                elif current_label == "Average loss trade": results_summary_dict["Average_loss_trade"] = paren_numeric_value
                                                elif current_label == "Maximum consecutive wins ($)": results_summary_dict["Maximum_consecutive_wins_Profit"] = paren_numeric_value
                                                elif current_label == "Maximal consecutive profit (count)": results_summary_dict["Maximal_consecutive_profit_Count"] = paren_numeric_value
                                                elif current_label == "Average consecutive wins": results_summary_dict["Average_consecutive_wins"] = paren_numeric_value
                                                elif current_label == "Maximum consecutive losses ($)": results_summary_dict["Maximum_consecutive_losses_Profit"] = paren_numeric_value
                                                elif current_label == "Maximal consecutive loss (count)": results_summary_dict["Maximal_consecutive_loss_Count"] = paren_numeric_value
                                        except Exception as e_paren_parse:
                                            print(f"Warning: Error parsing paren value for '{current_label}': {e_paren_parse}")
                                break
            if line_stripped_res.startswith("Average consecutive losses"): break
        elif results_start_line_idx != -1 and results_section_processed_lines >= max_lines_for_results: break
    extracted_data['results_summary'] = results_summary_dict

    return extracted_data