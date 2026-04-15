import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("data")
STATE_FILE = DATA_DIR / "state.json"

def init_data_dir():
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)

def load_state() -> dict:
    init_data_dir()
    if not STATE_FILE.exists():
        return {"shift_active": False, "shift_start": None, "auto_mode": False}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state: dict):
    init_data_dir()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def start_shift() -> bool:
    state = load_state()
    if state.get("shift_active"):
        return False # Already active
    
    state["shift_active"] = True
    state["shift_start"] = datetime.now().isoformat()
    save_state(state)
    return True

def end_shift() -> bool:
    state = load_state()
    if not state.get("shift_active"):
        return False # Already inactive
        
    state["shift_active"] = False
    state["shift_start"] = None
    save_state(state)
    return True

def is_shift_active() -> bool:
    state = load_state()
    return state.get("shift_active", False)

def toggle_auto_mode(active: bool):
    state = load_state()
    state["auto_mode"] = active
    save_state(state)

def is_auto_mode_active() -> bool:
    state = load_state()
    return state.get("auto_mode", False)
