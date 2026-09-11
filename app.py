"""
The frontend: a Streamlit dashboard for a business owner.

Paste customer reviews (one per line), click Analyze, and see the results.
This app does NOT call Gemini directly. It calls OUR OWN backend (api.py),
exactly the way we called external APIs in Lesson 9.

Run it (in a SECOND terminal, while api.py is also running):
    uv run streamlit run app.py
"""

from collections import Counter
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Our own database code, kept in a separate file (database.py).
from database import init_db, save_results, load_history, DB_FILE

# ─── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Customer Feedback Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# The address of our own backend service.
API_URL = "http://127.0.0.1:8000/analysis"

# Make sure the table exists before the app uses it.
init_db()

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Import Google Fonts ─────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global Overrides ────────────────────────────────────────────────── */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 40%, #24243e 100%);
    }

    /* ── Header ──────────────────────────────────────────────────────────── */
    .hero-header {
        text-align: center;
        padding: 2.5rem 1rem 1rem 1rem;
        margin-bottom: 1.5rem;
    }

    .hero-header h1 {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
        letter-spacing: -0.5px;
    }

    .hero-header p {
        color: #a0aec0;
        font-size: 1.05rem;
        font-weight: 300;
        letter-spacing: 0.3px;
    }

    .hero-divider {
        width: 80px;
        height: 3px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        margin: 0.8rem auto;
        border-radius: 2px;
    }

    /* ── Glass Card ──────────────────────────────────────────────────────── */
    .glass-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.8rem;
        margin-bottom: 1.2rem;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }

    .glass-card-header {
        font-size: 1.15rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ── KPI Metric Cards ────────────────────────────────────────────────── */
    .kpi-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        border-radius: 14px 14px 0 0;
    }

    .kpi-card:hover {
        transform: translateY(-4px);
        border-color: rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
    }

    .kpi-card.purple::before { background: linear-gradient(90deg, #667eea, #764ba2); }
    .kpi-card.green::before  { background: linear-gradient(90deg, #38b2ac, #48bb78); }
    .kpi-card.amber::before  { background: linear-gradient(90deg, #ed8936, #ecc94b); }
    .kpi-card.pink::before   { background: linear-gradient(90deg, #ed64a6, #f093fb); }

    .kpi-value {
        font-size: 2.4rem;
        font-weight: 800;
        color: #f7fafc;
        line-height: 1.1;
        margin: 0.5rem 0 0.3rem 0;
    }

    .kpi-label {
        font-size: 0.78rem;
        font-weight: 500;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }

    .kpi-icon {
        font-size: 1.6rem;
        margin-bottom: 0.2rem;
    }

    /* ── Sentiment Badges ────────────────────────────────────────────────── */
    .badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    .badge-positive {
        background: rgba(72, 187, 120, 0.15);
        color: #68d391;
        border: 1px solid rgba(72, 187, 120, 0.3);
    }

    .badge-negative {
        background: rgba(245, 101, 101, 0.15);
        color: #fc8181;
        border: 1px solid rgba(245, 101, 101, 0.3);
    }

    .badge-neutral {
        background: rgba(160, 174, 192, 0.15);
        color: #a0aec0;
        border: 1px solid rgba(160, 174, 192, 0.3);
    }

    .badge-error {
        background: rgba(237, 137, 54, 0.15);
        color: #ed8936;
        border: 1px solid rgba(237, 137, 54, 0.3);
    }

    /* ── Score Stars ──────────────────────────────────────────────────────── */
    .score-stars {
        color: #ecc94b;
        font-size: 0.95rem;
        letter-spacing: 1px;
    }

    /* ── Theme Tag ────────────────────────────────────────────────────────── */
    .theme-tag {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 500;
        background: rgba(102, 126, 234, 0.12);
        color: #a3bffa;
        border: 1px solid rgba(102, 126, 234, 0.25);
    }

    /* ── Review text in table ────────────────────────────────────────────── */
    .review-text {
        color: #e2e8f0;
        font-size: 0.9rem;
        line-height: 1.5;
        max-width: 400px;
    }

    /* ── Top Theme Callout ───────────────────────────────────────────────── */
    .top-theme-callout {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
        border: 1px solid rgba(102, 126, 234, 0.25);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-top: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }

    .top-theme-callout .icon { font-size: 1.5rem; }

    .top-theme-callout .text {
        color: #cbd5e0;
        font-size: 0.95rem;
    }

    .top-theme-callout .text strong {
        color: #a3bffa;
        font-weight: 700;
        text-transform: capitalize;
    }

    /* ── Section Titles ──────────────────────────────────────────────────── */
    .section-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 2rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }

    /* ── Table Styles ────────────────────────────────────────────────────── */
    .results-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .results-table th {
        background: rgba(102, 126, 234, 0.1);
        color: #a0aec0;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        padding: 14px 18px;
        text-align: left;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    .results-table td {
        padding: 14px 18px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        vertical-align: middle;
    }

    .results-table tr:last-child td {
        border-bottom: none;
    }

    .results-table tr:hover td {
        background: rgba(102, 126, 234, 0.05);
    }

    /* ── Streamlit Overrides ─────────────────────────────────────────────── */
    .stTextArea textarea,
    .stTextArea [data-testid="stTextArea"] textarea,
    div[data-testid="stTextArea"] textarea {
        background-color: #1a1a3e !important;
        background: #1a1a3e !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
        color: #f0f0f5 !important;
        -webkit-text-fill-color: #f0f0f5 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.92rem !important;
        padding: 1rem !important;
        caret-color: #667eea !important;
        transition: border-color 0.3s ease !important;
    }

    .stTextArea textarea::placeholder {
        color: #5a5a7a !important;
        -webkit-text-fill-color: #5a5a7a !important;
    }

    .stTextArea textarea:focus {
        border-color: rgba(102, 126, 234, 0.6) !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15) !important;
    }

    .stTextArea label,
    .stTextArea [data-testid="stWidgetLabel"] {
        color: #a0aec0 !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.7rem 2.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.45) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── Expander ─────────────────────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-weight: 500 !important;
    }

    /* ── Footer ──────────────────────────────────────────────────────────── */
    .app-footer {
        text-align: center;
        padding: 2rem 1rem;
        margin-top: 3rem;
        color: #4a5568;
        font-size: 0.8rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    .app-footer a {
        color: #667eea;
        text-decoration: none;
    }

    /* ── Hide Streamlit defaults ──────────────────────────────────────────── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] {
        background: rgba(15, 12, 41, 0.8);
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)


# ─── Utility Functions ──────────────────────────────────────────────────────────
def get_badge_html(label: str) -> str:
    """Return a colored HTML badge for a sentiment label."""
    css_class = f"badge-{label}" if label in ("positive", "negative", "neutral") else "badge-error"
    return f'<span class="badge {css_class}">{label}</span>'


def get_stars_html(score: int) -> str:
    """Return star icons for a numeric 1-5 score."""
    if score == 0:
        return '<span class="score-stars">—</span>'
    filled = "★" * score
    empty = "☆" * (5 - score)
    return f'<span class="score-stars">{filled}{empty}</span>'


def get_theme_html(theme: str) -> str:
    """Return a styled tag for the review theme."""
    if theme == "error":
        return '<span class="theme-tag" style="color:#ed8936;border-color:rgba(237,137,54,0.25);">error</span>'
    return f'<span class="theme-tag">{theme}</span>'


# ─── Hero Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <h1>📊 Customer Feedback Analyzer</h1>
    <div class="hero-divider"></div>
    <p>Transform raw customer reviews into actionable business intelligence — powered by AI</p>
</div>
""", unsafe_allow_html=True)


# ─── Input Section ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="glass-card-header">✍️ Paste Customer Reviews</div>
""", unsafe_allow_html=True)

reviews_text = st.text_area(
    "Enter reviews (one per line)",
    height=180,
    placeholder="The food was delicious but the delivery took over an hour...\nAmazing taste and the order arrived hot and early...\nPrices have gone up too much for the same small portion..."
)

col_btn, col_spacer = st.columns([1, 4])
with col_btn:
    analyze_clicked = st.button("🔍  Analyze Reviews", use_container_width=True)


# ─── Analysis Logic ─────────────────────────────────────────────────────────────
if analyze_clicked:
    # Split the text box into separate reviews, ignoring blank lines.
    reviews = [line.strip() for line in reviews_text.split("\n") if line.strip()]

    if not reviews:
        st.warning("⚠️ Please paste at least one review before analyzing.")
    else:
        results = []
        progress_bar = st.progress(0, text="Analyzing reviews...")

        # Go through each review and ask our backend to analyze it.
        for i, review in enumerate(reviews):
            try:
                response = requests.post(API_URL, json={"text": review})
                data = response.json()
                results.append({
                    "review": review,
                    "label": data["label"],
                    "score": data["score"],
                    "theme": data["theme"],
                })
            except Exception:
                # One bad review should not stop the whole batch.
                results.append({
                    "review": review,
                    "label": "error",
                    "score": 0,
                    "theme": "error",
                })
            progress_bar.progress(
                (i + 1) / len(reviews),
                text=f"Analyzing review {i + 1} of {len(reviews)}..."
            )

        progress_bar.empty()

        # Save results in session_state so they survive button clicks.
        st.session_state.results = results
        st.toast(f"✅ Successfully analyzed {len(results)} reviews!", icon="🎉")


# ─── Results Display ────────────────────────────────────────────────────────────
if "results" in st.session_state:
    results = st.session_state.results

    # ── Compute aggregates ──
    valid = [r for r in results if r["label"] != "error"]
    scores = [r["score"] for r in valid]
    positive = [r for r in valid if r["label"] == "positive"]
    negative = [r for r in valid if r["label"] == "negative"]
    neutral = [r for r in valid if r["label"] == "neutral"]
    themes = [r["theme"] for r in valid]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    pct_positive = round(len(positive) / len(results) * 100) if results else 0

    # ── KPI Metrics Row ──
    st.markdown('<div class="section-title">📈 Performance Overview</div>', unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f'<div class="kpi-card purple"><div class="kpi-icon">📋</div><div class="kpi-value">{len(results)}</div><div class="kpi-label">Total Reviews</div></div>', unsafe_allow_html=True)

    with k2:
        st.markdown(f'<div class="kpi-card green"><div class="kpi-icon">⭐</div><div class="kpi-value">{avg_score}</div><div class="kpi-label">Avg. Score</div></div>', unsafe_allow_html=True)

    with k3:
        st.markdown(f'<div class="kpi-card amber"><div class="kpi-icon">😊</div><div class="kpi-value">{pct_positive}%</div><div class="kpi-label">Positive</div></div>', unsafe_allow_html=True)

    with k4:
        st.markdown(f'<div class="kpi-card pink"><div class="kpi-icon">😟</div><div class="kpi-value">{len(negative)}</div><div class="kpi-label">Negative</div></div>', unsafe_allow_html=True)

    # ── Top Theme Callout ──
    if themes:
        theme_counts = Counter(themes)
        top_theme, top_count = theme_counts.most_common(1)[0]
        st.markdown(f'<div class="top-theme-callout"><div class="icon">🎯</div><div class="text">Customers talk most about <strong>{top_theme}</strong> — mentioned in {top_count} of {len(valid)} reviews</div></div>', unsafe_allow_html=True)

    # ── Charts Row ──
    st.markdown('<div class="section-title">📊 Visual Insights</div>', unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Sentiment Donut Chart — filter out zero-value segments to prevent label overlap
        if valid:
            all_sentiments = {"Positive": (len(positive), "#48bb78"), "Neutral": (len(neutral), "#a0aec0"), "Negative": (len(negative), "#fc8181")}
            filtered = {k: v for k, v in all_sentiments.items() if v[0] > 0}
            chart_labels = list(filtered.keys())
            chart_values = [v[0] for v in filtered.values()]
            chart_colors = [v[1] for v in filtered.values()]

            fig_donut = go.Figure(data=[go.Pie(
                labels=chart_labels,
                values=chart_values,
                hole=0.6,
                marker=dict(colors=chart_colors, line=dict(color='rgba(15,12,41,1)', width=2)),
                textinfo='label+percent',
                textposition='outside',
                textfont=dict(size=13, family="Inter", color="#e2e8f0"),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
            )])

            fig_donut.update_layout(
                title=dict(text="Sentiment Distribution", font=dict(size=15, color="#a0aec0", family="Inter"), x=0.5),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(font=dict(color="#a0aec0", size=12, family="Inter"), orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                margin=dict(t=60, b=40, l=40, r=40),
                height=370,
                annotations=[dict(text=f"<b>{len(valid)}</b><br>Reviews", x=0.5, y=0.5, font_size=18, font_color="#e2e8f0", font_family="Inter", showarrow=False)],
            )

            st.plotly_chart(fig_donut, use_container_width=True, key="donut_chart")

    with chart_col2:
        # Theme Bar Chart
        if themes:
            theme_counts = Counter(themes)
            theme_df = pd.DataFrame(theme_counts.most_common(8), columns=["Theme", "Count"])

            fig_bar = px.bar(
                theme_df,
                x="Count",
                y="Theme",
                orientation="h",
                color="Count",
                color_continuous_scale=["#4a5568", "#667eea", "#764ba2"],
            )

            fig_bar.update_layout(
                title=dict(text="Top Feedback Themes", font=dict(size=15, color="#a0aec0", family="Inter"), x=0.5),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                coloraxis_showscale=False,
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="", tickfont=dict(color="#a0aec0", family="Inter")),
                yaxis=dict(showgrid=False, title="", tickfont=dict(color="#e2e8f0", size=13, family="Inter"), autorange="reversed"),
                margin=dict(t=50, b=40, l=20, r=20),
                height=370,
            )

            fig_bar.update_traces(
                marker_line_width=0,
                hovertemplate="<b>%{y}</b><br>Mentions: %{x}<extra></extra>",
            )

            st.plotly_chart(fig_bar, use_container_width=True, key="bar_chart")

    # ── Detailed Results Table ──
    st.markdown('<div class="section-title">📝 Detailed Results</div>', unsafe_allow_html=True)

    # Build HTML table rows — NO indentation to prevent Markdown code-block rendering
    table_rows = ""
    for r in results:
        review_short = r["review"] if len(r["review"]) <= 100 else r["review"][:97] + "..."
        badge = get_badge_html(r['label'])
        stars = get_stars_html(r['score'])
        theme = get_theme_html(r['theme'])
        table_rows += f'<tr><td><div class="review-text">{review_short}</div></td><td>{badge}</td><td>{stars}</td><td>{theme}</td></tr>'

    table_html = f'<div class="glass-card" style="padding:0;overflow:hidden;"><table class="results-table"><thead><tr><th style="width:50%">Review</th><th>Sentiment</th><th>Score</th><th>Theme</th></tr></thead><tbody>{table_rows}</tbody></table></div>'
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Save to Database ──
    st.markdown("")  # Spacer
    save_col1, save_col2 = st.columns([1, 4])
    with save_col1:
        if st.button("💾  Save to Database", use_container_width=True):
            save_results(results)
            st.toast(f"Saved {len(results)} reviews to {DB_FILE}", icon="💾")
            st.success(f"✅ Saved {len(results)} reviews to `{DB_FILE}` successfully!")


# ─── History Section ─────────────────────────────────────────────────────────────
st.markdown("")  # Spacer

with st.expander("📚  Saved History — All Reviews in Database", expanded=False):
    history = load_history()
    if history:
        st.markdown(f'<div style="color:#a0aec0;font-size:0.85rem;margin-bottom:1rem;">Total records archived: <strong style="color:#e2e8f0;">{len(history)}</strong></div>', unsafe_allow_html=True)

        history_df = pd.DataFrame(
            [{"Review": r[0], "Label": r[1], "Score": r[2], "Theme": r[3]} for r in history]
        )
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Review": st.column_config.TextColumn("Review", width="large"),
                "Label": st.column_config.TextColumn("Sentiment"),
                "Score": st.column_config.NumberColumn("Score", format="%d ⭐"),
                "Theme": st.column_config.TextColumn("Theme"),
            }
        )
    else:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #4a5568;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📭</div>
            <p>No reviews saved yet. Analyze some reviews and click <strong>Save to Database</strong>.</p>
        </div>
        """, unsafe_allow_html=True)


# ─── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-footer">
    Customer Feedback Analyzer  ·  Powered by <a href="https://ai.google.dev/">Google Gemini</a>  ·  Built with FastAPI & Streamlit<br>
    <span style="font-size: 0.72rem; color: #2d3748;">© {datetime.now().year} All Rights Reserved</span>
</div>
""", unsafe_allow_html=True)
