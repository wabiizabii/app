# core/analytics_engine.py (รวมฟังก์ชัน Analytics ทั้งหมด)
import streamlit as st #
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_today_drawdown(df_logs: pd.DataFrame) -> float:
   
    if df_logs is None or df_logs.empty:
        return 0.0

    today_str = datetime.now().strftime("%Y-%m-%d")
    df_logs_cleaned = df_logs.copy()

    # Ensure 'Timestamp' column exists and is of datetime type
    if 'Timestamp' not in df_logs_cleaned.columns:
        return 0.0
    if not pd.api.types.is_datetime64_any_dtype(df_logs_cleaned['Timestamp']):
        df_logs_cleaned['Timestamp'] = pd.to_datetime(df_logs_cleaned['Timestamp'], errors='coerce')

    # Drop rows where timestamp conversion failed
    df_logs_cleaned.dropna(subset=['Timestamp'], inplace=True)

    if 'Risk $' not in df_logs_cleaned.columns:
        return 0.0
        
    df_today = df_logs_cleaned[df_logs_cleaned["Timestamp"].dt.strftime("%Y-%m-%d") == today_str]
    drawdown = df_today["Risk $"].sum()
    
    return float(drawdown) if pd.notna(drawdown) else 0.0


def get_performance(df_logs, period="week"):
   
    if df_logs is None or df_logs.empty:
        return 0.0, 0.0, 0

    df_logs_cleaned = df_logs.copy()
    if 'Timestamp' not in df_logs_cleaned.columns or not pd.api.types.is_datetime64_any_dtype(df_logs_cleaned['Timestamp']):
        df_logs_cleaned['Timestamp'] = pd.to_datetime(df_logs_cleaned['Timestamp'], errors='coerce')
    
    df_logs_cleaned.dropna(subset=['Timestamp'], inplace=True)
    if 'Risk $' not in df_logs_cleaned.columns:
        return 0.0, 0.0, 0

    now = datetime.now()
    if period == "week":
        start_date = now - pd.Timedelta(days=now.weekday())
        df_period = df_logs_cleaned[df_logs_cleaned["Timestamp"] >= start_date.replace(hour=0, minute=0, second=0, microsecond=0)]
    else:  # month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        df_period = df_logs_cleaned[df_logs_cleaned["Timestamp"] >= start_date]
    
    win = df_period[df_period["Risk $"] > 0].shape[0]
    loss = df_period[df_period["Risk $"] <= 0].shape[0]
    total_trades = win + loss
    winrate = (100 * win / total_trades) if total_trades > 0 else 0.0
    gain = df_period["Risk $"].sum()
    return float(winrate), float(gain) if pd.notna(gain) else 0.0, int(total_trades)


def calculate_simulated_drawdown(df_trades: pd.DataFrame, starting_balance: float) -> float:
    
    if df_trades is None or df_trades.empty or 'Risk $' not in df_trades.columns:
        return 0.0

    max_dd = 0.0
    current_balance = starting_balance
    peak_balance = starting_balance
    
    df_calc = df_trades.copy()
    if "Timestamp" in df_calc.columns and pd.api.types.is_datetime64_any_dtype(df_calc['Timestamp']):
        df_calc = df_calc.sort_values(by="Timestamp", ascending=True)

    for pnl in df_calc["Risk $"]:
        current_balance += pnl
        if current_balance > peak_balance:
            peak_balance = current_balance
        drawdown = peak_balance - current_balance
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd


def analyze_planned_trades_for_ai(
    df_all_planned_logs: pd.DataFrame,
    active_portfolio_id: str = None,
    active_portfolio_name: str = "ทั่วไป (ไม่ได้เลือกพอร์ต)",
    balance_for_simulation: float = 10000.0
):
   
    results = {
        "report_title_suffix": "(จากข้อมูลแผนเทรดทั้งหมด)", "total_trades": 0, "win_rate": 0.0,
        "gross_pnl": 0.0, "avg_rr": "N/A", "max_drawdown_simulated": 0.0, "best_day": "-",
        "worst_day": "-", "insights": [], "error_message": None, "data_found": False
    }

    if active_portfolio_id:
        results["report_title_suffix"] = f"(พอร์ต: '{active_portfolio_name}' - จากแผน)"

    if df_all_planned_logs is None or df_all_planned_logs.empty:
        results["error_message"] = f"ไม่พบข้อมูลแผนเทรดใน Log สำหรับพอร์ต '{active_portfolio_name}'." if active_portfolio_id else "ยังไม่มีข้อมูลแผนเทรดใน Log สำหรับวิเคราะห์"
        return results

    df_to_analyze = df_all_planned_logs.copy()
    if active_portfolio_id and 'PortfolioID' in df_to_analyze.columns:
        df_to_analyze = df_to_analyze[df_to_analyze['PortfolioID'] == str(active_portfolio_id)]

    if df_to_analyze.empty:
        results["error_message"] = f"ไม่พบข้อมูลแผนเทรดที่ตรงเงื่อนไขสำหรับพอร์ต '{active_portfolio_name}'" if active_portfolio_id else "ไม่พบข้อมูลแผนเทรดที่ตรงเงื่อนไข"
        return results

    results["data_found"] = True
    if 'Risk $' not in df_to_analyze.columns: df_to_analyze['Risk $'] = 0.0
    df_to_analyze['Risk $'] = pd.to_numeric(df_to_analyze['Risk $'], errors='coerce').fillna(0.0)

    results["total_trades"] = df_to_analyze.shape[0]
    win_trades = df_to_analyze[df_to_analyze["Risk $"] > 0].shape[0]
    results["win_rate"] = (100 * win_trades / results["total_trades"]) if results["total_trades"] > 0 else 0.0
    results["gross_pnl"] = df_to_analyze["Risk $"].sum()

    if "RR" in df_to_analyze.columns:
        rr_series = pd.to_numeric(df_to_analyze["RR"], errors='coerce').dropna()
        if not rr_series.empty:
            avg_rr_val = rr_series[rr_series > 0].mean()
            if pd.notna(avg_rr_val): results["avg_rr"] = f"{avg_rr_val:.2f}"
    
    results["max_drawdown_simulated"] = calculate_simulated_drawdown(df_to_analyze, balance_for_simulation)

    if "Timestamp" in df_to_analyze.columns and pd.api.types.is_datetime64_any_dtype(df_to_analyze['Timestamp']):
        df_daily_pnl = df_to_analyze.dropna(subset=["Timestamp"])
        if not df_daily_pnl.empty:
            df_daily_pnl["Weekday"] = df_daily_pnl["Timestamp"].dt.day_name()
            daily_pnl_sum = df_daily_pnl.groupby("Weekday")["Risk $"].sum()
            if not daily_pnl_sum.empty:
                if daily_pnl_sum.max() > 0: results["best_day"] = daily_pnl_sum.idxmax()
                if daily_pnl_sum.min() < 0: results["worst_day"] = daily_pnl_sum.idxmin()

    # Generate insights
    if results["total_trades"] > 0:
        if results["win_rate"] >= 60: results["insights"].append(f"✅ Winrate (แผน: {results['win_rate']:.1f}%) สูง: ระบบการวางแผนมีแนวโน้มที่ดี")
        elif results["win_rate"] < 40 and results["total_trades"] >= 10: results["insights"].append(f"⚠️ Winrate (แผน: {results['win_rate']:.1f}%) ต่ำ: ควรทบทวนกลยุทธ์การวางแผน")
        try: avg_rr_numeric = float(results["avg_rr"])
        except (ValueError, TypeError): avg_rr_numeric = None
        if avg_rr_numeric is not None and avg_rr_numeric < 1.5 and results["total_trades"] >= 5: results["insights"].append(f"📉 RR เฉลี่ย (แผน: {results['avg_rr']}) ต่ำกว่า 1.5: อาจต้องพิจารณาการตั้ง TP/SL")
        if balance_for_simulation > 0 and results["max_drawdown_simulated"] > (balance_for_simulation * 0.10):
            dd_percent = (results['max_drawdown_simulated'] / balance_for_simulation) * 100
            results["insights"].append(f"🚨 Max Drawdown (จำลองจากแผน: {results['max_drawdown_simulated']:,.2f} USD) ค่อนข้างสูง ({dd_percent:.1f}% ของ Balance)")
    if not results["insights"] and results["data_found"]: results["insights"].append("ดูเหมือนว่าข้อมูลแผนเทรดที่วิเคราะห์ยังไม่มีจุดที่น่ากังวลเป็นพิเศษ")
    return results

