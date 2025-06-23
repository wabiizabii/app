# config/settings.py (เวอร์ชันจัดระเบียบใหม่และถูกต้อง)

"""
Central configuration file for the Ultimate Chart Trade Planner.
"""

# =========================================================================
# I. GOOGLE SHEETS CONFIGURATION
# =========================================================================

# --- 1. นิยามชื่อชีตทั้งหมดที่ใช้ในโปรเจกต์ ---
GOOGLE_SHEET_NAME = "TradeLog"
WORKSHEET_PORTFOLIOS = "Portfolios"
WORKSHEET_PLANNED_LOGS = "PlannedTradeLogs"
WORKSHEET_ACTUAL_TRADES = "ActualTrades"
WORKSHEET_ACTUAL_ORDERS = "ActualOrders"
WORKSHEET_ACTUAL_POSITIONS = "ActualPositions"
WORKSHEET_STATEMENT_SUMMARIES = "StatementSummaries"
WORKSHEET_UPLOAD_HISTORY = "UploadHistory"
WORKSHEET_DASHBOARD = "PortfolioDashboard"

# --- 2. กำหนดโครงสร้างคอลัมน์ (Headers) ของแต่ละชีต ---
# ฟังก์ชัน setup_and_get_worksheets จะใช้ข้อมูลนี้ในการสร้างและตรวจสอบชีตทั้งหมด
WORKSHEET_HEADERS = {
    
    WORKSHEET_DASHBOARD: [
        "PortfolioID", "PortfolioName", "LastUpdated", "ProgramType", "Status",
        "CurrentBalance", "TotalNetProfit", "TotalDeposits", "TotalWithdrawals",
        "WinRate", "ProfitFactor", "TotalTrades", "GrossProfit", "GrossLoss",
        "AvgProfit", "AvgLoss", "Expectancy", "MaxDrawdown"
        "ProfitTrades", "LossTrades", "BreakevenTrades", "BestProfit", 
        "BiggestLoss", "AvgTradeSize"
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
        'MaxRiskPercentAllowed', 'CurrentRiskPercent'
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
    
    WORKSHEET_STATEMENT_SUMMARIES: [
        'Timestamp', 'PortfolioID', 'PortfolioName', 'SourceFile', 'ImportBatchID', 
        'Balance', 'Equity', 'Deposit', 'Withdrawal', 'Total_Net_Profit', 'Profit_Factor',
        'Total_Trades'
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

FIBO_LEVELS_DEFINITIONS = [0.114, 0.25, 0.382, 0.5, 0.618]
RATIO_TP1_EFF = 1.618
RATIO_TP2_EFF = 2.618
RATIO_TP3_EFF = 4.236