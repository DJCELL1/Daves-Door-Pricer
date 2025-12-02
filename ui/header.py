import streamlit as st
import base64

def render_header():
    """
    HDL Branded Header
    Left: Logo
    Right: Title + Subtitle
    """
    logo_path = "assets/hdl_logo.png"

    st.markdown(
        f"""
        <div class="hdl-header">
            <div>
                <img src="data:image/png;base64,{get_img_base64(logo_path)}" class="hdl-logo">
            </div>
            <div>
                <div class="hdl-title">HDL Door Intelligence Estimator</div>
                <div class="hdl-subtitle">Pricing • Production • Stock • Analysis</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def get_img_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()
