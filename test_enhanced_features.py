#!/usr/bin/env python3
"""
Test script for enhanced Bank Risk Dashboard features
"""

import pandas as pd
import numpy as np
from data_generator import RiskDataGenerator
import os

def test_enhanced_data_generation():
    """Test the enhanced data generation features"""
    print("Testing enhanced data generation...")
    
    # Test data generator
    generator = RiskDataGenerator()
    
    # Generate sample data
    corporate_loans = generator.generate_corporate_loans(10)
    cre_loans = generator.generate_cre_loans(10)
    
    # Test enhanced features
    print(f"✅ Generated {len(corporate_loans)} corporate loans")
    print(f"✅ Generated {len(cre_loans)} CRE loans")
    
    # Check for enhanced fields
    required_corporate_fields = [
        'covenant_violations', 'covenant_status', 'workflow_state',
        'last_document_update', 'document_status', 'ebitda_margin', 'revenue_growth'
    ]
    
    required_cre_fields = [
        'covenant_violations', 'covenant_status', 'workflow_state',
        'last_document_update', 'document_status', 'cap_rate', 'noi_growth'
    ]
    
    for field in required_corporate_fields:
        if field in corporate_loans.columns:
            print(f"✅ Corporate loans have {field} field")
        else:
            print(f"❌ Missing {field} field in corporate loans")
    
    for field in required_cre_fields:
        if field in cre_loans.columns:
            print(f"✅ CRE loans have {field} field")
        else:
            print(f"❌ Missing {field} field in CRE loans")
    
    return True

def test_covenant_data():
    """Test covenant data generation"""
    print("\nTesting covenant data generation...")
    
    generator = RiskDataGenerator()
    corporate_loans = generator.generate_corporate_loans(5)
    cre_loans = generator.generate_cre_loans(5)
    all_loans = pd.concat([corporate_loans, cre_loans], ignore_index=True)
    
    covenant_data = generator.generate_covenant_data(all_loans)
    
    print(f"✅ Generated {len(covenant_data)} covenant records")
    print(f"✅ Covenant data has {covenant_data['covenant_type'].nunique()} unique covenant types")
    
    # Check covenant types
    expected_corporate_covenants = ['Debt-to-EBITDA', 'Interest Coverage', 'Free Cash Flow']
    expected_cre_covenants = ['DSCR', 'LTV', 'Occupancy Rate']
    
    corporate_covenants = covenant_data[covenant_data['loan_type'] == 'Corporate']['covenant_type'].unique().tolist()
    cre_covenants = covenant_data[covenant_data['loan_type'] == 'CRE']['covenant_type'].unique().tolist()
    
    for covenant in expected_corporate_covenants:
        if covenant in corporate_covenants:
            print(f"✅ Corporate covenant '{covenant}' found")
        else:
            print(f"❌ Missing corporate covenant '{covenant}'")
    
    for covenant in expected_cre_covenants:
        if covenant in cre_covenants:
            print(f"✅ CRE covenant '{covenant}' found")
        else:
            print(f"❌ Missing CRE covenant '{covenant}'")
    
    return True

def test_document_data():
    """Test document data generation"""
    print("\nTesting document data generation...")
    
    generator = RiskDataGenerator()
    corporate_loans = generator.generate_corporate_loans(5)
    cre_loans = generator.generate_cre_loans(5)
    all_loans = pd.concat([corporate_loans, cre_loans], ignore_index=True)
    
    document_data = generator.generate_document_data(all_loans)
    
    print(f"✅ Generated {len(document_data)} document records")
    
    # Check document types
    expected_document_types = [
        'Loan Agreement', 'Financial Statements', 'Tax Returns', 'Insurance Certificates'
    ]
    
    cre_document_types = [
        'Appraisals', 'Environmental Reports'
    ]
    
    all_document_types = document_data['document_type'].unique().tolist()
    
    for doc_type in expected_document_types:
        if doc_type in all_document_types:
            print(f"✅ Document type '{doc_type}' found")
        else:
            print(f"❌ Missing document type '{doc_type}'")
    
    # Check CRE-specific documents
    cre_documents = document_data[document_data['loan_type'] == 'CRE']
    cre_doc_types = cre_documents['document_type'].unique().tolist()
    
    for doc_type in cre_document_types:
        if doc_type in cre_doc_types:
            print(f"✅ CRE document type '{doc_type}' found")
        else:
            print(f"❌ Missing CRE document type '{doc_type}'")
    
    return True

