#!/usr/bin/env python3
"""
Database Configuration Module
Provides unified database connection using the safety wrapper
"""

import sys
import os

# Add parent directory to path to import db_safety_wrapper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_safety_wrapper import get_safe_connection

def get_connection():
    """
    Get a safe database connection using the mandatory safety wrapper

    Returns:
        SafeConnection: A safe database connection with automatic timeouts and safety checks
    """
    return get_safe_connection()

# For backward compatibility, also provide the connection class
from db_safety_wrapper import SafeConnection

__all__ = ['get_connection', 'SafeConnection']