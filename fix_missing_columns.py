"""
This script adds the missing columns to the asset table.
Run it to fix the SQLite database error.
"""
import sqlite3
import os

def add_missing_columns(db_path):
    print(f"Checking database: {db_path}")
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found!")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if the asset table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asset'")
    if not cursor.fetchone():
        print(f"No 'asset' table found in {db_path}")
        conn.close()
        return False
    
    # Check if the column exists
    cursor.execute("PRAGMA table_info(asset)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add missing columns if they don't exist
    if 'has_market_price' not in columns:
        print(f"Adding 'has_market_price' column to {db_path}...")
        cursor.execute("ALTER TABLE asset ADD COLUMN has_market_price BOOLEAN DEFAULT 1")
    
    if 'issuer' not in columns:
        print(f"Adding 'issuer' column to {db_path}...")
        cursor.execute("ALTER TABLE asset ADD COLUMN issuer VARCHAR(100)")
    
    if 'maturity_date' not in columns:
        print(f"Adding 'maturity_date' column to {db_path}...")
        cursor.execute("ALTER TABLE asset ADD COLUMN maturity_date DATE")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Database {db_path} updated successfully!")
    return True

if __name__ == "__main__":
    # Try both database files
    success = False
    
    for db_file in ['instance/financeiro.db', 'instance/investments.db']:
        if add_missing_columns(db_file):
            success = True
    
    if success:
        print("Database update completed. You can now run the application.")
    else:
        print("Failed to update any database. Please check the database configuration.")