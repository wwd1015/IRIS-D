"""
Pydantic models for bank risk data validation and transformation
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, computed_field
import pandas as pd


class FacilityRecord(BaseModel):
    """Pydantic model for individual facility records with validation and transformations"""
    
    # Core facility information
    facility_id: str = Field(..., description="Unique facility identifier")
    obligor_name: str = Field(..., description="Name of the obligor")
    obligor_rating: int = Field(..., ge=1, le=17, description="Obligor rating (1-17)")
    balance: float = Field(..., ge=0, description="Facility balance")
    origination_date: str = Field(..., description="Loan origination date")
    maturity_date: str = Field(..., description="Loan maturity date")
    reporting_date: str = Field(..., description="Data reporting date")
    lob: str = Field(..., description="Line of business")
    
    # Corporate Banking metrics (optional)
    industry: Optional[str] = Field(None, description="Industry classification")
    free_cash_flow: Optional[float] = Field(None, description="Free cash flow")
    fixed_charge_coverage: Optional[float] = Field(None, description="Fixed charge coverage ratio")
    cash_flow_leverage: Optional[float] = Field(None, description="Cash flow leverage ratio")
    liquidity: Optional[float] = Field(None, description="Liquidity ratio")
    profitability: Optional[float] = Field(None, description="Profitability ratio")
    growth: Optional[float] = Field(None, description="Growth rate")
    
    # CRE metrics (optional)
    cre_property_type: Optional[str] = Field(None, description="CRE property type")
    msa: Optional[str] = Field(None, description="Metropolitan Statistical Area")
    noi: Optional[float] = Field(None, description="Net Operating Income")
    property_value: Optional[float] = Field(None, description="Property value")
    dscr: Optional[float] = Field(None, description="Debt Service Coverage Ratio")
    ltv: Optional[float] = Field(None, description="Loan to Value ratio")
    
    # Risk metrics
    sir: Optional[float] = Field(None, description="Special Interest Rate")
    
    class Config:
        str_strip_whitespace = True
        validate_assignment = True

    @field_validator('lob')
    @classmethod
    def validate_lob(cls, v):
        """Validate line of business"""
        allowed_lobs = ['Corporate Banking', 'CRE']
        if v not in allowed_lobs:
            raise ValueError(f'LOB must be one of {allowed_lobs}')
        return v

    @field_validator('origination_date', 'maturity_date', 'reporting_date')
    @classmethod
    def validate_dates(cls, v):
        """Validate date formats"""
        if not v:
            raise ValueError('Date cannot be empty')
        
        # Try to parse the date to ensure it's valid
        try:
            pd.to_datetime(v)
        except Exception:
            raise ValueError(f'Invalid date format: {v}')
        return v

    @computed_field
    @property
    def balance_millions(self) -> float:
        """Computed field: balance in millions"""
        return self.balance / 1_000_000

    @computed_field
    @property
    def risk_category(self) -> str:
        """Computed field: risk category based on obligor rating (1-17)"""
        if self.obligor_rating <= 13:
            return "Pass Rated"
        elif self.obligor_rating == 14:
            return "Watch"
        elif self.obligor_rating <= 16:
            return "Criticized"
        elif self.obligor_rating == 17:
            return "Defaulted"
        else:
            # Should not happen with validation, but safety net
            return "Defaulted"

    @computed_field
    @property
    def quarters_since_origination(self) -> Optional[int]:
        """Computed field: quarters since origination"""
        try:
            orig_date = pd.to_datetime(self.origination_date)
            report_date = pd.to_datetime(self.reporting_date)
            
            # Calculate quarters between dates
            orig_quarter = orig_date.to_period('Q')
            report_quarter = report_date.to_period('Q')
            
            return report_quarter - orig_quarter
        except Exception:
            return None


class FacilityDataset(BaseModel):
    """Model for the entire dataset with validation and transformation capabilities"""
    
    facilities: List[FacilityRecord] = Field(..., description="List of facility records")
    
    @field_validator('facilities')
    @classmethod
    def validate_non_empty(cls, v):
        """Ensure dataset is not empty"""
        if not v:
            raise ValueError('Dataset cannot be empty')
        return v

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame with all computed fields"""
        records = []
        for facility in self.facilities:
            # Get all fields including computed ones
            record = facility.model_dump()
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Ensure proper data types
        df['reporting_date'] = pd.to_datetime(df['reporting_date'])
        df['origination_date'] = pd.to_datetime(df['origination_date'])
        df['maturity_date'] = pd.to_datetime(df['maturity_date'])
        
        return df

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'FacilityDataset':
        """Create from pandas DataFrame with validation"""
        records = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Convert row to dict, handling NaN values
                row_dict = row.to_dict()
                
                # Convert pandas NaN to None for Pydantic
                for key, value in row_dict.items():
                    if pd.isna(value):
                        row_dict[key] = None
                
                facility = FacilityRecord(**row_dict)
                records.append(facility)
                
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
        
        if errors:
            # Log first few errors for debugging
            for error in errors[:5]:  # Show first 5 errors
                print(f"Validation error: {error}")
            
            if len(errors) > 5:
                print(f"... and {len(errors) - 5} more validation errors")
            
            # For now, continue with valid records
            print(f"Continuing with {len(records)} valid records out of {len(df)} total records")
        
        if not records:
            raise ValueError("No valid records found after validation")
        
        return cls(facilities=records)

    def get_summary_stats(self) -> dict:
        """Get summary statistics for the dataset"""
        df = self.to_dataframe()
        
        return {
            'total_facilities': len(df),
            'total_balance': df['balance'].sum(),
            'total_balance_millions': df['balance_millions'].sum(),
            'unique_obligors': df['obligor_name'].nunique(),
            'lob_distribution': df['lob'].value_counts().to_dict(),
            'risk_category_distribution': df['risk_category'].value_counts().to_dict(),
            'date_range': {
                'earliest_reporting_date': df['reporting_date'].min().isoformat(),
                'latest_reporting_date': df['reporting_date'].max().isoformat()
            }
        }