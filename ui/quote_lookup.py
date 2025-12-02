import streamlit as st
from core.save_load import (
    load_quote,
    delete_quote,
    get_existing_q_numbers
)


def render_quote_lookup_tab():
    st.header("Quote Lookup")

    # Get all saved quote numbers
    qnums = get_existing_q_numbers()

    if not qnums:
        st.info("No quotes saved yet.")
        return

    # Select quote
    q_select = st.selectbox("Select Quote", qnums)

    col1, col2 = st.columns(2)

    # -------------------------------
    # LOAD QUOTE BUTTON
    # -------------------------------
    if col1.button("Load Quote"):
        data = load_quote(q_select)
        if data:
            st.session_state.pending_load = data
            st.success(f"Loaded {q_select}")
            st.rerun()
        else:
            st.error("Could not load quote.")

    # -------------------------------
    # DELETE QUOTE BUTTON
    # -------------------------------
    if col2.button("Delete Quote"):
        ok = delete_quote(q_select)
        if ok:
            st.success(f"Deleted {q_select}")
            st.rerun()
        else:
            st.error("Could not delete quote.")
