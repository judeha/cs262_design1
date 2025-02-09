import sqlite3

# Connect to an SQLite database (or create it if it doesn't exist)
def database_setup():
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()

    # Create table
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                   id INTEGER PRIMARY KEY,
                   username TEXT NOT NULL,
                   password TEXT NOT NULL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                   id INTEGER PRIMARY KEY,
                   sender TEXT NOT NULL,
                   receiver TEXT NOT NULL,
                   content TEXT,
                   timestamp INTEGER,
                   delivered INTEGER)''')

    # Save (commit) the changes
    conn.commit()
    conn.close()
