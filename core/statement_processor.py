# ==============================================================================
# FILE: core/statement_processor.py (DEFINITIVE, RE-ARCHITECTED w/ BEAUTIFUL SOUP)
# ==============================================================================
import pandas as pd
import re
from bs4 import BeautifulSoup

def _clean_text(text):
    """Utility to clean text from HTML cells."""
    return text.strip().replace('\xa0', ' ') if text else ''

def _clean_and_float(value_str):
    """Utility to safely convert a string to a float."""
    if not value_str:
        return 0.0
    # Handles numbers like "1 234.56" and "-123.45" and percentages
    s = str(value_str).strip().replace(' ', '').replace(',', '').replace('%', '')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def _parse_special_summary_text(text):
    """Parses text that might contain values in parentheses, e.g., '842.23 (3.37%)'."""
    value = 0.0
    meta = ''
    match = re.search(r'([-+]?\s*\d[\d\s\.,-]*)\s*\((.*?)\)', text)
    if match:
        value = _clean_and_float(match.group(1))
        meta = _clean_text(match.group(2))
    else:
        value = _clean_and_float(text)
    return value, meta

def _parse_html_table(soup, table_title):
    """Finds a table by its title header and parses it into a list of dictionaries."""
    data = []
    header_tag = soup.find('b', string=table_title)
    if not header_tag:
        return pd.DataFrame()

    table = header_tag.find_parent('table')
    if not table:
        return pd.DataFrame()

    rows = table.find_all('tr')
    header_texts = []
    header_found = False

    for row in rows:
        if not header_found:
            # Find the actual header row which contains recognizable columns
            header_cells = row.find_all('td')
            temp_headers = [_clean_text(cell.get_text()) for cell in header_cells]
            if table_title == 'Positions' and 'Position' in temp_headers:
                header_texts = temp_headers
                header_found = True
            elif table_title == 'Orders' and 'Order' in temp_headers:
                header_texts = temp_headers
                header_found = True
            elif table_title == 'Deals' and 'Deal' in temp_headers:
                header_texts = temp_headers
                header_found = True
            continue

        # If header has been found, process data rows
        cells = row.find_all('td')
        if len(cells) < len(header_texts) - 3: # Simple filter for non-data rows
            continue

        row_data = {}
        cell_texts = [_clean_text(cell.get_text()) for cell in cells]
        
        # This logic handles colspan by iterating through headers and data cells together
        header_idx = 0
        data_idx = 0
        while header_idx < len(header_texts) and data_idx < len(cell_texts):
            header = header_texts[header_idx]
            cell = cells[data_idx]
            
            # Skip empty headers which are often placeholders
            if not header:
                header_idx += 1
                continue
                
            row_data[header] = _clean_text(cell.get_text())
            
            colspan = int(cell.get('colspan', 1))
            header_idx += colspan
            data_idx += 1
            
        if row_data:
            data.append(row_data)

    return pd.DataFrame(data)

def process_mt5_statement(file_content_input: bytes | str) -> dict:
    """
    Parses an MT5 HTML statement using BeautifulSoup for robustness.
    """
    try:
        soup = BeautifulSoup(file_content_input, 'html.parser')

        # --- Phase 1: Parse Summary Data (Key-Value pairs) ---
        summary_data = {}
        all_tds = soup.find_all('td')
        for i, td in enumerate(all_tds):
            text = _clean_text(td.get_text())
            if text.endswith(':'):
                key = text[:-1].replace(' ', '_')
                # Find the next non-empty td sibling for the value
                value_td = td.find_next_sibling('td')
                if value_td:
                    value_text = _clean_text(value_td.get_text())
                    if key in ['Balance_Drawdown_Maximal', 'Balance_Drawdown_Relative', 'Short_Trades_(won_%)', 'Long_Trades_(won_%)', 
                                'Profit_Trades_(%_of_total)', 'Loss_Trades_(%_of_total)', 'Maximum_consecutive_wins_($)', 'Maximum_consecutive_losses_($)',
                                'Maximal_consecutive_profit_(count)', 'Maximal_consecutive_loss_(count)']:
                        val, meta = _parse_special_summary_text(value_text)
                        summary_data[key + '_Value'] = val
                        summary_data[key + '_Meta'] = meta
                    else:
                        summary_data[key] = _clean_and_float(value_text)
        
        # --- Phase 2: Parse Transaction Tables ---
        positions_df = _parse_html_table(soup, 'Positions')
        orders_df = _parse_html_table(soup, 'Orders')
        deals_df = _parse_html_table(soup, 'Deals')
        
        # --- Phase 3: Data Cleaning & Final Assembly ---
        # (A more robust cleaning/typing section would be built here)
        if 'Profit' in deals_df.columns:
            deals_df['Profit'] = pd.to_numeric(deals_df['Profit'], errors='coerce').fillna(0)
            summary_data['Total_Net_Profit_Calculated'] = deals_df['Profit'].sum()

        return {
            'positions': positions_df,
            'orders': orders_df,
            'deals': deals_df,
            'final_summary_data': summary_data,
            # Add other keys to match the expected output structure if needed
            'portfolio_details': {},
            'balance_summary': {},
            'results_summary': {},
            'deposit_withdrawal_logs': pd.DataFrame()
        }

    except Exception as e:
        print(f"CRITICAL ERROR IN STATEMENT_PROCESSOR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'positions': pd.DataFrame(), 'orders': pd.DataFrame(), 'deals': pd.DataFrame(),
            'final_summary_data': {'error': f"Processing failed: {str(e)}"}
        }