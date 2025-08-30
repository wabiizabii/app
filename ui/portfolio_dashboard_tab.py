import streamlit as st
import pandas as pd
import numpy as np
import MetaTrader5 as mt5 
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Import handlers and config
from core.supabase_handler import SupabaseHandler
from core.mt5_handler import MT5Handler
from core.analytics_engine import AnalyticsEngine
from config import settings

# Instantiate AnalyticsEngine once and cache it, passing the SupabaseHandler.
@st.cache_resource
def get_analytics_engine(_db_handler):
    """
    Instantiates and caches the AnalyticsEngine.
    """
    return AnalyticsEngine(supabase_handler=_db_handler)

# Instantiate MT5Handler once and cache it.
@st.cache_resource
def get_mt5_handler():
    """
    Instantiates and caches the MT5Handler.
    """
    return MT5Handler()

# Cached function to load actual trades from Supabase
#@st.cache_data(ttl=3600)
def get_actual_trades_data(_db_handler_instance):
    """
    Loads all actual trades for caching.
    """
    return _db_handler_instance.load_actual_trades()

# Cached function to load planned trades from Supabase
#@st.cache_data(ttl=3600)
def get_planned_trades_data(_db_handler_instance, portfolio_id):
    """
    Loads all planned trade logs for caching.
    """
    return _db_handler_instance.load_all_planned_trade_logs()

#@st.cache_data(ttl=600) # Cache for 10 minutes
def get_account_history_data(_mt5_handler_instance, start_date_str, end_date_str):
    """
    Fetches account history (deals) from MT5 for a given date range.
    Returns a DataFrame with 'time_done', 'profit', 'balance', 'equity'.
    """
    deals = _mt5_handler_instance.get_account_history_deals(start_date_str, end_date_str)
    if deals.empty:
        return pd.DataFrame(columns=['time_done', 'profit', 'balance', 'equity'])
    
    # Ensure 'time_done' is datetime and sort
    deals['time_done'] = pd.to_datetime(deals['time_done'])
    deals = deals.sort_values(by='time_done')

    # Calculate running balance and equity from deals
    # This is a simplified approach, a true equity curve needs ticks or account history from MT5
    # For now, we'll use 'balance' and 'profit' from deals to simulate equity changes
    
    # Get initial balance from account info if possible
    account_info = _mt5_handler_instance.get_account_info()
    initial_balance = account_info['balance'] if account_info else 0.0

    equity_data = []
    current_balance = initial_balance
    current_equity = initial_balance # Start equity might be balance if no open trades

    # This part is tricky. MT5 deals don't directly give equity at each point.
    # We'll approximate by applying profit/loss from deals to balance.
    # For a true equity curve, we'd need account history data that includes equity.
    # MT5's history_deals only provides deals, not equity snapshots.
    # A more accurate way would be to fetch account history (balance, equity) from MT5.
    # For now, let's use a placeholder if we can't get proper equity history.
    
    # If we can't get detailed equity history, we will rely on actual trades from Supabase
    # or just show current equity.
    
    # Let's try to get account history from MT5 if available (deposits/withdrawals/profit)
    # This is an approximation. For true equity curve, it's best to get from MT5 directly.
    # For now, let's just return deals and let the analytics engine handle the equity curve from actual trades.
    
    # A better approach for equity curve from MT5:
    # Fetch all deals, calculate running balance. Equity would need open positions' P/L at each point.
    # Since MT5 API doesn't easily expose historical equity snapshots, we'll use actual trades.
    
    # Re-evaluating: The MT5Handler.get_account_history_deals() returns profit.
    # We can calculate a running balance/equity based on these profits and initial balance.
    
    if not deals.empty:
        # Get initial balance at the start of the period
        # This is a simplification; a real equity curve needs more granular data
        # For now, we'll assume the equity at the start of the first deal is the initial balance
        # or the balance at the start of the period.
        
        # We need to get the actual balance at the start_date_str for accuracy.
        # MT5 doesn't provide historical balance snapshots easily.
        # So, we'll rely on the AnalyticsEngine's equity curve calculation from actual trades.
        return pd.DataFrame(columns=['time_done', 'equity']) # Return empty if not using this for now

    return pd.DataFrame(columns=['time_done', 'equity']) # Placeholder, will use AnalyticsEngine for equity curve


