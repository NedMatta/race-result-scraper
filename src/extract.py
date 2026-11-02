"""Step 1 - Ingestion: download race results from the TimeTo public results API.

The results.timeto.com pages are a JavaScript app; the data actually comes from
https://sportinnovation.fr/api. We call that API directly (cleaner and faster
than scraping HTML). Endpoints used:

  GET /events/custom-url/{event_slug}   -> resolve event id from its URL slug
  GET /events/{event_id}                -> event metadata
  GET /events/{event_id}/races          -> list of races within the event
  GET /races/{race_slug}/results        -> full ranking (JSON array)

Usage: python3 src/extract.py
Output: data/raw/*.json
"""

import json
import time
import urllib.request
from pathlib import Path

API_BASE = "https://sportinnovation.fr/api"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Event URL slug (as used on results.timeto.com) -> local file prefix
EVENTS = {
    "harmonie_mutuelle_semi_de_paris_2025": "semi_de_paris",
    "10k_montmartre": "10k_montmartre",
}

# Politeness: pause between requests so we do not hammer the server.
REQUEST_DELAY_SECONDS = 2.0


def get_json(url: str):
    """Perform a GET request and parse the JSON response."""
    req = urllib.request.Request(url, headers={"User-Agent": "race-analysis-etl/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def ingest_event(event_slug: str, prefix: str) -> None:
    """Download metadata and full results for one event."""
    print(f"--- Event: {event_slug}")

    # 1. Resolve the event id from the public URL slug.
    event_id = get_json(f"{API_BASE}/events/custom-url/{event_slug}")["eventId"]
    print(f"eventId: {event_id}")

    # 2. Event metadata.
    event = get_json(f"{API_BASE}/events/{event_id}")
    (RAW_DIR / f"event_{prefix}.json").write_text(
        json.dumps(event, ensure_ascii=False), encoding="utf-8"
    )
    time.sleep(REQUEST_DELAY_SECONDS)

    # 3. Races within the event.
    races = get_json(f"{API_BASE}/events/{event_id}/races")
    (RAW_DIR / f"races_{prefix}.json").write_text(
        json.dumps(races, ensure_ascii=False), encoding="utf-8"
    )
    print(f"races found: {len(races)}")

    # 4. Full ranking of each race (one file per race, named with race slug).
    for race in races:
        race_slug = race["slug"]
        print(f"  downloading results for: {race['title']} ({race_slug})")
        results = get_json(f"{API_BASE}/races/{race_slug}/results")
        out = RAW_DIR / f"results_{prefix}__{race_slug}.json"
        out.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        print(f"    rows: {len(results)} -> {out.name}")
        time.sleep(REQUEST_DELAY_SECONDS)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for event_slug, prefix in EVENTS.items():
        ingest_event(event_slug, prefix)


if __name__ == "__main__":
    main()
