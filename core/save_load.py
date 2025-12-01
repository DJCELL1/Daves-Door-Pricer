import os
import json
from datetime import datetime

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
    next_num = max(nums) + 1
    return f"Q{next_num:04d}"


def save_quote(qnum, customer, project, raw_rows, recalculated_rows, settings):
    ensure_quotes_dir()

    data = {
        "q_number": qnum,
        "customer": customer,
        "project": project,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_rows": raw_rows,
        "recalculated_rows": recalculated_rows,
        "settings": settings
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
