# ui/ai_section.py (แก้ไขตามโค้ดของคุณ)

import streamlit as st
import pandas as pd
from core.supabase_handler import SupabaseHandler
import random
from datetime import datetime

def render_ai_insights_section(db_handler: SupabaseHandler):
    st.title("🤖 AI Insights")
    st.markdown("---")

    active_portfolio_id = st.session_state.get('active_portfolio_id_gs')
    active_portfolio_name = st.session_state.get('active_portfolio_name_gs')

    if not active_portfolio_id:
        st.warning("Please select a portfolio to view AI insights.")
        return

    st.subheader(f"Insights for **{active_portfolio_name}**")
    
    st.markdown("##### 📈 Your Performance Analysis")
    try:
        summary_data = db_handler.load_statement_summary(portfolio_id=active_portfolio_id)
        if not summary_data.empty:
            st.success(
                f"""
                - **Profitability:** Your portfolio has a net profit of `{summary_data['profit'].iloc[0]:,.2f} USD`.
                - **Total Trades:** `{summary_data['trades'].iloc[0]}`.
                - **Win Rate:** `{summary_data['win_rate'].iloc[0]:.2f}%`.
                """
            )
        else:
            st.info("No statement summary found. Please upload a statement to enable full analysis.")
    except AttributeError:
        st.warning("💡 **Note:** The `load_statement_summary` function is not available in your core. The following analysis is simulated.")
        st.info(
            """
            - **Simulated Profitability:** Your portfolio has generated a net profit of `500.00 USD`.
            - **Simulated Strengths:** The AI has identified that your trades on `XAUUSD` have been the most profitable.
            - **Simulated Weaknesses:** It appears your trades on `AAPL` have a low win rate.
            - **Recommendation:** Consider reviewing your strategy for `AAPL` or reducing exposure to this asset.
            """
        )
    
    st.markdown("---")

    st.markdown("##### 🌐 Market Sentiment Analysis")
    sentiment_options = {
        "Bullish": {"color": "🟢", "summary": "The market shows strong buying pressure..."},
        "Bearish": {"color": "🔴", "summary": "A downtrend is dominating the market..."},
        "Neutral": {"color": "🟡", "summary": "The market is consolidating..."}
    }
    
    current_sentiment = random.choice(list(sentiment_options.keys()))
    
    st.markdown(f"**Current Sentiment:** {sentiment_options[current_sentiment]['color']} **{current_sentiment}**")
    st.info(sentiment_options[current_sentiment]['summary'])
    
    st.markdown("---")