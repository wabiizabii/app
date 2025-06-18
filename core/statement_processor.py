# core/statement_processor.py (Restored from Original Logic - Corrected)

import streamlit as st
import pandas as pd
import numpy as np
import io
import re
from config import settings

def _parse_report_history_format(lines: list):
    """
    ฟังก์ชันใหม่สำหรับประมวลผลไฟล์ ReportHistory จาก Exness โดยเฉพาะ
    """
    # สร้าง Dictionary สำหรับเก็บผลลัพธ์
    extracted_data = {'deals': pd.DataFrame(), 'orders': pd.DataFrame(), 'positions': pd.DataFrame(), 'balance_summary': {}, 'results_summary': {}}

    # 1. อ่านข้อมูลตารางหลัก (ข้าม 6 บรรทัดแรก)
    # ใช้ io.StringIO เพื่อให้ pandas อ่าน list ของ string ได้เหมือนไฟล์
    data_string = "\n".join(lines)
    try:
        # skiprows=6 คือหัวใจสำคัญของการแก้ไขนี้
        df = pd.read_csv(io.StringIO(data_string), skiprows=6)
        
        # 2. แปลงชื่อคอลัมน์ให้อยู่ในรูปแบบมาตรฐานที่แอปพลิเคชันต้องการ
        column_mapping = {
            'Ticket': 'Deal_ID', 'Open Time': 'Time_Deal', 'Type': 'Type_Deal',
            'Symbol': 'Symbol_Deal', 'Volume': 'Volume_Deal', 'Open Price': 'Price_Deal',
            'S/L': 'S_L_Deal', 'T/P': 'T_P_Deal', 'Close Time': 'Close_Time_Deal',
            'Close Price': 'Price_Close_Deal', 'Commission': 'Commission_Deal',
            'Swap': 'Swap_Deal', 'Profit': 'Profit_Deal'
        }
        df.rename(columns=column_mapping, inplace=True)

        # 3. สร้างคอลัมน์ที่จำเป็นแต่ไม่มีในไฟล์ต้นฉบับ
        # ReportHistory จะมีแค่ buy/sell ไม่มี direction แยก
        df['Direction_Deal'] = df['Type_Deal'].apply(lambda x: 'buy' if x == 'buy' else 'sell')
        
        # เพิ่มคอลัมน์ว่างอื่นๆ เพื่อให้โครงสร้างตรงกัน
        for col in ['Order_ID_Deal', 'Fee_Deal', 'Balance_Deal', 'Comment_Deal']:
            if col not in df.columns:
                df[col] = np.nan

        extracted_data['deals'] = df
    except Exception as e:
        st.warning(f"ไม่สามารถประมวลผลตารางข้อมูลในไฟล์ ReportHistory ได้: {e}")
        # แม้จะ Error ก็ยังพยายามอ่านส่วน Summary ต่อไป

    # 4. ดึงข้อมูลจากส่วนหัว (Balance, Equity)
    summary_lines = lines[:6]
    balance_summary = {}
    try:
        for line in summary_lines:
            if "Balance:" in line:
                # แยกข้อมูล Balance จากบรรทัดที่ 5
                parts = line.split()
                # Balance จะอยู่ตำแหน่งที่ 1 และ Equity อยู่ตำแหน่งที่ 3
                balance_summary['balance'] = float(parts[1].replace(',', ''))
                balance_summary['equity'] = float(parts[3].replace(',', ''))
            elif "Profit:" in line:
                 # แยกข้อมูล Floating P/L จากบรรทัดที่ 5
                parts = line.split()
                balance_summary['floating_p_l'] = float(parts[5].replace(',', ''))

        extracted_data['balance_summary'] = balance_summary
    except Exception as e:
        st.warning(f"ไม่สามารถประมวลผลข้อมูลสรุปในไฟล์ ReportHistory ได้: {e}")

    return extracted_data

