"""
Enhanced Bank Risk Data Generator

Key Features:
- Rating system: 1-17 (17 = defaulted loans)
- Rating distribution: Normal distribution centered around 10 (fewer high ratings 14+)
- Rating transitions: Poisson distribution with 0 notch being most common
- Quarterly data limited to current quarter end (not maturity date)
- SIR (estimated loss) column for defaulted loans (rating 17)
- Defaulted loans remain on books for exactly 2 quarters then removed
- Default probability: 0.5% per quarter
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

class RiskDataGenerator:
    def __init__(self):
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
        
        # Use current quarter end if no end_date specified
        if end_date is None:
            end_date = self.get_current_quarter_end()
        
        # Start from the first quarter end after or on the start date
        current_date = self.get_quarter_end_date(start_date)
        
        while current_date <= end_date:
            dates.append(current_date)
            
            # Move to next quarter end
            if current_date.month == 3:
                current_date = datetime(current_date.year, 6, 30)
            elif current_date.month == 6:
                current_date = datetime(current_date.year, 9, 30)
            elif current_date.month == 9:
                current_date = datetime(current_date.year, 12, 31)
            else:  # December
                current_date = datetime(current_date.year + 1, 3, 31)
        
        return dates
    
    def generate_initial_rating(self):
        """Generate initial rating using normal distribution centered around 10 (ratings 1-17)"""
        # Use normal distribution centered at 10 with std dev of 2.0
        # This creates fewer high-risk ratings (14+) and concentrates around 8-12
        rating = np.random.normal(10, 2.0)
        # Clamp to 1-16 range (17 is only for defaults that happen later)
        rating = max(1, min(16, round(rating)))
        return int(rating)
    
    def simulate_rating_transition(self, current_rating, is_defaulted=False, quarters_defaulted=0):
        """Simulate rating transition using Poisson distribution"""
        if is_defaulted:
            # If already defaulted (rating 17), stay defaulted
            if quarters_defaulted >= 2:
                # Remove from dataset after 2 quarters
                return None, True, quarters_defaulted + 1
            else:
                return 17, True, quarters_defaulted + 1
        
        # Check for new default (0.5% chance per quarter)
        if np.random.random() < 0.005:
            return 17, True, 1
        
        # Normal rating transitions using Poisson (lambda=0.3 for low probability of change)
        # 0 notch is most common (no change)
        change = np.random.poisson(0.3)
        
        # Randomly determine direction (50/50 chance of upgrade vs downgrade)
        if change > 0:
            direction = 1 if np.random.random() < 0.5 else -1
            change = change * direction
        
        new_rating = current_rating + change
        # Clamp to valid range (1-16, excluding 17 which is default only)
        new_rating = max(1, min(16, new_rating))
        
        return int(new_rating), False, 0
    
    def calculate_sir(self, balance):
        """Calculate SIR (estimated loss) for defaulted loans, capped at balance"""
        # SIR typically ranges from 40-90% of balance for defaulted loans
        loss_rate = np.random.uniform(0.4, 0.9)
        sir = balance * loss_rate
        return min(sir, balance)  # Cap at balance
    
    def generate_corporate_obligors(self, num_obligors=100):
        """Generate 100 Corporate Banking obligors with 1-3 facilities each and quarterly time series"""
        facilities = []
        obligor_id = 1
        
        for i in range(num_obligors):
            # Generate obligor details
            obligor_name = self.generate_company_name()
            industry = random.choice(self.corporate_industries)
            
            # Determine number of facilities for this obligor (1-3)
            num_facilities = random.randint(1, 3)
            
            # Generate facilities for this obligor
            for j in range(num_facilities):
                facility_id = f"F{obligor_id:04d}_{j+1:02d}"
                
                # Fixed dates - ensure minimum 2 years between origination and maturity
                origination_date = datetime.now() - timedelta(days=np.random.randint(365, 1825))  # Last 5 years
                min_maturity_days = 730  # At least 2 years from origination
                max_maturity_days = 2190  # Up to 6 years from origination
                maturity_date = origination_date + timedelta(days=np.random.randint(min_maturity_days, max_maturity_days))
                
                # Generate quarterly time series from origination to current quarter end (not maturity)
                quarterly_dates = self.generate_quarterly_dates(origination_date)
                
                # Initialize base metrics for this facility
                base_balance = np.random.lognormal(mean=15, sigma=0.6)
                base_free_cash_flow = np.random.uniform(0.5, 3.0)
                base_fixed_charge_coverage = np.random.uniform(1.2, 4.0)
                base_cash_flow_leverage = np.random.uniform(2.0, 6.0)
                base_liquidity = np.random.uniform(1.0, 3.0)
                base_profitability = np.random.uniform(0.05, 0.25)
                base_growth = np.random.uniform(-0.1, 0.3)
                
                # Start with normally distributed rating centered around 11
                current_rating = self.generate_initial_rating()
                is_defaulted = False
                quarters_defaulted = 0
                
                for idx, date in enumerate(quarterly_dates):
                    # Simulate rating transition
                    rating_result = self.simulate_rating_transition(current_rating, is_defaulted, quarters_defaulted)
                    
                    # If facility should be removed (defaulted for 2+ quarters), skip
                    if rating_result[0] is None:
                        break
                    
                    current_rating, is_defaulted, quarters_defaulted = rating_result
                    
                    # Financial metrics that evolve over time with some randomness
                    balance = base_balance * (1 + np.random.normal(0, 0.1))
                    free_cash_flow = max(0.1, base_free_cash_flow + np.random.normal(0, 0.2))
                    fixed_charge_coverage = max(0.5, base_fixed_charge_coverage + np.random.normal(0, 0.3))
                    cash_flow_leverage = max(0.5, base_cash_flow_leverage + np.random.normal(0, 0.4))
                    liquidity = max(0.1, base_liquidity + np.random.normal(0, 0.2))
                    profitability = max(-0.05, base_profitability + np.random.normal(0, 0.03))
                    growth = base_growth + np.random.normal(0, 0.05)
                    
                    # Calculate SIR for defaulted loans (rating 17)
                    sir = self.calculate_sir(balance) if current_rating == 17 else None
                    
                    facilities.append({
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
        
        return pd.DataFrame(facilities)
    
    def generate_cre_obligors(self, num_obligors=100):
        """Generate 100 CRE obligors with 1-3 facilities each and quarterly time series"""
        facilities = []
        obligor_id = 101  # Start from 101 to avoid conflicts
        
        for i in range(num_obligors):
            # Generate obligor details
            obligor_name = self.generate_company_name()
            property_type = random.choice(self.cre_property_types)
            msa = random.choice(self.msa_cities)
            
            # Determine number of facilities for this obligor (1-3)
            num_facilities = random.randint(1, 3)
            
            # Generate facilities for this obligor
            for j in range(num_facilities):
                facility_id = f"F{obligor_id:04d}_{j+1:02d}"
                
                # Fixed dates - ensure minimum 2 years between origination and maturity
                origination_date = datetime.now() - timedelta(days=np.random.randint(365, 1825))  # Last 5 years
                min_maturity_days = 730  # At least 2 years from origination
                max_maturity_days = 2190  # Up to 6 years from origination
                maturity_date = origination_date + timedelta(days=np.random.randint(min_maturity_days, max_maturity_days))
                
                # Generate quarterly time series from origination to current quarter end (not maturity)
                quarterly_dates = self.generate_quarterly_dates(origination_date)
                
                # Initialize base metrics for this facility
                base_balance = np.random.lognormal(mean=16, sigma=0.7)
                base_ltv_ratio = np.random.uniform(0.4, 0.75)  # LTV between 40-75%
                base_property_value = base_balance / base_ltv_ratio
                base_cap_rate = np.random.uniform(0.06, 0.10)  # 6-10% cap rate
                base_noi = base_property_value * base_cap_rate
                base_dscr = np.random.uniform(1.1, 2.5)
                
                # Start with normally distributed rating centered around 11
                current_rating = self.generate_initial_rating()
                is_defaulted = False
                quarters_defaulted = 0
                
                for idx, date in enumerate(quarterly_dates):
                    # Simulate rating transition
                    rating_result = self.simulate_rating_transition(current_rating, is_defaulted, quarters_defaulted)
                    
                    # If facility should be removed (defaulted for 2+ quarters), skip
                    if rating_result[0] is None:
                        break
                    
                    current_rating, is_defaulted, quarters_defaulted = rating_result
                    
                    # Financial metrics that evolve over time with some randomness
                    balance = base_balance * (1 + np.random.normal(0, 0.1))
                    property_value = base_property_value * (1 + np.random.normal(0, 0.05))
                    noi = base_noi * (1 + np.random.normal(0, 0.08))
                    dscr = max(0.5, base_dscr + np.random.normal(0, 0.2))
                    ltv = (balance / property_value) * 100
                    
                    # Calculate SIR for defaulted loans (rating 17)
                    sir = self.calculate_sir(balance) if current_rating == 17 else None
                    
                    facilities.append({
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
        
        return pd.DataFrame(facilities)
    
    def generate_covenant_data(self, facilities_df):
        """Generate covenant compliance data for each facility"""
        covenant_data = []
        
        for _, facility in facilities_df.iterrows():
            facility_id = facility['facility_id']
            lob = facility['lob']
            
            if lob == 'Corporate Banking':
                # Corporate covenants
                covenants = [
                    {
                        'covenant_type': 'Fixed Charge Coverage',
                        'current_value': facility['fixed_charge_coverage'],
                        'covenant_limit': 1.25,
                        'status': 'Compliant' if facility['fixed_charge_coverage'] >= 1.25 else 'Violation'
                    },
                    {
                        'covenant_type': 'Cash Flow Leverage',
                        'current_value': facility['cash_flow_leverage'],
                        'covenant_limit': 4.0,
                        'status': 'Compliant' if facility['cash_flow_leverage'] <= 4.0 else 'Violation'
                    },
                    {
                        'covenant_type': 'Liquidity',
                        'current_value': facility['liquidity'],
                        'covenant_limit': 1.0,
                        'status': 'Compliant' if facility['liquidity'] >= 1.0 else 'Violation'
                    }
                ]
            else:
                # CRE covenants
                covenants = [
                    {
                        'covenant_type': 'DSCR',
                        'current_value': facility['dscr'],
                        'covenant_limit': 1.25,
                        'status': 'Compliant' if facility['dscr'] >= 1.25 else 'Violation'
                    },
                    {
                        'covenant_type': 'LTV',
                        'current_value': facility['ltv'],
                        'covenant_limit': 65.0,
                        'status': 'Compliant' if facility['ltv'] <= 65.0 else 'Violation'
                    }
                ]
            
            for covenant in covenants:
                covenant_data.append({
                    'facility_id': facility_id,
                    'lob': lob,
                    'covenant_type': covenant['covenant_type'],
                    'current_value': covenant['current_value'],
                    'covenant_limit': covenant['covenant_limit'],
                    'status': covenant['status'],
                    'reporting_date': facility['reporting_date']
                })
        
        return pd.DataFrame(covenant_data)
    
    def generate_alerts_data(self, facilities_df):
        """Generate alert data for high-risk facilities and covenant violations"""
        alerts_data = []
        
        # Defaulted facilities (rating 17)
        defaulted_facilities = facilities_df[facilities_df['obligor_rating'] == 17]
        for _, facility in defaulted_facilities.iterrows():
            alerts_data.append({
                'facility_id': facility['facility_id'],
                'alert_type': 'Default',
                'severity': 'Critical',
                'message': f"Facility {facility['facility_id']} has defaulted (Rating 17) - SIR: ${facility['sir']:,.2f}",
                'created_date': facility['reporting_date'],
                'status': 'Active',
                'assigned_to': f"Manager {np.random.randint(1, 3)}"
            })
        
        # High risk facilities (rating > 12 but < 17)
        high_risk_facilities = facilities_df[(facilities_df['obligor_rating'] > 12) & (facilities_df['obligor_rating'] < 17)]
        for _, facility in high_risk_facilities.iterrows():
            alerts_data.append({
                'facility_id': facility['facility_id'],
                'alert_type': 'High Risk',
                'severity': 'High',
                'message': f"Facility {facility['facility_id']} has high risk rating of {facility['obligor_rating']}",
                'created_date': facility['reporting_date'],
                'status': 'Active',
                'assigned_to': f"Analyst {np.random.randint(1, 6)}"
            })
        
        # Covenant violations (from covenant data)
        covenant_violations = facilities_df[
            ((facilities_df['lob'] == 'Corporate Banking') & 
             ((facilities_df['fixed_charge_coverage'] < 1.25) | 
              (facilities_df['cash_flow_leverage'] > 4.0) | 
              (facilities_df['liquidity'] < 1.0))) |
            ((facilities_df['lob'] == 'CRE') & 
             ((facilities_df['dscr'] < 1.25) | 
              (facilities_df['ltv'] > 65.0)))
        ]
        
        for _, facility in covenant_violations.iterrows():
            alerts_data.append({
                'facility_id': facility['facility_id'],
                'alert_type': 'Covenant Violation',
                'severity': 'Critical',
                'message': f"Facility {facility['facility_id']} has covenant violation(s)",
                'created_date': facility['reporting_date'],
                'status': 'Active',
                'assigned_to': f"Manager {np.random.randint(1, 3)}"
            })
        
        return pd.DataFrame(alerts_data)

def create_sample_data():
    """Create and save enhanced sample data for the dashboard"""
    generator = RiskDataGenerator()
    
    # Generate facility data
    corporate_facilities = generator.generate_corporate_obligors(100)
    cre_facilities = generator.generate_cre_obligors(100)
    
    # Combine all facilities
    all_facilities = pd.concat([corporate_facilities, cre_facilities], ignore_index=True)
    
    # Generate additional data
    covenant_data = generator.generate_covenant_data(all_facilities)
    alerts_data = generator.generate_alerts_data(all_facilities)
    
    # Create data directory if it doesn't exist
    import os
    os.makedirs('data', exist_ok=True)
    
    # Save all data files
    all_facilities.to_csv('data/facilities.csv', index=False)
    covenant_data.to_csv('data/covenants.csv', index=False)
    alerts_data.to_csv('data/alerts.csv', index=False)
    
    print("Enhanced sample data generated successfully!")
    print(f"Generated {len(all_facilities)} facility records across time series")
    print(f"Created {len(covenant_data)} covenant records")
    print(f"Generated {len(alerts_data)} alerts")
    
    # Print data summary
    print(f"\nData Summary:")
    print(f"  Unique facilities: {all_facilities['facility_id'].nunique()}")
    print(f"  Unique obligors: {all_facilities['obligor_name'].nunique()}")
    print(f"  Time periods: {all_facilities['reporting_date'].nunique()}")
    print(f"  Corporate Banking records: {len(all_facilities[all_facilities['lob'] == 'Corporate Banking'])}")
    print(f"  CRE records: {len(all_facilities[all_facilities['lob'] == 'CRE'])}")
    
    # Rating distribution summary
    rating_dist = all_facilities['obligor_rating'].value_counts().sort_index()
    print(f"\nRating Distribution (1-17):")
    for rating in range(1, 18):
        count = rating_dist.get(rating, 0)
        print(f"  Rating {rating:2d}: {count:4d} records ({count/len(all_facilities)*100:5.1f}%)")
    
    # Defaulted loans summary
    defaulted_loans = all_facilities[all_facilities['obligor_rating'] == 17]
    if len(defaulted_loans) > 0:
        print(f"\nDefaulted Loans (Rating 17):")
        print(f"  Count: {len(defaulted_loans)} records")
        print(f"  Total SIR: ${defaulted_loans['sir'].sum():,.2f}")
        print(f"  Average SIR: ${defaulted_loans['sir'].mean():,.2f}")
    
    # Current quarter summary
    current_quarter = generator.get_current_quarter_end().strftime('%Y-%m-%d')
    print(f"\nData covers periods up to current quarter end: {current_quarter}")

if __name__ == "__main__":
    create_sample_data() 