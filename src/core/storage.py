"""
Persistence layer for CQIA reports and jobs.

This module supports two backends:
1. SQLModel + SQLite (if SQLModel is installed)
2. File-based JSON storage fallback (if SQLModel is unavailable)

Functions provided:
- init_db(sqlite_url: str = "sqlite:///cqia.db")
- save_report(report: Dict[str, Any]) -> int
- get_report_by_id(report_id: int) -> Dict[str, Any]
- list_reports(limit=20, offset=0) -> List[Dict[str, Any]]
"""

import json
import datetime
import os
import random
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from sqlmodel import SQLModel, Field, Session, create_engine, select
except Exception:  # SQLModel not installed
    SQLModel = None

# --- Globals ---
_engine = None
_data_dir = Path("./data")
_index_file = _data_dir / "index.json"


# --- SQLModel-backed classes ---
if SQLModel:

    class Report(SQLModel, table=True):
        """Report model persisted in database."""
        id: Optional[int] = Field(default=None, primary_key=True)
        created_at: datetime.datetime
        path: str
        overall_score: int
        raw_json: str

    class Job(SQLModel, table=True):
        """Job model persisted in database."""
        id: Optional[int] = Field(default=None, primary_key=True)
        created_at: datetime.datetime
        status: str
        report_id: Optional[int] = None
        parameters: str = ""


# --- Core functions ---
def init_db(sqlite_url: str = "sqlite:///cqia.db"):
    """
    Initialize persistence layer.

    If SQLModel is available, sets up SQLite DB.
    Otherwise, sets up file-based storage.
    """
    global _engine
    if SQLModel:
        _engine = create_engine(sqlite_url)
        SQLModel.metadata.create_all(_engine)
    else:
        _data_dir.mkdir(exist_ok=True)
        if not _index_file.exists():
            with open(_index_file, "w") as f:
                json.dump({"last_id": 0, "map": {}}, f)


def save_report(report: Dict[str, Any]) -> int:
    """
    Save a report. Returns the ID of the saved report.

    Args:
        report: Dict with analysis results.
    Returns:
        int: report ID
    """
    if SQLModel and _engine:
        with Session(_engine) as session:
            new_report = Report(
                created_at=datetime.datetime.utcnow(),
                path=str(report.get("meta", {}).get("path", "")),
                overall_score=int(report.get("overall_score", 0)),
                raw_json=json.dumps(report),
            )
            session.add(new_report)
            session.commit()
            session.refresh(new_report)
            return new_report.id
    else:
        ts = int(datetime.datetime.utcnow().timestamp())
        rid = _next_file_id()
        fname = f"report_{ts}_{rid}.json"
        path = _data_dir / fname
        with open(path, "w") as f:
            json.dump(report, f)
        _update_index(rid, str(path))
        return rid


def get_report_by_id(report_id: int) -> Dict[str, Any]:
    """
    Load a report by its ID.

    Raises ValueError if not found.
    """
    if SQLModel and _engine:
        with Session(_engine) as session:
            stmt = select(Report).where(Report.id == report_id)
            res = session.exec(stmt).first()
            if not res:
                raise ValueError(f"Report {report_id} not found")
            return json.loads(res.raw_json)
    else:
        mapping = _load_index()["map"]
        path = mapping.get(str(report_id))
        if not path or not Path(path).exists():
            raise ValueError(f"Report {report_id} not found")
        with open(path) as f:
            return json.load(f)


def list_reports(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List reports in storage.
    """
    if SQLModel and _engine:
        with Session(_engine) as session:
            stmt = select(Report).order_by(Report.created_at.desc()).offset(offset).limit(limit)
            results = session.exec(stmt).all()
            return [json.loads(r.raw_json) for r in results]
    else:
        mapping = _load_index()["map"]
        ids = sorted(map(int, mapping.keys()), reverse=True)
        selected = ids[offset : offset + limit]
        reports = []
        for rid in selected:
            try:
                reports.append(get_report_by_id(rid))
            except ValueError:
                continue
        return reports


# --- Fallback helpers ---
def _next_file_id() -> int:
    data = _load_index()
    data["last_id"] += 1
    _save_index(data)
    return data["last_id"]


def _update_index(rid: int, path: str):
    data = _load_index()
    data["map"][str(rid)] = path
    _save_index(data)


def _load_index() -> Dict[str, Any]:
    if not _index_file.exists():
        return {"last_id": 0, "map": {}}
    with open(_index_file) as f:
        return json.load(f)


def _save_index(data: Dict[str, Any]):
    with open(_index_file, "w") as f:
        json.dump(data, f, indent=2)
