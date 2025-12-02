import streamlit as st
import pandas as pd

from core.production_helpers import (
    parse_csv_measurements,
    group_production_rows,
    calc_head_length,
    calc_frame_lengths,
    apply_stock_strategy
)

from ui.production_template import generate_production_template
from pdf.production_pdf import generate_production_pdf


# ===================================================================
# MAIN PRODUCTION TAB
# ===================================================================
def render_production_tab(og_df, settings):

    st.header("🏭 Production")

    # ---------------------------------------------------------------
    # Validate estimator rows (og_df)
    # ---------------------------------------------------------------
    if og_df.empty:
        st.warning("No doors in the quote. Add items first.")
        return

    # ---------------------------------------------------------------
    # Initialise session memory
    # ---------------------------------------------------------------
    if "production_rows" not in st.session_state:
        st.session_state.production_rows = []

    # ---------------------------------------------------------------
    # SELECT QUOTE LINE
    # ---------------------------------------------------------------
    st.subheader("📝 Enter Final Site Measurements")

    line_labels = []
    for idx, row in og_df.iterrows():
        label = (
            f"Line {idx+1}: {row['SKU']} | "
            f"{row['Leaf']} | "
            f"{row['Height']}h x {row['Width']}w | "
            f"{row['Form']}"
        )
        line_labels.append((label, idx))

    selected_label = st.selectbox(
        "Select Quote Line",
        [lbl for lbl, _ in line_labels]
    )

    selected_idx = [i for lbl, i in line_labels if lbl == selected_label][0]
    chosen_row = og_df.loc[selected_idx]

    # Extract jamb thickness from Jamb Type string
    def extract_jamb_thickness(text):
        try:
            for t in str(text).split():
                if "x" in t:
                    return float(t.split("x")[-1])
        except:
            return 0
        return 0

    # ---------------------------------------------------------------
    # MANUAL MEASUREMENT ENTRY
    # ---------------------------------------------------------------
    with st.form("add_measurement_form", clear_on_submit=True):

        undercut = st.number_input("Undercut (mm)", min_value=0, value=10)
        floor = st.number_input("Finished Floor Build-up (mm)", min_value=0, value=0)
        qty = st.number_input("Qty", min_value=1, value=1)

        if st.form_submit_button("Add Measurement"):
            new_row = {
                "QuoteLine": selected_idx,
                "LeafType": chosen_row["Leaf"],
                "LeafHeight": chosen_row["Height"],
                "Width": chosen_row["Width"],
                "Jamb Type": chosen_row["Jamb Type"],
                "JambThickness": extract_jamb_thickness(chosen_row["Jamb Type"]),
                "Form": chosen_row["Form"],
                "Undercut": undercut,
                "FinishedFloorHeight": floor,
                "Qty": qty
            }
            st.session_state.production_rows.append(new_row)
            st.success("Measurement added.")

    # ---------------------------------------------------------------
    # CSV IMPORT
    # ---------------------------------------------------------------
    st.markdown("### 📥 Import Measurements from CSV")
    csv_file = st.file_uploader("Upload CSV", type=["csv"])

    if csv_file:
        try:
            csv_df = pd.read_csv(csv_file)
            parsed = parse_csv_measurements(csv_df)
            st.session_state.production_rows.extend(parsed.to_dict(orient="records"))
            st.success("CSV imported.")
        except Exception as e:
            st.error(f"CSV import failed: {e}")

    # ---------------------------------------------------------------
    # CURRENT MANUAL INPUTS TABLE
    # ---------------------------------------------------------------
    st.markdown("### 📋 Current Production Measurements")

    prod_df = pd.DataFrame(st.session_state.production_rows)
    if prod_df.empty:
        st.info("No measurements added yet.")
        return

    st.dataframe(prod_df)

    del_idx = st.number_input("Delete row index", min_value=0, max_value=len(prod_df)-1)
    if st.button("Delete Selected Row"):
        del st.session_state.production_rows[del_idx]
        st.experimental_rerun()

    # ---------------------------------------------------------------
    # GROUP + FRAME CALCULATIONS
    # ---------------------------------------------------------------
    st.markdown("## 🧮 Production Calculations")

    grouped = group_production_rows(prod_df)

    calc_rows = []
    for _, g in grouped.iterrows():

        final_height = g["FinalHeight"]

        head_mm = calc_head_length(
            width=g["Width"],
            jamb_thickness=g["JambThickness"],
            form=g["Form"]
        )

        leg_mm = final_height

        per_frame_m, total_frame_m, total_stop_m = calc_frame_lengths(
            leg_mm=leg_mm,
            head_mm=head_mm,
            qty=g["Qty"]
        )

        calc_rows.append({
            "QuoteLine": g["QuoteLine"],
            "LeafType": g["LeafType"],
            "LeafHeight": g["LeafHeight"],
            "FinalHeight": final_height,
            "Width": g["Width"],
            "Qty": g["Qty"],
            "JambThickness": g["JambThickness"],
            "Form": g["Form"],
            "Leg (mm)": leg_mm,
            "Head (mm)": head_mm,
            "Frame/door (m)": per_frame_m,
            "Total Frame (m)": total_frame_m,
            "Total Stop (m)": total_stop_m
        })

    calc_df = pd.DataFrame(calc_rows)

    # ---------------------------------------------------------------
    # REBUILD JAMB TYPE + PROFILE FROM ORIGINAL og_df
    # ---------------------------------------------------------------
    calc_df = calc_df.merge(
        og_df[["Jamb Type"]],
        left_on="QuoteLine",
        right_index=True,
        how="left"
    )

    def extract_profile(j):
        return str(j).split()[0]

    calc_df["JambProfile"] = calc_df["Jamb Type"].apply(extract_profile)

    # ---------------------------------------------------------------
    # METRICS
    # ---------------------------------------------------------------
    colA, colB, colC = st.columns(3)

    colA.metric("Total Doors", int(calc_df["Qty"].sum()))
    colB.metric("Total Frame (m)", f"{calc_df['Total Frame (m)'].sum():.2f}")
    colC.metric("Total Stop (m)", f"{calc_df['Total Stop (m)'].sum():.2f}")

    st.divider()

    # ==================================================================
    # CLEAN 5-ITEM BOM SUMMARY
    # ==================================================================
    st.markdown("## 📦 Clean Material List (BOM)")

    # 1. Door blanks
    blanks = {}
    for _, r in og_df.iterrows():
        key = f"{r['Height']}x{r['Width']} {r['Leaf']} {r['Thickness']}mm"
        blanks[key] = blanks.get(key, 0) + r["Qty"]

    blank_df = pd.DataFrame([{"Door Blank": k, "Qty": v} for k, v in blanks.items()])

    # 2. Jambs (by profile, meters)
    jambs = (
        calc_df.groupby("JambProfile")["Total Frame (m)"]
        .sum()
        .reset_index()
        .rename(columns={"Total Frame (m)": "Meters"})
    )

    # 3. Stops (single profile)
    stop_df = pd.DataFrame([{
        "Stop Profile": "26A Stop",
        "Meters": round(calc_df["Total Stop (m)"].sum(), 2)
    }])

    # 4. Hinges
    hinge_total = og_df["Hinges"].sum()
    hinge_df = pd.DataFrame([{
        "Hinge": "Standard Hinges",
        "Qty": int(hinge_total)
    }])

    # 5. Screws
    screw_total = int(hinge_total * 4)

    # DISPLAY
    st.subheader("🚪 Door Blanks")
    st.dataframe(blank_df, use_container_width=True)

    st.subheader("📏 Jambs (Meters)")
    st.dataframe(jambs, use_container_width=True)

    st.subheader("🪵 Stops")
    st.dataframe(stop_df, use_container_width=True)

    st.subheader("🔩 Hinges")
    st.dataframe(hinge_df, use_container_width=True)

    st.subheader("🧷 Screws")
    st.write(f"Total screws needed: **{screw_total}**")

    st.divider()

    # ==================================================================
    # JAMB & STOP ORDER STRATEGY + CUT LISTS
    # ==================================================================
    st.markdown("## 📐 Jamb & Stop Ordering Strategy + Cut Lists")

    colJ, colS = st.columns(2)
    jamb_strategy = colJ.selectbox("Jamb Stock Strategy", ["Mix (5.4 + 2.1)", "Only 5.4", "Only 2.1"])
    stop_strategy = colS.selectbox("Stop Stock Strategy", ["Mix (5.4 + 2.1)", "Only 5.4", "Only 2.1"])

    jamb_mode = jamb_strategy.replace("Mix (5.4 + 2.1)", "Mix")
    stop_mode = stop_strategy.replace("Mix (5.4 + 2.1)", "Mix")

    # ---------- helper: build cut list ----------
    def build_cut_list(piece_lengths_mm, stock_lengths_mm):
        """
        Greedy bin pack:
        - piece_lengths_mm: list of ints (e.g. [2050, 2050, 900, ...])
        - stock_lengths_mm: list of ints (e.g. [5400] or [2100, 5400])
        Returns DataFrame with Stock Length, Cuts, Used, Waste.
        """
        pieces = sorted([int(p) for p in piece_lengths_mm if p > 0], reverse=True)
        stock_lengths_mm = sorted(stock_lengths_mm)

        stocks = []  # each: {"stock_length": int, "cuts": [ints], "used": int}

        for p in pieces:
            placed = False

            # try fit into existing stocks first
            for stc in stocks:
                remaining = stc["stock_length"] - stc["used"]
                if p <= remaining:
                    stc["cuts"].append(p)
                    stc["used"] += p
                    placed = True
                    break

            if not placed:
                # open a new stock length: smallest that fits
                chosen_len = None
                for L in stock_lengths_mm:
                    if p <= L:
                        chosen_len = L
                        break
                if chosen_len is None:
                    chosen_len = max(stock_lengths_mm)

                stocks.append({
                    "stock_length": chosen_len,
                    "cuts": [p],
                    "used": p
                })

        cut_rows = []
        for stc in stocks:
            waste = stc["stock_length"] - stc["used"]
            cut_rows.append({
                "Stock Length (mm)": stc["stock_length"],
                "Cuts (mm)": " + ".join(str(c) for c in stc["cuts"]),
                "Used (mm)": stc["used"],
                "Waste (mm)": waste
            })

        return pd.DataFrame(cut_rows)

    # ---------- JAMB LENGTH BREAKDOWN USING apply_stock_strategy ----------
    st.markdown("### Jamb Length Breakdown (by Profile)")

    jamb_summary2 = []
    for _, r in jambs.iterrows():
        total_m = r["Meters"]
        c54, c21, waste = apply_stock_strategy(total_m, jamb_mode)
        jamb_summary2.append({
            "Jamb Profile": r["JambProfile"],
            "Meters": total_m,
            "5.4m Qty": c54,
            "2.1m Qty": c21,
            "Waste (m)": waste
        })
    jamb_summary_df = pd.DataFrame(jamb_summary2)
    st.dataframe(jamb_summary_df, use_container_width=True)

    # ---------- JAMB CUT LISTS ----------
    st.markdown("### Jamb Cut Lists (per Profile)")

    for prof, grp in calc_df.groupby("JambProfile"):
        pieces = []
        for _, row in grp.iterrows():
            q = int(row["Qty"])
            leg = int(row["Leg (mm)"])
            head = int(row["Head (mm)"])
            # 2 legs + 1 head per door
            pieces.extend([leg] * 2 * q)
            pieces.extend([head] * 1 * q)

        if jamb_mode == "Only 5.4":
            stock_lengths = [5400]
        elif jamb_mode == "Only 2.1":
            stock_lengths = [2100]
        else:  # Mix
            stock_lengths = [2100, 5400]

        cut_df = build_cut_list(pieces, stock_lengths)

        st.markdown(f"#### {prof}")
        st.dataframe(cut_df, use_container_width=True)

    # ---------- STOP CUT LIST ----------
    st.markdown("### Stop Cut List")

    stop_pieces = []
    for _, row in calc_df.iterrows():
        q = int(row["Qty"])
        leg = int(row["Leg (mm)"])
        head = int(row["Head (mm)"])
        stop_pieces.extend([leg] * 2 * q)
        stop_pieces.extend([head] * 1 * q)

    if stop_mode == "Only 5.4":
        stop_stock_lengths = [5400]
    elif stop_mode == "Only 2.1":
        stop_stock_lengths = [2100]
    else:
        stop_stock_lengths = [2100, 5400]

    stop_cut_df = build_cut_list(stop_pieces, stop_stock_lengths)
    st.dataframe(stop_cut_df, use_container_width=True)

    st.divider()

    # ---------------------------------------------------------------
    # EXPORT XLSX
    # ---------------------------------------------------------------
    st.markdown("## 📤 Export XLSX Measurement Template")

    template = generate_production_template(
        df_quote=og_df,
        client=st.session_state.cust,
        project=st.session_state.proj,
        quote_number=settings.get("last_quote", "Q-XXXX")
    )

    st.download_button(
        "Download XLSX Template",
        data=template,
        file_name="HDL_Measurement_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()

    # ---------------------------------------------------------------
    # EXPORT PDF
    # ---------------------------------------------------------------
    st.markdown("## 📄 Export Production PDF")

    pdf = generate_production_pdf(
        data=calc_df,
        jamb_summary=jamb_summary_df,
        stop_summary=stop_df
    )

    st.download_button(
        "Download Production PDF",
        data=pdf,
        file_name="HDL_Production_Report.pdf",
        mime="application/pdf"
    )
