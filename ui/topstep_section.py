# ui/topstep_section.py (เวอร์ชันเต็มสมบูรณ์: Real-time Risk Integration)

import streamlit as st
from config import settings
from decimal import Decimal, InvalidOperation

def get_micro_version(symbol):
    """แปลงสัญลักษณ์ Standard เป็น Micro (ถ้ามี)"""
    if symbol in ["ES", "NQ", "YM", "RTY"]:
        return "M" + symbol
    if symbol == "GC": return "MGC"
    if symbol == "CL": return "MCL"
    if symbol == "SI": return "SIL"
    return None

def render_topstep_section():
    """
    แสดงผล Section เครื่องมือวางแผนการเทรดแบบ Universal (Futures & Forex)
    *** อัปเกรด: คำนวณความเสี่ยงจาก Sidebar แบบ Real-time ***
    """
    with st.expander("Universal Trade Planner", expanded=True):
        
        asset_type = st.radio(
            "เลือกประเภทสินทรัพย์ (Select Asset Type)",
            ["Futures", "Forex / CFD"],
            horizontal=True,
            key="universal_asset_type"
        )
        st.divider()

        # --- START: โค้ดส่วนแก้ไขที่สำคัญที่สุด ---
        
        # 1. ดึง "วัตถุดิบ" จาก session_state ที่ Sidebar เป็นคนกำหนด
        # ใช้ .get() พร้อมค่า default เพื่อป้องกัน error หาก session_state ยังไม่ถูกสร้าง
        balance_from_sidebar = st.session_state.get('current_account_balance', 10000.0) 
        percent_from_sidebar = st.session_state.get('risk_calc_percent', 0.9) 
        
        # 2. คำนวณ "ค่าความเสี่ยงเริ่มต้น" ที่ถูกต้องภายใน Section นี้เลย
        try:
            # ใช้ float() เพื่อให้แน่ใจว่าเป็นตัวเลขทศนิยมก่อนคำนวณ
            risk_value_from_sidebar = float(balance_from_sidebar) * (float(percent_from_sidebar) / 100)
        except (ValueError, TypeError):
            risk_value_from_sidebar = 100.0 # ค่าสำรองหากเกิดข้อผิดพลาด
            
        # --- END: สิ้นสุดโค้ดส่วนแก้ไข ---

        # ========================== UI & LOGIC สำหรับ FUTURES ==========================
        if asset_type == "Futures":
            st.subheader("🔵 Futures Trade Planner")
            with st.container(border=True):
                st.markdown("**1. กรอกแผนการเทรดของคุณ (Idea)**")
                
                form_col1, form_col2, form_col3 = st.columns(3)
                with form_col1:
                     risk_usd = st.number_input(
                         "ความเสี่ยงที่ยอมรับได้ ($)", 
                         min_value=1.0, 
                         value=risk_value_from_sidebar, 
                         step=10.0, 
                         help="ค่าเริ่มต้นมาจาก Risk Sizing Calculator ใน Sidebar", 
                         key="futures_risk"
                     )
                with form_col2:
                    if hasattr(settings, 'FUTURES_TICK_VALUES'):
                        standard_symbols = sorted([s for s in settings.FUTURES_TICK_VALUES.keys() if not s.startswith("M")])
                        symbol_index = standard_symbols.index("GC") if "GC" in standard_symbols else 0
                        symbol = st.selectbox("เลือกสินทรัพย์", options=standard_symbols, index=symbol_index, key="futures_symbol")
                    else:
                        st.error("ไม่พบข้อมูล FUTURES_TICK_VALUES ในไฟล์ settings.py"); symbol = None
                with form_col3:
                     direction = st.radio("ทิศทาง", ["Long", "Short"], horizontal=True, key="futures_dir")
                
                form_col4, form_col5 = st.columns(2)
                with form_col4:
                    entry_price_str = st.text_input("ราคาเข้า", placeholder="2350.50", key="futures_entry")
                with form_col5:
                    sl_price_str = st.text_input("ราคาหยุดขาดทุน", placeholder="2345.50", key="futures_sl")
            
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
                    recommended_contracts = 0; contract_type = "N/A"
                    if risk_per_micro > 0 and risk_per_micro <= risk_usd:
                        contract_type = "Micro"; recommended_contracts = int(risk_usd / risk_per_micro)
                    elif risk_per_standard > 0 and risk_per_standard <= risk_usd:
                        contract_type = "Standard"; recommended_contracts = int(risk_usd / risk_per_standard)
                    st.divider()
                    with st.container(border=True):
                        st.markdown("**2. ปรับขนาดและวางแผน (Sizing & Planning)**")
                        st.markdown(f"**ระยะ SL ที่คำนวณได้:** `{sl_ticks} Ticks`")
                        final_contracts = 0; total_risk_now = 0.0
                        if contract_type == "Micro":
                            final_contracts = st.slider(f"ปรับจำนวน Contracts ({micro_symbol})", 1, 50, recommended_contracts, 1)
                            total_risk_now = final_contracts * risk_per_micro
                        elif contract_type == "Standard":
                            final_contracts = st.slider(f"ปรับจำนวน Contracts ({symbol})", 1, 5, recommended_contracts, 1)
                            total_risk_now = final_contracts * risk_per_standard
                        else:
                            st.error(f"Setup นี้มีความเสี่ยงสูงเกินไปสำหรับงบประมาณ (${risk_usd:,.2f}) ของคุณ")
                        if final_contracts > 0:
                            st.success(f"**แผนปัจจุบัน:** เข้า **{final_contracts} {contract_type} Contracts** | **ความเสี่ยงรวม:** **${total_risk_now:,.2f}**")
                            st.markdown("#### 🎯 ตารางเป้าหมายกำไร (Potential Targets):")
                            rr_levels = [1, 2, 3, 5, 7, 10]; target_data = []
                            for rr in rr_levels:
                                tp_ticks = sl_ticks * rr; price_diff_tp = Decimal(tp_ticks) * tick_size
                                tp_price = entry_price + price_diff_tp if direction == "Long" else entry_price - price_diff_tp
                                if contract_type == "Micro": total_profit_now = final_contracts * (tp_ticks * micro_tick_value)
                                else: total_profit_now = final_contracts * (tp_ticks * standard_tick_value)
                                target_data.append({"RR": f"1:{rr}", "TP Price": f"{tp_price:.{sl_price.as_tuple().exponent*(-1)}f}", "Potential Profit": f"${total_profit_now:,.2f}"})
                            st.dataframe(target_data, hide_index=True, use_container_width=True)
                except (InvalidOperation, TypeError):
                    st.warning("กรุณากรอกราคาเข้าและราคา SL ให้ถูกต้องเพื่อเริ่มการคำนวณ")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด [Futures]: {e}")

        # ========================== UI & LOGIC สำหรับ FOREX/CFD ========================
        elif asset_type == "Forex / CFD":
            st.subheader("💹 Forex / CFD Trade Planner")
            with st.container(border=True):
                st.markdown("**1. กรอกแผนการเทรดของคุณ (Idea)**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    risk_usd_forex = st.number_input("ความเสี่ยงที่ยอมรับได้ ($)", 1.0, value=risk_value_from_sidebar, step=10.0, key="forex_risk")
                with col2:
                    if hasattr(settings, 'FOREX_POINT_VALUES'):
                        forex_symbols = sorted(list(settings.FOREX_POINT_VALUES.keys()))
                        symbol = st.selectbox("เลือกสินทรัพย์", forex_symbols, index=forex_symbols.index("XAUUSD"), key="forex_symbol")
                    else:
                        st.error("ไม่พบ FOREX_POINT_VALUES ใน settings.py"); symbol = None
                with col3:
                    direction = st.radio("ทิศทาง", ["Long", "Short"], horizontal=True, key="forex_direction")
                col4, col5 = st.columns(2)
                with col4: entry_price_str = st.text_input("ราคาเข้า (Entry Price)", placeholder="เช่น 1950.50", key="forex_entry")
                with col5: sl_price_str = st.text_input("ราคาหยุดขาดทุน (SL Price)", placeholder="เช่น 1945.50", key="forex_sl")
            
            if entry_price_str and sl_price_str and symbol:
                try:
                    entry_price = float(entry_price_str); sl_price = float(sl_price_str)
                    sl_points = abs(entry_price - sl_price)
                    point_value = settings.FOREX_POINT_VALUES.get(symbol, 1.0)
                    risk_per_lot = sl_points * point_value
                    st.divider()
                    with st.container(border=True):
                        st.markdown("**2. ปรับขนาดและวางแผน (Sizing & Planning)**")
                        st.markdown(f"**ระยะ SL:** `{sl_points:,.2f} Points` | **ความเสี่ยงต่อ 1 Lot:** `${risk_per_lot:,.2f}`")
                        recommended_lot_size = risk_usd_forex / risk_per_lot if risk_per_lot > 0 else 0.01
                        lot_size = st.slider("ปรับขนาด Lot Size", 0.01, 10.00, value=max(0.01, round(recommended_lot_size, 2)), step=0.01, format="%.2f")
                        total_risk_now = lot_size * risk_per_lot
                        st.success(f"**แผนปัจจุบัน:** เข้า **{lot_size:.2f} lots** | **ความเสี่ยงรวม:** **${total_risk_now:,.2f}**")
                        st.markdown("#### 🎯 ตารางเป้าหมายกำไร (Potential Targets):")
                        rr_levels = [1, 2, 3, 4, 5, 6, 7]; target_data = []
                        for rr in rr_levels:
                            tp_points = sl_points * rr
                            tp_price = entry_price + tp_points if direction == "Long" else entry_price - tp_points
                            total_profit_now = lot_size * (tp_points * point_value)
                            target_data.append({"RR": f"1:{rr}", "TP Price": f"{tp_price:,.3f}", "Potential Profit": f"${total_profit_now:,.2f}"})
                        st.dataframe(target_data, hide_index=True, use_container_width=True)
                except (ValueError, TypeError):
                    st.warning("กรุณากรอกราคาเข้าและราคา SL ให้ถูกต้อง")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด [Forex]: {e}")