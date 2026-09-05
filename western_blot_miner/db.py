"""SQLite storage for extracted western blot records.

One row per (protein, figure) extraction result. The schema is intentionally
flat — a single searchable table is all the demo needs.
"""
import sqlite3
from contextlib import contextmanager
from typing import Iterable, Optional

from . import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    protein         TEXT NOT NULL,
    protein_norm    TEXT NOT NULL,          -- uppercased for case-insensitive search
    cell_line       TEXT,
    organism        TEXT,
    mol_weight_kda  TEXT,
    antibody        TEXT,
    condition       TEXT,
    result          TEXT,                   -- expressed / not expressed / up / down / unclear
    pmid            TEXT,
    pmcid           TEXT,
    doi             TEXT,
    figure_id       TEXT,
    figure_caption  TEXT,
    image_path      TEXT,
    confidence      REAL,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_protein_norm ON records(protein_norm);
CREATE INDEX IF NOT EXISTS idx_pmcid_fig    ON records(pmcid, figure_id);

-- Track which (pmcid, figure) pairs we've already processed so re-runs are idempotent.
CREATE TABLE IF NOT EXISTS processed_figures (
    pmcid     TEXT NOT NULL,
    figure_id TEXT NOT NULL,
    PRIMARY KEY (pmcid, figure_id)
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def figure_already_processed(pmcid: str, figure_id: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_figures WHERE pmcid=? AND figure_id=?",
            (pmcid, figure_id),
        ).fetchone()
        return row is not None


def mark_figure_processed(pmcid: str, figure_id: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_figures (pmcid, figure_id) VALUES (?, ?)",
            (pmcid, figure_id),
        )


def insert_records(records: Iterable[dict]) -> int:
    rows = list(records)
    if not rows:
        return 0
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO records
                (protein, protein_norm, cell_line, organism, mol_weight_kda,
                 antibody, condition, result, pmid, pmcid, doi,
                 figure_id, figure_caption, image_path, confidence)
            VALUES
                (:protein, :protein_norm, :cell_line, :organism, :mol_weight_kda,
                 :antibody, :condition, :result, :pmid, :pmcid, :doi,
                 :figure_id, :figure_caption, :image_path, :confidence)
            """,
            rows,
        )
    return len(rows)


def search(protein: str, limit: int = 200) -> list[dict]:
    """Substring match on the normalized protein name."""
    needle = f"%{protein.strip().upper()}%"
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM records
            WHERE protein_norm LIKE ?
            ORDER BY (confidence IS NULL), confidence DESC, id DESC
            LIMIT ?
            """,
            (needle, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def stats_for(protein: str) -> dict:
    needle = f"%{protein.strip().upper()}%"
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*)                         AS n_results,
                COUNT(DISTINCT pmcid)            AS n_papers,
                COUNT(DISTINCT cell_line)        AS n_cell_lines
            FROM records
            WHERE protein_norm LIKE ?
            """,
            (needle,),
        ).fetchone()
        return dict(row) if row else {}


def global_stats() -> dict:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n_records,
                   COUNT(DISTINCT pmcid) AS n_papers,
                   COUNT(DISTINCT protein_norm) AS n_proteins
            FROM records
            """
        ).fetchone()
        return dict(row) if row else {}
