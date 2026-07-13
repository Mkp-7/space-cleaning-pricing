"""
Database layer for the Pricing & Revenue Management Platform.
SQLite for simplicity - works out of the box locally and on Streamlit Cloud.
Swap get_connection() to point at Postgres (Supabase/Neon) for real
multi-user persistence; nothing else in the app needs to change.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "pricing_data.db"

PRICING_UNITS = ["per hour", "per sq ft", "flat rate", "per event", "per room"]
JOB_STATUSES = ["Scheduled", "Completed", "Paid", "Cancelled"]


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT,
            pricing_unit TEXT NOT NULL DEFAULT 'flat rate',
            our_rate REAL,
            notes TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            website TEXT,
            service_area TEXT,
            notes TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS competitor_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            rate REAL,
            pricing_unit TEXT,
            source_note TEXT,
            updated_at TEXT,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE,
            FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
            UNIQUE(competitor_id, service_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            role TEXT,
            active INTEGER DEFAULT 1,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            service_id INTEGER,
            employee_id INTEGER,
            job_date TEXT,
            price_charged REAL,
            total_cost REAL,
            status TEXT DEFAULT 'Scheduled',
            notes TEXT,
            updated_at TEXT,
            FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- SERVICES ----------

def add_service(name, category, pricing_unit, our_rate, notes=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO services (name, category, pricing_unit, our_rate, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, category, pricing_unit, our_rate, notes, now()),
    )
    conn.commit()
    conn.close()


def update_service(service_id, name, category, pricing_unit, our_rate, notes=""):
    conn = get_connection()
    conn.execute(
        "UPDATE services SET name=?, category=?, pricing_unit=?, our_rate=?, notes=?, updated_at=? WHERE id=?",
        (name, category, pricing_unit, our_rate, notes, now(), service_id),
    )
    conn.commit()
    conn.close()


def update_service_rate(service_id, our_rate):
    conn = get_connection()
    conn.execute("UPDATE services SET our_rate=?, updated_at=? WHERE id=?", (our_rate, now(), service_id))
    conn.commit()
    conn.close()


def delete_service(service_id):
    conn = get_connection()
    conn.execute("DELETE FROM services WHERE id=?", (service_id,))
    conn.commit()
    conn.close()


def get_services():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM services ORDER BY category, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_service(service_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------- COMPETITORS ----------

def add_competitor(name, website="", service_area="", notes=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO competitors (name, website, service_area, notes, updated_at) VALUES (?, ?, ?, ?, ?)",
        (name, website, service_area, notes, now()),
    )
    conn.commit()
    conn.close()


def update_competitor(competitor_id, name, website, service_area, notes):
    conn = get_connection()
    conn.execute(
        "UPDATE competitors SET name=?, website=?, service_area=?, notes=?, updated_at=? WHERE id=?",
        (name, website, service_area, notes, now(), competitor_id),
    )
    conn.commit()
    conn.close()


def delete_competitor(competitor_id):
    conn = get_connection()
    conn.execute("DELETE FROM competitors WHERE id=?", (competitor_id,))
    conn.commit()
    conn.close()


def get_competitors():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM competitors ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- COMPETITOR PRICES ----------

def upsert_competitor_price(competitor_id, service_id, rate, pricing_unit, source_note=""):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO competitor_prices (competitor_id, service_id, rate, pricing_unit, source_note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(competitor_id, service_id)
        DO UPDATE SET rate=excluded.rate, pricing_unit=excluded.pricing_unit,
                      source_note=excluded.source_note, updated_at=excluded.updated_at
        """,
        (competitor_id, service_id, rate, pricing_unit, source_note, now()),
    )
    conn.commit()
    conn.close()


def delete_competitor_price(price_id):
    conn = get_connection()
    conn.execute("DELETE FROM competitor_prices WHERE id=?", (price_id,))
    conn.commit()
    conn.close()


def get_competitor_prices():
    conn = get_connection()
    rows = conn.execute("""
        SELECT cp.id, cp.competitor_id, c.name AS competitor_name,
               cp.service_id, s.name AS service_name, s.category,
               cp.rate, cp.pricing_unit, cp.source_note, cp.updated_at
        FROM competitor_prices cp
        JOIN competitors c ON c.id = cp.competitor_id
        JOIN services s ON s.id = cp.service_id
        ORDER BY s.name, c.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- EMPLOYEES ----------

def add_employee(name, role=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO employees (name, role, active, updated_at) VALUES (?, ?, 1, ?)",
        (name, role, now()),
    )
    conn.commit()
    conn.close()


def update_employee(employee_id, name, role, active):
    conn = get_connection()
    conn.execute(
        "UPDATE employees SET name=?, role=?, active=?, updated_at=? WHERE id=?",
        (name, role, int(active), now(), employee_id),
    )
    conn.commit()
    conn.close()


def delete_employee(employee_id):
    conn = get_connection()
    conn.execute("DELETE FROM employees WHERE id=?", (employee_id,))
    conn.commit()
    conn.close()


def get_employees(active_only=False):
    conn = get_connection()
    q = "SELECT * FROM employees"
    if active_only:
        q += " WHERE active=1"
    q += " ORDER BY name"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- JOBS ----------

def add_job(client_name, service_id, employee_id, job_date, price_charged, total_cost, status, notes=""):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO jobs (client_name, service_id, employee_id, job_date, price_charged,
                           total_cost, status, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (client_name, service_id, employee_id, job_date, price_charged, total_cost, status, notes, now()),
    )
    conn.commit()
    conn.close()


def update_job(job_id, client_name, service_id, employee_id, job_date, price_charged, total_cost, status, notes=""):
    conn = get_connection()
    conn.execute(
        """
        UPDATE jobs SET client_name=?, service_id=?, employee_id=?, job_date=?, price_charged=?,
                        total_cost=?, status=?, notes=?, updated_at=?
        WHERE id=?
        """,
        (client_name, service_id, employee_id, job_date, price_charged, total_cost, status, notes, now(), job_id),
    )
    conn.commit()
    conn.close()


def delete_job(job_id):
    conn = get_connection()
    conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    conn.commit()
    conn.close()


def get_jobs():
    conn = get_connection()
    rows = conn.execute("""
        SELECT j.id, j.client_name, j.service_id, s.name AS service_name, s.category,
               j.employee_id, e.name AS employee_name,
               j.job_date, j.price_charged, j.total_cost, j.status, j.notes, j.updated_at
        FROM jobs j
        LEFT JOIN services s ON s.id = j.service_id
        LEFT JOIN employees e ON e.id = j.employee_id
        ORDER BY j.job_date DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- SETTINGS ----------

def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()
