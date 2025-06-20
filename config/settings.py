# config/settings.py
"""
Central configuration file for the Ultimate Chart Trade Planner.
This file contains all global constants, default values, and structural definitions
to ensure consistency and ease of maintenance across the application.
"""

# =========================================================================
# I. GOOGLE SHEETS CONFIGURATION
#    Constants related to the structure of the Google Sheets document.
# =========================================================================

# --- Names of the Google Sheet and its individual worksheets ---
GOOGLE_SHEET_NAME = "TradeLog" # 
WORKSHEET_PORTFOLIOS = "Portfolios" # 
WORKSHEET_PLANNED_LOGS = "PlannedTradeLogs" # 
WORKSHEET_ACTUAL_TRADES = "ActualTrades"  # For Deals from statements 
WORKSHEET_ACTUAL_ORDERS = "ActualOrders"  # For Orders from statements 
WORKSHEET_ACTUAL_POSITIONS = "ActualPositions" # For Positions from statements 
WORKSHEET_STATEMENT_SUMMARIES = "StatementSummaries" # 
WORKSHEET_UPLOAD_HISTORY = "UploadHistory" # 

# --- Expected Headers for each worksheet ---
# Used by gs_handler.py to validate and write data, ensuring data integrity.

# Headers as defined in main (1).py SEC 6 for setup, and other save functions
WORKSHEET_HEADERS = {
    WORKSHEET_UPLOAD_HISTORY: ["UploadTimestamp", "PortfolioID", "PortfolioName", "FileName", "FileSize", "FileHash", "Status", "ImportBatchID", "Notes"],
    
    # !! ตรวจสอบและแก้ไขส่วนนี้ให้ถูกต้อง !!
    
    WORKSHEET_ACTUAL_TRADES: [
        "Time_Deal", "Deal_ID", "Symbol_Deal", "Type_Deal", "Direction_Deal", 
        "Volume_Deal", "Price_Deal", "Order_Deal", "Commission_Deal", "Fee_Deal", 
        "Swap_Deal", "Profit_Deal", "Balance_Deal", "Comment_Deal", "PortfolioID", 
        "PortfolioName", "SourceFile", "ImportBatchID"
    ],
    
    WORKSHEET_ACTUAL_ORDERS: [
        "Open_Time_Ord", "Order_ID_Ord", "Symbol_Ord", "Type_Ord", "Volume_Ord", 
        "Price_Ord", "S_L_Ord", "T_P_Ord", "Close_Time_Ord", "State_Ord", 
        "Comment_Ord", "PortfolioID", "PortfolioName", "SourceFile", "ImportBatchID"
    ],
    
    WORKSHEET_ACTUAL_POSITIONS: [
        "Time_Pos", "Position_ID", "Symbol_Pos", "Type_Pos", "Volume_Pos", 
        "Price_Open_Pos", "S_L_Pos", "T_P_Pos", "Time_Close_Pos", "Price_Close_Pos", 
        "Commission_Pos", "Swap_Pos", "Profit_Pos", "Comment_Pos", "PortfolioID", 
        "PortfolioName", "SourceFile", "ImportBatchID"
    ],
    
    # ... (ชีทอื่น ๆ) ...
    WORKSHEET_PORTFOLIOS: ["PortfolioID", "PortfolioName", "AccountBalance", "IsActive", "CreatedAt", "UpdatedAt"],
    WORKSHEET_PLANNED_LOGS: [
        "Timestamp", "PortfolioID", "PortfolioName", "TradeID", "Symbol", "Direction", 
        "EntryPrice", "StopLoss", "TakeProfit_1", "TakeProfit_2", "TakeProfit_3", 
        "Risk_Reward_Ratio_1", "Risk_Reward_Ratio_2", "Risk_Reward_Ratio_3", 
        "PositionSize", "Risk_USD", "Status", "Notes", "Chart_Image_URL"
    ],
    WORKSHEET_STATEMENT_SUMMARIES: [
        "Timestamp", "PortfolioID", "PortfolioName", "SourceFile", "ImportBatchID",
        "Balance", "Equity", "Free_Margin", "Margin", "Floating_P_L", "Margin_Level", 
        "Credit_Facility", "Trades", "Profit_Trades_Percent_of_total", "Loss_Trades_Percent_of_total", 
        "Gross_Profit", "Gross_Loss", "Total_Net_Profit", "Profit_Factor", "Expected_Payoff", 
        "Recovery_Factor", "Absolute_Drawdown", "Maximal_Drawdown_Value", "Maximal_Drawdown_Percent", 
        "Total_Trades", "Short_Trades_won_Percent", "Long_Trades_won_Percent", "Maximum_consecutive_wins_Profit",
        "Maximal_consecutive_profit_Count", "Maximum_consecutive_losses_Profit", 
        "Maximal_consecutive_loss_Count"
    ],

    WORKSHEET_PLANNED_LOGS: ["LogID", "PortfolioID", "PortfolioName", "Timestamp", "Asset", "Mode", "Direction",
                                "Risk %", "Fibo Level", "Entry", "SL", "TP", "Lot", "Risk $", "RR"], 
    WORKSHEET_PORTFOLIOS: [
        'PortfolioID', 'PortfolioName', 'ProgramType', 'EvaluationStep',
        'Status', 'InitialBalance', 'CreationDate',
        'ProfitTargetPercent', 'DailyLossLimitPercent', 'TotalStopoutPercent',
        'Leverage', 'MinTradingDays',
        'CompetitionEndDate', 'CompetitionGoalMetric',
        'OverallProfitTarget', 'TargetEndDate', 'WeeklyProfitTarget', 'DailyProfitTarget',
        'MaxAcceptableDrawdownOverall', 'MaxAcceptableDrawdownDaily',
        'EnableScaling', 'ScalingCheckFrequency',
        'ScaleUp_MinWinRate', 'ScaleUp_MinGainPercent', 'ScaleUp_RiskIncrementPercent',
        'ScaleDown_MaxLossPercent', 'ScaleDown_LowWinRate', 'ScaleDown_RiskDecrementPercent',
        'MinRiskPercentAllowed', 'MaxRiskPercentAllowed', 'CurrentRiskPercent',
        'Notes'
    ]  
}


