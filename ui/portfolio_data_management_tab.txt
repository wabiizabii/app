import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
from core.supabase_handler import SupabaseHandler
from core import statement_processor

# --- Form for Adding/Editing Portfolios ---
def _render_portfolio_form(db_handler, is_edit_mode=False, portfolio_data=None):
    """Renders a form for adding or editing portfolios based on your original logic."""
    st.subheader("Edit Portfolio Details" if is_edit_mode else "Create New Portfolio")
    default_data = portfolio_data if portfolio_data is not None else {}
    form_key = f"form_{default_data.get('PortfolioID', 'add')}"

    with st.form(key=form_key):
        st.text_input("Portfolio Name*", value=default_data.get("PortfolioName", ""), key=f"name_{form_key}")
        st.number_input("Initial Balance ($)*", min_value=0.01, value=float(default_data.get("InitialBalance", 10000.0)), step=100.0, key=f"balance_{form_key}")
        st.text_input("Linked MT5 Account ID", value=default_data.get("mt5_account_id", ""), key=f"mt5_{form_key}")
        
        # You can add all the other detailed fields from your original form here
        
        submitted = st.form_submit_button("Save Changes" if is_edit_mode else "Create Portfolio")
        if submitted:
            # Retrieve values from session state using the unique keys
            name = st.session_state[f"name_{form_key}"]
            mt5_id = st.session_state[f"mt5_{form_key}"]
            initial_balance = st.session_state[f"balance_{form_key}"]
            
            if not name:
                st.warning("Portfolio Name is required.")
            else:
                data_to_save = {
                    "PortfolioName": name,
                    "mt5_account_id": mt5_id.strip() if mt5_id else None,
                    "InitialBalance": initial_balance,
                }
                
                if is_edit_mode:
                    success, msg = db_handler.update_portfolio(default_data["PortfolioID"], data_to_save)
                else:
                    success, msg = db_handler.add_portfolio(data_to_save)

                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

# --- Main Render Function for the entire Tab ---
def render(db_handler: SupabaseHandler):
    """Renders the entire Portfolio & Data Management tab."""
    st.title("💼 Portfolio & Data Management")
    
    # Use tabs for clean separation of concerns
    tab_manage, tab_upload = st.tabs(["Manage Portfolios", "Upload Statement"])
    
    # --- Tab 1: Manage Portfolios ---
    with tab_manage:
        st.header("Manage Your Portfolios")
        df_portfolios = db_handler.load_portfolios()

        if df_portfolios.empty:
            st.info("No portfolios found. Use the form below to create one.")
        else:
            st.dataframe(df_portfolios)
            st.markdown("---")
            
            portfolio_names = ["-- Select a portfolio to edit --"] + df_portfolios['PortfolioName'].tolist()
            selected_name = st.selectbox("Edit Portfolio", portfolio_names)
            
            if selected_name != "-- Select a portfolio to edit --":
                # Find the data for the selected portfolio
                portfolio_data_to_edit = df_portfolios[df_portfolios['PortfolioName'] == selected_name].iloc[0].to_dict()
                _render_portfolio_form(db_handler, is_edit_mode=True, portfolio_data=portfolio_data_to_edit)

        st.markdown("---")
        with st.expander("➕ Create New Portfolio"):
            _render_portfolio_form(db_handler, is_edit_mode=False)

    # --- Tab 2: Upload Statement ---
    with tab_upload:
        st.header("📊 Upload Statement Report")
        active_portfolio_id = st.session_state.get('active_portfolio_id')
        active_portfolio_name = st.session_state.get('active_portfolio_name')

        if not active_portfolio_id:
            st.warning("⚠️ Please select an active portfolio from the sidebar before uploading a statement.")
            st.file_uploader("Upload Statement File", type=['csv', 'htm', 'html'], disabled=True)
        else:
            st.success(f"Statements will be uploaded to the currently active portfolio: **{active_portfolio_name}**")
            uploaded_file = st.file_uploader("Choose a statement file (CSV/HTML)", type=['csv', 'htm', 'html'])

            if uploaded_file is not None:
                file_content = uploaded_file.getvalue()
                
                with st.spinner("Processing statement..."):
                    try:
                        processed_data = statement_processor.process_mt5_statement(file_content)
                        st.session_state['processed_statement_data'] = processed_data
                        st.session_state['processed_file_name'] = uploaded_file.name
                        st.success("File processed successfully!")
                        
                    except Exception as e:
                        st.error(f"An error occurred during file processing: {e}")
                        st.session_state['processed_statement_data'] = None

                # Display preview if processing was successful
                if st.session_state.get('processed_statement_data'):
                    st.subheader("Preview and Confirmation")
                    preview_data = st.session_state['processed_statement_data']
                    st.write("**Deals (Trades):**")
                    st.dataframe(preview_data.get('deals', pd.DataFrame()).head())
                    st.write("**Summary:**")
                    st.json(preview_data.get('final_summary_data', {}))

        # The "Save" button should be outside the "if uploaded_file" block
        # so it remains visible after the file is processed.
        if 'processed_statement_data' in st.session_state and st.session_state['processed_statement_data'] is not None:
            if st.button("💾 Confirm and Save Data to Supabase"):
                with st.spinner("Saving data to database..."):
                    data_to_save = st.session_state['processed_statement_data']
                    file_name = st.session_state['processed_file_name']
                    
                    # Placeholder for your complex saving logic
                    # You would call db_handler.save_actual_trades, save_statement_summary, etc. here
                    
                    # Example of saving deals:
                    deals_df = data_to_save.get('deals')
                    if not deals_df.empty:
                        # Add necessary metadata before saving
                        deals_df['PortfolioID'] = active_portfolio_id
                        deals_df['UserID'] = db_handler.user_id 
                        deals_df['SourceFile'] = file_name
                        
                        success, msg = db_handler.save_actual_trades(deals_df)
                        if success:
                            st.success("Deals saved successfully!")
                        else:
                            st.error(f"Failed to save deals: {msg}")
                    
                    # ... Add saving logic for other data parts (orders, positions, summary) ...

                    # Clean up session state after saving
                    del st.session_state['processed_statement_data']
                    del st.session_state['processed_file_name']
                    st.success("Statement data saved!")
                    st.balloons()