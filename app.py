import streamlit as st
import pandas as pd
import math

# Local modules
from core.settings import get_default_settings
from core.pricing import (
    leaf_price,
    frame_cost_and_pieces,
    stop_cost
)
from core.sku import create_sku
from core.stock import greedy_stock
from utils.loaders import load_hinge_sheet


# =============================================================
# PAGE CONFIG
# =============================================================
st.set_page_config(page_title="Door Intelligence Estimator", layout="wide")
st.title("🚪Dave's Door Intelligence Estimator Bro")


# =============================================================
# SETTINGS INITIALISATION
# =============================================================
if "settings" not in st.session_state:
    st.session_state.settings = get_default_settings()

S = st.session_state.settings

# Load hinge sheet
HINGE_FOLDER = "data"
HINGE_DF = load_hinge_sheet(HINGE_FOLDER)

if HINGE_DF is None:
    st.error("No hinge sheet found in /data. Upload hinge_data.xlsx.")
    st.stop()


# =============================================================
# TABS
# =============================================================
tab1, tab2, tab3, tab4 = st.tabs(["Estimator", "Quote Table", "Settings", "Production"])


# =============================================================
# TAB 1 — ESTIMATOR
# =============================================================
with tab1:
    st.header("Estimator")

    if "rows" not in st.session_state:
        st.session_state.rows = []

    st.subheader("Project Details")
    customer = st.text_input("Customer Name", key="cust")
    project = st.text_input("Project Name", key="proj")

    heights = ["1980", "2200", "2400"]
    widths = ["410", "460", "510", "560", "610", "660",
              "710", "760", "810", "860", "910", "960"]

    leaf_type = st.selectbox("Leaf Type", list(S["door_leaf_prices"].keys()))
    thickness = st.selectbox("Thickness", ["35mm", "38mm"])
    jamb = st.selectbox("Jamb Type", list(S["frame_prices"].keys()))
    height = int(st.selectbox("Height", heights))
    width = int(st.selectbox("Width", widths))
    form = st.selectbox("Single/Double", ["Single", "Double"])
    qty = st.number_input("Qty", min_value=1, value=1)

    # Hinge lookup
    hm = HINGE_DF[(HINGE_DF["Height"] == height) & (HINGE_DF["Width"] == width)]
    if not hm.empty:
        hinges = int(hm.iloc[0]["Hinges"])
        screws = int(hm.iloc[0]["Screws"])
    else:
        hinges = S["hinges_per_door"]
        screws = S["hinges_per_door"] * S["hinge_screws"]

    # SKU + description
    prefix = S["prefix_map"][leaf_type]
    sku = create_sku(prefix, thickness, height, width, jamb, form)

    desc_row = HINGE_DF[HINGE_DF["Code"] == sku]
    desc = desc_row.iloc[0]["Description"] if not desc_row.empty else "DESCRIPTION NOT FOUND"


    # =========================================================
    # ADD LINE BUTTON WITH POA LOGIC
    # =========================================================
    if st.button("Add Line"):

        leaf_cost = leaf_price(
            S["door_leaf_prices"][leaf_type],
            height,
            width,
            thickness
        )

        # POA HANDLING
        if leaf_cost is None:
            poa_key = f"poa_{leaf_type}_{height}_{width}_{thickness}"

            if poa_key not in st.session_state:
                st.session_state[poa_key] = 0.0
                st.warning("❗ Leaf size not found in price list. This leaf is POA.")
                st.number_input(
                    f"Enter POA price for {leaf_type} {height}x{width} ({thickness})",
                    min_value=0.0,
                    key=poa_key
                )
                st.stop()

            # User entered a price
            leaf_cost = st.session_state[poa_key]

        # COST CALCULATIONS
        leaf_mult = 1 if form == "Single" else 2

        frame_cost_val, frame_m, leg_mm, head_mm = frame_cost_and_pieces(
            height,
            width,
            jamb,
            form,
            S["frame_prices"],
            S["minimum_frame_charge"]
        )

        stop_cost_val = stop_cost(
            frame_m,
            S["frame_prices"]["26A 30x10 Door Stop"],
            S["minimum_frame_charge"]
        )

        labour = S["labour_single"] if form == "Single" else S["labour_double"]

        row = {
            "Customer": customer,
            "Project": project,
            "SKU": sku,
            "Description": desc,
            "Leaf": leaf_type,
            "Thickness": thickness,
            "Height": height,
            "Width": width,
            "Form": form,
            "Qty": qty,
            "Jamb Type": jamb,
            "Leaf Cost": leaf_cost * leaf_mult,
            "Frame Cost": frame_cost_val,
            "Stop Cost": stop_cost_val,
            "Labour": labour,
            "Hinges": hinges * leaf_mult,
            "Hinge Cost": hinges * leaf_mult * S["hinge_price"],
            "Screws": screws * leaf_mult,
            "Screw Cost": screws * leaf_mult * S["screw_cost"],
            "Frame Length (m)": frame_m,
            "Leg Length (mm)": leg_mm,
            "Head Length (mm)": head_mm
        }

        row["Total Cost"] = (
            row["Leaf Cost"]
            + row["Frame Cost"]
            + row["Stop Cost"]
            + row["Labour"]
            + row["Hinge Cost"]
            + row["Screw Cost"]
        )

        st.session_state.rows.append(row)


    # RESET BUTTON
    if st.button("Reset All ❌"):
        for key in ["rows", "cust", "proj"]:
            if key in st.session_state:
                del st.session_state[key]

        st.success("Everything reset, uce. Clean slate now.")
        st.stop()

    # SHOW CURRENT TABLE
    if st.session_state.rows:
        st.dataframe(pd.DataFrame(st.session_state.rows))

