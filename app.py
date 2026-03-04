import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
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
  h1, h2, h3 { font-family: 'IBM Plex Mono', monospace !important; }

  .metric-card {
    background: linear-gradient(135deg, #111318 0%, #161b22 100%);
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
    margin-bottom: 8px;
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
  }
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


# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_prices():
    tickers = {
        "Brent":       "BZ=F",
        "WTI":         "CL=F",
        "Gás Natural": "NG=F",
        "EUR/USD":     "EURUSD=X",
    }
    result = {}
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="1mo", interval="1d")
            if len(data) >= 2:
                curr = data["Close"].iloc[-1]
                prev = data["Close"].iloc[-2]
                result[name] = {
                    "price": curr,
                    "delta": curr - prev,
                    "pct": (curr - prev) / prev * 100,
                }
        except:
            pass
    return result


@st.cache_data(ttl=300)
def fetch_history(ticker: str, period: str = "3mo"):
    try:
        df = yf.Ticker(ticker).history(period=period)
        return df[["Close"]].reset_index()
    except:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def fetch_news():
    feeds = [
        ("Reuters",    "https://feeds.reuters.com/reuters/businessNews"),
        ("EIA",        "https://www.eia.gov/rss/news.xml"),
        ("OilPrice",   "https://oilprice.com/rss/main"),
        ("Rigzone",    "https://www.rigzone.com/news/rss/rigzone_latest.aspx"),
    ]
    articles = []
    for source, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                try:
                    dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") and entry.published_parsed else None
                except:
                    dt = None
                articles.append({
                    "source": source,
                    "title": entry.get("title", ""),
                    "link":  entry.get("link", "#"),
                    "date":  dt,
                })
        except:
            pass
    articles.sort(key=lambda x: x["date"] or datetime.min, reverse=True)
    return articles


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom: 28px; padding-top: 8px;">
  <div style="display:flex; align-items:baseline; gap:16px; margin-bottom:4px;">
    <span style="font-family:'IBM Plex Mono',monospace; font-size:26px; font-weight:600; color:#f1f5f9;">🛢️ OIL MARKET INTELLIGENCE</span>
    <span style="font-size:13px; color:#6b7280;"><span class="live-dot"></span>Live · Galp Refining Business Office</span>
  </div>
  <div style="font-size:12px; color:#4b5563; font-family:'IBM Plex Mono',monospace;">
    Brent · WTI · Agregação de Notícias · Driver da Margem de Refinação · Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("A carregar dados de mercado..."):
    prices = fetch_prices()
    news   = fetch_news()

# ── Price metrics ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Preços de Mercado</div>', unsafe_allow_html=True)

cols = st.columns(4)
units = {"Brent": "$/bbl", "WTI": "$/bbl", "Gás Natural": "$/MMBtu", "EUR/USD": "taxa"}
for i, (key, unit) in enumerate(units.items()):
    with cols[i]:
        if key in prices:
            p = prices[key]
            cls   = "metric-delta-pos" if p["delta"] >= 0 else "metric-delta-neg"
            arrow = "▲" if p["delta"] >= 0 else "▼"
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{key} · {unit}</div>
              <div class="metric-value">{p['price']:.2f}</div>
              <div class="{cls}">{arrow} {abs(p['delta']):.2f} ({p['pct']:+.2f}%)</div>
            </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Chart + News ──────────────────────────────────────────────────────────────
col_chart, col_news = st.columns([3, 2], gap="large")

with col_chart:
    st.markdown('<div class="section-header">Histórico de Preços</div>', unsafe_allow_html=True)
    period = st.selectbox("Período", ["1mo", "3mo", "6mo", "1y"], index=1, label_visibility="collapsed")
    tab1, tab2 = st.tabs(["Brent Crude", "WTI Crude"])

    for tab, ticker, name in [(tab1, "BZ=F", "Brent"), (tab2, "CL=F", "WTI")]:
        with tab:
            hist = fetch_history(ticker, period)
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
                    height=300,
                    xaxis=dict(gridcolor="#1a1f2e", showline=False),
                    yaxis=dict(gridcolor="#1a1f2e", showline=False, tickformat="$.0f"),
                    showlegend=False,
                    hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)

with col_news:
    st.markdown('<div class="section-header">Últimas Notícias</div>', unsafe_allow_html=True)

    sources = list({a["source"] for a in news})
    filtro  = st.multiselect("Filtrar fontes", options=sources, default=[], placeholder="Todas as fontes", label_visibility="collapsed")
    filtered = [a for a in news if not filtro or a["source"] in filtro]

    news_box = st.container(height=380)
    with news_box:
        for a in filtered[:20]:
            date_str = a["date"].strftime("%d %b · %H:%M") if a["date"] else ""
            st.markdown(f"""
            <div class="news-card">
              <div class="news-source">{a['source']}</div>
              <div class="news-title"><a href="{a['link']}" target="_blank">{a['title']}</a></div>
              <div class="news-date">{date_str}</div>
            </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:40px 0 20px; font-family:'IBM Plex Mono',monospace; font-size:11px; color:#374151;">
  Oil Market Intelligence · Galp Refining Business Office · Dados: Yahoo Finance + RSS Feeds
</div>
""", unsafe_allow_html=True)
