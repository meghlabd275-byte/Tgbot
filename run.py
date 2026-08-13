#!/usr/bin/env python3
"""
Simple runner script for the Telegram Admin Bot
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    from bot import main
    main()