# config/settings.py (เวอร์ชันจัดระเบียบใหม่และแก้ไขสมบูรณ์)
"""
Central configuration file for the Ultimate Chart Trade Planner.
"""

# =========================================================================
# I. SUPABASE CONFIGURATION
# =========================================================================
# --- Names of the Supabase Tables ---
# (ชื่อตารางเหล่านี้ควรตรงกับชื่อตารางใน Supabase Dashboard ของคุณ)
SUPABASE_TABLE_PORTFOLIOS = "Portfolios"
SUPABASE_TABLE_PLANNED_LOGS = "PlannedTradeLogs"
SUPABASE_TABLE_ACTUAL_TRADES = "ActualTrades"  # For Deals from statements
SUPABASE_TABLE_ACTUAL_ORDERS = "ActualOrders"  # For Orders from statements
SUPABASE_TABLE_ACTUAL_POSITIONS = "ActualPositions" # For Positions from statements
SUPABASE_TABLE_STATEMENT_SUMMARIES = "StatementSummaries"
SUPABASE_TABLE_UPLOAD_HISTORY = "UploadHistory"
SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS = "DepositWithdrawalLogs"

# --- Expected Headers for each Table ---
# ใช้สำหรับยืนยันโครงสร้างข้อมูลที่อ่านจาก CSV และเตรียมก่อนส่งเข้า Supabase
WORKSHEET_HEADERS = {

    SUPABASE_TABLE_DEPOSIT_WITHDRAWAL_LOGS: [
        "TransactionID", "DateTime", "Type", "Amount", "PortfolioID", "PortfolioName",
        "SourceFile", "ImportBatchID", "Comment"
    ],

    SUPABASE_TABLE_PORTFOLIOS: [
        'PortfolioID', 'PortfolioName', 'ProgramType', 'EvaluationStep',
        'Status', 'InitialBalance', 'CreationDate', 'Notes',
        'ProfitTargetPercent', 'DailyLossLimitPercent', 'TotalStopoutPercent',
        'Leverage', 'MinTradingDays', 'CompetitionEndDate', 'CompetitionGoalMetric',
        'OverallProfitTarget', 'TargetEndDate', 'WeeklyProfitTarget', 'DailyProfitTarget',
        'MaxAcceptableDrawdownOverall', 'MaxAcceptableDrawdownDaily',
        'EnableScaling', 'ScalingCheckFrequency', 'ScaleUp_MinWinRate',
        'ScaleUp_MinGainPercent', 'ScaleUp_RiskIncrementPercent', 'ScaleDown_MaxLossPercent',
        'ScaleDown_LowWinRate', 'ScaleDown_RiskDecrementPercent', 'MinRiskPercentAllowed',
        'MaxRiskPercentAllowed', 'CurrentRiskPercent',
        'AccountID',
        'AccountType'
    ],

    SUPABASE_TABLE_PLANNED_LOGS: [
        "LogID", "PortfolioID", "PortfolioName", "Timestamp", "Asset", "Mode",
        "Direction", "Risk %", "Fibo Level", "Entry", "SL", "TP", "Lot", "Risk $", "RR"
    ],

    SUPABASE_TABLE_ACTUAL_TRADES: [
        "Time_Deal", "Deal_ID", "Symbol_Deal", "Type_Deal", "Direction_Deal", "Volume_Deal",
        "Price_Deal", "Order_ID_Deal", "Commission_Deal", "Fee_Deal", "Swap_Deal",
        "Profit_Deal", "Balance_Deal", "Comment_Deal", "PortfolioID", "PortfolioName",
        "SourceFile", "ImportBatchID"
    ],

    # --- แก้ไขสำหรับ Orders: เพิ่มคอลัมน์ที่หายไป (เช่น Unnamed) ให้ Pandas อ่านได้, เพิ่ม Volume_Ord_Clean ---
    # ตาม Header ที่ให้มา: Open Time,Order,Symbol,Type,Volume,Price,S / L,T / P,Time,State,,Comment,,
    SUPABASE_TABLE_ACTUAL_ORDERS: [
        "Open_Time_Ord", "Order_ID_Ord", "Symbol_Ord", "Type_Ord", "Volume_Ord_Raw", # Original raw volume with " / "
        "Price_Ord", "S_L_Ord", "T_P_Ord", "Close_Time_Ord", "State_Ord",
        "Filler_Ord_1", "Comment_Ord", "Filler_Ord_2", # These map to ,, in CSV header
        "PortfolioID", "PortfolioName", "SourceFile", "ImportBatchID",
        "Volume_Ord" # Cleaned volume from Volume_Ord_Raw (will be added in processor)
    ],
    # --- สิ้นสุดการแก้ไข Orders ---

    # --- แก้ไขสำหรับ Positions: ปรับชื่อคอลัมน์ให้ตรงและเพิ่มคอลัมน์ที่หายไป ---
    # ตาม Header ที่ให้มา: Time,Position,Symbol,Type,Volume,Price,S / L,T / P,Time,Price,Commission,Swap,Profit,
    SUPABASE_TABLE_ACTUAL_POSITIONS: [
        "Time_Pos", "Position_ID", "Symbol_Pos", "Type_Pos", "Volume_Pos", "Price_Open_Pos", "S_L_Pos",
        "T_P_Pos", "Time_Close_Pos_Raw", # This maps to the second 'Time' in CSV header
        "Price_Close_Pos", "Commission_Pos", "Swap_Pos", "Profit_Pos",
        "PortfolioID", "PortfolioName", "SourceFile", "ImportBatchID",
        "Time_Close_Pos" # Cleaned close time from Time_Close_Pos_Raw (will be added in processor)
    ],
    # --- สิ้นสุดการแก้ไข Positions ---

    SUPABASE_TABLE_STATEMENT_SUMMARIES: [
        "ImportBatchID", "Timestamp", "PortfolioID", "PortfolioName", "SourceFile", "ClientName",
        "Balance", "Equity", "Free_Margin", "Margin", "Floating_P_L", "Margin_Level",
        "Credit_Facility", "Deposit", "Withdrawal", "Gross_Profit", "Gross_Loss",
        "Total_Net_Profit", "Profit_Factor", "Recovery_Factor", "Expected_Payoff",
        "Sharpe_Ratio", "Balance_Drawdown", "Balance_Drawdown_Absolute",
        "Maximal_Drawdown_Value", "Maximal_Drawdown_Percent",
        "Balance_Drawdown_Relative_Percent", "Balance_Drawdown_Relative_Value",
        "Total_Trades", "Profit_Trades_Count", "Profit_Trades_Percent",
        "Loss_Trades_Count", "Loss_Trades_Percent",
        "Long_Trades_Count", "Long_Trades_Won_Percent",
        "Short_Trades_Count", "Short_Trades_Won_Percent",
        "Largest_Profit_Trade", "Average_Profit_Trade",
        "Largest_Loss_Trade", "Average_Loss_Trade",
        "Max_Consecutive_Wins_Count", "Max_Consecutive_Wins_Profit",
        "Maximal_Consecutive_Profit_Value", "Maximal_Consecutive_Profit_Count",
        "Max_Consecutive_Losses_Count", "Max_Consecutive_Losses_Profit",
        "Maximal_Consecutive_Loss_Value", "Maximal_Consecutive_Loss_Count",
        "Average_Consecutive_Wins", "Average_Consecutive_Losses"
    ],

    SUPABASE_TABLE_UPLOAD_HISTORY: [
        "UploadTimestamp", "PortfolioID", "PortfolioName", "FileName", "FileSize",
        "FileHash", "Status", "ImportBatchID", "Notes"
    ]
}

