"""Streamlit UI for Opportunity Radar."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from analyzer import analyze_job_description, generate_resume_tailoring
from pipeline import is_product_role
from ui_helpers import (
    DEFAULT_SORT_OPTION,
    SORT_OPTIONS,
    build_description_preview,
    build_interpretation_heading,
    build_interpretation_bullets,
    build_weighted_score_rows,
    compute_apply_priority,
    hide_low_priority_opportunities,
    sort_opportunities,
)

st.set_page_config(page_title="Opportunity Radar", layout="wide")


# Keep the data file path in one place so it is easy to update later.
DATA_FILE = Path("data/analyzed_jobs.json")
MAX_DISPLAYED_OPPORTUNITIES = 40


def inject_global_styles() -> None:
    """Apply a premium monochrome design system across the Streamlit app."""
    st.markdown(
        """
        <style>
        :root {
            --or-bg: #050505;
            --or-surface: #0B0B0B;
            --or-surface-secondary: #111111;
            --or-border: #1C1C1C;
            --or-border-muted: #262626;
            --or-text-main: #F5F5F5;
            --or-text-secondary: #A1A1AA;
            --or-text-tertiary: #71717A;
            --or-shadow: 0 24px 80px rgba(0, 0, 0, 0.42);
            --or-radius-xl: 28px;
            --or-radius-lg: 22px;
            --or-radius-md: 16px;
            --or-radius-sm: 12px;
        }

        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"] {
            background:
                radial-gradient(circle at top left, rgba(255, 255, 255, 0.04), transparent 24%),
                radial-gradient(circle at top right, rgba(255, 255, 255, 0.03), transparent 22%),
                linear-gradient(180deg, #050505 0%, #080808 45%, #050505 100%);
            color: var(--or-text-main);
        }

        [data-testid="stSidebar"] {
            background: rgba(5, 5, 5, 0.96);
            border-right: 1px solid var(--or-border);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 2.2rem;
            padding-bottom: 4rem;
        }

        [data-testid="stHeader"] {
            background: rgba(5, 5, 5, 0.72);
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(14px);
        }

        h1, h2, h3, h4, h5, h6,
        p, li, label, span,
        [data-testid="stMarkdownContainer"],
        [data-testid="stCaptionContainer"] {
            color: var(--or-text-main);
        }

        .stCaption,
        [data-testid="stCaptionContainer"],
        [data-testid="stMarkdownContainer"] p strong + br,
        .top-opportunities-copy,
        .opportunity-card-label,
        .opportunity-card-meta-label,
        .or-meta-label,
        .or-section-kicker {
            color: var(--or-text-secondary);
        }

        h1, h2, h3, h4 {
            letter-spacing: -0.04em;
        }

        p, li {
            line-height: 1.65;
        }

        .or-shell {
            display: flex;
            flex-direction: column;
            gap: 1.4rem;
        }

        .or-hero {
            padding: 0.2rem 0 0.2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 0.35rem;
        }

        .or-hero-kicker,
        .or-section-kicker {
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }

        .or-hero-title {
            margin-top: 0.3rem;
            font-size: clamp(2.1rem, 4vw, 3.2rem);
            line-height: 1.02;
            font-weight: 600;
            max-width: 12ch;
        }

        .or-hero-copy {
            max-width: 760px;
            margin-top: 0.55rem;
            font-size: 0.98rem;
            color: var(--or-text-secondary);
        }

        .or-section {
            background: linear-gradient(180deg, rgba(11, 11, 11, 0.94), rgba(8, 8, 8, 0.98));
            border: 1px solid var(--or-border);
            border-radius: var(--or-radius-xl);
            box-shadow: var(--or-shadow);
            padding: 1.5rem 1.5rem 1.35rem;
        }

        .or-section-header {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            margin-bottom: 1rem;
        }

        .or-section-title {
            font-size: 1.5rem;
            line-height: 1.05;
            font-weight: 600;
        }

        .or-section-copy {
            max-width: 760px;
            color: var(--or-text-secondary);
        }

        .or-panel {
            background: var(--or-surface-secondary);
            border: 1px solid var(--or-border);
            border-radius: var(--or-radius-lg);
            padding: 1.1rem 1.15rem;
            overflow: hidden;
        }

        .or-methodology {
            background:
                linear-gradient(180deg, rgba(17, 17, 17, 0.95), rgba(11, 11, 11, 0.98));
            border: 1px solid var(--or-border-muted);
        }

        .or-methodology-title {
            font-size: 0.9rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            margin-bottom: 0.5rem;
        }

        .or-methodology-copy {
            color: var(--or-text-secondary);
            font-size: 0.94rem;
            max-width: 920px;
        }

        .or-subtle-text {
            color: var(--or-text-tertiary);
            font-size: 0.9rem;
        }

        .or-footer {
            text-align: center;
            color: var(--or-text-tertiary);
            font-size: 0.86rem;
            padding: 0.3rem 0 0.8rem;
        }

        .or-footer a {
            color: var(--or-text-secondary);
            text-decoration: none;
        }

        .or-footer a:hover {
            color: var(--or-text-main);
        }

        .or-detail-heading {
            font-size: 0.95rem;
            font-weight: 600;
            letter-spacing: 0.01em;
            margin-bottom: 0.2rem;
        }

        .or-empty-state {
            background: rgba(255, 255, 255, 0.015);
            border: 1px solid var(--or-border);
            border-radius: var(--or-radius-md);
            padding: 1rem 1.1rem;
        }

        [data-testid="stMetric"],
        [data-testid="stExpander"],
        [data-testid="stAlert"],
        [data-testid="stTextArea"],
        [data-testid="stSelectbox"],
        [data-testid="stSlider"],
        [data-testid="stCheckbox"] {
            background: rgba(11, 11, 11, 0.92);
            border: 1px solid var(--or-border);
            border-radius: var(--or-radius-md);
            box-shadow: none;
        }

        [data-testid="stMetric"] {
            min-height: 112px;
            padding: 1rem 1.05rem;
            background: linear-gradient(180deg, rgba(17, 17, 17, 0.96), rgba(11, 11, 11, 0.98));
        }

        [data-testid="stMetricLabel"] {
            color: var(--or-text-tertiary);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.68rem;
            font-weight: 600;
        }

        [data-testid="stMetricDelta"] {
            color: var(--or-text-secondary);
        }

        [data-testid="stMetricValue"] {
            color: var(--or-text-main);
            font-size: 1.2rem;
            letter-spacing: -0.03em;
        }

        [data-testid="stExpander"] {
            overflow: hidden;
            border-radius: var(--or-radius-lg);
            background: linear-gradient(180deg, rgba(12, 12, 12, 0.98), rgba(9, 9, 9, 1));
            border: 1px solid var(--or-border);
        }

        [data-testid="stExpander"] details summary {
            background: rgba(12, 12, 12, 0.98);
            color: var(--or-text-main);
            padding-top: 0.35rem;
            padding-bottom: 0.35rem;
        }

        [data-testid="stExpander"] details summary:hover {
            background: rgba(17, 17, 17, 0.98);
        }

        [data-testid="stTextArea"] textarea,
        [data-baseweb="select"] > div,
        .stSlider > div[data-baseweb="slider"],
        .stCheckbox label {
            background: transparent;
            color: var(--or-text-main);
        }

        [data-testid="stTextArea"] textarea {
            border-radius: 14px;
            background: rgba(17, 17, 17, 0.78);
            border: 1px solid var(--or-border);
            padding: 1rem;
            line-height: 1.6;
        }

        [data-baseweb="select"] > div {
            min-height: 52px;
            border: 1px solid var(--or-border-muted) !important;
            border-radius: var(--or-radius-sm) !important;
            background: linear-gradient(180deg, rgba(20, 20, 20, 0.96), rgba(13, 13, 13, 0.98)) !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
            padding-left: 0.15rem;
            transition: border-color 0.18s ease, background 0.18s ease;
        }

        [data-baseweb="select"] > div:hover {
            border-color: #383838 !important;
            background: linear-gradient(180deg, rgba(22, 22, 22, 0.98), rgba(14, 14, 14, 1)) !important;
        }

        [data-baseweb="select"] * {
            color: var(--or-text-main) !important;
        }

        [data-baseweb="select"] input {
            caret-color: transparent !important;
            cursor: pointer !important;
        }

        [data-baseweb="select"] input::selection {
            background: transparent !important;
        }

        [data-baseweb="select"] [aria-expanded="true"] {
            border-color: #4A4A4A !important;
        }

        [data-baseweb="popover"] [role="listbox"] {
            background: rgba(14, 14, 14, 0.98) !important;
            border: 1px solid var(--or-border-muted) !important;
            border-radius: var(--or-radius-sm) !important;
            padding: 0.35rem !important;
            box-shadow: var(--or-shadow) !important;
        }

        [data-baseweb="popover"] [role="option"] {
            border-radius: 10px !important;
        }

        [data-baseweb="popover"] [role="option"]:hover,
        [data-baseweb="popover"] [aria-selected="true"] {
            background: rgba(255, 255, 255, 0.06) !important;
        }

        .stSlider [data-baseweb="slider"] {
            padding-top: 0.5rem;
            padding-bottom: 0.1rem;
        }

        .stSlider,
        .stCheckbox,
        [data-testid="stSelectbox"] {
            border-radius: var(--or-radius-sm);
            border-color: var(--or-border-muted);
        }

        .stSlider [role="slider"] {
            background: #D4D4D8 !important;
            box-shadow: 0 0 0 4px rgba(212, 212, 216, 0.08) !important;
            border: none !important;
        }

        .stSlider [data-testid="stTickBarMin"],
        .stSlider [data-testid="stTickBarMax"] {
            background: #2A2A2A !important;
        }

        .stSlider [data-testid="stTickBar"] {
            background: #5C5C5C !important;
        }

        .stCheckbox {
            min-height: 52px;
            padding: 0.8rem 0.95rem;
            display: flex;
            align-items: center;
            margin-top: 1.75rem;
        }

        .stCheckbox label p {
            color: var(--or-text-secondary);
        }

        [data-testid="stSelectbox"] label,
        [data-testid="stSlider"] label,
        [data-testid="stCheckbox"] label {
            font-size: 0.76rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--or-text-secondary);
        }

        [data-testid="stSelectbox"],
        [data-testid="stSlider"],
        [data-testid="stCheckbox"] {
            padding: 0.9rem 0.95rem;
        }

        .stButton {
            margin-top: 0.35rem;
        }

        .stButton > button {
            min-height: 48px;
            border-radius: 999px;
            border: 1px solid var(--or-border-muted);
            background: linear-gradient(180deg, #151515 0%, #0E0E0E 100%);
            color: var(--or-text-main);
            font-weight: 600;
            letter-spacing: 0.01em;
            padding: 0.7rem 1.05rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }

        .stButton > button:hover {
            border-color: #3A3A3A;
            background: linear-gradient(180deg, #181818 0%, #111111 100%);
            color: var(--or-text-main);
        }

        .stButton > button:focus {
            box-shadow: 0 0 0 0.18rem rgba(245, 245, 245, 0.08);
        }

        [data-testid="stDataFrame"] {
            background: rgba(11, 11, 11, 0.94);
            border: 1px solid var(--or-border);
            border-radius: var(--or-radius-lg);
            box-shadow: none;
            overflow: hidden;
        }

        [data-testid="stDataFrame"] [role="grid"] {
            border: none !important;
        }

        [data-testid="stDataFrame"] [role="columnheader"] {
            background: rgba(14, 14, 14, 0.98) !important;
            color: var(--or-text-tertiary) !important;
            border-bottom: 1px solid rgba(38, 38, 38, 0.9) !important;
            border-right: none !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            font-size: 0.7rem !important;
        }

        [data-testid="stDataFrame"] [role="gridcell"] {
            background: rgba(11, 11, 11, 0.78) !important;
            color: var(--or-text-main) !important;
            border-right: none !important;
            border-left: none !important;
            border-top: none !important;
            border-bottom: 1px solid rgba(28, 28, 28, 0.6) !important;
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }

        [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
            background: rgba(16, 16, 16, 0.96) !important;
        }

        [data-testid="stDataFrame"] [role="gridcell"] a {
            color: var(--or-text-secondary) !important;
            text-decoration: none !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em;
        }

        [data-testid="stDataFrame"] [role="gridcell"] a:hover {
            color: var(--or-text-main) !important;
        }

        .top-opportunities-heading,
        h2[data-testid="stHeader"],
        h3[data-testid="stHeader"] {
            color: var(--or-text-main);
        }

        .opportunity-card {
            background: linear-gradient(180deg, rgba(17, 17, 17, 0.96), rgba(10, 10, 10, 0.98));
            border: 1px solid var(--or-border);
            border-radius: var(--or-radius-lg);
            box-shadow: none;
        }

        .opportunity-card-company,
        .opportunity-card-label,
        .top-opportunities-copy,
        .opportunity-card-title,
        .opportunity-card-value,
        .or-section-copy,
        .or-methodology-copy,
        .or-results-count,
        .or-detail-heading,
        .or-hero-copy {
            word-break: break-word;
        }

        .top-opportunities-copy {
            color: var(--or-text-secondary);
        }

        .opportunity-card-title,
        .opportunity-card-value,
        .opportunity-card-action a,
        .opportunity-card-action span,
        .top-opportunities-heading {
            color: var(--or-text-main);
        }

        .opportunity-card-score,
        .radar-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.22rem 0.58rem;
            border-radius: 999px;
            border: 1px solid var(--or-border-muted);
            background: rgba(255, 255, 255, 0.025);
            color: var(--or-text-secondary);
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.04em;
        }

        .stMarkdown hr,
        [data-testid="stMarkdownContainer"] hr {
            border-color: rgba(28, 28, 28, 0.9);
        }

        a {
            color: #F5F5F5;
            text-decoration-color: rgba(245, 245, 245, 0.35);
            text-underline-offset: 0.2em;
        }

        a:hover {
            color: #FFFFFF;
            text-decoration-color: rgba(255, 255, 255, 0.75);
        }

        .or-results-count {
            font-size: 0.9rem;
            color: var(--or-text-secondary);
            margin: 0.2rem 0 0.6rem;
        }

        .or-detail-copy {
            color: var(--or-text-secondary);
            margin-top: 0.2rem;
        }

        .or-table-shell {
            border: 1px solid var(--or-border);
            border-radius: var(--or-radius-lg);
            background: linear-gradient(180deg, rgba(11, 11, 11, 0.96), rgba(8, 8, 8, 0.99));
            overflow: hidden;
        }

        .or-table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }

        .or-table thead {
            background: rgba(14, 14, 14, 0.98);
        }

        .or-table th {
            color: var(--or-text-tertiary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.7rem;
            text-align: left;
            padding: 0.95rem 1rem;
            border-bottom: 1px solid rgba(38, 38, 38, 0.9);
        }

        .or-table td {
            color: var(--or-text-main);
            padding: 1rem;
            border-bottom: 1px solid rgba(28, 28, 28, 0.6);
            vertical-align: top;
            word-break: break-word;
        }

        .or-table tbody tr:hover {
            background: rgba(16, 16, 16, 0.96);
        }

        .or-table tbody tr:last-child td {
            border-bottom: none;
        }

        .or-table-empty {
            color: var(--or-text-secondary);
            text-align: center;
            padding: 1.2rem 1rem;
        }

        .or-table-link {
            color: var(--or-text-secondary);
            text-decoration: none;
            font-weight: 600;
            letter-spacing: 0.01em;
        }

        .or-table-link:hover {
            color: var(--or-text-main);
        }

        .or-button-link {
            min-height: 48px;
            border-radius: 999px;
            border: 1px solid var(--or-border-muted);
            background: linear-gradient(180deg, #151515 0%, #0E0E0E 100%);
            color: var(--or-text-main);
            font-weight: 600;
            letter-spacing: 0.01em;
            padding: 0.7rem 1.05rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            text-decoration: none;
            box-sizing: border-box;
            transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
        }

        .or-button-link:hover {
            border-color: #3A3A3A;
            background: linear-gradient(180deg, #181818 0%, #111111 100%);
            color: var(--or-text-main);
            text-decoration: none;
        }

        .or-button-link:focus,
        .or-button-link:focus-visible {
            outline: none;
            box-shadow: 0 0 0 0.18rem rgba(245, 245, 245, 0.08);
        }

        .or-utility-section {
            background: linear-gradient(180deg, rgba(10, 10, 10, 0.9), rgba(7, 7, 7, 0.96));
            border-color: rgba(28, 28, 28, 0.85);
            box-shadow: none;
        }

        .or-utility-section .or-section-header {
            margin-bottom: 0.8rem;
        }

        .or-utility-section .or-section-title {
            font-size: 1.2rem;
        }

        .or-utility-section .or-section-copy {
            max-width: 620px;
            color: var(--or-text-tertiary);
        }

        .or-utility-section [data-testid="stTextArea"] {
            background: rgba(9, 9, 9, 0.82);
            border: 1px solid rgba(38, 38, 38, 0.8);
            border-radius: 20px;
            padding: 0.8rem;
            margin-top: 0.15rem;
        }

        .or-utility-section [data-testid="stTextArea"] label {
            font-size: 0.74rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--or-text-secondary);
        }

        .or-utility-section [data-testid="stTextArea"] textarea {
            min-height: 260px;
            background: linear-gradient(180deg, rgba(12, 12, 12, 0.98), rgba(9, 9, 9, 0.98));
            border: 1px solid rgba(38, 38, 38, 0.78);
            border-radius: 16px;
            color: var(--or-text-main);
            padding: 1rem 1.05rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
            transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
        }

        .or-utility-section [data-testid="stTextArea"] textarea::placeholder {
            color: #6F6F76;
            opacity: 1;
        }

        .or-utility-section [data-testid="stTextArea"] textarea:hover {
            border-color: rgba(58, 58, 58, 0.9);
            background: linear-gradient(180deg, rgba(14, 14, 14, 0.99), rgba(10, 10, 10, 0.99));
        }

        .or-utility-section [data-testid="stTextArea"] textarea:focus {
            border-color: rgba(92, 92, 92, 0.92);
            box-shadow: 0 0 0 0.16rem rgba(245, 245, 245, 0.05);
            outline: none;
        }

        .or-utility-section .stButton {
            margin-top: 0.6rem;
        }

        .or-utility-section .stButton > button {
            background: #111111;
            border: 1px solid rgba(38, 38, 38, 0.9);
            box-shadow: none;
        }

        .or-utility-section .stButton > button:hover {
            background: #151515;
            border-color: rgba(58, 58, 58, 0.95);
        }

        .or-utility-section .stButton > button:focus {
            box-shadow: 0 0 0 0.18rem rgba(245, 245, 245, 0.06);
        }

        @media (max-width: 1100px) {
            .opportunity-card-header,
            .opportunity-card-meta-item {
                flex-direction: column;
                align-items: flex-start;
            }

            .opportunity-card-value-wrap {
                text-align: left;
            }
        }

        @media (max-width: 900px) {
            .block-container {
                padding-top: 1.4rem;
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }

            .or-section {
                padding: 1.15rem 1rem 1rem;
            }

            .or-hero-title {
                font-size: clamp(2.2rem, 10vw, 3.2rem);
            }

            [data-testid="stMetric"] {
                min-height: 96px;
            }

            .stButton > button {
                width: 100%;
            }
        }

        @media (max-width: 640px) {
            .or-section-header {
                gap: 0.3rem;
            }

            [data-testid="stDataFrame"] [role="columnheader"],
            [data-testid="stDataFrame"] [role="gridcell"] {
                white-space: normal !important;
                word-break: break-word !important;
            }

            .or-table {
                table-layout: auto;
            }

            .or-table th,
            .or-table td {
                padding: 0.8rem 0.75rem;
                white-space: normal;
            }

            .or-utility-section [data-testid="stTextArea"] {
                padding: 0.65rem;
            }

            .or-utility-section [data-testid="stTextArea"] textarea {
                min-height: 220px;
                padding: 0.9rem 0.95rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_global_styles()


def initialize_session_state() -> None:
    """Create app-level session containers once per browser session."""
    # Cache resume-tailoring responses in memory so repeated clicks stay fast.
    st.session_state.setdefault("resume_tailoring_cache", {})


def build_resume_tailoring_cache_key(job: dict) -> str:
    """Create a stable cache key for one tracked job."""
    # Prefer the URL because it is usually unique across tracked jobs.
    url = str(job.get("url", "")).strip().lower()
    if url:
        return url

    # Fall back to a readable compound key if the URL is missing.
    company = str(job.get("company", "unknown")).strip().lower()
    title = str(job.get("title", "unknown")).strip().lower()
    location = str(job.get("location", "unknown")).strip().lower()
    return f"{company}::{title}::{location}"


def render_resume_tailoring_section(job: dict) -> None:
    """Render the on-demand resume-tailoring UI for one tracked job."""
    cache_key = build_resume_tailoring_cache_key(job)
    tailoring_cache: dict[str, dict] = st.session_state["resume_tailoring_cache"]
    tailoring_result = tailoring_cache.get(cache_key)

    st.markdown("---")
    st.markdown("**Resume Tailoring**")
    st.caption("Generate role-specific guidance only when you want it. Results are cached for this session.")

    # Use a job-specific button key so each expander can generate independently.
    if st.button(
        "Generate Resume Tailoring",
        key=f"resume-tailoring::{cache_key}",
        use_container_width=True,
    ):
        if tailoring_result is None:
            with st.spinner("Generating resume-tailoring guidance..."):
                try:
                    tailoring_result = generate_resume_tailoring(job)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Resume tailoring failed: {exc}")
                else:
                    tailoring_cache[cache_key] = tailoring_result
        else:
            st.info("Using the cached resume-tailoring guidance from this session.")

    # Only show the section output after a successful user-triggered generation.
    if tailoring_result is None:
        st.caption("Click the button to generate tailored resume guidance for this role.")
        return

    st.markdown("**Resume Highlights**")
    for bullet in tailoring_result["resume_highlights"]:
        st.markdown(f"- {bullet}")

    st.markdown("**Key Skills to Surface**")
    st.write(", ".join(tailoring_result["key_skills_to_surface"]))

    st.markdown("**Outreach Angle**")
    st.write(tailoring_result["outreach_angle"])

    st.markdown("**Why You Match**")
    st.write(tailoring_result["why_you_match"])


def get_data_file_cache_token() -> tuple[int, int]:
    """Return a token that changes when the analyzed jobs file changes."""
    if not DATA_FILE.exists():
        return (0, 0)

    file_stats = DATA_FILE.stat()
    return (file_stats.st_mtime_ns, file_stats.st_size)


@st.cache_data(show_spinner=False)
def load_tracked_opportunities(cache_token: tuple[int, int]) -> list[dict]:
    """Load tracked jobs from the backend pipeline output."""
    _ = cache_token
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        jobs = json.load(file)

    # Keep the UI trustworthy even if the saved dataset contains stale non-product roles.
    return [job for job in jobs if isinstance(job, dict) and is_product_role(job)]


def compute_opportunity_tier(fit_score: float) -> str:
    """Convert a fit score into a simple opportunity tier label."""
    if fit_score >= 85:
        return "Elite"
    if fit_score >= 70:
        return "Strong"
    if fit_score >= 50:
        return "Average"
    return "Avoid"


def enrich_job(job: dict) -> dict:
    """Add UI-derived fields without mutating the original payload."""
    fit_score = float(job.get("fit_score", 0))
    enriched_job = dict(job)
    enriched_job["fit_score"] = fit_score
    enriched_job["opportunity_tier"] = compute_opportunity_tier(fit_score)
    enriched_job["apply_priority"] = compute_apply_priority(fit_score)
    return enriched_job


def build_results_count_copy(total_matching_jobs: int, displayed_jobs: int) -> str:
    """Return concise, curated count copy for the current view."""
    if total_matching_jobs <= 0:
        return "No product roles match the current filters."
    if displayed_jobs < total_matching_jobs:
        return f"Showing top {displayed_jobs} of {total_matching_jobs} product roles evaluated"
    return f"{displayed_jobs} product roles evaluated"


def render_dark_table(
    rows: list[dict[str, object]],
    columns: list[tuple[str, str]],
    *,
    empty_message: str,
    link_columns: dict[str, str] | None = None,
) -> None:
    """Render a dark themed HTML table to avoid native light Streamlit table chrome."""
    header_markup = "".join(f"<th>{escape(label)}</th>" for _, label in columns)
    link_columns = link_columns or {}

    if rows:
        body_rows: list[str] = []
        for row in rows:
            cells: list[str] = []
            for key, _ in columns:
                value = row.get(key, "")
                if key in link_columns:
                    href = str(value).strip()
                    label = escape(link_columns[key])
                    if href:
                        cell_markup = (
                            f'<a class="or-table-link" href="{escape(href, quote=True)}" '
                            f'target="_blank" rel="noopener noreferrer">{label}</a>'
                        )
                    else:
                        cell_markup = '<span class="or-subtle-text">Unavailable</span>'
                else:
                    cell_markup = escape(str(value))
                cells.append(f"<td>{cell_markup}</td>")
            body_rows.append(f"<tr>{''.join(cells)}</tr>")
        body_markup = "".join(body_rows)
    else:
        body_markup = (
            f'<tr><td class="or-table-empty" colspan="{len(columns)}">{escape(empty_message)}</td></tr>'
        )

    st.markdown(
        f"""
        <div class="or-table-shell">
            <table class="or-table">
                <thead>
                    <tr>{header_markup}</tr>
                </thead>
                <tbody>
                    {body_markup}
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_job_posting_actions(job_url: str) -> None:
    """Render clean actions for opening and copying a job posting URL."""
    action_col, copy_col, _ = st.columns([1.35, 1, 3.65])

    with action_col:
        st.markdown(
            (
                f'<a class="or-button-link" href="{escape(job_url, quote=True)}" '
                'target="_blank" rel="noopener noreferrer" title="Open the original posting in a new browser tab.">'
                "Open job posting"
                "</a>"
            ),
            unsafe_allow_html=True,
        )

    with copy_col:
        components.html(
            f"""
            <html>
              <head>
                <style>
                  :root {{
                    color-scheme: dark;
                  }}

                  body {{
                    margin: 0;
                    background: transparent;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                  }}

                  button {{
                    width: 100%;
                    min-height: 48px;
                    border-radius: 999px;
                    border: 1px solid #262626;
                    background: linear-gradient(180deg, #151515 0%, #0e0e0e 100%);
                    color: #f5f5f5;
                    font-size: 0.84rem;
                    font-weight: 600;
                    letter-spacing: 0.01em;
                    padding: 0.7rem 1.05rem;
                    cursor: pointer;
                    box-sizing: border-box;
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
                  }}

                  button:hover {{
                    border-color: #3a3a3a;
                    background: linear-gradient(180deg, #181818 0%, #111111 100%);
                  }}

                  button:focus {{
                    outline: none;
                    box-shadow:
                      0 0 0 0.18rem rgba(245, 245, 245, 0.08),
                      inset 0 1px 0 rgba(255, 255, 255, 0.04);
                  }}
                </style>
              </head>
              <body>
                <button id="copy-button" type="button">Copy link</button>
                <script>
                  const button = document.getElementById("copy-button");
                  const jobUrl = {job_url!r};
                  const defaultLabel = "Copy link";

                  async function copyText(text) {{
                    if (navigator.clipboard && window.isSecureContext) {{
                      await navigator.clipboard.writeText(text);
                      return true;
                    }}

                    const textArea = document.createElement("textarea");
                    textArea.value = text;
                    textArea.style.position = "fixed";
                    textArea.style.opacity = "0";
                    textArea.style.pointerEvents = "none";
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();

                    try {{
                      return document.execCommand("copy");
                    }} finally {{
                      document.body.removeChild(textArea);
                    }}
                  }}

                  button.addEventListener("click", async () => {{
                    try {{
                      const copied = await copyText(jobUrl);
                      button.textContent = copied ? "Copied" : "Copy unavailable";
                    }} catch (error) {{
                      button.textContent = "Copy unavailable";
                    }}

                    window.setTimeout(() => {{
                      button.textContent = defaultLabel;
                    }}, 1600);
                  }});
                </script>
              </body>
            </html>
            """,
            height=48,
        )


def filter_and_sort_results(
    jobs: list[dict],
    selected_company: str,
    minimum_score: int,
    sort_option: str,
    hide_low_priority_roles: bool,
) -> list[dict]:
    """Filter tracked jobs and sort them for display."""
    filtered_jobs: list[dict] = []

    for job in jobs:
        fit_score = float(job.get("fit_score", 0))
        company = job.get("company", "Unknown")

        # Skip jobs that do not match the current filter controls.
        if selected_company != "All companies" and company != selected_company:
            continue
        if fit_score < minimum_score:
            continue

        filtered_jobs.append(enrich_job(job))

    filtered_jobs = hide_low_priority_opportunities(
        filtered_jobs,
        enabled=hide_low_priority_roles,
    )
    return sort_opportunities(filtered_jobs, sort_option=sort_option)


def render_top_opportunities_section(jobs: list[dict]) -> None:
    """Render a compact highlight grid for the best-scoring tracked roles."""
    top_jobs = sorted(
        (enrich_job(job) for job in jobs),
        key=lambda job: (
            float(job.get("fit_score", 0)),
            float(job.get("ai_score", 0)),
        ),
        reverse=True,
    )[:5]

    st.markdown(
        """
        <style>
        .top-opportunities-heading {
            font-size: 0.86rem;
            font-weight: 600;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }
        .top-opportunities-copy {
            font-size: 0.94rem;
            margin-bottom: 1.35rem;
            max-width: 760px;
        }
        .opportunity-card {
            padding: 1.15rem 1.1rem 1rem;
            min-height: 208px;
        }
        .opportunity-card + .opportunity-card {
            margin-top: 1rem;
        }
        .opportunity-card-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.9rem;
            margin-bottom: 1rem;
        }
        .opportunity-card-company {
            font-size: 0.68rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            margin-bottom: 0.45rem;
        }
        .opportunity-card-title {
            font-size: 1.02rem;
            font-weight: 600;
            line-height: 1.35;
            letter-spacing: -0.03em;
        }
        .opportunity-card-score {
            flex-shrink: 0;
        }
        .opportunity-card-meta {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-bottom: 1.15rem;
        }
        .opportunity-card-meta-item {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 1rem;
            padding-bottom: 0.55rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .opportunity-card-meta-item:last-child {
            border-bottom: none;
            padding-bottom: 0;
        }
        .opportunity-card-label {
            font-size: 0.68rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.14em;
        }
        .opportunity-card-value-wrap {
            text-align: right;
        }
        .opportunity-card-value {
            font-size: 0.88rem;
            line-height: 1.35;
        }
        .opportunity-card-action a,
        .opportunity-card-action span {
            font-size: 0.84rem;
            font-weight: 500;
            text-decoration: none;
        }
        .opportunity-card-action a:hover {
            color: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="top-opportunities-heading">Top Opportunities</div>
        <div class="top-opportunities-copy">
            Highest-fit product roles ranked by final score and surfaced first for faster review.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not top_jobs:
        st.info("No tracked opportunities are available to highlight yet.")
        return

    columns = st.columns(2)
    for index, job in enumerate(top_jobs):
        company = escape(str(job.get("company", "Unknown")).strip() or "Unknown")
        title = escape(str(job.get("title", "Unknown")).strip() or "Unknown")
        priority = escape(str(job.get("apply_priority", "Unknown")).strip() or "Unknown")
        location = escape(str(job.get("location", "Unknown")).strip() or "Unknown")
        url = str(job.get("url", "")).strip()
        action_markup = (
            (
                f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
                "Open job posting"
                "</a>"
            )
            if url
            else "<span>Open job posting</span>"
        )

        with columns[index % 2]:
            st.markdown(
                f"""
                <div class="opportunity-card">
                    <div class="opportunity-card-header">
                        <div>
                            <div class="opportunity-card-company">{company}</div>
                            <div class="opportunity-card-title">{title}</div>
                        </div>
                        <div class="opportunity-card-score radar-badge">{int(job["fit_score"])}/100</div>
                    </div>
                    <div class="opportunity-card-meta">
                        <div class="opportunity-card-meta-item">
                            <div class="opportunity-card-label">Priority</div>
                            <div class="opportunity-card-value-wrap">
                                <div class="opportunity-card-value">{priority}</div>
                            </div>
                        </div>
                        <div class="opportunity-card-meta-item">
                            <div class="opportunity-card-label">Location</div>
                            <div class="opportunity-card-value-wrap">
                                <div class="opportunity-card-value">{location}</div>
                            </div>
                        </div>
                    </div>
                    <div class="opportunity-card-action">{action_markup}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown(
    """
    <div class="or-shell">
        <section class="or-hero">
            <div class="or-hero-title">Opportunity Radar</div>
            <div class="or-hero-copy">
                Find and prioritize the most promising product roles based on ownership scope, AI exposure,
                and long-term upside.
            </div>
        </section>
    </div>
    """,
    unsafe_allow_html=True,
)
initialize_session_state()

# Load tracked opportunities once and reuse them across reruns.
tracked_jobs = load_tracked_opportunities(get_data_file_cache_token())

st.markdown(
    """
    <section class="or-section">
        <div class="or-section-header">
            <div class="or-section-kicker">Tracked Pipeline</div>
            <div class="or-section-title">Pipeline Overview</div>
            <div class="or-section-copy">
                Review product roles scored on ownership, AI exposure, and growth potential so the highest-signal opportunities rise first.
            </div>
        </div>
        <div class="or-panel or-methodology">
            <div class="or-methodology-title">Scoring Methodology</div>
            <div class="or-methodology-copy">
                Each role gets six raw scores from 0 to 10: Ownership, AI Relevance, Learning, Prestige,
                Startup Upside, and Comp Potential. Those scores are converted into a weighted fit score out of 100,
                where Ownership counts for 30%, AI Relevance 25%, Learning 15%, Prestige 15%, Startup Upside 10%,
                and Comp Potential 5%.
            </div>
        </div>
    """,
    unsafe_allow_html=True,
)

if not tracked_jobs:
    st.markdown(
        '<div class="or-empty-state">No tracked opportunities were found in <code>data/analyzed_jobs.json</code>.</div>',
        unsafe_allow_html=True,
    )
else:
    render_top_opportunities_section(tracked_jobs)

    # Build filter options from the loaded job data.
    company_options = ["All companies"] + sorted(
        {
            str(job.get("company", "Unknown")).strip() or "Unknown"
            for job in tracked_jobs
        }
    )

    st.markdown(
        """
        <div class="or-section-header" style="margin-top: 1.5rem;">
            <div class="or-section-kicker">Refine View</div>
            <div class="or-section-copy">Use the controls below to narrow the current product opportunity set.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filter_col_1, filter_col_2, filter_col_3, filter_col_4 = st.columns([2, 2, 2, 2])
    selected_company = filter_col_1.selectbox(
        "Company",
        options=company_options,
        help="Filter tracked jobs to a specific company.",
        accept_new_options=False,
    )
    minimum_score = filter_col_2.slider(
        "Minimum score",
        min_value=0,
        max_value=100,
        value=50,
        help="Show only jobs that meet or exceed this score.",
    )
    sort_option = filter_col_3.selectbox(
        "Sort",
        options=SORT_OPTIONS,
        index=SORT_OPTIONS.index(DEFAULT_SORT_OPTION),
        help="Choose how to order the visible opportunities.",
        accept_new_options=False,
    )
    hide_low_priority_roles = filter_col_4.checkbox(
        "Hide lower-priority roles",
        value=False,
        help="Hide roles with a final fit score below 70.",
    )

    matching_jobs = filter_and_sort_results(
        tracked_jobs,
        selected_company=selected_company,
        minimum_score=minimum_score,
        sort_option=sort_option,
        hide_low_priority_roles=hide_low_priority_roles,
    )
    visible_jobs = matching_jobs[:MAX_DISPLAYED_OPPORTUNITIES]

    summary_rows = [
        {
            "company": job.get("company", "Unknown"),
            "title": job.get("title", "Unknown"),
            "location": job.get("location", "Unknown"),
            "fit_score": int(job["fit_score"]),
            "opportunity_tier": job["opportunity_tier"],
            "apply_priority": job["apply_priority"],
            "job_link": str(job.get("url", "")).strip(),
        }
        for job in visible_jobs
    ]

    st.markdown(
        (
            f'<div class="or-results-count">'
            f'{build_results_count_copy(len(matching_jobs), len(visible_jobs))}'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    render_dark_table(
        summary_rows,
        [
            ("company", "Company"),
            ("title", "Title"),
            ("location", "Location"),
            ("fit_score", "Fit Score"),
            ("opportunity_tier", "Opportunity Tier"),
            ("apply_priority", "Apply Priority"),
            ("job_link", "Job Link"),
        ],
        empty_message="No tracked jobs match the current filters.",
        link_columns={"job_link": "Open ->"},
    )

    st.markdown(
        """
        <div class="or-section-header" style="margin-top: 1.45rem;">
            <div class="or-section-kicker">Deep Dive</div>
            <div class="or-section-title" style="font-size: 1.15rem;">Job Details</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not visible_jobs:
        st.markdown(
            '<div class="or-empty-state">No tracked jobs match the current filters.</div>',
            unsafe_allow_html=True,
        )
    else:
        for job in visible_jobs:
            header = (
                f'{job.get("company", "Unknown")} | '
                f'{job.get("title", "Unknown")} | '
                f'{int(job["fit_score"])}/100 | '
                f'{job["opportunity_tier"]}'
            )

            # Each expander keeps the main view clean while preserving full detail.
            with st.expander(header):
                info_col_1, info_col_2, info_col_3, info_col_4, info_col_5 = st.columns(5)
                info_col_1.metric("Company", job.get("company", "Unknown"))
                info_col_2.metric("Location", job.get("location", "Unknown"))
                info_col_3.metric("Fit Score", f'{int(job["fit_score"])}/100')
                info_col_4.metric("Tier", job["opportunity_tier"])
                info_col_5.metric("Apply Priority", job["apply_priority"])

                st.markdown(
                    f'<div class="or-detail-heading">{build_interpretation_heading(job)}</div>',
                    unsafe_allow_html=True,
                )
                for bullet in build_interpretation_bullets(job):
                    st.markdown(f"- {bullet}")

                st.markdown(
                    '<div class="or-detail-heading" style="margin-top: 1rem;">Weighted Score Breakdown</div>',
                    unsafe_allow_html=True,
                )
                render_dark_table(
                    build_weighted_score_rows(job),
                    [
                        ("Factor", "Factor"),
                        ("Raw score out of 10", "Raw score out of 10"),
                        ("Weight %", "Weight %"),
                        ("Weighted contribution", "Weighted contribution"),
                    ],
                    empty_message="No weighted score breakdown is available for this role.",
                )

                st.markdown(
                    '<div class="or-detail-heading" style="margin-top: 1rem;">Description Preview</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="or-detail-copy">{escape(build_description_preview(job))}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="or-detail-heading" style="margin-top: 1rem;">Full Analysis</div>',
                    unsafe_allow_html=True,
                )
                st.write(job.get("analysis", "No analysis available."))

                job_url = job.get("url", "")
                if job_url:
                    st.markdown(
                        '<div class="or-detail-heading" style="margin-top: 1rem;">Job Posting</div>',
                        unsafe_allow_html=True,
                    )
                    render_job_posting_actions(job_url)

                # Keep the tailoring UI separate from the scoring content above.
                render_resume_tailoring_section(job)

st.markdown("</section>", unsafe_allow_html=True)

st.divider()

st.markdown(
    """
    <section class="or-section or-utility-section">
        <div class="or-section-header">
            <div class="or-section-kicker">Role Analysis</div>
            <div class="or-section-title">Analyze a role</div>
            <div class="or-section-copy">
                Paste a role description to score it using the same evaluation framework.
            </div>
        </div>
    """,
    unsafe_allow_html=True,
)

job_description = st.text_area(
    "Role description",
    height=300,
    placeholder="Paste the full role description here...",
)

if st.button("Analyze Job", type="primary", use_container_width=True):
    if not job_description.strip():
        st.warning("Please paste a job description before running the analysis.")
    else:
        with st.spinner("Analyzing job description..."):
            try:
                result = analyze_job_description(job_description)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Analysis failed: {exc}")
            else:
                st.subheader("Structured Evaluation")

                top_col_1, top_col_2, top_col_3 = st.columns(3)
                top_col_1.metric("Company", result["company"])
                top_col_2.metric("Title", result["title"])
                top_col_3.metric("Overall Fit Score", f'{result["fit_score"]}/100')

                priority_col_1, priority_col_2 = st.columns(2)
                priority_col_1.metric("Tier", compute_opportunity_tier(float(result["fit_score"])))
                priority_col_2.metric(
                    "Apply Priority",
                    compute_apply_priority(float(result["fit_score"])),
                )

                score_col_1, score_col_2, score_col_3 = st.columns(3)
                score_col_1.metric("Ownership", f'{result["ownership_score"]}/10')
                score_col_1.metric("AI Relevance", f'{result["ai_score"]}/10')
                score_col_2.metric("Learning", f'{result["learning_score"]}/10')
                score_col_2.metric("Prestige", f'{result["prestige_score"]}/10')
                score_col_3.metric("Startup Upside", f'{result["startup_score"]}/10')
                score_col_3.metric("Comp Potential", f'{result["comp_score"]}/10')

                st.subheader("Analysis")
                st.write(result["analysis"])

st.markdown("</section>", unsafe_allow_html=True)

st.divider()

st.markdown(
    """
    <section class="or-section">
        <div class="or-section-header">
            <div class="or-section-kicker">About</div>
            <div class="or-section-title">About Opportunity Radar</div>
            <div class="or-section-copy">
                Opportunity Radar analyzes product roles across top AI and tech companies and ranks them based on ownership scope,
                AI exposure, learning potential, company prestige, startup upside, and compensation potential. The goal is to help
                product operators focus their time on the highest-signal opportunities.
            </div>
        </div>
        <div class="or-panel">
            <div class="or-subtle-text">
                Scores are heuristic estimates based on role descriptions and company signals. They are meant to support
                prioritization, not replace personal judgment.
            </div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="or-footer">
        Built by Aagam Shah · <a href="https://www.linkedin.com/in/aagamshah2020/" target="_blank" rel="noopener noreferrer">Feedback on LinkedIn</a>
    </div>
    """,
    unsafe_allow_html=True,
)
