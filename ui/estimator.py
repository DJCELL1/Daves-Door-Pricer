import streamlit as st
import pandas as pd

from core.pricing import leaf_price, frame_cost_and_pieces, stop_cost
from core.sku import create_sku
from core.save_load import save_quote, suggest_next_q

# NEW IMPORTS FOR DOOR ORDER FORM
from pdf.door_order_export import generate_order_form
from ui.helpers import build_door_order_rows


def render_estimator_tab(HINGE_DF):
    S = st.session_state.settings

    st.header("Estimator + Live Quote Summary")

    # ---------------------------------------------------------
    # CLIENT DETAILS
    # ---------------------------------------------------------
    with st.expander("Client Details", expanded=True):
        st.session_state.cust = st.text_input("Customer Name", value=st.session_state.cust)
        st.session_state.proj = st.text_input("Project Name", value=st.session_state.proj)

    # ---------------------------------------------------------
    # ADD DOOR LINE
    # ---------------------------------------------------------
    st.subheader("Add Door Line")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        heights = ["1980", "2200", "2400"]
        widths = ["410", "460", "510", "560", "610", "660", "710", "760", "810", "860", "910", "960"]

        leaf_type = st.selectbox("Leaf Type (Material)", list(S["door_leaf_prices"].keys()))
        thickness = st.selectbox("Thickness", ["35mm", "38mm"])
        jamb = st.selectbox("Jamb Type", list(S["frame_prices"].keys()))

    with col_right:
        height = int(st.selectbox("Height", heights))
        width = int(st.selectbox("Width", widths))
        form = st.selectbox("Single / Double", ["Single", "Double"])
        qty = st.number_input("Qty (Sets)", min_value=1, value=1)

    # ---------------------------------------------------------
    # DESCRIPTION LOOKUP
    # ---------------------------------------------------------
    prefix = S["prefix_map"][leaf_type]
    sku = create_sku(prefix, thickness, height, width, jamb, form)

    desc_lookup = HINGE_DF[HINGE_DF["Code"] == sku]
    desc = desc_lookup.iloc[0]["Description"] if not desc_lookup.empty else "DESCRIPTION NOT FOUND"

    # ---------------------------------------------------------
    # ADD LINE BUTTON
    # ---------------------------------------------------------
    if st.button("Add Line"):

        # ---------------------------------------------------------
        # LEAF COST LOOKUP (with POA handling)
        # ---------------------------------------------------------
        poa_key = f"poa_{leaf_type}_{height}_{width}_{thickness}"

        leaf_cost_val = leaf_price(S["door_leaf_prices"][leaf_type], height, width, thickness)

        if leaf_cost_val is None and poa_key not in st.session_state:
            st.warning(f"❗ No price for {leaf_type} {height}x{width} {thickness}. Enter POA.")
            st.session_state[poa_key] = 0.0
            st.stop()

        if leaf_cost_val is None:
            user_poa = st.number_input(
                f"Enter POA price for {leaf_type} {height}x{width} {thickness}",
                min_value=0.0,
                key=poa_key
            )
            if user_poa == 0:
                st.stop()
            leaf_cost_val = user_poa
            del st.session_state[poa_key]

        # ---------------------------------------------------------
        # COST CALC BLOCK
        # ---------------------------------------------------------

        # Leaves
        leaves_per_set = 1 if form == "Single" else 2

        # Frame & stop cost
        frame_cost_val, frame_m, leg_mm, head_mm = frame_cost_and_pieces(
            height, width, jamb, form,
            S["frame_prices"], S["minimum_frame_charge"]
        )

        stop_cost_val = stop_cost(
            frame_m,
            S["stop_price"],
            0
        )

        labour = S["labour_single"] if form == "Single" else S["labour_double"]

        # ---------------------------------------------------------
        # UCE — HERE IS THE CLEAN, FINAL HINGE PATCH
        # ---------------------------------------------------------

        hinges_per_leaf = 3         # rule: all standard doors = 3 hinges per leaf
        hinge_count = hinges_per_leaf * leaves_per_set
        screw_count = hinge_count * 6

        hinge_cost_val = hinge_count * S["hinge_price"]
        screw_cost_val = screw_count * S["screw_cost"]

        # ---------------------------------------------------------
        # TOTAL COST CALC
        # ---------------------------------------------------------
        unit_cost = (
            leaf_cost_val * leaves_per_set
            + frame_cost_val
            + stop_cost_val
            + labour
            + hinge_cost_val
            + screw_cost_val
        )

        total_cost = unit_cost * qty

        # ---------------------------------------------------------
        # BUILD ROW
        # ---------------------------------------------------------
        row = {
            "Customer": st.session_state.cust,
            "Project": st.session_state.proj,

            "SKU": sku,
            "Description": desc,

            "Leaf Type": leaf_type,
            "Form": form,
            "Thickness": thickness,
            "Height": height,
            "Width": width,
            "Qty": qty,
            "Jamb Type": jamb,

            "Unit Cost": unit_cost,
            "Total Cost": total_cost,

            "Leaf Cost": leaf_cost_val * leaves_per_set,
            "Frame Cost": frame_cost_val,
            "Stop Cost": stop_cost_val,
            "Labour": labour,

            "Hinges": hinge_count,
            "Hinge Cost": hinge_cost_val,
            "Screws": screw_count,
            "Screw Cost": screw_cost_val,

            "Frame Length (m)": frame_m,
            "Leg Length (mm)": leg_mm,
            "Head Length (mm)": head_mm,
        }

        st.session_state.rows.append(row)
        st.success("Door line added!")

    # ---------------------------------------------------------
    # SUMMARY + COSTING TABLE
    # ---------------------------------------------------------
    if st.session_state.rows:

        df = pd.DataFrame(st.session_state.rows)

        markup = st.number_input("Markup %", value=25)
        df["Sell"] = df["Total Cost"] * (1 + markup / 100)
        df["Margin %"] = ((df["Sell"] - df["Total Cost"]) / df["Sell"]) * 100

        total_lines = len(df)
        total_qty = df["Qty"].sum()
        total_cost = df["Total Cost"].sum()
        total_sell = df["Sell"].sum()
        overall_margin = (total_sell - total_cost) / total_sell * 100 if total_sell else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Lines", total_lines)
        c2.metric("Total Sets", int(total_qty))
        c3.metric("Total Cost", f"${total_cost:,.2f}")
        c4.metric("Total Sell", f"${total_sell:,.2f}")
        c5.metric("Margin %", f"{overall_margin:.1f}%")

        st.subheader("Quote Summary (Clean)")
        st.dataframe(df[["SKU", "Description", "Qty", "Total Cost", "Sell", "Margin %"]], height=300)

        with st.expander("Full Breakdown", expanded=False):
            st.dataframe(df, height=400)

        # SAVE
        qnum = st.text_input("Quote Number", value=suggest_next_q())

        if st.button("Save Quote 💾"):
            save_quote(
                qnum,
                st.session_state.cust,
                st.session_state.proj,
                df.to_dict(orient="records"),
                df.to_dict(orient="records"),
                S
            )
            st.success(f"Quote {qnum} saved!")

        # CSV EXPORT
        st.download_button("Download CSV", df.to_csv(index=False), "quote.csv")

        # ---------------------------------------------------------
        # DOOR ORDER FORM EXPORT
        # ---------------------------------------------------------
        st.subheader("📄 Door Order Form")

        if st.button("Download HD Door Order Form"):
            doors = build_door_order_rows(df)

            details = {
                "quote": qnum,
                "project": st.session_state.proj,
                "address": "",
            }

            contractor = {
                "contractor": "",
                "contact": "",
                "phone": "",
                "email": "",
                "onsite": "",
            }

            filebytes = generate_order_form(
                "templates/door_order_template.xlsx",    # <-- adjust path
                details,
                contractor,
                doors
            )

            st.download_button(
                "Download HD Door Order Form",
                data=filebytes,
                file_name="HD_Door_Order_Form.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------
    if st.button("Reset All ❌"):
        st.session_state.rows = []
        st.session_state.cust = ""
        st.session_state.proj = ""
        st.success("Reset complete.")
