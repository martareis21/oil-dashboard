import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Oil Market Intelligence",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
  html, body, [class*="css"] { font-family:'IBM Plex Sans',sans-serif; background-color:#0a0c0f; color:#e2e8f0; }
  .stApp { background-color:#0a0c0f; }
  h1,h2,h3 { font-family:'IBM Plex Mono',monospace !important; }

  .metric-card {
    background:linear-gradient(135deg,#111318 0%,#161b22 100%);
    border:1px solid #21262d; border-radius:12px; padding:20px 24px;
    position:relative; overflow:hidden; margin-bottom:8px;
  }
  .metric-card::before { content:''; position:absolute; top:0;left:0;right:0; height:2px; background:linear-gradient(90deg,#f97316,#fb923c); }
  .mc-green::before { background:linear-gradient(90deg,#22c55e,#4ade80) !important; }
  .mc-blue::before  { background:linear-gradient(90deg,#3b82f6,#60a5fa) !important; }
  .mc-purple::before{ background:linear-gradient(90deg,#a855f7,#c084fc) !important; }
  .mc-yellow::before{ background:linear-gradient(90deg,#eab308,#facc15) !important; }

  .metric-label { font-family:'IBM Plex Mono',monospace; font-size:11px; text-transform:uppercase; letter-spacing:.12em; color:#6b7280; margin-bottom:8px; }
  .metric-value { font-family:'IBM Plex Mono',monospace; font-size:26px; font-weight:600; color:#f1f5f9; line-height:1; }
  .metric-sub   { font-family:'IBM Plex Mono',monospace; font-size:12px; color:#9ca3af; margin-top:4px; }
  .dpos { color:#4ade80; font-size:13px; margin-top:6px; font-family:'IBM Plex Mono',monospace; }
  .dneg { color:#f87171; font-size:13px; margin-top:6px; font-family:'IBM Plex Mono',monospace; }

  .news-card { background:#111318; border:1px solid #21262d; border-left:3px solid #f97316; border-radius:8px; padding:16px 20px; margin-bottom:12px; }
  .news-source { font-family:'IBM Plex Mono',monospace; font-size:10px; text-transform:uppercase; letter-spacing:.1em; color:#f97316; margin-bottom:6px; }
  .news-title  { font-size:14px; font-weight:600; color:#e2e8f0; line-height:1.4; margin-bottom:6px; }
  .news-title a { color:#e2e8f0; text-decoration:none; }
  .news-title a:hover { color:#fb923c; }
  .news-date { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#4b5563; }

  .section-header { font-family:'IBM Plex Mono',monospace; font-size:11px; text-transform:uppercase; letter-spacing:.15em; color:#f97316; border-bottom:1px solid #21262d; padding-bottom:8px; margin-bottom:20px; }
  .info-box { background:#0f1923; border:1px solid #1e3a5f; border-radius:8px; padding:14px 18px; font-size:13px; color:#93c5fd; margin-bottom:16px; line-height:1.6; }
  .warn-box { background:#1a1200; border:1px solid #854d0e; border-radius:8px; padding:14px 18px; font-size:13px; color:#fbbf24; margin-bottom:16px; line-height:1.6; }

  .crude-card { background:#111318; border:1px solid #21262d; border-radius:10px; padding:18px 20px; margin-bottom:10px; }
  .crude-name { font-family:'IBM Plex Mono',monospace; font-size:14px; font-weight:600; color:#f1f5f9; margin-bottom:6px; }
  .crude-origin { font-size:12px; color:#6b7280; margin-bottom:10px; }
  .crude-bar-bg { background:#1f2937; border-radius:4px; height:8px; margin-bottom:8px; }
  .crude-bar { height:8px; border-radius:4px; }

  .live-dot { display:inline-block; width:8px;height:8px; background:#4ade80; border-radius:50%; margin-right:6px; animation:pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def make_fig(height=300):
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
        font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
        margin=dict(l=0, r=0, t=10, b=0), height=height,
        xaxis=dict(gridcolor="#1a1f2e", showline=False),
        yaxis=dict(gridcolor="#1a1f2e", showline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9ca3af")),
        hovermode="x unified",
    )
    return fig


# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_prices():
    tickers = {
        "Brent": "BZ=F", "WTI": "CL=F",
        "Gás Natural": "NG=F", "EUR/USD": "EURUSD=X",
        "Gasóleo (HO)": "HO=F", "Gasolina (RB)": "RB=F",
    }
    result = {}
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="1mo", interval="1d")
            if len(data) >= 2:
                curr, prev = data["Close"].iloc[-1], data["Close"].iloc[-2]
                result[name] = {"price": curr, "delta": curr-prev, "pct": (curr-prev)/prev*100}
        except:
            pass
    return result


@st.cache_data(ttl=300)
def fetch_history(ticker, period="3mo"):
    try:
        df = yf.Ticker(ticker).history(period=period)
        return df[["Close"]].reset_index()
    except:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_crack_spreads(period="3mo"):
    try:
        brent = yf.Ticker("BZ=F").history(period=period)[["Close"]].rename(columns={"Close":"Brent"})
        ho    = yf.Ticker("HO=F").history(period=period)[["Close"]].rename(columns={"Close":"HO"})
        rb    = yf.Ticker("RB=F").history(period=period)[["Close"]].rename(columns={"Close":"RB"})
        df = brent.join(ho, how="inner").join(rb, how="inner")
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df["HO_bbl"] = df["HO"] * 42
        df["RB_bbl"] = df["RB"] * 42
        df["Gasóleo Crack"]  = df["HO_bbl"] - df["Brent"]
        df["Gasolina Crack"] = df["RB_bbl"] - df["Brent"]
        df["3-2-1 Crack"]    = (2*df["RB_bbl"] + df["HO_bbl"]) / 3 - df["Brent"]
        return df.reset_index()
    except:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def fetch_news():
    feeds = [
        ("Reuters","https://feeds.reuters.com/reuters/businessNews"),
        ("EIA","https://www.eia.gov/rss/news.xml"),
        ("OilPrice","https://oilprice.com/rss/main"),
        ("Rigzone","https://www.rigzone.com/news/rss/rigzone_latest.aspx"),
    ]
    articles = []
    for source, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                try:
                    dt = datetime(*entry.published_parsed[:6]) if hasattr(entry,"published_parsed") and entry.published_parsed else None
                except:
                    dt = None
                articles.append({"source":source,"title":entry.get("title",""),"link":entry.get("link","#"),"date":dt})
        except:
            pass
    articles.sort(key=lambda x: x["date"] or datetime.min, reverse=True)
    return articles


@st.cache_data(ttl=300)
def fetch_benchmark_margins(period="6mo"):
    """
    Proxy para margens de refinação europeias:
    - Med Complex Margin proxy: 3-2-1 crack spread (já calculado)
    - NW Europe proxy: baseado nos mesmos produtos mas com diferencial
    - Sines proxy: 3-2-1 com ajuste geográfico estimado
    Nota: valores reais vêm da Argus/Platts (pagos). Estes são proxies públicos.
    """
    try:
        brent = yf.Ticker("BZ=F").history(period=period)[["Close"]].rename(columns={"Close":"Brent"})
        ho    = yf.Ticker("HO=F").history(period=period)[["Close"]].rename(columns={"Close":"HO"})
        rb    = yf.Ticker("RB=F").history(period=period)[["Close"]].rename(columns={"Close":"RB"})
        df = brent.join(ho, how="inner").join(rb, how="inner")
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df["HO_bbl"] = df["HO"] * 42
        df["RB_bbl"] = df["RB"] * 42
        # 3-2-1 base
        base = (2*df["RB_bbl"] + df["HO_bbl"]) / 3 - df["Brent"]
        # Proxies regionais com diferenciais históricos típicos
        df["Med Cracking (proxy)"]   = base - 1.5   # Mediterrâneo tipicamente ~$1-2 abaixo do NWE
        df["NW Europe (proxy)"]      = base
        df["Sines Proxy"]            = base - 0.8   # Sines entre Med e NWE
        return df.reset_index()
    except:
        return pd.DataFrame()


def crude_sourcing_analysis(prices):
    """
    Análise de custo efectivo de crudes alternativos chegados a Sines.
    Preço efectivo = preço crude + diferencial de qualidade + frete estimado
    Fontes: diferenciais típicos de mercado, fretes estimados (VLCC/Suezmax)
    """
    brent_price = prices.get("Brent", {}).get("price", 80)

    crudes = [
        {
            "nome": "Brent Dated",
            "origem": "🇬🇧 Mar do Norte",
            "diferencial": 0.0,
            "frete_bbl": 0.8,
            "qualidade": "Sweet / Light — API 38, S 0.37%",
            "notas": "Benchmark europeu. Referência base para Sines.",
            "cor": "#f97316",
            "risco": "Baixo",
        },
        {
            "nome": "Urals",
            "origem": "🇷🇺 Rússia (sancionado UE)",
            "diferencial": -12.0,
            "frete_bbl": 2.5,
            "qualidade": "Medium Sour — API 31, S 1.35%",
            "notas": "⚠️ Sancionado pela UE desde 2022. Não aplicável à Galp.",
            "cor": "#ef4444",
            "risco": "Muito Alto",
        },
        {
            "nome": "Arabian Light",
            "origem": "🇸🇦 Arábia Saudita",
            "diferencial": -1.5,
            "frete_bbl": 2.2,
            "qualidade": "Medium Sour — API 33, S 1.77%",
            "notas": "Crude OPEP premium. Frete via Suez ou cabo.",
            "cor": "#3b82f6",
            "risco": "Médio",
        },
        {
            "nome": "Arabian Heavy",
            "origem": "🇸🇦 Arábia Saudita",
            "diferencial": -4.0,
            "frete_bbl": 2.2,
            "qualidade": "Heavy Sour — API 28, S 2.85%",
            "notas": "Desconto elevado mas precisa de unidades de conversão.",
            "cor": "#8b5cf6",
            "risco": "Médio",
        },
        {
            "nome": "Bonny Light",
            "origem": "🇳🇬 Nigéria",
            "diferencial": +1.0,
            "frete_bbl": 0.9,
            "qualidade": "Sweet / Light — API 35, S 0.14%",
            "notas": "Geograficamente próximo. Muito boa qualidade.",
            "cor": "#22c55e",
            "risco": "Médio-Baixo",
        },
        {
            "nome": "Cabinda",
            "origem": "🇦🇴 Angola",
            "diferencial": -0.5,
            "frete_bbl": 1.0,
            "qualidade": "Medium / Light — API 32, S 0.17%",
            "notas": "Angola é fornecedor histórico da Galp. Frete curto.",
            "cor": "#06b6d4",
            "risco": "Baixo",
        },
        {
            "nome": "CPC Blend",
            "origem": "🇰🇿 Cazaquistão",
            "diferencial": -0.8,
            "frete_bbl": 1.5,
            "qualidade": "Sweet / Light — API 45, S 0.54%",
            "notas": "Exportado via Mar Negro/Estreito de Bósforo.",
            "cor": "#f59e0b",
            "risco": "Médio",
        },
    ]

    for c in crudes:
        c["preco_efectivo"] = brent_price + c["diferencial"] + c["frete_bbl"]
        c["vs_brent"] = c["preco_efectivo"] - brent_price

    crudes_validos = [c for c in crudes if c["nome"] != "Urals"]
    crudes_validos.sort(key=lambda x: x["preco_efectivo"])

    return crudes, crudes_validos


def build_forecast(df_crack, days_ahead=30):
    """
    Forecast simples de crack spread usando média móvel + tendência linear.
    Método: regressão linear nos últimos 30 dias + sazonalidade mensal.
    """
    if df_crack.empty or len(df_crack) < 10:
        return pd.DataFrame()

    series = df_crack["3-2-1 Crack"].values
    n = len(series)

    # Tendência linear simples nos últimos 30 dias
    window = min(30, n)
    recent = series[-window:]
    x = np.arange(window)
    slope, intercept = np.polyfit(x, recent, 1)

    # Volatilidade histórica
    vol = np.std(np.diff(recent))

    # Gerar forecast
    last_date = pd.to_datetime(df_crack["Date"].iloc[-1])
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=days_ahead, freq="B")

    forecast_vals = []
    for i in range(days_ahead):
        val = series[-1] + slope * (i + 1)
        # Reverter à média histórica de longo prazo (mean reversion)
        mean_lt = np.mean(series)
        val = val * 0.7 + mean_lt * 0.3
        forecast_vals.append(val)

    # Bandas de confiança (±1.5 std)
    lower = [v - 1.5 * vol * np.sqrt(i+1) for i, v in enumerate(forecast_vals)]
    upper = [v + 1.5 * vol * np.sqrt(i+1) for i, v in enumerate(forecast_vals)]

    return pd.DataFrame({
        "Date": future_dates,
        "Forecast": forecast_vals,
        "Lower": lower,
        "Upper": upper,
    })


# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("A carregar dados de mercado..."):
    prices = fetch_prices()
    news   = fetch_news()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:28px; padding-top:8px;">
  <div style="display:flex; align-items:baseline; gap:16px; margin-bottom:4px;">
    <span style="font-family:'IBM Plex Mono',monospace; font-size:26px; font-weight:600; color:#f1f5f9;">🛢️ OIL MARKET INTELLIGENCE</span>
    <span style="font-size:13px; color:#6b7280;"><span class="live-dot"></span>Live · Galp Refining Business Office</span>
  </div>
  <div style="font-size:12px; color:#4b5563; font-family:'IBM Plex Mono',monospace;">
    Mercado · Crack Spreads · Benchmark Margens · Crude Sourcing · Forecast · Notícias · {datetime.now().strftime("%d/%m/%Y %H:%M")}
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "📈 Market",
    "⚗️ Crack Spreads",
    "🏆 Benchmark Margens",
    "🌍 Crude Sourcing",
    "🔮 Forecast",
    "📊 Market Performance",
    "📰 News",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MERCADO
# ═══════════════════════════════════════════════════════════════════════════════
with t1:
    st.markdown('<div class="section-header">Preços de Mercado</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (key, unit) in enumerate([("Brent","$/bbl"),("WTI","$/bbl"),("Gás Natural","$/MMBtu"),("EUR/USD","taxa")]):
        with cols[i]:
            if key in prices:
                p = prices[key]
                cls = "dpos" if p["delta"]>=0 else "dneg"
                arrow = "▲" if p["delta"]>=0 else "▼"
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-label">{key} · {unit}</div>
                  <div class="metric-value">{p['price']:.2f}</div>
                  <div class="{cls}">{arrow} {abs(p['delta']):.2f} ({p['pct']:+.2f}%)</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Histórico Brent vs WTI</div>', unsafe_allow_html=True)
    period = st.selectbox("Período", ["1mo","3mo","6mo","1y"], index=1, label_visibility="collapsed")
    bh = fetch_history("BZ=F", period)
    wh = fetch_history("CL=F", period)
    if not bh.empty:
        fig = make_fig(320)
        fig.add_trace(go.Scatter(x=bh["Date"], y=bh["Close"], name="Brent", line=dict(color="#f97316",width=2), fill="tozeroy", fillcolor="rgba(249,115,22,0.05)"))
        fig.add_trace(go.Scatter(x=wh["Date"], y=wh["Close"], name="WTI",   line=dict(color="#3b82f6",width=2)))
        fig.update_layout(yaxis=dict(tickformat="$.0f"))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Spread Brent — WTI</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">O spread Brent-WTI reflecte diferenças de qualidade e logística. Um spread elevado favorece refinarias europeias.</div>', unsafe_allow_html=True)
    if not bh.empty and not wh.empty:
        m = bh.merge(wh, on="Date", suffixes=("_b","_w"))
        m["spread"] = m["Close_b"] - m["Close_w"]
        fig2 = make_fig(180)
        fig2.add_trace(go.Scatter(x=m["Date"], y=m["spread"], line=dict(color="#a78bfa",width=2), fill="tozeroy", fillcolor="rgba(167,139,250,0.08)"))
        fig2.add_hline(y=0, line_dash="dash", line_color="#374151")
        fig2.update_layout(yaxis=dict(tickformat="$.2f"))
        st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CRACK SPREADS
# ═══════════════════════════════════════════════════════════════════════════════
with t2:
    st.markdown('<div class="info-box">💡 <strong>Crack spread = margem bruta de refinação.</strong> É a diferença entre o preço dos produtos refinados e o crude. O <strong>3-2-1</strong> é o benchmark da indústria: 3 barris crude → 2 gasolina + 1 gasóleo.</div>', unsafe_allow_html=True)
    period_c = st.selectbox("Período", ["1mo","3mo","6mo","1y"], index=1, key="cp", label_visibility="collapsed")
    df_crack = fetch_crack_spreads(period_c)

    if not df_crack.empty:
        c1,c2,c3 = st.columns(3)
        for col, key, label, mc in [(c1,"3-2-1 Crack","3-2-1 Crack","metric-card"),(c2,"Gasóleo Crack","Gasóleo Crack","metric-card mc-green"),(c3,"Gasolina Crack","Gasolina Crack","metric-card mc-blue")]:
            with col:
                val = df_crack[key].iloc[-1]; prev = df_crack[key].iloc[-2]; d = val-prev
                cls = "dpos" if d>=0 else "dneg"; arrow = "▲" if d>=0 else "▼"
                st.markdown(f"""<div class="{mc}">
                  <div class="metric-label">{label} · $/bbl</div>
                  <div class="metric-value">${val:.2f}</div>
                  <div class="{cls}">{arrow} ${abs(d):.2f} vs dia anterior</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        fig_c = make_fig(340)
        fig_c.add_trace(go.Scatter(x=df_crack["Date"], y=df_crack["3-2-1 Crack"],    name="3-2-1",   line=dict(color="#f97316",width=2)))
        fig_c.add_trace(go.Scatter(x=df_crack["Date"], y=df_crack["Gasóleo Crack"],  name="Gasóleo", line=dict(color="#4ade80",width=2)))
        fig_c.add_trace(go.Scatter(x=df_crack["Date"], y=df_crack["Gasolina Crack"], name="Gasolina",line=dict(color="#60a5fa",width=2)))
        fig_c.add_hline(y=0, line_dash="dash", line_color="#374151")
        fig_c.update_layout(yaxis=dict(tickformat="$.0f"))
        st.plotly_chart(fig_c, use_container_width=True)

        resumo = pd.DataFrame({
            "Crack Spread":  ["3-2-1","Gasóleo","Gasolina"],
            "Actual":        [f"${df_crack[k].iloc[-1]:.2f}" for k in ["3-2-1 Crack","Gasóleo Crack","Gasolina Crack"]],
            "Média":         [f"${df_crack[k].mean():.2f}"   for k in ["3-2-1 Crack","Gasóleo Crack","Gasolina Crack"]],
            "Máx":           [f"${df_crack[k].max():.2f}"    for k in ["3-2-1 Crack","Gasóleo Crack","Gasolina Crack"]],
            "Mín":           [f"${df_crack[k].min():.2f}"    for k in ["3-2-1 Crack","Gasóleo Crack","Gasolina Crack"]],
        })
        st.dataframe(resumo, hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — BENCHMARK MARGENS
# ═══════════════════════════════════════════════════════════════════════════════
with t3:
    st.markdown('<div class="info-box">💡 Comparação da margem de refinação da Galp Sines com benchmarks europeus. <strong>Med Cracking</strong> é o índice de referência para refinarias do Mediterrâneo. Os valores são proxies calculados com dados públicos — os índices reais (Argus/Platts) são pagos.</div>', unsafe_allow_html=True)
    st.markdown('<div class="warn-box">⚠️ Estes valores são <strong>proxies estimados</strong> com base em crack spreads públicos. Os benchmarks reais Med Cracking Margin e NWE Cracking Margin são publicados pela Argus Media e S&P Global Platts (acesso pago via subscrição empresarial).</div>', unsafe_allow_html=True)

    period_b = st.selectbox("Período", ["3mo","6mo","1y"], index=1, key="bp", label_visibility="collapsed")
    df_bench = fetch_benchmark_margins(period_b)

    if not df_bench.empty:
        # Cards actuais
        c1, c2, c3 = st.columns(3)
        benchmarks = [
            (c1, "Med Cracking (proxy)", "Med Cracking", "metric-card"),
            (c2, "NW Europe (proxy)",    "NW Europe",    "metric-card mc-blue"),
            (c3, "Sines Proxy",          "Sines (proxy)","metric-card mc-green"),
        ]
        for col, key, label, mc in benchmarks:
            with col:
                val = df_bench[key].iloc[-1]
                prev = df_bench[key].iloc[-2]
                d = val - prev
                cls = "dpos" if d>=0 else "dneg"; arrow = "▲" if d>=0 else "▼"
                mean_val = df_bench[key].mean()
                vs_mean = val - mean_val
                vs_cls = "dpos" if vs_mean>=0 else "dneg"
                st.markdown(f"""<div class="{mc}">
                  <div class="metric-label">{label} · $/bbl</div>
                  <div class="metric-value">${val:.2f}</div>
                  <div class="{cls}">{arrow} ${abs(d):.2f} vs ontem</div>
                  <div class="metric-sub">Média período: ${mean_val:.2f}/bbl</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Comparação de Margens Regionais</div>', unsafe_allow_html=True)

        fig_b = make_fig(340)
        fig_b.add_trace(go.Scatter(x=df_bench["Date"], y=df_bench["NW Europe (proxy)"],    name="NW Europe",  line=dict(color="#3b82f6",width=2)))
        fig_b.add_trace(go.Scatter(x=df_bench["Date"], y=df_bench["Med Cracking (proxy)"], name="Med Cracking",line=dict(color="#f97316",width=2)))
        fig_b.add_trace(go.Scatter(x=df_bench["Date"], y=df_bench["Sines Proxy"],          name="Sines",      line=dict(color="#4ade80",width=2,dash="dot")))
        fig_b.add_hline(y=0, line_dash="dash", line_color="#374151")
        fig_b.update_layout(yaxis=dict(tickformat="$.0f", title="$/bbl"))
        st.plotly_chart(fig_b, use_container_width=True)

        # Tabela comparativa
        st.markdown('<div class="section-header">Posicionamento Relativo</div>', unsafe_allow_html=True)
        actual_sines = df_bench["Sines Proxy"].iloc[-1]
        actual_med   = df_bench["Med Cracking (proxy)"].iloc[-1]
        actual_nwe   = df_bench["NW Europe (proxy)"].iloc[-1]

        comp = pd.DataFrame({
            "Região":          ["NW Europe", "Med Cracking", "Sines (proxy)"],
            "Margem Actual":   [f"${actual_nwe:.2f}", f"${actual_med:.2f}", f"${actual_sines:.2f}"],
            "vs NW Europe":    ["—", f"${actual_med-actual_nwe:.2f}", f"${actual_sines-actual_nwe:.2f}"],
            "Média 6 meses":   [f"${df_bench['NW Europe (proxy)'].mean():.2f}", f"${df_bench['Med Cracking (proxy)'].mean():.2f}", f"${df_bench['Sines Proxy'].mean():.2f}"],
        })
        st.dataframe(comp, hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CRUDE SOURCING
# ═══════════════════════════════════════════════════════════════════════════════
with t4:
    st.markdown('<div class="info-box">💡 Análise do custo efectivo de cada crude chegado a Sines: <strong>preço de mercado + diferencial de qualidade + frete estimado</strong>. Quanto menor o custo efectivo, melhor a margem potencial — desde que a refinaria consiga processar esse crude.</div>', unsafe_allow_html=True)

    brent_price = prices.get("Brent", {}).get("price", 80)
    all_crudes, ranked_crudes = crude_sourcing_analysis(prices)

    st.markdown(f'<div class="section-header">Ranking de Custo Efectivo — Brent hoje: ${brent_price:.2f}/bbl</div>', unsafe_allow_html=True)

    min_price = min(c["preco_efectivo"] for c in ranked_crudes)
    max_price = max(c["preco_efectivo"] for c in ranked_crudes)

    for i, c in enumerate(ranked_crudes):
        pct_bar = int((c["preco_efectivo"] - min_price) / max(max_price - min_price, 1) * 100)
        vs_str  = f"+${c['vs_brent']:.2f}" if c["vs_brent"] >= 0 else f"-${abs(c['vs_brent']):.2f}"
        rank_emoji = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣"][i]

        st.markdown(f"""
        <div class="crude-card">
          <div style="display:flex; justify-content:space-between; align-items:start;">
            <div>
              <div class="crude-name">{rank_emoji} {c['nome']} <span style="color:{c['cor']}">●</span></div>
              <div class="crude-origin">{c['origem']} · {c['qualidade']}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-family:'IBM Plex Mono',monospace; font-size:22px; font-weight:600; color:#f1f5f9;">${c['preco_efectivo']:.2f}/bbl</div>
              <div style="font-family:'IBM Plex Mono',monospace; font-size:12px; color:{'#4ade80' if c['vs_brent']<=0 else '#f87171'};">{vs_str} vs Brent</div>
            </div>
          </div>
          <div class="crude-bar-bg"><div class="crude-bar" style="width:{pct_bar}%; background:{c['cor']};"></div></div>
          <div style="font-size:12px; color:#6b7280;">
            Diferencial: {'+' if c['diferencial']>=0 else ''}{c['diferencial']:.1f}$/bbl &nbsp;·&nbsp; 
            Frete: +{c['frete_bbl']:.1f}$/bbl &nbsp;·&nbsp; 
            Risco: {c['risco']}
          </div>
          <div style="font-size:12px; color:#9ca3af; margin-top:6px;">{c['notas']}</div>
        </div>""", unsafe_allow_html=True)

    # Urals separado com aviso
    urals = next(c for c in all_crudes if c["nome"] == "Urals")
    st.markdown(f"""
    <div class="crude-card" style="border-color:#7f1d1d; opacity:0.6;">
      <div class="crude-name">❌ {urals['nome']} <span style="color:#ef4444">●</span></div>
      <div class="crude-origin">{urals['origem']}</div>
      <div style="font-size:12px; color:#f87171; margin-top:6px;">{urals['notas']}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Custo Efectivo vs Brent ($/bbl)</div>', unsafe_allow_html=True)

    fig_cs = go.Figure()
    fig_cs.add_trace(go.Bar(
        x=[c["nome"] for c in ranked_crudes],
        y=[c["preco_efectivo"] for c in ranked_crudes],
        marker_color=[c["cor"] for c in ranked_crudes],
        text=[f"${c['preco_efectivo']:.1f}" for c in ranked_crudes],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=11, color="#9ca3af"),
    ))
    fig_cs.add_hline(y=brent_price, line_dash="dash", line_color="#f97316",
                     annotation_text=f"Brent ${brent_price:.1f}", annotation_font_color="#f97316")
    fig_cs.update_layout(
        paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
        font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
        margin=dict(l=0, r=0, t=30, b=0), height=320,
        xaxis=dict(gridcolor="#1a1f2e", showline=False),
        yaxis=dict(gridcolor="#1a1f2e", showline=False, tickformat="$.0f", range=[min_price-5, max_price+8]),
        showlegend=False,
    )
    st.plotly_chart(fig_cs, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — FORECAST
# ═══════════════════════════════════════════════════════════════════════════════
with t5:
    st.markdown('<div class="info-box">💡 Previsão do crack spread (margem bruta) para os próximos 30 dias úteis, baseada em tendência recente e reversão à média histórica. <strong>Nota:</strong> forecasts de commodities têm incerteza elevada — usa como orientação, não como valor preciso.</div>', unsafe_allow_html=True)
    st.markdown('<div class="warn-box">⚠️ Modelo estatístico simples (tendência linear + mean reversion). Para forecast profissional recomenda-se integrar dados de stocks EIA, produção OPEP e modelos econométricos mais robustos.</div>', unsafe_allow_html=True)

    period_f = st.selectbox("Histórico base", ["3mo","6mo","1y"], index=1, key="fp", label_visibility="collapsed")
    df_crack_f = fetch_crack_spreads(period_f)
    df_fore    = build_forecast(df_crack_f, days_ahead=30)

    if not df_crack_f.empty and not df_fore.empty:
        # Cards forecast
        c1, c2, c3 = st.columns(3)
        current   = df_crack_f["3-2-1 Crack"].iloc[-1]
        forecast1w = df_fore["Forecast"].iloc[4]   # ~1 semana
        forecast1m = df_fore["Forecast"].iloc[-1]  # ~1 mês
        mean_hist  = df_crack_f["3-2-1 Crack"].mean()

        for col, label, val, ref, mc in [
            (c1, "3-2-1 Crack Actual",     current,    current,   "metric-card"),
            (c2, "Forecast 1 Semana",       forecast1w, current,   "metric-card mc-purple"),
            (c3, "Forecast 1 Mês",          forecast1m, current,   "metric-card mc-yellow"),
        ]:
            with col:
                d = val - ref if label != "3-2-1 Crack Actual" else df_crack_f["3-2-1 Crack"].iloc[-1] - df_crack_f["3-2-1 Crack"].iloc[-2]
                cls = "dpos" if d>=0 else "dneg"; arrow = "▲" if d>=0 else "▼"
                st.markdown(f"""<div class="{mc}">
                  <div class="metric-label">{label}</div>
                  <div class="metric-value">${val:.2f}/bbl</div>
                  <div class="{cls}">{arrow} ${abs(d):.2f}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Histórico + Forecast 30 Dias</div>', unsafe_allow_html=True)

        fig_f = make_fig(380)

        # Histórico
        fig_f.add_trace(go.Scatter(
            x=df_crack_f["Date"], y=df_crack_f["3-2-1 Crack"],
            name="Histórico", line=dict(color="#f97316", width=2)))

        # Banda de confiança
        fig_f.add_trace(go.Scatter(
            x=pd.concat([df_fore["Date"], df_fore["Date"][::-1]]),
            y=pd.concat([df_fore["Upper"], df_fore["Lower"][::-1]]),
            fill="toself", fillcolor="rgba(168,85,247,0.1)",
            line=dict(color="rgba(0,0,0,0)"),
            name="Intervalo confiança", showlegend=True))

        # Linha forecast
        fig_f.add_trace(go.Scatter(
            x=df_fore["Date"], y=df_fore["Forecast"],
            name="Forecast", line=dict(color="#a855f7", width=2, dash="dot")))

        # Média histórica
        fig_f.add_hline(y=mean_hist, line_dash="dash", line_color="#374151",
                        annotation_text=f"Média histórica ${mean_hist:.1f}", annotation_font_color="#6b7280")
        fig_f.add_hline(y=0, line_dash="dash", line_color="#1f2937")
        fig_f.update_layout(yaxis=dict(tickformat="$.0f", title="$/bbl"))
        st.plotly_chart(fig_f, use_container_width=True)

        # Tabela forecast
        st.markdown('<div class="section-header">Tabela de Previsão</div>', unsafe_allow_html=True)
        tbl = df_fore.iloc[::5].copy()  # cada 5 dias úteis
        tbl_display = pd.DataFrame({
            "Data":              tbl["Date"].dt.strftime("%d/%m/%Y"),
            "Forecast ($/bbl)":  tbl["Forecast"].map(lambda x: f"${x:.2f}"),
            "Mínimo Esperado":   tbl["Lower"].map(lambda x: f"${x:.2f}"),
            "Máximo Esperado":   tbl["Upper"].map(lambda x: f"${x:.2f}"),
        })
        st.dataframe(tbl_display, hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — IR
# ═══════════════════════════════════════════════════════════════════════════════
with t6:

    @st.cache_data(ttl=300)
    def fetch_ir_data():
        # ── Oil & Gas stocks ────────────────────────────────────────────────
        stocks = {
            "Galp Energia":        "GALP.LS",
            "BP":                  "BP",
            "Shell":               "SHEL",
            "TotalEnergies":       "TTE",
            "Repsol":              "REP.MC",
            "Equinor":             "EQNR",
            "ExxonMobil":          "XOM",
            "Chevron":             "CVX",
            "ENI":                 "ENI.MI",
            "OMV":                 "OMV.VI",
        }
        # ── Indicadores de energia / macro ──────────────────────────────────
        indicators = {
            "BRT ICE (Brent)":     "BZ=F",
            "WTI NYMEX":           "CL=F",
            "Brent-WTI Spread":    None,           # calculado
            "Henry Hub Gas":       "NG=F",
            "TTF Gas (proxy)":     "TTF=F",
            "CO2 EUA (proxy)":     "KRBN",         # KraneShares ETF carbono
            "EUR/USD":             "EURUSD=X",
            "EUR/BRL":             "EURBRL=X",
            "EUR/GBP":             "EURGBP=X",
            "Petróleo Refinado HO":"HO=F",
        }

        stock_data, indic_data = {}, {}

        for name, ticker in stocks.items():
            try:
                d = yf.Ticker(ticker).history(period="1y", interval="1d")
                if len(d) >= 2:
                    curr = d["Close"].iloc[-1]
                    prev = d["Close"].iloc[-2]
                    start = d["Close"].iloc[0]
                    stock_data[name] = {
                        "ticker": ticker,
                        "price":  curr,
                        "delta":  curr - prev,
                        "pct":    (curr - prev) / prev * 100,
                        "ytd":    (curr - start) / start * 100,
                        "hist":   d[["Close"]].reset_index(),
                    }
            except:
                pass

        for name, ticker in indicators.items():
            if ticker is None:
                continue
            try:
                d = yf.Ticker(ticker).history(period="1mo", interval="1d")
                if len(d) >= 2:
                    curr = d["Close"].iloc[-1]
                    prev = d["Close"].iloc[-2]
                    indic_data[name] = {
                        "price": curr,
                        "delta": curr - prev,
                        "pct":   (curr - prev) / prev * 100,
                        "hist":  d[["Close"]].reset_index(),
                    }
            except:
                pass

        # Calcular spread Brent-WTI
        try:
            brent_p = indic_data.get("BRT ICE (Brent)", {}).get("price", 0)
            wti_p   = indic_data.get("WTI NYMEX",       {}).get("price", 0)
            if brent_p and wti_p:
                spread = brent_p - wti_p
                indic_data["Brent-WTI Spread"] = {
                    "price": spread,
                    "delta": 0,
                    "pct":   0,
                    "hist":  pd.DataFrame(),
                }
        except:
            pass

        return stock_data, indic_data

    with st.spinner("A carregar dados IR..."):
        stock_data, indic_data = fetch_ir_data()

    # ── Indicadores de Mercado ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Indicadores de Mercado — Energia & Macro</div>', unsafe_allow_html=True)

    indic_list = [
        ("BRT ICE (Brent)",      "$/bbl",  "metric-card"),
        ("WTI NYMEX",            "$/bbl",  "metric-card mc-blue"),
        ("Brent-WTI Spread",     "$/bbl",  "metric-card mc-purple"),
        ("Henry Hub Gas",        "$/MMBtu","metric-card"),
        ("TTF Gas (proxy)",      "€/MWh",  "metric-card mc-green"),
        ("CO2 EUA (proxy)",      "ETF",    "metric-card mc-yellow"),
        ("EUR/USD",              "taxa",   "metric-card"),
        ("EUR/BRL",              "taxa",   "metric-card mc-blue"),
        ("EUR/GBP",              "taxa",   "metric-card mc-purple"),
        ("Petróleo Refinado HO", "$/gal",  "metric-card mc-green"),
    ]

    # Renderizar em linhas de 5
    for row_start in range(0, len(indic_list), 5):
        row = indic_list[row_start:row_start+5]
        cols = st.columns(len(row))
        for col, (name, unit, mc) in zip(cols, row):
            with col:
                if name in indic_data:
                    p = indic_data[name]
                    cls   = "dpos" if p["delta"] >= 0 else "dneg"
                    arrow = "▲" if p["delta"] >= 0 else "▼"
                    delta_str = f"{arrow} {abs(p['delta']):.3f} ({p['pct']:+.2f}%)" if p["delta"] != 0 else "—"
                    st.markdown(f"""<div class="{mc}">
                      <div class="metric-label">{name}</div>
                      <div class="metric-value" style="font-size:20px;">{p['price']:.3f}</div>
                      <div class="metric-sub">{unit}</div>
                      <div class="{cls}" style="font-size:11px;">{delta_str}</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="{mc}">
                      <div class="metric-label">{name}</div>
                      <div class="metric-value" style="font-size:16px; color:#4b5563;">N/D</div>
                      <div class="metric-sub">{unit}</div>
                    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Stock Performance ────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Oil & Gas — Stock Performance (1 ano)</div>', unsafe_allow_html=True)

    if stock_data:
        # Ordenar por YTD performance
        sorted_stocks = sorted(stock_data.items(), key=lambda x: x[1]["ytd"], reverse=True)
        best  = sorted_stocks[:3]
        worst = sorted_stocks[-3:]

        col_b, col_w = st.columns(2)
        with col_b:
            st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace; font-size:11px; color:#4ade80; margin-bottom:12px;">▲ MELHORES PERFORMERS (YTD)</div>', unsafe_allow_html=True)
            for name, d in best:
                cls = "dpos" if d["ytd"] >= 0 else "dneg"
                st.markdown(f"""<div class="metric-card mc-green" style="padding:14px 18px; margin-bottom:8px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                      <div class="metric-label">{d['ticker']}</div>
                      <div style="font-family:'IBM Plex Mono',monospace; font-size:15px; font-weight:600; color:#f1f5f9;">{name}</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-family:'IBM Plex Mono',monospace; font-size:20px; font-weight:600; color:#f1f5f9;">{d['price']:.2f}</div>
                      <div class="{cls}">{'+' if d['ytd']>=0 else ''}{d['ytd']:.1f}% YTD</div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

        with col_w:
            st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace; font-size:11px; color:#f87171; margin-bottom:12px;">▼ PIORES PERFORMERS (YTD)</div>', unsafe_allow_html=True)
            for name, d in reversed(worst):
                cls = "dpos" if d["ytd"] >= 0 else "dneg"
                st.markdown(f"""<div class="metric-card" style="padding:14px 18px; margin-bottom:8px; border-color:#3f1515;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                      <div class="metric-label">{d['ticker']}</div>
                      <div style="font-family:'IBM Plex Mono',monospace; font-size:15px; font-weight:600; color:#f1f5f9;">{name}</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-family:'IBM Plex Mono',monospace; font-size:20px; font-weight:600; color:#f1f5f9;">{d['price']:.2f}</div>
                      <div class="{cls}">{'+' if d['ytd']>=0 else ''}{d['ytd']:.1f}% YTD</div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Gráfico comparativo normalizado (base 100)
        st.markdown('<div class="section-header">Performance Relativa Normalizada (Base 100)</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Todas as acções normalizadas a 100 no início do período para comparação directa de performance relativa.</div>', unsafe_allow_html=True)

        period_ir = st.selectbox("Período", ["3mo","6mo","1y"], index=2, key="ir_period", label_visibility="collapsed")

        fig_ir = make_fig(420)
        colors_ir = ["#f97316","#3b82f6","#4ade80","#a855f7","#f59e0b","#06b6d4","#ec4899","#84cc16","#f87171","#818cf8"]

        highlight = ["Galp Energia", "BP", "TotalEnergies", "Shell", "Repsol"]

        for i, (name, d) in enumerate(sorted_stocks):
            try:
                hist = yf.Ticker(d["ticker"]).history(period=period_ir)[["Close"]].reset_index()
                if hist.empty or len(hist) < 5:
                    continue
                normalized = hist["Close"] / hist["Close"].iloc[0] * 100
                width  = 2.5 if name == "Galp Energia" else (1.5 if name in highlight else 1)
                dash   = "solid" if name in highlight else "dot"
                opacity = 1.0 if name in highlight else 0.5
                fig_ir.add_trace(go.Scatter(
                    x=hist["Date"], y=normalized,
                    name=name,
                    line=dict(color=colors_ir[i % len(colors_ir)], width=width, dash=dash),
                    opacity=opacity,
                ))
            except:
                pass

        fig_ir.add_hline(y=100, line_dash="dash", line_color="#374151")
        fig_ir.update_layout(yaxis=dict(tickformat=".0f", title="Base 100"))
        st.plotly_chart(fig_ir, use_container_width=True)

        # Tabela resumo de todas as acções
        st.markdown('<div class="section-header">Tabela Completa — Oil & Gas Peers</div>', unsafe_allow_html=True)
        rows = []
        for name, d in sorted_stocks:
            rows.append({
                "Empresa":      name,
                "Ticker":       d["ticker"],
                "Preço Actual": f"{d['price']:.2f}",
                "Var. Dia":     f"{'+' if d['pct']>=0 else ''}{d['pct']:.2f}%",
                "YTD":          f"{'+' if d['ytd']>=0 else ''}{d['ytd']:.1f}%",
            })
        df_stocks = pd.DataFrame(rows)
        st.dataframe(df_stocks, hide_index=True, use_container_width=True)

    # ── Gráfico de indicadores ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Histórico de Indicadores Energéticos</div>', unsafe_allow_html=True)

    indic_sel = st.multiselect(
        "Selecciona indicadores",
        options=[k for k, v in indic_data.items() if not v["hist"].empty],
        default=["BRT ICE (Brent)", "Henry Hub Gas"],
        key="indic_sel",
        label_visibility="collapsed",
    )

    if indic_sel:
        fig_ind = make_fig(300)
        ind_colors = ["#f97316","#3b82f6","#4ade80","#a855f7","#f59e0b","#06b6d4"]
        for i, name in enumerate(indic_sel):
            if name in indic_data and not indic_data[name]["hist"].empty:
                h = indic_data[name]["hist"]
                fig_ind.add_trace(go.Scatter(
                    x=h["Date"], y=h["Close"],
                    name=name,
                    line=dict(color=ind_colors[i % len(ind_colors)], width=2),
                    yaxis="y" if i == 0 else "y2",
                ))
        fig_ind.update_layout(
            yaxis2=dict(overlaying="y", side="right", gridcolor="#1a1f2e", showline=False),
        )
        st.plotly_chart(fig_ind, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7 — NOTÍCIAS
# ═══════════════════════════════════════════════════════════════════════════════
with t7:
    st.markdown('<div class="section-header">Últimas Notícias</div>', unsafe_allow_html=True)
    sources  = list({a["source"] for a in news})
    filtro   = st.multiselect("Filtrar fontes", options=sources, default=[], placeholder="Todas as fontes", label_visibility="collapsed")
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
  Oil Market Intelligence · Business Office Industrial · Yahoo Finance + RSS Feeds · Proxies estimados — não substituem dados Argus/Platts
</div>
""", unsafe_allow_html=True)