# [แก้ไข] เปลี่ยนชื่อฟังก์ชันและ Parameter ให้ถูกต้อง
def extract_data_from_report_content(file_content_input: bytes):
    
    extracted_data = {'deals': pd.DataFrame(), 'orders': pd.DataFrame(), 'positions': pd.DataFrame(), 'balance_summary': {}, 'results_summary': {}}
    
    def safe_float_convert(value_str):
        if isinstance(value_str, (int, float)): return value_str
        try:
            clean_value = str(value_str).strip().replace(" ", "").replace(",", "").replace("%", "")
            if not clean_value: return None
            if clean_value.count('.') > 1:
                parts = clean_value.split('.'); integer_part = "".join(parts[:-1]); decimal_part = parts[-1]
                clean_value = integer_part + "." + decimal_part
            return float(clean_value)
        except (ValueError, TypeError, AttributeError): return None

    lines = []
    # [แก้ไข] ใช้ชื่อ Parameter ใหม่ 'file_content_input'
    if isinstance(file_content_input, str): lines = file_content_input.strip().split('\n')
    elif isinstance(file_content_input, bytes): lines = file_content_input.decode('utf-8', errors='replace').strip().split('\n')
    else: return extracted_data
    
    if not lines: return extracted_data
    
    if 'ReportHistory' in lines[0]:
        # ถ้าใช่ ให้เรียกใช้ฟังก์ชันใหม่แล้วจบการทำงาน
        return _parse_report_history_format(lines)
    
    # ส่วน Logic ที่เหลือยังคงแข็งแกร่งและทำงานได้ดีเหมือนเดิม
    section_raw_headers = {"Positions": "Time,Position,Symbol,Type,Volume,Price,S / L,T / P,Time,Price,Commission,Swap,Profit", "Orders": "Open Time,Order,Symbol,Type,Volume,Price,S / L,T / P,Time,State,,Comment", "Deals": "Time,Deal,Symbol,Type,Direction,Volume,Price,Order,Commission,Fee,Swap,Profit,Balance,Comment"}    
    expected_cleaned_columns = {"Positions": ["Time_Pos", "Position_ID", "Symbol_Pos", "Type_Pos", "Volume_Pos", "Price_Open_Pos", "S_L_Pos", "T_P_Pos", "Time_Close_Pos", "Price_Close_Pos", "Commission_Pos", "Swap_Pos", "Profit_Pos"], "Orders": ["Open_Time_Ord", "Order_ID_Ord", "Symbol_Ord", "Type_Ord", "Volume_Ord", "Price_Ord", "S_L_Ord", "T_P_Ord", "Close_Time_Ord", "State_Ord", "Filler_Ord","Comment_Ord"], "Deals": ["Time_Deal", "Deal_ID", "Symbol_Deal", "Type_Deal", "Direction_Deal", "Volume_Deal", "Price_Deal", "Order_ID_Deal", "Commission_Deal", "Fee_Deal", "Swap_Deal", "Profit_Deal", "Balance_Deal", "Comment_Deal"]}
    section_order_for_tables = ["Positions", "Orders", "Deals"]; section_header_indices = {}
    
    for line_idx, current_line_str in enumerate(lines):
        stripped_line = current_line_str.strip()
        for section_name, raw_header_template in section_raw_headers.items():
            if section_name not in section_header_indices:
                first_col_of_template = raw_header_template.split(',')[0].strip()
                if stripped_line.startswith(first_col_of_template) and raw_header_template in stripped_line: section_header_indices[section_name] = line_idx; break
    
    for table_idx, section_name in enumerate(section_order_for_tables):
        section_key_lower = section_name.lower()
        if section_name in section_header_indices:
            header_line_num = section_header_indices[section_name]; data_start_line_num = header_line_num + 1; data_end_line_num = len(lines)
            for next_table_name_idx in range(table_idx + 1, len(section_order_for_tables)):
                next_table_section_name = section_order_for_tables[next_table_name_idx]
                if next_table_section_name in section_header_indices: data_end_line_num = section_header_indices[next_table_section_name]; break
            current_table_data_lines = []
            for line_num_for_data in range(data_start_line_num, data_end_line_num):
                line_content_for_data = lines[line_num_for_data].strip()
                if not line_content_for_data:
                    if any(current_table_data_lines): pass
                    else: continue
                if line_content_for_data.startswith(("Balance:", "Credit Facility:", "Floating P/L:", "Equity:", "Results", "Total Net Profit:")): break
                is_another_header_line = False
                for other_sec_name, other_raw_hdr_template in section_raw_headers.items():
                    if other_sec_name != section_name and line_content_for_data.startswith(other_raw_hdr_template.split(',')[0]) and other_raw_hdr_template in line_content_for_data: is_another_header_line = True; break
                if is_another_header_line: break
                if section_name == "Deals":
                    cols_in_line = [col.strip() for col in line_content_for_data.split(',')]; is_balance_type_row = False
                    if len(cols_in_line) > 3 and str(cols_in_line[3]).lower() in ['balance', 'credit', 'initial_deposit', 'deposit', 'withdrawal', 'correction']: is_balance_type_row = True
                    missing_essential_identifiers = False
                    if len(cols_in_line) < 3: missing_essential_identifiers = True
                    elif not cols_in_line[0] or not cols_in_line[1] or not cols_in_line[2]: missing_essential_identifiers = True
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
                except Exception: pass

    balance_summary_dict = {}; balance_start_line_idx = -1
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("balance:"): balance_start_line_idx = i; break
    if balance_start_line_idx != -1:
        for i_bal in range(balance_start_line_idx, min(balance_start_line_idx + 8, len(lines))):
            line_stripped = lines[i_bal].strip()
            if not line_stripped : continue
            if line_stripped.startswith(("Results", "Total Net Profit:")) and i_bal > balance_start_line_idx: break
            parts_raw = line_stripped.split(',')
            if line_stripped.lower().startswith("balance:"):
                if len(parts_raw) > 3:
                    val_from_parts = safe_float_convert(parts_raw[3].strip())
                    if val_from_parts is not None: balance_summary_dict['balance'] = val_from_parts
            elif line_stripped.lower().startswith("equity:"):
                if len(parts_raw) > 3:
                    val_from_parts = safe_float_convert(parts_raw[3].strip())
                    if val_from_parts is not None: balance_summary_dict['equity'] = val_from_parts
            temp_key = ""; val_expected_next = False
            for part_val in parts_raw:
                part_val_clean = part_val.strip()
                if not part_val_clean: continue
                if ':' in part_val_clean:
                    key_str, val_str = part_val_clean.split(':', 1); key_clean = key_str.strip().replace(" ", "_").replace(".", "").replace("/","_").lower(); val_strip = val_str.strip()
                    if val_strip:
                        num_val = safe_float_convert(val_strip.split(' ')[0])
                        if num_val is not None and (key_clean not in balance_summary_dict or balance_summary_dict[key_clean] is None): balance_summary_dict[key_clean] = num_val
                        val_expected_next = False; temp_key = ""
                    else: temp_key = key_clean; val_expected_next = True
                elif val_expected_next and temp_key:
                    num_val = safe_float_convert(part_val_clean.split(' ')[0])
                    if num_val is not None and (temp_key not in balance_summary_dict or balance_summary_dict[temp_key] is None): balance_summary_dict[temp_key] = num_val
                    temp_key = ""; val_expected_next = False
    essential_balance_keys = ["balance", "equity", "free_margin", "margin", "floating_p_l", "margin_level", "credit_facility"]
    for k_b in essential_balance_keys:
        if k_b not in balance_summary_dict: balance_summary_dict[k_b] = None
    extracted_data['balance_summary'] = balance_summary_dict
    results_summary_dict = {}; stat_definitions_map = {"Total Net Profit": "Total_Net_Profit", "Gross Profit": "Gross_Profit", "Gross Loss": "Gross_Loss", "Profit Factor": "Profit_Factor", "Expected Payoff": "Expected_Payoff", "Recovery Factor": "Recovery_Factor", "Sharpe Ratio": "Sharpe_Ratio", "Balance Drawdown Absolute": "Balance_Drawdown_Absolute", "Balance Drawdown Maximal": "Balance_Drawdown_Maximal", "Balance Drawdown Relative": "Balance_Drawdown_Relative_Percent", "Total Trades": "Total_Trades", "Short Trades (won %)": "Short_Trades", "Long Trades (won %)": "Long_Trades", "Profit Trades (% of total)": "Profit_Trades", "Loss Trades (% of total)": "Loss_Trades", "Largest profit trade": "Largest_profit_trade", "Largest loss trade": "Largest_loss_trade", "Average profit trade": "Average_profit_trade", "Average loss trade": "Average_loss_trade", "Maximum consecutive wins ($)": "Maximum_consecutive_wins_Count", "Maximal consecutive profit (count)": "Maximal_consecutive_profit_Amount", "Average consecutive wins": "Average_consecutive_wins", "Maximum consecutive losses ($)": "Maximum_consecutive_losses_Count", "Maximal consecutive loss (count)": "Maximal_consecutive_loss_Amount", "Average consecutive losses": "Average_consecutive_losses"}
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
                                value_part_before_paren = raw_value_from_cell.split('(')[0].strip(); numeric_value = safe_float_convert(value_part_before_paren)
                                if numeric_value is not None:
                                    results_summary_dict[gsheet_key] = numeric_value
                                    if '(' in raw_value_from_cell and ')' in raw_value_from_cell:
                                        try:
                                            paren_content_str = raw_value_from_cell[raw_value_from_cell.find('(')+1:raw_value_from_cell.find(')')].strip().replace('%',''); paren_numeric_value = safe_float_convert(paren_content_str)
                                            if paren_numeric_value is not None:
                                                if current_label == "Balance Drawdown Maximal": results_summary_dict["Balance_Drawdown_Maximal_Percent"] = paren_numeric_value
                                                elif current_label == "Balance Drawdown Relative": results_summary_dict["Balance_Drawdown_Relative_Amount"] = numeric_value
                                                elif current_label == "Short Trades (won %)": results_summary_dict["Short_Trades_won_Percent"] = paren_numeric_value
                                                elif current_label == "Long Trades (won %)": results_summary_dict["Long_Trades_won_Percent"] = paren_numeric_value
                                                elif current_label == "Profit Trades (% of total)": results_summary_dict["Profit_Trades_Percent_of_total"] = paren_numeric_value
                                                elif current_label == "Loss Trades (% of total)": results_summary_dict["Loss_Trades_Percent_of_total"] = paren_numeric_value
                                                elif current_label == "Maximum consecutive wins ($)": results_summary_dict["Maximum_consecutive_wins_Profit"] = paren_numeric_value
                                                elif current_label == "Maximal consecutive profit (count)": results_summary_dict["Maximal_consecutive_profit_Count"] = paren_numeric_value
                                                elif current_label == "Maximum consecutive losses ($)": results_summary_dict["Maximum_consecutive_losses_Profit"] = paren_numeric_value
                                                elif current_label == "Maximal consecutive loss (count)": results_summary_dict["Maximal_consecutive_loss_Count"] = paren_numeric_value
                                        except Exception: pass
                                break 
            if line_stripped_res.startswith("Average consecutive losses"): break
        elif results_start_line_idx != -1 and results_section_processed_lines >= max_lines_for_results: break
    extracted_data['results_summary'] = results_summary_dict
    return extracted_data