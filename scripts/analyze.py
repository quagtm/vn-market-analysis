"""
VN Market Analysis - AI Analysis Engine
Gửi dữ liệu kỹ thuật tới DeepSeek để sinh phân tích tự nhiên
"""

import json
import os
import time
from datetime import datetime
from openai import OpenAI  # DeepSeek dùng OpenAI-compatible API

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


def build_prompt(index_code: str, data: dict) -> str:
    snap    = data.get("snapshot", {})
    sectors = data.get("sectors", {})
    movers  = data.get("movers", {})

    leading_str = ", ".join(
        f"{s['name']} ({s['change_pct']:+.1f}%)"
        for s in sectors.get("leading", [])
    )
    lagging_str = ", ".join(
        f"{s['name']} ({s['change_pct']:+.1f}%)"
        for s in sectors.get("lagging", [])
    )
    gainers_str = ", ".join(
        f"{s['symbol']} ({s['change_pct']:+.1f}%)"
        for s in movers.get("top_gainers", [])
    )
    losers_str  = ", ".join(
        f"{s['symbol']} ({s['change_pct']:+.1f}%)"
        for s in movers.get("top_losers", [])
    )

    def v(key, fmt=".1f"):
        val = snap.get(key)
        return f"{val:{fmt}}" if val is not None else "N/A"

    prompt = f"""Bạn là chuyên gia phân tích kỹ thuật chứng khoán Việt Nam chuyên nghiệp với 15 năm kinh nghiệm. 
Hãy phân tích {index_code} dựa trên dữ liệu kỹ thuật ngày {snap.get('date','hôm nay')} và trả về JSON theo đúng schema sau.

=== DỮ LIỆU KỸ THUẬT ===
Giá đóng cửa: {v('close', '.2f')} | Thay đổi: {v('change_pct', '+.2f')}%
Open/High/Low: {v('open', '.2f')} / {v('high', '.2f')} / {v('low', '.2f')}
Khối lượng: {snap.get('volume', 'N/A'):,} | Vol MA20: {v('vol_ma20', '.0f')}

Moving Averages:
  MA5={v('ma5', '.2f')} | MA10={v('ma10', '.2f')} | MA20={v('ma20', '.2f')}
  MA50={v('ma50', '.2f')} | MA100={v('ma100', '.2f')} | MA200={v('ma200', '.2f')}

Bollinger Bands: Upper={v('bb_upper', '.2f')} | Mid={v('bb_mid', '.2f')} | Lower={v('bb_lower', '.2f')}
RSI(14): {v('rsi14', '.1f')} | Stoch K/D: {v('stoch_k', '.1f')}/{v('stoch_d', '.1f')}
MACD: {v('macd', '.2f')} | Signal: {v('macd_signal', '.2f')} | Hist: {v('macd_hist', '.2f')}
ATR(14): {v('atr14', '.2f')}

Pivot: {v('pivot', '.2f')} | R1={v('r1', '.2f')} R2={v('r2', '.2f')} R3={v('r3', '.2f')}
                            | S1={v('s1', '.2f')} S2={v('s2', '.2f')} S3={v('s3', '.2f')}
Fibonacci (52w Hi={v('hi52', '.2f')}, Lo={v('lo52', '.2f')}):
  23.6%={v('fibo_236', '.2f')} | 38.2%={v('fibo_382', '.2f')} | 50%={v('fibo_500', '.2f')}
  61.8%={v('fibo_618', '.2f')} | 78.6%={v('fibo_786', '.2f')}

Nhóm ngành dẫn dắt: {leading_str or 'N/A'}
Nhóm ngành đi lùi:  {lagging_str or 'N/A'}
Top 3 tác động tích cực: {gainers_str or 'N/A'}
Top 3 tác động tiêu cực: {losers_str or 'N/A'}

=== YÊU CẦU ===
Trả về JSON hợp lệ (KHÔNG có markdown, KHÔNG có backtick) theo schema:
{{
  "summary": "Mô tả ngắn gọn thị trường hôm nay 2-3 câu súc tích",
  "market_description": "Đoạn văn 3-4 câu mô tả chi tiết thay đổi, nhóm ngành, cổ phiếu ảnh hưởng",
  "support_resistance": {{
    "key_resistance": "Mức kháng cự quan trọng nhất kèm lý do (BB/Pivot/Fibo)",
    "key_support": "Mức hỗ trợ quan trọng nhất kèm lý do",
    "comment": "Nhận xét ngắn về vị trí giá hiện tại so với các ngưỡng"
  }},
  "timeframe_analysis": {{
    "short_term": {{
      "trend": "Tăng|Giảm|Đi ngang",
      "strength": "Mạnh|Trung bình|Yếu",
      "signals": ["signal1", "signal2"],
      "comment": "Phân tích MA5/MA10/MA20, RSI, Stochastic cho ngắn hạn (1-2 tuần)"
    }},
    "mid_term": {{
      "trend": "Tăng|Giảm|Đi ngang",
      "strength": "Mạnh|Trung bình|Yếu",
      "signals": ["signal1", "signal2"],
      "comment": "Phân tích MA20/MA50/MA100, MACD cho trung hạn (1-3 tháng)"
    }},
    "long_term": {{
      "trend": "Tăng|Giảm|Đi ngang",
      "strength": "Mạnh|Trung bình|Yếu",
      "signals": ["signal1", "signal2"],
      "comment": "Phân tích MA100/MA200, cấu trúc xu hướng cho dài hạn (3-12 tháng)"
    }}
  }},
  "scenarios": [
    {{
      "name": "Kịch bản tăng (Bull)",
      "probability": 40,
      "condition": "Điều kiện để xảy ra kịch bản này",
      "target": "Mục tiêu giá nếu xảy ra",
      "description": "Mô tả 2 câu"
    }},
    {{
      "name": "Kịch bản giảm (Bear)",
      "probability": 35,
      "condition": "Điều kiện để xảy ra kịch bản này",
      "target": "Mục tiêu giá nếu xảy ra",
      "description": "Mô tả 2 câu"
    }},
    {{
      "name": "Kịch bản trung lập (Sideways)",
      "probability": 25,
      "condition": "Điều kiện để xảy ra kịch bản này",
      "target": "Vùng giao dịch dự kiến",
      "description": "Mô tả 2 câu"
    }}
  ],
  "key_levels": {{
    "immediate_resistance": number,
    "immediate_support": number,
    "strong_resistance": number,
    "strong_support": number
  }},
  "sentiment": "Tích cực|Trung lập|Tiêu cực",
  "recommendation": "Tóm tắt khuyến nghị ngắn 1 câu cho nhà đầu tư"
}}
"""
    return prompt


