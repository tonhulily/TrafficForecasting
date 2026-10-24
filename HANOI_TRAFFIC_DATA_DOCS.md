# TÀI LIỆU ĐẶC TẢ DỮ LIỆU GIAO THÔNG HÀ NỘI
## CHIẾN THUẬT THU THẬP, CẤU TRÚC DỮ LIỆU & GIỚI HẠN HERE TRAFFIC API v7

---

## 1. TỔNG QUAN VỀ TẬP DỮ LIỆU

Tập dữ liệu được thiết kế nhằm phục vụ bài toán **Dự báo Giao thông (Traffic Forecasting)** và **Phân tích Động thái Mạng lưới Giao thông Đô thị (Urban Traffic Dynamics)** tại Thủ đô Hà Nội. 

### Các đặc tính cốt lõi:
- **Phạm vi không gian (Spatial Coverage):** Toàn bộ khu vực nội đô và các vùng đô thị mở rộng của Hà Nội, bao phủ hơn **2.000 đoạn đường** và **hơn 730 tuyến phố chính**.
- **Độ phân giải thời gian (Temporal Resolution):** Dữ liệu được lấy mẫu đồng bộ theo chu kỳ **5 phút/lần** (chuẩn mực quốc tế tương thích với các tập benchmark lớn như *METR-LA*, *PEMS-BAY*, *PeMS04/08*).
- **Cấu trúc lưu trữ:** Lưu trữ tập trung trong **1 file JSON chuẩn hóa duy nhất** (`hanoi_traffic_data.json`), phân cấp theo từng chu kỳ quan trắc và tích hợp sẵn các chỉ số tóm tắt thống kê.

---

## 2. CHI TIẾT CẤU TRÚC VÀ ĐẶC TRƯNG DỮ LIỆU (DATA SCHEMA & FEATURE DICTIONARY)

Dữ liệu được tổ chức theo cấu trúc phân cấp (Hierarchical Schema), bao gồm 2 phần chính: `metadata` (thông tin chung) và `cycles` (danh sách các chu kỳ quan trắc).

### 2.1. Cấu trúc tổng thể file JSON

```json
{
  "metadata": {
    "city": "Ha Noi, Viet Nam",
    "source": "HERE Traffic API v7",
    "description": "Du lieu luu luong giao thong toan thanh pho Ha Noi theo chu ky 5 phut",
    "total_cycles_completed": 23
  },
  "cycles": [
    {
      "cycle_id": 1,
      "summary": {
        "total_segments": 2037,
        "avg_speed_kmh": 24.6,
        "avg_jam_factor": 1.91,
        "status_counts": {
          "free_flow": 1132,
          "moderate": 837,
          "congested": 68
        }
      },
      "segments": [
        {
          "road_name": "Pho Nguyen Viet Xuan",
          "region_id": "SW",
          "length_meters": 296.0,
          "speed_kmh": 37.0,
          "free_flow_kmh": 38.0,
          "speed_ratio": 0.974,
          "jam_factor": 0.3,
          "jam_level": "Thong thoang",
          "confidence": 0.9,
          "traversability": "open",
          "coord": {
            "lat": 20.97149,
            "lon": 105.77639
          }
        }
      ]
    }
  ]
}
```

---

### 2.2. Từ điển dữ liệu cho từng đoạn đường (`segments`)

