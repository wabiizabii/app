# tests/test_calculations.py (VERSION: PHILOSOPHICAL_ALIGNMENT_FINAL)
import pandas as pd
import pytest
from datetime import datetime

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.mt5_data_streamer import calculate_dashboard_metrics

# Test Case 1: Adheres to the new "Fixed Ceiling" and "Committed Risk" rules.
def test_simple_scenario_aligned_with_blueprint():
    # 1. Arrange
    opening_balance = 25000.0
    equity = 25100.0 # Total P/L is +100
    history_df = pd.DataFrame([{'Net P/L': 100.0, 'Close Time': datetime.now().isoformat()}])
    positions_df = pd.DataFrame([{'position_risk': 50.0, 'Profit': 0.0}]) # $50 open risk
    pending_orders_df = pd.DataFrame()

    # 2. Act
    metrics = calculate_dashboard_metrics(opening_balance, equity, history_df, positions_df, pending_orders_df)

    # 3. Assert based on the NEW PHILOSOPHY
    assert metrics['session_total_pl'] == 100.0 # equity - opening_balance
    assert metrics['realized_pl'] == 100.0
    # ddl_limit is now FIXED: 25000 * 1% * 0.9
    assert metrics['ddl_limit_usd'] == pytest.approx(225.0)
    # ddl_used is ONLY open/pending risk
    assert metrics['ddl_used_usd'] == 50.0
    # ddl_left = 225 - 50
    assert metrics['ddl_left_usd'] == pytest.approx(175.0)

# Test Case 2: Adheres to the new "Fixed Ceiling" and "Committed Risk" rules.
def test_complex_scenario_aligned_with_blueprint():
    # 1. Arrange
    opening_balance = 50000.0
    equity = 50130.0 # Total P/L is +130
    history_df = pd.DataFrame([
        {'Net P/L': 200.0, 'Close Time': datetime.now().isoformat()},
        {'Net P/L': -50.0, 'Close Time': datetime.now().isoformat()}
    ])
    positions_df = pd.DataFrame([{'position_risk': 75.0, 'Profit': -20.0}])
    pending_orders_df = pd.DataFrame([{'position_risk': 40.0}])

    # 2. Act
    metrics = calculate_dashboard_metrics(opening_balance, equity, history_df, positions_df, pending_orders_df)

    # 3. Assert based on the NEW PHILOSOPHY
    assert metrics['session_total_pl'] == 130.0
    assert metrics['realized_pl'] == 150.0
    # ddl_limit is FIXED: 50000 * 1% * 0.9
    assert metrics['ddl_limit_usd'] == pytest.approx(450.0)
    # ddl_used is ONLY open (75) + pending (40) risk. Realized losses are ignored.
    assert metrics['ddl_used_usd'] == 75.0 + 40.0
    # ddl_left = 450 - 115
    assert metrics['ddl_left_usd'] == pytest.approx(335.0)