def analyze_actual_trades_for_ai(
    df_all_actual_trades: pd.DataFrame,
    active_portfolio_id: str = None,
    active_portfolio_name: str = "ทั่วไป (ไม่ได้เลือกพอร์ต)"
):
    
    results = {
        "report_title_suffix": "(จากข้อมูลผลการเทรดจริงทั้งหมด)", "total_deals": 0, "win_rate": 0.0,
        "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": "0.00", "avg_profit_deal": 0.0,
        "avg_loss_deal": 0.0, "insights": [], "error_message": None, "data_found": False
    }

    if active_portfolio_id:
        results["report_title_suffix"] = f"(พอร์ต: '{active_portfolio_name}' - จากผลจริง)"

    if df_all_actual_trades is None or df_all_actual_trades.empty:
        results["error_message"] = f"ไม่พบข้อมูลผลการเทรดจริงใน Log สำหรับพอร์ต '{active_portfolio_name}'." if active_portfolio_id else "ยังไม่มีข้อมูลผลการเทรดจริงใน Log สำหรับวิเคราะห์"
        return results

    df_to_analyze = df_all_actual_trades.copy()
    if active_portfolio_id and 'PortfolioID' in df_to_analyze.columns:
        df_to_analyze = df_to_analyze[df_to_analyze['PortfolioID'] == str(active_portfolio_id)]

    if df_to_analyze.empty:
        results["error_message"] = f"ไม่พบข้อมูลผลการเทรดจริงที่ตรงเงื่อนไขสำหรับพอร์ต '{active_portfolio_name}'" if active_portfolio_id else "ไม่พบข้อมูลผลการเทรดจริงที่ตรงเงื่อนไข"
        return results
    
    if 'Profit_Deal' not in df_to_analyze.columns:
        results["error_message"] = "AI (Actual): ไม่พบคอลัมน์ 'Profit_Deal' ในข้อมูลผลการเทรดจริง"
        return results

    df_to_analyze['Profit_Deal'] = pd.to_numeric(df_to_analyze['Profit_Deal'], errors='coerce').fillna(0.0)
    df_trading_deals = df_to_analyze[~df_to_analyze.get('Type_Deal', pd.Series(dtype=str)).str.lower().isin(['balance', 'credit', 'deposit', 'withdrawal'])].copy()

    if df_trading_deals.empty:
        results["error_message"] = "ไม่พบรายการ Deals ที่เป็นการซื้อขายจริงสำหรับวิเคราะห์"
        return results
    
    results["data_found"] = True
    results["total_deals"] = len(df_trading_deals)
    
    winning_deals_df = df_trading_deals[df_trading_deals['Profit_Deal'] > 0]
    losing_deals_df = df_trading_deals[df_trading_deals['Profit_Deal'] < 0]

    results["win_rate"] = (100 * len(winning_deals_df) / results["total_deals"]) if results["total_deals"] > 0 else 0.0
    results["gross_profit"] = winning_deals_df['Profit_Deal'].sum()
    results["gross_loss"] = abs(losing_deals_df['Profit_Deal'].sum())

    if results["gross_loss"] > 0: results["profit_factor"] = f"{results['gross_profit'] / results['gross_loss']:.2f}"
    elif results["gross_profit"] > 0: results["profit_factor"] = "∞ (No Losses)"
    
    results["avg_profit_deal"] = results["gross_profit"] / len(winning_deals_df) if len(winning_deals_df) > 0 else 0.0
    results["avg_loss_deal"] = results["gross_loss"] / len(losing_deals_df) if len(losing_deals_df) > 0 else 0.0

    # Generate insights
    if results["total_deals"] > 0:
        if results["win_rate"] >= 50: results["insights"].append(f"✅ Win Rate (ผลจริง: {results['win_rate']:.1f}%) อยู่ในเกณฑ์ดี")
        else: results["insights"].append(f"📉 Win Rate (ผลจริง: {results['win_rate']:.1f}%) ควรปรับปรุง")
        try: pf_numeric = float(results["profit_factor"])
        except (ValueError, TypeError): pf_numeric = 0.0
        if "∞" in results["profit_factor"] or pf_numeric > 1.5: results["insights"].append(f"📈 Profit Factor (ผลจริง: {results['profit_factor']}) อยู่ในระดับที่ดี")
        elif pf_numeric < 1.0 and results["total_deals"] >= 10: results["insights"].append(f"⚠️ Profit Factor (ผลจริง: {results['profit_factor']}) ต่ำกว่า 1 บ่งชี้ว่าขาดทุนมากกว่ากำไร")
    if not results["insights"] and results["data_found"]: results["insights"].append("ข้อมูลผลการเทรดจริงกำลังถูกรวบรวม โปรดตรวจสอบ Insights เพิ่มเติมในอนาคต")
    
    return results