| Trường dữ liệu | Kiểu dữ liệu | Đơn vị / Thang đo | Mô tả chi tiết |
| :--- | :--- | :--- | :--- |
| `road_name` | `string` | Văn bản UTF-8 | Tên tuyến đường hoặc đoạn đường do HERE Maps định danh (ví dụ: `Pho Nguyen Viet Xuan`, `Duong Tran Duy Hung`). |
| `region_id` | `string` | Mã định danh (`SW`, `SE`, `NW`, `NE`) | Phân vùng địa lý thu thập đoạn đường (Tây Nam, Đông Nam, Tây Bắc, Đông Bắc). |
| `length_meters` | `float` | Mét ($m$) | Chiều dài vật lý của đoạn đường được quan trắc. |
| `speed_kmh` | `float` | $km/h$ | Tốc độ di chuyển thực tế trung bình hiện tại của các phương tiện trên đoạn đường. Quy đổi từ $m/s$ chuẩn của API: $v_{km/h} = v_{m/s} \times 3.6$. |
| `free_flow_kmh` | `float` | $km/h$ | Tốc độ lưu thông tự do lý tưởng (Free-Flow Speed) khi đường hoàn toàn thông thoáng và không bị cản trở bởi mật độ phương tiện. |
| `speed_ratio` | `float` | Tỉ lệ không thứ nguyên $[0.0, 1.0+]$ | Tỷ số tốc độ thực tế so với tốc độ tự do: $\text{Ratio} = \frac{v_{\text{actual}}}{v_{\text{free\_flow}}}$. Chỉ số càng gần $1.0$ thể hiện đường càng thông thoáng; dưới $0.5$ thể hiện ùn tắc nghiêm trọng. |
| `jam_factor` | `float` | $[0.0 - 10.0]$ | Chỉ số kẹt xe chuẩn hóa do HERE API tính toán dựa trên mức độ suy giảm tốc độ so với điều kiện lý tưởng. |
| `jam_level` | `string` | Định tính phân cấp | Phân nhóm trạng thái giao thông tương ứng với Jam Factor: *Thong thoang, Dong nhe, Un u trung binh, Un tac nang, Tac nghen nghiem trong*. |
| `confidence` | `float` | $[0.0 - 1.0]$ | Độ tin cậy thống kê của dữ liệu quan trắc. Giá trị càng gần $1.0$ nghĩa là đoạn đường có mật độ cảm biến/probe vehicle cao và độ chính xác lớn. |
| `traversability` | `string` | Trạng thái (`open`, `closed`, `restricted`) | Khả năng thông hành của đoạn đường. `open`: đang mở cho lưu thông; `closed`: đang cấm đường hoặc phong tỏa do sự cố/thi công. |
| `coord` | `object` | WGS84 (`lat`, `lon`) | Tọa độ địa lý điểm đầu của đoạn đường (Vĩ độ và Kinh độ), dùng để xây dựng ma trận kề không gian (Spatial Adjacency Matrix) trong mô hình đồ thị. |

---

### 2.3. Định lượng chỉ số Jam Factor và Phân cấp ùn tắc

Chỉ số `jam_factor` là một đặc trưng phi tuyến tính biểu diễn mức độ trễ hành trình trên đoạn đường:

$$\text{Jam Factor} \in [0.0, 10.0]$$

- **$0.0 \le \text{Jam Factor} < 2.0$ (Thông thoáng / Free flow):** Tốc độ thực tế xấp xỉ tốc độ thiết kế, không có sự chậm trễ đáng kể.
- **$2.0 \le \text{Jam Factor} < 4.0$ (Đông nhẹ / Light congestion):** Mật độ xe tăng nhưng vẫn duy trì vận tốc ổn định.
- **$4.0 \le \text{Jam Factor} < 7.0$ (Ùn ứ trung bình / Moderate congestion):** Xuất hiện hiện tượng dừng/chạy chậm ngắt quãng, vận tốc giảm $30\% - 50\%$.
- **$7.0 \le \text{Jam Factor} < 9.0$ (Ùn tắc nặng / Heavy congestion):** Phương tiện di chuyển rất chậm, hàng đợi kéo dài.
- **$9.0 \le \text{Jam Factor} \le 10.0$ (Tắc nghẽn nghiêm trọng / Standstill):** Giao thông tê liệt hoàn toàn, xe đứng yên hoặc nhích từng mét.

---

## 3. CHIẾN THUẬT THU THẬP DỮ LIỆU (CRAWLING STRATEGY)

### 3.1. Thách thức kỹ thuật đặt ra
1. **Quy mô đô thị Hà Nội:** Mạng lưới giao thông Hà Nội phân bố phức tạp trên diện tích rộng hơn $3.000\text{ km}^2$, với hệ thống đường trục chính đan xen ngõ ngách.
2. **Hạn chế của phương pháp Circle/Point:** Nếu dùng truy vấn theo tọa độ tròn (`in=circle:lat,lon;r=radius`), hệ thống phải gọi hàng trăm điểm ngã tư khác nhau, gây lãng phí request, dễ bỏ sót tuyến đường và khó kiểm soát dữ liệu trùng lặp.
3. **Nguy cơ quá tải của Bounding Box đơn:** Nếu truy vấn một Bounding Box duy nhất bao trùm toàn bộ thành phố, phản hồi API sẽ vượt ngưỡng dung lượng tối đa (Payload size limit), dẫn tới hiện tượng API tự động lược bỏ (truncate) các đoạn đường nhỏ hoặc gây lỗi Gateway Timeout.

---

### 3.2. Giải pháp: Phân vùng lưới không gian 2x2 (Grid Spatial Partitioning)

Chiến thuật tối ưu nhất là chia vùng đô thị lõi và cận đô thị Hà Nội thành **4 Bounding Box độc lập (2x2)** theo trục Kinh độ và Vĩ độ:

```
                  21.12°N ---------------------------------
                          |               |               |
                          |    VÙNG NW    |    VÙNG NE    |
                          |   (Tây Bắc)   |   (Đông Bắc)  |
                          |               |               |
                  21.01°N |---------------+---------------|
                          |               |               |
                          |    VÙNG SW    |    VÙNG SE    |
                          |   (Tây Nam)   |   (Đông Nam)  |
                          |               |               |
                  20.90°N ---------------------------------
                       105.65°E        105.80°E        105.95°E
```

