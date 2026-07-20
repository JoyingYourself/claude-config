"""Honest trial counter for factor research.

SQLite-backed database that records every factor test. n_trials is a simple
COUNT(*) — there is no API to zero it out. Every factor, every parameter sweep,
every "let me just try one more thing" gets a row.

The deflated Sharpe gate reads n_trials() to compute the expected maximum
Sharpe under the null of no edge. The counter's honesty IS the gate's power.

Database: ~/.gil_factors/trials.db

Schema:
    CREATE TABLE trials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factor_name TEXT NOT NULL,
        expression TEXT NOT NULL,
        dataset_path TEXT NOT NULL,
        ic_mean REAL,
        ic_ir REAL,
        sharpe REAL,
        accepted INTEGER NOT NULL DEFAULT 0,
        rejection_reason TEXT,
        returns_json TEXT,
        created_at TEXT NOT NULL
    );
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

DB_DIR = os.path.expanduser("~/.gil_factors")
DB_PATH = os.path.join(DB_DIR, "trials.db")


@dataclass
class TrialRecord:
    factor_name: str
    expression: str
    dataset_path: str
    ic_mean: float = 0.0
    ic_ir: float = 0.0
    sharpe: float = 0.0
    accepted: bool = False
    rejection_reason: str | None = None
    returns_json: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_SCHEMA = """
CREATE TABLE IF NOT EXISTS trials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factor_name TEXT NOT NULL,
    expression TEXT NOT NULL,
    dataset_path TEXT NOT NULL,
    ic_mean REAL DEFAULT 0.0,
    ic_ir REAL DEFAULT 0.0,
    sharpe REAL DEFAULT 0.0,
    accepted INTEGER NOT NULL DEFAULT 0,
    rejection_reason TEXT,
    returns_json TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trials_accepted ON trials(accepted);
CREATE INDEX IF NOT EXISTS idx_trials_created ON trials(created_at);
"""


class TrialsDB:
    """Persistent store of every factor trial.

    Use `record()` after each factor is validated; use `count()` to feed the
    deflated-Sharpe gate; use `accepted_returns()` to get returns for the
    correlation and PCA gates.
    """

    def __init__(self, path: str | Path = DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        for statement in _SCHEMA.strip().split(";"):
            if statement.strip():
                self._conn.execute(statement)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "TrialsDB":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def record(self, trial: TrialRecord) -> int:
        """Insert a trial. Returns the new row id."""
        cursor = self._conn.execute(
            """
            INSERT INTO trials (
                factor_name, expression, dataset_path, ic_mean, ic_ir,
                sharpe, accepted, rejection_reason, returns_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trial.factor_name,
                trial.expression,
                trial.dataset_path,
                trial.ic_mean,
                trial.ic_ir,
                trial.sharpe,
                int(trial.accepted),
                trial.rejection_reason,
                trial.returns_json,
                trial.created_at,
            ),
        )
        row_id = cursor.lastrowid
        return int(row_id) if row_id is not None else -1

    def count(self) -> int:
        """How many trials recorded. Feeds deflated_sharpe(n_trials=...)."""
        row = self._conn.execute("SELECT COUNT(*) AS c FROM trials").fetchone()
        return int(row["c"]) if row else 0

    def accepted_count(self) -> int:
        """Number of accepted factors."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM trials WHERE accepted=1"
        ).fetchone()
        return int(row["c"]) if row else 0

    def accepted_returns(self) -> list[pd.Series]:
        """Reconstruct the return series of every accepted trial.

        Used by evaluate_gates for the correlation and PCA gates.
        """
        rows = self._conn.execute(
            "SELECT factor_name, returns_json FROM trials WHERE accepted=1 ORDER BY id"
        ).fetchall()
        series_list: list[pd.Series] = []
        for row in rows:
            payload = row["returns_json"]
            if not payload:
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                # Simple array of returns
                series_list.append(pd.Series(data, name=row["factor_name"]))
            elif isinstance(data, dict) and "values" in data:
                series_list.append(
                    pd.Series(data["values"], name=row["factor_name"])
                )
        return series_list

    def accepted_factors(self) -> list[dict[str, Any]]:
        """List all accepted factors with their stats."""
        rows = self._conn.execute(
            "SELECT factor_name, expression, ic_mean, ic_ir, sharpe, created_at "
            "FROM trials WHERE accepted=1 ORDER BY id"
        ).fetchall()
        return [
            {
                "factor_name": r["factor_name"],
                "expression": r["expression"],
                "ic_mean": r["ic_mean"],
                "ic_ir": r["ic_ir"],
                "sharpe": r["sharpe"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def recent_rejections(self, limit: int = 10) -> list[dict[str, Any]]:
        """Recent rejection reasons for diagnostics."""
        rows = self._conn.execute(
            "SELECT factor_name, expression, rejection_reason, created_at "
            "FROM trials WHERE accepted=0 ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "factor_name": r["factor_name"],
                "expression": r["expression"],
                "rejection_reason": r["rejection_reason"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def summary(self) -> dict[str, Any]:
        """High-level summary of the trial database."""
        total = self.count()
        accepted = self.accepted_count()
        return {
            "total_trials": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "acceptance_rate": round(accepted / total, 3) if total > 0 else 0.0,
            "accepted_factors": self.accepted_factors(),
            "recent_rejections": self.recent_rejections(5),
            "db_path": str(self.path),
        }

    def to_dicts(self) -> list[dict[str, Any]]:
        """Dump everything as dicts for inspection / export."""
        rows = self._conn.execute("SELECT * FROM trials ORDER BY id").fetchall()
        return [dict(r) for r in rows]
