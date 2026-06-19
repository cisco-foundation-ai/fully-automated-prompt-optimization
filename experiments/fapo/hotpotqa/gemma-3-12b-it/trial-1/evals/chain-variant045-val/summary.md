# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 72.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.035 | 0.002 | 0.014 |
| summarize_hop1 | 2.449 | 2.262 | 4.250 |
| query_hop2 | 1.090 | 1.019 | 1.606 |
| retrieve_hop2 | 0.467 | 0.002 | 1.621 |
| summarize_hop2 | 2.895 | 2.540 | 4.262 |
| answer | 1.114 | 0.990 | 1.862 |
| **Total** | **8.049** | **7.634** | **11.905** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