#### Chi tiết 4 phân vùng tọa độ:

| Mã vùng | Tên phân vùng | Phạm vi Bounding Box (`W_lon, S_lat, E_lon, N_lat`) | Các khu vực & Quận huyện bao phủ | Số đoạn đường trung bình/lượt |
| :---: | :--- | :--- | :--- | :---: |
| **`SW`** | **Tây Nam** | `105.65, 20.90, 105.80, 21.01` | Quận Hà Đông, Quận Thanh Xuân, Quận Nam Từ Liêm, một phần Huyện Thanh Trì & Huyện Hoài Đức. | ~335 đoạn |
| **`SE`** | **Đông Nam** | `105.80, 20.90, 105.95, 21.01` | Quận Hoàng Mai, phía Nam Quận Hai Bà Trưng, Huyện Thanh Trì, khu vực Giáp Bát, Nước Ngầm. | ~529 đoạn |
| **`NW`** | **Tây Bắc** | `105.65, 21.01, 105.80, 21.12` | Quận Cầu Giấy, Quận Bắc Từ Liêm, khu đô thị Tây Hồ Tây, đường Vành đai 3 phía Bắc. | ~305 đoạn |
| **`NE`** | **Đông Bắc** | `105.80, 21.01, 105.95, 21.12` | Quận Ba Đình, Quận Hoàn Kiếm, Quận Đống Đa, Quận Tây Hồ, Quận Long Biên, Cầu Nhật Tân, Cầu Chương Dương, Cầu Vĩnh Tuy. | ~968 đoạn |

**Hiệu quả vượt trội:**
- Chỉ với **4 HTTP requests duy nhất**, hệ thống thu thập trọn vẹn hơn **2.000 đoạn đường** phủ kín toàn bộ 12 quận nội thành và các cửa ngõ giao thông huyết mạch của Hà Nội.
- Tránh được hoàn toàn nguy cơ quá tải payload hoặc timeout của API.

---

### 3.3. Thuật toán Khử trùng lặp tại ranh giới giao thoa (Deduplication)

Tại các đường biên giao nhau giữa 4 Bounding Box (trục Vĩ độ $21.01^\circ\text{N}$ và Kinh độ $105.80^\circ\text{E}$), một số đoạn đường dài có thể xuất hiện đồng thời trong 2 truy vấn kế cận.

Hệ thống triển khai bộ lọc định danh duy nhất (Composite Deduplication Key):
$$\text{Key} = \big(\text{road\_name},\; \text{round}(\text{length\_meters}),\; \text{speed\_kmh}\big)$$

Trong mỗi chu kỳ crawl:
1. Duyệt tuần tự qua 4 phân vùng.
2. Kiểm tra `Key` của từng đoạn đường trong `seen_roads` Set.
3. Nếu đã tồn tại thì bỏ qua, nếu chưa có thì thêm vào danh sách kết quả chu kỳ.
4. Đảm bảo dữ liệu trong mỗi chu kỳ là **100% không trùng lặp**.

---

### 3.4. Chiến lược Chu kỳ 5 phút (Sampling Interval)

Khoảng thời gian 5 phút ($300\text{ giây}$) được lựa chọn dựa trên 2 cơ sở khoa học:
1. **Động thái giao thông (Traffic Physics):** Tình trạng ùn tắc giao thông đô thị cần khoảng 3–5 phút để hình thành và lan truyền qua các nút giao (Shockwave propagation). Lấy mẫu quá ngắn ($< 1\text{ phút}$) gây nhiễu thống kê và lãng phí request; lấy mẫu quá thưa ($> 15\text{ phút}$) sẽ bỏ lỡ các đỉnh cao điểm cục bộ.
2. **Tiêu chuẩn mô hình hóa chuỗi thời gian:** Các tập dữ liệu benchmark kinh điển trên thế giới cho Spatio-Temporal Graph Neural Networks (như *METR-LA*, *PEMS-BAY*) đều chuẩn hóa bước thời gian là **5 phút** ($1\text{ ngày} = 288\text{ time-steps}$).

---

## 4. QUY TRÌNH VÀ KIẾN TRÚC HỆ THỐNG CRAWL

### 4.1. Sơ đồ dòng dữ liệu (Pipeline Flowchart)