# =============================================================
# TAB 2 — QUOTE TABLE (LIVE + SAVE + LOAD)
# =============================================================
from core.save_load import (
    suggest_next_q,
    save_quote,
    load_quote,
    get_existing_q_numbers
)

with tab2:
    st.header("Quote Table")

    # ------------------------------
    # LOAD EXISTING QUOTES
    # ------------------------------
    qlist = get_existing_q_numbers()

    load_col, spacer, clear_col = st.columns([2,1,2])

    with load_col:
        q_choice = st.selectbox("Load Existing Quote", [""] + qlist)

    with clear_col:
        if st.button("Clear Loaded Quote ❌"):
            if "rows" in st.session_state:
                del st.session_state["rows"]
            if "cust" in st.session_state:
                del st.session_state["cust"]
            if "proj" in st.session_state:
                del st.session_state["proj"]
            st.success("Cleared loaded quote.")
            st.experimental_rerun()

    # If user selects a quote to load
    if q_choice:
        data = load_quote(q_choice)

        if data:
            # Load data BEFORE widgets are drawn
            st.session_state.rows = data["raw_rows"]
            st.session_state.cust = data["customer"]
            st.session_state.proj = data["project"]
            st.success(f"Loaded quote {q_choice}")
            st.experimental_rerun()


    # ------------------------------
    # If no rows, show message
    # ------------------------------
    if not st.session_state.get("rows"):
        st.info("Add some doors first.")
        st.stop()

    # ------------------------------
    # PROCESS + DISPLAY QUOTE
    # ------------------------------
    df = pd.DataFrame(st.session_state.rows)

    st.subheader(f"Customer: {st.session_state.cust}")
    st.subheader(f"Project: {st.session_state.proj}")

    suggested_q = suggest_next_q()
    qnum = st.text_input("Q Number", value=suggested_q)

    mk = st.number_input("Markup %", value=25)

    recalculated_rows = []

    for _, r in df.iterrows():
        leaf_mult = 1 if r["Form"] == "Single" else 2

        frame_cost_val, frame_m, leg_mm, head_mm = frame_cost_and_pieces(
            r["Height"],
            r["Width"],
            r["Jamb Type"],
            r["Form"],
            S["frame_prices"],
            S["minimum_frame_charge"]
        )

        stop_cost_val = stop_cost(
            frame_m,
            S["frame_prices"]["26A 30x10 Door Stop"],
            S["minimum_frame_charge"]
        )

        hinge_cost = r["Hinges"] * S["hinge_price"]
        screw_cost = r["Screws"] * S["screw_cost"]
        labour = S["labour_single"] if r["Form"] == "Single" else S["labour_double"]

        total = (
            r["Leaf Cost"]
            + frame_cost_val
            + stop_cost_val
            + labour
            + hinge_cost
            + screw_cost
        )

        recalculated_rows.append({
            **r,
            "Frame Cost": frame_cost_val,
            "Stop Cost": stop_cost_val,
            "Labour": labour,
            "Hinge Cost": hinge_cost,
            "Screw Cost": screw_cost,
            "Total Cost": total,
            "Sell": total * (1 + mk / 100),
            "Margin %": ((total * (1 + mk/100)) - total) / (total * (1 + mk/100)) * 100
        })

    new_df = pd.DataFrame(recalculated_rows)
    st.dataframe(new_df)

    if st.button("Save Quote 💾"):
        save_quote(
            qnum,
            st.session_state.cust,
            st.session_state.proj,
            df.to_dict(orient="records"),
            new_df.to_dict(orient="records"),
            S
        )
        st.success(f"Quote {qnum} saved!")

    st.download_button("Download CSV", new_df.to_csv(index=False), "quote.csv")



