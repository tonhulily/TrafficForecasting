"""
Kiểm tra mỗi điểm lấy mẫu thực sự rơi vào đường nào theo chính TomTom, và loại điểm trùng đoạn đường.

Vì sao cần: Flow Segment Data API KHÔNG hiểu "khu vực" hay "ngã tư". Nó chỉ trả về đoạn đường gần
tọa độ gửi lên nhất. Script này, với mỗi điểm:
  1. (nếu thiếu tọa độ) tìm tọa độ từ tên đường bằng TomTom Geocoding;
  2. gọi Flow Segment Data để lấy đoạn đường mà API gắn vào;
  3. đổi một điểm giữa đoạn đường đó sang tên đường bằng TomTom Reverse Geocoding;
  4. so tên đường với tên mong đợi, và báo các điểm trùng đoạn đường.

Cách dùng:
    export TOMTOM_KEY="your_api_key"
    python calibrate_points.py --input candidates.csv       # điểm mới, tọa độ lấy từ tên đường
    python calibrate_points.py --input points_current.csv   # kiểm tra 10 điểm đã crawl trên Kaggle

File CSV đầu vào có các cột: name,road,area,lat,lon
  - road: tên đường mong đợi (để so khớp); có thể để trống
  - area: nhãn nhóm khu vực do bạn đặt (để phân tích theo khu vực); có thể để trống
  - lat,lon: để trống thì script tự tìm từ `road`

Mỗi điểm tốn tối đa 3 request (geocode + flow + reverse). 15 điểm ~ 45 request, nằm trong hạn mức free.

Đầu ra: points_calibrated.csv (mọi điểm kèm kết quả) và points.json (chỉ các điểm OK, không trùng,
để crawl.py dùng).
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import unicodedata
from urllib.parse import quote

import requests

FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
GEOCODE_URL = "https://api.tomtom.com/search/2/geocode/{q}.json"
REVERSE_URL = "https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


def haversine(a, b):
    R = 6371000
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


class Api:
    def __init__(self, key):
        self.key, self.s, self.n = key, requests.Session(), 0

    def get(self, url, **params):
        self.n += 1
        params["key"] = self.key
        r = self.s.get(url, params=params, timeout=15)
        time.sleep(0.3)
        if r.status_code in (401, 403, 429):
            sys.exit(f"HTTP {r.status_code}: key sai hoặc hết hạn mức. Dừng.")
        r.raise_for_status()
        return r.json()

    def geocode(self, query):
        j = self.get(GEOCODE_URL.format(q=quote(query)), countrySet="VN", limit=1, language="vi-VN")
        res = j.get("results") or []
        if not res:
            return None
        p = res[0]["position"]
        return p["lat"], p["lon"]

    def flow(self, lat, lon):
        d = self.get(FLOW_URL, point=f"{lat},{lon}")["flowSegmentData"]
        coords = [(c["latitude"], c["longitude"]) for c in d.get("coordinates", {}).get("coordinate", [])]
        return d, coords

    def street_at(self, lat, lon):
        j = self.get(REVERSE_URL.format(lat=lat, lon=lon), radius=60, language="vi-VN")
        addrs = j.get("addresses") or []
        if not addrs:
            return ""
        a = addrs[0].get("address", {})
        return a.get("streetName") or a.get("freeformAddress") or ""


def run(args):
    key = os.environ.get("TOMTOM_KEY") or sys.exit("Thiếu biến môi trường TOMTOM_KEY.")
    api = Api(key)
    rows = list(csv.DictReader(open(args.input, encoding="utf-8")))
    out = []
    for r in rows:
        name, road, area = r["name"].strip(), (r.get("road") or "").strip(), (r.get("area") or "").strip()
        res = {"name": name, "road": road, "area": area, "status": "", "note": ""}
        try:
            if r.get("lat") and r.get("lon"):
                lat, lon = float(r["lat"]), float(r["lon"])
            else:
                q = f"{road}, Hà Nội"
                pos = api.geocode(q)
                if not pos:
                    res.update(status="LỖI", note=f"không tìm được tọa độ cho '{q}'")
                    out.append(res); print(f"{name:16s} LỖI      {res['note']}"); continue
                lat, lon = pos
            res.update(lat=round(lat, 6), lon=round(lon, 6))

            d, coords = api.flow(lat, lon)
            if not coords:
                res.update(status="LỖI", note="API không trả tọa độ đoạn đường")
                out.append(res); print(f"{name:16s} LỖI      {res['note']}"); continue
            mid = coords[len(coords) // 2]
            street = api.street_at(*mid)
            ff_len = d["freeFlowSpeed"] / 3.6 * d["freeFlowTravelTime"]
            shape_len = sum(haversine(coords[i], coords[i + 1]) for i in range(len(coords) - 1))
            res.update(
                snapped_street=street, frc=d.get("frc"),
                seg_len_est_m=round(ff_len), shape_len_m=round(shape_len),
                n_vertices=len(coords),
                seg_key=f"{coords[0][0]:.5f},{coords[0][1]:.5f}|{coords[-1][0]:.5f},{coords[-1][1]:.5f}",
                free_flow_speed=d["freeFlowSpeed"], current_speed=d["currentSpeed"],
            )
            if road:
                res["status"] = "OK" if norm(road) in norm(street) else "KIỂM TRA"
                if res["status"] == "KIỂM TRA":
                    res["note"] = f"đường mong đợi '{road}' nhưng API trả '{street}'"
            else:
                res["status"] = "OK"
        except Exception as e:                    # không để một điểm lỗi làm hỏng cả lượt
            res.update(status="LỖI", note=str(e))
        out.append(res)
        print(f"{name:16s} {res['status']:9s} -> {res.get('snapped_street','?')!s:30s} "
              f"{res.get('frc','')} ~{res.get('seg_len_est_m','?')} m  {res['note']}")

    # đánh dấu điểm trùng đoạn đường: giữ điểm đầu tiên, các điểm sau là TRÙNG
    seen = {}
    for res in out:
        k = res.get("seg_key")
        if not k:
            continue
        if k in seen:
            res["status"] = "TRÙNG"
            res["note"] = f"cùng đoạn đường với {seen[k]}"
        else:
            seen[k] = res["name"]

    fields = ["name", "road", "area", "lat", "lon", "status", "snapped_street", "frc", "seg_len_est_m",
              "shape_len_m", "n_vertices", "current_speed", "free_flow_speed", "seg_key", "note"]
    with open("points_calibrated.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(out)
    good = [{"name": o["name"], "road": o["snapped_street"], "area": o["area"],
             "lat": o["lat"], "lon": o["lon"]} for o in out if o["status"] == "OK"]
    json.dump(good, open("points.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\nĐã dùng {api.n} request. OK: {len(good)}/{len(out)} điểm.")
    print("Xem points_calibrated.csv; các dòng KIỂM TRA/TRÙNG/LỖI cần sửa tọa độ rồi chạy lại.")
    print("points.json chỉ chứa điểm OK. crawl.py sẽ dùng file này nếu có.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    run(ap.parse_args())
