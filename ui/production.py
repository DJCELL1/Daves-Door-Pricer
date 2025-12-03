import streamlit as st
import pandas as pd

from core.production_helpers import (
    calc_head_length,
    calc_frame_lengths,
    apply_stock_strategy
)

from ui.production_template import generate_production_template
from pdf.production_pdf import generate_production_pdf
from pdf.door_order_import import read_order_form


# ===================================================================
# HELPERS
# ===================================================================

def expand_quote_rows(og_df):
    """Build rows for measurement editor."""
    doors = []
    door_counter = 1

    for idx, row in og_df.iterrows():
        sets = int(row["Qty"])
        for _ in range(sets):
            doors.append({
                "Door #": str(door_counter),
                "QuoteLine": idx,
                "SKU": row["SKU"],
                "LeafType": row["Leaf Type"],
                "Height": row["Height"],
                "Width": row["Width"],
                "JambType": row["Jamb Type"],
                "Form": row["Form"],
                "Undercut": 20,
                "FinishedFloorHeight": 0,
                "Measured": False,
            })
            door_counter += 1

    return pd.DataFrame(doors)


def import_xlsx_measurements(xlsx):
    """Imports XLSX from measurement template."""
    try:
        df = pd.read_excel(xlsx)
        df.columns = [c.strip() for c in df.columns]

        required = ["Door Number", "Undercut (mm)", "Finished Floor Height (mm)"]
        for r in required:
            if r not in df.columns:
                raise ValueError(f"Missing column: {r}")

        out = pd.DataFrame({
            "Door #": df["Door Number"].astype(str),
            "Undercut": df["Undercut (mm)"],
            "FinishedFloorHeight": df["Finished Floor Height (mm)"],
            "Measured": True
        })

        return out.dropna(subset=["Door #"])

    except Exception as e:
        raise ValueError(f"Import failed: {e}")


def _extract_jamb_thickness(text):
    """Extract the '18' or '30' from 92x18 etc."""
    try:
        for t in str(text).split():
            if "x" in t:
                return float(t.split("x")[-1])
    except:
        return 18
    return 18


# CLEAN FIXED CUT LIST BUILDER
def build_cut_list(piece_lengths, stock_lengths):
    pieces = sorted([int(x) for x in piece_lengths], reverse=True)
    stocks = sorted(stock_lengths)

    bundles = []

    for p in pieces:
        placed = False

        for b in bundles:
            if p <= (b["stock"] - b["used"]):
                b["cuts"].append(p)
                b["used"] += p
                placed = True
                break

        if not placed:
            chosen = next((s for s in stocks if p <= s), max(stocks))
            bundles.append({
                "stock": chosen,
                "cuts": [p],
                "used": p
            })

    rows = []
    for b in bundles:
        rows.append({
            "Stock Length (mm)": b["stock"],
            "Cuts (mm)": " + ".join(str(c) for c in b["cuts"]),
            "Used (mm)": b["used"],
            "Waste (mm)": b["stock"] - b["used"]
        })

    return pd.DataFrame(rows)   # FIXED


# ===================================================================
# MAIN PRODUCTION TAB
# ===================================================================

