import streamlit as st
import copy
from core.settings import get_default_settings

def render_settings_tab():
    S = st.session_state.settings

    # ------------------------------------------------------------
    # RESET BUTTON
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Settings Management</div>', unsafe_allow_html=True)

    if st.button("Reset to Default"):
        st.session_state.settings = copy.deepcopy(get_default_settings())
        st.session_state.clear()  # full widget reset
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # FRAME PRICES
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Frame Prices</div>', unsafe_allow_html=True)

    for frame_type, price in S["frame_prices"].items():
        new_val = st.number_input(
            frame_type,
            value=float(price),
            step=0.10,
            key=f"frame_{frame_type}"
        )
        S["frame_prices"][frame_type] = new_val

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # LABOUR COSTS
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Labour Costs</div>', unsafe_allow_html=True)

    S["labour_single"] = st.number_input(
        "Single Door Labour Cost",
        value=float(S["labour_single"]),
        step=0.10,
        key="lab_single"
    )

    S["labour_double"] = st.number_input(
        "Double Door Labour Cost",
        value=float(S["labour_double"]),
        step=0.10,
        key="lab_double"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # HARDWARE COSTS
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Hardware Costs</div>', unsafe_allow_html=True)

    S["hinge_price"] = st.number_input(
        "Hinge Price",
        value=float(S["hinge_price"]),
        step=0.10,
        key="hinge_price"
    )

    S["hinges_per_door"] = st.number_input(
        "Hinges per Door (default 3)",
        value=int(S["hinges_per_door"]),
        step=1,
        min_value=1,
        key="hinges_per_door"
    )

    S["screw_cost"] = st.number_input(
        "Screw Cost",
        value=float(S["screw_cost"]),
        step=0.01,
        key="screw_cost"
    )

    S["hinge_screws"] = st.number_input(
        "Screws per Hinge (default 6)",
        value=int(S["hinge_screws"]),
        step=1,
        min_value=1,
        key="hinge_screws"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # MINIMUM CHARGES
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Minimum Charges</div>', unsafe_allow_html=True)

    S["minimum_frame_charge"] = st.number_input(
        "Minimum Frame Charge",
        value=float(S["minimum_frame_charge"]),
        step=0.10,
        key="min_frame"
    )

    st.markdown('</div>', unsafe_allow_html=True)
