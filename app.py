import streamlit as st
import pandas as pd
import math
import os

# LOCAL MODULES
from core.settings import get_default_settings
from core.pricing import leaf_price, frame_cost_and_pieces, stop_cost
from core.sku import create_sku
from core.stock import greedy_stock
from utils.loaders import load_hinge_sheet

from core.save_load import (
    save_quote,
    load_quote,
    suggest_next_q,
    get_existing_q_numbers
)

# =============================================================
# PAGE CONFIG
# =============================================================
st.set_page_config(page_title="Dave’s Door Pricer", layout="wide")
st.title("🚪 Dave's Door Intelligence Estimator Bro")

# =============================================================
# SESSION INITIALISATION (BEFORE ANY UI)
# =============================================================
if "settings" not in st.session_state:
    st.session_state.settings = get_default_settings()

if "cust" not in st.session_state:
    st.session_state.cust = ""

if "proj" not in st.session_state:
    st.session_state.proj = ""

if "rows" not in st.session_state:
    st.session_state.rows = []

if "pending_load" not in st.session_state:
    st.session_state.pending_load = None


# =============================================================
# APPLY PENDING QUOTE LOAD BEFORE ANY WIDGETS EXIST
# =============================================================
if st.session_state.pending_load is not None:
    data = st.session_state.pending_load
    st.session_state.cust = data["customer"]
    st.session_state.proj = data["project"]
    st.session_state.rows = data["raw_rows"]
    st.session_state.pending_load = None


# =============================================================
# LOAD HINGE SHEET
# =============================================================
HINGE_FOLDER = "data"
HINGE_DF = load_hinge_sheet(HINGE_FOLDER)

if HINGE_DF is None:
    st.error("No hinge sheet found in /data. Upload hinge_data.xlsx.")
    st.stop()

S = st.session_state.settings


# =============================================================
# TABS
# =============================================================
tabs = st.tabs(["Estimator", "Quote Table", "Production", "Settings", "Quote Lookup"])

