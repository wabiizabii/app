# config/settings.py (เวอร์ชันจัดระเบียบใหม่และแก้ไขสมบูรณ์)

"""
Central configuration file for the Ultimate Chart Trade Planner.
"""

# =========================================================================
# I. GOOGLE SHEETS CONFIGURATION
# =========================================================================

# --- Names of the Google Sheet and its individual worksheets ---
GOOGLE_SHEET_NAME = "TradeLog"
WORKSHEET_PORTFOLIOS = "Portfolios"
WORKSHEET_PLANNED_LOGS = "PlannedTradeLogs"
WORKSHEET_ACTUAL_TRADES = "ActualTrades"  # For Deals from statements
WORKSHEET_ACTUAL_ORDERS = "ActualOrders"  # For Orders from statements
WORKSHEET_ACTUAL_POSITIONS = "ActualPositions" # For Positions from statements
WORKSHEET_STATEMENT_SUMMARIES = "StatementSummaries"
WORKSHEET_UPLOAD_HISTORY = "UploadHistory"
WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS = "DepositWithdrawalLogs"

# --- Expected Headers for each worksheet ---
# Used by gs_handler.py to validate and write data, ensuring data integrity.
WORKSHEET_HEADERS = {

    # Header สำหรับชีท DepositWithdrawalLogs ใหม่
    WORKSHEET_DEPOSIT_WITHDRAWAL_LOGS: [
        "TransactionID", "DateTime", "Type", "Amount", "PortfolioID", "PortfolioName",
        "SourceFile", "ImportBatchID", "Comment"
    ],

    # ใช้โครงสร้างที่สมบูรณ์และถูกต้องที่สุดสำหรับ Portfolios (เหลือแค่ครั้งเดียว)
    WORKSHEET_PORTFOLIOS: [
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

    # ใช้โครงสร้างที่ถูกต้องสำหรับ PlannedTradeLogs (เหลือแค่ครั้งเดียว)
    WORKSHEET_PLANNED_LOGS: [
        "LogID", "PortfolioID", "PortfolioName", "Timestamp", "Asset", "Mode",
        "Direction", "Risk %", "Fibo Level", "Entry", "SL", "TP", "Lot", "Risk $", "RR"
    ],

    WORKSHEET_ACTUAL_TRADES: [
        "Time_Deal", "Deal_ID", "Symbol_Deal", "Type_Deal", "Direction_Deal", "Volume_Deal",
        "Price_Deal", "Order_ID_Deal", "Commission_Deal", "Fee_Deal", "Swap_Deal",
        "Profit_Deal", "Balance_Deal", "Comment_Deal", "PortfolioID", "PortfolioName",
        "SourceFile", "ImportBatchID"
    ],

    WORKSHEET_ACTUAL_ORDERS: [
        "Open_Time_Ord", "Order_ID_Ord", "Symbol_Ord", "Type_Ord", "Volume_Ord", "Price_Ord", "S_L_Ord",
        "T_P_Ord", "Close_Time_Ord", "State_Ord", "Comment_Ord", "PortfolioID", "PortfolioName",
        "SourceFile", "ImportBatchID"
    ],

    WORKSHEET_ACTUAL_POSITIONS: [
        "Time_Pos", "Position_ID", "Symbol_Pos", "Type_Pos", "Volume_Pos", "Price_Open_Pos", "S_L_Pos",
        "T_P_Pos", "Time_Close_Pos", "Price_Close_Pos", "Commission_Pos", "Swap_Pos", "Profit_Pos",
        "Comment_Pos", "PortfolioID", "PortfolioName", "SourceFile", "ImportBatchID"
    ],

    # Header สำหรับ StatementSummaries ที่สมบูรณ์แบบ
    WORKSHEET_STATEMENT_SUMMARIES: [
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

    WORKSHEET_UPLOAD_HISTORY: [
        "UploadTimestamp", "PortfolioID", "PortfolioName", "FileName", "FileSize",
        "FileHash", "Status", "ImportBatchID", "Notes"
    ]
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
# IV. STATEMENT PARSING TEMPLATES
#     Structural templates for interpreting raw statement report files.
#     Used by statement_processor.py.
# =========================================================================

# Raw text headers used to identify the start of data sections in the CSV file.
SECTION_RAW_HEADERS_STATEMENT_PARSING = {
    "Positions": "Time,Position,Symbol,Type,Volume,Price,S / L,T / P,Time,Price,Commission,Swap,Profit",
    "Orders": "Open Time,Order,Symbol,Type,Volume,Price,S / L,T / P,Time,State,,Comment",
    "Deals": "Time,Deal,Symbol,Type,Direction,Volume,Price,Order,Commission,Fee,Swap,Profit,Balance,Comment"
}

# Defines the final column names for the pandas DataFrames after parsing.
EXPECTED_CLEANED_COLUMNS_STATEMENT_PARSING = {
    "Positions": [
        "Time_Pos", "Position_ID", "Symbol_Pos", "Type_Pos", "Volume_Pos", "Price_Open_Pos",
        "S_L_Pos", "T_P_Pos", "Time_Close_Pos", "Price_Close_Pos", "Commission_Pos",
        "Swap_Pos", "Profit_Pos", "Trailing_Empty_Pos"
    ],

    "Orders": [
        "Open_Time_Ord", "Order_ID_Ord", "Symbol_Ord", "Type_Ord", "Volume_Ord", "Price_Ord",
        "S_L_Ord", "T_P_Ord", "Close_Time_Ord", "State_Ord", "Unnamed_Ord", "Comment_Ord"
    ],
    "Deals": [
        "Time_Deal", "Deal_ID", "Symbol_Deal", "Type_Deal", "Direction_Deal", "Volume_Deal",
        "Price_Deal", "Order_ID_Deal", "Commission_Deal", "Fee_Deal", "Swap_Deal",
        "Profit_Deal", "Balance_Deal", "Comment_Deal"
    ]
}

# =========================================================================
# V. ASSET SPECIFICATIONS FOR LOT/RISK CALCULATION
#    Values derived from MT5 contract specifications for accurate lot sizing.
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
    "PROP_FIRM": { # <<<< คัดลอกมาจาก STANDARD เพื่อให้เหมือนกัน >>>>
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