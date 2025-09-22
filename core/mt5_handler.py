# core/mt5_handler.py (The Definitive Version)
import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime, time as dt_time, timedelta
import numpy as np
import pytz
from config import settings
import math
from collections import defaultdict
import traceback

class MT5Handler:
    def __init__(self):
        self._is_connected = False
        self.account_id = None
        
    def initialize_connection(self):
        if self._is_connected: 
            return True
        try:
            if not mt5.initialize():
                print(f"initialize() failed, error code = {mt5.last_error()}")
                return False
            
            account_info = mt5.account_info()
            if not account_info:
                print(f"account_info() failed, error code = {mt5.last_error()}")
                mt5.shutdown()
                return False
                
            self.account_id, self._is_connected = account_info.login, True
            print(f"Successfully connected to MT5 account {self.account_id}.")
            return True

        except Exception as e:
            print(f"An exception occurred during MT5 initialization: {e}")
            return False

    def shutdown_connection(self):
        if self._is_connected: mt5.shutdown(); self._is_connected = False

    def get_account_info(self):
        if not self._is_connected: return None
        account_info = mt5.account_info()
        if not account_info: return None
        
        # Convert to dictionary and add the server info
        info_dict = account_info._asdict()
        info_dict['server_name'] = account_info.server  # This contains the real broker server name
        return info_dict

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
            if result:
                print(f"Position {ticket} close order sent successfully. Result code: {result.retcode}")
                return {"success": True, "result": result._asdict()}
            else:
                print(f"Failed to send close order for position {ticket}. Error: {mt5.last_error()}")
                return {"error": "Order Send Failed", "last_error": mt5.last_error()}
        except Exception as e: return {"error": str(e)}

    # [ THE DEFINITIVE, ADAPTED FUNCTION ]
    def get_open_positions(self):
        if not self._is_connected:
            return pd.DataFrame()
        
        positions = mt5.positions_get()
        if not positions:
            return pd.DataFrame()
            
        df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
        if not df.empty:
            df['Time'] = df['time'].apply(lambda x: pd.to_datetime(x, unit='s', utc=True).isoformat())

        # [ THE FIX ] --- This new logic no longer references 'commission' ---
        def calculate_risk_without_commission(position):
            # A position is considered at "Break-Even" if the SL is at or better than the entry price.
            # While not perfect (doesn't account for costs), it's the safest assumption with available data.
            is_break_even = (
                (position['type'] == mt5.ORDER_TYPE_BUY and position['sl'] >= position['price_open']) or
                (position['type'] == mt5.ORDER_TYPE_SELL and position['sl'] > 0 and position['sl'] <= position['price_open'])
            )
            
            if position['sl'] > 0 and not is_break_even:
                return abs(mt5.order_calc_profit(
                    mt5.ORDER_TYPE_SELL if position['type'] == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    position['symbol'],
                    position['volume'],
                    position['price_open'],
                    position['sl']
                ) or 0.0)
            else:
                # If no SL or at BE, committed risk is zero
                return 0.0

        df['position_risk'] = df.apply(calculate_risk_without_commission, axis=1)
        # --- [ END OF FIX ] ---

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
        if not df.empty:
            df['Time'] = df['time_setup'].apply(lambda x: pd.to_datetime(x, unit='s', utc=True).isoformat())
        df['position_risk'] = df.apply(lambda o: abs(mt5.order_calc_profit(mt5.ORDER_TYPE_SELL if o['type'] in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else mt5.ORDER_TYPE_BUY, o['symbol'], o['volume_initial'], o['price_open'], o['sl'])) if o['sl'] > 0 else 0.0, axis=1)
        df.rename(columns={'ticket': 'Ticket', 'symbol': 'Symbol', 'volume_initial': 'Volume', 'price_open': 'Price', 'sl': 'SL', 'tp': 'TP'}, inplace=True)
        return df[['Ticket', 'Time', 'Symbol', 'Type', 'Volume', 'Price', 'SL', 'TP', 'position_risk']]

    def get_trade_history(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        if not self._is_connected:
            return pd.DataFrame()

        # [THE DEFINITIVE FIX]
        # We revert to using datetime objects directly, which is the most compatible method.
        # The key is ensuring the start_date for the lookup is far enough in the past.
        history_start_lookup = start_date - timedelta(days=30)
        
        all_deals = mt5.history_deals_get(history_start_lookup, end_date)
        
        if all_deals is None or len(all_deals) == 0:
            return pd.DataFrame()

        deals_df = pd.DataFrame(list(all_deals), columns=all_deals[0]._asdict().keys())
        deals_df['time_dt'] = pd.to_datetime(deals_df['time'], unit='s', utc=True)
        
        # Filter for deals that were closed within the current session (using datetime objects)
        closing_deals_today = deals_df[
            (deals_df['time_dt'] >= start_date) &
            (deals_df['time_dt'] <= end_date) &
            (deals_df['entry'].isin([mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT]))
        ]

        closed_position_ids = closing_deals_today['position_id'].unique()

        if len(closed_position_ids) == 0:
            return pd.DataFrame()

        # The rest of the function logic remains the same.
        relevant_deals = deals_df[deals_df['position_id'].isin(closed_position_ids)].copy()
        opening_deals = relevant_deals[relevant_deals['entry'] == mt5.DEAL_ENTRY_IN].copy()
        opening_deals = opening_deals.loc[opening_deals.groupby('position_id')['time'].idxmin()]
        summary_agg = relevant_deals.groupby('position_id').agg(
            Symbol=('symbol', 'first'), Volume=('volume', 'first'),
            Close_Time_Raw=('time', 'last'), Gross_Profit=('profit', 'sum'),
            Commission=('commission', 'sum'), Swap=('swap', 'sum')
        ).reset_index()
        summary = pd.merge(summary_agg, opening_deals[['position_id', 'type']], on='position_id', how='left')

        if not summary.empty:
            summary['Net P/L'] = summary['Gross_Profit'] + summary['Commission'] + summary['Swap']
            summary['Type'] = summary['type'].map({mt5.ORDER_TYPE_BUY: 'Buy', mt5.ORDER_TYPE_SELL: 'Sell'})
            summary['Close Time'] = summary['Close_Time_Raw'].apply(lambda x: pd.to_datetime(x, unit='s', utc=True).isoformat())
            summary['Costs'] = summary['Commission'] + summary['Swap']
            summary.rename(columns={'Gross_Profit': 'Gross P/L'}, inplace=True)
            return summary[['Close Time', 'Symbol', 'Type', 'Volume', 'Gross P/L', 'Costs', 'Net P/L']].sort_values(by='Close Time', ascending=True)
        
        return pd.DataFrame()    
        
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

    def calculate_trade_metrics(self, symbol_properties: dict, order_type: int, risk_usd: float, entry_price: float, sl_price: float, tp_price: float):
        results = {"lot_size": 0.0, "potential_loss_usd": 0.0, "potential_profit_usd": 0.0, "rr_ratio": 0.0, "sl_pips": 0, "tp_pips": 0, "tick_value": 0}
        if not self._is_connected or sl_price <= 0 or risk_usd <= 0: return results

        symbol = symbol_properties.get("symbol")
        point = mt5.symbol_info(symbol).point
        tick_value = mt5.symbol_info(symbol).trade_tick_value

        current_price = entry_price
        if current_price <= 0:
            tick = mt5.symbol_info_tick(symbol)
            if not tick: return results
            current_price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
            
        sl_pips = abs(current_price - sl_price) / point
        loss_per_lot = sl_pips * tick_value
        
        if loss_per_lot <= 0: return results
        
        lot_step = symbol_properties.get("lot_step", 0.01)
        lot_size = risk_usd / loss_per_lot
        lot_size = math.floor(lot_size / lot_step) * lot_step
        if lot_size < lot_step: return results

        results["lot_size"] = lot_size
        results["sl_pips"] = sl_pips
        results["tick_value"] = tick_value

        loss_calc_type = mt5.ORDER_TYPE_SELL if order_type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        actual_loss = abs(mt5.order_calc_profit(loss_calc_type, symbol, lot_size, current_price, sl_price) or 0.0)
        results["potential_loss_usd"] = actual_loss

        if tp_price > 0:
            tp_pips = abs(tp_price - current_price) / point
            results["tp_pips"] = tp_pips
            actual_profit = abs(mt5.order_calc_profit(order_type, symbol, lot_size, current_price, tp_price) or 0.0)
            results["potential_profit_usd"] = actual_profit
            if actual_loss > 0:
                results["rr_ratio"] = actual_profit / actual_loss
        
        return results

    def get_broker_now(self, broker_timezone_offset: int):
        """
        [SYSTEM INTEGRITY FIX] New helper function to get the current time in the broker's timezone.
        """
        try:
            broker_tz = pytz.timezone(f'Etc/GMT{-broker_timezone_offset}')
            return datetime.now(pytz.utc).astimezone(broker_tz)
        except Exception:
            # Fallback to UTC if offset is invalid
            return datetime.now(pytz.utc)

    def get_session_start_time_utc(self, broker_timezone_offset: int):
        """
        Calculates the start of the trading day (00:00) in UTC, based on the broker's timezone offset.
        """
        try:
            now_broker_time = self.get_broker_now(broker_timezone_offset)
            start_of_day_broker = now_broker_time.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_day_utc = start_of_day_broker.astimezone(pytz.utc)
            print(f"Calculated Session Start Time (UTC) using offset {broker_timezone_offset}: {start_of_day_utc}")
            return start_of_day_utc
        except Exception as e:
            print(f"ERROR calculating session start time: {e}. Falling back to current UTC day.")
            return datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    def get_balance_at_time(self, target_time_utc: datetime):
        """
        Finds the account balance from the deal history.
        This version uses direct positional access to prevent KeyError.
        """
        if not self._is_connected: return None
        
        try:
            deals = mt5.history_deals_get(target_time_utc - timedelta(days=3), target_time_utc)
            
            if deals is None or len(deals) == 0:
                account_info = self.get_account_info()
                return account_info.get('balance') if account_info else None

            # Sort deals by time in descending order (most recent first) directly on the list of tuples
            deals_sorted = sorted(deals, key=lambda d: d.time, reverse=True)

            # Find the first deal that occurred at or before the target time
            last_deal_tuple = None
            target_timestamp = int(target_time_utc.timestamp())

            for deal in deals_sorted:
                if deal.time <= target_timestamp:
                    last_deal_tuple = deal
                    break # Found the latest deal we need

            if last_deal_tuple:
                # [THE DEFINITIVE FIX]
                # Access the 'balance' field directly from the namedtuple.
                # This completely bypasses pandas DataFrame and potential column name issues.
                return last_deal_tuple.balance
            else:
                # No deals found before the session start time, fallback to current balance
                account_info = self.get_account_info()
                return account_info.get('balance') if account_info else None

        except Exception as e:
            print(f"   - ERROR in get_balance_at_time: {e}")
            traceback.print_exc()
            return None