```
[Bắt đầu chu kỳ] 
       │
       ▼
[Duyệt 4 Bounding Box: SW ➔ SE ➔ NW ➔ NE]
       │
       ├──► Gửi HTTP GET: https://data.traffic.hereapi.com/v7/flow?in=bbox:...
       │    (Giãn cách 0.5s giữa các request để giữ QPS an toàn)
       │
       ├──► Parse JSON phản hồi, chuẩn hóa đơn vị (m/s ➔ km/h, tính jam_level)
       │
       └──► Khử trùng lặp qua bộ lọc Key: (road_name, length, speed)
       │
       ▼
[Tính toán tóm tắt chu kỳ (Summary): Tốc độ TB, Tỉ lệ thông thoáng/ùn tắc, Top tuyến đường tắc]
       │
       ▼
[Ghi an toàn ra file tạm .tmp ➔ os.fsync() ➔ Atomic replace vào hanoi_traffic_data.json]
       │
       ▼
[Cập nhật giao diện Terminal: In thống kê, đếm ngược ⏳ mm:ss]
       │
       ├── (Nếu nhận tín hiệu Ctrl + C: Bắt KeyboardInterrupt ➔ Lưu an toàn ➔ Thoát sạch)
       │
       └── (Hết 300 giây: Lặp lại chu kỳ tiếp theo)
```

---

### 4.2. Cơ chế Lưu trữ An toàn Tuyệt đối (Atomic File Persistence)

Trong các tiến trình chạy ngầm dài ngày, nguy cơ mất điện, ngắt mạng hoặc người dùng nhấn dừng bất ngờ (`Ctrl + C`) có thể khiến file JSON bị cắt ngang giữa chừng dẫn đến hư hỏng toàn bộ dữ liệu (Corrupted JSON).

Hệ thống áp dụng kỹ thuật **Atomic Write**:
1. Đọc dữ liệu lịch sử đã lưu trước đó (nếu có).
2. Khi hoàn thành lượt crawl mới, dữ liệu được kết xuất ra file đệm tạm thời: `hanoi_traffic_data.json.tmp`.
3. Gọi lệnh `f.flush()` và `os.fsync()` để đảm bảo toàn bộ byte được ghi thực sự xuống đĩa cứng (không nằm lại trong OS cache).
4. Thực hiện thay thế nguyên tử (`os.replace(temp_file, final_file)`). Thao tác này diễn ra ở tầng kernel của hệ điều hành trong thời gian dưới $1\text{ mili-giây}$.
5. Kết quả: **File `hanoi_traffic_data.json` luôn luôn là một file JSON hợp lệ 100% tại bất kỳ thời điểm nào.**

---

### 4.3. Quản lý Console I/O và Khả năng tương thích Windows

- **UTF-8 Encoding:** Trên Windows PowerShell/Command Prompt, mã trang mặc định thường là `cp1252` hoặc `cp437`, dễ gây lỗi `UnicodeEncodeError` khi in các chuỗi tiếng Việt hoặc biểu tượng trạng thái. Hệ thống chủ động tái cấu hình stream xuất ra:
  ```python
  sys.stdout.reconfigure(encoding="utf-8")
  sys.stderr.reconfigure(encoding="utf-8")
  ```
- **Đồng hồ đếm ngược trực tiếp:** Sử dụng kỹ thuật ghi đè dòng terminal (`\r` và `sys.stdout.flush()`) giúp người dùng theo dõi số giây còn lại đến chu kỳ tiếp theo mà không làm trôi cuộn màn hình.

---

## 5. CÁC GIỚI HẠN VÀ CHÍNH SÁCH CỦA HERE TRAFFIC API v7

### 5.1. Mô hình cấp phép và Hạn ngạch (Quota & Billing)

Dịch vụ **HERE Traffic API v7** hoạt động theo mô hình *Freemium* với các quy định cụ thể:

| Tiêu chí | Thông số quy định của HERE API |
| :--- | :--- |
| **Gói dịch vụ (Plan)** | **HERE Base Plan (Freemium)** |
| **Hạn ngạch miễn phí hàng tháng** | **250.000 transactions / tháng** miễn phí hoàn toàn. |
| **Cách tính phí giao dịch** | Mỗi lần gửi yêu cầu HTTP GET hợp lệ tới `/v7/flow` được tính là **1 transaction** (bất kể số lượng đoạn đường trả về trong kết quả). |

#### Bài toán tính toán chi phí tài nguyên theo chiến thuật của hệ thống:
- **Số request cho 1 chu kỳ (5 phút):** 4 requests (tương ứng 4 Bounding Box).
- **Số chu kỳ trong 1 giờ:** 12 chu kỳ $\Rightarrow 12 \times 4 = \mathbf{48\text{ requests / giờ}}$.
- **Số request trong 1 ngày (24 giờ):** $48 \times 24 = \mathbf{1.152\text{ requests / ngày}}$.
- **Tổng số request trong 1 tháng (30 ngày liên tục):**
  $$\text{Tổng request / tháng} = 1.152 \times 30 = \mathbf{34.560\text{ requests / tháng}}$$
