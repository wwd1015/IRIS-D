"""Unit tests for src/dashboard/data/models.py"""

import pytest
from pydantic import ValidationError

from src.dashboard.data.models import FacilityRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_record(**overrides) -> dict:
    base = {
        "facility_id": "F001",
        "obligor_name": "Test Corp",
        "obligor_rating": 5,
        "balance": 1_000_000.0,
        "origination_date": "2020-01-01",
        "maturity_date": "2026-01-01",
        "reporting_date": "2024-01-01",
        "lob": "Corporate Banking",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestFacilityRecordValidation:
    def test_valid_corporate_banking_record(self):
        record = FacilityRecord(**_base_record())
        assert record.facility_id == "F001"
        assert record.lob == "Corporate Banking"

    def test_valid_cre_record(self):
        record = FacilityRecord(**_base_record(lob="CRE", cre_property_type="Office"))
        assert record.lob == "CRE"
        assert record.cre_property_type == "Office"

    def test_rating_too_low_raises(self):
        with pytest.raises(ValidationError):
            FacilityRecord(**_base_record(obligor_rating=0))

    def test_rating_too_high_raises(self):
        with pytest.raises(ValidationError):
            FacilityRecord(**_base_record(obligor_rating=18))

    def test_negative_balance_raises(self):
        with pytest.raises(ValidationError):
            FacilityRecord(**_base_record(balance=-1.0))

    def test_invalid_lob_raises(self):
        with pytest.raises(ValidationError):
            FacilityRecord(**_base_record(lob="Unknown LOB"))

    def test_optional_fields_default_none(self):
        record = FacilityRecord(**_base_record())
        assert record.industry is None
        assert record.cre_property_type is None
        assert record.noi is None


# ---------------------------------------------------------------------------
# Computed field tests
# ---------------------------------------------------------------------------

class TestFacilityRecordComputedFields:
    def test_balance_millions(self):
        record = FacilityRecord(**_base_record(balance=2_500_000.0))
        assert record.balance_millions == pytest.approx(2.5)

    def test_risk_category_pass_rated(self):
        record = FacilityRecord(**_base_record(obligor_rating=10))
        assert record.risk_category == "Pass Rated"

    def test_risk_category_watch(self):
        record = FacilityRecord(**_base_record(obligor_rating=14))
        assert record.risk_category == "Watch"

    def test_risk_category_criticized(self):
        record = FacilityRecord(**_base_record(obligor_rating=15))
        assert record.risk_category == "Criticized"

    def test_risk_category_defaulted(self):
        record = FacilityRecord(**_base_record(obligor_rating=17))
        assert record.risk_category == "Defaulted"