def get_dashboard_analytics_for_actual(df_all_actual_trades, df_all_statement_summaries, active_portfolio_id):
    
    results = {
        "data_found": False,
        "error_message": "",
        "metrics": {},
        "balance_curve_data": pd.DataFrame()
    }

    # Filter data for the active portfolio
    if active_portfolio_id:
        if not df_all_actual_trades.empty:
            df_actual = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == str(active_portfolio_id)].copy()
        else:
            df_actual = pd.DataFrame()
    else:
        df_actual = df_all_actual_trades.copy()

    if df_actual.empty:
        results["error_message"] = "ไม่พบข้อมูล 'ผลการเทรดจริง' ในพอร์ตที่เลือก"
        return results

    results["data_found"] = True

    # Ensure 'Profit_Deal' is numeric
    df_actual['Profit_Deal'] = pd.to_numeric(df_actual['Profit_Deal'], errors='coerce').fillna(0)

    # Calculate metrics
    total_deals = len(df_actual)
    winning_deals = df_actual[df_actual['Profit_Deal'] > 0]
    losing_deals = df_actual[df_actual['Profit_Deal'] < 0]

    gross_profit = winning_deals['Profit_Deal'].sum()
    gross_loss = losing_deals['Profit_Deal'].sum()
    total_net_profit = gross_profit + gross_loss # gross_loss is negative

    win_rate = (len(winning_deals) / total_deals) * 100 if total_deals > 0 else 0
    
    profit_factor = 0
    if gross_loss != 0:
        profit_factor = abs(gross_profit / gross_loss)

    # Prepare data for balance curve chart
    if 'Time_Deal' in df_actual.columns and 'Balance_Deal' in df_actual.columns:
        df_actual['Time_Deal'] = pd.to_datetime(df_actual['Time_Deal'])
        balance_curve_df = df_actual.sort_values(by='Time_Deal')[['Time_Deal', 'Balance_Deal']].rename(
            columns={'Time_Deal': 'Time', 'Balance_Deal': 'Balance'}
        ).set_index('Time')
        results["balance_curve_data"] = balance_curve_df

    # Store calculated metrics
    results["metrics"] = {
        "Total Net Profit": total_net_profit,
        "Total Deals": total_deals,
        "Win Rate (%)": win_rate,
        "Profit Factor": profit_factor,
        "Gross Profit": gross_profit,
        "Gross Loss": gross_loss
    }

    # Get Max Drawdown from the latest statement summary for this portfolio
    if active_portfolio_id and not df_all_statement_summaries.empty:
        df_summary = df_all_statement_summaries[df_all_statement_summaries['PortfolioID'] == str(active_portfolio_id)].copy()
        if not df_summary.empty:
            # Assuming the summary sheet might have a Drawdown column from the report
            if 'Drawdown' in df_summary.columns:
                 # Get the latest non-null drawdown value
                latest_drawdown = df_summary.sort_values(by='Timestamp', ascending=False)['Drawdown'].dropna().iloc[0]
                results["metrics"]["Max Drawdown"] = pd.to_numeric(latest_drawdown, errors='coerce')

    return results

# ==============================================================================
# NEW: Combined Analysis Engine for Deeper AI Insights (As of June 2025)
# ==============================================================================