- **Tỷ lệ tiêu hao hạn ngạch:**
  $$\text{Tỷ lệ sử dụng} = \frac{34.560}{250.000} \approx \mathbf{13.82\%}$$

> **Kết luận an toàn:** Hệ thống chỉ sử dụng chưa tới **14%** hạn ngạch miễn phí hàng tháng của HERE API. Tiến trình có thể chạy bền bỉ liên tục 24/7 suốt cả tháng mà không phát sinh bất kỳ chi phí nào và không bị khóa tài khoản.

---

### 5.2. Giới hạn tần suất gọi (Rate Limits & QPS)

- **QPS (Queries Per Second):** Hạn mức thông thường cho gói cơ bản là **5 - 10 requests / giây**.
- **Chiến lược kiểm soát lưu lượng của Crawler:**
  - Giữa mỗi request của 4 phân vùng có khoảng nghỉ chủ động `time.sleep(0.5)`.
  - Tốc độ gọi thực tế của crawler chỉ đạt xấp xỉ **$0.013\text{ requests / giây}$** (tính trung bình trên chu kỳ 5 phút).
  - Hoàn toàn loại bỏ rủi ro bị máy chủ HERE kích hoạt cơ chế chặn phòng thủ DDOS hoặc trả về mã lỗi `429 Too Many Requests`.

---

### 5.3. Giới hạn kích thước Bounding Box và Kích thước dữ liệu (Payload Limit)

- **Không gian Bounding Box:** HERE API quy định thứ tự tham số là:
  $$\text{in}=\text{bbox}:\{\text{Kinh độ Tây}\},\{\text{Vĩ độ Nam}\},\{\text{Kinh độ Đông}\},\{\text{Vĩ độ Bắc}\}$$
- **Ngưỡng tải phản hồi (Response Payload Size):** Nếu kích thước Bounding Box vượt quá phạm vi đô thị cấp vùng (ví dụ bao toàn bộ miền Bắc), phản hồi có thể vượt ngưỡng $15 - 20\text{ MB}$ khiến cổng API ngắt kết nối.
- Bằng cách giới hạn mỗi box trong phạm vi khoảng $0.15^\circ$ kinh độ $\times$ $0.11^\circ$ vĩ độ (xấp xỉ $16\text{ km} \times 12\text{ km}$), kích thước mỗi phản hồi luôn duy trì ổn định ở mức $1.5 - 3.5\text{ MB}$, tối ưu cho đường truyền mạng và tốc độ giải mã JSON.

---

### 5.4. Cơ chế Xác thực và An toàn (Authentication)

HERE Traffic API v7 hỗ trợ 2 phương thức xác thực:
1. **API Key (Query Parameter):** Truyền qua tham số `apiKey={YOUR_API_KEY}` trên URL. Đây là phương thức được sử dụng trong mã nguồn nhờ tính độc lập và không đòi hỏi trao đổi OAuth token định kỳ.
2. **Bearer Token (OAuth 2.0):** Gửi kèm trong Header `Authorization: Bearer {token}`.

---

### 5.5. Quản lý và xử lý mã lỗi HTTP (Error Handling Matrix)

| Mã trạng thái HTTP | Ý nghĩa kỹ thuật | Cơ chế xử lý tự động của hệ thống |
| :---: | :--- | :--- |
| **`200 OK`** | Yêu cầu thành công, dữ liệu lưu lượng được trả về trọn vẹn. | Giải mã payload, trích xuất danh sách `results` và phân tích thuộc tính. |
| **`401 / 403`** | API Key sai, hết hạn hoặc tài khoản bị giới hạn quyền truy cập. | Ngắt tiến trình và thông báo lỗi rõ ràng trên terminal để người dùng kiểm tra lại biến môi trường `HERE_API_KEY`. |
| **`429 Too Many Requests`** | Gửi quá nhiều yêu cầu trong thời gian ngắn, vượt ngưỡng tức thời của server. | Tự động kích hoạt cơ chế chờ (Backoff sleep $5\text{ giây}$) và gửi lại yêu cầu. |
| **`500 / 503`** | Sự cố máy chủ nội bộ hoặc bảo trì tạm thời phía hạ tầng HERE. | Tự động thử lại tối đa 3 lần với khoảng cách thời gian tăng dần ($2\text{s}, 4\text{s}, 6\text{s}$) trước khi chuyển sang phân vùng tiếp theo. |

---

## 6. HƯỚNG DẪN TRÍCH XUẤT PHỤC VỤ DỰ BÁO GIAO THÔNG (TRAFFIC FORECASTING)

Dữ liệu thu thập từ file `hanoi_traffic_data.json` được thiết kế để dễ dàng chuyển đổi sang các định dạng chuẩn trong Machine Learning / Deep Learning:

