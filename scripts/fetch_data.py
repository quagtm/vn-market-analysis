"""
VN Market Analysis - Data Fetcher
Dùng TCBS public API - không cần API key, không rate limit
"""

import json
import os
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────

DAYS_HISTORY = 400
END_DATE     = datetime.today().strftime("%Y-%m-%d")
START_DATE   = (datetime.today() - timedelta(days=DAYS_HISTORY)).strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer": "https://tcinvest.tcbs.com.vn/",
    "Origin": "https://tcinvest.tcbs.com.vn",
}

VN30_SYMBOLS = [
    "ACB","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG","LPB",
    "MBB","MSN","MWG","PLX","POW","SAB","SHB","SSB","SSI","STB",
    "TCB","TPB","VCB","VHM","VIB","VJC","VNM","VPB","VRE","VIC"
]

VN100_SYMBOLS = VN30_SYMBOLS + [
    "VCI","KDH","PDR","DXG","NLG","DGC","HCM","SCS","DPM","PVT",
    "GEX","REE","PNJ","EIB","POW","PVD","HSG","NKG","CMG","EVF"
]

SECTOR_MAP = {
    "Ngân hàng":    ["VCB","BID","CTG","TCB","MBB","VPB","HDB","ACB","STB","LPB","SHB","TPB","SSB"],
    "Bất động sản": ["VIC","VHM","KDH","VRE","PDR","DXG","NLG"],
    "Thép/Khoáng":  ["HPG","HSG","NKG","DGC"],
    "Tiêu dùng":    ["MSN","VNM","SAB","MWG","PNJ"],
    "Dầu khí":      ["GAS","PLX","POW","PVT","DPM"],
    "Công nghệ":    ["FPT","CMG"],
    "Chứng khoán":  ["SSI","HCM","VCI","SHS"],
}


# ─── TCBS API ─────────────────────────────────────────────────────────────────