def analyze_combined_trades_for_ai(
    df_planned: pd.DataFrame,
    df_actual: pd.DataFrame,
    active_portfolio_id: str = None,
    active_portfolio_name: str = "ทั่วไป"
):
    
    results = {
        "report_title_suffix": f"(พอร์ต: '{active_portfolio_name}' - วิเคราะห์เชิงลึก)",
        "insights": [],
        "error_message": None,
        "data_found": False
    }

    # 1. Validate and Filter Data
    if df_planned is None or df_planned.empty or df_actual is None or df_actual.empty:
        results["error_message"] = "AI (Combined): ต้องการข้อมูลทั้ง 'แผนการเทรด' และ 'ผลเทรดจริง' เพื่อทำการวิเคราะห์เชิงลึก"
        return results

    df_p = df_planned.copy()
    df_a = df_actual.copy()

    if active_portfolio_id:
        if 'PortfolioID' in df_p.columns:
            df_p = df_p[df_p['PortfolioID'] == str(active_portfolio_id)]
        if 'PortfolioID' in df_a.columns:
            df_a = df_a[df_a['PortfolioID'] == str(active_portfolio_id)]

    if df_p.empty or df_a.empty:
        results["error_message"] = f"AI (Combined): ไม่พบข้อมูลแผนหรือผลการเทรดจริงสำหรับพอร์ต '{active_portfolio_name}'"
        return results

    results["data_found"] = True

    # 2. Prepare Data Columns
    df_a['Time_Deal'] = pd.to_datetime(df_a['Time_Deal'], errors='coerce')
    df_a['Profit_Deal'] = pd.to_numeric(df_a['Profit_Deal'], errors='coerce').fillna(0)
    df_a.dropna(subset=['Time_Deal'], inplace=True)
    
    df_p['Timestamp'] = pd.to_datetime(df_p['Timestamp'], errors='coerce')
    df_p['Risk $'] = pd.to_numeric(df_p['Risk $'], errors='coerce').fillna(0)
    
    # --- INSIGHT GENERATION ---

    # 3. Time-Based Performance Analysis (วิเคราะห์ประสิทธิภาพตามช่วงเวลา)
    if not df_a.empty:
        # By Day of Week
        df_a["Weekday"] = df_a["Time_Deal"].dt.day_name()
        daily_pnl = df_a.groupby("Weekday")['Profit_Deal'].sum()
        if not daily_pnl.empty:
            best_day = daily_pnl.idxmax()
            worst_day = daily_pnl.idxmin()
            if daily_pnl[best_day] > 0:
                results["insights"].append(f"📈 [เวลา] คุณทำกำไรได้ดีที่สุดในวัน '{best_day}' ({daily_pnl[best_day]:,.2f} USD)")
            if daily_pnl[worst_day] < 0:
                results["insights"].append(f"📉 [เวลา] คุณมักจะขาดทุนมากที่สุดในวัน '{worst_day}' ({daily_pnl[worst_day]:,.2f} USD)")

        # By Month
        df_a["Month"] = df_a["Time_Deal"].dt.strftime('%Y-%m')
        monthly_pnl = df_a.groupby("Month")['Profit_Deal'].sum()
        if not monthly_pnl.empty and len(monthly_pnl) > 1:
            best_month = monthly_pnl.idxmax()
            worst_month = monthly_pnl.idxmin()
            if monthly_pnl[best_month] > 0:
                 results["insights"].append(f"🗓️ [เวลา] เดือน '{best_month}' เป็นเดือนที่คุณทำกำไรได้ดีที่สุด")
            if monthly_pnl[worst_month] < 0:
                 results["insights"].append(f"🗓️ [เวลา] เดือน '{worst_month}' เป็นเดือนที่ควรระมัดระวังเป็นพิเศษ")


    # 4. Plan vs. Actual by Symbol (เปรียบเทียบผลงานตามสินทรัพย์)
    if 'Symbol' in df_p.columns and 'Symbol' in df_a.columns:
        plan_by_Symbol = df_p.groupby('Symbol')['Risk $'].sum()
        actual_by_Symbol = df_a.groupby('Symbol')['Profit_Deal'].sum()
        common_Symbols = set(plan_by_Symbol.index) & set(actual_by_Symbol.index)
        
        for Symbol in common_Symbols:
            plan_pnl = plan_by_Symbol.get(Symbol, 0)
            actual_pnl = actual_by_Symbol.get(Symbol, 0)
            if actual_pnl > plan_pnl and actual_pnl > 0:
                results["insights"].append(f"💡 [สินทรัพย์] ในคู่เงิน {Symbol}, ผลงานจริงของคุณ ({actual_pnl:,.2f} USD) ดีกว่าที่วางแผนไว้ ({plan_pnl:,.2f} USD)!")
            elif actual_pnl < 0 and actual_pnl < plan_pnl:
                 results["insights"].append(f"⚠️ [สินทรัพย์] ในคู่เงิน {Symbol}, ผลขาดทุนจริง ({actual_pnl:,.2f} USD) มากกว่าที่วางแผนไว้ ({plan_pnl:,.2f} USD)")

    # 5. Missed Trades Analysis (วิเคราะห์การ 'ตกรถ') - Approximation
    if 'Setup' in df_p.columns and 'Type_Deal' in df_a.columns:
        # Approximate by counting planned Long/Short vs actual buy/sell
        planned_shorts = df_p[df_p['Setup'].str.contains("Short", case=False, na=False)].shape[0]
        actual_sells = df_a[df_a['Type_Deal'].str.contains("sell", case=False, na=False)].shape[0]
        if planned_shorts > actual_sells + (planned_shorts * 0.2): # Allow for some variance
            results["insights"].append(f"🤔 [พฤติกรรม] คุณมีแนวโน้มที่จะ 'ตกรถ' (ไม่ได้เข้าเทรดตามแผน) ใน Setup ฝั่ง Short มากกว่าฝั่ง Long")

    if not results["insights"]:
        results["insights"].append("ยังไม่พบ Insight เชิงลึกที่ชัดเจนในขณะนี้ ระบบกำลังรวบรวมข้อมูลเพิ่มเติม")

    return results

def generate_risk_alerts(
    df_planned_logs: pd.DataFrame, 
    daily_drawdown_limit_pct: float, 
    current_balance: float
) -> list:
    
    alerts = []
    
    # 1. ดึงข้อมูล Drawdown ของแผนวันนี้ (ค่าจะเป็นลบถ้าขาดทุน)
    # เราจะใช้ฟังก์ชัน get_today_drawdown ที่เรามีอยู่แล้ว
    drawdown_today = get_today_drawdown(df_planned_logs)

    # ถ้าไม่ขาดทุน หรือกำไร ก็ไม่ต้องทำอะไรต่อ
    if drawdown_today >= 0:
        return alerts

    # 2. คำนวณลิมิตขาดทุนเป็นจำนวนเงิน (ค่าจะเป็นลบ)
    if current_balance <= 0 or daily_drawdown_limit_pct <= 0:
        return alerts # ไม่มีการแจ้งเตือนถ้า balance หรือ limit ไม่ถูกต้อง
        
    drawdown_limit_absolute = -abs(current_balance * (daily_drawdown_limit_pct / 100.0))

    # 3. ตรวจสอบเงื่อนไขเพื่อสร้างการแจ้งเตือน
    
    # เงื่อนไขที่ 1: ขาดทุนถึงลิมิตแล้ว
    if drawdown_today <= drawdown_limit_absolute:
        alert_message = (
            f"คุณถึงลิมิตขาดทุนรายวันแล้ว! "
            f"(ขาดทุน: {drawdown_today:,.2f} / ลิมิต: {drawdown_limit_absolute:,.2f} USD)"
        )
        alerts.append({'level': 'error', 'message': alert_message})
        return alerts # เมื่อถึงลิมิตแล้ว ไม่ต้องแสดงคำเตือนซ้ำ

    # เงื่อนไขที่ 2: ขาดทุนเข้าใกล้ลิมิต (เช่น เกิน 80% ของลิมิต)
    warning_threshold = drawdown_limit_absolute * 0.8
    if drawdown_today <= warning_threshold:
        alert_message = (
            f"โปรดระวัง! คุณใกล้ถึงลิมิตขาดทุนรายวันแล้ว "
            f"(ขาดทุน: {drawdown_today:,.2f} / ลิมิต: {drawdown_limit_absolute:,.2f} USD)"
        )
        alerts.append({'level': 'warning', 'message': alert_message})

    return alerts

