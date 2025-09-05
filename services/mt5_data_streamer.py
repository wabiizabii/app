# services/mt5_data_streamer.py
import sys, os, asyncio, json, websockets, pandas as pd, traceback, uuid
from datetime import datetime, timezone
import numpy as np, pytz
import functools
import MetaTrader5 as mt5

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path: sys.path.insert(0, project_root)
from core.headless_supabase_handler import HeadlessSupabaseHandler
from core.mt5_handler import MT5Handler
from config import settings

WEBSOCKET_HOST, WEBSOCKET_PORT, CONNECTED_CLIENTS = "localhost", 5555, set()
SESSION_STATE = { 
    "status": "INITIALIZING", 
    "mt5_account_id": None, 
    "portfolio_id": None, 
    "portfolio_context": None, 
    "opening_balance": 0.0, 
    "session_start_time_utc": None, 
    "suggested_balance": 0.0, 
    "is_resuming_session": False, 
    "symbol_properties": {}, 
    "ddl_percent": 0.02,
    "session_flags": {
        "risk_warned_80": False,
        "risk_reached_100": False
    }
}
previous_history_df = pd.DataFrame()

def json_converter(o):
    if isinstance(o, (datetime, pd.Timestamp)): return o.isoformat()
    if isinstance(o, (np.integer, np.int64)): return int(o)
    if isinstance(o, (np.floating, np.float64)): return float(o) if not np.isnan(o) else None
    return str(o)