def fetch_index_history(ticker: str, count: int = 400) -> pd.DataFrame:
    """Lấy OHLCV index từ TCBS public API"""
    url = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/index/history"
    params = {"ticker": ticker, "type": "stock", "count": count}
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()

    # TCBS trả về list các candle
    candles = data.get("data", data) if isinstance(data, dict) else data
    if not candles:
        raise ValueError(f"Không có dữ liệu cho {ticker}")

    df = pd.DataFrame(candles)

    # Map tên cột TCBS -> chuẩn
    col_map = {
        "tradingDate": "time", "open": "open", "high": "high",
        "low": "low", "close": "close", "volume": "volume",
        "o": "open", "h": "high", "l": "low", "c": "close",
        "v": "volume", "t": "time", "d": "time",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Đảm bảo có cột time
    if "time" not in df.columns:
        for candidate in ["date", "tradingDate", "Date"]:
            if candidate in df.columns:
                df = df.rename(columns={candidate: "time"})
                break

    df["time"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%d")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)

    df = df.sort_values("time").reset_index(drop=True)
    return df


def fetch_stock_history(symbol: str, days: int = 10) -> pd.DataFrame:
    """Lấy lịch sử giá cổ phiếu từ TCBS"""
    url = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term"
    params = {"ticker": symbol, "type": "stock", "resolution": "D", "countBack": days}
    r = requests.get(url, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()
    candles = data.get("data", [])
    if not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles)
    df = df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume","t":"time"})
    if "time" in df.columns:
        # TCBS trả về unix timestamp
        if df["time"].iloc[0] > 1e9:
            df["time"] = pd.to_datetime(df["time"], unit="s").dt.strftime("%Y-%m-%d")
        else:
            df["time"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%d")
    for col in ["open","high","low","close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce") * 1000
    df["volume"] = pd.to_numeric(df.get("volume",0), errors="coerce").fillna(0)
    return df.sort_values("time").reset_index(drop=True)


# ─── Indicators ───────────────────────────────────────────────────────────────

def safe_float(v, decimals=2):
    try:
        return round(float(v), decimals)
    except Exception:
        return None


def calc_rma(series: pd.Series, period: int) -> pd.Series:
    result = series.copy().astype(float) * np.nan
    valid  = series.dropna()
    if len(valid) < period:
        return result
    idx = valid.index
    result.loc[idx[period-1]] = valid.iloc[:period].mean()
    for i in range(period, len(valid)):
        result.loc[idx[i]] = (result.loc[idx[i-1]] * (period-1) + valid.iloc[i]) / period
    return result


def calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values("time").reset_index(drop=True)
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    v = df["volume"].astype(float)

    for p in [5, 10, 20, 50, 100, 200]:
        df["ma" + str(p)] = c.rolling(p).mean()

    df["vol_ma20"] = v.rolling(20).mean()

    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    df["atr14"] = calc_rma(tr, 14)

    df["bb_mid"]   = c.rolling(20).mean()
    bb_std         = c.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std

    delta = c.diff()
    df["rsi14"] = 100 - 100 / (1 + calc_rma(delta.clip(lower=0), 14) /
                               calc_rma((-delta).clip(lower=0), 14).replace(0, np.nan))

    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]        = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    lo14 = l.rolling(14).min()
    hi14 = h.rolling(14).max()
    df["stoch_k"] = 100 * (c - lo14) / (hi14 - lo14).replace(0, np.nan)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    last  = df.iloc[-1]
    pivot = (float(last["high"]) + float(last["low"]) + float(last["close"])) / 3
    df.attrs["pivot"] = safe_float(pivot)
    df.attrs["r1"]    = safe_float(2*pivot - float(last["low"]))
    df.attrs["r2"]    = safe_float(pivot + float(last["high"]) - float(last["low"]))
    df.attrs["r3"]    = safe_float(float(last["high"]) + 2*(pivot - float(last["low"])))
    df.attrs["s1"]    = safe_float(2*pivot - float(last["high"]))
    df.attrs["s2"]    = safe_float(pivot - float(last["high"]) + float(last["low"]))
    df.attrs["s3"]    = safe_float(float(last["low"]) - 2*(float(last["high"]) - pivot))

    hi52 = h.tail(252).max()
    lo52 = l.tail(252).min()
    diff = hi52 - lo52
    df.attrs["fibo_236"] = safe_float(hi52 - 0.236 * diff)
    df.attrs["fibo_382"] = safe_float(hi52 - 0.382 * diff)
    df.attrs["fibo_500"] = safe_float(hi52 - 0.500 * diff)
    df.attrs["fibo_618"] = safe_float(hi52 - 0.618 * diff)
    df.attrs["fibo_786"] = safe_float(hi52 - 0.786 * diff)
    df.attrs["hi52"]     = safe_float(hi52)
    df.attrs["lo52"]     = safe_float(lo52)

    return df


def snapshot(df: pd.DataFrame) -> dict:
    last       = df.iloc[-1]
    prev       = df.iloc[-2] if len(df) > 1 else last
    close      = float(last["close"])
    prev_close = float(prev["close"])
    chg        = close - prev_close
    chg_pct    = chg / prev_close * 100 if prev_close else 0

    def col(name):
        val = last.get(name)
        return safe_float(val) if pd.notna(val) else None

    return {
        "date": str(last["time"])[:10],
        "close": safe_float(close), "open": safe_float(float(last["open"])),
        "high": safe_float(float(last["high"])), "low": safe_float(float(last["low"])),
        "volume": int(last["volume"]),
        "change": safe_float(chg), "change_pct": safe_float(chg_pct),
        "ma5": col("ma5"), "ma10": col("ma10"), "ma20": col("ma20"),
        "ma50": col("ma50"), "ma100": col("ma100"), "ma200": col("ma200"),
        "bb_upper": col("bb_upper"), "bb_mid": col("bb_mid"), "bb_lower": col("bb_lower"),
        "rsi14": col("rsi14"),
        "macd": col("macd"), "macd_signal": col("macd_signal"), "macd_hist": col("macd_hist"),
        "stoch_k": col("stoch_k"), "stoch_d": col("stoch_d"),
        "atr14": col("atr14"), "vol_ma20": col("vol_ma20"),
        "pivot": df.attrs.get("pivot"),
        "r1": df.attrs.get("r1"), "r2": df.attrs.get("r2"), "r3": df.attrs.get("r3"),
        "s1": df.attrs.get("s1"), "s2": df.attrs.get("s2"), "s3": df.attrs.get("s3"),
        "fibo_236": df.attrs.get("fibo_236"), "fibo_382": df.attrs.get("fibo_382"),
        "fibo_500": df.attrs.get("fibo_500"), "fibo_618": df.attrs.get("fibo_618"),
        "fibo_786": df.attrs.get("fibo_786"),
        "hi52": df.attrs.get("hi52"), "lo52": df.attrs.get("lo52"),
    }


def ohlcv_records(df: pd.DataFrame, n=365) -> list:
    cols = ["time","open","high","low","close","volume",
            "ma5","ma10","ma20","ma50","ma100","ma200",
            "bb_upper","bb_mid","bb_lower","rsi14",
            "macd","macd_signal","macd_hist","stoch_k","stoch_d"]
    sub = df.tail(n)[[c for c in cols if c in df.columns]].copy()
    sub["time"] = sub["time"].astype(str).str[:10]
    return sub.where(pd.notnull(sub), None).to_dict(orient="records")


# ─── Top Movers & Sectors ─────────────────────────────────────────────────────

def get_top_movers(symbols: list) -> dict:
    """Lấy top movers - gọi batch từ TCBS"""
    results = []
    for sym in symbols[:30]:
        try:
            df = fetch_stock_history(sym, days=5)
            if df is None or len(df) < 2:
                continue
            close = float(df.iloc[-1]["close"])
            prev  = float(df.iloc[-2]["close"])
            chg_pct = (close - prev) / prev * 100 if prev else 0
            results.append({"symbol": sym, "close": close, "change_pct": round(chg_pct, 2)})
            time.sleep(0.3)  # nhẹ nhàng với server
        except Exception:
            continue

    results.sort(key=lambda x: x["change_pct"], reverse=True)
    return {
        "top_gainers": results[:3],
        "top_losers":  results[-3:][::-1] if len(results) >= 3 else results[::-1][:3],
    }


def get_sector_performance(symbols: list) -> dict:
    """Tính hiệu suất theo ngành"""
    sector_results = {}
    for sector, tickers in SECTOR_MAP.items():
        chg_list = []
        for sym in tickers:
            if symbols and sym not in symbols:
                continue
            try:
                df = fetch_stock_history(sym, days=5)
                if df is None or len(df) < 2:
                    continue
                c = float(df.iloc[-1]["close"])
                p = float(df.iloc[-2]["close"])
                chg_list.append((c - p) / p * 100 if p else 0)
                time.sleep(0.2)
            except Exception:
                continue
        if chg_list:
            sector_results[sector] = round(sum(chg_list) / len(chg_list), 2)

    sorted_s = sorted(sector_results.items(), key=lambda x: x[1], reverse=True)
    return {
        "leading": [{"name": k, "change_pct": v} for k, v in sorted_s[:3]],
        "lagging": [{"name": k, "change_pct": v} for k, v in sorted_s[-3:][::-1]],
        "all":     dict(sorted_s),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

INDEX_CONFIG = {
    "VNINDEX": {"ticker": "VNINDEX", "symbols": VN30_SYMBOLS},
    "VN30":    {"ticker": "VN30",    "symbols": VN30_SYMBOLS},
    "VN100":   {"ticker": "VN100",   "symbols": VN100_SYMBOLS},
}


def fetch_index(index_code: str) -> dict:
    cfg = INDEX_CONFIG[index_code]
    print("\n" + "="*50)
    print("  Fetching " + index_code + " via TCBS API ...")

    hist = fetch_index_history(cfg["ticker"], count=DAYS_HISTORY)
    print("  -> " + str(len(hist)) + " candles")

    if len(hist) < 50:
        raise ValueError("Không đủ dữ liệu: chỉ có " + str(len(hist)) + " rows")

    # Scale nếu cần (VNINDEX thường ~1200, không cần scale)
    for col in ["open","high","low","close"]:
        if hist[col].max() < 100:
            hist[col] = hist[col] * 1000

    hist = calc_indicators(hist)
    snap = snapshot(hist)
    ohlcv = ohlcv_records(hist)

    print("  -> Lấy top movers ...")
    movers = get_top_movers(cfg["symbols"])

    print("  -> Lấy sector performance ...")
    sectors = get_sector_performance(cfg["symbols"])

    return {
        "index":     index_code,
        "snapshot":  snap,
        "ohlcv":     ohlcv,
        "movers":    movers,
        "sectors":   sectors,
        "symbols":   cfg["symbols"],
        "generated": datetime.now().isoformat(),
    }


def main():
    os.makedirs("data", exist_ok=True)
    all_data = {}

    for index_code in INDEX_CONFIG:
        try:
            data = fetch_index(index_code)
            all_data[index_code] = data
            chg = data["snapshot"].get("change_pct") or 0
            print("  OK " + index_code + ": " + str(data["snapshot"]["close"]) +
                  " (" + "{:+.2f}".format(chg) + "%)")
        except Exception as e:
            print("  FAIL " + index_code + ": " + str(e))
            all_data[index_code] = {"error": str(e), "index": index_code}

    all_data["generated_at"] = datetime.now().isoformat()

    out = "data/market_data.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

    print("\nDa luu -> " + out + " (" + str(os.path.getsize(out)) + " bytes)")


if __name__ == "__main__":
    main()
