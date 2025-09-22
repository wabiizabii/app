import pandas as pd

def calculate_dashboard_metrics(opening_balance, equity, history_df, positions_df, pending_orders_df):
    """
    The definitive calculation engine, rebuilt to perfectly align with the Captain's
    Philosophical Blueprint. This is the single source of truth.
    """
    metrics = {}
    
    opening_balance = float(opening_balance) if opening_balance is not None else 0.0
    equity = float(equity) if equity is not None else 0.0

    # --- Module 2: Live Equity & Total Daily P/L (As per Blueprint) ---
    total_daily_pl = equity - opening_balance
    metrics['session_total_pl'] = total_daily_pl

    # --- Module 4: Session P/L (Realized P/L) (As per Blueprint) ---
    realized_pl = history_df['Net P/L'].sum() if not history_df.empty else 0.0
    metrics['realized_pl'] = realized_pl

    # --- Module 3: Daily Risk (As per Blueprint) ---
    DAILY_RISK_PERCENT = 0.01

    # Max Daily Risk Limit is FIXED for the day.
    max_daily_risk_limit = opening_balance * DAILY_RISK_PERCENT
    scaled_risk_limit = max_daily_risk_limit * 0.9
    metrics['ddl_limit_usd'] = scaled_risk_limit

    # "Used" risk is ONLY from open and pending orders. Realized losses are NOT part of this calculation.
    risk_from_open_pos = positions_df['position_risk'].sum() if not positions_df.empty else 0.0
    risk_from_pending_orders = pending_orders_df['position_risk'].sum() if not pending_orders_df.empty else 0.0
    total_committed_risk = risk_from_open_pos + risk_from_pending_orders
    metrics['ddl_used_usd'] = total_committed_risk

    # "Left" is the ceiling minus the committed risk.
    metrics['ddl_left_usd'] = max(0, scaled_risk_limit - total_committed_risk)

    # --- RPT (Risk Per Trade) ---
    metrics['rpt_limit_usd'] = scaled_risk_limit
    metrics['rpt_available_usd'] = metrics['ddl_left_usd']

    # --- Target Calculation (As per Blueprint) ---
    # Target is 3R of the MAX daily risk limit (before scaling).
    metrics['pl_target'] = max_daily_risk_limit * 3.0

    # --- Other supporting metrics ---
    metrics['unrealized_pl'] = positions_df['Profit'].sum() if not positions_df.empty else 0.0
    
    profit_consistency_percent = 0.0
    highest_profit_day = 0.0
    if not history_df.empty:
        daily_profits = history_df.groupby(pd.to_datetime(history_df['Close Time']).dt.date)['Net P/L'].sum()
        if not daily_profits.empty:
            highest_profit_day = daily_profits.max()
        if highest_profit_day > 0 and realized_pl > 0:
            profit_consistency_percent = (highest_profit_day / realized_pl) * 100
            
    metrics['profit_consistency_percent'] = profit_consistency_percent
    metrics['highest_profit_day'] = highest_profit_day

    return metrics