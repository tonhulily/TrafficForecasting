"""
Standalone HERE Traffic API Checker
Independent utility script to query real-time Traffic Flow and Incidents.
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

# Default configuration
DEFAULT_API_KEY = "rKB0D9BpXohx0hbz8d1y4pgV-pl6gUbtSwn8Yf6afuA"
DEFAULT_LATITUDE = 20.96936
DEFAULT_LONGITUDE = 105.76761
DEFAULT_RADIUS_METERS = 1500


def get_traffic_flow(
    lat: float = DEFAULT_LATITUDE,
    lon: float = DEFAULT_LONGITUDE,
    radius: int = DEFAULT_RADIUS_METERS,
    api_key: str = DEFAULT_API_KEY,
) -> Dict[str, Any]:
    """
    Fetch Traffic Flow information (speed, jam factor, congestion) from HERE Traffic API v7.
    """
    base_url = "https://data.traffic.hereapi.com/v7/flow"
    params = {
        "in": f"circle:{lat},{lon};r={radius}",
        "locationReferencing": "shape",
        "apiKey": api_key,
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url, headers={"User-Agent": "HERE-Traffic-Checker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def get_traffic_incidents(
    lat: float = DEFAULT_LATITUDE,
    lon: float = DEFAULT_LONGITUDE,
    radius: int = DEFAULT_RADIUS_METERS,
    api_key: str = DEFAULT_API_KEY,
) -> Dict[str, Any]:
    """
    Fetch Traffic Incidents (accidents, road closures, hazards) from HERE Traffic API v7.
    """
    base_url = "https://data.traffic.hereapi.com/v7/incidents"
    params = {
        "in": f"circle:{lat},{lon};r={radius}",
        "locationReferencing": "shape",
        "apiKey": api_key,
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url, headers={"User-Agent": "HERE-Traffic-Checker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def format_jam_factor(jam_factor: Optional[float]) -> str:
    """Format Jam Factor (0.0 - 10.0 scale) into human readable text."""
    if jam_factor is None:
        return "Unknown"
    if jam_factor < 2.0:
        return f"{jam_factor:.1f}/10 (Thông thoáng / Free flow)"
    elif jam_factor < 4.0:
        return f"{jam_factor:.1f}/10 (Đông nhẹ / Light congestion)"
    elif jam_factor < 7.0:
        return f"{jam_factor:.1f}/10 (Ùn ứ trung bình / Moderate congestion)"
    elif jam_factor < 9.0:
        return f"{jam_factor:.1f}/10 (Ùn tắc nặng / Heavy congestion)"
    else:
        return f"{jam_factor:.1f}/10 (Tắc nghẽn nghiêm trọng / Standstill)"


def print_traffic_report(
    lat: float = DEFAULT_LATITUDE,
    lon: float = DEFAULT_LONGITUDE,
    radius: int = DEFAULT_RADIUS_METERS,
    api_key: str = DEFAULT_API_KEY,
):
    print("=" * 70)
    print("           BÁO CÁO THÔNG TIN GIAO THÔNG (HERE TRAFFIC API v7)")
    print("=" * 70)
    print(f"Vị trí (WGS84): Vĩ độ (Lat) = {lat}, Kinh độ (Lon) = {lon}")
    print(f"Bán kính khảo sát: {radius}m")
    print(f"API Key: {api_key[:6]}...{api_key[-4:]}")
    print("-" * 70)

    # 1. Flow
    try:
        flow_data = get_traffic_flow(lat, lon, radius, api_key)
        source_updated = flow_data.get("sourceUpdated", "N/A")
        results = flow_data.get("results", [])
        print(f"\n[1] LƯU LƯỢNG GIAO THÔNG (Traffic Flow) - Cập nhật: {source_updated}")
        print(f"Tìm thấy dữ liệu lưu lượng trên {len(results)} đoạn đường gần tọa độ:")

        if not results:
            print("  Không có dữ liệu lưu lượng giao thông chi tiết.")
        else:
            for idx, item in enumerate(results[:10], start=1):
                loc = item.get("location", {})
                cf = item.get("currentFlow", {})
                desc = loc.get("description", "Đoạn đường không tên")
                speed_mps = cf.get("speed", 0)
                free_flow_mps = cf.get("freeFlow", 0)
                speed_kmh = speed_mps * 3.6
                free_flow_kmh = free_flow_mps * 3.6
                jam = cf.get("jamFactor", 0.0)
                confidence = cf.get("confidence", 0.0)

                print(f"\n  #{idx}. Tuyến đường: {desc}")
                print(f"     - Chiều dài đoạn: {loc.get('length', 0):.0f} m")
                print(f"     - Tốc độ hiện tại: {speed_kmh:.1f} km/h ({speed_mps:.1f} m/s)")
                print(f"     - Tốc độ chuẩn (Free Flow): {free_flow_kmh:.1f} km/h ({free_flow_mps:.1f} m/s)")
                print(f"     - Mức độ ùn tắc (Jam Factor): {format_jam_factor(jam)}")
                print(f"     - Độ tin cậy dữ liệu: {confidence * 100:.0f}%")
    except Exception as e:
        print(f"\n[!] Lỗi khi lấy dữ liệu Traffic Flow: {e}")

    # 2. Incidents
    try:
        incidents_data = get_traffic_incidents(lat, lon, radius, api_key)
        inc_results = incidents_data.get("results", [])
        print(f"\n[2] SỰ CỐ GIAO THÔNG (Traffic Incidents)")
        print(f"Tìm thấy: {len(inc_results)} sự cố trong bán kính {radius}m.")

        if not inc_results:
            print("  -> Tuyệt vời: Hiện không ghi nhận sự cố, tai nạn hay đường cấm nào tại khu vực này.")
        else:
            for idx, inc in enumerate(inc_results, start=1):
                details = inc.get("incidentDetails", {})
                desc = details.get("description", {}).get("value", "Không có mô tả chi tiết")
                criticality = details.get("criticality", "N/A")
                print(f"  #{idx}. Mức độ: {criticality} | Mô tả: {desc}")
    except Exception as e:
        print(f"\n[!] Lỗi khi lấy dữ liệu Traffic Incidents: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print_traffic_report()
