"""
VN Market Analysis - Data Fetcher
Lấy dữ liệu từ vnstock, tính toán chỉ báo kỹ thuật
"""

import json
import os
import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# ─── vnstock ───────────────────────────────────────────────────────────────────
import vnai
from vnstock.api.quote import Quote
from vnstock.api.listing import Listing

# Setup API key từ GitHub Secret
_api_key = os.environ.get("vnstock_149d30a66f8b96efc43ca373a903b58b", "")
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
    """Wilder's smoothed MA (RMA)"""
    result = series.copy().astype(float)
    result[:] = np.nan
    valid = series.dropna()
    if len(valid) < period:
        return result
    result.iloc[valid.index.get_loc(valid.index[period - 1])] = valid.iloc[:period].mean()
    for i in range(period, len(valid)):
        prev = result.iloc[valid.index.get_loc(valid.index[i - 1])]
        result.iloc[valid.index.get_loc(valid.index[i])] = (prev * (period - 1) + valid.iloc[i]) / period
    return result


def calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tính toán toàn bộ chỉ báo kỹ thuật"""
    df = df.copy().sort_values("time").reset_index(drop=True)
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    v = df["volume"].astype(float)

    # Moving Averages
    for p in [5, 10, 20, 50, 100, 200]:
        df[f"ma{p}"] = c.rolling(p).mean()

    # Volume MA20
    df["vol_ma20"] = v.rolling(20).mean()

    # ATR(14)
    tr = pd.concat([
        h - l,
        (h - c.shift()).abs(),
        (l - c.shift()).abs()
    ], axis=1).max(axis=1)
    df["atr14"] = calc_rma(tr, 14)

    # Bollinger Bands (20, 2)
    df["bb_mid"]   = c.rolling(20).mean()
    bb_std         = c.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std

    # RSI(14)
    delta = c.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    df["rsi14"] = 100 - 100 / (1 + calc_rma(gain, 14) / calc_rma(loss, 14).replace(0, np.nan))

    # MACD (12,26,9)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]        = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    # Stochastic (14,3)
    lo14 = l.rolling(14).min()
    hi14 = h.rolling(14).max()
    df["stoch_k"] = 100 * (c - lo14) / (hi14 - lo14).replace(0, np.nan)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # Pivot Points (last day)
    last = df.iloc[-1]
    pivot = (last["high"] + last["low"] + last["close"]) / 3
    df.attrs["pivot"]  = safe_float(pivot)
    df.attrs["r1"]     = safe_float(2 * pivot - last["low"])
    df.attrs["r2"]     = safe_float(pivot + (last["high"] - last["low"]))
    df.attrs["r3"]     = safe_float(last["high"] + 2 * (pivot - last["low"]))
    df.attrs["s1"]     = safe_float(2 * pivot - last["high"])
    df.attrs["s2"]     = safe_float(pivot - (last["high"] - last["low"]))
    df.attrs["s3"]     = safe_float(last["low"] - 2 * (last["high"] - pivot))

    # Fibonacci Retracement (52-week high/low)
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
    """Lấy snapshot cuối ngày + chỉ báo"""
    last  = df.iloc[-1]
    prev  = df.iloc[-2] if len(df) > 1 else last
    close = float(last["close"])
    prev_close = float(prev["close"])
    chg   = close - prev_close
    chg_pct = chg / prev_close * 100 if prev_close else 0

    def col(name):
        return safe_float(last.get(name))

    return {
        "date":       str(last["time"])[:10],
        "close":      safe_float(close),
        "open":       safe_float(float(last["open"])),
        "high":       safe_float(float(last["high"])),
        "low":        safe_float(float(last["low"])),
        "volume":     int(last["volume"]),
        "change":     safe_float(chg),
        "change_pct": safe_float(chg_pct),
        "ma5":        col("ma5"),
        "ma10":       col("ma10"),
        "ma20":       col("ma20"),
        "ma50":       col("ma50"),
        "ma100":      col("ma100"),
        "ma200":      col("ma200"),
        "bb_upper":   col("bb_upper"),
        "bb_mid":     col("bb_mid"),
        "bb_lower":   col("bb_lower"),
        "rsi14":      col("rsi14"),
        "macd":       col("macd"),
        "macd_signal":col("macd_signal"),
        "macd_hist":  col("macd_hist"),
        "stoch_k":    col("stoch_k"),
        "stoch_d":    col("stoch_d"),
        "atr14":      col("atr14"),
        "vol_ma20":   col("vol_ma20"),
        "pivot":      df.attrs.get("pivot"),
        "r1": df.attrs.get("r1"), "r2": df.attrs.get("r2"), "r3": df.attrs.get("r3"),
        "s1": df.attrs.get("s1"), "s2": df.attrs.get("s2"), "s3": df.attrs.get("s3"),
        "fibo_236":   df.attrs.get("fibo_236"),
        "fibo_382":   df.attrs.get("fibo_382"),
        "fibo_500":   df.attrs.get("fibo_500"),
        "fibo_618":   df.attrs.get("fibo_618"),
        "fibo_786":   df.attrs.get("fibo_786"),
        "hi52":       df.attrs.get("hi52"),
        "lo52":       df.attrs.get("lo52"),
    }


def ohlcv_records(df: pd.DataFrame, n=365) -> list:
    """Trả về n ngày gần nhất dạng list of dict cho chart"""
    cols = ["time","open","high","low","close","volume",
            "ma5","ma10","ma20","ma50","ma100","ma200",
            "bb_upper","bb_mid","bb_lower","rsi14",
            "macd","macd_signal","macd_hist","stoch_k","stoch_d"]
    sub = df.tail(n)[cols].copy()
    sub["time"] = sub["time"].astype(str).str[:10]
    return sub.where(pd.notnull(sub), None).to_dict(orient="records")


# ─── VN30 / VN100 constituent stocks ─────────────────────────────────────────

def get_index_constituents(index_code: str) -> list[str]:
    """Lấy danh sách mã cổ phiếu trong rổ index"""
    try:
        stock = Listing(source="VCI")
        if index_code == "VN30":
            df = stock.symbols_by_group("VN30")
        elif index_code == "VN100":
            df = stock.symbols_by_group("VN100")
        else:
            df = stock.symbols_by_group("HOSE")
        if isinstance(df, pd.DataFrame):
            return df["symbol"].tolist()[:50]
        return list(df)[:50]
    except Exception as e:
        print(f"  [WARN] Không lấy được constituents {index_code}: {e}")
        # Fallback: VN30 blue chips
        if index_code == "VN30":
            return ["ACB","BID","BSR","CTG","FPT","GAS","GVR","HDB","HPG","LPB",
                    "MBB","MSN","MWG","PLX","SAB","SHB","SSB","SSI","STB","TCB",
                    "TPB","VCB","VHM","VIB","VIB","VJC","VNM","VPB","VRE","VPL"]
        elif index_code == "VN100":
            return ["VCB","BID","CTG","TCB","MBB","VPB","HPG","VIC","VHM","MSN",
                    "GAS","SAB","VNM","PLX","POW","FPT","MWG","PNJ","REE","SHB",
                    "SSI","HDB","VCI","ACB","STB","EIB","LPB","KDH","VRE","PDR",
                    "DGC","GVR","HCM","IDC","KBC","NLG","DPM","PVT","SCS","SIP"]
        return []


def get_top_movers(symbols: list[str], date_str: str) -> dict:
    """Lấy top gainers/losers trong ngày"""
    results = []
    stock_client = Quote(symbol="VCB", source="VCI")
    
    for sym in symbols[:40]:  # giới hạn để tránh timeout
        try:
            hist = stock_client.quote.history(
                symbol=sym,
                start=(datetime.today() - timedelta(days=5)).strftime("%Y-%m-%d"),
                end=date_str,
                interval="1D"
            )
            if hist is None or len(hist) < 2:
                continue
            hist = hist.sort_values("time")
            close = float(hist.iloc[-1]["close"])
            prev  = float(hist.iloc[-2]["close"])
            # Scale nếu cần
            if close < 1000:
                close *= 1000
                prev  *= 1000
            chg_pct = (close - prev) / prev * 100 if prev else 0
            results.append({"symbol": sym, "close": close, "change_pct": round(chg_pct, 2)})
        except Exception:
            continue

    results.sort(key=lambda x: x["change_pct"], reverse=True)
    return {
        "top_gainers": results[:3],
        "top_losers":  results[-3:][::-1],
    }


def get_sector_performance(symbols: list[str], date_str: str) -> dict:
    """Phân nhóm ngành và tính hiệu suất"""
    sector_map = {
        "Ngân hàng":     ["VCB","BID","CTG","TCB","MBB","VPB","HDB","ACB","STB","EIB","LPB","SHB"],
        "Bất động sản":  ["VIC","VHM","NVL","KDH","VRE","PDR","DXG","NLG","IDC","KBC"],
        "Thép/Khoáng":   ["HPG","HSG","NKG","TLH","TVN","DGC"],
        "Tiêu dùng":     ["MSN","VNM","SAB","MWG","PNJ","BAF"],
        "Dầu khí":       ["GAS","PLX","POW","PVT","PVD","DPM"],
        "Công nghệ":     ["FPT","CMG","VGI","ELC"],
        "Chứng khoán":   ["SSI","HCM","VCI","SHS","MBS","VDS"],
    }
    stock_client = Vnstock().stock(symbol="VCB", source="VCI")
    sector_results = {}

    for sector, tickers in sector_map.items():
        chg_list = []
        for sym in tickers:
            if sym not in symbols and symbols:
                continue
            try:
                hist = stock_client.quote.history(
                    symbol=sym,
                    start=(datetime.today() - timedelta(days=5)).strftime("%Y-%m-%d"),
                    end=date_str, interval="1D"
                )
                if hist is None or len(hist) < 2:
                    continue
                hist = hist.sort_values("time")
                c = float(hist.iloc[-1]["close"])
                p = float(hist.iloc[-2]["close"])
                if c < 1000: c *= 1000; p *= 1000
                chg_list.append((c - p) / p * 100 if p else 0)
            except Exception:
                continue
        if chg_list:
            sector_results[sector] = round(sum(chg_list) / len(chg_list), 2)

    sorted_sectors = sorted(sector_results.items(), key=lambda x: x[1], reverse=True)
    return {
        "leading":  [{"name": k, "change_pct": v} for k,v in sorted_sectors[:3]],
        "lagging":  [{"name": k, "change_pct": v} for k,v in sorted_sectors[-3:][::-1]],
        "all":      dict(sorted_sectors),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def fetch_index(index_code: str, symbol: str) -> dict:
    print(f"\n{'='*50}")
    print(f"  Fetching {index_code} ...")
    stock_client = Quote(symbol=symbol, source="VCI")

    # Lấy OHLCV
    hist = stock_client.quote.history(
        symbol=symbol,
        start=START_DATE,
        end=END_DATE,
        interval="1D"
    )
    if hist is None or len(hist) < 50:
        raise ValueError(f"Không đủ dữ liệu cho {index_code}")

    # Chuẩn hóa tên cột
    hist.columns = [c.lower() for c in hist.columns]
    for col in ["open","high","low","close"]:
        hist[col] = hist[col].astype(float)
        if hist[col].max() < 1000:
            hist[col] = hist[col] * 1000

    hist = calc_indicators(hist)
    snap = snapshot(hist)
    ohlcv = ohlcv_records(hist)

    # Constituents
    symbols = get_index_constituents(index_code)
    print(f"  -> {len(symbols)} cổ phiếu trong rổ {index_code}")

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
            print(f"  ✓ {index_code}: {data['snapshot']['close']} ({data['snapshot']['change_pct']:+.2f}%)")
        except Exception as e:
            print(f"  ✗ {index_code} lỗi: {e}")
            all_data[index_code] = {"error": str(e), "index": index_code}

    # Lưu JSON
    out_path = "data/market_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✓ Đã lưu dữ liệu -> {out_path}")
    print(f"  Kích thước: {os.path.getsize(out_path):,} bytes")


if __name__ == "__main__":
    main()
