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
SESSION_STATE = { "status": "INITIALIZING", "mt5_account_id": None, "portfolio_id": None, "portfolio_context": None, "opening_balance": 0.0, "session_start_time_utc": None, "suggested_balance": 0.0, "is_resuming_session": False, "symbol_properties": {}, "risk_percent": 0.01, "subscribed_symbol": "XAUUSD" }

def json_converter(o):
    if isinstance(o, (datetime, pd.Timestamp)): return o.isoformat()
    if isinstance(o, (np.integer, np.int64)): return int(o)
    if isinstance(o, (np.floating, np.float64)): return float(o) if not np.isnan(o) else None
    return str(o)

async def fetch_and_broadcast_data(mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
    while True:
        try:
            if SESSION_STATE["status"] == "SESSION_ACTIVE":
                
                # --- [FIXED] v0.1.1 Added explicit connection check ---
                if not mt5.terminal_info():
                    raise ConnectionError("Connection to MetaTrader 5 terminal has been lost.")
                # --- End of Fix ---

                account_info = mt5_handler.get_account_info()
                if not account_info:
                    await asyncio.sleep(1) # Sleep briefly and retry
                    continue
                
                equity = account_info.get('equity', 0.0)
                balance = account_info.get('balance', 0.0)
                floating_pl = account_info.get('profit', 0.0)
                
                positions_df = mt5_handler.get_open_positions()
                pending_orders_df = mt5_handler.get_pending_orders()
                history_df = mt5_handler.get_trade_history(start_date=SESSION_STATE["session_start_time_utc"], end_date=datetime.now(pytz.utc))
                
                realized_pl_today = history_df['Profit'].sum() if not history_df.empty else 0.0
                realized_loss_today = abs(history_df[history_df['Profit'] < 0]['Profit'].sum()) if not history_df.empty else 0.0
                
                opening_balance = SESSION_STATE["opening_balance"]
                risk_percent_from_dial = SESSION_STATE["risk_percent"]
                risk_scaling_factor = 0.90
                
                available_risk = opening_balance * risk_percent_from_dial * risk_scaling_factor
                pl_target = available_risk * 3
                
                total_open_risk = positions_df['position_risk'].sum() if not positions_df.empty else 0.0
                risk_used_today = realized_loss_today + total_open_risk
                risk_left_today = available_risk - risk_used_today

                todays_total_pl = equity - opening_balance
                todays_total_pl_percent = (todays_total_pl / opening_balance * 100) if opening_balance > 0 else 0.0

                payload = {
                    "status": "SESSION_ACTIVE",
                    "equity": equity,
                    "balance": balance,
                    "unrealized_pl": floating_pl,
                    "realized_pl": realized_pl_today,
                    "opening_balance": opening_balance,
                    "available_risk": available_risk,
                    "risk_used": risk_used_today,
                    "risk_left": risk_left_today,
                    "pl_target": pl_target,
                    "todays_total_pl": todays_total_pl,
                    "todays_total_pl_percent": todays_total_pl_percent,
                    "open_positions": positions_df.to_dict('records'),
                    "pending_orders": pending_orders_df.to_dict('records'),
                    "trade_history": history_df.to_dict('records'),
                    "all_symbols": list(SESSION_STATE["symbol_properties"].keys()),
                    "portfolio_context": SESSION_STATE.get("portfolio_context"),
                    "mt5_account_id": SESSION_STATE.get("mt5_account_id"),
                    "current_tick": mt5_handler.get_current_tick(SESSION_STATE.get('subscribed_symbol', 'XAUUSD')) or {'bid': 0, 'ask': 0},
                    "open_positions_total_profit": positions_df['Profit'].sum() if not positions_df.empty else 0.0,
                    "open_positions_total_risk": total_open_risk,
                    "history_total_profit": realized_pl_today
                }
            else:
                payload = {"status": SESSION_STATE["status"], "suggested_balance": SESSION_STATE["suggested_balance"]}
            
            if CONNECTED_CLIENTS:
                await asyncio.gather(*(client.send(json.dumps(payload, default=json_converter)) for client in CONNECTED_CLIENTS))
            
            await asyncio.sleep(2)
        except Exception as e:
            print(f"ERROR in broadcast loop: {e}")
            traceback.print_exc()
            error_payload = {
                "status": "ERROR_STATE",
                "error": {
                    "title": "Backend System Error",
                    "message": f"A critical error occurred: {str(e)}. The system is attempting to recover."
                }
            }
            if CONNECTED_CLIENTS:
                await asyncio.gather(*(client.send(json.dumps(error_payload, default=json_converter)) for client in CONNECTED_CLIENTS))
            await asyncio.sleep(5)

# --- The rest of the file (listen_to_client, main, etc.) remains unchanged ---
async def listen_to_client(websocket, mt5_handler: MT5Handler, supabase_handler: HeadlessSupabaseHandler):
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
                        print(f"\n✅ SESSION ACTIVATED for account {SESSION_STATE['mt5_account_id']}\n")
                    else: print("--- [CRITICAL DATABASE ERROR] Failed to set daily opening balance in Supabase.")
            elif event == "CALCULATE_LOT_REQUEST":
                if SESSION_STATE["status"] == "SESSION_ACTIVE":
                    symbol, sl_price = payload.get('symbol'), float(payload.get('sl_price', 0))
                    tp_price, order_type_str = float(payload.get('tp_price', 0)), payload.get('order_type_str')
                    entry_price = float(payload.get('entry_price', 0.0))
                    risk_percent = float(payload.get('risk_percent', SESSION_STATE["risk_percent"]))
                    symbol_properties = SESSION_STATE["symbol_properties"].get(symbol)
                    if not symbol_properties: continue
                    opening_balance, risk_scaling_factor = SESSION_STATE["opening_balance"], 0.90
                    available_risk_for_day = opening_balance * risk_percent * risk_scaling_factor
                    history_df = mt5_handler.get_trade_history(SESSION_STATE["session_start_time_utc"], datetime.now(pytz.utc))
                    realized_loss_today = abs(history_df[history_df['Profit'] < 0]['Profit'].sum()) if not history_df.empty else 0.0
                    positions_df = mt5_handler.get_open_positions()
                    total_open_risk = positions_df['position_risk'].sum() if not positions_df.empty else 0.0
                    risk_left_now = available_risk_for_day - (realized_loss_today + total_open_risk)
                    order_type = mt5.ORDER_TYPE_BUY if "BUY" in order_type_str else mt5.ORDER_TYPE_SELL
                    metrics = mt5_handler.calculate_trade_metrics(
                        symbol_properties=symbol_properties, order_type=order_type,
                        risk_usd=max(0, risk_left_now), entry_price=entry_price,
                        sl_price=sl_price, tp_price=tp_price
                    )
                    await websocket.send(json.dumps({"event": "CALCULATE_LOT_RESPONSE", "payload": metrics}, default=json_converter))
            elif event == "RISK_DIAL_CHANGED":
                SESSION_STATE["risk_percent"] = float(payload.get("risk_percent", 0.01))
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

async def connection_handler(websocket, mt5_handler, supabase_handler):
    CONNECTED_CLIENTS.add(websocket)
    listen_task = asyncio.create_task(listen_to_client(websocket, mt5_handler, supabase_handler))
    try: await websocket.wait_closed()
    finally: listen_task.cancel(); CONNECTED_CLIENTS.remove(websocket)

async def main():
    supabase_handler = HeadlessSupabaseHandler(url=settings.SUPABASE_URL, key=settings.SUPABASE_KEY)
    if not supabase_handler.client: return
    mt5_handler = MT5Handler()
    if not mt5_handler.initialize_connection(): return
    SESSION_STATE["symbol_properties"] = mt5_handler.get_all_symbol_properties()
    mt5_id_str = str(mt5_handler.account_id)
    SESSION_STATE["mt5_account_id"] = mt5_id_str
    portfolio_context = supabase_handler.get_portfolio_by_mt5_account_id(mt5_id_str)
    if not portfolio_context:
        new_portfolio_id, new_portfolio_data = str(uuid.uuid4()), {"PortfolioID": new_portfolio_id, "mt5_account_id": mt5_id_str, "PortfolioName": f"MT5 Account {mt5_id_str}"}
        portfolio_context, msg = supabase_handler.insert_new_portfolio(new_portfolio_data)
        if not portfolio_context: return
    SESSION_STATE.update({"portfolio_context": portfolio_context, "portfolio_id": str(portfolio_context["PortfolioID"])})
    suggested_balance = supabase_handler.get_daily_opening_balance(SESSION_STATE["portfolio_id"], mt5_id_str)
    if suggested_balance is None:
        suggested_balance = mt5_handler.get_account_info().get('balance', 0.0)
    else:
        SESSION_STATE.update({"opening_balance": suggested_balance, "is_resuming_session": True})
    SESSION_STATE.update({"suggested_balance": suggested_balance, "status": "READY_TO_START"})
    handler_with_deps = functools.partial(connection_handler, mt5_handler=mt5_handler, supabase_handler=supabase_handler)
    server = await websockets.serve(handler_with_deps, WEBSOCKET_HOST, WEBSOCKET_PORT)
    broadcast_task = asyncio.create_task(fetch_and_broadcast_data(mt5_handler, supabase_handler))
    print("--- [SUCCESS] WebSocket Server is live!")
    try: await asyncio.Future()
    finally: broadcast_task.cancel(); server.close(); await server.wait_closed(); mt5_handler.shutdown_connection()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nServer shutting down.")