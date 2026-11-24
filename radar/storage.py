"""Lokalna baza SQLite z migawkami ofert (jedno uruchomienie fetch = jeden run)."""

import os
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    env TEXT NOT NULL,              -- prod / sandbox / demo
    finished INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS search_meta (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    phrase TEXT NOT NULL,
    total_count INTEGER
);
CREATE TABLE IF NOT EXISTS offers (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    phrase TEXT NOT NULL,
    sort TEXT,
    offer_id TEXT NOT NULL,
    name TEXT,
    price REAL,
    delivery_price REAL,
    seller_id TEXT,
    seller_login TEXT,
    super_seller INTEGER,
    company INTEGER,
    popularity INTEGER,
    category_id TEXT,
    stock INTEGER,
    promoted INTEGER,
    raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_offers_run ON offers(run_id);
"""

OFFER_COLS = ["offer_id", "name", "price", "delivery_price", "seller_id", "seller_login",
              "super_seller", "company", "popularity", "category_id", "stock", "promoted", "raw"]


class Storage:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def new_run(self, env, started_at=None):
        started_at = started_at or datetime.now()
        cur = self.db.execute("INSERT INTO runs (started_at, env) VALUES (?, ?)",
                              (started_at.isoformat(timespec="seconds"), env))
        self.db.commit()
        return cur.lastrowid

    def finish_run(self, run_id):
        self.db.execute("UPDATE runs SET finished = 1 WHERE id = ?", (run_id,))
        self.db.commit()

    def delete_run(self, run_id):
        for table in ("offers", "search_meta"):
            self.db.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
        self.db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        self.db.commit()

    def add_meta(self, run_id, phrase, total_count):
        self.db.execute("INSERT INTO search_meta VALUES (?, ?, ?)", (run_id, phrase, total_count))

    def add_offers(self, run_id, phrase, sort, offers):
        cols = ["run_id", "phrase", "sort"] + OFFER_COLS
        sql = f"INSERT INTO offers ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
        self.db.executemany(sql, [[run_id, phrase, sort] + [o.get(c) for c in OFFER_COLS]
                                  for o in offers])
        self.db.commit()

    def runs(self, env=None):
        sql = "SELECT * FROM runs WHERE finished = 1"
        args = ()
        if env:
            sql += " AND env = ?"
            args = (env,)
        return [dict(r) for r in self.db.execute(sql + " ORDER BY id", args)]

    def run(self, run_id):
        row = self.db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def offers(self, run_id):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM offers WHERE run_id = ?", (run_id,))]

    def meta(self, run_id):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM search_meta WHERE run_id = ?", (run_id,))]

    def count_offers(self, run_id):
        return self.db.execute("SELECT COUNT(*) FROM offers WHERE run_id = ?",
                               (run_id,)).fetchone()[0]
