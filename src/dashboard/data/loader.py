"""
Data loading and filtering functions for the Bank Risk Dashboard
"""

import os
import pandas as pd
import yaml
from threading import Timer
from sqlalchemy import create_engine
from datatidy import DataTidy
from ..auth import user_management


# Global Variables
auto_save_timer = None


def auto_save_data(custom_metrics):
    """Auto-save current user data every 15 seconds"""
    global auto_save_timer
    if user_management.get_current_user() != 'Guest':
        # Only save if user has custom portfolios (not defaults)
        user_data = user_management.get_user_data(user_management.get_current_user())
        user_custom_portfolios = user_data.get('portfolios', {})
        
        # Only save portfolios if the user actually has custom ones
        portfolios_to_save = user_custom_portfolios
        user_management.save_user_data(user_management.get_current_user(), portfolios_to_save, custom_metrics)
    # Schedule next auto-save
    auto_save_timer = Timer(15.0, lambda: auto_save_data(custom_metrics))
    auto_save_timer.start()


def load_facilities_data():
    """
    Load facilities data using DataTidy transformations with fallback
    Returns: pd.DataFrame: Processed facilities data
    """
    db_path = 'data/bank_risk.db'
    config_path = 'data/datatidy_config.yaml'
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}. Please run db_data_generator.py first.")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"DataTidy config not found: {config_path}. Please run db_data_generator.py first.")
    
    try:
        print("Loading facilities data from database via DataTidy...")
        
        # Load DataTidy config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Process with DataTidy
        dt = DataTidy()
        dt.load_config(config)
        df = dt.process_data()
        
        print(f"✓ Loaded {len(df)} facility records from database via DataTidy")
        derived_fields = [col for col in df.columns if col in ['balance_millions', 'risk_category']]
        if derived_fields:
            print(f"✓ DataFrame includes derived fields: {derived_fields}")
        return df
        
    except Exception as e:
        print(f"DataTidy processing failed: {e}")
        print("Falling back to direct database query...")
        
        try:
            # Direct database fallback
            engine = create_engine(f'sqlite:///{db_path}')
            df = pd.read_sql('SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date', engine)
            print(f"✓ Loaded {len(df)} facility records from database (direct query)")
            return df
        except Exception as e2:
            raise Exception(f"Both DataTidy and direct database query failed. DataTidy error: {e}. Database error: {e2}")


