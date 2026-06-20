import psycopg2
import sys

ports = [5432, 5433, 5434]
passwords = ["postgres", "admin", "root", "1234", "password", "123456", "123", "", "12345", "admin123"]

for port in ports:
    for p in passwords:
        try:
            conn = psycopg2.connect(
                host="localhost",
                user="postgres",
                password=p,
                port=port,
                connect_timeout=2
            )
            print(f"SUCCESS: port={port}, password='{p}'")
            conn.close()
            sys.exit(0)
        except Exception as e:
            err_msg = str(e).strip().split('\n')[0]
            print(f"FAILED: port={port}, password='{p}' -> {err_msg}")
