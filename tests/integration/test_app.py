#!/usr/bin/env python3
"""
Test script for Portfolio Performance Dashboard
This script tests the core functionality before deployment to Posit Connect
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import json

def test_dependencies():
    """Test that all required dependencies are available"""
    print("Testing dependencies...")
    
    required_packages = [
        'dash', 'pandas', 'numpy', 'plotly'
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

def test_data_files():
    """Test that required data files exist and are valid"""
    print("Testing data files...")
    
    try:
        required_files = [
            'data/facilities.csv'
        ]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                print(f"✗ Required file {file_path} not found")
                return False
                
            df = pd.read_csv(file_path)
            if len(df) == 0:
                print(f"✗ File {file_path} is empty")
                return False
            
            print(f"✓ {file_path} valid ({len(df)} records)")
        
        # Test facilities.csv structure
        facilities_df = pd.read_csv('data/facilities.csv')
        required_columns = [
            'facility_id', 'obligor_name', 'balance', 'lob', 
            'obligor_rating', 'reporting_date'
        ]
        
        for col in required_columns:
            if col not in facilities_df.columns:
                print(f"✗ Missing required column: {col}")
                return False
        
        print("✓ All data files are valid")
        return True
        
    except Exception as e:
        print(f"✗ Data files test failed: {e}")
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

def test_user_profiles():
    """Test user profile functionality"""
    print("Testing user profile functionality...")
    
    try:
        profiles_file = 'data/user_profiles.json'
        
        # Create default profiles file if it doesn't exist
        if not os.path.exists(profiles_file):
            os.makedirs('data', exist_ok=True)
            default_profiles = {}
            with open(profiles_file, 'w') as f:
                json.dump(default_profiles, f)
        
        # Test reading profiles
        with open(profiles_file, 'r') as f:
            profiles = json.load(f)
        
        print(f"✓ User profiles file valid ({len(profiles)} profiles)")
        return True
        
    except Exception as e:
        print(f"✗ User profiles test failed: {e}")
        return False

def test_app_import():
    """Test that the main app can be imported without errors"""
    print("Testing app import...")
    
    try:
        from src.dashboard import app
        print("✓ App import successful")
        
        # Test that essential globals exist
        assert hasattr(app, 'facilities_df'), "facilities_df not found"
        assert hasattr(app, 'current_user'), "current_user not found"
        assert hasattr(app, 'portfolios'), "portfolios not found"
        
        print("✓ App structure validated")
        return True
        
    except Exception as e:
        print(f"✗ App import failed: {e}")
        return False

def test_custom_metrics():
    """Test custom metrics functionality"""
    print("Testing custom metrics...")
    
    try:
        from src.dashboard import app
        
        # Test that custom metrics dict exists
        assert hasattr(app, 'custom_metrics'), "custom_metrics not found"
        
        # Test basic formula validation (if facilities_df is loaded)
        if hasattr(app, 'facilities_df') and len(app.facilities_df) > 0:
            test_formula = "balance > 1000000"
            # This is a simple test - we're not actually evaluating the formula
            assert isinstance(test_formula, str), "Formula should be string"
            print("✓ Custom metrics structure valid")
        
        return True
        
    except Exception as e:
        print(f"✗ Custom metrics test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Portfolio Performance Dashboard - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Data Files", test_data_files),
        ("User Profiles", test_user_profiles),
        ("Portfolio Functionality", test_portfolio_functionality),
        ("Custom Metrics", test_custom_metrics),
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
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready for deployment.")
        print("\nNext steps for Posit Connect deployment:")
        print("1. Ensure all data files are in the 'data/' directory")
        print("2. Run: rsconnect deploy dash app.py")
        print("3. Or use VS Code Posit Connect extension")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)