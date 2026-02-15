import csv
import sqlite3

conn = sqlite3.connect('mydatabase.db')
cur = conn.cursor()
cur.execute("""DROP TABLE IF EXISTS users""")
cur.execute("""
            CREATE TABLE users 
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
            address TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
            )""")


cur.execute("""DROP TABLE IF EXISTS limericks""")
cur.execute("""
            CREATE TABLE limericks
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            filename TEXT NOT NULL)
            """)

conn.commit()
conn.close()