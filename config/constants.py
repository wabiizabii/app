# config/constants.py

# --- Trading Parameters ---
SYMBOL = "XAUUSD" # Default trading symbol (e.g., "XAUUSD", "EURUSD")
TIMEFRAME = "1h"  # Main timeframe for analysis (e.g., "1h", "4h", "1d")
INTERVAL_LARGE_TF = "1d" # Larger timeframe for multi-timeframe analysis (e.g., "1d", "1wk", "1mo")

# --- Historical Data Fetch Parameters ---
# Adjust START_DATE to fetch more historical data for model training
# For 32GB RAM, you can go back several years for daily data.
START_DATE = "2019-01-01" # Format: YYYY-MM-DD
END_DATE = None           # None means fetch until today's date

# --- Model Training Parameters ---
# Path to save/load the trained ML model, scaler, and feature names
MODEL_SAVE_PATH = "models/random_forest_model.joblib" 
# Number of recent bars to use for analysis (should be sufficient for indicators)
NUM_BARS_FOR_ANALYSIS = 200 
# Prediction horizon for target label generation (e.g., 2 means predict 2 periods ahead)
DEFAULT_PREDICTION_HORIZON = 2 

# --- Indicator Parameters (used in feature_engineer and indicators_calculator) ---
# MACD
MACD_FAST_PERIOD = 8
MACD_SLOW_PERIOD = 16
MACD_SIGNAL_PERIOD = 9

# RSI
RSI_PERIOD = 14

# CCI
CCI_PERIOD = 20

# Stochastic Oscillator
STOCH_K_PERIOD = 9
STOCH_D_PERIOD = 3

# EMA Periods (used in feature_engineer)
EMA_SHORT_PERIOD = 10
EMA_MEDIUM_PERIOD = 20
EMA_LONG_PERIOD = 50

# --- Supabase Configuration (for Ultimate Chart Dashboard) ---
# IMPORTANT: Replace with your actual Supabase URL and Anon Key
# These should ideally be loaded from environment variables for security in production
SUPABASE_URL = "https://xmqriscinxccbdggmtnb.supabase.co"    
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhtcXJpc2NpbnhjY2JkZ2dtdG5iIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTEyMjU3MywiZXhwIjoyMDY2Njk4NTczfQ.YUX36ML3CZmya4h3CJSuZvlRjinbsPX3yTWBTduJc88" 

# --- Telegram Notification Configuration (if using notifier.py) ---
# IMPORTANT: Replace with your actual Telegram Bot Token and Chat ID
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_HERE"
