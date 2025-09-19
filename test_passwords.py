#!/usr/bin/env python3
import psycopg2

passwords = ['postgres', 'admin', 'password', '123456', 'root', 'test', 'lawre', '', 'P@ssw0rd', 'postgresql']

for pwd in passwords:
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='postgres',
            user='postgres',
            password=pwd
        )
        print(f'SUCCESS: Password "{pwd}" works!')
        cursor = conn.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()[0]
        print(f'PostgreSQL version: {version[:50]}...')
        conn.close()
        break
    except Exception as e:
        print(f'Failed with password "{pwd}": {str(e)[:80]}...')