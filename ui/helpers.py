def build_door_order_rows(df):
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "Door #": r.get("Door #"),
            "Room": r.get("Room Name", r.get("Description", "")),
            "Handing": r.get("Handing", ""),
            "UnderCut": r.get("UnderCut", 25),
            "LeafWidth": r.get("Width"),
            "LeafHeight": r.get("Height"),
            "JambType": r.get("JambType", ""),
            "Form": r.get("Form", "Single"),
        })
    return rows