def generate_weekly_summary(df_all_actual_trades: pd.DataFrame, active_portfolio_id: str) -> str | None:
    
    if df_all_actual_trades.empty or not active_portfolio_id:
        return None

    # 1. กรองข้อมูลเฉพาะพอร์ตที่เลือก
    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()

    # 2. เปลี่ยนชื่อคอลัมน์ 'Symbol_Deal' เป็น 'Symbol' เพื่อให้เป็นมาตรฐาน
    if 'Symbol_Deal' in df.columns:
        df.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True)
    
    # 3. เตรียมข้อมูลสำหรับการวิเคราะห์
    df['Time_Deal'] = pd.to_datetime(df['Time_Deal'], errors='coerce')
    df.dropna(subset=['Time_Deal', 'Profit_Deal'], inplace=True)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    week_df = df[df['Time_Deal'] >= start_date]

    if week_df.empty or len(week_df) < 3:
        return None

    # 4. คำนวณ Metrics ที่สำคัญ
    net_profit = week_df['Profit_Deal'].sum()
    total_trades = len(week_df)
    win_trades = len(week_df[week_df['Profit_Deal'] > 0])
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0

    # 5. หาข้อมูลเชิงลึก
    week_df['Weekday'] = week_df['Time_Deal'].dt.day_name()
    daily_pnl = week_df.groupby('Weekday')['Profit_Deal'].sum()
    best_day = daily_pnl.idxmax()
    worst_day = daily_pnl.idxmin()

    best_Symbol = None
    # ตรวจสอบก่อนว่ามีคอลัมน์ 'Symbol' จริงๆ ก่อนจะเรียกใช้
    if 'Symbol' in week_df.columns:
        Symbol_pnl = week_df.groupby('Symbol')['Profit_Deal'].sum()
        if not Symbol_pnl.empty and Symbol_pnl.max() > 0:
            best_Symbol = Symbol_pnl.idxmax()
    
    # 6. สร้างข้อความสรุป
    # 6. Generate summary text
    summary_lines = []
    summary_lines.append(f"Last week's overview: Net Profit {net_profit:,.2f} USD, Win Rate {win_rate:.1f}%.")
    
    if daily_pnl[best_day] > 0:
        summary_lines.append(f"🗓️ Your best day was **{best_day}** (Profit {daily_pnl[best_day]:,.2f} USD).")
    
    if daily_pnl[worst_day] < 0:
        summary_lines.append(f"📉 Be cautious on **{worst_day}** (Loss {daily_pnl[worst_day]:,.2f} USD).")

    if best_Symbol:
        summary_lines.append(f"💰 The most profitable asset was **{best_Symbol}**.")

    return " ".join(summary_lines)


def find_user_strengths(
    df_all_actual_trades: pd.DataFrame,
    active_portfolio_id: str,
    min_trades_threshold: int = 5,
    win_rate_threshold: float = 60.0,
    profit_factor_threshold: float = 1.5
) -> list[str]:
   
    if df_all_actual_trades.empty or not active_portfolio_id:
        return []

    # 1. กรองข้อมูลและเปลี่ยนชื่อคอลัมน์
    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
    if 'Symbol_Deal' in df.columns:
        df.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True)
    
    df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
    
    # 2. วิเคราะห์เฉพาะรายการที่เป็นการเทรดจริงๆ
    trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
    df_trades = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)].copy()
    
    if len(df_trades) < min_trades_threshold:
        return []
        
    # 3. สร้างคอลัมน์ Direction และตรวจสอบว่ามีคอลัมน์ Symbol ก่อน Groupby
    if 'Symbol' not in df_trades.columns:
        return [] # ถ้าไม่มีคอลัมน์ Symbol ก็ไม่สามารถวิเคราะห์ต่อได้
        
    df_trades['Direction'] = np.where(df_trades['Type_Deal'].str.lower() == 'buy', 'Long', 'Short')

    # 4. จัดกลุ่มและคำนวณสถิติ
    agg_functions = {
        'Profit_Deal': [
            ('total_trades', 'count'),
            ('winning_trades', lambda x: (x > 0).sum()),
            ('gross_profit', lambda x: x[x > 0].sum()),
            ('gross_loss', lambda x: abs(x[x < 0].sum()))
        ]
    }
    grouped = df_trades.groupby(['Symbol', 'Direction']).agg(agg_functions)
    grouped.columns = grouped.columns.droplevel(0)

    # 5. คำนวณ Win Rate และ Profit Factor
    grouped['win_rate'] = (grouped['winning_trades'] / grouped['total_trades']) * 100
    grouped['profit_factor'] = grouped['gross_profit'] / grouped['gross_loss']
    is_infinite = np.isinf(grouped['profit_factor'])
    grouped.loc[is_infinite, 'profit_factor'] = grouped.loc[is_infinite, 'gross_profit']
    grouped.fillna({'profit_factor': 0}, inplace=True)
    
    # 6. คัดเลือก "ท่าไม้ตาย"
    strong_setups_df = grouped[
        (grouped['total_trades'] >= min_trades_threshold) &
        (grouped['win_rate'] >= win_rate_threshold) &
        (grouped['profit_factor'] >= profit_factor_threshold)
    ]

    # 7. แปลงผลลัพธ์
    strengths = []
    if not strong_setups_df.empty:
        for index, row in strong_setups_df.iterrows():
            symbol, direction = index
            strengths.append(f"{symbol}-{direction}")

    return strengths