WORKSHEET_HEADERS_MAPPER = {
    "deals": "ActualTrades",
    "orders": "ActualOrders",
    "positions": "ActualPositions",
    "deposit_withdrawal_logs": "DepositWithdrawalLogs",
    "deals": "ActualTrades",
    "orders": "ActualOrders",
    "positions": "ActualPositions",
    "deposit_withdrawal_logs": "DepositWithdrawalLogs",
}



# --- Expected Raw Headers for parsing sections in CSV files ---
# These are used to locate the start of data tables within the raw CSV content.
# They MUST match the actual headers in your CSV file EXACTLY.
SECTION_RAW_HEADERS_STATEMENT_PARSING = {
    # Positions Header: Time,Position,Symbol,Type,Volume,Price,S / L,T / P,Time,Price,Commission,Swap,Profit,
    # Note the trailing comma, and the space around "S / L", "T / P"
    "Positions": "Time,Position,Symbol,Type,Volume,Price,S / L,T / P,Time,Price,Commission,Swap,Profit,",
    
    # Orders Header: Open Time,Order,Symbol,Type,Volume,Price,S / L,T / P,Time,State,,Comment,,
    # Note the multiple trailing commas, and the empty headers (,,)
    "Orders": "Open Time,Order,Symbol,Type,Volume,Price,S / L,T / P,Time,State,,Comment,,",
    
    # Deals Header: Time,Deal,Symbol,Type,Direction,Volume,Price,Order,Commission,Fee,Swap,Profit,Balance,Comment
    "Deals": "Time,Deal,Symbol,Type,Direction,Volume,Price,Order,Commission,Fee,Swap,Profit,Balance,Comment"
}

# =========================================================================
# II. APPLICATION DEFAULTS & BEHAVIOR
# =========================================================================

