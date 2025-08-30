import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import numpy as np

# Correct relative import for a module within the same package
from .supabase_handler import SupabaseHandler

class AnalyticsEngine:
    """
    A class to encapsulate all analytical functions for the trading dashboard.
    It performs various trading analytics and calculations.
    """
    def __init__(self, supabase_handler: SupabaseHandler = None):
        """
        Initializes the AnalyticsEngine.
        Args:
            supabase_handler (SupabaseHandler, optional): An instance of SupabaseHandler.
                                                         Defaults to None.
        """
        self.supabase = supabase_handler

    def _ensure_utc_datetime(self, series: pd.Series) -> pd.Series:
        """
        Ensures a pandas Series of datetime objects is timezone-aware (UTC)
        for consistent comparisons. This is now a method of the class.
        """
        if not pd.api.types.is_datetime64_any_dtype(series):
            series = pd.to_datetime(series, errors='coerce')
        series = series.dropna()
        if series.empty:
            return series
        if series.dt.tz is None:
            return series.dt.tz_localize(pytz.utc)
        elif series.dt.tz != pytz.utc:
            return series.dt.tz_convert(pytz.utc)
        return series

    def calculate_total_net_profit(self, df_actual_trades: pd.DataFrame) -> float:
        """
        Calculates the total net profit from actual trades.
        Args:
            df_actual_trades (pd.DataFrame): DataFrame containing actual trade data.
                                             Expected columns: 'Profit'.
        Returns:
            float: Total net profit.
        """
        if df_actual_trades.empty or 'Profit' not in df_actual_trades.columns:
            return 0.0
        # Ensure 'Profit' column is numeric, coercing errors to NaN
        df_actual_trades['Profit'] = pd.to_numeric(df_actual_trades['Profit'], errors='coerce')
        return df_actual_trades['Profit'].sum()

    def calculate_win_rate(self, df_actual_trades: pd.DataFrame) -> float:
        """
        Calculates the win rate from actual trades.
        Args:
            df_actual_trades (pd.DataFrame): DataFrame containing actual trade data.
                                             Expected columns: 'Profit'.
        Returns:
            float: Win rate in percentage.
        """
        if df_actual_trades.empty or 'Profit' not in df_actual_trades.columns:
            return 0.0
        
        # Ensure 'Profit' column is numeric
        df_actual_trades['Profit'] = pd.to_numeric(df_actual_trades['Profit'], errors='coerce')
        
        total_trades = len(df_actual_trades.dropna(subset=['Profit']))
        if total_trades == 0:
            return 0.0
        
        winning_trades = df_actual_trades[df_actual_trades['Profit'] > 0].dropna(subset=['Profit'])
        return (len(winning_trades) / total_trades) * 100

    def calculate_profit_factor(self, df_actual_trades: pd.DataFrame) -> float:
        """
        Calculates the profit factor from actual trades.
        Args:
            df_actual_trades (pd.DataFrame): DataFrame containing actual trade data.
                                             Expected columns: 'Profit'.
        Returns:
            float: Profit factor.
        """
        if df_actual_trades.empty or 'Profit' not in df_actual_trades.columns:
            return 0.0
        
        # Ensure 'Profit' column is numeric
        df_actual_trades['Profit'] = pd.to_numeric(df_actual_trades['Profit'], errors='coerce')
        
        gross_profit = df_actual_trades[df_actual_trades['Profit'] > 0]['Profit'].sum()
        gross_loss = abs(df_actual_trades[df_actual_trades['Profit'] < 0]['Profit'].sum())
        
        if gross_loss == 0:
            return gross_profit # Avoid division by zero, if no losses, profit factor is gross_profit
        return round(gross_profit / gross_loss, 2)

    def calculate_max_drawdown(self, df_statement_summaries: pd.DataFrame) -> float:
        """
        Calculates the maximum drawdown from statement summaries.
        Args:
            df_statement_summaries (pd.DataFrame): DataFrame containing statement summary data.
                                                   Expected columns: 'Equity'.
        Returns:
            float: Maximum drawdown in percentage.
        """
        if df_statement_summaries.empty or 'Equity' not in df_statement_summaries.columns:
            return 0.0
        
        # Ensure 'Equity' column is numeric
        df_statement_summaries['Equity'] = pd.to_numeric(df_statement_summaries['Equity'], errors='coerce')
        
        # Drop rows where Equity is NaN
        df_statement_summaries = df_statement_summaries.dropna(subset=['Equity'])
        
        if df_statement_summaries.empty:
            return 0.0

        # Calculate cumulative max equity
        cumulative_max = df_statement_summaries['Equity'].cummax()
        # Calculate drawdown
        drawdown = (cumulative_max - df_statement_summaries['Equity']) / cumulative_max
        
        if drawdown.empty:
            return 0.0
        
        max_drawdown = drawdown.max() * 100
        return round(max_drawdown, 2)

    def get_today_drawdown(self, df_logs: pd.DataFrame) -> float:
        """
        Calculates the total drawdown for today from planned trade logs.
        This function is now a method of the class.
        """
        if df_logs is None or df_logs.empty:
            return 0.0
        df_logs_cleaned = df_logs.copy()
        if 'Timestamp' not in df_logs_cleaned.columns:
            return 0.0
        df_logs_cleaned['Timestamp'] = self._ensure_utc_datetime(df_logs_cleaned['Timestamp'])
        df_logs_cleaned.dropna(subset=['Timestamp'], inplace=True)
        if df_logs_cleaned.empty or 'Risk $' not in df_logs_cleaned.columns:
            return 0.0
        today_utc = datetime.now(pytz.utc).date()
        df_today = df_logs_cleaned[df_logs_cleaned["Timestamp"].dt.date == today_utc]
        drawdown = df_today["Risk $"].sum()
        return float(drawdown) if pd.notna(drawdown) else 0.0

    def get_performance(self, df_logs: pd.DataFrame, period="week"):
        """
        Calculates performance metrics (winrate, gain, total trades) for a given period.
        This function is now a method of the class.
        """
        if df_logs is None or df_logs.empty:
            return 0.0, 0.0, 0
        df_logs_cleaned = df_logs.copy()
        if 'Timestamp' not in df_logs_cleaned.columns:
            return 0.0, 0.0, 0
        df_logs_cleaned['Timestamp'] = self._ensure_utc_datetime(df_logs_cleaned['Timestamp'])
        df_logs_cleaned.dropna(subset=['Timestamp'], inplace=True)
        if df_logs_cleaned.empty or 'Risk $' not in df_logs_cleaned.columns:
            return 0.0, 0.0, 0
        now_utc = datetime.now(pytz.utc)
        if period == "week":
            start_date = now_utc - pd.Timedelta(days=now_utc.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # month
            start_date = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        df_period = df_logs_cleaned[df_logs_cleaned["Timestamp"] >= start_date]
        win = df_period[df_period["Risk $"] > 0].shape[0]
        loss = df_period[df_period["Risk $"] <= 0].shape[0]
        total_trades = win + loss
        winrate = (100 * win / total_trades) if total_trades > 0 else 0.0
        gain = df_period["Risk $"].sum()
        return float(winrate), float(gain) if pd.notna(gain) else 0.0, int(total_trades)

    def calculate_simulated_drawdown(self, df_trades: pd.DataFrame, starting_balance: float) -> float:
        """
        Calculates simulated drawdown from a DataFrame of trades.
        This function is now a method of the class.
        """
        if df_trades is None or df_trades.empty or 'Risk $' not in df_trades.columns:
            return 0.0
        max_dd = 0.0
        current_balance = starting_balance
        peak_balance = starting_balance
        df_calc = df_trades.copy()
        if "Timestamp" in df_calc.columns:
            df_calc['Timestamp'] = self._ensure_utc_datetime(df_calc['Timestamp'])
            df_calc.dropna(subset=['Timestamp'], inplace=True)
            df_calc = df_calc.sort_values(by="Timestamp", ascending=True)
        else:
            df_calc['Risk $'] = pd.to_numeric(df_calc['Risk $'], errors='coerce').fillna(0.0)
        for pnl in df_calc["Risk $"]:
            current_balance += pnl
            if current_balance > peak_balance:
                peak_balance = current_balance
            drawdown = peak_balance - current_balance
            if drawdown > max_dd:
                max_dd = drawdown
        return max_dd

    def analyze_planned_trades_for_ai(
        self,
        df_all_planned_logs: pd.DataFrame,
        active_portfolio_id: str = None,
        active_portfolio_name: str = "ทั่วไป (ไม่ได้เลือกพอร์ต)",
        balance_for_simulation: float = 10000.0
    ):
        """
        Analyzes planned trade logs for AI insights.
        This function is now a method of the class.
        """
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
        if 'Risk $' not in df_to_analyze.columns: df_to_analyze['Risk $' ] = 0.0
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
        results["max_drawdown_simulated"] = self.calculate_simulated_drawdown(df_to_analyze, balance_for_simulation)
        if "Timestamp" in df_to_analyze.columns:
            df_to_analyze['Timestamp'] = self._ensure_utc_datetime(df_to_analyze['Timestamp'])
            df_daily_pnl = df_to_analyze.dropna(subset=["Timestamp"])
            if not df_daily_pnl.empty:
                df_daily_pnl["Weekday"] = df_daily_pnl["Timestamp"].dt.day_name()
                daily_pnl_sum = df_daily_pnl.groupby("Weekday")["Risk $"].sum()
                if not daily_pnl_sum.empty:
                    if daily_pnl_sum.max() > 0: results["best_day"] = daily_pnl_sum.idxmax()
                    if daily_pnl_sum.min() < 0: results["worst_day"] = daily_pnl_sum.idxmin()
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
        self,
        df_all_actual_trades: pd.DataFrame,
        active_portfolio_id: str = None,
        active_portfolio_name: str = "ทั่วไป (ไม่ได้เลือกพอร์ต)"
    ):
        """
        Analyzes actual trade data for AI insights.
        This function is now a method of the class.
        """
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
        if results["total_deals"] > 0:
            if results["win_rate"] >= 50: results["insights"].append(f"✅ Win Rate (ผลจริง: {results['win_rate']:.1f}%) อยู่ในเกณฑ์ดี")
            else: results["insights"].append(f"📉 Win Rate (ผลจริง: {results['win_rate']:.1f}%) ควรปรับปรุง")
            try: pf_numeric = float(results["profit_factor"])
            except (ValueError, TypeError): pf_numeric = 0.0
            if "∞" in results["profit_factor"] or pf_numeric > 1.5: results["insights"].append(f"📈 Profit Factor (ผลจริง: {results['profit_factor']}) อยู่ในระดับที่ดี")
            elif pf_numeric < 1.0 and results["total_deals"] >= 10: results["insights"].append(f"⚠️ Profit Factor (ผลจริง: {results['profit_factor']}) ต่ำกว่า 1 บ่งชี้ว่าขาดทุนมากกว่ากำไร")
        if not results["insights"] and results["data_found"]: results["insights"].append("ข้อมูลผลการเทรดจริงกำลังถูกรวบรวม โปรดตรวจสอบ Insights เพิ่มเติมในอนาคต")
        return results

    def get_dashboard_analytics_for_actual(self, df_all_actual_trades: pd.DataFrame, df_all_statement_summaries: pd.DataFrame, active_portfolio_id: str) -> dict:
        """
        Generates dashboard analytics specifically for actual trades and statement summaries.
        This function is now a method of the class.
        """
        results = {
            "data_found": False,
            "error_message": "",
            "metrics": {},
            "balance_curve_data": pd.DataFrame()
        }
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
        df_actual['Profit_Deal'] = pd.to_numeric(df_actual['Profit_Deal'], errors='coerce').fillna(0)
        total_deals = len(df_actual)
        winning_deals = df_actual[df_actual['Profit_Deal'] > 0]
        losing_deals = df_actual[df_actual['Profit_Deal'] < 0]
        gross_profit = winning_deals['Profit_Deal'].sum()
        gross_loss = losing_deals['Profit_Deal'].sum()
        total_net_profit = gross_profit + gross_loss
        win_rate = (len(winning_deals) / total_deals) * 100 if total_deals > 0 else 0
        profit_factor = 0
        if gross_loss != 0:
            profit_factor = abs(gross_profit / gross_loss)
        
        # Ensure 'Time_Deal' and 'Balance_Deal' exist and are processed correctly for balance curve
        if 'Time_Deal' in df_actual.columns and 'Balance_Deal' in df_actual.columns:
            df_actual['Time_Deal'] = self._ensure_utc_datetime(df_actual['Time_Deal'])
            # Ensure Balance_Deal is numeric
            df_actual['Balance_Deal'] = pd.to_numeric(df_actual['Balance_Deal'], errors='coerce')
            df_actual.dropna(subset=['Time_Deal', 'Balance_Deal'], inplace=True) # Drop rows with missing essential data
            
            if not df_actual.empty:
                balance_curve_df = df_actual.sort_values(by='Time_Deal')[['Time_Deal', 'Balance_Deal']].rename(
                    columns={'Time_Deal': 'Time', 'Balance_Deal': 'Balance'}
                ).set_index('Time')
                results["balance_curve_data"] = balance_curve_df
        else:
            results["balance_curve_data"] = pd.DataFrame(columns=['Time', 'Balance']).set_index('Time') # Empty DataFrame with correct index
            results["error_message"] += " (Missing 'Time_Deal' or 'Balance_Deal' for balance curve)"

        results["metrics"] = {
            "Total Net Profit": total_net_profit,
            "Total Deals": total_deals,
            "Win Rate (%)": win_rate,
            "Profit Factor": profit_factor,
            "Gross Profit": gross_profit,
            "Gross Loss": gross_loss
        }
        
        # Max Drawdown from statement summaries
        if active_portfolio_id and not df_all_statement_summaries.empty:
            df_summary = df_all_statement_summaries[df_all_statement_summaries['PortfolioID'] == str(active_portfolio_id)].copy()
            if not df_summary.empty:
                # Use the class method for max drawdown calculation
                max_dd_percent = self.calculate_max_drawdown(df_summary)
                results["metrics"]["Max Drawdown (%)"] = max_dd_percent
            else:
                results["metrics"]["Max Drawdown (%)"] = 0.0 # Default if no summaries for portfolio
        else:
            results["metrics"]["Max Drawdown (%)"] = 0.0 # Default if no summaries at all

        return results

    def analyze_combined_trades_for_ai(
        self,
        df_planned: pd.DataFrame,
        df_actual: pd.DataFrame,
        active_portfolio_id: str = None,
        active_portfolio_name: str = "ทั่วไป"
    ):
        """
        Analyzes combined planned and actual trade data for AI insights.
        This function is now a method of the class.
        """
        results = {
            "report_title_suffix": f"(พอร์ต: '{active_portfolio_name}' - วิเคราะห์เชิงลึก)",
            "insights": [],
            "error_message": None,
            "data_found": False
        }
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
        df_a['Time_Deal'] = self._ensure_utc_datetime(df_a['Time_Deal'])
        df_a['Profit_Deal'] = pd.to_numeric(df_a['Profit_Deal'], errors='coerce').fillna(0)
        df_a.dropna(subset=['Time_Deal'], inplace=True)
        df_p['Timestamp'] = self._ensure_utc_datetime(df_p['Timestamp'])
        df_p['Risk $'] = pd.to_numeric(df_p['Risk $'], errors='coerce').fillna(0)

        # Daily and Monthly PnL analysis for actual trades
        if not df_a.empty:
            df_a["Weekday"] = df_a["Time_Deal"].dt.day_name()
            daily_pnl = df_a.groupby("Weekday")['Profit_Deal'].sum()
            if not daily_pnl.empty:
                best_day = daily_pnl.idxmax()
                worst_day = daily_pnl.idxmin()
                if daily_pnl.get(best_day, 0) > 0:
                    results["insights"].append(f"📈 [เวลา] คุณทำกำไรได้ดีที่สุดในวัน '{best_day}' ({daily_pnl[best_day]:,.2f} USD)")
                if daily_pnl.get(worst_day, 0) < 0:
                    results["insights"].append(f"📉 [เวลา] คุณมักจะขาดทุนมากที่สุดในวัน '{worst_day}' ({daily_pnl[worst_day]:,.2f} USD)")
            
            df_a["Month"] = df_a["Time_Deal"].dt.strftime('%Y-%m')
            monthly_pnl = df_a.groupby("Month")['Profit_Deal'].sum()
            if not monthly_pnl.empty and len(monthly_pnl) > 1:
                best_month = monthly_pnl.idxmax()
                worst_month = monthly_pnl.idxmin()
                if monthly_pnl[best_month] > 0:
                    results["insights"].append(f"🗓️ [เวลา] เดือน '{best_month}' เป็นเดือนที่คุณทำกำไรได้ดีที่สุด")
                if monthly_pnl[worst_month] < 0:
                    results["insights"].append(f"🗓️ [เวลา] เดือน '{worst_month}' เป็นเดือนที่ควรระมัดระวังเป็นพิเศษ")
        
        # Symbol performance comparison (Planned vs Actual)
        if 'Symbol' in df_p.columns and 'Symbol_Deal' in df_a.columns: # Changed to Symbol_Deal for actual
            df_a.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True, errors='ignore') # Ensure 'Symbol' column exists in df_a
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
        
        # Behavior insights (e.g., missed trades)
        if 'Setup' in df_p.columns and 'Type_Deal' in df_a.columns:
            planned_shorts = df_p[df_p['Setup'].str.contains("Short", case=False, na=False)].shape[0]
            actual_sells = df_a[df_a['Type_Deal'].str.contains("sell", case=False, na=False)].shape[0]
            if planned_shorts > actual_sells + (planned_shorts * 0.2): # If planned shorts are significantly more than actual sells
                results["insights"].append(f"🤔 [พฤติกรรม] คุณมีแนวโน้มที่จะ 'ตกรถ' (ไม่ได้เข้าเทรดตามแผน) ใน Setup ฝั่ง Short มากกว่าฝั่ง Long")
        
        if not results["insights"]:
            results["insights"].append("ยังไม่พบ Insight เชิงลึกที่ชัดเจนในขณะนี้ ระบบกำลังรวบรวมข้อมูลเพิ่มเติม")
        return results

    def generate_risk_alerts(
        self,
        df_planned_logs: pd.DataFrame,
        daily_drawdown_limit_pct: float,
        current_balance: float
    ) -> list:
        """
        Generates risk alerts based on planned drawdown and daily limits.
        This function is now a method of the class.
        """
        alerts = []
        drawdown_today = self.get_today_drawdown(df_planned_logs) # Use class method
        if drawdown_today >= 0:
            return alerts
        if current_balance <= 0 or daily_drawdown_limit_pct <= 0:
            return alerts
        drawdown_limit_absolute = -abs(current_balance * (daily_drawdown_limit_pct / 100.0))
        if drawdown_today <= drawdown_limit_absolute:
            alert_message = (
                f"คุณถึงลิมิตขาดทุนรายวันแล้ว! "
                f"(ขาดทุน: {drawdown_today:,.2f} / ลิมิต: {drawdown_limit_absolute:,.2f} USD)"
            )
            alerts.append({'level': 'error', 'message': alert_message})
            return alerts
        warning_threshold = drawdown_limit_absolute * 0.8
        if drawdown_today <= warning_threshold:
            alert_message = (
                f"โปรดระวัง! คุณใกล้ถึงลิมิตขาดทุนรายวันแล้ว "
                f"(ขาดทุน: {drawdown_today:,.2f} / ลิมิต: {drawdown_limit_absolute:,.2f} USD)"
            )
            alerts.append({'level': 'warning', 'message': alert_message})
        return alerts

    def generate_weekly_summary(self, df_all_actual_trades: pd.DataFrame, active_portfolio_id: str) -> str | None:
        """
        Generates a weekly performance summary from actual trades.
        This function is now a method of the class.
        """
        if df_all_actual_trades.empty or not active_portfolio_id:
            return None
        df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
        if 'Time_Deal' in df.columns:
            df['Time_Deal'] = pd.to_datetime(df['Time_Deal'], errors='coerce')
            df.dropna(subset=['Time_Deal'], inplace=True)
        else:
            return None
        if 'Profit_Deal' in df.columns:
            df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
        else:
            return None
        if 'Symbol_Deal' in df.columns:
            df.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True, errors='ignore')
        
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=7)
        
        # Ensure Time_Deal is timezone-aware before comparison
        df['Time_Deal'] = self._ensure_utc_datetime(df['Time_Deal'])
        
        week_df = df[df['Time_Deal'] >= start_date].copy()
        if week_df.empty or len(week_df) < 3: # Require at least 3 trades for a meaningful summary
            return None
        
        net_profit = week_df['Profit_Deal'].sum()
        total_trades = len(week_df)
        win_trades = len(week_df[week_df['Profit_Deal'] > 0])
        win_rate = (100 * win_trades / total_trades) if total_trades > 0 else 0
        
        summary_lines = []
        summary_lines.append(f"ภาพรวมสัปดาห์ที่ผ่านมา: กำไรสุทธิ {net_profit:,.2f} USD, Win Rate {win_rate:.1f}%.")
        
        week_df['Weekday'] = week_df['Time_Deal'].dt.day_name()
        daily_pnl = week_df.groupby('Weekday')['Profit_Deal'].sum()
        if not daily_pnl.empty:
            best_day = daily_pnl.idxmax()
            worst_day = daily_pnl.idxmin()
            if daily_pnl.get(best_day, 0) > 0:
                summary_lines.append(f"🗓️ วันที่ดีที่สุดคือวัน **{best_day}** (กำไร {daily_pnl[best_day]:,.2f} USD).")
            if daily_pnl.get(worst_day, 0) < 0:
                summary_lines.append(f"📉 วันที่ควรระวังคือวัน **{worst_day}** (ขาดทุน {daily_pnl[worst_day]:,.2f} USD).")
        
        best_Symbol = None
        if 'Symbol' in week_df.columns:
            Symbol_pnl = week_df.groupby('Symbol')['Profit_Deal'].sum()
            if not Symbol_pnl.empty and Symbol_pnl.max() > 0:
                best_Symbol = Symbol_pnl.idxmax()
                summary_lines.append(f"💰 สินทรัพย์ที่ทำกำไรสูงสุดคือ **{best_Symbol}**.")
        
        return " ".join(summary_lines)

    def find_user_strengths(
        self,
        df_all_actual_trades: pd.DataFrame,
        active_portfolio_id: str,
        min_trades_threshold: int = 5,
        win_rate_threshold: float = 60.0,
        profit_factor_threshold: float = 1.5
    ) -> list[str]:
        """
        Analyzes actual trades for a given portfolio to find trading strengths (e.g., Symbol-Direction pairs).
        This function is now a method of the class.
        """
        if df_all_actual_trades.empty or not active_portfolio_id:
            return []
        df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
        if 'Symbol_Deal' in df.columns:
            df.rename(columns={'Symbol_Deal': 'Symbol'}, inplace=True)
        df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
        trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
        df_trades = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)].copy()
        
        if len(df_trades) < min_trades_threshold:
            return []
        if 'Symbol' not in df_trades.columns or 'Type_Deal' not in df_trades.columns:
            return []
        
        df_trades['Direction'] = np.where(df_trades['Type_Deal'].str.lower() == 'buy', 'Long', 'Short')
        
        agg_functions = {
            'Profit_Deal': [
                ('total_trades', 'count'),
                ('winning_trades', lambda x: (x > 0).sum()),
                ('gross_profit', lambda x: x[x > 0].sum()),
                ('gross_loss', lambda x: abs(x[x < 0].sum()))
            ]
        }
        
        grouped = df_trades.groupby(['Symbol', 'Direction']).agg(agg_functions)
        grouped.columns = grouped.columns.droplevel(0) # Remove multi-level index
        
        grouped['win_rate'] = (grouped['winning_trades'] / grouped['total_trades']) * 100
        grouped['profit_factor'] = grouped['gross_profit'] / grouped['gross_loss']
        
        # Handle cases where gross_loss is zero (infinite profit factor)
        is_infinite = np.isinf(grouped['profit_factor'])
        grouped.loc[is_infinite, 'profit_factor'] = grouped.loc[is_infinite, 'gross_profit'] # Set to gross_profit if no losses
        grouped.fillna({'profit_factor': 0}, inplace=True) # Fill NaN profit factors (e.g., no trades)
        
        strong_setups_df = grouped[
            (grouped['total_trades'] >= min_trades_threshold) &
            (grouped['win_rate'] >= win_rate_threshold) &
            (grouped['profit_factor'] >= profit_factor_threshold)
        ]
        
        strengths = []
        if not strong_setups_df.empty:
            for index, row in strong_setups_df.iterrows():
                symbol, direction = index
                strengths.append(f"{symbol}-{direction}")
        
        return strengths

    def get_advanced_statistics(self, df_all_actual_trades: pd.DataFrame, active_portfolio_id: str) -> dict:
        """
        Calculates advanced trading statistics (e.g., recent form, biggest wins/losses, streaks).
        This function is now a method of the class.
        """
        if df_all_actual_trades.empty or not active_portfolio_id:
            return {}
        df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
        trade_types_to_exclude = ['balance', 'credit', 'deposit', 'withdrawal']
        df = df[~df['Type_Deal'].str.lower().isin(trade_types_to_exclude)].copy()
        if df.empty:
            return {}
        
        df['Time_Deal'] = self._ensure_utc_datetime(df['Time_Deal'])
        df = df.sort_values(by='Time_Deal', ascending=False)
        df['Profit_Deal'] = pd.to_numeric(df['Profit_Deal'], errors='coerce').fillna(0)
        
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
        
        # Calculate streaks (max consecutive wins/losses)
        df_rev = df.iloc[::-1].copy() # Reverse for streak calculation
        df_rev['outcome'] = np.sign(df_rev['Profit_Deal']) # 1 for win, -1 for loss, 0 for break-even
        
        # Identify streaks
        streaks = df_rev['outcome'].groupby((df_rev['outcome'] != df_rev['outcome'].shift()).cumsum()).cumcount() + 1
        
        results['max_consecutive_wins'] = streaks[df_rev['outcome'] == 1].max()
        results['max_consecutive_losses'] = streaks[df_rev['outcome'] == -1].max()

        # Profit concentration
        total_profit = df[df['Profit_Deal'] > 0]['Profit_Deal'].sum()
        if total_profit > 0:
            daily_pnl = df.groupby(df['Time_Deal'].dt.date)['Profit_Deal'].sum()
            best_day_profit = daily_pnl[daily_pnl > 0].max()
            results['profit_concentration'] = (best_day_profit / total_profit) * 100
        else:
            results['profit_concentration'] = 0

        # Active trading days in last 30 days
        thirty_days_ago = datetime.now(pytz.utc) - timedelta(days=30)
        results['active_trading_days'] = df[df['Time_Deal'] >= thirty_days_ago]['Time_Deal'].dt.date.nunique()
        
        return results

    # The calculate_stats method was a placeholder. If it's not used, it can be removed.
    # If it's intended to be a general stats calculator, it needs more logic.
    def calculate_stats(self, df: pd.DataFrame) -> dict:
        """
        Calculates key trading statistics from a DataFrame.
        This is a placeholder and needs to be implemented based on requirements.
        """
        stats = {
            "total_trades": len(df),
            "win_rate": 0.0, # Placeholder
            "average_profit": 0.0, # Placeholder
            "total_profit": df['Profit_Deal'].sum() if 'Profit_Deal' in df.columns else 0.0
        }
        # Example: if you want to calculate win_rate here
        if 'Profit_Deal' in df.columns and len(df) > 0:
            winning_trades = df[df['Profit_Deal'] > 0]
            stats['win_rate'] = (len(winning_trades) / len(df)) * 100
            stats['average_profit'] = df['Profit_Deal'].mean()
        return stats
