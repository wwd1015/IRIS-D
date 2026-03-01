"""
Pydantic models for bank risk data validation and transformation
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, computed_field
import pandas as pd
import polars as pl

logger = logging.getLogger(__name__)


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
        try:
            datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        except (ValueError, TypeError):
            # Fallback: try pandas for more flexible parsing
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
            return "Defaulted"

    @computed_field
    @property
    def quarters_since_origination(self) -> Optional[int]:
        """Computed field: quarters since origination"""
        try:
            orig_date = pd.to_datetime(self.origination_date)
            report_date = pd.to_datetime(self.reporting_date)
            orig_quarter = orig_date.year * 4 + (orig_date.month - 1) // 3
            report_quarter = report_date.year * 4 + (report_date.month - 1) // 3
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

    def to_dataframe(self) -> pl.DataFrame:
        """Convert to polars DataFrame with all computed fields"""
        records = [facility.model_dump() for facility in self.facilities]
        pdf = pd.DataFrame(records)

        # Ensure proper data types
        pdf['reporting_date'] = pd.to_datetime(pdf['reporting_date'])
        pdf['origination_date'] = pd.to_datetime(pdf['origination_date'])
        pdf['maturity_date'] = pd.to_datetime(pdf['maturity_date'])

        return pl.from_pandas(pdf)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame | pl.DataFrame) -> 'FacilityDataset':
        """Create from pandas or polars DataFrame with validation"""
        # Convert polars to list of dicts
        if isinstance(df, pl.DataFrame):
            rows = df.to_dicts()
        else:
            rows = df.to_dict('records')

        records = []
        errors = []

        for idx, row_dict in enumerate(rows):
            try:
                # Convert NaN/None values
                for key, value in row_dict.items():
                    if isinstance(value, float) and pd.isna(value):
                        row_dict[key] = None
                    elif value is None:
                        pass  # already None

                facility = FacilityRecord(**row_dict)
                records.append(facility)

            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        if errors:
            for error in errors[:5]:
                logger.warning("Validation error: %s", error)
            if len(errors) > 5:
                logger.warning("... and %d more validation errors", len(errors) - 5)
            logger.info("Continuing with %d valid records out of %d total records", len(records), len(rows))

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
            'unique_obligors': df['obligor_name'].n_unique(),
            'lob_distribution': df['lob'].value_counts().to_dict(),
            'risk_category_distribution': df['risk_category'].value_counts().to_dict(),
            'date_range': {
                'earliest_reporting_date': str(df['reporting_date'].min()),
                'latest_reporting_date': str(df['reporting_date'].max()),
            }
        }
