# ui/entry_table_section.py

import streamlit as st
import pandas as pd
import numpy as np
from config import settings

def render_entry_table_section():
    """
    [แก้ไขล่าสุด] แก้ไข ValueError โดยที่ยังคงฟีเจอร์ TP Tabs ไว้ครบถ้วน
    """
    mode = st.session_state.get("mode", "").upper()
    
    with st.expander("📋 Entry Table & Strategy Summary", expanded=True):
        planning_result = st.session_state.get("planning_result")

        if not planning_result:
            st.info("กรุณาเลือกพอร์ตและกรอกข้อมูลใน Sidebar เพื่อคำนวณแผนเทรด")
            return

        entry_data = planning_result.get("entry_data", [])
        df = pd.DataFrame(entry_data)

        col_left, col_right = st.columns([3, 2])

        with col_right:
            st.markdown("##### 🧾 Strategy Summary")
            st.markdown("<hr style='margin-top:0; margin-bottom:10px'>", unsafe_allow_html=True)

            direction = planning_result.get('direction', 'N/A')
            num_entries = len(entry_data)
            total_lots = planning_result.get('total_lots', 0.0)
            total_risk_dollar = planning_result.get('total_risk_dollar', 0.0)
            balance = st.session_state.get('current_account_balance', 0.0)
            risk_input_key = f"risk_pct_{mode.lower()}_val_v2" if mode else "risk_pct_fibo_val_v2"
            risk_input = st.session_state.get(risk_input_key, 0.0)

            st.markdown(f"**Direction:** {direction}")
            st.markdown(f"**จำนวนไม้ (Entries):** {num_entries}")
            st.markdown(f"**Total Lots:** {total_lots:.2f}")

            # --- [แก้ไข] ตรวจสอบค่าว่างก่อนคำนวณ ---
            valid_entries_for_avg = [e for e in entry_data if e.get('Entry') and e.get('Lot')]
            if num_entries > 1 and total_lots > 0 and valid_entries_for_avg:
                weighted_avg_price = sum(float(e['Entry']) * float(e['Lot']) for e in valid_entries_for_avg) / total_lots
                st.markdown(f"**ราคาเข้าเฉลี่ย (Avg Entry):** {weighted_avg_price:,.3f}")

            sl_prices = [float(e['SL']) for e in entry_data if e.get('SL')]
            if sl_prices:
                furthest_sl = min(sl_prices) if direction == "Long" else max(sl_prices)
                st.markdown(f"**จุดหยุดขาดทุนรวม (Overall SL):** {furthest_sl:,.3f}")
            # --- [สิ้นสุดการแก้ไข] ---

            st.markdown(
                f"**Total Risk $:** {total_risk_dollar:.2f} "
                f"(จาก Balance: {balance:,.2f}, Risk: {risk_input:.2f}%)"
            )
            
            st.markdown("---")
            st.markdown("**เป้าหมายกำไร (Potential Targets):**")
            
            if mode == "FIBO" and "results_by_tp" in planning_result:
                results_by_tp = planning_result["results_by_tp"]
                for tp_key in ["TP1", "TP2", "TP3"]:
                    if tp_key in results_by_tp:
                        tp_info = results_by_tp[tp_key]
                        profit = tp_info.get('total_profit', 0.0)
                        rr = tp_info.get('avg_rr', 0.0)
                        st.markdown(f"&nbsp;&nbsp;&nbsp;• **{tp_key}:** {profit:,.2f} USD (Avg RR: {rr:.2f})")

        with col_left:
            if df.empty:
                if planning_result.get('error_message'):
                    st.warning(f"ไม่สามารถคำนวณแผนได้: {planning_result['error_message']}")
                else:
                    st.info("กรุณากรอกข้อมูลใน Sidebar หรือเลือก Fibo Levels")
                return

            if mode == "FIBO":
                Symbol_name = st.session_state.get('Symbol_fibo_val_v2', 'N/A')
                st.markdown(f"##### 🎯 Entry Levels (FIBO - {Symbol_name})")
                core_cols = ["Fibo Level", "Entry", "SL", "Lot", "Risk $"]
                display_df = df.copy()
                for col in core_cols:
                    if col in display_df.columns:
                        display_df[col] = pd.to_numeric(display_df[col], errors='coerce')
                st.dataframe(
                    display_df[core_cols].style.format({"Fibo Level": "{:.3f}", "Entry": "{:,.2f}", "SL": "{:,.2f}", "Lot": "{:.2f}", "Risk $": "{:,.2f}"}),
                    hide_index=True, use_container_width=True
                )
                
                # --- [คงไว้] ส่วน TP Tabs ที่สำคัญยังอยู่ครบถ้วน ---
                tp_levels_str = [leg.get("Fibo Level") for leg in planning_result.get("entry_data", [])]
                ext_prices    = planning_result.get('extension_prices', {})
                ext_results   = planning_result.get('extension_results', {})
                extension_ratios = getattr(settings, 'extension_ratios', [1.618, 2.618, 4.326])

                if tp_levels_str:
                    tabs = st.tabs([f"Entry {lvl}" for lvl in tp_levels_str if lvl])
                    for idx, lvl_str in enumerate(filter(None, tp_levels_str)):
                        with tabs[idx]:
                            st.markdown(f"##### 🎯 TP Levels for Entry {lvl_str}")
                            rows = []
                            price_map  = ext_prices.get(lvl_str, {})
                            result_map = ext_results.get(lvl_str, {})
                            for ratio in extension_ratios:
                                rows.append({'TP Level': ratio, 'Price': price_map.get(str(ratio)), 'Avg RR': result_map.get(str(ratio), {}).get('avg_rr'), 'Profit ($)': result_map.get(str(ratio), {}).get('profit')})
                            ext_df = pd.DataFrame(rows)
                            if not ext_df.empty:
                                for c in ext_df.columns:
                                    ext_df[c] = pd.to_numeric(ext_df[c], errors='coerce')
                                st.dataframe(
                                    ext_df.style.format({'TP Level': '{:.3f}', 'Price': '{:,.2f}', 'Avg RR': '{:.2f}', 'Profit ($)': '{:,.2f}'}),
                                    hide_index=True, use_container_width=True
                                )
                # --- [สิ้นสุดส่วน TP Tabs] ---
            
            elif mode == "CUSTOM":
                st.markdown("##### 🎯 Entry Levels (CUSTOM)")
                
                # --- [แก้ไข] แปลงชนิดข้อมูลก่อนแสดงผลสำหรับ CUSTOM ---
                custom_numeric_cols = ["Entry", "SL", "TP", "Lot", "Risk $", "RR", "TP (RR≈3)"]
                for col in custom_numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                display_cols = [c for c in custom_numeric_cols if c in df.columns]
                st.dataframe(
                    df[display_cols].style.format({
                        "Entry": "{:,.2f}", "SL": "{:,.2f}", "TP": "{:,.2f}",
                        "Lot": "{:.2f}", "Risk $": "{:.2f}", "RR": "{:.2f}",
                        "TP (RR≈3)": "{:,.2f}"
                    }, na_rep='N/A'),
                    hide_index=True, use_container_width=True
                )