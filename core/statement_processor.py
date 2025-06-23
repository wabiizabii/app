# core/statement_processor.py (เวอร์ชันสมบูรณ์: Deals, Orders, Positions)

import pandas as pd
import io

def extract_data_from_report_content(file_content_input: bytes):
    """
    [Final Complete Version] This version parses all three tables (Deals, Orders, Positions)
    and also calculates the final summary directly from the deals_df for maximum robustness.
    """
    extracted_data = {'deals': pd.DataFrame(), 'orders': pd.DataFrame(), 'positions': pd.DataFrame(), 'balance_summary': {}, 'results_summary': {}}
    
    lines = []
    if isinstance(file_content_input, str):
        lines = file_content_input.strip().split('\n')
    elif isinstance(file_content_input, bytes):
        lines = file_content_input.decode('utf-8', errors='replace').strip().split('\n')
    else:
        return extracted_data

    # --- 1. Find all section headers first ---
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
            # Use 'in' for flexibility in case of extra spaces in header
            if header_text in line:
                header_indices[name] = i
                break

    # --- 2. Parse each section into a DataFrame ---
    for i, section_name in enumerate(section_order):
        start_index = header_indices[section_name]
        if start_index == -1:
            continue

        data_start_line = start_index + 1
        data_end_line = len(lines)
        
        # Find the end of the current section by looking for the start of the next section
        for next_section_name in section_order[i+1:]:
            if header_indices[next_section_name] != -1 and header_indices[next_section_name] > start_index:
                data_end_line = header_indices[next_section_name]
                break
        
        # Also check for the text summary section as a potential end boundary
        for j in range(data_start_line, data_end_line):
            if lines[j].strip().startswith("Balance:"):
                data_end_line = j
                break

        section_lines = [line.strip() for line in lines[data_start_line:data_end_line] if line.strip() and ',' in line]

        if not section_lines:
            continue

        try:
            df = pd.read_csv(io.StringIO("\n".join(section_lines)), header=None, names=expected_columns_map[section_name], skipinitialspace=True, dtype=str)
            df.dropna(how='all', inplace=True)
            extracted_data[section_name.lower()] = df
        except Exception:
            pass # If a section fails to parse, leave it as an empty DataFrame

    # --- 3. Calculate summary directly from the 'deals' DataFrame for accuracy ---
    deals_df = extracted_data.get('deals', pd.DataFrame())
    balance_summary = {}
    results_summary = {}

    if not deals_df.empty:
        deals_df_copy = deals_df.copy()
        
        deals_df_copy['Profit_Deal'] = deals_df_copy['Profit_Deal'].astype(str).str.replace(' ', '').str.replace('–', '-').str.replace('—', '-')
        deals_df_copy['Profit_Deal'] = pd.to_numeric(deals_df_copy['Profit_Deal'], errors='coerce').fillna(0)
        deals_df_copy['Balance_Deal'] = pd.to_numeric(deals_df_copy['Balance_Deal'], errors='coerce').fillna(0)
        
        calculated_profit = 0.0
        calculated_deposit = 0.0
        calculated_withdrawal = 0.0

        for index, row in deals_df_copy.iterrows():
            deal_type = str(row.get('Type_Deal', '')).lower().strip()
            comment = str(row.get('Comment_Deal', '')).lower().strip()
            profit_val = row['Profit_Deal']

            if deal_type in ['buy', 'sell']:
                calculated_profit += profit_val
            elif deal_type == 'balance':
                if 'deposit' in comment:
                    calculated_deposit += profit_val
                elif 'withdraw' in comment:
                    calculated_withdrawal += profit_val
        
        results_summary['Total_Net_Profit'] = calculated_profit
        balance_summary['deposit'] = calculated_deposit
        balance_summary['withdrawal'] = calculated_withdrawal
        
        if not deals_df_copy.empty:
            balance_summary['balance'] = deals_df_copy['Balance_Deal'].iloc[-1]
            balance_summary['equity'] = deals_df_copy['Balance_Deal'].iloc[-1]

    extracted_data['balance_summary'] = balance_summary
    extracted_data['results_summary'] = results_summary

    return extracted_data