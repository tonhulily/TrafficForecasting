"""
Crawl dữ liệu lưu lượng giao thông Hà Nội từ TomTom Traffic Flow Segment Data API.

Chạy trên laptop:
    export TOMTOM_KEY="your_api_key"
    caffeinate -i python3 crawl.py --hours 8 --interval 300

Chạy trên Kaggle: thêm secret TOMTOM_KEY (Add-ons -> Secrets), hoặc gán biến môi trường,
rồi chạy:  !python crawl.py --hours 8 --interval 300 --out /kaggle/working

Dùng --test để chỉ chạy 1 lượt kiểm tra key và mạng.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
VN_TZ = timezone(timedelta(hours=7))

# Danh sách điểm mặc định (tọa độ gần đúng, CHƯA kiểm chứng). Nên dùng points.json do
# calibrate_points.py tạo ra: file đó chỉ giữ các điểm đã được TomTom xác nhận đúng đường.
# Lưu ý: API chỉ trả về đoạn đường gần tọa độ nhất, không hiểu "khu vực" hay "ngã tư".
DEFAULT_POINTS = [
    {"name": "ho_guom",       "road": "", "area": "", "lat": 21.0285, "lon": 105.8542},
    {"name": "nga_tu_so",     "road": "", "area": "", "lat": 21.0072, "lon": 105.8268},
    {"name": "cau_giay",      "road": "", "area": "", "lat": 21.0333, "lon": 105.7940},
    {"name": "nga_tu_vong",   "road": "", "area": "", "lat": 20.9969, "lon": 105.8409},
    {"name": "kim_ma",        "road": "", "area": "", "lat": 21.0330, "lon": 105.8160},
    {"name": "pham_van_dong", "road": "", "area": "", "lat": 21.0460, "lon": 105.7830},
    {"name": "dai_co_viet",   "road": "", "area": "", "lat": 21.0050, "lon": 105.8450},
    {"name": "nguyen_trai",   "road": "", "area": "", "lat": 20.9985, "lon": 105.8010},
    {"name": "cau_long_bien", "road": "", "area": "", "lat": 21.0437, "lon": 105.8590},
    {"name": "bach_mai",      "road": "", "area": "", "lat": 21.0000, "lon": 105.8510},
]


def load_points(path):
    if path and Path(path).exists():
        pts = json.loads(Path(path).read_text(encoding="utf-8"))
        print(f"Dùng {len(pts)} điểm từ {path}")
        return pts
    print("Không có points.json, dùng danh sách mặc định (chưa kiểm chứng).")
    return DEFAULT_POINTS


def get_api_key() -> str:
    key = os.environ.get("TOMTOM_KEY")
    if not key:
        try:  # Kaggle Secrets
            from kaggle_secrets import UserSecretsClient
            key = UserSecretsClient().get_secret("TOMTOM_KEY")
        except Exception:
            pass
    if not key:
        sys.exit("Thiếu API key: đặt biến môi trường TOMTOM_KEY.")
    return key


class Budget:
    """Đếm request theo ngày UTC, lưu vào file để cộng dồn giữa các lần chạy."""

    def __init__(self, path: Path, daily_cap: int):
        self.path, self.cap = path, daily_cap

    @staticmethod
    def _today():
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def used(self) -> int:
        if self.path.exists():
            c = json.loads(self.path.read_text())
            if c.get("date") == self._today():
                return c["count"]
        return 0

    def bump(self):
        self.path.write_text(json.dumps({"date": self._today(), "count": self.used() + 1}))


def fetch(session, key, budget, pt):
    name, lat, lon = pt["name"], pt["lat"], pt["lon"]
    for _ in range(2):                       # thử lại 1 lần nếu lỗi mạng
        budget.bump()                        # đếm trước khi gọi, kể cả khi lỗi
        try:
            r = session.get(URL, params={"key": key, "point": f"{lat},{lon}"}, timeout=15)
        except requests.RequestException as e:
            print(f"  lỗi mạng {name}: {e}")
            time.sleep(2)
            continue
        if r.status_code in (401, 403, 429):
            raise RuntimeError(f"HTTP {r.status_code}: key sai hoặc đã chạm hạn mức.")
        if r.status_code != 200:
            print(f"  {name}: HTTP {r.status_code}")
            return None
        d = r.json()["flowSegmentData"]
        coords = d.get("coordinates", {}).get("coordinate", [{}])
        now = datetime.now(timezone.utc)
        return {
            "ts_utc": now.isoformat(),
            "ts_vn": now.astimezone(VN_TZ).isoformat(),
            "point": name, "road": pt.get("road", ""), "area": pt.get("area", ""),
            "lat": lat, "lon": lon,
            "seg_lat": coords[0].get("latitude"), "seg_lon": coords[0].get("longitude"),
            "frc": d.get("frc"),
            "current_speed": d.get("currentSpeed"),
            "free_flow_speed": d.get("freeFlowSpeed"),
            "current_tt": d.get("currentTravelTime"),
            "free_flow_tt": d.get("freeFlowTravelTime"),
            "confidence": d.get("confidence"),
            "road_closure": d.get("roadClosure"),
        }
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=8, help="tổng thời gian chạy (giờ)")
    ap.add_argument("--interval", type=int, default=300, help="chu kỳ giữa các lượt (giây)")
    ap.add_argument("--daily-cap", type=int, default=2000, help="ngưỡng request/ngày (free: 2500)")
    ap.add_argument("--out", default="data", help="thư mục ghi dữ liệu")
    ap.add_argument("--points", default="points.json", help="file điểm do calibrate_points.py tạo")
    ap.add_argument("--test", action="store_true", help="chỉ chạy 1 lượt để kiểm tra")
    args = ap.parse_args()

    key = get_api_key()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"traffic_{datetime.now(timezone.utc):%Y%m%d_%H%M}.jsonl"
    budget = Budget(out_dir / "counter.json", args.daily_cap)
    session = requests.Session()
    points = load_points(args.points)

    cycles = int(args.hours * 3600 / args.interval)
    print(f"{'TEST' if args.test else 'CHẠY'} | {len(points)} điểm | ~{cycles * len(points)} request | "
          f"hôm nay (UTC) đã dùng {budget.used()} | ghi vào {out_file}")

    end_time = time.time() + args.hours * 3600
    next_tick = time.time()
    try:
        while time.time() < end_time:
            if budget.used() + len(points) * 2 > budget.cap:
                print("Đã đạt ngưỡng request trong ngày, chờ sang ngày mới (UTC)...", flush=True)
                time.sleep(600)
                next_tick = time.time()
                continue
            rows = []
            for pt in points:
                row = fetch(session, key, budget, pt)
                if row:
                    rows.append(row)
                time.sleep(0.3)                   # giữ dưới 5 request/giây
            with open(out_file, "a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{datetime.now(VN_TZ):%H:%M:%S} | ghi {len(rows)} dòng | hôm nay đã dùng {budget.used()}",
                  flush=True)
            if args.test:
                break
            next_tick += args.interval
            now = time.time()
            if next_tick < now:                   # bị trễ (máy ngủ, chờ hạn mức) thì không chạy dồn
                next_tick = now + args.interval
            time.sleep(next_tick - now)
    except KeyboardInterrupt:
        print("Đã dừng bằng tay.")
    except Exception as e:                        # thoát êm để file kết quả vẫn được giữ lại
        print("Dừng do lỗi:", e)
    print("Xong.")


if __name__ == "__main__":
    main()
