# ==============================================================================
# FILE: services/mt5_data_streamer.py (VERSION: FINAL_INTEGRATED_STABLE)
# ==============================================================================
import sys
import os
import asyncio
import json
import websockets
import pandas as pd
import traceback
import uuid
import functools
from datetime import datetime, timedelta
import numpy as np
import pytz
from core.calculation_engine import calculate_dashboard_metrics

# --- [DEFINITIVE] Project Root Setup ---
# This block ensures that the script can see all other modules in the project,
# regardless of how the script is run.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- [DEFINITIVE] Project-specific Imports ---
# Now that the path is corrected, these imports will work reliably.
from shared.data_contracts import WebSocketPayloadKeys as P_KEYS
from core.headless_supabase_handler import HeadlessSupabaseHandler
from core.mt5_handler import MT5Handler
from config import settings
 
# --- Global Variables ---
WEBSOCKET_HOST, WEBSOCKET_PORT = "localhost", 5555
CONNECTED_CLIENTS = set()
SESSION_STATE = { "status": "INITIALIZING" }
SHUTDOWN_EVENT = asyncio.Event()


def json_converter(o):
    if isinstance(o, (datetime, pd.Timestamp)): return o.isoformat()
    if isinstance(o, (np.integer, np.int64)): return int(o)
    if isinstance(o, (np.floating, np.float64)): return float(o) if not np.isnan(o) else None
    return str(o)



