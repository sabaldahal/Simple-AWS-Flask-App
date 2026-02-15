
import sqlite3

conn = sqlite3.connect('mydatabase.db')
cur = conn.cursor()



cur.execute("""
    INSERT INTO users (username, password, email, first_name, last_name, address, is_admin)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ("admin", "admin", "admin@example.com", "admin", "admin", "N/A", 1))

conn.commit()
conn.close()