### 6.1. Xây dựng Ma trận Tốc độ Không gian - Thời gian (Traffic Speed Matrix $X$)
Với $N$ đoạn đường quan trắc độc lập và $T$ chu kỳ thời gian:
$$X \in \mathbb{R}^{T \times N \times F}$$
- $T$: Số lượng chu kỳ 5 phút ($T = \text{total\_cycles}$).
- $N$: Số lượng tuyến đường cố định được theo dõi ($N \approx 2.000$).
- $F$: Số lượng đặc trưng tại mỗi thời điểm (ví dụ: $F = 3$ gồm `speed_kmh`, `jam_factor`, `speed_ratio`).

### 6.2. Xây dựng Ma trận Kề Đồ thị Không gian (Spatial Adjacency Matrix $A$)
Dựa trên tọa độ WGS84 (`lat`, `lon`) trong trường `coord`, tính toán ma trận khoảng cách địa lý $D_{ij}$ giữa 2 đoạn đường $i$ và $j$ theo công thức Haversine, sau đó áp dụng hàm suy giảm Gaussian (Thresholded Gaussian Kernel):

$$A_{ij} = \begin{cases} 
\exp\left(-\left(\frac{\text{dist}(i,j)}{\sigma}\right)^2\right) & \text{nếu } \text{dist}(i,j) \le \kappa \\
0 & \text{nếu } \text{dist}(i,j) > \kappa 
\end{cases}$$

Ma trận kề $A$ này là đầu vào trực tiếp cho các mô hình học sâu hiện đại:
- **STGCN** (Spatio-Temporal Graph Convolutional Networks)
- **DCRNN** (Diffusion Convolutional Recurrent Neural Network)
- **Graph WaveNet**
- **ASTGCN** (Attention Based Spatial-Temporal Graph Convolutional Networks)

---

## 7. CHIẾN LƯỢC & KIẾN TRÚC THU THẬP DỮ LIỆU DÀI HẠN 1 THÁNG (24/7 LONG-TERM CRAWLER)

Để xây dựng một bộ dữ liệu chuẩn mực phục vụ các mô hình học sâu (Deep Learning) chuỗi thời gian không gian, việc thu thập liên tục **1 tháng (30 ngày liên tục, 24/7)** cung cấp chu kỳ biến động giao thông hoàn chỉnh: giờ cao điểm - thấp điểm trong ngày, ngày trong tuần (thứ 2 đến thứ 6) so với cuối tuần (thứ 7, CN), cùng các điều kiện thời tiết đặc biệt.

---

### 7.1. Phân tích Định lượng Tài nguyên & Rủi ro Kỹ thuật khi chạy 30 ngày

| Chỉ số kỹ thuật | Tính toán cho 1 ngày (24 giờ) | Tính toán cho 1 tháng (30 ngày) | Đánh giá & Rủi ro |
| :--- | :--- | :--- | :--- |
| **Số chu kỳ quan trắc** | $12 \times 24 = 288\text{ chu kỳ}$ | $288 \times 30 = \mathbf{8.640\text{ chu kỳ}}$ | Hoàn toàn tương thích độ phân giải thời gian của METR-LA / PEMS-BAY. |
| **Số request HERE API** | $288 \times 4 = 1.152\text{ calls}$ | $8.640 \times 4 = \mathbf{34.560\text{ calls}}$ | **Chỉ dùng 13.8%** hạn mức miễn phí (250.000 calls/tháng). Hoàn toàn an toàn. |
| **Dung lượng JSON thô** | $\approx 280\text{ MB} - 300\text{ MB}$ | $\approx \mathbf{8.5\text{ GB} - 10.0\text{ GB}}$ | ⚠️ **CỰC KỲ NGUY HIỂM NẾU LƯU 1 FILE DUY NHẤT:** Dẫn đến cạn kiệt RAM (OOM Crash). |
| **Dung lượng sau nén Gzip** | $\approx 22\text{ MB} - 25\text{ MB}$ | $\approx \mathbf{650\text{ MB} - 800\text{ MB}}$ | **Tiết kiệm >90% ổ cứng**, đọc/ghi cực nhanh, an toàn tuyệt đối. |

---

### 7.2. Ba Rào Cản Chí Mạng và Giải Pháp Kỹ Thuật

