"""Step 2 - Data preparation: turn raw JSON into a star-schema CSV set.

Star schema: one central fact table (fact_results: one row = one finisher of
one race) surrounded by small dimension tables (dim_race, dim_category).
This shape is what Power BI consumes best: small lookup tables + one big
measurable table, linked by keys.

Only the Python standard library is used (json, csv, statistics).

Usage: python3 src/transform.py
Input:  data/raw/*.json
Output: data/processed/*.csv
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
OUT = BASE / "data" / "processed"

# event file prefix -> fallback distance (km) if the race metadata is empty
EVENTS = {
    "semi_de_paris": {"distance_km": 21.0975},
    "10k_montmartre": {"distance_km": 10.0},
}

# FFA category codes: first two letters = sex+age group.
CATEGORY_LABELS = {
    "SE": "Senior", "ES": "Espoir (U23)", "JU": "Junior (U20)",
    "CA": "Cadet (U18)", "MI": "Minime (U16)", "BE": "Benjamin (U14)",
    "PO": "Poussin (U12)", "EA": "Eveil athletique", "BB": "Baby athle",
}
MASTER_RE = re.compile(r"^M(\d+)$")


def parse_category(code):
    """Split an FFA category code like 'SEH' or 'M3F' into (sex, label)."""
    if not code:
        return "", "Unknown"
    if len(code) >= 3:
        prefix, sex = code[:2], code[2]
        m = MASTER_RE.match(prefix)
        if m:
            return sex, f"Masters {m.group(1)}"
        return sex, CATEGORY_LABELS.get(prefix, prefix)
    return (code[-1] if code in ("H", "F") else ""), code


def hhmmss(seconds):
    """Seconds -> 'HH:MM:SS' text (None-safe)."""
    if seconds is None:
        return ""
    seconds = int(round(seconds))
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def _ingest_rows(rows, categories_seen, race_info, results):
    """Append one row per participant to the fact rows list."""
    race_key = race_info["slug"]
    distance = float(race_info.get("distance") or 0) or None
    for r in results:
        sex, cat_label = parse_category(r.get("category"))
        categories_seen[r.get("category") or "NA"] = [r.get("category") or "NA", sex, cat_label]
        off_sec = r.get("officialTimeFfaSec")
        real_sec = r.get("realTimeFfaSec")
        time_sec = off_sec or real_sec
        rows.append({
            "race_key": race_key,
            "bib": r.get("bib"),
            "first_name": r.get("firstName") or "",
            "last_name": r.get("lastName") or "",
            "runner_slug": r.get("runnerSlug") or "",
            "sex": r.get("sex") or sex,
            "nationality": r.get("nationality") or "",
            "category_code": r.get("category") or "NA",
            "is_finisher": 1 if time_sec else 0,
            "official_time_sec": off_sec or "",
            "real_time_sec": real_sec or "",
            "time_sec": time_sec or "",
            "time_hms": hhmmss(time_sec) if time_sec else "",
            "general_rank": r.get("officialGeneralRank") or r.get("realGeneralRank") or "",
            "sex_rank": r.get("officialSexRank") or r.get("realSexRank") or "",
            "category_rank": r.get("officialCategoryRank") or r.get("realCategoryRank") or "",
            "pace_sec_per_km": round(time_sec / distance, 1) if time_sec and distance else "",
            "speed_kmh": round(distance / (time_sec / 3600), 2) if time_sec and distance else "",
            "club": r.get("clubName") or "",
            "team": r.get("teamName") or "",
            "status": r.get("status") or "",
        })


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    categories_seen = {}
    rows = []
    races = []

    for prefix, meta in EVENTS.items():
        event = load(f"event_{prefix}.json")
        race_list = load(f"races_{prefix}.json")
        for race_info in race_list:
            race_slug = race_info["slug"]
            results_file = f"results_{prefix}__{race_slug}.json"
            try:
                results = load(results_file)
            except FileNotFoundError:
                print(f"  WARNING: {results_file} missing, skipping race {race_slug}")
                continue
            distance = float(race_info.get("distance") or meta["distance_km"])
            race_key = race_slug

            races.append({
                "race_key": race_key,
                "event_title": event["title"],
                "race_title": race_info["title"],
                "event_date": event["eventDate"],
                "distance_km": distance,
                "organizer": event.get("entity") or "",
                "finishers": sum(1 for r in results if r.get("officialTimeFfaSec")),
                "rows": len(results),
            })
            _ingest_rows(rows, categories_seen, race_info, results)

    # --- fact_results (one row per participant) ---
    fact_path = OUT / "fact_results.csv"
    with fact_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"fact_results.csv: {len(rows)} rows")

    # --- dim_race ---
    with (OUT / "dim_race.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(races[0].keys()))
        writer.writeheader()
        writer.writerows(races)
    print(f"dim_race.csv: {len(races)} rows")

    # --- dim_category ---
    cats = sorted(categories_seen.values(), key=lambda c: (c[1], c[0]))
    with (OUT / "dim_category.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category_code", "sex", "category_label"])
        writer.writerows(cats)
    print(f"dim_category.csv: {len(cats)} rows")

    for r in races:
        print(f"  {r['race_title']}: {r['finishers']} finishers / {r['rows']} rows")


if __name__ == "__main__":
    main()
