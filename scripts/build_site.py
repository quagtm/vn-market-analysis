"""
VN Market Analysis - Static Site Generator
Tạo docs/index.html từ data/market_data.json
"""

import json
import os
from datetime import datetime


def load_data() -> dict:
    with open("data/market_data.json", "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_num(v, decimals=2, suffix=""):
    if v is None:
        return "<span class='na'>—</span>"
    return f"{v:,.{decimals}f}{suffix}"


def fmt_chg(v):
    if v is None:
        return "<span class='na'>—</span>"
    cls = "pos" if v > 0 else ("neg" if v < 0 else "flat")
    sign = "+" if v > 0 else ""
    return f"<span class='{cls}'>{sign}{v:.2f}%</span>"


def trend_badge(trend, strength=""):
    colors = {"Tăng": "badge-bull", "Giảm": "badge-bear", "Đi ngang": "badge-neutral"}
    cls = colors.get(trend, "badge-neutral")
    txt = f"{trend}" + (f" · {strength}" if strength else "")
    return f"<span class='badge {cls}'>{txt}</span>"


def sentiment_icon(s):
    icons = {"Tích cực": "↑", "Tiêu cực": "↓", "Trung lập": "→"}
    cls   = {"Tích cực": "pos", "Tiêu cực": "neg", "Trung lập": "flat"}
    c = cls.get(s, "flat")
    i = icons.get(s, "—")
    return f"<span class='{c}'>{i} {s}</span>"


def render_index_tab(code: str, data: dict) -> str:
    snap = data.get("snapshot", {})
    anl  = data.get("analysis", {})
    sectors = data.get("sectors", {})
    movers  = data.get("movers", {})

    if data.get("error"):
        return f"<div class='error-box'>⚠ Lỗi tải dữ liệu: {data['error']}</div>"

    # ── Hero ──────────────────────────────────────────────────────────────────
    close     = snap.get("close")
    chg       = snap.get("change")
    chg_pct   = snap.get("change_pct")
    date_str  = snap.get("date", "")
    vol       = snap.get("volume", 0)
    is_up     = (chg_pct or 0) >= 0
    hero_cls  = "hero-up" if is_up else "hero-down"
    chg_sign  = "+" if is_up else ""

    hero = f"""
    <div class='hero-card {hero_cls}'>
      <div class='hero-index-name'>{code}</div>
      <div class='hero-price'>{close:,.2f}</div>
      <div class='hero-change'>{chg_sign}{chg:.2f} ({chg_sign}{chg_pct:.2f}%)</div>
      <div class='hero-meta'>
        <span>📅 {date_str}</span>
        <span>📊 KL: {vol:,}</span>
        <span>Cao: {fmt_num(snap.get('high'))}</span>
        <span>Thấp: {fmt_num(snap.get('low'))}</span>
      </div>
    </div>
    """

    # ── Summary ───────────────────────────────────────────────────────────────
    summary_html = ""
    if anl.get("summary"):
        sentiment = anl.get("sentiment", "Trung lập")
        summary_html = f"""
        <div class='section-card'>
          <div class='section-title'>📋 Tổng quan thị trường</div>
          <div class='summary-sentiment'>{sentiment_icon(sentiment)}</div>
          <p class='summary-text'>{anl.get('market_description', anl.get('summary',''))}</p>
          {f"<div class='recommendation'>💡 {anl['recommendation']}</div>" if anl.get('recommendation') else ''}
        </div>
        """

    # ── Sectors ───────────────────────────────────────────────────────────────
    leading_html = "".join(
        f"<div class='mover-item pos'><span class='mover-sym'>{s['name']}</span><span>{s['change_pct']:+.2f}%</span></div>"
        for s in sectors.get("leading", [])
    )
    lagging_html = "".join(
        f"<div class='mover-item neg'><span class='mover-sym'>{s['name']}</span><span>{s['change_pct']:+.2f}%</span></div>"
        for s in sectors.get("lagging", [])
    )
    top3_pos = "".join(
        f"<div class='mover-item pos'><span class='mover-sym'>{s['symbol']}</span><span>{s['change_pct']:+.2f}%</span></div>"
        for s in movers.get("top_gainers", [])
    )
    top3_neg = "".join(
        f"<div class='mover-item neg'><span class='mover-sym'>{s['symbol']}</span><span>{s['change_pct']:+.2f}%</span></div>"
        for s in movers.get("top_losers", [])
    )

    movers_html = f"""
    <div class='section-card'>
      <div class='section-title'>🏭 Nhóm ngành & Cổ phiếu</div>
      <div class='movers-grid'>
        <div>
          <div class='movers-label'>▲ Ngành dẫn dắt</div>
          {leading_html or '<div class="na">Không có dữ liệu</div>'}
        </div>
        <div>
          <div class='movers-label'>▼ Ngành đi lùi</div>
          {lagging_html or '<div class="na">Không có dữ liệu</div>'}
        </div>
        <div>
          <div class='movers-label'>📈 Top 3 tác động (+)</div>
          {top3_pos or '<div class="na">Không có dữ liệu</div>'}
        </div>
        <div>
          <div class='movers-label'>📉 Top 3 tác động (−)</div>
          {top3_neg or '<div class="na">Không có dữ liệu</div>'}
        </div>
      </div>
    </div>
    """

    # ── Support / Resistance ──────────────────────────────────────────────────
    sr = anl.get("support_resistance", {})
    kl = anl.get("key_levels", {})
    sr_html = f"""
    <div class='section-card'>
      <div class='section-title'>⚖️ Hỗ trợ & Kháng cự</div>
      <div class='sr-grid'>
        <div class='sr-col'>
          <div class='sr-label neg'>Kháng cự</div>
          <div class='sr-val'>{fmt_num(kl.get('strong_resistance'))} <small>(mạnh)</small></div>
          <div class='sr-val'>{fmt_num(kl.get('immediate_resistance'))} <small>(gần)</small></div>
        </div>
        <div class='sr-price-col'>
          <div class='sr-current-price'>{fmt_num(close)}</div>
          <div class='sr-current-label'>Giá hiện tại</div>
        </div>
        <div class='sr-col'>
          <div class='sr-label pos'>Hỗ trợ</div>
          <div class='sr-val'>{fmt_num(kl.get('immediate_support'))} <small>(gần)</small></div>
          <div class='sr-val'>{fmt_num(kl.get('strong_support'))} <small>(mạnh)</small></div>
        </div>
      </div>
      <div class='pivot-row'>
        <span>Pivot: <b>{fmt_num(snap.get('pivot'))}</b></span>
        <span>R1: {fmt_num(snap.get('r1'))}</span>
        <span>R2: {fmt_num(snap.get('r2'))}</span>
        <span>S1: {fmt_num(snap.get('s1'))}</span>
        <span>S2: {fmt_num(snap.get('s2'))}</span>
      </div>
      <div class='fibo-row'>
        <span>Fibo: </span>
        <span>23.6%: {fmt_num(snap.get('fibo_236'))}</span>
        <span>38.2%: {fmt_num(snap.get('fibo_382'))}</span>
        <span>50%: {fmt_num(snap.get('fibo_500'))}</span>
        <span>61.8%: {fmt_num(snap.get('fibo_618'))}</span>
      </div>
      {f"<div class='sr-comment'>{sr.get('comment','')}</div>" if sr.get('comment') else ''}
    </div>
    """

    # ── Timeframe Analysis ────────────────────────────────────────────────────
    ta = anl.get("timeframe_analysis", {})
    def tf_card(label, key, icon):
        tf = ta.get(key, {})
        if not tf:
            return ""
        sigs = "".join(f"<li>{s}</li>" for s in tf.get("signals", []))
        return f"""
        <div class='tf-card'>
          <div class='tf-header'>{icon} {label}</div>
          <div class='tf-trend'>{trend_badge(tf.get('trend',''), tf.get('strength',''))}</div>
          <p class='tf-comment'>{tf.get('comment','')}</p>
          {"<ul class='tf-signals'>" + sigs + "</ul>" if sigs else ""}
        </div>
        """

    tf_html = f"""
    <div class='section-card'>
      <div class='section-title'>📊 Phân tích theo khung thời gian</div>
      <div class='tf-grid'>
        {tf_card("Ngắn hạn", "short_term", "🔹")}
        {tf_card("Trung hạn", "mid_term", "🔷")}
        {tf_card("Dài hạn", "long_term", "🔵")}
      </div>
    </div>
    """

    # ── Scenarios ─────────────────────────────────────────────────────────────
    scenarios = anl.get("scenarios", [])
    def scenario_card(sc):
        prob = sc.get("probability", 0)
        name = sc.get("name", "")
        is_bull = "Bull" in name or "tăng" in name.lower()
        is_bear = "Bear" in name or "giảm" in name.lower()
        cls = "sc-bull" if is_bull else ("sc-bear" if is_bear else "sc-neutral")
        return f"""
        <div class='sc-card {cls}'>
          <div class='sc-header'>
            <span class='sc-name'>{name}</span>
            <span class='sc-prob'>{prob}%</span>
          </div>
          <div class='sc-prob-bar'><div class='sc-prob-fill' style='width:{prob}%'></div></div>
          <div class='sc-target'>🎯 {sc.get('target','')}</div>
          <div class='sc-condition'>📌 {sc.get('condition','')}</div>
          <p class='sc-desc'>{sc.get('description','')}</p>
        </div>
        """

    sc_html = ""
    if scenarios:
        sc_html = f"""
        <div class='section-card'>
          <div class='section-title'>🎲 Kịch bản xác suất</div>
          <div class='sc-grid'>
            {"".join(scenario_card(sc) for sc in scenarios)}
          </div>
        </div>
        """

    # ── Technical Indicators Row ──────────────────────────────────────────────
    def indicator_row(label, val, status=""):
        return f"""
        <div class='ind-row'>
          <span class='ind-label'>{label}</span>
          <span class='ind-val'>{val}</span>
          {f"<span class='ind-status {status}'>{status}</span>" if status else ""}
        </div>
        """

    rsi = snap.get("rsi14")
    rsi_status = "Quá mua" if (rsi or 0) > 70 else ("Quá bán" if (rsi or 0) < 30 else "Trung tính")
    macd_status = "Tích cực" if (snap.get("macd_hist") or 0) > 0 else "Tiêu cực"

    ind_html = f"""
    <div class='section-card'>
      <div class='section-title'>📉 Chỉ báo kỹ thuật</div>
      <div class='ind-grid'>
        <div class='ind-col'>
          <div class='ind-group-title'>Moving Averages</div>
          {indicator_row("MA5", fmt_num(snap.get('ma5')))}
          {indicator_row("MA10", fmt_num(snap.get('ma10')))}
          {indicator_row("MA20", fmt_num(snap.get('ma20')))}
          {indicator_row("MA50", fmt_num(snap.get('ma50')))}
          {indicator_row("MA100", fmt_num(snap.get('ma100')))}
          {indicator_row("MA200", fmt_num(snap.get('ma200')))}
        </div>
        <div class='ind-col'>
          <div class='ind-group-title'>Oscillators</div>
          {indicator_row("RSI(14)", fmt_num(rsi, 1), rsi_status)}
          {indicator_row("Stoch %K", fmt_num(snap.get('stoch_k'), 1))}
          {indicator_row("Stoch %D", fmt_num(snap.get('stoch_d'), 1))}
          {indicator_row("MACD", fmt_num(snap.get('macd')), macd_status)}
          {indicator_row("Signal", fmt_num(snap.get('macd_signal')))}
          {indicator_row("ATR(14)", fmt_num(snap.get('atr14')))}
        </div>
        <div class='ind-col'>
          <div class='ind-group-title'>Bollinger Bands</div>
          {indicator_row("Upper", fmt_num(snap.get('bb_upper')))}
          {indicator_row("Middle", fmt_num(snap.get('bb_mid')))}
          {indicator_row("Lower", fmt_num(snap.get('bb_lower')))}
          <div class='ind-group-title' style='margin-top:1rem'>52-Week</div>
          {indicator_row("High", fmt_num(snap.get('hi52')))}
          {indicator_row("Low", fmt_num(snap.get('lo52')))}
        </div>
      </div>
    </div>
    """

    # ── Chart (placeholder, real chart via Lightweight Charts JS) ────────────
    ohlcv_json = json.dumps(data.get("ohlcv", []))
    chart_html = f"""
    <div class='section-card'>
      <div class='section-title'>📈 Biểu đồ giá</div>
      <div class='chart-toolbar'>
        <button class='chart-btn active' onclick='setChartType("{code}","candlestick")'>Nến</button>
        <button class='chart-btn' onclick='setChartType("{code}","line")'>Đường</button>
        <button class='chart-btn' onclick='toggleMA("{code}")'>MA</button>
        <button class='chart-btn' onclick='toggleBB("{code}")'>BB</button>
        <div style='flex:1'></div>
        <button class='chart-btn' onclick='setRange("{code}",30)'>1M</button>
        <button class='chart-btn' onclick='setRange("{code}",90)'>3M</button>
        <button class='chart-btn active' onclick='setRange("{code}",180)'>6M</button>
        <button class='chart-btn' onclick='setRange("{code}",365)'>1Y</button>
      </div>
      <div id='chart-{code}' class='chart-container'></div>
      <div id='vol-chart-{code}' class='vol-chart-container'></div>
      <div class='chart-legend' id='legend-{code}'></div>
      <script>
        window.__ohlcv_{code} = {ohlcv_json};
      </script>
    </div>
    """

    return hero + summary_html + movers_html + sr_html + tf_html + sc_html + ind_html + chart_html


def build_html(data: dict) -> str:
    generated = data.get("generated_at", datetime.now().isoformat())[:16].replace("T", " ")

    tabs_nav = ""
    tabs_content = ""
    for i, code in enumerate(["VNINDEX", "VN30", "VN100"]):
        active = "active" if i == 0 else ""
        tabs_nav += f"<button class='tab-btn {active}' onclick='switchTab(\"{code}\")'>{code}</button>"
        display = "block" if i == 0 else "none"
        idx_data = data.get(code, {})
        tabs_content += f"""
        <div id='tab-{code}' class='tab-content' style='display:{display}'>
          {render_index_tab(code, idx_data)}
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VN Market Analysis</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

  :root {{
    --bg:        #0d0f14;
    --bg2:       #141720;
    --bg3:       #1c2030;
    --border:    #252a3a;
    --text:      #c8cfe0;
    --text-dim:  #5a6278;
    --accent:    #3d7eff;
    --accent2:   #7c5cfc;
    --pos:       #26c281;
    --neg:       #e05c5c;
    --flat:      #8899aa;
    --gold:      #f4a836;
    --font:      'IBM Plex Sans', sans-serif;
    --mono:      'IBM Plex Mono', monospace;
    --radius:    8px;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    font-size: 14px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }}

  /* ── Header ── */
  .header {{
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 0 2rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    height: 56px;
    position: sticky;
    top: 0;
    z-index: 100;
  }}
  .header-logo {{
    font-family: var(--mono);
    font-weight: 600;
    font-size: 1.1rem;
    color: var(--accent);
    letter-spacing: 0.05em;
  }}
  .header-logo span {{ color: var(--accent2); }}
  .header-updated {{
    margin-left: auto;
    font-size: 11px;
    color: var(--text-dim);
    font-family: var(--mono);
  }}

  /* ── Layout ── */
  .layout {{
    display: flex;
    flex: 1;
    min-height: 0;
  }}
  .sidebar {{
    width: 200px;
    min-width: 200px;
    background: var(--bg2);
    border-right: 1px solid var(--border);
    padding: 1.5rem 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .sidebar-label {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
    padding: 0 1.25rem;
    margin-bottom: 0.5rem;
  }}
  .main-content {{
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem 2rem;
    max-width: 100%;
  }}

  /* ── Sidebar Tabs ── */
  .tab-btn {{
    all: unset;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 1.25rem;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-dim);
    border-left: 2px solid transparent;
    transition: all 0.15s;
    width: 100%;
  }}
  .tab-btn:hover {{ background: var(--bg3); color: var(--text); }}
  .tab-btn.active {{
    color: var(--accent);
    border-left-color: var(--accent);
    background: rgba(61,126,255,0.08);
  }}

  /* ── Hero ── */
  .hero-card {{
    padding: 1.5rem;
    border-radius: var(--radius);
    margin-bottom: 1rem;
    border: 1px solid var(--border);
  }}
  .hero-up   {{ background: linear-gradient(135deg, rgba(38,194,129,0.12), rgba(13,15,20,0)); border-color: rgba(38,194,129,0.25); }}
  .hero-down {{ background: linear-gradient(135deg, rgba(224,92,92,0.12), rgba(13,15,20,0)); border-color: rgba(224,92,92,0.25); }}
  .hero-index-name {{
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-bottom: 0.4rem;
  }}
  .hero-price {{
    font-family: var(--mono);
    font-size: 2.4rem;
    font-weight: 600;
    line-height: 1;
    color: var(--text);
  }}
  .hero-change {{
    font-family: var(--mono);
    font-size: 1rem;
    margin-top: 0.3rem;
    color: var(--pos);
  }}
  .hero-up .hero-change   {{ color: var(--pos); }}
  .hero-down .hero-change {{ color: var(--neg); }}
  .hero-meta {{
    margin-top: 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    font-size: 12px;
    color: var(--text-dim);
    font-family: var(--mono);
  }}

  /* ── Section Card ── */
  .section-card {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem;
    margin-bottom: 1rem;
  }}
  .section-title {{
    font-weight: 600;
    font-size: 13px;
    color: var(--text);
    margin-bottom: 1rem;
    letter-spacing: 0.02em;
  }}

  /* ── Colors ── */
  .pos {{ color: var(--pos); }}
  .neg {{ color: var(--neg); }}
  .flat {{ color: var(--flat); }}
  .na {{ color: var(--text-dim); }}

  /* ── Badge ── */
  .badge {{
    display: inline-flex; align-items: center;
    padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 600; font-family: var(--mono);
  }}
  .badge-bull    {{ background: rgba(38,194,129,0.15); color: var(--pos); border: 1px solid rgba(38,194,129,0.3); }}
  .badge-bear    {{ background: rgba(224,92,92,0.15); color: var(--neg); border: 1px solid rgba(224,92,92,0.3); }}
  .badge-neutral {{ background: rgba(136,153,170,0.15); color: var(--flat); border: 1px solid rgba(136,153,170,0.3); }}

  /* ── Summary ── */
  .summary-sentiment {{ font-size: 15px; font-weight: 600; margin-bottom: 0.75rem; }}
  .summary-text {{ line-height: 1.7; color: var(--text); }}
  .recommendation {{
    margin-top: 1rem;
    background: rgba(61,126,255,0.08);
    border: 1px solid rgba(61,126,255,0.2);
    border-radius: 6px;
    padding: 0.75rem 1rem;
    font-size: 13px;
    color: var(--accent);
  }}

  /* ── Movers ── */
  .movers-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
  }}
  .movers-label {{
    font-size: 11px;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.5rem;
  }}
  .mover-item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--border);
    font-family: var(--mono);
    font-size: 13px;
  }}
  .mover-sym {{ font-weight: 600; }}

  /* ── SR ── */
  .sr-grid {{
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 1rem;
    align-items: center;
    text-align: center;
    margin-bottom: 1rem;
  }}
  .sr-label {{ font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.5rem; }}
  .sr-val {{ font-family: var(--mono); font-size: 14px; padding: 2px 0; }}
  .sr-price-col {{ padding: 0.5rem; }}
  .sr-current-price {{
    font-family: var(--mono);
    font-size: 1.4rem;
    font-weight: 600;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
  }}
  .sr-current-label {{ font-size: 11px; color: var(--text-dim); margin-top: 4px; }}
  .pivot-row, .fibo-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-dim);
    padding: 0.5rem 0;
    border-top: 1px solid var(--border);
  }}
  .sr-comment {{
    margin-top: 0.75rem;
    font-size: 13px;
    color: var(--text);
    line-height: 1.6;
    font-style: italic;
  }}

  /* ── Timeframe ── */
  .tf-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }}
  .tf-card {{
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem;
  }}
  .tf-header {{ font-size: 13px; font-weight: 600; margin-bottom: 0.5rem; }}
  .tf-trend {{ margin-bottom: 0.75rem; }}
  .tf-comment {{ font-size: 13px; line-height: 1.6; color: var(--text); }}
  .tf-signals {{ margin-top: 0.5rem; padding-left: 1.25rem; font-size: 12px; color: var(--text-dim); }}
  .tf-signals li {{ margin: 2px 0; }}

  /* ── Scenarios ── */
  .sc-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
  }}
  .sc-card {{
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem;
    background: var(--bg3);
  }}
  .sc-bull {{ border-top: 3px solid var(--pos); }}
  .sc-bear {{ border-top: 3px solid var(--neg); }}
  .sc-neutral {{ border-top: 3px solid var(--flat); }}
  .sc-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }}
  .sc-name {{ font-weight: 600; font-size: 13px; }}
  .sc-prob {{
    font-family: var(--mono);
    font-size: 18px;
    font-weight: 600;
  }}
  .sc-bull .sc-prob {{ color: var(--pos); }}
  .sc-bear .sc-prob {{ color: var(--neg); }}
  .sc-neutral .sc-prob {{ color: var(--flat); }}
  .sc-prob-bar {{ height: 3px; background: var(--border); border-radius: 2px; margin-bottom: 0.75rem; }}
  .sc-bull .sc-prob-fill {{ background: var(--pos); height: 100%; border-radius: 2px; }}
  .sc-bear .sc-prob-fill {{ background: var(--neg); height: 100%; border-radius: 2px; }}
  .sc-neutral .sc-prob-fill {{ background: var(--flat); height: 100%; border-radius: 2px; }}
  .sc-target, .sc-condition {{ font-size: 12px; color: var(--text-dim); margin-bottom: 4px; font-family: var(--mono); }}
  .sc-desc {{ font-size: 13px; color: var(--text); line-height: 1.5; margin-top: 0.5rem; }}

  /* ── Indicators ── */
  .ind-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; }}
  .ind-group-title {{ font-size: 11px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem; }}
  .ind-row {{ display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid var(--border); font-family: var(--mono); font-size: 12px; }}
  .ind-label {{ color: var(--text-dim); }}
  .ind-val {{ font-weight: 500; }}
  .ind-status {{ font-size: 10px; padding: 1px 5px; border-radius: 3px; background: var(--bg3); }}

  /* ── Chart ── */
  .chart-toolbar {{
    display: flex;
    gap: 4px;
    margin-bottom: 0.75rem;
    align-items: center;
  }}
  .chart-btn {{
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text-dim);
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    font-family: var(--mono);
    transition: all 0.15s;
  }}
  .chart-btn:hover, .chart-btn.active {{
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }}
  .chart-container {{
    width: 100%;
    height: 380px;
    border-radius: 6px;
    overflow: hidden;
    background: var(--bg3);
  }}
  .vol-chart-container {{
    width: 100%;
    height: 100px;
    border-radius: 6px;
    overflow: hidden;
    background: var(--bg3);
    margin-top: 4px;
  }}
  .chart-legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-top: 0.5rem;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-dim);
  }}

  /* ── Error ── */
  .error-box {{
    background: rgba(224,92,92,0.1);
    border: 1px solid rgba(224,92,92,0.3);
    border-radius: 8px;
    padding: 1.5rem;
    color: var(--neg);
  }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 5px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg2); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
</style>
</head>
<body>

<header class="header">
  <div class="header-logo">VN<span>Market</span>.analysis</div>
  <div class="header-updated">Cập nhật: {generated} (ICT)</div>
</header>

<div class="layout">
  <nav class="sidebar">
    <div class="sidebar-label">Thị trường</div>
    {tabs_nav}
  </nav>
  <main class="main-content">
    {tabs_content}
  </main>
</div>

<script>
// ── Tab switching ──────────────────────────────────────────────────────────
const TAB_CODES = ["VNINDEX","VN30","VN100"];

function switchTab(code) {{
  TAB_CODES.forEach(c => {{
    document.getElementById('tab-' + c).style.display = (c === code) ? 'block' : 'none';
  }});
  document.querySelectorAll('.tab-btn').forEach((btn, i) => {{
    btn.classList.toggle('active', TAB_CODES[i] === code);
  }});
  if (!window.__charts__[code]) initChart(code);
}}

// ── Chart state ──────────────────────────────────────────────────────────
window.__charts__ = {{}};
window.__chartState__ = {{}};

const COLORS = {{
  ma5: '#f4a836', ma10: '#7c5cfc', ma20: '#3d7eff',
  ma50: '#26c281', ma100: '#e05c5c', ma200: '#ffffff',
  bb: '#5a6278',
}};

function initChart(code) {{
  const el  = document.getElementById('chart-' + code);
  const vel = document.getElementById('vol-chart-' + code);
  const raw = window['__ohlcv_' + code] || [];
  if (!el || !raw.length) return;

  const chart = LightweightCharts.createChart(el, {{
    layout: {{ background: {{ color: '#1c2030' }}, textColor: '#c8cfe0' }},
    grid:   {{ vertLines: {{ color: '#252a3a' }}, horzLines: {{ color: '#252a3a' }} }},
    crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
    rightPriceScale: {{ borderColor: '#252a3a' }},
    timeScale: {{ borderColor: '#252a3a', timeVisible: true }},
    width: el.clientWidth,
    height: el.clientHeight,
  }});

  const vchart = LightweightCharts.createChart(vel, {{
    layout: {{ background: {{ color: '#1c2030' }}, textColor: '#c8cfe0' }},
    grid:   {{ vertLines: {{ color: '#252a3a' }}, horzLines: {{ color: 'transparent' }} }},
    rightPriceScale: {{ borderColor: '#252a3a' }},
    timeScale: {{ borderColor: '#252a3a', timeVisible: true }},
    width: vel.clientWidth,
    height: vel.clientHeight,
  }});

  // Candlestick series
  const candleSeries = chart.addCandlestickSeries({{
    upColor: '#26c281', downColor: '#e05c5c',
    borderUpColor: '#26c281', borderDownColor: '#e05c5c',
    wickUpColor: '#26c281', wickDownColor: '#e05c5c',
  }});

  const toTS = d => {{ const [y,m,day] = d.time.split('-'); return {{year:+y,month:+m,day:+day}}; }};

  const candles = raw.filter(d => d.close).map(d => ({{
    time: toTS(d), open: d.open, high: d.high, low: d.low, close: d.close
  }}));
  candleSeries.setData(candles);

  // Volume
  const volSeries = vchart.addHistogramSeries({{
    color: '#3d7eff', priceFormat: {{ type: 'volume' }},
    priceScaleId: '', scaleMargins: {{ top: 0.1, bottom: 0 }},
  }});
  volSeries.setData(raw.filter(d => d.volume).map(d => ({{
    time: toTS(d), value: d.volume,
    color: (d.close >= d.open) ? 'rgba(38,194,129,0.5)' : 'rgba(224,92,92,0.5)'
  }})));

  // MA series
  const maSeries = {{}};
  ['ma5','ma10','ma20','ma50','ma100','ma200'].forEach(ma => {{
    const s = chart.addLineSeries({{
      color: COLORS[ma], lineWidth: ma === 'ma200' ? 2 : 1,
      title: ma.toUpperCase(), lastValueVisible: false, priceLineVisible: false,
    }});
    s.setData(raw.filter(d => d[ma]).map(d => ({{ time: toTS(d), value: d[ma] }})));
    maSeries[ma] = s;
  }});

  // BB
  const bbU = chart.addLineSeries({{ color: COLORS.bb, lineWidth: 1, lineStyle: 2, lastValueVisible: false, priceLineVisible: false }});
  const bbM = chart.addLineSeries({{ color: COLORS.bb, lineWidth: 1, lineStyle: 1, lastValueVisible: false, priceLineVisible: false }});
  const bbL = chart.addLineSeries({{ color: COLORS.bb, lineWidth: 1, lineStyle: 2, lastValueVisible: false, priceLineVisible: false }});
  bbU.setData(raw.filter(d => d.bb_upper).map(d => ({{ time: toTS(d), value: d.bb_upper }})));
  bbM.setData(raw.filter(d => d.bb_mid).map(d => ({{ time: toTS(d), value: d.bb_mid }})));
  bbL.setData(raw.filter(d => d.bb_lower).map(d => ({{ time: toTS(d), value: d.bb_lower }})));

  // Sync time scale
  chart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
    if (range) vchart.timeScale().setVisibleLogicalRange(range);
  }});

  window.__charts__[code] = {{ chart, vchart, candleSeries, maSeries, bbU, bbM, bbL, raw, toTS }};
  window.__chartState__[code] = {{ showMA: true, showBB: false, type: 'candlestick', range: 180 }};
  setRange(code, 180);

  // Resize
  new ResizeObserver(() => {{
    chart.applyOptions({{ width: el.clientWidth }});
    vchart.applyOptions({{ width: vel.clientWidth }});
  }}).observe(el);
}}

function setChartType(code, type) {{
  const c = window.__charts__[code];
  if (!c) return;
  window.__chartState__[code].type = type;
  // lightweight-charts v4 candlestick toggle via visible
  // simple approach: hide/show opacity via series
  document.querySelectorAll(`#tab-${{code}} .chart-btn`).forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}}

function toggleMA(code) {{
  const c = window.__charts__[code];
  if (!c) return;
  const st = window.__chartState__[code];
  st.showMA = !st.showMA;
  Object.values(c.maSeries).forEach(s => s.applyOptions({{ visible: st.showMA }}));
}}

function toggleBB(code) {{
  const c = window.__charts__[code];
  if (!c) return;
  const st = window.__chartState__[code];
  st.showBB = !st.showBB;
  c.bbU.applyOptions({{ visible: st.showBB }});
  c.bbM.applyOptions({{ visible: st.showBB }});
  c.bbL.applyOptions({{ visible: st.showBB }});
}}

function setRange(code, days) {{
  const c = window.__charts__[code];
  if (!c) return;
  const all = c.raw;
  const cutoff = all.length - days;
  const fromIdx = Math.max(0, cutoff);
  c.chart.timeScale().setVisibleLogicalRange({{ from: fromIdx, to: all.length - 1 }});
  c.vchart.timeScale().setVisibleLogicalRange({{ from: fromIdx, to: all.length - 1 }});
  document.querySelectorAll(`#tab-${{code}} .chart-btn`).forEach(b => {{
    if (['1M','3M','6M','1Y'].includes(b.textContent)) b.classList.remove('active');
  }});
  const rangeMap = {{30:'1M', 90:'3M', 180:'6M', 365:'1Y'}};
  document.querySelectorAll(`#tab-${{code}} .chart-btn`).forEach(b => {{
    if (b.textContent === rangeMap[days]) b.classList.add('active');
  }});
}}

// ── Init on load ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {{
  initChart('VNINDEX');
}});
</script>
</body>
</html>
"""


def main():
    os.makedirs("docs", exist_ok=True)
    data = load_data()
    html = build_html(data)
    out  = "docs/index.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ Đã tạo {out} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
