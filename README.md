# Traffic Forecasting for Hanoi Urban Network

Dự án thu thập dữ liệu và dự báo lưu lượng giao thông mạng lưới đô thị Hà Nội sử dụng dữ liệu thời gian thực từ **HERE Traffic API v7** kết hợp các mô hình Spatio-Temporal Graph Neural Networks (STGCN, DCRNN, Graph WaveNet).

---

## 📌 Tổng quan

- **Khu vực quan trắc:** Toàn bộ mạng lưới đường bộ Hà Nội (4 phân vùng Bounding Box: Tây Nam, Đông Nam, Tây Bắc, Đông Bắc).
- **Quy mô:** Hơn 2.000 đoạn đường và hơn 730 tuyến phố chính.
- **Tần suất thu thập:** 5 phút/chu kỳ (tương thích các chuẩn benchmark quốc tế như METR-LA, PEMS-BAY).
- **Đặc trưng thu thập:** Tốc độ thực tế (`speed_kmh`), Tốc độ tự do (`free_flow_kmh`), Tỷ số tốc độ (`speed_ratio`), Chỉ số kẹt xe (`jam_factor`), Phân cấp ùn tắc (`jam_level`), Độ tin cậy (`confidence`), Tọa độ WGS84 (`coord`).

---

## 📂 Cấu trúc thư mục

```
TrafficForecasting/
├── HANOI_TRAFFIC_DATA_DOCS.md    # Tài liệu đặc tả dữ liệu, API & chiến lược crawl 1 tháng
├── crawl_hanoi_traffic.py        # Script thu thập dữ liệu giao thông tự động
├── here_traffic_checker.py       # Script kiểm tra kết nối & hạn ngạch HERE API
├── .gitignore                    # Bỏ qua file dữ liệu lớn & cache
└── README.md                     # Giới thiệu dự án
```

---

## 🚀 Hướng dẫn nhanh

### 1. Cài đặt môi trường
Dự án sử dụng Python 3.8+ và các thư viện chuẩn (không yêu cầu cài thêm package ngoài cho việc crawl):
```bash
python crawl_hanoi_traffic.py --interval 300 --out data/hanoi_traffic_data.json
```

### 2. Kiểm tra kết nối HERE API
```bash
python here_traffic_checker.py
```

### 3. Tài liệu chi tiết
Xem toàn bộ đặc tả kiến trúc dữ liệu, công thức toán học và hướng dẫn chạy bền bỉ 1 tháng (24/7) tại:
👉 **[HANOI_TRAFFIC_DATA_DOCS.md](HANOI_TRAFFIC_DATA_DOCS.md)**