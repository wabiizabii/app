# ==============================================================================
# FILE: services/portfolio_server.py (VERSION: FLEET_COMMAND_CRUD - COMPLETE)
# ==============================================================================
import asyncio
import websockets
import json
import traceback
import uuid
import pandas as pd
import numpy as np
from config import settings
from core.headless_supabase_handler import HeadlessSupabaseHandler
from core.statement_processor import process_mt5_statement
import datetime
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating, np.bool_)): return obj.item()
        if isinstance(obj, np.ndarray): return obj.tolist()
        if pd.isna(obj): return None
        return super(CustomEncoder, self).default(obj)

class PortfolioServer:
    def __init__(self, host='localhost', port=5556):
        self.host = host
        self.port = port
        self.server = None
        self.supabase_handler = HeadlessSupabaseHandler(
            url=settings.SUPABASE_URL, 
            key=settings.SUPABASE_KEY
        )
        print("[OK] HEADLESS Supabase client initialized successfully.")

    async def handler(self, websocket):
        print(f"[PortfolioServer] Client connected from: {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = data.get("event")
                    payload = data.get("payload", {})
                    
                    print(f"\n[PortfolioServer] Received event: '{event}'")

                    response = {"event": "OPERATION_STATUS", "request_event": event, "payload": {}}

                    # --- [FULL EVENT ROUTER] ---
                    if event == "GET_ALL_PORTFOLIOS":
                        portfolios = self.supabase_handler.get_all_portfolios()
                        response["event"] = "PORTFOLIO_LIST_DATA"
                        response["payload"] = {"portfolios": portfolios}
                    
                    elif event == "CREATE_PORTFOLIO":
                        new_data = payload
                        new_data['PortfolioID'] = str(uuid.uuid4())
                        created_portfolio, error_msg = self.supabase_handler.create_new_portfolio(new_data)
                        if error_msg:
                            response["payload"] = {"success": False, "message": error_msg}
                        else:
                            response["payload"] = {"success": True, "message": f"Portfolio '{created_portfolio.get('PortfolioName', '')}' created successfully."}

                    elif event == "UPDATE_PORTFOLIO":
                        portfolio_id = payload.get("portfolio_id")
                        update_data = payload.get("update_data")
                        success, error_msg = self.supabase_handler.update_portfolio_details(portfolio_id, update_data)
                        response["payload"] = {"success": success, "message": error_msg or "Portfolio updated successfully."}

                    elif event == "DELETE_PORTFOLIO":
                        portfolio_id = payload.get("portfolio_id")
                        success, error_msg = self.supabase_handler.delete_portfolio(portfolio_id)
                        response["payload"] = {"success": success, "message": error_msg or "Portfolio deleted successfully."}
                        
                    elif event == "UPLOAD_STATEMENT":
                        file_content_b64 = payload.get('file_content')
                        if file_content_b64:
                            file_content_bytes = file_content_b64.encode('utf-8')
                            processed_data = process_mt5_statement(file_content_bytes)
                            
                            for key in ['deals', 'orders', 'positions', 'deposit_withdrawal_logs']:
                                if key in processed_data and isinstance(processed_data[key], pd.DataFrame):
                                    df_sanitized = processed_data[key].replace({np.nan: None})
                                    processed_data[key] = df_sanitized.to_dict(orient='records')
                                else:
                                    processed_data[key] = []
                            
                            if 'final_summary_data' in processed_data:
                                summary = processed_data['final_summary_data']
                                processed_data['final_summary_data'] = {k: (None if pd.isna(v) else v) for k, v in summary.items()}

                            response["payload"] = {"success": True, "data": processed_data}
                        else:
                            response["payload"] = {"success": False, "message": "No file content received."}
                    
                    elif event == "SAVE_PROCESSED_DATA":
                        print("[PortfolioServer] Processing SAVE_PROCESSED_DATA...")
                        
                        # --- Data Extraction and Preparation ---
                        portfolio_id = payload.get('portfolio_id')
                        file_name = payload.get('file_name', 'Unknown')
                        import_batch_id = str(uuid.uuid4()) # Generate a unique ID for this entire upload batch

                        # Find portfolio name for enrichment
                        portfolio_info = self.supabase_handler.get_portfolio_by_id(portfolio_id)
                        portfolio_name = portfolio_info.get('PortfolioName', 'Unknown') if portfolio_info else 'Unknown'

                        summary_data = payload.get('final_summary_data', {})
                        deals_data = payload.get('deals', [])
                        positions_data = payload.get('positions', [])
                        orders_data = payload.get('orders', [])

                        # Enrich records with consistent metadata
                        for record in deals_data + positions_data + orders_data:
                            record['PortfolioID'] = portfolio_id
                            record['PortfolioName'] = portfolio_name
                            record['SourceFile'] = file_name
                            record['ImportBatchID'] = import_batch_id
                        
                        summary_data['PortfolioID'] = portfolio_id
                        summary_data['PortfolioName'] = portfolio_name
                        summary_data['SourceFile'] = file_name
                        summary_data['ImportBatchID'] = import_batch_id
                        summary_data['Timestamp'] = datetime.now().isoformat()
                        
                        # --- Database Operations ---
                        # We will save them sequentially to ensure data integrity
                        summary_success, summary_msg = self.supabase_handler.save_statement_summary(summary_data)
                        if not summary_success:
                            raise Exception(f"Failed to save summary: {summary_msg}")

                        deals_success, deals_msg = self.supabase_handler.save_bulk_deals(deals_data)
                        if not deals_success:
                            raise Exception(f"Failed to save deals: {deals_msg}")
                            
                        positions_success, positions_msg = self.supabase_handler.save_bulk_positions(positions_data)
                        if not positions_success:
                            raise Exception(f"Failed to save positions: {positions_msg}")
                        
                        orders_success, orders_msg = self.supabase_handler.save_bulk_orders(orders_data)
                        if not orders_success:
                            raise Exception(f"Failed to save orders: {orders_msg}")

                        # If all operations succeed
                        response['payload'] = {"success": True, "message": f"Successfully imported {len(deals_data)} deals and all related data from '{file_name}'."}

                    json_to_send = json.dumps(response, cls=CustomEncoder)
                    print(f"[PortfolioServer] Sending response for event '{event}'...")
                    await websocket.send(json_to_send)
                    print(f"[PortfolioServer] Response for event '{event}' sent successfully.")

                except Exception as e:
                    print(f"CRITICAL Error processing message in handler: {e}")
                    traceback.print_exc()
                    error_response = {
                        "event": "OPERATION_STATUS", 
                        "request_event": locals().get('event', 'unknown'),
                        "payload": {"success": False, "message": f"An error occurred: {str(e)}"}
                    }
                    await websocket.send(json.dumps(error_response))

        except websockets.exceptions.ConnectionClosed:
            print(f"[PortfolioServer] Client disconnected: {websocket.remote_address}")
        except Exception as e:
            print(f"An unexpected error occurred in the handler: {e}")
            traceback.print_exc()

    async def start(self):
        print(f"--- Starting Portfolio Command Center Server on ws://{self.host}:{self.port} ---")
        self.server = await websockets.serve(self.handler, self.host, self.port)
        await self.server.wait_closed()

def main():
    server = PortfolioServer()
    asyncio.run(server.start())

if __name__ == "__main__":
    main()