# =============================================================
# TAB 3 — SETTINGS (ALWAYS LIVE + RESET DEFAULTS)
# =============================================================
with tab3:
    st.header("Settings (Always Live)")

    # Reset settings to defaults
    if st.button("Reset Settings to Default 🔄"):
        st.session_state.settings = get_default_settings()
        S = st.session_state.settings
        st.success("Settings reset to default values, uso.")
        st.experimental_rerun()

    st.subheader("Frame Prices")
    for k in S["frame_prices"]:
        S["frame_prices"][k] = st.number_input(
            k,
            value=S["frame_prices"][k],
            key=f"fp_{k}"
        )

    st.subheader("Labour")
    S["labour_single"] = st.number_input(
        "Single Labour",
        value=S["labour_single"],
        key="lab1"
    )
    S["labour_double"] = st.number_input(
        "Double Labour",
        value=S["labour_double"],
        key="lab2"
    )

    st.subheader("Hardware Costs")
    S["hinge_price"] = st.number_input(
        "Hinge Price",
        value=S["hinge_price"],
        key="hingep"
    )
    S["hinges_per_door"] = st.number_input(
        "Hinges per Door",
        value=S["hinges_per_door"],
        key="hingecount"
    )
    S["screw_cost"] = st.number_input(
        "Screw Cost",
        value=S["screw_cost"],
        key="scr_cost"
    )
    S["hinge_screws"] = st.number_input(
        "Screws per Hinge",
        value=S["hinge_screws"],
        key="scr_hinges"
    )

    st.subheader("Minimum Charges")
    S["minimum_frame_charge"] = st.number_input(
        "Minimum Charge",
        value=S["minimum_frame_charge"],
        key="mincharge"
    )