DEFAULT_ACCOUNT_BALANCE = 10000.0
DEFAULT_RISK_PERCENT = 1.0
DEFAULT_DRAWDOWN_LIMIT_PCT = 2.0
DEFAULT_SCALING_STEP = 0.25
DEFAULT_MIN_RISK_PERCENT = 0.50
DEFAULT_MAX_RISK_PERCENT = 5.0

# =========================================================================
# III. TRADING LOGIC CONSTANTS
# =========================================================================
# Fibonacci Ratios for Entry Levels (from main (1).py SEC 2.1)
FIBO_LEVELS_DEFINITIONS = [0.114, 0.25, 0.382, 0.5, 0.618]

# Ratio constants for FIBO Take Profit (TP) calculations
RATIO_TP1_EFF = 1.618
RATIO_TP2_EFF = 2.618
RATIO_TP3_EFF = 4.236

# =========================================================================
# IV. ASSET SPECIFICATIONS FOR LOT/RISK CALCULATION
# =========================================================================
ASSET_SPECIFICATIONS = {
    "STANDARD": { # Symbol สำหรับบัญชี STANDARD
        "XAUUSD": { # จาก Screenshot 2025-07-06 at 15.41.44.png
            "tick_size": 0.01,
            "tick_value_per_tick_per_lot": 1.5427 # ค่านี้เพื่อให้ Lot ตรง 0.02 ที่ Risk 1% (ตามปัญหาที่คุณเจอ)
        },
        "EURUSD": { # จาก Screenshot 2025-07-06 at 15.42.21.png
            "tick_size": 0.00001,
            "tick_value_per_tick_per_lot": 1.00
        },
        "USDJPY": { # จาก Screenshot 2025-07-06 at 15.42.12.png
            "tick_size": 0.001,
            "tick_value_per_tick_per_lot": 1.00
        },
        "GBPUSD": { # จาก Screenshot 2025-07-06 at 15.42.04.png
            "tick_size": 0.00001,
            "tick_value_per_tick_per_lot": 1.00
        },
        "NAS100": { # จาก Screenshot 2025-07-06 at 15.42.45.png
            "tick_size": 0.01, # ประเมินจาก Digits 2
            "tick_value_per_tick_per_lot": 1.00 # ประเมิน
        },
        "US30": { # จาก Screenshot 2025-07-06 at 15.42.53.png
            "tick_size": 0.01, # ประเมินจาก Digits 2
            "tick_value_per_tick_per_lot": 1.00 # ประเมิน
        },
        "SP500": { # จาก Screenshot 2025-07-06 at 15.42.38.png
            "tick_size": 0.01, # ประเมินจาก Digits 2
            "tick_value_per_tick_per_lot": 1.00 # ประเมิน
        },
        "JPN225": { # จาก Screenshot 2025-07-06 at 15.43.01.png
            "tick_size": 0.01, # ประเมินจาก Digits 2
            "tick_value_per_tick_per_lot": 1.00 # ประเมิน
        },
        "BTCUSD": { # จาก Screenshot 2025-07-06 at 15.43.10.png
            "tick_size": 0.01, # ประเมินจาก Digits 2
            "tick_value_per_tick_per_lot": 1.00 # ประเมิน
        },
    },
    "CENT": { # Symbol สำหรับบัญชี CENT
        "XAUUSDc": { # จาก Screenshot 2025-07-06 at 15.39.08.png
            "tick_size": 0.01, # (ประเมิน)
            "tick_value_per_tick_per_lot": 0.01 # (ประเมินว่า 1 Lot = 1 ออนซ์)
        },
        "USDJPYc": { # จาก Screenshot 2025-07-06 at 15.37.13.png
            "tick_size": 0.001, # (ประเมิน)
            "tick_value_per_tick_per_lot": 0.01 # (ประเมิน)
        },
        "BTCUSDc": { # จาก Screenshot 2025-07-06 at 15.38.13.png
            "tick_size": 0.01, # (ประเมิน)
            "tick_value_per_tick_per_lot": 0.01 # (ประเมิน)
        },
    },
    "PROP_FIRM": { 
        "XAUUSD": {
            "tick_size": 0.01,
            "tick_value_per_tick_per_lot": 1.5427
        },
        "EURUSD": {
            "tick_size": 0.00001,
            "tick_value_per_tick_per_lot": 1.00
        },
        "USDJPY": {
            "tick_size": 0.001,
            "tick_value_per_tick_per_lot": 1.00
        },
        "GBPUSD": {
            "tick_size": 0.00001,
            "tick_value_per_tick_per_lot": 1.00
        },
        "NAS100": {
            "tick_size": 0.01,
            "tick_value_per_tick_per_lot": 1.00
        },
        "US30": {
            "tick_size": 0.01,
            "tick_value_per_tick_per_lot": 1.00
        },
        "SP500": {
            "tick_size": 0.01,
            "tick_value_per_tick_per_lot": 1.00
        },
        "JPN225": {
            "tick_size": 0.01,
            "tick_value_per_tick_per_lot": 1.00
        },
        "BTCUSD": {
            "tick_size": 0.01,
            "tick_value_per_tick_per_lot": 1.00
        },
    },
}
# =========================================================================
# V. SUPABASE API CONFIGURATION (เพิ่มส่วนนี้เข้าไป)
# =========================================================================
# IMPORTANT: Replace these with your actual Supabase Project URL and Public API Key
# You can find these in your Supabase project dashboard under Project Settings > API
SUPABASE_URL = "https://xmqriscinxccbdggmtnb.supabase.co"    
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhtcXJpc2NpbnhjY2JkZ2dtdG5iIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTEyMjU3MywiZXhwIjoyMDY2Njk4NTczfQ.YUX36ML3CZmya4h3CJSuZvlRjinbsPX3yTWBTduJc88" 

