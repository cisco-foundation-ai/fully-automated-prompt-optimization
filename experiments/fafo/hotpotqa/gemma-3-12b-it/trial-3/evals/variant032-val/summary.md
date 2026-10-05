# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- exact_match: 58.33
- f1: 66.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.045 | 0.002 | 0.009 |
| summarize_hop1 | 2.249 | 2.082 | 3.695 |
| query_hop2 | 1.029 | 0.998 | 1.487 |
| retrieve_hop2 | 0.510 | 0.003 | 1.580 |
| summarize_hop2 | 3.642 | 3.556 | 6.075 |
| answer | 0.887 | 0.833 | 1.274 |
| **Total** | **8.363** | **8.029** | **12.445** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 125 |