# =============================================================
# TAB 4 — PRODUCTION
# =============================================================
with tab4:
    st.header("Production Summary")

    if not st.session_state.rows:
        st.info("Add some doors first.")
    else:
        df = pd.DataFrame(st.session_state.rows)

        # FRAME ORDER STRATEGY
        st.subheader("Stock Length Strategy")
        opt = st.radio(
            "Choose Stock Availability:",
            ["Mix (5.4 + 2.1)", "Only 5.4m", "Only 2.1m"],
            horizontal=True
        )

        # Helper functions
        def only_54(total):
            count = math.ceil(total / 5.4)
            waste = count * 5.4 - total
            return count, waste

        def only_21(total):
            count = math.ceil(total / 2.1)
            waste = count * 2.1 - total
            return count, waste

        # TOTALS
        df["Leafs to Order"] = df.apply(lambda r: r["Qty"] * (1 if r["Form"] == "Single" else 2), axis=1)
        df["Total Hinges"] = df["Qty"] * df["Hinges"]
        df["Total Screws"] = df["Qty"] * df["Screws"]
        df["Total Frame (m)"] = df["Qty"] * df["Frame Length (m)"]
        df["Total Stop (m)"] = df["Total Frame (m)"]

        total_leafs = int(df["Leafs to Order"].sum())
        total_hinges = int(df["Total Hinges"].sum())
        total_screws = int(df["Total Screws"].sum())

        st.subheader("Totals")
        st.write(f"Leafs needed: **{total_leafs}**")
        st.write(f"Hinges needed: **{total_hinges}**")
        st.write(f"Screws needed: **{total_screws}**")

        # FRAME BY JAMB TYPE
        st.subheader("Frame Ordering by Jamb Type")
        frame_group = df.groupby("Jamb Type")["Total Frame (m)"].sum().reset_index()

        for _, row in frame_group.iterrows():
            jamb = row["Jamb Type"]
            total_m = row["Total Frame (m)"]

            if opt == "Only 5.4m":
                f54, waste = only_54(total_m)
                st.write(f"### {jamb} — Only 5.4m")
                st.write(f"5.4m lengths: **{f54}**")
                st.write(f"Waste: **{waste:.2f} m**")

            elif opt == "Only 2.1m":
                f21, waste = only_21(total_m)
                st.write(f"### {jamb} — Only 2.1m")
                st.write(f"2.1m lengths: **{f21}**")
                st.write(f"Waste: **{waste:.2f} m**")

            else:
                f54, f21, waste = greedy_stock(total_m)
                st.write(f"### {jamb} — Mixed Stock")
                st.write(f"5.4m: **{f54}**")
                st.write(f"2.1m: **{f21}**")
                st.write(f"Waste: **{waste:.2f} m**")

            st.write("---")

        # STOP TOTAL
        st.subheader("Total Door Stop Ordering (All Profiles Combined)")
        total_stop_m = df["Total Stop (m)"].sum()

        if opt == "Only 5.4m":
            s54, sw = only_54(total_stop_m)
            st.write(f"5.4m: **{s54}** — Waste: **{sw:.2f} m**")

        elif opt == "Only 2.1m":
            s21, sw = only_21(total_stop_m)
            st.write(f"2.1m: **{s21}** — Waste: **{sw:.2f} m**")

        else:
            s54, s21, sw = greedy_stock(total_stop_m)
            st.write(f"5.4m: **{s54}**, 2.1m: **{s21}**, Waste: **{sw:.2f} m**")

        st.write("---")

        # DOOR MAKEUP SUMMARY
        st.subheader("Door Makeup (Blanks to Order)")
        makeup_cols = ["SKU", "Leaf", "Thickness", "Height", "Width", "Form", "Qty"]
        makeup_df = df[makeup_cols].copy()

        makeup_df["Total Leafs"] = makeup_df.apply(
            lambda r: r["Qty"] * (1 if r["Form"] == "Single" else 2),
            axis=1
        )

        summary = makeup_df.groupby(
            ["SKU", "Leaf", "Thickness", "Height", "Width"]
        )["Total Leafs"].sum().reset_index()

        st.dataframe(summary)

        # FULL BREAKDOWN
        st.subheader("Full Breakdown")
        st.dataframe(df)
# =============================================================
# TAB 5 — QUOTE LOOKUP
# =============================================================
tab5 = st.tabs(["Estimator", "Quote Table", "Settings", "Production", "Quote Lookup"])[4]

with tab5:
    st.header("Quote Lookup")

    qnums = get_existing_q_numbers()

    if not qnums:
        st.info("No saved quotes yet.")
    else:
        q_choice = st.selectbox("Select Quote", qnums)

        if st.button("Load Selected Quote"):
            data = load_quote(q_choice)
            if data:
                raw = data["raw_rows"]
                st.session_state.rows = raw
                st.session_state.cust = data["customer"]
                st.session_state.proj = data["project"]
                st.success(f"Loaded quote {q_choice}")
                st.experimental_rerun()
            else:
                st.error("Could not load quote.")

