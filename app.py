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
tabs = st.tabs(["Estimator + Quote Table", "Production", "Settings", "Quote Lookup"])

# -------------------------------------------------------------
# SUPER TAB — ESTIMATOR + LIVE QUOTE SUMMARY
# -------------------------------------------------------------
with tabs[0]:
    st.header("Estimator + Live Quote Summary")

    # =========================================================
    # A. CLIENT DETAILS
    # =========================================================
    with st.expander("Client Details", expanded=True):
        st.session_state.cust = st.text_input("Customer Name", value=st.session_state.cust)
        st.session_state.proj = st.text_input("Project Name", value=st.session_state.proj)


    # =========================================================
    # B. ADD DOOR LINE (with POA handling)
    # =========================================================
    st.subheader("Add Door Line")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        heights = ["1980", "2200", "2400"]
        widths = ["410", "460", "510", "560", "610", "660", "710", "760", "810", "860", "910", "960"]

        leaf_type = st.selectbox("Leaf Type", list(S["door_leaf_prices"].keys()))
        thickness = st.selectbox("Thickness", ["35mm", "38mm"])
        jamb = st.selectbox("Jamb Type", list(S["frame_prices"].keys()))

    with col_right:
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


    # =========================================================
    # ADD LINE BUTTON + POA LOGIC (BULLETPROOF)
    # =========================================================
    if st.button("Add Line"):

        # Unique POA key
        poa_key = f"poa_{leaf_type}_{height}_{width}_{thickness}"

        # Try normal price
        leaf_cost = leaf_price(S["door_leaf_prices"][leaf_type], height, width, thickness)

        # -------------------------
        # PHASE 1 - First POA trigger
        # -------------------------
        if leaf_cost is None and poa_key not in st.session_state:
            st.warning(f"❗ This leaf {leaf_type} {height}x{width} ({thickness}) has NO price. Enter POA value.")
            st.session_state[poa_key] = 0.0
            st.stop()

        # -------------------------
        # PHASE 2 - Show POA input
        # -------------------------
        if leaf_cost is None:
            user_poa = st.number_input(
                f"Enter POA price for {leaf_type} {height}x{width} ({thickness})",
                min_value=0.0,
                key=poa_key
            )

            if user_poa == 0:
                st.stop()

            leaf_cost = user_poa
            del st.session_state[poa_key]  # reset state

        # =========================================================
        # COST CALCULATIONS
        # =========================================================
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
            "Head Length (mm)": head_mm,
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


    # =========================================================
    # C. SUMMARY TILES
    # =========================================================
    if st.session_state.rows:
        df = pd.DataFrame(st.session_state.rows)

        # Markup input (global)
        mk = st.number_input("Markup %", value=25)

        # Calculate sell + margin
        df["Sell"] = df["Total Cost"] * (1 + mk / 100)
        df["Margin %"] = (df["Sell"] - df["Total Cost"]) / df["Sell"] * 100

        total_lines = len(df)
        total_qty = df["Qty"].sum()
        total_cost = df["Total Cost"].sum()
        total_sell = df["Sell"].sum()
        overall_margin = (total_sell - total_cost) / total_sell * 100 if total_sell > 0 else 0

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Lines", total_lines)
        c2.metric("Total Qty", int(total_qty))
        c3.metric("Total Cost", f"${total_cost:,.2f}")
        c4.metric("Total Sell", f"${total_sell:,.2f}")
        c5.metric("Margin %", f"{overall_margin:.1f}%")


        # =====================================================
        # D. MAIN SUMMARY TABLE
        # =====================================================
        st.subheader("Quote Summary (Clean View)")

        summary_df = df[[
            "SKU",
            "Description",
            "Qty",
            "Total Cost",
            "Sell",
            "Margin %"
        ]]

        st.dataframe(summary_df, height=300)


        # =====================================================
        # FULL BREAKDOWN TABLE EXPANDER
        # =====================================================
        with st.expander("Full Breakdown (Detailed Costs)", expanded=False):
            st.dataframe(df, height=400)


        # =====================================================
        # SAVE QUOTE + EXPORT
        # =====================================================
        qnum = st.text_input("Quote Number", value=suggest_next_q())

        if st.button("Save Quote 💾"):
            save_quote(
                qnum,
                st.session_state.cust,
                st.session_state.proj,
                df.to_dict(orient="records"),
                df.to_dict(orient="records"),   # recalculated rows identical here
                S
            )
            st.success(f"Quote {qnum} saved!")

        st.download_button("Download CSV", df.to_csv(index=False), "quote.csv")


    # =========================================================
    # RESET BUTTON
    # =========================================================
    if st.button("Reset All ❌"):
        st.session_state.rows = []
        st.session_state.cust = ""
        st.session_state.proj = ""
        st.success("Reset complete.")

