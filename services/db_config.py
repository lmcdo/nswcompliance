#!/usr/bin/env python3
"""
Database Configuration Module
Provides direct database connection for the compliance engine
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_connection():
    """
    Get a direct database connection to PostgreSQL

    Returns:
        psycopg2 connection object
    """
    # Direct connection to existing PostgreSQL database
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', '127.0.0.1'),
        database=os.environ.get('DB_NAME', 'nsw_planning'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),  # Add password if needed
        port=int(os.environ.get('DB_PORT', 5432))
    )

def get_dict_connection():
    """
    Get a database connection that returns dictionaries

    Returns:
        psycopg2 connection with RealDictCursor
    """
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', '127.0.0.1'),
        database=os.environ.get('DB_NAME', 'nsw_planning'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        port=int(os.environ.get('DB_PORT', 5432)),
        cursor_factory=RealDictCursor
    )

# For backward compatibility with old code expecting SafeConnection
class SafeConnection:
    """Compatibility wrapper that just uses direct connection"""
    def __init__(self, **kwargs):
        self.connection = get_connection()

    def cursor(self):
        return self.connection.cursor()

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        return self.connection.rollback()

    def close(self):
        return self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

__all__ = ['get_connection', 'get_dict_connection', 'SafeConnection']