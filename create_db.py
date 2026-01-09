import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()
cur.execute("ALTER TABLE users ADD COLUMN name TEXT")
conn.close()


print("Database created successfully")
