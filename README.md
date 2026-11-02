# Race Analysis

ETL pipeline that collects running race results (Semi de Paris, 10K Montmartre)
from the public results API behind results.timeto.com, cleans them into a
star schema, and prepares them for Power BI reporting.

## Architecture

```
API (sportinnovation.fr/api)  ->  src/extract.py  ->  data/raw/*.json
data/raw/*.json               ->  src/transform.py ->  data/processed/*.csv
data/processed/*.csv          ->  src/analyze.py   ->  analysis_*.csv
```

## How to run

```bash
python3 src/extract.py     # download raw results (2s delay between calls)
python3 src/transform.py   # build star-schema CSVs
python3 src/analyze.py     # compute per-race / per-category analyses
```

Only the Python standard library is required (no pip install).

## Data model (star schema)

- `fact_results.csv` — one row per participant: rank, times, sex, category,
  nationality, pace, speed, runner slug.
- `dim_race.csv` — one row per race: event, date, distance, finisher counts.
- `dim_category.csv` — FFA category codes with labels (SEH = Senior Men...).
- `analysis_*.csv` — pre-aggregated summaries for quick charts.

Relations: fact_results.race_key -> dim_race.race_key,
fact_results.category_code -> dim_category.category_code.

## Notes

- The results.timeto.com site is a JavaScript app; all data comes from
  `https://sportinnovation.fr/api` (endpoints documented in src/extract.py).
- Public results data; requests are rate-limited (2 s) and cached in data/raw.
- Re-running extract.py refreshes the data (e.g. after a new edition).
- data/raw/ is gitignored (large JSON files); regenerate it with extract.py.
