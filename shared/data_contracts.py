# shared/data_contracts.py

class WebSocketPayloadKeys:
    """
    Defines the exact key names for the main WebSocket payload.
    This acts as the single source of truth to prevent typos and inconsistencies.
    """
    # --- System & State ---
    STATUS = "status"
    SUGGESTED_BALANCE = "suggested_balance"
    BROKER_NAME = "broker_name"
    SUGGESTED_OFFSET = "suggested_offset"
    ERROR = "error"
    EVENTS = "events"

    # --- Core Account Metrics ---
    EQUITY = "equity"
    OPENING_BALANCE = "opening_balance"
    
    # --- P/L Metrics ---
    DAILY_PL_TOTAL_USD = "daily_pl_total_usd"
    DAILY_PL_TOTAL_PERCENT = "daily_pl_total_percent"
    REALIZED_PL = "realized_pl" # For Session P/L Card
    UNREALIZED_PL = "open_positions_total_profit" # For Open Positions Footer
    PL_TARGET = "pl_target"

    # --- Risk Metrics ---
    DDL_LIMIT_USD = "ddl_limit_usd"
    DDL_USED_USD = "ddl_used_usd"
    DDL_LEFT_USD = "ddl_left_usd"
    RPT_LIMIT_USD = "rpt_limit_usd"
    RPT_AVAILABLE_USD = "rpt_available_usd"
    
    # --- Consistency Metrics ---
    PROFIT_CONSISTENCY_PERCENT = "profit_consistency_percent"
    HIGHEST_PROFIT_DAY = "highest_profit_day"

    # --- Data Tables & Context ---
    OPEN_POSITIONS = "open_positions"
    PENDING_ORDERS = "pending_orders"
    TRADE_HISTORY = "trade_history"
    ALL_SYMBOLS = "all_symbols"
    PORTFOLIO_CONTEXT = "portfolio_context"
    MT5_ACCOUNT_ID = "mt5_account_id"