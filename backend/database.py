import sqlite3
from pathlib import Path
from flask import g
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "bankguard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, display_name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, customer_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, account_type TEXT NOT NULL, typical_amount REAL NOT NULL, typical_time TEXT NOT NULL, typical_channels TEXT NOT NULL, monthly_volume INTEGER NOT NULL, payee_count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), transaction_code TEXT UNIQUE NOT NULL, occurred_at TEXT NOT NULL, description TEXT NOT NULL, payee TEXT NOT NULL, amount REAL NOT NULL, channel TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS investigations (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), score INTEGER NOT NULL, level TEXT NOT NULL, finding TEXT NOT NULL, triggered_rules TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS investigation_transactions (investigation_id INTEGER NOT NULL, transaction_id INTEGER NOT NULL, rule_name TEXT NOT NULL, PRIMARY KEY (investigation_id, transaction_id, rule_name));
CREATE TABLE IF NOT EXISTS investigator_decisions (id INTEGER PRIMARY KEY, investigation_id INTEGER NOT NULL, user_id INTEGER NOT NULL, decision TEXT NOT NULL, created_at TEXT NOT NULL);
"""


def get_db():
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def seed_db():
    db = get_db()
    if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        return
    db.execute("INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)", ("investigator", generate_password_hash("bankguard-demo"), "Avery Morgan"))
    customers = [
        ("CUS-2048", "Maya Patel", "Premier Current", 4200, "09:00–18:00", "UPI, Card", 28, 12),
        ("CUS-7714", "Daniel Okafor", "Business Current", 4000, "08:00–19:00", "UPI, NEFT", 34, 18),
        ("CUS-3159", "Sofia Chen", "Savings Plus", 3100, "09:00–20:00", "Card, UPI", 21, 9),
    ]
    db.executemany("INSERT INTO customers (customer_code, name, account_type, typical_amount, typical_time, typical_channels, monthly_volume, payee_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", customers)
    routine = [
        (1, "TX-2001", "2026-08-29 10:12", "Grocery purchase", "Local Grocery", 2450, "UPI"),
        (1, "TX-2002", "2026-08-30 13:45", "Metro top-up", "City Transit", 780, "Card"),
        (1, "TX-2003", "2026-09-01 09:18", "Utility bill", "PowerGrid", 3980, "UPI"),
        (1, "TX-2004", "2026-09-02 17:05", "Pharmacy purchase", "Wellness Pharmacy", 1860, "Card"),
        (1, "TX-2005", "2026-09-03 11:26", "Grocery purchase", "Local Grocery", 4210, "UPI"),
        (1, "TX-2006", "2026-09-04 15:32", "Monthly subscription", "Streamline", 1299, "Card"),
    ]
    difficult = [
        (2, "TX-4101", "2026-08-29 10:04", "Supplier settlement", "Known Supplier", 3800, "NEFT"),
        (2, "TX-4102", "2026-08-30 14:25", "Office supplies", "Office Mart", 5200, "UPI"),
        (2, "TX-4103", "2026-09-04 23:48", "Vendor payment", "PAYEE-X", 20000, "UPI"),
        (2, "TX-4104", "2026-09-04 23:55", "Vendor payment", "PAYEE-X", 18500, "UPI"),
        (2, "TX-4105", "2026-09-05 00:07", "Vendor payment", "PAYEE-X", 21000, "UPI"),
        (2, "TX-4106", "2026-09-05 00:18", "Urgent settlement", "PAYEE-X", 45000, "UPI"),
        (2, "TX-4107", "2026-09-05 02:16", "External transfer", "PAYEE-X", 48000, "NEFT"),
        (3, "TX-6201", "2026-09-01 12:10", "Restaurant", "Green Table", 2800, "Card"),
        (3, "TX-6202", "2026-09-03 18:20", "Household purchase", "Home Goods", 3600, "Card"),
        (3, "TX-6203", "2026-09-04 09:40", "Grocery purchase", "Market Street", 2900, "UPI"),
    ]
    db.executemany("INSERT INTO transactions (customer_id, transaction_code, occurred_at, description, payee, amount, channel) VALUES (?, ?, ?, ?, ?, ?, ?)", routine + difficult)
    db.commit()
