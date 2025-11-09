# ui/topstep_section.py (เวอร์ชันแก้ไข KeyError: 'max_contracts_std')

import streamlit as st
from config import settings
from decimal import Decimal, InvalidOperation

def get_micro_version(symbol):
    if symbol.startswith("E") or symbol.startswith("R") or symbol.startswith("Y"):
        return "M" + symbol[1:] if len(symbol) > 1 else None
    if symbol == "GC": return "MGC"
    if symbol == "CL": return "MCL"
    if symbol == "SI": return "SIL"
    return None

def render_topstep_section():
    with st.expander("🔵 Universal Topstep Futures Planner", expanded=True):
        
        if not hasattr(settings, 'ACCOUNT_RULES'):
            st.error("ไม่พบข้อมูล ACCOUNT_RULES ในไฟล์ settings.py")
            st.stop()

        account_selection = st.selectbox(
            "เลือกขนาดบัญชีของคุณ (Select Your Account Size)",
            options=list(settings.ACCOUNT_RULES.keys()),
            key="topstep_account_selector"
        )
        selected_rules = settings.ACCOUNT_RULES[account_selection]

        PROFIT_TARGET = selected_rules['profit_target']
        MAX_LOSS_LIMIT = selected_rules['max_loss_limit']
        STARTING_BALANCE = selected_rules['start_balance']

        st.info("กรอกข้อมูล Equity ปัจจุบันของคุณเพื่อวิเคราะห์สถานะ")
        col1, col2 = st.columns(2)
        with col1:
            current_equity = st.number_input("ยอด Equity ปัจจุบัน ($)", min_value=0.0, value=STARTING_BALANCE, step=100.0, format="%.2f", key="ts_equity")
        with col2:
            highest_equity = st.number_input("ยอด Equity สูงสุดที่เคยทำได้ ($)", min_value=STARTING_BALANCE, value=max(STARTING_BALANCE, current_equity), step=100.0, format="%.2f", key="ts_highest_equity")

        trailing_stopout_level = max(highest_equity - MAX_LOSS_LIMIT, STARTING_BALANCE)
        cushion = current_equity - trailing_stopout_level
        
        st.success("#### สถานะและกฎของคุณ:")
        st.metric(label="🎯 เป้าหมายกำไร (Profit Target)", value=f"${PROFIT_TARGET:,.0f}")
        st.warning(f"**กฎที่อันตรายที่สุด (Trailing Drawdown):** จุดสอบตกของคุณตอนนี้คือ **${trailing_stopout_level:,.2f}**")
        st.metric(label="ระยะปลอดภัย (Cushion)", value=f"${cushion:,.2f}")

        st.divider()
        st.info("#### 🔬 เครื่องมือวางแผนการเทรดอัจฉริยะ")

        with st.container(border=True):
            st.markdown("**1. กรอกแผนการเทรดของคุณ (Idea)**")
            form_col1, form_col2 = st.columns(2)
            with form_col1:
                if hasattr(settings, 'FUTURES_TICK_VALUES'):
                    standard_symbols = sorted([s for s in settings.FUTURES_TICK_VALUES.keys() if not s.startswith("M")])
                    symbol_index = standard_symbols.index("GC") if "GC" in standard_symbols else 0
                    symbol = st.selectbox("เลือกสินทรัพย์ (Standard)", options=standard_symbols, index=symbol_index)
                else:
                    st.error("ไม่พบข้อมูล FUTURES_TICK_VALUES ในไฟล์ settings.py"); symbol = None
            with form_col2:
                 direction = st.radio("ทิศทาง (Direction)", ["Long", "Short"], horizontal=True)
            form_col3, form_col4 = st.columns(2)
            with form_col3:
                entry_price_str = st.text_input("ราคาเข้า (Entry Price)", placeholder="เช่น 2350.50")
            with form_col4:
                sl_price_str = st.text_input("ราคาหยุดขาดทุน (SL Price)", placeholder="เช่น 2345.50")
        
        if entry_price_str and sl_price_str and symbol:
            try:
                entry_price = Decimal(entry_price_str); sl_price = Decimal(sl_price_str)
                if hasattr(settings, 'FUTURES_TICK_SIZES'):
                    tick_size = Decimal(str(settings.FUTURES_TICK_SIZES.get(symbol, 0.01)))
                else:
                    st.error("ไม่พบข้อมูล FUTURES_TICK_SIZES ในไฟล์ settings.py"); st.stop()
                price_diff_sl = abs(entry_price - sl_price); sl_ticks = int(price_diff_sl / tick_size)
                standard_tick_value = settings.FUTURES_TICK_VALUES.get(symbol, 0)
                risk_per_standard = sl_ticks * standard_tick_value
                micro_symbol = get_micro_version(symbol)
                micro_tick_value = settings.FUTURES_TICK_VALUES.get(micro_symbol, 0) if micro_symbol else 0
                risk_per_micro = sl_ticks * micro_tick_value if micro_tick_value > 0 else 0

                daily_loss_limit = selected_rules['daily_loss_limit']
                recommended_risk_usd = daily_loss_limit * 0.25
                
                recommended_contracts = 0; contract_type = "N/A"
                if risk_per_micro > 0 and risk_per_micro <= recommended_risk_usd:
                    contract_type = "Micro"; recommended_contracts = int(recommended_risk_usd / risk_per_micro)
                elif risk_per_standard > 0 and risk_per_standard <= recommended_risk_usd:
                    contract_type = "Standard"; recommended_contracts = int(recommended_risk_usd / risk_per_standard)

                with st.container(border=True):
                    st.markdown("**2. ปรับขนาดและวางแผน (Sizing & Planning)**")
                    
                    if contract_type == "Micro":
                        # --- แก้ไขจุดที่เกิด Error ---
                        max_micro_contracts = selected_rules['max_contracts_std'] * 10
                        final_contracts = st.slider(f"ปรับจำนวน Contracts ({micro_symbol})", 1, max_micro_contracts, recommended_contracts, 1)
                        total_risk_now = final_contracts * risk_per_micro
                    elif contract_type == "Standard":
                        scaling_level = selected_rules['scaling_level_1']
                        contracts_step1 = selected_rules['scaling_contracts_1']
                        contracts_step2 = selected_rules['scaling_contracts_2']
                        contracts_allowed_by_plan = contracts_step1 if current_equity < scaling_level else contracts_step2
                        final_contracts = st.slider(f"ปรับจำนวน Contracts ({symbol})", 1, contracts_allowed_by_plan, recommended_contracts, 1)
                        total_risk_now = final_contracts * risk_per_standard
                    else:
                        st.error("Setup นี้มีความเสี่ยงสูงเกินไป แม้จะใช้ 1 Micro Contract ก็ตาม กรุณาหา Setup ใหม่")
                        final_contracts = 0; total_risk_now = 0
                    
                    if final_contracts > 0:
                        st.success(f"**แผนปัจจุบัน:** เข้า **{final_contracts} {contract_type} Contracts** | **ความเสี่ยงรวม:** **${total_risk_now:,.2f}**")
                        st.markdown("#### 🎯 ตารางเป้าหมายกำไร (Potential Targets):")
                        rr_levels = [1, 2, 3, 4, 5, 6, 7]; target_data = []
                        for rr in rr_levels:
                            tp_ticks = sl_ticks * rr
                            price_diff_tp = Decimal(tp_ticks) * tick_size
                            tp_price = entry_price + price_diff_tp if direction == "Long" else entry_price - price_diff_tp
                            if contract_type == "Micro":
                                total_profit_now = final_contracts * (tp_ticks * micro_tick_value)
                            else:
                                total_profit_now = final_contracts * (tp_ticks * standard_tick_value)
                            target_data.append({"RR": f"1:{rr}", "TP Price": f"{tp_price:.{sl_price.as_tuple().exponent*(-1)}f}", "Potential Profit": f"${total_profit_now:,.2f}"})
                        st.dataframe(target_data, hide_index=True, use_container_width=True)
            
            except (InvalidOperation, TypeError):
                st.warning("กรุณากรอกราคาเข้าและราคา SL ให้ถูกต้องเพื่อเริ่มการคำนวณ")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")