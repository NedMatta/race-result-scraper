"""Step 3 - Analysis: compute per-race and per-category insights.

Reads the star-schema CSVs and produces:
  - analysis_race_summary.csv   one row per race with key metrics
  - analysis_category.csv       per race x category statistics
  - analysis_time_buckets.csv   finisher distribution by 10-minute bucket
  - a console report with the headline numbers

Usage: python3 src/analyze.py
"""

import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PROC = BASE / "data" / "processed"


def read_csv(name):
    with (PROC / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pct(sorted_vals, p):
    """Percentile of a sorted list (nearest-rank method)."""
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, round(p / 100 * (len(sorted_vals) - 1))))
    return sorted_vals[k]


def to_num(v):
    return float(v) if v not in ("", None) else None


def secs_hms(v):
    if v is None:
        return ""
    v = int(round(v))
    return f"{v//3600:02d}:{(v%3600)//60:02d}:{v%60:02d}"


def write(name, rows):
    if not rows:
        return
    with (PROC / name).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main() -> None:
    facts = read_csv("fact_results.csv")
    races = {r["race_key"]: r for r in read_csv("dim_race.csv")}

    by_race = defaultdict(list)
    for row in facts:
        if row["is_finisher"] == "1" and row["time_sec"]:
            by_race[row["race_key"]].append(row)

    # --- race summary ---
    summaries = []
    for rk, rows in by_race.items():
        meta = races[rk]
        times = sorted(to_num(r["time_sec"]) for r in rows)
        winner = ""
        for r in rows:
            if str(r.get("general_rank")) == "1":
                winner = r["time_hms"]
                break
        summaries.append({
            "race": meta["race_title"],
            "event_date": meta["event_date"],
            "distance_km": meta["distance_km"],
            "finishers": len(rows),
            "men": sum(1 for r in rows if r["sex"] == "H"),
            "women": sum(1 for r in rows if r["sex"] == "F"),
            "winner_hms": winner,
            "median_hms": secs_hms(statistics.median(times)),
            "p10_hms": secs_hms(pct(times, 10)),
            "p25_hms": secs_hms(pct(times, 25)),
            "p75_hms": secs_hms(pct(times, 75)),
            "p90_hms": secs_hms(pct(times, 90)),
            "last_hms": secs_hms(times[-1]),
            "mean_pace_sec_km": round(statistics.mean(times) / float(meta["distance_km"]), 1),
        })
    write("analysis_race_summary.csv", summaries)

    # --- per race x category ---
    cat_stats = []
    for rk, rows in by_race.items():
        groups = defaultdict(list)
        for r in rows:
            groups[r["category_code"]].append(to_num(r["time_sec"]))
        for code, times in sorted(groups.items()):
            if len(times) < 5:
                continue
            times.sort()
            cat_stats.append({
                "race": races[rk]["race_title"],
                "category_code": code,
                "finishers": len(times),
                "median_hms": secs_hms(statistics.median(times)),
                "fastest_hms": secs_hms(times[0]),
                "p90_hms": secs_hms(pct(times, 90)),
            })
    write("analysis_category.csv", cat_stats)

    # --- distribution buckets (10 min) ---
    buckets = []
    for rk, rows in by_race.items():
        counter = Counter(int(to_num(r["time_sec"]) // 600) for r in rows)
        for b in sorted(counter):
            buckets.append({
                "race": races[rk]["race_title"],
                "bucket_minutes": b * 10,
                "bucket_label": f"{b*10}-{b*10+10} min",
                "finishers": counter[b],
                "share_pct": round(100 * counter[b] / len(rows), 2),
            })
    write("analysis_time_buckets.csv", buckets)

    # --- console report ---
    for s in summaries:
        print(f"\n=== {s['race']} ({s['event_date']}, {s['distance_km']} km)")
        print(f"finishers: {s['finishers']} ({s['men']} H / {s['women']} F)")
        print(f"winner {s['winner_hms']} | median {s['median_hms']} | "
              f"p90 {s['p90_hms']} | last {s['last_hms']}")
        print(f"mean pace: {s['mean_pace_sec_km']} s/km")


if __name__ == "__main__":
    main()