#### 🔴 Rào cản 1: Tràn bộ nhớ RAM (OOM Crash) và Nghẽn I/O đĩa
* **Hiện tượng:** Nếu gom tất cả chu kỳ vào 1 file `hanoi_traffic_data.json`, mỗi chu kỳ Python phải đọc lại mảng JSON hàng gigabyte vào RAM, parse cú pháp, rồi tuần tự hóa (`json.dump`) lại toàn bộ. Sau khoảng 5–7 ngày, file vượt quá 2 GB, thời gian ghi đĩa sẽ vượt quá chu kỳ 5 phút và Python sẽ bị hệ điều hành tiêu diệt vì ngốn quá nhiều RAM.
* **Giải pháp chuẩn:** **Phân vùng lưu trữ theo ngày (Daily Sharding)** kết hợp **Nén Gzip tự động**:
  * Mỗi ngày (từ 00:00:00 đến 23:59:59) được lưu vào 1 file độc lập: `data/daily/traffic_YYYY-MM-DD.json.gz`.
  * RAM duy trì cố định ở mức **dưới 50 MB** trong suốt 30 ngày vì dữ liệu chu kỳ trước không cần giữ lại trong bộ nhớ.
  * Tự động chuyển file (Rotation) khi bước sang ngày mới.

```
data/
├── hanoi_traffic_data.json         # Snapshot mẫu ban đầu (phục vụ dev & test nhanh)
└── daily/                          # Kho dữ liệu 30 ngày phân vùng độc lập
    ├── traffic_2026-10-24.json.gz  # ~25 MB / ngày
    ├── traffic_2026-10-25.json.gz
    ├── traffic_2026-10-26.json.gz
    └── ...
```

---

#### 🔴 Rào cản 2: Windows tự động Sleep (Ngủ) hoặc Hibernate khi không tương tác
* **Hiện tượng:** Mặc định sau 15–30 phút người dùng không gõ phím hay rê chuột, hệ điều hành Windows sẽ đưa máy tính vào trạng thái Sleep/Modern Standby để tiết kiệm điện. Khi đó CPU ngừng thực thi và crawler bị đóng băng.
* **Giải pháp:** Sử dụng Windows Kernel API `SetThreadExecutionState` thông qua thư viện chuẩn `ctypes` trong Python. Lệnh này thông báo cho Windows Kernel biết tiến trình đang chạy tác vụ nền quan trọng và yêu cầu hệ thống **KHÔNG ĐƯỢC TỰ ĐỘNG NGỦ**:

```python
import sys
import ctypes

def prevent_windows_sleep():
    """Yêu cầu Windows giữ CPU luôn thức (không vào chế độ Sleep) khi cắm sạc."""
    if sys.platform == "win32":
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_AWAYMODE_REQUIRED = 0x00000040
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
        print("[+] Da kich hoat che do chong Windows Sleep tu dong.")
```

* **Cấu hình bổ sung trên Windows Settings:**
  * Nhấn `Windows + I` $\rightarrow$ **System** $\rightarrow$ **Power & battery**.
  * Mục **Screen and sleep**: Đặt *"When plugged in, put my device to sleep after"* thành **Never**.

---

#### 🔴 Rào cản 3: Gián đoạn kết nối mạng (Network Outages, Wi-Fi Timeout)
* **Hiện tượng:** Trong suốt 720 giờ liên tục, kết nối Internet gia đình có thể gặp sự cố ngắn hạn (nhà mạng bảo trì, đổi IP, modem khởi động lại). Nếu tiến trình văng ngoại lệ `sys.exit(1)`, toàn bộ công sức sẽ dừng lại.
* **Giải pháp:** **Vòng lặp giám sát cấp cao (Top-Level Guardian Loop) kết hợp Exponential Backoff**:
  * Khi mất mạng hoàn toàn, crawler chuyển sang trạng thái chờ an toàn: thử lại sau 30 giây $\rightarrow$ 60 giây $\rightarrow$ 120 giây.
  * **Không bao giờ thoát tiến trình**. Ngay khi có mạng trở lại, hệ thống tự động nối tiếp chu kỳ tiếp theo và tiếp tục thu thập bình thường.

---

### 7.3. Thiết kế Mã nguồn Chạy Daemon Bền Bỉ 1 Tháng (`crawl_traffic_daemon.py`)

Dưới đây là kiến trúc chuẩn cho tiến trình chạy ngầm 1 tháng kết hợp cả 3 giải pháp trên:

```python
"""
Daemon thu thap du lieu giao thong Ha Noi 24/7 trong 30 ngay
- Phan vung theo ngay: data/daily/traffic_YYYY-MM-DD.json.gz
- Nen tu dong Gzip (giam 90% dung luong dia)
- Tu dong giu Windows khong bi Sleep
- Tu dong phuc hoi vo han khi mat mang
"""
import ctypes
import gzip
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Khai bao chong sleep Windows
def keep_system_awake():
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000040)
        except Exception:
            pass

def save_daily_cycle(cycle_record: dict, data_dir: Path):
    """Luu chu ky vao file gzip cua ngay hien tai theo phong cach append-friendly."""
    data_dir.mkdir(parents=True, exist_ok=True)
    today_str = cycle_record["timestamp_vn"][:10]  # YYYY-MM-DD
    target_file = data_dir / f"traffic_{today_str}.json.gz"
    
    # Doc du lieu ngay hien tai neu da co
    day_dataset = {"date": today_str, "cycles": []}
    if target_file.exists():
        try:
            with gzip.open(target_file, "rt", encoding="utf-8") as f:
                day_dataset = json.load(f)
        except Exception:
            pass
            
    day_dataset["cycles"].append(cycle_record)
    
    # Ghi de an toan voi nén Gzip
    temp_file = target_file.with_suffix(".tmp.gz")
    with gzip.open(temp_file, "wt", encoding="utf-8") as f:
        json.dump(day_dataset, f, ensure_ascii=False)
        
    os.replace(temp_file, target_file)
```

