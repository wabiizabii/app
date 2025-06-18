# utils/helpers.py
import pandas as pd
from datetime import datetime
import numpy as np # numpy is used by pd.to_datetime and potentially in data handling
import hashlib

# ============== GENERAL UTILITY FUNCTIONS ==============
# Functions taken from PART 1.6 of main (1).py

def get_today_drawdown(log_source_df):
    if log_source_df.empty:
        return 0.0
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        # Ensure Timestamp is datetime before strftime
        if 'Timestamp' not in log_source_df.columns or not pd.api.types.is_datetime64_any_dtype(log_source_df['Timestamp']):
            log_source_df['Timestamp'] = pd.to_datetime(log_source_df['Timestamp'], errors='coerce')

        log_source_df_cleaned = log_source_df.dropna(subset=['Timestamp'])
        if 'Risk $' not in log_source_df_cleaned.columns:
            return 0.0

        df_today = log_source_df_cleaned[log_source_df_cleaned["Timestamp"].dt.strftime("%Y-%m-%d") == today_str]
        # Ensure "Risk $" is numeric; it should be after load_all_planned_trade_logs_from_gsheets
        drawdown = df_today["Risk $"].sum()
        return float(drawdown) if pd.notna(drawdown) else 0.0
    except KeyError as e:
        print(f"KeyError in get_today_drawdown: {e}")
        return 0.0
    except Exception as e:
        print(f"Exception in get_today_drawdown: {e}")
        return 0.0

def get_performance(log_source_df, mode="week"):
    if log_source_df.empty: return 0.0, 0.0, 0
    try:
        if 'Timestamp' not in log_source_df.columns or not pd.api.types.is_datetime64_any_dtype(log_source_df['Timestamp']):
            log_source_df['Timestamp'] = pd.to_datetime(log_source_df['Timestamp'], errors='coerce')

        log_source_df_cleaned = log_source_df.dropna(subset=['Timestamp'])
        if 'Risk $' not in log_source_df_cleaned.columns:
            return 0.0, 0.0, 0

        now = datetime.now()
        if mode == "week":
            week_start_date = now - pd.Timedelta(days=now.weekday())
            df_period = log_source_df_cleaned[log_source_df_cleaned["Timestamp"] >= week_start_date.replace(hour=0, minute=0, second=0, microsecond=0)]
        else:  # month
            month_start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            df_period = log_source_df_cleaned[log_source_df_cleaned["Timestamp"] >= month_start_date]

        win = df_period[df_period["Risk $"] > 0].shape[0]
        loss = df_period[df_period["Risk $"] <= 0].shape[0] # Assuming 0 or negative is a loss or break-even
        total_trades = win + loss
        winrate = (100 * win / total_trades) if total_trades > 0 else 0.0
        gain = df_period["Risk $"].sum()
        return float(winrate), float(gain) if pd.notna(gain) else 0.0, int(total_trades)
    except KeyError as e:
        print(f"KeyError in get_performance: {e}")
        return 0.0, 0.0, 0
    except Exception as e:
        print(f"Exception in get_performance: {e}")
        return 0.0, 0.0, 0
    
# ============== FILE HASHING UTILITY ==============
# เพิ่มฟังก์ชันนี้เข้าไปที่ท้ายไฟล์

def calculate_file_hash(file_bytes: bytes) -> str:
    """
    คำนวณค่าแฮช (SHA256) ของไฟล์จากข้อมูลที่เป็น bytes
    เพื่อใช้เป็นตัวระบุเอกลักษณ์ของไฟล์

    Args:
        file_bytes: เนื้อหาของไฟล์ในรูปแบบ bytes

    Returns:
        สตริงที่แสดงค่าแฮช SHA256 ในรูปแบบเลขฐาน 16
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_bytes)
    return sha256_hash.hexdigest()    