# --- START: เพิ่มข้อมูลสำหรับ Futures Calculator ---
FUTURES_TICK_VALUES = {
    # Indices
    "ES": 12.50,  # E-mini S&P 500
    "MES": 1.25,   # Micro E-mini S&P 500
    "NQ": 5.00,   # E-mini NASDAQ 100
    "MNQ": 0.50,   # Micro E-mini NASDAQ 100
    "YM": 5.00,   # E-mini Dow Jones
    "MYM": 0.50,   # Micro E-mini Dow Jones
    
    # Energies
    "CL": 10.00,  # Crude Oil
    "MCL": 1.00,   # Micro Crude Oil
    
    # Metals
    "GC": 10.00,  # Gold
    "MGC": 1.00,   # Micro Gold
}
# --- END: สิ้นสุดข้อมูลที่เพิ่ม ---

# --- START: เพิ่มข้อมูล Tick Size สำหรับคำนวณอัตโนมัติ ---
FUTURES_TICK_SIZES = {
    # Indices
    "ES": 0.25, "MES": 0.25, "NQ": 0.25, "MNQ": 0.25,
    "YM": 1.00, "MYM": 1.00, "RTY": 0.10, "M2K": 0.10,

    # Energies
    "CL": 0.01, "MCL": 0.01, "NG": 0.001,

    # Metals
    "GC": 0.10, "MGC": 0.10, "SI": 0.005, "SIL": 0.005,

    # Currencies
    "6E": 0.00005,
}
# --- END: สิ้นสุดข้อมูลที่เพิ่ม ---

ACCOUNT_RULES = {
    "50K Buying Power": {
        "start_balance": 50000.0,
        "profit_target": 3000.0,
        "max_loss_limit": 2000.0,
        "daily_loss_limit": 1000.0,
        "max_contracts_std": 5, # <-- ตรวจสอบให้แน่ใจว่าเป็นชื่อนี้
        "scaling_level_1": 51500.0,
        "scaling_contracts_1": 2,
        "scaling_contracts_2": 3,
    },
    "100K Buying Power": {
        "start_balance": 100000.0,
        "profit_target": 6000.0,
        "max_loss_limit": 3000.0,
        "daily_loss_limit": 2000.0,
        "max_contracts_std": 10, # <-- ตรวจสอบให้แน่ใจว่าเป็นชื่อนี้
        "scaling_level_1": 102000.0,
        "scaling_contracts_1": 4,
        "scaling_contracts_2": 6,
    },
    "150K Buying Power": {
        "start_balance": 150000.0,
        "profit_target": 9000.0,
        "max_loss_limit": 4500.0,
        "daily_loss_limit": 3000.0,
        "max_contracts_std": 15, # <-- ตรวจสอบให้แน่ใจว่าเป็นชื่อนี้
        "scaling_level_1": 152500.0,
        "scaling_contracts_1": 6,
        "scaling_contracts_2": 9,
    }
}
FOREX_POINT_VALUES = {
    # (มูลค่ากำไร/ขาดทุนต่อ 1 Lot เมื่อราคาขยับ 1.0 หน่วย)
    "XAUUSD": 100.0,  # 1 Standard Lot = 100 oz. ดังนั้นราคาขยับ $1 = $100 P/L
    "US30": 1.0,    # สำหรับโบรกเกอร์ส่วนใหญ่ 1 point move = $1 P/L per Lot
    "NAS100": 1.0,    # สำหรับโบรกเกอร์ส่วนใหญ่ 1 point move = $1 P/L per Lot
    "EURUSD": 100000.0, # 1 Standard Lot = 100,000 EUR. ราคาขยับ 1.0 (เช่น 1.08 -> 2.08) = $100,000 P/L
    "GBPUSD": 100000.0, # 1 Standard Lot = 100,000 GBP.
}