---

### 7.4. Hướng dẫn Chạy Ngầm Bền Bỉ (Background Execution)

#### Cách 1: Chạy ngầm trong nền PowerShell (Background Job)
Bạn có thể khởi chạy script dưới dạng PowerShell Background Job để không bị ảnh hưởng khi đóng cửa sổ terminal:

```powershell
Start-Job -ScriptBlock {
    python "c:\Users\PHAN THANH MAI\Documents\Allthings\project_school\TrafficForecasting\crawl_hanoi_traffic.py"
}
```

Kiểm tra trạng thái job đang chạy:
```powershell
Get-Job
Receive-Job -Id <Job_ID> -Keep
```

#### Cách 2: Thiết lập Windows Task Scheduler (Tự chạy lại khi bật máy)
Để đảm bảo nếu máy tính bị khởi động lại do Windows Update hoặc mất điện, crawler sẽ **tự động khởi động lại ngay khi người dùng đăng nhập**:
1. Mở **Task Scheduler** trên Windows (`taskschd.msc`).
2. Chọn **Create Basic Task** $\rightarrow$ Đặt tên: `HanoiTrafficCrawler_24_7`.
3. Trigger: Chọn **When I log on** (Khi tôi đăng nhập vào máy).
4. Action: Chọn **Start a program**:
   * **Program/script:** Đường dẫn Python (ví dụ: `c:\Users\PHAN THANH MAI\Documents\Allthings\.venv\Scripts\python.exe`).
   * **Add arguments:** `project_school/TrafficForecasting/crawl_hanoi_traffic.py`
   * **Start in:** `c:\Users\PHAN THANH MAI\Documents\Allthings`
5. Nhấn **Finish**. Hệ thống sẽ tự vận hành liên tục mà không cần can thiệp thủ công.

---

### 7.5. Pipeline Tiền Xử Lý & Ghép Nối Dữ Liệu 30 Ngày cho Deep Learning

Sau khi hoàn tất thu thập 1 tháng, ta sử dụng script sau để đọc toàn bộ các file `.json.gz` và chuyển đổi trực tiếp thành Tensor dữ liệu $X \in \mathbb{R}^{T \times N \times F}$:

```python
import gzip
import json
import glob
import numpy as np
import pandas as pd
from pathlib import Path

def load_month_traffic_dataset(daily_folder: str):
    """
    Doc toan bo file traffic_*.json.gz trong thu muc daily,
    tao ma tran toc do khong - thoi gian (Traffic Speed Matrix).
    """
    gz_files = sorted(glob.glob(f"{daily_folder}/traffic_*.json.gz"))
    print(f"[*] Tim thay {len(gz_files)} ngay du lieu.")
    
    all_cycles = []
    for gz_path in gz_files:
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            day_data = json.load(f)
            all_cycles.extend(day_data.get("cycles", []))
            
    print(f"[+] Tong so chu ky 5 phut da nap: {len(all_cycles):,} chu ky.")
    
    # Chuyen doi sang DataFrame
    records = []
    for c in all_cycles:
        t = c["timestamp_vn"]
        for seg in c.get("segments", []):
            records.append({
                "timestamp": t,
                "road_name": seg["road_name"],
                "speed_kmh": seg["speed_kmh"],
                "jam_factor": seg["jam_factor"],
                "speed_ratio": seg["speed_ratio"]
            })
            
    df = pd.DataFrame(records)
    print(f"[+] Kich thuoc DataFrame tong hop: {df.shape}")
    
    # Pivot sang ma tran Thoi gian x Doan duong (T x N)
    speed_matrix = df.pivot_table(index="timestamp", columns="road_name", values="speed_kmh")
    # Xu ly thieu du lieu bang noi suy tuyen tinh theo truc thoi gian
    speed_matrix = speed_matrix.interpolate(method="time").ffill().bfill()
    
    print(f"[+] Ma tran toc do hoan chinh: {speed_matrix.shape} (So buoc thoi gian x So doan duong)")
    return speed_matrix

# Su dung:
# speed_matrix = load_month_traffic_dataset("data/daily")
# np.save("data/hanoi_speed_matrix_30days.npy", speed_matrix.values)
```

