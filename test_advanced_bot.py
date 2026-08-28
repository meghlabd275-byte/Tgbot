#!/usr/bin/env python3
"""
Advanced test script for the Telegram Admin Bot
Tests all new features and handlers
"""

import os
import sys
import traceback

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test all imports"""
    print("🧪 Testing Advanced Bot Features")
    print("=" * 50)

    tests_passed = 0
    total_tests = 0

    # Test basic imports
    print("Testing basic imports...")
    try:
        from config import Config

        print("✅ Config imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Config error: {e}")
    total_tests += 1

    try:
        from database import db

        print("✅ Database imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Database error: {e}")
    total_tests += 1

    try:
        import utils

        print("✅ Utils imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Utils error: {e}")
    total_tests += 1

    # Test new handler imports
    print("\nTesting new handler imports...")

    try:
        import handlers.antiflood

        print("✅ Anti-flood handler imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Anti-flood error: {e}")
        traceback.print_exc()
    total_tests += 1

    try:
        import handlers.filters

        print("✅ Filters handler imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Filters error: {e}")
        traceback.print_exc()
    total_tests += 1

    try:
        import handlers.welcome

        print("✅ Welcome handler imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Welcome error: {e}")
        traceback.print_exc()
    total_tests += 1

    try:
        import handlers.notes

        print("✅ Notes handler imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Notes error: {e}")
        traceback.print_exc()
    total_tests += 1

    try:
        import handlers.reports

        print("✅ Reports handler imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Reports error: {e}")
        traceback.print_exc()
    total_tests += 1

    try:
        import handlers.advanced_features

        print("✅ Advanced features handler imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Advanced features error: {e}")
        traceback.print_exc()
    total_tests += 1

    # Test main bot import
    print("\nTesting main bot import...")
    try:
        import bot

        print("✅ Main bot imported")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Main bot error: {e}")
        traceback.print_exc()
    total_tests += 1

    return tests_passed, total_tests


def test_database_tables():
    """Test database table creation"""
    print("\nTesting database table creation...")
    tests_passed = 0
    total_tests = 0

    try:
        from database import db
        from handlers.advanced_features import update_advanced_database
        from handlers.filters import update_database as update_filters_db
        from handlers.notes import update_notes_database
        from handlers.reports import update_reports_database
        from handlers.welcome import update_welcome_database

        # Create all new tables
        update_filters_db()
        update_welcome_database()
        update_notes_database()
        update_reports_database()
        update_advanced_database()

        print("✅ All database tables created successfully")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Database table creation error: {e}")
        traceback.print_exc()
    total_tests += 1

    return tests_passed, total_tests


def test_command_functions():
    """Test that command functions are properly defined"""
    print("\nTesting command function definitions...")
    tests_passed = 0
    total_tests = 0

    # Test anti-flood commands
    try:
        from handlers.antiflood import check_flood, flood_command, setflood_command, setfloodmode_command

        print("✅ Anti-flood commands defined")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Anti-flood commands error: {e}")
    total_tests += 1

    # Test filter commands
    try:
        from handlers.filters import (
            addfilter_command,
            antispam_command,
            check_message_filters,
            filters_command,
            lock_command,
            locks_command,
            removefilter_command,
            unlock_command,
        )

        print("✅ Filter commands defined")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Filter commands error: {e}")
    total_tests += 1

    # Test welcome commands
    try:
        from handlers.welcome import (
            captcha_command,
            cleanservice_command,
            goodbye_command,
            handle_captcha_callback,
            handle_left_member_goodbye,
            handle_new_member_welcome,
            setgoodbye_command,
            setwelcome_command,
            welcome_command,
        )

        print("✅ Welcome commands defined")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Welcome commands error: {e}")
    total_tests += 1

    # Test notes commands
    try:
        from handlers.notes import (
            clear_command,
            clearrules_command,
            get_command,
            handle_note_shortcut,
            notes_command,
            rules_command,
            save_command,
            setrules_command,
        )

        print("✅ Notes commands defined")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Notes commands error: {e}")
    total_tests += 1

    # Test report commands
    try:
        from handlers.reports import handle_report_callback, report_command, reporthistory_command, reports_command

        print("✅ Report commands defined")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Report commands error: {e}")
    total_tests += 1

    # Test advanced feature commands
    try:
        from handlers.advanced_features import (
            addcmd_command,
            backup_command,
            check_night_mode,
            cleanup_command,
            delcmd_command,
            handle_custom_command,
            listcmds_command,
            nightmode_command,
            setlang_command,
            slowmode_command,
        )

        print("✅ Advanced feature commands defined")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Advanced feature commands error: {e}")
    total_tests += 1

    return tests_passed, total_tests


def test_utility_functions():
    """Test utility functions"""
    print("\nTesting utility functions...")
    tests_passed = 0
    total_tests = 0

    try:
        from utils import format_time_duration, parse_time_string

        # Test time parsing
        assert parse_time_string("30s") == 30
        assert parse_time_string("5m") == 300
        assert parse_time_string("2h") == 7200
        assert parse_time_string("1d") == 86400

        # Test time formatting
        assert format_time_duration(30) == "30s"
        assert format_time_duration(300) == "5m"

        print("✅ Utility functions work correctly")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Utility functions error: {e}")
        traceback.print_exc()
    total_tests += 1

    return tests_passed, total_tests


def test_database_operations():
    """Test database operations"""
    print("\nTesting database operations...")
    tests_passed = 0
    total_tests = 0

    try:
        from database import db

        # Test basic database operations
        session = db.get_session()
        from sqlalchemy import text

        session.execute(text("SELECT 1"))
        session.close()

        # Test new database methods
        if hasattr(db, "add_mute"):
            print("✅ Mute methods available")
        else:
            print("❌ Mute methods missing")

        print("✅ Database operations work")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Database operations error: {e}")
        traceback.print_exc()
    total_tests += 1

    return tests_passed, total_tests


def main():
    """Run all tests"""
    total_passed = 0
    total_tests = 0

    # Run all test suites
    passed, tests = test_imports()
    total_passed += passed
    total_tests += tests

    passed, tests = test_database_tables()
    total_passed += passed
    total_tests += tests

    passed, tests = test_command_functions()
    total_passed += passed
    total_tests += tests

    passed, tests = test_utility_functions()
    total_passed += passed
    total_tests += tests

    passed, tests = test_database_operations()
    total_passed += passed
    total_tests += tests

    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("🎉 All tests passed! The advanced bot features are ready.")
        return 0
    else:
        print(f"⚠️  {total_tests - total_passed} tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