async def fetch_and_broadcast_data(mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    global previous_history_df
    while True:
        try:
            if SESSION_STATE["status"] == "SESSION_ACTIVE":
                current_account_info = mt5.account_info()
                if not current_account_info or str(current_account_info.login) != SESSION_STATE["mt5_account_id"]:
                    print(f"\n--- CRITICAL ERROR ---\nACCOUNT MISMATCH DETECTED! Shutting down.\n----------------------")
                    loop = asyncio.get_running_loop(); loop.stop(); return

                # --- [START] FINAL SUM FIX ---

                # Step 1: Get the processed history DataFrame that will be displayed
                history_df = mt5_handler.get_trade_history(start_date=SESSION_STATE["session_start_time_utc"], end_date=datetime.now(pytz.utc))
                
                # Step 2: Calculate the total SUM directly from THIS DataFrame
                history_total_profit_calculated = history_df['Profit'].sum() if not history_df.empty else 0.0
                print("--- Checking History Data ---")
                print(history_df)
                print("---------------------------")
                # Step 3: Use account_info for other REAL-TIME values that need to be exact
                equity = current_account_info.equity
                opening_balance = SESSION_STATE["opening_balance"]
                realized_pl_today = current_account_info.profit # For the Session P/L Card, this is the most accurate value

                positions_df = mt5_handler.get_open_positions()
                pending_orders_df = mt5_handler.get_pending_orders()
                
                unrealized_pl = positions_df['Profit'].sum() if not positions_df.empty else 0.0
                # The overall daily P/L for the HUD should also use the most accurate server value
                session_total_pl = realized_pl_today + unrealized_pl

                ddl_percent = SESSION_STATE.get("ddl_percent", 0.02)
                ddl_limit_usd = opening_balance * ddl_percent
                
                equity_drawdown = max(0, opening_balance - equity)
                ddl_used_usd = equity_drawdown
                ddl_left_usd = max(0, ddl_limit_usd - ddl_used_usd)

                risk_unit_usd = opening_balance * 0.01
                total_open_risk = positions_df['position_risk'].sum() if not positions_df.empty else 0.0
                rpt_limit_usd = risk_unit_usd * 0.90
                rpt_available_usd = max(0, rpt_limit_usd - total_open_risk)
                pl_target = ddl_limit_usd * 1.5
                
                # --- [END] FINAL SUM FIX ---

                payload = {
                    "status": "SESSION_ACTIVE", "equity": equity, "opening_balance": opening_balance,
                    "daily_pl_total_usd": session_total_pl,
                    "daily_pl_total_percent": (session_total_pl / opening_balance * 100) if opening_balance > 0 else 0.0,
                    "ddl_limit_usd": ddl_limit_usd, "ddl_used_usd": ddl_used_usd, "ddl_left_usd": ddl_left_usd,
                    "realized_pl": realized_pl_today,
                    "pl_target": pl_target,
                    "rpt_available_usd": rpt_available_usd, "rpt_limit_usd": rpt_limit_usd,
                    "open_positions_total_profit": unrealized_pl,
                    "open_positions_total_risk": total_open_risk,
                    "history_total_profit": history_total_profit_calculated, # THIS IS THE FIX for the table footer
                    "risk_unit_usd": risk_unit_usd,
                    "open_positions": positions_df.to_dict('records'),
                    "pending_orders": pending_orders_df.to_dict('records'),
                    "trade_history": history_df.to_dict('records'),
                    "events": [],
                    "all_symbols": list(SESSION_STATE["symbol_properties"].keys()),
                    "portfolio_context": SESSION_STATE.get("portfolio_context"),
                    "mt5_account_id": SESSION_STATE.get("mt5_account_id"),
                    "current_tick": mt5_handler.get_current_tick(SESSION_STATE.get('subscribed_symbol', 'XAUUSD')) or {'bid': 0, 'ask': 0}
                }
            else:
                payload = {"status": SESSION_STATE["status"], "suggested_balance": SESSION_STATE["suggested_balance"]}
            
            if CONNECTED_CLIENTS:
                await asyncio.gather(*(client.send(json.dumps(payload, default=json_converter)) for client in CONNECTED_CLIENTS))
            
            await asyncio.sleep(2)

        except websockets.exceptions.ConnectionClosed:
            print("INFO: Client connection closed normally.")
            await asyncio.sleep(2) 
        except Exception as e:
            print(f"ERROR in broadcast loop: {e}")
            traceback.print_exc()
            error_payload = {
                "status": "ERROR_STATE",
                "error": { "title": "Backend System Error", "message": f"A critical error occurred: {str(e)}. Attempting to recover." }
            }
            if CONNECTED_CLIENTS:
                clients_to_send = CONNECTED_CLIENTS.copy()
                await asyncio.gather(*(client.send(json.dumps(error_payload, default=json_converter)) for client in clients_to_send))
            await asyncio.sleep(5)

async def listen_to_client(websocket, mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    try:
        async for message in websocket:
            try:
                command = json.loads(message)
                event, payload = command.get("event"), command.get("payload", {})
                if event == "START_SESSION":
                    user_confirmed_balance = float(payload.get("openingBalance", 0.0))
                    if user_confirmed_balance > 0 and SESSION_STATE["status"] == "READY_TO_START":
                        success = supabase_handler.set_daily_opening_balance(SESSION_STATE["portfolio_id"], SESSION_STATE["mt5_account_id"], user_confirmed_balance) if not SESSION_STATE["is_resuming_session"] else True
                        if success:
                            SESSION_STATE.update({"opening_balance": user_confirmed_balance, "status": "SESSION_ACTIVE", "session_start_time_utc": mt5_handler._get_start_of_trading_day_utc()})
                            SESSION_STATE["session_flags"]["risk_warned_80"] = False
                            SESSION_STATE["session_flags"]["risk_reached_100"] = False
                            global previous_history_df; previous_history_df = pd.DataFrame()
                            print(f"\n✅ SESSION ACTIVATED for account {SESSION_STATE['mt5_account_id']}\n")
                        else: print("--- [CRITICAL DATABASE ERROR] Failed to set daily opening balance in Supabase.")
                
                elif event == "CALCULATE_LOT_REQUEST":
                    if SESSION_STATE["status"] == "SESSION_ACTIVE":
                        opening_balance = SESSION_STATE["opening_balance"]
                        ddl_percent = SESSION_STATE.get("ddl_percent", 0.02)
                        ddl_limit_usd = opening_balance * ddl_percent
                        account_info = mt5_handler.get_account_info()
                        equity = account_info.get('equity', 0.0)
                        ddl_used_now = max(0, opening_balance - equity)
                        risk_ceiling_from_ddl = max(0, ddl_limit_usd - ddl_used_now)
                        positions_df = mt5_handler.get_open_positions()
                        total_open_risk = positions_df['position_risk'].sum() if not positions_df.empty else 0.0
                        risk_unit_usd = opening_balance * 0.01
                        rpt_limit_usd = risk_unit_usd * 0.90
                        risk_ceiling_from_rpt = max(0, rpt_limit_usd - total_open_risk)
                        actual_risk_usd_allowed = min(risk_ceiling_from_ddl, risk_ceiling_from_rpt)
                        symbol_properties = SESSION_STATE["symbol_properties"].get(payload.get('symbol'))
                        if not symbol_properties: continue
                        metrics = mt5_handler.calculate_trade_metrics(
                            symbol_properties=symbol_properties, 
                            order_type=mt5.ORDER_TYPE_BUY if "BUY" in payload.get('order_type_str') else mt5.ORDER_TYPE_SELL,
                            risk_usd=actual_risk_usd_allowed,
                            entry_price=float(payload.get('entry_price', 0.0)),
                            sl_price=float(payload.get('sl_price', 0)), 
                            tp_price=float(payload.get('tp_price', 0))
                        )
                        await websocket.send(json.dumps({"event": "CALCULATE_LOT_RESPONSE", "payload": metrics}, default=json_converter))
                
                elif event == "SET_DDL_PERCENT":
                    SESSION_STATE["ddl_percent"] = float(payload.get("ddl_percent", 0.02))

                elif event == "EXECUTE_TRADE":
                    if SESSION_STATE["status"] == "SESSION_ACTIVE":
                        result = mt5_handler.execute_trade(payload)
                        await websocket.send(json.dumps({"event": "TRADE_RESULT", "payload": result}, default=json_converter))
                
                elif event == "CLOSE_POSITION":
                    if SESSION_STATE["status"] == "SESSION_ACTIVE":
                        ticket = payload.get("ticket")
                        if ticket: mt5_handler.close_position_by_ticket(ticket)
                
                elif event == "SUBSCRIBE_TICK":
                    if payload.get("symbol"):
                        SESSION_STATE['subscribed_symbol'] = payload.get("symbol")
            except Exception as e:
                print(f"Error processing client message: {e}"); traceback.print_exc()

    except websockets.exceptions.ConnectionClosed:
        print(f"INFO: Client {websocket.remote_address} disconnected.")
    
    finally:
        if websocket in CONNECTED_CLIENTS:
            CONNECTED_CLIENTS.remove(websocket)

async def connection_handler(websocket, mt5_handler, supabase_handler):
    CONNECTED_CLIENTS.add(websocket)
    await listen_to_client(websocket, mt5_handler, supabase_handler)

async def main():
    supabase_handler = HeadlessSupabaseHandler(url=settings.SUPABASE_URL, key=settings.SUPABASE_KEY)
    if not supabase_handler.client: return
    mt5_handler = MT5Handler()
    if not mt5_handler.initialize_connection(): return
    
    server = None
    broadcast_task = None
    try:
        SESSION_STATE["symbol_properties"] = mt5_handler.get_all_symbol_properties()
        mt5_id_str = str(mt5_handler.account_id)
        SESSION_STATE["mt5_account_id"] = mt5_id_str
        portfolio_context = supabase_handler.get_portfolio_by_mt5_account_id(mt5_id_str)
        if not portfolio_context:
            new_portfolio_id = str(uuid.uuid4())
            new_portfolio_data = {
                "PortfolioID": new_portfolio_id, 
                "mt5_account_id": mt5_id_str, 
                "PortfolioName": f"MT5 Account {mt5_id_str}"
            }
            portfolio_context, msg = supabase_handler.insert_new_portfolio(new_portfolio_data)
            if not portfolio_context: return
        SESSION_STATE.update({"portfolio_context": portfolio_context, "portfolio_id": str(portfolio_context["PortfolioID"])})
        suggested_balance = supabase_handler.get_daily_opening_balance(SESSION_STATE["portfolio_id"], mt5_id_str)
        if suggested_balance is None:
            suggested_balance = mt5_handler.get_account_info().get('balance', 0.0)
        else:
            SESSION_STATE.update({"opening_balance": suggested_balance, "is_resuming_session": True})
        SESSION_STATE.update({"suggested_balance": suggested_balance, "status": "READY_TO_START", "session_start_time_utc": mt5_handler._get_start_of_trading_day_utc()})
        handler_with_deps = functools.partial(connection_handler, mt5_handler=mt5_handler, supabase_handler=supabase_handler)
        server = await websockets.serve(handler_with_deps, WEBSOCKET_HOST, WEBSOCKET_PORT)
        broadcast_task = asyncio.create_task(fetch_and_broadcast_data(mt5_handler, supabase_handler))
        print("--- [SUCCESS] WebSocket Server is live!")
        await asyncio.Future()
    finally:
        if broadcast_task:
            broadcast_task.cancel()
        if server:
            server.close()
            await server.wait_closed()
        if mt5_handler and mt5_handler._is_connected:
            print("--- Shutting down MT5 connection. ---")
            mt5_handler.shutdown_connection()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer is shutting down.")