# =============================================================
# MODULE 2 — PRODUCTION INPUT UI
# =============================================================

import pandas as pd
import streamlit as st
from core.production_helpers import parse_csv_measurements


# Initialise production rows container
if "production_rows" not in st.session_state:
    st.session_state.production_rows = []


st.subheader("Production Measurements")

st.info("Enter final site measurements for each quoted door line. "
        "Production height = leaf height + 3mm + undercut + finished floor height.")


# -------------------------------------------------------------
# 1. SELECT QUOTE LINE
# -------------------------------------------------------------

df_quote = pd.DataFrame(st.session_state.rows)

if df_quote.empty:
    st.warning("No doors in this quote. Add some items first.")
    st.stop()

# Build dropdown list
quote_options = []
for idx, row in df_quote.iterrows():
    label = f"Line {idx+1}: {row['SKU']} | {row['Leaf']} | {row['Height']}h x {row['Width']}w | {row['Form']}"
    quote_options.append((label, idx))

selected_label = st.selectbox(
    "Select Quote Line to Add Measurements",
    [label for label, idx in quote_options]
)

# Get chosen index
chosen_idx = [idx for label, idx in quote_options if label == selected_label][0]
quote_row = df_quote.loc[chosen_idx]


# -------------------------------------------------------------
# 2. PRODUCTION INPUT FORM
# -------------------------------------------------------------

st.markdown("### Add Measurement for Selected Line")

with st.form("add_measurement_form", clear_on_submit=True):

    undercut = st.number_input("Undercut (mm)", min_value=0, value=10)
    finished_floor_height = st.number_input("Finished Floor Build-up (mm)", min_value=0, value=0)
    qty = st.number_input("Qty", min_value=1, value=1)

    submitted = st.form_submit_button("Add Measurement")

    if submitted:

        # Build row for production data
        new_row = {
            "QuoteLine": chosen_idx,
            "LeafType": quote_row["Leaf"],
            "LeafHeight": quote_row["Height"],
            "Width": quote_row["Width"],
            "JambThickness": float(str(quote_row["Jamb Type"]).split()[-1]),  # assumes "US14 92x18" -> 18
            "Form": quote_row["Form"],
            "Undercut": undercut,
            "FinishedFloorHeight": finished_floor_height,
            "Qty": qty
        }

        st.session_state.production_rows.append(new_row)
        st.success("Measurement added.")


# -------------------------------------------------------------
# 3. CSV IMPORTER
# -------------------------------------------------------------

st.markdown("### Import Measurements from CSV")

csv_file = st.file_uploader("Upload CSV", type=["csv"])

if csv_file:
    try:
        csv_df = pd.read_csv(csv_file)
        parsed = parse_csv_measurements(csv_df)
        st.session_state.production_rows.extend(parsed.to_dict(orient="records"))
        st.success("CSV measurements imported.")
    except Exception as e:
        st.error(f"CSV import failed: {e}")


# -------------------------------------------------------------
# 4. EDITABLE TABLE OF MEASUREMENTS
# -------------------------------------------------------------

st.markdown("### Current Production Measurements")

prod_df = pd.DataFrame(st.session_state.production_rows)

if not prod_df.empty:
    st.dataframe(prod_df)

    # Delete row
    del_index = st.number_input("Delete row index", min_value=0,
                                max_value=len(prod_df)-1, step=1)
    if st.button("Delete Selected Measurement"):
        del st.session_state.production_rows[del_index]
        st.experimental_rerun()
else:
    st.info("No production measurements added yet.")
# =============================================================
# MODULE 3 — PRODUCTION GROUPING + SUMMARY CALCULATIONS
# =============================================================

from core.production_helpers import (
    group_production_rows,
    calc_head_length,
    calc_frame_lengths
)

st.markdown("## Production Summary & Calculations")

if not st.session_state.production_rows:
    st.info("No production measurements added yet.")
    st.stop()

