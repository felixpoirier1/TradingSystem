import sqlite3

conn = sqlite3.connect("data/data.db")

# check if pairs trading table exists and return boolean
def check_pairs_trading_table_exists():
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs_trading'")
    return bool(c.fetchone())

print(check_pairs_trading_table_exists())