# =========================================================================
# II. APPLICATION DEFAULTS & BEHAVIOR
#     Default values used for initializing session state and UI components.
# =========================================================================

DEFAULT_ACCOUNT_BALANCE = 10000.0 # 
DEFAULT_RISK_PERCENT = 1.0 # 
DEFAULT_DRAWDOWN_LIMIT_PCT = 2.0 # From app.py initialize_session_state() 
DEFAULT_SCALING_STEP = 0.25 # From app.py initialize_session_state() 
DEFAULT_MIN_RISK_PERCENT = 0.50 # From app.py initialize_session_state() 
DEFAULT_MAX_RISK_PERCENT = 5.0 # From app.py initialize_session_state() 


# =========================================================================
# III. TRADING LOGIC CONSTANTS
#      Mathematical constants for trade plan calculations (FIBO, etc.).
# =========================================================================

# Fibonacci Ratios for Entry Levels (from main (1).py SEC 2.1) 
FIBO_LEVELS_DEFINITIONS = [0.114, 0.25, 0.382, 0.5, 0.618] # 

# Ratio constants for FIBO Take Profit (TP) calculations 
RATIO_TP1_EFF = 1.618 # 
RATIO_TP2_EFF = 2.618 # 
RATIO_TP3_EFF = 4.236 # 


# =========================================================================
# IV. STATEMENT PARSING TEMPLATES
#     Structural templates for interpreting raw statement report files.
#     Used by statement_processor.py.
# =========================================================================

# Raw text headers used to identify the start of data sections in the CSV file. 
SECTION_RAW_HEADERS_STATEMENT_PARSING = {
    "Positions": "Time,Position,Symbol,Type,Volume,Price,S / L,T / P,Time,Price,Commission,Swap,Profit", # 
    "Orders": "Open Time,Order,Symbol,Type,Volume,Price,S / L,T / P,Time,State,,Comment", # 
    "Deals": "Time,Deal,Symbol,Type,Direction,Volume,Price,Order,Commission,Fee,Swap,Profit,Balance,Comment" # 
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