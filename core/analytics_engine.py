# --- START: โค้ดที่เพิ่มเข้ามาสำหรับ Edge Score Dashboard ---
import pandas as pd
import numpy as np

def calculate_edge_score_metrics(df_all_actual_trades: pd.DataFrame, active_portfolio_id: str):
    """
    คำนวณ Metrics ทั้งหมดที่เกี่ยวข้องกับ Edge Score จากข้อมูลการเทรดจริง

    Args:
        df_all_actual_trades (pd.DataFrame): DataFrame ที่มีข้อมูลการเทรดจริงทั้งหมด
        active_portfolio_id (str): ID ของพอร์ตที่กำลังใช้งาน

    Returns:
        dict: Dictionary ที่มีค่าสถิติทั้งหมด หรือ None หากมีข้อมูลไม่เพียงพอ
    """
    if df_all_actual_trades is None or df_all_actual_trades.empty or not active_portfolio_id:
        return None

    # 1. กรองข้อมูลเฉพาะพอร์ตที่เลือก
    df = df_all_actual_trades[df_all_actual_trades['PortfolioID'] == active_portfolio_id].copy()
    if df.empty:
        return None

    # 2. แปลงชนิดข้อมูลให้ถูกต้องและคำนวณค่าพื้นฐาน
    df['Profit'] = pd.to_numeric(df['Profit'], errors='coerce').fillna(0)
    df['Time_Close'] = pd.to_datetime(df['Time_Close'], errors='coerce')
    df.dropna(subset=['Time_Close'], inplace=True)
    
    # 3. คำนวณ Metrics
    
    # === PILLAR 1: SKILL (ทักษะ) ===
    gross_profit = df[df['Profit'] > 0]['Profit'].sum()
    gross_loss = abs(df[df['Profit'] < 0]['Profit'].sum())
    total_net_profit = df['Profit'].sum()
    total_trades = len(df)
    
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    
    win_trades = df[df['Profit'] > 0]
    loss_trades = df[df['Profit'] < 0]
    win_rate = (len(win_trades) / total_trades) * 100 if total_trades > 0 else 0
    
    avg_win = win_trades['Profit'].mean() if not win_trades.empty else 0
    avg_loss = abs(loss_trades['Profit'].mean()) if not loss_trades.empty else 0
    
    expectancy = ((win_rate / 100) * avg_win) - (((100 - win_rate) / 100) * avg_loss)

    # === PILLAR 2: RISK MANAGEMENT (การบริหารความเสี่ยง) ===
    # Max Drawdown (คำนวณแบบง่ายจาก Profit/Loss)
    df_sorted = df.sort_values(by='Time_Close')
    df_sorted['Cumulative_Profit'] = df_sorted['Profit'].cumsum()
    df_sorted['Running_Max'] = df_sorted['Cumulative_Profit'].cummax()
    df_sorted['Drawdown'] = df_sorted['Running_Max'] - df_sorted['Cumulative_Profit']
    max_drawdown = df_sorted['Drawdown'].max()
    
    avg_rr_ratio = avg_win / avg_loss if avg_loss > 0 else np.inf

    # === PILLAR 3: CONSISTENCY (ความสม่ำเสมอ) ===
    # Profit Concentration (Best Day vs Total Profit)
    daily_profit = df.groupby(df['Time_Close'].dt.date)['Profit'].sum()
    best_day_profit = daily_profit.max()
    profit_concentration = (best_day_profit / total_net_profit) * 100 if total_net_profit > 0 and best_day_profit > 0 else 0
    
    # Standard Deviation of Daily Returns
    daily_returns_std = daily_profit.std()

    # === PILLAR 4: EXPERIENCE (ประสบการณ์) ===
    active_trading_days = df['Time_Close'].dt.normalize().nunique()

    # 4. รวบรวมผลลัพธ์
    metrics = {
        # Skill
        "profit_factor": profit_factor,
        "win_rate": win_rate,
        "expectancy": expectancy,
        # Risk
        "max_drawdown": max_drawdown,
        "average_loss": avg_loss * -1, # แสดงเป็นค่าติดลบ
        "average_rr_ratio": avg_rr_ratio,
        # Consistency
        "profit_concentration": profit_concentration,
        "daily_returns_std": daily_returns_std,
        # Experience
        "total_trades": total_trades,
        "active_trading_days": active_trading_days,
    }
    
    return metrics
# --- END: สิ้นสุดโค้ดที่เพิ่มเข้ามา ---