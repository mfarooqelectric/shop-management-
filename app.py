import streamlit as st
import sqlite3
from datetime import datetime

# ---------------------------------------------------------
# DATABASE SETUP & INITIALIZATION
# ---------------------------------------------------------
DB_FILE = "shop_inventory.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL UNIQUE,
            category TEXT,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL DEFAULT 0.0
        )
    ''')

    # 2. Sales Table
    cursor.execute('''
 …
