"""
Database-backed Bank Risk Data Generator

Generates ~14K facilities with monthly reporting over 10 years of history.
70/30 Corporate Banking / CRE split.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
import random
import sqlite3
from sqlalchemy import create_engine, text
import os
import logging

logger = logging.getLogger(__name__)


# MSA city coordinates for realistic lat/lon generation
MSA_COORDS = {
    'New York': (40.7128, -74.0060),
    'Dallas': (32.7767, -96.7970),
    'Chicago': (41.8781, -87.6298),
    'Los Angeles': (34.0522, -118.2437),
    'Houston': (29.7604, -95.3698),
    'Phoenix': (33.4484, -112.0740),
    'Philadelphia': (39.9526, -75.1652),
    'San Antonio': (29.4241, -98.4936),
    'San Diego': (32.7157, -117.1611),
    'San Jose': (37.3382, -121.8863),
    'Austin': (30.2672, -97.7431),
    'Jacksonville': (30.3322, -81.6557),
    'Fort Worth': (32.7555, -97.3308),
    'Columbus': (39.9612, -82.9988),
    'Charlotte': (35.2271, -80.8431),
    'San Francisco': (37.7749, -122.4194),
    'Indianapolis': (39.7684, -86.1581),
    'Seattle': (47.6062, -122.3321),
}


class DatabaseRiskDataGenerator:
    def __init__(self, db_path='data/bank_risk.db'):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}')

        self.corporate_industries = [
            'Manufacturing', 'Retail', 'Energy', 'Technology', 'Healthcare',
            'Financial Services', 'Transportation', 'Telecommunications', 'Real Estate', 'Consumer Goods'
        ]

        self.cre_property_types = [
            'Office', 'Retail', 'Multifamily', 'Industrial', 'Hotel', 'Mixed Use'
        ]

        self.msa_cities = list(MSA_COORDS.keys())

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
            conn.execute(text("DROP TABLE IF EXISTS raw_facilities"))

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
                    latitude REAL,
                    longitude REAL,
                    noi REAL,
                    property_value REAL,
                    dscr REAL,
                    ltv REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            conn.execute(text("DROP TABLE IF EXISTS generation_metadata"))

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

    @staticmethod
    def get_month_end_date(date):
        """Get the end-of-month date for any given date."""
        last_day = calendar.monthrange(date.year, date.month)[1]
        return datetime(date.year, date.month, last_day)

    def get_current_month_end(self):
        """Get the current month-end date."""
        now = datetime.now()
        return self.get_month_end_date(now)

    def generate_monthly_dates(self, start_date, end_date=None):
        """Generate end-of-month dates from start_date to end_date."""
        dates = []
        if end_date is None:
            end_date = self.get_current_month_end()

        current = self.get_month_end_date(start_date)

        while current <= end_date:
            dates.append(current)
            # Advance to next month
            if current.month == 12:
                current = datetime(current.year + 1, 1, 31)
            else:
                next_month = current.month + 1
                next_year = current.year
                last_day = calendar.monthrange(next_year, next_month)[1]
                current = datetime(next_year, next_month, last_day)

        return dates

    def generate_initial_rating(self):
        """Generate initial rating using normal distribution centered around 10"""
        rating = np.random.normal(10, 2.0)
        rating = max(1, min(16, round(rating)))
        return int(rating)

    def simulate_rating_transition(self, current_rating, is_defaulted=False, months_defaulted=0):
        """Simulate rating transition (monthly granularity).

        Default probability ~0.0017/month (≈0.005/quarter).
        Exit after 6 months defaulted (same real-time as 2 quarters).
        Lower per-step volatility since monthly is 3× more granular.
        """
        if is_defaulted:
            if months_defaulted >= 6:
                return None, True, months_defaulted + 1
            else:
                return 17, True, months_defaulted + 1

        if np.random.random() < 0.0017:
            return 17, True, 1

        change = np.random.poisson(0.15)

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

    def _jitter_coords(self, lat, lon):
        """Add slight random jitter to lat/lon (±0.15 degrees ≈ ±10 miles)."""
        return (
            lat + np.random.uniform(-0.15, 0.15),
            lon + np.random.uniform(-0.15, 0.15),
        )

    def generate_and_store_data(self, num_corporate=2100, num_cre=900):
        """Generate data and store in database"""
        all_facilities = []

        # Generate Corporate Banking facilities
        print(f"Generating {num_corporate} Corporate Banking obligors...")
        obligor_id = 1

        for i in range(num_corporate):
            if (i + 1) % 500 == 0:
                print(f"  Corporate progress: {i + 1}/{num_corporate}")

            obligor_name = self.generate_company_name()
            industry = random.choice(self.corporate_industries)
            msa = random.choice(self.msa_cities)
            lat, lon = self._jitter_coords(*MSA_COORDS[msa])

            num_facilities = random.randint(1, 3)

            for j in range(num_facilities):
                facility_id = f"F{obligor_id:05d}_{j+1:02d}"

                origination_date = datetime.now() - timedelta(days=np.random.randint(30, 3650))
                min_maturity_days = 730
                max_maturity_days = 2555  # ~7 years
                maturity_date = origination_date + timedelta(days=np.random.randint(min_maturity_days, max_maturity_days))

                monthly_dates = self.generate_monthly_dates(origination_date)

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
                months_defaulted = 0

                for date in monthly_dates:
                    rating_result = self.simulate_rating_transition(current_rating, is_defaulted, months_defaulted)

                    if rating_result[0] is None:
                        break

                    current_rating, is_defaulted, months_defaulted = rating_result

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
                        'msa': msa,
                        'latitude': round(lat, 4),
                        'longitude': round(lon, 4),
                        'noi': None,
                        'property_value': None,
                        'dscr': None,
                        'ltv': None
                    })

            obligor_id += 1

        # Generate CRE facilities
        print(f"Generating {num_cre} CRE obligors...")
        cre_start_id = num_corporate + 1

        for i in range(num_cre):
            if (i + 1) % 500 == 0:
                print(f"  CRE progress: {i + 1}/{num_cre}")

            obligor_name = self.generate_company_name()
            property_type = random.choice(self.cre_property_types)
            msa = random.choice(self.msa_cities)
            lat, lon = self._jitter_coords(*MSA_COORDS[msa])

            num_facilities = random.randint(1, 3)

            for j in range(num_facilities):
                facility_id = f"F{cre_start_id + i:05d}_{j+1:02d}"

                origination_date = datetime.now() - timedelta(days=np.random.randint(30, 3650))
                min_maturity_days = 730
                max_maturity_days = 2555  # ~7 years
                maturity_date = origination_date + timedelta(days=np.random.randint(min_maturity_days, max_maturity_days))

                monthly_dates = self.generate_monthly_dates(origination_date)

                # Base metrics
                base_balance = np.random.lognormal(mean=16, sigma=0.7)
                base_ltv_ratio = np.random.uniform(0.4, 0.75)
                base_property_value = base_balance / base_ltv_ratio
                base_cap_rate = np.random.uniform(0.06, 0.10)
                base_noi = base_property_value * base_cap_rate
                base_dscr = np.random.uniform(1.1, 2.5)

                current_rating = self.generate_initial_rating()
                is_defaulted = False
                months_defaulted = 0

                for date in monthly_dates:
                    rating_result = self.simulate_rating_transition(current_rating, is_defaulted, months_defaulted)

                    if rating_result[0] is None:
                        break

                    current_rating, is_defaulted, months_defaulted = rating_result

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
                        'latitude': round(lat, 4),
                        'longitude': round(lon, 4),
                        'noi': round(noi, 2),
                        'property_value': round(property_value, 2),
                        'dscr': round(dscr, 2),
                        'ltv': round(ltv, 2)
                    })

            # Note: obligor_id for CRE is cre_start_id + i, handled in facility_id above

        # Store in database
        print(f"Storing {len(all_facilities)} records in database...")
        df = pd.DataFrame(all_facilities)
        df.to_sql('raw_facilities', self.engine, if_exists='replace', index=False, chunksize=10000)

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
                'version': '2.0'
            })
            conn.commit()

        print(f"Stored {len(df)} facility records in database")
        unique_facilities = df['facility_id'].nunique()
        print(f"Unique facilities: {unique_facilities}")
        return len(df)


def generate_database_and_process():
    """Main function to generate database data."""
    os.makedirs('data', exist_ok=True)

    generator = DatabaseRiskDataGenerator()
    generator.setup_database()

    total_records = generator.generate_and_store_data(4800, 2050)

    print(f"Database generation complete!")
    print(f"Generated {total_records} facility records in database")

    return total_records


if __name__ == "__main__":
    generate_database_and_process()
