# core/mt5_handler.py
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, time as dt_time
import numpy as np
import pytz
from config import settings
import math
from collections import defaultdict

class MT5Handler:
    def __init__(self):
        self._is_connected = False
        self.account_id = None
        self.BROKER_TZ = pytz.timezone('Etc/GMT-3') 

    def initialize_connection(self):
        if self._is_connected: return True
        try:
            if not mt5.initialize(): return False
            account_info = mt5.account_info()
            if not account_info: mt5.shutdown(); return False
            self.account_id, self._is_connected = account_info.login, True
            print(f"Successfully connected to MT5 account {self.account_id}.")
            return True
        except Exception as e: return False

    def shutdown_connection(self):
        if self._is_connected: mt5.shutdown(); self._is_connected = False

    def _get_start_of_trading_day_utc(self):
        now_broker_time = datetime.now(self.BROKER_TZ)
        start_of_day_broker = self.BROKER_TZ.localize(datetime.combine(now_broker_time.date(), dt_time(0, 0)))
        return start_of_day_broker.astimezone(pytz.utc)
    
    def get_account_info(self): return mt5.account_info()._asdict() if self._is_connected and mt5.account_info() else None

    def get_all_symbol_properties(self):
        if not self._is_connected: return {}
        properties_map = {}
        symbols = mt5.symbols_get()
        if symbols:
            for s in symbols:
                info = mt5.symbol_info(s.name)
                if info: properties_map[s.name] = {"symbol": s.name, "contract_size": info.trade_contract_size, "lot_step": info.volume_step, "tick_size": info.trade_tick_size, "digits": info.digits}
        return properties_map
        
    def get_current_tick(self, symbol):
        tick = mt5.symbol_info_tick(symbol)
        return {'bid': tick.bid, 'ask': tick.ask} if self._is_connected and tick else None      

    def close_position_by_ticket(self, ticket):
        try:
            position = mt5.positions_get(ticket=int(ticket))
            if not position: return {"error": f"Position with ticket {ticket} not found."}
            position = position[0]
            symbol_info = mt5.symbol_info(position.symbol)
            request = { "action": mt5.TRADE_ACTION_DEAL, "symbol": position.symbol, "volume": position.volume, "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY, "position": position.ticket, "price": symbol_info.bid if position.type == mt5.ORDER_TYPE_BUY else symbol_info.ask, "deviation": 20, "magic": 12345, "comment": "Dashboard Close", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC }
            result = mt5.order_send(request)
            return result._asdict() if result else {"error": "Order Send Failed", "last_error": mt5.last_error()}
        except Exception as e: return {"error": str(e)}

    def get_open_positions(self):
        if not self._is_connected: return pd.DataFrame()
        positions = mt5.positions_get()
        if not positions: return pd.DataFrame()
        df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
        df['Time'] = pd.to_datetime(df['time'], unit='s', utc=True).dt.tz_convert('Asia/Bangkok').dt.strftime('%H:%M:%S')
        df['position_risk'] = df.apply(lambda p: abs(mt5.order_calc_profit(mt5.ORDER_TYPE_SELL if p['type'] == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY, p['symbol'], p['volume'], p['price_open'], p['sl'])) if p['sl'] > 0 else 0.0, axis=1)
        df['position_reward'] = df.apply(lambda p: mt5.order_calc_profit(p['type'], p['symbol'], p['volume'], p['price_open'], p['tp']) if p['tp'] > 0 else 0.0, axis=1)
        df['position_rr'] = df.apply(lambda r: r['position_reward'] / r['position_risk'] if r['position_risk'] > 0 else 0, axis=1)
        df['Type'] = df['type'].apply(lambda x: 'Buy' if x == mt5.ORDER_TYPE_BUY else 'Sell')
        df.rename(columns={'symbol': 'Symbol', 'volume': 'Volume', 'profit': 'Profit', 'price_open': 'Price', 'sl': 'SL', 'tp': 'TP', 'ticket': 'Ticket'}, inplace=True)
        return df[['Ticket', 'Time', 'Symbol', 'Type', 'Volume', 'Price', 'SL', 'TP', 'Profit', 'position_risk', 'position_rr']]
    
    def get_pending_orders(self):
        if not self._is_connected: return pd.DataFrame()
        orders = mt5.orders_get()
        if not orders: return pd.DataFrame()
        df = pd.DataFrame(list(orders), columns=orders[0]._asdict().keys())
        if df.empty: return pd.DataFrame()
        order_type_map = {mt5.ORDER_TYPE_BUY_LIMIT: 'Buy Limit', mt5.ORDER_TYPE_SELL_LIMIT: 'Sell Limit', mt5.ORDER_TYPE_BUY_STOP: 'Buy Stop', mt5.ORDER_TYPE_SELL_STOP: 'Sell Stop'}
        df['Type'] = df['type'].map(order_type_map)
        df = df[df['Type'].notna()]
        if df.empty: return pd.DataFrame()
        df['Time'] = pd.to_datetime(df['time_setup'], unit='s', utc=True).dt.tz_convert('Asia/Bangkok').dt.strftime('%H:%M:%S')
        df.rename(columns={'ticket': 'Ticket', 'symbol': 'Symbol', 'volume_current': 'Lots', 'price_open': 'Entry Price', 'sl': 'SL', 'tp': 'TP'}, inplace=True)
        return df[['Ticket', 'Time', 'Symbol', 'Type', 'Lots', 'Entry Price', 'SL', 'TP']]

        # [CORRECTED V3] The most robust trade history logic
    def get_trade_history(self, start_date, end_date):
        if not self._is_connected:
            return pd.DataFrame()
        deals = mt5.history_deals_get(start_date, end_date)
        if deals is None or len(deals) == 0:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        
        trade_deals = df[df['position_id'] != 0].copy()
        if trade_deals.empty:
            return pd.DataFrame()

        trade_deals['net_profit'] = trade_deals['profit'] + trade_deals['commission'] + trade_deals['swap']

        summary = trade_deals.groupby('position_id').agg(
            Symbol=('symbol', 'first'),
            Type=('type', 'first'),
            Volume=('volume', 'first'),
            Close_Time_Raw=('time', 'last'),
            Profit=('net_profit', 'sum')
        ).reset_index()

        if summary.empty:
            return pd.DataFrame()

        summary['Close Time'] = pd.to_datetime(summary['Close_Time_Raw'], unit='s', utc=True).dt.tz_convert('Asia/Bangkok').dt.strftime('%H:%M:%S')
        
        summary['Type'] = summary['Type'].map({mt5.DEAL_TYPE_BUY: 'Buy', mt5.DEAL_TYPE_SELL: 'Sell'})
        
        return summary[['Close Time', 'Symbol', 'Type', 'Volume', 'Profit']].sort_values(by='Close Time', ascending=True)
    
    def execute_trade(self, trade_details):
        try:
            symbol, order_type_str, lot_size, sl, tp, entry = trade_details.get('symbol'), trade_details.get('type'), float(trade_details.get('lot_size')), float(trade_details.get('sl', 0)), float(trade_details.get('tp', 0)), float(trade_details.get('entry_price', 0))
            if not symbol: return {"error": "Symbol is missing"}
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info: return {"error": f"Symbol {symbol} not found"}
            order_map = { "MARKET_BUY": mt5.ORDER_TYPE_BUY, "MARKET_SELL": mt5.ORDER_TYPE_SELL, "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT, "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT, "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP, "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP }
            order_type = order_map.get(order_type_str)
            if order_type is None: return {"error": "Invalid order type"}
            price = entry if "MARKET" not in order_type_str else (symbol_info.ask if order_type == mt5.ORDER_TYPE_BUY else symbol_info.bid)
            request = { "action": mt5.TRADE_ACTION_DEAL if "MARKET" in order_type_str else mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": lot_size, "type": order_type, "price": price, "sl": sl, "tp": tp, "deviation": 20, "magic": 12345, "comment": "Dashboard Trade", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_FOK, }
            result = mt5.order_send(request)
            return result._asdict() if result else {"error": "Order Send Failed", "last_error": mt5.last_error()}
        except Exception as e:
            return {"error": str(e)}

    # --- [CORRECTED & CONSOLIDATED] New Calculation Engine ---
    def calculate_trade_metrics(self, symbol_properties: dict, order_type: int, risk_usd: float, entry_price: float, sl_price: float, tp_price: float):
        results = {"lot_size": 0.0, "potential_loss_usd": 0.0, "potential_profit_usd": 0.0, "rr_ratio": 0.0}
        if not self._is_connected or sl_price <= 0 or risk_usd <= 0: return results

        symbol = symbol_properties.get("symbol")
        contract_size = symbol_properties.get("contract_size", 1)
        lot_step = symbol_properties.get("lot_step", 0.01)

        current_price = entry_price
        if current_price <= 0:
            tick = mt5.symbol_info_tick(symbol)
            if not tick: return results
            current_price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        stop_distance_price = abs(current_price - sl_price)
        if stop_distance_price <= 0: return results
        
        loss_per_lot = stop_distance_price * contract_size
        if loss_per_lot <= 0: return results
        
        lot_size = risk_usd / loss_per_lot
        lot_size = math.floor(lot_size / lot_step) * lot_step
        if lot_size <= 0: return results
        results["lot_size"] = lot_size

        loss_calc_type = mt5.ORDER_TYPE_SELL if order_type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        actual_loss = abs(mt5.order_calc_profit(loss_calc_type, symbol, lot_size, current_price, sl_price) or 0.0)
        results["potential_loss_usd"] = actual_loss

        if tp_price > 0:
            actual_profit = abs(mt5.order_calc_profit(order_type, symbol, lot_size, current_price, tp_price) or 0.0)
            results["potential_profit_usd"] = actual_profit
            if actual_loss > 0:
                results["rr_ratio"] = actual_profit / actual_loss
        
        return results