def get_advanced_statistics(df_all_actual_trades: pd.DataFrame, active_portfolio_id: str) -> dict:
    if df_all_actual_trades.empty or not active_portfolio_id:
        return {}

    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
    
    trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
    df = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)].copy()
    
    if df.empty:
        return {}
        
    df['Time_Deal'] = pd.to_datetime(df['Time_Deal'])
    df = df.sort_values(by='Time_Deal', ascending=False)
    df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)

    # [แก้ไข] เพิ่ม .str.strip() เพื่อตัดช่องว่าง และ .str.upper() เพื่อให้เป็นมาตรฐาน
    if 'DealDirection' in df.columns and not df['DealDirection'].isnull().all():
        df['Direction'] = df['DealDirection'].str.strip().str.upper()
    else:
        df['Direction'] = np.where(df['Type_Deal'].str.lower() == 'buy', 'LONG', 'SHORT')

    results = {}

    def _get_recent_form(df_direction, n=5):
        if df_direction.empty: return "N/A"
        recent_trades = df_direction.head(n)
        form = ["W" if p > 0 else "L" if p < 0 else "B" for p in recent_trades['Profit_Deal']]
        return "-".join(form)

    df_long = df[df['Direction'] == 'LONG']
    df_short = df[df['Direction'] == 'SHORT']
    
    results['recent_form_long'] = _get_recent_form(df_long)
    results['recent_form_short'] = _get_recent_form(df_short)

    results['biggest_win_long'] = df_long[df_long['Profit_Deal'] > 0]['Profit_Deal'].max()
    results['biggest_loss_long'] = df_long[df_long['Profit_Deal'] < 0]['Profit_Deal'].min()
    results['biggest_win_short'] = df_short[df_short['Profit_Deal'] > 0]['Profit_Deal'].max()
    results['biggest_loss_short'] = df_short[df_short['Profit_Deal'] < 0]['Profit_Deal'].min()
    
    df_rev = df.iloc[::-1].copy()
    df_rev['outcome'] = np.sign(df_rev['Profit_Deal'])
    streaks = df_rev['outcome'].groupby((df_rev['outcome'] != df_rev['outcome'].shift()).cumsum()).cumcount() + 1
    results['max_consecutive_wins'] = streaks[df_rev['outcome'] == 1].max()
    results['max_consecutive_losses'] = streaks[df_rev['outcome'] == -1].max()

    total_profit = df[df['Profit_Deal'] > 0]['Profit_Deal'].sum()
    if total_profit > 0:
        daily_pnl = df.groupby(df['Time_Deal'].dt.date)['Profit_Deal'].sum()
        best_day_profit = daily_pnl[daily_pnl > 0].max()
        results['profit_concentration'] = (best_day_profit / total_profit) * 100
    else:
        results['profit_concentration'] = 0

    thirty_days_ago = datetime.now() - timedelta(days=30)
    results['active_trading_days'] = df[df['Time_Deal'] > thirty_days_ago]['Time_Deal'].dt.normalize().nunique()
    
    return results

