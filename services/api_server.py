# services/api_server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys

# --- Dynamic Path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# --- FIX 1: Comment out the unused import ---
# from core.statement_processor import process_mt5_statement_html # ใช้ชื่อนี้
from core.supabase_handler import SupabaseHandler
from config import settings

# --- Initialization ---
app = Flask(__name__)
CORS(app)
db_handler = SupabaseHandler(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# --- FIX 2: Rename the function to match the one in your other files ---
@app.route('/upload_statement', methods=['POST'])
def upload_statement():
    print("[API Server] Received a file upload request.")
    if 'statementFile' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['statementFile']
    if not file:
        return jsonify({"status": "error", "message": "No file selected"}), 400

    try:
        file_content = file.read()
        
        # --- FIX 3: Comment out the call to the non-existent function ---
        # processed_data = process_mt5_statement_html(file_content)
        print("[API Server] DEBUG: File received. Processing is currently disabled.")
        
        # --- สำหรับดีบัก ---
        # เราจะยังไม่บันทึกลง DB แต่จะเช็คว่าอ่านข้อมูลได้หรือไม่
        # if not processed_data['positions'].empty or not processed_data['deals'].empty:
        #     print("[API Server] SUCCESS: Data was parsed from the HTML file.")
        #     return jsonify({"status": "success", "message": "File parsed successfully. Check server logs."}), 200
        # else:
        #     print("[API Server] ERROR: Processor ran but failed to extract any table data.")
        #     return jsonify({"status": "error", "message": "Failed to extract table data from HTML."}), 500
        
        # Return a temporary success message
        return jsonify({"status": "success", "message": "File received successfully. Processing is disabled for now."}), 200

    except Exception as e:
        print(f"[API Server] CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)