def safe_float_convert(value, default=0.0):
    """
    Safely converts a value to a float, handling None, empty strings, and 'None' strings.
    """
    if value is None or (isinstance(value, str) and (value.strip().lower() == 'none' or value.strip() == '')):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def calculate_rr(row, df_planned_trades):
    """
    Helper function to calculate RR for open positions.
    """
    mt5_sl = safe_float_convert(row['StopLoss'])
    mt5_tp = safe_float_convert(row['TakeProfit'])
    mt5_price = safe_float_convert(row['Price']) # Open price from MT5

    if mt5_sl != 0.0 and not pd.isna(mt5_sl):
        risk_mt5 = abs(mt5_price - mt5_sl)
        if risk_mt5 > 0:
            if mt5_tp != 0.0 and not pd.isna(mt5_tp):
                reward_mt5 = abs(mt5_tp - mt5_price)
                return round(reward_mt5 / risk_mt5, 2)
            else:
                if not df_planned_trades.empty:
                    planned_matches = df_planned_trades[
                        (df_planned_trades['Symbol'] == row['Symbol']) &
                        (df_planned_trades['EntryTime'].dt.date == row['OpenTime'].date())
                    ]
                    if not planned_matches.empty:
                        closest_plan = planned_matches.iloc[(planned_matches['EntryTime'] - row['OpenTime']).abs().argsort()[:1]]
                        if not closest_plan.empty and pd.notna(closest_plan.iloc[0]['RR']):
                            return round(safe_float_convert(closest_plan.iloc[0]['RR']), 2)
    
    if not df_planned_trades.empty:
        planned_matches = df_planned_trades[
            (df_planned_trades['Symbol'] == row['Symbol']) &
            (df_planned_trades['EntryTime'].dt.date == row['OpenTime'].date())
        ]
        if not planned_matches.empty:
            closest_plan = planned_matches.iloc[(planned_matches['EntryTime'] - row['OpenTime']).abs().argsort()[:1]]
            if not closest_plan.empty and pd.notna(closest_plan.iloc[0]['RR']):
                return round(safe_float_convert(closest_plan.iloc[0]['RR']), 2)
    
    return "N/A"

def calculate_position_risk(row, asset_specs):
    """
    Helper function to calculate Risk ($) for each Position.
    """
    mt5_sl = safe_float_convert(row['StopLoss'])
    mt5_price = safe_float_convert(row['Price'])
    volume = safe_float_convert(row['Volume'])
    symbol = row['Symbol']

    if mt5_sl != 0.0 and not pd.isna(mt5_sl) and volume > 0:
        contract_size = asset_specs.get(symbol, {}).get('ContractSize', 1.0)
        calculated_risk = abs(mt5_price - mt5_sl) * volume * contract_size
        if calculated_risk < 0.05:
            return "BE"
        return round(calculated_risk, 2)
    return "No SL Set"

def get_pf_param(current_pf_details, param_name, default_value):
    """
    Safely gets a parameter from the portfolio details dictionary.
    """
    if current_pf_details and isinstance(current_pf_details, dict):
        val = current_pf_details.get(param_name)
        if pd.notna(val) and str(val).strip() != "":
            try: 
                return float(val)
            except (ValueError, TypeError): 
                pass
    return default_value

