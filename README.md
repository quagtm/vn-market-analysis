# 📊 VN Market Analysis — Static Dashboard

Web tĩnh tự động phân tích VNINDEX, VN30, VN100 mỗi ngày sau giờ đóng cửa.  
Data từ **vnstock** · Phân tích AI từ **DeepSeek** · Deploy trên **GitHub Pages**.

---

## 🗂 Cấu trúc

```
.
├── .github/workflows/
│   └── market_update.yml    # GitHub Actions - chạy 17:00 ICT mỗi ngày
├── scripts/
│   ├── fetch_data.py        # Lấy OHLCV + tính chỉ báo kỹ thuật từ vnstock
│   ├── analyze.py           # Gửi dữ liệu tới DeepSeek, nhận phân tích JSON
│   └── build_site.py        # Tạo docs/index.html từ data/market_data.json
├── data/
│   └── market_data.json     # Dữ liệu + phân tích (auto-generated)
├── docs/
│   └── index.html           # Web tĩnh (auto-generated)
└── requirements.txt
```

---

## ⚙️ Setup (5 bước)

### 1. Fork / Clone repo này

```bash
git clone https://github.com/YOUR_USERNAME/vn-market-analysis.git
cd vn-market-analysis
```

### 2. Thêm GitHub Secrets

Vào **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Giá trị |
|-------------|---------|
| `VNSTOCK_API_KEY` | API key vnstock của bạn |
| `DEEPSEEK_API_KEY` | API key DeepSeek của bạn |

> DeepSeek API: https://platform.deepseek.com/api_keys  
> Nếu vnstock không cần key, để giá trị bất kỳ.

### 3. Bật GitHub Pages

**Settings → Pages → Source**: chọn `Deploy from a branch` → branch `main` → folder `/docs`

URL của bạn sẽ là: `https://YOUR_USERNAME.github.io/vn-market-analysis/`

### 4. Kích hoạt Actions

**Actions tab → Enable workflows** (nếu bị tắt)

Chạy thử: **Actions → VN Market Analysis - Daily Update → Run workflow**

### 5. Kiểm tra kết quả

Sau ~5 phút, vào URL GitHub Pages để xem dashboard.

---

## 🕐 Lịch cập nhật

| Thời gian | Múi giờ | Cron |
|-----------|---------|------|
| 17:00 (Thứ 2 - Thứ 6) | ICT (UTC+7) | `0 10 * * 1-5` |

---

## 🛠 Chạy local

```bash
pip install -r requirements.txt

# Bước 1: Fetch data
python scripts/fetch_data.py

# Bước 2: Phân tích AI (cần DEEPSEEK_API_KEY)
export DEEPSEEK_API_KEY=your_key_here
python scripts/analyze.py

# Bước 3: Build HTML
python scripts/build_site.py

# Xem kết quả
open docs/index.html
```

---

## 📈 Tính năng

### Mỗi index (VNINDEX / VN30 / VN100)
- **Hero card**: Giá, thay đổi %, High/Low, Khối lượng
- **Tổng quan AI**: Mô tả thị trường, nhận định sentiment, khuyến nghị
- **Nhóm ngành**: Top 3 ngành dẫn dắt / đi lùi, Top 3 cổ phiếu ảnh hưởng
- **Hỗ trợ & Kháng cự**: BB + Pivot + Fibonacci 52-week
- **Phân tích 3 khung thời gian**: Ngắn/Trung/Dài hạn với MA, MACD, RSI
- **Kịch bản xác suất**: Bull / Bear / Sideways với điều kiện + target
- **Chỉ báo kỹ thuật**: MA5-MA200, RSI, MACD, Stochastic, ATR, BB
- **Biểu đồ tương tác**: Nến Nhật + Volume, toggle MA/BB, zoom 1M/3M/6M/1Y

---

## 🔧 Tùy chỉnh

### Đổi lịch chạy
Sửa `cron` trong `.github/workflows/market_update.yml`:
```yaml
- cron: '0 10 * * 1-5'   # 17:00 ICT
- cron: '0 12 * * 1-5'   # 19:00 ICT
```

### Đổi số ngày lịch sử
Sửa `DAYS_HISTORY` trong `scripts/fetch_data.py`:
```python
DAYS_HISTORY = 365  # Đổi thành 180, 500, v.v.
```

### Thêm index khác
Sửa `INDICES` dict trong `scripts/fetch_data.py`.
