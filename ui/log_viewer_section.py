# ui/log_viewer_section.py
import streamlit as st
import pandas as pd

# Import functions from other modules
from core import gs_handler # To load all planned trade logs

@st.cache_data(ttl=120) # Cache ผลลัพธ์ของฟังก์ชันนี้ (ซึ่งรวมการเรียงข้อมูลแล้ว) ไว้ 2 นาที
def load_and_sort_planned_trades_for_viewer():
    """
    Loads planned trade logs using gs_handler and sorts them by Timestamp.
    This function is specific to the log viewer's needs.
    """
    df_logs_viewer = gs_handler.load_all_planned_trade_logs_from_gsheets()

    if df_logs_viewer.empty:
        return pd.DataFrame()

    # Ensure Timestamp is datetime before sorting
    if 'Timestamp' in df_logs_viewer.columns and not df_logs_viewer['Timestamp'].isnull().all():
        if not pd.api.types.is_datetime64_any_dtype(df_logs_viewer['Timestamp']):
             df_logs_viewer['Timestamp'] = pd.to_datetime(df_logs_viewer['Timestamp'], errors='coerce')
        # Sort by Timestamp descending after ensuring it's a datetime type
        return df_logs_viewer.sort_values(by="Timestamp", ascending=False)
    
    # Return df_logs_viewer if Timestamp column is missing or cannot be used for sorting
    return df_logs_viewer