# --- Main Rendering Function ---
def render(db_handler):
    """
    Renders the Dashboard.
    """
    st.title("📊 Dashboard")

    active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
    current_pf_details = st.session_state.get('current_portfolio_details')
    mt5_equity = st.session_state.get('mt5_equity')
    mt5_connected = st.session_state.get('mt5_login') is not None # Check if MT5 login exists in session state

    if not active_portfolio_id:
        st.info("โปรดเลือก Portfolio จากแถบด้านข้างเพื่อดูข้อมูล Dashboard")
        return

    analytics_engine = get_analytics_engine(db_handler)
    mt5_handler = get_mt5_handler()

    df_actual_trades = get_actual_trades_data(db_handler)
    df_planned_trades = get_planned_trades_data(db_handler, active_portfolio_id)

    # Filter actual trades for the active portfolio
    if df_actual_trades is not None and not df_actual_trades.empty:
        df_portfolio_actual_trades = df_actual_trades[df_actual_trades['PortfolioID'] == active_portfolio_id].copy()
        # Ensure 'CloseTime' is datetime and sort
        df_portfolio_actual_trades['CloseTime'] = pd.to_datetime(df_portfolio_actual_trades['CloseTime'])
        df_portfolio_actual_trades = df_portfolio_actual_trades.sort_values(by='CloseTime')
    else:
        df_portfolio_actual_trades = pd.DataFrame()

    st.subheader("📈 ภาพรวมประสิทธิภาพ Portfolio")

    col1, col2, col3 = st.columns(3)

    # --- Overall Performance Metrics ---
    if not df_portfolio_actual_trades.empty:
        total_profit_loss = df_portfolio_actual_trades['Profit'].sum()
        total_trades = len(df_portfolio_actual_trades)
        profitable_trades = df_portfolio_actual_trades[df_portfolio_actual_trades['Profit'] > 0]
        losing_trades = df_portfolio_actual_trades[df_portfolio_actual_trades['Profit'] <= 0]
        
        win_rate = (len(profitable_trades) / total_trades) * 100 if total_trades > 0 else 0
        loss_rate = (len(losing_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        avg_win = profitable_trades['Profit'].mean() if not profitable_trades.empty else 0
        avg_loss = losing_trades['Profit'].mean() if not losing_trades.empty else 0 # Avg loss will be negative

        with col1:
            st.metric(label="กำไร/ขาดทุนรวม", value=f"{total_profit_loss:,.2f} USD", delta=f"{win_rate:,.2f}% Win Rate")
        with col2:
            st.metric(label="เฉลี่ยกำไรต่อเทรด", value=f"{avg_win:,.2f} USD")
        with col3:
            st.metric(label="เฉลี่ยขาดทุนต่อเทรด", value=f"{avg_loss:,.2f} USD")
        
        st.markdown("---")

        # --- Equity Curve ---
        st.subheader("📊 กราฟ Equity Portfolio")
        
        # Calculate equity curve from actual trades
        equity_curve_df = analytics_engine.calculate_equity_curve(df_portfolio_actual_trades, initial_balance=st.session_state.get('current_account_balance', settings.DEFAULT_ACCOUNT_BALANCE))
        
        if not equity_curve_df.empty:
            fig = px.line(equity_curve_df, x='Date', y='Equity', title='Equity Curve Over Time')
            fig.update_layout(xaxis_title="วันที่", yaxis_title="Equity (USD)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ไม่พบข้อมูลการเทรดที่ปิดแล้วสำหรับ Portfolio นี้เพื่อสร้างกราฟ Equity Curve")

        st.markdown("---")

        # --- Drawdown Metrics ---
        st.subheader("📉 ข้อมูล Drawdown")
        max_drawdown, max_drawdown_percent = analytics_engine.calculate_max_drawdown(df_portfolio_actual_trades, initial_balance=st.session_state.get('current_account_balance', settings.DEFAULT_ACCOUNT_BALANCE))
        
        col_dd1, col_dd2 = st.columns(2)
        with col_dd1:
            st.metric(label="Maximum Drawdown", value=f"{max_drawdown:,.2f} USD", delta=f"{max_drawdown_percent:,.2f}%")
        
        # Current Daily Drawdown from MT5 (if connected)
        if mt5_connected and mt5_equity is not None:
            daily_start_equity = st.session_state.get('mt5_daily_start_equity')
            if daily_start_equity is not None:
                live_daily_drawdown_amount = mt5_equity - daily_start_equity
                live_daily_drawdown_pct = (live_daily_drawdown_amount / daily_start_equity) * 100 if daily_start_equity != 0 else 0
                
                with col_dd2:
                    color_dd = 'green' if live_daily_drawdown_amount >= 0 else 'red'
                    st.markdown(
                        f"<p style='font-size: 0.9em; color: grey; margin-bottom: 0;'>Current Daily Drawdown</p>"
                        f"<p style='font-size: 1.5em; font-weight: bold; color:{color_dd}; margin-top: 0;'>{live_daily_drawdown_pct:+.2f}% (${live_daily_drawdown_amount:+.2f})</p>", 
                        unsafe_allow_html=True
                    )
            else:
                with col_dd2:
                    st.info("รอข้อมูล Daily Start Equity จาก MT5")
        else:
            with col_dd2:
                st.info("ไม่สามารถคำนวณ Current Daily Drawdown (MT5 ไม่ได้เชื่อมต่อ)")

        st.markdown("---")

        # --- Trade Analysis ---
        st.subheader("📊 การวิเคราะห์การเทรด")
        col_ta1, col_ta2 = st.columns(2)
        with col_ta1:
            st.metric(label="จำนวนเทรดทั้งหมด", value=f"{total_trades}")
        with col_ta2:
            st.metric(label="จำนวนเทรดที่ทำกำไร", value=f"{len(profitable_trades)}")
            st.metric(label="จำนวนเทรดที่ขาดทุน", value=f"{len(losing_trades)}")
        
        st.markdown("---")

        # --- Risk Metrics (from actual trades) ---
        st.subheader("🛡️ ข้อมูลความเสี่ยง")
        avg_risk_per_trade = df_portfolio_actual_trades['RiskAmount'].mean() if 'RiskAmount' in df_portfolio_actual_trades.columns and not df_portfolio_actual_trades.empty else 0
        st.metric(label="ความเสี่ยงเฉลี่ยต่อเทรด (USD)", value=f"{avg_risk_per_trade:,.2f} USD")

        # Total Risk Exposure from Open Positions (from MT5)
        st.markdown("#### ความเสี่ยงรวมจาก Position ที่เปิดอยู่ (Live MT5)")
        open_positions = mt5_handler.get_open_positions()
        if not open_positions.empty:
            active_account_type = current_pf_details.get('AccountType', 'STANDARD').upper() if current_pf_details else 'STANDARD'
            asset_specs = settings.ASSET_SPECIFICATIONS.get(active_account_type, {})
            
            open_positions['RR'] = open_positions.apply(lambda row: calculate_rr(row, df_planned_trades), axis=1)
            open_positions['Risk ($)'] = open_positions.apply(lambda row: calculate_position_risk(row, asset_specs), axis=1)
            
            numeric_risks = open_positions[open_positions['Risk ($)'] != "No SL Set"]['Risk ($)'].astype(float)
            total_open_positions_risk_sum = numeric_risks.sum()

            if abs(total_open_positions_risk_sum) < 0.05:
                st.success("RISK ปัจจุบัน: BE (Break-Even) - ความเสี่ยงรวมต่ำมาก")
            else:
                st.metric(label="ความเสี่ยงรวม", value=f"{total_open_positions_risk_sum:,.2f} USD")
            
            st.dataframe(open_positions[['OpenTime', 'Symbol', 'Type', 'Volume', 'Price', 'Profit', 'RR', 'Risk ($)']])
            if "No SL Set" in open_positions['Risk ($)'].values:
                st.error("⚠️ คำเตือน: มี Position ที่ไม่ได้ตั้ง Stop Loss! โปรดตั้ง SL เพื่อควบคุมความเสี่ยง")
        else:
            st.info("ไม่มี Position ที่เปิดอยู่")

        st.markdown("---")

        # --- User Strengths and Weaknesses ---
        st.subheader("💪 จุดแข็งและจุดอ่อนในการเทรด")
        user_strengths = analytics_engine.find_user_strengths(df_all_actual_trades=df_portfolio_actual_trades, active_portfolio_id=active_portfolio_id)
        user_weaknesses = analytics_engine.find_user_weaknesses(df_all_actual_trades=df_portfolio_actual_trades, active_portfolio_id=active_portfolio_id)

        if user_strengths:
            st.success("**จุดแข็งของคุณ:**")
            for strength in user_strengths:
                st.markdown(f"- {strength}")
        else:
            st.info("ยังไม่มีข้อมูลจุดแข็งที่ชัดเจน")

        if user_weaknesses:
            st.warning("**จุดอ่อนของคุณที่ควรปรับปรุง:**")
            for weakness in user_weaknesses:
                st.markdown(f"- {weakness}")
        else:
            st.info("ยังไม่มีข้อมูลจุดอ่อนที่ชัดเจน")

    else:
        st.info("ไม่พบข้อมูลการเทรดที่ปิดแล้วสำหรับ Portfolio นี้ กรุณาบันทึกการเทรดเพื่อดูข้อมูล Dashboard")