prod_df = pd.DataFrame(st.session_state.production_rows)

# ---------------------------
# GROUP BY FINAL HEIGHT + LEAF TYPE
# ---------------------------
grouped = group_production_rows(prod_df)

# Calculate leg, head, frame, stops
calc_rows = []

for _, r in grouped.iterrows():

    # Final Height
    final_height = r["FinalHeight"]

    # Head Length using custom rule
    head_mm = calc_head_length(
        width=r["Width"],
        jamb_thickness=r["JambThickness"],
        form=r["Form"]
    )

    # Leg Length
    leg_mm = final_height

    # Frame + Stop lengths
    frame_per_door_m, total_frame_m, total_stop_m = calc_frame_lengths(
        leg_mm=leg_mm,
        head_mm=head_mm,
        qty=r["Qty"]
    )

    calc_rows.append({
        "QuoteLine": r["QuoteLine"],
        "LeafType": r["LeafType"],
        "LeafHeight": r["LeafHeight"],
        "FinalHeight": final_height,
        "Width": r["Width"],
        "JambThickness": r["JambThickness"],
        "Form": r["Form"],
        "Qty": r["Qty"],
        "Leg (mm)": leg_mm,
        "Head (mm)": head_mm,
        "Frame/door (m)": frame_per_door_m,
        "Total Frame (m)": total_frame_m,
        "Total Stop (m)": total_stop_m
    })

calc_df = pd.DataFrame(calc_rows)

# ---------------------------
# STORE FOR LATER MODULES
# ---------------------------
st.session_state.calc_df = calc_df

# ---------------------------
# SUMMARY METRICS
# ---------------------------

total_doors = calc_df["Qty"].sum()
total_groups = len(calc_df)
total_frame_m = calc_df["Total Frame (m)"].sum()
total_stop_m = calc_df["Total Stop (m)"].sum()

# Hinges + screws from quoted rows
original_df = pd.DataFrame(st.session_state.rows)
total_hinges = int(original_df["Hinges"].sum())
total_screws = int(original_df["Screws"].sum())

# Display summary tiles
colA, colB, colC = st.columns(3)
with colA:
    st.metric("Total Doors", total_doors)
    st.metric("Total Groups", total_groups)
with colB:
    st.metric("Total Frame (m)", f"{total_frame_m:.2f}")
    st.metric("Total Stop (m)", f"{total_stop_m:.2f}")
with colC:
    st.metric("Total Hinges", total_hinges)
    st.metric("Total Screws", total_screws)

st.divider()

st.markdown("### Grouped Production Data")
st.dataframe(calc_df, use_container_width=True)
# =============================================================
# MODULE 4 — JAMB + STOP STOCK STRATEGY
# =============================================================

from core.production_helpers import apply_stock_strategy

st.markdown("## Stock Ordering Strategy")

# -------------------------------
# 1. STOCK SELECTION CONTROLS
# -------------------------------
colJ, colS = st.columns(2)

with colJ:
    jamb_strategy = st.selectbox(
        "Jamb Stock Strategy",
        ["Mix (5.4 + 2.1)", "Only 5.4", "Only 2.1"],
        index=0
    )

with colS:
    stop_strategy = st.selectbox(
        "Stop Stock Strategy",
        ["Mix (5.4 + 2.1)", "Only 5.4", "Only 2.1"],
        index=0
    )

# Normalize strategy names for helper function
jamb_strat = jamb_strategy.replace("Mix (5.4 + 2.1)", "Mix")
stop_strat = stop_strategy.replace("Mix (5.4 + 2.1)", "Mix")


# -------------------------------------------------------------
# 2. APPLY JAMB ORDERING BY JAMB TYPE
# -------------------------------------------------------------
st.markdown("### Jamb Ordering Summary")

calc_df = st.session_state.calc_df

# Group by jamb through original quote rows
og_df = pd.DataFrame(st.session_state.rows)

# Merge jamb type into calc_df
calc_df = calc_df.merge(
    og_df[["SKU", "Jamb Type"]],
    left_on="QuoteLine",
    right_index=True,
    how="left"
)

# Extract jamb profile code + thickness
def extract_jamb_profile(jamb_str):
    return jamb_str.split()[0]  # e.g., "US14"

def extract_jamb_thickness(jamb_str):
    try:
        return float(jamb_str.split()[-1])  # e.g., 18 from "US14 92x18"
    except:
        return 0

