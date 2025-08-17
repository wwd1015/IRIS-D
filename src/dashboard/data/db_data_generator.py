"""
Database-backed Bank Risk Data Generator with DataTidy Integration

This module creates a SQLite database with raw bank risk data and uses DataTidy
to transform it into the final dataset consumed by the Dash app.

Key Features:
- SQLite database for data storage
- DataTidy YAML configuration for transformations
- Same data model as original generator but database-backed
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import sqlite3
from sqlalchemy import create_engine, text
import os
from datatidy import DataTidy

class DatabaseRiskDataGenerator:
    def __init__(self, db_path='data/bank_risk.db'):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}')
        
        # Same industry/property data as original
        self.corporate_industries = [
            'Manufacturing', 'Retail', 'Energy', 'Technology', 'Healthcare', 
            'Financial Services', 'Transportation', 'Telecommunications', 'Real Estate', 'Consumer Goods'
        ]
        
        self.cre_property_types = [
            'Office', 'Retail', 'Multifamily', 'Industrial', 'Hotel', 'Mixed Use'
        ]
        
        self.msa_cities = [
            'New York', 'Dallas', 'Chicago', 'Los Angeles', 'Houston', 'Phoenix',
            'Philadelphia', 'San Antonio', 'San Diego', 'San Jose', 'Austin', 'Jacksonville',
            'Fort Worth', 'Columbus', 'Charlotte', 'San Francisco', 'Indianapolis', 'Seattle'
        ]
        
        self.company_prefixes = [
            'Global', 'Advanced', 'Premier', 'Elite', 'Innovative', 'Strategic', 'Dynamic',
            'Progressive', 'Excellence', 'Quality', 'Professional', 'Enterprise', 'Solutions',
            'Industries', 'Corporation', 'Enterprises', 'Group', 'Partners', 'Holdings', 'International'
        ]
        
        self.company_suffixes = [
            'Inc', 'Corp', 'LLC', 'Ltd', 'Co', 'Company', 'Industries', 'Enterprises',
            'Group', 'Partners', 'Holdings', 'International', 'Solutions', 'Systems', 'Technologies'
        ]

    def setup_database(self):
        """Create database tables for raw data storage"""
        with self.engine.connect() as conn:
            # Raw facilities table
            conn.execute(text("""
                DROP TABLE IF EXISTS raw_facilities
            """))
            
            conn.execute(text("""
                CREATE TABLE raw_facilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    facility_id TEXT NOT NULL,
                    obligor_name TEXT NOT NULL,
                    obligor_rating INTEGER NOT NULL,
                    balance REAL NOT NULL,
                    origination_date TEXT NOT NULL,
                    maturity_date TEXT NOT NULL,
                    reporting_date TEXT NOT NULL,
                    lob TEXT NOT NULL,
                    industry TEXT,
                    free_cash_flow REAL,
                    fixed_charge_coverage REAL,
                    cash_flow_leverage REAL,
                    liquidity REAL,
                    profitability REAL,
                    growth REAL,
                    sir REAL,
                    cre_property_type TEXT,
                    msa TEXT,
                    noi REAL,
                    property_value REAL,
                    dscr REAL,
                    ltv REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Metadata table for tracking generation runs
            conn.execute(text("""
                DROP TABLE IF EXISTS generation_metadata
            """))
            
            conn.execute(text("""
                CREATE TABLE generation_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    num_corporate_obligors INTEGER,
                    num_cre_obligors INTEGER,
                    total_facilities INTEGER,
                    data_version TEXT
                )
            """))
            
            conn.commit()

    def generate_company_name(self):
        """Generate realistic company names"""
        prefix = random.choice(self.company_prefixes)
        suffix = random.choice(self.company_suffixes)
        industry_word = random.choice(['Tech', 'Solutions', 'Systems', 'Industries', 'Group', 'Corp'])
        return f"{prefix} {industry_word} {suffix}"

    def get_quarter_end_date(self, date):
        """Get the end of quarter date for any given date"""
        year = date.year
        month = date.month
        
        if month <= 3:
            return datetime(year, 3, 31)
        elif month <= 6:
            return datetime(year, 6, 30)
        elif month <= 9:
            return datetime(year, 9, 30)
        else:
            return datetime(year, 12, 31)

    def get_current_quarter_end(self):
        """Get the current quarter end date based on system time"""
        now = datetime.now()
        return self.get_quarter_end_date(now)

    def generate_quarterly_dates(self, start_date, end_date=None):
        """Generate end-of-quarter dates from start_date to current quarter end or end_date"""
        dates = []
        
        if end_date is None:
            end_date = self.get_current_quarter_end()
        
        current_date = self.get_quarter_end_date(start_date)
        
        while current_date <= end_date:
            dates.append(current_date)
            
            if current_date.month == 3:
                current_date = datetime(current_date.year, 6, 30)
            elif current_date.month == 6:
                current_date = datetime(current_date.year, 9, 30)
            elif current_date.month == 9:
                current_date = datetime(current_date.year, 12, 31)
            else:
                current_date = datetime(current_date.year + 1, 3, 31)
        
        return dates

    def generate_initial_rating(self):
        """Generate initial rating using normal distribution centered around 10"""
        rating = np.random.normal(10, 2.0)
        rating = max(1, min(16, round(rating)))
        return int(rating)

    def simulate_rating_transition(self, current_rating, is_defaulted=False, quarters_defaulted=0):
        """Simulate rating transition using Poisson distribution"""
        if is_defaulted:
            if quarters_defaulted >= 2:
                return None, True, quarters_defaulted + 1
            else:
                return 17, True, quarters_defaulted + 1
        
        if np.random.random() < 0.005:
            return 17, True, 1
        
        change = np.random.poisson(0.3)
        
        if change > 0:
            direction = 1 if np.random.random() < 0.5 else -1
            change = change * direction
        
        new_rating = current_rating + change
        new_rating = max(1, min(16, new_rating))
        
        return int(new_rating), False, 0

    def calculate_sir(self, balance):
        """Calculate SIR (estimated loss) for defaulted loans"""
        loss_rate = np.random.uniform(0.4, 0.9)
        sir = balance * loss_rate
        return min(sir, balance)

    def generate_and_store_data(self, num_corporate=100, num_cre=100):
        """Generate data and store in database"""
        all_facilities = []
        
        # Generate Corporate Banking facilities
        print("Generating Corporate Banking facilities...")
        obligor_id = 1
        
        for i in range(num_corporate):
            obligor_name = self.generate_company_name()
            industry = random.choice(self.corporate_industries)
            
            num_facilities = random.randint(1, 3)
            
            for j in range(num_facilities):
                facility_id = f"F{obligor_id:04d}_{j+1:02d}"
                
                origination_date = datetime.now() - timedelta(days=np.random.randint(365, 1825))
                min_maturity_days = 730
                max_maturity_days = 2190
                maturity_date = origination_date + timedelta(days=np.random.randint(min_maturity_days, max_maturity_days))
                
                quarterly_dates = self.generate_quarterly_dates(origination_date)
                
                # Base metrics
                base_balance = np.random.lognormal(mean=15, sigma=0.6)
                base_free_cash_flow = np.random.uniform(0.5, 3.0)
                base_fixed_charge_coverage = np.random.uniform(1.2, 4.0)
                base_cash_flow_leverage = np.random.uniform(2.0, 6.0)
                base_liquidity = np.random.uniform(1.0, 3.0)
                base_profitability = np.random.uniform(0.05, 0.25)
                base_growth = np.random.uniform(-0.1, 0.3)
                
                current_rating = self.generate_initial_rating()
                is_defaulted = False
                quarters_defaulted = 0
                
                for date in quarterly_dates:
                    rating_result = self.simulate_rating_transition(current_rating, is_defaulted, quarters_defaulted)
                    
                    if rating_result[0] is None:
                        break
                    
                    current_rating, is_defaulted, quarters_defaulted = rating_result
                    
                    # Evolving metrics
                    balance = base_balance * (1 + np.random.normal(0, 0.1))
                    free_cash_flow = max(0.1, base_free_cash_flow + np.random.normal(0, 0.2))
                    fixed_charge_coverage = max(0.5, base_fixed_charge_coverage + np.random.normal(0, 0.3))
                    cash_flow_leverage = max(0.5, base_cash_flow_leverage + np.random.normal(0, 0.4))
                    liquidity = max(0.1, base_liquidity + np.random.normal(0, 0.2))
                    profitability = max(-0.05, base_profitability + np.random.normal(0, 0.03))
                    growth = base_growth + np.random.normal(0, 0.05)
                    
                    sir = self.calculate_sir(balance) if current_rating == 17 else None
                    
                    all_facilities.append({
                        'facility_id': facility_id,
                        'obligor_name': obligor_name,
                        'obligor_rating': current_rating,
                        'balance': round(balance, 2),
                        'origination_date': origination_date.strftime('%Y-%m-%d'),
                        'maturity_date': maturity_date.strftime('%Y-%m-%d'),
                        'reporting_date': date.strftime('%Y-%m-%d'),
                        'lob': 'Corporate Banking',
                        'industry': industry,
                        'free_cash_flow': round(free_cash_flow, 2),
                        'fixed_charge_coverage': round(fixed_charge_coverage, 2),
                        'cash_flow_leverage': round(cash_flow_leverage, 2),
                        'liquidity': round(liquidity, 2),
                        'profitability': round(profitability, 3),
                        'growth': round(growth, 3),
                        'sir': round(sir, 2) if sir is not None else None,
                        'cre_property_type': None,
                        'msa': None,
                        'noi': None,
                        'property_value': None,
                        'dscr': None,
                        'ltv': None
                    })
            
            obligor_id += 1
        
        # Generate CRE facilities
        print("Generating CRE facilities...")
        obligor_id = 101
        
        for i in range(num_cre):
            obligor_name = self.generate_company_name()
            property_type = random.choice(self.cre_property_types)
            msa = random.choice(self.msa_cities)
            
            num_facilities = random.randint(1, 3)
            
            for j in range(num_facilities):
                facility_id = f"F{obligor_id:04d}_{j+1:02d}"
                
                origination_date = datetime.now() - timedelta(days=np.random.randint(365, 1825))
                min_maturity_days = 730
                max_maturity_days = 2190
                maturity_date = origination_date + timedelta(days=np.random.randint(min_maturity_days, max_maturity_days))
                
                quarterly_dates = self.generate_quarterly_dates(origination_date)
                
                # Base metrics
                base_balance = np.random.lognormal(mean=16, sigma=0.7)
                base_ltv_ratio = np.random.uniform(0.4, 0.75)
                base_property_value = base_balance / base_ltv_ratio
                base_cap_rate = np.random.uniform(0.06, 0.10)
                base_noi = base_property_value * base_cap_rate
                base_dscr = np.random.uniform(1.1, 2.5)
                
                current_rating = self.generate_initial_rating()
                is_defaulted = False
                quarters_defaulted = 0
                
                for date in quarterly_dates:
                    rating_result = self.simulate_rating_transition(current_rating, is_defaulted, quarters_defaulted)
                    
                    if rating_result[0] is None:
                        break
                    
                    current_rating, is_defaulted, quarters_defaulted = rating_result
                    
                    # Evolving metrics
                    balance = base_balance * (1 + np.random.normal(0, 0.1))
                    property_value = base_property_value * (1 + np.random.normal(0, 0.05))
                    noi = base_noi * (1 + np.random.normal(0, 0.08))
                    dscr = max(0.5, base_dscr + np.random.normal(0, 0.2))
                    ltv = (balance / property_value) * 100
                    
                    sir = self.calculate_sir(balance) if current_rating == 17 else None
                    
                    all_facilities.append({
                        'facility_id': facility_id,
                        'obligor_name': obligor_name,
                        'obligor_rating': current_rating,
                        'balance': round(balance, 2),
                        'origination_date': origination_date.strftime('%Y-%m-%d'),
                        'maturity_date': maturity_date.strftime('%Y-%m-%d'),
                        'reporting_date': date.strftime('%Y-%m-%d'),
                        'lob': 'CRE',
                        'industry': None,
                        'free_cash_flow': None,
                        'fixed_charge_coverage': None,
                        'cash_flow_leverage': None,
                        'liquidity': None,
                        'profitability': None,
                        'growth': None,
                        'sir': round(sir, 2) if sir is not None else None,
                        'cre_property_type': property_type,
                        'msa': msa,
                        'noi': round(noi, 2),
                        'property_value': round(property_value, 2),
                        'dscr': round(dscr, 2),
                        'ltv': round(ltv, 2)
                    })
            
            obligor_id += 1
        
        # Store in database
        print("Storing data in database...")
        df = pd.DataFrame(all_facilities)
        df.to_sql('raw_facilities', self.engine, if_exists='replace', index=False)
        
        # Store metadata
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO generation_metadata 
                (num_corporate_obligors, num_cre_obligors, total_facilities, data_version)
                VALUES (:corp, :cre, :total, :version)
            """), {
                'corp': num_corporate,
                'cre': num_cre, 
                'total': len(df),
                'version': '1.0'
            })
            conn.commit()
        
        print(f"Stored {len(df)} facility records in database")
        return len(df)

def create_datatidy_config():
    """Create comprehensive YAML configuration file for DataTidy transformations"""
    config = {
        'global_settings': {
            'error_handling': 'strict',
            'null_handling': 'keep',
            'date_format': '%Y-%m-%d',
            'decimal_places': 2,
            'chunk_size': 10000,
            'memory_limit': '1GB'
        },
        'input': {
            'type': 'database',
            'source': {
                'connection_string': 'sqlite:///data/bank_risk.db',
                'query': 'SELECT * FROM raw_facilities'
            }
        },
        'filters': [
            {
                'column': 'obligor_rating',
                'condition': '>=',
                'value': 1
            },
            {
                'column': 'obligor_rating', 
                'condition': '<=',
                'value': 17
            },
            {
                'column': 'balance',
                'condition': '>',
                'value': 0
            }
        ],
        'sort': [
            {
                'column': 'facility_id',
                'order': 'asc'
            },
            {
                'column': 'reporting_date',
                'order': 'asc'
            }
        ],
        'output': {
            'columns': {
                'facility_id': {
                    'source': 'facility_id',
                    'type': 'string',
                    'transformation': 'facility_id.str.upper()',
                    'validation': {
                        'required': True,
                        'pattern': '^F\\d{4}_\\d{2}$'
                    }
                },
                'obligor_name': {
                    'source': 'obligor_name',
                    'type': 'string',
                    'transformation': 'obligor_name.str.strip().str.title()',
                    'validation': {
                        'required': True,
                        'min_length': 3,
                        'max_length': 100
                    }
                },
                'obligor_rating': {
                    'source': 'obligor_rating',
                    'type': 'int',
                    'validation': {
                        'required': True,
                        'min': 1,
                        'max': 17
                    }
                },
                'balance': {
                    'source': 'balance',
                    'type': 'float',
                    'transformation': 'round(balance, 2)',
                    'validation': {
                        'required': True,
                        'min': 0
                    }
                },
                'balance_millions': {
                    'source': 'balance',
                    'type': 'float',
                    'transformation': 'round(balance / 1000000, 2)',
                    'validation': {
                        'min': 0
                    }
                },
                'risk_category': {
                    'source': 'obligor_rating',
                    'type': 'string',
                    'transformation': '"Low Risk" if obligor_rating <= 8 else ("Medium Risk" if obligor_rating <= 12 else ("High Risk" if obligor_rating <= 16 else "Default"))'
                },
                'origination_date': {
                    'source': 'origination_date',
                    'type': 'string',
                    'validation': {
                        'required': True
                    }
                },
                'maturity_date': {
                    'source': 'maturity_date',
                    'type': 'string',
                    'validation': {
                        'required': True
                    }
                },
                'reporting_date': {
                    'source': 'reporting_date',
                    'type': 'string',
                    'validation': {
                        'required': True
                    }
                },
                'lob': {
                    'source': 'lob',
                    'type': 'string',
                    'validation': {
                        'required': True,
                        'allowed_values': ['Corporate Banking', 'CRE']
                    }
                },
                'industry': {
                    'source': 'industry',
                    'type': 'string',
                    'transformation': 'industry.str.strip() if industry is not None else None'
                },
                'free_cash_flow': {
                    'source': 'free_cash_flow',
                    'type': 'float',
                    'transformation': 'round(free_cash_flow, 2) if free_cash_flow is not None else None',
                    'validation': {
                        'min': 0
                    }
                },
                'fixed_charge_coverage': {
                    'source': 'fixed_charge_coverage',
                    'type': 'float',
                    'transformation': 'round(fixed_charge_coverage, 2) if fixed_charge_coverage is not None else None',
                    'validation': {
                        'min': 0
                    }
                },
                'cash_flow_leverage': {
                    'source': 'cash_flow_leverage',
                    'type': 'float',
                    'transformation': 'round(cash_flow_leverage, 2) if cash_flow_leverage is not None else None',
                    'validation': {
                        'min': 0
                    }
                },
                'liquidity': {
                    'source': 'liquidity',
                    'type': 'float',
                    'transformation': 'round(liquidity, 2) if liquidity is not None else None',
                    'validation': {
                        'min': 0
                    }
                },
                'profitability': {
                    'source': 'profitability',
                    'type': 'float',
                    'transformation': 'round(profitability, 3) if profitability is not None else None'
                },
                'growth': {
                    'source': 'growth',
                    'type': 'float',
                    'transformation': 'round(growth, 3) if growth is not None else None'
                },
                'sir': {
                    'source': 'sir',
                    'type': 'float',
                    'transformation': 'round(sir, 2) if sir is not None else None',
                    'validation': {
                        'min': 0
                    }
                },
                'cre_property_type': {
                    'source': 'cre_property_type',
                    'type': 'string',
                    'transformation': 'cre_property_type.str.strip() if cre_property_type is not None else None',
                    'validation': {
                        'allowed_values': ['Office', 'Retail', 'Multifamily', 'Industrial', 'Hotel', 'Mixed Use', None]
                    }
                },
                'msa': {
                    'source': 'msa',
                    'type': 'string',
                    'transformation': 'msa.str.strip() if msa is not None else None'
                },
                'noi': {
                    'source': 'noi',
                    'type': 'float',
                    'transformation': 'round(noi, 2) if noi is not None else None',
                    'validation': {
                        'min': 0
                    }
                },
                'property_value': {
                    'source': 'property_value',
                    'type': 'float',
                    'transformation': 'round(property_value, 2) if property_value is not None else None',
                    'validation': {
                        'min': 0
                    }
                },
                'dscr': {
                    'source': 'dscr',
                    'type': 'float',
                    'transformation': 'round(dscr, 2) if dscr is not None else None',
                    'validation': {
                        'min': 0
                    }
                },
                'ltv': {
                    'source': 'ltv',
                    'type': 'float',
                    'transformation': 'round(ltv, 2) if ltv is not None else None',
                    'validation': {
                        'min': 0,
                        'max': 100
                    }
                }
            }
        },
        'validation': {
            'required_columns': ['facility_id', 'obligor_name', 'obligor_rating', 'balance', 'lob'],
            'unique_constraints': ['facility_id', 'reporting_date'],
            'rules': {
                'obligor_rating': {
                    'min': 1,
                    'max': 17
                },
                'balance': {
                    'min': 0
                },
                'ltv': {
                    'max': 100
                },
                'dscr': {
                    'min': 0
                }
            },
            'business_rules': [
                {
                    'name': 'corporate_banking_fields',
                    'condition': 'lob == "Corporate Banking"',
                    'required_fields': ['industry'],
                    'description': 'Corporate Banking facilities must have industry specified'
                },
                {
                    'name': 'cre_fields',
                    'condition': 'lob == "CRE"',
                    'required_fields': ['cre_property_type', 'msa'],
                    'description': 'CRE facilities must have property type and MSA specified'
                },
                {
                    'name': 'defaulted_loans_have_sir',
                    'condition': 'obligor_rating == 17',
                    'required_fields': ['sir'],
                    'description': 'Defaulted loans (rating 17) must have SIR value'
                }
            ]
        }
    }
    
    return config

def generate_database_and_process():
    """Main function to generate database data and process with DataTidy"""
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Initialize generator and setup database
    generator = DatabaseRiskDataGenerator()
    generator.setup_database()
    
    # Generate and store raw data
    total_records = generator.generate_and_store_data(100, 100)
    
    # Create DataTidy config
    config = create_datatidy_config()
    
    # Save config to YAML file
    import yaml
    with open('data/datatidy_config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print("Created DataTidy configuration file: data/datatidy_config.yaml")
    
    print(f"Database setup and DataTidy configuration complete!")
    print(f"Generated {total_records} facility records in database")
    print(f"DataTidy config saved to: data/datatidy_config.yaml")
    print(f"✓ Ready for data loading via DataTidy pipeline")
    
    return total_records

if __name__ == "__main__":
    generate_database_and_process()