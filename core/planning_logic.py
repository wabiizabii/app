# ultimate_chart_trade_planner/core/planning_logic.py

import numpy as np
import pandas as pd
from config import settings

def calculate_fibo_trade_plan(
    swing_high_str: str,
    swing_low_str: str,
    risk_pct_fibo_input: float,
    fibo_levels_definitions: list,
    fibo_flags_selected: list,
    direction: str,
    current_active_balance: float,
    spread_str: str,
    asset_name: str,
    account_type: str
):
    # --- START OF FIX: Initialize all returnable variables at the top ---
    # การกำหนดค่าเริ่มต้นทั้งหมดไว้ที่นี่ จะช่วยป้องกัน UnboundLocalError ได้ 100%
    error_message = None
    entry_data_list = []
    total_lots = 0.0
    total_risk_dollar_calculated = 0.0
    tp_prices = {}  # Initialize as empty dict
    extension_prices = {}
    extension_results = {}
    results_by_tp = {
        'TP1': {'total_profit': 0.0, 'avg_rr': 0.0, 'rr_list': []},
        'TP2': {'total_profit': 0.0, 'avg_rr': 0.0, 'rr_list': []},
        'TP3': {'total_profit': 0.0, 'avg_rr': 0.0, 'rr_list': []}
    }
    # --- END OF FIX ---

    try:
        # Input Validation
        if not swing_high_str or not swing_low_str: raise ValueError("กรุณากรอก High และ Low")
        high_fibo = float(swing_high_str)
        low_fibo = float(swing_low_str)

        try: spread = float(spread_str) if spread_str else 0.0
        except (ValueError, TypeError): spread = 0.0

        if risk_pct_fibo_input <= 0: raise ValueError("Risk % ต้องมากกว่า 0")
        if high_fibo <= low_fibo: raise ValueError("High ต้องมากกว่า Low")

        range_fibo = abs(high_fibo - low_fibo)
        if range_fibo <= 1e-9: raise ValueError("Range ระหว่าง High และ Low น้อยเกินไป")

        num_selected = sum(fibo_flags_selected)
        if num_selected == 0: raise ValueError("กรุณาเลือก Fibo Level อย่างน้อยหนึ่งระดับ")

        # Main Calculations
        total_risk_dollar = current_active_balance * (risk_pct_fibo_input / 100.0)
        risk_per_leg = total_risk_dollar / num_selected

        fibo_prices_long  = [low_fibo  + range_fibo * lvl for lvl in fibo_levels_definitions]
        fibo_prices_short = [high_fibo - range_fibo * lvl for lvl in fibo_levels_definitions]

        # TP prices are now calculated inside the 'try' block after validation passes
        tp_prices = {
            'TP1': (high_fibo + range_fibo * (settings.RATIO_TP1_EFF - 1)) if direction=="Long" else (low_fibo - range_fibo * (settings.RATIO_TP1_EFF - 1)),
            'TP2': (high_fibo + range_fibo * (settings.RATIO_TP2_EFF - 1)) if direction=="Long" else (low_fibo - range_fibo * (settings.RATIO_TP2_EFF - 1)),
            'TP3': (high_fibo + range_fibo * (settings.RATIO_TP3_EFF - 1)) if direction=="Long" else (low_fibo - range_fibo * (settings.RATIO_TP3_EFF - 1)),
        }
        
        selected_idxs = [i for i, f in enumerate(fibo_flags_selected) if f]

        for fibo_idx in selected_idxs:
            current_fibo_level = fibo_levels_definitions[fibo_idx]
            
            if direction == "Long":
                entry_price = fibo_prices_long[fibo_idx]
                if current_fibo_level <= 0.382: sl_base = low_fibo
                else:
                    current_selection_index = selected_idxs.index(fibo_idx)
                    if current_selection_index == 0: sl_base = low_fibo
                    elif current_selection_index == 1: sl_base = (fibo_prices_long[selected_idxs[0]] + low_fibo) / 2
                    else: sl_base = (fibo_prices_long[selected_idxs[current_selection_index - 1]] + fibo_prices_long[selected_idxs[current_selection_index - 2]]) / 2
                sl_price = sl_base - spread
            else: # Short
                entry_price = fibo_prices_short[fibo_idx]
                if current_fibo_level <= 0.382: sl_base = high_fibo
                else:
                    current_selection_index = selected_idxs.index(fibo_idx)
                    if current_selection_index == 0: sl_base = high_fibo
                    elif current_selection_index == 1: sl_base = (fibo_prices_short[selected_idxs[0]] + high_fibo) / 2
                    else: sl_base = (fibo_prices_short[selected_idxs[current_selection_index - 1]] + fibo_prices_short[selected_idxs[current_selection_index - 2]]) / 2
                sl_price = sl_base + spread

            stop_dist = abs(entry_price - sl_price)
            lot  = (risk_per_leg / stop_dist) if stop_dist > 1e-9 else 0.0
            risk = lot * stop_dist if stop_dist > 1e-9 else risk_per_leg

            total_lots += lot
            total_risk_dollar_calculated += risk

            fibo_level_str = f"{current_fibo_level:.3f}"
            
            leg = { "Fibo Level": fibo_level_str, "Entry": round(entry_price,5), "SL": round(sl_price,5), "Lot": round(lot,2), "Risk $": round(risk,2) }
            entry_data_list.append(leg)

            for tp_key, target_price in tp_prices.items():
                profit, rr = 0.0, 0.0
                if stop_dist > 1e-9:
                    dist = abs(target_price - entry_price)
                    is_valid_tp = (direction=="Long" and target_price > entry_price) or \
                                  (direction=="Short" and target_price < entry_price)
                    if is_valid_tp:
                        profit = lot * dist
                        rr = dist / stop_dist
                        results_by_tp[tp_key]['rr_list'].append(rr)
                results_by_tp[tp_key]['total_profit'] += profit

            extension_prices[fibo_level_str] = {}
            extension_results[fibo_level_str] = {}
            extension_ratios = [1.618, 2.618, 4.326]
            for ratio in extension_ratios:
                ext_price = (high_fibo + range_fibo * (ratio - 1)) if direction == "Long" else (low_fibo - range_fibo * (ratio - 1))
                extension_prices[fibo_level_str][str(ratio)] = round(ext_price, 5)
                ext_profit, ext_rr = 0.0, 0.0
                if stop_dist > 1e-9:
                    ext_dist = abs(ext_price - entry_price)
                    if (direction=="Long" and ext_price > entry_price) or (direction=="Short" and ext_price < entry_price):
                        ext_profit = lot * ext_dist
                        ext_rr = ext_dist / stop_dist
                extension_results[fibo_level_str][str(ratio)] = {'profit': round(ext_profit, 2), 'avg_rr': round(ext_rr, 2)}

    except ValueError as ve: error_message = str(ve)
    except Exception as ex: error_message = f"คำนวณ FIBO ผิดพลาด: {ex}"

    for tp_key, vals in results_by_tp.items():
        clean_rr_list = [r for r in vals['rr_list'] if pd.notna(r) and r > 0]
        if clean_rr_list:
            results_by_tp[tp_key]['avg_rr'] = np.mean(clean_rr_list)

    return {
        "total_lots": total_lots, "total_risk_dollar": total_risk_dollar_calculated,
        "results_by_tp": results_by_tp, "tp_prices": tp_prices, "entry_data": entry_data_list,
        "extension_prices": extension_prices, "extension_results": extension_results,
        "direction": direction, "error_message": error_message,
    }


