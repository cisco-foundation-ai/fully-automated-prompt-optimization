# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.46

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.015 | 0.002 | 0.007 |
| summarize_hop1 | 5.466 | 4.789 | 10.504 |
| query_hop2 | 2.195 | 2.023 | 3.322 |
| retrieve_hop2 | 0.649 | 0.003 | 1.581 |
| summarize_hop2 | 4.385 | 3.953 | 7.711 |
| answer | 1.730 | 1.518 | 2.801 |
| **Total** | **14.441** | **13.540** | **21.884** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
