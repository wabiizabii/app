import streamlit as st
from core.supabase_handler import SupabaseHandler
from datetime import datetime
class PortfolioManager:
    """
    Manages user portfolios by interacting with the Supabase database.
    This includes adding, retrieving, updating, and deleting portfolios.
    """
    def __init__(self, db_handler: SupabaseHandler):
        """
        Initializes the PortfolioManager with a SupabaseHandler instance.

        Args:
            db_handler (SupabaseHandler): An instance of the SupabaseHandler for database interaction.
        """
        self.db_handler = db_handler
        self.table_name = "user_portfolios" # The table name in Supabase for portfolios

    def get_user_portfolios(self):
        """
        Retrieves all portfolios for the current authenticated user from Supabase.

        Returns:
            list: A list of dictionaries, where each dictionary represents a portfolio.
                  Returns an empty list if no portfolios are found or on error.
        """
        st.write("Fetching user portfolios...")
        try:
            # Ensure the user is authenticated. In a real app, you'd get the user_id from auth context.
            # For now, we might use a placeholder or assume a session-based user ID if not explicitly provided.
            # In Streamlit context, you often need to pass the user_id from auth.
            # For simplicity, let's assume `st.session_state['user_id']` exists after login.
            # If not, you might need to adjust how user_id is passed or retrieved.
            user_id = st.session_state.get('user_id') # Assumes user_id is stored in session state upon login
            if not user_id:
                st.error("Error: User not authenticated. Cannot fetch portfolios.")
                return []
            
            # Query portfolios for the current user (assuming 'user_id' column in your table)
            # Adjust the query if your security rules/table structure are different.
            data, count = self.db_handler.get_all(self.table_name, filters={"user_id": user_id})
            
            if data:
                st.write(f"Found {len(data)} portfolios.")
                return data
            else:
                st.write("No portfolios found for this user.")
                return []
        except Exception as e:
            st.error(f"Error retrieving portfolios: {e}")
            return []

    def add_portfolio(self, portfolio_name: str, mt5_account_id: str = None):
        """
        Adds a new portfolio for the current user to Supabase.

        Args:
            portfolio_name (str): The name of the new portfolio.
            mt5_account_id (str, optional): The MT5 account ID to link with this portfolio. Defaults to None.

        Returns:
            bool: True if the portfolio was added successfully, False otherwise.
        """
        st.write(f"Attempting to add new portfolio: {portfolio_name}")
        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Error: User not authenticated. Cannot add portfolio.")
            return False

        # Basic validation: Check if a portfolio with this name already exists for the user
        existing_portfolios, _ = self.db_handler.get_all(self.table_name, filters={"user_id": user_id, "portfolio_name": portfolio_name})
        if existing_portfolios:
            st.warning(f"Portfolio '{portfolio_name}' already exists for this user.")
            return False

        portfolio_data = {
            "user_id": user_id,
            "portfolio_name": portfolio_name,
            "mt5_account_id": mt5_account_id,
            "created_at": st.session_state.get('current_utc_timestamp_str', datetime.utcnow().isoformat()) + "Z",
            "last_updated": st.session_state.get('current_utc_timestamp_str', datetime.utcnow().isoformat()) + "Z",
            # Add other default portfolio parameters here if needed
            "default_risk_pct": 0.01,
            "daily_drawdown_limit_pct": 1.0,
            "current_balance": 10000.0, # Initial mock balance
            "AccountType": "STANDARD" # Default account type
        }
        
        try:
            response, count = self.db_handler.insert(self.table_name, [portfolio_data])
            if response:
                st.write(f"Portfolio '{portfolio_name}' added successfully.")
                return True
            else:
                st.error(f"Failed to add portfolio '{portfolio_name}'.")
                return False
        except Exception as e:
            st.error(f"Error adding portfolio: {e}")
            return False

    def update_portfolio_mt5_id(self, portfolio_id: str, new_mt5_account_id: str):
        """
        Updates the MT5 account ID for a specific portfolio.

        Args:
            portfolio_id (str): The ID of the portfolio to update.
            new_mt5_account_id (str): The new MT5 account ID to set.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        st.write(f"Attempting to update MT5 account ID for portfolio {portfolio_id} to {new_mt5_account_id}")
        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Error: User not authenticated. Cannot update portfolio.")
            return False

        update_data = {
            "mt5_account_id": new_mt5_account_id,
            "last_updated": st.session_state.get('current_utc_timestamp_str', datetime.utcnow().isoformat()) + "Z"
        }
        
        try:
            # Update only if the portfolio belongs to the current user
            response, count = self.db_handler.update(
                self.table_name,
                filters={"portfolio_id": portfolio_id, "user_id": user_id},
                data=update_data
            )
            if response:
                st.write(f"MT5 Account ID for portfolio {portfolio_id} updated successfully.")
                return True
            else:
                st.error(f"Failed to update MT5 Account ID for portfolio {portfolio_id}.")
                return False
        except Exception as e:
            st.error(f"Error updating portfolio MT5 ID: {e}")
            return False

    def delete_portfolio(self, portfolio_id: str):
        """
        Deletes a portfolio from Supabase.

        Args:
            portfolio_id (str): The ID of the portfolio to delete.

        Returns:
            bool: True if the portfolio was deleted successfully, False otherwise.
        """
        st.write(f"Attempting to delete portfolio: {portfolio_id}")
        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Error: User not authenticated. Cannot delete portfolio.")
            return False
        
        try:
            # Delete only if the portfolio belongs to the current user
            response, count = self.db_handler.delete(
                self.table_name,
                filters={"portfolio_id": portfolio_id, "user_id": user_id}
            )
            if response:
                st.write(f"Portfolio {portfolio_id} deleted successfully.")
                return True
            else:
                st.error(f"Failed to delete portfolio {portfolio_id}.")
                return False
        except Exception as e:
            st.error(f"Error deleting portfolio: {e}")
            return False

