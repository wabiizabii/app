# ui/statement_section.py 

import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
import uuid

from config import settings
from core import gs_handler, statement_processor

def render_statement_section():
    with st.expander("📂 Ultimate Chart Dashboard Import & Processing", expanded=True): # Expanded for debugging
        st.markdown("### 📊 จัดการ Statement และข้อมูลดิบ")
        st.markdown("---")
        st.subheader("📤 อัปโหลด Statement Report (CSV)")

        if 'uploader_key' not in st.session_state:
            st.session_state.uploader_key = 0

        uploaded_file = st.file_uploader(
            "ลากและวางไฟล์ Statement Report (CSV) ที่นี่",
            type=["csv"],
            key=f"statement_uploader_{st.session_state.uploader_key}"
        )

        st.checkbox("⚙️ เปิดโหมด Debug", key="debug_statement_processing_v2", value=True) # Force True for this test

        if uploaded_file is not None:
            active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
            active_portfolio_name = st.session_state.get('active_portfolio_name_gs')

            if not active_portfolio_id:
                st.toast("กรุณาเลือกพอร์ตก่อนอัปโหลด", icon="⚠️")
                return

            # --- Start Processing ---
            st.info(f"เริ่มกระบวนการดีบักสำหรับไฟล์: {uploaded_file.name}")
            
            try:
                file_content_bytes = uploaded_file.getvalue()
                extracted_data = statement_processor.extract_data_from_report_content(file_content_bytes)
                
                st.markdown("---")
                st.subheader("🕵️‍♂️ DEBUG STEP 1: ผลลัพธ์จากการแยกข้อมูล (Parser)")
                st.write(f"Deals found: {len(extracted_data.get('deals', pd.DataFrame()))}")
                st.write(f"Orders found: {len(extracted_data.get('orders', pd.DataFrame()))}")
                st.write(f"Positions found: {len(extracted_data.get('positions', pd.DataFrame()))}")
                st.write(f"Balance Summary found: {'Yes' if extracted_data.get('balance_summary') else 'No'}")
                st.write(f"Results Summary found: {'Yes' if extracted_data.get('results_summary') else 'No'}")
                st.markdown("---")

                has_errors = False
                
                gc = gs_handler.get_gspread_client()
                ws_dict, setup_error = gs_handler.setup_and_get_worksheets(gc)

                if setup_error:
                    st.error(f"Setup GSheet Error: {setup_error}")
                    return

                st.subheader("🕵️‍♂️ DEBUG STEP 2: ผลลัพธ์จากการบันทึกข้อมูล (Save Handler)")

                # --- DEALS ---
                deals_data = extracted_data.get('deals', pd.DataFrame())
                ok_d, new_d, skip_d = gs_handler.save_deals_to_actual_trades(ws_dict.get(settings.WORKSHEET_ACTUAL_TRADES), deals_data, active_portfolio_id, active_portfolio_name, uploaded_file.name, "debug_batch")
                st.write(f"Deals Save -> OK: `{ok_d}` (Type: {type(ok_d)}), New: `{new_d}`, Skip: `{skip_d}`")
                if not ok_d: has_errors = True
                st.write(f"-> has_errors after Deals: `{has_errors}`")

                # --- ORDERS ---
                orders_data = extracted_data.get('orders', pd.DataFrame())
                ok_o, new_o, skip_o = gs_handler.save_orders_to_gsheets(ws_dict.get(settings.WORKSHEET_ACTUAL_ORDERS), orders_data, active_portfolio_id, active_portfolio_name, uploaded_file.name, "debug_batch")
                st.write(f"Orders Save -> OK: `{ok_o}` (Type: {type(ok_o)}), New: `{new_o}`, Skip: `{skip_o}`")
                if not ok_o: has_errors = True
                st.write(f"-> has_errors after Orders: `{has_errors}`")

                # --- POSITIONS ---
                positions_data = extracted_data.get('positions', pd.DataFrame())
                ok_p, new_p, skip_p = gs_handler.save_positions_to_gsheets(ws_dict.get(settings.WORKSHEET_ACTUAL_POSITIONS), positions_data, active_portfolio_id, active_portfolio_name, uploaded_file.name, "debug_batch")
                st.write(f"Positions Save -> OK: `{ok_p}` (Type: {type(ok_p)}), New: `{new_p}`, Skip: `{skip_p}`")
                if not ok_p: has_errors = True
                st.write(f"-> has_errors after Positions: `{has_errors}`")
                
                # --- SUMMARY ---
                bal_summary = extracted_data.get('balance_summary', {})
                res_summary = extracted_data.get('results_summary', {})
                ok_s, note_s = gs_handler.save_results_summary_to_gsheets(ws_dict.get(settings.WORKSHEET_STATEMENT_SUMMARIES), bal_summary, res_summary, active_portfolio_id, active_portfolio_name, uploaded_file.name, "debug_batch")
                st.write(f"Summary Save -> OK: `{ok_s}` (Type: {type(ok_s)}), Note: `{note_s}`")
                if not ok_s: has_errors = True
                st.write(f"-> has_errors after Summary: `{has_errors}`")
                
                st.markdown("---")
                st.subheader("🕵️‍♂️ DEBUG STEP 3: ผลลัพธ์สุดท้าย")
                st.write(f"Final `has_errors` flag is: **`{has_errors}`**")

                if not has_errors:
                    st.toast("การประมวลผล (ดีบัก) สำเร็จ!", icon="✅")
                    #gs_handler.load_actual_trades_from_gsheets.clear()
                    #gs_handler.load_actual_orders_from_gsheets.clear()  # เคลียร์แคช Orders
                    #gs_handler.load_actual_positions_from_gsheets.clear() # เคลียร์แคช Pos
                    # Update balance in session state
                    if 'equity' in bal_summary and bal_summary['equity'] is not None:
                        st.session_state.latest_statement_equity = float(bal_summary['equity'])
                        st.session_state.current_account_balance = float(bal_summary['equity'])
                else:
                    st.toast("การประมวลผล (ดีบัก) พบข้อผิดพลาดบางอย่าง", icon="🚨")

            except Exception as e:
                st.error("เกิด Exception ร้ายแรงระหว่างการดีบัก")
                st.exception(e)
            
            finally:
                # ทำให้สามารถอัปโหลดไฟล์เดิมซ้ำเพื่อดีบักได้
                st.session_state.uploader_key += 1
                st.warning("โหมดดีบักทำงานเสร็จสิ้น, กด R เพื่อเริ่มใหม่ หรืออัปโหลดไฟล์อีกครั้ง")