calc_df["JambProfile"] = calc_df["Jamb Type"].apply(extract_jamb_profile)
calc_df["JambThickness"] = calc_df["Jamb Type"].apply(extract_jamb_thickness)


# Calculate total frame per jamb profile
jamb_summary_rows = []

for jamb, grp in calc_df.groupby("JambProfile"):

    total_m = grp["Total Frame (m)"].sum()

    # Apply chosen jamb stock strategy
    c54, c21, waste = apply_stock_strategy(total_m, jamb_strat)

    jamb_summary_rows.append({
        "Jamb Profile": jamb,
        "Total Frame (m)": total_m,
        "5.4m Qty": c54,
        "2.1m Qty": c21,
        "Waste (m)": waste
    })

jamb_summary_df = pd.DataFrame(jamb_summary_rows)

st.dataframe(jamb_summary_df, use_container_width=True)

st.session_state.jamb_summary = jamb_summary_df


# -------------------------------------------------------------
# 3. DETAILED JAMB CUT TABLES
# -------------------------------------------------------------
with st.expander("Detailed Jamb Cut Breakdown"):

    for jamb, grp in calc_df.groupby("JambProfile"):

        st.markdown(f"#### {jamb}")

        detail_rows = []

        for _, r in grp.iterrows():
            detail_rows.append({
                "Final Height (mm)": r["FinalHeight"],
                "Leg Length (mm)": r["Leg (mm)"],
                "Head Length (mm)": r["Head (mm)"],
                "Qty": r["Qty"],
                "Frame/door (m)": r["Frame/door (m)"],
                "Total Frame (m)": r["Total Frame (m)"]
            })

        st.dataframe(pd.DataFrame(detail_rows), use_container_width=True)


# -------------------------------------------------------------
# 4. STOP ORDERING SUMMARY
# -------------------------------------------------------------
st.markdown("### Stop Ordering Summary")

total_stop_m = calc_df["Total Stop (m)"].sum()

s54, s21, swaste = apply_stock_strategy(total_stop_m, stop_strat)

stop_summary_df = pd.DataFrame([{
    "Total Stop (m)": total_stop_m,
    "5.4m Qty": s54,
    "2.1m Qty": s21,
    "Waste (m)": swaste
}])

st.dataframe(stop_summary_df, use_container_width=True)
st.session_state.stop_summary = stop_summary_df

st.divider()
# =============================================================
# MODULE 5 — OUTPUT TABLES (CUT LIST, GROUPS, BREAKDOWNS)
# =============================================================

st.markdown("## Production Output Tables")


# -------------------------------------------------------------
# 1. GROUPED SIZE OUTPUT
# -------------------------------------------------------------
st.markdown("### Grouped Sizes (By Final Height + Leaf Type)")

group_table = calc_df[[
    "LeafType",
    "FinalHeight",
    "Qty",
    "Width",
    "JambThickness",
    "Form"
]].rename(columns={
    "LeafType": "Leaf Type",
    "FinalHeight": "Final Height (mm)",
    "Qty": "Qty",
    "Width": "Width (mm)",
    "JambThickness": "Jamb Thickness (mm)",
    "Form": "Form"
})

st.dataframe(group_table, use_container_width=True)

st.divider()


# -------------------------------------------------------------
# 2. CUT LIST
# -------------------------------------------------------------
st.markdown("### Cut List (Legs + Heads + Totals)")

cutlist_table = calc_df[[
    "LeafType",
    "FinalHeight",
    "Leg (mm)",
    "Head (mm)",
    "Qty",
    "Frame/door (m)",
    "Total Frame (m)"
]].rename(columns={
    "LeafType": "Leaf Type",
    "FinalHeight": "Final Height (mm)",
    "Leg (mm)": "Leg (mm)",
    "Head (mm)": "Head (mm)",
    "Qty": "Qty",
    "Frame/door (m)": "Frame per Door (m)",
    "Total Frame (m)": "Total Frame (m)"
})

st.dataframe(cutlist_table, use_container_width=True)

st.divider()


# -------------------------------------------------------------
# 3. JAMB STOCK SUMMARY (FROM MODULE 4)
# -------------------------------------------------------------
st.markdown("### Jamb Stock Summary")

if "jamb_summary" in st.session_state:
    st.dataframe(st.session_state.jamb_summary, use_container_width=True)
