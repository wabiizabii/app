# ==============================================================================
# FILE: services/mt5_data_streamer.py (VERSION: SYSTEM_INTEGRITY_CORRECTED)
# ==============================================================================
import sys, os, asyncio, json, websockets, pandas as pd, traceback, uuid, functools, time
from datetime import datetime, timezone, time as dt_time, timedelta
import numpy as np, pytz
import MetaTrader5 as mt5

# --- Project Root Setup ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path: sys.path.insert(0, project_root)
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

# [ แทนที่ฟังก์ชันเดิมทั้งหมดของคุณด้วยฟังก์ชันนี้ ]
async def fetch_and_broadcast_data(mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    while True:
        payload = {}
        try:
            if SESSION_STATE["status"] == "SESSION_ACTIVE":
                current_account_info = mt5.account_info()
                # Refined Check with clearer message
                if not current_account_info or str(current_account_info.login) != SESSION_STATE.get("mt5_account_id"):
                    print(f"\n--- TACTICAL SHUTDOWN ---")
                    print(f"Reason: Live MT5 Account ({current_account_info.login if current_account_info else 'N/A'}) does not match Session Account ({SESSION_STATE.get('mt5_account_id')}).")
                    print(f"This is a safety measure to prevent operating on the wrong account. Please restart the script.")
                    print(f"---------------------------\n")
                    SHUTDOWN_EVENT.set()
                    return

                opening_balance = SESSION_STATE["opening_balance"]
                equity = current_account_info.equity

                positions_df = mt5_handler.get_open_positions()
                pending_orders_df = mt5_handler.get_pending_orders()

                session_start_utc = SESSION_STATE["session_start_time_utc"]
                session_end_utc = session_start_utc + timedelta(hours=23, minutes=59, seconds=59)

                history_df = mt5_handler.get_trade_history(start_date=session_start_utc, end_date=session_end_utc)

                # [ START OF SURGICAL REPLACEMENT ]
                # The old logic has been removed and replaced with this new, correct engine.

                unrealized_pl = positions_df['Profit'].sum() if not positions_df.empty else 0.0
                session_total_pl = equity - opening_balance

                ddl_percent = SESSION_STATE.get("ddl_percent", 0.01)

                initial_risk_limit_usd = opening_balance * ddl_percent

                realized_gains = history_df[history_df['Net P/L'] > 0]['Net P/L'].sum() if not history_df.empty else 0.0

                dynamic_risk_ceiling_usd = initial_risk_limit_usd + realized_gains

                realized_losses = abs(history_df[history_df['Net P/L'] < 0]['Net P/L'].sum()) if not history_df.empty else 0.0

                open_positions_risk = positions_df['position_risk'].sum() if not positions_df.empty else 0.0

                pending_orders_risk = pending_orders_df['position_risk'].sum() if not pending_orders_df.empty else 0.0

                total_used_risk_usd = realized_losses + open_positions_risk + pending_orders_risk

                risk_left_usd = max(0, dynamic_risk_ceiling_usd - total_used_risk_usd)

                # We now rename the variables for consistency with the rest of your code
                ddl_limit_usd = dynamic_risk_ceiling_usd
                ddl_used_usd = total_used_risk_usd
                ddl_left_usd = risk_left_usd

                # [ END OF SURGICAL REPLACEMENT ]

                risk_unit_usd = opening_balance * 0.01 # This is for R-Unit, not DDL
                total_open_risk = positions_df['position_risk'].sum() if not positions_df.empty else 0.0
                theoretical_rpt_limit = (opening_balance * 0.01) * 0.90 
                rpt_limit_usd = min(theoretical_rpt_limit, risk_left_usd)
                total_potential_risk = open_positions_risk + pending_orders_risk
                rpt_available_usd = max(0, rpt_limit_usd - total_potential_risk)
                pl_target = ddl_limit_usd / 0.9 * 1.5 if ddl_limit_usd > 0 else (opening_balance * ddl_percent) * 1.5 # Target calculation adjusted for dynamic ceiling

                # Profit Consistency Calculation
                profit_consistency_percent = 0.0
                if not history_df.empty:
                    winning_trades = history_df[history_df['Net P/L'] > 0]
                    if not winning_trades.empty:
                        total_win_profit = winning_trades['Net P/L'].sum()
                        largest_win_profit = winning_trades['Net P/L'].max()
                        if total_win_profit > 0:
                            profit_consistency_percent = (largest_win_profit / total_win_profit) * 100

                payload = {
                            "status": "SESSION_ACTIVE", "equity": equity, "opening_balance": opening_balance,
                            "daily_pl_total_usd": session_total_pl,
                            "daily_pl_total_percent": (session_total_pl / opening_balance * 100) if opening_balance > 0 else 0.0,
                            "ddl_percent_setting": ddl_percent,
                            "ddl_limit_usd": ddl_limit_usd, 
                            "ddl_used_usd": ddl_used_usd, 
                            "ddl_left_usd": ddl_left_usd,
                            "realized_pl": history_df['Net P/L'].sum() if not history_df.empty else 0.0,
                            "pl_target": pl_target,
                            "profit_consistency_percent": profit_consistency_percent,

                            # [ CRITICAL SYNCHRONIZATION ] ---
                            # Ensure these two lines are present and use the new variables
                            "rpt_available_usd": rpt_available_usd,
                            "rpt_limit_usd": rpt_limit_usd, # This now correctly reflects the true, lower ceiling
                            # --- [ END SYNCHRONIZATION ] ---

                            "open_positions_total_profit": unrealized_pl,
                            "open_positions_total_risk": total_open_risk, # Corrected to use the variable we already have
                            "history_total_profit": history_df['Net P/L'].sum() if not history_df.empty else 0.0,
                            "risk_unit_usd": risk_unit_usd, # You might want to remove this if it's no longer used on the frontend
                            "open_positions": positions_df.to_dict('records'),
                            "pending_orders": pending_orders_df.to_dict('records'),
                            "trade_history": history_df.to_dict('records'),
                            "all_symbols": list(SESSION_STATE.get("symbol_properties", {}).keys()),
                            "portfolio_context": SESSION_STATE.get("portfolio_context"),
                            "mt5_account_id": SESSION_STATE.get("mt5_account_id"),
                        }            
            else:
                payload = {
                    "status": SESSION_STATE.get("status"),
                    "suggested_balance": SESSION_STATE.get("suggested_balance", 0.0),
                    "broker_name": SESSION_STATE.get("broker_name"),
                    "suggested_offset": 3
                }
            
            if CONNECTED_CLIENTS:
                await asyncio.gather(*(client.send(json.dumps(payload, default=json_converter)) for client in CONNECTED_CLIENTS))
            
            await asyncio.sleep(2)

        except websockets.exceptions.ConnectionClosed:
            await asyncio.sleep(2) 

        except Exception as e:
            print(f"ERROR in broadcast loop: {e}")
            traceback.print_exc()
            await asyncio.sleep(5)

# [ THE DEFINITIVE, CORRECTED VERSION ]
async def handle_client_commands(websocket, mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    global SESSION_STATE
    async for message in websocket:
        try:
            command = json.loads(message)
            event, payload = command.get("event"), command.get("payload", {})

            if event == "CONFIRM_TIMEZONE":
                offset = int(payload.get("offset"))
                broker_name = SESSION_STATE.get("broker_name")
                if broker_name and broker_name != 'Unknown Broker':
                    success = supabase_handler.set_broker_timezone(broker_name, offset)
                    if success:
                        print(f"Timezone for '{broker_name}' confirmed. Re-evaluating system state.")
                        await initialize_system_state(mt5_handler, supabase_handler)
                else:
                    print("ERROR: Cannot confirm timezone for an unknown broker.")

            elif event == "START_SESSION":
                user_confirmed_balance = float(payload.get("openingBalance", 0.0))
                if user_confirmed_balance > 0 and SESSION_STATE.get("status") == "READY_TO_START":
                    broker_date_str = SESSION_STATE.get("broker_date_str")
                    success = supabase_handler.set_daily_opening_balance(
                        SESSION_STATE.get("portfolio_id"), 
                        SESSION_STATE.get("mt5_account_id"), 
                        user_confirmed_balance,
                        broker_date_str
                    )
                    if success:
                        # [ THE FIX ] --- We now AUGMENT the state, not OVERWRITE it ---
                        SESSION_STATE["opening_balance"] = user_confirmed_balance
                        SESSION_STATE["status"] = "SESSION_ACTIVE"
                        # --- End of Fix ---
                        
                        print(f"\n✅ SESSION ACTIVATED for account {SESSION_STATE.get('mt5_account_id')} with user-confirmed balance: {user_confirmed_balance}\n")
                else:
                    print(f"WARNING: Could not start session. Balance: {user_confirmed_balance}, Status: {SESSION_STATE.get('status')}")

            elif event == "UPDATE_DDL_SETTING":
                new_ddl_percent = float(payload.get("ddl_percent"))
                portfolio_id = SESSION_STATE.get("portfolio_id")

                if portfolio_id and new_ddl_percent:
                    success = supabase_handler.update_portfolio_settings(
                        portfolio_id, 
                        {"DailyLossLimitPercent": new_ddl_percent}
                    )
                    if success:
                        SESSION_STATE["ddl_percent"] = new_ddl_percent
                        print(f"✅ Daily Risk for portfolio {portfolio_id} updated to {new_ddl_percent*100}%.")
                    else:
                        print(f"❌ FAILED to update Daily Risk for portfolio {portfolio_id}.")

        except Exception as e:
            print(f"Error processing client command: {e}")
            traceback.print_exc()

async def client_handler(websocket, mt5_handler, supabase_handler):
    print(f"Client connected: {websocket.remote_address}")
    CONNECTED_CLIENTS.add(websocket)
    try:
        # Send initial state immediately upon connection
        initial_payload = {
            "status": SESSION_STATE.get("status"),
            "suggested_balance": SESSION_STATE.get("suggested_balance", 0.0),
            "broker_name": SESSION_STATE.get("broker_name"),
            "suggested_offset": 3
        }
        await websocket.send(json.dumps(initial_payload, default=json_converter))
        
        await handle_client_commands(websocket, mt5_handler, supabase_handler)
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected normally: {websocket.remote_address}")
    finally:
        CONNECTED_CLIENTS.remove(websocket)

# [ แทนที่ฟังก์ชันเดิมทั้งหมดของคุณด้วยฟังก์ชันนี้ ]
async def initialize_system_state(mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    global SESSION_STATE
    # Hard reset on every startup to prevent state desync
    SESSION_STATE = { "status": "INITIALIZING" }

    account_info = mt5_handler.get_account_info()
    mt5_id_str = str(account_info.get('login'))
    
    terminal_info = mt5.terminal_info()
    broker_identifier = terminal_info.company if terminal_info else "Unknown Broker"
    
    SESSION_STATE.update({ "mt5_account_id": mt5_id_str, "broker_name": broker_identifier })
    print(f"Connected to Broker: {broker_identifier}, Account: {mt5_id_str}")

    broker_offset = supabase_handler.get_broker_timezone(broker_identifier)
    if broker_offset is None:
        SESSION_STATE["status"] = "REQUIRE_TIMEZONE_CONFIRMATION"
        return

    # --- This logic now correctly handles BOTH new and existing portfolios ---
    portfolio_context = supabase_handler.get_portfolio_by_mt5_account_id(mt5_id_str)
    if not portfolio_context:
        print(f"INFO: No portfolio found for MT5 ID {mt5_id_str}. Auto-provisioning new portfolio.")
        new_portfolio_id = str(uuid.uuid4())
        new_portfolio_data = {
            "PortfolioID": new_portfolio_id, "mt5_account_id": mt5_id_str, "PortfolioName": f"MT5 Acct {mt5_id_str}",
            "DailyLossLimitPercent": 0.01, "ConsistencyThresholdPercent": 30
        }
        portfolio_context, msg = supabase_handler.insert_new_portfolio(new_portfolio_data)
        if not portfolio_context:
            print("CRITICAL: Failed to create portfolio context. Halting.")
            return

    # --- All data is now fetched. Prepare for a single, definitive state update. ---
    portfolio_id = str(portfolio_context.get("PortfolioID"))
    
    ddl_percent = portfolio_context.get("DailyLossLimitPercent")
    if ddl_percent is None: ddl_percent = 0.01 # Defensive guard for old records
    
    broker_now = mt5_handler.get_broker_now(broker_offset)
    broker_date_str = broker_now.strftime('%Y-%m-%d')
    session_start_utc = mt5_handler.get_session_start_time_utc(broker_offset)
    
    SESSION_STATE.update({
        "portfolio_context": portfolio_context, "portfolio_id": portfolio_id,
        "symbol_properties": mt5_handler.get_all_symbol_properties(),
        "ddl_percent": ddl_percent, "broker_date_str": broker_date_str,
        "session_start_time_utc": session_start_utc
    })

    # --- This logic now correctly checks for the daily balance for the unified context ---
    existing_balance = supabase_handler.get_daily_opening_balance(portfolio_id, mt5_id_str, broker_date_str)
    if existing_balance is not None:
        SESSION_STATE.update({ "opening_balance": existing_balance, "status": "SESSION_ACTIVE" })
        print(f"STATE: Record found. Starting session automatically with balance: {existing_balance}")
    else:
        SESSION_STATE.update({ "status": "READY_TO_START", "suggested_balance": account_info.get('balance', 0.0) })
        print(f"STATE: New trading day for portfolio {portfolio_id}. Awaiting user confirmation.")

async def main():
    print("--- [VERSION: SYSTEM_INTEGRITY] Initializing Obsidian Core... ---")

    mt5_handler = MT5Handler()
    if not mt5_handler.initialize_connection():
        print("CRITICAL: MT5 connection failed. Server cannot start.")
        return
    
    supabase_handler = HeadlessSupabaseHandler(url=settings.SUPABASE_URL, key=settings.SUPABASE_KEY)
    if not supabase_handler.client:
        print("CRITICAL: Supabase connection failed. Server cannot start.")
        return

    # Run the state initialization logic
    await initialize_system_state(mt5_handler, supabase_handler)
    
    print(f"--- System Initialized. Current Status: {SESSION_STATE.get('status')} ---")
    
    handler_with_deps = functools.partial(client_handler, mt5_handler=mt5_handler, supabase_handler=supabase_handler)
    
    server = await websockets.serve(handler_with_deps, WEBSOCKET_HOST, WEBSOCKET_PORT)
    broadcast_task = asyncio.create_task(fetch_and_broadcast_data(mt5_handler, supabase_handler))
    
    print(f"WebSocket Server started at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    
    await SHUTDOWN_EVENT.wait() # Keep server running indefinitely

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shutdown requested by user.")
    finally:
        print("--- Server shutting down. ---")