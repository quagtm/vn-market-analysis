"""
VN Market Analysis - Data Fetcher
Lấy dữ liệu từ vnstock, tính toán chỉ báo kỹ thuật
"""

import json
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# ─── vnstock API mới ──────────────────────────────────────────────────────────
import vnai
from vnstock.api.quote import Quote
from vnstock.api.listing import Listing

# Setup API key từ GitHub Secret
_api_key = os.environ.get("VNSTOCK_API_KEY", "")
if _api_key:
    vnai.setup_api_key(_api_key)

INDICES = {
    "VNINDEX": "VNINDEX",
    "VN30":    "VN30",
    "VN100":   "VN100",
}

DAYS_HISTORY = 365
END_DATE   = datetime.today().strftime("%Y-%m-%d")
START_DATE = (datetime.today() - timedelta(days=DAYS_HISTORY + 60)).strftime("%Y-%m-%d")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_float(v, decimals=2):
    try:
        return round(float(v), decimals)
    except Exception:
        return None


def calc_rma(series: pd.Series, period: int) -> pd.Series:
    result = series.copy().astype(float)
    result[:] = np.nan
    valid = series.dropna()
    if len(valid) < period:
        return result
    idx = valid.index
    result.loc[idx[period - 1]] = valid.iloc[:period].mean()
    for i in range(period, len(valid)):
        result.loc[idx[i]] = (result.loc[idx[i-1]] * (period - 1) + valid.iloc[i]) / period
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

    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    df["atr14"] = calc_rma(tr, 14)

    df["bb_mid"]   = c.rolling(20).mean()
    bb_std         = c.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std

    delta = c.diff()
    df["rsi14"] = 100 - 100 / (1 + calc_rma(delta.clip(lower=0), 14) / calc_rma((-delta).clip(lower=0), 14).replace(0, np.nan))

    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]         = ema12 - ema26
    df["macd_signal"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]    = df["macd"] - df["macd_signal"]

    lo14 = l.rolling(14).min()
    hi14 = h.rolling(14).max()
    df["stoch_k"] = 100 * (c - lo14) / (hi14 - lo14).replace(0, np.nan)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    last  = df.iloc[-1]
    pivot = (float(last["high"]) + float(last["low"]) + float(last["close"])) / 3
    df.attrs["pivot"] = safe_float(pivot)
    df.attrs["r1"]    = safe_float(2 * pivot - float(last["low"]))
    df.attrs["r2"]    = safe_float(pivot + float(last["high"]) - float(last["low"]))
    df.attrs["r3"]    = safe_float(float(last["high"]) + 2 * (pivot - float(last["low"])))
    df.attrs["s1"]    = safe_float(2 * pivot - float(last["high"]))
    df.attrs["s2"]    = safe_float(pivot - float(last["high"]) + float(last["low"]))
    df.attrs["s3"]    = safe_float(float(last["low"]) - 2 * (float(last["high"]) - pivot))

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
        return safe_float(val) if val is not None else None

    return {
        "date":        str(last["time"])[:10],
        "close":       safe_float(close),
        "open":        safe_float(float(last["open"])),
        "high":        safe_float(float(last["high"])),
        "low":         safe_float(float(last["low"])),
        "volume":      int(last["volume"]),
        "change":      safe_float(chg),
        "change_pct":  safe_float(chg_pct),
        "ma5":         col("ma5"),   "ma10":  col("ma10"),
        "ma20":        col("ma20"),  "ma50":  col("ma50"),
        "ma100":       col("ma100"), "ma200": col("ma200"),
        "bb_upper":    col("bb_upper"), "bb_mid": col("bb_mid"), "bb_lower": col("bb_lower"),
        "rsi14":       col("rsi14"),
        "macd":        col("macd"), "macd_signal": col("macd_signal"), "macd_hist": col("macd_hist"),
        "stoch_k":     col("stoch_k"), "stoch_d": col("stoch_d"),
        "atr14":       col("atr14"),
        "vol_ma20":    col("vol_ma20"),
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
    sub = df.tail(n)[cols].copy()
    sub["time"] = sub["time"].astype(str).str[:10]
    return sub.where(pd.notnull(sub), None).to_dict(orient="records")


# ─── Index constituents ───────────────────────────────────────────────────────

VN30_DEFAULT  = ["ACB","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG","LPB",
                 "MBB","MSN","MWG","PLX","SAB","SHB","SSB","SSI","STB","TCB",
                 "TPB","VCB","VHM","VIB","VJC","VNM","VPB","VRE","VIC","VPL"]
VN100_DEFAULT = VN30_DEFAULT + ["VCI","KDH","PDR","DXG","NLG","IDC","KBC",
                 "DGC","HCM","SCS","DPM","PVT","GEX","REE","PNJ","MWG",
                 "EIB","POW","PVD","HSG","NKG","CMG","FPT","EVF","VDS"]

def get_index_constituents(index_code: str) -> list:
    try:
        lst = Listing(source="VCI")
        if index_code == "VN30":
            df = lst.symbols_by_group("VN30")
        elif index_code == "VN100":
            df = lst.symbols_by_group("VN100")
        else:
            df = lst.symbols_by_group("HOSE")
        if isinstance(df, pd.DataFrame) and "symbol" in df.columns:
            return df["symbol"].tolist()[:50]
        return list(df)[:50]
    except Exception as e:
        print("  [WARN] Constituents fallback:", e)
        if index_code == "VN30":
            return VN30_DEFAULT
        elif index_code == "VN100":
            return VN100_DEFAULT
        return VN30_DEFAULT


# ─── Movers & Sectors ─────────────────────────────────────────────────────────

def get_top_movers(symbols: list, date_str: str) -> dict:
    return {"top_gainers": [], "top_losers": []}


def get_sector_performance(symbols: list, date_str: str) -> dict:
    return {"leading": [], "lagging": [], "all": {}}


# ─── Main ─────────────────────────────────────────────────────────────────────

def fetch_index(index_code: str, symbol: str) -> dict:
    print("\n" + "=" * 50)
    print("  Fetching " + index_code + " ...")

    q    = Quote(symbol=symbol, source="VCI")
    hist = q.history(start=START_DATE, end=END_DATE, interval="1D")

    if hist is None or len(hist) < 50:
        raise ValueError("Không đủ dữ liệu cho " + index_code)

    hist.columns = [c.lower() for c in hist.columns]
    for col in ["open", "high", "low", "close"]:
        hist[col] = hist[col].astype(float)
        if hist[col].max() < 1000:
            hist[col] = hist[col] * 1000

    hist = calc_indicators(hist)
    snap = snapshot(hist)
    ohlcv = ohlcv_records(hist)

    symbols = get_index_constituents(index_code)
    print("  -> " + str(len(symbols)) + " cổ phiếu trong rổ " + index_code)

    movers  = get_top_movers(symbols, END_DATE)
    sectors = get_sector_performance(symbols, END_DATE)

    return {
        "index":     index_code,
        "snapshot":  snap,
        "ohlcv":     ohlcv,
        "movers":    movers,
        "sectors":   sectors,
        "symbols":   symbols,
        "generated": datetime.now().isoformat(),
    }


def main():
    os.makedirs("data", exist_ok=True)
    all_data = {}

    for index_code, symbol in INDICES.items():
        try:
            data = fetch_index(index_code, symbol)
            all_data[index_code] = data
            chg = data["snapshot"]["change_pct"] or 0
            print("  OK " + index_code + ": " + str(data["snapshot"]["close"]) + " (" + "{:+.2f}".format(chg) + "%)")
        except Exception as e:
            print("  FAIL " + index_code + ": " + str(e))
            all_data[index_code] = {"error": str(e), "index": index_code}

    out_path = "data/market_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

    print("\nDa luu du lieu -> " + out_path)
    print("Kich thuoc: " + str(os.path.getsize(out_path)) + " bytes")


if __name__ == "__main__":
    main()