def calculate_custom_trade_plan(
    num_entries_custom: int,
    risk_pct_custom_input: float,
    custom_entries_details: list,
    current_active_balance: float
):
    # This function remains unchanged as it is working correctly.
    entry_data_list = []
    total_lots = 0.0
    total_risk_dollar_calculated = 0.0
    total_profit_at_primary_tp = 0.0
    temp_rr_list = []
    summary_direction = "N/A"
    error_message = None
    long_count, short_count = 0, 0

    try:
        if num_entries_custom <= 0: raise ValueError("เลือกจำนวนไม้ (CUSTOM) มากกว่า 0")
        if risk_pct_custom_input <= 0: raise ValueError("Risk % (CUSTOM) ต้องมากกว่า 0")

        total_risk_dollar = current_active_balance * (risk_pct_custom_input/100.0)
        risk_per_leg = total_risk_dollar / num_entries_custom

        for i in range(num_entries_custom):
            d = custom_entries_details[i]
            e_str, s_str, t_str = d["entry_str"], d["sl_str"], d["tp_str"]
            try:
                entry_val = float(e_str)
                sl_val    = float(s_str)
                tp_val    = float(t_str) if t_str and float(t_str)>0 else 0.0
            except (ValueError, TypeError):
                entry_data_list.append({ "Entry": e_str, "SL": s_str, "TP": t_str, "Lot":"Error", "Risk $":f"{risk_per_leg:.2f}", "RR":"Error","TP (RR≈3)":"Error" })
                total_risk_dollar_calculated += risk_per_leg
                continue

            stop_dist = abs(entry_val - sl_val)
            if stop_dist>1e-9:
                lot = risk_per_leg/stop_dist
                risk = lot*stop_dist
                profit, rr = 0.0, 0.0
                if tp_val>0:
                    dist_tp = abs(tp_val-entry_val)
                    valid = (entry_val > sl_val and tp_val > entry_val) or (entry_val < sl_val and tp_val < entry_val)
                    if valid and dist_tp > 1e-9:
                        rr = dist_tp / stop_dist
                        profit = lot * dist_tp
                        temp_rr_list.append(rr)
                        total_profit_at_primary_tp += profit
            else:
                lot, risk, rr, profit = 0.0, risk_per_leg, 0.0, 0.0

            if entry_val > sl_val: long_count += 1
            elif entry_val < sl_val: short_count += 1

            total_lots += lot
            total_risk_dollar_calculated += risk

            tp_rr3 = (entry_val + 3*stop_dist) if entry_val > sl_val else (entry_val - 3*stop_dist) if stop_dist > 1e-9 else "N/A"

            entry_data_list.append({
                "Entry": round(entry_val,5), "SL": round(sl_val,5), "TP": round(tp_val,5) if tp_val > 0 else "N/A",
                "Lot": round(lot,2), "Risk $": round(risk,2), "RR": round(rr,2) if rr > 0 else "N/A",
                "TP (RR≈3)": tp_rr3 if isinstance(tp_rr3,str) else round(tp_rr3,5)
            })

        if long_count == num_entries_custom and short_count == 0: summary_direction = "Long"
        elif short_count == num_entries_custom and long_count == 0: summary_direction = "Short"
        elif long_count > 0 and short_count > 0: summary_direction = "Mixed"

    except Exception as e: error_message = f"คำนวณ CUSTOM ผิดพลาด: {e}"

    avg_rr = np.mean([r for r in temp_rr_list if pd.notna(r) and r>0]) if temp_rr_list else 0.0

    return {
        "total_lots": total_lots, "total_risk_dollar": total_risk_dollar_calculated, "avg_rr": avg_rr,
        "total_profit_at_primary_tp": total_profit_at_primary_tp, "entry_data": entry_data_list,
        "direction": summary_direction, "error_message": error_message
    }