def render_production_tab(og_df, settings):

    st.header("🏭 Production")

    if og_df.empty:
        st.warning("No doors in this quote yet.")
        return

    # ============================================================
    # EXPORT TEMPLATE
    # ============================================================

    st.markdown("## 📤 Download XLSX Measurement Template")
    template = generate_production_template(
        df_quote=og_df,
        client=st.session_state.cust,
        project=st.session_state.proj,
        quote_number=settings.get("last_quote", "Q-XXXX"),
    )

    st.download_button(
        "Download XLSX Template",
        data=template,
        file_name="HDL_Measurement_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

    st.divider()

    # ============================================================
    # IMPORT DOOR ORDER FORM
    # ============================================================

    st.subheader("📥 Upload HD Door Order Form (.xlsx)")

    uploaded_form = st.file_uploader("Upload Door Order Form (.xlsx)")

    if uploaded_form:
        try:
            imported_rows = read_order_form(uploaded_form)
            imported_df = pd.DataFrame(imported_rows)

            st.success("Door Order Form imported successfully.")
            st.dataframe(imported_df, use_container_width=True)

            st.session_state.all_doors = imported_df.copy()

        except Exception as e:
            st.error(f"❌ Error reading form: {e}")
            return

    # ============================================================
    # FALLBACK IF NO UPLOAD
    # ============================================================

    if "all_doors" not in st.session_state or st.session_state.all_doors is None:
        st.session_state.all_doors = expand_quote_rows(og_df)

    # ============================================================
    # EDIT DOORS INLINE
    # ============================================================

    st.subheader("🔧 Edit Door Measurements (Per Set)")

    st.session_state.all_doors["Door #"] = st.session_state.all_doors["Door #"].astype(str)

    edited = st.data_editor(
        st.session_state.all_doors,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="door_editor",
        column_config={
            "Door #": st.column_config.TextColumn("Door #"),
            "Measured": st.column_config.CheckboxColumn("Measured"),
        }
    )

    st.session_state.all_doors = edited

    st.divider()

    # ============================================================
    # PRODUCTION CALCULATIONS
    # ============================================================

    st.markdown("## 🧮 Production Calculations")

    calc_rows = []

    for _, r in edited.iterrows():

        final_h = int(r["Height"]) + 3 + int(r["Undercut"]) + int(r["FinishedFloorHeight"])

        head_mm = calc_head_length(
            width=r["Width"],
            jamb_thickness=_extract_jamb_thickness(r["JambType"]),
            form=r["Form"]
        )

        leg_mm = final_h

        per_frame_m, total_frame_m, total_stop_m = calc_frame_lengths(
            leg_mm=leg_mm,
            head_mm=head_mm,
            qty=1
        )

        hinge_qty = int(og_df.loc[r["QuoteLine"]]["Hinges"]) if "QuoteLine" in r else 0

        calc_rows.append({
            "Door #": r["Door #"],
            "QuoteLine": r.get("QuoteLine", 0),
            "LeafType": r["LeafType"],
            "LeafHeight": r["Height"],
            "LeafThickness": og_df.loc[r.get("QuoteLine", 0)]["Thickness"],
            "FinalHeight": final_h,
            "Width": r["Width"],
            "JambType": r["JambType"],
            "Form": r["Form"],
            "Leg (mm)": leg_mm,
            "Head (mm)": head_mm,
            "Total Frame (m)": total_frame_m,
            "Total Stop (m)": total_stop_m,
            "Hinges": hinge_qty,
            "Measured": r["Measured"],
        })

    calc_df = pd.DataFrame(calc_rows)
    st.dataframe(calc_df, use_container_width=True)

    st.divider()

    # ============================================================
    # SUMMARY METRICS
    # ============================================================

    colA, colB, colC, colD = st.columns(4)
    colA.metric("Total Sets", len(calc_df))
    colB.metric("Total Frame (m)", f"{calc_df['Total Frame (m)'].sum():.2f}")
    colC.metric("Total Stop (m)", f"{calc_df['Total Stop (m)'].sum():.2f}")
    colD.metric("Total Hinges", int(calc_df["Hinges"].sum()))

    st.divider()

    # ============================================================
    # BOM — DOOR BLANKS
    # ============================================================

    st.markdown("## 📦 Clean Material List (BOM)")

    blanks = (
        og_df.assign(
            Leaves=og_df.apply(lambda r: 1 if r["Form"] == "Single" else 2, axis=1)
        ).assign(
            Total=lambda r: r["Qty"] * r["Leaves"]
        )
    )

    blanks_df = blanks[["SKU", "Leaf Type", "Height", "Width", "Thickness", "Total"]]
    blanks_df = blanks_df.rename(columns={"Total": "Qty"})

    st.subheader("🚪 Door Blanks")
    st.dataframe(blanks_df, use_container_width=True)

    # ============================================================
    # Jambs
    # ============================================================

    calc_df["JambProfile"] = calc_df["JambType"].apply(lambda j: str(j).split()[0])
    jambs = (
        calc_df.groupby("JambProfile")["Total Frame (m)"]
        .sum()
        .reset_index()
        .rename(columns={"Total Frame (m)": "Meters"})
    )

    st.subheader("📏 Jambs (Meters)")
    st.dataframe(jambs, use_container_width=True)

    # ============================================================
    # Stops
    # ============================================================

    stop_df = pd.DataFrame([{
        "Stop Profile": "26A Stop",
        "Meters": round(calc_df["Total Stop (m)"].sum(), 2)
    }])

    st.subheader("🪵 Stops")
    st.dataframe(stop_df, use_container_width=True)

    st.divider()

    # ============================================================
    # STOCK STRATEGY + CUT LISTS
    # ============================================================

    st.markdown("## 📐 Stock Strategy + Cut Lists")

    colJ, colS = st.columns(2)
    jamb_strategy = colJ.selectbox("Jamb Stock Strategy", ["Mix (5.4 + 2.1)", "Only 5.4", "Only 2.1"])
    stop_strategy = colS.selectbox("Stop Stock Strategy", ["Mix (5.4 + 2.1)", "Only 5.4", "Only 2.1"])

    jamb_mode = jamb_strategy.replace("Mix (5.4 + 2.1)", "Mix")
    stop_mode = stop_strategy.replace("Mix (5.4 + 2.1)", "Mix")

    summary = []
    for _, r in jambs.iterrows():
        total_m = r["Meters"]
        qty54, qty21, waste = apply_stock_strategy(total_m, jamb_mode)
        summary.append({
            "Profile": r["JambProfile"],
            "Meters": total_m,
            "5.4m Qty": qty54,
            "2.1m Qty": qty21,
            "Waste (m)": waste
        })

    summary_df = pd.DataFrame(summary)
    st.dataframe(summary_df, use_container_width=True)

    st.divider()

    # ============================================================
    # BUILD CUT LISTS
    # ============================================================

    cutlists = {}

    for prof, grp in calc_df.groupby("JambProfile"):
        pieces = []
        for _, row in grp.iterrows():
            leg = int(row["Leg (mm)"])
            head = int(row["Head (mm)"])
            pieces.extend([leg] * 2)
            pieces.append(head)

        stock_lengths = (
            [5400] if jamb_mode == "Only 5.4"
            else [2100] if jamb_mode == "Only 2.1"
            else [2100, 5400]
        )

        cutlists[f"Jamb — {prof}"] = build_cut_list(pieces, stock_lengths)

    stop_pieces = []
    for _, row in calc_df.iterrows():
        leg = int(row["Leg (mm)"])
        head = int(row["Head (mm)"])
        stop_pieces.extend([leg] * 2)
        stop_pieces.append(head)

    stop_stock_lengths = (
        [5400] if stop_mode == "Only 5.4"
        else [2100] if stop_mode == "Only 2.1"
        else [2100, 5400]
    )

    cutlists["Stops"] = build_cut_list(stop_pieces, stop_stock_lengths)

    st.subheader("Cut Lists Ready for PDF")

    for title, df in cutlists.items():
        st.write(f"### {title}")
        st.dataframe(df, use_container_width=True)

    st.divider()

    # ============================================================
    # PDF EXPORT
    # ============================================================

    st.markdown("## 📄 Export Production PDF")

    total_hinges = int(calc_df["Hinges"].sum())
    total_screws = total_hinges * 6

    pdf = generate_production_pdf(
        data=calc_df,
        jamb_summary=summary_df,
        stop_summary=stop_df,
        blanks_df=blanks_df,
        hinge_qty=total_hinges,
        screw_qty=total_screws,
        cutlists=cutlists,
        job_name=st.session_state.proj,
        customer=st.session_state.cust,
        qnum=settings.get("last_quote", "Q-XXXX")
    )

    st.download_button(
        "Download Production PDF",
        data=pdf,
        file_name="HDL_Production_Report.pdf",
        mime="application/pdf"
    )
