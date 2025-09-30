#!/usr/bin/env python3
"""
Test script to validate the startup registration and company information endpoints
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_startup_registration():
    """Test startup user registration"""
    print("1. Testing Startup Registration...")
    
    registration_data = {
        "email": "test@startup.com",
        "first_name": "Test",
        "last_name": "Startup",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
        "terms": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/startup/register/", json=registration_data)
        print(f"Registration Status: {response.status_code}")
        print(f"Registration Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Registration Error: {e}")
        return False

def test_login():
    """Test user login and get JWT token"""
    print("\n2. Testing Login...")
    
    login_data = {
        "email": "test@startup.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login/", json=login_data)
        print(f"Login Status: {response.status_code}")
        login_response = response.json()
        print(f"Login Response: {login_response}")
        
        if response.status_code == 200:
            return login_response.get('token')
        return None
    except Exception as e:
        print(f"Login Error: {e}")
        return None

def test_add_startup(token):
    """Test adding startup company information"""
    print("\n3. Testing Add Startup...")
    
    company_data = {
        "company_name": "Test Tech Solutions",
        "industry": "Technology",
        "company_description": "A test technology company focused on innovative solutions",
        "data_source_confidence": "High",
        "revenue": 1000000.00,
        "net_income": 150000.00,
        "total_assets": 500000.00,
        "total_liabilities": 200000.00,
        "shareholder_equity": 300000.00,
        "cash_flow": 100000.00,
        "funding_ask": 500000.00,
        "team_strength": "Strong technical team with 10+ years experience",
        "market_position": "Growing market share in B2B solutions",
        "brand_reputation": "Well-known in the local tech community",
        "confidence_percentage": 85
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/startup/add/", json=company_data, headers=headers)
        print(f"Add Startup Status: {response.status_code}")
        print(f"Add Startup Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Add Startup Error: {e}")
        return False

def main():
    print("🚀 Testing Fundora API Endpoints\n")
    
    # Test registration (might fail if user already exists)
    registration_success = test_startup_registration()
    
    # Test login
    token = test_login()
    if not token:
        print("❌ Login failed - cannot proceed with further tests")
        return
    
    print(f"✅ JWT Token obtained: {token[:50]}...")
    
    # Test add startup
    add_startup_success = test_add_startup(token)
    
    print(f"\n📊 Test Results:")
    print(f"Registration: {'✅' if registration_success else '⚠️  (might already exist)'}")
    print(f"Login: {'✅' if token else '❌'}")
    print(f"Add Startup: {'✅' if add_startup_success else '❌'}")
    
    if token and add_startup_success:
        print(f"\n🎉 All tests passed! Your HTML form should work with token: {token}")
        print(f"💡 Copy this token to localStorage.setItem('authToken', '{token}') in your browser console")

if __name__ == "__main__":
    main()