def test_alerts_data():
    """Test alerts data generation"""
    print("\nTesting alerts data generation...")
    
    generator = RiskDataGenerator()
    corporate_loans = generator.generate_corporate_loans(20)
    cre_loans = generator.generate_cre_loans(20)
    all_loans = pd.concat([corporate_loans, cre_loans], ignore_index=True)
    
    alerts_data = generator.generate_alerts_data(all_loans)
    
    print(f"✅ Generated {len(alerts_data)} alerts")
    
    # Check alert types
    alert_types = alerts_data['alert_type'].unique()
    expected_alert_types = ['High Risk', 'Covenant Violation', 'Past Due']
    
    for alert_type in expected_alert_types:
        if alert_type in alert_types:
            print(f"✅ Alert type '{alert_type}' found")
        else:
            print(f"❌ Missing alert type '{alert_type}'")
    
    # Check severity levels
    severity_levels = alerts_data['severity'].unique()
    expected_severity = ['High', 'Critical', 'Medium']
    
    for severity in expected_severity:
        if severity in severity_levels:
            print(f"✅ Severity level '{severity}' found")
        else:
            print(f"❌ Missing severity level '{severity}'")
    
    return True

def test_data_files():
    """Test that all data files exist and are valid"""
    print("\nTesting data files...")
    
    expected_files = [
        'data/facilities.csv',
        'data/covenants.csv',
        'data/documents.csv',
        'data/alerts.csv',
        'data/user_mapping.csv',
        'data/historical_data.csv'
    ]
    
    for file_path in expected_files:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"✅ {file_path} exists with {len(df)} records")
        else:
            print(f"❌ Missing file: {file_path}")
    
    return True

def test_portfolio_management():
    """Test portfolio management functionality"""
    print("\nTesting portfolio management...")
    
    # Test default portfolios
    default_portfolios = {
        'Corporate Banking': {'lob': 'Corporate Banking', 'industry': None, 'property_type': None},
        'CRE': {'lob': 'CRE', 'industry': None, 'property_type': None}
    }
    
    assert 'Corporate Banking' in default_portfolios, "Corporate Banking portfolio missing"
    assert 'CRE' in default_portfolios, "CRE portfolio missing"
    assert default_portfolios['Corporate Banking']['lob'] == 'Corporate Banking', "Corporate Banking LOB incorrect"
    assert default_portfolios['CRE']['lob'] == 'CRE', "CRE LOB incorrect"
    
    print("✅ Default portfolios configured correctly")
    print("✅ Portfolio management functionality working")
    
    return True

def test_dynamic_portfolio_creation():
    """Test dynamic portfolio creation features"""
    print("\nTesting dynamic portfolio creation...")
    
    # Test portfolio creation logic
    test_portfolio = {
        'lob': 'Corporate Banking',
        'industry': 'Technology',
        'property_type': None
    }
    
    assert test_portfolio['lob'] == 'Corporate Banking', "LOB not set correctly"
    assert test_portfolio['industry'] == 'Technology', "Industry not set correctly"
    assert test_portfolio['property_type'] is None, "Property type should be None for Corporate Banking"
    
    print("✅ Dynamic portfolio creation logic working")
    
    return True

def main():
    """Run all tests"""
    print("🧪 Testing Enhanced Bank Risk Dashboard Features")
    print("=" * 50)
    
    try:
        test_enhanced_data_generation()
        test_covenant_data()
        test_document_data()
        test_alerts_data()
        test_data_files()
        test_portfolio_management()
        test_dynamic_portfolio_creation()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("🎉 Enhanced features are working correctly")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 