def analyze_index(index_code: str, data: dict) -> dict:
    """Gọi DeepSeek để phân tích một index"""
    if data.get("error"):
        return {"error": data["error"]}

    print(f"  Analyzing {index_code} with DeepSeek...")
    prompt = build_prompt(index_code, data)

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là chuyên gia phân tích kỹ thuật chứng khoán Việt Nam. Luôn trả lời bằng JSON hợp lệ, không có markdown."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        # Loại bỏ markdown nếu có
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        analysis = json.loads(raw)
        print(f"    ✓ Phân tích xong {index_code}")
        return analysis

    except json.JSONDecodeError as e:
        print(f"    ✗ JSON parse error {index_code}: {e}")
        return {"error": f"JSON parse error: {e}", "raw": raw[:500]}
    except Exception as e:
        print(f"    ✗ DeepSeek error {index_code}: {e}")
        return {"error": str(e)}


def main():
    # Load market data
    data_path = "data/market_data.json"
    if not os.path.exists(data_path):
        print(f"✗ Không tìm thấy {data_path}. Chạy fetch_data.py trước.")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    analyses = {}
    for index_code, data in all_data.items():
        analysis = analyze_index(index_code, data)
        analyses[index_code] = analysis
        time.sleep(1)  # Rate limit

    # Gộp vào market_data.json
    for index_code in all_data:
        all_data[index_code]["analysis"] = analyses.get(index_code, {})

    all_data["generated_at"] = datetime.now().isoformat()

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✓ Đã lưu phân tích AI -> {data_path}")


if __name__ == "__main__":
    main()
