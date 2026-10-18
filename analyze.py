"""
Phân tích dữ liệu giao thông Hà Nội crawl từ TomTom Traffic Flow API.

Cách dùng:
    python analyze.py                          # đọc data/traffic_*.jsonl
    python analyze.py --input "data/*.jsonl" --out analysis

Đầu ra (thư mục analysis/):
    summary.md            các bảng thống kê dạng markdown, dán thẳng vào báo cáo
    per_point_stats.csv   thống kê theo từng điểm
    hourly_ratio.csv      tỷ lệ tốc độ trung bình theo giờ và theo điểm
    *.png                 biểu đồ (biểu đồ theo thời gian chỉ vẽ khi đủ dữ liệu)
"""
import argparse
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- đọc dữ liệu
def load(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    if not files:
        sys.exit(f"Không tìm thấy file nào khớp: {pattern}")
    frames = []
    for f in files:
        d = pd.read_json(f, lines=True)
        d["source_file"] = Path(f).name
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["ts_vn"] = pd.to_datetime(df["ts_vn"], format="ISO8601")
    df = df.sort_values(["ts_vn", "point"]).reset_index(drop=True)
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Một "lượt crawl" = các dòng cách nhau < 60 giây (một lượt kéo dài vài giây)
    gap = df["ts_vn"].diff().dt.total_seconds().fillna(1e9)
    df["cycle_id"] = (gap > 60).cumsum()
    df["cycle_time"] = df.groupby("cycle_id")["ts_vn"].transform("min")

    df["speed_ratio"] = df["current_speed"] / df["free_flow_speed"]
    df["delay_s"] = df["current_tt"] - df["free_flow_tt"]
    df["delay_ratio"] = df["current_tt"] / df["free_flow_tt"]
    # Độ dài đoạn đường (ước lượng) = vận tốc thông thoáng x thời gian thông thoáng
    df["seg_len_m_est"] = df["free_flow_speed"] / 3.6 * df["free_flow_tt"]
    df["hour"] = df["ts_vn"].dt.hour
    df["dow"] = df["ts_vn"].dt.dayofweek            # 0 = Thứ Hai
    df["is_weekend"] = df["dow"] >= 5
    # Mức ùn tắc theo tỷ lệ tốc độ (ngưỡng tham khảo, có thể chỉnh)
    df["congestion"] = pd.cut(
        df["speed_ratio"], bins=[0, 0.4, 0.7, 0.9, 10],
        labels=["Ùn tắc nặng", "Ùn tắc", "Hơi chậm", "Thông thoáng"], include_lowest=True)
    return df


# ------------------------------------------------------------- chất lượng dữ liệu
def quality_report(df: pd.DataFrame) -> dict:
    n_points = df["point"].nunique()
    n_cycles = df["cycle_id"].nunique()
    cyc_times = df.groupby("cycle_id")["cycle_time"].first().sort_values()
    intervals = cyc_times.diff().dt.total_seconds().dropna()
    median_interval = float(intervals.median()) if len(intervals) else float("nan")
    big_gaps = intervals[intervals > 1.5 * median_interval] if len(intervals) else intervals

    seg = df.groupby("point")[["seg_lat", "seg_lon"]].agg(lambda s: s.round(6).iloc[0])
    seg["key"] = list(zip(seg["seg_lat"], seg["seg_lon"]))
    dup = seg.groupby("key").apply(lambda g: list(g.index), include_groups=False)
    dup_groups = [g for g in dup if len(g) > 1]

    return {
        "n_rows": len(df),
        "n_points": n_points,
        "n_cycles": n_cycles,
        "expected_rows": n_points * n_cycles,
        "missing_rows": n_points * n_cycles - len(df),
        "start": df["ts_vn"].min(),
        "end": df["ts_vn"].max(),
        "median_interval_s": median_interval,
        "n_gaps": int(len(big_gaps)),
        "max_gap_min": float(intervals.max() / 60) if len(intervals) else float("nan"),
        "null_cells": int(df.isna().sum().sum()),
        "duplicate_segment_groups": dup_groups,
        "road_closure_rows": int(df["road_closure"].sum()),
    }


# ----------------------------------------------------------------- thống kê
def per_point_stats(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("point")
    extra = {}
    for col in ("road", "area"):
        if col in df.columns and df[col].fillna("").astype(str).str.len().gt(0).any():
            extra[col] = g[col].agg(lambda s: s.mode().iloc[0])
    out = pd.DataFrame({
        **extra,
        "frc": g["frc"].agg(lambda s: s.mode().iloc[0]),
        "n": g.size(),
        "speed_mean": g["current_speed"].mean(),
        "speed_min": g["current_speed"].min(),
        "speed_max": g["current_speed"].max(),
        "free_flow_speed": g["free_flow_speed"].median(),
        "ratio_mean": g["speed_ratio"].mean(),
        "ratio_min": g["speed_ratio"].min(),
        "delay_s_mean": g["delay_s"].mean(),
        "delay_s_max": g["delay_s"].max(),
        "confidence_mean": g["confidence"].mean(),
        "seg_len_m_est": g["seg_len_m_est"].median(),
    }).round(3)
    return out.sort_values("ratio_mean")


def to_md(df: pd.DataFrame, index=True) -> str:
    return df.to_markdown(index=index) if hasattr(df, "to_markdown") else df.to_string(index=index)


# ------------------------------------------------------------------ biểu đồ
def savefig(path: Path):
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def plot_ratio_by_point(df, out):
    order = df.groupby("point")["speed_ratio"].mean().sort_values().index
    data = [df.loc[df["point"] == p, "speed_ratio"].values for p in order]
    plt.figure(figsize=(9, 4.8))
    plt.boxplot(data, tick_labels=list(order), vert=True)
    plt.axhline(1.0, color="gray", ls="--", lw=0.8)
    plt.ylabel("Tốc độ hiện tại / tốc độ thông thoáng")
    plt.title("Mức độ ùn tắc theo từng điểm (thấp hơn = tắc hơn)")
    plt.xticks(rotation=35, ha="right")
    savefig(out / "ratio_by_point.png")


def has_area(df):
    return "area" in df.columns and df["area"].fillna("").astype(str).str.len().gt(0).any()


def area_stats(df):
    d = df[df["area"].fillna("").astype(str).str.len() > 0]
    g = d.groupby("area")
    return pd.DataFrame({
        "n_points": g["point"].nunique(),
        "ratio_mean": g["speed_ratio"].mean(),
        "ratio_min": g["speed_ratio"].min(),
        "delay_s_mean": g["delay_s"].mean(),
    }).round(3).sort_values("ratio_mean")


def plot_area(df, out):
    a = area_stats(df)
    plt.figure(figsize=(8, 4.5))
    plt.barh(a.index, a["ratio_mean"], color="tab:orange")
    plt.axvline(1.0, color="gray", ls="--", lw=0.8)
    plt.xlabel("Tỷ lệ tốc độ trung bình (thấp hơn = tắc hơn)")
    plt.title("Mức độ ùn tắc theo khu vực (nhóm các đường trong khu vực)")
    savefig(out / "ratio_by_area.png")


def plot_speed_time(df, out):
    plt.figure(figsize=(11, 5))
    for p, g in df.groupby("point"):
        plt.plot(g["cycle_time"], g["current_speed"], lw=1, label=p)
    plt.ylabel("Tốc độ hiện tại (km/h)")
    plt.xlabel("Thời gian (giờ Việt Nam)")
    plt.title("Tốc độ theo thời gian tại từng điểm")
    plt.legend(fontsize=7, ncol=2)
    plt.gcf().autofmt_xdate()
    savefig(out / "speed_over_time.png")


def plot_city_ratio_time(df, out):
    city = df.groupby("cycle_time")["speed_ratio"].mean()
    plt.figure(figsize=(11, 4.5))
    plt.plot(city.index, city.values, lw=1.4, color="tab:red")
    plt.axhline(1.0, color="gray", ls="--", lw=0.8)
    plt.ylabel("Tỷ lệ tốc độ trung bình các điểm")
    plt.xlabel("Thời gian (giờ Việt Nam)")
    plt.title("Mức độ thông thoáng trung bình toàn bộ điểm theo thời gian")
    plt.gcf().autofmt_xdate()
    savefig(out / "city_ratio_over_time.png")


def plot_hourly_heatmap(df, out):
    pv = df.pivot_table(index="point", columns="hour", values="speed_ratio", aggfunc="mean")
    pv = pv[list(dict.fromkeys(df.sort_values("ts_vn")["hour"]))]   # cột theo thứ tự thời gian crawl
    pv = pv.loc[pv.mean(axis=1).sort_values().index]
    pv.to_csv(out / "hourly_ratio.csv", float_format="%.3f")
    plt.figure(figsize=(10, 5))
    plt.imshow(pv.values, aspect="auto", cmap="RdYlGn", vmin=0.3, vmax=1.0)
    plt.colorbar(label="Tốc độ / thông thoáng")
    plt.yticks(range(len(pv.index)), pv.index)
    plt.xticks(range(len(pv.columns)), pv.columns)
    plt.xlabel("Giờ trong ngày (giờ Việt Nam)")
    plt.title("Tỷ lệ tốc độ theo giờ và theo điểm")
    savefig(out / "hourly_heatmap.png")


def plot_hist_confidence(df, out):
    plt.figure(figsize=(7, 4))
    plt.hist(df["confidence"], bins=20, color="tab:blue")
    plt.xlabel("confidence")
    plt.ylabel("Số bản ghi")
    plt.title("Phân phối độ tin cậy của dữ liệu")
    savefig(out / "confidence_hist.png")


def plot_frc(df, out):
    c = df.drop_duplicates("point")["frc"].value_counts().sort_index()
    plt.figure(figsize=(6, 4))
    plt.bar(c.index, c.values, color="tab:green")
    plt.ylabel("Số điểm")
    plt.title("Số điểm theo cấp đường chức năng (FRC)")
    savefig(out / "frc_counts.png")


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/traffic_*.jsonl")
    ap.add_argument("--out", default="analysis")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = add_features(load(args.input))
    q = quality_report(df)
    stats = per_point_stats(df)
    stats.to_csv(out / "per_point_stats.csv")

    plot_ratio_by_point(df, out)
    plot_hist_confidence(df, out)
    plot_frc(df, out)
    if has_area(df):
        plot_area(df, out)
    notes = []
    if q["n_cycles"] >= 3:
        plot_speed_time(df, out)
        plot_city_ratio_time(df, out)
    else:
        notes.append("Chưa đủ số lượt crawl (< 3) nên bỏ qua các biểu đồ theo thời gian.")
    if df["hour"].nunique() >= 2:
        plot_hourly_heatmap(df, out)
    else:
        notes.append("Dữ liệu chỉ nằm trong 1 giờ nên bỏ qua heatmap theo giờ.")

    cong = df["congestion"].value_counts(normalize=True).sort_index().mul(100).round(1)
    worst = stats.index[0]

    lines = [
        "# Kết quả phân tích tự động\n",
        "## 1. Chất lượng dữ liệu\n",
        f"- Số bản ghi: **{q['n_rows']}** ({q['n_points']} điểm x {q['n_cycles']} lượt crawl)",
        f"- Khoảng thời gian: {q['start']:%Y-%m-%d %H:%M} đến {q['end']:%Y-%m-%d %H:%M} (giờ Việt Nam)",
        f"- Chu kỳ crawl trung vị: {q['median_interval_s']:.0f} giây" if q["n_cycles"] > 1 else "- Chu kỳ crawl: chỉ có 1 lượt",
        f"- Số bản ghi thiếu so với lý thuyết: {q['missing_rows']}",
        f"- Số khoảng trống thời gian lớn hơn 1,5 lần chu kỳ: {q['n_gaps']} (dài nhất {q['max_gap_min']:.1f} phút)" if q["n_cycles"] > 1 else "",
        f"- Số ô dữ liệu rỗng (null): {q['null_cells']}",
        f"- Số bản ghi báo đường bị đóng (`road_closure = true`): {q['road_closure_rows']}",
        "- Các điểm bị gắn vào **cùng một đoạn đường** (dữ liệu trùng nhau): "
        + (", ".join("/".join(g) for g in q["duplicate_segment_groups"]) if q["duplicate_segment_groups"] else "không có"),
        "",
        "## 2. Thống kê theo điểm (sắp xếp từ tắc nhất)\n",
        to_md(stats),
        "",
        "## 3. Phân bố mức ùn tắc (% bản ghi)\n",
        to_md(cong.to_frame("percent")),
        "",
        f"Điểm có tỷ lệ tốc độ trung bình thấp nhất: **{worst}**.\n",
        "## 4. Thống kê mô tả các biến số\n",
        to_md(df[["current_speed", "free_flow_speed", "speed_ratio", "delay_s",
                  "current_tt", "free_flow_tt", "confidence"]].describe().round(3)),
        "",
    ]
    if has_area(df):
        lines += ["## 5. Thống kê theo khu vực (nhóm các đường đã chọn trong khu vực)\n", to_md(area_stats(df)), ""]
    lines += [f"> Ghi chú: {n}" for n in notes]
    (out / "summary.md").write_text("\n".join(l for l in lines if l is not None), encoding="utf-8")
    print(f"Đã ghi kết quả vào {out}/")
    for n in notes:
        print("Ghi chú:", n)


if __name__ == "__main__":
    main()
