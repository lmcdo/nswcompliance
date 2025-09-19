#!/usr/bin/env python3
import psycopg2

# Try different authentication methods to reset the postgres password
auth_methods = [
    {'user': 'lawre', 'password': None},  # Windows user
    {'user': 'postgres', 'password': ''},  # Empty password
    {'user': 'postgres', 'password': None},  # No password specified
]

for method in auth_methods:
    try:
        kwargs = {
            'host': 'localhost',
            'port': 5433,
            'database': 'postgres',
            'user': method['user']
        }
        if method['password'] is not None:
            kwargs['password'] = method['password']

        conn = psycopg2.connect(**kwargs)
        print(f"SUCCESS: Connected with user '{method['user']}'")

        cursor = conn.cursor()
        cursor.execute("ALTER USER postgres PASSWORD 'postgres';")
        conn.commit()
        print("Password for postgres user set to 'postgres'")
        conn.close()

        # Test the new password
        test_conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='postgres',
            user='postgres',
            password='postgres'
        )
        print("SUCCESS: Password 'postgres' now works!")
        test_conn.close()
        break

    except Exception as e:
        print(f"Failed with user '{method['user']}': {e}")
        continue
else:
    print("All authentication methods failed")