def render_log_viewer_section():
    """
    Renders the Trade Log Viewer section in the main area.
    Corresponds to SEC 7 of main (1).py.
    """
    with st.expander("📚 Trade Log Viewer (แผนเทรดจาก Google Sheets)", expanded=False):
        df_log_viewer_gs_sorted = load_and_sort_planned_trades_for_viewer()

        if df_log_viewer_gs_sorted.empty:
            st.info("ยังไม่มีข้อมูลแผนที่บันทึกไว้ใน Google Sheets หรือ Worksheet 'PlannedTradeLogs' ว่างเปล่า/โหลดไม่สำเร็จ.")
        else:
            df_show_log_viewer = df_log_viewer_gs_sorted.copy() # Work on a copy for filtering

            # --- Filters UI ---
            log_filter_cols = st.columns(4)
            with log_filter_cols[0]:
                portfolios_in_log = ["ทั้งหมด"]
                if "PortfolioName" in df_show_log_viewer.columns and not df_show_log_viewer["PortfolioName"].isnull().all():
                     portfolios_in_log.extend(sorted(df_show_log_viewer["PortfolioName"].dropna().unique().tolist()))
                portfolio_filter_log = st.selectbox("Portfolio", portfolios_in_log, key="log_viewer_portfolio_filter_v1_ref")

            with log_filter_cols[1]:
                modes_in_log = ["ทั้งหมด"]
                if "Mode" in df_show_log_viewer.columns and not df_show_log_viewer["Mode"].isnull().all():
                    modes_in_log.extend(sorted(df_show_log_viewer["Mode"].dropna().unique().tolist()))
                mode_filter_log = st.selectbox("Mode", modes_in_log, key="log_viewer_mode_filter_v1_ref")

            with log_filter_cols[2]:
                Symbols_in_log = ["ทั้งหมด"]
                if "Symbol" in df_show_log_viewer.columns and not df_show_log_viewer["Symbol"].isnull().all():
                    Symbols_in_log.extend(sorted(df_show_log_viewer["Symbol"].dropna().unique().tolist()))
                Symbol_filter_log = st.selectbox("Symbol", Symbols_in_log, key="log_viewer_Symbol_filter_v1_ref")

            with log_filter_cols[3]:
                date_filter_log = None
                if 'Timestamp' in df_show_log_viewer.columns and not df_show_log_viewer['Timestamp'].isnull().all():
                     date_filter_log = st.date_input("ค้นหาวันที่ (Log)", value=None, key="log_viewer_date_filter_v1_ref", help="เลือกวันที่เพื่อกรอง Log")

            # --- Apply Filters ---
            if portfolio_filter_log != "ทั้งหมด" and "PortfolioName" in df_show_log_viewer.columns:
                df_show_log_viewer = df_show_log_viewer[df_show_log_viewer["PortfolioName"] == portfolio_filter_log]
            if mode_filter_log != "ทั้งหมด" and "Mode" in df_show_log_viewer.columns:
                df_show_log_viewer = df_show_log_viewer[df_show_log_viewer["Mode"] == mode_filter_log]
            if Symbol_filter_log != "ทั้งหมด" and "Symbol" in df_show_log_viewer.columns:
                df_show_log_viewer = df_show_log_viewer[df_show_log_viewer["Symbol"] == Symbol_filter_log]
            
            if date_filter_log and 'Timestamp' in df_show_log_viewer.columns:
                # Ensure 'Timestamp' is datetime for comparison
                if not pd.api.types.is_datetime64_any_dtype(df_show_log_viewer['Timestamp']):
                    df_show_log_viewer['Timestamp'] = pd.to_datetime(df_show_log_viewer['Timestamp'], errors='coerce')
                
                # Filter out NaT rows that might result from errors='coerce' before attempting .dt accessor
                df_show_log_viewer_filtered_date = df_show_log_viewer.dropna(subset=['Timestamp'])
                if not df_show_log_viewer_filtered_date.empty:
                    df_show_log_viewer = df_show_log_viewer_filtered_date[df_show_log_viewer_filtered_date["Timestamp"].dt.date == date_filter_log]
                else: # If all rows had NaT Timestamps
                    df_show_log_viewer = pd.DataFrame(columns=df_show_log_viewer.columns) # Empty DataFrame

            st.markdown("---")
            st.markdown("**Log Details & Actions:**")

            cols_to_display_log_viewer_map = { # Original column name : Display Name
                "Timestamp": "Timestamp", "PortfolioName": "Portfolio", "Symbol": "Symbol",
                "Mode": "Mode", "Direction": "Direction", "Entry": "Entry", "SL": "SL", "TP": "TP",
                "Lot": "Lot", "Risk $": "Risk $", "RR": "RR"
            }
            # Only try to display columns that actually exist in the dataframe
            actual_cols_to_display_keys = [k for k in cols_to_display_log_viewer_map.keys() if k in df_show_log_viewer.columns]
            
            num_display_cols = len(actual_cols_to_display_keys)

            if not df_show_log_viewer.empty:
                # Create header row
                header_cols_list = st.columns(num_display_cols + 1) # +1 for Action column
                for i, col_key in enumerate(actual_cols_to_display_keys):
                    header_cols_list[i].markdown(f"**{cols_to_display_log_viewer_map[col_key]}**")
                header_cols_list[num_display_cols].markdown(f"**Action**")

                # Display data rows
                for index_log, row_log in df_show_log_viewer.iterrows():
                    row_display_cols_list = st.columns(num_display_cols + 1)
                    for i, col_key in enumerate(actual_cols_to_display_keys):
                        val = row_log.get(col_key, "-")
                        if pd.isna(val): val_display = "-"
                        elif isinstance(val, float):
                            if col_key in ['Entry', 'SL', 'TP']: val_display = f"{val:.5f}" if val != 0 else "0.00000"
                            elif col_key in ['Lot', 'Risk $', 'RR', 'Risk %']: val_display = f"{val:.2f}"
                            else: val_display = str(val)
                        elif isinstance(val, pd.Timestamp): val_display = val.strftime("%Y-%m-%d %H:%M")
                        else: val_display = str(val)
                        row_display_cols_list[i].write(val_display)

                    log_id_for_key = row_log.get('LogID', str(index_log)) # Use LogID if available, else index
                    if row_display_cols_list[num_display_cols].button(f"📈 Plot", key=f"plot_log_sec7_refactored_{log_id_for_key}"):
                        st.session_state['plot_data'] = row_log.to_dict()
                        st.success(f"เลือกข้อมูลเทรด '{row_log.get('Symbol', '-')}' @ Entry '{row_log.get('Entry', '-')}' เตรียมพร้อมสำหรับ Plot บน Chart Visualizer!")
                        st.rerun() # Rerun to update chart section
            else:
                st.info("ไม่พบข้อมูล Log ที่ตรงกับเงื่อนไขการค้นหา")
            
            # Display plot_data in sidebar (as per original SEC 7)
            if 'plot_data' in st.session_state and st.session_state['plot_data']:
                st.sidebar.success(f"ข้อมูลพร้อม Plot: {st.session_state['plot_data'].get('Symbol')} @ {st.session_state['plot_data'].get('Entry')}")
                try:
                    # Truncate for display if too long, to prevent sidebar clutter
                    plot_data_str = str(st.session_state['plot_data'])
                    plot_data_display_sidebar = (plot_data_str[:297] + "...") if len(plot_data_str) > 300 else plot_data_str
                    st.sidebar.json(plot_data_display_sidebar, expanded=False)
                except Exception as e_json_sidebar:
                    st.sidebar.text(f"ไม่สามารถแสดง plot_data (JSON error): {e_json_sidebar}")