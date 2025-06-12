# ui/chart_section.py
import streamlit as st

def render_chart_section():
    """
    Renders the TradingView chart visualizer in the main area.
    Corresponds to 'SEC ??: MAIN AREA - CHART VISUALIZER' of main (1).py.
    """
    with st.expander("📈 Chart Visualizer", expanded=False):
        Symbol_to_display_default = "OANDA:XAUUSD" # Default Symbol
        Symbol_to_display = Symbol_to_display_default
        info_source = "ค่าเริ่มต้น"

        # Determine Symbol based on current mode's input or plot_data from log viewer
        current_mode = st.session_state.get("mode")
        current_Symbol_input_from_mode = ""

        if current_mode == "FIBO":
            current_Symbol_input_from_mode = st.session_state.get("Symbol_fibo_val_v2", "XAUUSD")
            info_source = f"Input ปัจจุบัน (FIBO: {current_Symbol_input_from_mode})"
        elif current_mode == "CUSTOM":
            current_Symbol_input_from_mode = st.session_state.get("Symbol_custom_val_v2", "XAUUSD")
            info_source = f"Input ปัจจุบัน (CUSTOM: {current_Symbol_input_from_mode})"
        else: # No mode or other mode, use default or plot_data
            info_source = "Input ปัจจุบัน (ยังไม่ได้เลือกโหมด)"


        # Override with plot_data if it exists (from Log Viewer)
        if 'plot_data' in st.session_state and st.session_state['plot_data']:
            Symbol_from_log = st.session_state['plot_data'].get('Symbol')
            if Symbol_from_log: # Check if 'Symbol' key exists and has a value
                current_Symbol_input_from_mode = Symbol_from_log # Prioritize Symbol from log
                info_source = f"Log Viewer ({current_Symbol_input_from_mode})"
        
        # Normalize the Symbol symbol for TradingView
        if current_Symbol_input_from_mode: # If any Symbol string is determined
            Symbol_upper = current_Symbol_input_from_mode.upper()
            if Symbol_upper == "XAUUSD":
                Symbol_to_display = "OANDA:XAUUSD"
            elif Symbol_upper == "EURUSD":
                Symbol_to_display = "OANDA:EURUSD"
            # Add more common mappings if needed, e.g., BTCUSD, OIL, etc.
            # For example:
            # elif Symbol_upper == "GBPUSD":
            #     Symbol_to_display = "OANDA:GBPUSD"
            # elif "USD" in Symbol_upper and len(Symbol_upper) == 6: # Basic check for FX pairs
            #     # Attempt to prefix with OANDA if it's a common FX structure
            #     # This might need a more robust check or a predefined list
            #     Symbol_to_display = f"OANDA:{Symbol_upper}"
            else:
                # For other symbols, try using them directly or allow user to specify prefix
                # For now, use directly as per original logic if not XAUUSD/EURUSD
                Symbol_to_display = Symbol_upper
        else: # Fallback if no Symbol determined from mode or log
            Symbol_to_display = Symbol_to_display_default
            info_source = "ค่าเริ่มต้น"


        st.info(f"แสดงกราฟ TradingView สำหรับ: **{Symbol_to_display}** (จาก: {info_source})")

        # TradingView Widget HTML (same as original)
        # Ensure locale is 'en' for broader compatibility or 'th' if preferred and supported well.
        tradingview_html = f"""
        <div class="tradingview-widget-container" style="height:100%;width:100%">
          <div id="tradingview_widget_chart" style="height:calc(100% - 32px);width:100%"></div>
          <div class="tradingview-widget-copyright">
            <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">
              <span class="blue-text">Track all markets on TradingView</span>
            </a>
          </div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget(
          {{
            "width": "100%",
            "height": 600,
            "symbol": "{Symbol_to_display}",
            "interval": "15",
            "timezone": "Asia/Bangkok",
            "theme": "dark",
            "style": "1",
            "locale": "th", 
            "enable_publishing": false,
            "withdateranges": true,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "details": true,
            "hotlist": true,
            "calendar": true,
            "container_id": "tradingview_widget_chart"
          }});
          </script>
        </div>
        """
        st.components.v1.html(tradingview_html, height=620)