def get_full_dashboard_stats(df_all_actual_trades: pd.DataFrame, df_all_summaries: pd.DataFrame, active_portfolio_id: str) -> dict:
    """
    Calculates comprehensive dashboard statistics for a given portfolio.
    Prioritizes calculated values from actual trades,
    then overrides with latest summary values from StatementSummaries if available.
    """
    stats = {}

    # --- Part 1: Calculate core metrics from ActualTrades ---
    if not df_all_actual_trades.empty and active_portfolio_id:
        df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
        
        # Filter to actual trading deals only (exclude balance, credit, deposit, withdrawal)
        trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
        df = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)]
        
        if not df.empty:
            df['Time_Deal'] = pd.to_datetime(df['Time_Deal'], errors='coerce')
            df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
            
            # Determine trade direction
            if 'DealDirection' in df.columns and not df['DealDirection'].isnull().all():
                df['Direction'] = df['DealDirection'].str.strip().str.upper()
            else:
                df['Direction'] = np.where(df['Type_Deal'].str.lower() == 'buy', 'LONG', 'SHORT')

            # Populate basic stats from actual trades
            stats['Total_Trades'] = len(df)
            stats['Profit_Trades_Count'] = int((df['Profit_Deal'] > 0).sum())
            stats['Loss_Trades_Count'] = int((df['Profit_Deal'] < 0).sum())
            stats['Breakeven_Trades_Count'] = int((df['Profit_Deal'] == 0).sum()) # Assuming 0 profit is breakeven
            
            stats['Long_Trades_Count'] = int((df['Direction'] == 'LONG').sum())
            stats['Short_Trades_Count'] = int((df['Direction'] == 'SHORT').sum())

            stats['Gross_Profit'] = df[df['Profit_Deal'] > 0]['Profit_Deal'].sum()
            stats['Gross_Loss'] = df[df['Profit_Deal'] < 0]['Profit_Deal'].sum()
            stats['Total_Net_Profit'] = stats['Gross_Profit'] + stats['Gross_Loss'] # Gross_Loss is negative

            stats['Win_Rate'] = (stats['Profit_Trades_Count'] / stats['Total_Trades']) * 100 if stats['Total_Trades'] > 0 else 0
            stats['Profit_Factor'] = abs(stats['Gross_Profit'] / stats['Gross_Loss']) if stats['Gross_Loss'] != 0 else 0 # Corrected profit factor calculation
            
            stats['Largest_Profit_Trade'] = df['Profit_Deal'].max()
            stats['Largest_Loss_Trade'] = df['Profit_Deal'].min()

            stats['Average_Profit_Trade'] = stats['Gross_Profit'] / stats['Profit_Trades_Count'] if stats['Profit_Trades_Count'] > 0 else 0
            stats['Average_Loss_Trade'] = stats['Gross_Loss'] / stats['Loss_Trades_Count'] if stats['Loss_Trades_Count'] > 0 else 0
            
            win_rate_frac = stats['Win_Rate'] / 100
            stats['Expected_Payoff'] = (win_rate_frac * stats['Average_Profit_Trade']) - ((1 - win_rate_frac) * abs(stats['Average_Loss_Trade'])) if stats['Total_Trades'] > 0 else 0.0

            if 'Volume_Deal' in df.columns:
                stats['Average_Trade_Size'] = pd.to_numeric(df['Volume_Deal'], errors='coerce').mean()
            else:
                stats['Average_Trade_Size'] = 0.0
            
            # --- Max Consecutive Wins/Losses (Simplified from get_advanced_statistics if needed) ---
            df_rev = df.iloc[::-1].copy() # Reverse for streaks
            df_rev['outcome'] = np.sign(df_rev['Profit_Deal']) # 1 for win, -1 for loss, 0 for BE
            
            # Group consecutive outcomes and count them
            streaks = df_rev['outcome'].groupby((df_rev['outcome'] != df_rev['outcome'].shift()).cumsum()).cumcount() + 1
            
            stats['Max_Consecutive_Wins_Count'] = streaks[df_rev['outcome'] == 1].max() if (df_rev['outcome'] == 1).any() else 0
            stats['Max_Consecutive_Losses_Count'] = streaks[df_rev['outcome'] == -1].max() if (df_rev['outcome'] == -1).any() else 0

            # Calculate profit/loss for those max streaks (requires more complex logic, leave as 0 for now)
            stats['Max_Consecutive_Wins_Profit'] = 0.0 # To be calculated if needed
            stats['Max_Consecutive_Losses_Profit'] = 0.0 # To be calculated if needed

            # Other stats that are typically in StatementSummaries but can be calculated:
            stats['Active_Trading_Days_Total'] = df['Time_Deal'].dt.normalize().nunique()
            
            # Placeholder for today's PnL (actual trades for the current day)
            today_str = datetime.now().strftime('%Y-%m-%d')
            stats['Today_PnL_Actual'] = df[df['Time_Deal'].dt.strftime('%Y-%m-%d') == today_str]['Profit_Deal'].sum()


    # --- Part 2: Override/Supplement with data from the LATEST StatementSummaries entry ---
    # This ensures consistency with the report's own calculated values where appropriate.
    if not df_all_summaries.empty and active_portfolio_id:
        df_summary_filtered = df_all_summaries[df_all_summaries['PortfolioID'] == active_portfolio_id].copy()
        
        if not df_summary_filtered.empty and 'DateTime' in df_summary_filtered.columns:
            # Get the latest summary row for this portfolio
            latest_summary_row = df_summary_filtered.sort_values(by='DateTime', ascending=False).iloc[0]

            # Helper to safely get numeric value from summary row
            def get_summary_numeric(col_name, default_value=0.0):
                if col_name in latest_summary_row and pd.notna(latest_summary_row[col_name]):
                    # Attempt to clean and convert, as these might come as strings from GSheets
                    val = str(latest_summary_row[col_name]).replace('$', '').replace('%', '').replace(',', '').strip()
                    try: return float(val) if '.' in val or 'e' in val.lower() else int(val)
                    except ValueError: return default_value
                return default_value

            # Update stats with latest values from StatementSummaries, overriding calculated if preferred
            # This mapping should align with the headers in settings.WORKSHEET_STATEMENT_SUMMARIES
            stats['Balance'] = get_summary_numeric('Balance')
            stats['Equity'] = get_summary_numeric('Equity')
            stats['Free_Margin'] = get_summary_numeric('Free_Margin')
            stats['Margin'] = get_summary_numeric('Margin')
            stats['Floating_P_L'] = get_summary_numeric('Floating_P_L')
            stats['Margin_Level'] = get_summary_numeric('Margin_Level')
            stats['Credit_Facility'] = get_summary_numeric('Credit_Facility')
            stats['Deposit'] = get_summary_numeric('Deposit') # Total Deposit from Summary
            stats['Withdrawal'] = get_summary_numeric('Withdrawal') # Total Withdrawal from Summary
            
            # Gross/Net Profit (Total_Net_Profit is calculated from deals, Gross_Profit from summary text)
            if 'Gross_Profit' in latest_summary_row.index:
                stats['Gross_Profit'] = get_summary_numeric('Gross_Profit')
            if 'Gross_Loss' in latest_summary_row.index:
                stats['Gross_Loss'] = get_summary_numeric('Gross_Loss')
            
            # Performance Metrics
            if 'Profit_Factor' in latest_summary_row.index:
                stats['Profit_Factor'] = get_summary_numeric('Profit_Factor')
            if 'Recovery_Factor' in latest_summary_row.index:
                stats['Recovery_Factor'] = get_summary_numeric('Recovery_Factor')
            if 'Expected_Payoff' in latest_summary_row.index:
                stats['Expected_Payoff'] = get_summary_numeric('Expected_Payoff')
            if 'Sharpe_Ratio' in latest_summary_row.index:
                stats['Sharpe_Ratio'] = get_summary_numeric('Sharpe_Ratio')

            # Drawdown Metrics
            stats['Balance_Drawdown'] = get_summary_numeric('Balance_Drawdown') # If this field is ever populated
            stats['Balance_Drawdown_Absolute'] = get_summary_numeric('Balance_Drawdown_Absolute')
            stats['Maximal_Drawdown_Value'] = get_summary_numeric('Maximal_Drawdown_Value')
            stats['Maximal_Drawdown_Percent'] = get_summary_numeric('Maximal_Drawdown_Percent')
            stats['Balance_Drawdown_Relative_Percent'] = get_summary_numeric('Balance_Drawdown_Relative_Percent')
            stats['Balance_Drawdown_Relative_Value'] = get_summary_numeric('Balance_Drawdown_Relative_Value')

            # Trade Counts/Percentages (from Summary)
            stats['Total_Trades'] = int(get_summary_numeric('Total_Trades', default_value=0))
            stats['Profit_Trades_Count'] = int(get_summary_numeric('Profit_Trades_Count', default_value=0))
            stats['Profit_Trades_Percent'] = get_summary_numeric('Profit_Trades_Percent')
            stats['Loss_Trades_Count'] = int(get_summary_numeric('Loss_Trades_Count', default_value=0))
            stats['Loss_Trades_Percent'] = get_summary_numeric('Loss_Trades_Percent')
            stats['Long_Trades_Count'] = int(get_summary_numeric('Long_Trades_Count', default_value=0))
            stats['Long_Trades_Won_Percent'] = get_summary_numeric('Long_Trades_Won_Percent')
            stats['Short_Trades_Count'] = int(get_summary_numeric('Short_Trades_Count', default_value=0))
            stats['Short_Trades_Won_Percent'] = get_summary_numeric('Short_Trades_Won_Percent')

            # Largest/Average Trades
            stats['Largest_Profit_Trade'] = get_summary_numeric('Largest_Profit_Trade')
            stats['Average_Profit_Trade'] = get_summary_numeric('Average_Profit_Trade')
            stats['Largest_Loss_Trade'] = get_summary_numeric('Largest_Loss_Trade')
            stats['Average_Loss_Trade'] = get_summary_numeric('Average_Loss_Trade')

            # Consecutive Trades
            stats['Max_Consecutive_Wins_Count'] = int(get_summary_numeric('Max_Consecutive_Wins_Count', default_value=0))
            stats['Max_Consecutive_Wins_Profit'] = get_summary_numeric('Max_Consecutive_Wins_Profit')
            stats['Maximal_Consecutive_Profit_Value'] = get_summary_numeric('Maximal_Consecutive_Profit_Value')
            stats['Maximal_Consecutive_Profit_Count'] = int(get_summary_numeric('Maximal_Consecutive_Profit_Count', default_value=0))
            stats['Max_Consecutive_Losses_Count'] = int(get_summary_numeric('Max_Consecutive_Losses_Count', default_value=0))
            stats['Max_Consecutive_Losses_Profit'] = get_summary_numeric('Max_Consecutive_Losses_Profit')
            stats['Maximal_Consecutive_Loss_Value'] = get_summary_numeric('Maximal_Consecutive_Loss_Value')
            stats['Maximal_Consecutive_Loss_Count'] = int(get_summary_numeric('Maximal_Consecutive_Loss_Count', default_value=0))
            stats['Average_Consecutive_Wins'] = int(get_summary_numeric('Average_Consecutive_Wins', default_value=0))
            stats['Average_Consecutive_Losses'] = int(get_summary_numeric('Average_Consecutive_Losses', default_value=0))

    return stats