async def fetch_and_broadcast_data(mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    while not SHUTDOWN_EVENT.is_set():
        payload = {}
        try:
            if SESSION_STATE["status"] == "SESSION_ACTIVE":
                current_account_info = mt5.account_info()
                if not current_account_info or str(current_account_info.login) != SESSION_STATE.get("mt5_account_id"):
                    print(f"\n--- TACTICAL SHUTDOWN ---\n"); SHUTDOWN_EVENT.set(); return
                
                opening_balance = SESSION_STATE["opening_balance"]
                equity = current_account_info.equity
                positions_df = mt5_handler.get_open_positions()
                pending_orders_df = mt5_handler.get_pending_orders()
                session_start_utc = SESSION_STATE["session_start_time_utc"]
                end_of_session_utc = datetime.now(pytz.utc) 
                history_df = mt5_handler.get_trade_history(start_date=session_start_utc, end_date=end_of_session_utc)
                
                metrics = calculate_dashboard_metrics(opening_balance, equity, history_df, positions_df, pending_orders_df)
                
                # [CONTRACT ENFORCED] The payload is now built using the Data Contract.
                payload = {
                    P_KEYS.STATUS: "SESSION_ACTIVE",
                    P_KEYS.EQUITY: equity,
                    P_KEYS.OPENING_BALANCE: opening_balance,
                    P_KEYS.DAILY_PL_TOTAL_USD: metrics['session_total_pl'],
                    P_KEYS.DAILY_PL_TOTAL_PERCENT: (metrics['session_total_pl'] / opening_balance * 100) if opening_balance > 0 else 0.0,
                    P_KEYS.DDL_LIMIT_USD: metrics['ddl_limit_usd'],
                    P_KEYS.DDL_USED_USD: metrics['ddl_used_usd'],
                    P_KEYS.DDL_LEFT_USD: metrics['ddl_left_usd'],
                    P_KEYS.REALIZED_PL: metrics['realized_pl'],
                    P_KEYS.PL_TARGET: metrics['pl_target'],
                    P_KEYS.PROFIT_CONSISTENCY_PERCENT: metrics['profit_consistency_percent'],
                    P_KEYS.HIGHEST_PROFIT_DAY: metrics['highest_profit_day'],
                    P_KEYS.RPT_AVAILABLE_USD: metrics['rpt_available_usd'],
                    P_KEYS.RPT_LIMIT_USD: metrics['rpt_limit_usd'],
                    P_KEYS.UNREALIZED_PL: metrics['unrealized_pl'],
                    P_KEYS.OPEN_POSITIONS: positions_df.to_dict('records'),
                    P_KEYS.PENDING_ORDERS: pending_orders_df.to_dict('records'),
                    P_KEYS.TRADE_HISTORY: history_df.to_dict('records'),
                    P_KEYS.ALL_SYMBOLS: list(SESSION_STATE.get("symbol_properties", {}).keys()),
                    P_KEYS.PORTFOLIO_CONTEXT: SESSION_STATE.get("portfolio_context"),
                    P_KEYS.MT5_ACCOUNT_ID: SESSION_STATE.get("mt5_account_id"),
                    P_KEYS.EVENTS: [] # Placeholder for future event system
                }
            else:
                payload = {
                    P_KEYS.STATUS: SESSION_STATE.get("status"),
                    P_KEYS.SUGGESTED_BALANCE: SESSION_STATE.get("suggested_balance", 0.0),
                    P_KEYS.BROKER_NAME: SESSION_STATE.get("broker_name"),
                    P_KEYS.SUGGESTED_OFFSET: 3
                }
            
            if CONNECTED_CLIENTS:
                await asyncio.gather(*(client.send(json.dumps(payload, default=json_converter)) for client in CONNECTED_CLIENTS))
            
            await asyncio.sleep(2)
        except Exception as e:
            print(f"ERROR in broadcast loop: {e}"); traceback.print_exc(); await asyncio.sleep(5)

async def handle_client_commands(websocket, mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    global SESSION_STATE
    async for message in websocket:
        try:
            command = json.loads(message)
            event, payload = command.get("event"), command.get("payload", {})
            if event == "CONFIRM_TIMEZONE":
                offset = int(payload.get("offset"))
                broker_name = SESSION_STATE.get("broker_name")
                if broker_name and supabase_handler.set_broker_timezone(broker_name, offset):
                    print(f"✅ Timezone for '{broker_name}' confirmed. Re-initializing...")
                    await initialize_system_state(mt5_handler, supabase_handler)
            elif event == "START_SESSION":
                user_confirmed_balance = float(payload.get("openingBalance", 0.0))
                if user_confirmed_balance > 0 and SESSION_STATE.get("status") == "READY_TO_START":
                    if supabase_handler.set_daily_opening_balance(SESSION_STATE.get("portfolio_id"), SESSION_STATE.get("mt5_account_id"), user_confirmed_balance, SESSION_STATE.get("broker_date_str")):
                        SESSION_STATE["opening_balance"] = user_confirmed_balance
                        SESSION_STATE["status"] = "SESSION_ACTIVE"
                        print(f"\n✅ SESSION ACTIVATED\n")
        except Exception as e:
            print(f"ERROR in handle_client_commands: {e}"); traceback.print_exc()

async def client_handler(websocket, mt5_handler, supabase_handler):
    CONNECTED_CLIENTS.add(websocket)
    try:
        await websocket.send(json.dumps({ "status": SESSION_STATE.get("status"), "broker_name": SESSION_STATE.get("broker_name") }, default=json_converter))
        await handle_client_commands(websocket, mt5_handler, supabase_handler)
    finally:
        CONNECTED_CLIENTS.remove(websocket)

# แทนที่ฟังก์ชัน initialize_system_state เดิมทั้งหมดด้วยโค้ดนี้

# [VERSION: ULTIMATE_FALLBACK & STABLE]
async def initialize_system_state(mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    global SESSION_STATE
    SESSION_STATE = { "status": "INITIALIZING" }
    print("\n--- [REBOOT] Initializing System State ---")
    try:
        account_info = mt5_handler.get_account_info()
        if not account_info: raise Exception("Could not get account info from MT5.")
        
        mt5_id_str = str(account_info.get('login'))
        broker_identifier = account_info.get('server_name', "Unknown Broker")
        
        SESSION_STATE.update({ "mt5_account_id": mt5_id_str, "broker_name": broker_identifier })
        print(f"-> MT5 Connection: OK (Broker: {broker_identifier}, Account: {mt5_id_str})")
        
        broker_offset = supabase_handler.get_broker_timezone(broker_identifier)
        if broker_offset is None:
            SESSION_STATE["status"] = "REQUIRE_TIMEZONE_CONFIRMATION"
            print(f"-> STATE: Timezone for '{broker_identifier}' is unknown.")
            return
        
        print(f"-> Timezone: OK (Offset: {broker_offset})")
        
        portfolio_context = supabase_handler.get_portfolio_by_mt5_account_id(mt5_id_str)
        if not portfolio_context:
            print(f"INFO: No portfolio for MT5 ID {mt5_id_str}. Auto-provisioning...")
            new_portfolio_data = {
                "PortfolioID": str(uuid.uuid4()), "mt5_account_id": mt5_id_str, "PortfolioName": f"MT5 Acct {mt5_id_str}",
                "BrokerName": broker_identifier, "DailyLossLimitPercent": 0.01,
                "InitialBalance": account_info.get('balance', 0.0)
            }
            portfolio_context, _ = supabase_handler.insert_new_portfolio(new_portfolio_data)
            if not portfolio_context: raise Exception("Failed to auto-provision portfolio.")
        
        print(f"-> Portfolio: OK (Name: {portfolio_context.get('PortfolioName')})")
        
        portfolio_id = str(portfolio_context.get("PortfolioID"))
        broker_date_str = mt5_handler.get_broker_now(broker_offset).strftime('%Y-%m-%d')
        session_start_utc = mt5_handler.get_session_start_time_utc(broker_offset)
        
        SESSION_STATE.update({
            "portfolio_context": portfolio_context, "portfolio_id": portfolio_id,
            "symbol_properties": mt5_handler.get_all_symbol_properties(),
            "broker_date_str": broker_date_str, "session_start_time_utc": session_start_utc
        })
        print(f"-> Session Context: OK (Date: {broker_date_str})")

        existing_balance = supabase_handler.get_daily_opening_balance(portfolio_id, mt5_id_str, broker_date_str)
        
        if existing_balance is not None:
            SESSION_STATE.update({ "opening_balance": existing_balance, "status": "SESSION_ACTIVE" })
            print(f"✅ STATE: SESSION_ACTIVE (Resuming with saved balance: {existing_balance})")
        else:
            # [ULTIMATE FALLBACK] We will always suggest the CURRENT, most up-to-date balance.
            # The user is the final authority to confirm or correct this value.
            current_balance = account_info.get('balance', 0.0)
            SESSION_STATE.update({ "status": "READY_TO_START", "suggested_balance": current_balance })
            print(f"-> STATE: READY_TO_START (Suggested current balance: {current_balance})")

    except Exception as e:
        print(f"❌ CRITICAL ERROR during initialization: {e}"); traceback.print_exc(); SESSION_STATE["status"] = "ERROR_STATE"

async def main():
    print("--- [VERSION: SYSTEM_INTEGRITY] Initializing Obsidian Core... ---")
    mt5_handler = MT5Handler()
    if not mt5_handler.initialize_connection(): return
    supabase_handler = HeadlessSupabaseHandler(url=settings.SUPABASE_URL, key=settings.SUPABASE_KEY)
    if not supabase_handler.client: return
    await initialize_system_state(mt5_handler, supabase_handler)
    print(f"--- System Initialized. Current Status: {SESSION_STATE.get('status')} ---")
    server = await websockets.serve(functools.partial(client_handler, mt5_handler=mt5_handler, supabase_handler=supabase_handler), WEBSOCKET_HOST, WEBSOCKET_PORT)
    await asyncio.create_task(fetch_and_broadcast_data(mt5_handler, supabase_handler))

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nServer shutdown.")