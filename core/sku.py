import re

def create_sku(prefix, thickness, height, width, jamb, form):
    m = re.search(r"(\d+)[xX](\d+)", jamb)
    face = m.group(1) if m else "0"
    stop = m.group(2) if m else "0"
    ph = f"PH{stop}-{face}"

    sku = f"{prefix}{thickness.replace('mm','')}{height}{width}{ph}"
    return sku + "-PR" if form == "Double" else sku
