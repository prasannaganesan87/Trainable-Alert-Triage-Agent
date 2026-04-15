import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

DATA_DIR = Path("data")
HISTORY_FILE = DATA_DIR / "triage_history.jsonl"

class TriageRecord(BaseModel):
    timestamp: str
    subject: str
    body: str
    decision: str
    comment: Optional[str] = None
    model_suggestion: Optional[str] = None
    confidence: Optional[float] = None
    is_auto: bool = False

def init_data_dir():
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)

def append_record(record: TriageRecord):
    init_data_dir()
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")

def load_history() -> List[TriageRecord]:
    if not HISTORY_FILE.exists():
        return []
    records = []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(TriageRecord.model_validate_json(line))
                except Exception:
                    pass
    return records

PROCESSED_FILE = DATA_DIR / "processed.txt"

def init_processed_file():
    if not PROCESSED_FILE.exists():
        init_data_dir()
        PROCESSED_FILE.touch()

def get_processed_ids() -> set:
    init_processed_file()
    with open(PROCESSED_FILE, "r") as f:
        return set(line.strip() for line in f)

def mark_processed(entry_id: str):
    init_processed_file()
    with open(PROCESSED_FILE, "a") as f:
        f.write(f"{entry_id}\n")
