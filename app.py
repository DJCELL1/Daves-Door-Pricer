import streamlit as st
import pandas as pd

# -------------------------------------
# CORE MODULES
# -------------------------------------
from core.settings import get_default_settings
from core.save_load import (
    save_quote,
    load_quote,
    suggest_next_q,
    get_existing_q_numbers
)

# -------------------------------------
# UI MODULES
# -------------------------------------
from ui.estimator import render_estimator_tab
from ui.production import render_production_tab
from ui.settings_ui import render_settings_tab
from ui.quote_lookup import render_quote_lookup_tab

# -------------------------------------
# HINGE LOADER
# -------------------------------------
from utils.loaders import load_hinge_sheet


# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(page_title="Dave’s Door Pricer", layout="wide")
st.title("🚪 Dave's Door Intelligence Estimator Bro")


# =====================================
# SESSION INITIALISATION
# =====================================

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

S = st.session_state.settings


# =====================================
# LOAD HINGE SHEET
# =====================================

HINGE_FOLDER = "data"
HINGE_DF = load_hinge_sheet(HINGE_FOLDER)

if HINGE_DF is None:
    st.error("No hinge sheet found in /data. Upload hinge_data.xlsx.")
    st.stop()


# =====================================
# APPLY PENDING QUOTE LOAD
# =====================================

if st.session_state.pending_load is not None:
    data = st.session_state.pending_load
    st.session_state.cust = data["customer"]
    st.session_state.proj = data["project"]
    st.session_state.rows = data["raw_rows"]
    st.session_state.pending_load = None


# =====================================
# TABS
# =====================================

tabs = st.tabs([
    "Estimator + Quote Table",
    "Production",
    "Settings",
    "Quote Lookup",
])


# =====================================
# TAB 1 — ESTIMATOR
# =====================================
with tabs[0]:
    render_estimator_tab(HINGE_DF)


# =====================================
# TAB 2 — PRODUCTION
# =====================================
with tabs[1]:
    og_df = pd.DataFrame(st.session_state.rows)
    render_production_tab(og_df, S)


# =====================================
# TAB 3 — SETTINGS
# =====================================
with tabs[2]:
    render_settings_tab()


# =====================================
# TAB 4 — QUOTE LOOKUP
# =====================================
with tabs[3]:
    render_quote_lookup_tab()
