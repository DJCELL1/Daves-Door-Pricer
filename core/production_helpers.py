import pandas as pd
import math

# ============================================================
# HEIGHT CALCULATION
# ============================================================

def calc_final_height(leaf_height, undercut, finished_floor_height):
    """
    Production height:
    leaf_height + 3mm clearance + undercut + finished_floor_height
    """
    return leaf_height + 3 + undercut + finished_floor_height


# ============================================================
# HEAD LENGTH (CUSTOM FACTORY RULE)
# ============================================================

def calc_head_length(width, jamb_thickness, form):
    """
    Single:
        width + 6mm gap + (jamb_thickness * 2)
    Double:
        width + 3mm gap + (jamb_thickness * 2)
    """
    if form == "Single":
        return width + 6 + (jamb_thickness * 2)
    else:
        return width + 3 + (jamb_thickness * 2)


# ============================================================
# FRAME LENGTH CALCULATION
# ============================================================

def calc_frame_lengths(leg_mm, head_mm, qty):
    """
    leg_mm = final height
    head_mm = calculated head
    qty = number of doors in this group

    Returns:
        frame_per_door_m
        total_frame_m
        total_stop_m (same as frame)
    """

    frame_mm_per_door = (leg_mm * 2) + head_mm
    frame_m_per_door = frame_mm_per_door / 1000

    total_frame_m = frame_m_per_door * qty
    total_stop_m = total_frame_m  # stop = same length as frame

    return frame_m_per_door, total_frame_m, total_stop_m


# ============================================================
# GROUPING PRODUCTION MEASUREMENTS
# ============================================================

def group_production_rows(df):
    """
    Groups measured production entries by:
        FinalHeight + LeafType

    Expects columns:
        ['QuoteLine', 'LeafType', 'LeafHeight', 'Width',
         'JambThickness', 'Form', 'Undercut',
         'FinishedFloorHeight', 'Qty']
    """

    df = df.copy()

    # Compute final height
    df["FinalHeight"] = df.apply(
        lambda r: calc_final_height(r["LeafHeight"], r["Undercut"], r["FinishedFloorHeight"]),
        axis=1
    )

    # Group
    grouped = df.groupby(["FinalHeight", "LeafType"]).agg(
        {
            "QuoteLine": "first",
            "LeafHeight": "first",
            "Width": "first",
            "JambThickness": "first",
            "Form": "first",
            "Qty": "sum"
        }
    ).reset_index()

    return grouped


# ============================================================
# STOCK STRATEGY CALCULATIONS
# ============================================================

def apply_stock_strategy(total_m, strategy):
    """
    Returns: (count_54, count_21, waste_m)
    """

    def only_54(m):
        c = math.ceil(m / 5.4)
        waste = c * 5.4 - m
        return c, 0, waste

    def only_21(m):
        c = math.ceil(m / 2.1)
        waste = c * 2.1 - m
        return 0, c, waste

    def mix_lengths(m):
        remaining = m
        count_54 = 0
        count_21 = 0

        # Greedy: use as many 5.4s as possible
        while remaining > 5.4:
            count_54 += 1
            remaining -= 5.4

        # Then use 2.1s
        while remaining > 0:
            count_21 += 1
            remaining -= 2.1

        waste = abs(remaining)
        return count_54, count_21, waste

    if strategy == "Only 5.4":
        return only_54(total_m)
    elif strategy == "Only 2.1":
        return only_21(total_m)
    else:
        return mix_lengths(total_m)


# ============================================================
# CSV PARSER FOR PRODUCTION INPUTS
# ============================================================

def parse_csv_measurements(csv_df):
    """
    Expected columns:
        LeafType, LeafHeight, Width, JambThickness,
        Form, Undercut, FinishedFloorHeight, Qty, QuoteLine

    Auto-converts types & cleans.
    """

    df = csv_df.copy()

    required = [
        "LeafType", "LeafHeight", "Width", "JambThickness",
        "Form", "Undercut", "FinishedFloorHeight", "Qty", "QuoteLine"
    ]

    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column in CSV: {col}")

    # Convert numeric fields
    numeric_cols = ["LeafHeight", "Width", "JambThickness",
                    "Undercut", "FinishedFloorHeight", "Qty"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=numeric_cols)

    return df[required]
