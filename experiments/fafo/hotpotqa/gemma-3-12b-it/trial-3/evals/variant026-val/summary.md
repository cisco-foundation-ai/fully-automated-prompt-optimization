# Evaluation Summary

Total cases: 300

## Composite Score
- average: 54.33

## Score Breakdown
- exact_match: 54.33
- f1: 63.38

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.011 |
| summarize_hop1 | 1.186 | 1.129 | 1.577 |
| query_hop2 | 0.963 | 0.919 | 1.269 |
| retrieve_hop2 | 0.711 | 0.004 | 1.615 |
| summarize_hop2 | 2.356 | 2.345 | 3.260 |
| answer | 1.104 | 1.022 | 1.740 |
| **Total** | **6.346** | **6.101** | **8.331** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 137 |