def get_ai_powered_insights(df_all_actual_trades: pd.DataFrame, active_portfolio_id: str) -> dict:
    """
    วิเคราะห์ข้อมูลการเทรดเพื่อหาข้อมูลเชิงลึกที่น่าสนใจ
    - วันที่เทรดดีที่สุด/แย่ที่สุด
    - คู่เงินที่ทำกำไร/ขาดทุนมากที่สุด
    - ประสิทธิภาพ Long vs. Short
    """
    if df_all_actual_trades.empty or not active_portfolio_id:
        return {}

    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
    
    trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
    df = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)]
    
    if df.empty:
        return {}

    # --- ตรรกะการวิเคราะห์ข้อมูล ---
    df['Time_Deal'] = pd.to_datetime(df['Time_Deal'])
    df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
    
    if 'DealDirection' in df.columns and not df['DealDirection'].isnull().all():
        df['Direction'] = df['DealDirection'].str.strip().str.upper()
    else:
        df['Direction'] = np.where(df['Type_Deal'].str.lower() == 'buy', 'LONG', 'SHORT')

    if 'Symbol_Deal' in df.columns:
        df.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True, errors='ignore')
    
    insights = {}

    # 1. วิเคราะห์วันที่เทรดดีที่สุด/แย่ที่สุด
    df['day_of_week'] = df['Time_Deal'].dt.day_name()
    daily_pnl = df.groupby('day_of_week')['Profit_Deal'].sum()
    if not daily_pnl.empty:
        insights['best_day'] = (daily_pnl.idxmax(), daily_pnl.max())
        insights['worst_day'] = (daily_pnl.idxmin(), daily_pnl.min())

    # 2. วิเคราะห์คู่เงินที่ทำกำไร/ขาดทุนมากที่สุด
    if 'Symbol' in df.columns:
        symbol_pnl = df.groupby('Symbol')['Profit_Deal'].sum()
        if not symbol_pnl.empty:
            insights['best_pair'] = (symbol_pnl.idxmax(), symbol_pnl.max())
            insights['worst_pair'] = (symbol_pnl.idxmin(), symbol_pnl.min())

    # 3. วิเคราะห์ประสิทธิภาพ Long vs. Short
    direction_pnl = df.groupby('Direction')['Profit_Deal'].sum()
    insights['long_vs_short_pnl'] = (
        direction_pnl.get('LONG', 0.0),
        direction_pnl.get('SHORT', 0.0)
    )
    
    return insights

# core/analytics_engine.py

def calculate_true_equity_curve(df_summaries: pd.DataFrame, portfolio_id: str):
    """
    คำนวณ True Equity Curve, Realized Net Profit, Total Deposit, Total Withdrawal
    จาก DataFrame สรุป Statement.
    """
    # กรองข้อมูลสำหรับ Portfolio ที่เลือกและเรียงตาม Timestamp
    df_filtered = df_summaries[df_summaries['PortfolioID'] == portfolio_id].sort_values(by='Timestamp').copy()

    if df_filtered.empty:
        return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0 # คืนค่าเริ่มต้นที่เหมาะสม

    # --- ตรวจสอบและแปลงประเภทข้อมูล ---
    numeric_cols = ['Balance', 'Deposit', 'Withdrawal', 'Total_Net_Profit', 'Equity']
    for col in numeric_cols:
        if col not in df_filtered.columns:
            df_filtered[col] = 0.0

    # มั่นใจว่าเป็น numeric
    df_filtered['Balance'] = pd.to_numeric(df_filtered['Balance'], errors='coerce').fillna(0)
    df_filtered['Deposit'] = pd.to_numeric(df_filtered['Deposit'], errors='coerce').fillna(0)
    df_filtered['Withdrawal'] = pd.to_numeric(df_filtered['Withdrawal'], errors='coerce').fillna(0)
    df_filtered['Total_Net_Profit'] = pd.to_numeric(df_filtered['Total_Net_Profit'], errors='coerce').fillna(0)
    df_filtered['Equity'] = pd.to_numeric(df_filtered['Equity'], errors='coerce').fillna(0)


    # --- คำนวณ Metrics ที่ต้องการ ---
    df_filtered['Equity For Chart'] = df_filtered['Balance']

    total_deposit = df_filtered['Deposit'].sum()
    total_withdrawal = df_filtered['Withdrawal'].sum()

    initial_balance = df_filtered['Balance'].iloc[0] if not df_filtered.empty else 0
    final_balance = df_filtered['Balance'].iloc[-1] if not df_filtered.empty else 0

    realized_net_profit = final_balance - initial_balance + total_withdrawal - total_deposit
    
    # --- VVVV START EDIT (โค้ดที่แก้ไข) VVVV ---
    # เปลี่ยนจากการ .sum() เป็นการเลือกค่าจากแถวสุดท้าย (.iloc[-1]) ของข้อมูลที่เรียงตามเวลาแล้ว
    if not df_filtered.empty:
        total_net_profit_from_sheet = df_filtered['Total_Net_Profit'].iloc[-1]
    else:
        total_net_profit_from_sheet = 0.0
    # --- ^^^^ END EDIT ^^^^ ---

    return df_filtered, realized_net_profit, total_deposit, total_withdrawal, total_net_profit_from_sheet