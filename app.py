import streamlit as st
import requests
import pandas as pd
import time
import json
import streamlit.components.v1 as components

# 1. PAGE INITIALIZATION
st.set_page_config(
    page_title="Enterprise GraphRAG Command Center", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Target API endpoint (replace with your actual deployed Render service URL)
BACKEND_URL = "https://your-fastmcp-backend.onrender.com"
# 2. CUSTOM DARK THEME & CSS MATRIX
st.markdown("""
    <style>
    .stApp {
        background-color: #060913;
        color: #f1f5f9;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    section[data-testid="stSidebar"] {
        background-color: #0b1120 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    .telemetry-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .telemetry-card:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
    }
    
    .stTextInput input, .stSelectbox select, .stMultiSelect div {
        background-color: #0f172a !important;
        border: 1px solid #334155 !important;
        color: #f8fafc !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    .stTextInput input:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2) !important;
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 0.025em !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #0ea5e9 0%, #0284c7 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(14, 165, 233, 0.4) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: #0f172a;
        color: #94a3b8;
        font-weight: 600;
        border: 1px solid #1e293b;
        border-radius: 8px 8px 0 0;
        padding: 0 24px;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        border: 1px solid #334155 !important;
        border-bottom: 3px solid #38bdf8 !important;
    }
    </style>
""", unsafe_allow_html=True)

