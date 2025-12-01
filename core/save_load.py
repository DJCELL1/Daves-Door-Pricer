import os
import json
from datetime import datetime
import pandas as pd
import numpy as np

QUOTES_DIR = "quotes"


def ensure_quotes_dir():
    if not os.path.exists(QUOTES_DIR):
        os.makedirs(QUOTES_DIR)


def get_existing_q_numbers():
    ensure_quotes_dir()
    files = os.listdir(QUOTES_DIR)
    qnums = [f.replace(".json", "") for f in files if f.endswith(".json")]
    return sorted(qnums)


def suggest_next_q():
    qnums = get_existing_q_numbers()

    if not qnums:
        return "Q0001"

    nums = []
    for q in qnums:
        try:
            nums.append(int(q.replace("Q", "")))
        except:
            pass

    if not nums:
        return "Q0001"

    return f"Q{max(nums) + 1:04d}"


def json_safe(o):
    # Prevent DataFrame ambiguity
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
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    return json_safe(obj)


def save_quote(qnum, customer, project, raw_rows, recalculated_rows, settings):
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
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

    return True


def load_quote(qnum):
    ensure_quotes_dir()
    path = os.path.join(QUOTES_DIR, f"{qnum}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)
