"""
Data loading and filtering functions for the Bank Risk Dashboard
"""

import os
import pandas as pd
from threading import Timer
from sqlalchemy import create_engine
from .models import FacilityDataset
from ..auth import user_management


# Global Variables
auto_save_timer = None
_data_cache = {}
_cache_timestamp = None


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
    Load facilities data from SQLite database with Pydantic validation and transformations
    Returns: pd.DataFrame: Processed and validated facilities data
    """
    global _data_cache, _cache_timestamp
    import time
    
    # Check cache (valid for 1 day)
    current_time = time.time()
    if _cache_timestamp and (current_time - _cache_timestamp) < 86400 and 'facilities_df' in _data_cache:
        print("✓ Using cached facilities data")
        return _data_cache['facilities_df']
    
    db_path = 'data/bank_risk.db'
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}. Please run db_data_generator.py first.")
    
    try:
        print("=== Bank Risk Dashboard - Pydantic Data Validation ===")
        print("Loading facilities data from database...")
        
        # Load raw data from SQLite
        engine = create_engine(f'sqlite:///{db_path}')
        raw_df = pd.read_sql('SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date', engine)
        
        print(f"✓ Loaded {len(raw_df)} raw facility records from database")
        
        # Validate and transform data using Pydantic
        print("Validating and transforming data with Pydantic...")
        dataset = FacilityDataset.from_dataframe(raw_df)
        
        # Convert back to DataFrame with computed fields
        processed_df = dataset.to_dataframe()
        
        print(f"✓ Validated {len(processed_df)} facility records with Pydantic")
        
        # Show derived fields
        derived_fields = [col for col in processed_df.columns if col in ['balance_millions', 'risk_category', 'quarters_since_origination']]
        if derived_fields:
            print(f"✓ Added computed fields: {derived_fields}")
        
        # Show summary stats
        stats = dataset.get_summary_stats()
        print(f"✓ Dataset summary: {stats['total_facilities']} facilities, ${stats['total_balance_millions']:.1f}M total balance")
        print(f"✓ LOB distribution: {stats['lob_distribution']}")
        print(f"✓ Risk categories: {stats['risk_category_distribution']}")
        
        # Cache the result
        _data_cache['facilities_df'] = processed_df
        _cache_timestamp = current_time
        
        return processed_df
        
    except Exception as e:
        print(f"Error loading data with Pydantic validation: {e}")
        print("Falling back to direct database query...")
        
        try:
            # Fallback: direct database load without validation
            engine = create_engine(f'sqlite:///{db_path}')
            df = pd.read_sql('SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date', engine)
            
            # Add basic computed fields manually
            df['balance_millions'] = df['balance'] / 1_000_000
            df['risk_category'] = df['obligor_rating'].apply(
                lambda x: "Pass Rated" if x <= 13 else "Watch" if x == 14 else "Criticized" if x <= 16 else "Defaulted" if x == 17 else "Defaulted"
            )
            
            print(f"✓ Loaded {len(df)} facility records from database (fallback mode)")
            return df
            
        except Exception as e2:
            raise Exception(f"Both Pydantic validation and direct database query failed. Pydantic error: {e}. Database error: {e2}")


