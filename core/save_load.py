import os
import json
from datetime import datetime
import pandas as pd
import numpy as np

QUOTES_DIR = "quotes"


# ============================================================
# CORE HELPERS
# ============================================================
def ensure_quotes_dir():
    """Create quotes/ folder if missing."""
    if not os.path.exists(QUOTES_DIR):
        os.makedirs(QUOTES_DIR)


def get_existing_q_numbers():
    """Return list of all saved quote filenames without extension."""
    ensure_quotes_dir()
    files = [f for f in os.listdir(QUOTES_DIR) if f.endswith(".json")]
    qnums = [f.replace(".json", "") for f in files]
    return sorted(qnums)


# ============================================================
# NEXT QUOTE NUMBER
# ============================================================
def suggest_next_q():
    """Suggest next quote number: Q0001, Q0002, etc."""
    qnums = get_existing_q_numbers()

    if not qnums:
        return "Q0001"

    nums = []
    for q in qnums:
        try:
            nums.append(int(q.replace("Q", "").strip()))
        except:
            pass

    if not nums:
        return "Q0001"

    next_num = max(nums) + 1
    return f"Q{next_num:04d}"


# ============================================================
# JSON SAFETY LAYER
# ============================================================
def json_safe(o):
    """Convert objects into JSON-friendly forms."""
    if isinstance(o, pd.DataFrame):
        return o.to_dict(orient="records")
    if isinstance(o, pd.Series):
        return o.to_dict()

    if isinstance(o, (np.integer, int)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return float(o)

    try:
        if pd.isna(o):
            return None
    except:
        pass

    if isinstance(o, pd.Timestamp):
        return o.strftime("%Y-%m-%d %H:%M:%S")

    return o


def make_json_safe(obj):
    """Deep convert nested objects for safe JSON writing."""
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    return json_safe(obj)


# ============================================================
# SAVE QUOTE
# ============================================================
def save_quote(qnum, customer, project, raw_rows, recalculated_rows, settings):
    """
    Save a quote with FULL data:
    - raw rows
    - recalculated rows
    - settings snapshot
    """
    ensure_quotes_dir()

    data = {
        "q_number": qnum,
        "customer": customer,
        "project": project,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_rows": make_json_safe(raw_rows),
        "recalculated_rows": make_json_safe(recalculated_rows),
        "settings": make_json_safe(settings)
    }

    path = os.path.join(QUOTES_DIR, f"{qnum}.json")

    # Write JSON
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return True
import os

def delete_quote(qnum):
    """
    Deletes a saved quote JSON file.
    Returns True if deleted, False if not found.
    """
    path = os.path.join("quotes", f"{qnum}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False



# ============================================================
# LOAD QUOTE
# ============================================================
def load_quote(qnum):
    """Load a saved quote safely and return dict."""
    ensure_quotes_dir()
    path = os.path.join(QUOTES_DIR, f"{qnum}.json")

    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
