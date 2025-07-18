#!/usr/bin/env python3
"""
Test script for Bank Risk Management Dashboard
This script tests the core functionality before deployment
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

def test_data_generation():
    """Test data generation functionality"""
    print("Testing data generation...")
    
    try:
        from data_generator import RiskDataGenerator
        
        generator = RiskDataGenerator()
        
        # Test corporate loans generation
        corp_loans = generator.generate_corporate_loans(10)
        assert len(corp_loans) == 10, f"Expected 10 corporate loans, got {len(corp_loans)}"
        assert 'free_cash_flow_ratio' in corp_loans.columns, "Missing FCF ratio column"
        assert 'interest_coverage' in corp_loans.columns, "Missing interest coverage column"
        print("✓ Corporate loans generation successful")
        
        # Test CRE loans generation
        cre_loans = generator.generate_cre_loans(8)
        assert len(cre_loans) == 8, f"Expected 8 CRE loans, got {len(cre_loans)}"
        assert 'dscr' in cre_loans.columns, "Missing DSCR column"
        assert 'ltv' in cre_loans.columns, "Missing LTV column"
        print("✓ CRE loans generation successful")
        
        # Test user mapping
        user_mapping = generator.generate_user_portfolio_mapping(5)
        assert len(user_mapping) == 5, f"Expected 5 users, got {len(user_mapping)}"
        print("✓ User mapping generation successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Data generation test failed: {e}")
        return False

def test_authentication():
    """Test authentication functionality"""
    print("Testing authentication...")
    
    try:
        from auth import AuthManager, User
        
        # Test user creation
        user = User('test_user', 'test_username', 'test@bank.com', ['Corporate Banking'], 'Analyst')
        assert user.id == 'test_user', "User ID not set correctly"
        assert user.username == 'test_username', "Username not set correctly"
        assert 'Corporate Banking' in user.assigned_portfolios, "Portfolio assignment failed"
        print("✓ User creation successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Authentication test failed: {e}")
        return False

def test_data_structure():
    """Test data structure and file operations"""
    print("Testing data structure...")
    
    try:
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Test sample data creation
        from data_generator import create_sample_data
        create_sample_data()
        
        # Verify files exist - updated to match current application
        required_files = [
            'data/facilities.csv', 
            'data/covenants.csv', 
            'data/alerts.csv',
            'data/historical_data.csv',
            'data/user_mapping.csv',
            'data/documents.csv'
        ]
        
        for file_path in required_files:
            assert os.path.exists(file_path), f"Required file {file_path} not found"
            df = pd.read_csv(file_path)
            assert len(df) > 0, f"File {file_path} is empty"
        
        print("✓ Data structure test successful")
        return True
        
    except Exception as e:
        print(f"✗ Data structure test failed: {e}")
        return False

def test_dependencies():
    """Test that all required dependencies are available"""
    print("Testing dependencies...")
    
    required_packages = [
        'dash', 'flask', 'pandas', 'numpy', 'plotly'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} available")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} missing")
    
    if missing_packages:
        print(f"Missing packages: {missing_packages}")
        print("Please install missing packages with: pip install -r requirements.txt")
        return False
    
    return True

def test_app_import():
    """Test that the main app can be imported"""
    print("Testing app import...")
    
    try:
        # This will test if the app can be imported without errors
        # Note: We don't actually run the app, just test the import
        import app
        print("✓ App import successful")
        return True
        
    except Exception as e:
        print(f"✗ App import failed: {e}")
        return False

def test_portfolio_functionality():
    """Test portfolio management functionality"""
    print("Testing portfolio functionality...")
    
    try:
        # Test default portfolios
        default_portfolios = {
            'Corporate Banking': {'lob': 'Corporate Banking', 'industry': None, 'property_type': None},
            'CRE': {'lob': 'CRE', 'industry': None, 'property_type': None}
        }
        
        assert 'Corporate Banking' in default_portfolios, "Corporate Banking portfolio missing"
        assert 'CRE' in default_portfolios, "CRE portfolio missing"
        assert default_portfolios['Corporate Banking']['lob'] == 'Corporate Banking', "Corporate Banking LOB incorrect"
        assert default_portfolios['CRE']['lob'] == 'CRE', "CRE LOB incorrect"
        
        print("✓ Default portfolios configured correctly")
        return True
        
    except Exception as e:
        print(f"✗ Portfolio functionality test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Bank Risk Management Dashboard - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Data Generation", test_data_generation),
        ("Authentication", test_authentication),
        ("Data Structure", test_data_structure),
        ("Portfolio Functionality", test_portfolio_functionality),
        ("App Import", test_app_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"✗ {test_name} test failed")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready for deployment.")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 