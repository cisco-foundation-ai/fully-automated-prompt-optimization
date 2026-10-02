# Evaluation Summary

Total cases: 300

## Composite Score
- average: 35.00

## Score Breakdown
- exact_match: 35.00
- f1: 51.54

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.010 |
| summarize_hop1 | 4.617 | 3.899 | 8.827 |
| query_hop2 | 3.125 | 2.401 | 7.066 |
| retrieve_hop2 | 1.109 | 1.309 | 1.645 |
| summarize_hop2 | 3.711 | 2.856 | 6.496 |
| answer | 2.957 | 2.330 | 5.869 |
| **Total** | **15.524** | **13.811** | **26.779** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 195 |
