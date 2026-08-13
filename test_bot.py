#!/usr/bin/env python3
"""
Test script for Telegram Admin Bot
"""

import sys
import os
import asyncio
from unittest.mock import Mock

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all modules can be imported"""
    try:
        print("Testing imports...")
        
        # Test config
        from config import Config
        print("✅ Config imported")
        
        # Test database
        from database import db
        print("✅ Database imported")
        
        # Test utils
        from utils import get_user_from_message, format_user_mention
        print("✅ Utils imported")
        
        # Test handlers
        from handlers.admin_commands import fileid_command
        from handlers.user_management import ban_command
        from handlers.warning_system import warn_command
        from handlers.whitelist_system import whitelist_command
        from handlers.user_info import user_command
        from handlers.verification import verify_command
        from handlers.help_commands import help_command
        from handlers.events import handle_message
        print("✅ All handlers imported")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database():
    """Test database functionality"""
    try:
        print("\nTesting database...")
        from database import db
        
        # Test basic operations
        chat = db.get_or_create_chat(12345, "Test Chat")
        user = db.get_or_create_user(67890, "testuser", "Test", "User")
        
        # Test admin functions
        db.add_admin(67890, 12345)
        is_admin = db.is_admin(67890, 12345)
        assert is_admin, "Admin check failed"
        
        # Test ban functions
        db.add_ban(67890, 12345, 67890, "Test ban")
        is_banned = db.is_banned(67890, 12345)
        assert is_banned, "Ban check failed"
        
        # Clean up
        db.remove_ban(67890, 12345)
        db.remove_admin(67890, 12345)
        
        print("✅ Database tests passed")
        return True
    except Exception as e:
        print(f"❌ Database test error: {e}")
        return False

def test_utils():
    """Test utility functions"""
    try:
        print("\nTesting utilities...")
        from utils import parse_time_string, format_time_duration
        
        # Test time parsing
        assert parse_time_string("30s") == 30
        assert parse_time_string("5m") == 300
        assert parse_time_string("2h") == 7200
        assert parse_time_string("1d") == 86400
        
        # Test time formatting
        assert format_time_duration(30) == "30s"
        assert format_time_duration(300) == "5m"
        assert format_time_duration(7200) == "2h"
        assert format_time_duration(86400) == "1d"
        
        print("✅ Utility tests passed")
        return True
    except Exception as e:
        print(f"❌ Utility test error: {e}")
        return False

def test_config():
    """Test configuration"""
    try:
        print("\nTesting configuration...")
        from config import Config
        
        # Check if required attributes exist
        assert hasattr(Config, 'BOT_TOKEN')
        assert hasattr(Config, 'BOT_USERNAME')
        assert hasattr(Config, 'DATABASE_URL')
        assert hasattr(Config, 'SUPER_ADMIN_ID')
        assert hasattr(Config, 'MAX_WARNINGS')
        
        print("✅ Configuration tests passed")
        return True
    except Exception as e:
        print(f"❌ Configuration test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Telegram Admin Bot")
    print("=" * 30)
    
    tests = [
        test_imports,
        test_config,
        test_database,
        test_utils
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The bot should work correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)