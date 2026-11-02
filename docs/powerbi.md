# Power BI setup guide

## Connection
1. Power BI Desktop > Get data > Text/CSV.
2. Import the 3 star-schema tables + the analysis tables:
   - fact_results.csv (facts)
   - dim_race.csv, dim_category.csv (dimensions)
   - analysis_race_summary.csv, analysis_category.csv, analysis_time_buckets.csv (pre-aggregates)
3. Model > Manage relationships:
   - fact_results[race_key] -> dim_race[race_key] (many to one)
   - fact_results[category_code] -> dim_category[category_code] (many to one)

## Recommended visuals
- Distribution: bar chart of finishers per 10-min bucket (analysis_time_buckets, x=bucket_minutes, y=finishers, legend=race).
- Performance profile: percentile comparison using analysis_race_summary (median, p10, p25, p75, p90).
- Categories: clustered bar of median_hms per category_code (analysis_category).
- Personal tracking: filter fact_results on last_name/first_name or runner_slug, show time_hms, ranks, pace over races.

## Measures (DAX, minimal set)
- Finishers = COUNTROWS(FILTER(fact_results, fact_results[is_finisher] = 1))
- Median Time (s) = MEDIAN(fact_results[time_sec])
- Pace (s/km) = AVERAGE(fact_results[pace_sec_per_km])

## Mobile access
Publish to the Power BI Service, open the report in the Power BI mobile app
(iOS/Android). Less than 2 clicks from the home screen.
