"""
Hệ thống thu thập dữ liệu lưu lượng giao thông Hà Nội (HERE Traffic API v7)
- Phạm vi: Toàn bộ các tuyến đường tại Hà Nội (4 phân vùng địa lý)
- Chu kỳ: 5 phút/lần (mặc định)
- Lưu trữ: 1 file JSON hoàn chỉnh và cập nhật an toàn theo từng chu kỳ
- Dừng: Nhấn Ctrl + C để dừng bất cứ lúc nào
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Cấu hình UTF-8 cho Windows Terminal để không bị lỗi ký tự Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Cấu hình mặc định
DEFAULT_API_KEY = os.environ.get("HERE_API_KEY", "rKB0D9BpXohx0hbz8d1y4pgV-pl6gUbtSwn8Yf6afuA")
DEFAULT_INTERVAL_SECONDS = 300  # 5 phút
DEFAULT_OUTPUT_FILE = "data/hanoi_traffic_data.json"
VN_TZ = timezone(timedelta(hours=7))

# 4 phân vùng bounding box bao phủ toàn bộ đô thị và ngoại vi Hà Nội
# Định dạng bbox của HERE API: west_longitude,south_latitude,east_longitude,north_latitude
HANOI_REGIONS = [
    {
        "id": "SW",
        "name": "Tay Nam (Ha Dong, Thanh Xuan, Nam Tu Liem, Thanh Tri Tay)",
        "bbox": "105.65,20.90,105.80,21.01"
    },
    {
        "id": "SE",
        "name": "Dong Nam (Hoang Mai, Thanh Tri Dong, Hai Ba Trung Nam)",
        "bbox": "105.80,20.90,105.95,21.01"
    },
    {
        "id": "NW",
        "name": "Tay Bac (Cau Giay, Bac Tu Liem, Tay Ho Tay)",
        "bbox": "105.65,21.01,105.80,21.12"
    },
    {
        "id": "NE",
        "name": "Dong Bac (Ba Dinh, Hoan Kiem, Dong Da, Long Bien, Tay Ho)",
        "bbox": "105.80,21.01,105.95,21.12"
    }
]


def format_jam_level(jam_factor: Optional[float]) -> str:
    """Mô tả mức độ kẹt xe dựa trên Jam Factor (thang điểm 0 - 10)"""
    if jam_factor is None:
        return "Khong xac dinh"
    if jam_factor < 2.0:
        return "Thong thoang"
    elif jam_factor < 4.0:
        return "Dong nhe"
    elif jam_factor < 7.0:
        return "Un u trung binh"
    elif jam_factor < 9.0:
        return "Un tac nang"
    else:
        return "Tac nghen nghiem trong"


def fetch_region_flow(region: Dict[str, str], api_key: str, max_retries: int = 3) -> List[Dict[str, Any]]:
    """Gửi yêu cầu tới HERE Traffic API v7 lấy dữ liệu lưu lượng của 1 vùng bbox."""
    base_url = "https://data.traffic.hereapi.com/v7/flow"
    params = {
        "in": f"bbox:{region['bbox']}",
        "locationReferencing": "shape",
        "apiKey": api_key,
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Hanoi-Traffic-Crawler/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=40) as response:
                status = getattr(response, "status", getattr(response, "code", 200))
                if status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    return payload.get("results", [])
                else:
                    print(f"\n  [!] Vung {region['id']} tra ve ma HTTP {status}")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError(f"Loi xac thuc API Key ({e.code}): Vui long kiem tra lai HERE_API_KEY.")
            elif e.code == 429:
                print(f"\n  [!] Cham gioi han tan suat goi (HTTP 429), cho 5s thu lai...")
                time.sleep(5)
            else:
                print(f"\n  [!] HTTP {e.code} o lan thu {attempt}/{max_retries}")
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 * attempt)
            else:
                print(f"\n  [!] Khong the lay du lieu vung {region['id']}: {e}")
    return []


def parse_segment(raw_item: Dict[str, Any], region_id: str) -> Dict[str, Any]:
    """Trích xuất và chuẩn hóa thông tin đoạn đường phục vụ phân tích."""
    loc = raw_item.get("location", {})
    cf = raw_item.get("currentFlow", {})
    
    speed_mps = cf.get("speed") or 0.0
    free_flow_mps = cf.get("freeFlow") or 0.0
    speed_kmh = round(float(speed_mps) * 3.6, 2)
    free_flow_kmh = round(float(free_flow_mps) * 3.6, 2)
    jam_factor = round(float(cf.get("jamFactor") or 0.0), 2)
    
    # Tọa độ điểm đầu của đoạn đường nếu có
    shape_links = loc.get("shape", {}).get("links", [])
    first_coord = None
    if shape_links and isinstance(shape_links, list) and len(shape_links) > 0:
        first_link = shape_links[0]
        if isinstance(first_link, dict):
            pts = first_link.get("points")
            if pts and isinstance(pts, list) and len(pts) > 0:
                pt = pts[0]
                if isinstance(pt, dict):
                    first_coord = {"lat": pt.get("lat"), "lon": pt.get("lng")}

    return {
        "road_name": loc.get("description", "Doan duong khong ten"),
        "region_id": region_id,
        "length_meters": float(loc.get("length") or 0.0),
        "speed_kmh": speed_kmh,
        "free_flow_kmh": free_flow_kmh,
        "speed_ratio": round(speed_kmh / free_flow_kmh, 3) if free_flow_kmh > 0 else 1.0,
        "jam_factor": jam_factor,
        "jam_level": format_jam_level(jam_factor),
        "confidence": float(cf.get("confidence") or 0.0),
        "traversability": cf.get("traversability", "open"),
        "coord": first_coord
    }


def load_or_init_dataset(file_path: Path) -> Dict[str, Any]:
    """Đọc file JSON hiện có nếu có hoặc khởi tạo cấu trúc dữ liệu mới."""
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "cycles" in data:
                    return data
        except Exception:
            pass
            
    return {
        "metadata": {
            "city": "Ha Noi, Viet Nam",
            "source": "HERE Traffic API v7",
            "started_at": datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "total_cycles_completed": 0,
            "description": "Du lieu luu luong giao thong toan thanh pho Ha Noi theo chu ky 5 phut"
        },
        "cycles": []
    }


def save_dataset_atomic(file_path: Path, dataset: Dict[str, Any]):
    """Ghi dữ liệu an toàn bằng file tạm để tránh hỏng dữ liệu nếu bị ngắt đột ngột."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = file_path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

    try:
        os.replace(temp_file, file_path)
    except OSError:
        # Fallback cho trường hợp Windows file lock
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def run_crawler():
    parser = argparse.ArgumentParser(description="He thong thu thap du lieu giao thong Ha Noi")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS, help="Khoang cach giua cac luot crawl (giay), mac dinh 300s")
    parser.add_argument("--out", type=str, default=DEFAULT_OUTPUT_FILE, help="Duong dan file JSON xuat ra")
    parser.add_argument("--api-key", type=str, default=DEFAULT_API_KEY, help="HERE API Key")
    parser.add_argument("--test", action="store_true", help="Chi chay 1 luot kiem tra roi thoat")
    args = parser.parse_args()

    out_path = Path(args.out)
    dataset = load_or_init_dataset(out_path)
    cycle_count = dataset["metadata"].get("total_cycles_completed", 0)

    print("\n" + "=" * 80)
    print("      HE THONG CRAWL DU LIEU GIAO THONG TOAN TP HA NOI (HERE TRAFFIC API)")
    print("=" * 80)
    print(f" * Chu ky thu thap: Moi {args.interval} giay (~{args.interval // 60} phut)")
    print(f" * File luu tru:    {out_path.resolve()}")
    print(f" * So phan vung:    4 khu vuc bounding box (phu tron noi va ngoai thanh Ha Noi)")
    print(f" * Da luu truoc do: {cycle_count} luot trong file JSON")
    print(f" * Cach dung:       Nhan [Ctrl + C] bat cu luc nao de dung an toan")
    print("=" * 80 + "\n")

    try:
        while True:
            cycle_count += 1
            now_vn = datetime.now(VN_TZ)
            timestamp_str = now_vn.strftime("%Y-%m-%d %H:%M:%S")

            print(f"\n[+] [LUOT CRAWL #{cycle_count}] Bat dau luc {timestamp_str}")
            print("-" * 80)

            all_records: List[Dict[str, Any]] = []
            seen_roads = set()

            for idx, reg in enumerate(HANOI_REGIONS, start=1):
                sys.stdout.write(f"  [{idx}/4] Dang quet {reg['name']}...")
                sys.stdout.flush()
                start_req = time.time()
                
                raw_results = fetch_region_flow(reg, args.api_key)
                elapsed = time.time() - start_req

                count = 0
                for item in raw_results:
                    parsed = parse_segment(item, reg["id"])
                    # Tao key dinh danh de tranh trung lap giua cac vung giao thoa
                    road_key = (parsed["road_name"], round(parsed["length_meters"], 0), parsed["speed_kmh"])
                    if road_key not in seen_roads:
                        seen_roads.add(road_key)
                        all_records.append(parsed)
                        count += 1

                sys.stdout.write(f"\r  [{idx}/4] [OK] {reg['name']}: {count} doan duong ({elapsed:.1f}s)\n")
                sys.stdout.flush()
                time.sleep(0.5)  # Tranh gui don dap

            # Tinh toan thong ke luot crawl nay
            total_segs = len(all_records)
            if total_segs > 0:
                avg_speed = sum(r["speed_kmh"] for r in all_records) / total_segs
                avg_jam = sum(r["jam_factor"] for r in all_records) / total_segs
                free_count = sum(1 for r in all_records if r["jam_factor"] < 2.0)
                moderate_count = sum(1 for r in all_records if 2.0 <= r["jam_factor"] < 7.0)
                congested_count = sum(1 for r in all_records if r["jam_factor"] >= 7.0)
            else:
                avg_speed = 0.0
                avg_jam = 0.0
                free_count = moderate_count = congested_count = 0

            # Cap nhat vao dataset
            cycle_data = {
                "cycle_id": cycle_count,
                "timestamp_vn": timestamp_str,
                "summary": {
                    "total_segments": total_segs,
                    "avg_speed_kmh": round(avg_speed, 1),
                    "avg_jam_factor": round(avg_jam, 2),
                    "status_counts": {
                        "free_flow": free_count,
                        "moderate": moderate_count,
                        "congested": congested_count
                    }
                },
                "segments": all_records
            }

            dataset["cycles"].append(cycle_data)
            dataset["metadata"]["total_cycles_completed"] = cycle_count
            dataset["metadata"]["last_updated_at"] = timestamp_str

            # Luu vao file JSON an toan
            save_dataset_atomic(out_path, dataset)
            file_size_mb = out_path.stat().st_size / (1024 * 1024)

            # In bao cao tien trinh
            print("\n  >> TONG KET TIEN TRINH LUOT #" f"{cycle_count}:")
            print(f"     * Tong so doan duong thu thap: {total_segs:,} doan")
            print(f"     * Toc do trung binh toan TP:    {avg_speed:.1f} km/h (Jam Factor: {avg_jam:.2f}/10)")
            print(f"     * Phan loai luu thong:          Thong thoang: {free_count:,} | Un u: {moderate_count:,} | Tac nghen: {congested_count:,}")
            print(f"     * Da luu file:                  {out_path.name} ({file_size_mb:.2f} MB)")

            # Hien thi Top 5 tuyen duong tac nhat
            if congested_count > 0:
                top_congested = sorted(all_records, key=lambda x: x["jam_factor"], reverse=True)[:5]
                print("     * [!] Top tuyen duong un tac nhat:")
                for r_idx, road in enumerate(top_congested, start=1):
                    print(f"        {r_idx}. {road['road_name'][:45]}: {road['speed_kmh']} km/h (Muc: {road['jam_factor']}/10 - {road['jam_level']})")

            print("-" * 80)

            if args.test:
                print("[*] Che do --test: Hoan thanh 1 luot chay thu nghiem thanh cong.")
                break

            # Dem nguoc thoi gian cho den luot tiep theo
            next_run_time = time.time() + args.interval
            while time.time() < next_run_time:
                remaining = int(next_run_time - time.time())
                mins, secs = divmod(remaining, 60)
                sys.stdout.write(f"\r  [Cho] Luot tiep theo sau: {mins:02d}:{secs:02d} ... (Nhan Ctrl + C de dung) ")
                sys.stdout.flush()
                time.sleep(1)

            sys.stdout.write("\r" + " " * 80 + "\r")

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("[!] NHAN DUOC LENH DUNG (Ctrl + C) TU BAN!")
        print(f" * Da ghi lai an toan: {cycle_count} luot thu thap.")
        print(f" * File du lieu day du tai: {out_path.resolve()}")
        print(" * Toan bo cau truc file JSON da duoc luu hoan chinh va san sang de su dung.")
        print("=" * 80 + "\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Gap su co khong mong muon: {e}")
        # Van bao toan file da luu
        save_dataset_atomic(out_path, dataset)
        sys.exit(1)


if __name__ == "__main__":
    run_crawler()
