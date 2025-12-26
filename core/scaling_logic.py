# core/scaling_logic.py
import pandas as pd
# Import get_performance from utils.helpers
from utils import helpers
# No direct st.session_state access here; values will be passed as parameters.

def get_scaling_suggestion(
    df_logs_for_analysis: pd.DataFrame,
    current_active_balance: float,
    current_risk_in_active_mode: float, # The risk % currently set for the active trade mode
    scaling_step_from_ui: float,
    max_risk_allowed_from_ui: float,
    min_risk_allowed_from_ui: float,
    active_trade_mode_name: str # e.g., "FIBO" or "CUSTOM"
):
    """
    Generates risk scaling suggestions based on performance from planned trade logs.
    Corresponds to logic in SEC 2.4.1 of main (1).py.
    """
    suggested_new_risk = current_risk_in_active_mode
    advice_message_parts = [f"Risk ปัจจุบัน (โหมด {active_trade_mode_name}): {current_risk_in_active_mode:.2f}%. "]
    winrate_weekly, gain_weekly, total_trades_weekly = 0.0, 0.0, 0

    if df_logs_for_analysis is None or df_logs_for_analysis.empty:
        advice_message_parts.append("ยังไม่มีข้อมูล Performance เพียงพอในสัปดาห์นี้ (จากแผนเทรด) หรือ Performance อยู่ในเกณฑ์คงที่.")
    else:
        # Get performance metrics for the week using the helper function
        # df_logs_for_analysis should already be filtered for the correct portfolio if applicable
        winrate_weekly, gain_weekly, total_trades_weekly = helpers.get_performance(df_logs_for_analysis, mode="week")

        if total_trades_weekly > 0:
            # Simplified logic based on original code:
            # Thresholds could be made more dynamic or passed as parameters if needed
            gain_threshold_for_scaleup = 0.02 * current_active_balance # 2% of current balance

            if winrate_weekly > 55 and gain_weekly > gain_threshold_for_scaleup: # Scale Up condition
                suggested_new_risk = min(current_risk_in_active_mode + scaling_step_from_ui, max_risk_allowed_from_ui)
                advice_message_parts.append(
                    f"<font color='lightgreen'>ผลงานดีเยี่ยม! (Winrate: {winrate_weekly:.1f}%, กำไรสัปดาห์: {gain_weekly:,.2f} USD)</font><br>"
                    f"<b>แนะนำเพิ่ม Risk% เป็น {suggested_new_risk:.2f}%</b>"
                )
            elif winrate_weekly < 45 or gain_weekly < 0: # Scale Down condition (gain < 0 implies loss)
                suggested_new_risk = max(current_risk_in_active_mode - scaling_step_from_ui, min_risk_allowed_from_ui)
                advice_message_parts.append(
                    f"<font color='salmon'>ควรพิจารณาลดความเสี่ยง (Winrate: {winrate_weekly:.1f}%, กำไรสัปดาห์: {gain_weekly:,.2f} USD)</font><br>"
                    f"<b>แนะนำลด Risk% เป็น {suggested_new_risk:.2f}%</b>"
                )
            else: # Maintain current risk
                advice_message_parts.append(f"คง Risk% ปัจจุบัน (Winrate สัปดาห์: {winrate_weekly:.1f}%, กำไร: {gain_weekly:,.2f} USD)")
        else:
            advice_message_parts.append("ยังไม่มีข้อมูล Performance เพียงพอในสัปดาห์นี้ (จากแผนเทรด) หรือ Performance อยู่ในเกณฑ์คงที่.")

    full_advice_message = "".join(advice_message_parts)

    return {
        "suggested_new_risk": suggested_new_risk,
        "advice_message": full_advice_message,
        "winrate_weekly": winrate_weekly,
        "gain_weekly": gain_weekly,
        "total_trades_weekly": total_trades_weekly
    }