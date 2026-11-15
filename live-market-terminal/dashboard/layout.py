"""
Institutional Styling and Global Layout for Streamlit Dashboard.
"""

import streamlit as st

def apply_institutional_theme():
    """Applies institutional dark Bloomberg-style CSS styling."""
    st.set_page_config(
        page_title="Live Indian Market Terminal",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    custom_css = """
    <style>
        /* Base page styling */
        .stApp {
            background-color: #0d1117;
            color: #e6edf3;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        /* Metric cards */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            color: #ffffff !important;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.85rem !important;
        }
        div[data-testid="metric-container"] {
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 10px 14px;
            border-radius: 6px;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #161b22;
            border-right: 1px solid #30363d;
        }

        /* Tabs and headings */
        h1, h2, h3, h4 {
            color: #f0f6fc;
            font-weight: 600;
        }

        /* Plotly chart container */
        .js-plotly-plot {
            border-radius: 6px;
            border: 1px solid #30363d;
        }

        /* Alert and warning callouts */
        .stAlert {
            background-color: #161b22;
            border: 1px solid #30363d;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
