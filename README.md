# TrafficForecasting – Thu thập và phân tích dữ liệu giao thông Hà Nội

Dự án môn Big Data: thu thập dữ liệu lưu lượng giao thông của Hà Nội theo thời gian từ
**TomTom Traffic API**, phân tích mô tả dữ liệu và chuẩn bị nền tảng cho bài toán dự báo
giao thông.

Báo cáo chi tiết về dữ liệu: [`report.md`](report.md)

## Cấu trúc thư mục

```
TrafficForecasting/
├── crawl.py                       # Thu thập dữ liệu từ TomTom API
├── calibrate_points.py            # Kiểm chứng điểm lấy mẫu thuộc đường nào, loại điểm trùng
├── analyze.py                     # Thống kê, kiểm tra chất lượng, vẽ biểu đồ
├── candidates.csv                 # Danh sách đường ứng viên (tọa độ để trống, script tự tìm)
├── points_current.csv             # 10 điểm đã dùng trong đợt crawl đầu tiên
├── points_current_calibrated.csv  # Kết quả kiểm chứng 10 điểm trên (đường thực tế mỗi điểm)
├── report.md                      # Báo cáo mô tả dữ liệu và kết quả phân tích
├── requirements.txt
├── data/
│   └── traffic_20261017_1431.jsonl  # Dữ liệu crawl: 960 bản ghi (mỗi dòng một bản ghi JSON)
└── analysis/                      # Kết quả do analyze.py sinh ra (bảng, biểu đồ)
```

## Dữ liệu hiện có

`data/traffic_20261017_1431.jsonl`: 10 điểm × 96 lượt (5 phút/lượt) = 960 bản ghi, từ 21:31 ngày 17/10/2026
đến 05:26 ngày 18/10/2026 (giờ Việt Nam), thu thập trên Kaggle. Đây là dữ liệu của **một đêm cuối tuần**;
chi tiết, hạn chế và kết quả phân tích xem [`report.md`](report.md).

## Cài đặt

```bash
pip install -r requirements.txt
```

## Lấy API key TomTom (miễn phí)

1. Đăng ký tài khoản tại <https://developer.tomtom.com> (chỉ cần email, gói miễn phí không cần thẻ).
2. Vào **Dashboard → Keys**, tạo một key mới và bật các API **Traffic**.
3. Đặt key vào biến môi trường (không ghi key vào code hay commit lên GitHub):
   - macOS/Linux: `export TOMTOM_KEY="your_api_key"`
   - Windows PowerShell: `$env:TOMTOM_KEY="your_api_key"`
4. Gói miễn phí cho khoảng 2.500 request không phải tile mỗi ngày (kiểm tra lại trên trang giá của TomTom).
   `crawl.py` tự giới hạn ở 2.000 request/ngày để có biên an toàn.

## 0. Chọn và kiểm chứng điểm lấy mẫu

TomTom Flow Segment Data **không làm việc với "khu vực" hay "ngã tư"**: mỗi tọa độ chỉ cho dữ liệu của
một đoạn đường gần nhất. Muốn phân tích một khu vực, hãy chọn nhiều đường trong khu vực đó và đặt điểm
lên từng đường. Script sau kiểm tra bằng chính dữ liệu của TomTom:

```bash
export TOMTOM_KEY="your_api_key"
python calibrate_points.py --input candidates.csv
```

Kết quả: `points_calibrated.csv` (mỗi điểm rơi vào đường nào, điểm nào trùng đoạn) và `points.json`
(chỉ các điểm đạt) để `crawl.py` dùng. Tốn khoảng 3 request mỗi điểm.

## 1. Thu thập dữ liệu

Cần API key miễn phí của TomTom (đăng ký tại <https://developer.tomtom.com>).
**Không commit API key lên GitHub**: script đọc key từ biến môi trường.

```bash
export TOMTOM_KEY="your_api_key"

# Chạy thử 1 lượt để kiểm tra key và mạng
python crawl.py --test

# Chạy thật: 8 giờ, mỗi 5 phút một lượt
python crawl.py --hours 8 --interval 300
```

Trên macOS, thêm `caffeinate -i` phía trước để máy không ngủ khi đang crawl.
Script có bộ đếm request theo ngày (`data/counter.json`) và tự dừng khi chạm ngưỡng
`--daily-cap` (mặc định 2.000, thấp hơn hạn mức free 2.500 request/ngày).

Trên Kaggle: thêm secret `TOMTOM_KEY` trong Add-ons → Secrets, bật Internet,
rồi chạy `!python crawl.py --hours 8 --interval 300 --out /kaggle/working`.

## 2. Phân tích dữ liệu

```bash
python analyze.py                                  # đọc data/traffic_*.jsonl
python analyze.py --input "data/*.jsonl" --out analysis
```

Kết quả gồm `analysis/summary.md` (bảng thống kê và kiểm tra chất lượng), các file CSV
và biểu đồ `.png`. Biểu đồ theo thời gian chỉ được vẽ khi dữ liệu có đủ nhiều lượt crawl.

## Các trường dữ liệu chính

| Trường | Ý nghĩa |
|---|---|
| `ts_utc`, `ts_vn` | Thời điểm lấy dữ liệu (UTC và giờ Việt Nam) |
| `point`, `lat`, `lon` | Tên và tọa độ điểm lấy mẫu |
| `current_speed`, `free_flow_speed` | Tốc độ hiện tại và tốc độ khi thông thoáng (km/h) |
| `current_tt`, `free_flow_tt` | Thời gian đi qua đoạn đường hiện tại và khi thông thoáng (giây) |
| `confidence`, `frc`, `road_closure` | Độ tin cậy, cấp đường chức năng, đường có bị cấm không |

Mô tả đầy đủ từng trường xem trong [`report.md`](report.md).

## Lưu ý về dữ liệu

Dữ liệu giao thông thuộc về TomTom và được thu thập qua API cho mục đích học tập. Khi sử dụng hoặc chia sẻ lại
dữ liệu, hãy đọc điều khoản sử dụng của TomTom.