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
  .metric-card-green::before {
    background: linear-gradient(90deg, #22c55e, #4ade80) !important;
  }
  .metric-card-blue::before {
    background: linear-gradient(90deg, #3b82f6, #60a5fa) !important;
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
  .info-box {
    background: #0f1923;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 13px;
    color: #93c5fd;
    margin-bottom: 16px;
    line-height: 1.6;
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
        "Brent":         "BZ=F",
        "WTI":           "CL=F",
        "Gás Natural":   "NG=F",
        "EUR/USD":       "EURUSD=X",
        "Gasóleo (HO)":  "HO=F",
        "Gasolina (RB)": "RB=F",
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
                    "pct":   (curr - prev) / prev * 100,
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


@st.cache_data(ttl=300)
def fetch_crack_spreads(period: str = "3mo"):
    try:
        brent = yf.Ticker("BZ=F").history(period=period)[["Close"]].rename(columns={"Close": "Brent"})
        ho    = yf.Ticker("HO=F").history(period=period)[["Close"]].rename(columns={"Close": "HO"})
        rb    = yf.Ticker("RB=F").history(period=period)[["Close"]].rename(columns={"Close": "RB"})

        df = brent.join(ho, how="inner").join(rb, how="inner")
        df.index = pd.to_datetime(df.index).tz_localize(None)

        df["HO_bbl"] = df["HO"] * 42
        df["RB_bbl"] = df["RB"] * 42

        df["Gasóleo Crack"]  = df["HO_bbl"] - df["Brent"]
        df["Gasolina Crack"] = df["RB_bbl"] - df["Brent"]
        df["3-2-1 Crack"]    = (2 * df["RB_bbl"] + df["HO_bbl"]) / 3 - df["Brent"]

        return df.reset_index()
    except:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def fetch_news():
    feeds = [
        ("Reuters",  "https://feeds.reuters.com/reuters/businessNews"),
        ("EIA",      "https://www.eia.gov/rss/news.xml"),
        ("OilPrice", "https://oilprice.com/rss/main"),
        ("Rigzone",  "https://www.rigzone.com/news/rss/rigzone_latest.aspx"),
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
    Brent · WTI · Crack Spreads · Produtos Refinados · Notícias · Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("A carregar dados de mercado..."):
    prices = fetch_prices()
    news   = fetch_news()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_mercado, tab_crack, tab_produtos, tab_noticias = st.tabs([
    "📈 Mercado",
    "⚗️ Crack Spreads",
    "🏭 Produtos Refinados",
    "📰 Notícias",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MERCADO
# ═══════════════════════════════════════════════════════════════════════════════
with tab_mercado:
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
    st.markdown('<div class="section-header">Histórico Brent vs WTI</div>', unsafe_allow_html=True)

    period = st.selectbox("Período", ["1mo", "3mo", "6mo", "1y"], index=1, label_visibility="collapsed")
    brent_h = fetch_history("BZ=F", period)
    wti_h   = fetch_history("CL=F", period)

    if not brent_h.empty and not wti_h.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=brent_h["Date"], y=brent_h["Close"],
            name="Brent", line=dict(color="#f97316", width=2),
            fill="tozeroy", fillcolor="rgba(249,115,22,0.05)"))
        fig.add_trace(go.Scatter(x=wti_h["Date"], y=wti_h["Close"],
            name="WTI", line=dict(color="#3b82f6", width=2)))
        fig.update_layout(
            paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
            font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
            margin=dict(l=0, r=0, t=10, b=0), height=320,
            xaxis=dict(gridcolor="#1a1f2e", showline=False),
            yaxis=dict(gridcolor="#1a1f2e", showline=False, tickformat="$.0f"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9ca3af")),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Spread Brent — WTI</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">O spread Brent-WTI reflecte diferenças de qualidade e logística. Um spread elevado favorece refinarias europeias que usam Brent como referência de custo de crude.</div>', unsafe_allow_html=True)

    if not brent_h.empty and not wti_h.empty:
        merged = brent_h.merge(wti_h, on="Date", suffixes=("_brent", "_wti"))
        merged["spread"] = merged["Close_brent"] - merged["Close_wti"]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=merged["Date"], y=merged["spread"],
            line=dict(color="#a78bfa", width=2),
            fill="tozeroy", fillcolor="rgba(167,139,250,0.08)",
        ))
        fig2.add_hline(y=0, line_dash="dash", line_color="#374151")
        fig2.update_layout(
            paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
            font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
            margin=dict(l=0, r=0, t=10, b=0), height=200,
            xaxis=dict(gridcolor="#1a1f2e", showline=False),
            yaxis=dict(gridcolor="#1a1f2e", showline=False, tickformat="$.2f"),
            showlegend=False, hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CRACK SPREADS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_crack:
    st.markdown('<div class="info-box">💡 <strong>O que são crack spreads?</strong> É a diferença entre o preço dos produtos refinados e o preço do crude — é a <strong>margem bruta de refinação</strong>. Um valor positivo e elevado significa que refinar é lucrativo. O <strong>3-2-1 crack spread</strong> é o benchmark da indústria: por cada 3 barris de crude, produzem-se 2 de gasolina e 1 de gasóleo.</div>', unsafe_allow_html=True)

    period_crack = st.selectbox("Período", ["1mo", "3mo", "6mo", "1y"], index=1, key="crack_period", label_visibility="collapsed")

    with st.spinner("A calcular crack spreads..."):
        df_crack = fetch_crack_spreads(period_crack)

    if not df_crack.empty:
        st.markdown('<div class="section-header">Crack Spreads Actuais ($/bbl)</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)

        for col, key, label, extra_class in [
            (c1, "3-2-1 Crack",    "3-2-1 Crack Spread",   "metric-card"),
            (c2, "Gasóleo Crack",  "Gasóleo Crack Spread",  "metric-card metric-card-green"),
            (c3, "Gasolina Crack", "Gasolina Crack Spread", "metric-card metric-card-blue"),
        ]:
            with col:
                val   = df_crack[key].iloc[-1]
                prev  = df_crack[key].iloc[-2]
                delta = val - prev
                cls   = "metric-delta-pos" if delta >= 0 else "metric-delta-neg"
                arrow = "▲" if delta >= 0 else "▼"
                st.markdown(f"""
                <div class="{extra_class}">
                  <div class="metric-label">{label}</div>
                  <div class="metric-value">${val:.2f}</div>
                  <div class="{cls}">{arrow} ${abs(delta):.2f} vs dia anterior</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Evolução Histórica</div>', unsafe_allow_html=True)

        fig_crack = go.Figure()
        fig_crack.add_trace(go.Scatter(x=df_crack["Date"], y=df_crack["3-2-1 Crack"],
            name="3-2-1 Crack", line=dict(color="#f97316", width=2)))
        fig_crack.add_trace(go.Scatter(x=df_crack["Date"], y=df_crack["Gasóleo Crack"],
            name="Gasóleo", line=dict(color="#4ade80", width=2)))
        fig_crack.add_trace(go.Scatter(x=df_crack["Date"], y=df_crack["Gasolina Crack"],
            name="Gasolina", line=dict(color="#60a5fa", width=2)))
        fig_crack.add_hline(y=0, line_dash="dash", line_color="#374151")
        fig_crack.update_layout(
            paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
            font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
            margin=dict(l=0, r=0, t=10, b=0), height=350,
            xaxis=dict(gridcolor="#1a1f2e", showline=False),
            yaxis=dict(gridcolor="#1a1f2e", showline=False, tickformat="$.0f"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9ca3af")),
            hovermode="x unified",
        )
        st.plotly_chart(fig_crack, use_container_width=True)

        st.markdown('<div class="section-header">Resumo Estatístico</div>', unsafe_allow_html=True)
        resumo = pd.DataFrame({
            "Crack Spread":    ["3-2-1 Crack", "Gasóleo Crack", "Gasolina Crack"],
            "Actual ($/bbl)":  [f"${df_crack['3-2-1 Crack'].iloc[-1]:.2f}",  f"${df_crack['Gasóleo Crack'].iloc[-1]:.2f}",  f"${df_crack['Gasolina Crack'].iloc[-1]:.2f}"],
            "Média Período":   [f"${df_crack['3-2-1 Crack'].mean():.2f}",     f"${df_crack['Gasóleo Crack'].mean():.2f}",     f"${df_crack['Gasolina Crack'].mean():.2f}"],
            "Máximo":          [f"${df_crack['3-2-1 Crack'].max():.2f}",      f"${df_crack['Gasóleo Crack'].max():.2f}",      f"${df_crack['Gasolina Crack'].max():.2f}"],
            "Mínimo":          [f"${df_crack['3-2-1 Crack'].min():.2f}",      f"${df_crack['Gasóleo Crack'].min():.2f}",      f"${df_crack['Gasolina Crack'].min():.2f}"],
        })
        st.dataframe(resumo, hide_index=True, use_container_width=True)
    else:
        st.warning("Não foi possível calcular os crack spreads. Tenta novamente mais tarde.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRODUTOS REFINADOS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_produtos:
    st.markdown('<div class="info-box">💡 Monitorização dos preços dos principais produtos refinados. O gasóleo (Heating Oil) e a gasolina (RBOB) são os maiores contribuintes para a margem de refinação europeia.</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Preços Actuais dos Produtos</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    for col, key, label in [
        (c1, "Gasóleo (HO)",  "Gasóleo · Heating Oil"),
        (c2, "Gasolina (RB)", "Gasolina · RBOB"),
    ]:
        with col:
            if key in prices:
                p = prices[key]
                cls   = "metric-delta-pos" if p["delta"] >= 0 else "metric-delta-neg"
                arrow = "▲" if p["delta"] >= 0 else "▼"
                price_bbl = p['price'] * 42
                delta_bbl = p['delta'] * 42
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-label">{label} · $/bbl</div>
                  <div class="metric-value">${price_bbl:.2f}</div>
                  <div class="{cls}">{arrow} ${abs(delta_bbl):.2f} ({p['pct']:+.2f}%)</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Crude vs Produtos Refinados ($/bbl)</div>', unsafe_allow_html=True)

    period_prod = st.selectbox("Período", ["1mo", "3mo", "6mo", "1y"], index=1, key="prod_period", label_visibility="collapsed")
    ho_h = fetch_history("HO=F", period_prod)
    rb_h = fetch_history("RB=F", period_prod)
    br_h = fetch_history("BZ=F", period_prod)

    if not ho_h.empty and not br_h.empty:
        fig_prod = go.Figure()
        fig_prod.add_trace(go.Scatter(x=br_h["Date"], y=br_h["Close"],
            name="Brent (crude)", line=dict(color="#f97316", width=2)))
        fig_prod.add_trace(go.Scatter(x=ho_h["Date"], y=ho_h["Close"] * 42,
            name="Gasóleo $/bbl", line=dict(color="#4ade80", width=2)))
        fig_prod.add_trace(go.Scatter(x=rb_h["Date"], y=rb_h["Close"] * 42,
            name="Gasolina $/bbl", line=dict(color="#60a5fa", width=2)))
        fig_prod.update_layout(
            paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
            font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
            margin=dict(l=0, r=0, t=10, b=0), height=350,
            xaxis=dict(gridcolor="#1a1f2e", showline=False),
            yaxis=dict(gridcolor="#1a1f2e", showline=False, tickformat="$.0f"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9ca3af")),
            hovermode="x unified",
        )
        st.plotly_chart(fig_prod, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — NOTÍCIAS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_noticias:
    st.markdown('<div class="section-header">Últimas Notícias</div>', unsafe_allow_html=True)

    sources  = list({a["source"] for a in news})
    filtro   = st.multiselect("Filtrar fontes", options=sources, default=[],
                              placeholder="Todas as fontes", label_visibility="collapsed")
    filtered = [a for a in news if not filtro or a["source"] in filtro]

    for a in filtered[:25]:
        date_str = a["date"].strftime("%d %b %Y · %H:%M") if a["date"] else ""
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