else:
    st.warning("No jamb summary available.")


# -------------------------------------------------------------
# 4. STOP STOCK SUMMARY (FROM MODULE 4)
# -------------------------------------------------------------
st.markdown("### Stop Stock Summary")

if "stop_summary" in st.session_state:
    st.dataframe(st.session_state.stop_summary, use_container_width=True)
else:
    st.warning("No stop summary available.")

st.divider()


# -------------------------------------------------------------
# 5. FULL PRODUCTION BREAKDOWN TABLE
# -------------------------------------------------------------
st.markdown("### Full Production Breakdown")

full_breakdown = calc_df[[
    "QuoteLine",
    "LeafType",
    "LeafHeight",
    "FinalHeight",
    "Width",
    "JambThickness",
    "Form",
    "Qty",
    "Leg (mm)",
    "Head (mm)",
    "Frame/door (m)",
    "Total Frame (m)",
    "Total Stop (m)"
]].rename(columns={
    "QuoteLine": "Quote Line",
    "LeafType": "Leaf Type",
    "LeafHeight": "Leaf Height (mm)",
    "FinalHeight": "Final Height (mm)",
    "Width": "Width (mm)",
    "JambThickness": "Jamb Thickness (mm)",
    "Form": "Form",
    "Qty": "Qty",
    "Leg (mm)": "Leg (mm)",
    "Head (mm)": "Head (mm)",
    "Frame/door (m)": "Frame per Door (m)",
    "Total Frame (m)": "Total Frame (m)",
    "Total Stop (m)": "Total Stop (m)"
})

st.dataframe(full_breakdown, use_container_width=True)

st.session_state.full_breakdown = full_breakdown

# ============================================================
# PDF EXPORT HELPER (HTML → PDF)
# ============================================================

import pdfkit
from jinja2 import Template

def generate_production_pdf(data, jamb_summary, stop_summary):
    """
    Builds an HDL-branded PDF from calculated production data.
    """

    html_template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header {
                background-color: #FF6600;
                color: white;
                padding: 15px;
                font-size: 24px;
                font-weight: bold;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th {
                background-color: #FF6600;
                color: white;
                padding: 8px;
                border: 1px solid #ddd;
            }
            td {
                padding: 8px;
                border: 1px solid #ccc;
            }
            h2 { margin-top: 40px; }
        </style>
    </head>
    <body>

        <div class="header">HDL Production Report</div>

        <h2>Grouped Production Data</h2>
        <table>
            <tr>
                {% for col in data.columns %}
                <th>{{ col }}</th>
                {% endfor %}
            </tr>
            {% for _, row in data.iterrows() %}
            <tr>
                {% for col in data.columns %}
                <td>{{ row[col] }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </table>

        <h2>Jamb Stock Summary</h2>
        <table>
            <tr>
                {% for col in jamb_summary.columns %}
                <th>{{ col }}</th>
                {% endfor %}
            </tr>
            {% for _, row in jamb_summary.iterrows() %}
            <tr>
                {% for col in jamb_summary.columns %}
                <td>{{ row[col] }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </table>

        <h2>Stop Stock Summary</h2>
        <table>
            <tr>
                {% for col in stop_summary.columns %}
                <th>{{ col }}</th>
                {% endfor %}
            </tr>
            {% for _, row in stop_summary.iterrows() %}
            <tr>
                {% for col in stop_summary.columns %}
                <td>{{ row[col] }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </table>

    </body>
    </html>
    """

    template = Template(html_template)
    html = template.render(
        data=data,
        jamb_summary=jamb_summary,
        stop_summary=stop_summary
    )

    pdf = pdfkit.from_string(html, False)
    return pdf
# =============================================================
# MODULE 6 — PDF EXPORT BUTTON
# =============================================================

st.markdown("## Export Production Report")

if st.button("Download Production PDF"):
    pdf = generate_production_pdf(
        st.session_state.full_breakdown,
        st.session_state.jamb_summary,
        st.session_state.stop_summary
    )

    st.download_button(
        label="Download HDL Production Report (PDF)",
        data=pdf,
        file_name="HDL_Production_Report.pdf",
        mime="application/pdf"
    )







# -------------------------------------------------------------
# TAB 4 — SETTINGS
# -------------------------------------------------------------
with tabs[2]:
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
with tabs[3]:
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
