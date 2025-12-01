import pandas as pd
import re

# ---------------------------------------------
# Handle width ranges in your price tables
# ---------------------------------------------
def width_band(width: int):
    if 410 <= width <= 810:
        return "410-810"
    return str(width)

# ---------------------------------------------
# Get the leaf price from the DF
# ---------------------------------------------
def leaf_price(df, height, width, thickness):
    wb = width_band(width)

    # Match exact height + width or width range
    row = df[(df["Height"] == str(height)) & (df["Width"] == wb)]

    if row.empty:
        return None  # signals POA

    price = row.iloc[0][thickness]
    return float(price) if not pd.isna(price) else 0.0

# ---------------------------------------------
# Extract jamb thickness
# ---------------------------------------------
def parse_jamb_thickness(jamb):
    m = re.search(r"\d+x(\d+)", jamb)
    return int(m.group(1)) if m else 18

# ---------------------------------------------
# Frame lengths + cost
# ---------------------------------------------
def frame_cost_and_pieces(height, width, jamb, form, prices, min_charge):
    jamb_thk = parse_jamb_thickness(jamb)

    # Legs
    leg_len_mm = height + 23

    # Head
    if form == "Double":
        head_len_mm = (width * 2) + 9 + (jamb_thk * 2)
    else:
        head_len_mm = width + 6 + (jamb_thk * 2)

    # Total frame length
    total_mm = (leg_len_mm * 2) + head_len_mm
    frame_m = total_mm / 1000

    raw_cost = frame_m * prices[jamb]
    cost = max(raw_cost, min_charge)

    return cost, frame_m, leg_len_mm, head_len_mm

# ---------------------------------------------
# Stop cost (same length as frame)
# ---------------------------------------------
def stop_cost(frame_m, stop_rate, minimum):
    raw = frame_m * stop_rate
    return max(raw, minimum)