# -------------------------------------------------------------
# TAB 1 — ESTIMATOR
# -------------------------------------------------------------
with tabs[0]:
    st.header("Estimator")

    # ---------------------
    # Client Details
    # ---------------------
    with st.expander("Client Details", expanded=True):
        st.session_state.cust = st.text_input("Customer Name", value=st.session_state.cust)
        st.session_state.proj = st.text_input("Project Name", value=st.session_state.proj)

    # ---------------------
    # Item Input
    # ---------------------
    with st.expander("Add Door Line", expanded=True):

        heights = ["1980", "2200", "2400"]
        widths = ["410", "460", "510", "560", "610", "660", "710", "760", "810", "860", "910", "960"]

        leaf_type = st.selectbox("Leaf Type", list(S["door_leaf_prices"].keys()))
        thickness = st.selectbox("Thickness", ["35mm", "38mm"])
        jamb = st.selectbox("Jamb Type", list(S["frame_prices"].keys()))
        height = int(st.selectbox("Height", heights))
        width = int(st.selectbox("Width", widths))
        form = st.selectbox("Single / Double", ["Single", "Double"])
        qty = st.number_input("Qty", min_value=1, value=1)

        # Hinge lookup
        hm = HINGE_DF[(HINGE_DF["Height"] == height) & (HINGE_DF["Width"] == width)]
        if not hm.empty:
            hinges = int(hm.iloc[0]["Hinges"])
            screws = int(hm.iloc[0]["Screws"])
        else:
            hinges = S["hinges_per_door"]
            screws = S["hinges_per_door"] * S["hinge_screws"]

        prefix = S["prefix_map"][leaf_type]
        sku = create_sku(prefix, thickness, height, width, jamb, form)

        desc_row = HINGE_DF[HINGE_DF["Code"] == sku]
        desc = desc_row.iloc[0]["Description"] if not desc_row.empty else "DESCRIPTION NOT FOUND"

        # Add Button
        if st.button("Add Line"):
            leaf_cost = leaf_price(S["door_leaf_prices"][leaf_type], height, width, thickness)

            if leaf_cost is None:
                st.warning("❗ POA – This leaf size not found. Add manually in Settings.")
                st.stop()

            leaf_mult = 1 if form == "Single" else 2

            frame_cost_val, frame_m, leg_mm, head_mm = frame_cost_and_pieces(
                height, width, jamb, form,
                S["frame_prices"], S["minimum_frame_charge"]
            )

            stop_cost_val = stop_cost(
                frame_m,
                S["frame_prices"]["26A 30x10 Door Stop"],
                S["minimum_frame_charge"]
            )

            labour = S["labour_single"] if form == "Single" else S["labour_double"]

            row = {
                "Customer": st.session_state.cust,
                "Project": st.session_state.proj,
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
            st.success("Door line added!")

    # ---------------------
    # Current Items
    # ---------------------
    if st.session_state.rows:
        st.subheader("Current Items")
        st.dataframe(pd.DataFrame(st.session_state.rows))

    if st.button("Reset All ❌"):
        st.session_state.rows = []
        st.session_state.cust = ""
        st.session_state.proj = ""
        st.success("Reset complete.")


# -------------------------------------------------------------
# TAB 2 — QUOTE TABLE
# -------------------------------------------------------------
with tabs[1]:
    st.header("Quote Summary")

    if not st.session_state.rows:
        st.info("Add doors first.")
        st.stop()

    df = pd.DataFrame(st.session_state.rows)

    st.subheader(f"Customer: {st.session_state.cust}")
    st.subheader(f"Project: {st.session_state.proj}")

    qnum = st.text_input("Quote Number", value=suggest_next_q())

    mk = st.number_input("Markup %", value=25)

    new_rows = []
    for _, r in df.iterrows():
        leaf_mult = 1 if r["Form"] == "Single" else 2

        frame_cost_val, frame_m, leg_mm, head_mm = frame_cost_and_pieces(
            r["Height"], r["Width"], r["Jamb Type"], r["Form"],
            S["frame_prices"], S["minimum_frame_charge"]
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
            r["Leaf Cost"] + frame_cost_val + stop_cost_val +
            labour + hinge_cost + screw_cost
        )

        new_rows.append({
            **r,
            "Frame Cost": frame_cost_val,
            "Stop Cost": stop_cost_val,
            "Labour": labour,
            "Hinge Cost": hinge_cost,
            "Screw Cost": screw_cost,
            "Total Cost": total,
            "Sell": total * (1 + mk / 100),
        })

    final_df = pd.DataFrame(new_rows)
    st.dataframe(final_df)

    if st.button("Save Quote 💾"):
        save_quote(
            qnum,
            st.session_state.cust,
            st.session_state.proj,
            df.to_dict(orient="records"),
            final_df.to_dict(orient="records"),
            S
        )
        st.success(f"Quote {qnum} saved!")

    st.download_button("Download CSV", final_df.to_csv(index=False), "quote.csv")


# -------------------------------------------------------------
# TAB 3 — PRODUCTION
# -------------------------------------------------------------
with tabs[2]:
    st.header("Production")

    if not st.session_state.rows:
        st.info("Add some doors first.")
        st.stop()

    df = pd.DataFrame(st.session_state.rows)

    df["Leafs to Order"] = df.apply(lambda r: r["Qty"] * (1 if r["Form"] == "Single" else 2), axis=1)
    df["Total Hinges"] = df["Qty"] * df["Hinges"]
    df["Total Screws"] = df["Qty"] * df["Screws"]
    df["Total Frame (m)"] = df["Qty"] * df["Frame Length (m)"]
    df["Total Stop (m)"] = df["Total Frame (m)"]

    st.subheader("Totals")
    st.write(f"Leafs: **{df['Leafs to Order'].sum()}**")
    st.write(f"Hinges: **{df['Total Hinges'].sum()}**")
    st.write(f"Screws: **{df['Total Screws'].sum()}**")

    st.subheader("Frame by Jamb Type")
    for jt, group in df.groupby("Jamb Type"):
        total_m = group["Total Frame (m)"].sum()
        st.write(f"### {jt}: {total_m:.2f} m")
        st.write("---")

    st.subheader("Full Breakdown")
    st.dataframe(df)


# -------------------------------------------------------------
# TAB 4 — SETTINGS
# -------------------------------------------------------------
with tabs[3]:
    st.header("Settings")

    if st.button("Reset Settings to Default"):
        st.session_state.settings = get_default_settings()
        st.success("Defaults restored.")
        st.rerun()

    st.subheader("Frame Prices")
    for k in S["frame_prices"]:
        S["frame_prices"][k] = st.number_input(k, value=S["frame_prices"][k])

    st.subheader("Labour Costs")
    S["labour_single"] = st.number_input("Single Labour", value=S["labour_single"])
    S["labour_double"] = st.number_input("Double Labour", value=S["labour_double"])

    st.subheader("Hardware Costs")
    S["hinge_price"] = st.number_input("Hinge Price", value=S["hinge_price"])
    S["hinges_per_door"] = st.number_input("Hinges per Door", value=S["hinges_per_door"])
    S["screw_cost"] = st.number_input("Screw Cost", value=S["screw_cost"])
    S["hinge_screws"] = st.number_input("Screws per Hinge", value=S["hinge_screws"])

    st.subheader("Minimum Frame Charge")
    S["minimum_frame_charge"] = st.number_input("Minimum Charge", value=S["minimum_frame_charge"])


# -------------------------------------------------------------
# TAB 5 — QUOTE LOOKUP
# -------------------------------------------------------------
with tabs[4]:
    st.header("Quote Lookup")

    qnums = get_existing_q_numbers()

    if not qnums:
        st.info("No quotes saved yet.")
    else:
        q_select = st.selectbox("Select Quote", qnums)

        if st.button("Load Quote"):
            data = load_quote(q_select)
            if data:
                st.session_state.pending_load = data
                st.success(f"Loaded {q_select}")
                st.rerun()
            else:
                st.error("Could not load quote.")
