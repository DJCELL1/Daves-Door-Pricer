import streamlit as st
from core.settings import get_default_settings


def render_settings_tab():
    S = st.session_state.settings

    # ------------------------------------------------------------
    # RESET BUTTON (TOP CARD)
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Settings Management</div>', unsafe_allow_html=True)

    if st.button("Reset All Settings to Default"):
        st.session_state.settings = get_default_settings()
        st.success("Defaults restored.")
        st.experimental_rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # FRAME PRICES
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Frame Prices</div>', unsafe_allow_html=True)

    for frame_type, price in S["frame_prices"].items():
        S["frame_prices"][frame_type] = st.number_input(
            frame_type,
            value=price,
            step=0.10
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # LABOUR COSTS
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Labour Costs</div>', unsafe_allow_html=True)

    S["labour_single"] = st.number_input(
        "Single Door Labour Cost",
        value=float(S["labour_single"]),
        step=0.10
    )

    S["labour_double"] = st.number_input(
        "Double Door Labour Cost",
        value=float(S["labour_double"]),
        step=0.10
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # HARDWARE COSTS — FIXED DEFAULTS: 3 HINGES/DOOR, 6 SCREWS/HINGE
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Hardware Costs</div>', unsafe_allow_html=True)

    # Hinge PRICE stays editable
    S["hinge_price"] = st.number_input(
        "Hinge Price",
        value=S["hinge_price"],
        step=0.10
    )

    # Hinges per door — force default = 3
    S["hinges_per_door"] = st.number_input(
        "Hinges per Door (default 3)",
        value=3,
        step=1,
        min_value=1
    )

    # Screw price stays editable
    S["screw_cost"] = st.number_input(
        "Screw Cost",
        value=S["screw_cost"],
        step=0.01
    )

    # Screws per hinge — force default = 6
    S["hinge_screws"] = st.number_input(
        "Screws per Hinge (default 6)",
        value=6,
        step=1,
        min_value=1
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # MINIMUM CHARGES
    # ------------------------------------------------------------
    st.markdown('<div class="hdl-card">', unsafe_allow_html=True)
    st.markdown('<div class="hdl-section-title">Minimum Charges</div>', unsafe_allow_html=True)

    S["minimum_frame_charge"] = st.number_input(
        "Minimum Frame Charge",
        value=S["minimum_frame_charge"],
        step=0.10
    )

    st.markdown('</div>', unsafe_allow_html=True)
