import sqlite3

conn = sqlite3.connect('cex_ledger.db')
try:
    conn.execute("ALTER TABLE user ADD COLUMN pin TEXT;")
    print("Column 'pin' added to 'user' table.")
except Exception as e:
    print(f"Migration error or column already exists: {e}")
finally:
    conn.close()
