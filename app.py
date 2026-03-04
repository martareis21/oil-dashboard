import streamlit as st
import yfinance as yf
import feedparser
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from anthropic import Anthropic

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Oil Market Intelligence",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0a0c0f;
    color: #e2e8f0;
  }

  .stApp { background-color: #0a0c0f; }

  h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    letter-spacing: -0.02em;
  }

  .metric-card {
    background: linear-gradient(135deg, #111318 0%, #161b22 100%);
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
  }
  .metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #f97316, #fb923c);
  }
  .metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #6b7280;
    margin-bottom: 8px;
  }
  .metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 28px;
    font-weight: 600;
    color: #f1f5f9;
    line-height: 1;
  }
  .metric-delta-pos { color: #4ade80; font-size: 13px; margin-top: 6px; font-family: 'IBM Plex Mono', monospace; }
  .metric-delta-neg { color: #f87171; font-size: 13px; margin-top: 6px; font-family: 'IBM Plex Mono', monospace; }

  .news-card {
    background: #111318;
    border: 1px solid #21262d;
    border-left: 3px solid #f97316;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
  }
  .news-card:hover { border-left-color: #fb923c; }
  .news-source {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #f97316;
    margin-bottom: 6px;
  }
  .news-title {
    font-size: 14px;
    font-weight: 600;
    color: #e2e8f0;
    line-height: 1.4;
    margin-bottom: 6px;
  }
  .news-title a { color: #e2e8f0; text-decoration: none; }
  .news-title a:hover { color: #fb923c; }
  .news-date {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4b5563;
  }

  .section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #f97316;
    border-bottom: 1px solid #21262d;
    padding-bottom: 8px;
    margin-bottom: 20px;
  }

  .ai-summary {
    background: linear-gradient(135deg, #0f1923 0%, #111827 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 24px;
    font-size: 14px;
    line-height: 1.8;
    color: #cbd5e1;
  }
  .ai-summary strong { color: #93c5fd; }

  .stButton > button {
    background: linear-gradient(135deg, #ea580c, #f97316) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 0.05em !important;
    padding: 10px 24px !important;
    transition: opacity 0.2s !important;
  }
  .stButton > button:hover { opacity: 0.85 !important; }

  div[data-testid="stChatMessage"] {
    background: #111318 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
  }

  .stSpinner > div { border-top-color: #f97316 !important; }

  .header-bar {
    display: flex;
    align-items: baseline;
    gap: 16px;
    margin-bottom: 4px;
  }
  .header-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 26px;
    font-weight: 600;
    color: #f1f5f9;
  }
  .header-subtitle {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    color: #6b7280;
  }
  .live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: #4ade80;
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_prices():
    tickers = {"Brent": "BZ=F", "WTI": "CL=F", "Natural Gas": "NG=F", "USD/EUR": "EURUSD=X"}
    result = {}
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="5d", interval="1d")
            if len(data) >= 2:
                curr = data["Close"].iloc[-1]
                prev = data["Close"].iloc[-2]
                result[name] = {"price": curr, "delta": curr - prev, "pct": (curr - prev) / prev * 100}
        except:
            pass
    return result


@st.cache_data(ttl=300)
def fetch_price_history(ticker_symbol: str, period: str = "3mo"):
    try:
        df = yf.Ticker(ticker_symbol).history(period=period)
        return df[["Close"]].reset_index()
    except:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def fetch_news():
    feeds = [
        ("Reuters Energy", "https://feeds.reuters.com/reuters/businessNews"),
        ("FT Markets",     "https://www.ft.com/markets?format=rss"),
        ("Google News – Oil", "https://news.google.com/rss/search?q=oil+price+crude+OPEC&hl=en-US&gl=US&ceid=US:en"),
        ("Google News – Refining", "https://news.google.com/rss/search?q=oil+refining+margin+petroleum&hl=en-US&gl=US&ceid=US:en"),
        ("EIA News",       "https://www.eia.gov/rss/news.xml"),
    ]
    articles = []
    for source, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                pub = entry.get("published", entry.get("updated", ""))
                try:
                    dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") and entry.published_parsed else None
                except:
                    dt = None
                articles.append({
                    "source": source,
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", "#"),
                    "date": dt,
                    "summary": entry.get("summary", "")[:300],
                })
        except:
            pass
    articles.sort(key=lambda x: x["date"] or datetime.min, reverse=True)
    return articles[:30]


def get_ai_summary(news_articles, prices, client):
    price_str = "\n".join([f"- {k}: ${v['price']:.2f} ({v['pct']:+.2f}%)" for k, v in prices.items()])
    headlines = "\n".join([f"- [{a['source']}] {a['title']}" for a in news_articles[:15]])

    prompt = f"""You are an oil market analyst for Galp's refining division in Lisbon.

Current market prices:
{price_str}

Latest news headlines:
{headlines}

Write a concise market intelligence briefing (4-6 paragraphs) covering:
1. Key drivers behind today's price movements
2. Geopolitical/OPEC factors at play
3. Implications for European refining margins (crack spreads)
4. Short-term outlook

Be direct, analytical, and specific. Format in clear paragraphs. No bullet points."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


# ── Chat with context ─────────────────────────────────────────────────────────
def chat_with_analyst(messages, prices, news_articles, client):
    price_str = "\n".join([f"- {k}: ${v['price']:.2f} ({v['pct']:+.2f}%)" for k, v in prices.items()])
    headlines = "\n".join([f"- [{a['source']}] {a['title']}" for a in news_articles[:12]])

    system = f"""You are an expert oil market analyst assistant for Galp's refining Business Office in Lisbon, Portugal.

Current live market data:
{price_str}

Today's top headlines:
{headlines}

Answer questions about oil markets, refining margins, OPEC, geopolitics affecting energy, and their impact on Galp's refining operations. Be concise and analytical."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=system,
        messages=messages,
    )
    return response.content[0].text


# ── Session state ─────────────────────────────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "ai_summary" not in st.session_state:
    st.session_state.ai_summary = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom: 28px; padding-top: 8px;">
  <div class="header-bar">
    <span class="header-title">🛢️ OIL MARKET INTELLIGENCE</span>
    <span class="header-subtitle"><span class="live-dot"></span>Live · Galp Refining Business Office</span>
  </div>
  <div style="font-size: 12px; color: #4b5563; font-family: 'IBM Plex Mono', monospace;">
    Brent · WTI · News Aggregation · AI Analysis · Refining Margin Driver
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching market data..."):
    prices = fetch_prices()
    news   = fetch_news()

# ── Price metrics row ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Market Prices</div>', unsafe_allow_html=True)

cols = st.columns(4)
labels = {
    "Brent":       ("Brent Crude", "$/bbl"),
    "WTI":         ("WTI Crude",   "$/bbl"),
    "Natural Gas": ("Nat. Gas",    "$/MMBtu"),
    "USD/EUR":     ("EUR/USD",     "rate"),
}
for i, (key, (label, unit)) in enumerate(labels.items()):
    with cols[i]:
        if key in prices:
            p = prices[key]
            delta_class = "metric-delta-pos" if p["delta"] >= 0 else "metric-delta-neg"
            arrow = "▲" if p["delta"] >= 0 else "▼"
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{label} · {unit}</div>
              <div class="metric-value">{p['price']:.2f}</div>
              <div class="{delta_class}">{arrow} {abs(p['delta']):.2f} ({p['pct']:+.2f}%)</div>
            </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts + News ─────────────────────────────────────────────────────────────
col_chart, col_news = st.columns([3, 2], gap="large")

with col_chart:
    st.markdown('<div class="section-header">Price History</div>', unsafe_allow_html=True)

    period_opt = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1, label_visibility="collapsed")
    tab1, tab2 = st.tabs(["Brent Crude", "WTI Crude"])

    for tab, ticker, name in [(tab1, "BZ=F", "Brent"), (tab2, "CL=F", "WTI")]:
        with tab:
            hist = fetch_price_history(ticker, period_opt)
            if not hist.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist["Date"], y=hist["Close"],
                    mode="lines",
                    line=dict(color="#f97316", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(249,115,22,0.08)",
                    name=name,
                ))
                fig.update_layout(
                    paper_bgcolor="#0a0c0f",
                    plot_bgcolor="#0a0c0f",
                    font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=280,
                    xaxis=dict(gridcolor="#1a1f2e", showline=False, tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="#1a1f2e", showline=False, tickformat="$.0f"),
                    showlegend=False,
                    hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)

with col_news:
    st.markdown('<div class="section-header">Latest Headlines</div>', unsafe_allow_html=True)
    source_filter = st.multiselect(
        "Filter sources", options=list({a["source"] for a in news}),
        default=[], placeholder="All sources", label_visibility="collapsed"
    )
    filtered = [a for a in news if not source_filter or a["source"] in source_filter]

    news_container = st.container(height=340)
    with news_container:
        for article in filtered[:15]:
            date_str = article["date"].strftime("%d %b · %H:%M") if article["date"] else ""
            st.markdown(f"""
            <div class="news-card">
              <div class="news-source">{article['source']}</div>
              <div class="news-title"><a href="{article['link']}" target="_blank">{article['title']}</a></div>
              <div class="news-date">{date_str}</div>
            </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── AI Analysis ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">AI Market Briefing</div>', unsafe_allow_html=True)

col_btn, col_info = st.columns([1, 4])
with col_btn:
    run_analysis = st.button("⚡ Generate Briefing")
with col_info:
    st.markdown('<span style="font-size:12px; color:#4b5563; font-family:\'IBM Plex Mono\',monospace;">Powered by Claude · Synthesizes prices + headlines into refining-focused analysis</span>', unsafe_allow_html=True)

client = Anthropic()

if run_analysis:
    with st.spinner("Analysing market signals..."):
        st.session_state.ai_summary = get_ai_summary(news, prices, client)

if st.session_state.ai_summary:
    st.markdown(f'<div class="ai-summary">{st.session_state.ai_summary}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Chat ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Ask the Analyst</div>', unsafe_allow_html=True)
st.markdown('<span style="font-size:12px; color:#4b5563;">Ask anything about oil markets, crack spreads, OPEC, or refining margins.</span>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("E.g. 'What's driving Brent today?' or 'How does this affect crack spreads?'"):
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = chat_with_analyst(st.session_state.chat_messages, prices, news, client)
        st.markdown(reply)
    st.session_state.chat_messages.append({"role": "assistant", "content": reply})

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 40px 0 20px; font-family:'IBM Plex Mono',monospace; font-size:11px; color:#374151;">
  Oil Market Intelligence · Galp Refining Business Office · Data: Yahoo Finance + RSS Feeds · AI: Claude
</div>
""", unsafe_allow_html=True)
